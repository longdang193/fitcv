"""Evidence retrieval — rank and select candidate evidence items per job.

Public API
----------
normalise_evidence_item  : convert a raw profile entry to the canonical evidence schema
score_evidence_item      : compute a weighted score for one evidence item against JD skills
retrieve_evidence        : score all evidence types globally, return top-k ranked items
store_evidence_selection : persist selected evidence to BigQuery (integration)
"""

import uuid
from datetime import datetime, timezone
from typing import Any


# ── scoring weights ───────────────────────────────────────────────────────────

SKILL_OVERLAP_WEIGHT: float = 0.60
TYPE_WEIGHT_FACTOR: float = 0.25
BUSINESS_VALUE_WEIGHT: float = 0.15

TYPE_WEIGHTS: dict[str, float] = {
    "project": 1.0,
    "experience_bullet": 0.7,
    "achievement": 0.4,
}

_UUID_NAMESPACE = uuid.NAMESPACE_OID


# ── normalisation ─────────────────────────────────────────────────────────────

def normalise_evidence_item(
    raw: dict[str, Any],
    evidence_type: str,
    source_ref: str,
) -> dict[str, Any]:
    """Convert a raw profile entry into the canonical evidence item schema.

    The ``evidence_id`` is a deterministic UUID5 derived from
    ``evidence_type`` and the item's name, so it is stable across runs.
    """
    name = str(raw.get("name") or raw.get("text") or "")
    skills: list[str] = list(raw.get("skills") or [])
    business_value: str = str(raw.get("business_value") or "")

    evidence_id = str(uuid.uuid5(_UUID_NAMESPACE, f"{evidence_type}:{name}"))

    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "name": name,
        "skills": skills,
        "business_value": business_value,
        "score": 0.0,          # populated by score_evidence_item
        "source_ref": source_ref,
    }


# ── scoring ───────────────────────────────────────────────────────────────────

def score_evidence_item(item: dict[str, Any], jd_skills: list[str]) -> float:
    """Compute a weighted score in [0.0, 1.0] for one normalised evidence item.

    Components:
    - Skill overlap ratio            (weight 0.60)
    - Evidence type weight           (weight 0.25)
    - Business-value keyword overlap (weight 0.15)
    """
    item_skills = [s.lower() for s in item.get("skills") or []]
    jd_lower = [s.lower() for s in jd_skills]

    if jd_lower and item_skills:
        matched = sum(1 for s in item_skills if s in jd_lower)
        skill_ratio = matched / len(jd_lower)
    else:
        skill_ratio = 0.0

    type_score = TYPE_WEIGHTS.get(str(item.get("evidence_type") or "achievement"), 0.4)

    biz_value = str(item.get("business_value") or "").lower().split()
    if jd_lower and biz_value:
        biz_hits = sum(1 for word in biz_value if word in jd_lower)
        biz_ratio = min(biz_hits / len(jd_lower), 1.0)
    else:
        biz_ratio = 0.0

    return (
        SKILL_OVERLAP_WEIGHT * skill_ratio
        + TYPE_WEIGHT_FACTOR * type_score
        + BUSINESS_VALUE_WEIGHT * biz_ratio
    )


# ── retrieval ─────────────────────────────────────────────────────────────────

def _collect_all_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Yield all normalised evidence items from projects, achievements, and experience bullets."""
    items: list[dict[str, Any]] = []

    for idx, proj in enumerate(profile.get("projects") or []):
        items.append(normalise_evidence_item(proj, "project", f"projects[{idx}]"))

    for idx, ach in enumerate(profile.get("achievements") or []):
        items.append(normalise_evidence_item(ach, "achievement", f"achievements[{idx}]"))

    for exp_idx, exp in enumerate(profile.get("experiences") or []):
        for bul_idx, bullet in enumerate(exp.get("bullets") or []):
            items.append(
                normalise_evidence_item(
                    bullet,
                    "experience_bullet",
                    f"experiences[{exp_idx}].bullets[{bul_idx}]",
                )
            )

    return items


def retrieve_evidence(
    profile: dict[str, Any],
    jd_skills: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Normalise all evidence types, score globally, and return the top-k items.

    Tie-breaking order (deterministic):
    1. score DESC
    2. type weight DESC  (project > experience_bullet > achievement)
    3. name ASC          (alphabetical)
    """
    items = _collect_all_items(profile)

    for item in items:
        item["score"] = score_evidence_item(item, jd_skills)

    sorted_items = sorted(
        items,
        key=lambda it: (
            it["score"],
            TYPE_WEIGHTS.get(str(it.get("evidence_type") or "achievement"), 0.4),
            # name ascending → negate with a string reversal trick is not clean;
            # use a separate tuple element and reverse=False for name
        ),
        reverse=True,
    )

    # Secondary stable sort on name ascending to make tie-break fully deterministic.
    # Python sort is stable, so we can sort by name first, then by the score key.
    sorted_items = sorted(
        sorted(items, key=lambda it: str(it.get("name") or "")),
        key=lambda it: (
            it["score"],
            TYPE_WEIGHTS.get(str(it.get("evidence_type") or "achievement"), 0.4),
        ),
        reverse=True,
    )

    return sorted_items[:top_k]


# ── integration: store to bigquery ────────────────────────────────────────────

def store_evidence_selection(
    job_url: str,
    evidence: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert evidence selection rows into fitcv.evidence_selections.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    if not evidence:
        return

    from google.cloud import bigquery  # type: ignore[import-not-found]
    from google.oauth2 import service_account  # type: ignore[import-not-found]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.evidence_selections"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows = [
        {
            "job_url": str(job_url),
            "evidence_id": str(item["evidence_id"]),
            "evidence_type": str(item["evidence_type"]),
            "name": str(item["name"]),
            "skills": list(item.get("skills") or []),
            "business_value": str(item.get("business_value") or ""),
            "score": float(item["score"]),
            "source_ref": str(item["source_ref"]),
            "selected_at": now,
        }
        for item in evidence
    ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for evidence_selections: {errors}")
