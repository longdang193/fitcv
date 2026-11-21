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
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION = "ranking_ai_score_prompt_v2"
STRUCTURED_CV_SCHEMA_VERSION = "cv_doc_v1"
CV_ANALYSIS_REUSE_SCHEMA_VERSION = "cv_analysis_reuse_v3"
SHORTLIST_REQUIREMENT_CONTRACT_VERSION = "requirement_occurrence_v1"
SHORTLIST_DECISION_ENVELOPE_VERSION = "shortlist_decision_envelope_v1"
EVIDENCE_INTEGRITY_POLICY_VERSION = "evidence-integrity-v2"
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
class RequirementOccurrence:
    occurrence_id: str
    category: str
    required: bool
    source_requirement_id: str | None
    source_span: Any
    source_wording: str
    qualifiers: Mapping[str, Any]
    compound_operator: str | None = None
    child_occurrence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "category": self.category,
            "required": self.required,
            "source_requirement_id": self.source_requirement_id,
            "source_span": self.source_span,
            "source_wording": self.source_wording,
            "qualifiers": dict(self.qualifiers),
            "compound_operator": self.compound_operator,
            "child_occurrence_ids": list(self.child_occurrence_ids),
        }


def _stable_requirement_occurrence_id(
    *,
    job_identity: str,
    category: str,
    index: int,
    source_requirement_id: str | None,
    source_span: Any,
    source_wording: str,
) -> str:
    payload = json.dumps(
        {
            "job_identity": job_identity,
            "category": category,
            "index": index,
            "source_requirement_id": source_requirement_id,
            "source_span": source_span,
            "source_wording": source_wording,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return f"req-occ:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def build_requirement_occurrences(
    job: Mapping[str, Any],
    *,
    job_identity: str | None = None,
) -> list[RequirementOccurrence]:
    """Adapt job-specific requirements into one stable, duplicate-safe contract."""
    identity = str(job_identity or job.get("job_url") or job.get("source_job_id") or "job").strip()
    raw_items: list[dict[str, Any]] = []
    explicit = job.get("requirement_occurrences")
    if isinstance(explicit, list):
        raw_items.extend(item for item in explicit if isinstance(item, Mapping))

    def add_values(values: Any, category: str, default_source: str) -> None:
        if not isinstance(values, list):
            return
        for value in values:
            if isinstance(value, Mapping):
                item = dict(value)
                item.setdefault("category", category)
                if default_source == "language" and str(item.get("requirement_type") or "").strip().lower() == "preferred":
                    item["category"] = "preferred"
                item.setdefault(
                    "source_wording",
                    item.get("value") or item.get("normalized_value") or item.get("language") or item.get("text") or "",
                )
                if item.get("source_span") is None and item.get("source_spans") is not None:
                    item["source_span"] = item.get("source_spans")
            else:
                item = {"category": category, "source_wording": str(value)}
            if not item.get("source_requirement_id"):
                item["source_requirement_id"] = str(item.get("requirement_id") or item.get("clause_id") or "").strip()
            if not item.get("source_requirement_id"):
                wording = str(item.get("source_wording") or item.get("raw_text") or item.get("name") or "").strip()
                if default_source in {"required_skill", "preferred_skill"} and wording:
                    canonical = str(item.get("canonical") or wording).strip().casefold().replace("-", "_").replace(" ", "_")
                    item["source_requirement_id"] = f"{default_source}:{canonical}"
                else:
                    item["source_requirement_id"] = default_source
            raw_items.append(item)

    add_values(job.get("required_skill_entities"), "required", "required_skill")
    if not job.get("required_skill_entities"):
        add_values(job.get("required_skills") or job.get("required_skills_canonical"), "required", "required_skill")
    add_values(job.get("responsibility_entities") or job.get("responsibilities"), "duties", "responsibility")
    add_values(job.get("mandatory_clauses"), "required", "mandatory_clause")
    add_values(job.get("required_languages") or job.get("language_requirements"), "required", "language")
    add_values(job.get("preferred_skill_entities"), "preferred", "preferred_skill")
    if not job.get("preferred_skill_entities"):
        add_values(job.get("preferred_skills") or job.get("preferred_skills_canonical"), "preferred", "preferred_skill")
    add_values(job.get("other_requirements"), "required", "other_requirement")

    occurrences: list[RequirementOccurrence] = []
    for index, raw in enumerate(raw_items):
        category = str(raw.get("category") or "required").strip().lower()
        if category in {"must_have", "must-have", "required_skill", "mandatory"}:
            category = "required"
        elif category in {"responsibility", "responsibilities", "duty"}:
            category = "duties"
        elif category in {"nice_to_have", "nice-to-have", "preferred_skill"}:
            category = "preferred"
        wording = str(raw.get("source_wording") or raw.get("raw_text") or raw.get("requirement") or raw.get("name") or raw.get("text") or "").strip()
        source_id = str(raw.get("source_requirement_id") or raw.get("requirement_id") or "").strip() or None
        source_span = raw.get("source_span")
        qualifiers = raw.get("qualifiers") if isinstance(raw.get("qualifiers"), Mapping) else {}
        compound_operator = str(raw.get("compound_operator") or raw.get("operator") or "").strip().upper() or None
        children = tuple(str(value).strip() for value in raw.get("child_occurrence_ids") or [] if str(value).strip())
        occurrence_id = str(raw.get("occurrence_id") or "").strip() or _stable_requirement_occurrence_id(
            job_identity=identity,
            category=category,
            index=index,
            source_requirement_id=source_id,
            source_span=source_span,
            source_wording=wording,
        )
        occurrences.append(
            RequirementOccurrence(
                occurrence_id=occurrence_id,
                category=category,
                required=bool(raw.get("required", category != "preferred")),
                source_requirement_id=source_id,
                source_span=source_span,
                source_wording=wording,
                qualifiers=dict(qualifiers),
                compound_operator=compound_operator,
                child_occurrence_ids=children,
            )
        )
    return occurrences


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
