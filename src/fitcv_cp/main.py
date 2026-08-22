"""@meta
name: main
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.main.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fitcv.config import load_config
from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import resolve_backend_runtime, set_backend_runtime
from fitcv_cp.env_defaults import load_dotenv_defaults
from fitcv_cp.sqlite_store import ensure_control_plane_database

logger = logging.getLogger(__name__)


def _ensure_safe_local_execution_mode() -> None:
    """Default to inline execution for bare local web starts on Windows."""
    if os.name != "nt":
        return
    raw = str(os.environ.get("FITCV_CP_INLINE_EXECUTION", "") or "").strip().lower()
    redis_url = str(os.environ.get("REDIS_URL", "") or "").strip()
    if not redis_url:
        if raw in {"1", "true", "yes", "on"}:
            return
        os.environ["FITCV_CP_INLINE_EXECUTION"] = "1"
        logger.warning(
            "FITCV_CP_INLINE_EXECUTION was disabled on Windows without REDIS_URL; defaulted to inline mode."
        )
        return
    if not raw:
        os.environ["FITCV_CP_INLINE_EXECUTION"] = "0"
        logger.warning(
            "FITCV_CP_INLINE_EXECUTION was unset on Windows; defaulted to queue mode (inline disabled)."
        )


def _resolve_candidate_profile_path() -> Path:
    config = load_config()
    candidate_profile_path = str(
        dict(config.get("paths") or {}).get("candidate_profile") or ""
    ).strip()
    if not candidate_profile_path:
        raise ValueError("paths.candidate_profile must be configured")
    return Path(candidate_profile_path)


def build_app() -> Any:
    load_dotenv_defaults()
    from fitcv_cp.local_storage import activate_local_storage, is_local_mode

    local_mode = is_local_mode()
    if local_mode:
        activate_local_storage()
    _ensure_safe_local_execution_mode()
    runtime = resolve_backend_runtime()
    set_backend_runtime(runtime)
    if not local_mode:
        ensure_control_plane_database(
            Path(runtime.sqlite_path),
            _resolve_candidate_profile_path(),
        )
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    logger.info("control-plane backend mode: sqlite")
    application = create_app(redis_url=redis_url, backend_runtime=runtime)
    try:
        from fitcv_cp.reporter import retry_pending_process_event_deliveries

        retry_pending_process_event_deliveries(limit=20)
    except Exception as exc:
        logger.warning("Pending process-event delivery retry failed during app startup: %s", exc)
    return application


app = build_app()
