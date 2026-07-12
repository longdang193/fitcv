"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - shared run lifecycle policy helpers
excludes:
  - live HTTP deployment
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import datetime

from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.run_lifecycle import (
    can_archive_run,
    can_cancel_run,
    can_retry_run,
    can_unarchive_run,
    cancel_request_target_status,
    is_stale_cancelling,
    run_status_projection,
    timeout_reference_timestamp,
    timeout_transition_for_run,
)


def _run(status: RunStatus, **overrides: object) -> PipelineRun:
    created_at = datetime.datetime(2026, 7, 12, 12, 0, tzinfo=datetime.timezone.utc)
    payload = {
        "run_id": "run-1",
        "status": status,
        "triggered_by": "tester",
        "trigger_source": "unit",
        "jobs_path": "data/jobs.json",
        "config_path": ".env.yaml",
        "created_at": created_at,
    }
    payload.update(overrides)
    return PipelineRun(**payload)


def test_run_status_projection_marks_active_and_archived() -> None:
    run = _run(RunStatus.RUNNING, raw_status="worker_busy", archived_at=datetime.datetime.now(datetime.timezone.utc))

    assert run_status_projection(run) == {
        "status": "running",
        "raw_status": "worker_busy",
        "display_status": "worker_busy",
        "is_active": True,
        "is_terminal": False,
        "is_awaiting_continue": False,
        "is_archived": True,
    }


def test_cancel_retry_archive_and_unarchive_guards() -> None:
    assert can_cancel_run(_run(RunStatus.QUEUED)) is True
    assert can_cancel_run(_run(RunStatus.RUNNING)) is True
    assert can_cancel_run(_run(RunStatus.SUCCEEDED)) is False

    assert can_retry_run(_run(RunStatus.FAILED)) is True
    assert can_retry_run(_run(RunStatus.CANCELLED)) is False
    assert can_retry_run(_run(RunStatus.FAILED, cancel_requested_at=datetime.datetime.now(datetime.timezone.utc))) is False

    assert can_archive_run(_run(RunStatus.SUCCEEDED)) is True
    assert can_archive_run(_run(RunStatus.SUCCEEDED, archived_at=datetime.datetime.now(datetime.timezone.utc))) is False
    assert can_unarchive_run(_run(RunStatus.SUCCEEDED, archived_at=datetime.datetime.now(datetime.timezone.utc))) is True


def test_is_stale_cancelling_uses_start_and_cancel_timestamps() -> None:
    now = datetime.datetime(2026, 7, 12, 12, 5, tzinfo=datetime.timezone.utc)

    queued_cancel = _run(RunStatus.CANCELLING, started_at=None)
    assert is_stale_cancelling(queued_cancel, now=now) is True

    fresh_cancel = _run(
        RunStatus.CANCELLING,
        started_at=now - datetime.timedelta(minutes=10),
        cancel_requested_at=now - datetime.timedelta(minutes=1),
    )
    assert is_stale_cancelling(fresh_cancel, now=now) is False

    stale_cancel = _run(
        RunStatus.CANCELLING,
        started_at=now - datetime.timedelta(minutes=10),
        cancel_requested_at=now - datetime.timedelta(minutes=3),
    )
    assert is_stale_cancelling(stale_cancel, now=now) is True


def test_cancel_target_and_timeout_helpers() -> None:
    queued = _run(RunStatus.QUEUED)
    awaiting = _run(RunStatus.AWAITING_CONTINUE)
    running = _run(RunStatus.RUNNING, started_at=datetime.datetime(2026, 7, 12, 12, 1, tzinfo=datetime.timezone.utc))

    assert cancel_request_target_status(awaiting) == RunStatus.CANCELLED
    assert cancel_request_target_status(queued, cancelled_in_queue=True) == RunStatus.CANCELLED
    assert cancel_request_target_status(queued) == RunStatus.CANCELLING

    assert timeout_reference_timestamp(queued) == queued.created_at
    assert timeout_reference_timestamp(awaiting) == awaiting.created_at
    assert timeout_reference_timestamp(running) == running.started_at
    assert timeout_reference_timestamp(_run(RunStatus.SUCCEEDED)) is None

    assert timeout_transition_for_run(queued, 15) == (
        RunStatus.CANCELLED,
        "Run timed out after waiting more than 15 minute(s) in the queue.",
        None,
    )
    assert timeout_transition_for_run(awaiting, 15) == (
        RunStatus.CANCELLED,
        "Run timed out after waiting more than 15 minute(s) for manual continuation.",
        None,
    )
    assert timeout_transition_for_run(running, 15) == (
        RunStatus.FAILED,
        "Run exceeded the maximum runtime of 15 minute(s).",
        "run_lifecycle_timeout",
    )
