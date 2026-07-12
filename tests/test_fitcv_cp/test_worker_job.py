"""
@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - worker job behavior in the control plane
excludes:
  - live queue workers
tags:
  - fast
  - ci-safe
"""

from unittest.mock import MagicMock, patch
import datetime
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from fitcv_cp.backend_runtime import BackendRuntime, set_backend_runtime
from fitcv_cp.worker_job import execute_pipeline_run
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
import pytest

@pytest.fixture(autouse=True)
def _force_sqlite_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    set_backend_runtime(None)
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", "data/fitcv_cp.sqlite3")
    yield
    set_backend_runtime(None)

def test_execute_cv_regenerate_once_updates_target_record_and_emits_success() -> None:
    from fitcv_cp.worker_job import execute_cv_regenerate_once

    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="run-regen-1",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=now,
        cv_generation_debug_json=json.dumps(
            {
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "status": "review_required",
                        "markdown_full": "# Draft 1",
                    },
                    {
                        "job_url": "https://example.com/job-2",
                        "status": "review_required",
                        "markdown_full": "# Draft 2",
                    },
                ]
            },
            ensure_ascii=False,
        ),
    )
    with patch("fitcv_cp.worker_job.get_run", return_value=run), \
         patch("fitcv_cp.worker_job._get_bq", return_value=MagicMock()), \
         patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_update, \
         patch("fitcv_cp.worker_job.append_event") as mock_append:
        execute_cv_regenerate_once(
            run_id="run-regen-1",
            job_url="https://example.com/job-1",
            actor="operator",
            note="retry",
        )

    saved_payload = json.loads(mock_update.call_args.args[1])
    target = next(
        row for row in saved_payload["cv_generation_debug_records"]
        if row.get("job_url") == "https://example.com/job-1"
    )
    untouched = next(
        row for row in saved_payload["cv_generation_debug_records"]
        if row.get("job_url") == "https://example.com/job-2"
    )
    assert target["last_regenerated_at"]
    assert target["regenerated_draft_fingerprint"]
    assert target["regeneration_attempt_count"] == 1
    assert untouched.get("last_regenerated_at") is None
    stages = [call.args[0].stage for call in mock_append.call_args_list]
    assert stages == ["cv_regenerate_once_started", "cv_regenerate_once_succeeded"]

def test_execute_cv_regenerate_once_emits_failed_event_for_missing_record() -> None:
    from fitcv_cp.worker_job import execute_cv_regenerate_once

    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="run-regen-2",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=now,
        cv_generation_debug_json=json.dumps({"cv_generation_debug_records": []}, ensure_ascii=False),
    )
    with patch("fitcv_cp.worker_job.get_run", return_value=run), \
         patch("fitcv_cp.worker_job._get_bq", return_value=MagicMock()), \
         patch("fitcv_cp.worker_job.append_event") as mock_append:
        with pytest.raises(ValueError):
            execute_cv_regenerate_once(
                run_id="run-regen-2",
                job_url="https://example.com/job-404",
                actor="operator",
                note=None,
            )
    stages = [call.args[0].stage for call in mock_append.call_args_list]
    assert stages == ["cv_regenerate_once_started", "cv_regenerate_once_failed"]


def test_execute_cv_regenerate_once_emits_failed_event_for_invalid_json_payload() -> None:
    from fitcv_cp.worker_job import execute_cv_regenerate_once

    now = datetime.datetime.now(datetime.timezone.utc)
    run = PipelineRun(
        run_id="run-regen-3",
        status=RunStatus.AWAITING_CONTINUE,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=now,
        cv_generation_debug_json="{invalid-json",
    )
    with (
        patch("fitcv_cp.worker_job.get_run", return_value=run),
        patch("fitcv_cp.worker_job._get_bq", return_value=MagicMock()),
        patch("fitcv_cp.worker_job.append_event") as mock_append,
    ):
        with pytest.raises(ValueError):
            execute_cv_regenerate_once(
                run_id="run-regen-3",
                job_url="https://example.com/job-1",
                actor="operator",
                note=None,
            )
    stages = [call.args[0].stage for call in mock_append.call_args_list]
    assert stages == ["cv_regenerate_once_started", "cv_regenerate_once_failed"]


def test_worker_synonym_policy_defaults_when_effective_settings_json_invalid() -> None:
    from fitcv_cp.worker_job import _auto_accept_ai_action_enabled_from_run_record

    run_record = MagicMock(effective_settings_json="{invalid-json")
    assert _auto_accept_ai_action_enabled_from_run_record(run_record) is True


def test_worker_marks_succeeded_on_success():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1", "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update_status:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    statuses = [call.args[1].value for call in mock_update_status.call_args_list if len(call.args) >= 2]
    assert "running" in statuses and "succeeded" in statuses

