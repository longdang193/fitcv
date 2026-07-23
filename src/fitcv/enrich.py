"""@meta
name: enrich
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.location-language-eligibility
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.enrich.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import json
import hashlib
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from pydantic import BaseModel as _BaseModel, Field as _Field, ValidationError as _ValidationError
from fitcv.config import (
    get_enrich_extraction_model,
    get_prompt_replacement,
    get_prompt_replacement_metadata,
    get_stage_runtime_concurrency,
    get_system_initial_backoff_seconds,
    get_system_maximum_attempts,
    load_prompt_task_registry,
    sqlite_mode_enabled,
)
from fitcv.fit_factors import (
    ACTUAL_LOCATION_EXTRACTION_VERSION,
    LANGUAGE_REQUIREMENT_EXTRACTION_VERSION,
    comparison_key,
    normalize_display_text,
)
from fitcv.candidate import infer_role_family
from fitcv.llm_runtime import (
    LlmAdapter,
    LlmAdapterResponse,
    LlmRuntimeFailure,
    LlmRuntimeResult,
    LlmTaskRequest,
    LlmValidationResult,
    execute_llm_task,
    project_llm_runtime_evidence,
)
from fitcv.runtime_routing import resolve_llm_routing
from fitcv.pipeline_stages.common import extract_job_url
from fitcv.prompts import get_prompt_definition, render_prompt
from fitcv.semantic_snapshot import (
    build_semantic_snapshot,
    compile_semantic_policy,
    project_canonical,
)

logger = logging.getLogger(__name__)

_SQLITE_STRUCTURED_JOBS_TABLE = "structured_jobs_cache"
_VERBOSE_REQUIRED_SKILL_MAX_LEN = 80

# ── enum definitions (fallbacks — overridden by taxonomy.yaml via config) ──────

_FALLBACK_LOCATION_TYPES: frozenset[str] = frozenset({"remote", "hybrid", "onsite"})
_FALLBACK_SENIORITY_ENRICH: frozenset[str] = frozenset({"junior", "mid", "senior", "lead"})

@dataclass(frozen=True)
class NormalizationPolicy:
    valid_location_types: frozenset[str]
    valid_seniority_enrich: frozenset[str]
    skill_synonyms: dict[str, str]
    domain_alias_map: dict[str, str]
    role_family_alias_map: dict[str, str]
    role_taxonomy: dict[str, Any]

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

def _build_normalization_policy(config: dict | None) -> NormalizationPolicy:
    cfg = config or {}
    semantic_policy = cfg.get("semantic_policy")
    if not isinstance(semantic_policy, dict):
        semantic_policy = compile_semantic_policy(cfg)
    maps = semantic_policy.get("maps")
    semantic_maps = maps if isinstance(maps, dict) else {}
    skill_synonyms = semantic_maps.get("skill")
    domain_alias_map = semantic_maps.get("domain")
    role_family_alias_map = semantic_maps.get("role_family")
    role_taxonomy = cfg.get("role_taxonomy")
    return NormalizationPolicy(
        valid_location_types=_get_valid_location_types(cfg),
        valid_seniority_enrich=_get_valid_seniority_enrich(cfg),
        skill_synonyms=dict(skill_synonyms) if isinstance(skill_synonyms, dict) else {},
        domain_alias_map=dict(domain_alias_map) if isinstance(domain_alias_map, dict) else {},
        role_family_alias_map=(
            dict(role_family_alias_map) if isinstance(role_family_alias_map, dict) else {}
        ),
        role_taxonomy=role_taxonomy if isinstance(role_taxonomy, dict) else {},
    )

# ── schema: which fields are arrays vs scalars ─────────────────────────────────

_ARRAY_FIELDS: frozenset[str] = frozenset({
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "tech_stack",
    "keywords",
})
_CANONICAL_SKILL_FIELDS: frozenset[str] = frozenset({
    "required_skills",
    "preferred_skills",
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
_LANGUAGE_CANONICALS: frozenset[str] = frozenset({
    "english",
    "german",
    "french",
    "spanish",
    "italian",
    "dutch",
    "portuguese",
    "polish",
})
_NON_SKILL_CANONICAL_EXACT: frozenset[str] = frozenset({
    "analytical thinking",
    "analytical skills",
    "attention to detail",
    "proactiveness",
    "solution-oriented approach",
    "communication skills",
    "ownership",
    "data presentation",
    "actionable insights",
    "business model analysis",
    "value chain analysis",
    "technical systems understanding",
    "complex operations management",
    "performance driver analysis",
    "telecommunications domain knowledge",
    "mvne domain knowledge",
    "mvno domain knowledge",
    "sme financing",
    "data handling",
    "business case development",
    "benchmarking",
    "strategic analysis",
    "end-to-end project management",
})
_NON_SKILL_PHRASE_MARKERS: tuple[str, ...] = (
    "domain experience",
    "domain knowledge",
    "language",
    "communication",
    "attention to detail",
    "ownership",
    "proactive",
    "solution-oriented",
    "analytical focus",
    "analytical ability",
    "analytical skills",
    "problem-solving",
    "business model",
    "value chain",
    "performance driver",
    "technical systems",
    "complex operations",
    "actionable recommendation",
    "actionable insight",
    "present complex insights",
    "data presentation",
    "high degree of ownership",
    "soft skill",
)


class SkillEntity(TypedDict):
    raw_text: str
    canonical: str
    confidence: float


class SkillEntityOutput(_BaseModel):
    raw_text: str
    canonical: str
    confidence: float | None = None


class MappingSuggestion(TypedDict):
    must_have_skill: str
    matches: bool
    alias: str
    canonical: str
    confidence: float

class FieldMappingSuggestion(TypedDict):
    field: str
    alias: str
    canonical: str
    confidence: float
    matches: bool


class RawJobFingerprintPayload(TypedDict):
    fingerprint_version: str
    job_url: str
    title: str | None
    company_name: str | None
    location: str | None
    description_cleaned: str | None
    contract_type: str | None
    experience_level: str | None
    source: str | None
    source_location: dict[str, str | None] | None


class RawJobFingerprintResult(TypedDict):
    payload: RawJobFingerprintPayload
    fingerprint: str


class EnrichContractFingerprintPayload(TypedDict):
    contract_version: str
    prompt_id: str
    prompt_version: str
    template_path: str
    model: str
    response_schema_version: str
    skill_postprocessing_version: str
    actual_location_extraction_version: str
    language_requirement_extraction_version: str


class EnrichContractFingerprintResult(TypedDict):
    payload: EnrichContractFingerprintPayload
    fingerprint: str


RAW_JOB_FINGERPRINT_VERSION = "raw_job_fingerprint_v2"
ENRICH_RESPONSE_SCHEMA_VERSION = "enrichment_output_v2"
ENRICH_SKILL_POSTPROCESSING_VERSION = "canonical_skill_entities_v1"
ENRICH_CONTRACT_VERSION = "enrich_contract_v2"
FRESH_ENRICHMENT_STATUS = "fresh_enrichment"
REUSED_CACHED_ENRICHMENT_STATUS = "reused_cached_enrichment"
_SPARSE_REQUIRED_SKILLS_THRESHOLD = 3

# ── Markdown fence stripper ───────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_MISSING_STRING_COMMA_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s+"([^"\\]*(?:\\.[^"\\]*)*)"')
_DESCRIPTION_SEGMENT_SPLIT_RE = re.compile(r"(?:\r?\n+|[•●▪◦·]+)")
_DESCRIPTION_LIST_SPLIT_RE = re.compile(r"\s*(?:,|;|\bund\b|\band\b|\boder\b|\bor\b)\s*", re.IGNORECASE)
_DESCRIPTION_REQUIREMENT_MARKERS: tuple[str, ...] = (
    "experience",
    "erfahrung",
    "kenntnis",
    "knowledge",
    "required",
    "must have",
    "you have",
    "du hast",
    "ideal",
    "idealerweise",
)
_DESCRIPTION_REQUIREMENT_PREFIX_RE = re.compile(
    r"^(?:"
    r"\d+\+?\s*(?:years?|jahre)\s+(?:of\s+)?(?:experience|erfahrung)\s+(?:in|with|im|ins|in der|in dem)?\s*|"
    r"(?:experience|erfahrung|kenntnisse?|knowledge)\s+(?:in|with|mit|im|ins|in der|in dem)?\s*"
    r")",
    re.IGNORECASE,
)
_DESCRIPTION_TRAILING_CONTEXT_RE = re.compile(
    r"\s*(?:-|–|—)\s*(?:ideally|ideal|idealerweise|preferred)\b.*$",
    re.IGNORECASE,
)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences if present."""
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def _repair_common_json_issues(text: str) -> str:
    """Repair a small set of common model JSON mistakes before giving up."""
    repaired = text
    while True:
        updated = _MISSING_STRING_COMMA_RE.sub(r'"\1", "\2"', repaired)
        if updated == repaired:
            return repaired
        repaired = updated


# ── field coercion ────────────────────────────────────────────────────────────

def _normalize_enum(value: Any, valid: frozenset[str]) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.lower().strip()
    return lowered if lowered in valid else None


