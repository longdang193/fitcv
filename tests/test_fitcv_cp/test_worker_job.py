from unittest.mock import MagicMock, patch
import json
from fitcv_cp.worker_job import execute_pipeline_run


def test_worker_marks_succeeded_on_success():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1", "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=MagicMock(effective_settings_json=None)):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    assert bq.query.call_count >= 2  # running + succeeded


def test_worker_marks_failed_on_exception():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=MagicMock(effective_settings_json=None)):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    # Both the status update AND the error event insert must have been called
    bq.query.assert_called()  # update to failed
    bq.insert_rows_json.assert_called()  # error event appended


def test_worker_error_event_has_correct_level():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.get_run", return_value=MagicMock(effective_settings_json=None)):
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

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is None

