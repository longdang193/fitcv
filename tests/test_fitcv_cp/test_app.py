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

    def fake_enqueue_with_job(*args, **kwargs):
        call_order.append("enqueue")
        return "run-123", "rq-job-abc"

    with patch("fitcv_cp.app.insert_run", side_effect=fake_insert), \
         patch("fitcv_cp.app.enqueue_run_with_job_id", side_effect=fake_enqueue_with_job), \
         patch("fitcv_cp.app.update_run_queue_job_id"), \
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


# ── multi-file upload tests ────────────────────────────────────────────────────

_UPLOAD_COMMON_PATCHES = {
    "fitcv_cp.app.load_active_settings": lambda: {"return_value": {}},
}


def _upload_patches():
    return (
        patch("fitcv_cp.app.load_active_settings", return_value={}),
        patch("fitcv_cp.app.insert_run"),
        patch("fitcv_cp.app.enqueue_run_with_job_id", return_value=("run-multi", "rq-job-1")),
        patch("fitcv_cp.app.update_run_queue_job_id"),
        patch("fitcv_cp.app.load_config", return_value={
            "gcp_project": "p", "bigquery_dataset": "d", "service_account_key": "k",
            "pipeline": {"final_top_n": 10},
        }),
    )


def test_admin_upload_trigger_merges_multiple_job_files():
    """Two valid JSON files → 201, merged snapshot contains both jobs."""
    file1 = b'[{"title": "Engineer", "job_url": "http://a.com"}]'
    file2 = b'[{"title": "Analyst", "job_url": "http://b.com"}]'
    captured = {}

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run", side_effect=_capture_insert):
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
                files=[
                    ("jobs_files", ("file1.json", file1, "application/json")),
                    ("jobs_files", ("file2.json", file2, "application/json")),
                ],
            )

    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()
    merged = json.loads(captured["run"].jobs_input_json)
    urls = [j["job_url"] for j in merged]
    assert "http://a.com" in urls
    assert "http://b.com" in urls


def test_admin_upload_trigger_multi_file_preserves_order():
    """Merged snapshot preserves file order (file1 rows first, then file2)."""
    file1 = b'[{"job_url": "http://first.com"}]'
    file2 = b'[{"job_url": "http://second.com"}]'
    captured = {}

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run", side_effect=_capture_insert):
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
                files=[
                    ("jobs_files", ("a.json", file1, "application/json")),
                    ("jobs_files", ("b.json", file2, "application/json")),
                ],
            )

    assert resp.status_code == 201, resp.text
    merged = json.loads(captured["run"].jobs_input_json)
    assert [j["job_url"] for j in merged] == ["http://first.com", "http://second.com"]


def test_admin_upload_trigger_one_invalid_file_rejects_entire_request():
    """One file with invalid JSON → 422; run must NOT be created."""
    file1 = b'[{"job_url": "http://good.com"}]'
    file2 = b'THIS IS NOT JSON'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.insert_run") as mock_insert:
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
                files=[
                    ("jobs_files", ("good.json", file1, "application/json")),
                    ("jobs_files", ("bad.json", file2, "application/json")),
                ],
            )
    assert resp.status_code == 422
    mock_insert.assert_not_called()


def test_admin_upload_trigger_all_empty_arrays_rejected():
    """Two files both containing empty arrays → 422 (total merged is empty)."""
    file1 = b'[]'
    file2 = b'[]'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
            files=[
                ("jobs_files", ("a.json", file1, "application/json")),
                ("jobs_files", ("b.json", file2, "application/json")),
            ],
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_upload_mode_no_files_rejected():
    """Upload mode with neither jobs_file nor jobs_files → 422."""
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_multi_file_non_array_rejected():
    """A file whose top-level is not a JSON array → 422."""
    file1 = b'{"title": "not an array"}'
    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).post(
            "/admin/upload-trigger",
            data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
            files=[
                ("jobs_files", ("dict.json", file1, "application/json")),
            ],
        )
    assert resp.status_code == 422


