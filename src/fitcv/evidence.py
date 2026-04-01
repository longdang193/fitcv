"""Evidence retrieval — rank and select candidate evidence items per job.

Public API
----------
normalise_evidence_item  : convert a raw profile entry to the canonical evidence schema
score_evidence_item      : compute a weighted score for one evidence item against JD skills
retrieve_evidence        : score section-aware evidence pools and return top-k ranked items
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
    "experience_entry": 1.1,
    "project_entry": 1.0,
    "project": 1.0,
    "experience_bullet": 0.7,
    "achievement": 0.4,
}

_UUID_NAMESPACE = uuid.NAMESPACE_OID
DEFAULT_EXPERIENCE_ENTRY_TOP_K = 2
DEFAULT_PROJECT_ENTRY_TOP_K = 2
DEFAULT_ACHIEVEMENT_TOP_K = 1
DEFAULT_BULLETS_PER_EXPERIENCE = 2
DEFAULT_HIGHLIGHTS_PER_PROJECT = 2
DEFAULT_STACK_LINES_PER_PROJECT = 2


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


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        sorted(items, key=lambda item: str(item.get("name") or "")),
        key=lambda item: (
            float(item.get("score") or 0.0),
            TYPE_WEIGHTS.get(str(item.get("evidence_type") or "achievement"), 0.4),
        ),
        reverse=True,
    )


def _normalise_experience_entry(
    experience: dict[str, Any],
    *,
    experience_index: int,
    jd_skills: list[str],
    bullets_per_experience: int,
) -> dict[str, Any]:
    role = str(experience.get("role") or "").strip()
    company = str(experience.get("company") or "").strip()
    name = " — ".join(part for part in (role, company) if part)
    source_ref = f"experiences[{experience_index}]"

    bullet_items: list[dict[str, Any]] = []
    for bullet_index, bullet in enumerate(experience.get("bullets") or []):
        if not isinstance(bullet, dict):
            continue
        bullet_item = normalise_evidence_item(
            bullet,
            "experience_bullet",
            f"{source_ref}.bullets[{bullet_index}]",
        )
        bullet_item["score"] = score_evidence_item(bullet_item, jd_skills)
        bullet_items.append(bullet_item)

    sorted_bullets = _sort_items(bullet_items)
    selected_bullets = sorted_bullets[:bullets_per_experience]

    aggregated_skills: list[str] = []
    for item in selected_bullets:
        for skill in item.get("skills") or []:
            skill_text = str(skill).strip()
            if skill_text and skill_text not in aggregated_skills:
                aggregated_skills.append(skill_text)

    evidence_id = str(uuid.uuid5(_UUID_NAMESPACE, f"experience_entry:{source_ref}:{name}"))
    business_value = " ".join(str(item.get("name") or "") for item in selected_bullets)
    return {
        "evidence_id": evidence_id,
        "evidence_type": "experience_entry",
        "name": name,
        "role": role,
        "company": company,
        "location": str(experience.get("location") or "").strip() or None,
        "start": str(experience.get("start") or "").strip() or None,
        "end": str(experience.get("end") or "").strip() or None,
        "skills": aggregated_skills,
        "bullets": [str(item.get("name") or "") for item in selected_bullets if str(item.get("name") or "").strip()],
        "business_value": business_value,
        "score": 0.0,
        "source_ref": source_ref,
    }


def _normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            result.append(text)
    return result


def _build_project_scoring_context(
    *,
    business_value: str,
    tech_stack: list[str],
    highlights: list[str],
) -> str:
    parts: list[str] = []
    if business_value:
        parts.append(business_value)
    parts.extend(tech_stack)
    parts.extend(highlights)
    return " ".join(parts)


def _normalise_project_entry(
    project: dict[str, Any],
    *,
    project_index: int,
) -> dict[str, Any]:
    name = str(project.get("name") or "").strip()
    source_ref = f"projects[{project_index}]"
    business_value = str(project.get("business_value") or "").strip()
    tech_stack = _normalize_text_list(project.get("tech_stack"))
    highlights = _normalize_text_list(project.get("highlights"))
    skills = [str(skill).strip() for skill in project.get("skills") or [] if str(skill).strip()]
    evidence_id = str(uuid.uuid5(_UUID_NAMESPACE, f"project_entry:{source_ref}:{name}"))
    scoring_context = _build_project_scoring_context(
        business_value=business_value,
        tech_stack=tech_stack,
        highlights=highlights,
    )
    return {
        "evidence_id": evidence_id,
        "evidence_type": "project_entry",
        "name": name,
        "duration": str(project.get("duration") or "").strip() or None,
        "url": str(project.get("url") or "").strip() or None,
        "skills": skills,
        "tech_stack": tech_stack,
        "business_value": business_value,
        "highlights": highlights,
        "scoring_context": scoring_context,
        "score": 0.0,
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

    biz_value = str(item.get("scoring_context") or item.get("business_value") or "").lower().split()
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


def _collect_experience_entries(
    profile: dict[str, Any],
    jd_skills: list[str],
    *,
    bullets_per_experience: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for experience_index, experience in enumerate(profile.get("experiences") or []):
        if not isinstance(experience, dict):
            continue
        items.append(
            _normalise_experience_entry(
                experience,
                experience_index=experience_index,
                jd_skills=jd_skills,
                bullets_per_experience=bullets_per_experience,
            )
        )
    return items


def _collect_project_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for project_index, project in enumerate(profile.get("projects") or []):
        if not isinstance(project, dict):
            continue
        items.append(
            _normalise_project_entry(
                project,
                project_index=project_index,
            )
        )
    return items


def _text_overlap_score(text: str, jd_skills: list[str]) -> int:
    lowered_text = text.lower()
    return sum(1 for skill in jd_skills if skill.lower() in lowered_text)


def _select_relevant_texts(values: list[str], jd_skills: list[str], limit: int) -> list[str]:
    if limit <= 0 or not values:
        return []
    ranked = sorted(
        enumerate(values),
        key=lambda pair: (-_text_overlap_score(pair[1], jd_skills), pair[0]),
    )
    selected = [values[index] for index, _ in ranked[:limit]]
    return selected


def _trim_selected_project_entry(item: dict[str, Any], jd_skills: list[str]) -> dict[str, Any]:
    trimmed = dict(item)
    trimmed["tech_stack"] = _select_relevant_texts(
        list(item.get("tech_stack") or []),
        jd_skills,
        DEFAULT_STACK_LINES_PER_PROJECT,
    )
    trimmed["highlights"] = _select_relevant_texts(
        list(item.get("highlights") or []),
        jd_skills,
        DEFAULT_HIGHLIGHTS_PER_PROJECT,
    )
    return trimmed


def _select_budgeted_items(
    *,
    top_k: int,
    jd_skills: list[str],
    experience_items: list[dict[str, Any]],
    project_items: list[dict[str, Any]],
    achievement_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if top_k <= 0:
        return []

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    remaining_slots = top_k

    minimum_experience = 1 if experience_items and remaining_slots > 0 else 0
    minimum_projects = 1 if project_items and remaining_slots > minimum_experience else 0
    reserved_experience = minimum_experience
    remaining_slots -= minimum_experience
    reserved_projects = minimum_projects
    remaining_slots -= minimum_projects

    additional_experience = min(
        max(DEFAULT_EXPERIENCE_ENTRY_TOP_K - reserved_experience, 0),
        len(experience_items) - reserved_experience,
        remaining_slots,
    )
    reserved_experience += max(additional_experience, 0)
    remaining_slots -= max(additional_experience, 0)

    additional_projects = min(
        max(DEFAULT_PROJECT_ENTRY_TOP_K - reserved_projects, 0),
        len(project_items) - reserved_projects,
        remaining_slots,
    )
    reserved_projects += max(additional_projects, 0)
    remaining_slots -= max(additional_projects, 0)

    reserved_achievements = min(DEFAULT_ACHIEVEMENT_TOP_K, len(achievement_items), remaining_slots)
    remaining_slots -= reserved_achievements

    for items, limit in (
        (experience_items, reserved_experience),
        (project_items, reserved_projects),
        (achievement_items, reserved_achievements),
    ):
        for item in items[:limit]:
            selected_item = item
            if str(item.get("evidence_type") or "") == "project_entry":
                selected_item = _trim_selected_project_entry(item, jd_skills)
            selected.append(selected_item)
            selected_ids.add(str(item["evidence_id"]))

    if remaining_slots > 0:
        fallback_pool = _sort_items(
            [
                item
                for item in [*experience_items, *project_items, *achievement_items]
                if str(item["evidence_id"]) not in selected_ids
            ]
        )
        for item in fallback_pool[:remaining_slots]:
            selected_item = item
            if str(item.get("evidence_type") or "") == "project_entry":
                selected_item = _trim_selected_project_entry(item, jd_skills)
            selected.append(selected_item)

    return _sort_items(selected)


def retrieve_evidence(
    profile: dict[str, Any],
    jd_skills: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Normalise section-aware evidence pools and return a bounded ranked selection.

    The first-pass policy preserves grouped experience capacity so multiple relevant
    roles can survive selection when grounded evidence exists.
    """
    experience_items = _collect_experience_entries(
        profile,
        jd_skills,
        bullets_per_experience=DEFAULT_BULLETS_PER_EXPERIENCE,
    )
    project_items = _collect_project_entries(profile)
    achievement_items = [
        normalise_evidence_item(achievement, "achievement", f"achievements[{index}]")
        for index, achievement in enumerate(profile.get("achievements") or [])
    ]

    for item in [*experience_items, *project_items, *achievement_items]:
        item["score"] = score_evidence_item(item, jd_skills)

    return _select_budgeted_items(
        top_k=top_k,
        jd_skills=jd_skills,
        experience_items=_sort_items(experience_items),
        project_items=_sort_items(project_items),
        achievement_items=_sort_items(achievement_items),
    )


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
