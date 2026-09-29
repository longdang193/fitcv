"""@meta
name: persistence
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared sqlite persistence helpers for fitcv runtime modules.
inputs:
  - Runtime config and environment values
outputs:
  - Normalized sqlite path
lifecycle:
  - status: active
"""

import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from fitcv.config import load_control_plane_config


@contextmanager
def sqlite_connection(*args: Any, **kwargs: Any) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(*args, **kwargs)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def get_local_sqlite_path() -> str:
    default_path = "data/fitcv_cp.sqlite3"
    env_path = str(os.environ.get("FITCV_CP_SQLITE_PATH") or "").strip()
    if env_path:
        return env_path
    try:
        cfg = load_control_plane_config()
    except Exception:
        return default_path
    data_backend = dict(cfg.get("data_backend") or {})
    sqlite_cfg = dict(data_backend.get("sqlite") or {})
    return str(sqlite_cfg.get("path") or default_path).strip() or default_path
