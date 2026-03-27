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
    """cv defaults are present after loading the full config."""
    cfg = load_config()
    assert cfg["cv_generation_model"] == "gemini-2.5-flash"
    assert cfg["cv"]["generation"]["model"] == "gemini-2.5-flash"
    assert cfg["cv"]["preset"] == "europass"
    assert cfg["cv"]["composition"]["summary"]["enabled"] is True
    assert cfg["cv"]["validation"]["max_pages"] == 2
    assert cfg["cv"]["generation"]["prompt_version"] == "v1"


def test_load_config_cv_keys_missing_raises(tmp_path: Path) -> None:
    """A config without cv.yaml keys should raise ValueError after loader validation."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    # No cv.yaml → missing top-level 'cv' key → ValueError
    with pytest.raises(ValueError, match="Missing top-level 'cv' key"):
        load_config(env_yaml)


def test_load_config_cv_required_sections_must_be_nonempty_list(tmp_path: Path) -> None:
    """required_cv_sections must be derivable from composition (at least one required section)."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    # composition with a required section → required_cv_sections will be non-empty
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: gemini-2.5-flash\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "      required: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    assert "Experience" in cfg["required_cv_sections"]


def test_load_config_cv_max_pages_must_be_positive(tmp_path: Path) -> None:
    """cv.validation.max_pages must be a positive integer."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: gemini-2.5-flash\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 0\n"
    )
    with pytest.raises(ValueError, match="max_pages"):
        load_config(env_yaml)


def test_load_config_env_yaml_overrides_nested_cv(tmp_path: Path) -> None:
    """.env.yaml keys take precedence over nested cv values in cv.yaml."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: my-custom-model\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    # cv.yaml also has generation.model — but env.yaml wins
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: gemini-2.5-flash\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 2\n"
    )
    cfg = load_config(env_yaml)
    # env.yaml value wins
    assert cfg["cv_generation_model"] == "my-custom-model"
    assert cfg["cv"]["generation"]["model"] == "my-custom-model"


# ── Task 1: nested preset-based cv config ─────────────────────────────────────


def test_load_config_returns_nested_cv_object() -> None:
    """load_config() must return a nested cv dict."""
    cfg = load_config()
    assert "cv" in cfg
    assert isinstance(cfg["cv"], dict)


def test_load_config_nested_cv_has_preset() -> None:
    cfg = load_config()
    assert "preset" in cfg["cv"]


def test_load_config_nested_cv_generation_has_model_and_prompt_version() -> None:
    cfg = load_config()
    assert "generation" in cfg["cv"]
    assert "model" in cfg["cv"]["generation"]
    assert "prompt_version" in cfg["cv"]["generation"]


def test_load_config_nested_cv_validation_has_max_pages() -> None:
    cfg = load_config()
    assert "validation" in cfg["cv"]
    assert "max_pages" in cfg["cv"]["validation"]


def test_load_config_nested_cv_composition_has_sections() -> None:
    cfg = load_config()
    assert "composition" in cfg["cv"]
    assert isinstance(cfg["cv"]["composition"], dict)


def test_load_config_compatibility_projection_cv_generation_model() -> None:
    """Legacy flat key must still be projected during the migration window."""
    cfg = load_config()
    # Compatibility projection: flat key must be present for control-plane compatibility
    assert "cv_generation_model" in cfg
    # And must match the nested value
    assert cfg["cv_generation_model"] == cfg["cv"]["generation"]["model"]


def test_load_config_compatibility_projection_cv_max_pages() -> None:
    cfg = load_config()
    assert "cv_max_pages" in cfg
    assert cfg["cv_max_pages"] == cfg["cv"]["validation"]["max_pages"]


def test_load_config_compatibility_projection_prompt_version() -> None:
    cfg = load_config()
    assert "prompt_version" in cfg
    assert cfg["prompt_version"] == cfg["cv"]["generation"]["prompt_version"]


def test_load_config_compatibility_projection_required_cv_sections() -> None:
    cfg = load_config()
    assert "required_cv_sections" in cfg
    # required_cv_sections is derived from composition.sections with enabled:true, required:true
    assert isinstance(cfg["required_cv_sections"], list)
    assert len(cfg["required_cv_sections"]) > 0


def test_load_config_nested_cv_validation_max_pages_positive(tmp_path: Path) -> None:
    """max_pages in the nested validation block must be a positive integer."""
    env_yaml = tmp_path / ".env.yaml"
    env_yaml.write_text(
        "gcp_project: test\nbigquery_dataset: ds\nservice_account_key: /dev/null\n"
    )
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "cv.yaml").write_text(
        "cv:\n"
        "  preset: europass\n"
        "  generation:\n"
        "    model: gemini-2.5-flash\n"
        "    prompt_version: v1\n"
        "  composition:\n"
        "    summary:\n"
        "      enabled: true\n"
        "    experience:\n"
        "      enabled: true\n"
        "      required: true\n"
        "  content_rules:\n"
        "    evidence_grounded_only: true\n"
        "  validation:\n"
        "    max_pages: 0\n"
    )
    with pytest.raises(ValueError, match="max_pages"):
        load_config(env_yaml)


