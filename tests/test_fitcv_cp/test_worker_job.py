from unittest.mock import MagicMock, patch
import json
from fitcv_cp.worker_job import execute_pipeline_run


def test_worker_marks_succeeded_on_success():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1", "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    assert bq.query.call_count >= 2  # running + succeeded


def test_worker_persists_results_export_json_on_success():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 2,
        "cvs_generated": 1,
        "export_results": [{"job_url": "https://example.com/1", "pipeline_status": "ranked_with_cv"}],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    mock_store_export.assert_called_once()
    stored_json = mock_store_export.call_args.args[1]
    payload = json.loads(stored_json)
    assert payload["run_id"] == "r1"
    assert payload["summary"]["ranked"] == 2
    assert payload["results"][0]["job_url"] == "https://example.com/1"


def test_worker_marks_failed_on_exception():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    # Both the status update AND the error event insert must have been called
    bq.query.assert_called()  # update to failed
    bq.insert_rows_json.assert_called()  # error event appended


def test_worker_error_event_has_correct_level():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    event_row = bq.insert_rows_json.call_args_list[-1][0][1][0]
    assert event_row["level"] == "error"
    assert event_row["stage"] == "pipeline_failed"


def test_worker_uses_effective_settings_not_bq_settings():
    """Worker must use the stored effective_settings_json, not re-read BQ settings."""
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    effective = {"pipeline": {"final_top_n": 5}, "gcp_project": "p",
                 "bigquery_dataset": "d", "service_account_key": "k"}
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps(effective)
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is not None
    assert call_kwargs["config"]["pipeline"]["final_top_n"] == 5


def test_worker_falls_back_to_config_path_if_no_snapshot():
    """If effective_settings_json is None, worker falls back to config_path."""
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is None


def test_worker_passes_control_plane_run_id_to_pipeline():
    """Worker must pass the admin run_id into the pipeline for downstream joins."""
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1", "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs["run_id"] == "r1"


# ── cooperative cancellation ─────────────────────────────────────────────────

def test_worker_marks_cancelled_when_cancel_already_requested():
    """Worker should check cancel_requested_at after RUNNING update and exit early."""
    import datetime
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.cancel_requested_at = datetime.datetime.now(datetime.timezone.utc)

    status_updates = []

    def capture_query(sql, job_config=None):
        m = MagicMock()
        m.result.return_value = iter([])
        return m

    bq.query.side_effect = capture_query

    with patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline") as mock_pipeline, \
         patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")
        status_updates = [c.args[1] for c in mock_update.call_args_list]

    # pipeline should NOT have been called
    mock_pipeline.assert_not_called()
    # Should have marked RUNNING then CANCELLED
    from fitcv_cp.models import RunStatus
    assert RunStatus.RUNNING in status_updates
    assert RunStatus.CANCELLED in status_updates


def test_worker_cancellation_event_appended_on_early_exit():
    """Worker must append a run_cancelled event when exiting early due to cancel."""
    import datetime
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    bq.insert_rows_json.return_value = []

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.cancel_requested_at = datetime.datetime.now(datetime.timezone.utc)

    with patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline"), \
         patch("fitcv_cp.worker_job.update_run_status"), \
         patch("fitcv_cp.worker_job.append_event") as mock_append:
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    stages = [c.args[0].stage for c in mock_append.call_args_list]
    assert "run_cancelled" in stages


def test_worker_pipeline_cancelled_exception_marks_cancelled():
    """PipelineCancelled raised during execution should produce cancelled status."""
    from fitcv.pipeline import PipelineCancelled
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", side_effect=PipelineCancelled("stopped")), \
         patch("fitcv_cp.worker_job.update_run_status") as mock_update, \
         patch("fitcv_cp.worker_job.append_event"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    from fitcv_cp.models import RunStatus
    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status == RunStatus.CANCELLED
