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
from pathlib import Path

from fastapi.testclient import TestClient

from fitcv_cp import sqlite_store
from fitcv_cp.app import create_app
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.orchestrator import RunSubmission
from fitcv_cp.retry_settings import RetrySettings
from fitcv_cp.run_artifact_contracts import run_attempt_payload_v1


def _app() -> object:
    return create_app(redis_url="redis://localhost:6379/0")

def _seed_failed_local_run(tmp_path: Path, monkeypatch) -> tuple[PipelineRun, datetime.datetime]:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv.sqlite3"))
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="retry-local-run",
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
        started_at=now,
        progress_completed=1,
        progress_total=1,
        partial_completion=True,
        effective_settings_json=json.dumps({"snapshot": "settings-a"}),
        jobs_input_json=json.dumps({"snapshot": "jobs-a"}),
        candidate_profile_json=json.dumps({"snapshot": "profile-a"}),
        settings_used_json=json.dumps({"snapshot": "settings-a"}),
    )
    sqlite_store.create_run_bundle(
        run,
        input_resource={
            "jobs_snapshot_json": json.dumps([{"job_url": "https://example.test/job-1"}]),
            "settings_snapshot_json": json.dumps({"snapshot": "settings-a"}),
            "settings_revision": "settings-revision-a",
        },
        jobs=[{"job_url": "https://example.test/job-1", "title": "Job 1"}],
    )
    finished_at = now + datetime.timedelta(seconds=1)
    sqlite_store.update_run_status(
        run.run_id,
        RunStatus.FAILED,
        finished_at=finished_at,
        error_message="worker failed",
        error_stage="worker",
    )
    sqlite_store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_id="attempt-before-retry",
            stage="run_attempt",
            level="error",
            message="worker failed",
            created_at=finished_at,
            payload_json=json.dumps(run_attempt_payload_v1(attempt_id="attempt-a", status="failed")),
        )
    )
    return run, finished_at


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
                    maximum_attempts=2,
                    initial_backoff_seconds=10,
                    lease_seconds=900,
                    reconciler_interval_seconds=30,
                    error_detail_limit=2048,
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
            with patch("fitcv_cp.app.update_run_status", update_run_status):
                with patch("fitcv_cp.app.update_run_orchestration_binding", update_binding):
                    with patch("fitcv_cp.app.update_run_queue_job_id", update_job_id):
                        with patch("fitcv_cp.app.append_event", append_event):
                            with patch(
                                "fitcv_cp.queue.enqueue_run_with_job_id",
                                return_value=("r1", "job-1"),
                            ):
                                with patch(
                                    "fitcv_cp.retry_settings.load_retry_settings",
                                    return_value=RetrySettings(
                                        maximum_attempts=3,
                                        initial_backoff_seconds=10,
                                        lease_seconds=900,
                                        reconciler_interval_seconds=30,
                                        error_detail_limit=2048,
                                    ),
                                ):
                                    resp = TestClient(_app()).post("/admin/runs/r1/retry")

    assert resp.status_code == 200
    update_run_status.assert_called()
    append_event.assert_called()

def test_local_retry_clears_finished_at_and_preserves_run_truth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run, _finished_at = _seed_failed_local_run(tmp_path, monkeypatch)
    app = create_app(redis_url="redis://localhost:6379/0")
    submission = RunSubmission(
        run_id=run.run_id,
        queue_job_id="local-retry-submission-b",
        backend_run_id="local-retry-submission-b",
        backend="local",
    )

    with patch("fitcv_cp.app.submit_run", return_value=submission):
        response = TestClient(app).post(f"/admin/runs/{run.run_id}/retry")

    assert response.status_code == 200
    retried = sqlite_store.get_run(run.run_id)
    assert retried is not None
    assert retried.status is RunStatus.QUEUED
    assert retried.started_at is None
    assert retried.finished_at is None
    assert retried.error_message is None
    assert retried.error_stage is None
    assert retried.partial_completion is False
    assert retried.progress_completed == 0
    assert retried.progress_total == 1
    assert retried.queue_job_id == "local-retry-submission-b"
    assert retried.jobs_input_json == run.jobs_input_json
    assert retried.candidate_profile_json == run.candidate_profile_json
    assert retried.settings_used_json == run.settings_used_json
    assert len(sqlite_store.query_run_jobs(run.run_id)["items"]) == 1
    attempt_events = [
        json.loads(event.payload_json)
        for event in sqlite_store.get_events(run.run_id)
        if event.stage == "run_attempt" and event.payload_json
    ]
    assert {payload["attempt"]["attempt_id"] for payload in attempt_events} == {"attempt-a"}

def test_local_retry_enqueue_failure_restores_failed_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run, finished_at = _seed_failed_local_run(tmp_path, monkeypatch)
    app = create_app(redis_url="redis://localhost:6379/0")

    with patch("fitcv_cp.app.submit_run", side_effect=RuntimeError("queue unavailable")):
        response = TestClient(app, raise_server_exceptions=False).post(f"/admin/runs/{run.run_id}/retry")

    assert response.status_code == 503
    restored = sqlite_store.get_run(run.run_id)
    assert restored is not None
    assert restored.status is RunStatus.FAILED
    assert restored.started_at == run.started_at
    assert restored.finished_at == finished_at
    assert restored.error_message == "worker failed"
    assert restored.error_stage == "worker"
    assert restored.partial_completion is True
    assert restored.progress_completed == 1
    assert restored.progress_total == 1
    assert restored.queue_job_id is None
    assert any(event.stage == "retry_enqueue_failed" for event in sqlite_store.get_events(run.run_id))




