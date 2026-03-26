from unittest.mock import MagicMock, patch
import json
from fastapi.testclient import TestClient
from fitcv_cp.app import create_app


def _app():
    bq = MagicMock()
    return create_app(bq=bq, project="p", dataset="d", redis_url="redis://localhost:6379/0")


def test_post_runs_inserts_before_enqueue():
    """BQ insert must happen before enqueue to ensure DB is source of truth."""
    call_order = []

    def fake_insert(*args, **kwargs):
        call_order.append("insert")

    def fake_enqueue(*args, **kwargs):
        call_order.append("enqueue")
        return "run-123"

    with patch("fitcv_cp.app.insert_run", side_effect=fake_insert), \
         patch("fitcv_cp.app.enqueue_run", side_effect=fake_enqueue), \
         patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p", "bigquery_dataset": "d", "service_account_key": "k",
             "pipeline": {"final_top_n": 10}
         }):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": "data/sample_jobs.json"})
    assert resp.status_code == 201
    assert "run_id" in resp.json()
    assert call_order == ["insert", "enqueue"], f"Order was: {call_order}"


def test_post_runs_rejects_empty_jobs_path():
    resp = TestClient(_app()).post("/runs", json={"jobs_path": ""})
    assert resp.status_code == 422


def test_get_runs_returns_list():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_run_detail_not_found():
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).get("/runs/missing-id")
    assert resp.status_code == 404


def test_get_run_events():
    with patch("fitcv_cp.app.get_run", return_value=MagicMock()), \
         patch("fitcv_cp.app.get_events", return_value=[]):
        resp = TestClient(_app()).get("/runs/some-id/events")
    assert resp.status_code == 200


def test_healthz():
    resp = TestClient(_app()).get("/healthz")
    assert resp.status_code == 200


# ── settings API ─────────────────────────────────────────────────────────────

def test_get_settings_returns_dict():
    with patch("fitcv_cp.app.load_active_settings", return_value={"pipeline.final_top_n": 5}):
        resp = TestClient(_app()).get("/settings")
    assert resp.status_code == 200
    assert resp.json()["pipeline.final_top_n"] == 5


def test_post_settings_key_saves_and_returns_200():
    with patch("fitcv_cp.app.save_setting") as mock_save:
        resp = TestClient(_app()).post(
            "/settings/pipeline.final_top_n",
            json={"value": 7, "updated_by": "admin"},
        )
    assert resp.status_code == 200
    mock_save.assert_called_once()


def test_post_settings_key_rejects_invalid_value():
    resp = TestClient(_app()).post(
        "/settings/pipeline.final_top_n",
        json={"value": 0, "updated_by": "admin"},  # 0 violates int >= 1
    )
    assert resp.status_code == 422


def test_post_settings_key_rejects_unknown_key():
    resp = TestClient(_app()).post(
        "/settings/unknown.key",
        json={"value": 1, "updated_by": "admin"},
    )
    assert resp.status_code == 422


def test_post_runs_with_config_overrides():
    """POST /runs with per-run overrides snapshot effective settings."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.enqueue_run", return_value="run-123"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p", "bigquery_dataset": "d", "service_account_key": "k",
             "pipeline": {"final_top_n": 10}
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": "data/sample_jobs.json",
            "config_overrides": {"pipeline.final_top_n": 5},
        })
    assert resp.status_code == 201
    assert "run_id" in resp.json()


def test_post_runs_rejects_invalid_config_overrides():
    resp = TestClient(_app()).post("/runs", json={
        "jobs_path": "data/sample_jobs.json",
        "config_overrides": {"pipeline.final_top_n": 0},  # violates >= 1
    })
    assert resp.status_code == 422


def test_admin_upload_trigger_success(tmp_path):
    """Test POST /admin/upload-trigger saves file and calls trigger logic."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.enqueue_run", return_value="run-123"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project": "p", "bigquery_dataset": "d", "service_account_key": "k",
             "pipeline": {"final_top_n": 10},
             "paths": {"candidate_profile": "/tmp/dummy.yaml"},
         }):

        file_content = b'[{"title": "Engineer", "job_url": "http://x.com"}]'
        files = {"jobs_file": ("custom_jobs.json", file_content, "application/json")}
        data = {
            "config_path": ".env.yaml",
            "jobs_input_mode": "upload",
            "candidate_profile_mode": "default_config",
        }

        resp = TestClient(_app()).post("/admin/upload-trigger", data=data, files=files)

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()



