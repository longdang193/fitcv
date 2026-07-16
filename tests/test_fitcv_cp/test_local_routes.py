"""
@meta
type: test
scope: integration
domain: fitcv_local_onboarding
covers:
  - packaged route security
  - resumable onboarding
  - provider discovery and readiness
excludes:
  - live provider calls
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import BackendRuntime


@pytest.fixture
def local_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_CP_INLINE_EXECUTION", "1")
    monkeypatch.setenv("FITCV_LOCAL_DATA_ROOT", str(data_root))
    monkeypatch.setenv("FITCV_LOCAL_CANDIDATE_PROFILE_PATH", str(data_root / "candidate_profile.yaml"))
    monkeypatch.setenv("FITCV_LOCAL_ROUTING_OVERLAY_PATH", str(data_root / "routing.yaml"))
    app = create_app(
        redis_url="",
        backend_runtime=BackendRuntime(
            backend_type="sqlite",
            sqlite_path=str(data_root / "fitcv.sqlite3"),
        ),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


def _csrf_headers(client: TestClient) -> dict[str, str]:
    return {
        "Origin": "http://127.0.0.1",
        "X-FitCV-CSRF": str(client.app.state.csrf_token),
    }


def test_wrong_host_is_rejected(local_client: TestClient) -> None:
    response = local_client.get("/local/onboarding", headers={"Host": "evil.example"})

    assert response.status_code == 403


def test_every_unsafe_route_requires_same_origin(local_client: TestClient) -> None:
    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}
    routes = [
        (method, route.path)
        for route in local_client.app.routes
        for method in sorted(set(route.methods or ()) & unsafe_methods)
    ]

    assert routes
    for method, path in routes:
        response = local_client.request(method, path)
        assert response.status_code == 403, (method, path, response.text)


def test_onboarding_sets_csrf_cookie_and_redirects_incomplete_app(local_client: TestClient) -> None:
    onboarding = local_client.get("/local/onboarding")
    redirect = local_client.get("/admin/runs", follow_redirects=False)

    assert onboarding.status_code == 200
    assert onboarding.cookies.get("fitcv_csrf") == local_client.app.state.csrf_token
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/local/onboarding"


def test_onboarding_resumes_saved_step(local_client: TestClient) -> None:
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "current_step": "models",
                "complete": False,
                "provider_test_ok": False,
            }
        ),
        encoding="utf-8",
    )

    response = local_client.get("/local/onboarding")

    assert response.status_code == 200
    assert 'data-current-step="models"' in response.text


def test_valid_profile_post_is_atomic_and_advances_state(local_client: TestClient) -> None:
    raw_profile = """name: Test User
experiences: []
skills: []
projects: []
achievements: []
preferences: {}
"""
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/onboarding/profile",
        data={"profile": raw_profile},
        headers=_csrf_headers(local_client),
        follow_redirects=False,
    )

    assert response.status_code == 303
    target = Path(__import__("os").environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"])
    assert target.exists()
    state = json.loads((target.parent / "onboarding.json").read_text(encoding="utf-8"))
    assert state["current_step"] == "provider"
    assert state["profile_configured"] is True


def test_invalid_profile_preserves_draft(local_client: TestClient) -> None:
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/onboarding/profile",
        data={"profile": "not: [valid"},
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 422
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["drafts"]["profile"] == "not: [valid"
    assert state["errors"]["profile"]


def test_invalid_provider_preserves_non_secret_draft(local_client: TestClient) -> None:
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/onboarding/provider",
        data={
            "provider_id": "openai_compatible",
            "base_url": "https://example.test/v1/models",
            "api_key": "must-not-persist",
            "default_model": "model-a",
        },
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 422
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    raw_state = state_path.read_text(encoding="utf-8")
    assert "must-not-persist" not in raw_state
    state = json.loads(raw_state)
    assert state["drafts"]["provider"]["base_url"] == "https://example.test/v1/models"
    assert state["errors"]["provider"]


def test_model_discovery_and_provider_test_update_state(
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv_cp import local_routes

    monkeypatch.setattr(local_routes, "discover_models", lambda setup, api_key="": ["model-a", "model-b"])
    monkeypatch.setattr(local_routes, "get_credential", lambda provider_id: "")
    monkeypatch.setattr(local_routes, "test_provider", lambda setup: {"ok": True})
    payload = {
        "provider_id": "openai_compatible",
        "base_url": "https://example.test/v1",
        "auth_mode": "none",
        "wire_api": "responses",
        "default_model": "model-a",
    }
    local_client.get("/local/onboarding")

    models = local_client.post(
        "/local/onboarding/models/discover",
        data=payload,
        headers=_csrf_headers(local_client),
    )
    provider_test = local_client.post(
        "/local/onboarding/provider/test",
        data=payload,
        headers=_csrf_headers(local_client),
    )

    assert models.status_code == 200
    assert models.json() == {"models": ["model-a", "model-b"]}
    assert provider_test.status_code == 200
    assert provider_test.json()["ok"] is True
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    assert json.loads(state_path.read_text(encoding="utf-8"))["provider_test_ok"] is True


def test_incomplete_readiness_blocks_completion_and_run_submission(local_client: TestClient) -> None:
    Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"], "onboarding.json").write_text(
        json.dumps(
            {
                "version": 1,
                "current_step": "review",
                "complete": False,
                "provider_test_ok": False,
            }
        ),
        encoding="utf-8",
    )
    local_client.get("/local/onboarding")

    completion = local_client.post(
        "/local/onboarding/complete",
        headers=_csrf_headers(local_client),
    )
    trigger = local_client.post(
        "/runs",
        json={"jobs_path": "jobs.json"},
        headers=_csrf_headers(local_client),
    )

    assert completion.status_code == 409
    assert "Provider routing is not configured" in completion.text
    assert trigger.status_code == 409
    assert "onboarding is incomplete" in trigger.text.lower()


def test_server_mode_keeps_existing_host_and_csrf_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    app = create_app(
        redis_url="",
        backend_runtime=BackendRuntime(
            backend_type="sqlite",
            sqlite_path=str(tmp_path / "server.sqlite3"),
        ),
    )

    with TestClient(app) as client:
        response = client.get("/healthz", headers={"Host": "server.example"})

    assert response.status_code == 200
