"""Deterministic checkpoint resume and downstream invalidation decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fitcv.pipeline_contracts import PIPELINE_STAGE_SEQUENCE


class ResumeDecisionError(ValueError):
    """Raised when persisted lifecycle state cannot be resumed safely."""


_REVISION_KEYS = (
    "handoff_fingerprint",
    "contract_revision",
    "policy_revision",
    "profile_revision",
    "jd_revision",
    "requirement_contract_revision",
    "evidence_revision",
    "predecessor_revision",
    "coverage_fingerprint",
)

_FIRST_AFFECTED_STAGE = {
    "handoff_fingerprint": "cv_analysis",
    "contract_revision": "shortlist",
    "policy_revision": "cv_analysis",
    "profile_revision": "enrich",
    "jd_revision": "shortlist",
    "requirement_contract_revision": "shortlist",
    "evidence_revision": "shortlist",
    "predecessor_revision": "shortlist",
    "coverage_fingerprint": "shortlist",
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _stage_index(stage: Any) -> int:
    normalized = str(stage or "").strip()
    if normalized in PIPELINE_STAGE_SEQUENCE:
        return PIPELINE_STAGE_SEQUENCE.index(normalized)
    return 0


def _downstream_stages(boundary: str | None) -> list[str]:
    if boundary not in PIPELINE_STAGE_SEQUENCE:
        return []
    return list(PIPELINE_STAGE_SEQUENCE[_stage_index(boundary) :])


def _state_conflicts(checkpoint: Mapping[str, Any], worker: Mapping[str, Any]) -> bool:
    pairs = (
        ("terminal", "terminal"),
        ("completed", "completed"),
        ("completed_stage", "last_completed_stage"),
        ("next_stage", "next_stage"),
    )
    for checkpoint_key, worker_key in pairs:
        left = checkpoint.get(checkpoint_key)
        right = worker.get(worker_key)
        if left is None or right is None:
            continue
        if checkpoint_key.endswith("stage") or worker_key.endswith("stage"):
            if str(left or "").strip() != str(right or "").strip():
                return True
        elif bool(left) != bool(right):
            return True
    return False


def decide_resume_invalidation(
    checkpoint: Mapping[str, Any] | None,
    *,
    current: Mapping[str, Any] | None = None,
    worker_projection: Mapping[str, Any] | None = None,
    recomputation_available: bool = True,
) -> dict[str, Any]:
    """Return the active-contract decision for a persisted checkpoint.

    Old checkpoints without resume metadata keep the existing stage-based resume
    behavior. New callers can provide ``resume_contract`` metadata to make
    ownership, invalidation, and retry behavior explicit.
    """
    root = _as_mapping(checkpoint)
    contract = _as_mapping(root.get("resume_contract") or root)
    current_inputs = _as_mapping(current)
    worker = _as_mapping(worker_projection or root.get("worker_projection"))

    if _state_conflicts(contract, worker):
        return {
            "status": "technical_resume_failure",
            "decision_owner": "lifecycle",
            "resume_boundary": None,
            "restart_boundary": None,
            "invalidated_stages": [],
            "reason_code": "worker_checkpoint_state_conflict",
            "terminal": True,
            "retryable": True,
            "checkpoint_action": "preserve_for_repair",
            "worker_action": "stop_without_continuation",
            "reused_downstream_state": False,
        }

    legacy_status = str(
        _first_value(contract.get("analysis_status"), contract.get("status")) or ""
    ).strip()
    if legacy_status in {"skipped_fit_gate", "blocked_by_reranker_fit"} and contract.get("valid_current_handoff", True):
        boundary = "cv_analysis"
        return {
            "status": "recompute",
            "decision_owner": "stage7_policy",
            "resume_boundary": None,
            "restart_boundary": boundary,
            "invalidated_stages": _downstream_stages(boundary),
            "reason_code": "legacy_fit_gate_requires_recompute",
            "terminal": False,
            "retryable": True,
            "checkpoint_action": "replace_after_recompute",
            "worker_action": "recompute_current_admission",
            "reused_downstream_state": False,
        }

    expected_coverage = _first_value(
        current_inputs.get("coverage_fingerprint"),
        current_inputs.get("coverage_fingerprints"),
    )
    persisted_coverage = _first_value(
        contract.get("coverage_fingerprint"),
        contract.get("coverage_fingerprints"),
    )
    coverage_required = bool(contract.get("coverage_required") or expected_coverage is not None)
    coverage_incomplete = bool(
        contract.get("coverage_incomplete") or contract.get("failure_derived")
    )
    coverage_mismatch = coverage_required and (
        persisted_coverage is None
        or expected_coverage is None
        or persisted_coverage != expected_coverage
    )
    if coverage_incomplete or coverage_mismatch:
        boundary = "shortlist"
        if not recomputation_available:
            return {
                "status": "technical_resume_failure",
                "decision_owner": "shortlist_assessment",
                "resume_boundary": None,
                "restart_boundary": boundary,
                "invalidated_stages": _downstream_stages(boundary),
                "reason_code": "coverage_recomputation_unavailable",
                "terminal": False,
                "retryable": True,
                "checkpoint_action": "persist_incomplete_failure_derived_u",
                "worker_action": "retry_from_assessment_boundary",
                "reused_downstream_state": False,
            }
        return {
            "status": "restart",
            "decision_owner": "shortlist_assessment",
            "resume_boundary": None,
            "restart_boundary": boundary,
            "invalidated_stages": _downstream_stages(boundary),
            "reason_code": "coverage_fingerprint_incompatible",
            "terminal": False,
            "retryable": True,
            "checkpoint_action": "invalidate_dependent_state",
            "worker_action": "recompute_affected_coverage",
            "reused_downstream_state": False,
        }

    changed = [
        key
        for key in _REVISION_KEYS
        if contract.get(key) is not None
        and current_inputs.get(key) is not None
        and contract.get(key) != current_inputs.get(key)
    ]
    if changed:
        boundary = min(
            (_FIRST_AFFECTED_STAGE[key] for key in changed),
            key=_stage_index,
        )
        return {
            "status": "restart",
            "decision_owner": "upstream_contract",
            "resume_boundary": None,
            "restart_boundary": boundary,
            "invalidated_stages": _downstream_stages(boundary),
            "reason_code": "upstream_revision_changed",
            "changed_revisions": changed,
            "terminal": False,
            "retryable": True,
            "checkpoint_action": "invalidate_dependent_state",
            "worker_action": "restart_from_first_affected_boundary",
            "reused_downstream_state": False,
        }

    if contract.get("display_metadata_changed"):
        return {
            "status": "metadata_refresh",
            "decision_owner": "active_contract",
            "resume_boundary": _first_value(contract.get("next_stage"), contract.get("current_stage")),
            "restart_boundary": None,
            "invalidated_stages": list(contract.get("metadata_dependent_stages") or []),
            "reason_code": "display_metadata_changed_only",
            "terminal": False,
            "retryable": False,
            "checkpoint_action": "replace_provenance_only",
            "worker_action": "preserve_admission",
            "reused_downstream_state": True,
        }

    boundary = _first_value(contract.get("next_stage"), contract.get("current_stage"))
    return {
        "status": "resume",
        "decision_owner": "active_contract",
        "resume_boundary": boundary,
        "restart_boundary": None,
        "invalidated_stages": [],
        "reason_code": "checkpoint_compatible",
        "terminal": bool(contract.get("terminal", False)),
        "retryable": False,
        "checkpoint_action": "preserve",
        "worker_action": "resume_current_stage",
        "reused_downstream_state": True,
    }


def require_safe_resume(decision: Mapping[str, Any]) -> None:
    if str(decision.get("status") or "") == "technical_resume_failure":
        raise ResumeDecisionError(str(decision.get("reason_code") or "technical_resume_failure"))