# ── html routes ──────────────────────────────────────────────────────────────

def test_admin_runs_rendered_nav():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    assert 'href="/admin/settings">Settings</a>' in resp.text
    assert 'Refresh Status' in resp.text
    assert 'id="jobs_file"' in resp.text
    assert 'id="jobs_path"' in resp.text


def test_admin_run_detail_success_banner():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    
    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-123", status=RunStatus.SUCCEEDED, 
        cvs_generated=5, total_jobs=10, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path="config/default.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[{"version_id": "v123", "job_url": "mock.com", "fit_classification": "strong", "generated_at": datetime.now(timezone.utc)}]):
        resp = TestClient(_app()).get("/admin/runs/test-123")
    assert resp.status_code == 200
    assert "candidate CV(s) were successfully generated." in resp.text
    assert "Persisted to the <strong>cv_versions</strong> BigQuery table." in resp.text
    assert 'href="/admin/cvs/v123/download"' in resp.text
    assert 'href="/admin/runs/test-123"' in resp.text
    assert "Refresh Status" in resp.text


def test_admin_run_detail_warning_banner():
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    
    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-124", status=RunStatus.SUCCEEDED, 
        cvs_generated=0, total_jobs=10, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path="config/default.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-124")
    assert resp.status_code == 200
    assert "No candidates passed the final AI ranking threshold." in resp.text

def test_download_cv_endpoint_200():
    with patch("fitcv_cp.app.get_cv_markdown", return_value="# Mock CV"):
        resp = TestClient(_app()).get("/admin/cvs/v456/download")
    assert resp.status_code == 200
    assert resp.text == "# Mock CV"
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment; filename=\"cv_v456.md\"" in resp.headers["content-disposition"]

def test_download_cv_endpoint_404():
    with patch("fitcv_cp.app.get_cv_markdown", return_value=None):
        resp = TestClient(_app()).get("/admin/cvs/missing/download")
    assert resp.status_code == 404


# ── enriched jobs on run detail ──────────────────────────────────────────────

def test_admin_run_detail_shows_enriched_jobs_section():
    """Run detail page renders Enriched Jobs section when rows are returned."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-123",
            "job_url": "https://example.com/job/1",
            "title": "Senior Data Engineer",
            "location_type": "remote",
            "seniority": "senior",
            "job_family": "data_engineering",
            "domain": "fintech",
            "required_skills": ["SQL", "Python", "Spark"],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-123", status=RunStatus.SUCCEEDED,
        cvs_generated=1, total_jobs=5, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-123")

    assert resp.status_code == 200
    assert "Enriched Jobs" in resp.text
    assert "Senior Data Engineer" in resp.text
    assert "remote" in resp.text
    assert "senior" in resp.text
    assert "data_engineering" in resp.text
    assert "fintech" in resp.text


def test_admin_run_detail_empty_enriched_jobs_renders_gracefully():
    """Run detail page handles empty enriched_jobs without errors."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-empty", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=3, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/test-empty")

    assert resp.status_code == 200
    assert "Enriched Jobs" in resp.text
    # empty state message
    assert "No enrichment data" in resp.text or "enriched" in resp.text.lower()


