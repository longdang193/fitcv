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

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from fitcv.config import load_control_plane_config, resolve_cv_generation_runtime_expectation

_CANONICAL_CONTROL_PLANE_PATH = (
    Path(__file__).parents[2] / "config" / "runtime" / "control_plane.yaml"
)
_CANONICAL_CONTROL_PLANE = yaml.safe_load(
    _CANONICAL_CONTROL_PLANE_PATH.read_text(encoding="utf-8")
)["control_plane"]

def _write_control_plane_config(path: Path, control_plane: dict[str, object]) -> None:
    path.write_text(
        yaml.safe_dump({"control_plane": control_plane}, sort_keys=False),
        encoding="utf-8",
    )


def test_load_control_plane_config_defaults_from_runtime_yaml() -> None:
    cfg = load_control_plane_config()

    assert cfg["data_backend"]["type"] == "sqlite"

def test_load_control_plane_config_ignores_deprecated_route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CP_OPENAI_COMPATIBLE_BASE_URL", "http://override.local/v1")
    monkeypatch.setenv("FITCV_CP_OPENAI_COMPATIBLE_WIRE_API", "responses")

    cfg = load_control_plane_config()

    canonical_provider = _CANONICAL_CONTROL_PLANE["providers"]["openai_compatible"]
    assert cfg["providers"]["openai_compatible"]["base_url"] == canonical_provider["base_url"]
    assert cfg["providers"]["openai_compatible"]["wire_api"] == canonical_provider["wire_api"]
    assert "providers" in cfg
    assert "model_routing" in cfg
    assert "parts" in cfg["model_routing"]
    assert "observability" in cfg



def test_load_control_plane_config_rejects_invalid_backend_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "control_plane.yaml"
    control_plane = deepcopy(_CANONICAL_CONTROL_PLANE)
    control_plane["data_backend"]["type"] = "invalid_backend"
    _write_control_plane_config(config_path, control_plane)

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
    control_plane = deepcopy(_CANONICAL_CONTROL_PLANE)
    control_plane["providers"]["openai_compatible"].update(
        {"base_url": "http://router.local/v1", "wire_api": "chat_completions"}
    )
    control_plane["model_routing"]["parts"]["cv_generation_structured_write"].update(
        {"provider": "openai_compatible", "model": "cx/gpt-5.2"}
    )
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config" / "runtime" / "control_plane.yaml"
    config_path.parent.mkdir(parents=True)
    _write_control_plane_config(config_path, control_plane)

    resolved = resolve_cv_generation_runtime_expectation()

    assert resolved["provider"] == "openai_compatible"
    assert resolved["model"] == "cx/gpt-5.2"
    assert resolved["base_url"] == "http://router.local/v1"
    assert resolved["wire_api"] == "chat_completions"
    assert resolved["source"] == "control_plane"


def test_resolve_cv_generation_runtime_expectation_ignores_adapter_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    control_plane = deepcopy(_CANONICAL_CONTROL_PLANE)
    control_plane["providers"]["openai_compatible"].update(
        {"base_url": "http://router.local/v1", "wire_api": "chat_completions"}
    )
    control_plane["model_routing"]["parts"]["cv_generation_structured_write"].update(
        {"provider": "openai_compatible", "model": "cx/gpt-5.2"}
    )
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config" / "runtime" / "control_plane.yaml"
    config_path.parent.mkdir(parents=True)
    _write_control_plane_config(config_path, control_plane)
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
    control_plane = deepcopy(_CANONICAL_CONTROL_PLANE)
    del control_plane["providers"]["openai_compatible"]["wire_api"]
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config" / "runtime" / "control_plane.yaml"
    config_path.parent.mkdir(parents=True)
    _write_control_plane_config(config_path, control_plane)

    with pytest.raises(
        ValueError,
        match="control_plane.providers.openai_compatible.wire_api is required",
    ):
        resolve_cv_generation_runtime_expectation()
