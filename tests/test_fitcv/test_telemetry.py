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


def test_trace_context_always_has_otel_compatible_ids() -> None:
    telemetry.reset_telemetry_runtime_for_tests()
    trace_context = telemetry.build_trace_context("seed-value")
    assert len(str(trace_context["trace_id"])) == 32
    assert len(str(trace_context["span_id"])) == 16
    assert len(str(trace_context["parent_span_id"])) == 16