def test_admin_run_detail_enriched_jobs_shows_required_skills():
    """Run detail renders required_skills from enriched job rows."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    enriched_jobs = [
        {
            "run_id": "test-456",
            "job_url": "https://example.com/job/2",
            "title": "ML Engineer",
            "location_type": "hybrid",
            "seniority": "mid",
            "job_family": "ml_engineering",
            "domain": "healthcare",
            "required_skills": ["Python", "TensorFlow", "Kubernetes"],
        }
    ]

    with patch("fitcv_cp.app.get_run", return_value=PipelineRun(
        run_id="test-456", status=RunStatus.SUCCEEDED,
        cvs_generated=0, total_jobs=1, jobs_path="",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc)
    )), patch("fitcv_cp.app.get_events", return_value=[]), \
    patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
    patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs):
        resp = TestClient(_app()).get("/admin/runs/test-456")

    assert resp.status_code == 200
    assert "Python" in resp.text
    assert "TensorFlow" in resp.text
    assert "https://example.com/job/2" in resp.text






# ── Inspection Tab Tests ──────────────────────────────────────────────────────


def _run_detail_base_patches(run_obj):
    """Return tuple of patchers for standard run detail route dependencies."""
    return (
        patch("fitcv_cp.app.get_run", return_value=run_obj),
        patch("fitcv_cp.app.get_events", return_value=[]),
        patch("fitcv_cp.app.list_cvs_for_run", return_value=[]),
        patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]),
        patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]),
    )


def test_run_detail_default_tab_is_enriched():
    """Enriched Jobs pane must be active by default on page load."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-1", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-1")

    assert resp.status_code == 200
    html = resp.text
    assert 'id="pane-enriched"' in html
    assert 'id="tab-btn-enriched"' in html
    # active class must be on the enriched pane (class attr comes before id= in HTML)
    pane_pos = html.index('id="pane-enriched"')
    assert "active" in html[max(0, pane_pos - 60):pane_pos + 50]
    # active class must be on the enriched tab button
    btn_pos = html.index('id="tab-btn-enriched"')
    assert "active" in html[max(0, btn_pos - 80):btn_pos + 10]


def test_run_detail_tab2_fallback_when_no_jobs_snapshot():
    """Tab 2 shows source/path fallback when jobs_input_json is absent."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-2", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", jobs_input_source="path",
        jobs_input_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-2")

    assert resp.status_code == 200
    html = resp.text
    assert "No immutable raw snapshot" in html
    assert "data/sample_jobs.json" in html


def test_run_detail_tab3_null_source_shows_not_recorded_not_default_config():
    """Tab 3 fallback must not infer 'default_config' when source is NULL."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-3", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        candidate_profile_source=None,
        candidate_profile_json=None,
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-3")

    assert resp.status_code == 200
    html = resp.text
    assert "No candidate profile snapshot" in html
    pane_start = html.index('id="pane-profile"')
    pane_html = html[pane_start:pane_start + 2000]
    assert "not recorded" in pane_html
    assert "default_config" not in pane_html


def test_run_detail_event_timeline_appears_after_tab_panes():
    """Event Timeline heading must come after all 3 tab panes in the HTML."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone

    run = PipelineRun(
        run_id="tab-test-4", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json",
        triggered_by="admin", trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/tab-test-4")

    assert resp.status_code == 200
    html = resp.text
    profile_pane_pos = html.index('id="pane-profile"')
    timeline_pos = html.index("Event Timeline")
    assert timeline_pos > profile_pane_pos, (
        "Event Timeline must appear after all tab panes in the HTML"
    )


# ── grouped settings endpoint ─────────────────────────────────────────────────

_VALID_WEIGHTS = {
    "ranking_weights.ai_score": "0.40",
    "ranking_weights.must_have_match": "0.20",
    "ranking_weights.vector_similarity": "0.15",
    "ranking_weights.title_relevance": "0.10",
    "ranking_weights.seniority_fit": "0.10",
    "ranking_weights.preference_fit": "0.05",
}


def test_grouped_save_valid_ranking_weights_redirects():
    """Valid 6-weight form POST → 303 redirect; save_settings_group called."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/ranking-weights",
            data=_VALID_WEIGHTS,
        )
    assert resp.status_code == 303
    mock_group_save.assert_called_once()
    saved_keys = set(mock_group_save.call_args[0][0].keys())
    assert saved_keys == set(_VALID_WEIGHTS.keys())


def test_grouped_save_weights_dont_sum_to_one_returns_422():
    """Weights summing to 0.9 → 422; no write."""
    bad_weights = dict(_VALID_WEIGHTS)
    bad_weights["ranking_weights.ai_score"] = "0.30"  # sum = 0.90
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/ranking-weights",
            data=bad_weights,
        )
    assert resp.status_code == 422
    mock_group_save.assert_not_called()


def test_grouped_save_weights_error_preserved_in_response():
    """Error response must contain the submitted form values (so admin can correct)."""
    bad_weights = dict(_VALID_WEIGHTS)
    bad_weights["ranking_weights.ai_score"] = "0.30"  # sum ≠ 1.0
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/ranking-weights",
            data=bad_weights,
        )
    assert resp.status_code == 422
    # The form values must persist (input elements show the submitted values)
    assert "0.30" in resp.text


