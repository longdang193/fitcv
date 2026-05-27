"""@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.worker_job attempt terminal event ordering invariants
excludes:
  - live pipeline execution
  - live persistence backends
tags:
  - fast
  - ci-safe
"""

import datetime
from unittest.mock import MagicMock, patch

from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.worker_job import execute_pipeline_run


def test_worker_appends_success_attempt_event_before_marking_run_succeeded() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="r1",
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=now,
    )

    timeline: list[tuple[object, ...]] = []

    def _update_run_status(*args, **kwargs):
        _ = kwargs
        status = args[1] if len(args) > 1 else None
        timeline.append(("update", status))
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    def _append_event(event: RunEvent, *args, **kwargs):
        _ = (args, kwargs)
        timeline.append(("append", getattr(event, "stage", None), getattr(event, "message", None)))
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    with patch("fitcv_cp.worker_job._get_bq", return_value=MagicMock()):
        with patch("fitcv_cp.worker_job.get_run", return_value=run):
            with patch("fitcv_cp.worker_job.run_pipeline", return_value={"summary": {}}):
                with patch("fitcv_cp.worker_job.append_event", side_effect=_append_event):
                    with patch("fitcv_cp.worker_job.update_run_status", side_effect=_update_run_status):
                        execute_pipeline_run(
                            run_id="r1",
                            jobs_path="data/jobs.json",
                            config_path=".env.yaml",
                            attempt_id="a1",
                            queue_job_id="job-1",
                        )

    attempt_finished_idx = next(
        (
            idx
            for idx, item in enumerate(timeline)
            if item == ("append", "run_attempt", "Run attempt finished")
        ),
        None,
    )
    run_succeeded_idx = next(
        (
            idx
            for idx, item in enumerate(timeline)
            if item == ("update", RunStatus.SUCCEEDED)
        ),
        None,
    )

    assert attempt_finished_idx is not None
    assert run_succeeded_idx is not None
    assert attempt_finished_idx < run_succeeded_idx
