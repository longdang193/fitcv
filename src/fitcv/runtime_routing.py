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


@dataclass(frozen=True)
class CvGenerationRouting:
    provider: str
    base_url: str
    wire_api: str
    model: str
    timeout_seconds: float


def resolve_cv_generation_routing(config: dict[str, Any]) -> CvGenerationRouting:
    route = resolve_model_routing_part(
        "cv_generation_structured_write",
        model_fallback=get_cv_generation_model(config),
    )
    provider = str(route.get("provider") or "").strip().lower()
    base_url = str(route.get("base_url") or "").strip()
    wire_api = str(route.get("wire_api") or "").strip().lower() or "responses"
    model = str(route.get("model") or "").strip()
    timeout_seconds = float(str(route.get("timeout_seconds") or "").strip() or "120")
    return CvGenerationRouting(
        provider=provider,
        base_url=base_url,
        wire_api=wire_api,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def build_langgraph_env_overrides() -> dict[str, str]:
    try:
        enrich_route = resolve_model_routing_part("enrich_extraction")
        cv_route = resolve_model_routing_part("cv_generation_structured_write")
    except Exception:
        return {}

    provider = str(enrich_route.get("provider") or "").strip()
    base_url = str(enrich_route.get("base_url") or "").strip()
    wire_api = str(enrich_route.get("wire_api") or "").strip()
    model = str(cv_route.get("model") or "").strip()
    overrides: dict[str, str] = {}
    if provider:
        overrides["FITCV_LANGGRAPH_PROVIDER"] = provider
    if base_url:
        overrides["FITCV_LANGGRAPH_OPENAI_BASE_URL"] = base_url
    if wire_api:
        overrides["FITCV_LANGGRAPH_WIRE_API"] = wire_api
    if model:
        overrides["FITCV_LANGGRAPH_MODEL"] = model
    return overrides


def resolve_openai_compatible_api_key() -> str:
    return (
        str(os.environ.get("OPENAI_API_KEY") or "").strip()
        or str(os.environ.get("OPENAI_COMPATIBLE_API_KEY") or "").strip()
    )
