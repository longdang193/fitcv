"""@meta
name: pipeline_contracts
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Single-source-of-truth contracts for FitCV pipeline runtime.
inputs:
  - Used by src.fitcv.pipeline and control-plane helpers for stable taxonomies.
outputs:
  - Enums and helpers for pipeline invariants.
lifecycle:
  - status: active
"""

from __future__ import annotations

from enum import Enum
from typing import Final

PIPELINE_STAGE_SEQUENCE: Final[tuple[str, ...]] = (
    "normalize",
    "enrich",
    "rule_filter",
    "shortlist",
    "ranking",
    "cv_analysis",
    "cv_generation",
)
PIPELINE_STAGE_SET: Final[frozenset[str]] = frozenset(PIPELINE_STAGE_SEQUENCE)

PIPELINE_STAGE_DISPLAY_LABELS: Final[dict[str, str]] = {
    "normalize": "Normalize",
    "enrich": "Enrich",
    "rule_filter": "Rule Filter",
    "shortlist": "Shortlist",
    "ranking": "Ranking",
    "cv_analysis": "CV Analysis",
    "cv_generation": "CV Generation",
}

PIPELINE_STAGE_ARTIFACT_FILENAMES: Final[dict[str, str]] = {
    "normalize": "normalize.json",
    "enrich": "enrich.json",
    "rule_filter": "rule_filter.json",
    "shortlist": "shortlist.json",
    "ranking": "ranking.json",
    "cv_analysis": "cv_analysis.json",
    "cv_generation": "cv_generation.json",
}

TIMELINE_STAGE_DOWNLOADS: Final[dict[str, str]] = {
    "layer1_normalize": "normalize",
    "layer1_jobs": "enrich",
    "layer3_filter": "rule_filter",
    "layer3_shortlist": "shortlist",
    "layer3_ranking": "ranking",
    "layer4_cv_analysis": "cv_analysis",
    "layer4_cv_analysis_skip": "cv_analysis",
    "pipeline_complete": "cv_generation",
    "pipeline_compute_complete": "cv_generation",
    "layer4_cv_skip": "cv_analysis",
    "layer4_cv_validation_failed": "cv_generation",
}

TIMELINE_STAGE_DOWNLOADABLE_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "layer1_normalize",
        "layer1_jobs",
        "layer3_filter",
        "layer3_shortlist",
        "layer3_ranking",
        "layer4_cv_analysis",
        "layer4_cv_validation_failed",
        "pipeline_complete",
        "pipeline_compute_complete",
    }
)

TIMELINE_STAGE_LABELS: Final[dict[str, str]] = {
    "pipeline_start": "Pipeline",
    "layer1_normalize": "Normalize",
    "layer1b_pre_filter": "Pre-Enrichment Filter",
    "enrich_heartbeat": "Enrich In Progress",
    "layer1_jobs": "Enrich",
    "layer2_candidate": "Candidate Profile",
    "layer3_filter": "Rule Filter",
    "layer3_shortlist": "Shortlist",
    "layer3_ai_score": "Ranking",
    "layer3_ranking": "Ranking",
    "layer4_cv_analysis": "CV Analysis",
    "layer4_cv_analysis_invoked": "CV Analysis",
    "layer4_cv_analysis_skip": "CV Analysis",
    "layer4_cv_skip": "CV Analysis",
    "layer4_cv_generation_invoked": "CV Generation",
    "layer4_cv_generation_reused": "CV Generation",
    "layer4_cv_validation_failed": "CV Generation",
    "pipeline_complete": "CV Generation",
    "pipeline_compute_complete": "CV Generation",
    "layer4_cv_analysis_blocked_details": "CV Analysis Blocked Details",
    "stage_checkpoint": "Checkpoint",
    "manual_continue_requested": "Manual Continue",
    "pipeline_failed": "Pipeline",
    "synonym_overlay_uploaded": "Synonym Overlay",
}

STAGE_DOWNLOAD_LABELS: Final[dict[str, str]] = {
    stage_id: f"Download {label} JSON"
    for stage_id, label in PIPELINE_STAGE_DISPLAY_LABELS.items()
}

