import datetime
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from fitcv_cp.app import (
    _build_hitl_review_audit_payload,
    _build_synonym_suppression_diff_payload,
    _load_run_synonym_proposals_trace_payload,
    create_app,
)
from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.run_artifact_mirror import (
    build_terminal_run_artifact_payloads,
    persist_terminal_run_artifact_mirror,
)


def _app():
    return create_app(redis_url="redis://localhost:6379/0")


def _make_succeeded_run() -> PipelineRun:
    return PipelineRun(
        run_id="run-artifact-parity",
        status=RunStatus.SUCCEEDED,
        triggered_by="admin",
        trigger_source="web",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 7, 12, 10, 0, tzinfo=datetime.timezone.utc),
        last_completed_stage="enrich",
        completed_stages=["normalize", "enrich"],
        results_export_json=json.dumps(
            {
                "run_id": "run-artifact-parity",
                "results": [
                    {
                        "job_url": "https://example.com/job-1",
                        "job_title": "Data Engineer",
                        "company": "Acme",
                        "pipeline_status": "ranked_no_cv",
                        "stage_owned_subreason": "review_required",
                        "decision_chain": {
                            "primary_fit": {"label": "Strong fit"},
                            "cv_generation": {"status": "review_required"},
                        },
                        "raw_job_fingerprint": "fp-1",
                        "source_job_url": "https://example.com/source-1",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        cv_generation_debug_json=json.dumps(
            {
                "debug_records": [
                    {
                        "review_item_id": "ri-1",
                        "job_url": "https://example.com/job-1",
                        "status": "review_required",
                        "reason": "Manual review required",
                        "markdown_final": "# Draft",
                    }
                ],
                "hitl_review_actions": [
                    {
                        "review_item_id": "ri-1",
                        "job_url": "https://example.com/job-1",
                        "action": "approved_as_is",
                        "resolution_status": "approved_as_is",
                        "actor": "reviewer",
                        "created_at": "2026-07-12T10:05:00+00:00",
                        "note": "looks good",
                        "artifact_version_id": "cv-v1",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        stage_transition_artifacts_json=json.dumps(
            {
                "run_id": "run-artifact-parity",
                "artifacts": {"stages": {"enrich": {"status": "completed"}}},
            },
            ensure_ascii=False,
        ),
        mapping_suggestions_json=json.dumps(
            {"suggestions": [{"alias": "k8s", "canonical": "kubernetes"}]},
            ensure_ascii=False,
        ),
        synonym_proposals_json=json.dumps(
            {
                "proposals": [
                    {
                        "proposal_id": "p-1",
                        "field": "skill",
                        "alias": "k8s",
                        "canonical": "kubernetes",
                        "proposal_status": "approved_for_run_overlay",
                    }
                ],
                "synonym_proposals_trace": {
                    "trace_status": "generated",
                    "trace_summary": {
                        "suppressed_count_by_field": {"skill": 1},
                        "generated_for_review_count": 1,
                        "suppression_source": "already_global",
                    },
                    "suppression_examples": [
                        {"field": "skill", "alias": "etl", "canonical": "extract transform load"}
                    ],
                },
            },
            ensure_ascii=False,
        ),
    )


def test_build_terminal_run_artifact_payloads_matches_control_plane_derived_payloads() -> None:
    run = _make_succeeded_run()

    payloads = build_terminal_run_artifact_payloads(run_record=run, events=[])

    assert payloads["export.json"]["results"][0]["final_status"] == "review_required"
    assert payloads["export.json"]["results"][0]["fit_label"] == "Strong fit"
    assert payloads["export.json"]["results"][0]["reason"] == "review_required"
    assert payloads["hitl-review-audit.json"] == _build_hitl_review_audit_payload(run)
    assert payloads["synonym-proposals-trace.json"] == _load_run_synonym_proposals_trace_payload(run)

    actual_suppression = dict(payloads["synonym-suppression-diff.json"])
    expected_suppression = dict(_build_synonym_suppression_diff_payload(run))
    actual_suppression.pop("created_at", None)
    expected_suppression.pop("created_at", None)
    assert actual_suppression == expected_suppression


def test_persist_terminal_run_artifact_mirror_writes_review_and_synonym_files(tmp_path, monkeypatch) -> None:
    run = _make_succeeded_run()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("fitcv_cp.run_artifact_mirror.get_run", lambda run_id: run)
    monkeypatch.setattr("fitcv_cp.run_artifact_mirror.get_events", lambda run_id: [])

    persist_terminal_run_artifact_mirror(run_id=run.run_id)

    mirror_dir = tmp_path / "artifacts" / f"live_run_{run.run_id}"
    assert (mirror_dir / "export.json").exists()
    assert (mirror_dir / "hitl-review-audit.json").exists()
    assert (mirror_dir / "synonym-proposals-trace.json").exists()
    assert (mirror_dir / "synonym-suppression-diff.json").exists()


def test_artifact_bundle_matches_endpoint_payloads_for_review_and_synonym_exports() -> None:
    run = _make_succeeded_run()
    with patch("fitcv_cp.app.get_run", return_value=run), patch("fitcv_cp.app.list_cvs_for_run", return_value=[]):
        client = TestClient(_app())
        bundle_response = client.get(f"/admin/runs/{run.run_id}/artifacts.zip")

        assert bundle_response.status_code == 200
        bundle_payloads: dict[str, dict] = {}
        with zipfile.ZipFile(io.BytesIO(bundle_response.content)) as zf:
            for name in (
                "results.json",
                "hitl-review-audit.json",
                "synonym-proposals-trace.json",
                "synonym-suppression-diff.json",
            ):
                bundle_payloads[name] = json.loads(zf.read(name).decode("utf-8"))

        endpoint_map = {
            "results.json": f"/admin/runs/{run.run_id}/export.json",
            "hitl-review-audit.json": f"/admin/runs/{run.run_id}/hitl-review-audit.json",
            "synonym-proposals-trace.json": f"/admin/runs/{run.run_id}/synonym-proposals-trace.json",
            "synonym-suppression-diff.json": f"/admin/runs/{run.run_id}/synonym-suppression-diff.json",
        }
        for filename, route in endpoint_map.items():
            response = client.get(route)
            assert response.status_code == 200
            assert bundle_payloads[filename] == json.loads(response.content)
