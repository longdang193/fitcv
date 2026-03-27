"""Load project configuration from .env.yaml and config/*.yaml policy files.

Load order
----------
1. .env.yaml          — infrastructure secrets (GCP project, SA key, etc.)
2. config/taxonomy.yaml      — seniority ladder, allowed enum values
3. config/skill_synonyms.yaml — skill alias → canonical mapping
4. config/pipeline.yaml      — model names, top_n limits, batch/sleep settings
5. config/ranking.yaml        — ranking weights, fit-label thresholds, missing defaults
6. config/cv.yaml             — CV generation and validation defaults (nested preset-based)

Later files do NOT override .env.yaml keys. They only add new top-level keys.
Missing config/*.yaml files → warning logged, not a crash (safe degradation).

CV config contract (preset-based, v2)
-------------------------------------
config["cv"] is the canonical nested object:
  - cv.preset             : preset name string
  - cv.generation.model    : LLM model name
  - cv.generation.prompt_version : version tag
  - cv.composition.<section>.enabled : bool
  - cv.content_rules.<rule> : bool
  - cv.validation.max_pages : int

Backward-compatibility projection (TEMPORARY — remove after plan 2 lands)
  config["cv_generation_model"]   → cv.generation.model
  config["prompt_version"]        → cv.generation.prompt_version
  config["cv_max_pages"]           → cv.validation.max_pages
  config["required_cv_sections"]   → list derived from composition (enabled:true AND required:true)
"""

import logging
from fitcv.cv_presets import PRESET_REGISTRY, SUPPORTED_PRESETS
import warnings
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_REQUIRED_KEYS = [
    "gcp_project",
    "bigquery_dataset",
    "service_account_key",
]

# Optional — only needed when using the Apify API source
_APIFY_KEYS = ["apify_dataset_id", "apify_token"]

# Config YAML files merged into the base config (relative to repo root)
_POLICY_FILES = [
    "taxonomy.yaml",
    "skill_synonyms.yaml",
    "pipeline.yaml",
    "ranking.yaml",
    "cv.yaml",
]