def test_worker_persists_terminal_artifact_mirror_for_succeeded_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    now = datetime.datetime(2026, 5, 17, 16, 31, 28, tzinfo=datetime.timezone.utc)
    run_record = PipelineRun(
        run_id="r-mirror-1",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=now,
        started_at=now,
        finished_at=now,
        results_export_json=json.dumps({"results": [{"job_url": "https://example.com/1"}]}, ensure_ascii=False),
        cv_generation_debug_json=json.dumps({"debug_records": [], "agentic_live_trace": {"trace_status": "completed"}}, ensure_ascii=False),
        stage_transition_artifacts_json=json.dumps({"status": "succeeded", "artifacts": {}}, ensure_ascii=False),
        settings_used_json=json.dumps({"effective_settings": {}}, ensure_ascii=False),
        mapping_suggestions_json=json.dumps({"suggestions": []}, ensure_ascii=False),
        synonym_proposals_json=json.dumps({"proposals": []}, ensure_ascii=False),
        effective_settings_json=json.dumps({}, ensure_ascii=False),
    )
    run_record.cancel_requested_at = None
    events = [
        RunEvent(
            run_id="r-mirror-1",
            event_id="e1",
            stage="pipeline_complete",
            level="info",
            message="done",
            created_at=now,
            payload_json=None,
        )
    ]
    def _run_once() -> None:
        with patch("fitcv_cp.worker_job.run_pipeline", return_value={"run_id": "r-mirror-1", "total_jobs": 1, "passed_filter": 1, "ranked": 1, "cvs_generated": 1}), \
            patch("fitcv_cp.worker_job.resolve_backend_runtime", return_value=BackendRuntime(backend_type="sqlite",  sqlite_path="data/fitcv_cp.sqlite3")), \
            patch("fitcv_cp.worker_job._get_bq", return_value=client), \
            patch("fitcv_cp.worker_job.get_run", return_value=run_record), \
            patch("fitcv_cp.run_artifact_mirror.get_run", return_value=run_record), \
            patch("fitcv_cp.run_artifact_mirror.get_events", return_value=events), \
            patch("fitcv_cp.worker_job.update_run_results_export"), \
            patch("fitcv_cp.worker_job.update_run_cv_generation_debug"), \
            patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts"), \
            patch("fitcv_cp.worker_job.update_run_settings_used"), \
            patch("fitcv_cp.worker_job.update_run_mapping_suggestions"), \
            patch("fitcv_cp.worker_job.update_run_synonym_proposals"):
            execute_pipeline_run(run_id="r-mirror-1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    _run_once()

    mirror_dir = tmp_path / "artifacts" / "live_run_r-mirror-1"
    assert mirror_dir.is_dir()
    assert (mirror_dir / "run.json").is_file()
    assert (mirror_dir / "events.json").is_file()
    assert (mirror_dir / "export.json").is_file()
    assert (mirror_dir / "cv-debug.json").is_file()
    assert (mirror_dir / "stage-artifacts.json").is_file()

    # Idempotent overwrite check: running again should keep mirror writable and valid.
    _run_once()
    payload = json.loads((mirror_dir / "run.json").read_text(encoding="utf-8"))
    assert payload["run_id"] == "r-mirror-1"


def test_worker_uses_local_runtime_without_remote_client_bootstrap():
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch(
        "fitcv_cp.worker_job.resolve_backend_runtime",
        return_value=BackendRuntime(
            backend_type="sqlite",
            project = "local",
            dataset = "fitcv",
            sqlite_path="data/fitcv_cp.sqlite3",
        ),
    ), patch(
        "fitcv_cp.worker_job._get_bq",
        side_effect=RuntimeError("should not build remote client in sqlite mode"),
    ), patch(
        "fitcv_cp.worker_job.get_run",
        return_value=mock_run,
    ), patch(
        "fitcv_cp.worker_job.run_pipeline",
        return_value={"run_id": "r1", "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0},
    ):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")


def test_worker_results_export_keeps_ai_plane_payload_equivalent_across_backends() -> None:
    """@proves cv_system.backend-symmetry-ai-plane-equivalence"""
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    ai_plane_result = {
        "run_id": "r1",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "export_results": [
            {
                "job_url": "https://example.com/1",
                "pipeline_status": "ranked_with_cv",
                "deterministic_outcome": "accepted",
                "source_stage": "cv_generation",
                "stage_owned_subreason": "accepted",
                "cv": {"version_id": "v1", "ranking_fit_label": "strong"},
            }
        ],
        "cv_analysis_trace": {
            "trace_schema_version": "agentic_step_trace_run_v1",
            "late_stage_mode": {"late_stage_mode": "agentic"},
            "records": [{"record_id": "https://example.com/1", "status": "ready_for_generation"}],
        },
        "agentic_live_trace": {
            "trace_schema_version": "agentic_step_trace_run_v1",
            "late_stage_mode": {"late_stage_mode": "agentic"},
            "records": [{"record_id": "https://example.com/1", "status": "accepted"}],
        },
    }

    def _capture_results_export(backend_type: str) -> dict:
        client = MagicMock()
        client.query.return_value.result.return_value = iter([])
        with patch(
            "fitcv_cp.worker_job.resolve_backend_runtime",
            return_value=BackendRuntime(
                backend_type=backend_type,
                project = "local",
                dataset = "fitcv",
                sqlite_path="data/fitcv_cp.sqlite3" if backend_type == "sqlite" else None,
            ),
        ), patch("fitcv_cp.worker_job._get_bq", return_value=client), patch(
            "fitcv_cp.worker_job.get_run",
            return_value=mock_run,
        ), patch("fitcv_cp.worker_job.run_pipeline", return_value=ai_plane_result), patch(
            "fitcv_cp.worker_job.update_run_results_export"
        ) as mock_store_export:
            execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")
        return json.loads(mock_store_export.call_args.args[1])

    legacy_payload = _capture_results_export("legacy")
    sqlite_payload = _capture_results_export("sqlite")

    assert legacy_payload["data_plane"]["state_backend"] == sqlite_payload["data_plane"]["state_backend"]
    # Allowed backend-only diff set: persistence substrate metadata.
    legacy_normalized = deepcopy(legacy_payload)
    sqlite_normalized = deepcopy(sqlite_payload)
    legacy_normalized["data_plane"]["state_backend"] = "<backend>"
    sqlite_normalized["data_plane"]["state_backend"] = "<backend>"
    legacy_normalized["data_plane"]["artifact_backend"] = "<artifact_backend>"
    sqlite_normalized["data_plane"]["artifact_backend"] = "<artifact_backend>"
    legacy_normalized["finished_at"] = "<finished_at>"
    sqlite_normalized["finished_at"] = "<finished_at>"

    assert legacy_normalized == sqlite_normalized




def test_worker_persists_results_export_json_on_success():
    """@proves pipeline_performance.results-json-now-keeps-only-compact-job-ledger-fields-instead-of-repeating-full-job-snapshots-heavy-score-explanation-internals-and-full-cv-bodies-already-represented-elsewhere
    @proves trigger_run_management.run-results-export
    @proves inspection_debugging.results-ledger-inspection
    """
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    mock_store_export.assert_called_once()
    stored_json = mock_store_export.call_args.args[1]
    payload = json.loads(stored_json)
    assert payload["run_id"] == "r1"
    assert payload["results_schema_version"] == "results_job_ledger_v3"
    assert payload["schema_version"] == "results_job_ledger_v3"
    assert payload["run_mode"] == "run_all"
    assert payload["run_mode_label"] == "Run All"
    assert payload["data_plane"]["runtime_mode"] == "full"
    assert payload["data_plane"]["state_backend"] == "sqlite"
    assert payload["replay_context"]["replay_mode"] == "strict"
    assert payload["replay_context"]["replay_source_run_id"] == "r1"
    assert payload["replay_context"]["policy_registry_version"] == "policy_registry.v1"
    assert payload["summary"]["ranked"] == 2
    assert payload["late_stage_mode"]["late_stage_mode"] == "agentic"
    assert payload["late_stage_mode"]["agentic_late_stage_enabled"] is True
    assert payload["late_stage_mode"]["agentic_status"] == "completed"
    assert "stage_quality_metrics" not in payload
    assert "late_stage_reuse_metrics" not in payload
    assert "shortlist_debug" not in payload
    assert payload["results"][0]["job_url"] == "https://example.com/1"

def test_results_export_payload_encoding_is_deterministic():
    from fitcv_cp.worker_job import _build_results_export_payload

    run_record = MagicMock()
    run_record.triggered_by = "admin"
    run_record.run_mode = "run_all"
    run_record.created_at = None
    run_record.started_at = None
    run_record.finished_at = None
    run_record.jobs_path = "data/sample_jobs.json"
    run_record.jobs_input_source = "upload"
    run_record.candidate_profile_source = "default_config"

    finished_at = datetime.datetime(2026, 5, 24, tzinfo=datetime.timezone.utc)
    replay_context = {
        "replay_mode": "strict",
        "replay_source_run_id": "r1",
        "policy_registry_version": "policy_registry.v1",
    }
    summary = {
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
    }
    export_results = [{"job_url": "https://example.com/1", "pipeline_status": "ranked"}]

    payload_a = _build_results_export_payload(
        run_id="r1",
        run_record=run_record,
        effective_config={},
        summary=summary,
        export_results=export_results,
        finished_at=finished_at,
        replay_context=replay_context,
    )
    payload_b = _build_results_export_payload(
        run_id="r1",
        run_record=run_record,
        effective_config={},
        summary=summary,
        export_results=export_results,
        finished_at=finished_at,
        replay_context=replay_context,
    )
    assert payload_a == payload_b
    assert json.loads(payload_a)["run_id"] == "r1"


def test_worker_persists_compact_cv_fields_in_results_export_json():
    """@proves trigger_run_management.run-owned-artifact-exports"""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "manual_staged"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 2,
        "cvs_generated": 1,
        "export_results": [{
            "job_url": "https://example.com/1",
            "pipeline_status": "ranked_with_cv",
            "deterministic_outcome": "accepted",
            "stage_owned_subreason": "accepted",
            "source_stage": "cv_generation",
            "decision_chain": {
                "shortlist": {"status": "returned_by_vector_search", "advanced_to_scoring": True},
                "primary_fit": {"source": "reranker", "label": "strong"},
                "cv_generation": {"status": "accepted", "attempted": True},
                "validation": {"status": "accepted"},
            },
                "cv": {
                    "version_id": "v1",
                    "ranking_fit_label": "strong",
                    "model_used": "cx/gpt-5.5",
                    "schema_version": "cv_doc_v1",
                    "created_at": "2026-03-29T12:00:00+00:00",
                },
            }],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_export.call_args.args[1])
    assert payload["results"][0]["deterministic_outcome"] == "accepted"
    assert payload["results"][0]["stage_owned_subreason"] == "accepted"
    assert payload["results"][0]["source_stage"] == "cv_generation"
    assert payload["results"][0]["decision_chain"]["primary_fit"]["label"] == "strong"
    assert payload["results"][0]["cv"]["ranking_fit_label"] == "strong"
    assert payload["results"][0]["cv"]["model_used"] == "cx/gpt-5.5"
    assert payload["results"][0]["cv"]["schema_version"] == "cv_doc_v1"
    assert "structured" not in payload["results"][0]["cv"]
    assert "markdown" not in payload["results"][0]["cv"]


def test_worker_excludes_stage_quality_metrics_from_results_export_json():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 2,
        "cvs_generated": 1,
        "stage_quality_metrics": {
            "shortlist": {
                "backfill_rate": 0.0,
                "backfilled_jobs_total": 0,
                "scoring_shortlisted_jobs_total": 3,
            },
            "cv_generation": {
                "accepted_rate": 0.5,
                "accepted": 1,
                "total_attempted": 2,
            },
        },
        "export_results": [{"job_url": "https://example.com/1", "pipeline_status": "ranked_with_cv"}],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_export.call_args.args[1])
    assert "stage_quality_metrics" not in payload


def test_worker_moves_late_stage_reuse_snapshots_under_diagnostic_support():
    """@proves inspection_debugging.reuse-diagnostics"""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
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
        "late_stage_reuse_metrics": {
            "ranking": {
                "reused_ai_scores": 1,
                "fresh_ai_scores": 1,
                "total_ai_scores": 2,
                "reuse_rate": 0.5,
            },
            "cv_analysis": {
                "analysis_rows_executed": 1,
                "reused_analysis_rows": 1,
                "fresh_analysis_rows": 0,
                "blocked_before_analysis_rows": 0,
                "analysis_reuse_rate": 1.0,
            },
        },
        "late_stage_reuse_snapshots": {
            "schema_version": "late_stage_reuse_v1",
            "ranking_ai_scores": [{"job_url": "https://example.com/1"}],
            "cv_analysis_records": [{"job_url": "https://example.com/1"}],
        },
        "export_results": [{"job_url": "https://example.com/1", "pipeline_status": "ranked_with_cv"}],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.list_runs", return_value=[]), \
        patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_export.call_args.args[1])
    assert "late_stage_reuse_metrics" not in payload
    assert payload["diagnostic_support"]["late_stage_reuse_snapshots"]["schema_version"] == "late_stage_reuse_v1"


def test_worker_passes_collected_late_stage_reuse_snapshots_to_run_pipeline():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    prior_run = MagicMock()
    prior_run.run_id = "prior-run"
    prior_run.status = RunStatus.SUCCEEDED
    prior_run.results_export_json = json.dumps({
        "diagnostic_support": {
            "late_stage_reuse_snapshots": {
                "schema_version": "late_stage_reuse_v1",
                "ranking_ai_scores": [
                    {"job_url": "https://example.com/1", "ai_score_input_fingerprint": "fp-1", "ai_score_row": {"job_url": "https://example.com/1"}}
                ],
                "cv_analysis_records": [
                    {"job_url": "https://example.com/1", "analysis_input_fingerprint": "afp-1", "analysis_record": {"job_url": "https://example.com/1"}}
                ],
            }
        }
    })

    with patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.list_runs", return_value=[prior_run]), \
       patch("fitcv_cp.worker_job.run_pipeline", return_value={
           "run_id": "r1",
           "total_jobs": 0,
           "passed_filter": 0,
           "ranked": 0,
           "cvs_generated": 0,
       }) as mock_run_pipeline:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    passed_snapshots = mock_run_pipeline.call_args.kwargs["reuse_snapshots"]
    assert passed_snapshots["ranking_ai_scores"][0]["ai_score_input_fingerprint"] == "fp-1"
    assert passed_snapshots["cv_analysis_records"][0]["analysis_input_fingerprint"] == "afp-1"

