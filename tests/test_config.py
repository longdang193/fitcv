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


# ── Task 1: cv.yaml config layer tests ────────────────────────────────────────


def test_load_config_includes_cv_defaults() -> None:
    """cv.yaml keys are present after loading the full config."""
    cfg = load_config()
    assert cfg["cv_generation_model"] == "gemini-2.5-flash"
    assert cfg["cv_template_path"] == "templates/cv_template.md"
    assert isinstance(cfg["required_cv_sections"], list)
    assert len(cfg["required_cv_sections"]) > 0
    assert int(cfg["cv_max_pages"]) > 0
    assert cfg["prompt_version"]


def test_load_config_cv_keys_missing_raises(tmp_path: Path) -> None:
    """A config without cv.yaml keys should raise ValueError after loader validation."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    # No cv.yaml in the config dir → required CV keys missing → ValueError
    with pytest.raises(ValueError, match="Missing CV config keys"):
        load_config(env_yaml)


def test_load_config_cv_required_sections_must_be_nonempty_list(tmp_path: Path) -> None:
    """required_cv_sections must be a non-empty list."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv_generation_model: gemini-2.5-flash\n"
        "cv_template_path: templates/cv_template.md\n"
        "required_cv_sections: []\n"
        "cv_max_pages: 2\n"
        "prompt_version: v1\n"
    )
    with pytest.raises(ValueError, match="required_cv_sections"):
        load_config(env_yaml)


def test_load_config_cv_max_pages_must_be_positive(tmp_path: Path) -> None:
    """cv_max_pages must be a positive integer."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv_generation_model: gemini-2.5-flash\n"
        "cv_template_path: templates/cv_template.md\n"
        "required_cv_sections: [Summary]\n"
        "cv_max_pages: 0\n"
        "prompt_version: v1\n"
    )
    with pytest.raises(ValueError, match="cv_max_pages"):
        load_config(env_yaml)


def test_load_config_env_yaml_overrides_cv_yaml(tmp_path: Path) -> None:
    """.env.yaml / higher layer keys take precedence over cv.yaml."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
        "cv_generation_model: my-custom-model\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv_generation_model: gemini-2.5-flash\n"
        "cv_template_path: templates/cv_template.md\n"
        "required_cv_sections: [Summary]\n"
        "cv_max_pages: 2\n"
        "prompt_version: v1\n"
    )
    cfg = load_config(env_yaml)
    # env.yaml value wins
    assert cfg["cv_generation_model"] == "my-custom-model"
