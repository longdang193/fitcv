"""
Minimal OpenTelemetry runtime helpers with safe fallback behavior.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import threading
from collections.abc import Iterator, Mapping
from typing import Any

_INIT_LOCK = threading.Lock()
_INITIALIZED = False
_DEGRADED_REASON: str | None = None
_OTEL_ENABLED = False
_LANGFUSE_JSON_MAX_CHARS = 4000
_LANGFUSE_COLLECTION_MAX_ITEMS = 25
_LANGFUSE_MAPPING_MAX_ITEMS = 50


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


def _parse_otlp_headers(value: str | None) -> dict[str, str]:
    raw = _normalized_env(value)
    if not raw:
        return {}
    headers: dict[str, str] = {}
    for part in raw.split(","):
        segment = part.strip()
        if not segment or "=" not in segment:
            continue
        key, val = segment.split("=", 1)
        key_clean = key.strip()
        val_clean = val.strip()
        if key_clean and val_clean:
            headers[key_clean] = val_clean
    return headers


def _truncate_langfuse_text(value: str, *, max_chars: int = _LANGFUSE_JSON_MAX_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    suffix = "... [truncated]"
    if max_chars <= len(suffix):
        return value[:max_chars]
    return f"{value[: max_chars - len(suffix)]}{suffix}"


def _bounded_langfuse_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate_langfuse_text(value)
    if isinstance(value, Mapping):
        bounded_items = list(value.items())[:_LANGFUSE_MAPPING_MAX_ITEMS]
        return {
            str(key): _bounded_langfuse_value(item_value)
            for key, item_value in bounded_items
            if item_value is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [
            _bounded_langfuse_value(item)
            for item in list(value)[:_LANGFUSE_COLLECTION_MAX_ITEMS]
        ]
    return _truncate_langfuse_text(str(value))


def serialize_langfuse_json(value: Any, *, max_chars: int = _LANGFUSE_JSON_MAX_CHARS) -> str | None:
    if value is None:
        return None
    try:
        serialized = json.dumps(
            _bounded_langfuse_value(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        serialized = json.dumps({"value": _truncate_langfuse_text(str(value), max_chars=max_chars)})
    return _truncate_langfuse_text(serialized, max_chars=max_chars)


def build_langfuse_trace_attributes(
    *,
    trace_name: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    input_payload: Any = None,
    output_payload: Any = None,
    metadata: Mapping[str, Any] | None = None,
    extra_attributes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return _normalized_attributes(
        {
            "langfuse.trace.name": trace_name,
            "langfuse.session.id": session_id,
            "langfuse.user.id": user_id,
            "langfuse.trace.input": serialize_langfuse_json(input_payload),
            "langfuse.trace.output": serialize_langfuse_json(output_payload),
            "langfuse.trace.metadata": serialize_langfuse_json(metadata),
            **dict(extra_attributes or {}),
        }
    )


def build_langfuse_observation_attributes(
    *,
    observation_type: str | None = None,
    input_payload: Any = None,
    output_payload: Any = None,
    metadata: Mapping[str, Any] | None = None,
    model: str | None = None,
    model_parameters: Mapping[str, Any] | None = None,
    usage_details: Mapping[str, Any] | None = None,
    cost_details: Mapping[str, Any] | None = None,
    prompt_name: str | None = None,
    extra_attributes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return _normalized_attributes(
        {
            "langfuse.observation.type": observation_type,
            "langfuse.observation.input": serialize_langfuse_json(input_payload),
            "langfuse.observation.output": serialize_langfuse_json(output_payload),
            "langfuse.observation.metadata": serialize_langfuse_json(metadata),
            "langfuse.observation.model": model,
            "langfuse.observation.model_parameters": serialize_langfuse_json(model_parameters),
            "langfuse.observation.usage_details": serialize_langfuse_json(usage_details),
            "langfuse.observation.cost_details": serialize_langfuse_json(cost_details),
            "langfuse.observation.prompt_name": prompt_name,
            **dict(extra_attributes or {}),
        }
    )


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
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
        except Exception:
            _DEGRADED_REASON = "otel_dependency_missing"
            _OTEL_ENABLED = False
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}

        endpoint = str(os.environ.get("FITCV_OTEL_EXPORTER_OTLP_ENDPOINT", "") or "").strip()
        if not endpoint:
            _DEGRADED_REASON = "otel_exporter_endpoint_missing"
            _OTEL_ENABLED = False
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}

        try:
            service_name = str(os.environ.get("FITCV_OTEL_SERVICE_NAME", "fitcv-control-plane") or "fitcv-control-plane")
            provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
            exporter_headers = _parse_otlp_headers(os.environ.get("FITCV_OTEL_EXPORTER_OTLP_HEADERS"))
            exporter = OTLPSpanExporter(endpoint=endpoint, headers=exporter_headers or None)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            _OTEL_ENABLED = True
            _DEGRADED_REASON = None
            return {"enabled": True, "degraded_reason": None}
        except Exception:
            _DEGRADED_REASON = "otel_exporter_init_failed"
            _OTEL_ENABLED = False
            return {"enabled": False, "degraded_reason": _DEGRADED_REASON}


def _normalized_attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in dict(attributes or {}).items():
        if value is None:
            continue
        normalized[str(key)] = value
    return normalized


def _fallback_trace_context(seed: str, *, parent_seed: str | None = None) -> dict[str, str]:
    trace_id = _otel_id(seed, length=32)
    span_id = _otel_id(f"{seed}:span", length=16)
    parent_source = parent_seed or f"{seed}:parent"
    parent_span_id = _otel_id(parent_source, length=16)
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
    }


def current_trace_context() -> dict[str, str] | None:
    setup_telemetry_runtime()
    if not _OTEL_ENABLED:
        return None
    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.trace.span import format_span_id, format_trace_id  # type: ignore

        current = trace.get_current_span()
        span_context = current.get_span_context()
        if not getattr(span_context, "is_valid", False):
            return None
        parent_ctx = getattr(current, "parent", None)
        parent_span_id = None
        if parent_ctx is not None:
            parent_span_id = format_span_id(parent_ctx.span_id)
        return {
            "trace_id": format_trace_id(span_context.trace_id),
            "span_id": format_span_id(span_context.span_id),
            "parent_span_id": parent_span_id or "0" * 16,
        }
    except Exception:
        return None


@contextlib.contextmanager
def observe_span(name: str, *, attributes: Mapping[str, Any] | None = None) -> Iterator[dict[str, str] | None]:
    setup_telemetry_runtime()
    normalized_attributes = _normalized_attributes(attributes)
    if not _OTEL_ENABLED:
        yield None
        return
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer("fitcv.telemetry")
        with tracer.start_as_current_span(name) as span:
            for key, value in normalized_attributes.items():
                span.set_attribute(key, value)
            yield current_trace_context()
            return
    except Exception:
        yield None


def set_span_attributes(attributes: Mapping[str, Any] | None) -> None:
    normalized_attributes = _normalized_attributes(attributes)
    if not normalized_attributes:
        return
    setup_telemetry_runtime()
    if not _OTEL_ENABLED:
        return
    try:
        from opentelemetry import trace  # type: ignore

        current = trace.get_current_span()
        for key, value in normalized_attributes.items():
            current.set_attribute(key, value)
    except Exception:
        return


def build_trace_context(
    seed: str,
    *,
    parent_seed: str | None = None,
    emit_otel_span: bool = True,
) -> dict[str, str]:
    setup_telemetry_runtime()
    active_context = current_trace_context()
    if active_context is not None:
        return active_context
    fallback_context = _fallback_trace_context(seed, parent_seed=parent_seed)

    if not _OTEL_ENABLED or not emit_otel_span:
        return fallback_context

    try:
        with observe_span(seed) as trace_context:
            return trace_context or fallback_context
    except Exception:
        return fallback_context


def langfuse_link_status(trace_id: str | None, *, verified: bool = False) -> dict[str, Any]:
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
    if verified:
        return {
            "status": "verified",
            "degradation_reason": None,
            "trace_url": f"{base_url.rstrip('/')}/trace/{normalized_trace_id}",
        }
    return {
        "status": "unverified",
        "degradation_reason": "langfuse_ingestion_unverified",
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
