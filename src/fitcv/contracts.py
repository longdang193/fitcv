"""@meta
name: contracts
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.contracts.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping


RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION = "ranking_ai_score_prompt_v2"
STRUCTURED_CV_SCHEMA_VERSION = "cv_doc_v1"
CV_ANALYSIS_REUSE_SCHEMA_VERSION = "cv_analysis_reuse_v3"
FINAL_ARTIFACT_CONTRACT_VERSION = "fitcv.final_artifact.v1"
TRACE_CONTRACT_VERSION = "fitcv.trace.v1"
EFFICIENCY_CONTRACT_VERSION = "fitcv.efficiency.v1"
STAGE_TRANSITION_ARTIFACTS_PIPELINE_SCHEMA_VERSION = "stage_transition_artifacts_v8"
STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION = "stage_transition_artifacts_run_v1"
STAGE_TRANSITION_ARTIFACTS_STAGE_SCHEMA_VERSION = "stage_transition_artifacts_stage_v1"
MAPPING_SUGGESTIONS_SCHEMA_VERSION = "mapping_suggestions_v1"
MAPPING_SUGGESTIONS_AGGREGATE_SCHEMA_VERSION = "mapping_suggestions_aggregate_v1"
SETTINGS_USED_SCHEMA_VERSION = "settings_used_v2"
SYNONYM_PROPOSALS_SCHEMA_VERSION = "synonym_proposals_v1"
SYNONYM_PROPOSALS_QUEUE_SCHEMA_VERSION = "synonym_proposals_queue_v1"

REQUIRED_SKILL_SUPPORT_CHANNEL = "required_skill_support"
ROLE_ALIGNMENT_CHANNEL = "role_alignment"
DOMAIN_ALIGNMENT_CHANNEL = "domain_alignment"
RESPONSIBILITY_ALIGNMENT_CHANNEL = "responsibility_alignment"


@dataclass(frozen=True)
class AnalysisChannelDefinition:
    channel_id: str
    display_label: str
    intended_usage: str


ANALYSIS_CHANNEL_DEFINITIONS = {
    REQUIRED_SKILL_SUPPORT_CHANNEL: AnalysisChannelDefinition(
        channel_id=REQUIRED_SKILL_SUPPORT_CHANNEL,
        display_label="Required Skill Support",
        intended_usage="Use as grounding for concrete technical and skill claims.",
    ),
    ROLE_ALIGNMENT_CHANNEL: AnalysisChannelDefinition(
        channel_id=ROLE_ALIGNMENT_CHANNEL,
        display_label="Role Alignment",
        intended_usage="Use to shape summary positioning and headline alignment.",
    ),
    DOMAIN_ALIGNMENT_CHANNEL: AnalysisChannelDefinition(
        channel_id=DOMAIN_ALIGNMENT_CHANNEL,
        display_label="Domain Alignment",
        intended_usage="Use only for grounded business-context and domain familiarity claims.",
    ),
    RESPONSIBILITY_ALIGNMENT_CHANNEL: AnalysisChannelDefinition(
        channel_id=RESPONSIBILITY_ALIGNMENT_CHANNEL,
        display_label="Responsibility Alignment",
        intended_usage="Use to support experience bullets around similar work and outcomes.",
    ),
}

ANALYSIS_CHANNEL_IDS = tuple(ANALYSIS_CHANNEL_DEFINITIONS.keys())

ANALYSIS_CHANNEL_ALIASES = {
    "responsibility": RESPONSIBILITY_ALIGNMENT_CHANNEL,
    "domain": DOMAIN_ALIGNMENT_CHANNEL,
}


def canonical_analysis_channel_id(channel_id: str) -> str:
    normalized = str(channel_id or "").strip()
    if not normalized:
        return normalized
    return ANALYSIS_CHANNEL_ALIASES.get(normalized, normalized)


def normalize_analysis_channel_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, value in dict(mapping or {}).items():
        canonical_key = canonical_analysis_channel_id(str(raw_key))
        if not canonical_key:
            continue
        if canonical_key in normalized and isinstance(normalized[canonical_key], dict) and isinstance(value, Mapping):
            merged = dict(normalized[canonical_key])
            merged.update(dict(value))
            normalized[canonical_key] = merged
            continue
        normalized[canonical_key] = value
    return normalized

# Shared ingest/normalize/tracker contracts
SCRAPER_CAMEL_TO_SNAKE: dict[str, str] = {
    "jobUrl": "job_url",
    "postedTime": "posted_time",
    "publishedAt": "published_at",
    "companyName": "company_name",
    "companyUrl": "company_url",
    "companyId": "company_id",
    "applicationsCount": "applications_count",
    "contractType": "contract_type",
    "experienceLevel": "experience_level",
    "workType": "work_type",
    "posterFullName": "poster_full_name",
    "posterProfileUrl": "poster_profile_url",
    "applyUrl": "apply_url",
    "applyType": "apply_type",
    "descriptionHtml": "description_html",
    "sourceDescription": "description_source",
    "descriptionQuality": "description_quality",
    "descriptionSourceChecksum": "description_source_checksum",
    "descriptionSourceLength": "description_source_length",
    "descriptionQualitySignals": "description_quality_signals",
    "descriptionBoundary": "description_boundary",
}

REQUIRED_SCRAPER_FIELDS: tuple[str, ...] = (
    "jobUrl",
    "title",
    "companyName",
    "description",
    "contractType",
    "experienceLevel",
)

REQUIRED_INDEED_FIELDS: tuple[str, ...] = (
    "url",
    "title",
    "description",
)

CANONICAL_JOB_METADATA_FIELDS: tuple[str, ...] = (
    "source_provider",
    "source_job_id",
    "description_source",
    "description_complete",
    "description_quality",
    "description_source_checksum",
    "description_source_length",
    "description_quality_signals",
    "description_boundary",
)

_DESCRIPTION_CONTACT_RE = re.compile(
    r"\b(?:lebenslauf|cv|resume|telefon|tel\.?|e[- ]?mail|email|kontakt|contact|bewerben|apply)\b|[+]?\d[\d ()/-]{6,}",
    re.IGNORECASE,
)
_DESCRIPTION_CONTENT_RE = re.compile(
    r"\b(?:aufgaben|anforderungen|anforderung|profil|kenntnisse|verantwort(?:ung|lich)|qualifikation|skills?|requirements?|responsibilit(?:y|ies)|develop|build|experience|erfahrung|power\s*bi|python|sql)\b",
    re.IGNORECASE,
)
_DESCRIPTION_BENEFITS_RE = re.compile(
    r"\b(?:benefits?|vorteile|perks?|flexible\s+hours?|remote\s+work|meal\s+vouchers?|commuter\s+support)\b",
    re.IGNORECASE,
)


def build_description_quality(description: Any, source: Any = "") -> dict[str, Any]:
    """Return one provenance-aware quality contract for a job description."""
    text = str(description or "").strip()
    source_name = str(source or "").strip() or "unknown"
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    signals: list[str] = []
    if not text:
        quality = "missing"
        signals.append("empty")
    else:
        contact_matches = _DESCRIPTION_CONTACT_RE.findall(text)
        content_match = bool(_DESCRIPTION_CONTENT_RE.search(text))
        contact_only = bool(contact_matches) and not content_match
        benefits_only = bool(_DESCRIPTION_BENEFITS_RE.search(text)) and not content_match
        if contact_only:
            quality = "boilerplate_only"
            signals.append("contact_or_application_only")
        elif benefits_only:
            quality = "boilerplate_only"
            signals.append("benefits_only")
        elif source_name in {"api_structured_summary", "text_snippet"}:
            quality = "partial"
            signals.append(source_name)
        elif len(text) < 80:
            quality = "partial"
            signals.append("short_text")
        elif content_match:
            quality = "full"
            signals.append("substantive_content")
        else:
            quality = "unknown"
            signals.append("no_substantive_signal")
    return {
        "description_quality": quality,
        "description_source_checksum": checksum,
        "description_source_length": len(text),
        "description_quality_signals": signals,
        "description_boundary": {"start": 0, "end": len(text)},
    }

DEFAULT_APPLICATION_STATUSES: tuple[str, ...] = (
    "applied",
    "not_applied",
    "interview",
    "rejected",
    "no_response",
)
