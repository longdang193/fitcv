"""@meta
name: local_setup
type: utility
domain: fitcv_local
ownership: feature
responsibility:
  - Validate local provider and model setup.
  - Persist narrow non-secret routing overlay atomically.
inputs:
  - Provider fields, model routes, credential configured state
outputs:
  - Validated routing overlay and readiness result
capabilities:
  - settings_system.settings-schema-registry
  - settings_system.baseline-default-hydration
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict

from fitcv.config import (
    LOCAL_CONTROLLER_OVERLAY_VERSION,
    SUPPORTED_PROVIDER_IDS,
    SUPPORTED_ROUTING_PARTS,
    normalize_api_root,
    validate_local_controller_overlay,
)
from fitcv_cp.local_storage import write_controller_overlay


AuthMode = Literal["required", "optional", "none"]
WireApi = Literal["responses", "chat_completions"]
TASK_PARTS = SUPPORTED_ROUTING_PARTS
PROVIDER_IDS = SUPPORTED_PROVIDER_IDS

@dataclass(frozen=True)
class ProviderSetup:
    provider_id: str
    provider_type: Literal["openai", "openai_compatible"]
    display_name: str
    base_url: str
    auth_mode: AuthMode
    wire_api: WireApi
    timeout_seconds: float
    default_model: str
    task_models: dict[str, str]
    run_retry: dict[str, Any] = field(default_factory=dict)
    prompt_addenda: dict[str, str] = field(default_factory=dict)


class ReadinessResult(TypedDict):
    ready: bool
    reasons: list[str]
    overlay: dict[str, Any]


def build_routing_overlay(setup: ProviderSetup) -> dict[str, Any]:
    if setup.provider_id not in PROVIDER_IDS:
        raise ValueError(f"unsupported provider_id: {setup.provider_id}")
    if setup.auth_mode not in {"required", "optional", "none"}:
        raise ValueError("auth_mode must be required, optional, or none")
    if setup.wire_api not in {"responses", "chat_completions"}:
        raise ValueError("wire_api must be responses or chat_completions")
    if setup.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    default_model = str(setup.default_model or "").strip()
    if not default_model:
        raise ValueError("default_model must be non-empty")
    unknown_parts = sorted(set(setup.task_models) - set(TASK_PARTS))
    if unknown_parts:
        raise ValueError(f"unsupported task model parts: {unknown_parts}")
    provider = {
        "base_url": normalize_api_root(setup.base_url),
        "auth_mode": setup.auth_mode,
        "wire_api": setup.wire_api,
        "timeout_seconds": setup.timeout_seconds,
    }
    parts = {
        part: {
            "provider": setup.provider_id,
            "model": str(setup.task_models.get(part) or default_model).strip(),
        }
        for part in TASK_PARTS
    }
    payload: dict[str, Any] = {
        "version": LOCAL_CONTROLLER_OVERLAY_VERSION,
        "providers": {setup.provider_id: provider},
        "model_routing": {"parts": parts},
    }
    if setup.run_retry:
        payload["fitcv_cp"] = {"retry": dict(setup.run_retry)}
    if setup.prompt_addenda:
        payload["prompts"] = {
            "additional_instructions": dict(setup.prompt_addenda)
        }
    return validate_local_controller_overlay(payload)


def write_routing_overlay(path: Path, payload: dict[str, Any]) -> None:
    write_controller_overlay(path, payload)


def discover_models(setup: ProviderSetup, *, api_key: str = "") -> list[str]:
    from fitcv_cp.provider_registry import discover_provider_models

    return discover_provider_models(
        compatibility="openai",
        base_url=setup.base_url,
        api_key=api_key,
        timeout_seconds=setup.timeout_seconds,
    )


def test_provider(setup: ProviderSetup, *, api_key: str = "") -> dict[str, object]:
    from fitcv_cp.provider_registry import validate_connection_draft

    return validate_connection_draft(
        compatibility="openai",
        base_url=setup.base_url,
        api_type=setup.wire_api,
        api_key=api_key,
        timeout_seconds=setup.timeout_seconds,
    )


def readiness(
    setup: ProviderSetup, *, credential_configured: bool, provider_test_ok: bool
) -> ReadinessResult:
    overlay = build_routing_overlay(setup)
    reasons: list[str] = []
    if setup.auth_mode == "required" and not credential_configured:
        reasons.append("Provider credential is required")
    parts = dict((overlay["model_routing"] or {}).get("parts") or {})
    missing = [part for part in TASK_PARTS if not str((parts.get(part) or {}).get("model") or "").strip()]
    if missing:
        reasons.append(f"Missing model routes: {', '.join(missing)}")
    if not provider_test_ok:
        reasons.append("Provider connection test has not succeeded")
    return {"ready": not reasons, "reasons": reasons, "overlay": overlay}
