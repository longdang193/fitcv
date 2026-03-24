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

Config keys consumed (loaded via config.py from taxonomy.yaml / skill_synonyms.yaml)
-------------------------------------------------------------------------------------
config["seniority"]["ladder"]    : ordered list of seniority levels
config["seniority"]["aliases"]   : alias → canonical mapping
config["skill_synonyms"]         : alias → canonical skill mapping
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── built-in fallbacks (used when config is not passed) ───────────────────────
# Kept here so unit tests that don't inject config still pass.

_FALLBACK_SENIORITY_LADDER: list[str] = [
    "intern", "entry", "associate", "mid", "senior", "lead", "manager", "director",
]

_FALLBACK_SENIORITY_ALIASES: dict[str, str] = {
    "junior": "entry", "jr": "entry", "sr": "senior",
    "staff": "lead", "principal": "lead", "vp": "director", "vice president": "director",
}

_FALLBACK_SKILL_SYNONYMS: dict[str, str] = {
    "gcp": "google cloud", "google cloud platform": "google cloud",
    "bigquery": "google bigquery", "big query": "google bigquery",
    "k8s": "kubernetes", "aws": "amazon web services", "azure": "microsoft azure",
    "ml": "machine learning", "nlp": "natural language processing",
    "postgres": "postgresql", "pg": "postgresql",
}


# ── config helpers ────────────────────────────────────────────────────────────

def _get_seniority_ladder(config: dict[str, Any] | None) -> list[str]:
    """Return the ordered seniority ladder from config, or the built-in fallback."""
    if config:
        seniority = config.get("seniority", {})
        if isinstance(seniority, dict) and seniority.get("ladder"):
            return list(seniority["ladder"])
    return _FALLBACK_SENIORITY_LADDER


def _get_seniority_aliases(config: dict[str, Any] | None) -> dict[str, str]:
    """Return the seniority alias map from config, or the built-in fallback."""
    if config:
        seniority = config.get("seniority", {})
        if isinstance(seniority, dict) and seniority.get("aliases"):
            return {str(k).lower(): str(v).lower() for k, v in seniority["aliases"].items()}
    return _FALLBACK_SENIORITY_ALIASES


def _get_skill_synonyms(config: dict[str, Any] | None) -> dict[str, str]:
    """Return the skill synonym map from config, or the built-in fallback."""
    if config:
        synonyms = config.get("skill_synonyms")
        if isinstance(synonyms, dict) and synonyms:
            return {str(k).lower(): str(v).lower() for k, v in synonyms.items()}
    return _FALLBACK_SKILL_SYNONYMS


# ── seniority normalisation ───────────────────────────────────────────────────

def _normalise_seniority(
    raw: str | None,
    config: dict[str, Any] | None = None,
) -> str | None:
    """Map raw seniority string to a canonical ladder value, or None if unknown."""
    if not raw:
        return None
    ladder = _get_seniority_ladder(config)
    aliases = _get_seniority_aliases(config)
    lowered = raw.strip().lower()
    mapped = aliases.get(lowered, lowered)
    return mapped if mapped in ladder else None


