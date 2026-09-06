"""Canonical retry and worker-recovery settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from fitcv.config import load_control_plane_config
from fitcv_cp.retry_policy import (
    RETRY_POLICY_BOUNDS,
    RETRY_POLICY_DEFAULTS,
    RetryPolicy,
    normalize_retry_policy,
)

SYSTEM_SETTING_BOUNDS = RETRY_POLICY_BOUNDS
SYSTEM_SETTINGS_DEFAULTS = RETRY_POLICY_DEFAULTS


@dataclass(frozen=True)
class RetrySettings(RetryPolicy):
    revision: int = 0


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

    normalized = normalize_retry_policy(values)
    return RetrySettings(**normalized, revision=revision)


def _run_retry_snapshot(run: Any) -> dict[str, Any] | None:
    raw_settings = getattr(run, "settings_used_json", None)
    if not isinstance(raw_settings, str) or not raw_settings.strip():
        return None
    try:
        settings_used = json.loads(raw_settings)
    except (TypeError, ValueError):
        return None
    if not isinstance(settings_used, dict):
        return None
    effective_settings = settings_used.get("effective_settings")
    if not isinstance(effective_settings, dict):
        effective_settings = settings_used
    runtime_inputs = effective_settings.get("runtime_inputs")
    if not isinstance(runtime_inputs, dict):
        return None
    snapshot = runtime_inputs.get("system_settings_snapshot")
    if not isinstance(snapshot, dict):
        return None
    fields = tuple(RETRY_POLICY_DEFAULTS)
    if any(type(snapshot.get(field)) is not int for field in fields):
        return None
    if any(
        not (minimum <= snapshot[field] <= maximum)
        for field, (minimum, maximum) in RETRY_POLICY_BOUNDS.items()
    ):
        return None
    return snapshot


def get_run_retry_settings(run: Any) -> RetrySettings:
    """Return immutable Run retry settings, falling back for legacy Runs only."""
    snapshot = _run_retry_snapshot(run)
    if snapshot is None:
        return load_retry_settings()
    normalized = normalize_retry_policy(snapshot)
    revision = snapshot.get("revision", 0)
    return RetrySettings(**normalized, revision=revision if type(revision) is int else 0)