def test_worker_reporter_event_includes_telemetry_degraded_payload() -> None:
    client = MagicMock()
    client.insert_rows_json.return_value = []
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.checkpoint_payload_json = None

    def _run_pipeline_stub(*args, **kwargs):
        reporter = kwargs.get("reporter")
        if reporter is not None:
            reporter.emit("pipeline_start", "info", "Run started")
        return {
            "run_id": "r1",
            "total_jobs": 0,
            "passed_filter": 0,
            "ranked": 0,
            "cvs_generated": 0,
        }

    with patch("fitcv_cp.worker_job._get_bq", return_value=client),        patch("fitcv_cp.worker_job.get_run", return_value=mock_run),        patch("fitcv_cp.worker_job.list_runs", return_value=[]),        patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock,        patch("fitcv_cp.worker_job.run_pipeline", side_effect=_run_pipeline_stub):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    events = [call.args[0] for call in append_mock.call_args_list if call.args]
    matching = [ev for ev in events if str(getattr(ev, "stage", "")) == "pipeline_start"]
    assert matching, "expected pipeline_start event row"
    payload = json.loads(str(getattr(matching[0], "payload_json", "") or "{}"))
    telemetry_export = dict(payload.get("telemetry_export") or {})
    assert telemetry_export.get("status") in {"degraded", "disabled"}

def test_worker_reporter_event_includes_langfuse_rich_contract_disabled_by_default() -> None:
    client = MagicMock()
    client.insert_rows_json.return_value = []
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.checkpoint_payload_json = None

    def _run_pipeline_stub(*args, **kwargs):
        reporter = kwargs.get("reporter")
        if reporter is not None:
            reporter.emit("pipeline_start", "info", "Run started")
        return {
            "run_id": "r1",
            "total_jobs": 0,
            "passed_filter": 0,
            "ranked": 0,
            "cvs_generated": 0,
        }

    with patch("fitcv_cp.worker_job._get_bq", return_value=client),        patch("fitcv_cp.worker_job.get_run", return_value=mock_run),        patch("fitcv_cp.worker_job.list_runs", return_value=[]),        patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock,        patch("fitcv_cp.worker_job.run_pipeline", side_effect=_run_pipeline_stub):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    events = [call.args[0] for call in append_mock.call_args_list if call.args]
    matching = [ev for ev in events if str(getattr(ev, "stage", "")) == "pipeline_start"]
    assert matching
    payload = json.loads(str(getattr(matching[0], "payload_json", "") or "{}"))
    rich = dict(payload.get("langfuse_rich_io") or {})
    native = dict(payload.get("langfuse_rich_io_native") or {})
    assert rich.get("status") == "disabled"
    assert native.get("status") == "disabled"

