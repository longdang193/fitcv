"""@meta
name: env_defaults
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Load local dotenv defaults into process env without overriding existing values.
inputs:
  - Optional dotenv path
outputs:
  - Process environment mutations for missing keys only
lifecycle:
  - status: active
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_dotenv_defaults(dotenv_path: Path | None = None) -> None:
    path = dotenv_path or (Path.cwd() / ".env")
    if not path.exists() or not path.is_file():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_key = key.strip()
            if not env_key or os.environ.get(env_key) is not None:
                continue
            os.environ[env_key] = value.strip().strip("'\"")
    except OSError as exc:
        logger.warning("Failed to read .env defaults from %s: %s", path, exc)
