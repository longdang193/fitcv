from unittest.mock import MagicMock, patch
import datetime
import json
from fitcv_cp.worker_job import execute_pipeline_run
from fitcv_cp.models import RunStatus


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
        "shortlist_debug": {
            "vector_search_top_n": 50,
            "passed_jobs_total": 3,
            "shortlisted_jobs_total": 2,
            "candidate_query_text": "Candidate: Senior Data Engineer",
        },
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
    assert payload["shortlist_debug"]["shortlisted_jobs_total"] == 2
    assert payload["results"][0]["job_url"] == "https://example.com/1"


def test_worker_persists_structured_cv_fields_in_results_export_json():
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

    structured_cv = {"schema_version": "cv_doc_v1", "sections": {"summary": {"text": "Grounded summary."}}}
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 2,
        "cvs_generated": 1,
        "export_results": [{
            "job_url": "https://example.com/1",
            "pipeline_status": "ranked_with_cv",
            "decision_chain": {
                "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                "primary_fit": {"source": "reranker", "label": "strong"},
                "cv_generation": {"status": "accepted", "attempted": True},
                "validation": {"status": "accepted"},
            },
            "cv": {
                "version_id": "v1",
                "ranking_fit_label": "strong",
                "model_used": "gemini-2.5-pro",
                "prompt_version": "cv_prompt_v3",
                "schema_version": "cv_doc_v1",
                "structured": structured_cv,
                "markdown": "# CV",
                "created_at": "2026-03-29T12:00:00+00:00",
            },
        }],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_export.call_args.args[1])
    assert payload["results"][0]["decision_chain"]["primary_fit"]["label"] == "strong"
    assert payload["results"][0]["cv"]["ranking_fit_label"] == "strong"
    assert payload["results"][0]["cv"]["model_used"] == "gemini-2.5-pro"
    assert payload["results"][0]["cv"]["schema_version"] == "cv_doc_v1"
    assert payload["results"][0]["cv"]["structured"] == structured_cv


