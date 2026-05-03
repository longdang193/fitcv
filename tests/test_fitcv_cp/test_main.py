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


def _reload_main_module(monkeypatch: pytest.MonkeyPatch, *, backend: str) -> Any:
    monkeypatch.setenv("FITCV_CP_DATA_BACKEND", backend)
    sys.modules.pop("fitcv_cp.main", None)
    return importlib.import_module("fitcv_cp.main")


def test_build_app_sqlite_mode_skips_bigquery_client(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch, backend="sqlite")

    captured: dict[str, Any] = {}

    def _fake_create_app(*, bq: Any, project: str, dataset: str, redis_url: str) -> str:
        captured["bq"] = bq
        captured["project"] = project
        captured["dataset"] = dataset
        captured["redis_url"] = redis_url
        return "ok"

    monkeypatch.setattr(module, "create_app", _fake_create_app)
    monkeypatch.setattr(module, "_build_bigquery_client", lambda: (_ for _ in ()).throw(RuntimeError("should not be called")))

    result = module.build_app()

    assert result == "ok"
    assert captured["bq"] is None


def test_build_app_bigquery_mode_requires_project(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_main_module(monkeypatch, backend="sqlite")

    monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "bigquery")
    monkeypatch.delenv("GCP_PROJECT", raising=False)

    def _fake_load_cp() -> dict[str, Any]:
        return {
            "data_backend": {
                "type": "bigquery",
                "bigquery": {"project": "", "dataset": "fitcv"},
            }
        }

    monkeypatch.setattr(module, "load_control_plane_config", _fake_load_cp)

    with pytest.raises(ValueError, match="GCP_PROJECT must be set"):
        module.build_app()
