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
from typing import Any

from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import resolve_backend_runtime, set_backend_runtime
from fitcv_cp.env_defaults import load_dotenv_defaults

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


def build_app() -> Any:
    load_dotenv_defaults()
    from fitcv_cp.local_storage import activate_local_storage, is_local_mode

    if is_local_mode():
        activate_local_storage()
    _ensure_safe_local_execution_mode()
    runtime = resolve_backend_runtime()
    set_backend_runtime(runtime)
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    logger.info("control-plane backend mode: sqlite")
    return create_app(redis_url=redis_url, backend_runtime=runtime)


app = build_app()