def test_worker_persists_cv_generation_debug_json_on_success():
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
        "cv_generation_debug_records": [
            {
                "job_url": "https://example.com/1",
                "job_title": "Data Engineer",
                "status": "accepted",
                "ranking_fit_label": "strong",
                "fit_classification": "strong",
                "decision_chain": {
                    "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                    "primary_fit": {"source": "reranker", "label": "strong"},
                    "cv_generation": {"status": "accepted", "attempted": True},
                    "validation": {"status": "accepted"},
                },
                "evidence_used": [],
                "gap_summary": {"matched": ["SQL"]},
                "structured_cv_initial": {"schema_version": "cv_doc_v1"},
                "validation_initial": {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": {"schema_version": "cv_doc_v1"},
                "markdown_final": "# CV",
                "error": None,
            }
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    mock_store_debug.assert_called_once()
    payload = json.loads(mock_store_debug.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["ranked_jobs_total"] == 2
    assert payload["debug_records_captured"] == 1
    assert payload["snapshot_complete"] is False
    assert payload["debug_records"][0]["job_url"] == "https://example.com/1"
    assert payload["debug_records"][0]["ranking_fit_label"] == "strong"
    assert payload["debug_records"][0]["decision_chain"]["primary_fit"]["source"] == "reranker"


def test_worker_persists_stage_transition_artifacts_json_on_success():
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
        "stage_transition_artifacts": {
            "schema_version": "stage_transition_artifacts_v2",
            "stages": {
                "normalize": {
                    "stage_id": "normalize",
                    "status": "completed",
                    "input_counts": {"raw_jobs": 5},
                    "output_counts": {"normalized_jobs": 4},
                    "decision_summary": {},
                    "inputs_sample": [],
                    "outputs_sample": [],
                    "dropped_or_changed_sample": [],
                },
                "ranking": {
                    "stage_id": "ranking",
                    "status": "completed",
                    "input_counts": {"ranking_inputs": 3},
                    "output_counts": {"ranked_jobs": 2},
                    "decision_summary": {},
                    "inputs_sample": [],
                    "outputs_sample": [],
                    "dropped_or_changed_sample": [],
                },
            },
        },
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts") as mock_store_stage_artifacts:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_stage_artifacts.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["snapshot_complete"] is True
    assert payload["artifacts"]["schema_version"] == "stage_transition_artifacts_v2"
    assert payload["artifacts"]["stages"]["normalize"]["input_counts"]["raw_jobs"] == 5
    assert payload["artifacts"]["stages"]["ranking"]["output_counts"]["ranked_jobs"] == 2


def test_worker_persists_settings_used_json_on_success():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({
        "pipeline": {"final_top_n": 10},
        "cv": {"generation": {"model": "gemini-2.5-flash"}},
        "prompts_runtime": {
            "enrich": {
                "extraction": {
                    "prompt_id": "enrich.extraction.v1",
                    "version": "v1",
                    "template_path": "src/fitcv/prompts/templates/enrich_extraction_v1.md",
                }
            }
        },
    })
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_settings.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["settings_schema_version"] == "settings_used_v1"
    assert payload["effective_settings"]["pipeline"]["final_top_n"] == 10
    assert payload["sources"]["config_path"] == ".env.yaml"
    assert payload["sources"]["effective_settings_snapshot_present"] is True
    assert payload["sources"]["prompts_runtime"]["enrich"]["extraction"]["prompt_id"] == "enrich.extraction.v1"


def test_worker_settings_used_persistence_failure_does_not_fail_run():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({"pipeline": {"final_top_n": 10}})
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used", side_effect=RuntimeError("settings snapshot boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_stage_transition_artifacts_persistence_failure_does_not_fail_run():
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
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "stage_transition_artifacts": {"schema_version": "stage_transition_artifacts_v2", "stages": {}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts", side_effect=RuntimeError("stage artifacts boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_mapping_suggestions_persistence_failure_appends_warning_event() -> None:
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
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "mapping_suggestions": [{"alias": "gcp", "canonical": "google cloud"}],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_mapping_suggestions", side_effect=RuntimeError("missing column")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    event_row = bq.insert_rows_json.call_args_list[-1][0][1][0]
    assert event_row["stage"] == "snapshot_persist_failed"
    assert event_row["level"] == "warning"
    assert "mapping_suggestions snapshot persistence failed" in event_row["message"]


def test_worker_debug_snapshot_persistence_failure_does_not_fail_run():
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
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "cv_generation_debug_records": [],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug", side_effect=RuntimeError("debug snapshot boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_cv_generation_debug_json_truncates_large_markdown_but_keeps_core_fields():
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

    large_markdown = "# CV\n" + ("x" * 20000)
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "cv_generation_debug_records": [
            {
                "job_url": "https://example.com/1",
                "job_title": "Data Engineer",
                "status": "accepted",
                "fit_classification": "strong",
                "evidence_used": [{"evidence_type": "experience_entry", "source_ref": "experience[0]", "name": "Data Engineer"}],
                "gap_summary": {"matched": ["SQL"]},
                "structured_cv_initial": {"schema_version": "cv_doc_v1"},
                "validation_initial": {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": {"schema_version": "cv_doc_v1"},
                "markdown_final": large_markdown,
                "error": None,
            }
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    record = payload["debug_records"][0]
    assert record["job_url"] == "https://example.com/1"
    assert record["status"] == "accepted"
    assert record["evidence_used"] == [{"evidence_type": "experience_entry", "source_ref": "experience[0]", "name": "Data Engineer"}]
    assert len(record["markdown_final"]) < len(large_markdown)


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


def test_worker_manual_staged_run_pauses_and_persists_checkpoint() -> None:
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "manual_staged"
    mock_run.next_stage = "enrich"
    mock_run.checkpoint_payload_json = None
    mock_run.started_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1",
             "paused_after_stage": "enrich",
             "next_stage": "rule_filter",
             "completed_stages": ["normalize", "enrich"],
             "checkpoint_payload": {"enriched": []},
             "stage_transition_artifacts": {"schema_version": "stage_transition_artifacts_v3", "stages": {}},
             "total_jobs": 5,
             "passed_filter": 0,
             "ranked": 0,
             "cvs_generated": 0,
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts") as mock_stage_artifacts, \
         patch("fitcv_cp.worker_job.update_run_status") as mock_status:
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args.kwargs
    assert call_kwargs["start_stage"] == "enrich"
    assert call_kwargs["stop_after_stage"] == "enrich"
    assert mock_status.call_args_list[-1].args[1] == RunStatus.AWAITING_CONTINUE
    assert mock_checkpoint.called
    assert mock_stage_artifacts.called


def test_worker_manual_resume_passes_checkpoint_payload_to_pipeline() -> None:
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "manual_staged"
    mock_run.next_stage = "ranking"
    mock_run.checkpoint_payload_json = json.dumps({
        "checkpoint_payload": {"shortlist": [{"job_url": "https://example.com/1"}]}
    })
    mock_run.started_at = datetime.datetime.now().astimezone()

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1", "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq), \
         patch("fitcv_cp.worker_job.update_run_checkpoint"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args.kwargs
    assert call_kwargs["start_stage"] == "ranking"
    assert call_kwargs["stop_after_stage"] == "ranking"
    assert call_kwargs["checkpoint_payload"] == {
        "shortlist": [{"job_url": "https://example.com/1"}]
    }


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
