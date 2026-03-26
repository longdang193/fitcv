from unittest.mock import MagicMock
from fitcv_cp.bq_store import insert_run, update_run_status, append_event, get_run, list_runs, get_events, list_cvs_for_run, get_cv_markdown, list_run_structured_jobs
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


# ── list_run_structured_jobs ─────────────────────────────────────────────────

def test_list_run_structured_jobs_returns_list():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    result = list_run_structured_jobs("rid", bq, project="p", dataset="d")
    assert isinstance(result, list)


def test_list_run_structured_jobs_uses_parameterized_query():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    list_run_structured_jobs("run-secret-id", bq, project="p", dataset="d")
    bq.query.assert_called_once()
    sql_arg = bq.query.call_args[0][0]
    assert "run-secret-id" not in sql_arg, "SQL must use query parameters, not string interpolation"


def test_list_run_structured_jobs_returns_rows_as_dicts():
    bq = MagicMock()

    class FakeRow:
        def items(self):
            return [
                ("run_id", "run-abc"),
                ("job_url", "https://example.com/1"),
                ("title", "Data Engineer"),
                ("location_type", "remote"),
                ("seniority", "senior"),
                ("job_family", "data_engineering"),
                ("domain", "fintech"),
                ("required_skills", ["SQL", "Python"]),
            ]

    bq.query.return_value.result.return_value = iter([FakeRow()])
    result = list_run_structured_jobs("run-abc", bq, project="p", dataset="d")
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, dict)
    assert row["run_id"] == "run-abc"
    assert row["job_url"] == "https://example.com/1"
    assert row["location_type"] == "remote"
    assert row["required_skills"] == ["SQL", "Python"]


def test_list_run_structured_jobs_queries_correct_table():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    list_run_structured_jobs("run-abc", bq, project="myproject", dataset="myds")
    sql_arg = bq.query.call_args[0][0]
    assert "run_structured_jobs" in sql_arg, "SQL must reference run_structured_jobs table"


# ── Task 1: run-scoped input metadata fields ──────────────────────────────────

def test_insert_run_includes_input_metadata_params() -> None:
    """insert_run sends all 4 new input metadata fields as query parameters."""
    bq = MagicMock()
    run = _make_run()
    run.jobs_input_source = "paste"
    run.jobs_input_json = '[{"title": "DE"}]'
    run.candidate_profile_source = "upload"
    run.candidate_profile_json = '{"skills": []}'
    insert_run(run, bq, project="p", dataset="d")
    call_args = bq.query.call_args
    job_config = call_args[1]["job_config"]
    param_names = {p.name for p in job_config.query_parameters}
    assert "jobs_input_source" in param_names
    assert "jobs_input_json" in param_names
    assert "candidate_profile_source" in param_names
    assert "candidate_profile_json" in param_names


def test_insert_run_input_metadata_none_values_are_included() -> None:
    """insert_run includes None input metadata params (not silently omitted)."""
    bq = MagicMock()
    run = _make_run()  # all 4 new fields default to None
    insert_run(run, bq, project="p", dataset="d")
    call_args = bq.query.call_args
    job_config = call_args[1]["job_config"]
    param_names = {p.name for p in job_config.query_parameters}
    assert "jobs_input_source" in param_names
    assert "candidate_profile_json" in param_names
    # verify value is None (not missing)
    params_by_name = {p.name: p for p in job_config.query_parameters}
    assert params_by_name["jobs_input_source"].value is None


def test_row_to_run_maps_input_metadata_fields() -> None:
    """_row_to_run correctly maps all 4 new fields from a BQ row."""
    from fitcv_cp.bq_store import _row_to_run
    import datetime
    row = {
        "run_id": "r1",
        "status": "queued",
        "triggered_by": "admin",
        "trigger_source": "ui",
        "jobs_path": "data/jobs.json",
        "config_path": ".env.yaml",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "jobs_input_source": "paste",
        "jobs_input_json": '[{"title": "Analyst"}]',
        "candidate_profile_source": "upload",
        "candidate_profile_json": '{"skills": []}',
    }
    result = _row_to_run(row)
    assert result.jobs_input_source == "paste"
    assert result.jobs_input_json == '[{"title": "Analyst"}]'
    assert result.candidate_profile_source == "upload"
    assert result.candidate_profile_json == '{"skills": []}'


def test_row_to_run_handles_missing_input_metadata_fields() -> None:
    """_row_to_run returns None for new fields absent from old BQ rows."""
    from fitcv_cp.bq_store import _row_to_run
    import datetime
    row = {
        "run_id": "r2",
        "status": "succeeded",
        "jobs_path": "data/jobs.json",
        "config_path": ".env.yaml",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        # no input metadata fields — simulates old row
    }
    result = _row_to_run(row)
    assert result.jobs_input_source is None
    assert result.jobs_input_json is None
    assert result.candidate_profile_source is None
    assert result.candidate_profile_json is None
