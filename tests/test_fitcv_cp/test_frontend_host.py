"""
@meta
type: test
scope: integration
domain: fitcv_frontend_host
covers:
  - /app SPA entry and deep linking
  - /app/assets static delivery
  - / redirect to /app
  - api route preservation
  - legacy /admin/* reachability
  - CSRF cookie and header enforcement
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from fitcv_cp.app import create_app, _resolve_frontend_dist_dir
from fitcv_cp.backend_runtime import BackendRuntime
from fitcv_cp.local_storage import _paths, migrate_packaged_local_integration_state
from fitcv_cp.sqlite_store import initialize_control_plane_database


@pytest.fixture
def local_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_CP_INLINE_EXECUTION", "1")
    monkeypatch.setenv("FITCV_LOCAL_DATA_ROOT", str(data_root))
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(data_root / "fitcv.sqlite3"))
    monkeypatch.setenv("FITCV_LOCAL_CANDIDATE_PROFILE_PATH", str(data_root / "candidate_profile.yaml"))
    monkeypatch.setenv("FITCV_LOCAL_CONTROLLER_OVERLAY_PATH", str(data_root / "config" / "local_controller_overlay.yaml"))
    monkeypatch.setenv("FITCV_LOCAL_ARTIFACTS_PATH", str(data_root / "artifacts"))
    monkeypatch.setenv("FITCV_LOCAL_EXPORTS_PATH", str(data_root / "exports"))
    monkeypatch.setenv("FITCV_LOCAL_LOGS_PATH", str(data_root / "logs"))
    monkeypatch.setenv("FITCV_LOCAL_BACKUPS_PATH", str(data_root / "backups"))
    monkeypatch.setenv("FITCV_LOCAL_UPLOADS_PATH", str(data_root / "uploads"))
    monkeypatch.setenv("FITCV_LOCAL_TEMP_PATH", str(data_root / "tmp"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    for name in ("config", "artifacts", "exports", "logs", "backups", "uploads", "tmp"):
        (data_root / name).mkdir(exist_ok=True)
    database_path = data_root / "fitcv.sqlite3"
    profile_path = data_root / "candidate_profile.yaml"
    initialize_control_plane_database(database_path, profile_path)
    migrate_packaged_local_integration_state(
        _paths(tmp_path / "roaming" / "FitCV" / "bootstrap.json", data_root)
    )
    app = create_app(
        redis_url="",
        backend_runtime=BackendRuntime(
            backend_type="sqlite",
            sqlite_path=str(data_root / "fitcv.sqlite3"),
        ),
    )
    app.state.run_store.list_runs_fn = lambda **_kwargs: []
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


def test_resolve_frontend_dist_dir_frozen_and_source():
    # Source mode
    dist_dir = _resolve_frontend_dist_dir()
    assert dist_dir.name == "dist"
    assert dist_dir.parent.name == "frontend"

    # Frozen mode
    with patch.object(sys, "_MEIPASS", "C:\\fake\\frozen", create=True):
        frozen_dist = _resolve_frontend_dist_dir()
        assert str(frozen_dist).replace("/", "\\").endswith("fake\\frozen\\frontend")


def test_local_root_redirects_to_app(local_client: TestClient):
    response = local_client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/app"


def test_app_spa_entry_and_deep_links(local_client: TestClient):
    # Root /app
    response = local_client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "FitCV" in response.text

    # Deep-link /app/candidate-profile
    deep_res = local_client.get("/app/candidate-profile")
    assert deep_res.status_code == 200
    assert "text/html" in deep_res.headers["content-type"]
    assert "FitCV" in deep_res.text


def test_api_routes_not_swallowed_by_app(local_client: TestClient):
    # Healthz
    health_res = local_client.get("/healthz")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    # Scans API
    scans_res = local_client.get("/scans")
    assert scans_res.status_code == 200

    # Runs API
    runs_res = local_client.get("/runs")
    assert runs_res.status_code == 200


def test_admin_routes_remain_accessible(local_client: TestClient):
    # Complete onboarding to test /admin/runs
    state_path = Path(os.environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state_path.write_text(json.dumps({"version": 1, "complete": True}), encoding="utf-8")

    # /admin/runs
    admin_res = local_client.get("/admin/runs")
    assert admin_res.status_code == 200
    assert "text/html" in admin_res.headers["content-type"]


def test_csrf_cookie_issuance_and_unsafe_request_guard(local_client: TestClient):
    # Initial GET sets cookie
    init_res = local_client.get("/app")
    assert init_res.status_code == 200
    assert "fitcv_csrf" in local_client.cookies

    csrf_token = local_client.cookies["fitcv_csrf"]
    assert len(csrf_token) > 20

    # POST without matching CSRF header/cookie fails with 403
    local_client.cookies.clear()
    bad_post = local_client.post(
        "/api-providers",
        json={"name": "test"},
        headers={"Origin": "http://127.0.0.1"},
    )
    assert bad_post.status_code == 403


def test_vite_dev_origin_can_submit_unsafe_local_request(local_client: TestClient):
    init_res = local_client.get("/healthz")
    csrf_token = local_client.cookies["fitcv_csrf"]

    response = local_client.post(
        "/api-providers",
        json={"display_name": "Local test provider", "compatibility": "openai"},
        headers={
            "Origin": "http://127.0.0.1:5173",
            "X-FitCV-CSRF": csrf_token,
            "Idempotency-Key": "vite-dev-origin-test",
        },
    )

    assert init_res.status_code == 200
    assert response.status_code != 403
