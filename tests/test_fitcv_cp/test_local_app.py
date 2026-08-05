"""
@meta
type: test
scope: unit
domain: fitcv_local_runtime
covers:
  - serialized packaged job execution
  - packaged environment enforcement
excludes:
  - live browser launch
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import os
import json
import sqlite3
import threading
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from fitcv_cp import provider_registry
from fitcv_cp.app import create_app

from fitcv_cp.local_app import (
    LocalAppBusyError,
    LocalJobExecutor,
    _open_browser,
    _prebound_socket,
    build_recovery_app,
    prepare_local_environment,
    process_pending_storage_operation,
)
from fitcv_cp.local_storage import (
    LocalStoragePaths,
    load_pending_operation,
    write_bootstrap,
    write_pending_operation,
)
from fitcv_cp.sqlite_store import CONTROL_PLANE_SCHEMA_VERSION

LOCAL_ENVIRONMENT_KEYS = (
    "FITCV_LOCAL_MODE",
    "FITCV_CP_INLINE_EXECUTION",
    "REDIS_URL",
    "FITCV_CP_SQLITE_PATH",
    "FITCV_LOCAL_DATA_ROOT",
    "FITCV_LOCAL_CONTROLLER_OVERLAY_PATH",
    "FITCV_LOCAL_CANDIDATE_PROFILE_PATH",
    "FITCV_LOCAL_ARTIFACTS_PATH",
    "FITCV_LOCAL_EXPORTS_PATH",
    "FITCV_LOCAL_LOGS_PATH",
    "FITCV_LOCAL_BACKUPS_PATH",
    "FITCV_LOCAL_UPLOADS_PATH",
    "FITCV_LOCAL_TEMP_PATH",
)


@pytest.fixture(autouse=True)
def restore_local_environment() -> None:
    original = {key: os.environ.get(key) for key in LOCAL_ENVIRONMENT_KEYS}
    yield
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_local_job_executor_rejects_second_active_submission() -> None:
    executor = LocalJobExecutor()
    release = threading.Event()
    first = executor.submit(lambda: release.wait(2))

    with pytest.raises(LocalAppBusyError):
        executor.submit(lambda: None)

    release.set()
    first.result(timeout=2)
    executor.submit(lambda: None).result(timeout=2)
    executor.shutdown()


def test_prepare_local_environment_forces_inline_without_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setenv("FITCV_CP_INLINE_EXECUTION", "0")
    monkeypatch.setenv("FITCV_LOCAL_MODE", "")

    prepare_local_environment()

    assert "REDIS_URL" not in __import__("os").environ
    assert __import__("os").environ["FITCV_CP_INLINE_EXECUTION"] == "1"
    assert __import__("os").environ["FITCV_LOCAL_MODE"] == "1"


def _provider_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[object, TestClient]:
    from fitcv_cp import local_routes
    from fitcv_cp.backend_runtime import set_backend_runtime

    set_backend_runtime(None)
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv.sqlite3"))
    monkeypatch.setattr(local_routes, "onboarding_is_complete", lambda: True)
    credentials: dict[str, str] = {}
    monkeypatch.setattr(
        provider_registry,
        "set_credential",
        lambda provider_id, api_key: credentials.__setitem__(provider_id, api_key),
    )
    monkeypatch.setattr(
        provider_registry,
        "get_credential",
        lambda provider_id: credentials.get(provider_id, ""),
    )
    monkeypatch.setattr(
        provider_registry,
        "delete_credential",
        lambda provider_id: credentials.pop(provider_id, None),
    )
    monkeypatch.setattr(
        provider_registry,
        "validate_connection_draft",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    monkeypatch.setattr(
        provider_registry,
        "validate_model",
        lambda **_kwargs: {"ok": True, "failure_code": None, "http_status": 200},
    )
    app = create_app(redis_url="redis://localhost:6379/0")
    return app, TestClient(app, base_url="http://127.0.0.1:8000")


def _unsafe_headers(app: object, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Origin": "http://127.0.0.1:8000",
        "X-FitCV-CSRF": str(app.state.csrf_token),
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def test_packaged_provider_api_supports_verified_connection_and_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = _provider_client(tmp_path, monkeypatch)

    collection = client.get("/api-providers")
    assert collection.status_code == 200
    assert [provider["provider_id"] for provider in collection.json()["data"]] == [
        "openai",
        "anthropic",
        "deepseek",
        "groq",
    ]
    assert "/api-providers" in client.get("/openapi.json").json()["paths"]

    create_body = {"display_name": "Company Gateway", "compatibility": "openai"}
    created = client.post(
        "/api-providers",
        json=create_body,
        headers=_unsafe_headers(app, idempotency_key="provider-create-1"),
    )
    assert created.status_code == 200
    provider = created.json()["data"]
    assert provider["connection_status"] == "not_configured"
    replay = client.post(
        "/api-providers",
        json=create_body,
        headers=_unsafe_headers(app, idempotency_key="provider-create-1"),
    )
    assert replay.json() == created.json()

    draft = {
        "base_url": "https://gateway.example/v1",
        "api_type": "responses",
        "api_key": "credential-secret-canary",
    }
    tested = client.post(
        f"/api-providers/{provider['provider_id']}/connection/actions/test",
        json=draft,
        headers=_unsafe_headers(app),
    )
    assert tested.json()["data"]["ok"] is True
    assert client.get(f"/api-providers/{provider['provider_id']}").json()["data"][
        "connection_status"
    ] == "not_configured"

    connected = client.put(
        f"/api-providers/{provider['provider_id']}/connection",
        json={**draft, "expected_revision": provider["revision"]},
        headers=_unsafe_headers(app),
    )
    assert connected.status_code == 200
    connected_provider = connected.json()["data"]
    assert connected_provider["connection_status"] == "verified"
    assert "credential-secret-canary" not in connected.text

    model_test = client.post(
        f"/api-providers/{provider['provider_id']}/models/actions/test",
        json={"model_id": "model-alpha"},
        headers=_unsafe_headers(app),
    )
    assert model_test.json()["data"]["ok"] is True
    added = client.post(
        f"/api-providers/{provider['provider_id']}/models",
        json={"model_id": "model-alpha", "expected_revision": connected_provider["revision"]},
        headers=_unsafe_headers(app, idempotency_key="provider-model-1"),
    )
    assert added.status_code == 200
    assert added.json()["data"]["validation_status"] == "validated"
    assert b"credential-secret-canary" not in (tmp_path / "fitcv.sqlite3").read_bytes()


def test_packaged_provider_api_rejects_stale_revision_and_unsafe_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = _provider_client(tmp_path, monkeypatch)

    unsafe = client.post(
        "/api-providers",
        json={"display_name": "Blocked", "compatibility": "openai"},
        headers={
            "Origin": "http://example.test",
            "X-FitCV-CSRF": str(app.state.csrf_token),
            "Idempotency-Key": "blocked",
        },
    )
    assert unsafe.status_code == 403

    stale = client.put(
        "/api-providers/openai/connection",
        json={
            "api_type": "responses",
            "api_key": "secret",
            "expected_revision": 999,
        },
        headers=_unsafe_headers(app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "provider_revision_conflict"


def test_packaged_llm_configuration_is_revisioned_and_local_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = _provider_client(tmp_path, monkeypatch)

    current = client.get("/llm-configuration")
    assert current.status_code == 200
    resource = current.json()["data"]
    assert resource["default_model_ref"] is None
    assert resource["eligible_models"] == []
    assert "candidate_profile_base_mapping" in resource["tasks"]
    assert "candidate_profile_derived_claims" in resource["tasks"]
    assert current.headers["etag"] == f'"{resource["revision"]}"'

    updated = client.patch(
        "/llm-configuration",
        json={
            "tasks": {"enrich_extraction": {"timeout_seconds": 90}},
            "expected_revision": resource["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["tasks"]["enrich_extraction"]["timeout_seconds"] == 90

    stale = client.patch(
        "/llm-configuration",
        json={
            "tasks": {"enrich_extraction": {"temperature": 0.4}},
            "expected_revision": resource["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "llm_configuration_revision_conflict"

    invalid = client.patch(
        "/llm-configuration",
        json={
            "default_model_ref": "missing-model",
            "expected_revision": updated.json()["data"]["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "llm_configuration_invalid"

    persisted = client.get("/llm-configuration").json()["data"]
    assert persisted["revision"] == updated.json()["data"]["revision"]
    assert persisted["default_model_ref"] is None


def test_packaged_prompt_configuration_exposes_defaults_and_validates_replacements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = _provider_client(tmp_path, monkeypatch)

    current = client.get("/prompt-configurations")
    assert current.status_code == 200
    resources = current.json()["data"]
    assert [resource["task_id"] for resource in resources] == [
        "candidate_profile_base_mapping",
        "candidate_profile_derived_claims",
        "enrich_extraction",
        "ranking_ai_score",
        "cv_generation_structured_write",
        "synonym_triage_recommendation",
    ]
    resource = next(item for item in resources if item["task_id"] == "enrich_extraction")
    assert resource["display_name"] == "Enrich Extraction"
    assert resource["group"] == "Pipeline Prompts"
    assert resource["mode"] == "default"
    assert resource["replacement_text"] is None
    assert "default_text" in resource
    assert resource["required_runtime_variables"]
    assert current.headers["etag"]

    replacement = resource["default_text"].replace("You are", "You are precise and", 1)
    updated = client.patch(
        "/prompt-configurations/enrich_extraction",
        json={"replacement_text": replacement, "expected_revision": resource["revision"]},
        headers=_unsafe_headers(app),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["mode"] == "custom"
    assert updated.json()["data"]["replacement_text"] == replacement

    invalid = client.patch(
        "/prompt-configurations/enrich_extraction",
        json={
            "replacement_text": replacement + "\n${unsupported_variable}",
            "expected_revision": updated.json()["data"]["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "prompt_configuration_invalid"

    stale = client.patch(
        "/prompt-configurations/enrich_extraction",
        json={"replacement_text": None, "expected_revision": resource["revision"]},
        headers=_unsafe_headers(app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "prompt_configuration_revision_conflict"

    reset = client.patch(
        "/prompt-configurations/enrich_extraction",
        json={"replacement_text": None, "expected_revision": updated.json()["data"]["revision"]},
        headers=_unsafe_headers(app),
    )
    assert reset.status_code == 200
    assert reset.json()["data"]["mode"] == "default"
    assert reset.json()["data"]["replacement_text"] is None

    persisted = client.get("/prompt-configurations").json()["data"]
    restored = next(item for item in persisted if item["task_id"] == "enrich_extraction")
    assert restored["revision"] == reset.json()["data"]["revision"]
    assert restored["mode"] == "default"


def test_packaged_system_settings_are_revisioned_validated_and_local_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client = _provider_client(tmp_path, monkeypatch)

    current = client.get("/system-settings")
    assert current.status_code == 200
    resource = current.json()["data"]
    assert resource["maximum_attempts"] == 3
    assert resource["initial_backoff_seconds"] == 10
    assert resource["bounds"]["lease_seconds"] == {"minimum": 30, "maximum": 86400}
    assert current.headers["etag"] == f'"{resource["revision"]}"'

    updated = client.patch(
        "/system-settings",
        json={
            "maximum_attempts": 4,
            "initial_backoff_seconds": 20,
            "lease_seconds": 600,
            "reconciler_interval_seconds": 60,
            "error_detail_limit": 20000,
            "expected_revision": resource["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["maximum_attempts"] == 4

    invalid = client.patch(
        "/system-settings",
        json={
            "maximum_attempts": 0,
            "initial_backoff_seconds": 20,
            "lease_seconds": 600,
            "reconciler_interval_seconds": 60,
            "error_detail_limit": 20000,
            "expected_revision": updated.json()["data"]["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "system_settings_invalid"

    stale = client.patch(
        "/system-settings",
        json={
            "maximum_attempts": 2,
            "initial_backoff_seconds": 20,
            "lease_seconds": 600,
            "reconciler_interval_seconds": 60,
            "error_detail_limit": 20000,
            "expected_revision": resource["revision"],
        },
        headers=_unsafe_headers(app),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "system_settings_revision_conflict"


def test_submit_run_maps_local_busy_to_http_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    from fitcv_cp import app

    class BusyAdapter:
        def submit(self, **_kwargs: object) -> None:
            raise LocalAppBusyError("busy")

    monkeypatch.setattr(app, "ORCHESTRATION_ADAPTER", BusyAdapter())

    with pytest.raises(HTTPException) as error:
        app.submit_run(jobs_path="jobs.json", config_path=".env.yaml", triggered_by="user")

    assert error.value.status_code == 409


def test_prebound_socket_uses_loopback_and_dynamic_port() -> None:
    listener = _prebound_socket()
    try:
        host, port = listener.getsockname()
        assert host == "127.0.0.1"
        assert port > 0
    finally:
        listener.close()


def test_second_launch_opens_existing_url_and_exits(tmp_path: Path) -> None:
    from fitcv_cp import local_app

    paths = LocalStoragePaths(
        bootstrap_path=tmp_path / "bootstrap.json",
        data_root=tmp_path,
        sqlite_path=tmp_path / "fitcv.sqlite3",
        candidate_profile_path=tmp_path / "candidate_profile.yaml",
        controller_overlay_path=tmp_path / "local_controller_overlay.yaml",
        legacy_routing_overlay_path=tmp_path / "local_routing_overlay.yaml",
        migrated_routing_overlay_path=tmp_path / "local_routing_overlay.yaml.migrated.bak",
        onboarding_state_path=tmp_path / "onboarding.json",
        integration_migration_error_path=tmp_path / "integration-migration-error.json",
        artifacts_path=tmp_path / "artifacts",
        exports_path=tmp_path / "exports",
        logs_path=tmp_path / "logs",
        backups_path=tmp_path / "backups",
        uploads_path=tmp_path / "uploads",
        temporary_path=tmp_path / "tmp",
    )
    (tmp_path / ".fitcv-local-runtime.json").write_text(
        '{"url": "http://127.0.0.1:12345/", "pid": 123}\n', encoding="utf-8"
    )
    mutex = MagicMock(already_exists=True)
    ensure_database = MagicMock()
    with patch.object(local_app, "activate_local_storage", return_value=paths), patch.object(
        local_app, "_WindowsMutex", return_value=mutex
    ), patch.object(local_app, "_bundle_root", return_value=tmp_path), patch.object(
        local_app.os, "chdir"
    ), patch.object(
        local_app, "ensure_control_plane_database", ensure_database
    ), patch.object(local_app.webbrowser, "open") as browser_open:
        result = local_app.main()

    assert result == 0
    ensure_database.assert_called_once_with(paths.sqlite_path, paths.candidate_profile_path)
    browser_open.assert_called_once_with("http://127.0.0.1:12345/")
    mutex.close.assert_called_once()


def test_first_launch_runs_uvicorn_on_prebound_socket(tmp_path: Path) -> None:
    from fitcv_cp import local_app

    paths = LocalStoragePaths(
        bootstrap_path=tmp_path / "bootstrap.json",
        data_root=tmp_path,
        sqlite_path=tmp_path / "fitcv.sqlite3",
        candidate_profile_path=tmp_path / "candidate_profile.yaml",
        controller_overlay_path=tmp_path / "local_controller_overlay.yaml",
        legacy_routing_overlay_path=tmp_path / "local_routing_overlay.yaml",
        migrated_routing_overlay_path=tmp_path / "local_routing_overlay.yaml.migrated.bak",
        onboarding_state_path=tmp_path / "onboarding.json",
        integration_migration_error_path=tmp_path / "integration-migration-error.json",
        artifacts_path=tmp_path / "artifacts",
        exports_path=tmp_path / "exports",
        logs_path=tmp_path / "logs",
        backups_path=tmp_path / "backups",
        uploads_path=tmp_path / "uploads",
        temporary_path=tmp_path / "tmp",
    )
    listener = MagicMock()
    listener.getsockname.return_value = ("127.0.0.1", 23456)
    mutex = MagicMock(already_exists=False)
    run_store = MagicMock()
    application = MagicMock()
    application.state = types.SimpleNamespace(run_store=run_store)
    server = MagicMock(should_exit=False)
    executor = MagicMock()
    tray = MagicMock()
    uvicorn_module = types.ModuleType("uvicorn")
    uvicorn_module.Config = MagicMock(return_value="config")
    uvicorn_module.Server = MagicMock(return_value=server)
    main_module = types.ModuleType("fitcv_cp.main")
    main_module.build_app = MagicMock(return_value=application)
    reconciler_module = types.ModuleType("fitcv_cp.reconciler")
    reconciler_module.reconcile_abandoned_attempts = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "uvicorn": uvicorn_module,
            "fitcv_cp.main": main_module,
            "fitcv_cp.reconciler": reconciler_module,
        },
    ), patch.object(local_app, "activate_local_storage", return_value=paths), patch.object(
        local_app, "_WindowsMutex", return_value=mutex
    ), patch.object(local_app, "_bundle_root", return_value=tmp_path), patch.object(
        local_app.os, "chdir"
    ), patch.object(local_app, "_prebound_socket", return_value=listener), patch.object(
        local_app, "_write_runtime_metadata"
    ), patch.object(local_app, "get_local_job_executor", return_value=executor), patch.object(
        local_app, "WindowsTray", return_value=tray
    ), patch.object(
        local_app.webbrowser, "open"
    ) as browser_open:
        result = local_app.main()

    assert result == 0
    server.run.assert_called_once_with(sockets=[listener])
    browser_open.assert_called_once_with("http://127.0.0.1:23456/")
    reconciler_module.reconcile_abandoned_attempts.assert_called_once_with(run_store)
    assert application.state.local_job_executor is executor
    tray.start.assert_called_once()
    tray.stop.assert_called_once()
    listener.close.assert_called_once()
    executor.shutdown.assert_called_once()
    mutex.close.assert_called_once()

def test_process_pending_relocation_switches_bootstrap_and_keeps_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appdata = tmp_path / "roaming"
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    with sqlite3.connect(source / "fitcv.sqlite3") as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
    bootstrap_path = appdata / "FitCV" / "bootstrap.json"
    write_bootstrap(bootstrap_path, source, "1")
    pending_path = appdata / "FitCV" / "pending-operation.json"
    destination = tmp_path / "destination"
    write_pending_operation(
        pending_path,
        {"operation": "relocate", "destination": str(destination)},
    )

    previous = process_pending_storage_operation(app_version="2")

    assert previous == source
    assert source.exists()
    assert json.loads(bootstrap_path.read_text(encoding="utf-8"))["data_root"] == str(destination)
    assert not pending_path.exists()

def test_process_pending_database_reset_archives_old_database_and_seeds_new_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appdata = tmp_path / "roaming"
    source = tmp_path / "source"
    source.mkdir()
    (source / "backups").mkdir()
    (source / "tmp").mkdir()
    (source / "candidate_profile.yaml").write_text(
        """