def _normalize_text_item(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get_skill_synonyms(config: dict | None) -> dict[str, str]:
    return _build_normalization_policy(config).skill_synonyms


def _canonicalize_text_item(field_name: str, raw_text: str, config: dict | None) -> str:
    normalized = raw_text.strip().lower()
    if field_name in _CANONICAL_SKILL_FIELDS:
        return _get_skill_synonyms(config).get(normalized, normalized)
    return normalized


def _normalize_array_values(values: list[Any] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        text = _normalize_text_item(value)
        if text is not None:
            normalized.append(text)
    return normalized


def _build_canonical_list(raw_values: list[str], field_name: str, config: dict | None) -> list[str]:
    return [_canonicalize_text_item(field_name, raw_value, config) for raw_value in raw_values]


def _dedupe_text_values(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


def _dedupe_canonical_values(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _normalise_confidence(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return numeric
    return None


def _canonical_from_entities(entities: list[SkillEntity]) -> list[str]:
    seen: set[str] = set()
    canonical_values: list[str] = []
    for entity in entities:
        canonical = str(entity.get("canonical") or "").strip().lower()
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        canonical_values.append(canonical)
    return canonical_values


def _is_generic_ai_concept_overreach(raw_text: str, canonical: str) -> bool:
    raw_lower = raw_text.strip().lower()
    canonical_lower = canonical.strip().lower()
    if canonical_lower not in {"genai", "generative ai"}:
        return False
    return "genai" not in raw_lower and "generative ai" not in raw_lower


def _is_allowed_skill_entity(raw_text: str, canonical: str) -> bool:
    raw_lower = raw_text.strip().lower()
    canonical_lower = canonical.strip().lower()
    if not raw_lower or not canonical_lower:
        return False
    if canonical_lower in _LANGUAGE_CANONICALS:
        return False
    if canonical_lower in _NON_SKILL_CANONICAL_EXACT:
        return False
    if any(marker in raw_lower or marker in canonical_lower for marker in _NON_SKILL_PHRASE_MARKERS):
        return False
    if _is_generic_ai_concept_overreach(raw_text, canonical):
        return False
    return True


def _is_reusable_skill_alias(raw_text: str, canonical: str) -> bool:
    normalized_alias = raw_text.strip().lower()
    normalized_canonical = canonical.strip().lower()
    if not normalized_alias or not normalized_canonical or normalized_alias == normalized_canonical:
        return False
    if len(normalized_alias) > 40:
        return False
    if len(normalized_alias.split()) > 4:
        return False
    if any(char in normalized_alias for char in ",;:()[]{}"):
        return False
    return True


def _normalise_skill_entities(
    raw_entities: list[Any] | None,
    *,
    config: dict | None,
) -> list[SkillEntity]:
    entities: list[SkillEntity] = []
    for raw_entity in raw_entities or []:
        if not isinstance(raw_entity, dict):
            continue
        raw_text = _normalize_text_item(raw_entity.get("raw_text"))
        canonical_raw = _normalize_text_item(raw_entity.get("canonical"))
        if raw_text is None or canonical_raw is None:
            continue
        canonical = _get_skill_synonyms(config).get(canonical_raw.strip().lower(), canonical_raw.strip().lower())
        if not _is_allowed_skill_entity(raw_text, canonical):
            continue
        confidence = _normalise_confidence(raw_entity.get("confidence"))
        entities.append(
            {
                "raw_text": raw_text,
                "canonical": canonical,
                "confidence": confidence if confidence is not None else 1.0,
            }
        )
    return entities


def _build_skill_entities(
    raw_values: list[str],
    field_name: str,
    config: dict | None,
    *,
    raw_entities: list[Any] | None = None,
) -> list[SkillEntity]:
    if field_name not in {"required_skills", "preferred_skills"}:
        return []
    normalized_entities = _normalise_skill_entities(raw_entities, config=config)
    if normalized_entities:
        return normalized_entities
    fallback_entities: list[SkillEntity] = []
    for raw_value in raw_values:
        normalized_alias = raw_value.strip().lower()
        canonical = _canonicalize_text_item(field_name, raw_value, config)
        if not _is_reusable_skill_alias(raw_value, canonical):
            continue
        if not _is_allowed_skill_entity(raw_value, canonical):
            continue
        fallback_entities.append(
            {
                "raw_text": raw_value,
                "canonical": canonical,
                "confidence": 1.0,
            }
        )
    return fallback_entities


def _build_mapping_suggestions(
    *,
    entities: list[SkillEntity],
) -> list[MappingSuggestion]:
    suggestions: list[MappingSuggestion] = []
    seen_pairs: set[tuple[str, str]] = set()
    for entity in entities:
        raw_value = str(entity.get("raw_text") or "")
        canonical = str(entity.get("canonical") or "").strip().lower()
        normalized_alias = raw_value.strip().lower()
        if not _is_reusable_skill_alias(raw_value, canonical):
            continue
        pair = (normalized_alias, canonical)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        suggestions.append(
            {
                "must_have_skill": canonical,
                "matches": True,
                "alias": normalized_alias,
                "canonical": canonical,
                "confidence": float(entity.get("confidence") or 1.0),
            }
        )
    return suggestions

def _build_field_mapping_suggestions(
    *,
    field: str,
    alias_raw: str | None,
    canonical_raw: str | None,
    config: dict | None = None,
) -> list[FieldMappingSuggestion]:
    alias = str(alias_raw or "").strip().lower()
    canonical = str(canonical_raw or "").strip().lower()
    map_key = "domain_alias_map" if field == "domain" else "role_family_alias_map"
    alias_map = (config or {}).get(map_key)
    if isinstance(alias_map, dict):
        canonical = str(alias_map.get(alias) or canonical).strip().lower()
    if field == "role_family":
        role_taxonomy = (config or {}).get("role_taxonomy") or {}
        known_families: set[str] = set()
        if isinstance(role_taxonomy, dict):
            for family in list((role_taxonomy.get("role_family_neighbors") or {}).keys()):
                normalized = str(family).strip().lower()
                if normalized:
                    known_families.add(normalized)
        if alias and known_families and canonical == alias:
            underscore_candidate = re.sub(r"\s+", "_", alias)
            if underscore_candidate in known_families:
                canonical = underscore_candidate
        if alias == canonical and "_" in alias:
            alias = alias.replace("_", " ")
    if not alias or not canonical or alias == canonical:
        return []
    return [
        {
            "field": field,
            "alias": alias,
            "canonical": canonical,
            "confidence": 1.0,
            "matches": True,
        }
    ]


def _build_array_companions(
    *,
    field_name: str,
    raw_values: list[str],
    config: dict | None,
    raw_entities: list[Any] | None = None,
) -> dict[str, Any]:
    companions: dict[str, Any] = {field_name: raw_values}
    if field_name in _CANONICAL_SKILL_FIELDS:
        skill_entities = _build_skill_entities(
            raw_values,
            field_name,
            config,
            raw_entities=raw_entities,
        )
        companions[f"{field_name}_canonical"] = _canonical_from_entities(skill_entities)
        singular_prefix = "required_skill" if field_name == "required_skills" else "preferred_skill"
        companions[f"{singular_prefix}_entities"] = skill_entities
    return companions


class RequiredSkillsDisplay(TypedDict):
    values: list[str]
    source: str | None


def _parse_required_skill_entities_payload(row: dict[str, Any]) -> list[dict[str, Any]]:
    entities = row.get("required_skill_entities")
    if isinstance(entities, list):
        return [entity for entity in entities if isinstance(entity, dict)]
    raw_json = row.get("required_skill_entities_json")
    if not isinstance(raw_json, str) or not raw_json.strip():
        return []
    try:
        payload = json.loads(raw_json)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    return [entity for entity in payload if isinstance(entity, dict)]


def _is_concise_required_skill_value(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate:
        return False
    if len(candidate) > _VERBOSE_REQUIRED_SKILL_MAX_LEN:
        return False
    if ". " in candidate or ":" in candidate or ";" in candidate:
        return False
    if candidate.count(",") >= 2:
        return False
    if "(" in candidate and ")" in candidate and len(candidate) > 60:
        return False
    return True


def _display_values_from_required_skill_entities(row: dict[str, Any]) -> list[str]:
    display_values: list[str] = []
    seen: set[str] = set()
    for entity in _parse_required_skill_entities_payload(row):
        raw_text = str(entity.get("raw_text") or "").strip()
        canonical = str(entity.get("canonical") or "").strip()
        preferred = raw_text if _is_concise_required_skill_value(raw_text) else canonical
        fallback = canonical if preferred == raw_text else raw_text
        for candidate in (preferred, fallback):
            normalized = candidate.strip().lower()
            if not candidate or not normalized or normalized in seen:
                continue
            seen.add(normalized)
            display_values.append(candidate)
            break
    return display_values


def derive_required_skills_display(row: dict[str, Any]) -> RequiredSkillsDisplay:
    required_skills = _normalize_array_values(
        row.get("required_skills") if isinstance(row.get("required_skills"), list) else []
    )
    entity_values = _display_values_from_required_skill_entities(row)
    if required_skills and all(_is_concise_required_skill_value(value) for value in required_skills):
        return {"values": required_skills, "source": "required_skills"}
    if entity_values:
        return {"values": entity_values, "source": "required_skill_entities"}
    if required_skills:
        return {"values": required_skills, "source": "required_skills"}
    tech_stack = _normalize_array_values(row.get("tech_stack") if isinstance(row.get("tech_stack"), list) else [])
    if tech_stack:
        return {"values": tech_stack, "source": "tech_stack"}
    keywords = _normalize_array_values(row.get("keywords") if isinstance(row.get("keywords"), list) else [])
    if keywords:
        return {"values": keywords, "source": "keywords"}
    return {"values": [], "source": None}


def _required_skill_fallback_values(
    row: dict[str, Any],
    config: dict | None,
    *,
    source_fields: tuple[str, ...] = ("tech_stack", "keywords"),
) -> list[str]:
    fallback_values: list[str] = []
    for field_name in source_fields:
        raw_values = row.get(field_name)
        if not isinstance(raw_values, list):
            continue
        for raw_value in _normalize_array_values(raw_values):
            canonical = _canonicalize_text_item("required_skills", raw_value, config)
            if not _is_allowed_skill_entity(raw_value, canonical):
                continue
            fallback_values.append(raw_value)
    return _dedupe_text_values(fallback_values)


def _is_requirement_like_description_segment(segment: str) -> bool:
    lowered = segment.strip().lower()
    if not lowered:
        return False
    if any(marker in lowered for marker in _DESCRIPTION_REQUIREMENT_MARKERS):
        return True
    return bool(
        re.match(
            r"^\d+\+?\s*(?:years?|jahre)\s+(?:of\s+)?(?:experience|erfahrung)\b",
            lowered,
        )
    )


def _clean_description_skill_candidate(raw_value: str) -> str:
    cleaned = raw_value.strip()
    cleaned = _DESCRIPTION_REQUIREMENT_PREFIX_RE.sub("", cleaned)
    cleaned = _DESCRIPTION_TRAILING_CONTEXT_RE.sub("", cleaned)
    return cleaned.strip(" -–—:;,.()[]{}")


def _looks_like_description_skill_candidate(candidate: str) -> bool:
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9+#./&-]+", candidate)
    if not words or len(words) > 4:
        return False
    lowered = candidate.lower()
    if any(
        marker in lowered
        for marker in (
            "arbeitsweise",
            "priorit",
            "stakeholder",
            "coordinat",
            "set ",
            "setzen",
            "support",
        )
    ):
        return False
    if len(words) == 1:
        token = words[0]
        return bool(re.search(r"[A-Z0-9+#/&-]", token))
    return candidate[0].isupper()


def _required_skill_candidates_from_description(
    row: dict[str, Any],
    config: dict | None,
) -> list[str]:
    description = _normalize_text_item(row.get("description_cleaned") or row.get("description"))
    if description is None:
        return []

    candidates: list[str] = []
    for raw_segment in _DESCRIPTION_SEGMENT_SPLIT_RE.split(description):
        segment = raw_segment.strip()
        if not _is_requirement_like_description_segment(segment):
            continue
        segment_body = segment.split(":", 1)[-1].strip()
        segment_candidates: list[str] = []
        for raw_part in _DESCRIPTION_LIST_SPLIT_RE.split(segment_body):
            cleaned = _clean_description_skill_candidate(raw_part)
            if not _looks_like_description_skill_candidate(cleaned):
                continue
            canonical = _canonicalize_text_item("required_skills", cleaned, config)
            if not _is_allowed_skill_entity(cleaned, canonical):
                continue
            segment_candidates.append(cleaned)
        if len(segment_candidates) < 2:
            continue
        candidates.extend(segment_candidates)
    return _dedupe_text_values(candidates)


def _supplement_sparse_required_skills(
    required_skills: list[str],
    row: dict[str, Any],
    config: dict | None,
) -> list[str]:
    if len(required_skills) >= _SPARSE_REQUIRED_SKILLS_THRESHOLD:
        return required_skills

    supplemented = list(required_skills)
    existing_text = {value.strip().lower() for value in supplemented}
    existing_canonical = {
        canonical
        for canonical in _build_canonical_list(supplemented, "required_skills", config)
        if canonical.strip()
    }
    for raw_value in _required_skill_fallback_values(
        row,
        config,
        source_fields=("tech_stack",),
    ):
        normalized_text = raw_value.strip().lower()
        canonical = _canonicalize_text_item("required_skills", raw_value, config)
        if normalized_text in existing_text or canonical in existing_canonical:
            continue
        supplemented.append(raw_value)
        existing_text.add(normalized_text)
        existing_canonical.add(canonical)
    if len(supplemented) >= _SPARSE_REQUIRED_SKILLS_THRESHOLD:
        return supplemented
    for raw_value in _required_skill_candidates_from_description(row, config):
        normalized_text = raw_value.strip().lower()
        canonical = _canonicalize_text_item("required_skills", raw_value, config)
        if normalized_text in existing_text or canonical in existing_canonical:
            continue
        supplemented.append(raw_value)
        existing_text.add(normalized_text)
        existing_canonical.add(canonical)
    return supplemented


def _repair_required_skill_signal(
    row: dict[str, Any],
    config: dict | None,
) -> dict[str, Any]:
    repaired = dict(row)
    original_required_skills = _normalize_array_values(
        repaired.get("required_skills") if isinstance(repaired.get("required_skills"), list) else []
    )
    required_skills = list(original_required_skills)
    required_skills_changed = False
    existing_required_entities = (
        list(repaired.get("required_skill_entities"))
        if isinstance(repaired.get("required_skill_entities"), list)
        else []
    )
    required_entities = existing_required_entities
    if not required_skills:
        required_skills = _required_skill_fallback_values(repaired, config)
        if required_skills:
            required_skills_changed = True
    else:
        supplemented_required_skills = _supplement_sparse_required_skills(required_skills, repaired, config)
        if supplemented_required_skills != required_skills:
            required_skills = supplemented_required_skills
            required_skills_changed = True
    if required_skills_changed:
        repaired["required_skills"] = required_skills
    if required_skills and (required_skills_changed or not required_entities):
        required_entities = _build_skill_entities(required_skills, "required_skills", config)
    required_canonical = _normalize_array_values(
        repaired.get("required_skills_canonical")
        if isinstance(repaired.get("required_skills_canonical"), list)
        else []
    )
    if required_skills_changed:
        required_canonical = _dedupe_canonical_values(
            _build_canonical_list(required_skills, "required_skills", config)
        )
    elif not required_canonical and required_entities:
        required_canonical = _canonical_from_entities(
            _normalise_skill_entities(required_entities, config=config)
        )
    if not required_canonical and required_skills:
        required_canonical = _dedupe_canonical_values(
            _build_canonical_list(required_skills, "required_skills", config)
        )
    repaired["required_skill_entities"] = required_entities
    repaired["required_skills_canonical"] = required_canonical
    return repaired


def _is_semantically_blank_enrichment_row(row: dict[str, Any]) -> bool:
    for field_name in (
        "required_skills",
        "required_skill_entities",
        "preferred_skills",
        "preferred_skill_entities",
        "responsibilities",
        "tech_stack",
        "keywords",
    ):
        value = row.get(field_name)
        if isinstance(value, list) and _normalize_array_values(value):
            return False
    for field_name in ("location_type", "seniority", "job_family", "domain"):
        if _normalize_text_item(row.get(field_name)) is not None:
            return False
    for field_name in ("years_experience_min", "years_experience_max"):
        if isinstance(row.get(field_name), int):
            return False
    return True


def _coerce_field(key: str, value: Any, config: dict | None = None) -> Any:
    """Coerce a raw LLM value to its canonical Python type."""
    if key in _ARRAY_FIELDS:
        if value is None or not isinstance(value, list):
            return []
        return _normalize_array_values(value)

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


# ── Pydantic model for structured output ─────────────────────────────────────

class ExtractionEvidenceOutput(_BaseModel):
    source_field: str
    text: str


class ActualLocationOutput(_BaseModel):
    raw_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    remote_scope: str | None = None
    remote_scope_value: str | None = None
    evidence: list[ExtractionEvidenceOutput] = _Field(default_factory=list)


class LanguageRequirementOutput(_BaseModel):
    language: str | None = None
    expected_level: str | None = None
    requirement_type: str | None = None
    evidence: list[ExtractionEvidenceOutput] = _Field(default_factory=list)


_REMOTE_SCOPES = frozenset(
    {"unrestricted", "city", "region", "country", "unknown", "not_applicable"}
)
_LANGUAGE_LEVEL_RANK = {
    "unspecified": -1,
    "a1": 0,
    "a2": 1,
    "b1": 2,
    "b2": 3,
    "c1": 4,
    "c2": 5,
    "native": 6,
}
_LANGUAGE_REQUIREMENT_RANK = {"unspecified": 0, "preferred": 1, "required": 2}
_EVIDENCE_SOURCE_FIELDS = frozenset(
    {"location", "description", "title", "provider_component"}
)


def _fact_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, _BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, dict):
        return value
    return None


def _fact_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = normalize_display_text(value)
    return normalized or None


def _canonical_evidence(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    evidence_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for raw_item in value[:8]:
        item = _fact_mapping(raw_item)
        if item is None:
            continue
        source_field = comparison_key(item.get("source_field", ""))
        text_value = _fact_text(item.get("text"))
        if source_field not in _EVIDENCE_SOURCE_FIELDS or text_value is None:
            continue
        evidence_by_key[(source_field, text_value)] = {
            "source_field": source_field,
            "text": text_value[:500],
        }
    return [evidence_by_key[key] for key in sorted(evidence_by_key)]


def _canonical_actual_location(
    value: Any,
    source_location: Any = None,
) -> dict[str, Any]:
    raw = _fact_mapping(value) or {}
    source = source_location if isinstance(source_location, dict) else {}
    invalid = value is not None and _fact_mapping(value) is None

    normalized: dict[str, str | None] = {}
    for field_name, source_name in (
        ("city", "city_raw"),
        ("region", "region_raw"),
        ("country", "country_raw"),
    ):
        if field_name in raw and raw[field_name] is not None and not isinstance(raw[field_name], str):
            invalid = True
        normalized[field_name] = _fact_text(raw.get(field_name)) or _fact_text(source.get(source_name))

    raw_text = _fact_text(raw.get("raw_text")) or _fact_text(source.get("raw_text")) or ""
    remote_scope_raw = comparison_key(raw.get("remote_scope", ""))
    if remote_scope_raw and remote_scope_raw not in _REMOTE_SCOPES:
        invalid = True
        remote_scope = "unknown"
    else:
        remote_scope = remote_scope_raw or "unknown"
    remote_scope_value = _fact_text(raw.get("remote_scope_value"))
    evidence = _canonical_evidence(raw.get("evidence"))
    source_text = _fact_text(source.get("raw_text"))
    if source_text:
        source_evidence = {
            "source_field": "provider_component",
            "text": source_text[:500],
        }
        if source_evidence not in evidence:
            evidence.append(source_evidence)
            evidence.sort(key=lambda item: (item["source_field"], item["text"]))

    has_components = any(normalized.values())
    has_remote_truth = remote_scope in {"unrestricted", "city", "region", "country"}
    has_any = bool(raw_text or has_components or has_remote_truth or evidence)
    if not has_any:
        extraction_status = "unknown"
    elif invalid or not (has_components or has_remote_truth):
        extraction_status = "partial"
    else:
        extraction_status = "complete"
    return {
        "raw_text": raw_text,
        "city": normalized["city"],
        "region": normalized["region"],
        "country": normalized["country"],
        "remote_scope": remote_scope,
        "remote_scope_value": remote_scope_value,
        "extraction_status": extraction_status,
        "evidence": evidence,
        "extraction_version": ACTUAL_LOCATION_EXTRACTION_VERSION,
    }


def _canonical_language_requirements(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    grouped: dict[str, dict[str, Any]] = {}
    for raw_item in value:
        item = _fact_mapping(raw_item)
        if item is None:
            continue
        language = _fact_text(item.get("language"))
        if language is None:
            continue
        language_key = comparison_key(language)
        requirement_type_raw = comparison_key(item.get("requirement_type", "unspecified"))
        expected_level_raw = comparison_key(item.get("expected_level", "unspecified"))
        is_valid_type = requirement_type_raw in _LANGUAGE_REQUIREMENT_RANK
        is_valid_level = expected_level_raw in _LANGUAGE_LEVEL_RANK
        requirement_type = requirement_type_raw if is_valid_type else "unspecified"
        expected_level = expected_level_raw if is_valid_level else "unspecified"
        group = grouped.setdefault(
            language_key,
            {
                "language": language,
                "requirement_type": requirement_type,
                "expected_level": expected_level,
                "invalid": False,
                "evidence": [],
            },
        )
        if language < group["language"]:
            group["language"] = language
        if _LANGUAGE_REQUIREMENT_RANK[requirement_type] > _LANGUAGE_REQUIREMENT_RANK[group["requirement_type"]]:
            group["requirement_type"] = requirement_type
        if _LANGUAGE_LEVEL_RANK[expected_level] > _LANGUAGE_LEVEL_RANK[group["expected_level"]]:
            group["expected_level"] = expected_level
        group["invalid"] = bool(group["invalid"] or not is_valid_type or not is_valid_level)
        group["evidence"].extend(_canonical_evidence(item.get("evidence")))

    canonical: list[dict[str, Any]] = []
    for language_key in sorted(grouped):
        group = grouped[language_key]
        evidence_by_key = {
            (item["source_field"], item["text"]): item
            for item in group["evidence"]
        }
        canonical.append(
            {
                "language": group["language"],
                "expected_level": group["expected_level"],
                "requirement_type": group["requirement_type"],
                "extraction_status": "partial" if group["invalid"] else "complete",
                "evidence": [evidence_by_key[key] for key in sorted(evidence_by_key)],
                "extraction_version": LANGUAGE_REQUIREMENT_EXTRACTION_VERSION,
            }
        )
    return canonical


def _remove_language_requirements_from_skills(
    values: list[str],
    language_requirements: list[dict[str, Any]],
) -> list[str]:
    language_keys = {
        comparison_key(requirement.get("language", ""))
        for requirement in language_requirements
        if comparison_key(requirement.get("language", ""))
    }
    filtered: list[str] = []
    for value in values:
        value_key = comparison_key(value)
        if any(
            value_key == language_key or value_key.startswith(f"{language_key} ")
            for language_key in language_keys
        ):
            continue
        filtered.append(value)
    return filtered

class EnrichmentOutput(_BaseModel):
    """Structured extraction output normalized into stage-owned field semantics."""
    required_skills: list[str] = _Field(default_factory=list)
    preferred_skills: list[str] = _Field(default_factory=list)
    required_skill_entities: list[SkillEntityOutput] = _Field(default_factory=list)
    preferred_skill_entities: list[SkillEntityOutput] = _Field(default_factory=list)
    responsibilities: list[str] = _Field(default_factory=list)
    tech_stack: list[str] = _Field(default_factory=list)
    keywords: list[str] = _Field(default_factory=list)
    location_type: str | None = None
    seniority: str | None = None
    domain: str | None = None
    job_family: str | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
    actual_location: ActualLocationOutput | None = None
    language_requirements: list[LanguageRequirementOutput] = _Field(default_factory=list)


def _apply_structured_normalization(
    output: EnrichmentOutput | dict[str, Any],
    config: dict | None,
) -> dict[str, Any]:
    """Convert EnrichmentOutput to a normalized dict preserving existing field semantics.

    Applies the same canonicalization as _coerce_field on the text path:
    - enum fields (location_type, seniority): validated against valid sets, unknown → None
    - domain, job_family: lowercased and stripped
    - list fields: None values removed, items coerced to str
    """
    if isinstance(output, dict):
        # Keep structured-dict behavior aligned with text-path coercion.
        coerced_output = {
            key: _coerce_field(key, value, config)
            for key, value in output.items()
        }
        output = EnrichmentOutput.model_validate(coerced_output)

    actual_location = _canonical_actual_location(output.actual_location)
    language_requirements = _canonical_language_requirements(output.language_requirements)
    required_skills = _remove_language_requirements_from_skills(
        _normalize_array_values(output.required_skills),
        language_requirements,
    )
    preferred_skills = _remove_language_requirements_from_skills(
        _normalize_array_values(output.preferred_skills),
        language_requirements,
    )
    responsibilities = _normalize_array_values(output.responsibilities)
    tech_stack = _normalize_array_values(output.tech_stack)
    keywords = _normalize_array_values(output.keywords)
    required_skill_entities = _build_skill_entities(
        required_skills,
        "required_skills",
        config,
        raw_entities=[entity.model_dump(mode="python") for entity in output.required_skill_entities],
    )
    preferred_skill_entities = _build_skill_entities(
        preferred_skills,
        "preferred_skills",
        config,
        raw_entities=[entity.model_dump(mode="python") for entity in output.preferred_skill_entities],
    )
    mapping_suggestions = [
        *_build_mapping_suggestions(entities=required_skill_entities),
        *_build_mapping_suggestions(entities=preferred_skill_entities),
    ]
    domain_mapping_suggestions = _build_field_mapping_suggestions(
        field="domain",
        alias_raw=_normalize_text_item(output.domain),
        canonical_raw=output.domain.lower().strip() if output.domain else None,
        config=config,
    )
    role_family_mapping_suggestions = _build_field_mapping_suggestions(
        field="role_family",
        alias_raw=_normalize_text_item(output.job_family),
        canonical_raw=output.job_family.lower().strip() if output.job_family else None,
        config=config,
    )

    return {
        "actual_location": actual_location,
        "language_requirements": language_requirements,
        "location_type_raw": _normalize_text_item(output.location_type),
        "location_type": _normalize_enum(
            output.location_type, _get_valid_location_types(config)
        ),
        "seniority_raw": _normalize_text_item(output.seniority),
        "seniority": _normalize_enum(
            output.seniority, _get_valid_seniority_enrich(config)
        ),
        "domain_raw": output.domain,
        "domain": output.domain.lower().strip() if output.domain else None,
        "job_family_raw": output.job_family,
        "job_family": output.job_family.lower().strip() if output.job_family else None,
        "years_experience_min": output.years_experience_min,
        "years_experience_max": output.years_experience_max,
        **_build_array_companions(
            field_name="required_skills",
            raw_values=required_skills,
            config=config,
            raw_entities=required_skill_entities,
        ),
        **_build_array_companions(
            field_name="preferred_skills",
            raw_values=preferred_skills,
            config=config,
            raw_entities=preferred_skill_entities,
        ),
        **_build_array_companions(field_name="responsibilities", raw_values=responsibilities, config=config),
        **_build_array_companions(field_name="tech_stack", raw_values=tech_stack, config=config),
        **_build_array_companions(field_name="keywords", raw_values=keywords, config=config),
        "mapping_suggestions": mapping_suggestions,
        "domain_mapping_suggestions": domain_mapping_suggestions,
        "role_family_mapping_suggestions": role_family_mapping_suggestions,
    }

# ── prompt construction ───────────────────────────────────────────────────────

_EXTRACTION_SCHEMA = """\
{
  "required_skills":      ["list", "of", "required", "skills"],
  "preferred_skills":     ["nice-to-have skills"],
  "required_skill_entities": [
    {"raw_text": "raw requirement phrase", "canonical": "normalized skill", "confidence": 0.95}
  ],
  "preferred_skill_entities": [
    {"raw_text": "raw preferred phrase", "canonical": "normalized skill", "confidence": 0.95}
  ],
  "responsibilities":     ["key responsibilities"],
  "tech_stack":           ["specific tools and technologies"],
  "keywords":             ["searchable keywords"],
  "actual_location": {
    "raw_text": "display location text or null",
    "city": "city or null",
    "region": "region or null",
    "country": "country or null",
    "remote_scope": "unrestricted | city | region | country | unknown | not_applicable",
    "remote_scope_value": "scope value or null",
    "evidence": [{"source_field": "location | description | provider_component", "text": "short quote"}]
  },
  "language_requirements": [
    {
      "language": "language name",
      "expected_level": "a1 | a2 | b1 | b2 | c1 | c2 | native | unspecified",
      "requirement_type": "required | preferred | unspecified",
      "evidence": [{"source_field": "description | title | provider_component", "text": "short quote"}]
    }
  ],
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
    config: dict[str, Any] | None = None,
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
    prompt_id = get_enrich_extraction_prompt_id(config)
    rendered = render_prompt(
        prompt_id,
        {
            "metadata_block": metadata_block,
            "extraction_schema": _EXTRACTION_SCHEMA,
            "description": description,
        },
        replacement_text=get_prompt_replacement("enrich_extraction", config),
    )
    return rendered.text


def get_enrich_extraction_prompt_id(config: dict[str, Any] | None = None) -> str:
    prompt_id = str(
        ((((config or {}).get("prompts") or {}).get("enrich") or {}).get("extraction") or {}
    ).get("prompt_id") or "").strip()
    if prompt_id:
        return prompt_id
    return load_prompt_task_registry()["enrich_extraction"]["prompt_id"]


def get_enrich_prompt_provenance(config: dict[str, Any] | None = None) -> dict[str, Any]:
    prompt_id = get_enrich_extraction_prompt_id(config)
    definition = get_prompt_definition(prompt_id)
    model_name = get_enrich_extraction_model(config or {})
    customization = get_prompt_replacement_metadata("enrich_extraction", config)
    return {
        "prompt_id": definition.prompt_id,
        "prompt_version": definition.version,
        "template_path": str(definition.template_path),
        "model": model_name,
        "prompt_customized": customization["customized"],
        "prompt_replacement_sha256": customization["replacement_sha256"],
        "prompt_replacement_char_count": customization["replacement_char_count"],
    }


def _normalize_fingerprint_text(value: Any) -> str | None:
    text = _normalize_text_item(value)
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip().lower()


def _fingerprint_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalize_source_location_fingerprint(value: Any) -> dict[str, str | None] | None:
    if not isinstance(value, dict):
        return None
    return {
        key: _normalize_fingerprint_text(value.get(key))
        for key in ("raw_text", "city_raw", "region_raw", "country_raw", "provider")
    }

def build_raw_job_fingerprint(job: dict[str, Any]) -> RawJobFingerprintResult:
    payload: RawJobFingerprintPayload = {
        "fingerprint_version": RAW_JOB_FINGERPRINT_VERSION,
        "job_url": str(job.get("job_url") or "").strip(),
        "title": _normalize_fingerprint_text(job.get("title")),
        "company_name": _normalize_fingerprint_text(job.get("company_name")),
        "location": _normalize_fingerprint_text(job.get("location")),
        "description_cleaned": _normalize_fingerprint_text(
            job.get("description_cleaned") or job.get("description")
        ),
        "contract_type": _normalize_fingerprint_text(job.get("contract_type")),
        "experience_level": _normalize_fingerprint_text(job.get("experience_level")),
        "source": _normalize_fingerprint_text(job.get("source")),
        "source_location": _normalize_source_location_fingerprint(
            job.get("source_location")
        ),
    }
    return {
        "payload": payload,
        "fingerprint": _fingerprint_hash(payload),
    }


def build_enrich_contract_fingerprint(
    config: dict[str, Any] | None = None,
) -> EnrichContractFingerprintResult:
    prompt_provenance = get_enrich_prompt_provenance(config)
    payload: EnrichContractFingerprintPayload = {
        "contract_version": ENRICH_CONTRACT_VERSION,
        "prompt_id": prompt_provenance["prompt_id"],
        "prompt_version": prompt_provenance["prompt_version"],
        "template_path": prompt_provenance["template_path"],
        "model": prompt_provenance["model"],
        "response_schema_version": ENRICH_RESPONSE_SCHEMA_VERSION,
        "skill_postprocessing_version": ENRICH_SKILL_POSTPROCESSING_VERSION,
        "actual_location_extraction_version": ACTUAL_LOCATION_EXTRACTION_VERSION,
        "language_requirement_extraction_version": (
            LANGUAGE_REQUIREMENT_EXTRACTION_VERSION
        ),
    }
    return {
        "payload": payload,
        "fingerprint": _fingerprint_hash(payload),
    }


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
    policy = _build_normalization_policy(config)
    cleaned = _strip_markdown_fences(response_text)

    try:
        raw: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        repaired = _repair_common_json_issues(cleaned)
        if repaired != cleaned:
            try:
                raw = json.loads(repaired)
            except json.JSONDecodeError:
                raw = None
            else:
                cleaned = repaired
        else:
            raw = None
        if raw is not None:
            pass
        else:
        # Some models sometimes emit malformed JSON
        # (missing commas, trailing commas, etc.). Try json_repair before giving up.
            try:
                from json_repair import repair_json  # type: ignore[import-untyped]
                raw = json.loads(repair_json(cleaned))
            except Exception:
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
    if isinstance(raw.get("location_type"), str) and raw.get("location_type") and parsed.get("location_type") is None:
        errors.append("coercion_warning:location_type:invalid_enum")
    if isinstance(raw.get("seniority"), str) and raw.get("seniority") and parsed.get("seniority") is None:
        errors.append("coercion_warning:seniority:invalid_enum")

    parsed["location_type_raw"] = _normalize_text_item(raw.get("location_type"))
    parsed["seniority_raw"] = _normalize_text_item(raw.get("seniority"))
    parsed["domain_raw"] = raw.get("domain") if isinstance(raw.get("domain"), str) else None
    parsed["job_family_raw"] = raw.get("job_family") if isinstance(raw.get("job_family"), str) else None

    required_skill_entities = _build_skill_entities(
        list(parsed.get("required_skills") or []),
        "required_skills",
        config,
        raw_entities=raw.get("required_skill_entities") if isinstance(raw.get("required_skill_entities"), list) else None,
    )
    preferred_skill_entities = _build_skill_entities(
        list(parsed.get("preferred_skills") or []),
        "preferred_skills",
        config,
        raw_entities=raw.get("preferred_skill_entities") if isinstance(raw.get("preferred_skill_entities"), list) else None,
    )
    parsed["required_skill_entities"] = required_skill_entities
    parsed["preferred_skill_entities"] = preferred_skill_entities
    parsed["required_skills_canonical"] = _canonical_from_entities(required_skill_entities)
    parsed["preferred_skills_canonical"] = _canonical_from_entities(preferred_skill_entities)
    mapping_suggestions: list[MappingSuggestion] = [
        *_build_mapping_suggestions(entities=required_skill_entities),
        *_build_mapping_suggestions(entities=preferred_skill_entities),
    ]
    domain_mapping_suggestions = _build_field_mapping_suggestions(
        field="domain",
        alias_raw=parsed.get("domain_raw"),
        canonical_raw=parsed.get("domain"),
        config=config or {"domain_alias_map": policy.domain_alias_map},
    )
    role_family_mapping_suggestions = _build_field_mapping_suggestions(
        field="role_family",
        alias_raw=parsed.get("job_family_raw"),
        canonical_raw=parsed.get("job_family"),
        config=config or {"role_family_alias_map": policy.role_family_alias_map, "role_taxonomy": policy.role_taxonomy},
    )
    parsed["mapping_suggestions"] = mapping_suggestions
    parsed["domain_mapping_suggestions"] = domain_mapping_suggestions
    parsed["role_family_mapping_suggestions"] = role_family_mapping_suggestions
    parsed["actual_location"] = _canonical_actual_location(raw.get("actual_location"))
    parsed["language_requirements"] = _canonical_language_requirements(
        raw.get("language_requirements")
    )

    return {
        "parsed": parsed,
        "errors": errors,
        "raw_response": response_text,
    }


# ── merge ─────────────────────────────────────────────────────────────────────

def _semantic_skill_values(
    enriched: dict[str, Any],
    raw_field: str,
    entity_field: str,
) -> list[str] | None:
    raw_values = enriched.get(raw_field)
    if isinstance(raw_values, list):
        return [str(value) for value in raw_values if str(value or "").strip()]
    entities = enriched.get(entity_field)
    if not isinstance(entities, list):
        return None
    values = [
        str(entity.get("raw_text"))
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("raw_text") or "").strip()
    ]
    return values or None

def _apply_job_semantic_snapshot(
    merged: dict[str, Any],
    enriched: dict[str, Any],
    config: dict[str, Any],
) -> None:
    policy = config.get("semantic_policy")
    if not isinstance(policy, dict):
        policy = compile_semantic_policy(config)

    raw_fields: dict[str, object] = {}
    for raw_field, entity_field in (
        ("required_skills", "required_skill_entities"),
        ("preferred_skills", "preferred_skill_entities"),
    ):
        values = _semantic_skill_values(enriched, raw_field, entity_field)
        if values is not None:
            raw_fields[raw_field] = values
    for raw_field, snapshot_field in (
        ("domain_raw", "domain"),
        ("job_family_raw", "job_family"),
    ):
        value = enriched.get(raw_field)
        if isinstance(value, str):
            raw_fields[snapshot_field] = value

    snapshot = build_semantic_snapshot(
        "job",
        str(merged.get("raw_job_fingerprint") or merged.get("job_url") or ""),
        raw_fields,
        policy,
    )
    merged["semantic_snapshot"] = snapshot
    for field, target in (
        ("required_skills", "required_skills_canonical"),
        ("preferred_skills", "preferred_skills_canonical"),
        ("domain", "domain"),
        ("job_family", "job_family"),
    ):
        canonical = project_canonical(snapshot, field)
        if canonical is not None:
            merged[target] = canonical

    snapshot_fields = snapshot.get("fields")
    if not isinstance(snapshot_fields, dict):
        return
    for field, entity_field in (
        ("required_skills", "required_skill_entities"),
        ("preferred_skills", "preferred_skill_entities"),
    ):
        field_entities = snapshot_fields.get(field)
        if not isinstance(field_entities, list):
            continue
        canonical_by_raw = {
            str(entity.get("raw_value") or ""): str(entity.get("canonical_value") or "")
            for entity in field_entities
            if isinstance(entity, dict)
        }
        existing = merged.get(entity_field)
        if isinstance(existing, list) and existing:
            merged[entity_field] = [
                {
                    **entity,
                    "canonical": canonical_by_raw.get(
                        str(entity.get("raw_text") or "").strip().lower(),
                        str(entity.get("canonical") or ""),
                    ),
                }
                for entity in existing
                if isinstance(entity, dict)
            ]

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
    model = str(enriched.get("enrichment_model") or get_enrich_extraction_model(cfg) or cfg.get("ai_score_model") or "")
    version = str(enriched.get("enrichment_version") or cfg.get("enrichment_version", "v1"))
    source_location = (
        scraped.get("source_location")
        if isinstance(scraped.get("source_location"), dict)
        else None
    )
    actual_location = _canonical_actual_location(
        enriched.get("actual_location"),
        source_location,
    )
    raw_language_requirements = enriched.get("language_requirements")
    language_requirements = (
        raw_language_requirements
        if isinstance(raw_language_requirements, list)
        else []
    )

    merged: dict[str, Any] = {
        # ── scraped fields ────────────────────────────────────────────
        "job_url":            scraped.get("job_url", ""),
        "title":              scraped.get("title", ""),
        "company_name":       scraped.get("company_name", ""),
        "company_id":         scraped.get("company_id", ""),
        "location":           scraped.get("location", ""),
        "source_location":    source_location,
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
        "actual_location":     actual_location,
        "language_requirements": language_requirements,
        "location_type_raw":    enriched.get("location_type_raw"),
        "location_type":        enriched.get("location_type"),
        "seniority_raw":        enriched.get("seniority_raw"),
        "seniority":            enriched.get("seniority"),
        "required_skills":      enriched.get("required_skills", []),
        "required_skills_canonical": enriched.get("required_skills_canonical", []),
        "required_skill_entities": enriched.get("required_skill_entities", []),
        "preferred_skills":     enriched.get("preferred_skills", []),
        "preferred_skills_canonical": enriched.get("preferred_skills_canonical", []),
        "preferred_skill_entities": enriched.get("preferred_skill_entities", []),
        "responsibilities":     enriched.get("responsibilities", []),
        "domain_raw":           enriched.get("domain_raw"),
        "domain":               enriched.get("domain"),
        "tech_stack":           enriched.get("tech_stack", []),
        "years_experience_min": enriched.get("years_experience_min"),
        "years_experience_max": enriched.get("years_experience_max"),
        "keywords":             enriched.get("keywords", []),
        "job_family_raw":       enriched.get("job_family_raw"),
        "job_family":           enriched.get("job_family"),
        "mapping_suggestions":  enriched.get("mapping_suggestions", []),
        "domain_mapping_suggestions": enriched.get("domain_mapping_suggestions", []),
        "role_family_mapping_suggestions": enriched.get("role_family_mapping_suggestions", []),
        # ── audit fields ──────────────────────────────────────────────
        "enrichment_version": version,
        "enrichment_model":   model,
        "enriched_at":        _normalise_enriched_at(enriched.get("enriched_at")) or datetime.now(tz=timezone.utc).isoformat(),
        "raw_job_fingerprint": enriched.get("raw_job_fingerprint"),
        "enrich_contract_fingerprint": enriched.get("enrich_contract_fingerprint"),
        "enrich_reuse_status": enriched.get("enrich_reuse_status"),
    }
    # Seed domain mapping suggestions from scraper sector -> enrich domain when they differ.
    sector_alias = str(scraped.get("sector") or "").strip().lower()
    domain_canonical = str(merged.get("domain") or "").strip().lower()
    if sector_alias and domain_canonical and sector_alias != domain_canonical:
        existing = list(merged.get("domain_mapping_suggestions") or [])
        dedupe_keys = {
            (
                str(item.get("alias") or "").strip().lower(),
                str(item.get("canonical") or "").strip().lower(),
            )
            for item in existing
            if isinstance(item, dict)
        }
        candidate_key = (sector_alias, domain_canonical)
        if candidate_key not in dedupe_keys:
            existing.append(
                {
                    "field": "domain",
                    "alias": sector_alias,
                    "canonical": domain_canonical,
                    "confidence": 1.0,
                    "matches": True,
                }
            )
        merged["domain_mapping_suggestions"] = existing

    # Seed role-family suggestions from title-derived taxonomy family when it
    # differs from the enrich-extracted job_family phrasing.
    role_family_alias = str(merged.get("job_family_raw") or merged.get("job_family") or "").strip().lower()
    role_family_canonical = infer_role_family(
        str(scraped.get("title") or ""),
        config=config,
    )
    if not role_family_alias and role_family_canonical:
        role_family_alias = role_family_canonical.replace("_", " ")
    if role_family_alias == role_family_canonical and "_" in role_family_alias:
        role_family_alias = role_family_alias.replace("_", " ")
    if role_family_alias and role_family_canonical and role_family_alias != role_family_canonical:
        existing_role = list(merged.get("role_family_mapping_suggestions") or [])
        dedupe_role_keys = {
            (
                str(item.get("alias") or "").strip().lower(),
                str(item.get("canonical") or "").strip().lower(),
            )
            for item in existing_role
            if isinstance(item, dict)
        }
        candidate_role_key = (role_family_alias, role_family_canonical)
        if candidate_role_key not in dedupe_role_keys:
            existing_role.append(
                {
                    "field": "role_family",
                    "alias": role_family_alias,
                    "canonical": role_family_canonical,
                    "confidence": 1.0,
                    "matches": True,
                }
            )
        merged["role_family_mapping_suggestions"] = existing_role
    merged = _repair_required_skill_signal(merged, config)
    _apply_job_semantic_snapshot(merged, merged, cfg)
    return merged


def _parse_json_field(raw_value: Any) -> Any:
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return None
    return None


def _normalise_enriched_at(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _cached_structured_row_to_enriched_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "location_type_raw": row.get("location_type_raw"),
        "location_type": row.get("location_type"),
        "seniority_raw": row.get("seniority_raw"),
        "seniority": row.get("seniority"),
        "required_skills": list(row.get("required_skills") or []),
        "required_skills_canonical": list(row.get("required_skills_canonical") or []),
        "required_skill_entities": _parse_json_field(row.get("required_skill_entities_json")) or [],
        "preferred_skills": list(row.get("preferred_skills") or []),
        "preferred_skills_canonical": list(row.get("preferred_skills_canonical") or []),
        "preferred_skill_entities": _parse_json_field(row.get("preferred_skill_entities_json")) or [],
        "responsibilities": list(row.get("responsibilities") or []),
        "domain_raw": row.get("domain_raw"),
        "domain": row.get("domain"),
        "tech_stack": list(row.get("tech_stack") or []),
        "years_experience_min": row.get("years_experience_min"),
        "years_experience_max": row.get("years_experience_max"),
        "keywords": list(row.get("keywords") or []),
        "job_family_raw": row.get("job_family_raw"),
        "job_family": row.get("job_family"),
        "mapping_suggestions": _parse_json_field(row.get("mapping_suggestions_json")) or [],
        "domain_mapping_suggestions": _parse_json_field(row.get("domain_mapping_suggestions_json")) or [],
        "role_family_mapping_suggestions": _parse_json_field(row.get("role_family_mapping_suggestions_json")) or [],
        "enrichment_version": row.get("enrichment_version"),
        "enrichment_model": row.get("enrichment_model"),
        "enriched_at": _normalise_enriched_at(row.get("enriched_at")),
        "raw_job_fingerprint": row.get("raw_job_fingerprint"),
        "enrich_contract_fingerprint": row.get("enrich_contract_fingerprint"),
        "enrich_reuse_status": row.get("enrich_reuse_status"),
    }


def lookup_reusable_structured_jobs(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    raw_job_fingerprints: dict[str, str],
    enrich_contract_fingerprint: str,
) -> dict[str, dict[str, Any]]:
    if not normalized_jobs:
        return {}

    job_urls = [
        str(job.get("job_url") or "")
        for job in normalized_jobs
        if str(job.get("job_url") or "")
    ]
    if not job_urls:
        return {}
    normalized_by_url = {
        str(job.get("job_url") or ""): job
        for job in normalized_jobs
        if str(job.get("job_url") or "")
    }
    placeholders = ",".join("?" for _ in job_urls)
    sql = (
        "SELECT job_url, raw_job_fingerprint, enrich_contract_fingerprint, payload_json "
        f"FROM {_SQLITE_STRUCTURED_JOBS_TABLE} "
        f"WHERE job_url IN ({placeholders})"
    )
    reusable_rows: dict[str, dict[str, Any]] = {}
    with sqlite3.connect(_sqlite_path(), timeout=30) as conn:
        _configure_sqlite_connection(conn)
        _ensure_sqlite_structured_jobs_table(conn)
        for job_url, raw_fingerprint, contract_fingerprint, payload_json in conn.execute(sql, job_urls).fetchall():
            if not isinstance(job_url, str) or not job_url:
                continue
            if job_url in reusable_rows:
                continue
            if str(raw_fingerprint or "") != str(raw_job_fingerprints.get(job_url) or ""):
                continue
            if str(contract_fingerprint or "") != str(enrich_contract_fingerprint or ""):
                continue
            normalized_job = normalized_by_url.get(job_url)
            if normalized_job is None:
                continue
            try:
                cached_payload = json.loads(str(payload_json or "{}"))
            except json.JSONDecodeError:
                continue
            if not isinstance(cached_payload, dict):
                continue
            merged_row = merge_scraped_and_enriched(
                normalized_job,
                {
                    **cached_payload,
                    "raw_job_fingerprint": raw_job_fingerprints[job_url],
                    "enrich_contract_fingerprint": enrich_contract_fingerprint,
                    "enrich_reuse_status": REUSED_CACHED_ENRICHMENT_STATUS,
                },
                config,
            )
            if _is_semantically_blank_enrichment_row(merged_row):
                continue
            reusable_rows[job_url] = merged_row
    return reusable_rows


# ── integration: LLM call ─────────────────────────────────────────────────────

class EnrichRuntimeError(RuntimeError):
    """Expose normalized runtime failure to stage retry policy."""

    def __init__(self, failure: LlmRuntimeFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def _execute_enrich_runtime(
    job: dict[str, Any],
    config: dict[str, Any],
    *,
    adapter: LlmAdapter | None = None,
) -> LlmRuntimeResult:
    prompt = build_extraction_prompt(
        description=str(job.get("description", "")),
        scraped_metadata={
            "title": job.get("title", ""),
            "experienceLevel": job.get("experience_level", ""),
            "contractType": job.get("contract_type", ""),
            "sector": job.get("sector", ""),
            "location": job.get("location", ""),
        },
        config=config,
    )
    request = LlmTaskRequest(
        routing_part="enrich_extraction",
        prompt=prompt,
        response_mode="json_object",
    )

    def _parser(response: LlmAdapterResponse) -> dict[str, Any]:
        raw_text = response.raw_text
        try:
            decoded = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            return parse_extraction_response(raw_text, config)
        if not isinstance(decoded, dict):
            return parse_extraction_response(raw_text, config)
        try:
            parsed = _apply_structured_normalization(decoded, config)
        except _ValidationError:
            return parse_extraction_response(raw_text, config)
        return {"parsed": parsed, "errors": [], "raw_response": raw_text}

    def _validator(value: Any) -> LlmValidationResult:
        is_valid = (
            isinstance(value, dict)
            and isinstance(value.get("parsed"), dict)
            and isinstance(value.get("errors"), list)
        )
        return LlmValidationResult(
            valid=is_valid,
            errors=[] if is_valid else ["Enrichment parser returned invalid contract."],
            details={},
        )

    return execute_llm_task(
        request,
        parser=_parser,
        validator=_validator,
        adapter=adapter,
        resolved_route=resolve_llm_routing("enrich_extraction", runtime_config=config),
    )


def _enrich_result_to_row(
    job: dict[str, Any],
    config: dict[str, Any],
    result: LlmRuntimeResult,
) -> dict[str, Any]:
    if result.status != "succeeded" or not isinstance(result.parsed_value, dict):
        failure = result.failure or LlmRuntimeFailure(
            stage="validate",
            code="validation_error",
            message="Enrichment runtime returned no parsed value.",
        )
        raise EnrichRuntimeError(failure)

    extraction = result.parsed_value
    if extraction["errors"]:
        logger.warning(
            "Enrichment parse errors for job %r: %s",
            job.get("title") or job.get("job_url"),
            "; ".join(extraction["errors"]),
        )
    return merge_scraped_and_enriched(job, extraction["parsed"], config)


def enrich_job(job: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Extract structured fields through shared LLM runtime."""
    return _enrich_result_to_row(job, config, _execute_enrich_runtime(job, config))


def _enrich_one(
    job: dict[str, Any],
    config: dict[str, Any],
    *,
    job_event_callback: Callable[[dict[str, Any]], None] | None = None,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
    input_index: int = 0,
    cancellation_callback: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Enrich one job with System-owned fixed-backoff retry semantics."""
    maximum_attempts = get_system_maximum_attempts(config)
    backoff_seconds = get_system_initial_backoff_seconds(config)
    job_url = extract_job_url(job)

    for attempt_number in range(1, maximum_attempts + 1):
        if cancellation_callback is not None:
            cancellation_callback()
        started_at = time.monotonic()
        if job_event_callback and job_url:
            try:
                job_event_callback({"phase": "job_start", "job_url": job_url})
            except Exception:  # noqa: BLE001
                pass
        try:
            if runtime_observation_callback is None:
                enriched = enrich_job(job, config)
            else:
                result = _execute_enrich_runtime(job, config)
                try:
                    runtime_observation_callback(
                        {
                            "contract_version": "llm_runtime_observation_v1",
                            "scope_key": str(
                                job.get("raw_job_fingerprint")
                                or build_raw_job_fingerprint(job)["fingerprint"]
                            ),
                            "input_index": input_index,
                            "invocation_index": attempt_number,
                            "evidence": project_llm_runtime_evidence(result),
                        }
                    )
                except Exception:  # noqa: BLE001
                    logger.warning("runtime observation callback failed", exc_info=True)
                enriched = _enrich_result_to_row(job, config, result)
        except EnrichRuntimeError as exc:
            failure = exc.failure
            retryable_rate_limit = (
                failure.stage == "adapter"
                and failure.code == "adapter_http_error"
                and failure.http_status == 429
            )
            if not retryable_rate_limit or attempt_number >= maximum_attempts:
                raise
            time.sleep(backoff_seconds)
            continue

        if job_event_callback and job_url:
            try:
                job_event_callback(
                    {
                        "phase": "job_done",
                        "job_url": job_url,
                        "elapsed_secs": int(max(0.0, time.monotonic() - started_at)),
                    }
                )
            except Exception:  # noqa: BLE001
                pass
        return enriched

    raise RuntimeError("enrichment attempts exhausted")


def enrich_batch(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    job_event_callback: Callable[[dict[str, Any]], None] | None = None,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
    on_item_complete: Callable[[dict[str, Any]], None] | None = None,
    cancellation_callback: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    """Enrich one job per future while returning rows in input order."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    concurrency = get_stage_runtime_concurrency(
        config,
        stage="enrich",
        default=8,
    )
    if not normalized_jobs:
        return []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {
            executor.submit(
                _enrich_one,
                job,
                config,
                job_event_callback=job_event_callback,
                runtime_observation_callback=runtime_observation_callback,
                input_index=idx,
                cancellation_callback=cancellation_callback,
            ): idx
            for idx, job in enumerate(normalized_jobs)
        }
        results: list[dict[str, Any] | None] = [None] * len(normalized_jobs)
        try:
            for future in as_completed(future_to_idx):
                if cancellation_callback is not None:
                    cancellation_callback()
                idx = future_to_idx[future]
                row = future.result()
                results[idx] = row
                if on_item_complete is not None:
                    try:
                        on_item_complete(row)
                    except Exception:  # noqa: BLE001
                        logger.warning("on_item_complete callback failed for item %d", idx, exc_info=True)
        except BaseException:
            for future in future_to_idx:
                future.cancel()
            raise

    return [row for row in results if row is not None]


# ── structured-job upsert ─────────────────────────────────────────────────────

_MERGE_COLUMNS = [
    "title", "company_name", "company_id", "location", "contract_type",
    "experience_level", "sector", "salary_min", "salary_max", "salary_currency",
    "applications_count", "published_at", "location_type_raw", "location_type",
    "seniority_raw", "seniority", "required_skills", "required_skills_canonical",
    "required_skill_entities_json", "preferred_skills", "preferred_skills_canonical",
    "preferred_skill_entities_json", "responsibilities", "responsibilities_canonical",
    "domain_raw", "domain", "tech_stack", "tech_stack_canonical",
    "years_experience_min", "years_experience_max", "keywords", "keywords_canonical",
    "job_family_raw", "job_family", "mapping_suggestions_json", "domain_mapping_suggestions_json",
    "role_family_mapping_suggestions_json", "description_cleaned",
    "enrichment_version", "enrichment_model", "enriched_at",
    "raw_job_fingerprint", "enrich_contract_fingerprint", "enrich_reuse_status",
]

_STAGING_SCHEMA_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("job_url", "STRING", "REQUIRED"),
    ("title", "STRING", "NULLABLE"),
    ("company_name", "STRING", "NULLABLE"),
    ("company_id", "STRING", "NULLABLE"),
    ("location", "STRING", "NULLABLE"),
    ("contract_type", "STRING", "NULLABLE"),
    ("experience_level", "STRING", "NULLABLE"),
    ("sector", "STRING", "NULLABLE"),
    ("salary_min", "FLOAT64", "NULLABLE"),
    ("salary_max", "FLOAT64", "NULLABLE"),
    ("salary_currency", "STRING", "NULLABLE"),
    ("applications_count", "INT64", "NULLABLE"),
    ("published_at", "DATE", "NULLABLE"),
    ("location_type_raw", "STRING", "NULLABLE"),
    ("location_type", "STRING", "NULLABLE"),
    ("seniority_raw", "STRING", "NULLABLE"),
    ("seniority", "STRING", "NULLABLE"),
    ("required_skills", "STRING", "REPEATED"),
    ("required_skills_canonical", "STRING", "REPEATED"),
    ("required_skill_entities_json", "STRING", "NULLABLE"),
    ("preferred_skills", "STRING", "REPEATED"),
    ("preferred_skills_canonical", "STRING", "REPEATED"),
    ("preferred_skill_entities_json", "STRING", "NULLABLE"),
    ("responsibilities", "STRING", "REPEATED"),
    ("responsibilities_canonical", "STRING", "REPEATED"),
    ("domain_raw", "STRING", "NULLABLE"),
    ("domain", "STRING", "NULLABLE"),
    ("tech_stack", "STRING", "REPEATED"),
    ("tech_stack_canonical", "STRING", "REPEATED"),
    ("years_experience_min", "INT64", "NULLABLE"),
    ("years_experience_max", "INT64", "NULLABLE"),
    ("keywords", "STRING", "REPEATED"),
    ("keywords_canonical", "STRING", "REPEATED"),
    ("job_family_raw", "STRING", "NULLABLE"),
    ("job_family", "STRING", "NULLABLE"),
    ("mapping_suggestions_json", "STRING", "NULLABLE"),
    ("domain_mapping_suggestions_json", "STRING", "NULLABLE"),
    ("role_family_mapping_suggestions_json", "STRING", "NULLABLE"),
    ("description_cleaned", "STRING", "NULLABLE"),
    ("enrichment_version", "STRING", "NULLABLE"),
    ("enrichment_model", "STRING", "NULLABLE"),
    ("enriched_at", "TIMESTAMP", "NULLABLE"),
    ("raw_job_fingerprint", "STRING", "NULLABLE"),
    ("enrich_contract_fingerprint", "STRING", "NULLABLE"),
    ("enrich_reuse_status", "STRING", "NULLABLE"),
)

_STRUCTURED_JSON_LIST_FIELDS: tuple[tuple[str, str], ...] = (
    ("required_skill_entities", "required_skill_entities_json"),
    ("preferred_skill_entities", "preferred_skill_entities_json"),
    ("mapping_suggestions", "mapping_suggestions_json"),
    ("domain_mapping_suggestions", "domain_mapping_suggestions_json"),
    ("role_family_mapping_suggestions", "role_family_mapping_suggestions_json"),
)

_STRUCTURED_SCHEMA_KEYS: frozenset[str] = frozenset(
    ["job_url", *_MERGE_COLUMNS]
)


def _project_enriched_row(
    row: dict[str, Any],
    *,
    schema_keys: frozenset[str],
    json_list_fields: tuple[tuple[str, str], ...],
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    if extra_fields:
        mapped.update(extra_fields)
    for key in schema_keys:
        if key in row:
            mapped[key] = row[key]
    for source_key, target_key in json_list_fields:
        if source_key in row:
            mapped[target_key] = json.dumps(row.get(source_key, []), ensure_ascii=False)
    return mapped

def _map_to_structured_jobs_row(row: dict[str, Any]) -> dict[str, Any]:
    return _project_enriched_row(
        row,
        schema_keys=_STRUCTURED_SCHEMA_KEYS,
        json_list_fields=_STRUCTURED_JSON_LIST_FIELDS,
    )


def load_structured_jobs(
    enriched: list[dict[str, Any]],
    config: dict[str, Any],
) -> int:
    """Upsert enriched job rows into local sqlite structured-jobs cache."""
    cacheable_rows = [row for row in enriched if not _is_semantically_blank_enrichment_row(row)]
    if not cacheable_rows:
        return 0

    with sqlite3.connect(_sqlite_path(), timeout=30) as conn:
        _configure_sqlite_connection(conn)
        _ensure_sqlite_structured_jobs_table(conn)
        rows = []
        for row in cacheable_rows:
            job_url = str(row.get("job_url") or "").strip()
            if not job_url:
                continue
            rows.append(
                (
                    job_url,
                    str(row.get("raw_job_fingerprint") or ""),
                    str(row.get("enrich_contract_fingerprint") or ""),
                    json.dumps(row, ensure_ascii=False),
                    _normalise_enriched_at(row.get("enriched_at")) or datetime.now(tz=timezone.utc).isoformat(),
                )
            )
        conn.executemany(
            f"""
            INSERT INTO {_SQLITE_STRUCTURED_JOBS_TABLE}
                (job_url, raw_job_fingerprint, enrich_contract_fingerprint, payload_json, enriched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                raw_job_fingerprint=excluded.raw_job_fingerprint,
                enrich_contract_fingerprint=excluded.enrich_contract_fingerprint,
                payload_json=excluded.payload_json,
                enriched_at=excluded.enriched_at
            """,
            rows,
        )
        conn.commit()
    return len(rows)


# ── run-scoped append ──────────────────────────────────────────────────────────

# Ordered columns for run_structured_jobs (same order as DDL).
_RUN_SCHEMA_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("run_id",               "STRING",    "REQUIRED"),
    ("job_url",              "STRING",    "REQUIRED"),
    ("title",                "STRING",    "NULLABLE"),
    ("company_name",         "STRING",    "NULLABLE"),
    ("location",             "STRING",    "NULLABLE"),
    ("actual_location",      "JSON",      "NULLABLE"),
    ("language_requirements", "JSON",     "NULLABLE"),
    ("contract_type",        "STRING",    "NULLABLE"),
    ("experience_level",     "STRING",    "NULLABLE"),
    ("published_at",         "DATE",      "NULLABLE"),
    ("location_type_raw",    "STRING",    "NULLABLE"),
    ("location_type",        "STRING",    "NULLABLE"),
    ("seniority_raw",        "STRING",    "NULLABLE"),
    ("seniority",            "STRING",    "NULLABLE"),
    ("required_skills",      "STRING",    "REPEATED"),
    ("required_skills_canonical", "STRING", "REPEATED"),
    ("required_skill_entities_json", "STRING", "NULLABLE"),
    ("preferred_skills",     "STRING",    "REPEATED"),
    ("preferred_skills_canonical", "STRING", "REPEATED"),
    ("preferred_skill_entities_json", "STRING", "NULLABLE"),
    ("responsibilities",     "STRING",    "REPEATED"),
    ("responsibilities_canonical", "STRING", "REPEATED"),
    ("domain_raw",           "STRING",    "NULLABLE"),
    ("domain",               "STRING",    "NULLABLE"),
    ("tech_stack",           "STRING",    "REPEATED"),
    ("tech_stack_canonical", "STRING",    "REPEATED"),
    ("years_experience_min", "INT64",     "NULLABLE"),
    ("years_experience_max", "INT64",     "NULLABLE"),
    ("keywords",             "STRING",    "REPEATED"),
    ("keywords_canonical",   "STRING",    "REPEATED"),
    ("job_family_raw",       "STRING",    "NULLABLE"),
    ("job_family",           "STRING",    "NULLABLE"),
    ("mapping_suggestions_json", "STRING", "NULLABLE"),
    ("domain_mapping_suggestions_json", "STRING", "NULLABLE"),
    ("role_family_mapping_suggestions_json", "STRING", "NULLABLE"),
    ("description_cleaned",  "STRING",    "NULLABLE"),
    ("enrichment_version",   "STRING",    "NULLABLE"),
    ("enrichment_model",     "STRING",    "NULLABLE"),
    ("enriched_at",          "TIMESTAMP", "NULLABLE"),
    ("raw_job_fingerprint",  "STRING",    "NULLABLE"),
    ("enrich_contract_fingerprint", "STRING", "NULLABLE"),
    ("enrich_reuse_status",  "STRING",    "NULLABLE"),
    ("semantic_snapshot",    "JSON",      "NULLABLE"),
)

_RUN_SCHEMA_KEYS: frozenset[str] = frozenset(name for name, _, _ in _RUN_SCHEMA_FIELDS)


def _map_to_run_structured_jobs_row(
    row: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Project an enriched row into the run_structured_jobs schema, injecting run_id."""
    return _project_enriched_row(
        row,
        schema_keys=_RUN_SCHEMA_KEYS - {"run_id"},
        json_list_fields=_STRUCTURED_JSON_LIST_FIELDS,
        extra_fields={"run_id": run_id},
    )


def _ensure_sqlite_run_structured_jobs_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_structured_jobs (
            run_id TEXT NOT NULL,
            job_url TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            enriched_at TEXT,
            PRIMARY KEY (run_id, job_url)
        )
        """
    )
    conn.commit()



def load_run_structured_jobs(
    enriched: list[dict[str, Any]],
    run_id: str,
    config: dict[str, Any],
) -> int:
    """Append run-scoped enriched job rows into local sqlite table."""
    rows = [_map_to_run_structured_jobs_row(row, run_id) for row in enriched]
    db_path = _sqlite_path()
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _configure_sqlite_connection(conn)
        _ensure_sqlite_run_structured_jobs_table(conn)
        conn.executemany(
            """
            INSERT INTO run_structured_jobs(run_id, job_url, payload_json, enriched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, job_url) DO UPDATE SET
                payload_json = excluded.payload_json,
                enriched_at = excluded.enriched_at
            """,
            [
                (
                    str(row["run_id"]),
                    str(row["job_url"]),
                    json.dumps(row, ensure_ascii=False),
                    str(row.get("enriched_at") or ""),
                )
                for row in rows
            ],
        )
        conn.commit()
    return len(rows)


def _sqlite_path() -> str:
    from fitcv.persistence import get_local_sqlite_path

    return get_local_sqlite_path()


def _configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")


def _ensure_sqlite_structured_jobs_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_SQLITE_STRUCTURED_JOBS_TABLE} (
            job_url TEXT PRIMARY KEY,
            raw_job_fingerprint TEXT,
            enrich_contract_fingerprint TEXT,
            payload_json TEXT NOT NULL,
            enriched_at TEXT
        )
        """
    )
