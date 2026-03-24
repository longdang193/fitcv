"""Tests for config loading."""
from pathlib import Path

from fitcv.config import load_config


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
