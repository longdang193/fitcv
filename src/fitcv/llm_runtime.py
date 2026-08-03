"""@meta
name: llm_runtime
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.config-owned-generation-contract
responsibility:
  - Execute routed LLM adapter calls through one stage-neutral contract.
  - Normalize operational failures and provenance without owning stage meaning.
inputs:
  - rendered prompts, response contracts, parser/validator callables, routed credentials
outputs:
  - normalized runtime results, failures, provenance, and adapter telemetry
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import threading
import time
from typing import Any, Callable, Literal, TypeAlias

from fitcv.config import SUPPORTED_PROVIDER_IDS
from fitcv.openai_compat import (
    decode_openai_compat_response_body,
    extract_openai_chat_completions_text,
    extract_openai_responses_text,
)
from fitcv.runtime_routing import (
    LlmRouting,
    resolve_llm_api_key,
    resolve_llm_routing,
    validate_llm_routing_ready,
)

ResponseMode: TypeAlias = Literal["text", "json_object", "json_schema"]
RuntimeStatus: TypeAlias = Literal["succeeded", "failed"]
FailureStage: TypeAlias = Literal["routing", "adapter", "parse", "validate"]

_REQUEST_START_LOCK = threading.Lock()
_NEXT_REQUEST_START_BY_PROVIDER: dict[str, float] = {}
_REQUEST_START_MONOTONIC = time.monotonic
_REQUEST_START_SLEEP = time.sleep


@dataclass(frozen=True)
class LlmTaskRequest:
    routing_part: str
    prompt: str
    response_mode: ResponseMode | str
    instructions: str | None = None
    schema_name: str | None = None
    schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class LlmAdapterResponse:
    adapter: str
    runtime_path: str
    raw_text: str
    provider_payload: dict[str, Any] | None = None
    response_id: str | None = None
    trace_id: str | None = None
    attempt_count: int = 1
    telemetry: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LlmValidationResult:
    valid: bool
    errors: list[str]
    details: dict[str, Any]


@dataclass(frozen=True)
class LlmRuntimeFailure:
    stage: FailureStage
    code: str
    message: str
    retryable: bool = False
    http_status: int | None = None


@dataclass(frozen=True)
class LlmRuntimeProvenance:
    routing_part: str
    runtime_path: str
    adapter: str
    provider: str
    model: str
    wire_api: str
    attempt_count: int
    response_id: str | None
    trace_id: str | None
    latency_ms: int
    model_record_id: str | None = None
    configuration_revision: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class LlmRuntimeResult:
    status: RuntimeStatus
    parsed_value: Any | None
    validation: LlmValidationResult | None
    failure: LlmRuntimeFailure | None
    provenance: LlmRuntimeProvenance
    adapter_response: LlmAdapterResponse | None


def parse_llm_json_object(response: LlmAdapterResponse) -> dict[str, Any]:
    value = json.loads(response.raw_text)
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def project_llm_runtime_evidence(result: LlmRuntimeResult) -> dict[str, Any]:
    provenance = result.provenance
    failure = result.failure
    evidence: dict[str, Any] = {
        "contract_version": "llm_runtime_evidence_v1",
        "status": result.status,
        "provenance": {
            "routing_part": provenance.routing_part,
            "runtime_path": provenance.runtime_path,
            "adapter": provenance.adapter,
            "provider": provenance.provider,
            "model": provenance.model,
            "wire_api": provenance.wire_api,
            "attempt_count": provenance.attempt_count,
            "response_id": provenance.response_id,
            "trace_id": provenance.trace_id,
            "latency_ms": provenance.latency_ms,
            "model_record_id": provenance.model_record_id,
            "configuration_revision": provenance.configuration_revision,
            "temperature": provenance.temperature,
        },
        "failure": (
            {
                "stage": failure.stage,
                "code": failure.code,
                "message": failure.message,
                "retryable": failure.retryable,
                "http_status": failure.http_status,
            }
            if failure is not None
            else None
        ),
    }
    adapter_response = result.adapter_response
    if adapter_response is not None:
        provider_payload = adapter_response.provider_payload or {}
        telemetry = {
            key: dict(value)
            for key, value in adapter_response.telemetry.items()
            if key in {"usage", "cost"} and isinstance(value, dict) and value
        }
        provider_model = str(provider_payload.get("model") or "").strip()
        if provider_model:
            telemetry["provider_reported_model"] = provider_model
        reasoning = provider_payload.get("reasoning")
        if isinstance(reasoning, dict) and reasoning:
            telemetry["reasoning"] = dict(reasoning)
        if telemetry:
            evidence["telemetry"] = telemetry
    return evidence

class LlmAdapterError(RuntimeError):
    def __init__(
        self,
        code: Literal["adapter_timeout", "adapter_transport_error", "adapter_http_error"],
        message: str,
        retryable: bool = False,
        http_status: int | None = None,
        *,
        adapter: str | None = None,
        runtime_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.http_status = http_status
        self.adapter = adapter
        self.runtime_path = runtime_path

def _wait_for_provider_request_start(route: LlmRouting) -> None:
    interval = route.request_start_interval_secs
    if interval <= 0.0:
        return
    provider = route.provider.strip().lower()
    with _REQUEST_START_LOCK:
        now = _REQUEST_START_MONOTONIC()
        reserved_start = max(now, _NEXT_REQUEST_START_BY_PROVIDER.get(provider, now))
        _NEXT_REQUEST_START_BY_PROVIDER[provider] = reserved_start + interval
    wait_seconds = reserved_start - now
    if wait_seconds > 0.0:
        _REQUEST_START_SLEEP(wait_seconds)


LlmAdapter: TypeAlias = Callable[[LlmTaskRequest, LlmRouting, str], LlmAdapterResponse]
LlmParser: TypeAlias = Callable[[LlmAdapterResponse], Any]
LlmValidator: TypeAlias = Callable[[Any], LlmValidationResult]


def _validate_request(request: LlmTaskRequest) -> None:
    if not isinstance(request, LlmTaskRequest):
        raise TypeError("request must be LlmTaskRequest")
    if not str(request.routing_part or "").strip():
        raise ValueError("routing_part must be non-empty")
    if not str(request.prompt or "").strip():
        raise ValueError("prompt must be non-empty")
    if request.response_mode not in {"text", "json_object", "json_schema"}:
        raise ValueError("response_mode must be text, json_object, or json_schema")
    if request.response_mode == "json_schema":
        if not str(request.schema_name or "").strip():
            raise ValueError("schema_name is required for json_schema")
        if not isinstance(request.schema, dict) or not request.schema:
            raise ValueError("schema is required for json_schema")
    elif request.schema_name is not None or request.schema is not None:
        raise ValueError("schema fields are only valid for json_schema")


def _provenance(
    request: LlmTaskRequest,
    *,
    route: LlmRouting | None,
    response: LlmAdapterResponse | None,
    latency_ms: int,
    adapter: str = "",
    runtime_path: str = "",
) -> LlmRuntimeProvenance:
    return LlmRuntimeProvenance(
        routing_part=request.routing_part,
        runtime_path=(response.runtime_path if response else runtime_path),
        adapter=(response.adapter if response else adapter),
        provider=(route.provider if route else ""),
        model=(route.model if route else ""),
        wire_api=(route.wire_api if route else ""),
        attempt_count=(response.attempt_count if response else 0),
        response_id=(response.response_id if response else None),
        trace_id=(response.trace_id if response else None),
        latency_ms=latency_ms,
        model_record_id=(route.model_record_id if route else None),
        configuration_revision=(route.configuration_revision if route else None),
        temperature=(route.temperature if route else None),
    )


def _failed(
    request: LlmTaskRequest,
    *,
    route: LlmRouting | None,
    response: LlmAdapterResponse | None,
    failure: LlmRuntimeFailure,
    started: float,
    parsed_value: Any | None = None,
    validation: LlmValidationResult | None = None,
    adapter: str = "",
    runtime_path: str = "",
) -> LlmRuntimeResult:
    return LlmRuntimeResult(
        status="failed",
        parsed_value=parsed_value,
        validation=validation,
        failure=failure,
        provenance=_provenance(
            request,
            route=route,
            response=response,
            latency_ms=int((time.monotonic() - started) * 1000),
            adapter=adapter,
            runtime_path=runtime_path,
        ),
        adapter_response=response,
    )


def execute_llm_task(
    request: LlmTaskRequest,
    *,
    parser: LlmParser,
    validator: LlmValidator,
    adapter: LlmAdapter | None = None,
    resolved_route: LlmRouting | None = None,
) -> LlmRuntimeResult:
    _validate_request(request)
    started = time.monotonic()
    route = resolved_route
    try:
        if route is None:
            route = resolve_llm_routing(request.routing_part)
        api_key = resolve_llm_api_key(route)
        validate_llm_routing_ready(route, api_key=api_key)
    except Exception as exc:
        code = "credentials_missing" if "API key" in str(exc) else "routing_invalid"
        return _failed(
            request,
            route=route,
            response=None,
            failure=LlmRuntimeFailure(stage="routing", code=code, message=str(exc)),
            started=started,
        )

    selected_adapter = adapter or (
        _anthropic_messages_adapter
        if route.wire_api == "messages"
        else _openai_compatible_adapter
    )
    default_adapter = adapter is None
    adapter_name = (
        "anthropic_messages"
        if default_adapter and route.wire_api == "messages"
        else "openai_compatible" if default_adapter else "custom"
    )
    runtime_path = (
        "fitcv_llm_anthropic_messages"
        if default_adapter and route.wire_api == "messages"
        else "fitcv_llm_openai_compatible" if default_adapter else "fitcv_llm_custom"
    )
    try:
        _wait_for_provider_request_start(route)
        response = selected_adapter(request, route, api_key)
    except LlmAdapterError as exc:
        return _failed(
            request,
            route=route,
            response=None,
            failure=LlmRuntimeFailure(
                stage="adapter",
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
                http_status=exc.http_status,
            ),
            started=started,
            adapter=exc.adapter or adapter_name,
            runtime_path=exc.runtime_path or runtime_path,
        )
    except Exception as exc:
        return _failed(
            request,
            route=route,
            response=None,
            failure=LlmRuntimeFailure(
                stage="adapter",
                code="adapter_contract_error",
                message=str(exc),
            ),
            started=started,
            adapter=adapter_name,
            runtime_path=runtime_path,
        )
    if not isinstance(response, LlmAdapterResponse):
        return _failed(
            request,
            route=route,
            response=(response if isinstance(response, LlmAdapterResponse) else None),
            failure=LlmRuntimeFailure(
                stage="adapter",
                code="adapter_contract_error",
                message="Adapter must return LlmAdapterResponse.",
            ),
            started=started,
            adapter=adapter_name,
            runtime_path=runtime_path,
        )

    try:
        parsed_value = parser(response)
    except Exception as exc:
        return _failed(
            request,
            route=route,
            response=response,
            failure=LlmRuntimeFailure(stage="parse", code="parse_error", message=str(exc)),
            started=started,
        )
    try:
        validation = validator(parsed_value)
    except Exception as exc:
        return _failed(
            request,
            route=route,
            response=response,
            failure=LlmRuntimeFailure(
                stage="validate",
                code="validation_error",
                message=str(exc),
            ),
            started=started,
            parsed_value=parsed_value,
        )
    if not isinstance(validation, LlmValidationResult):
        return _failed(
            request,
            route=route,
            response=response,
            failure=LlmRuntimeFailure(
                stage="validate",
                code="validation_error",
                message="Validator must return LlmValidationResult.",
            ),
            started=started,
            parsed_value=parsed_value,
        )
    if not validation.valid:
        return _failed(
            request,
            route=route,
            response=response,
            failure=LlmRuntimeFailure(
                stage="validate",
                code="validation_error",
                message="; ".join(validation.errors) or "Validation failed.",
            ),
            started=started,
            parsed_value=parsed_value,
            validation=validation,
        )
    return LlmRuntimeResult(
        status="succeeded",
        parsed_value=parsed_value,
        validation=validation,
        failure=None,
        provenance=_provenance(
            request,
            route=route,
            response=response,
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        adapter_response=response,
    )


def _response_format(request: LlmTaskRequest, *, responses_api: bool) -> dict[str, Any] | None:
    if request.response_mode == "text":
        return None
    if request.response_mode == "json_object":
        return {"type": "json_object"}
    schema_format = {
        "name": request.schema_name,
        "schema": request.schema,
        "strict": True,
    }
    if responses_api:
        return {"type": "json_schema", **schema_format}
    return {"type": "json_schema", "json_schema": schema_format}


def _openai_compatible_adapter(
    request: LlmTaskRequest,
    route: LlmRouting,
    api_key: str,
) -> LlmAdapterResponse:
    import httpx

    if route.provider not in SUPPORTED_PROVIDER_IDS and not str(
        __import__("os").environ.get("FITCV_LOCAL_MODE") or ""
    ).strip():
        raise ValueError(f"Unsupported default-adapter provider: {route.provider}.")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    attempts = 0
    try:
        with httpx.Client(timeout=route.timeout_seconds) as client:
            if route.wire_api == "responses":
                attempts += 1
                payload: dict[str, Any] = {"model": route.model, "input": request.prompt}
                if request.instructions:
                    payload["instructions"] = request.instructions
                response_format = _response_format(request, responses_api=True)
                if response_format is not None:
                    payload["text"] = {"format": response_format}
                response = client.post(
                    f"{route.base_url.rstrip('/')}/responses",
                    headers=headers,
                    json=payload,
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 404:
                        raise
                    attempts += 1
                    response = client.post(
                        f"{route.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=_chat_payload(request, route),
                    )
                    response.raise_for_status()
                    body = decode_openai_compat_response_body(response)
                    raw_text = extract_openai_chat_completions_text(body)
                else:
                    body = decode_openai_compat_response_body(response)
                    raw_text = extract_openai_responses_text(body)
            else:
                attempts += 1
                response = client.post(
                    f"{route.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=_chat_payload(request, route),
                )
                response.raise_for_status()
                body = decode_openai_compat_response_body(response)
                raw_text = extract_openai_chat_completions_text(body)
    except httpx.TimeoutException as exc:
        raise LlmAdapterError(
            "adapter_timeout",
            str(exc),
            True,
            adapter="openai_compatible",
            runtime_path="fitcv_llm_openai_compatible",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise LlmAdapterError(
            "adapter_http_error",
            str(exc),
            status in {408, 409, 425, 429, 500, 502, 503, 504},
            status,
            adapter="openai_compatible",
            runtime_path="fitcv_llm_openai_compatible",
        ) from exc
    except httpx.TransportError as exc:
        raise LlmAdapterError(
            "adapter_transport_error",
            str(exc),
            True,
            adapter="openai_compatible",
            runtime_path="fitcv_llm_openai_compatible",
        ) from exc
    telemetry = {
        key: body[key]
        for key in ("usage", "cost")
        if isinstance(body.get(key), dict)
    }
    return LlmAdapterResponse(
        adapter="openai_compatible",
        runtime_path="fitcv_llm_openai_compatible",
        raw_text=raw_text,
        provider_payload=body,
        response_id=str(body.get("id") or body.get("response_id") or "").strip() or None,
        trace_id=str((getattr(response, "headers", {}) or {}).get("x-request-id") or "").strip() or None,
        attempt_count=attempts,
        telemetry=telemetry,
    )


def _chat_payload(request: LlmTaskRequest, route: LlmRouting) -> dict[str, Any]:
    messages = []
    if request.instructions:
        messages.append({"role": "system", "content": request.instructions})
    messages.append({"role": "user", "content": request.prompt})
    payload: dict[str, Any] = {
        "model": route.model,
        "messages": messages,
        "temperature": route.temperature,
    }
    response_format = _response_format(request, responses_api=False)
    if response_format is not None:
        payload["response_format"] = response_format
    return payload


def _anthropic_messages_adapter(
    request: LlmTaskRequest,
    route: LlmRouting,
    api_key: str,
) -> LlmAdapterResponse:
    import httpx

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload: dict[str, Any] = {
        "model": route.model,
        "max_tokens": 4096,
        "temperature": route.temperature,
        "messages": [{"role": "user", "content": request.prompt}],
    }
    if request.instructions:
        payload["system"] = request.instructions
    try:
        with httpx.Client(timeout=route.timeout_seconds) as client:
            response = client.post(
                f"{route.base_url.rstrip('/')}/v1/messages"
                if not route.base_url.rstrip("/").endswith("/v1")
                else f"{route.base_url.rstrip('/')}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        raw_text = "".join(
            str(item.get("text") or "")
            for item in body.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        )
    except httpx.TimeoutException as exc:
        raise LlmAdapterError("adapter_timeout", str(exc), True, adapter="anthropic_messages", runtime_path="fitcv_llm_anthropic_messages") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise LlmAdapterError("adapter_http_error", str(exc), status in {408, 409, 425, 429, 500, 502, 503, 504}, status, adapter="anthropic_messages", runtime_path="fitcv_llm_anthropic_messages") from exc
    except httpx.TransportError as exc:
        raise LlmAdapterError("adapter_transport_error", str(exc), True, adapter="anthropic_messages", runtime_path="fitcv_llm_anthropic_messages") from exc
    return LlmAdapterResponse(
        adapter="anthropic_messages",
        runtime_path="fitcv_llm_anthropic_messages",
        raw_text=raw_text,
        provider_payload=body,
        response_id=str(body.get("id") or "").strip() or None,
        trace_id=str((getattr(response, "headers", {}) or {}).get("request-id") or "").strip() or None,
    )
