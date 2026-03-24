"""Enrich raw LinkedIn job postings with LLM-extracted structured fields.

Public API
----------
build_extraction_prompt      : build prompt asking LLM to extract structured fields
parse_extraction_response    : parse LLM JSON with strict fallback contract
merge_scraped_and_enriched   : combine scraper metadata + LLM parsed dict
enrich_job                   : call Gemini for one job (integration)
enrich_batch                 : batch enrichment with rate limiting (integration)
load_structured_jobs         : MERGE upsert into fitcv.structured_jobs (integration)
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

# ── enum definitions (fallbacks — overridden by taxonomy.yaml via config) ──────

_FALLBACK_LOCATION_TYPES: frozenset[str] = frozenset({"remote", "hybrid", "onsite"})
_FALLBACK_SENIORITY_ENRICH: frozenset[str] = frozenset({"junior", "mid", "senior", "lead"})


def _get_valid_location_types(config: dict | None) -> frozenset[str]:
    if config:
        vals = config.get("valid_location_types")
        if vals:
            return frozenset(str(v).lower() for v in vals)
    return _FALLBACK_LOCATION_TYPES


def _get_valid_seniority_enrich(config: dict | None) -> frozenset[str]:
    if config:
        vals = config.get("valid_seniority_enrich")
        if vals:
            return frozenset(str(v).lower() for v in vals)
    return _FALLBACK_SENIORITY_ENRICH

# ── schema: which fields are arrays vs scalars ─────────────────────────────────

_ARRAY_FIELDS: frozenset[str] = frozenset({
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "tech_stack",
    "keywords",
})

_SCALAR_FIELDS: frozenset[str] = frozenset({
    "location_type",
    "seniority",
    "domain",
    "job_family",
    "years_experience_min",
    "years_experience_max",
})

_KNOWN_FIELDS: frozenset[str] = _ARRAY_FIELDS | _SCALAR_FIELDS

# ── Markdown fence stripper ───────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences if present."""
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


# ── field coercion ────────────────────────────────────────────────────────────

def _normalize_enum(value: Any, valid: frozenset[str]) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.lower().strip()
    return lowered if lowered in valid else None


def _coerce_field(key: str, value: Any, config: dict | None = None) -> Any:
    """Coerce a raw LLM value to its canonical Python type."""
    if key in _ARRAY_FIELDS:
        if value is None or not isinstance(value, list):
            return []
        return [str(v) for v in value if v is not None]

    if key == "location_type":
        return _normalize_enum(value, _get_valid_location_types(config))

    if key == "seniority":
        return _normalize_enum(value, _get_valid_seniority_enrich(config))

    if key in ("years_experience_min", "years_experience_max"):
        if isinstance(value, (int, float)):
            return int(value)
        return None

    if key in ("job_family", "domain"):
        if isinstance(value, str) and value.strip():
            return value.lower().strip()
        return None

    return value


# ── prompt construction ───────────────────────────────────────────────────────

_EXTRACTION_SCHEMA = """\
{
  "required_skills":      ["list", "of", "required", "skills"],
  "preferred_skills":     ["nice-to-have skills"],
  "responsibilities":     ["key responsibilities"],
  "tech_stack":           ["specific tools and technologies"],
  "keywords":             ["searchable keywords"],
  "location_type":        "remote | hybrid | onsite",
  "seniority":            "junior | mid | senior | lead",
  "domain":               "business/industry domain, e.g. banking, fintech, healthcare",
  "job_family":           "role category, e.g. data_engineering, analytics, data_science, ml_engineering",
  "years_experience_min": 0,
  "years_experience_max": null
}"""


