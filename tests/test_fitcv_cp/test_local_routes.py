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
import io
import re
import zipfile
import types
from pathlib import Path

import yaml
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from fitcv_cp import local_routes
from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import BackendRuntime
from fitcv_cp.local_storage import _paths, migrate_packaged_local_integration_state
from fitcv_cp.sqlite_store import initialize_control_plane_database


def test_local_paths_derive_from_data_root_not_path_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data"
    appdata = tmp_path / "roaming"
    monkeypatch.setenv("FITCV_LOCAL_DATA_ROOT", str(data_root))
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "wrong.sqlite3"))
    monkeypatch.setenv("FITCV_LOCAL_BACKUPS_PATH", str(tmp_path / "wrong-backups"))
    monkeypatch.setenv("APPDATA", str(appdata))

    assert local_routes._local_paths() == _paths(
        appdata / "FitCV" / "bootstrap.json",
        data_root,
    )


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


def _csrf_headers(client: TestClient) -> dict[str, str]:
    return {
        "Origin": "http://127.0.0.1",
        "X-FitCV-CSRF": str(client.app.state.csrf_token),
    }

def _complete_onboarding() -> None:
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state_path.write_text(json.dumps({"version": 1, "complete": True}), encoding="utf-8")

def test_packaged_local_admin_pages_render_canonical_resources(local_client: TestClient) -> None:
    _complete_onboarding()

    expectations = {
        "/admin/api-providers": ("API Providers", "/api-providers"),
        "/admin/api-providers/openai": ("OpenAI", "/api-providers/openai/connection/actions/test"),
        "/admin/llm-configuration": ("LLM Configuration", "/llm-configuration"),
        "/admin/settings/prompt-management": ("Prompt Management", "/prompt-configurations"),
        "/admin/system": ("System", "/system-settings"),
        "/admin/lifecycle": ("Lifecycle", "/local/lifecycle/status"),
    }

    for path, markers in expectations.items():
        response = local_client.get(path)
        assert response.status_code == 200, (path, response.text)
        for marker in markers:
            assert marker in response.text


def test_provider_setup_pages_and_resources_are_available_before_onboarding_completion(
    local_client: TestClient,
) -> None:
    for path in (
        "/admin/api-providers",
        "/admin/api-providers/openai",
        "/admin/llm-configuration",
        "/api-providers",
        "/llm-configuration",
    ):
        response = local_client.get(path, follow_redirects=False)
        assert response.status_code == 200, (path, response.text)

    blocked = local_client.get("/admin/runs", follow_redirects=False)
    assert blocked.status_code == 307
    assert blocked.headers["location"] == "/local/onboarding"

def test_packaged_local_admin_pages_are_not_registered_in_server_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    database_path = tmp_path / "server.sqlite3"
    initialize_control_plane_database(database_path, tmp_path / "profile.yaml")
    app = create_app(
        redis_url="",
        backend_runtime=BackendRuntime(backend_type="sqlite", sqlite_path=str(database_path)),
    )
    client = TestClient(app)

    for path in (
        "/admin/api-providers",
        "/admin/api-providers/openai",
        "/admin/llm-configuration",
        "/admin/settings/prompt-management",
        "/admin/system",
        "/admin/lifecycle",
        "/admin/optimization",
        "/admin/optimization/runs/por_missing",
    ):
        assert client.get(path).status_code in {404, 405}
    openapi_paths = client.get("/openapi.json").json()["paths"]
    assert "get" not in openapi_paths.get("/admin/settings/{key}", {})

def test_pipeline_section_urls_render_server_owned_settings(local_client: TestClient) -> None:
    _complete_onboarding()

    sections = {
        "enrichment": "Enrichment",
        "screening": "Screening",
        "shortlisting": "Shortlisting",
        "ranking": "Ranking",
        "cv-analysis": "CV Analysis",
        "cv-generation": "CV Generation",
        "runtime-limits": "Runtime &amp; Limits",
        "automation-reuse": "Automation &amp; Reuse",
    }
    for section, title in sections.items():
        response = local_client.get(f"/admin/settings/{section}")
        assert response.status_code == 200
        assert f"<h2>{title}</h2>" in response.text
        assert 'data-header-title="Pipeline"' in response.text
        sidebar = response.text[response.text.index('<aside class="sidebar'):response.text.index('</aside>')]
        assert sidebar.count('aria-current="page"') == 1
        assert re.search(
            rf'href="/admin/settings/{re.escape(section)}" aria-current="page"',
            response.text,
        )
        main = response.text[response.text.index('<main'):response.text.index('</main>')]
        assert "workspace-tabs" not in main
        assert 'aria-label="Pipeline settings sections"' not in main
        assert 'data-setting-row=' in response.text

    assert local_client.get("/admin/settings/unknown").status_code == 404


