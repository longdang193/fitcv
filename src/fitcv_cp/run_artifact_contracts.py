"""@meta
name: run_artifact_contracts
type: module
domain: run_orchestration
ownership: infrastructure
responsibility:
  - Provide shared SSOT helper contracts for run artifact payload construction.
inputs:
  - run records, replay context, and runtime artifact values
outputs:
  - normalized run-mode labels and JSON-safe artifact payload fragments
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
from typing import Any

RUN_MODE_LABELS = {
    "run_all": "Run All",
    "manual_staged": "Stage by Stage",
}


def string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def normalized_run_mode(value: Any) -> str:
    run_mode = string_or_none(value)
    if run_mode in RUN_MODE_LABELS:
        return run_mode
    return "run_all"


def run_mode_label(value: Any) -> str:
    return RUN_MODE_LABELS[normalized_run_mode(value)]


def iso_or_none(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime.datetime) else None


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return [json_safe(item) for item in sorted(value)]
    return value


def replay_context_payload(*, replay_context: dict[str, Any], run_id: str) -> dict[str, str]:
    return {
        "replay_mode": str(replay_context.get("replay_mode") or "strict"),
        "replay_source_run_id": str(replay_context.get("replay_source_run_id") or run_id),
        "policy_registry_version": str(replay_context.get("policy_registry_version") or "policy_registry.v1"),
        "policy_envelope_signature": str(replay_context.get("policy_envelope_signature") or ""),
    }