def test_worker_persists_cv_generation_debug_json_on_success():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
        "cv_analysis_trace": {
            "run_id": "r1",
            "trace_schema_version": "agentic_step_trace_run_v1",
            "trace_family": "agentic_step_trace",
            "step_id": "cv_analysis",
            "late_stage_mode": {
                "late_stage_mode": "agentic",
                "agentic_late_stage_enabled": True,
                "mode_source": "cv.agentic_late_stage.unified_runtime",
                "agentic_status": "completed",
            },
            "trace_status": "completed",
            "trace_summary": {
                "records_total": 1,
                "present_records": 1,
                "attempted_analysis_jobs_total": 1,
            },
            "records": [
                {
                    "record_id": "https://example.com/1",
                    "scope_type": "job",
                    "scope_key": "https://example.com/1",
                    "status": "ready_for_generation",
                    "attempts": [{"attempt_index": 1, "attempt_type": "analysis"}],
                }
            ],
            "degradation": {},
        },
        "agentic_live_trace": {
            "run_id": "r1",
            "trace_schema_version": "agentic_step_trace_run_v1",
            "trace_family": "agentic_step_trace",
            "step_id": "cv_generation",
            "late_stage_mode": {
                "late_stage_mode": "agentic",
                "agentic_late_stage_enabled": True,
                "mode_source": "cv.agentic_late_stage.unified_runtime",
                "agentic_status": "completed",
            },
            "trace_status": "completed",
            "trace_summary": {
                "records_total": 1,
                "present_records": 1,
                "attempted_generation_jobs_total": 1,
            },
            "records": [
                {
                    "record_id": "https://example.com/1",
                    "scope_type": "job",
                    "scope_key": "https://example.com/1",
                    "status": "accepted",
                    "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
                }
            ],
            "degradation": {},
        },
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    mock_store_debug.assert_called_once()
    payload = json.loads(mock_store_debug.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["debug_schema_version"] == "cv_generation_debug_v3"
    assert payload["schema_version"] == "cv_generation_debug_v3"
    assert payload["run_mode"] == "run_all"
    assert payload["run_mode_label"] == "Run All"
    assert payload["ranked_jobs_total"] == 2
    assert payload["debug_records_captured"] == 1
    assert payload["snapshot_complete"] is False
    assert payload["cv_analysis_trace"]["trace_family"] == "agentic_step_trace"
    assert payload["cv_analysis_trace"]["step_id"] == "cv_analysis"
    assert payload["cv_analysis_trace"]["records"][0]["status"] == "ready_for_generation"
    assert payload["agentic_live_trace"]["trace_status"] == "completed"
    assert payload["agentic_live_trace"]["trace_family"] == "agentic_step_trace"
    assert payload["agentic_live_trace"]["step_id"] == "cv_generation"
    assert payload["agentic_live_trace"]["records"][0]["attempts"][0]["provider_status"] == "accepted"
    assert payload["debug_records"][0]["job_url"] == "https://example.com/1"
    assert payload["debug_records"][0]["ranking_fit_label"] == "strong"
    assert payload["debug_records"][0]["reranker_fit_label"] == "strong"
    assert payload["debug_records"][0]["decision_chain"]["primary_fit"]["source"] == "reranker"


def test_worker_persists_cv_generation_debug_coverage_accounting():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
                "status": "accepted",
                "ranking_fit_label": "strong",
                "fit_classification": "strong",
                "decision_chain": {},
                "evidence_used": [],
                "gap_summary": {"matched": ["SQL"]},
                "structured_cv_initial": {"schema_version": "cv_doc_v1"},
                "validation_initial": {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": {"schema_version": "cv_doc_v1"},
                "markdown_final": "# CV",
                "error": None,
            },
            {
                "job_url": "",
                "status": "skipped_fit_gate",
                "ranking_fit_label": "skip",
                "fit_classification": "skip",
                "decision_chain": {},
                "evidence_used": [],
                "gap_summary": {"matched": [], "missing": ["SQL"]},
                "structured_cv_initial": None,
                "validation_initial": None,
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": None,
                "markdown_final": None,
                "error": None,
            },
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    assert payload["attempted_generation_jobs_total"] == 1
    assert payload["non_attempted_ranked_jobs_total"] == 1
    assert payload["omission_reason_counts"] == {"skipped_fit_gate": 1}
    assert payload["snapshot_complete"] is True

def test_worker_persists_review_item_id_for_review_required_debug_rows():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 2,
        "passed_filter": 2,
        "ranked": 2,
        "cvs_generated": 0,
        "cv_generation_debug_records": [
            {
                "job_url": "",
                "job_title": "Missing URL Role",
                "rank": 1,
                "status": "review_required",
                "ranking_fit_label": "strong",
                "fit_classification": "strong",
                "decision_chain": {},
                "evidence_used": [],
                "gap_summary": {"missing": ["sql"]},
                "structured_cv_initial": {"schema_version": "cv_doc_v1"},
                "validation_initial": {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": {"schema_version": "cv_doc_v1"},
                "markdown_final": "# CV",
                "error": {"message": "Manual review required."},
            },
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    assert payload["debug_records"][0]["status"] == "review_required"
    assert str(payload["debug_records"][0].get("review_item_id") or "").startswith("ri_")


def test_worker_persists_cv_generation_debug_coverage_for_reranker_blocked_rows():
    """@proves trigger_run_management.reranker-fit-authority
    @proves inspection_debugging.quality-metrics-diagnostics
    """
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "manual_staged"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 3,
        "cvs_generated": 1,
        "cv_generation_debug_records": [
            {
                "job_url": "https://example.com/1",
                "status": "accepted",
                "ranking_fit_label": "stretch",
                "fit_classification": "stretch",
                "decision_chain": {},
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
        "cv_analysis_results": [
            {
                "job_url": "https://example.com/1",
                "status": "ready_for_generation",
                "analysis_reuse_status": "reused_exact_match",
            },
            {
                "job_url": "",
                "status": "blocked_by_reranker_fit",
                "analysis_reuse_status": "not_run_reranker_skip",
            },
            {
                "job_url": "https://example.com/3",
                "status": "blocked_by_reranker_fit",
                "analysis_reuse_status": "not_run_reranker_skip",
            },
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    assert payload["attempted_generation_jobs_total"] == 1
    assert payload["non_attempted_ranked_jobs_total"] == 2
    assert payload["omission_reason_counts"] == {"blocked_by_reranker_fit": 2}
    assert payload["snapshot_complete"] is False


def test_worker_persists_stage_transition_artifacts_json_on_success():
    """@proves trigger_run_management.shared-stage-progress
    @proves inspection_debugging.stage-transition-diagnostics
    @proves pipeline_performance.large-runs-avoid-some-row-scaled-layer-4-event-noise-by-relying-more-on-aggregate-stage-summaries-plus-stage-owned-artifacts
    """
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts") as mock_store_stage_artifacts:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_stage_artifacts.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["status"] == "succeeded"
    assert payload["snapshot_complete"] is True
    assert payload["degradation_reason"] == ""
    assert payload["artifacts"]["schema_version"] == "stage_transition_artifacts_v2"
    assert payload["artifacts"]["stages"]["normalize"]["input_counts"]["raw_jobs"] == 5
    assert payload["artifacts"]["stages"]["ranking"]["output_counts"]["ranked_jobs"] == 2

def test_stage_transition_payload_marks_failed_partial_snapshot_with_reason() -> None:
    summary = {
        "run_id": "r1",
        "stage_transition_artifacts": {
            "schema_version": "stage_transition_artifacts_v6",
            "stages": {
                "normalize": {"status": "completed"},
                "enrich": {"status": "completed"},
                "rule_filter": {"status": "not_reached"},
            },
        },
    }
    from fitcv_cp.worker_job import _build_stage_transition_artifacts_payload
    payload = json.loads(
        _build_stage_transition_artifacts_payload(
            run_id="r1",
            summary=summary,
            finished_at=datetime.datetime.now(datetime.timezone.utc),
            run_status=RunStatus.FAILED,
            degradation_reason="partial_snapshot",
        )
    )
    assert payload["status"] == "failed"
    assert payload["snapshot_complete"] is False
    assert payload["degradation_reason"] == "partial_snapshot"


def test_worker_persists_settings_used_json_on_success():
    """@proves settings_system.settings-used-exports
    @proves inspection_debugging.settings-used-export
    @proves inspection_debugging.prompt-provenance-diagnostics
    """
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({
        "pipeline": {"final_top_n": 10},
        "cv": {"generation": {"model": "cx/gpt-5.4-mini"}},
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_settings.call_args.args[1])
    assert payload["run_id"] == "r1"
    assert payload["settings_schema_version"] == "settings_used_v2"
    assert payload["data_plane"]["runtime_mode"] == "full"
    assert payload["data_plane"]["artifact_backend"] == "sqlite_json"
    assert payload["replay_context"]["replay_mode"] == "strict"
    assert payload["replay_context"]["replay_source_run_id"] == "r1"
    assert payload["replay_context"]["policy_registry_version"] == "policy_registry.v1"
    assert payload["late_stage_mode"]["late_stage_mode"] == "agentic"
    assert payload["late_stage_mode"]["agentic_late_stage_enabled"] is True
    assert payload["late_stage_mode"]["agentic_status"] == "completed"
    assert payload["effective_settings"]["pipeline"]["final_top_n"] == 10
    assert payload["sources"]["config_path"] == ".env.yaml"
    assert payload["sources"]["effective_settings_snapshot_present"] is True
    assert payload["sources"]["prompts_runtime"]["enrich"]["extraction"]["prompt_id"] == "enrich.extraction.v1"


def test_worker_settings_used_export_canonicalizes_legacy_compatibility_keys():
    """@proves settings_system.settings-used-exports"""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({
        "vector_top_n": 40,
        "rerank_top_n": 15,
        "cv_generation_model": "legacy-model",
        "cv_max_pages": 3,
        "pipeline": {"vector_search_top_n": 50, "ai_score_top_n": 10, "final_top_n": 5},
        "cv": {"generation": {"model": "cx/gpt-5.4-mini"}, "validation": {"max_pages": 2}},
        "prompts_runtime": {
            "ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v1", "template_path": "ranking.md"}},
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
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_settings.call_args.args[1])
    assert "vector_top_n" not in payload["effective_settings"]
    assert "rerank_top_n" not in payload["effective_settings"]
    assert "cv_generation_model" not in payload["effective_settings"]
    assert "cv_max_pages" not in payload["effective_settings"]
    assert payload["compatibility_projection"]["vector_top_n"] == 40
    assert payload["compatibility_projection"]["rerank_top_n"] == 15
    assert payload["compatibility_projection"]["cv_generation_model"] == "legacy-model"
    assert payload["compatibility_projection"]["cv_max_pages"] == 3
    assert payload["effective_settings"]["stage_runtime"]["enrich"]["batch_size"] == 10
    assert payload["effective_settings"]["stage_runtime"]["enrich"]["concurrency"] == 1
    assert payload["effective_settings"]["stage_runtime"]["ranking"]["sleep_secs"] == 0.5
    assert payload["effective_settings"]["stage_runtime"]["ranking"]["concurrency"] == 1
    assert payload["effective_settings"]["stage_runtime"]["cv_analysis"]["concurrency"] == 1
    assert payload["effective_settings"]["stage_runtime"]["cv_generation"]["concurrency"] == 1

def test_worker_settings_used_snapshot_materializes_ranking_concurrency_from_canonical_stage_runtime() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({
        "pipeline": {"vector_search_top_n": 50, "ai_score_top_n": 10, "final_top_n": 5},
        "stage_runtime": {"ranking": {"concurrency": 6}},
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
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_settings.call_args.args[1])
    assert payload["effective_settings"]["stage_runtime"]["ranking"]["concurrency"] == 6


def test_worker_settings_used_persistence_failure_does_not_fail_run():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_settings_used", side_effect=RuntimeError("settings snapshot boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_retries_missing_settings_used_artifact_once() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({"pipeline": {"final_top_n": 10}})
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    persisted_missing = MagicMock(
        effective_settings_json=json.dumps({"pipeline": {"final_top_n": 10}}, ensure_ascii=False),
        cv_generation_debug_json=json.dumps({"debug_records": []}, ensure_ascii=False),
        stage_transition_artifacts_json=json.dumps({"artifacts": {}}, ensure_ascii=False),
        settings_used_json="",
    )

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", side_effect=[mock_run, mock_run, persisted_missing]), \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    assert mock_store_settings.call_count == 2


def test_worker_stage_transition_artifacts_persistence_failure_does_not_fail_run():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts", side_effect=RuntimeError("stage artifacts boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_mapping_suggestions_persistence_failure_appends_warning_event() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
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
        "completed_stages": ["normalize", "enrich"],
        "last_completed_stage": "enrich",
        "stage_transition_artifacts": {
            "artifacts": {"stages": {"enrich": {"status": "completed"}}}
        },
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_mapping_suggestions", side_effect=RuntimeError("missing column")), \
       patch("fitcv_cp.worker_job.append_event", return_value={"persistence_status": "persisted"}) as append_mock, \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    events = [call.args[0] for call in append_mock.call_args_list if call.args]
    warning_events = [ev for ev in events if getattr(ev, "stage", "") == "snapshot_persist_failed" and getattr(ev, "level", "") == "warning"]
    assert warning_events
    assert any(
        "mapping_suggestions snapshot persistence failed" in str(getattr(ev, "message", ""))
        for ev in warning_events
    )


def test_worker_synonym_proposals_degradation_appends_warning_event() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
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
        "completed_stages": ["normalize", "enrich"],
        "last_completed_stage": "enrich",
        "stage_transition_artifacts": {
            "artifacts": {"stages": {"enrich": {"status": "completed"}}}
        },
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_synonym_proposals", return_value={
           "persistence_status": "bundle_only_degraded",
           "degradation_reason": "missing_synonym_proposals_json_column",
       }), \
       patch("fitcv_cp.worker_job.append_event", return_value={"persistence_status": "persisted"}) as append_mock, \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    events = [call.args[0] for call in append_mock.call_args_list if call.args]
    warning_events = [ev for ev in events if getattr(ev, "stage", "") == "snapshot_persist_failed" and getattr(ev, "level", "") == "warning"]
    assert warning_events
    message = str(getattr(warning_events[-1], "message", ""))
    assert "synonym_proposals snapshot persistence failed" in message
    assert "missing_synonym_proposals_json_column" in message


def test_worker_review_hold_uses_non_null_snapshot_timestamp_for_synonym_and_mapping() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-review",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "mapping_suggestions": [{"field": "skill", "alias": "gcp", "canonical": "google cloud", "confidence": 0.9}],
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [{"status": "review_required", "job_url": "https://example.com/1"}],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_mapping_suggestions") as mock_mapping_update, \
       patch("fitcv_cp.worker_job.update_run_synonym_proposals", return_value={"persistence_status": "persisted"}) as mock_syn_update, \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r-review", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    mapping_payload = json.loads(mock_mapping_update.call_args.args[1])
    synonym_payload = json.loads(mock_syn_update.call_args.args[1])
    assert isinstance(mapping_payload.get("created_at"), str) and mapping_payload["created_at"]
    assert isinstance(synonym_payload.get("created_at"), str) and synonym_payload["created_at"]


def test_worker_run_all_auto_accepts_low_risk_review_required_when_enabled() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_ai_action_enabled": True}}
        )
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-auto-accept",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [
            {"status": "review_required", "job_url": "https://example.com/1", "error": {"stage": "provider", "message": "response unusable"}}
        ],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r-auto-accept", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_run_all_keeps_awaiting_review_for_high_risk_review_required() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_ai_action_enabled": True}}
        )
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-high-risk-review",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [
            {"status": "review_required", "job_url": "https://example.com/1", "error": {"stage": "validation", "message": "validation failed"}}
        ],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r-high-risk-review", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_run_all_awaiting_review_persists_terminal_snapshots_as_succeeded() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_ai_action_enabled": True}}
        )
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-awaiting-review-persist",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [
            {"status": "review_required", "job_url": "https://example.com/1", "error": {"stage": "validation", "message": "validation failed"}}
        ],
        "mapping_suggestions": [{"field": "skill", "alias": "py", "canonical": "python", "confidence": 0.8}],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update_status, \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export, \
       patch("fitcv_cp.worker_job.update_run_settings_used") as mock_store_settings, \
       patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts") as mock_store_stage_artifacts:
        execute_pipeline_run(run_id="r-awaiting-review-persist", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update_status.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    assert mock_store_export.called
    assert mock_store_settings.called
    assert mock_store_stage_artifacts.called
    stage_payload = json.loads(mock_store_stage_artifacts.call_args.args[1])
    assert stage_payload["status"] == "succeeded"
    assert stage_payload["snapshot_complete"] is True
    assert stage_payload["degradation_reason"] == ""
    assert isinstance(stage_payload.get("created_at"), str) and stage_payload["created_at"]

def test_worker_run_all_executes_synonym_automation_when_enabled() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps(
            {
                "skill_synonyms": {},
                "synonym_management": {
                    "propose_enabled": True,
                    "apply_to_run_enabled": True,
                    "promote_global_enabled": True,
                    "auto_triage_recommendation_enabled": True,
                    "triage_recommendation_reuse_enabled": True,
                    "auto_apply_recommendation_enabled": True,
                    "auto_promote_global_enabled": True,
                    "auto_accept_ai_action_enabled": True,
                },
            }
        )
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-auto-synonym",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "mapping_suggestions": [
            {"field": "skill", "alias": "gcp", "canonical": "google cloud", "confidence": 0.91, "must_have_skill": "gcp"}
        ],
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "last_completed_stage": "cv_generation",
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
        "cv_generation_debug_records": [],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job._persist_global_skill_synonyms_map"), \
       patch("fitcv_cp.worker_job._load_global_skill_synonyms_map", return_value={}), \
       patch("fitcv_cp.worker_job.update_run_effective_settings"), \
       patch("fitcv_cp.worker_job.update_run_synonym_proposals", return_value={"persistence_status": "persisted"}) as mock_syn_update, \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r-auto-synonym", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    synonym_payload = json.loads(mock_syn_update.call_args.args[1])
    proposals = list(synonym_payload.get("proposals") or [])
    assert proposals
    assert proposals[0]["recommended_action"] == "approve"
    assert proposals[0]["proposal_status"] == "approved_for_run_overlay"
    trace_summary = dict((synonym_payload.get("synonym_proposals_trace") or {}).get("trace_summary") or {})
    assert int(trace_summary.get("triage_recommendation_generated_total") or 0) >= 1
    assert int(trace_summary.get("auto_apply_recommendation_applied") or 0) >= 1
    assert trace_summary.get("auto_promote_global_skip_reason") == "applied"

