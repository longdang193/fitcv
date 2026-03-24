"""Load project configuration from .env.yaml."""

from pathlib import Path

import yaml

_REQUIRED_KEYS = [
    "gcp_project",
    "bigquery_dataset",
    "service_account_key",
]

# Optional — only needed when using the Apify API source
_APIFY_KEYS = ["apify_dataset_id", "apify_token"]


def load_config(path: str | Path = ".env.yaml") -> dict[str, object]:
    """Load and validate config from a YAML file.

    Args:
        path: Path to the .env.yaml config file.

    Returns:
        Parsed config dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required config keys are missing.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        cfg: dict[str, object] = yaml.safe_load(f)

    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")

    return cfg