def check_seniority(
    job: dict[str, Any],
    prefs: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> bool:
    """Return True if the job seniority is within ±1 step of the target.

    Rules:
    - target ± 1 step → pass
    - target + 2 or more → reject (too senior)
    - target - 2 or more → reject (too junior)
    - unknown seniority (None / unrecognised) → pass with warning
    """
    ladder = _get_seniority_ladder(config)
    target_raw = prefs.get("seniority_target", "")
    job_raw = job.get("seniority")

    target = _normalise_seniority(target_raw, config)
    job_seniority = _normalise_seniority(job_raw, config)

    if target is None:
        logger.warning("Unknown seniority_target '%s' in preferences — skipping check", target_raw)
        return True
    if job_seniority is None:
        logger.warning("Job '%s' has unknown seniority '%s' — keeping", job.get("job_url"), job_raw)
        return True

    target_idx = ladder.index(target)
    job_idx = ladder.index(job_seniority)
    return -1 <= (job_idx - target_idx) <= 1


# ── skill canonicalisation ────────────────────────────────────────────────────

def _canonicalise_skill(skill: str, config: dict[str, Any] | None = None) -> str:
    """Return the canonical form of a skill name (lower-cased, synonym-resolved)."""
    synonyms = _get_skill_synonyms(config)
    lower = skill.strip().lower()
    return synonyms.get(lower, lower)


# ── individual checks ─────────────────────────────────────────────────────────

def check_location_type(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job location_type matches any preferred type.

    Empty preferred_locations = no preference → accept everything.
    """
    allowed = [t.lower() for t in prefs.get("location_types", [])]
    if not allowed:
        return True
    return (job.get("location_type") or "").lower() in allowed


def check_contract_type(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job contract_type is in the allowed list."""
    allowed = [t.lower() for t in prefs.get("contract_types", [])]
    if not allowed:
        return True
    return (job.get("contract_type") or "").lower() in allowed


def check_experience_level(job: dict[str, Any], prefs: dict[str, Any]) -> bool:
    """Return True if job experience_level is NOT in the exclusion list.

    experience_level (raw LinkedIn label) is used for exclusion only.
    seniority (LLM-normalised) is the primary signal — handled by check_seniority.
    """
    excluded = [e.lower() for e in prefs.get("exclude_experience_levels", [])]
    return (job.get("experience_level") or "").lower() not in excluded


def check_must_have_skills(
    job: dict[str, Any],
    prefs: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> bool:
    """Return True if all must-have skills appear in the job's required_skills.

    Uses the synonym map (from config or built-in fallback) and case-insensitive
    comparison before checking overlap.
    """
    must_haves = prefs.get("must_have_skills", [])
    if not must_haves:
        return True
    job_skills_canonical = {
        _canonicalise_skill(s, config) for s in (job.get("required_skills") or [])
    }
    return all(_canonicalise_skill(skill, config) in job_skills_canonical for skill in must_haves)


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
            pub_date = published_at
        return (datetime.now(tz=timezone.utc) - pub_date).days <= max_age
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
    return (job.get("domain") or "").lower() in preferred


# ── orchestrator ──────────────────────────────────────────────────────────────

def apply_rule_filters(
    jobs: list[dict[str, Any]],
    prefs: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, list]:
    """Apply all policy checks and return {passed, rejected}.

    Return contract:
        {
            "passed": ["url1", "url3", ...],
            "rejected": [
                {"job_url": "url2", "reasons": ["seniority_mismatch", "contract_type_excluded"]}
            ]
        }

    config: merged config dict (from load_config). When None, built-in fallbacks apply.

    Note: experience_level is used for exclusion only. seniority is the primary signal.
    Conflicts (e.g. experience_level=Entry + seniority=mid) are logged but not auto-rejected.
    """
    checks: list[tuple[str, Any]] = [
        ("seniority_mismatch",        lambda j, p: check_seniority(j, p, config)),
        ("location_type_excluded",    check_location_type),
        ("contract_type_excluded",    check_contract_type),
        ("experience_level_excluded", check_experience_level),
        ("must_have_skill_missing",   lambda j, p: check_must_have_skills(j, p, config)),
        ("job_too_stale",             check_freshness),
        ("domain_not_preferred",      check_domain_preference),
    ]

    passed: list[str] = []
    rejected: list[dict[str, Any]] = []

    for job in jobs:
        reasons: list[str] = []
        for reason_code, check_fn in checks:
            if not check_fn(job, prefs):
                reasons.append(reason_code)

        # Log seniority / experience_level conflicts (do not auto-reject)
        exp_level = (job.get("experience_level") or "").lower()
        seniority = _normalise_seniority(job.get("seniority"), config)
        if exp_level in ("entry level", "internship") and seniority not in (None, "entry", "intern"):
            logger.info(
                "Conflict: experience_level='%s', seniority='%s' for job '%s'",
                job.get("experience_level"), job.get("seniority"), job.get("job_url"),
            )

        if reasons:
            rejected.append({"job_url": str(job.get("job_url", "")), "reasons": reasons})
        else:
            passed.append(str(job.get("job_url", "")))

    return {"passed": passed, "rejected": rejected}


# ── integration: persist to BigQuery ─────────────────────────────────────────

def store_filter_results(result: dict[str, list], config: dict[str, Any]) -> None:
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
            "job_url": item["job_url"], "passed": False,
            "reasons": item["reasons"], "filtered_at": now,
        })

    if rows:
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors for rule_filter_results: {errors}")
