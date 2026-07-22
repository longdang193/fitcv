"""Canonical retry and worker-recovery settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fitcv.config import load_control_plane_config

SYSTEM_SETTINGS_DEFAULTS = {
    "maximum_attempts": 3,
    "initial_backoff_seconds": 10,
    "lease_seconds": 300,
    "reconciler_interval_seconds": 30,
    "error_detail_limit": 10000,
}

SYSTEM_SETTING_BOUNDS = {
    "maximum_attempts": (1, 10),
    "initial_backoff_seconds": (0, 3600),
    "lease_seconds": (30, 86400),
    "reconciler_interval_seconds": (5, 3600),
    "error_detail_limit": (1000, 100000),
}


@dataclass(frozen=True)
class RetrySettings:
    maximum_attempts: int
    initial_backoff_seconds: int
    lease_seconds: int
    reconciler_interval_seconds: int
    error_detail_limit: int
    revision: int = 0


def _bounded_int(value: Any, *, field: str) -> int:
    default = SYSTEM_SETTINGS_DEFAULTS[field]
    minimum, maximum = SYSTEM_SETTING_BOUNDS[field]
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def load_retry_settings(control_plane_cfg: dict[str, Any] | None = None) -> RetrySettings:
    """Load one effective retry/recovery resource for all runtime consumers."""
    local_mode = str(os.environ.get("FITCV_LOCAL_MODE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if control_plane_cfg is None and local_mode:
        from fitcv_cp.settings_store import load_system_settings

        resource = load_system_settings()
        values = resource
        revision = int(resource["revision"])
    else:
        cfg = load_control_plane_config() if control_plane_cfg is None else control_plane_cfg
        values = dict((dict(cfg.get("fitcv_cp") or {}).get("retry") or {}))
        revision = 0

    normalized = {
        field: _bounded_int(values.get(field), field=field)
        for field in SYSTEM_SETTINGS_DEFAULTS
    }
    return RetrySettings(**normalized, revision=revision)