def test_worker_run_all_does_not_execute_synonym_automation_when_disabled() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps(
            {
                "skill_synonyms": {},
                "synonym_management": {
                    "propose_enabled": True,
                    "apply_to_run_enabled": True,
                    "promote_global_enabled": True,
                    "auto_triage_recommendation_enabled": False,
                    "triage_recommendation_reuse_enabled": True,
                    "auto_apply_recommendation_enabled": False,
                    "auto_promote_global_enabled": False,
                    "auto_accept_ai_action_enabled": True,
                },
            }
        )
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-auto-synonym-disabled",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 1,
        "mapping_suggestions": [
            {"field": "skill", "alias": "gcp", "canonical": "google cloud", "confidence": 0.91, "must_have_skill": "gcp"}
        ],
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "last_completed_stage": "cv_generation",
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
        "cv_generation_debug_records": [],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job._persist_global_skill_synonyms_map"), \
       patch("fitcv_cp.worker_job._load_global_skill_synonyms_map", return_value={}), \
       patch("fitcv_cp.worker_job.update_run_effective_settings"), \
       patch("fitcv_cp.worker_job.append_event", return_value={"persistence_status": "persisted"}) as append_mock, \
       patch("fitcv_cp.worker_job.update_run_synonym_proposals", return_value={"persistence_status": "persisted"}) as mock_syn_update, \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r-auto-synonym-disabled", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"
    synonym_payload = json.loads(mock_syn_update.call_args.args[1])
    proposals = list(synonym_payload.get("proposals") or [])
    assert proposals
    assert proposals[0].get("recommended_action") is None
    assert proposals[0]["proposal_status"] == "proposed_unreviewed"
    trace_summary = dict((synonym_payload.get("synonym_proposals_trace") or {}).get("trace_summary") or {})
    assert int(trace_summary.get("triage_recommendation_generated_total") or 0) == 0
    assert int(trace_summary.get("auto_apply_recommendation_applied") or 0) == 0
    assert int(trace_summary.get("auto_promote_global_applied") or 0) == 0
    automation_stages = {
        "synonym_proposal_triage_completed",
        "synonym_proposal_auto_apply_completed",
        "synonym_proposal_promoted_global",
    }
    emitted = [call.args[0] for call in append_mock.call_args_list if call.args]
    assert not any(getattr(ev, "stage", "") in automation_stages for ev in emitted)


def test_worker_debug_snapshot_persistence_failure_does_not_fail_run():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug", side_effect=RuntimeError("debug snapshot boom")), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"


def test_worker_cv_generation_debug_json_truncates_large_markdown_but_keeps_core_fields():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    record = payload["debug_records"][0]
    assert record["job_url"] == "https://example.com/1"
    assert record["status"] == "accepted"
    assert record["evidence_used"] == [{"evidence_type": "experience_entry", "source_ref": "experience[0]", "name": "Data Engineer"}]
    assert record["markdown_full"] == large_markdown
    assert record["markdown_preview"].endswith("...[truncated]")
    assert len(record["markdown_preview"]) < len(large_markdown)
    assert record["markdown_final"] == record["markdown_preview"]
    assert len(record["markdown_final"]) < len(large_markdown)



def test_worker_cv_generation_debug_json_preserves_evidence_selection_summary():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None

    summary_payload = {
        "selected_evidence_ids": ["exp-1"],
        "selected_evidence_count": 1,
        "fallback_used": False,
        "hybrid_alignment": {
            "responsibility_alignment": {"lexical_weight": 0.25, "semantic_weight": 0.75},
        },
    }
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
                "evidence_selection_summary": summary_payload,
                "gap_summary": {"matched": ["SQL"]},
                "structured_cv_initial": {"schema_version": "cv_doc_v1"},
                "validation_initial": {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
                "repair_attempt": {"performed": False, "missing_sections": []},
                "structured_cv_final": {"schema_version": "cv_doc_v1"},
                "markdown_final": "# CV",
                "error": None,
            }
        ],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_cv_generation_debug") as mock_store_debug:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_debug.call_args.args[1])
    record = payload["debug_records"][0]
    assert record["evidence_selection_summary"]["selected_evidence_ids"] == ["exp-1"]
    assert record["evidence_selection_summary"]["selected_evidence_count"] == 1
    assert record["evidence_selection_summary"]["hybrid_alignment"]["responsibility_alignment"]["semantic_weight"] == 0.75
def test_worker_marks_failed_on_exception():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.update_run_status") as mock_update_status, \
         patch("fitcv_cp.worker_job.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    statuses = [call.args[1].value for call in mock_update_status.call_args_list if len(call.args) >= 2]
    assert "failed" in statuses
    append_mock.assert_called()


def test_worker_error_event_has_correct_level():
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    events = [call.args[0] for call in append_mock.call_args_list if call.args]
    assert any(getattr(ev, "level", "") == "error" and getattr(ev, "stage", "") == "pipeline_failed" for ev in events)


def test_worker_uses_effective_settings_snapshot():
    """Worker must use stored effective_settings_json without rebuilding runtime config."""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    effective = {"pipeline": {"final_top_n": 5}, "gcp_project": "p"}
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps(effective)
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=client):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is not None
    assert call_kwargs["config"]["pipeline"]["final_top_n"] == 5


def test_worker_falls_back_to_config_path_if_no_snapshot():
    """If effective_settings_json is None, worker falls back to config_path."""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=client):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is None


def test_worker_passes_control_plane_run_id_to_pipeline():
    """Worker must pass the admin run_id into the pipeline for downstream joins."""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1", "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=client):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs["run_id"] == "r1"


def test_worker_manual_staged_run_pauses_and_persists_checkpoint() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
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


