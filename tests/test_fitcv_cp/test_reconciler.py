"""@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.reconciler reconcile_abandoned_attempts
tags:
  - fast
  - ci-safe
"""

import datetime
import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.reconciler import reconcile_abandoned_attempts
from fitcv_cp.run_artifact_contracts import run_attempt_payload_v1
from fitcv_cp.retry_settings import RetrySettings


@dataclass
class _FakeStore:
    runs: list[PipelineRun]
    events_by_run_id: dict[str, list[RunEvent]]
    appended: list[RunEvent]
    status_updates: list[tuple[str, RunStatus]]

    def list_runs(self, *, limit: int = 50, include_archived: bool = False, archived_only: bool = False):
        _ = (limit, include_archived, archived_only)
        return list(self.runs)

    def get_events(self, run_id: str):
        return list(self.events_by_run_id.get(run_id, []))

    def append_event(self, event: RunEvent):
        self.appended.append(event)
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    def update_run_status(self, run_id: str, status, **kwargs):
        _ = kwargs
        self.status_updates.append((run_id, status))
        return {"persistence_status": "persisted", "degradation_reason": "none"}


def test_reconcile_abandoned_attempts_marks_failed_when_retry_disabled() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
    )
    payload = run_attempt_payload_v1(
        attempt_id="a1",
        status=RunStatus.RUNNING.value,
        lease_expires_at=now - datetime.timedelta(seconds=1),
    )
    store = _FakeStore(
        runs=[run],
        events_by_run_id={
            "r1": [
                RunEvent(
                    run_id="r1",
                    event_id="ev-1",
                    stage="run_attempt",
                    level="info",
                    message="start",
                    created_at=now - datetime.timedelta(seconds=10),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            ]
        },
        appended=[],
        status_updates=[],
    )

    with patch(
        "fitcv_cp.reconciler.load_retry_settings",
        return_value=RetrySettings(
            maximum_attempts=1,
            initial_backoff_seconds=10,
            lease_seconds=900,
            reconciler_interval_seconds=30,
            error_detail_limit=2048,
        ),
    ):
        summary = reconcile_abandoned_attempts(store, now=now)
    assert summary.abandoned_attempts == 1
    assert summary.terminal_failed_runs == 1
    assert store.status_updates[0][1] == RunStatus.FAILED


def test_reconcile_abandoned_attempts_requeues_when_retry_enabled() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
    )
    payload = run_attempt_payload_v1(
        attempt_id="a1",
        status=RunStatus.RUNNING.value,
        lease_expires_at=now - datetime.timedelta(seconds=1),
    )
    store = _FakeStore(
        runs=[run],
        events_by_run_id={
            "r1": [
                RunEvent(
                    run_id="r1",
                    event_id="ev-1",
                    stage="run_attempt",
                    level="info",
                    message="start",
                    created_at=now - datetime.timedelta(seconds=10),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            ]
        },
        appended=[],
        status_updates=[],
    )

    with patch(
        "fitcv_cp.reconciler.load_retry_settings",
        return_value=RetrySettings(
            maximum_attempts=3,
            initial_backoff_seconds=10,
            lease_seconds=900,
            reconciler_interval_seconds=30,
            error_detail_limit=2048,
        ),
    ):
        with patch("fitcv_cp.reconciler.time.sleep") as sleep_mock, patch(
            "fitcv_cp.reconciler.enqueue_run_with_job_id",
            return_value=("r1", "job-1"),
        ) as enqueue_mock:
            summary = reconcile_abandoned_attempts(store, now=now)

    assert summary.abandoned_attempts == 1
    assert summary.requeued_attempts == 1
    sleep_mock.assert_called_once_with(10)
    enqueue_mock.assert_called_once()






def test_reconcile_abandoned_attempts_honors_cancel_request_and_blocks_retry() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.RUNNING,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
        cancel_requested_at=now - datetime.timedelta(seconds=5),
        cancel_requested_by="admin",
    )
    payload = run_attempt_payload_v1(
        attempt_id="a1",
        status=RunStatus.RUNNING.value,
        lease_expires_at=now - datetime.timedelta(seconds=1),
    )
    store = _FakeStore(
        runs=[run],
        events_by_run_id={
            "r1": [
                RunEvent(
                    run_id="r1",
                    event_id="ev-1",
                    stage="run_attempt",
                    level="info",
                    message="start",
                    created_at=now - datetime.timedelta(seconds=10),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            ]
        },
        appended=[],
        status_updates=[],
    )

    with patch(
        "fitcv_cp.reconciler.load_retry_settings",
        return_value=RetrySettings(
            maximum_attempts=3,
            initial_backoff_seconds=10,
            lease_seconds=900,
            reconciler_interval_seconds=30,
            error_detail_limit=2048,
        ),
    ):
        with patch("fitcv_cp.reconciler.enqueue_run_with_job_id") as enqueue_mock:
            summary = reconcile_abandoned_attempts(store, now=now)

    assert summary.abandoned_attempts == 1
    assert summary.requeued_attempts == 0
    assert summary.terminal_failed_runs == 0
    assert store.status_updates[0][1] == RunStatus.CANCELLED
    enqueue_mock.assert_not_called()
