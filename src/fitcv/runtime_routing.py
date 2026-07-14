"""@meta
name: runtime_routing
type: module
domain: runtime
ownership: feature
capabilities:
  - inspection_debugging.cv-generation-diagnostics
responsibility:
  - Provide SSOT routing translation and env override helpers for CV generation paths.
inputs:
  - routing-capable config dictionaries and process environment
outputs:
  - canonical routing object, langgraph env overrides, resolved API key
lifecycle:
  - status: active
"""
from dataclasses import dataclass
import os
from typing import Any

from fitcv.config import get_cv_generation_model, resolve_model_routing_part

_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible", "9router"}
_OPENAI_COMPATIBLE_API_KEY_ENV_NAMES = (
    "FITCV_LLM_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_COMPATIBLE_API_KEY",
)
_LANGGRAPH_OPENAI_COMPATIBLE_API_KEY_ENV_NAMES = (
    "FITCV_LANGGRAPH_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_COMPATIBLE_API_KEY",
)

@dataclass(frozen=True)
class LlmRouting:
    provider: str
    base_url: str
    wire_api: str
    model: str
    timeout_seconds: float


@dataclass(frozen=True)
class CvGenerationRouting(LlmRouting):
    pass


def build_runtime_routing_snapshot(
    *,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    wire_api: str | None,
    api_key: str | None,
    default_provider: str,
    default_model: str,
    default_wire_api: str,
) -> dict[str, Any]:
    normalized_provider = str(provider or "").strip().lower() or default_provider
    normalized_model = str(model or "").strip() or default_model
    normalized_base_url = str(base_url or "").strip() or None
    normalized_wire_api = str(wire_api or "").strip().lower() or default_wire_api
    return {
        "provider": normalized_provider,
        "model": normalized_model,
        "base_url": normalized_base_url,
        "wire_api": normalized_wire_api,
        "api_key_available": bool(str(api_key or "").strip()),
    }


def resolve_llm_routing(part_name: str, *, model_fallback: str = "") -> LlmRouting:
    normalized_part_name = str(part_name or "").strip()
    if not normalized_part_name:
        raise ValueError("part_name must be non-empty")
    route = resolve_model_routing_part(
        normalized_part_name,
        model_fallback=str(model_fallback or "").strip(),
    )
    timeout_seconds = float(str(route.get("timeout_seconds") or "").strip() or "120")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    return LlmRouting(
        provider=str(route.get("provider") or "").strip().lower(),
        base_url=str(route.get("base_url") or "").strip(),
        wire_api=str(route.get("wire_api") or "").strip().lower() or "responses",
        model=str(route.get("model") or "").strip(),
        timeout_seconds=timeout_seconds,
    )


def resolve_llm_api_key(route: LlmRouting) -> str:
    if route.provider in _OPENAI_COMPATIBLE_PROVIDERS:
        return resolve_openai_compatible_api_key()
    return ""


def validate_llm_routing_ready(route: LlmRouting, *, api_key: str | None = None) -> None:
    if not route.provider:
        raise RuntimeError("LLM routing requires provider in control-plane model_routing.parts.")
    if not route.model:
        raise RuntimeError("LLM routing requires model in control-plane model_routing.parts.")
    if route.provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        return
    if not route.base_url:
        raise RuntimeError("OpenAI-compatible LLM routing requires provider base_url in control-plane config.")
    if not str(api_key if api_key is not None else resolve_llm_api_key(route)).strip():
        raise RuntimeError("OpenAI-compatible LLM routing requires API key in env.")


def resolve_cv_generation_routing(config: dict[str, Any]) -> CvGenerationRouting:
    route = resolve_llm_routing(
        "cv_generation_structured_write",
        model_fallback=get_cv_generation_model(config),
    )
    return CvGenerationRouting(
        provider=route.provider,
        base_url=route.base_url,
        wire_api=route.wire_api,
        model=route.model,
        timeout_seconds=route.timeout_seconds,
    )


def build_langgraph_env_overrides() -> dict[str, str]:
    try:
        cv_route = resolve_model_routing_part("cv_generation_structured_write")
    except Exception:
        return {}

    snapshot = build_runtime_routing_snapshot(
        provider=str(cv_route.get("provider") or "").strip(),
        model=str(cv_route.get("model") or "").strip(),
        base_url=str(cv_route.get("base_url") or "").strip(),
        wire_api=str(cv_route.get("wire_api") or "").strip(),
        api_key="",
        default_provider="",
        default_model="",
        default_wire_api="",
    )
    overrides: dict[str, str] = {}
    if snapshot["provider"]:
        overrides["FITCV_LANGGRAPH_PROVIDER"] = str(snapshot["provider"])
    if snapshot["base_url"]:
        overrides["FITCV_LANGGRAPH_OPENAI_BASE_URL"] = str(snapshot["base_url"])
    if snapshot["wire_api"]:
        overrides["FITCV_LANGGRAPH_WIRE_API"] = str(snapshot["wire_api"])
    if snapshot["model"]:
        overrides["FITCV_LANGGRAPH_MODEL"] = str(snapshot["model"])
    return overrides


