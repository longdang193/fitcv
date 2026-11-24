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
STAGE_6_TO_7_HANDOFF_SCHEMA_VERSION = "fitcv.stage6_to_stage7_handoff.v1"

REQUIRED_SKILL_SUPPORT_CHANNEL = "required_skill_support"
ROLE_ALIGNMENT_CHANNEL = "role_alignment"
DOMAIN_ALIGNMENT_CHANNEL = "domain_alignment"
RESPONSIBILITY_ALIGNMENT_CHANNEL = "responsibility_alignment"


@dataclass(frozen=True)
class AnalysisChannelDefinition:
    channel_id: str
    display_label: str
    intended_usage: str


@dataclass(frozen=True)
class Stage6To7Handoff:
    """Versioned, additive input contract for CV analysis/generation."""

    job_identity: str
    job_url: str
    jd_reference: Mapping[str, Any]
    stage5_admission: Mapping[str, Any]
    stage5_evidence: tuple[Mapping[str, Any], ...]
    qualifiers: tuple[Mapping[str, Any], ...]
    gaps: tuple[Mapping[str, Any], ...]
    confirmed_gaps: tuple[Mapping[str, Any], ...]
    confirmed_unknowns: tuple[Mapping[str, Any], ...]
    clause_coverage: Mapping[str, Any]
    score_status: str
    ai_score: float | None
    baseline_rank: int | None
    final_rank: int | None
    candidate_profile_id: str
    candidate_profile_revision: str
    contract_versions: Mapping[str, str]
    fingerprints: Mapping[str, str]
    model_provenance: Mapping[str, Any]
    strategy_provenance: Mapping[str, Any]
    created_at: str | None = None
    schema_version: str = STAGE_6_TO_7_HANDOFF_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "job_identity": self.job_identity,
            "job_url": self.job_url,
            "jd_reference": dict(self.jd_reference),
            "stage5_admission": dict(self.stage5_admission),
            "stage5_evidence": [dict(item) for item in self.stage5_evidence],
            "qualifiers": [dict(item) for item in self.qualifiers],
            "gaps": [dict(item) for item in self.gaps],
            "confirmed_gaps": [dict(item) for item in self.confirmed_gaps],
            "confirmed_unknowns": [dict(item) for item in self.confirmed_unknowns],
            "clause_coverage": dict(self.clause_coverage),
            "score_status": self.score_status,
            "ai_score": self.ai_score,
            "baseline_rank": self.baseline_rank,
            "final_rank": self.final_rank,
            "candidate_profile_id": self.candidate_profile_id,
            "candidate_profile_revision": self.candidate_profile_revision,
            "contract_versions": dict(self.contract_versions),
            "fingerprints": dict(self.fingerprints),
            "model_provenance": dict(self.model_provenance),
            "strategy_provenance": dict(self.strategy_provenance),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, allow_legacy: bool = True) -> "Stage6To7Handoff":
        raw = dict(payload or {})
        schema_version = str(raw.get("schema_version") or "").strip()
        if schema_version and schema_version != STAGE_6_TO_7_HANDOFF_SCHEMA_VERSION and not allow_legacy:
            raise ValueError(f"Unsupported Stage 6 -> Stage 7 handoff schema: {schema_version}")
        required = ("job_identity", "job_url", "candidate_profile_revision")
        missing = [key for key in required if not str(raw.get(key) or "").strip()]
        if not isinstance(raw.get("jd_reference"), Mapping):
            missing.append("jd_reference")
        if not isinstance(raw.get("stage5_admission"), Mapping):
            missing.append("stage5_admission")
        if missing:
            raise ValueError(f"Incomplete Stage 6 -> Stage 7 handoff: {sorted(set(missing))}")
        def _mappings(key: str) -> tuple[Mapping[str, Any], ...]:
            value = raw.get(key) or []
            return tuple(dict(item) for item in value if isinstance(item, Mapping)) if isinstance(value, list) else ()
        score = raw.get("ai_score")
        try:
            normalized_score = float(score) if score is not None else None
        except (TypeError, ValueError):
            normalized_score = None
        return cls(
            job_identity=str(raw.get("job_identity") or raw.get("job_url") or ""),
            job_url=str(raw.get("job_url") or ""),
            jd_reference=dict(raw.get("jd_reference") or {}),
            stage5_admission=dict(raw.get("stage5_admission") or {}),
            stage5_evidence=_mappings("stage5_evidence"),
            qualifiers=_mappings("qualifiers"),
            gaps=_mappings("gaps"),
            confirmed_gaps=_mappings("confirmed_gaps") or _mappings("gaps"),
            confirmed_unknowns=_mappings("confirmed_unknowns") or _mappings("unknowns"),
            clause_coverage=dict(raw.get("clause_coverage") or raw.get("coverage") or {}),
            score_status=str(raw.get("score_status") or "unscored"),
            ai_score=normalized_score,
            baseline_rank=int(raw["baseline_rank"]) if raw.get("baseline_rank") is not None else None,
            final_rank=int(raw["final_rank"]) if raw.get("final_rank") is not None else None,
            candidate_profile_id=str(raw.get("candidate_profile_id") or ""),
            candidate_profile_revision=str(raw.get("candidate_profile_revision") or ""),
            contract_versions={str(k): str(v) for k, v in dict(raw.get("contract_versions") or {}).items()},
            fingerprints={str(k): str(v) for k, v in dict(raw.get("fingerprints") or {}).items()},
            model_provenance=dict(raw.get("model_provenance") or {}),
            strategy_provenance=dict(raw.get("strategy_provenance") or {}),
            created_at=str(raw.get("created_at") or "") or None,
            schema_version=STAGE_6_TO_7_HANDOFF_SCHEMA_VERSION,
        )


