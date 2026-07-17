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
from typing import Final, cast

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
    "cv-generation-trace.json",
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


JOB_OUTCOME_SCHEMA_VERSION: Final[str] = "job_outcome.v1"
JOB_OUTCOME_EVENT_STAGE: Final[str] = "job_outcome"
JOB_OUTCOME_VALUES: Final[frozenset[str]] = frozenset(
    {"accepted", "held", "blocked", "rejected", "skipped"}
)
JOB_OUTCOME_PROJECTION_STATUSES: Final[frozenset[str]] = frozenset(
    {"native", "legacy_projected", "incomplete"}
)
JOB_OUTCOME_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "run_id",
        "job_key",
        "job_url",
        "attempt_id",
        "stage",
        "stage_status",
        "outcome",
        "reason_code",
        "reason_facts",
        "policy_version",
        "trace_id",
        "evidence_ref",
        "projection_status",
        "occurred_at",
    }
)
JOB_OUTCOME_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {"artifact", "fingerprint", "record_key"}
)
JOB_OUTCOME_STATUS_MAP: Final[dict[str, tuple[str, str, str, str]]] = {
    "ranked_with_cv": ("accepted", "cv_generation", "accepted", "native"),
    "review_required": (
        "held",
        "cv_generation",
        "review_gate_manual_required",
        "native",
    ),
    "ranked_blocked_by_reranker_fit": (
        "blocked",
        "cv_analysis",
        "reranker_fit_below_threshold",
        "native",
    ),
    "blocked_by_reranker_fit": (
        "blocked",
        "cv_analysis",
        "reranker_fit_below_threshold",
        "native",
    ),
    "ranked_skipped_fit_gate": (
        "skipped",
        "cv_analysis",
        "cv_analysis_fit_gate_skipped",
        "native",
    ),
    "skipped_fit_gate": (
        "skipped",
        "cv_analysis",
        "cv_analysis_fit_gate_skipped",
        "native",
    ),
    "validation_failed": (
        "rejected",
        "cv_generation",
        "post_validation_failed",
        "native",
    ),
    "generation_failed": (
        "blocked",
        "cv_generation",
        "cv_generation_failed",
        "native",
    ),
    "persistence_failed": (
        "blocked",
        "cv_generation",
        "cv_persistence_failed",
        "native",
    ),
    "analysis_failed": (
        "blocked",
        "cv_analysis",
        "cv_analysis_failed",
        "native",
    ),
    "not_shortlisted": (
        "skipped",
        "shortlist",
        "not_selected_by_shortlist",
        "native",
    ),
    "shortlisted_not_scored": (
        "skipped",
        "ranking",
        "not_selected_for_scoring",
        "native",
    ),
    "scored_not_ranked": (
        "skipped",
        "ranking",
        "not_selected_in_final_ranking",
        "native",
    ),
    "rejected_after_enrichment": (
        "rejected",
        "rule_filter",
        "rule_filter_rejected",
        "native",
    ),
    "rejected_before_enrichment": (
        "rejected",
        "normalize",
        "pre_enrichment_filter_rejected",
        "native",
    ),
    "deduplicated_before_enrichment": (
        "skipped",
        "normalize",
        "duplicate_job_url",
        "native",
    ),
    "unknown_pipeline_state": (
        "blocked",
        "pipeline",
        "pipeline_state_unclassified",
        "native",
    ),
    "ranked_no_cv": (
        "blocked",
        "cv_generation",
        "legacy_ranked_no_cv_unclassified",
        "incomplete",
    ),
}


def project_pipeline_status_outcome(stage_status: str) -> dict[str, str]:
    normalized = str(stage_status or "").strip()
    outcome, stage, reason_code, projection_status = JOB_OUTCOME_STATUS_MAP.get(
        normalized,
        JOB_OUTCOME_STATUS_MAP["unknown_pipeline_state"],
    )
    return {
        "outcome": outcome,
        "stage": stage,
        "reason_code": reason_code,
        "projection_status": projection_status,
    }


