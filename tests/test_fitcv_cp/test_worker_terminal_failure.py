from unittest.mock import MagicMock, patch

from fitcv_cp.models import RunStatus
from fitcv_cp.worker_job import _stage_technical_failure, execute_pipeline_run


def _summary(*, ranking_status="completed", generation_status="completed", generation_records=None):
    return {
        "run_id": "run-terminalization",
        "total_jobs": 2,
        "passed_filter": 2,
        "ranked": 2,
        "cvs_generated": 0,
        "cv_generation_debug_records": list(generation_records or []),
        "stage_transition_artifacts": {
            "schema_version": "stage_transition_artifacts_v8",
            "stages": {
                "ranking": {
                    "status": ranking_status,
                    "decision_summary": {},
                    "output_counts": {"ranked_jobs": 2},
                },
                "cv_analysis": {
                    "status": "completed",
                    "decision_summary": {},
                    "output_counts": {"analysis_failed": 0},
                },
                "cv_generation": {
                    "status": generation_status,
                    "decision_summary": {},
                    "output_counts": {
                        "accepted": 0,
                        "review_required": 0,
                        "validation_failed": 0,
                        "generation_failed": sum(
                            1 for row in generation_records or []
                            if row.get("status") == "generation_failed"
                        ),
                        "persistence_failed": 0,
                    },
                },
            },
        },
    }


def test_generation_failure_is_a_terminal_technical_failure():
    failure = _stage_technical_failure(
        _summary(generation_records=[{"status": "generation_failed"}])
    )

    assert failure == {"failure_code": "generation_failed", "stage": "cv_generation"}


def test_partial_ranking_is_a_terminal_technical_failure():
    failure = _stage_technical_failure(_summary(ranking_status="partial"))

    assert failure == {"failure_code": "ranking_partial", "stage": "ranking"}


def test_complete_generation_with_review_required_is_not_a_technical_failure():
    assert _stage_technical_failure(
        _summary(
            generation_records=[{"status": "review_required"}],
        )
    ) is None


def test_worker_persists_failure_for_partial_ranking_and_generation_failure():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "run_all"
    mock_run.checkpoint_payload_json = '{"checkpoint_payload":{"resume_token":"preserve"}}'
    summary = _summary(
        ranking_status="partial",
        generation_records=[{"status": "generation_failed"}],
    )

    with patch("fitcv_cp.worker_job.run_pipeline", return_value=summary), \
        patch("fitcv_cp.worker_job._get_bq", return_value=client), \
        patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
        patch("fitcv_cp.worker_job.update_run_status") as update_status, \
        patch("fitcv_cp.worker_job.update_run_checkpoint") as update_checkpoint, \
        patch("fitcv_cp.worker_job.update_run_progress") as update_progress:
        execute_pipeline_run(
            run_id="run-terminalization",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
        )

    failed_calls = [
        call for call in update_status.call_args_list
        if len(call.args) >= 2 and call.args[1] == RunStatus.FAILED
    ]
    assert failed_calls
    assert failed_calls[-1].kwargs["error_stage"] == "ranking"
    assert failed_calls[-1].kwargs["error_message"] == "ranking_partial"
    checkpoint = update_checkpoint.call_args.kwargs
    assert checkpoint["checkpoint_status"] == "failed"
    assert checkpoint["next_stage"] == "cv_analysis"
    assert checkpoint["last_completed_stage"] == "ranking"
    update_progress.assert_not_called()

def test_manual_checkpoint_terminalizes_partial_ranking_before_next_stage():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "manual_staged"
    mock_run.next_stage = "ranking"
    mock_run.last_completed_stage = "shortlist"
    mock_run.completed_stages = ["normalize", "enrich", "rule_filter", "shortlist"]
    mock_run.checkpoint_payload_json = '{"checkpoint_payload":{"resume_token":"preserve"}}'
    summary = _summary(ranking_status="partial")
    summary.update(
        {
            "paused_after_stage": "ranking",
            "next_stage": "cv_analysis",
            "last_completed_stage": "ranking",
            "completed_stages": [
                "normalize",
                "enrich",
                "rule_filter",
                "shortlist",
                "ranking",
            ],
        }
    )

    with patch("fitcv_cp.worker_job.run_pipeline", return_value=summary), \
        patch("fitcv_cp.worker_job._get_bq", return_value=client), \
        patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
        patch("fitcv_cp.worker_job.update_run_status") as update_status, \
        patch("fitcv_cp.worker_job.update_run_checkpoint") as update_checkpoint:
        execute_pipeline_run(
            run_id="run-manual-partial-ranking",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
        )

    failed_calls = [
        call for call in update_status.call_args_list
        if len(call.args) >= 2 and call.args[1] == RunStatus.FAILED
    ]
    assert failed_calls
    assert failed_calls[-1].kwargs["error_stage"] == "ranking"
    assert failed_calls[-1].kwargs["error_message"] == "ranking_partial"
    checkpoint = update_checkpoint.call_args.kwargs
    assert checkpoint["checkpoint_status"] == "failed"
    assert checkpoint["next_stage"] == "cv_analysis"
    assert checkpoint["last_completed_stage"] == "ranking"


def test_worker_preserves_success_for_complete_valid_zero_work():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "run_all"
    mock_run.checkpoint_payload_json = None
    summary = _summary(generation_records=[])
    summary["ranked"] = 0
    summary["stage_transition_artifacts"]["stages"]["ranking"]["output_counts"] = {"ranked_jobs": 0}
    summary["stage_transition_artifacts"]["stages"]["cv_generation"]["output_counts"] = {
        "accepted": 0,
        "review_required": 0,
        "validation_failed": 0,
        "generation_failed": 0,
        "persistence_failed": 0,
    }

    with patch("fitcv_cp.worker_job.run_pipeline", return_value=summary), \
        patch("fitcv_cp.worker_job._get_bq", return_value=client), \
        patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
        patch("fitcv_cp.worker_job.update_run_status") as update_status:
        execute_pipeline_run(
            run_id="run-zero-work",
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
        )

    assert any(
        len(call.args) >= 2 and call.args[1] == RunStatus.SUCCEEDED
        for call in update_status.call_args_list
    )
