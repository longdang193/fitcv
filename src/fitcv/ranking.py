"""Composite final ranking — weighted combination of rule filters, vector similarity, and AI score.

Public API
----------
compute_must_have_match  : compute ratio of candidate skills to required job skills
compute_seniority_fit    : map seniority closeness to [0.0, 1.0]
compute_title_relevance  : compute token overlap between job title and candidate target role
compute_preference_fit   : compute overlap of preferred domains/locations
compute_final_score      : compute weighted sum of features using config weights
rank_jobs                : sort jobs by final_score (then ai_score, then vector similarity)
store_final_ranking      : persist ranked list to BigQuery (integration)
"""

from datetime import datetime, timezone
from typing import Any


# ── feature computation ───────────────────────────────────────────────────────

def compute_must_have_match(
    job_skills: list[str],
    candidate_skills: list[str],
    config: dict[str, Any] | None = None,
) -> float:
    """Compute ratio of required skills matched by the candidate.

    - Uses the synonym map via config (or default if None) for canonical matching.
    - If job has no required skills, returns 0.5 (neutral, no penalty).
    - If candidate has no skills but job does, returns 0.0.
    """
    if not job_skills:
        return 0.5
    if not candidate_skills:
        return 0.0

    synonyms = (config or {}).get("skill_synonyms", {})

    def canonical(s: str) -> str:
        lower = s.strip().lower()
        return synonyms.get(lower, lower)

    reqs = {canonical(s) for s in job_skills}
    cands = {canonical(s) for s in candidate_skills}

    matched = len(reqs & cands)
    return matched / len(reqs)


def compute_seniority_fit(
    job_seniority: str | None,
    target_seniority: str | None,
    config: dict[str, Any] | None = None,
) -> float:
    """Map seniority closeness to a score in [0.0, 1.0].

    Rules:
    - exact match: 1.0
    - off by ±1 step: 0.5
    - off by ±2+ steps: 0.0
    - unknown (either side): 0.5 (neutral)
    """
    if not job_seniority or not target_seniority:
        return 0.5

    ladder = (config or {}).get("seniority", {}).get("ladder", [])
    if not ladder:
        # Fallback if config is missing
        ladder = ["intern", "entry", "associate", "mid", "senior", "lead", "manager", "director"]

    try:
        job_idx = ladder.index(job_seniority.lower())
        tgt_idx = ladder.index(target_seniority.lower())
    except ValueError:
        return 0.5

    diff = abs(job_idx - tgt_idx)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.5
    return 0.0


def compute_title_relevance(job_title: str | None, candidate_target_role: str | None) -> float:
    """Compute token overlap ratio between target role and job title.

    Ratio is: (matched target tokens) / (total target tokens).
    If either is missing, returns 0.5 (neutral).
    """
    if not job_title or not candidate_target_role:
        return 0.5

    tgt_tokens = set(candidate_target_role.lower().split())
    job_tokens = set(job_title.lower().split())

    if not tgt_tokens:
        return 0.5

    matched = len(tgt_tokens & job_tokens)
    return matched / len(tgt_tokens)


def compute_preference_fit(job: dict[str, Any], prefs: dict[str, Any]) -> float:
    """Compute fractional match of explicit preferences (domain, location_type).

    Returns 0.5 (neutral) if no preferences are explicitly set.
    """
    scored_items = 0
    matched_items = 0

    pref_domains = [d.lower() for d in prefs.get("domains", [])]
    if pref_domains:
        scored_items += 1
        job_family = str(job.get("job_family") or "").lower()
        job_domain = str(job.get("domain") or "").lower()
        if job_family in pref_domains or job_domain in pref_domains:
            matched_items += 1

    pref_locations = [l.lower() for l in prefs.get("location_types", [])]
    if pref_locations:
        scored_items += 1
        if (job.get("location_type") or "").lower() in pref_locations:
            matched_items += 1

    if scored_items == 0:
        return 0.5
    return matched_items / scored_items


# ── composite score ───────────────────────────────────────────────────────────

def compute_final_score(
    features: dict[str, float],
    weights: dict[str, float],
    null_defaults: dict[str, float],
) -> float:
    """Compute the weighted composite score, applying missing-value fallbacks.

    Args:
        features: Dictionary of scores (e.g. ai_score, title_relevance, etc.)
        weights: Dictionary of weights summing to 1.0
        null_defaults: Dictionary of fallback values when a feature is missing
    """
    score = 0.0
    for feature_name, weight in weights.items():
        val = features.get(feature_name)
        if val is None:
            val = null_defaults.get(feature_name, 0.0)
        score += val * weight
    return score


# ── sorting and ranking ───────────────────────────────────────────────────────

def rank_jobs(jobs: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    """Sort jobs by final score and assign a final_rank.

    Tie-breaking order:
    1. final_score DESC
    2. ai_score DESC
    3. vector_similarity DESC
    """
    sorted_jobs = sorted(
        jobs,
        key=lambda j: (
            float(j.get("final_score", 0.0)),
            float(j.get("ai_score", 0.0)),
            float(j.get("vector_similarity", 0.0)),
        ),
        reverse=True,
    )

    ranked = sorted_jobs[:top_n]
    for i, job in enumerate(ranked):
        job["final_rank"] = i + 1

    return ranked


# ── integration: store to bigquery ────────────────────────────────────────────

def store_final_ranking(
    ranked_jobs: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert final ranking rows into fitcv.final_ranking.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    if not ranked_jobs:
        return

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.final_ranking"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows = []
    for job in ranked_jobs:
        rows.append({
            "job_url": str(job["job_url"]),
            "final_rank": int(job["final_rank"]),
            "final_score": float(job["final_score"]),
            "ai_score": float(job.get("ai_score", 0.0)),
            "must_have_match": float(job.get("must_have_match", 0.0)),
            "vector_similarity": float(job.get("vector_similarity", 0.0)),
            "title_relevance": float(job.get("title_relevance", 0.5)),
            "seniority_fit": float(job.get("seniority_fit", 0.5)),
            "preference_fit": float(job.get("preference_fit", 0.5)),
            "fit_label": str(job.get("fit_label", "skip")),
            "ranked_at": now,
        })

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for final_ranking: {errors}")