def test_pipeline_settings_render_prototype_component_contract(local_client: TestClient) -> None:
    _complete_onboarding()

    overview = local_client.get("/admin/settings").text
    cv_analysis = local_client.get("/admin/settings/cv-analysis").text
    ranking = local_client.get("/admin/settings/ranking").text

    assert '<main class="workspace-stack" id="pipeline-settings-app" data-header-title="Pipeline"' in cv_analysis
    assert '<h1>CV Analysis</h1>' not in cv_analysis
    assert re.search(
        r'<label class="switch">\s*<input[^>]+data-setting-key="cv_analysis\.semantic_alignment\.enabled"[^>]+type="checkbox"[^>]*>\s*<span class="track"',
        cv_analysis,
    )
    assert "<code>Enabled</code>" not in cv_analysis
    assert re.search(
        r'<input[^>]+data-setting-key="pipeline\.vector_search_top_n"[^>]+type="number"[^>]+min="1"[^>]+step="1"',
        overview,
    )
    assert 'class="transaction-summary"' in ranking
    assert 'class="mirror-value"' in cv_analysis
    assert 'class="dialog-head"' in cv_analysis
    assert 'class="weight-form"' in cv_analysis
    assert 'class="weight-status"' in cv_analysis
    assert 'class="dialog-actions"' in cv_analysis
    assert 'aria-describedby="pipeline-manage-description"' in cv_analysis


def test_runtime_limits_route_renders_shared_pacing_and_concurrency_only(local_client: TestClient) -> None:
    _complete_onboarding()

    response = local_client.get("/admin/settings/runtime-limits")

    assert response.status_code == 200
    assert "Minimum Request Start Interval (seconds)" in response.text
    assert response.text.count("Maximum Concurrent Jobs") == 4
    assert "same provider connection" in response.text
    assert "retry backoff remains separate" in response.text
    assert "Maximum number of local CV Analysis jobs" in response.text
    assert "Batch Size" not in response.text
    assert "Request Delay" not in response.text

def test_packaged_local_pages_encode_approved_ui_states(local_client: TestClient) -> None:
    _complete_onboarding()

    providers = local_client.get("/admin/api-providers").text
    assert "API Key Providers" in providers
    assert "Custom Providers" in providers
    assert "No connection" in providers
    assert "1 connection" not in providers

    provider = local_client.get("/admin/api-providers/openai").text
    assert 'id="provider-base-url"' in provider and "disabled" in provider
    assert 'id="provider-api-type"' in provider
    assert 'id="test-provider-connection"' in provider
    assert 'id="save-provider-connection" type="submit" disabled' in provider
    assert "A verified connection is required" in provider
    assert 'id="open-add-model" type="button" disabled' in provider
    assert 'id="add-model-dialog"' in provider
    assert 'data-model-test=' in provider or "No models added." in provider
    assert "provider_revision_conflict" in provider

    llm = local_client.get("/admin/llm-configuration").text
    llm_main = llm[llm.index('<main'):llm.index('</main>')]
    for label in ("Enrich Extraction", "Ranking AI Score", "CV Generation", "Synonym Recommendation"):
        assert label in llm_main
    assert "CV Analysis" not in llm_main
    assert "llm_configuration_revision_conflict" in llm

    prompts = local_client.get("/admin/settings/prompt-management").text
    assert "Pipeline Prompts" in prompts and "Synonym Prompts" in prompts
    assert '<option value="default">Default</option>' in prompts
    assert '<option value="custom">Custom</option>' in prompts
    assert 'maxlength="4000"' in prompts
    assert "3800" in prompts and "Character limit reached." in prompts
    assert "Discard unsaved prompt changes?" in prompts
    assert "prompt_configuration_revision_conflict" in prompts

    system = local_client.get("/admin/system").text
    lifecycle = local_client.get("/admin/lifecycle").text
    system_main = system[system.index('<main'):system.index('</main>')]
    lifecycle_main = lifecycle[lifecycle.index('<main'):lifecycle.index('</main>')]
    assert "Download Backup" in system and "Import Backup" in system
    assert "Maximum Attempts" in system and "Initial Backoff" in system
    assert "Relocate Data" not in system_main and "Download Diagnostics" not in system_main
    assert "Relocate Data" in lifecycle_main and "Download Diagnostics" in lifecycle_main
    assert "Download Backup" not in lifecycle_main and "Shutdown FitCV" not in lifecycle_main
    assert "Shutdown FitCV?</h2>" in lifecycle

    assert "Health" not in system and "Appearance" not in system
    assert system.index('id="theme-toggle"') < system.index('id="open-shutdown-dialog"')
    assert "t === 'dark' ? '☀' : '☾'" in system
    assert "Switch to light theme" in system and "Switch to dark theme" in system


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


