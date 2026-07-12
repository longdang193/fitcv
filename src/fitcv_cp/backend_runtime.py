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

from dataclasses import dataclass

from fitcv.config import load_control_plane_config
from fitcv.persistence import get_local_sqlite_path

_ACTIVE_BACKEND_RUNTIME: BackendRuntime | None = None


@dataclass(frozen=True, init=False)
class BackendRuntime:
    backend_type: str
    sqlite_path: str

    def __init__(self, backend_type: str, sqlite_path: str, **_compat_kwargs: object) -> None:
        object.__setattr__(self, "backend_type", backend_type)
        object.__setattr__(self, "sqlite_path", sqlite_path)


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
    if str(data_backend.get("type") or "sqlite").strip().lower() != "sqlite":
        raise ValueError("control_plane.data_backend.type must resolve to sqlite")
    return BackendRuntime(
        backend_type="sqlite",
        sqlite_path=get_local_sqlite_path(),
    )
