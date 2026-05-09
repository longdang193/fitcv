"""
@meta
type: test
scope: unit
domain: observability
covers:
  - OTel runtime degradation and config behavior
  - bounded Langfuse JSON serialization helpers
excludes:
  - live collector connectivity
tags:
  - fast
  - ci-safe
"""

import json

from fitcv import telemetry


def test_telemetry_disabled_by_default_reports_disabled() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    status = telemetry.telemetry_export_status()
    assert status["status"] == "disabled"
    assert status["degradation_reason"] == "otel_disabled"


def test_telemetry_enabled_without_endpoint_reports_endpoint_missing(monkeypatch) -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    monkeypatch.setenv("FITCV_OTEL_ENABLED", "true")
    monkeypatch.delenv("FITCV_OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    status = telemetry.telemetry_export_status()
    assert status["status"] == "degraded"
    assert status["degradation_reason"] in {"otel_dependency_missing", "otel_exporter_endpoint_missing"}



def test_telemetry_does_not_report_enabled_after_failed_init(monkeypatch) -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    monkeypatch.setenv("FITCV_OTEL_ENABLED", "true")
    monkeypatch.setenv("FITCV_OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:3000/api/public/otel/v1/traces")
    monkeypatch.setattr(telemetry, "_parse_otlp_headers", lambda _value: "bad")
    first = telemetry.telemetry_export_status()
    second = telemetry.telemetry_export_status()
    assert first["status"] == "degraded"
    assert second["status"] == "degraded"


def test_trace_context_always_has_otel_compatible_ids() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    trace_context = telemetry.build_trace_context("seed-value")
    assert len(str(trace_context["trace_id"])) == 32
    assert len(str(trace_context["span_id"])) == 16
    assert len(str(trace_context["parent_span_id"])) == 16


def test_current_trace_context_is_none_when_telemetry_disabled() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    assert telemetry.current_trace_context() is None


def test_observe_span_yields_none_when_telemetry_disabled() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    with telemetry.observe_span("pipeline.test", attributes={"run_id": "r1"}) as trace_context:
        assert trace_context is None
        assert telemetry.current_trace_context() is None


def test_langfuse_link_status_disabled_by_default() -> None:
    status = telemetry.langfuse_link_status("abc123")
    assert status["status"] == "disabled"
    assert status["degradation_reason"] == "langfuse_disabled"
    assert status["trace_url"] is None


def test_langfuse_link_status_degraded_when_enabled_without_base_url(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_LANGFUSE_ENABLED", "true")
    monkeypatch.delenv("FITCV_LANGFUSE_BASE_URL", raising=False)
    status = telemetry.langfuse_link_status("abc123")
    assert status["status"] == "degraded"
    assert status["degradation_reason"] == "langfuse_base_url_missing"
    assert status["trace_url"] is None


def test_langfuse_link_status_returns_trace_url_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("FITCV_LANGFUSE_BASE_URL", "http://localhost:3000")
    status = telemetry.langfuse_link_status("trace-123")
    assert status["status"] == "unverified"
    assert status["degradation_reason"] == "langfuse_ingestion_unverified"
    assert status["trace_url"] == "http://localhost:3000/trace/trace-123"


def test_langfuse_link_status_returns_verified_when_ingestion_confirmed(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("FITCV_LANGFUSE_BASE_URL", "http://localhost:3000")
    status = telemetry.langfuse_link_status("trace-123", verified=True)
    assert status["status"] == "verified"
    assert status["degradation_reason"] is None
    assert status["trace_url"] == "http://localhost:3000/trace/trace-123"


def test_serialize_langfuse_json_returns_none_for_none() -> None:
    assert telemetry.serialize_langfuse_json(None) is None


def test_serialize_langfuse_json_bounds_collections_and_mappings() -> None:
    payload = {"items": list(range(40))}
    payload.update(
        {
            f"k{idx}": idx
            for idx in range(60)
        }
    )

    serialized = telemetry.serialize_langfuse_json(payload)

    assert serialized is not None
    parsed = json.loads(serialized)
    assert len(parsed) == telemetry._LANGFUSE_MAPPING_MAX_ITEMS
    assert len(parsed["items"]) == telemetry._LANGFUSE_COLLECTION_MAX_ITEMS
    assert parsed["items"][-1] == telemetry._LANGFUSE_COLLECTION_MAX_ITEMS - 1


def test_serialize_langfuse_json_truncates_long_strings() -> None:
    serialized = telemetry.serialize_langfuse_json({"text": "x" * 5000}, max_chars=200)

    assert serialized is not None
    assert len(serialized) == 200
    assert serialized.endswith("... [truncated]")


class _UnserializableValue:
    def __str__(self) -> str:
        return "custom-value"


def test_serialize_langfuse_json_falls_back_for_unserializable_values() -> None:
    serialized = telemetry.serialize_langfuse_json({"value": _UnserializableValue()})

    assert serialized is not None
    parsed = json.loads(serialized)
    assert parsed == {"value": {"value": "custom-value"}} or parsed == {"value": "custom-value"}


def test_build_langfuse_trace_attributes_omits_none_values() -> None:
    attributes = telemetry.build_langfuse_trace_attributes(
        trace_name="fitcv.run_pipeline",
        session_id="run-123",
        user_id=None,
        input_payload={"jobs_path": "jobs.json"},
        output_payload=None,
        metadata={"stage": "pipeline"},
        extra_attributes={"run_id": "run-123", "unused": None},
    )

    assert attributes["langfuse.trace.name"] == "fitcv.run_pipeline"
    assert attributes["langfuse.session.id"] == "run-123"
    assert attributes["run_id"] == "run-123"
    assert "langfuse.user.id" not in attributes
    assert "langfuse.trace.output" not in attributes
    assert "unused" not in attributes
    assert json.loads(attributes["langfuse.trace.input"]) == {"jobs_path": "jobs.json"}
    assert json.loads(attributes["langfuse.trace.metadata"]) == {"stage": "pipeline"}


def test_build_langfuse_observation_attributes_serializes_optional_payloads() -> None:
    attributes = telemetry.build_langfuse_observation_attributes(
        observation_type="generation",
        input_payload={"prompt": "hello"},
        output_payload={"answer": "world"},
        metadata={"stage_id": "cv_generation"},
        model="gpt-test",
        model_parameters={"temperature": 0.2},
        usage_details={"input_tokens": 10, "output_tokens": 20},
        cost_details={"total_cost": 0.01},
        prompt_name="fitcv_structured_generation_prompt",
        extra_attributes={"job_url": "https://example.test/job"},
    )

    assert attributes["langfuse.observation.type"] == "generation"
    assert attributes["langfuse.observation.model"] == "gpt-test"
    assert attributes["langfuse.observation.prompt_name"] == "fitcv_structured_generation_prompt"
    assert attributes["job_url"] == "https://example.test/job"
    assert json.loads(attributes["langfuse.observation.input"]) == {"prompt": "hello"}
    assert json.loads(attributes["langfuse.observation.output"]) == {"answer": "world"}
    assert json.loads(attributes["langfuse.observation.metadata"]) == {"stage_id": "cv_generation"}
    assert json.loads(attributes["langfuse.observation.model_parameters"]) == {"temperature": 0.2}
    assert json.loads(attributes["langfuse.observation.usage_details"]) == {"input_tokens": 10, "output_tokens": 20}
    assert json.loads(attributes["langfuse.observation.cost_details"]) == {"total_cost": 0.01}