def _validate_reason_value(value: object, *, depth: int) -> None:
    import math

    if depth > 3:
        raise ValueError("reason_facts exceeds maximum nesting depth")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("reason_facts numbers must be finite")
        return
    if isinstance(value, str):
        if len(value) > 512:
            raise ValueError("reason_facts strings must not exceed 512 characters")
        return
    if isinstance(value, list):
        if len(value) > 16:
            raise ValueError("reason_facts lists must not exceed 16 items")
        for item in value:
            _validate_reason_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 16:
            raise ValueError("reason_facts objects must not exceed 16 keys")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("reason_facts keys must be strings")
            _validate_reason_value(item, depth=depth + 1)
        return
    raise ValueError("reason_facts contains unsupported JSON value")


def _canonical_json_bytes(value: object) -> bytes:
    import json

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def validate_job_outcome_fact(fact: dict[str, object]) -> dict[str, object]:
    from datetime import datetime

    missing = JOB_OUTCOME_REQUIRED_KEYS.difference(fact)
    if missing:
        raise ValueError(f"job outcome missing keys: {sorted(missing)}")
    if fact["schema_version"] != JOB_OUTCOME_SCHEMA_VERSION:
        raise ValueError("unsupported job outcome schema version")
    if not str(fact["run_id"] or "").strip():
        raise ValueError("run_id is required")
    job_key = str(fact["job_key"] or "").strip()
    if not job_key.startswith("input:") or not job_key[6:].isdigit():
        raise ValueError("job_key must use input:<input_index>")
    if fact["outcome"] not in JOB_OUTCOME_VALUES:
        raise ValueError("invalid job outcome")
    if fact["projection_status"] not in JOB_OUTCOME_PROJECTION_STATUSES:
        raise ValueError("invalid job outcome projection status")
    for key in ("stage", "stage_status", "reason_code"):
        if not str(fact[key] or "").strip():
            raise ValueError(f"{key} is required")
    reason_facts = fact["reason_facts"]
    if not isinstance(reason_facts, dict):
        raise ValueError("reason_facts must be an object")
    _validate_reason_value(reason_facts, depth=1)
    if len(_canonical_json_bytes(reason_facts)) > 4096:
        raise ValueError("reason_facts exceeds 4096 canonical JSON bytes")
    evidence_ref = fact["evidence_ref"]
    if not isinstance(evidence_ref, dict) or set(evidence_ref) != JOB_OUTCOME_EVIDENCE_KEYS:
        raise ValueError("evidence_ref must contain artifact, fingerprint, and record_key")
    if evidence_ref["record_key"] != job_key:
        raise ValueError("evidence_ref record_key must equal job_key")
    if not str(evidence_ref["artifact"] or "").strip() or not str(
        evidence_ref["fingerprint"] or ""
    ).strip():
        raise ValueError("evidence_ref artifact and fingerprint are required")
    occurred_at = str(fact["occurred_at"] or "").strip()
    try:
        parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("occurred_at must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")
    return fact


def build_job_outcome_fact(
    *,
    run_id: str,
    input_index: int,
    stage_status: str,
    evidence_ref: dict[str, object],
    occurred_at: object,
    job_url: str | None = None,
    attempt_id: str | None = None,
    reason_facts: dict[str, object] | None = None,
    policy_version: str | None = None,
    trace_id: str | None = None,
    stage: str | None = None,
    outcome: str | None = None,
    reason_code: str | None = None,
    projection_status: str | None = None,
) -> dict[str, object]:
    from datetime import datetime

    projected = project_pipeline_status_outcome(stage_status)
    if isinstance(occurred_at, datetime):
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        occurred_at_value = occurred_at.isoformat().replace("+00:00", "Z")
    else:
        occurred_at_value = str(occurred_at or "").strip()
    fact: dict[str, object] = {
        "schema_version": JOB_OUTCOME_SCHEMA_VERSION,
        "run_id": str(run_id).strip(),
        "job_key": f"input:{int(input_index)}",
        "job_url": str(job_url or "").strip() or None,
        "attempt_id": str(attempt_id or "").strip() or None,
        "stage": stage or projected["stage"],
        "stage_status": str(stage_status).strip(),
        "outcome": outcome or projected["outcome"],
        "reason_code": reason_code or projected["reason_code"],
        "reason_facts": dict(reason_facts or {}),
        "policy_version": str(policy_version or "").strip() or None,
        "trace_id": str(trace_id or "").strip() or None,
        "evidence_ref": dict(evidence_ref),
        "projection_status": projection_status or projected["projection_status"],
        "occurred_at": occurred_at_value,
    }
    return validate_job_outcome_fact(fact)


