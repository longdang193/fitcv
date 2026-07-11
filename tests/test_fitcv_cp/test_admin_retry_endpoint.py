"""@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.app admin retry endpoint policy caps
excludes:
  - live redis workers
  - live remote database
tags:
  - fast
  - ci-safe
"""

import datetime
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from fitcv_cp.app import create_app
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.retry_settings import RetrySettings
from fitcv_cp.run_artifact_contracts import run_attempt_payload_v1


def _app() -> object:
    return create_app(bq=None, project="p", dataset="d", redis_url="redis://localhost:6379/0")


def test_admin_retry_run_rejects_when_max_attempts_exhausted() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
    )
    attempts = [
        RunEvent(
            run_id="r1",
            event_id="e1",
            stage="run_attempt",
            level="info",
            message="start",
            created_at=now,
            payload_json=json.dumps(run_attempt_payload_v1(attempt_id="a1", status="failed"), ensure_ascii=False),
        ),
        RunEvent(
            run_id="r1",
            event_id="e2",
            stage="run_attempt",
            level="info",
            message="start",
            created_at=now,
            payload_json=json.dumps(run_attempt_payload_v1(attempt_id="a2", status="failed"), ensure_ascii=False),
        ),
    ]

    with patch("fitcv_cp.sqlite_store.get_run", return_value=run):
        with patch("fitcv_cp.sqlite_store.get_events", return_value=attempts):
            with patch(
                "fitcv_cp.retry_settings.load_retry_settings",
                return_value=RetrySettings(
                    enabled=True,
                    max_attempts=2,
                    backoff_seconds=(1, 2, 4, 8),
                    lease_seconds=900,
                    reconciler_interval_seconds=0,
                    error_details_max_chars=2048,
                ),
            ):
                resp = TestClient(_app()).post("/admin/runs/r1/retry")

    assert resp.status_code == 409


def test_admin_retry_run_enqueues_when_under_cap() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.FAILED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
    )
    attempts = [
        RunEvent(
            run_id="r1",
            event_id="e1",
            stage="run_attempt",
            level="info",
            message="start",
            created_at=now,
            payload_json=json.dumps(run_attempt_payload_v1(attempt_id="a1", status="failed"), ensure_ascii=False),
        )
    ]

    update_run_status = MagicMock(return_value={"persistence_status": "persisted", "degradation_reason": "none"})
    update_binding = MagicMock(return_value={"persistence_status": "persisted", "degradation_reason": "none"})
    update_job_id = MagicMock(return_value={"persistence_status": "persisted", "degradation_reason": "none"})
    append_event = MagicMock(return_value={"persistence_status": "persisted", "degradation_reason": "none"})

    with patch("fitcv_cp.sqlite_store.get_run", return_value=run):
        with patch("fitcv_cp.sqlite_store.get_events", return_value=attempts):
            with patch("fitcv_cp.sqlite_store.update_run_status", update_run_status):
                with patch("fitcv_cp.sqlite_store.update_run_orchestration_binding", update_binding):
                    with patch("fitcv_cp.sqlite_store.update_run_queue_job_id", update_job_id):
                        with patch("fitcv_cp.sqlite_store.append_event", append_event):
                            with patch(
                                "fitcv_cp.queue.enqueue_run_with_job_id",
                                return_value=("r1", "job-1"),
                            ):
                                with patch(
                                    "fitcv_cp.retry_settings.load_retry_settings",
                                    return_value=RetrySettings(
                                        enabled=True,
                                        max_attempts=3,
                                        backoff_seconds=(1, 2, 4, 8),
                                        lease_seconds=900,
                                        reconciler_interval_seconds=0,
                                        error_details_max_chars=2048,
                                    ),
                                ):
                                    resp = TestClient(_app()).post("/admin/runs/r1/retry")

    assert resp.status_code == 200
    update_run_status.assert_called()
    append_event.assert_called()




