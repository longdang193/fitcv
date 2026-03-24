"""Rule-based job filtering — deterministic policy layer before semantic retrieval.

Public API
----------
check_seniority          : seniority ladder match (±1 pass, ±2 reject, unknown=keep)
check_location_type      : job location_type in preferred list
check_contract_type      : contract_type in allowed list
check_experience_level   : exclusion filter on raw LinkedIn experience_level label
check_must_have_skills   : candidate must-haves present in JD (with synonym map)
check_freshness          : published_at within max_age_days window
check_domain_preference  : job domain in preferred list (empty = accept all)
apply_rule_filters       : compose all checks → {passed, rejected}
store_filter_results     : persist results to BigQuery (integration)

Return contract
---------------
apply_rule_filters returns:
    {
        "passed": ["url1", "url3", ...],
        "rejected": [
            {"job_url": "url2", "reasons": ["seniority_mismatch", "contract_type_excluded"]}
        ]
    }
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── seniority ladder ──────────────────────────────────────────────────────────

_SENIORITY_LADDER: list[str] = [
    "intern",
    "entry",
    "associate",
    "mid",
    "senior",
    "lead",
    "manager",
    "director",
]

_SENIORITY_ALIASES: dict[str, str] = {
    # common LinkedIn / LLM aliases → canonical ladder values
    "junior": "entry",
    "jr": "entry",
    "sr": "senior",
    "staff": "lead",
    "principal": "lead",
    "vp": "director",
    "vice president": "director",
}


def _normalise_seniority(raw: str | None) -> str | None:
    """Map raw seniority string to a canonical ladder value, or None if unknown."""
    if not raw:
        return None
    lowered = raw.strip().lower()
    # try alias map first
    mapped = _SENIORITY_ALIASES.get(lowered, lowered)
    return mapped if mapped in _SENIORITY_LADDER else None


def check_seniority(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if the job seniority is within ±1 step of the target.

    Rules:
    - target ± 1 step → pass
    - target + 2 or more → reject (too senior)
    - target - 2 or more → reject (too junior)
    - unknown seniority (None / unrecognised) → pass with warning
    """
    target_raw = prefs.get("seniority_target", "")
    job_raw = job.get("seniority")

    target = _normalise_seniority(target_raw)
    job_seniority = _normalise_seniority(job_raw)

    if target is None:
        logger.warning("Unknown seniority_target '%s' in preferences — skipping check", target_raw)
        return True

    if job_seniority is None:
        logger.warning("Job '%s' has unknown seniority '%s' — keeping", job.get("job_url"), job_raw)
        return True  # do not hard-reject unknown

    target_idx = _SENIORITY_LADDER.index(target)
    job_idx = _SENIORITY_LADDER.index(job_seniority)
    diff = job_idx - target_idx

    return -1 <= diff <= 1


# ── skill synonym map ─────────────────────────────────────────────────────────

_SKILL_SYNONYMS: dict[str, str] = {
    # canonical form → normalised form (both sides normalised to lower for lookup)
    "gcp": "google cloud",
    "google cloud platform": "google cloud",
    "bigquery": "google bigquery",
    "big query": "google bigquery",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "azure": "microsoft azure",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "postgres": "postgresql",
    "pg": "postgresql",
}


def _canonicalise_skill(skill: str) -> str:
    """Return the canonical form of a skill name (lower-cased, synonym-resolved)."""
    lower = skill.strip().lower()
    return _SKILL_SYNONYMS.get(lower, lower)


# ── individual checks ─────────────────────────────────────────────────────────

