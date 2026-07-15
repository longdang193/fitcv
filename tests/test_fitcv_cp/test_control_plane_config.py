"""
@meta
type: test
scope: unit
domain: control_plane_config
covers:
  - control-plane runtime config loading and validation
excludes:
  - provider API calls
  - backend network connectivity
tags:
  - fast
  - ci-safe
"""

from pathlib import Path

import pytest

from fitcv.config import load_control_plane_config, resolve_cv_generation_runtime_expectation


def test_load_control_plane_config_defaults_from_runtime_yaml() -> None:
    cfg = load_control_plane_config()

    assert cfg["data_backend"]["type"] == "sqlite"

def test_load_control_plane_config_ignores_deprecated_route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CP_OPENAI_COMPATIBLE_BASE_URL", "http://override.local/v1")
    monkeypatch.setenv("FITCV_CP_OPENAI_COMPATIBLE_WIRE_API", "responses")

    cfg = load_control_plane_config()

    assert cfg["providers"]["openai_compatible"]["base_url"] == "http://host.docker.internal:20128/v1"
    assert cfg["providers"]["openai_compatible"]["wire_api"] == "chat_completions"
    assert "providers" in cfg
    assert "model_routing" in cfg
    assert "parts" in cfg["model_routing"]
    assert "observability" in cfg



def test_load_control_plane_config_rejects_invalid_backend_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "control_plane.yaml"
    config_path.write_text(
        "control_plane:\n"
        "  data_backend:\n"
        "    type: invalid_backend\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="data_backend.type"):
        load_control_plane_config(config_path)


def test_load_control_plane_config_rejects_secret_or_env_key_names(tmp_path: Path) -> None:
    config_path = tmp_path / "control_plane.yaml"
    config_path.write_text(
        "control_plane:\n"
        "  providers:\n"
        "    openai:\n"
        "      api_key_env: OPENAI_API_KEY\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden secret-oriented key names"):
        load_control_plane_config(config_path)

def test_resolve_cv_generation_runtime_expectation_uses_control_plane_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  providers:\n"
        "    openai_compatible:\n"
        "      base_url: http://router.local/v1\n"
        "      wire_api: chat_completions\n"
        "  model_routing:\n"
        "    parts:\n"
        "      cv_generation_structured_write:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n",
        encoding="utf-8",
    )
    resolved = resolve_cv_generation_runtime_expectation()

    assert resolved["provider"] == "openai_compatible"
    assert resolved["model"] == "cx/gpt-5.2"
    assert resolved["base_url"] == "http://router.local/v1"
    assert resolved["wire_api"] == "chat_completions"
    assert resolved["source"] == "control_plane"

def test_resolve_cv_generation_runtime_expectation_ignores_adapter_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  providers:\n"
        "    openai_compatible:\n"
        "      base_url: http://router.local/v1\n"
        "      wire_api: chat_completions\n"
        "  model_routing:\n"
        "    parts:\n"
        "      cv_generation_structured_write:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FITCV_LANGGRAPH_PROVIDER", "9router")
    monkeypatch.setenv("FITCV_LANGGRAPH_MODEL", "cx/gpt-5.3-codex")
    monkeypatch.setenv("FITCV_LANGGRAPH_OPENAI_BASE_URL", "http://override.local/v1")
    monkeypatch.setenv("FITCV_LANGGRAPH_WIRE_API", "responses")

    resolved = resolve_cv_generation_runtime_expectation()

    assert resolved["provider"] == "openai_compatible"
    assert resolved["model"] == "cx/gpt-5.2"
    assert resolved["base_url"] == "http://router.local/v1"
    assert resolved["wire_api"] == "chat_completions"
    assert resolved["source"] == "control_plane"

def test_resolve_cv_generation_runtime_expectation_fails_when_missing_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  providers:\n"
        "    openai_compatible:\n"
        "      base_url: http://router.local/v1\n"
        "  model_routing:\n"
        "    parts:\n"
        "      cv_generation_structured_write:\n"
        "        provider: openai_compatible\n"
        "        model: cx/gpt-5.2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing resolved CV-generation runtime routing fields: wire_api"):
        resolve_cv_generation_runtime_expectation()