# ── Task 2: preset registry ─────────────────────────────────────────────────────

def test_cv_presets_module_exists() -> None:
    """cv_presets.py must exist and define the preset registry."""
    from fitcv import cv_presets
    assert hasattr(cv_presets, "PRESET_REGISTRY")
    assert hasattr(cv_presets, "SUPPORTED_PRESETS")


def test_europass_is_a_supported_preset() -> None:
    from fitcv import cv_presets
    assert "europass" in cv_presets.SUPPORTED_PRESETS


def test_preset_registry_has_sections_for_europass() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "sections" in europass
    sections = europass["sections"]
    expected = {"summary", "education", "experience", "skills", "certifications", "projects", "publications", "languages"}
    assert set(sections.keys()) >= expected


def test_preset_registry_defines_section_ordering() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "section_order" in europass
    assert europass["section_order"][0] == "summary"


def test_preset_registry_defines_allowed_enum_values() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "allowed_values" in europass
    allowed = europass["allowed_values"]
    # summary styles
    assert "summary" in allowed
    assert "concise" in allowed["summary"].get("style", [])
    # detail levels
    assert "compact" in allowed.get("detail", [])
    assert "standard" in allowed.get("detail", [])
    assert "detailed" in allowed.get("detail", [])


def test_preset_registry_maps_template_path_for_europass() -> None:
    from fitcv import cv_presets
    europass = cv_presets.PRESET_REGISTRY["europass"]
    assert "template_path" in europass
    assert isinstance(europass["template_path"], str)
    assert europass["template_path"] == "templates/cv_template.md"


def test_get_required_sections_returns_europass_required() -> None:
    from fitcv import cv_presets
    sections = cv_presets.get_required_sections("europass")
    assert isinstance(sections, list)
    # europass default_required = experience, skills
    assert "experience" in sections
    assert "skills" in sections


def test_get_section_order_returns_europass_order() -> None:
    from fitcv import cv_presets
    order = cv_presets.get_section_order("europass")
    assert order[0] == "summary"
    assert "experience" in order


def test_validate_composition_rejects_unknown_section() -> None:
    from fitcv import cv_presets
    bad_composition = {"unknown_section": {"enabled": True}}
    result = cv_presets.validate_composition("europass", bad_composition)
    assert result["valid"] is False
    assert any("unknown_section" in err for err in result["errors"])


def test_validate_composition_accepts_valid_europass() -> None:
    from fitcv import cv_presets
    valid_composition = {
        "summary": {"enabled": True, "style": "concise"},
        "experience": {"enabled": True, "detail": "standard"},
    }
    result = cv_presets.validate_composition("europass", valid_composition)
    assert result["valid"] is True


def test_validate_composition_rejects_bad_enum_value() -> None:
    from fitcv import cv_presets
    bad_enum = {
        "summary": {"enabled": True, "style": "invalid_style"},
    }
    result = cv_presets.validate_composition("europass", bad_enum)
    assert result["valid"] is False
    assert any("invalid_style" in err for err in result["errors"])


def test_validate_composition_rejects_unknown_preset() -> None:
    from fitcv import cv_presets
    result = cv_presets.validate_composition("unknown_preset", {"summary": {"enabled": True}})
    assert result["valid"] is False
    assert any("unknown_preset" in err for err in result["errors"])


# ── Task 6: compatibility shim guard ───────────────────────────────────────────

def test_load_config_compatibility_flat_keys_work_after_nested_migration() -> None:
    """After migration to nested cv, flat keys are still projected for control-plane compatibility."""
    cfg = load_config()
    # These are the keys the control plane (settings_schema) still reads
    assert cfg["cv_generation_model"] == cfg["cv"]["generation"]["model"]
    assert cfg["prompt_version"] == cfg["cv"]["generation"]["prompt_version"]
    assert cfg["cv_max_pages"] == cfg["cv"]["validation"]["max_pages"]
    assert isinstance(cfg["required_cv_sections"], list)
    # required_cv_sections is derived from composition
    assert len(cfg["required_cv_sections"]) > 0


def test_load_config_compatibility_required_cv_sections_from_composition() -> None:
    """required_cv_sections is derived from composition (enabled:true AND required:true)."""
    cfg = load_config()
    # projects has required:true in cv.yaml, so it should appear in required_cv_sections
    assert "Projects" in cfg["required_cv_sections"]
    # publications has enabled:false, so it should NOT appear
    assert "Publications" not in cfg["required_cv_sections"]
