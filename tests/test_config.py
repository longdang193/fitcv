"""Tests for config loading."""
from pathlib import Path

import pytest

from fitcv.config import get_vertex_location, load_config


def test_load_config_returns_dict() -> None:
    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")
    assert isinstance(cfg, dict)
    assert "gcp_project" in cfg
    assert "bigquery_dataset" in cfg


def test_load_config_has_required_keys() -> None:
    cfg = load_config(Path(__file__).parent.parent / ".env.yaml")
    assert cfg["gcp_project"] == "fitcv-491123"
    assert cfg["bigquery_dataset"] == "fitcv"
    assert "service_account_key" in cfg


def test_load_config_raises_for_missing_file() -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/.env.yaml")


def test_load_config_raises_for_missing_keys(tmp_path: Path) -> None:
    import pytest
    bad_yaml = tmp_path / ".env.yaml"
    bad_yaml.write_text("some_key: value\n")
    with pytest.raises(ValueError, match="Missing config keys"):
        load_config(bad_yaml)


def test_get_vertex_location_prefers_vertex_location() -> None:
    cfg = {"location": "US", "vertex_location": "us-central1"}
    assert get_vertex_location(cfg) == "us-central1"


def test_get_vertex_location_defaults_to_us_central1() -> None:
    cfg = {"location": "US"}
    assert get_vertex_location(cfg) == "us-central1"


def test_load_config_defaults_to_repo_config_shape() -> None:
    cfg = load_config()
    assert cfg["gcp_project"] == "fitcv-491123"
    assert cfg["gemini_model"] == "gemini-2.5-flash"
    assert cfg["vertex_location"] == "us-central1"
    assert cfg["paths"]["candidate_profile"] == "data/candidate_profile.yaml"


def test_load_config_accepts_legacy_config_env_path_with_warning() -> None:
    legacy_path = Path(__file__).parent.parent / "config" / "env.yaml"
    with pytest.warns(UserWarning, match="legacy config path"):
        cfg = load_config(legacy_path)
    assert cfg["gemini_model"] == "gemini-2.5-flash"
    assert cfg["vertex_location"] == "us-central1"
