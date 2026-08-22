"""
@meta
type: test
scope: unit
domain: control_plane_startup
covers:
  - backend-resolved startup mode selection
excludes:
  - live GCP connectivity
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest
from fitcv_cp import sqlite_store
from fitcv_cp.backend_runtime import BackendRuntime


@pytest.fixture(autouse=True)
def _temporary_startup_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "startup.sqlite3"))
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)


def _candidate_profile(path: Path) -> None:
    path.write_text(
        """
name: Test Candidate
headline: Data leader
contact:
  email: test@example.com
experiences: []
education: []
skills: []
projects: []
achievements: []
preferences:
  seniority_target: senior
  location_types: [remote]
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _assert_control_plane_database(database_path: Path) -> None:
    required_tables = {
        "candidate_profiles",
        "candidate_profile_revisions",
        "pipeline_runs",
        "run_inputs",
        "scans",
        "scan_outputs",
        "run_scan_inputs",
        "run_stage_executions",
        "run_jobs",
        "run_job_stage_results",
    }
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == sqlite_store.CONTROL_PLANE_SCHEMA_VERSION
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert required_tables <= tables


def _configure_source_build(
    module: Any,
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    candidate_profile_path: Path,
) -> None:
    runtime = BackendRuntime(backend_type="sqlite", sqlite_path=str(database_path))
    monkeypatch.setattr(module, "resolve_backend_runtime", lambda: runtime)
    monkeypatch.setattr(
        module,
        "load_config",
        lambda: {"paths": {"candidate_profile": str(candidate_profile_path)}},
        raising=False,
    )
    monkeypatch.setattr(
        "fitcv_cp.reporter.retry_pending_process_event_deliveries",
        lambda *, limit: 0,
    )


def _reload_main_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    sys.modules.pop("fitcv_cp.main", None)
    return importlib.import_module("fitcv_cp.main")


def test_build_app_uses_sqlite_runtime_without_remote_client(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch)

    captured: dict[str, Any] = {}

    def _fake_create_app(*, redis_url: str, backend_runtime: Any = None) -> str:
        captured["redis_url"] = redis_url
        captured["backend_runtime"] = backend_runtime
        return "ok"

    monkeypatch.setattr(module, "create_app", _fake_create_app)

    result = module.build_app()

    assert result == "ok"
    assert captured["backend_runtime"].backend_type == "sqlite"


def test_build_app_retries_pending_process_event_deliveries(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch)
    calls: list[int] = []

    monkeypatch.setattr(
        "fitcv_cp.reporter.retry_pending_process_event_deliveries",
        lambda *, limit: calls.append(limit) or 0,
    )
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: "ok")

    assert module.build_app() == "ok"
    assert calls == [20]


def test_build_app_always_uses_sqlite_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)

    monkeypatch.setattr(
        module,
        "resolve_backend_runtime",
        lambda: BackendRuntime(
            backend_type="sqlite",
            sqlite_path=str(tmp_path / "fitcv_cp.sqlite3"),
        ),
    )

    captured: dict[str, Any] = {}

    def _fake_create_app(*, redis_url: str, backend_runtime: Any = None) -> str:
        captured["backend_runtime"] = backend_runtime
        return "ok"

    monkeypatch.setattr(module, "create_app", _fake_create_app)

    assert module.build_app() == "ok"
    assert captured["backend_runtime"].backend_type == "sqlite"

def test_build_app_defaults_to_inline_when_no_redis_url_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch)

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("FITCV_CP_INLINE_EXECUTION", raising=False)
    monkeypatch.setattr(
        module,
        "load_dotenv_defaults",
        lambda: module.os.environ.setdefault("FITCV_CP_INLINE_EXECUTION", "false"),
    )

    captured: dict[str, Any] = {}

    def _fake_create_app(*, redis_url: str, backend_runtime: Any = None) -> str:
        captured["redis_url"] = redis_url
        captured["backend_runtime"] = backend_runtime
        return "ok"

    monkeypatch.setattr(module, "create_app", _fake_create_app)

    assert module.build_app() == "ok"
    assert captured["backend_runtime"].backend_type == "sqlite"
    assert module.os.environ["FITCV_CP_INLINE_EXECUTION"] == "1"