def build_extraction_prompt(
    description: str,
    scraped_metadata: dict[str, Any],
) -> str:
    """Build a Gemini extraction prompt for structured JD fields.

    The prompt is designed to extract only fields NOT already available in
    the scraped metadata. The LLM is instructed to return valid JSON only.

    Important field definitions embedded in the prompt:
    - job_family = role category (what you do)
    - domain = business/industry domain (what industry you do it in)
    - seniority = normalized from JD TEXT, distinct from scraped experience_level
    """
    metadata_block = json.dumps(scraped_metadata, ensure_ascii=False, indent=2)

    return f"""You are an expert recruiter extracting structured information from job descriptions.

The following metadata was already scraped directly from LinkedIn and is available:
{metadata_block}

Your task is to extract ONLY the fields listed in the JSON schema below from the job
description text. Do not repeat or infer fields already present in the scraped metadata.

FIELD DEFINITIONS:
- job_family: the ROLE CATEGORY (what you do), e.g. data_engineering, analytics, data_science, ml_engineering
- domain: the BUSINESS/INDUSTRY domain (what industry you do it in), e.g. banking, fintech, healthcare, retail
- seniority: normalized level inferred from the JD TEXT (not the LinkedIn label). Values: junior / mid / senior / lead.
  Example: if the JD says "5+ years required" but LinkedIn shows "Entry level", infer seniority = mid.
- location_type: must be exactly one of: remote, hybrid, onsite

Return ONLY a valid JSON object matching this schema. No markdown, no explanation:
{_EXTRACTION_SCHEMA}

JOB DESCRIPTION:
{description}"""


# ── response parsing ──────────────────────────────────────────────────────────

def parse_extraction_response(response_text: str, config: dict | None = None) -> dict[str, Any]:
    """Parse LLM extraction response with explicit fallback contract.

    Returns:
        {
            "parsed": dict of validated/coerced known fields,
            "errors": list of error strings (empty on full success),
            "raw_response": original response_text unchanged,
        }

    Contract:
        - Strips Markdown code fences before parsing
        - Invalid JSON → parsed = {}, error recorded, no crash
        - Missing field → [] for arrays, None for scalars
        - Unknown keys → silently ignored
        - Null list values → coerced to []
        - Enum fields (location_type, seniority) → lowercased; unrecognized → None
        - job_family, domain → lowercased free strings
    """
    errors: list[str] = []
    cleaned = _strip_markdown_fences(response_text)

    try:
        raw: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {
            "parsed": {},
            "errors": [f"JSON parse error: {exc}"],
            "raw_response": response_text,
        }

    if not isinstance(raw, dict):
        return {
            "parsed": {},
            "errors": ["LLM response was valid JSON but not an object"],
            "raw_response": response_text,
        }

    parsed: dict[str, Any] = {}
    for field in _KNOWN_FIELDS:
        raw_value = raw.get(field)
        parsed[field] = _coerce_field(field, raw_value, config)

    return {
        "parsed": parsed,
        "errors": errors,
        "raw_response": response_text,
    }


# ── merge ─────────────────────────────────────────────────────────────────────