def check_location_type(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job location_type matches any preferred type.

    Empty preferred_locations = no preference → accept everything.
    """
    allowed = [t.lower() for t in prefs.get("location_types", [])]
    if not allowed:
        return True
    job_location = (job.get("location_type") or "").lower()
    return job_location in allowed


def check_contract_type(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job contract_type is in the allowed list."""
    allowed = [t.lower() for t in prefs.get("contract_types", [])]
    if not allowed:
        return True
    job_contract = (job.get("contract_type") or "").lower()
    return job_contract in allowed


def check_experience_level(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job experience_level is NOT in the exclusion list.

    experience_level (raw LinkedIn label) is used for exclusion only.
    seniority (LLM-normalised) is the primary signal — handled by check_seniority.
    """
    excluded = [e.lower() for e in prefs.get("exclude_experience_levels", [])]
    job_level = (job.get("experience_level") or "").lower()
    return job_level not in excluded


def check_must_have_skills(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if all must-have skills appear in the job's required_skills.

    Uses the synonym map and case-insensitive comparison before checking overlap.
    """
    must_haves = prefs.get("must_have_skills", [])
    if not must_haves:
        return True

    job_skills_canonical = {
        _canonicalise_skill(s) for s in (job.get("required_skills") or [])
    }
    for skill in must_haves:
        if _canonicalise_skill(skill) not in job_skills_canonical:
            return False
    return True


def check_freshness(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if published_at is within max_age_days of today.

    Missing published_at → pass (cannot determine staleness).
    """
    max_age = int(prefs.get("max_age_days", 30))
    published_at = job.get("published_at")
    if not published_at:
        return True

    try:
        if isinstance(published_at, str):
            pub_date = datetime.fromisoformat(published_at.split("T")[0]).replace(tzinfo=timezone.utc)
        else:
            pub_date = published_at  # assume datetime if not str
        age_days = (datetime.now(tz=timezone.utc) - pub_date).days
        return age_days <= max_age
    except (ValueError, TypeError):
        logger.warning("Could not parse published_at '%s' — keeping job", published_at)
        return True


def check_domain_preference(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if the job domain matches any preferred domain.

    Empty preferred_domains = no preference → accept everything.
    """
    preferred = [d.lower() for d in prefs.get("preferred_domains", [])]
    if not preferred:
        return True
    job_domain = (job.get("domain") or "").lower()
    return job_domain in preferred


# ── orchestrator ──────────────────────────────────────────────────────────────

# Maps reason code → check function
_CHECKS: list[tuple[str, Any]] = [
    ("seniority_mismatch",        check_seniority),
    ("location_type_excluded",    check_location_type),
    ("contract_type_excluded",    check_contract_type),
    ("experience_level_excluded", check_experience_level),
    ("must_have_skill_missing",   check_must_have_skills),
    ("job_too_stale",             check_freshness),
    ("domain_not_preferred",      check_domain_preference),
]


def apply_rule_filters(
    jobs: list[dict[str, Any]],
    prefs: dict[str, Any],
) -> dict[str, list]:
    """Apply all policy checks and return {passed, rejected}.

    Return contract:
        {
            "passed": ["url1", "url3", ...],
            "rejected": [
                {"job_url": "url2", "reasons": ["seniority_mismatch", "contract_type_excluded"]}
            ]
        }

    Note: experience_level is used for exclusion only. seniority is the primary signal.
    Conflicts (e.g. experience_level=Entry + seniority=mid) are logged but not auto-rejected.
    """
    passed: list[str] = []
    rejected: list[dict[str, Any]] = []

    for job in jobs:
        reasons: list[str] = []
        for reason_code, check_fn in _CHECKS:
            if not check_fn(job, prefs):
                reasons.append(reason_code)

        # Log seniority / experience_level conflicts for analysis (do not auto-reject)
        exp_level = (job.get("experience_level") or "").lower()
        seniority = _normalise_seniority(job.get("seniority"))
        if (
            exp_level in ("entry level", "internship")
            and seniority not in (None, "entry", "intern")
        ):
            logger.info(
                "Conflict: experience_level='%s', seniority='%s' for job '%s'",
                job.get("experience_level"),
                job.get("seniority"),
                job.get("job_url"),
            )

        if reasons:
            rejected.append({"job_url": str(job.get("job_url", "")), "reasons": reasons})
        else:
            passed.append(str(job.get("job_url", "")))

    return {"passed": passed, "rejected": rejected}


# ── integration: persist to BigQuery ─────────────────────────────────────────

def store_filter_results(
    result: dict[str, list],
    config: dict[str, Any],
) -> None:
    """Insert rule filter results into fitcv.rule_filter_results.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.rule_filter_results"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows: list[dict[str, Any]] = []
    for job_url in result.get("passed", []):
        rows.append({"job_url": job_url, "passed": True, "reasons": [], "filtered_at": now})
    for item in result.get("rejected", []):
        rows.append({
            "job_url": item["job_url"],
            "passed": False,
            "reasons": item["reasons"],
            "filtered_at": now,
        })

    if rows:
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors for rule_filter_results: {errors}")
