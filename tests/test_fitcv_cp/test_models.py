from fitcv_cp.models import RunStatus, EventLevel, PipelineRun, RunEvent
import dataclasses


def test_run_status_values():
    assert set(RunStatus) == {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.SUCCEEDED, RunStatus.FAILED}


def test_event_level_values():
    assert set(EventLevel) == {EventLevel.INFO, EventLevel.WARNING, EventLevel.ERROR}


def test_pipeline_run_fields():
    fields = {f.name for f in dataclasses.fields(PipelineRun)}
    assert {"run_id", "status", "triggered_by", "trigger_source", "jobs_path",
            "config_path", "created_at", "error_stage"} <= fields


def test_run_event_fields():
    fields = {f.name for f in dataclasses.fields(RunEvent)}
    assert {"run_id", "event_id", "stage", "level", "message", "created_at"} <= fields
