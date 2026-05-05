"""
@meta
type: test
scope: unit
domain: observability
covers:
  - OTel runtime degradation and config behavior
excludes:
  - live collector connectivity
tags:
  - fast
  - ci-safe
"""

from fitcv import telemetry


def test_telemetry_disabled_by_default_reports_degraded() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    status = telemetry.telemetry_export_status()
    assert status["status"] == "degraded"
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