_DEFAULT_ENV_CANDIDATES = (".env.yaml", "config/env.yaml")


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a single YAML file. Returns {} on missing file or empty file."""
    if not path.exists():
        logger.warning("Config file not found (skipping): %s", path)
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _find_config_dir(base_path: Path) -> Path:
    """Locate the config/ directory relative to .env.yaml or the repo root."""
    # Walk up from the .env.yaml location to find a config/ dir
    candidate = base_path.parent
    for _ in range(4):  # max 4 levels up
        config_dir = candidate / "config"
        if config_dir.is_dir():
            return config_dir
        candidate = candidate.parent
    return base_path.parent / "config"  # fallback: sibling of .env.yaml


def _resolve_env_path(path: str | Path | None) -> Path:
    """Resolve the active env file, supporting legacy config/env.yaml."""
    if path is not None:
        return Path(path)
    for candidate in _DEFAULT_ENV_CANDIDATES:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    return Path(_DEFAULT_ENV_CANDIDATES[0])


def _is_legacy_env_path(path: Path) -> bool:
    return path.name == "env.yaml" and path.parent.name == "config"


def _merge_missing_keys(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    for key, value in extra.items():
        if key not in base:
            base[key] = value
    return base


def _normalize_config_keys(cfg: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy config keys into the canonical runtime shape."""
    if "gemini_model" not in cfg and "ai_score_model" in cfg:
        cfg["gemini_model"] = cfg["ai_score_model"]
    if "vertex_location" not in cfg:
        location = str(cfg.get("location", "")).strip()
        if location and location.lower() != "us":
            cfg["vertex_location"] = location
    return cfg


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate config from .env.yaml, then merge policy YAML files.

    Args:
        path: Path to the .env.yaml config file.

    Returns:
        Merged config dict. Policy file keys are added alongside .env.yaml keys.
        .env.yaml keys always win on collision.

    Raises:
        FileNotFoundError: If .env.yaml does not exist.
        ValueError: If required infrastructure keys are missing from .env.yaml.
    """
    env_path = _resolve_env_path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Config file not found: {env_path}")
    if _is_legacy_env_path(env_path):
        warnings.warn(
            f"legacy config path in use: {env_path}",
            UserWarning,
            stacklevel=2,
        )

    with open(env_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    resolved_env_path = env_path.resolve()
    config_dir = _find_config_dir(resolved_env_path)
    if env_path.name == ".env.yaml":
        legacy_env_path = config_dir / "env.yaml"
        if legacy_env_path.exists():
            cfg = _merge_missing_keys(cfg, _load_yaml_file(legacy_env_path))
    elif _is_legacy_env_path(env_path):
        root_env_path = config_dir.parent / ".env.yaml"
        if root_env_path.exists():
            cfg = _merge_missing_keys(cfg, _load_yaml_file(root_env_path))

    cfg = _normalize_config_keys(cfg)

    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")

    # Merge policy YAML files — later files add keys; .env.yaml keys take priority
    for filename in _POLICY_FILES:
        policy = _load_yaml_file(config_dir / filename)
        for key, value in policy.items():
            if key not in cfg:  # never overwrite .env.yaml values
                cfg[key] = value

    cfg = _normalize_config_keys(cfg)
    _validate_nested_cv_config(cfg)
    cfg = _apply_cv_compatibility_projection(cfg)
    return cfg


def _validate_nested_cv_config(cfg: dict[str, Any]) -> None:
    """Validate the nested cv block after policy files are merged.

    Raises ValueError with a descriptive message for any violation.
    """
    if "cv" not in cfg:
        raise ValueError("Missing top-level 'cv' key in config")

    cv_cfg = cfg["cv"]

    if "preset" not in cv_cfg:
        raise ValueError("cv.preset is required")
    preset = str(cv_cfg["preset"])
    if preset not in SUPPORTED_PRESETS:
        raise ValueError(
            f"cv.preset must be one of {sorted(SUPPORTED_PRESETS)}, got: {preset!r}"
        )

    # generation block
    if "generation" not in cv_cfg:
        raise ValueError("cv.generation is required")
    gen = cv_cfg["generation"]
    if "model" not in gen:
        raise ValueError("cv.generation.model is required")
    if "prompt_version" not in gen:
        raise ValueError("cv.generation.prompt_version is required")

    # composition block
    if "composition" not in cv_cfg:
        raise ValueError("cv.composition is required")
    comp = cv_cfg["composition"]
    if not isinstance(comp, dict):
        raise ValueError("cv.composition must be a dict")
    # Validate composition against preset registry
    from fitcv.cv_presets import validate_composition
    comp_result = validate_composition(preset, comp)
    if not comp_result["valid"]:
        raise ValueError(
            f"cv.composition errors for preset '{preset}': {comp_result['errors']}"
        )

    # content_rules block
    if "content_rules" not in cv_cfg:
        raise ValueError("cv.content_rules is required")
    cr = cv_cfg["content_rules"]
    if not isinstance(cr, dict):
        raise ValueError("cv.content_rules must be a dict")

    # validation block
    if "validation" not in cv_cfg:
        raise ValueError("cv.validation is required")
    val = cv_cfg["validation"]
    if "max_pages" not in val:
        raise ValueError("cv.validation.max_pages is required")
    try:
        max_pages = int(val["max_pages"])
    except (TypeError, ValueError):
        raise ValueError(f"cv.validation.max_pages must be an integer, got: {val['max_pages']!r}")
    if max_pages <= 0:
        raise ValueError(f"cv.validation.max_pages must be a positive integer, got: {max_pages}")


# ── Compatibility projection (TEMPORARY — remove after preset-based admin settings plan lands) ─

def _apply_cv_compatibility_projection(cfg: dict[str, Any]) -> dict[str, Any]:
    """Project nested cv keys back to flat legacy keys for the migration window.

    This lets control-plane code (settings_schema, etc.) that still reads
    flat keys continue to function until the preset-based admin settings plan
    replaces those reads with nested ones.

    TEMPORARY: Must be removed once plan 2 (preset-based admin settings) is complete.
    """
    cv_cfg = cfg.get("cv")
    if cv_cfg is None:
        return cfg

    cfg["cv_generation_model"] = str(cv_cfg.get("generation", {}).get("model", ""))
    cfg["prompt_version"] = str(cv_cfg.get("generation", {}).get("prompt_version", ""))
    cfg["cv_max_pages"] = int(cv_cfg.get("validation", {}).get("max_pages", 2))

    # required_cv_sections: sections where enabled:true AND required:true,
    # plus preset defaults where the user has not overridden the required flag.
    preset = str(cv_cfg.get("preset", ""))
    required: list[str] = []
    comp = cv_cfg.get("composition") or {}
    preset_default_required: set[str] = set()
    if preset in PRESET_REGISTRY:
        preset_default_required = PRESET_REGISTRY[preset].get("default_required", set())
    for section_name, section_cfg in comp.items():
        if not isinstance(section_cfg, dict):
            continue
        enabled = section_cfg.get("enabled", False)
        explicitly_required = section_cfg.get("required", None)
        is_required = explicitly_required if explicitly_required is not None else (section_name in preset_default_required)
        if enabled and is_required:
            required.append(section_name.title())
    cfg["required_cv_sections"] = required

    return cfg


def get_vertex_location(config: dict[str, Any]) -> str:
    """Return the Vertex AI region, separate from BigQuery location."""
    vertex_location = str(config.get("vertex_location", "")).strip()
    if vertex_location:
        return vertex_location
    return "us-central1"