def job_outcome_fingerprint(fact: dict[str, object]) -> str:
    import hashlib

    validate_job_outcome_fact(fact)
    return f"sha256:{hashlib.sha256(_canonical_json_bytes(fact)).hexdigest()}"


def project_job_outcome(
    row: dict[str, object],
    *,
    run_id: str,
    input_index: int,
) -> dict[str, object]:
    from datetime import datetime, timezone

    native = row.get("job_outcome")
    if native is not None:
        if isinstance(native, dict):
            try:
                return validate_job_outcome_fact(dict(native))
            except ValueError:
                pass
        return build_job_outcome_fact(
            run_id=run_id,
            input_index=input_index,
            job_url=str(row.get("job_url") or "") or None,
            stage_status="invalid_native_outcome",
            stage="pipeline",
            outcome="blocked",
            reason_code="invalid_native_outcome",
            projection_status="incomplete",
            evidence_ref={
                "artifact": "results.json",
                "fingerprint": "sha256:unavailable",
                "record_key": f"input:{input_index}",
            },
            occurred_at=datetime.now(timezone.utc),
        )
    stage_status = str(row.get("pipeline_status") or "unknown_pipeline_state")
    projected = project_pipeline_status_outcome(stage_status)
    return build_job_outcome_fact(
        run_id=run_id,
        input_index=input_index,
        job_url=str(row.get("job_url") or "") or None,
        stage_status=stage_status,
        stage=projected["stage"],
        outcome=projected["outcome"],
        reason_code=projected["reason_code"],
        projection_status=(
            "incomplete"
            if projected["projection_status"] == "incomplete"
            else "legacy_projected"
        ),
        evidence_ref={
            "artifact": "results.json",
            "fingerprint": "sha256:unavailable",
            "record_key": f"input:{input_index}",
        },
        occurred_at=datetime.now(timezone.utc),
    )

def count_job_outcomes(
    rows: list[dict[str, object]],
    *,
    run_id: str,
) -> dict[str, int]:
    counts = {outcome: 0 for outcome in ("accepted", "held", "blocked", "rejected", "skipped")}
    for input_index, row in enumerate(rows):
        fact = project_job_outcome(row, run_id=run_id, input_index=input_index)
        counts[str(fact["outcome"])] += 1
    return counts
JOB_OUTCOME_SURFACES: Final[dict[str, tuple[str, str]]] = {
    "accepted": ("Accepted", "badge-success"),
    "held": ("Held", "badge-warning"),
    "blocked": ("Blocked", "badge-error"),
    "rejected": ("Rejected", "badge-error"),
    "skipped": ("Skipped", "badge-warning"),
}
JOB_OUTCOME_REASON_LABELS: Final[dict[str, str]] = {
    "accepted": "Accepted result available",
    "review_gate_manual_required": "Manual review required",
    "reranker_fit_below_threshold": "Reranker fit below threshold",
    "cv_analysis_fit_gate_skipped": "CV analysis skipped by fit policy",
    "post_validation_failed": "Post-generation validation failed",
    "cv_generation_failed": "CV generation failed",
    "cv_persistence_failed": "CV persistence failed",
    "cv_analysis_failed": "CV analysis failed",
    "not_selected_by_shortlist": "Not selected by shortlist",
    "not_selected_for_scoring": "Not selected for scoring",
    "not_selected_in_final_ranking": "Not selected in final ranking",
    "rule_filter_rejected": "Rejected by rule filter",
    "pre_enrichment_filter_rejected": "Rejected before enrichment",
    "duplicate_job_url": "Duplicate job URL",
    "near_duplicate_job_posting": "Near-duplicate job posting",
    "pipeline_state_unclassified": "Pipeline state could not be classified",
    "legacy_ranked_no_cv_unclassified": "Historical ranked result lacks decisive CV status",
    "invalid_native_outcome": "Stored native outcome is invalid",
}