def test_admin_upload_trigger_effective_settings_includes_enrichment_parallelism():
    """Trigger run with mocked active settings containing batch_size/concurrency → stored in effective_settings_json."""
    active = {"enrichment_batch_size": 5, "enrichment_concurrency": 3}
    captured = {}

    def _capture_insert(run, *args, **kwargs):
        captured["run"] = run

    p = _upload_patches()
    with p[0], p[1], p[2], p[3], p[4]:
        with patch("fitcv_cp.app.load_active_settings", return_value=active), \
             patch("fitcv_cp.app.insert_run", side_effect=_capture_insert):
            file1 = b'[{"job_url": "http://e.com"}]'
            resp = TestClient(_app()).post(
                "/admin/upload-trigger",
                data={"jobs_input_mode": "upload", "candidate_profile_mode": "default_config"},
                files=[
                    ("jobs_files", ("e.json", file1, "application/json")),
                ],
            )

    assert resp.status_code == 201, resp.text
    effective = json.loads(captured["run"].effective_settings_json)
    assert effective.get("enrichment_batch_size") == 5
    assert effective.get("enrichment_concurrency") == 3



# ── html routes ──────────────────────────────────────────────────────────────

def test_admin_runs_rendered_nav():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    assert 'href="/admin/settings">Settings</a>' in resp.text
    assert 'Refresh' in resp.text
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
    assert "Refresh Status" in resp.text  # still present on run_detail page


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


# ── Lifecycle API routes ─────────────────────────────────────────────────────

def _make_run_mock(status="queued", archived_at=None, queue_job_id="rq-job-1"):
    from fitcv_cp.models import PipelineRun, RunStatus
    import datetime
    return PipelineRun(
        run_id="run-lifecycle-1",
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        queue_job_id=queue_job_id,
        archived_at=archived_at,
    )


def test_admin_stop_queued_run_returns_json():
    run = _make_run_mock(status="queued")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.cancel_queued_run", return_value=True), \
         patch("fitcv_cp.app.request_run_cancel"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 200
    assert "cancelled" in resp.json().get("status", "")


def test_admin_stop_succeeded_run_returns_409():
    run = _make_run_mock(status="succeeded")
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/stop")
    assert resp.status_code == 409


def test_admin_stop_unknown_run_returns_404():
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).post("/admin/runs/nonexistent/stop")
    assert resp.status_code == 404


def test_admin_archive_succeeded_run_returns_json():
    run = _make_run_mock(status="succeeded")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.archive_run"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/archive")
    assert resp.status_code == 200


def test_admin_archive_running_run_returns_409():
    run = _make_run_mock(status="running")
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/archive")
    assert resp.status_code == 409


def test_admin_unarchive_archived_run_returns_json():
    import datetime
    run = _make_run_mock(status="succeeded", archived_at=datetime.datetime.now(datetime.timezone.utc))
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.unarchive_run"), \
         patch("fitcv_cp.app.append_event"):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/unarchive")
    assert resp.status_code == 200


def test_admin_unarchive_non_archived_run_returns_409():
    run = _make_run_mock(status="succeeded", archived_at=None)
    with patch("fitcv_cp.app.get_run", return_value=run):
        resp = TestClient(_app()).post("/admin/runs/run-lifecycle-1/unarchive")
    assert resp.status_code == 409


def test_admin_runs_active_view_passes_archive_filter():
    with patch("fitcv_cp.app.list_runs", return_value=[]) as mock_list:
        resp = TestClient(_app()).get("/admin/runs?view=active")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args[1]
    assert call_kwargs.get("include_archived") is False
    assert call_kwargs.get("archived_only", False) is False


def test_admin_runs_archived_view_passes_archived_only():
    with patch("fitcv_cp.app.list_runs", return_value=[]) as mock_list:
        resp = TestClient(_app()).get("/admin/runs?view=archived")
    assert resp.status_code == 200
    call_kwargs = mock_list.call_args[1]
    assert call_kwargs.get("archived_only") is True


# ── Task 5: Admin UI lifecycle controls ─────────────────────────────────────

def _make_full_run_mock(status="queued", archived_at=None, run_id="run-ui-1"):
    from fitcv_cp.models import PipelineRun, RunStatus
    import datetime
    return PipelineRun(
        run_id=run_id,
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 3, 26, 12, 0, 0, tzinfo=datetime.timezone.utc),
        archived_at=archived_at,
    )


def test_runs_list_shows_active_all_archived_filter_tabs():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs")
    assert resp.status_code == 200
    body = resp.text
    assert "Active" in body
    assert "Archived" in body
    assert "All" in body


def test_runs_list_queued_row_shows_stop_button():
    run = _make_full_run_mock(status="queued")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert "Stop Run" in resp.text


