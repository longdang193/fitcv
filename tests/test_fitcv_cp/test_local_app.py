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

from fitcv_cp.local_app import (
    LocalAppBusyError,
    LocalJobExecutor,
    _open_browser,
    _prebound_socket,
    build_recovery_app,
    prepare_local_environment,
    process_pending_storage_operation,
)
from fitcv_cp.local_storage import LocalStoragePaths, write_bootstrap, write_pending_operation

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
    with patch.object(local_app, "activate_local_storage", return_value=paths), patch.object(
        local_app, "_WindowsMutex", return_value=mutex
    ), patch.object(local_app, "_bundle_root", return_value=tmp_path), patch.object(
        local_app.os, "chdir"
    ), patch.object(local_app.webbrowser, "open") as browser_open:
        result = local_app.main()

    assert result == 0
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