def job_outcome_surface(
    row: dict[str, object],
    *,
    run_id: str,
    input_index: int,
) -> dict[str, object]:
    fact = project_job_outcome(row, run_id=run_id, input_index=input_index)
    outcome = str(fact["outcome"])
    label, badge_class = JOB_OUTCOME_SURFACES[outcome]
    reason_code = str(fact["reason_code"])
    return {
        "status": outcome,
        "label": label,
        "badge_class": badge_class,
        "stage": str(fact["stage"]),
        "reason_code": reason_code,
        "reason_label": JOB_OUTCOME_REASON_LABELS.get(
            reason_code,
            reason_code.replace("_", " ").capitalize(),
        ),
        "projection_status": str(fact["projection_status"]),
        "why": {
            "stage_status": str(fact["stage_status"]),
            "reason_facts": dict(cast(dict[str, object], fact["reason_facts"])),
            "policy_version": fact["policy_version"],
            "attempt_id": fact["attempt_id"],
            "trace_id": fact["trace_id"],
            "evidence_ref": dict(cast(dict[str, object], fact["evidence_ref"])),
        },
    }

def resolve_job_outcome_fact(
    current: dict[str, object],
    *,
    resolution: str,
    occurred_at: object,
) -> dict[str, object]:
    validated = validate_job_outcome_fact(dict(current))
    normalized = str(resolution or "").strip().lower()
    if normalized not in {"accepted", "rejected"}:
        raise ValueError("resolution must be accepted or rejected")
    job_key = str(validated["job_key"])
    return build_job_outcome_fact(
        run_id=str(validated["run_id"]),
        input_index=int(job_key.removeprefix("input:")),
        job_url=str(validated.get("job_url") or "") or None,
        attempt_id=str(validated.get("attempt_id") or "") or None,
        stage_status=f"review_{normalized}",
        stage="cv_generation",
        outcome=normalized,
        reason_code="accepted" if normalized == "accepted" else "operator_rejected",
        reason_facts={"review_resolution": normalized},
        policy_version=str(validated.get("policy_version") or "") or None,
        trace_id=str(validated.get("trace_id") or "") or None,
        evidence_ref=dict(cast(dict[str, object], validated["evidence_ref"])),
        projection_status="native",
        occurred_at=occurred_at,
    )
JOB_OUTCOME_LEGACY_SURFACES: Final[dict[str, tuple[str, str]]] = {
    "ranked_with_cv": ("CV created", "badge-success"),
    "ranked_blocked_by_reranker_fit": (
        "Ranked, blocked by reranker fit",
        "badge-warning",
    ),
    "ranked_skipped_fit_gate": ("Skipped after CV analysis", "badge-warning"),
    "ranked_no_cv": ("Ranked, CV failed", "badge-warning"),
    "not_shortlisted": ("Passed filter, not shortlisted", "badge-info"),
    "shortlisted_not_scored": ("Shortlisted, not AI scored", "badge-info"),
    "scored_not_ranked": ("Scored, not final top-N", "badge-info"),
    "rejected_after_enrichment": ("Rejected after enrichment", "badge-error"),
    "rejected_before_enrichment": ("Rejected before enrichment", "badge-error"),
    "deduplicated_before_enrichment": (
        "Deduplicated before enrichment",
        "badge-warning",
    ),
}
JOB_OUTCOME_DEFAULT_FILTERS: Final[tuple[str, ...]] = (
    "ranked_with_cv",
    "ranked_blocked_by_reranker_fit",
    "ranked_no_cv",
    "scored_not_ranked",
    "ranked_skipped_fit_gate",
    "accepted",
    "held",
    "blocked",
    "skipped",
)

def job_outcome_event_reference(fact: dict[str, object]) -> dict[str, object]:
    validated = validate_job_outcome_fact(dict(fact))
    return {
        "job_key": validated["job_key"],
        "stage": validated["stage"],
        "outcome": validated["outcome"],
        "reason_code": validated["reason_code"],
        "outcome_fingerprint": job_outcome_fingerprint(validated),
        "evidence_ref": dict(cast(dict[str, object], validated["evidence_ref"])),
    }