def build_stage_6_to_7_handoff(
    row: Mapping[str, Any],
    *,
    profile: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build the smallest lossless Stage 6 handoff without recomputing admission."""
    stage5_evidence = row.get("stage5_evidence") or row.get("evidence") or []
    qualifiers = row.get("qualifiers") or row.get("requirement_qualifiers") or []
    gaps = row.get("gaps") or row.get("requirement_gaps") or []
    confirmed_gaps = row.get("confirmed_gaps") or gaps
    confirmed_unknowns = row.get("confirmed_unknowns") or row.get("unknowns") or []
    clause_coverage = row.get("clause_coverage") or row.get("coverage") or row.get("coverage_summary") or {}
    handoff = Stage6To7Handoff(
        job_identity=str(row.get("job_identity") or row.get("job_url") or row.get("raw_job_fingerprint") or ""),
        job_url=str(row.get("job_url") or ""),
        jd_reference={key: row.get(key) for key in ("job_url", "job_id", "source_job_id", "title", "company_name", "source_provider") if row.get(key) not in (None, "")},
        stage5_admission=dict(row.get("stage5_admission") or {"admitted": True, "status": "admitted", "source": "stage5_shortlist"}),
        stage5_evidence=tuple(item for item in stage5_evidence if isinstance(item, Mapping)),
        qualifiers=tuple(item for item in qualifiers if isinstance(item, Mapping)),
        gaps=tuple(item for item in gaps if isinstance(item, Mapping)),
        confirmed_gaps=tuple(item for item in confirmed_gaps if isinstance(item, Mapping)),
        confirmed_unknowns=tuple(item for item in confirmed_unknowns if isinstance(item, Mapping)),
        clause_coverage=dict(clause_coverage) if isinstance(clause_coverage, Mapping) else {},
        score_status=str(row.get("score_status") or "unscored"),
        ai_score=float(row["ai_score"]) if row.get("ai_score") is not None else None,
        baseline_rank=int(row["baseline_rank"]) if row.get("baseline_rank") is not None else None,
        final_rank=int(row["final_rank"]) if row.get("final_rank") is not None else None,
        candidate_profile_id=str(row.get("candidate_profile_id") or (profile or {}).get("candidate_profile_id") or ""),
        candidate_profile_revision=str(row.get("candidate_profile_revision") or (profile or {}).get("revision") or ""),
        contract_versions={"ranking": str(row.get("ranking_contract_version") or row.get("ranking_policy_version") or ""), "shortlist": str(row.get("shortlist_contract_version") or row.get("admission_contract_version") or "")},
        fingerprints={key: str(row.get(key) or "") for key in ("raw_job_fingerprint", "ranking_contract_fingerprint", "eligibility_policy_fingerprint") if str(row.get(key) or "")},
        model_provenance=dict(row.get("model_provenance") or {"provider": row.get("ai_provider"), "model": row.get("ai_model") or row.get("model"), "prompt_version": row.get("prompt_version")}),
        strategy_provenance=dict(row.get("strategy_provenance") or {"ranking_policy_version": row.get("ranking_policy_version"), "ranking_order_version": row.get("ranking_order_version")}),
        created_at=created_at,
    )
    return handoff.to_dict()


def deserialize_stage_6_to_7_handoff(payload: Mapping[str, Any] | None, *, allow_legacy: bool = True) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    return Stage6To7Handoff.from_dict(payload, allow_legacy=allow_legacy).to_dict()


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
)

DEFAULT_APPLICATION_STATUSES: tuple[str, ...] = (
    "applied",
    "not_applied",
    "interview",
    "rejected",
    "no_response",
)


SHORTLIST_REQUIREMENT_CONTRACT_VERSION = "requirement_occurrence_v1"
SHORTLIST_DECISION_ENVELOPE_VERSION = "shortlist_decision_envelope_v1"


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
                    item.get("value")
                    or item.get("normalized_value")
                    or item.get("language")
                    or item.get("text")
                    or "",
                )
                if item.get("source_span") is None and item.get("source_spans") is not None:
                    item["source_span"] = item.get("source_spans")
            else:
                item = {"category": category, "source_wording": str(value)}
            if not item.get("source_requirement_id"):
                item["source_requirement_id"] = str(
                    item.get("requirement_id") or item.get("clause_id") or ""
                ).strip()
            if not item.get("source_requirement_id"):
                wording = str(
                    item.get("source_wording")
                    or item.get("raw_text")
                    or item.get("name")
                    or ""
                ).strip()
                if default_source in {"required_skill", "preferred_skill"} and wording:
                    canonical = (
                        str(item.get("canonical") or wording)
                        .strip()
                        .casefold()
                        .replace("-", "_")
                        .replace(" ", "_")
                    )
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
        wording = str(
            raw.get("source_wording")
            or raw.get("raw_text")
            or raw.get("requirement")
            or raw.get("name")
            or raw.get("text")
            or ""
        ).strip()
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
