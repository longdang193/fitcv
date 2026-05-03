"""
@meta
name: fitcv_cp_observability
type: utility
domain: observability
responsibility:
  - Emit structured control-plane diagnostics for backend and routing behavior.
inputs:
  - event names and diagnostic payload fields
outputs:
  - structured log events
lifecycle:
  status: active
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def emit_observability_event(event: str, payload: dict[str, Any]) -> None:
    body = {"event": event, **payload}
    logger.info(json.dumps(body, ensure_ascii=False, sort_keys=True))

