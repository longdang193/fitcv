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
    assert telemetry_export.get("status") in {"disabled", "degraded", "export_enabled"}
    assert str(trace_context.get("trace_id") or "").strip()
    assert str(trace_context.get("span_id") or "").strip()
    assert str(trace_context.get("parent_span_id") or "").strip()
