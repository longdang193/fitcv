"""@meta
type: test
scope: integration
domain: run_orchestration
covers:
  - reconcile_abandoned_attempts end-to-end sqlite SSOT events
excludes:
  - live redis worker execution
  - live remote database
tags:
  - fast
  - ci-safe
"""

import datetime
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fitcv_cp.sqlite_store import append_event, get_run, insert_run
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.reconciler import reconcile_abandoned_attempts
from fitcv_cp.retry_settings import RetrySettings
from fitcv_cp.run_artifact_contracts import run_attempt_payload_v1
from fitcv_cp.store import ControlPlaneStore


def test_reconciler_sqlite_requeues_and_marks_queued() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "fitcv_cp.sqlite3"
        with patch.dict("os.environ", {"FITCV_CP_SQLITE_PATH": str(db_path)}, clear=False):
            run = PipelineRun(
                run_id="r1",
                status=RunStatus.RUNNING,
                triggered_by="admin",
                trigger_source="ui",
                jobs_path="data/jobs.json",
                config_path=".env.yaml",
                created_at=now,
            )
            insert_run(run, bq=None, project="local", dataset="local")

            payload = run_attempt_payload_v1(
                attempt_id="a1",
                status=RunStatus.RUNNING.value,
                lease_expires_at=now - datetime.timedelta(seconds=1),
            )
            append_event(
                RunEvent(
                    run_id="r1",
                    event_id="e1",
                    stage="run_attempt",
                    level="info",
                    message="start",
                    created_at=now - datetime.timedelta(seconds=10),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                ),
                bq=None,
                project="local",
                dataset="local",
            )

            store = ControlPlaneStore(bq=None, project="local", dataset="local")
            with patch(
                "fitcv_cp.reconciler.load_retry_settings",
                return_value=RetrySettings(
                    enabled=True,
                    max_attempts=3,
                    backoff_seconds=(1, 2, 4, 8),
                    lease_seconds=900,
                    reconciler_interval_seconds=0,
                    error_details_max_chars=2048,
                ),
            ):
                with patch("fitcv_cp.reconciler.enqueue_run_with_job_id", return_value=("r1", "job-1")):
                    summary = reconcile_abandoned_attempts(store, now=now)

            assert summary.requeued_attempts == 1

            refreshed = get_run("r1", bq=None, project="local", dataset="local")
            assert refreshed is not None
            assert refreshed.status == RunStatus.QUEUED