def test_build_app_ignores_deprecated_langgraph_route_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_LANGGRAPH_PROVIDER", "stale-provider")
    monkeypatch.setenv("FITCV_LANGGRAPH_MODEL", "stale-model")
    monkeypatch.setenv("FITCV_LANGGRAPH_OVERRIDE_STRICT", "true")

    module = _reload_main_module(monkeypatch)

    assert module.app is not None


def test_source_build_app_bootstraps_missing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "source.sqlite3"
    candidate_profile_path = tmp_path / "candidate_profile.yaml"
    _candidate_profile(candidate_profile_path)
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: "ok")

    assert module.build_app() == "ok"

    _assert_control_plane_database(database_path)


def test_source_build_app_initializes_empty_schema_zero_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "empty.sqlite3"
    candidate_profile_path = tmp_path / "candidate_profile.yaml"
    _candidate_profile(candidate_profile_path)
    sqlite3.connect(database_path).close()
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: "ok")

    assert module.build_app() == "ok"

    _assert_control_plane_database(database_path)


def test_source_build_app_keeps_current_database_initialization_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "current.sqlite3"
    candidate_profile_path = tmp_path / "candidate_profile.yaml"
    _candidate_profile(candidate_profile_path)
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    synonym_paths = {
        synonym_type: tmp_path / f"{synonym_type}.yaml"
        for synonym_type in ("skills", "domain", "role_family")
    }
    monkeypatch.setattr(
        module,
        "ensure_control_plane_database",
        lambda database, profile: sqlite_store.ensure_control_plane_database(
            database, profile, synonym_paths=synonym_paths
        ),
    )
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: "ok")

    assert module.build_app() == "ok"
    with sqlite3.connect(database_path) as connection:
        tables_before = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    assert module.build_app() == "ok"
    _assert_control_plane_database(database_path)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall() == tables_before


def test_source_build_app_rejects_nonempty_schema_zero_before_create_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "incompatible.sqlite3"
    candidate_profile_path = tmp_path / "candidate_profile.yaml"
    _candidate_profile(candidate_profile_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE preserved (value TEXT NOT NULL)")
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    create_calls: list[object] = []
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: create_calls.append(True) or "bad")

    with pytest.raises(sqlite_store.DatabaseSchemaIncompatibleError):
        module.build_app()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'preserved'"
        ).fetchone() is not None
    assert create_calls == []


def test_source_build_app_propagates_non_openable_database_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "database-directory"
    candidate_profile_path = tmp_path / "candidate_profile.yaml"
    _candidate_profile(candidate_profile_path)
    database_path.mkdir()
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    create_calls: list[object] = []
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: create_calls.append(True) or "bad")

    with pytest.raises(sqlite3.OperationalError):
        module.build_app()

    assert create_calls == []


def test_source_bootstrap_runs_before_create_app_and_uses_configured_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _reload_main_module(monkeypatch)
    database_path = tmp_path / "ordered.sqlite3"
    candidate_profile_path = tmp_path / "configured-profile.yaml"
    _candidate_profile(candidate_profile_path)
    _configure_source_build(module, monkeypatch, database_path, candidate_profile_path)
    calls: list[tuple[str, Path, Path] | str] = []

    def fake_ensure(database: Path, profile: Path) -> None:
        calls.append(("ensure", database, profile))

    def fake_create_app(**_kwargs: object) -> str:
        calls.append("create")
        return "ok"

    monkeypatch.setattr(module, "ensure_control_plane_database", fake_ensure, raising=False)
    monkeypatch.setattr(module, "create_app", fake_create_app)

    assert module.build_app() == "ok"
    assert calls == [("ensure", database_path, candidate_profile_path), "create"]


def test_local_build_app_does_not_duplicate_packaged_database_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _reload_main_module(monkeypatch)
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setattr("fitcv_cp.local_storage.activate_local_storage", lambda: None)
    ensure_calls: list[object] = []
    monkeypatch.setattr(
        module,
        "ensure_control_plane_database",
        lambda *_args, **_kwargs: ensure_calls.append(True),
        raising=False,
    )
    monkeypatch.setattr(module, "create_app", lambda **_kwargs: "ok")

    assert module.build_app() == "ok"
    assert ensure_calls == []
