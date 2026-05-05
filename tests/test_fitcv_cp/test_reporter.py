"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - control-plane reporting behavior
excludes:
  - live BigQuery or queue integrations
tags:
  - fast
  - ci-safe
"""

from unittest.mock import MagicMock, patch
import json
from fitcv_cp.reporter import PipelineReporter


def test_reporter_emits_event():
    """@proves admin_control_plane_core.pipelinereporter-integration
    @proves run_lifecycle_controls.full-audit-trail-in-pipeline-run-events
    """
    bq = MagicMock()
    bq.insert_rows_json.return_value = []
    reporter = PipelineReporter(run_id="r1", bq=bq, project="p", dataset="d")
    reporter.emit("pipeline_start", "info", "Run started")
    bq.insert_rows_json.assert_called_once()


def test_reporter_persists_local_event_without_bq():
    """@proves admin_control_plane_core.pipelinereporter-integration"""
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    with patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        reporter.emit("pipeline_start", "info", "ok")
    append_mock.assert_called_once()


def test_reporter_payload_serialized():
    """@proves admin_control_plane_core.pipelinereporter-integration"""
    bq = MagicMock()
    bq.insert_rows_json.return_value = []
    reporter = PipelineReporter(run_id="r1", bq=bq, project="p", dataset="d")
    reporter.emit("layer3_filter", "error", "timeout", payload={"retries": 3})
    call_args = bq.insert_rows_json.call_args[0][1][0]
    assert call_args["level"] == "error"
    assert "retries" in call_args["payload_json"]
    payload = json.loads(call_args["payload_json"])
    telemetry_export = dict(payload.get("telemetry_export") or {})
    trace_context = dict(payload.get("trace_context") or {})
    assert telemetry_export.get("status") in {"degraded", "export_enabled"}
    assert str(trace_context.get("trace_id") or "").strip()
    assert str(trace_context.get("span_id") or "").strip()
    assert str(trace_context.get("parent_span_id") or "").strip()


def test_reporter_langfuse_rich_io_disabled_by_default():
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    with patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        reporter.emit("pipeline_start", "info", "ok")
    event = append_mock.call_args[0][0]
    payload = json.loads(str(event.payload_json or "{}"))
    rich = dict(payload.get("langfuse_rich_io") or {})
    native = dict(payload.get("langfuse_rich_io_native") or {})
    assert rich.get("status") == "disabled"
    assert rich.get("degradation_reason") == "langfuse_rich_io_disabled"
    assert native.get("status") == "disabled"


def test_reporter_langfuse_rich_io_redacts_and_truncates(monkeypatch):
    monkeypatch.setenv("FITCV_LANGFUSE_RICH_IO_ENABLED", "true")
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    long_text = "x" * 700
    payload = {
        "api_key": "abc-123",
        "nested": {
            "password": "super-secret",
            "notes": long_text,
        },
    }
    with patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        reporter.emit("cv_analysis", "info", long_text, payload=payload)
    event = append_mock.call_args[0][0]
    emitted = json.loads(str(event.payload_json or "{}"))
    rich = dict(emitted.get("langfuse_rich_io") or {})
    assert rich.get("status") == "ready"
    rich_input = dict(rich.get("input") or {})
    rich_payload = dict(rich_input.get("payload") or {})
    assert rich_payload.get("api_key") == "[REDACTED]"
    nested = dict(rich_payload.get("nested") or {})
    assert nested.get("password") == "[REDACTED]"
    assert str(nested.get("notes") or "").endswith("...[truncated]")


def test_reporter_langfuse_rich_io_stage_specific_snapshots(monkeypatch):
    monkeypatch.setenv("FITCV_LANGFUSE_RICH_IO_ENABLED", "true")
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    payload = {
        "input_snapshot": {"total_jobs": 7, "token": "abc"},
        "output_snapshot": {"passed_filter": 2},
    }
    with patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        reporter.emit("layer4_cv_analysis", "info", "cv analysis complete", payload=payload)
    event = append_mock.call_args[0][0]
    emitted = json.loads(str(event.payload_json or "{}"))
    rich = dict(emitted.get("langfuse_rich_io") or {})
    native = dict(emitted.get("langfuse_rich_io_native") or {})
    rich_input = dict(rich.get("input") or {})
    rich_output = dict(rich.get("output") or {})
    assert rich_input.get("stage_family") == "cv_analysis"
    snapshot_in = dict(rich_input.get("input_snapshot") or {})
    assert snapshot_in.get("token") == "[REDACTED]"
    snapshot_out = dict(rich_output.get("output_snapshot") or {})
    assert snapshot_out.get("passed_filter") == 2
    assert native.get("status") in {"degraded", "sent"}


def test_reporter_langfuse_rich_io_native_sent(monkeypatch):
    monkeypatch.setenv("FITCV_LANGFUSE_RICH_IO_ENABLED", "true")
    monkeypatch.setenv("FITCV_LANGFUSE_PROJECT_PUBLIC_KEY", "pk-local")
    monkeypatch.setenv("FITCV_LANGFUSE_PROJECT_SECRET_KEY", "sk-local")
    monkeypatch.setenv("FITCV_LANGFUSE_BASE_URL", "http://localhost:3000")
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    payload = {"input_snapshot": {"total_jobs": 3}, "output_snapshot": {"passed_filter": 1}}
    with patch("fitcv_cp.reporter.httpx.post") as post_mock, \
         patch("fitcv_cp.reporter.append_event", return_value={"persistence_status": "persisted"}) as append_mock:
        post_mock.return_value.status_code = 200
        reporter.emit("layer1_normalize", "info", "normalize done", payload=payload)
    event = append_mock.call_args[0][0]
    emitted = json.loads(str(event.payload_json or "{}"))
    native = dict(emitted.get("langfuse_rich_io_native") or {})
    assert str(native.get("status") or "").startswith("sent:")