def test_worker_manual_staged_normalize_checkpoint_does_not_persist_mapping_suggestions() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "manual_staged"
    mock_run.next_stage = "normalize"
    mock_run.checkpoint_payload_json = None
    mock_run.started_at = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1",
             "paused_after_stage": "normalize",
             "next_stage": "enrich",
             "completed_stages": ["normalize"],
             "checkpoint_payload": {"normalized": []},
             "stage_transition_artifacts": {
                 "schema_version": "stage_transition_artifacts_v6",
                 "artifacts": {"stages": {"normalize": {"status": "completed"}}},
             },
             "total_jobs": 5,
             "passed_filter": 0,
             "ranked": 0,
             "cvs_generated": 0,
         }), \
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.update_run_checkpoint"), \
         patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts"), \
         patch("fitcv_cp.worker_job.update_run_mapping_suggestions") as mock_mapping, \
         patch("fitcv_cp.worker_job.update_run_status"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    mock_mapping.assert_not_called()


def test_worker_run_all_persists_stage_progress_without_checkpoint_state() -> None:
    """@proves trigger_run_management.shared-stage-progress"""
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "run_all"
    mock_run.next_stage = None
    mock_run.checkpoint_payload_json = None
    mock_run.started_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.finished_at = None

    def _run_pipeline_side_effect(**kwargs):
        kwargs["stage_progress_callback"](
            {
                "run_id": "r1",
                "last_completed_stage": "enrich",
                "completed_stages": ["normalize", "enrich"],
                "next_stage": "rule_filter",
                "total_jobs": 5,
                "passed_filter": 0,
                "ranked": 0,
                "cvs_generated": 0,
                "mapping_suggestions": [{"alias": "gcp", "canonical": "google cloud"}],
                "stage_transition_artifacts": {
                    "schema_version": "stage_transition_artifacts_v6",
                    "artifacts": {
                        "stages": {
                            "normalize": {"status": "completed"},
                            "enrich": {"status": "completed"},
                        }
                    },
                },
            }
        )
        return {
            "run_id": "r1",
            "total_jobs": 5,
            "passed_filter": 3,
            "ranked": 2,
            "cvs_generated": 1,
            "export_results": [],
            "stage_transition_artifacts": {
                "schema_version": "stage_transition_artifacts_v6",
                "artifacts": {
                    "stages": {
                        "normalize": {"status": "completed"},
                        "enrich": {"status": "completed"},
                        "rule_filter": {"status": "completed"},
                        "shortlist": {"status": "completed"},
                        "ranking": {"status": "completed"},
                        "cv_analysis": {"status": "completed"},
                        "cv_generation": {"status": "completed"},
                    }
                },
            },
        }

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", side_effect=_run_pipeline_side_effect) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.update_run_checkpoint") as mock_checkpoint, \
         patch("fitcv_cp.worker_job.update_run_progress") as mock_progress, \
         patch("fitcv_cp.worker_job.update_run_stage_transition_artifacts") as mock_stage_artifacts, \
         patch("fitcv_cp.worker_job.update_run_mapping_suggestions") as mock_mapping, \
         patch("fitcv_cp.worker_job.update_run_synonym_proposals", return_value={
             "persistence_status": "persisted",
             "degradation_reason": "",
         }) as mock_synonyms, \
         patch("fitcv_cp.worker_job.update_run_results_export"), \
         patch("fitcv_cp.worker_job.update_run_cv_generation_debug"), \
         patch("fitcv_cp.worker_job.update_run_settings_used"), \
         patch("fitcv_cp.worker_job.update_run_status"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args.kwargs
    assert call_kwargs["start_stage"] is None
    assert call_kwargs["stop_after_stage"] is None
    assert call_kwargs["stage_progress_callback"] is not None
    mock_checkpoint.assert_not_called()
    assert mock_progress.call_count >= 2
    first_progress = mock_progress.call_args_list[0]
    assert first_progress.kwargs["last_completed_stage"] == "enrich"
    assert first_progress.kwargs["completed_stages"] == ["normalize", "enrich"]
    mock_stage_artifacts.assert_called()
    mock_mapping.assert_called()
    mock_synonyms.assert_called()


def test_worker_manual_resume_passes_checkpoint_payload_to_pipeline() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
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
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.update_run_checkpoint"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args.kwargs
    assert call_kwargs["start_stage"] == "ranking"
    assert call_kwargs["stop_after_stage"] == "ranking"
    assert call_kwargs["checkpoint_payload"] == {
        "shortlist": [{"job_url": "https://example.com/1"}]
    }


def test_worker_manual_resume_uses_uploaded_run_scoped_synonym_overlay() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps({
        "gcp_project": "p",
        "skill_synonyms": {
            "gcp": "google cloud",
            "ga4": "google analytics",
        },
        "skill_synonyms_runtime": {
            "base_policy_path": "config/skill_synonyms.yaml",
            "overlay_paths": [],
            "has_overlay": True,
            "entry_count": 2,
            "has_run_overlay": True,
            "run_overlay_filename": "reviewed-skill-synonyms.yaml",
            "run_overlay_entry_count": 1,
        },
    })
    mock_run.cancel_requested_at = None
    mock_run.run_mode = "manual_staged"
    mock_run.next_stage = "rule_filter"
    mock_run.checkpoint_payload_json = json.dumps({
        "checkpoint_payload": {"enriched": [{"job_url": "https://example.com/1"}]}
    })
    mock_run.started_at = datetime.datetime.now().astimezone()

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "run_id": "r1", "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.update_run_checkpoint"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args.kwargs
    assert call_kwargs["config"]["skill_synonyms"]["ga4"] == "google analytics"
    assert call_kwargs["config"]["skill_synonyms_runtime"]["has_run_overlay"] is True


def test_build_synonym_proposals_payload_groups_conflicts_for_review() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals",
            summary={
                "mapping_suggestions": [
                    {
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "confidence": 0.9,
                        "must_have_skill": "google cloud",
                    },
                    {
                        "alias": "gcp",
                        "canonical": "google cloud platform",
                        "confidence": 0.7,
                        "must_have_skill": "google cloud platform",
                    },
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
        )
    )

    assert payload["synonym_proposals_schema_version"] == "synonym_proposals_v1"
    assert payload["synonym_proposals_trace"]["trace_family"] == "agentic_step_trace"
    assert payload["synonym_proposals_trace"]["step_id"] == "synonym_proposals"
    assert payload["synonym_proposals_trace"]["trace_status"] == "completed"
    assert len(payload["proposals"]) == 1
    proposal = payload["proposals"][0]
    assert proposal["proposal_scope"] == "run_scoped_overlay_candidate"
    assert proposal["proposal_status"] == "proposed_unreviewed"
    assert proposal["proposal_family"] == "conflict_bundle"
    assert proposal["field"] == "skill"
    assert proposal["alias"] == "gcp"
    assert proposal["canonical"] == "google cloud"
    assert proposal["candidate_canonicals"] == ["google cloud", "google cloud platform"]
    assert proposal["conflict_summary"]["has_conflict"] is True
    assert proposal["evidence_summary"]["occurrence_count"] == 2


def test_build_synonym_proposals_payload_preserves_existing_review_state() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    baseline_payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals",
            summary={
                "mapping_suggestions": [
                    {
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "confidence": 0.9,
                        "must_have_skill": "google cloud",
                    }
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
        )
    )
    proposal_id = baseline_payload["proposals"][0]["proposal_id"]

    existing_payload_json = json.dumps(
        {
            "run_id": "run-synonym-proposals",
            "proposals": [
                {
                    "proposal_id": proposal_id,
                    "proposal_status": "approved_for_run_overlay",
                    "review_history": [
                        {
                            "action": "approve_for_run_overlay",
                            "acted_by": "operator@example.com",
                        }
                    ],
                }
            ],
        }
    )

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals",
            summary={
                "mapping_suggestions": [
                    {
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "confidence": 0.9,
                        "must_have_skill": "google cloud",
                    }
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
            existing_payload_json=existing_payload_json,
        )
    )

    proposal = payload["proposals"][0]
    assert proposal["proposal_id"] == proposal_id
    assert proposal["proposal_status"] == "approved_for_run_overlay"
    assert proposal["review_history"][0]["action"] == "approve_for_run_overlay"


def test_build_synonym_proposals_payload_marks_not_applicable_without_mapping_suggestions() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals-empty",
            summary={},
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
        )
    )

    assert payload["proposal_generation_status"] == "not_applicable"
    assert payload["persistence_status"] == "not_applicable"
    assert payload["synonym_proposals_trace"]["trace_status"] == "not_applicable"
    assert payload["proposals"] == []


# ── cooperative cancellation ─────────────────────────────────────────────────

def test_build_synonym_proposals_payload_skips_pairs_already_in_global_synonyms() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals-global-skip",
            summary={
                "mapping_suggestions": [
                    {
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "confidence": 0.9,
                    }
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
            global_synonyms={"gcp": "google cloud"},
        )
    )

    assert payload["proposals"] == []
    assert payload["proposal_generation_status"] == "not_applicable"
    assert payload["synonym_proposals_trace"]["trace_summary"]["suppressed_as_already_global_count"] == 1
    assert payload["synonym_proposals_trace"]["trace_summary"]["generated_for_review_count"] == 0
    assert payload["synonym_proposals_trace"]["trace_summary"]["suppression_source"] == "run_effective_skill_synonyms"
    assert payload["synonym_proposals_trace"]["trace_summary"]["suppressed_count_by_field"]["skill"] == 1
    assert (
        payload["synonym_proposals_trace"]["trace_summary"]["suppressed_reason_counts_by_field"]["skill"]["already_global_exact"]
        == 1
    )
    assert payload["synonym_proposals_trace"]["suppression_examples"][0]["alias"] == "gcp"

def test_build_synonym_proposals_payload_supports_domain_and_role_family_fields() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-multi-field-proposals",
            summary={
                "mapping_suggestions": [
                    {"field": "domain", "alias": "fintech", "canonical": "financial services", "confidence": 0.91},
                    {"field": "domain", "alias": "fintech", "canonical": "financial services", "confidence": 0.9},
                    {"field": "role_family", "alias": "bi analyst", "canonical": "analytics", "confidence": 0.89},
                    {"field": "role_family", "alias": "bi analyst", "canonical": "analytics", "confidence": 0.88},
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
            global_synonyms={"fintech": "financial services"},
        )
    )

    proposals = list(payload["proposals"])
    assert len(proposals) == 2
    assert {proposal["field"] for proposal in proposals} == {"domain", "role_family"}

