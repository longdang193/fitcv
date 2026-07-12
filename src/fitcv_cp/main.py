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

from fitcv.runtime_routing import langgraph_override_drift_fields
from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import resolve_backend_runtime, set_backend_runtime

logger = logging.getLogger(__name__)


def _load_dotenv_defaults() -> None:
    """Load local `.env` defaults without overriding existing process env."""
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return
    try:
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_key = key.strip()
            if not env_key or os.environ.get(env_key) is not None:
                continue
            os.environ[env_key] = value.strip().strip("'\"")
    except OSError as exc:
        logger.warning("Failed to read .env defaults from %s: %s", dotenv_path, exc)


def _warn_or_fail_langgraph_override_drift() -> None:
    """Detect env override drift against control-plane SSOT routing."""
    drift_fields = langgraph_override_drift_fields()
    if not drift_fields:
        return

    message = (
        "LangGraph env override conflicts with control-plane routing SSOT "
        f"(fields={','.join(drift_fields)}). "
        "Clear FITCV_LANGGRAPH_* env vars or align them with config/runtime/control_plane.yaml."
    )
    strict = str(os.environ.get("FITCV_LANGGRAPH_OVERRIDE_STRICT") or "").strip().lower() in {"1", "true", "yes", "on"}
    if strict:
        raise RuntimeError(message)
    logger.warning(message)


def _ensure_safe_local_execution_mode() -> None:
    """Default to queue execution on Windows when execution mode is unset."""
    if os.name != "nt":
        return
    raw = str(os.environ.get("FITCV_CP_INLINE_EXECUTION", "") or "").strip().lower()
    if raw:
        return
    os.environ["FITCV_CP_INLINE_EXECUTION"] = "0"
    logger.warning(
        "FITCV_CP_INLINE_EXECUTION was unset on Windows; defaulted to queue mode (inline disabled)."
    )


def build_app() -> Any:
    _load_dotenv_defaults()
    _ensure_safe_local_execution_mode()
    _warn_or_fail_langgraph_override_drift()
    runtime = resolve_backend_runtime()
    set_backend_runtime(runtime)
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    logger.info("control-plane backend mode: sqlite")
    return create_app(redis_url=redis_url, backend_runtime=runtime)


app = build_app()
