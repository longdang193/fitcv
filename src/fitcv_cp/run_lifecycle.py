"""@meta
name: run_lifecycle
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Shared lifecycle policy helpers for control-plane run commands and projections.
inputs:
  - PipelineRun records and lifecycle command context
outputs:
  - Shared lifecycle booleans, projections, and target-status decisions
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from fitcv_cp.models import JobStageStatus, PipelineRun, ResultBucket, RunStageStatus, RunStatus

@dataclass(frozen=True)
class PrototypeStage:
    stage_id: str
    label: str
    ordinal: int

PROTOTYPE_STAGES = (
    PrototypeStage("enrichment", "Enrichment", 1),
    PrototypeStage("screening", "Screening", 2),
    PrototypeStage("shortlisting", "Shortlisting", 3),
    PrototypeStage("ranking", "Ranking", 4),
    PrototypeStage("cv-analysis", "CV Analysis", 5),
    PrototypeStage("cv-generation", "CV Generation", 6),
)
_CANONICAL_STAGE_BY_ALIAS = {
    "normalize": "enrichment",
    "enrich": "enrichment",
    "enrichment": "enrichment",
    "rule_filter": "screening",
    "screening": "screening",
    "shortlist": "shortlisting",
    "shortlisting": "shortlisting",
    "ranking": "ranking",
    "cv_analysis": "cv-analysis",
    "cv-analysis": "cv-analysis",
    "cv_generation": "cv-generation",
    "cv-generation": "cv-generation",
}
_RUN_DISPLAY_STATUS = {
    RunStatus.QUEUED: "Running",
    RunStatus.RUNNING: "Running",
    RunStatus.AWAITING_CONTINUE: "Running",
    RunStatus.CANCELLING: "Running",
    RunStatus.SUCCEEDED: "Succeeded",
    RunStatus.CANCELLED: "Cancelled",
    RunStatus.FAILED: "Failed",
}

def canonical_stage_id(stage_id: str) -> str | None:
    return _CANONICAL_STAGE_BY_ALIAS.get(str(stage_id or "").strip())

def run_display_status(status: RunStatus) -> str:
    return _RUN_DISPLAY_STATUS[status]

def result_bucket_for_job_stage(
    status: JobStageStatus,
    *,
    has_usable_output: bool = False,
    skip_is_terminal_rejection: bool = False,
) -> ResultBucket | None:
    if status in {JobStageStatus.PASSED, JobStageStatus.GENERATED}:
        return ResultBucket.PASSED
    if status == JobStageStatus.REVIEW_REQUIRED:
        return ResultBucket.PASSED if has_usable_output else ResultBucket.REJECTED
    if status in {JobStageStatus.REJECTED, JobStageStatus.BLOCKED, JobStageStatus.FAILED}:
        return ResultBucket.REJECTED
    if status == JobStageStatus.SKIPPED and skip_is_terminal_rejection:
        return ResultBucket.REJECTED
    return None

def run_stage_status_from_pipeline(value: str) -> RunStageStatus:
    normalized = str(value or "").strip().lower()
    if normalized in {"completed", "complete", "succeeded", "success"}:
        return RunStageStatus.SUCCEEDED
    if normalized in {"running", "started", "in_progress"}:
        return RunStageStatus.RUNNING
    if normalized in {"warning", "degraded"}:
        return RunStageStatus.WARNING
    if normalized == "partial":
        return RunStageStatus.PARTIAL
    if normalized in {"failed", "error"}:
        return RunStageStatus.FAILED
    if normalized == "cancelled":
        return RunStageStatus.CANCELLED
    if normalized in {"skipped", "not_reached", "not_applicable"}:
        return RunStageStatus.SKIPPED
    return RunStageStatus.PENDING

def job_stage_status_from_outcome(outcome: str, stage_id: str) -> JobStageStatus:
    normalized = str(outcome or "").strip().lower()
    if normalized == "accepted":
        return JobStageStatus.GENERATED if stage_id == "cv-generation" else JobStageStatus.PASSED
    if normalized == "held":
        return JobStageStatus.REVIEW_REQUIRED
    if normalized == "rejected":
        return JobStageStatus.REJECTED
    if normalized == "blocked":
        return JobStageStatus.BLOCKED
    if normalized == "skipped":
        return JobStageStatus.SKIPPED
    return JobStageStatus.FAILED

def decide_terminal_run(
    *,
    orchestration_completed: bool,
    cancelled: bool,
    required_failure: bool,
    unresolved_jobs: int,
    partial_stages: int,
    usable_results: int,
) -> tuple[RunStatus, bool, str]:
    if cancelled:
        status = RunStatus.CANCELLED
    elif not orchestration_completed or required_failure or unresolved_jobs or partial_stages:
        status = RunStatus.FAILED
    else:
        status = RunStatus.SUCCEEDED
    partial_completion = status != RunStatus.SUCCEEDED and usable_results > 0
    return status, partial_completion, "partial_completion" if partial_completion else status.value

ACTIVE_RUN_STATUS_VALUES = frozenset(
    {
        RunStatus.QUEUED.value,
        RunStatus.RUNNING.value,
        RunStatus.CANCELLING.value,
    }
)
TERMINAL_RUN_STATUS_VALUES = frozenset(
    {
        RunStatus.SUCCEEDED.value,
        RunStatus.FAILED.value,
        RunStatus.CANCELLED.value,
    }
)
AWAITING_CONTINUE_RUN_STATUS_VALUES = frozenset({RunStatus.AWAITING_CONTINUE.value})


def run_status_projection(run: PipelineRun) -> dict[str, Any]:
    status_value = run.status.value
    raw_status = str(getattr(run, "raw_status", "") or "").strip() or None
    return {
        "status": status_value,
        "raw_status": raw_status,
        "display_status": raw_status or status_value,
        "is_active": status_value in ACTIVE_RUN_STATUS_VALUES,
        "is_terminal": status_value in TERMINAL_RUN_STATUS_VALUES,
        "is_awaiting_continue": status_value in AWAITING_CONTINUE_RUN_STATUS_VALUES,
        "is_archived": bool(run.archived_at),
    }


def can_cancel_run(run: PipelineRun) -> bool:
    return run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.AWAITING_CONTINUE}


def can_reconcile_abandoned_attempts(run: PipelineRun) -> bool:
    return run.status in {RunStatus.QUEUED, RunStatus.RUNNING}


def can_retry_run(run: PipelineRun) -> bool:
    if run.status == RunStatus.CANCELLED:
        return False
    if getattr(run, "cancel_requested_at", None) is not None:
        return False
    return run.status in {RunStatus.FAILED, RunStatus.QUEUED, RunStatus.RUNNING}


def can_archive_run(run: PipelineRun) -> bool:
    return run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED} and run.archived_at is None


def can_unarchive_run(run: PipelineRun) -> bool:
    return run.archived_at is not None


def is_stale_cancelling(
    run: PipelineRun,
    *,
    now: datetime.datetime | None = None,
    stale_after: datetime.timedelta = datetime.timedelta(minutes=2),
) -> bool:
    if run.status != RunStatus.CANCELLING or run.finished_at is not None:
        return False
    if run.started_at is None:
        return True
    if run.cancel_requested_at is None:
        return False
    effective_now = now or datetime.datetime.now(datetime.timezone.utc)
    return (effective_now - run.cancel_requested_at) >= stale_after


def cancel_request_target_status(
    run: PipelineRun,
    *,
    cancelled_in_queue: bool = False,
) -> RunStatus:
    if run.status == RunStatus.AWAITING_CONTINUE:
        return RunStatus.CANCELLED
    if run.status == RunStatus.QUEUED and cancelled_in_queue:
        return RunStatus.CANCELLED
    if run.status == RunStatus.QUEUED and run.started_at is None:
        return RunStatus.CANCELLING
    return RunStatus.CANCELLING


def timeout_reference_timestamp(run: PipelineRun) -> datetime.datetime | None:
    if run.status in {RunStatus.RUNNING, RunStatus.CANCELLING}:
        return run.started_at or run.created_at
    if run.status in {RunStatus.QUEUED, RunStatus.AWAITING_CONTINUE}:
        return run.created_at
    return None


def timeout_transition_for_run(run: PipelineRun, max_runtime_minutes: int) -> tuple[RunStatus, str, str | None]:
    if run.status == RunStatus.QUEUED:
        return (
            RunStatus.CANCELLED,
            f"Run timed out after waiting more than {max_runtime_minutes} minute(s) in the queue.",
            None,
        )
    if run.status == RunStatus.AWAITING_CONTINUE:
        return (
            RunStatus.CANCELLED,
            f"Run timed out after waiting more than {max_runtime_minutes} minute(s) for manual continuation.",
            None,
        )
    return (
        RunStatus.FAILED,
        f"Run exceeded the maximum runtime of {max_runtime_minutes} minute(s).",
        "run_lifecycle_timeout",
    )
