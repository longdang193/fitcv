"""@meta
name: models
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.models.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import dataclasses
import datetime
from enum import Enum
import json
import uuid
from typing import Any, Optional

from fitcv_cp.run_artifact_contracts import stable_sha256_fingerprint


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_CONTINUE = "awaiting_continue"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class RunStageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

class JobStageStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    GENERATED = "generated"

class ResultBucket(str, Enum):
    PASSED = "passed"
    REJECTED = "rejected"

class CvGenerationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    GENERATED = "generated"
    REVIEW_REQUIRED = "review_required"
    VALIDATION_FAILED = "validation_failed"
    GENERATION_FAILED = "generation_failed"
    PERSISTENCE_FAILED = "persistence_failed"
    CANCELLED = "cancelled"

class CvEvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class CvReviewState(str, Enum):
    NONE = "none"
    STRETCH = "stretch"
    MANUAL_REQUIRED = "manual_required"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# Standardised stage names — use these constants in reporter and pipeline.py
STAGE_PIPELINE_START = "pipeline_start"
STAGE_LAYER1_JOBS = "layer1_jobs"
STAGE_LAYER2_CANDIDATE = "layer2_candidate"
STAGE_LAYER3_FILTER = "layer3_filter"
STAGE_LAYER3_RANKING = "layer3_ranking"
STAGE_LAYER4_CV_SKIP = "layer4_cv_skip"
STAGE_LAYER4_CV_VALIDATION_FAILED = "layer4_cv_validation_failed"
STAGE_PIPELINE_COMPLETE = "pipeline_complete"
STAGE_PIPELINE_FAILED = "pipeline_failed"


@dataclasses.dataclass
class PipelineRun:
    run_id: str
    status: RunStatus
    triggered_by: str
    trigger_source: str
    jobs_path: str
    config_path: str
    created_at: datetime.datetime
    run_name: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    total_jobs: Optional[int] = None
    passed_filter: Optional[int] = None
    ranked: Optional[int] = None
    cvs_generated: Optional[int] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None   # which stage the run failed at
    effective_settings_json: Optional[str] = None  # merged config snapshot at trigger time
    results_export_json: Optional[str] = None      # immutable run-results export snapshot for completed runs
    cv_generation_debug_json: Optional[str] = None  # immutable run-scoped CV-generation debug snapshot
    stage_transition_artifacts_json: Optional[str] = None  # immutable run-scoped stage transition artifact snapshot
    settings_used_json: Optional[str] = None  # immutable run-scoped effective-settings snapshot
    mapping_suggestions_json: Optional[str] = None  # immutable run-scoped mapping suggestions snapshot
    synonym_proposals_json: Optional[str] = None  # mutable run-scoped synonym proposal review snapshot
    run_mode: str = "run_all"
    checkpoint_status: Optional[str] = None
    next_stage: Optional[str] = None
    last_completed_stage: Optional[str] = None
    completed_stages: Optional[list[str]] = None
    checkpoint_payload_json: Optional[str] = None
    # run-scoped input metadata
    jobs_input_source: Optional[str] = None           # "path" | "upload" | "paste" | "scanner"
    jobs_input_json: Optional[str] = None             # canonical resolved jobs-input snapshot for supported trigger modes in new runs
    jobs_input_manifest_json: Optional[str] = None    # trigger-time jobs-input provenance metadata (e.g. upload source filenames)
    candidate_profile_source: Optional[str] = None    # "default_config" | "upload" | "paste"
    candidate_profile_json: Optional[str] = None      # canonical resolved candidate-profile snapshot for supported trigger modes in new runs
    # lifecycle controls
    queue_job_id: Optional[str] = None               # RQ job id for queued-run cancellation
    orchestration_backend: Optional[str] = None      # orchestration backend used for this run
    orchestration_run_id: Optional[str] = None       # backend-native execution id for this run
    cancel_requested_at: Optional[datetime.datetime] = None
    cancel_requested_by: Optional[str] = None
    archived_at: Optional[datetime.datetime] = None
    archived_by: Optional[str] = None
    raw_status: Optional[str] = None
    status_detail: Optional[str] = None
    warning_json: Optional[str] = None
    partial_completion: bool = False
    progress_completed: int = 0
    progress_total: int = 0
    status_detail: Optional[str] = None
    warning_json: Optional[str] = None
    partial_completion: bool = False
    progress_completed: int = 0
    progress_total: int = 0


@dataclasses.dataclass
class RunEvent:
    run_id: str
    event_id: str
    stage: str
    level: str   # one of EventLevel values
    message: str
    created_at: datetime.datetime
    payload_json: Optional[str] = None

PROCESS_EVENT_SCHEMA_VERSION = "process_event_v1"
PROCESS_EVENT_STATES = frozenset({
    "requested",
    "started",
    "progress",
    "waiting",
    "succeeded",
    "skipped",
    "rejected",
    "failed",
    "cancelled",
    "recorded",
})
_PROCESS_EVENT_MAX_STRING_LENGTH = 500
_PROCESS_EVENT_MAX_LIST_ITEMS = 20
_PROCESS_EVENT_MAX_OBJECT_KEYS = 30
_PROCESS_EVENT_MAX_DEPTH = 4
_PROCESS_EVENT_SENSITIVE_KEY_PARTS = frozenset({
    "password",
    "secret",
    "authorization",
    "api_key",
    "private_key",
    "access_key",
    "cookie",
})


def _bound_process_event_string(value: str) -> str:
    if len(value) <= _PROCESS_EVENT_MAX_STRING_LENGTH:
        return value
    return f"{value[:_PROCESS_EVENT_MAX_STRING_LENGTH]}...[truncated]"


def sanitize_process_event_value(value: Any, *, depth: int = 0) -> Any:
    if depth > _PROCESS_EVENT_MAX_DEPTH:
        return "[truncated_depth]"
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, datetime.datetime):
        value = value.isoformat()
    if isinstance(value, dict):
        reduced: dict[str, Any] = {}
        keys = sorted((str(key), key) for key in value)
        for key_text, original_key in keys[:_PROCESS_EVENT_MAX_OBJECT_KEYS]:
            if any(part in key_text.lower() for part in _PROCESS_EVENT_SENSITIVE_KEY_PARTS):
                reduced[key_text] = "[REDACTED]"
            else:
                reduced[key_text] = sanitize_process_event_value(
                    value[original_key], depth=depth + 1
                )
        if len(keys) > _PROCESS_EVENT_MAX_OBJECT_KEYS:
            reduced["__truncated_keys__"] = True
        return reduced
    if isinstance(value, (list, tuple)):
        items = [
            sanitize_process_event_value(item, depth=depth + 1)
            for item in list(value)[:_PROCESS_EVENT_MAX_LIST_ITEMS]
        ]
        if len(value) > _PROCESS_EVENT_MAX_LIST_ITEMS:
            items.append("[truncated_items]")
        return items
    if isinstance(value, str):
        return _bound_process_event_string(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    try:
        return _bound_process_event_string(str(value))
    except Exception as exc:
        raise ValueError("unsupported process event value") from exc


def _process_event_json(value: Any) -> str:
    return json.dumps(
        sanitize_process_event_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclasses.dataclass(frozen=True)
class ProcessEvent:
    schema_version: str
    event_id: str
    process_type: str
    process_id: str
    operation: str
    state: str
    level: str
    message: str
    payload_json: Optional[str]
    diagnostic_refs_json: Optional[str]
    trace_context_json: Optional[str]
    recorded_at: datetime.datetime
    event_fingerprint: str

    @property
    def run_id(self) -> str:
        return self.process_id

    @property
    def stage(self) -> str:
        return self.operation

    @property
    def created_at(self) -> datetime.datetime:
        return self.recorded_at


@dataclasses.dataclass(frozen=True)
class ProcessEventIntegrityConflict:
    conflict_id: str
    process_type: str
    process_id: str
    event_id: Optional[str]
    reason: str
    evidence_json: str
    recorded_at: datetime.datetime


def build_process_event(
    *,
    process_type: str,
    process_id: str,
    operation: str,
    state: str,
    level: str,
    message: str,
    payload: Any = None,
    diagnostic_refs: Any = None,
    trace_context: Any = None,
    event_id: str | None = None,
    recorded_at: datetime.datetime | None = None,
) -> ProcessEvent:
    normalized_process_type = str(process_type).strip()
    normalized_process_id = str(process_id).strip()
    normalized_operation = str(operation).strip()
    normalized_state = str(state).strip().lower()
    normalized_level = str(level).strip().lower()
    if not normalized_process_type or not normalized_process_id or not normalized_operation:
        raise ValueError("process_type, process_id, and operation are required")
    if normalized_state not in PROCESS_EVENT_STATES:
        raise ValueError(f"invalid process event state: {state}")
    if normalized_level not in {item.value for item in EventLevel}:
        raise ValueError(f"invalid process event level: {level}")
    timestamp = recorded_at or datetime.datetime.now(datetime.timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    timestamp = timestamp.astimezone(datetime.timezone.utc)
    normalized_event_id = str(event_id or uuid.uuid4()).strip()
    if not normalized_event_id:
        raise ValueError("event_id is required")
    normalized_message = _bound_process_event_string(str(message))
    payload_json = _process_event_json(payload) if payload is not None else None
    diagnostic_refs_json = (
        _process_event_json(diagnostic_refs) if diagnostic_refs is not None else None
    )
    trace_context_json = (
        _process_event_json(trace_context) if trace_context is not None else None
    )
    fingerprint_payload = {
        "schema_version": PROCESS_EVENT_SCHEMA_VERSION,
        "event_id": normalized_event_id,
        "process_type": normalized_process_type,
        "process_id": normalized_process_id,
        "operation": normalized_operation,
        "state": normalized_state,
        "level": normalized_level,
        "message": normalized_message,
        "payload_json": payload_json,
        "diagnostic_refs_json": diagnostic_refs_json,
        "trace_context_json": trace_context_json,
        "recorded_at": timestamp.isoformat(),
    }
    return ProcessEvent(
        schema_version=PROCESS_EVENT_SCHEMA_VERSION,
        event_id=normalized_event_id,
        process_type=normalized_process_type,
        process_id=normalized_process_id,
        operation=normalized_operation,
        state=normalized_state,
        level=normalized_level,
        message=normalized_message,
        payload_json=payload_json,
        diagnostic_refs_json=diagnostic_refs_json,
        trace_context_json=trace_context_json,
        recorded_at=timestamp,
        event_fingerprint=stable_sha256_fingerprint(fingerprint_payload),
    )