def merge_scraped_and_enriched(
    scraped: dict[str, Any],
    enriched: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine scraper metadata and LLM-parsed dict into structured_jobs schema.

    Args:
        scraped:  Normalized scraped job dict (snake_case keys).
        enriched: The `parsed` dict from parse_extraction_response().
        config:   Project config; used for enrichment_version and ai_score_model.

    Returns:
        Merged dict matching fitcv.structured_jobs schema including audit fields.
    """
    cfg = config or {}
    model = str(cfg.get("ai_score_model", ""))
    version = str(cfg.get("enrichment_version", "v1"))

    merged: dict[str, Any] = {
        # ── scraped fields ────────────────────────────────────────────
        "job_url":            scraped.get("job_url", ""),
        "title":              scraped.get("title", ""),
        "company_name":       scraped.get("company_name", ""),
        "company_id":         scraped.get("company_id", ""),
        "location":           scraped.get("location", ""),
        "contract_type":      scraped.get("contract_type", ""),
        "experience_level":   scraped.get("experience_level", ""),
        "sector":             scraped.get("sector", ""),
        "salary_min":         scraped.get("salary_min"),
        "salary_max":         scraped.get("salary_max"),
        "salary_currency":    scraped.get("salary_currency"),
        "applications_count": scraped.get("applications_count_int"),
        "published_at":       scraped.get("published_at"),
        "description_cleaned": scraped.get("description", ""),
        # ── LLM-enriched fields ───────────────────────────────────────
        "location_type":        enriched.get("location_type"),
        "seniority":            enriched.get("seniority"),
        "required_skills":      enriched.get("required_skills", []),
        "preferred_skills":     enriched.get("preferred_skills", []),
        "responsibilities":     enriched.get("responsibilities", []),
        "domain":               enriched.get("domain"),
        "tech_stack":           enriched.get("tech_stack", []),
        "years_experience_min": enriched.get("years_experience_min"),
        "years_experience_max": enriched.get("years_experience_max"),
        "keywords":             enriched.get("keywords", []),
        "job_family":           enriched.get("job_family"),
        # ── audit fields ──────────────────────────────────────────────
        "enrichment_version": version,
        "enrichment_model":   model,
        "enriched_at":        datetime.now(tz=timezone.utc).isoformat(),
    }
    return merged


# ── integration: LLM call ─────────────────────────────────────────────────────

def enrich_job(job: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini to extract structured fields from one normalized job.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.

    Returns:
        Merged dict ready for load_structured_jobs().
    """
    import vertexai  # type: ignore[import-untyped]
    from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]

    vertexai.init(
        project=str(config["gcp_project"]),
        location=str(config.get("location", "us-central1")),
    )
    model_name = str(config.get("gemini_model", "gemini-2.0-flash"))
    model = GenerativeModel(model_name)

    prompt = build_extraction_prompt(
        description=str(job.get("description", "")),
        scraped_metadata={
            "title": job.get("title", ""),
            "experienceLevel": job.get("experience_level", ""),
            "contractType": job.get("contract_type", ""),
            "sector": job.get("sector", ""),
            "location": job.get("location", ""),
        },
    )
    response = model.generate_content(prompt)
    extraction = parse_extraction_response(response.text)
    return merge_scraped_and_enriched(job, extraction["parsed"], config)


def enrich_batch(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Enrich a batch of normalized jobs with rate limiting.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    import time

    results: list[dict[str, Any]] = []
    for i, job in enumerate(normalized_jobs):
        enriched = enrich_job(job, config)
        results.append(enriched)
        # Simple rate limit: 1 req/s to stay within Gemini free-tier limits
        if i < len(normalized_jobs) - 1:
            time.sleep(1.0)
    return results


# ── integration: BigQuery upsert ──────────────────────────────────────────────

_MERGE_COLUMNS = [
    "title", "company_name", "company_id", "location", "contract_type",
    "experience_level", "sector", "salary_min", "salary_max", "salary_currency",
    "applications_count", "published_at", "location_type", "seniority",
    "required_skills", "preferred_skills", "responsibilities", "domain",
    "tech_stack", "years_experience_min", "years_experience_max", "keywords",
    "job_family", "description_cleaned", "enrichment_version", "enrichment_model",
    "enriched_at",
]


def load_structured_jobs(
    enriched: list[dict[str, Any]],
    config: dict[str, Any],
) -> int:
    """Upsert enriched job rows into fitcv.structured_jobs via MERGE on job_url.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.

    Returns:
        Number of rows upserted.
    """
    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)

    target = f"`{project}.{dataset}.structured_jobs`"
    update_set = ",\n    ".join(
        f"T.{col} = S.{col}" for col in _MERGE_COLUMNS
    )
    insert_cols = ", ".join(["job_url"] + _MERGE_COLUMNS)
    insert_vals = ", ".join([f"S.{c}" for c in ["job_url"] + _MERGE_COLUMNS])

    rows_json = json.dumps(enriched, default=str)
    temp_table = f"`{project}.{dataset}._enrich_staging`"

    # Load to a temp table first, then MERGE
    staging_ref = f"{project}.{dataset}._enrich_staging"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    ndjson = "\n".join(json.dumps(row, default=str) for row in enriched)
    load_job = client.load_table_from_json(
        [json.loads(r) for r in ndjson.splitlines()],
        staging_ref,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE", autodetect=True),
    )
    load_job.result()

    merge_sql = f"""
    MERGE {target} AS T
    USING {temp_table} AS S
    ON T.job_url = S.job_url
    WHEN MATCHED THEN UPDATE SET
        {update_set}
    WHEN NOT MATCHED THEN INSERT ({insert_cols})
    VALUES ({insert_vals})
    """
    client.query(merge_sql).result()
    return len(enriched)
