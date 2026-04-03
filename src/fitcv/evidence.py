"""Evidence retrieval and final evidence selection for CV analysis.

Public API
----------
normalise_evidence_item  : convert a raw profile entry to the canonical evidence schema
score_evidence_item      : compatibility skill-support score for one evidence item
retrieve_evidence_bundle : retrieve channel pools, merge/dedupe, and select final evidence
retrieve_evidence        : compatibility wrapper that returns final selected evidence only
store_evidence_selection : persist selected evidence to BigQuery (integration)
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fitcv.ranking import _ROLE_FAMILY_NEIGHBORS, _infer_role_family, _normalize_text


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

REQUIRED_SKILL_SUPPORT_CHANNEL = "required_skill_support"
ROLE_ALIGNMENT_CHANNEL = "role_alignment"
DOMAIN_ALIGNMENT_CHANNEL = "domain_alignment"
RESPONSIBILITY_ALIGNMENT_CHANNEL = "responsibility_alignment"
RETRIEVAL_CHANNELS = (
    REQUIRED_SKILL_SUPPORT_CHANNEL,
    ROLE_ALIGNMENT_CHANNEL,
    DOMAIN_ALIGNMENT_CHANNEL,
    RESPONSIBILITY_ALIGNMENT_CHANNEL,
)
DEFAULT_CHANNEL_POOL_SIZE = 4
SELECTION_CHANNEL_WEIGHTS: dict[str, float] = {
    REQUIRED_SKILL_SUPPORT_CHANNEL: 0.40,
    RESPONSIBILITY_ALIGNMENT_CHANNEL: 0.30,
    ROLE_ALIGNMENT_CHANNEL: 0.15,
    DOMAIN_ALIGNMENT_CHANNEL: 0.15,
}
SELECTION_MULTI_CHANNEL_BONUS = 0.05
SELECTION_TYPE_WEIGHT_FACTOR = 0.10
SELECTION_NEW_TYPE_BONUS = 0.03
SELECTION_SAME_TYPE_PENALTY = 0.02
ROLE_ALIGNMENT_NEIGHBOR_SCORE = 0.75

_UUID_NAMESPACE = uuid.NAMESPACE_OID
DEFAULT_EXPERIENCE_ENTRY_TOP_K = 2
DEFAULT_PROJECT_ENTRY_TOP_K = 2
DEFAULT_ACHIEVEMENT_TOP_K = 1
DEFAULT_BULLETS_PER_EXPERIENCE = 2
DEFAULT_HIGHLIGHTS_PER_PROJECT = 2
DEFAULT_STACK_LINES_PER_PROJECT = 2
_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def _normalize_optional_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if not text:
            continue
        if text in seen_values:
            continue
        seen_values.add(text)
        normalized.append(text)
    return normalized


def _canonicalize_terms(values: list[str]) -> list[str]:
    canonical: list[str] = []
    seen_terms: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen_terms:
            continue
        seen_terms.add(normalized)
        canonical.append(normalized)
    return canonical


def _canonicalize_term_set(values: list[str]) -> set[str]:
    return set(_canonicalize_terms(values))


def _build_evidence_id(*parts: str) -> str:
    seed = "|".join(_normalize_optional_text(part) for part in parts)
    return str(uuid.uuid5(_UUID_NAMESPACE, seed))


def _extract_canonical_entities(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    extracted: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        canonical = _normalize_optional_text(value.get("canonical"))
        if canonical:
            extracted.append(canonical)
    return extracted


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()
    return {
        token
        for token in normalized.split()
        if len(token) > 1 and token not in _STOPWORDS
    }


def _overlap_ratio(lhs: set[str], rhs: set[str]) -> float:
    if not lhs or not rhs:
        return 0.0
    return len(lhs & rhs) / len(rhs)


def _context_terms(job_context: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(list(job_context.get("required_skills") or []))
    terms.extend(list(job_context.get("preferred_skills") or []))
    title = _normalize_optional_text(job_context.get("job_title"))
    if title:
        terms.append(title)
    domain = _normalize_optional_text(job_context.get("domain"))
    if domain:
        terms.append(domain)
    job_family = _normalize_optional_text(job_context.get("job_family"))
    if job_family:
        terms.append(job_family)
    terms.extend(list(job_context.get("responsibilities") or []))
    return terms


def _job_context_tokens(job_context: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for value in _context_terms(job_context):
        tokens |= _tokenize(value)
    return tokens


def _coerce_job_context(job_context: dict[str, Any] | list[str]) -> dict[str, Any]:
    if isinstance(job_context, list):
        required_skills = _canonicalize_terms(job_context)
        return {
            "job_url": "",
            "job_title": "",
            "job_family": "",
            "domain": "",
            "required_skills": required_skills,
            "preferred_skills": [],
            "responsibilities": [],
            "context_tokens": set().union(*(_tokenize(skill) for skill in required_skills)) if required_skills else set(),
        }

    required_skills = _canonicalize_terms(
        _extract_canonical_entities(job_context.get("required_skill_entities"))
        or list(job_context.get("required_skills_canonical") or [])
        or list(job_context.get("required_skills") or [])
    )
    preferred_skills = _canonicalize_terms(
        _extract_canonical_entities(job_context.get("preferred_skill_entities"))
        or list(job_context.get("preferred_skills_canonical") or [])
        or list(job_context.get("preferred_skills") or [])
    )
    responsibilities = _normalize_text_list(job_context.get("responsibilities"))
    context: dict[str, Any] = {
        "job_url": _normalize_optional_text(job_context.get("job_url")),
        "job_title": _normalize_optional_text(job_context.get("title") or job_context.get("job_title")),
        "job_family": _normalize_optional_text(job_context.get("job_family")),
        "domain": _normalize_optional_text(job_context.get("domain")),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "responsibilities": responsibilities,
    }
    context["context_tokens"] = _job_context_tokens(context)
    return context


def normalise_evidence_item(
    raw: dict[str, Any],
    evidence_type: str,
    source_ref: str,
) -> dict[str, Any]:
    """Convert a raw profile entry into the canonical evidence item schema."""
    name = _normalize_optional_text(raw.get("name") or raw.get("text"))
    business_value = _normalize_optional_text(raw.get("business_value"))
    skills = _normalize_text_list(raw.get("skills"))
    domain_tags = _canonicalize_terms(_normalize_text_list(raw.get("domain_tags")))
    responsibility_themes = _canonicalize_terms(_normalize_text_list(raw.get("responsibility_themes")))
    role_family = _normalize_text(raw.get("role_family")) or None

    evidence_id = _build_evidence_id(evidence_type, source_ref, name)
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "name": name,
        "skills": skills,
        "business_value": business_value,
        "score": 0.0,
        "source_ref": source_ref,
        "domain_tags": domain_tags,
        "responsibility_themes": responsibility_themes,
        "role_family": role_family,
        "scoring_context": " ".join(part for part in (name, business_value, *domain_tags, *responsibility_themes) if part),
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
) -> dict[str, Any]:
    role = _normalize_optional_text(experience.get("role"))
    company = _normalize_optional_text(experience.get("company"))
    name = " — ".join(part for part in (role, company) if part)
    source_ref = f"experiences[{experience_index}]"

    bullet_texts: list[str] = []
    aggregated_skills: list[str] = []
    seen_skills: set[str] = set()
    for bullet in experience.get("bullets") or []:
        if not isinstance(bullet, dict):
            continue
        text = _normalize_optional_text(bullet.get("text") or bullet.get("name"))
        if text:
            bullet_texts.append(text)
        for skill in _normalize_text_list(bullet.get("skills")):
            if skill not in seen_skills:
                seen_skills.add(skill)
                aggregated_skills.append(skill)

    domain_tags = _canonicalize_terms(_normalize_text_list(experience.get("domain_tags")))
    responsibility_themes = _canonicalize_terms(_normalize_text_list(experience.get("responsibility_themes")))
    role_family = _normalize_text(experience.get("role_family")) or _infer_role_family(role)
    scoring_parts = [role, company, *bullet_texts, *domain_tags, *responsibility_themes]
    return {
        "evidence_id": _build_evidence_id("experience_entry", source_ref, name),
        "evidence_type": "experience_entry",
        "name": name,
        "role": role,
        "company": company,
        "location": _normalize_optional_text(experience.get("location")) or None,
        "start": _normalize_optional_text(experience.get("start")) or None,
        "end": _normalize_optional_text(experience.get("end")) or None,
        "skills": aggregated_skills,
        "bullets": bullet_texts,
        "business_value": " ".join(bullet_texts),
        "score": 0.0,
        "source_ref": source_ref,
        "role_family": role_family,
        "domain_tags": domain_tags,
        "responsibility_themes": responsibility_themes,
        "scoring_context": " ".join(part for part in scoring_parts if part),
    }

def _build_project_scoring_context(
    *,
    name: str,
    business_value: str,
    tech_stack: list[str],
    highlights: list[str],
    domain_tags: list[str],
    responsibility_themes: list[str],
) -> str:
    parts: list[str] = [name]
    if business_value:
        parts.append(business_value)
    parts.extend(tech_stack)
    parts.extend(highlights)
    parts.extend(domain_tags)
    parts.extend(responsibility_themes)
    return " ".join(parts)


def _normalise_project_entry(
    project: dict[str, Any],
    *,
    project_index: int,
) -> dict[str, Any]:
    name = _normalize_optional_text(project.get("name"))
    source_ref = f"projects[{project_index}]"
    business_value = _normalize_optional_text(project.get("business_value"))
    tech_stack = _normalize_text_list(project.get("tech_stack"))
    highlights = _normalize_text_list(project.get("highlights"))
    skills = _normalize_text_list(project.get("skills"))
    domain_tags = _canonicalize_terms(_normalize_text_list(project.get("domain_tags")))
    responsibility_themes = _canonicalize_terms(_normalize_text_list(project.get("responsibility_themes")))
    evidence_id = _build_evidence_id("project_entry", source_ref, name)
    scoring_context = _build_project_scoring_context(
        name=name,
        business_value=business_value,
        tech_stack=tech_stack,
        highlights=highlights,
        domain_tags=domain_tags,
        responsibility_themes=responsibility_themes,
    )
    return {
        "evidence_id": evidence_id,
        "evidence_type": "project_entry",
        "name": name,
        "duration": _normalize_optional_text(project.get("duration")) or None,
        "url": _normalize_optional_text(project.get("url")) or None,
        "skills": skills,
        "tech_stack": tech_stack,
        "business_value": business_value,
        "highlights": highlights,
        "scoring_context": scoring_context,
        "score": 0.0,
        "source_ref": source_ref,
        "role_family": _infer_role_family(name),
        "domain_tags": domain_tags,
        "responsibility_themes": responsibility_themes,
    }


def score_evidence_item(item: dict[str, Any], jd_skills: list[str]) -> float:
    """Compute a weighted score in [0.0, 1.0] for one normalised evidence item."""
    item_skills = _canonicalize_term_set(list(item.get("skills") or []))
    jd_lower = _canonicalize_term_set(jd_skills)

    if jd_lower and item_skills:
        skill_ratio = len(item_skills & jd_lower) / len(jd_lower)
    else:
        skill_ratio = 0.0

    type_score = TYPE_WEIGHTS.get(str(item.get("evidence_type") or "achievement"), 0.4)

    biz_value = _tokenize(str(item.get("scoring_context") or item.get("business_value") or ""))
    if jd_lower and biz_value:
        biz_ratio = min(len(biz_value & jd_lower) / len(jd_lower), 1.0)
    else:
        biz_ratio = 0.0

    return (
        SKILL_OVERLAP_WEIGHT * skill_ratio
        + TYPE_WEIGHT_FACTOR * type_score
        + BUSINESS_VALUE_WEIGHT * biz_ratio
    )


def _collect_experience_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for experience_index, experience in enumerate(profile.get("experiences") or []):
        if not isinstance(experience, dict):
            continue
        items.append(
            _normalise_experience_entry(
                experience,
                experience_index=experience_index,
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


def _collect_achievement_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for achievement_index, achievement in enumerate(profile.get("achievements") or []):
        if not isinstance(achievement, dict):
            continue
        items.append(
            normalise_evidence_item(
                achievement,
                "achievement",
                f"achievements[{achievement_index}]",
            )
        )
    return items


def _text_overlap_score(text: str, reference_terms: list[str]) -> int:
    lowered_text = _normalize_text(text)
    return sum(1 for term in reference_terms if _normalize_text(term) in lowered_text)


def _select_relevant_texts(values: list[str], reference_terms: list[str], limit: int) -> list[str]:
    if limit <= 0 or not values:
        return []
    ranked = sorted(
        enumerate(values),
        key=lambda pair: (-_text_overlap_score(pair[1], reference_terms), pair[0]),
    )
    selected = [values[index] for index, _ in ranked[:limit]]
    return selected


def _trim_selected_project_entry(item: dict[str, Any], reference_terms: list[str]) -> dict[str, Any]:
    trimmed = dict(item)
    trimmed["tech_stack"] = _select_relevant_texts(
        list(item.get("tech_stack") or []),
        reference_terms,
        DEFAULT_STACK_LINES_PER_PROJECT,
    )
    trimmed["highlights"] = _select_relevant_texts(
        list(item.get("highlights") or []),
        reference_terms,
        DEFAULT_HIGHLIGHTS_PER_PROJECT,
    )
    return trimmed


def _trim_selected_experience_entry(item: dict[str, Any], reference_terms: list[str]) -> dict[str, Any]:
    trimmed = dict(item)
    trimmed["bullets"] = _select_relevant_texts(
        list(item.get("bullets") or []),
        reference_terms,
        DEFAULT_BULLETS_PER_EXPERIENCE,
    )
    return trimmed


def _collect_base_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *_collect_experience_entries(profile),
        *_collect_project_entries(profile),
        *_collect_achievement_entries(profile),
    ]


def _select_budgeted_items(
    *,
    top_k: int,
    reference_terms: list[str],
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
                selected_item = _trim_selected_project_entry(item, reference_terms)
            if str(item.get("evidence_type") or "") == "experience_entry":
                selected_item = _trim_selected_experience_entry(item, reference_terms)
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
                selected_item = _trim_selected_project_entry(item, reference_terms)
            if str(item.get("evidence_type") or "") == "experience_entry":
                selected_item = _trim_selected_experience_entry(item, reference_terms)
            selected.append(selected_item)

    return _sort_items(selected)


def _retrieve_evidence_legacy(
    profile: dict[str, Any],
    jd_skills: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    experience_items = _collect_experience_entries(profile)
    project_items = _collect_project_entries(profile)
    achievement_items = _collect_achievement_entries(profile)

    for item in [*experience_items, *project_items, *achievement_items]:
        item["score"] = score_evidence_item(item, jd_skills)

    return _select_budgeted_items(
        top_k=top_k,
        reference_terms=jd_skills,
        experience_items=_sort_items(experience_items),
        project_items=_sort_items(project_items),
        achievement_items=_sort_items(achievement_items),
    )


def _item_role_family(item: dict[str, Any]) -> str | None:
    explicit_family = _normalize_text(item.get("role_family"))
    if explicit_family:
        return explicit_family
    role_text = _normalize_optional_text(item.get("role") or item.get("name"))
    inferred_family = _infer_role_family(role_text)
    return inferred_family


def _score_required_skill_support(item: dict[str, Any], job_context: dict[str, Any]) -> float:
    required_skills = _canonicalize_term_set(list(job_context.get("required_skills") or []))
    if not required_skills:
        return 0.0
    item_skills = _canonicalize_term_set(list(item.get("skills") or []))
    context_tokens = _tokenize(str(item.get("scoring_context") or ""))
    return max(
        _overlap_ratio(item_skills, required_skills),
        _overlap_ratio(context_tokens, required_skills),
    )


def _score_role_alignment(item: dict[str, Any], job_context: dict[str, Any]) -> float:
    job_title = _normalize_optional_text(job_context.get("job_title"))
    job_family = _normalize_text(job_context.get("job_family")) or _infer_role_family(job_title)
    item_family = _item_role_family(item)

    family_score = 0.0
    if job_family and item_family:
        if job_family == item_family:
            family_score = 1.0
        elif item_family in _ROLE_FAMILY_NEIGHBORS.get(job_family, frozenset()):
            family_score = ROLE_ALIGNMENT_NEIGHBOR_SCORE

    lexical_score = _overlap_ratio(
        _tokenize(_normalize_optional_text(item.get("role") or item.get("name"))),
        _tokenize(job_title),
    )
    return max(family_score, lexical_score)


def _score_domain_alignment(item: dict[str, Any], job_context: dict[str, Any]) -> float:
    domain_terms = _canonicalize_term_set(
        [
            _normalize_optional_text(job_context.get("domain")),
            _normalize_optional_text(job_context.get("job_family")),
        ]
    )
    if not domain_terms:
        return 0.0
    item_domain_tags = _canonicalize_term_set(list(item.get("domain_tags") or []))
    if item_domain_tags:
        return max(
            _overlap_ratio(item_domain_tags, domain_terms),
            _overlap_ratio(domain_terms, item_domain_tags),
        )
    return _overlap_ratio(_tokenize(str(item.get("scoring_context") or "")), domain_terms)


def _score_responsibility_alignment(item: dict[str, Any], job_context: dict[str, Any]) -> float:
    responsibilities = list(job_context.get("responsibilities") or [])
    if not responsibilities:
        return 0.0
    responsibility_tokens = set().union(*(_tokenize(text) for text in responsibilities))
    if not responsibility_tokens:
        return 0.0
    theme_tokens = set().union(*(_tokenize(theme) for theme in item.get("responsibility_themes") or []))
    context_tokens = _tokenize(str(item.get("scoring_context") or ""))
    return max(
        _overlap_ratio(theme_tokens, responsibility_tokens),
        _overlap_ratio(context_tokens, responsibility_tokens),
    )


def _channel_score(item: dict[str, Any], channel: str, job_context: dict[str, Any]) -> float:
    if channel == REQUIRED_SKILL_SUPPORT_CHANNEL:
        return _score_required_skill_support(item, job_context)
    if channel == ROLE_ALIGNMENT_CHANNEL:
        return _score_role_alignment(item, job_context)
    if channel == DOMAIN_ALIGNMENT_CHANNEL:
        return _score_domain_alignment(item, job_context)
    if channel == RESPONSIBILITY_ALIGNMENT_CHANNEL:
        return _score_responsibility_alignment(item, job_context)
    return 0.0


def _channel_rationale(channel: str, item: dict[str, Any], job_context: dict[str, Any]) -> list[str]:
    if channel == REQUIRED_SKILL_SUPPORT_CHANNEL:
        required_skills = _canonicalize_term_set(list(job_context.get("required_skills") or []))
        item_skills = _canonicalize_term_set(list(item.get("skills") or []))
        matched = sorted(required_skills & item_skills)
        return matched[:3]
    if channel == ROLE_ALIGNMENT_CHANNEL:
        item_family = _item_role_family(item)
        job_family = _normalize_text(job_context.get("job_family"))
        reasons: list[str] = []
        if item_family and job_family and item_family == job_family:
            reasons.append(f"role_family:{job_family}")
        role_name = _normalize_optional_text(item.get("role") or item.get("name"))
        if role_name:
            reasons.append(role_name)
        return reasons[:3]
    if channel == DOMAIN_ALIGNMENT_CHANNEL:
        matched_domains = sorted(
            _canonicalize_term_set(list(item.get("domain_tags") or []))
            & _canonicalize_term_set(
                [
                    _normalize_optional_text(job_context.get("domain")),
                    _normalize_optional_text(job_context.get("job_family")),
                ]
            )
        )
        return matched_domains[:3]
    if channel == RESPONSIBILITY_ALIGNMENT_CHANNEL:
        themes = [str(theme) for theme in list(item.get("responsibility_themes") or []) if theme]
        if themes:
            return themes[:3]
        return _select_relevant_texts(
            list(item.get("bullets") or item.get("highlights") or []),
            list(job_context.get("responsibilities") or []),
            1,
        )
    return []


def _select_channel_candidates(
    *,
    items: list[dict[str, Any]],
    channel: str,
    job_context: dict[str, Any],
    pool_size: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in items:
        channel_score = _channel_score(item, channel, job_context)
        if channel_score <= 0.0:
            continue
        candidates.append(
            {
                **item,
                "channel": channel,
                "channel_score": channel_score,
                "channel_rationale": _channel_rationale(channel, item, job_context),
            }
        )
    return sorted(
        candidates,
        key=lambda item: (
            float(item.get("channel_score") or 0.0),
            TYPE_WEIGHTS.get(str(item.get("evidence_type") or ""), 0.0),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )[:pool_size]


def _merge_channel_pools(channel_pools: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}
    for channel, pool in channel_pools.items():
        for item in pool:
            evidence_id = str(item.get("evidence_id") or "")
            if not evidence_id:
                continue
            existing = merged_by_id.get(evidence_id)
            if existing is None:
                merged_by_id[evidence_id] = {
                    key: value
                    for key, value in item.items()
                    if key not in {"channel", "channel_score", "channel_rationale"}
                }
                existing = merged_by_id[evidence_id]
                existing["matched_channels"] = []
                existing["channel_scores"] = {}
                existing["channel_rationales"] = {}
            matched_channels = list(existing.get("matched_channels") or [])
            if channel not in matched_channels:
                matched_channels.append(channel)
            existing["matched_channels"] = matched_channels
            channel_scores = dict(existing.get("channel_scores") or {})
            channel_scores[channel] = float(item.get("channel_score") or 0.0)
            existing["channel_scores"] = channel_scores
            channel_rationales = dict(existing.get("channel_rationales") or {})
            channel_rationales[channel] = list(item.get("channel_rationale") or [])
            existing["channel_rationales"] = channel_rationales
    return sorted(
        merged_by_id.values(),
        key=lambda item: (
            sum(float(score) for score in dict(item.get("channel_scores") or {}).values()),
            len(list(item.get("matched_channels") or [])),
            TYPE_WEIGHTS.get(str(item.get("evidence_type") or ""), 0.0),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )


def _base_selection_score(item: dict[str, Any]) -> float:
    channel_scores = dict(item.get("channel_scores") or {})
    weighted_score = sum(
        float(channel_scores.get(channel) or 0.0) * SELECTION_CHANNEL_WEIGHTS[channel]
        for channel in RETRIEVAL_CHANNELS
    )
    matched_channels = list(item.get("matched_channels") or [])
    multi_channel_bonus = max(len(matched_channels) - 1, 0) * SELECTION_MULTI_CHANNEL_BONUS
    type_bonus = TYPE_WEIGHTS.get(str(item.get("evidence_type") or ""), 0.0) * SELECTION_TYPE_WEIGHT_FACTOR
    return weighted_score + multi_channel_bonus + type_bonus


def _selection_reasons(item: dict[str, Any]) -> list[str]:
    channel_scores = dict(item.get("channel_scores") or {})
    ordered_channels = sorted(
        list(item.get("matched_channels") or []),
        key=lambda channel: (-float(channel_scores.get(channel) or 0.0), channel),
    )
    return ordered_channels[:3]


def _reference_terms(job_context: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(list(job_context.get("required_skills") or []))
    terms.extend(list(job_context.get("preferred_skills") or []))
    terms.extend(list(job_context.get("responsibilities") or []))
    title = _normalize_optional_text(job_context.get("job_title"))
    if title:
        terms.append(title)
    domain = _normalize_optional_text(job_context.get("domain"))
    if domain:
        terms.append(domain)
    job_family = _normalize_optional_text(job_context.get("job_family"))
    if job_family:
        terms.append(job_family)
    return terms


def _finalize_selected_item(item: dict[str, Any], job_context: dict[str, Any]) -> dict[str, Any]:
    reference_terms = _reference_terms(job_context)
    finalized = dict(item)
    if str(item.get("evidence_type") or "") == "project_entry":
        finalized = _trim_selected_project_entry(finalized, reference_terms)
    if str(item.get("evidence_type") or "") == "experience_entry":
        finalized = _trim_selected_experience_entry(finalized, reference_terms)
    return finalized


def _select_final_evidence(
    merged_pool: list[dict[str, Any]],
    *,
    top_k: int,
    job_context: dict[str, Any],
) -> list[dict[str, Any]]:
    if top_k <= 0:
        return []

    selected: list[dict[str, Any]] = []
    selected_types: list[str] = []
    remaining = list(merged_pool)
    while remaining and len(selected) < top_k:
        best_index = -1
        best_score = -1.0
        for index, item in enumerate(remaining):
            evidence_type = str(item.get("evidence_type") or "")
            dynamic_score = _base_selection_score(item)
            if evidence_type and evidence_type not in selected_types:
                dynamic_score += SELECTION_NEW_TYPE_BONUS
            dynamic_score -= selected_types.count(evidence_type) * SELECTION_SAME_TYPE_PENALTY
            if dynamic_score > best_score:
                best_score = dynamic_score
                best_index = index
        if best_index < 0:
            break
        chosen = dict(remaining.pop(best_index))
        evidence_type = str(chosen.get("evidence_type") or "")
        selected_types.append(evidence_type)
        chosen["selection_score"] = round(best_score, 6)
        chosen["selection_reasons"] = _selection_reasons(chosen)
        selected.append(_finalize_selected_item(chosen, job_context))
    return selected


def retrieve_evidence_bundle(
    profile: dict[str, Any],
    job_context: dict[str, Any] | list[str],
    top_k: int,
) -> dict[str, Any]:
    """Retrieve evidence via separate channels, then merge/dedupe/select."""
    coerced_job_context = _coerce_job_context(job_context)
    base_items = _collect_base_items(profile)
    channel_pools = {
        channel: _select_channel_candidates(
            items=base_items,
            channel=channel,
            job_context=coerced_job_context,
            pool_size=DEFAULT_CHANNEL_POOL_SIZE,
        )
        for channel in RETRIEVAL_CHANNELS
    }
    merged_pool = _merge_channel_pools(channel_pools)
    selected_evidence = _select_final_evidence(
        merged_pool,
        top_k=top_k,
        job_context=coerced_job_context,
    )
    return {
        "selected_evidence": selected_evidence,
        "selected_evidence_ids": [str(item.get("evidence_id") or "") for item in selected_evidence],
        "channel_counts": {
            channel: len(channel_pools.get(channel, []))
            for channel in RETRIEVAL_CHANNELS
        },
        "merged_pool_size": sum(len(pool) for pool in channel_pools.values()),
        "deduped_pool_size": len(merged_pool),
    }


def retrieve_evidence(
    profile: dict[str, Any],
    job_context: dict[str, Any] | list[str] | None = None,
    top_k: int = 0,
    *,
    jd_skills: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Compatibility wrapper that returns the selected evidence list only."""
    if jd_skills is not None or isinstance(job_context, list) or job_context is None:
        resolved_skills = list(jd_skills or job_context or [])
        return _retrieve_evidence_legacy(profile, resolved_skills, top_k)

    resolved_context: dict[str, Any] | list[str]
    resolved_context = job_context
    return list(retrieve_evidence_bundle(profile, resolved_context, top_k).get("selected_evidence") or [])


def store_evidence_selection(
    job_url: str,
    evidence: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert evidence selection rows into fitcv.evidence_selections."""
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
            "score": float(item.get("selection_score") or item.get("score") or 0.0),
            "source_ref": str(item["source_ref"]),
            "selected_at": now,
        }
        for item in evidence
    ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for evidence_selections: {errors}")
