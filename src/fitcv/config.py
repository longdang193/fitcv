"""Load project configuration from .env.yaml and config/*.yaml policy files.

Load order
----------
1. .env.yaml          — infrastructure secrets (GCP project, SA key, etc.)
2. config/taxonomy.yaml      — seniority ladder, allowed enum values
3. config/skill_synonyms.yaml — skill alias → canonical mapping
4. config/pipeline.yaml      — model names, top_n limits, batch/sleep settings
5. config/ranking.yaml        — ranking weights, fit-label thresholds, missing defaults

Later files do NOT override .env.yaml keys. They only add new top-level keys.
Missing config/*.yaml files → warning logged, not a crash (safe degradation).
"""

import logging
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

    return _normalize_config_keys(cfg)


def get_vertex_location(config: dict[str, Any]) -> str:
    """Return the Vertex AI region, separate from BigQuery location."""
    vertex_location = str(config.get("vertex_location", "")).strip()
    if vertex_location:
        return vertex_location
    return "us-central1"
