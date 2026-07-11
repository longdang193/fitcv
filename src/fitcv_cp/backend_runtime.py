"""@meta
name: backend_runtime
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.backend_runtime.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fitcv.config import load_control_plane_config

_ACTIVE_BACKEND_RUNTIME: BackendRuntime | None = None


@dataclass(frozen=True)
class BackendRuntime:
    backend_type: str
    project: str
    dataset: str
    sqlite_path: str


def set_backend_runtime(runtime: BackendRuntime | None) -> None:
    """Set process-wide backend runtime for live data-plane helpers."""
    global _ACTIVE_BACKEND_RUNTIME
    _ACTIVE_BACKEND_RUNTIME = runtime


def get_backend_runtime() -> BackendRuntime | None:
    """Return active backend runtime when startup already resolved it."""
    return _ACTIVE_BACKEND_RUNTIME


def resolve_backend_runtime_or_active() -> BackendRuntime:
    active = get_backend_runtime()
    if active is not None:
        return active
    return resolve_backend_runtime()


def resolve_backend_runtime() -> BackendRuntime:
    """Resolve SQLite-only runtime connection settings."""
    cfg = load_control_plane_config()
    data_backend = dict(cfg.get("data_backend") or {})
    sqlite_cfg = dict(data_backend.get("sqlite") or {})
    sqlite_path = str(
        os.environ.get("FITCV_CP_SQLITE_PATH")
        or sqlite_cfg.get("path")
        or "data/fitcv_cp.sqlite3"
    ).strip() or "data/fitcv_cp.sqlite3"
    project = str(os.environ.get("GCP_PROJECT") or "local").strip() or "local"
    dataset = str(os.environ.get("FITCV_CP_DATASET") or "fitcv").strip() or "fitcv"
    return BackendRuntime(
        backend_type="sqlite",
        project=project,
        dataset=dataset,
        sqlite_path=sqlite_path,
    )
