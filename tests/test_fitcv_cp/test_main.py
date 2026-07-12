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
import sys
from typing import Any

import pytest
from fitcv_cp.backend_runtime import BackendRuntime


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


def test_build_app_always_uses_sqlite_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch)

    monkeypatch.setattr(
        module,
        "resolve_backend_runtime",
        lambda: BackendRuntime(
            backend_type="sqlite",
            sqlite_path="data/fitcv_cp.sqlite3",
        ),
    )

    captured: dict[str, Any] = {}

    def _fake_create_app(*, redis_url: str, backend_runtime: Any = None) -> str:
        captured["backend_runtime"] = backend_runtime
        return "ok"

    monkeypatch.setattr(module, "create_app", _fake_create_app)

    assert module.build_app() == "ok"
    assert captured["backend_runtime"].backend_type == "sqlite"

def test_warn_or_fail_langgraph_override_drift_uses_shared_runtime_routing_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _reload_main_module(monkeypatch)

    monkeypatch.setattr(module, "langgraph_override_drift_fields", lambda: ["provider", "model"])
    monkeypatch.setenv("FITCV_LANGGRAPH_OVERRIDE_STRICT", "true")

    with pytest.raises(RuntimeError, match="fields=provider,model"):
        module._warn_or_fail_langgraph_override_drift()