def langgraph_override_drift_fields(*, part_name: str = "cv_generation_structured_write") -> list[str]:
    routed = resolve_model_routing_part(part_name)
    env_provider = str(os.environ.get("FITCV_LANGGRAPH_PROVIDER") or "").strip().lower()
    env_model = str(os.environ.get("FITCV_LANGGRAPH_MODEL") or "").strip()
    env_base_url = str(os.environ.get("FITCV_LANGGRAPH_OPENAI_BASE_URL") or "").strip()
    env_wire_api = str(os.environ.get("FITCV_LANGGRAPH_WIRE_API") or "").strip()
    if not any((env_provider, env_model, env_base_url, env_wire_api)):
        return []

    routed_provider = str(routed.get("provider") or "").strip().lower()
    routed_model = str(routed.get("model") or "").strip()
    routed_base_url = str(routed.get("base_url") or "").strip()
    routed_wire_api = str(routed.get("wire_api") or "").strip()
    drift_fields: list[str] = []
    if env_provider and env_provider != routed_provider:
        drift_fields.append("provider")
    if env_model and env_model != routed_model:
        drift_fields.append("model")
    if env_base_url and env_base_url != routed_base_url:
        drift_fields.append("base_url")
    if env_wire_api and env_wire_api != routed_wire_api:
        drift_fields.append("wire_api")
    return drift_fields


def _resolve_first_present_env(env_names: tuple[str, ...]) -> str:
    for env_name in env_names:
        candidate = str(os.environ.get(env_name) or "").strip()
        if candidate:
            return candidate
    return ""


def resolve_openai_compatible_api_key() -> str:
    return _resolve_first_present_env(_OPENAI_COMPATIBLE_API_KEY_ENV_NAMES)


def resolve_langgraph_openai_compatible_api_key() -> str:
    return _resolve_first_present_env(_LANGGRAPH_OPENAI_COMPATIBLE_API_KEY_ENV_NAMES)


def resolve_cv_generation_routing_snapshot(
    config: dict[str, Any],
    *,
    default_model: str | None = None,
) -> dict[str, Any]:
    fallback_model = str(default_model or "").strip()
    try:
        routing = resolve_cv_generation_routing(config)
    except Exception:
        snapshot = build_runtime_routing_snapshot(
            provider="fitcv_builtin",
            model=fallback_model,
            base_url=None,
            wire_api="responses",
            api_key="",
            default_provider="fitcv_builtin",
            default_model=fallback_model,
            default_wire_api="responses",
        )
        snapshot["runtime_path"] = "fitcv_cv_generation_builtin"
        return snapshot
    provider = str(routing.provider or "").strip().lower() or "fitcv_builtin"
    snapshot = build_runtime_routing_snapshot(
        provider=provider,
        model=str(routing.model or "").strip() or fallback_model,
        base_url=routing.base_url,
        wire_api=routing.wire_api,
        api_key=(resolve_openai_compatible_api_key() if provider in _OPENAI_COMPATIBLE_PROVIDERS else ""),
        default_provider="fitcv_builtin",
        default_model=fallback_model,
        default_wire_api="responses",
    )
    snapshot["runtime_path"] = (
        "fitcv_cv_generation_openai_compatible"
        if provider in _OPENAI_COMPATIBLE_PROVIDERS
        else "fitcv_cv_generation_builtin"
    )
    return snapshot


def resolve_cv_generation_runtime_provenance(
    config: dict[str, Any],
    *,
    default_model: str | None = None,
) -> dict[str, Any]:
    """Return truthful runtime provenance aligned to resolved routing."""
    snapshot = resolve_cv_generation_routing_snapshot(config, default_model=default_model)
    return {
        "runtime_path": snapshot["runtime_path"],
        "provider": snapshot["provider"],
        "model": str(snapshot.get("model") or "").strip() or None,
    }


def validate_cv_generation_routing_ready(config: dict[str, Any]) -> None:
    """Raise when resolved CV-generation routing lacks required runtime inputs."""
    routing = resolve_cv_generation_routing(config)
    try:
        validate_llm_routing_ready(routing)
    except RuntimeError as exc:
        message = str(exc)
        if "base_url" in message:
            raise RuntimeError(
                "OpenAI-compatible CV generation routing requires provider base_url in control-plane config."
            ) from exc
        if "model" in message:
            raise RuntimeError(
                "cv_generation_structured_write model must be configured in control-plane model_routing.parts."
            ) from exc
        if "API key" in message:
            raise RuntimeError("OpenAI-compatible CV generation routing requires API key in env.") from exc
        raise
