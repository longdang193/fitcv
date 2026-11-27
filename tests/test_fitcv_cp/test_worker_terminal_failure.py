from unittest.mock import MagicMock, patch

from fitcv.ranking_contract import build_ranking_cv_handoff
from fitcv_cp.models import RunStatus
from fitcv_cp.worker_job import _stage_technical_failure, execute_pipeline_run


def _valid_handoff_items():
    return [
        {
            **build_ranking_cv_handoff(
                {
                    "canonical_job_identity": f"job-{index}",
                    "job_qualifiers": {},
                    "baseline_rank": index,
                    "ai_score": 0.8,
                    "score_status": "valid",
                    "disposition": "rankable",
                    "retry_eligible": False,
                    "candidate_profile_revision": "profile-r1",
                    "ranking_order_version": "ai-only-v1",
                    "ranking_policy_version": "ranking-v2",
                    "source_provenance": {"source": "test"},
                },
                candidate_profile_revision="profile-r1",
                ranking_order_version="ai-only-v1",
                ranking_policy_version="ranking-v2",
                source_provenance={"source": "test"},
            ),
            "handoff_status": "complete",
        }
        for index in (1, 2)
    ]

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
                    "ranking_cv_handoff": {
                        "status": "complete",
                        "items": _valid_handoff_items(),
                    },
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


def test_partial_ranking_with_usable_rows_is_not_a_terminal_technical_failure():
    failure = _stage_technical_failure(_summary(ranking_status="partial"))

    assert failure is None


def test_partial_ranking_without_usable_rows_is_a_terminal_technical_failure():
    summary = _summary(ranking_status="partial")
    summary["stage_transition_artifacts"]["stages"]["ranking"]["output_counts"]["ranked_jobs"] = 0

    assert _stage_technical_failure(summary) == {
        "failure_code": "ranking_partial",
        "stage": "ranking",
    }

def test_partial_ranking_with_persistence_failure_is_terminal():
    summary = _summary(ranking_status="partial")
    summary["stage_transition_artifacts"]["stages"]["ranking"]["output_counts"]["persistence_failed"] = 1

    assert _stage_technical_failure(summary) == {
        "failure_code": "persistence_failed",
        "stage": "ranking",
    }

def test_partial_ranking_with_missing_handoff_fails_closed():
    summary = _summary(ranking_status="partial")
    summary["stage_transition_artifacts"]["stages"]["ranking"].pop("ranking_cv_handoff")

    assert _stage_technical_failure(summary) == {
        "failure_code": "ranking_handoff_incomplete",
        "stage": "ranking",
    }


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
    assert failed_calls[-1].kwargs["error_stage"] == "cv_generation"
    assert failed_calls[-1].kwargs["error_message"] == "generation_failed"
    checkpoint = update_checkpoint.call_args.kwargs
    assert checkpoint["checkpoint_status"] == "failed"
    assert checkpoint["next_stage"] == "cv_generation"
    assert checkpoint["last_completed_stage"] == "cv_analysis"
    assert checkpoint["completed_stages"] == [
        "normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis"
    ]
    update_progress.assert_not_called()

def test_manual_checkpoint_continues_after_partial_ranking_with_usable_rows():
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

    awaiting_calls = [
        call for call in update_status.call_args_list
        if len(call.args) >= 2 and call.args[1] == RunStatus.AWAITING_CONTINUE
    ]
    assert awaiting_calls
    checkpoint = update_checkpoint.call_args.kwargs
    assert checkpoint["checkpoint_status"] == "awaiting_continue"
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
