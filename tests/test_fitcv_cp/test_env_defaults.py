"""
@meta
type: test
scope: unit
domain: control_plane_startup
covers:
  - shared dotenv default loading for control-plane entrypoints
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_load_dotenv_defaults_sets_missing_process_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FITCV_LLM_API_KEY", raising=False)
    (tmp_path / ".env").write_text("FITCV_LLM_API_KEY=test-dotenv-key\n", encoding="utf-8")

    from fitcv_cp.env_defaults import load_dotenv_defaults

    load_dotenv_defaults(tmp_path / ".env")

    assert __import__("os").environ.get("FITCV_LLM_API_KEY") == "test-dotenv-key"
