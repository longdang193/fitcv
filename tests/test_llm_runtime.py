"""
@meta
type: test
scope: unit
domain: llm_runtime
covers:
  - shared LLM request, adapter, parser, validator, failure, and provenance contracts
  - OpenAI-compatible structured transport symmetry
excludes:
  - live provider calls
  - stage-owned semantic repair and review
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from fitcv.llm_runtime import (
    LlmAdapterError,
    LlmAdapterResponse,
    LlmTaskRequest,
    LlmValidationResult,
    execute_llm_task,
    project_llm_runtime_evidence,
)
from fitcv.runtime_routing import LlmRouting


def _route(*, wire_api: str = "responses") -> LlmRouting:
    return LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api=wire_api,
        model="cx/test-model",
        timeout_seconds=12.0,
    )


def _response(raw_text: str = '{"value": 7}') -> LlmAdapterResponse:
    return LlmAdapterResponse(
        adapter="fake",
        runtime_path="fitcv_llm_fake",
        raw_text=raw_text,
        provider_payload={"output_text": raw_text},
        response_id="resp-1",
        trace_id="trace-1",
        attempt_count=1,
        telemetry={"usage": {"total_tokens": 3}},
    )


def _request() -> LlmTaskRequest:
    return LlmTaskRequest(
        routing_part="cv_generation_structured_write",
        prompt="Generate one document.",
        response_mode="json_schema",
        instructions="Return JSON only.",
        schema_name="fitcv_structured_cv_document",
        schema={"type": "object", "additionalProperties": False},
    )


def _run(
    *,
    adapter: Any,
    parser: Any = lambda response: json.loads(response.raw_text),
    validator: Any = lambda value: LlmValidationResult(valid=True, errors=[], details={}),
):
    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=_route()),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        return execute_llm_task(
            _request(),
            parser=parser,
            validator=validator,
            adapter=adapter,
        )


def test_execute_llm_task_runs_one_uniform_success_flow() -> None:
    """@proves cv_system.config-owned-generation-contract"""
    events: list[str] = []

    def adapter(request: LlmTaskRequest, route: LlmRouting, api_key: str) -> LlmAdapterResponse:
        events.append("adapter")
        assert request == _request()
        assert route == _route()
        assert api_key == "secret"
        return _response()

    def parser(response: LlmAdapterResponse) -> dict[str, int]:
        events.append("parser")
        return json.loads(response.raw_text)

    def validator(value: dict[str, int]) -> LlmValidationResult:
        events.append("validator")
        assert value == {"value": 7}
        return LlmValidationResult(valid=True, errors=[], details={"checked": True})

    result = _run(adapter=adapter, parser=parser, validator=validator)

    assert events == ["adapter", "parser", "validator"]
    assert result.status == "succeeded"
    assert result.parsed_value == {"value": 7}
    assert result.validation == LlmValidationResult(valid=True, errors=[], details={"checked": True})
    assert result.failure is None
    assert result.provenance.adapter == "fake"
    assert result.provenance.runtime_path == "fitcv_llm_fake"
    assert result.provenance.provider == "openai_compatible"
    assert result.provenance.model == "cx/test-model"
    assert result.provenance.wire_api == "responses"
    assert result.provenance.response_id == "resp-1"
    assert result.provenance.trace_id == "trace-1"
    assert not hasattr(result.provenance, "base_url")
    assert "secret" not in repr(result)


@pytest.mark.parametrize(
    ("task_request", "message"),
    [
        (LlmTaskRequest("", "prompt", "text"), "routing_part"),
        (LlmTaskRequest("part", "", "text"), "prompt"),
        (LlmTaskRequest("part", "prompt", "invalid"), "response_mode"),
        (LlmTaskRequest("part", "prompt", "json_schema"), "schema_name"),
        (LlmTaskRequest("part", "prompt", "text", schema_name="x", schema={}), "schema"),
    ],
)
def test_execute_llm_task_rejects_invalid_programmer_contracts(
    task_request: LlmTaskRequest,
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        execute_llm_task(
            task_request,
            parser=lambda response: response.raw_text,
            validator=lambda value: LlmValidationResult(valid=True, errors=[], details={}),
            adapter=lambda request, route, api_key: _response(),
        )


def test_execute_llm_task_preserves_invalid_value_and_validation() -> None:
    validation = LlmValidationResult(valid=False, errors=["bad"], details={"rule": "x"})
    result = _run(adapter=lambda request, route, api_key: _response(), validator=lambda value: validation)

    assert result.status == "failed"
    assert result.parsed_value == {"value": 7}
    assert result.validation == validation
    assert result.failure is not None
    assert result.failure.stage == "validate"
    assert result.failure.code == "validation_error"


def test_execute_llm_task_normalizes_parser_and_validator_exceptions() -> None:
    parse_result = _run(
        adapter=lambda request, route, api_key: _response(),
        parser=lambda response: (_ for _ in ()).throw(ValueError("bad json")),
    )
    assert parse_result.status == "failed"
    assert parse_result.parsed_value is None
    assert parse_result.validation is None
    assert parse_result.failure is not None
    assert parse_result.failure.code == "parse_error"

    validate_result = _run(
        adapter=lambda request, route, api_key: _response(),
        validator=lambda value: (_ for _ in ()).throw(RuntimeError("bad validation")),
    )
    assert validate_result.status == "failed"
    assert validate_result.parsed_value == {"value": 7}
    assert validate_result.validation is None
    assert validate_result.failure is not None
    assert validate_result.failure.code == "validation_error"


@pytest.mark.parametrize(
    ("error", "code", "retryable", "http_status"),
    [
        (LlmAdapterError("adapter_timeout", "timeout", True), "adapter_timeout", True, None),
        (
            LlmAdapterError("adapter_transport_error", "network", True),
            "adapter_transport_error",
            True,
            None,
        ),
        (
            LlmAdapterError("adapter_http_error", "rate limited", True, 429),
            "adapter_http_error",
            True,
            429,
        ),
    ],
)
def test_execute_llm_task_preserves_adapter_failures(
    error: LlmAdapterError,
    code: str,
    retryable: bool,
    http_status: int | None,
) -> None:
    def adapter(request: LlmTaskRequest, route: LlmRouting, api_key: str) -> LlmAdapterResponse:
        raise error

    result = _run(adapter=adapter)

    assert result.status == "failed"
    assert result.failure is not None
    assert result.failure.stage == "adapter"
    assert result.failure.code == code
    assert result.failure.retryable is retryable
    assert result.failure.http_status == http_status


def test_execute_llm_task_normalizes_unknown_and_malformed_adapter_results() -> None:
    unknown = _run(
        adapter=lambda request, route, api_key: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert unknown.failure is not None
    assert unknown.failure.code == "adapter_contract_error"

    malformed = _run(adapter=lambda request, route, api_key: {"raw_text": "not-contract"})
    assert malformed.failure is not None
    assert malformed.failure.code == "adapter_contract_error"


class _HttpResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json", "x-request-id": "trace-http"}

    def json(self) -> dict[str, Any]:
        return dict(self._payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("POST", "https://provider.example/v1/responses")
            raise httpx.HTTPStatusError("http error", request=request, response=httpx.Response(self.status_code, request=request))


class _HttpClient:
    def __init__(self, responses: list[_HttpResponse], calls: list[dict[str, Any]]) -> None:
        self._responses = responses
        self._calls = calls

    def __enter__(self) -> _HttpClient:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> _HttpResponse:
        self._calls.append({"url": url, "headers": headers, "json": json})
        return self._responses.pop(0)


def test_default_adapter_preserves_json_schema_on_responses_404_fallback() -> None:
    calls: list[dict[str, Any]] = []
    responses = [
        _HttpResponse(404, {"error": "missing"}),
        _HttpResponse(
            200,
            {
                "id": "resp-chat",
                "choices": [{"message": {"content": '{"value": 7}'}}],
                "usage": {"total_tokens": 9},
            },
        ),
    ]

    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=_route()),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
        patch("httpx.Client", return_value=_HttpClient(responses, calls)),
    ):
        result = execute_llm_task(
            _request(),
            parser=lambda response: json.loads(response.raw_text),
            validator=lambda value: LlmValidationResult(valid=True, errors=[], details={}),
        )

    assert result.status == "succeeded"
    assert len(calls) == 2
    assert calls[0]["url"].endswith("/responses")
    assert calls[0]["json"]["text"]["format"] == {
        "type": "json_schema",
        "name": "fitcv_structured_cv_document",
        "schema": {"type": "object", "additionalProperties": False},
        "strict": True,
    }
    assert calls[1]["url"].endswith("/chat/completions")
    assert calls[1]["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "fitcv_structured_cv_document",
            "schema": {"type": "object", "additionalProperties": False},
            "strict": True,
        },
    }
    assert result.adapter_response is not None
    assert result.adapter_response.attempt_count == 2
    assert result.adapter_response.response_id == "resp-chat"
    assert result.adapter_response.telemetry["usage"] == {"total_tokens": 9}

def test_execute_llm_task_passes_empty_adapter_text_to_parser() -> None:
    seen: list[str] = []

    result = _run(
        adapter=lambda request, route, api_key: _response(""),
        parser=lambda response: seen.append(response.raw_text) or {"empty": True},
    )

    assert seen == [""]
    assert result.status == "succeeded"
    assert result.parsed_value == {"empty": True}


def test_default_adapter_passes_empty_json_object_text_to_parser() -> None:
    calls: list[dict[str, Any]] = []
    responses = [_HttpResponse(200, {"id": "resp-empty", "output_text": ""})]
    request = LlmTaskRequest(
        routing_part="enrich_extraction",
        prompt="Extract one job.",
        response_mode="json_object",
    )
    seen: list[str] = []

    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=_route()),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
        patch("httpx.Client", return_value=_HttpClient(responses, calls)),
    ):
        result = execute_llm_task(
            request,
            parser=lambda response: seen.append(response.raw_text) or {"empty": True},
            validator=lambda value: LlmValidationResult(valid=True, errors=[], details={}),
        )

    assert seen == [""]
    assert result.status == "succeeded"
    assert calls[0]["json"]["text"]["format"] == {"type": "json_object"}


def test_project_llm_runtime_evidence_serializes_only_canonical_safe_fields() -> None:
    success = _run(
        adapter=lambda request, route, api_key: LlmAdapterResponse(
            adapter="fake",
            runtime_path="fitcv_llm_fake",
            raw_text='{"value": 7}',
            provider_payload={
                "model": "gpt-5.4-2026-01-01",
                "reasoning": {"effort": "high"},
            },
            response_id="resp-1",
            telemetry={
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                "cost": {"total_cost": 0.03},
            },
        )
    )
    evidence = project_llm_runtime_evidence(success)

    assert evidence["contract_version"] == "llm_runtime_evidence_v1"
    assert evidence["status"] == "succeeded"
    assert evidence["failure"] is None
    assert evidence["provenance"]["routing_part"] == "cv_generation_structured_write"
    assert evidence["provenance"]["model"] == "cx/test-model"
    assert evidence["provenance"]["response_id"] == "resp-1"
    assert evidence["telemetry"] == {
        "provider_reported_model": "gpt-5.4-2026-01-01",
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "cost": {"total_cost": 0.03},
        "reasoning": {"effort": "high"},
    }
    assert "route_part" not in evidence["provenance"]
    serialized = json.dumps(evidence, sort_keys=True)
    assert "secret" not in serialized
    assert "provider_payload" not in serialized
    assert "raw_text" not in serialized

    failure = _run(
        adapter=lambda request, route, api_key: (_ for _ in ()).throw(
            LlmAdapterError("adapter_http_error", "rate limited", True, 429)
        )
    )
    failed_evidence = project_llm_runtime_evidence(failure)
    assert failed_evidence["status"] == "failed"
    assert failed_evidence["failure"] == {
        "stage": "adapter",
        "code": "adapter_http_error",
        "message": "rate limited",
        "retryable": True,
        "http_status": 429,
    }


def test_execute_llm_task_uses_pre_resolved_route_without_reloading_config() -> None:
    route = _route(wire_api="chat_completions")
    seen: list[LlmRouting] = []

    def adapter(request: LlmTaskRequest, resolved_route: LlmRouting, api_key: str) -> LlmAdapterResponse:
        assert request == _request()
        assert api_key == "secret"
        seen.append(resolved_route)
        return _response()

    with (
        patch("fitcv.llm_runtime.resolve_llm_routing") as mock_resolve,
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        result = execute_llm_task(
            _request(),
            parser=lambda response: json.loads(response.raw_text),
            validator=lambda value: LlmValidationResult(valid=True, errors=[], details={}),
            adapter=adapter,
            resolved_route=route,
        )

    mock_resolve.assert_not_called()
    assert seen == [route]
    assert result.status == "succeeded"
    assert result.provenance.provider == route.provider
    assert result.provenance.model == route.model
    assert result.provenance.wire_api == route.wire_api