PIPELINE_BUNDLE_STAGE_IDS: Final[tuple[str, ...]] = PIPELINE_STAGE_SEQUENCE
PIPELINE_BUNDLE_ARTIFACT_FILENAMES: Final[tuple[str, ...]] = (
    "results.json",
    "hitl-review-audit.json",
    "stage-artifacts.json",
    *tuple(PIPELINE_STAGE_ARTIFACT_FILENAMES[stage_id] for stage_id in PIPELINE_STAGE_SEQUENCE),
    "settings-used.json",
    "cv-debug.json",
    "cv-generation-review-required.json",
    "cv-analysis-trace.json",
    "agentic-live-trace.json",
    "mapping-suggestions.json",
    "synonym-proposals.json",
    "synonym-proposals-trace.json",
    "synonym-suppression-diff.json",
    "approved-synonym-proposals.yaml",
    "synonym-overlay-used.yaml",
)

def build_stage_dispatch_map() -> dict[str, str]:
    return {stage_name: stage_name for stage_name in PIPELINE_STAGE_SEQUENCE}

def next_pipeline_stage(stage_name: str | None) -> str | None:
    normalized = str(stage_name or "").strip()
    if not normalized:
        return PIPELINE_STAGE_SEQUENCE[0]
    if normalized not in PIPELINE_STAGE_SET:
        raise ValueError(f"Unknown stage: {normalized}")
    stage_index = PIPELINE_STAGE_SEQUENCE.index(normalized)
    if stage_index + 1 >= len(PIPELINE_STAGE_SEQUENCE):
        return None
    return PIPELINE_STAGE_SEQUENCE[stage_index + 1]

def completed_pipeline_stages_through(stage_name: str | None) -> list[str]:
    normalized = str(stage_name or "").strip()
    if not normalized:
        return []
    if normalized not in PIPELINE_STAGE_SET:
        raise ValueError(f"Unknown stage: {normalized}")
    stage_index = PIPELINE_STAGE_SEQUENCE.index(normalized)
    return list(PIPELINE_STAGE_SEQUENCE[: stage_index + 1])

def timeline_stage_download_for_event(event_stage: str) -> str | None:
    normalized = str(event_stage or "").strip()
    if not normalized:
        return None
    return TIMELINE_STAGE_DOWNLOADS.get(normalized)

def timeline_event_allows_stage_download(event_stage: str) -> bool:
    return str(event_stage or "").strip() in TIMELINE_STAGE_DOWNLOADABLE_EVENTS

def timeline_stage_label(event_stage: str) -> str:
    normalized = str(event_stage or "").strip()
    if not normalized:
        return "—"
    return TIMELINE_STAGE_LABELS.get(normalized, normalized.replace("_", " ").title())

def stage_download_label(stage_id: str) -> str:
    normalized = str(stage_id or "").strip()
    if not normalized:
        raise ValueError("stage_id is required")
    return STAGE_DOWNLOAD_LABELS[normalized]

def stage_artifact_filename(stage_id: str) -> str:
    normalized = str(stage_id or "").strip()
    if not normalized:
        raise ValueError("stage_id is required")
    return PIPELINE_STAGE_ARTIFACT_FILENAMES[normalized]


class ReviewRequiredReasonCode(str, Enum):
    """Canonical reason-code taxonomy for CV generation review-required outcomes."""

    PROVIDER_ERROR = "provider_error"
    PROVIDER_RESPONSE_UNUSABLE = "provider_response_unusable"
    TIMEOUT = "timeout"
    EMPTY_OUTPUT = "empty_output"
    TEMPLATE_CONTRACT_VIOLATION = "template_contract_violation"
    MARKDOWN_STRUCTURE_VIOLATION = "markdown_structure_violation"
    POST_VALIDATION_FAILED = "post_validation_failed"
    PERSISTENCE_FAILED = "persistence_failed"

    POLICY_REQUIRED_RATIO_FAIL = "policy_required_ratio_fail"
    POLICY_MISSING_REQUIRED_FAIL = "policy_missing_required_fail"
    POLICY_ACCEPTANCE_FAIL = "policy_acceptance_fail"

    UNSUPPORTED_REQUIREMENT_GAP = "unsupported_requirement_gap"
    LOW_CONFIDENCE_SECTIONS = "low_confidence_sections"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    VALIDATION_GUARDRAIL_FAILED = "validation_guardrail_failed"
    EVIDENCE_COVERAGE_INSUFFICIENT = "evidence_coverage_insufficient"
    REVIEW_GATE_MANUAL_REQUIRED = "review_gate_manual_required"

    MANUAL_REVIEW_OTHER = "manual_review_other"


def is_review_required_reason_code(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ReviewRequiredReasonCode(value)
    except ValueError:
        return False
    return True