def test_runs_list_running_row_shows_stop_button():
    run = _make_full_run_mock(status="running")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert "Stop Run" in resp.text


def test_runs_list_succeeded_row_shows_archive_button():
    run = _make_full_run_mock(status="succeeded")
    with patch("fitcv_cp.app.list_runs", return_value=[run]):
        resp = TestClient(_app()).get("/admin/runs")
    assert "Archive" in resp.text


def test_run_detail_queued_shows_stop_run():
    import datetime
    run = _make_full_run_mock(status="queued")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-ui-1")
    assert resp.status_code == 200
    assert "Stop Run" in resp.text


def test_run_detail_succeeded_shows_archive_run():
    run = _make_full_run_mock(status="succeeded")
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-ui-1")
    assert resp.status_code == 200
    assert "Archive Run" in resp.text


def test_run_detail_archived_shows_unarchive_and_badge():
    import datetime
    run = _make_full_run_mock(status="succeeded", archived_at=datetime.datetime(2026, 3, 26, 13, 0, 0, tzinfo=datetime.timezone.utc))
    with patch("fitcv_cp.app.get_run", return_value=run), \
         patch("fitcv_cp.app.get_events", return_value=[]), \
         patch("fitcv_cp.app.list_cvs_for_run", return_value=[]), \
         patch("fitcv_cp.app.list_run_structured_jobs", return_value=[]), \
         patch("fitcv_cp.app.list_filter_results_for_run", return_value=[]):
        resp = TestClient(_app()).get("/admin/runs/run-ui-1")
    assert resp.status_code == 200
    assert "Unarchive Run" in resp.text
    assert "Archived" in resp.text


# ── Component 1: app.py server-side enrichment ───────────────────────────────

def _run_detail_patches(
    status="succeeded",
    cv_versions=None,
    enriched_jobs=None,
    filter_results=None,
):
    import datetime
    from fitcv_cp.models import PipelineRun, RunStatus
    run = PipelineRun(
        run_id="run-detail-test",
        status=RunStatus(status),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime(2026, 3, 27, 9, 0, 0, tzinfo=datetime.timezone.utc),
    )
    return (
        patch("fitcv_cp.app.get_run", return_value=run),
        patch("fitcv_cp.app.get_events", return_value=[]),
        patch("fitcv_cp.app.list_cvs_for_run", return_value=cv_versions or []),
        patch("fitcv_cp.app.list_run_structured_jobs", return_value=enriched_jobs or []),
        patch("fitcv_cp.app.list_filter_results_for_run", return_value=filter_results or []),
    )


