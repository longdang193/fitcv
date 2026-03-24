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


def load_config(path: str | Path = ".env.yaml") -> dict[str, Any]:
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
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Config file not found: {env_path}")

    with open(env_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")

    # Merge policy YAML files — later files add keys; .env.yaml keys take priority
    config_dir = _find_config_dir(env_path.resolve())
    for filename in _POLICY_FILES:
        policy = _load_yaml_file(config_dir / filename)
        for key, value in policy.items():
            if key not in cfg:  # never overwrite .env.yaml values
                cfg[key] = value

    return cfg