def test_local_root_redirects_to_onboarding_when_setup_incomplete(local_client: TestClient) -> None:
    response = local_client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/local/onboarding"

def test_onboarding_sets_csrf_cookie_and_redirects_incomplete_app(local_client: TestClient) -> None:
    onboarding = local_client.get("/local/onboarding")
    redirect = local_client.get("/admin/runs", follow_redirects=False)

    assert onboarding.status_code == 200
    assert onboarding.cookies.get("fitcv_csrf") == local_client.app.state.csrf_token
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/local/onboarding"


def test_local_root_redirects_to_runs_when_setup_complete(local_client: TestClient) -> None:
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state_path.write_text(json.dumps({"version": 1, "complete": True}), encoding="utf-8")

    response = local_client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/admin/runs"


def test_completed_onboarding_redirects_to_runs(
    local_client: TestClient,
) -> None:
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state_path.write_text(json.dumps({"version": 1, "complete": True}), encoding="utf-8")

    response = local_client.get("/local/onboarding", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/runs"

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


def test_legacy_onboarding_configuration_routes_do_not_write_overlay(
    local_client: TestClient,
) -> None:
    overlay_path = Path(__import__("os").environ["FITCV_LOCAL_CONTROLLER_OVERLAY_PATH"])
    before = overlay_path.read_bytes()

    responses = [
        local_client.post(
            path,
            data={"provider_id": "openai_compatible", "scope": "provider"},
            headers=_csrf_headers(local_client),
        )
        for path in (
            "/local/onboarding/provider",
            "/local/onboarding/models/discover",
            "/local/onboarding/provider/test",
            "/local/onboarding/controller/reset",
        )
    ]

    assert [response.status_code for response in responses] == [410, 410, 410, 410]
    assert overlay_path.read_bytes() == before

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


def test_invalid_profile_does_not_expand_onboarding_state(local_client: TestClient) -> None:
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/onboarding/profile",
        data={"profile": "not: [valid"},
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 422
    state_path = Path(__import__("os").environ["FITCV_LOCAL_DATA_ROOT"]) / "onboarding.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert set(state) <= {"version", "current_step", "complete", "profile_configured"}
    assert "Invalid YAML in candidate profile" in response.text


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
    assert "Candidate profile is not configured" in completion.text
    assert "provider_test_ok" not in completion.text
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


def test_backup_rejects_active_work(local_client: TestClient) -> None:
    executor = MagicMock()
    executor.is_busy.return_value = True
    local_client.app.state.local_job_executor = executor
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/data/backup",
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 409
    assert "active" in response.text.lower()


def test_data_page_and_backup_download(local_client: TestClient) -> None:
    Path(__import__("os").environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"]).write_text(
        "name: User\n", encoding="utf-8"
    )
    routing = Path(__import__("os").environ["FITCV_LOCAL_CONTROLLER_OVERLAY_PATH"])
    routing.parent.mkdir(parents=True, exist_ok=True)
    routing.write_text("version: 1\nproviders: {}\nmodel_routing:\n  parts: {}\n", encoding="utf-8")
    local_client.get("/local/onboarding")

    page = local_client.get("/local/data")
    backup = local_client.post(
        "/local/data/backup",
        headers=_csrf_headers(local_client),
    )

    assert page.status_code == 200
    assert __import__("os").environ["FITCV_LOCAL_DATA_ROOT"] in page.text
    assert backup.status_code == 200
    with zipfile.ZipFile(io.BytesIO(backup.content)) as bundle:
        assert json.loads(bundle.read("manifest.json"))["format"] == "fitcv-backup.v1"


def test_relocation_request_persists_cold_operation_and_signals_shutdown(
    local_client: TestClient,
    tmp_path: Path,
) -> None:
    shutdown = MagicMock()
    local_client.app.state.local_shutdown_callback = shutdown
    local_client.get("/local/onboarding")
    destination = tmp_path / "moved"

    response = local_client.post(
        "/local/data/relocate",
        data={"destination": str(destination)},
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 202
    assert response.json()["restart_required"] is True
    pending = Path(__import__("os").environ["APPDATA"]) / "FitCV" / "pending-operation.json"
    assert json.loads(pending.read_text(encoding="utf-8"))["destination"] == str(destination)
    shutdown.assert_called_once()


def test_diagnostics_redact_secrets_and_shutdown_is_idempotent(local_client: TestClient) -> None:
    log_path = Path(__import__("os").environ["FITCV_LOCAL_LOGS_PATH"]) / "fitcv.log"
    log_path.write_text(
        "INFO startup complete\nAuthorization: Bearer secret-canary\n",
        encoding="utf-8",
    )
    shutdown = MagicMock()
    local_client.app.state.local_shutdown_callback = shutdown
    local_client.get("/local/onboarding")

    diagnostics = local_client.get("/local/system/diagnostics")
    first = local_client.post("/local/system/shutdown", headers=_csrf_headers(local_client))
    second = local_client.post("/local/system/shutdown", headers=_csrf_headers(local_client))

    assert diagnostics.status_code == 200
    assert b"secret-canary" not in diagnostics.content
    with zipfile.ZipFile(io.BytesIO(diagnostics.content)) as bundle:
        assert "system.json" in bundle.namelist()
        assert b"startup complete" in bundle.read("log_tail.txt")
    assert first.status_code == 200
    assert second.status_code == 200
    shutdown.assert_called_once()


def test_awaiting_continue_run_blocks_backup_and_shutdown(local_client: TestClient) -> None:
    local_client.app.state.run_store.list_runs_fn = lambda **_kwargs: [
        types.SimpleNamespace(run_id="run-paused", status="awaiting_continue")
    ]
    local_client.get("/local/onboarding")

    backup = local_client.post("/local/data/backup", headers=_csrf_headers(local_client))
    shutdown = local_client.post("/local/system/shutdown", headers=_csrf_headers(local_client))

    assert backup.status_code == 409
    assert shutdown.status_code == 409
    assert "run-paused" in backup.text


def test_import_rejects_unsafe_archive(local_client: TestClient, tmp_path: Path) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.txt", "bad")
    local_client.get("/local/onboarding")

    response = local_client.post(
        "/local/data/import",
        data={"destination": str(tmp_path / "restored")},
        files={"archive": ("bad.zip", archive.getvalue(), "application/zip")},
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 422
    assert "unsafe path" in response.text


def test_onboarding_links_to_canonical_configuration_and_omits_legacy_forms(
    local_client: TestClient,
) -> None:
    response = local_client.get("/local/onboarding")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert 'href="/admin/api-providers"' in response.text
    assert 'href="/admin/llm-configuration"' in response.text
    assert 'name="controller_settings_present"' not in response.text
    assert 'name="retry_max_attempts"' not in response.text
    assert 'name="prompt_addendum_' not in response.text
    assert '/local/onboarding/provider/test' not in response.text


def test_controller_settings_save_and_prompt_reset(local_client: TestClient) -> None:
    overlay_path = Path(
        __import__("os").environ["FITCV_LOCAL_CONTROLLER_OVERLAY_PATH"]
    )
    before = overlay_path.read_bytes()

    response = local_client.post(
        "/local/onboarding/controller/reset",
        data={"scope": "prompt:enrich_extraction"},
        headers=_csrf_headers(local_client),
    )

    assert response.status_code == 410
    assert overlay_path.read_bytes() == before