def test_build_synonym_proposals_payload_suppresses_low_support_non_skill_rows() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-non-skill-low-support",
            summary={
                "mapping_suggestions": [
                    {"field": "domain", "alias": "fintech", "canonical": "financial services", "confidence": 0.91},
                    {"field": "role_family", "alias": "bi analyst", "canonical": "analytics", "confidence": 0.89},
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
        )
    )

    assert payload["proposals"] == []
    summary = payload["synonym_proposals_trace"]["trace_summary"]
    assert summary["suppressed_count_by_field"]["domain"] == 1
    assert summary["suppressed_count_by_field"]["role_family"] == 1
    assert (
        summary["suppressed_reason_counts_by_field"]["domain"]["insufficient_non_skill_support"] == 1
    )
    assert (
        summary["suppressed_reason_counts_by_field"]["role_family"]["insufficient_non_skill_support"] == 1
    )

def test_append_synonym_suppression_summary_event_deduplicates_same_fingerprint() -> None:
    from fitcv_cp.worker_job import _append_synonym_suppression_summary_event

    payload_json = json.dumps(
        {
            "synonym_proposals_trace": {
                "trace_summary": {
                    "suppressed_as_already_global_count": 2,
                    "generated_for_review_count": 1,
                    "suppression_source": "run_effective_skill_synonyms",
                },
                "suppression_examples": [{"field": "skill", "alias": "gcp", "canonical": "google cloud"}],
            }
        }
    )
    appended: list[object] = []
    existing_events: list[object] = []

    def _fake_append_event(event: object, client: object, *, project: str, dataset: str) -> None:
        appended.append(event)
        existing_events.append(event)

    with patch("fitcv_cp.worker_job.get_events", side_effect=lambda *args, **kwargs: list(existing_events)), \
         patch("fitcv_cp.worker_job.append_event", side_effect=_fake_append_event):
        _append_synonym_suppression_summary_event(
            run_id="run-1",
            synonym_payload_json=payload_json,
            client=object(),
            project="proj",
            dataset="ds",
        )
        _append_synonym_suppression_summary_event(
            run_id="run-1",
            synonym_payload_json=payload_json,
            client=object(),
            project="proj",
            dataset="ds",
        )

    assert len(appended) == 1

def test_append_synonym_suppression_summary_event_respects_legacy_sha1_fingerprint() -> None:
    from types import SimpleNamespace

    from fitcv_cp.worker_job import _append_synonym_suppression_summary_event

    payload_json = json.dumps(
        {
            "synonym_proposals_trace": {
                "trace_summary": {
                    "suppressed_as_already_global_count": 2,
                    "generated_for_review_count": 1,
                    "suppression_source": "run_effective_skill_synonyms",
                },
                "suppression_examples": [{"field": "skill", "alias": "gcp", "canonical": "google cloud"}],
            }
        }
    )
    suppression_payload = {
        "suppressed_as_already_global_count": 2,
        "generated_for_review_count": 1,
        "suppression_source": "run_effective_skill_synonyms",
        "suppression_examples": [{"field": "skill", "alias": "gcp", "canonical": "google cloud"}],
    }
    legacy_sha1 = hashlib.sha1(
        json.dumps(suppression_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    existing_events = [
        SimpleNamespace(
            stage="synonym_proposal_suppression_summary",
            payload_json=json.dumps({"suppression_fingerprint": legacy_sha1}),
        )
    ]
    appended: list[object] = []

    def _fake_append_event(event: object, client: object, *, project: str, dataset: str) -> None:
        appended.append(event)

    with patch("fitcv_cp.worker_job.get_events", side_effect=lambda *args, **kwargs: list(existing_events)), \
         patch("fitcv_cp.worker_job.append_event", side_effect=_fake_append_event):
        _append_synonym_suppression_summary_event(
            run_id="run-1",
            synonym_payload_json=payload_json,
            client=object(),
            project="proj",
            dataset="ds",
        )

    assert appended == []

def test_build_synonym_proposals_payload_keeps_conflicts_when_global_points_elsewhere() -> None:
    from fitcv_cp.synonym_proposals import build_synonym_proposals_payload

    payload = json.loads(
        build_synonym_proposals_payload(
            run_id="run-synonym-proposals-global-conflict",
            summary={
                "mapping_suggestions": [
                    {
                        "alias": "gcp",
                        "canonical": "google cloud",
                        "confidence": 0.9,
                    }
                ]
            },
            created_at=datetime.datetime(2026, 4, 28, tzinfo=datetime.timezone.utc),
            global_synonyms={"gcp": "google cloud platform"},
        )
    )

    assert len(payload["proposals"]) == 1
    assert payload["proposals"][0]["alias"] == "gcp"
    assert payload["proposals"][0]["canonical"] == "google cloud"
    assert payload["synonym_proposals_trace"]["trace_summary"]["suppressed_as_already_global_count"] == 0

def test_synonym_management_mode_matches_authoritative_resolver_defaults() -> None:
    from fitcv_cp.synonym_proposals import resolve_synonym_management_mode
    from fitcv_cp.worker_job import _synonym_management_mode_from_run_record

    expected = resolve_synonym_management_mode(None)
    actual = _synonym_management_mode_from_run_record(None)

    assert actual == expected

def test_synonym_management_mode_prefers_canonical_reuse_toggle() -> None:
    from fitcv_cp.synonym_proposals import resolve_synonym_management_mode

    mode = resolve_synonym_management_mode(
        {
            "synonym_management": {"triage_recommendation_reuse_enabled": True},
            "reuse": {"synonym_triage": {"enabled": False}},
        }
    )
    assert mode["triage_recommendation_reuse_enabled"] is False

def test_build_synonym_overlay_yaml_roundtrips_reserved_scalars() -> None:
    from fitcv.config import parse_skill_synonym_overlay_yaml
    from fitcv_cp.worker_job import _build_synonym_overlay_yaml

    overlay = {
        "c#/.net": "platform:core",
        "gcp#ops": "google cloud #1",
    }
    yaml_text = _build_synonym_overlay_yaml(overlay)

    assert parse_skill_synonym_overlay_yaml(yaml_text) == {
        "c#/.net": "platform:core",
        "gcp#ops": "google cloud #1",
    }

def test_persist_global_skill_synonyms_map_atomic_write_failure_preserves_existing_file(
    tmp_path: Path,
) -> None:
    from fitcv_cp.worker_job import _persist_global_skill_synonyms_map

    target = tmp_path / "skill_synonyms.yaml"
    original = "skill_synonyms:\n  keep: existing\n"
    target.write_text(original, encoding="utf-8")

    with patch("fitcv_cp.worker_job._global_skill_synonyms_path", return_value=target), \
         patch("fitcv_cp.worker_job.os.replace", side_effect=OSError("replace failed")):
        with pytest.raises(OSError, match="replace failed"):
            _persist_global_skill_synonyms_map({"new": "value"})

    assert target.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("skill_synonyms.yaml.*.tmp")) == []

def test_worker_marks_cancelled_when_cancel_already_requested():
    """@proves run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs

    Worker should exit before RUNNING when cancel_requested_at is already set.
    """
    import datetime
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = datetime.datetime.now(datetime.timezone.utc)

    status_updates = []

    def capture_query(sql, job_config=None):
        m = MagicMock()
        m.result.return_value = iter([])
        return m

    client.query.side_effect = capture_query

    with patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline") as mock_pipeline, \
         patch("fitcv_cp.worker_job.update_run_status") as mock_update:
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")
        status_updates = [c.args[1] for c in mock_update.call_args_list]

    # pipeline should NOT have been called
    mock_pipeline.assert_not_called()
    from fitcv_cp.models import RunStatus
    assert RunStatus.RUNNING not in status_updates
    assert RunStatus.CANCELLED in status_updates


def test_worker_cancellation_event_appended_on_early_exit():
    """@proves run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs
    @proves run_lifecycle_controls.full-audit-trail-in-pipeline-run-events

    Worker must append a run_cancelled event when exiting early due to cancel.
    """
    import datetime
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    client.insert_rows_json.return_value = []

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.cancel_requested_at = datetime.datetime.now(datetime.timezone.utc)

    with patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline"), \
         patch("fitcv_cp.worker_job.update_run_status"), \
         patch("fitcv_cp.worker_job.append_event") as mock_append:
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    stages = [c.args[0].stage for c in mock_append.call_args_list]
    assert "run_cancelled" in stages


def test_worker_pipeline_cancelled_exception_marks_cancelled():
    """@proves run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs

    PipelineCancelled raised during execution should produce cancelled status.
    """
    from fitcv.pipeline import PipelineCancelled
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])

    mock_run = MagicMock()
    mock_run.effective_settings_json = None
    mock_run.cancel_requested_at = None
    mock_run.cancel_requested_at = None

    with patch("fitcv_cp.worker_job._get_bq", return_value=client), \
         patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", side_effect=PipelineCancelled("stopped")), \
         patch("fitcv_cp.worker_job.update_run_status") as mock_update, \
         patch("fitcv_cp.worker_job.append_event"):
        execute_pipeline_run(run_id="r1", jobs_path="data/jobs.json", config_path=".env.yaml")

    from fitcv_cp.models import RunStatus
    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status == RunStatus.CANCELLED