def test_run_detail_cv_versions_show_job_title():
    """CV output link uses the enriched job title instead of generic 'View Job'."""
    cv = {"version_id": "cv1", "job_url": "https://jobs.example.com/1",
          "fit_classification": "strong",
          "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)}
    enriched = [{"job_url": "https://jobs.example.com/1", "title": "Senior Data Engineer",
                 "domain": "data", "job_family": "engineering", "required_skills": [],
                 "location_type": "remote", "seniority": "senior"}]
    patches = _run_detail_patches(cv_versions=[cv], enriched_jobs=enriched,
                                  filter_results=[{"job_url": "https://jobs.example.com/1",
                                                   "passed": True, "reasons": []}])
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert resp.status_code == 200
    assert "Senior Data Engineer" in resp.text
    assert "View Job" not in resp.text.split("Senior Data Engineer")[0].split("Generated Outputs")[-1]


def test_run_detail_cv_versions_fallback_when_no_title():
    """CV output link falls back to 'View Job' when no enriched job matches the job_url."""
    import datetime as _dt
    cv = {"version_id": "cv2", "job_url": "https://jobs.example.com/orphan",
          "fit_classification": "strong",
          "generated_at": _dt.datetime.now(_dt.timezone.utc)}
    # Run must have cvs_generated > 0 for the pipeline results section to render
    patches = _run_detail_patches(cv_versions=[cv], enriched_jobs=[])
    # Override the run object to have cvs_generated set
    import datetime as _dt2
    from fitcv_cp.models import PipelineRun, RunStatus
    run_with_cv = PipelineRun(
        run_id="run-detail-test",
        status=RunStatus("succeeded"),
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=_dt2.datetime(2026, 3, 27, 9, 0, 0, tzinfo=_dt2.timezone.utc),
        cvs_generated=1,
    )
    with patch("fitcv_cp.app.get_run", return_value=run_with_cv), \
         patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert resp.status_code == 200
    assert "View Job" in resp.text


def test_run_detail_enriched_shows_summary_counts():
    """Enriched tab renders Total, Passed, Rejected summary counts."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    fr = [{"job_url": "https://j.test/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert "Total:" in resp.text
    assert "Passed:" in resp.text
    assert "Rejected:" in resp.text


def test_run_detail_enriched_shows_filter_controls():
    """Filter buttons All, Passed, Rejected are present (only rendered when enriched_jobs is non-empty)."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    patches = _run_detail_patches(enriched_jobs=enriched)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert "setFilter('all')" in resp.text or ">All<" in resp.text
    assert "setFilter('passed')" in resp.text or ">Passed<" in resp.text
    assert "setFilter('rejected')" in resp.text or ">Rejected<" in resp.text


def test_run_detail_enriched_shows_search_box():
    """Search input with id='enr-search' is present (only rendered when enriched_jobs is non-empty)."""
    enriched = [{"job_url": "https://j.test/1", "title": "A", "domain": "d",
                 "job_family": "f", "required_skills": [], "location_type": None, "seniority": None}]
    patches = _run_detail_patches(enriched_jobs=enriched)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert 'id="enr-search"' in resp.text


def test_run_detail_enriched_rows_have_data_attributes():
    """Enriched job rows have data-filter, data-title, data-domain, data-family attributes."""
    enriched = [{"job_url": "https://j.test/1", "title": "ML Engineer", "domain": "AI",
                 "job_family": "engineering", "required_skills": [], "location_type": None, "seniority": None}]
    fr = [{"job_url": "https://j.test/1", "passed": True, "reasons": []}]
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert 'data-filter=' in resp.text
    assert 'data-title=' in resp.text
    assert 'data-domain=' in resp.text
    assert 'data-family=' in resp.text


def test_run_detail_enriched_shows_pagination():
    """Pagination controls are present for the enriched jobs tab."""
    patches = _run_detail_patches()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert "enr-prev" in resp.text or "Prev" in resp.text


def test_run_detail_enriched_unknown_filter_not_counted_as_rejected():
    """A job with no filter result gets data-filter=unknown and is not counted as rejected."""
    enriched = [
        {"job_url": "https://j.test/pass", "title": "Engineer A", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
        {"job_url": "https://j.test/no-fr", "title": "Engineer B", "domain": "d",
         "job_family": "f", "required_skills": [], "location_type": None, "seniority": None},
    ]
    fr = [{"job_url": "https://j.test/pass", "passed": True, "reasons": []}]
    # j.test/no-fr has no filter result → must be 'unknown', not 'rejected'
    patches = _run_detail_patches(enriched_jobs=enriched, filter_results=fr)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        resp = TestClient(_app()).get("/admin/runs/run-detail-test")
    assert 'data-filter="unknown"' in resp.text
    # Rejected count should be 0 (no explicit reject), not 1
    assert "Rejected: 0" in resp.text



# ── Task 6: Composition consistency tests ──────────────────────────────────────

def test_settings_ranking_section_has_no_tailwind_classes():
    """The ranking section must not contain Tailwind class names in the rendered HTML."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    # Find the ranking section
    ranking_start = html.index("Ranking Weights")
    section_slice = html[ranking_start:ranking_start + 3000]
    tailwind_prefixes = ("text-gray-", "bg-slate-", "bg-indigo-", "text-indigo-", "rounded-", "px-", "py-", "mb-", "mt-", "mr-", "ml-", "gap-", "border-")
    for prefix in tailwind_prefixes:
        assert prefix not in section_slice, f"Tailwind class '{prefix}' found in ranking section"


def test_settings_ranking_contains_three_sub_cards():
    """The ranking section must render exactly three .sub-card elements."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    # Count occurrences of class="sub-card" (each sub-card has exactly this class attribute)
    count = html.count('class="sub-card"')
    assert count >= 3, f"Expected at least 3 sub-card elements, got {count}"


def test_settings_ranking_sub_cards_have_save_buttons_with_correct_form_targets():
    """Each ranking sub-card must have a submit button inside its group form."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}):
        resp = TestClient(_app()).get("/admin/settings")
    assert resp.status_code == 200
    html = resp.text
    for form_id in ("form-ranking-weights", "form-fit-label-thresholds", "form-gap-thresholds"):
        # Locate the form element
        form_open = f'<form id="{form_id}"'
        form_start = html.index(form_open)
        form_end = html.index("</form>", form_start)
        form_body = html[form_start:form_end]
        # The submit button must be nested inside the form (not using form= attribute)
        assert '<button type="submit"' in form_body, f"Submit button inside form '{form_id}' not found"


def test_run_detail_inspection_area_wrapped_in_inspection_card():
    """The inspection area must be wrapped in .inspection-card, with tab bar inside."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    run = PipelineRun(
        run_id="composition-test-1", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/composition-test-1")
    assert resp.status_code == 200
    html = resp.text
    # .inspection-card must appear in the HTML
    assert 'class="inspection-card"' in html
    # Verify the tab bar is actually INSIDE the card (not just later in the document).
    # Find the card's opening position and its closing </div><!-- /.inspection-card -->.
    card_pos = html.index('class="inspection-card"')
    card_close_pos = html.index('</div><!-- /.inspection-card -->', card_pos)
    # Now find the first tab button and verify it is between the open and close.
    tab_btn_pos = html.index('id="tab-btn-enriched"')
    assert card_pos < tab_btn_pos < card_close_pos, (
        "Tab bar button is not inside .inspection-card. "
        f"card={card_pos}, tab_btn={tab_btn_pos}, card_close={card_close_pos}"
    )


def test_run_detail_tab_bar_uses_attached_modifier():
    """The tab bar must use .tab-bar--attached (not the old .tab-bar)."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    run = PipelineRun(
        run_id="composition-test-2", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/composition-test-2")
    assert resp.status_code == 200
    html = resp.text
    # .tab-bar--attached must be present
    assert 'tab-bar--attached' in html, 'class="tab-bar--attached" not found in rendered HTML'
    # The bare "tab-bar" class (without --attached) must NOT appear as the opening class attribute
    # Check around the tab-bar element: find a position where class= is followed by tab-bar
    # Use token-level check: split on 'class="' and look at tokens
    import re
    class_tokens = re.findall(r'class="([^"]*)"', html)
    bare_tab_bar_in_classes = any('tab-bar' in token and 'tab-bar--attached' not in token for token in class_tokens)
    assert not bare_tab_bar_in_classes, "Bare 'tab-bar' class found in rendered HTML (should be 'tab-bar--attached')"


def test_run_detail_panes_use_pane_container():
    """All three inspection panes must use .pane-container alongside .tab-pane."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    run = PipelineRun(
        run_id="composition-test-3", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/composition-test-3")
    assert resp.status_code == 200
    html = resp.text
    for pane_id in ("pane-enriched", "pane-jobs-input", "pane-profile"):
        pane_pos = html.index(f'id="{pane_id}"')
        # Check that "pane-container" appears within 100 chars before the pane id (it's on the same div's class attribute)
        context = html[max(0, pane_pos - 100):pane_pos + len(pane_id) + 10]
        assert "pane-container" in context, f"'pane-container' not found near {pane_id} pane"


def test_run_detail_no_page_local_tab_style_inside_inspection_area():
    """No <style> tag may appear between the inspection card open and the first tab button."""
    from fitcv_cp.models import PipelineRun, RunStatus
    from datetime import datetime, timezone
    run = PipelineRun(
        run_id="composition-test-4", status=RunStatus.SUCCEEDED,
        jobs_path="data/sample_jobs.json", triggered_by="admin",
        trigger_source="web", config_path=".env.yaml",
        created_at=datetime.now(timezone.utc),
    )
    p = _run_detail_base_patches(run)
    with p[0], p[1], p[2], p[3], p[4]:
        resp = TestClient(_app()).get("/admin/runs/composition-test-4")
    assert resp.status_code == 200
    html = resp.text
    # Find the .inspection-card region (open to close)
    card_pos = html.index('class="inspection-card"')
    card_close_pos = html.index('</div><!-- /.inspection-card -->', card_pos)
    card_region = html[card_pos:card_close_pos]
    # No <style> tag may appear inside the inspection card region
    assert "<style>" not in card_region, (
        "Page-local <style> tag found inside .inspection-card region — "
        "tab styling should use shared CSS from base.html"
    )