def test_grouped_save_fit_label_thresholds_valid():
    """strong > stretch → 303 redirect; 2 keys saved."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "fit_label_thresholds.strong": "0.70",
                "fit_label_thresholds.stretch": "0.40",
            },
        )
    assert resp.status_code == 303
    mock_group_save.assert_called_once()


def test_grouped_save_fit_label_thresholds_invalid_order():
    """stretch > strong → 422; no write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "fit_label_thresholds.strong": "0.40",
                "fit_label_thresholds.stretch": "0.70",
            },
        )
    assert resp.status_code == 422
    mock_group_save.assert_not_called()


def test_grouped_save_gap_thresholds_valid():
    """strong_min > stretch_min → 303."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/gap-thresholds",
            data={
                "gap_thresholds.strong_min_matched_ratio": "0.80",
                "gap_thresholds.stretch_min_matched_ratio": "0.50",
            },
        )
    assert resp.status_code == 303
    mock_group_save.assert_called_once()


def test_grouped_save_gap_thresholds_invalid_order():
    """stretch_min > strong_min → 422; no write."""
    with patch("fitcv_cp.app.save_settings_group") as mock_group_save, \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/gap-thresholds",
            data={
                "gap_thresholds.strong_min_matched_ratio": "0.30",
                "gap_thresholds.stretch_min_matched_ratio": "0.80",
            },
        )
    assert resp.status_code == 422
    mock_group_save.assert_not_called()


def test_grouped_save_unknown_group_returns_404():
    """Unknown group name → 404."""
    resp = TestClient(_app()).post(
        "/admin/settings/group/nonexistent",
        data={"some.key": "1"},
    )
    assert resp.status_code == 404


def test_grouped_save_bq_error_returns_422_not_303():
    """BQ failure from save_settings_group → 422 error page, not a redirect."""
    with patch("fitcv_cp.app.save_settings_group", side_effect=RuntimeError("BQ failed")), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "fit_label_thresholds.strong": "0.70",
                "fit_label_thresholds.stretch": "0.40",
            },
        )
    assert resp.status_code == 422
    assert "BQ failed" in resp.text


def test_grouped_save_audit_identity_encoded_in_updated_by():
    """Each group save uses updated_by='admin:grp:{uuid}'."""
    captured = {}

    def fake_save(keys_values, *, updated_by, bq, project, dataset):
        captured["updated_by"] = updated_by

    with patch("fitcv_cp.app.save_settings_group", side_effect=fake_save), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/group/fit-label-thresholds",
            data={
                "fit_label_thresholds.strong": "0.70",
                "fit_label_thresholds.stretch": "0.40",
            },
        )
    assert captured.get("updated_by", "").startswith("admin:grp:")


# ── POST /admin/settings/section/{section_name} ───────────────────────────────

def test_post_settings_section_valid_redirects():
    """Valid payload for retrieval section returns 303."""
    with patch("fitcv_cp.app.save_settings_group"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval",
            data={
                "pipeline.vector_search_top_n": "100",
                "pipeline.ai_score_top_n": "20",
                "pipeline.final_top_n": "10",
                "pipeline.evidence_top_k": "5",
            },
        )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/settings"


def test_post_settings_section_unknown_returns_404():
    with patch("fitcv_cp.app.save_settings_group"), \
         patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/does-not-exist",
            data={"some.key": "1"},
        )
    assert resp.status_code == 404


def test_post_settings_section_invalid_value_returns_422():
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app(), follow_redirects=False).post(
            "/admin/settings/section/retrieval",
            data={
                "pipeline.vector_search_top_n": "not-a-number",
                "pipeline.ai_score_top_n": "20",
                "pipeline.final_top_n": "10",
                "pipeline.evidence_top_k": "5",
            },
        )
    assert resp.status_code == 422


def test_get_settings_renders_section_save_actions():
    """GET /admin/settings renders section-level save labels, not per-row Save buttons."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    body = resp.text
    assert "Save Retrieval Settings" in body
    assert "Save Timing Settings" in body
    assert "Save Global Job Filters" in body
