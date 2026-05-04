"""
Minimal OpenTelemetry runtime helpers with safe fallback behavior.
"""

from __future__ import annotations

import hashlib
import os
import threading
from typing import Any

_INIT_LOCK = threading.Lock()
_INITIALIZED = False
_DEGRADED_REASON: str | None = None
_OTEL_ENABLED = False

def reset_telemetry_runtime_for_tests() -> None:
    global _INITIALIZED, _DEGRADED_REASON, _OTEL_ENABLED
    with _INIT_LOCK:
        _INITIALIZED = False
        _DEGRADED_REASON = None
        _OTEL_ENABLED = False


def _otel_id(seed: str, *, length: int) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:length]


def _is_truthy(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "on"}

def _normalized_env(value: str | None) -> str:
    return str(value or "").strip()


def setup_telemetry_runtime() -> dict[str, Any]:
    global _INITIALIZED, _DEGRADED_REASON, _OTEL_ENABLED
    with _INIT_LOCK:
        if _INITIALIZED:
            return {"enabled": _OTEL_ENABLED, "degraded_reason": _DEGRADED_REASON}
        _INITIALIZED = True
        _OTEL_ENABLED = _is_truthy(os.environ.get("FITCV_OTEL_ENABLED"))

        if not _OTEL_ENABLED:
            return {"enabled": False, "degraded_reason": None}

        try:
            from opentelemetry import trace  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
        except Exception:
            _DEGRADED_REASON = "otel_dependency_missing"
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}

        endpoint = str(os.environ.get("FITCV_OTEL_EXPORTER_OTLP_ENDPOINT", "") or "").strip()
        if not endpoint:
            _DEGRADED_REASON = "otel_exporter_endpoint_missing"
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}

        try:
            service_name = str(os.environ.get("FITCV_OTEL_SERVICE_NAME", "fitcv-control-plane") or "fitcv-control-plane")
            provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            _OTEL_ENABLED = True
            _DEGRADED_REASON = None
            return {"enabled": True, "degraded_reason": None}
        except Exception:
            _DEGRADED_REASON = "otel_exporter_init_failed"
            _OTEL_ENABLED = False
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}


def build_trace_context(seed: str, *, parent_seed: str | None = None) -> dict[str, str]:
    setup_telemetry_runtime()
    trace_id = _otel_id(seed, length=32)
    span_id = _otel_id(f"{seed}:span", length=16)
    parent_source = parent_seed or f"{seed}:parent"
    parent_span_id = _otel_id(parent_source, length=16)

    if not _OTEL_ENABLED:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
        }

    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.trace.span import format_span_id, format_trace_id  # type: ignore

        tracer = trace.get_tracer("fitcv.telemetry")
        with tracer.start_as_current_span(seed) as span:
            ctx = span.get_span_context()
            current = trace.get_current_span()
            parent_ctx = current.parent
            return {
                "trace_id": format_trace_id(ctx.trace_id),
                "span_id": format_span_id(ctx.span_id),
                "parent_span_id": format_span_id(parent_ctx.span_id) if parent_ctx else parent_span_id,
            }
    except Exception:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
        }

def langfuse_link_status(trace_id: str | None) -> dict[str, Any]:
    enabled = _is_truthy(os.environ.get("FITCV_LANGFUSE_ENABLED"))
    if not enabled:
        return {
            "status": "disabled",
            "degradation_reason": "langfuse_disabled",
            "trace_url": None,
        }
    base_url = _normalized_env(os.environ.get("FITCV_LANGFUSE_BASE_URL"))
    if not base_url:
        return {
            "status": "degraded",
            "degradation_reason": "langfuse_base_url_missing",
            "trace_url": None,
        }
    normalized_trace_id = _normalized_env(trace_id)
    if not normalized_trace_id:
        return {
            "status": "degraded",
            "degradation_reason": "langfuse_trace_id_missing",
            "trace_url": None,
        }
    return {
        "status": "linked",
        "degradation_reason": None,
        "trace_url": f"{base_url.rstrip('/')}/trace/{normalized_trace_id}",
    }


def telemetry_export_status() -> dict[str, Any]:
    setup = setup_telemetry_runtime()
    if bool(setup.get("enabled")):
        return {"status": "export_enabled", "degradation_reason": None}
    degraded_reason = str(setup.get("degraded_reason") or "otel_disabled")
    if degraded_reason == "otel_disabled":
        return {"status": "disabled", "degradation_reason": degraded_reason}
    return {
        "status": "degraded",
        "degradation_reason": degraded_reason,
    }