def test_worker_results_export_includes_deterministic_stage_summary_fields() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=None)
    mock_run.cancel_requested_at = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "path"
    mock_run.candidate_profile_source = "default_config"
    mock_run.run_mode = "run_all"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.checkpoint_payload_json = None

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1",
        "total_jobs": 5,
        "passed_filter": 3,
        "ranked": 2,
        "cvs_generated": 1,
        "stage_transition_artifacts": {
            "stages": {
                "cv_analysis": {
                    "status": "completed",
                    "output_counts": {
                        "ready_for_generation": 1,
                        "blocked_by_reranker_fit": 1,
                        "skipped_fit_gate": 0,
                        "analysis_failed": 0,
                    },
                    "stage_result": {
                        "policy_version": "policy.cv_analysis.v1",
                        "decision": "pass",
                        "trace_context": {"trace_id": "t1", "span_id": "s1", "parent_span_id": "p1"},
                    },
                },
                "cv_generation": {
                    "status": "completed",
                    "output_counts": {
                        "accepted": 1,
                        "review_required": 0,
                        "validation_failed": 1,
                        "generation_failed": 0,
                        "persistence_failed": 0,
                    },
                    "stage_result": {
                        "policy_version": "policy.cv_generation.v1",
                        "decision": "manual_review",
                        "trace_context": {"trace_id": "t2", "span_id": "s2", "parent_span_id": "p2"},
                    },
                },
            }
        },
        "export_results": [{"job_url": "https://example.com/1", "pipeline_status": "ranked_no_cv"}],
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_results_export") as mock_store_export:
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    payload = json.loads(mock_store_export.call_args.args[1])
    cv_analysis_summary = payload["stage_result_summary"]["cv_analysis"]
    assert cv_analysis_summary["source_stage"] == "cv_analysis"
    assert cv_analysis_summary["stage_owned_subreason"] == "stage_summary"
    assert cv_analysis_summary["deterministic_outcome"] is None
    assert cv_analysis_summary["outcome_counts"]["ready_for_generation"] == 1
    assert cv_analysis_summary["outcome_counts"]["blocked_by_reranker_fit"] == 1

    cv_generation_summary = payload["stage_result_summary"]["cv_generation"]
    assert cv_generation_summary["source_stage"] == "cv_generation"
    assert cv_generation_summary["stage_owned_subreason"] == "stage_summary"
    assert cv_generation_summary["deterministic_outcome"] is None
    assert cv_generation_summary["outcome_counts"]["accepted"] == 1
    assert cv_generation_summary["outcome_counts"]["validation_failed"] == 1

def test_worker_review_required_with_terminal_resolution_status_is_not_counted_pending() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(effective_settings_json=json.dumps({"synonym_management": {"auto_accept_ai_action_enabled": True}}))
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-resolved-review",
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [
            {
                "status": "review_required",
                "job_url": "https://example.com/1",
                "resolution_status": "rejected",
                "error": {"stage": "validation", "message": "validation failed"},
            }
        ],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update, \
       patch("fitcv_cp.worker_job.append_event") as mock_append:
        execute_pipeline_run(run_id="r-resolved-review", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    final_status = mock_update.call_args_list[-1].args[1]
    assert final_status.value == "succeeded"

def test_worker_review_required_reason_totals_preserved_while_remaining_counts_only_pending() -> None:
    client = MagicMock()
    client.query.return_value.result.return_value = iter([])
    mock_run = MagicMock(
        effective_settings_json=json.dumps({"synonym_management": {"auto_accept_ai_action_enabled": True}})
    )
    mock_run.cancel_requested_at = None
    mock_run.checkpoint_payload_json = None
    mock_run.triggered_by = "admin"
    mock_run.jobs_input_source = "upload"
    mock_run.candidate_profile_source = "default_config"
    mock_run.created_at = None
    mock_run.started_at = None
    mock_run.finished_at = None
    mock_run.synonym_proposals_json = None
    mock_run.run_mode = "run_all"

    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r-reason-parity",
        "total_jobs": 2,
        "passed_filter": 2,
        "ranked": 2,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"],
        "cv_generation_debug_records": [
            {
                "status": "review_required",
                "job_url": "https://example.com/1",
                "resolution_status": "rejected",
                "error": {"stage": "validation", "message": "validation failed"},
            },
            {
                "status": "review_required",
                "job_url": "",
                "error": {"stage": "validation", "message": "validation failed"},
            },
        ],
        "stage_transition_artifacts": {"artifacts": {"stages": {"enrich": {"status": "completed"}}}},
    }), patch("fitcv_cp.worker_job._get_bq", return_value=client), \
       patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
       patch("fitcv_cp.worker_job.update_run_status") as mock_update, \
       patch("fitcv_cp.worker_job.append_event") as mock_append:
        execute_pipeline_run(run_id="r-reason-parity", jobs_path="data/sample_jobs.json", config_path=".env.yaml")

    status_updates = mock_update.call_args_list
    assert status_updates
    final_args = status_updates[-1].args
    final_status = final_args[1]
    final_summary = dict(status_updates[-1].kwargs.get("summary") or {})

    assert final_status.value == "succeeded"
    assert int(final_summary.get("review_required_total") or 0) == 2
    assert int(final_summary.get("review_required_remaining") or 0) == 1
    assert int(final_summary.get("review_required_remaining_missing_job_url") or 0) == 1

    review_events = [call.args[0] for call in mock_append.call_args_list if call.args and str(getattr(call.args[0], "stage", "")) == "cv_review_required"]
    assert review_events
    payload = json.loads(str(getattr(review_events[-1], "payload_json", "") or "{}"))
    assert int(payload.get("remaining") or 0) == 1
    assert int(payload.get("remaining_missing_job_url") or 0) == 1

def test_build_settings_used_payload_dict_has_required_shape() -> None:
    from types import SimpleNamespace

    from fitcv.contracts import SETTINGS_USED_SCHEMA_VERSION
    from fitcv_cp.worker_job import _build_settings_used_payload_dict

    run_record = SimpleNamespace(
        config_path=".env.yaml",
        jobs_input_source="path",
        candidate_profile_source="path",
    )
    payload = _build_settings_used_payload_dict(
        run_id="run-shape-1",
        run_record=run_record,
        effective_config={"run_mode": "run_all"},
        config_path=".env.yaml",
        finished_at=datetime.datetime(2026, 5, 24, tzinfo=datetime.timezone.utc),
        replay_context={},
    )

    assert payload["run_id"] == "run-shape-1"
    assert payload["settings_schema_version"] == SETTINGS_USED_SCHEMA_VERSION
    assert isinstance(payload["effective_settings"], dict)
    assert isinstance(payload["sources"], dict)
    assert isinstance(payload["data_plane"], dict)
    assert isinstance(payload["replay_context"], dict)


def test_build_settings_used_payload_json_safe_values() -> None:
    from types import SimpleNamespace

    from fitcv_cp.worker_job import _build_settings_used_payload

    run_record = SimpleNamespace(
        config_path=".env.yaml",
        jobs_input_source="path",
        candidate_profile_source="path",
    )
    payload = json.loads(
        _build_settings_used_payload(
            run_id="run-safe-1",
            run_record=run_record,
            effective_config={
                "pipeline": {"final_top_n": 10},
                "captured_on": datetime.date(2026, 7, 12),
                "debug_sections": {"experience", "skills"},
                "nested": {
                    "seen_at": datetime.datetime(2026, 7, 12, 9, 30, tzinfo=datetime.timezone.utc),
                },
            },
            config_path=".env.yaml",
            finished_at=datetime.datetime(2026, 7, 12, 10, 0, tzinfo=datetime.timezone.utc),
            replay_context={},
        )
    )

    effective_settings = payload["effective_settings"]
    assert effective_settings["captured_on"] == "2026-07-12"
    assert effective_settings["debug_sections"] == ["experience", "skills"]
    assert effective_settings["nested"]["seen_at"] == "2026-07-12T09:30:00+00:00"


def test_build_cv_generation_debug_payload_json_safe_values() -> None:
    from types import SimpleNamespace

    from fitcv_cp.worker_job import _build_cv_generation_debug_payload

    payload = json.loads(
        _build_cv_generation_debug_payload(
            run_id="run-debug-safe-1",
            run_record=SimpleNamespace(),
            summary={
                "ranked": 1,
                "cv_generation_debug_records": [
                    {
                        "job_url": "https://example.com/job-1",
                        "status": "review_required",
                        "captured_on": datetime.date(2026, 7, 12),
                        "debug_sections": {"experience", "skills"},
                        "nested": {
                            "seen_at": datetime.datetime(2026, 7, 12, 9, 30, tzinfo=datetime.timezone.utc),
                        },
                        "markdown_final": "# Draft",
                    }
                ],
            },
            finished_at=datetime.datetime(2026, 7, 12, 10, 0, tzinfo=datetime.timezone.utc),
        )
    )

    record = payload["debug_records"][0]
    assert record["captured_on"] == "2026-07-12"
    assert record["debug_sections"] == ["experience", "skills"]
    assert record["nested"]["seen_at"] == "2026-07-12T09:30:00+00:00"
    assert str(record.get("review_item_id") or "").strip()

def test_build_stage_transition_artifacts_payload_dict_has_required_shape() -> None:
    from fitcv.contracts import STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION
    from fitcv_cp.worker_job import _build_stage_transition_artifacts_payload_dict

    finished_at = datetime.datetime(2026, 5, 24, tzinfo=datetime.timezone.utc)
    payload = _build_stage_transition_artifacts_payload_dict(
        run_id="run-stage-shape-1",
        summary={"stage_transition_artifacts": {"stages": {"enrich": {"status": "succeeded"}}}},
        finished_at=finished_at,
        run_status=RunStatus.SUCCEEDED,
        degradation_reason=None,
    )

    assert payload["run_id"] == "run-stage-shape-1"
    assert payload["artifact_schema_version"] == STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION
    assert payload["created_at"] == finished_at.isoformat()
    assert isinstance(payload["artifacts"], dict)