experiences: []
skills: []
projects: []
achievements: []
preferences: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APPDATA", str(appdata))
    connection = sqlite3.connect(source / "fitcv.sqlite3")
    connection.execute("CREATE TABLE local_pipeline_runs (run_id TEXT PRIMARY KEY)")
    connection.commit()
    connection.close()
    Path(f"{source / 'fitcv.sqlite3'}-wal").write_bytes(b"wal")
    Path(f"{source / 'fitcv.sqlite3'}-shm").write_bytes(b"shm")
    bootstrap_path = appdata / "FitCV" / "bootstrap.json"
    write_bootstrap(bootstrap_path, source, "1")
    pending_path = appdata / "FitCV" / "pending-operation.json"
    write_pending_operation(pending_path, {"operation": "reset_database"})

    previous = process_pending_storage_operation(app_version="2")

    assert previous is None
    assert not pending_path.exists()
    with sqlite3.connect(source / "fitcv.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CONTROL_PLANE_SCHEMA_VERSION
        assert connection.execute("SELECT COUNT(*) FROM candidate_profiles").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0] == 0
    retired = next((source / "backups").glob("database-reset-*"))
    assert (retired / "fitcv.sqlite3-wal").read_bytes() == b"wal"
    assert (retired / "fitcv.sqlite3-shm").read_bytes() == b"shm"
    assert next((source / "backups").glob("fitcv-reset-*.fitcv.zip")).exists()

def test_main_reset_database_writes_versioned_pending_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv_cp import local_app

    appdata = tmp_path / "roaming"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(local_app, "_bundle_root", lambda: tmp_path)
    monkeypatch.setattr(local_app.os, "chdir", lambda _path: None)
    monkeypatch.setattr(
        local_app,
        "process_pending_storage_operation",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("stop after queue")),
    )
    monkeypatch.setattr(local_app, "_run_recovery", lambda _error: 1)

    assert local_app.main(["--reset-database"]) == 1
    assert load_pending_operation(appdata / "FitCV" / "pending-operation.json") == {
        "version": 1,
        "operation": "reset_database",
    }

def test_recovery_app_hides_exception_details() -> None:
    app = build_recovery_app(RuntimeError("secret path and key"))

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Recovery" in response.text
    assert "RuntimeError" in response.text
    assert "secret path and key" not in response.text

def test_open_browser_can_be_disabled_for_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_NO_BROWSER", "1")

    with patch("fitcv_cp.local_app.webbrowser.open") as browser_open:
        _open_browser("http://127.0.0.1:1234/")

    browser_open.assert_not_called()
