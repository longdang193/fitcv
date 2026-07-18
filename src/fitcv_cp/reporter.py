"""@meta
name: reporter
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.reporter.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import datetime
import json
import logging
import os
import uuid
from typing import Any, Optional

import httpx
from fitcv.pipeline_contracts import JOB_OUTCOME_EVENT_STAGE
from fitcv.telemetry import (
    build_trace_context,
    current_trace_context,
    telemetry_export_status,
)
from fitcv_cp.sqlite_store import (
    append_process_event,
    list_pending_process_event_deliveries,
    record_process_event_delivery,
)
from fitcv_cp.models import (
    ProcessEvent,
    build_process_event,
    sanitize_process_event_value,
)
from fitcv_cp.runtime_contracts import is_truthy_env

logger = logging.getLogger(__name__)

def _truncate_string(value: str) -> str:
    return str(sanitize_process_event_value(value))


def _redact_and_bound(value: Any, *, depth: int = 0) -> Any:
    return sanitize_process_event_value(value, depth=depth)

def _build_langfuse_rich_io_contract(
    *,
    stage: str,
    level: str,
    message: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not is_truthy_env(os.environ.get("FITCV_LANGFUSE_RICH_IO_ENABLED")):
        return {
            "status": "disabled",
            "degradation_reason": "langfuse_rich_io_disabled",
            "input": None,
            "output": None,
        }
    stage_lower = stage.lower()
    stage_family = "generic"
    if "normalize" in stage_lower:
        stage_family = "normalize"
    elif "cv_analysis" in stage_lower:
        stage_family = "cv_analysis"
    elif "cv_generation" in stage_lower:
        stage_family = "cv_generation"

    bounded_payload = payload
    rich_input: dict[str, Any] = {
        "stage": stage,
        "stage_family": stage_family,
        "message": message,
        "payload": bounded_payload,
    }
    rich_output: dict[str, Any] = {
        "level": level,
        "event_status": "emitted",
        "stage_family": stage_family,
    }
    latency_ms = payload.get("latency_ms")
    if isinstance(latency_ms, int) and latency_ms >= 0:
        rich_output["latency_ms"] = latency_ms
    usage_payload = payload.get("usage")
    if isinstance(usage_payload, dict):
        rich_output["usage"] = _redact_and_bound(usage_payload)
    cost_payload = payload.get("cost")
    if isinstance(cost_payload, dict):
        rich_output["cost"] = _redact_and_bound(cost_payload)
    elif isinstance(cost_payload, (int, float)):
        rich_output["cost"] = {"total": float(cost_payload), "currency": "usd"}
    elif isinstance(payload.get("cost_usd"), (int, float)):
        rich_output["cost"] = {"total": float(payload["cost_usd"]), "currency": "usd"}

    if stage_family in {"normalize", "cv_analysis", "cv_generation"}:
        input_snapshot = payload.get("input_snapshot")
        output_snapshot = payload.get("output_snapshot")
        if isinstance(input_snapshot, (dict, list)):
            rich_input["input_snapshot"] = _redact_and_bound(input_snapshot)
        if isinstance(output_snapshot, (dict, list)):
            rich_output["output_snapshot"] = _redact_and_bound(output_snapshot)

    return {
        "status": "ready",
        "degradation_reason": None,
        "input": rich_input,
        "output": rich_output,
    }


def _langfuse_ingestion_enabled() -> bool:
    return is_truthy_env(os.environ.get("FITCV_LANGFUSE_RICH_IO_ENABLED"))


def _build_langfuse_ingestion_headers() -> dict[str, str] | None:
    public_key = str(os.environ.get("FITCV_LANGFUSE_PROJECT_PUBLIC_KEY") or "").strip()
    secret_key = str(os.environ.get("FITCV_LANGFUSE_PROJECT_SECRET_KEY") or "").strip()
    if not public_key or not secret_key:
        return None
    import base64

    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _emit_langfuse_native_io(
    *,
    run_id: str,
    stage: str,
    trace_id: str,
    rich_contract: dict[str, Any],
    event: ProcessEvent,
) -> tuple[str, str | None]:
    if not _langfuse_ingestion_enabled():
        return "disabled", "langfuse_rich_io_disabled"
    stage_family = str((rich_contract.get("input") or {}).get("stage_family") or "")
    if stage_family in {"normalize", "cv_analysis", "cv_generation"}:
        return "superseded_by_span_contract", "otel_langfuse_span_contract_active"
    headers = _build_langfuse_ingestion_headers()
    if headers is None:
        return "degraded", "langfuse_credentials_missing"
    if stage_family not in {"generic"}:
        return "not_applicable", None
    base_url = str(os.environ.get("FITCV_LANGFUSE_BASE_URL") or "").strip().rstrip("/")
    if not base_url:
        return "degraded", "langfuse_base_url_missing"
    ingestion_url = f"{base_url}/api/public/ingestion"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    rich_input = dict(rich_contract.get("input") or {})
    rich_output = dict(rich_contract.get("output") or {})
    batch: list[dict[str, Any]] = [
        {
            "id": str(uuid.uuid4()),
            "timestamp": now,
            "type": "trace-create",
            "body": {
                # Attach rich payloads to the same trace context surfaced in run events.
                "id": trace_id,
                "name": f"{stage}:rich_io",
                "sessionId": run_id,
                "userId": str(os.environ.get("FITCV_LANGFUSE_USER_ID") or "fitcv-control-plane"),
                "input": rich_input,
                "output": rich_output,
                "metadata": {
                    "source_trace_id": trace_id,
                    "stage": stage,
                    "stage_family": stage_family,
                    "rich_io_source": "fitcv-control-plane",
                    "process_event": {
                        "schema_version": event.schema_version,
                        "event_id": event.event_id,
                        "process_type": event.process_type,
                        "process_id": event.process_id,
                        "operation": event.operation,
                        "state": event.state,
                        "level": event.level,
                        "message": event.message,
                        "payload_json": event.payload_json,
                        "diagnostic_refs_json": event.diagnostic_refs_json,
                        "trace_context_json": event.trace_context_json,
                        "recorded_at": event.recorded_at.isoformat(),
                        "event_fingerprint": event.event_fingerprint,
                    },
                },
            },
        }
    ]
    latency_ms = rich_output.get("latency_ms")
    if isinstance(latency_ms, int) and latency_ms > 0:
        end_at = datetime.datetime.now(datetime.timezone.utc)
        start_at = end_at - datetime.timedelta(milliseconds=int(latency_ms))
        batch.append(
            {
                "id": str(uuid.uuid4()),
                "timestamp": now,
                "type": "observation-create",
                "body": {
                    "id": f"{trace_id}:latency",
                    "traceId": trace_id,
                    "name": f"{stage}:rich_io_latency",
                    "type": "SPAN",
                    "startTime": start_at.isoformat().replace("+00:00", "Z"),
                    "endTime": end_at.isoformat().replace("+00:00", "Z"),
                    "level": "DEFAULT",
                    "metadata": {
                        "source_trace_id": trace_id,
                        "stage": stage,
                        "stage_family": stage_family,
                        "latency_source": "payload.latency_ms",
                    },
                },
            }
        )
    body = {
        "batch": batch,
        "metadata": {"source": "fitcv-control-plane"},
    }
    try:
        resp = httpx.post(ingestion_url, headers=headers, json=body, timeout=5.0)
        if 200 <= resp.status_code < 300:
            return f"sent:{trace_id}", None
        return "degraded", f"langfuse_ingestion_http_{resp.status_code}"
    except Exception:
        return "degraded", "langfuse_ingestion_failed"


def append_event(event: ProcessEvent, **kwargs: Any) -> dict[str, str]:
    return append_process_event(event, **kwargs)


def _default_process_event_rich_contract(event: ProcessEvent) -> dict[str, Any]:
    payload = json.loads(event.payload_json) if event.payload_json else {}
    return {
        "status": "enabled",
        "degradation_reason": None,
        "input": {
            "stage": event.operation,
            "stage_family": "generic",
            "message": event.message,
            "payload": payload,
        },
        "output": {
            "level": event.level,
            "event_status": event.state,
            "stage_family": "generic",
        },
    }


def deliver_process_event(
    event: ProcessEvent,
    *,
    rich_contract: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    trace_context = json.loads(event.trace_context_json) if event.trace_context_json else {}
    trace_id = str(trace_context.get("trace_id") or event.event_id)
    native_status, native_reason = _emit_langfuse_native_io(
        run_id=event.process_id,
        stage=event.operation,
        trace_id=trace_id,
        rich_contract=rich_contract or _default_process_event_rich_contract(event),
        event=event,
    )
    delivered = native_status.startswith("sent:") or native_status in {
        "disabled",
        "not_applicable",
        "superseded_by_span_contract",
    }
    record_process_event_delivery(
        event.event_id,
        "langfuse",
        "delivered" if delivered else "failed",
        native_reason,
    )
    return native_status, native_reason


def retry_pending_process_event_deliveries(*, limit: int = 20) -> int:
    delivered_count = 0
    for item in list_pending_process_event_deliveries(limit=limit):
        if item["sink"] != "langfuse":
            continue
        status, _reason = deliver_process_event(item["event"])
        if status.startswith("sent:") or status in {
            "disabled",
            "not_applicable",
            "superseded_by_span_contract",
        }:
            delivered_count += 1
    return delivered_count


class PipelineReporter:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id

    def emit(
        self,
        stage: str,
        level: str,
        message: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            retry_pending_process_event_deliveries(limit=5)
        except Exception as exc:
            logger.warning("Pending process-event delivery retry failed during emission: %s", exc)
        source_payload = dict(payload or {})
        trace_context: dict[str, Any] | None = None
        rich_contract: dict[str, Any] | None = None
        payload_value = dict(source_payload)
        delivery_sinks: tuple[str, ...] = ()
        if stage != JOB_OUTCOME_EVENT_STAGE:
            active_trace_context = current_trace_context()
            trace_context = (
                dict(active_trace_context)
                if active_trace_context is not None
                else build_trace_context(
                    f"run:{self._run_id}:stage:{stage}:message:{message}",
                    emit_otel_span=False,
                )
            )
            payload_value["telemetry_export"] = telemetry_export_status()
            rich_contract = _build_langfuse_rich_io_contract(
                stage=stage,
                level=level,
                message=message,
                payload=source_payload,
            )
            payload_value["langfuse_rich_io"] = rich_contract
            delivery_sinks = ("langfuse",)
        event = build_process_event(
            process_type="pipeline",
            process_id=self._run_id,
            operation=stage,
            state="recorded",
            level=level,
            message=message,
            payload=payload_value,
            trace_context=trace_context,
        )
        if rich_contract is not None and event.payload_json:
            rich_contract = dict(json.loads(event.payload_json).get("langfuse_rich_io") or {})
        try:
            status = append_event(event, delivery_sinks=delivery_sinks)
            if status.get("persistence_status") != "persisted":
                logger.warning(
                    "Reporter event degraded [run_id=%s stage=%s status=%s reason=%s]",
                    self._run_id,
                    stage,
                    status.get("persistence_status"),
                    status.get("degradation_reason"),
                )
                return
            if status.get("persistence_backend") != "sqlite" or rich_contract is None:
                return
            deliver_process_event(event, rich_contract=rich_contract)
        except Exception as exc:
            logger.warning("Reporter failed to write event: %s", exc)
