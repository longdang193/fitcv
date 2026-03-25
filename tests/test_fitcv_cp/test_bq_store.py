from unittest.mock import MagicMock
from fitcv_cp.bq_store import insert_run, update_run_status, append_event, get_run, list_runs, get_events, list_cvs_for_run, get_cv_markdown
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
import datetime
import uuid


def _make_run() -> PipelineRun:
    return PipelineRun(
        run_id=str(uuid.uuid4()), status=RunStatus.QUEUED, triggered_by="admin",
        trigger_source="ui", jobs_path="data/sample_jobs.json",
        config_path=".env.yaml", created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def test_insert_run_calls_bq():
    bq = MagicMock()
    insert_run(_make_run(), bq, project="p", dataset="d")
    bq.query.assert_called_once()


def test_update_run_status_uses_parameterized_query():
    bq = MagicMock()
    update_run_status("rid", RunStatus.RUNNING, bq, project="p", dataset="d")
    bq.query.assert_called_once()
    # Verify parameterized: run_id must NOT appear literally in the SQL string
    sql_arg = bq.query.call_args[0][0]
    assert "rid" not in sql_arg, "SQL must use query parameters, not string interpolation"


def test_append_event_calls_bq():
    bq = MagicMock()
    ev = RunEvent(run_id="rid", event_id=str(uuid.uuid4()), stage="ingest",
                  level="info", message="done", created_at=datetime.datetime.now(datetime.timezone.utc))
    append_event(ev, bq, project="p", dataset="d")
    bq.insert_rows_json.assert_called_once()


def test_get_run_returns_none_when_not_found():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert get_run("missing", bq, project="p", dataset="d") is None


def test_list_runs_returns_list():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert isinstance(list_runs(bq, project="p", dataset="d"), list)


def test_get_events_returns_list():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert isinstance(get_events("rid", bq, project="p", dataset="d"), list)


def test_list_cvs_for_run_parameterized():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([
        {"version_id": "v1", "job_url": "http", "fit_classification": "strong", "generated_at": datetime.datetime.now(datetime.timezone.utc)}
    ])
    result = list_cvs_for_run("rid", bq, project="p", dataset="d")
    assert len(result) == 1
    bq.query.assert_called_once()
    sql_arg = bq.query.call_args[0][0]
    assert "rid" not in sql_arg, "SQL must use query parameters"

def test_get_cv_markdown_returns_string_or_none():
    bq = MagicMock()
    # Test not found
    bq.query.return_value.result.return_value = iter([])
    assert get_cv_markdown("missing", bq, project="p", dataset="d") is None
    
    # Test found
    bq.query.return_value.result.return_value = iter([{"cv_markdown": "my cv"}])
    assert get_cv_markdown("found", bq, project="p", dataset="d") == "my cv"
