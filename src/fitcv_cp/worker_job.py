"""
@meta
name: control_plane_worker_job
type: script
domain: run_orchestration
responsibility:
  - Execute one queued pipeline run and persist lifecycle state.
  - Persist run-scoped settings-used and compact results snapshots.
inputs:
  - queued run id and pipeline paths
  - control-plane BigQuery run state
outputs:
  - run lifecycle updates
  - settings-used and results-export snapshots
capabilities:
  - admin_control_plane_core.pipelinereporter-integration
  - run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs
  - run_lifecycle_controls.full-audit-trail-in-pipeline-run-events
  - inspection_debugging.settings-used-export
  - inspection_debugging.results-ledger-inspection
  - inspection_debugging.stage-transition-diagnostics
  - inspection_debugging.prompt-provenance-diagnostics
  - inspection_debugging.reuse-diagnostics
  - inspection_debugging.quality-metrics-diagnostics
  - settings_system.settings-used-exports
  - pipeline_performance.large-runs-avoid-some-row-scaled-layer-4-event-noise-by-relying-more-on-aggregate-stage-summaries-plus-stage-owned-artifacts
  - pipeline_performance.results-json-now-keeps-only-compact-job-ledger-fields-instead-of-repeating-full-job-snapshots-heavy-score-explanation-internals-and-full-cv-bodies-already-represented-elsewhere
  - trigger_run_management.shared-stage-progress
  - trigger_run_management.run-owned-artifact-exports
  - trigger_run_management.run-results-export
  - trigger_run_management.reranker-fit-authority
tags:
  - worker
  - control-plane
lifecycle:
  status: active
"""
import datetime
import hashlib
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from fitcv.pipeline import PipelineCancelled, run_pipeline
from fitcv_cp.backend_runtime import resolve_backend_runtime
from fitcv_cp.bq_store import (
    append_event,
    get_events,
    get_run,
    list_runs,
    update_run_checkpoint,
    update_run_progress,
    update_run_cv_generation_debug,
    update_run_mapping_suggestions,
    update_run_synonym_proposals,
    update_run_results_export,
    update_run_settings_used,
    update_run_stage_transition_artifacts,
    update_run_status,
)
from fitcv_cp.models import RunEvent, RunStatus
from fitcv_cp.data_plane import data_plane_contract_payload

logger = logging.getLogger(__name__)
_MAX_DEBUG_MARKDOWN_CHARS = 4000
_LATE_STAGE_REUSE_RUN_SCAN_LIMIT = 50
_SETTINGS_COMPATIBILITY_KEYS = {
    "vector_top_n",
    "rerank_top_n",
    "cv_generation_model",
    "prompt_version",
    "cv_max_pages",
    "required_cv_sections",
}
_CV_GENERATION_ATTEMPTED_STATUSES = {
    "accepted",
    "review_required",
    "validation_failed",
    "generation_failed",
    "persistence_failed",
}
_CV_DEBUG_ANALYSIS_OMISSION_STATUSES = {
    "blocked_by_reranker_fit",
    "skipped_fit_gate",
    "analysis_failed",
}
_RUN_MODE_LABELS = {
    "run_all": "Run All",
    "manual_staged": "Stage by Stage",
}
_NON_SKILL_MIN_SUPPORT_FOR_PROPOSAL = 2
_WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def _stage_deterministic_summary(
    *,
    stage_id: str,
    output_counts: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = dict(output_counts or {})
    if stage_id == "cv_analysis":
        return {
            "source_stage": "cv_analysis",
            "stage_owned_subreason": "stage_summary",
            "deterministic_outcome": None,
            "outcome_counts": {
                "ready_for_generation": int(counts.get("ready_for_generation") or 0),
                "blocked_by_reranker_fit": int(counts.get("blocked_by_reranker_fit") or 0),
                "skipped_fit_gate": int(counts.get("skipped_fit_gate") or 0),
                "analysis_failed": int(counts.get("analysis_failed") or 0),
            },
        }
    if stage_id == "cv_generation":
        return {
            "source_stage": "cv_generation",
            "stage_owned_subreason": "stage_summary",
            "deterministic_outcome": None,
            "outcome_counts": {
                "accepted": int(counts.get("accepted") or 0),
                "review_required": int(counts.get("review_required") or 0),
                "validation_failed": int(counts.get("validation_failed") or 0),
                "generation_failed": int(counts.get("generation_failed") or 0),
                "persistence_failed": int(counts.get("persistence_failed") or 0),
            },
        }
    return {
        "source_stage": None,
        "stage_owned_subreason": None,
        "deterministic_outcome": None,
        "outcome_counts": {},
    }

def _policy_registry_version(config_payload: dict[str, Any] | None) -> str:
    cfg = dict(config_payload or {})
    block = dict(cfg.get("policy_registry") or {})
    return str(block.get("version") or "policy_registry.v1")

def _policy_envelope_signature(config_payload: dict[str, Any] | None) -> str:
    cfg = dict(config_payload or {})
    envelope = {
        "ranking_weights": dict(cfg.get("ranking_weights") or {}),
        "preference_fit_weights": dict(cfg.get("preference_fit_weights") or {}),
        "missing_value_defaults": dict(cfg.get("missing_value_defaults") or {}),
        "fit_label_thresholds": dict(cfg.get("fit_label_thresholds") or {}),
        "cv": dict(cfg.get("cv") or {}),
        "pipeline": dict(cfg.get("pipeline") or {}),
        "prompts_runtime": dict(cfg.get("prompts_runtime") or {}),
    }
    raw = json.dumps(envelope, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _resolve_run_replay_context(
    *,
    effective_config: dict[str, Any] | None,
    run_id: str,
) -> dict[str, Any]:
    cfg = dict(effective_config or {})
    runtime_inputs = dict(cfg.get("runtime_inputs") or {})
    replay = dict(runtime_inputs.get("replay_context") or {})
    replay_mode = str(replay.get("replay_mode") or "strict").strip().lower() or "strict"
    if replay_mode not in {"strict", "policy_replay"}:
        replay_mode = "strict"
    return {
        "replay_mode": replay_mode,
        "replay_source_run_id": str(replay.get("replay_source_run_id") or run_id),
        "policy_registry_version": str(replay.get("policy_registry_version") or _policy_registry_version(cfg)),
        "policy_envelope_signature": str(replay.get("policy_envelope_signature") or _policy_envelope_signature(cfg)),
    }


def _get_bq() -> bigquery.Client:
    return bigquery.Client()


def _normalize_runtime_service_account_key(
    effective_config: dict[str, Any] | None,
    *,
    run_id: str,
) -> dict[str, Any] | None:
    """Normalize service_account_key for Linux/container runtime safety."""
    if not isinstance(effective_config, dict):
        return effective_config
    key_path = str(effective_config.get("service_account_key") or "").strip()
    if not key_path:
        return effective_config
    if os.name == "nt":
        return effective_config
    if not _WINDOWS_ABSOLUTE_PATH_PATTERN.match(key_path):
        return effective_config

    normalized = dict(effective_config)
    env_key_path = str(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if env_key_path and Path(env_key_path).exists():
        normalized["service_account_key"] = env_key_path
        logger.warning(
            "[run_id=%s] Normalized Windows service_account_key %r to runtime credential path %r",
            run_id,
            key_path,
            env_key_path,
        )
        return normalized

    fallback_path = "/app/sa_key.json"
    if Path(fallback_path).exists():
        normalized["service_account_key"] = fallback_path
        logger.warning(
            "[run_id=%s] Normalized Windows service_account_key %r to container fallback %r",
            run_id,
            key_path,
            fallback_path,
        )
    else:
        logger.warning(
            "[run_id=%s] Windows service_account_key %r detected in non-Windows runtime and no fallback key file was found.",
            run_id,
            key_path,
        )
    return normalized


def _run_cancelled_event(run_id: str, message: str) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        event_id=str(uuid.uuid4()),
        stage="run_cancelled",
        level="warning",
        message=message,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def _snapshot_persist_failed_event(run_id: str, snapshot_name: str, message: str) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        event_id=str(uuid.uuid4()),
        stage="snapshot_persist_failed",
        level="warning",
        message=f"{snapshot_name} snapshot persistence failed: {message}",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def _append_degraded_snapshot_persistence_warning(
    *,
    run_id: str,
    snapshot_name: str,
    persistence_status: dict[str, str] | None,
    bq: Any,
    project: str,
    dataset: str,
) -> None:
    status = dict(persistence_status or {})
    if status.get("persistence_status") in {"persisted", "not_applicable", ""}:
        return
    append_event(
        _snapshot_persist_failed_event(
            run_id,
            snapshot_name,
            str(status.get("degradation_reason") or status.get("persistence_status") or "unknown_degradation"),
        ),
        bq,
        project=project,
        dataset=dataset,
    )


def _estimate_jobs_count_from_input(jobs_path: str) -> int:
    try:
        payload = json.loads(Path(jobs_path).read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        jobs = payload.get("jobs")
        if isinstance(jobs, list):
            return len(jobs)
    return 0


def _config_agentic_late_stage_enabled(config: dict[str, Any] | None) -> bool:
    cv_block = dict((config or {}).get("cv") or {})
    late_stage_block = dict(cv_block.get("agentic_late_stage") or {})
    return bool(late_stage_block.get("enabled"))


def _build_late_stage_mode_payload(
    *,
    summary: dict[str, Any],
    effective_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing_payload = summary.get("late_stage_mode")
    if isinstance(existing_payload, dict):
        return dict(existing_payload)
    agentic_enabled = _config_agentic_late_stage_enabled(effective_config)
    return {
        "late_stage_mode": "agentic" if agentic_enabled else "non_agentic",
        "agentic_late_stage_enabled": agentic_enabled,
        "mode_source": "cv.agentic_late_stage.enabled",
        "agentic_status": "completed" if agentic_enabled else "not_applicable",
    }


def _build_results_export_payload(
    *,
    run_id: str,
    run_record: Any,
    effective_config: dict[str, Any] | None,
    summary: dict[str, Any],
    export_results: list[dict[str, Any]],
    finished_at: datetime.datetime,
    replay_context: dict[str, Any],
) -> str:
    def _json_safe(value: Any) -> Any:
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [_json_safe(item) for item in value]
        if isinstance(value, set):
            return [_json_safe(item) for item in sorted(value)]
        return value

    def _string_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    def _normalized_run_mode(value: Any) -> str:
        run_mode = _string_or_none(value)
        if run_mode in _RUN_MODE_LABELS:
            return run_mode
        return "run_all"

    def _iso_or_none(value: Any) -> str | None:
        return value.isoformat() if isinstance(value, datetime.datetime) else None

    diagnostic_support = {
        "late_stage_reuse_snapshots": _json_safe(summary.get("late_stage_reuse_snapshots") or {}),
    }
    stage_result_summary: dict[str, Any] = {}
    stage_transition_artifacts = dict(summary.get("stage_transition_artifacts") or {})
    stage_blocks = dict(stage_transition_artifacts.get("stages") or {})
    for stage_id, block in stage_blocks.items():
        if not isinstance(block, dict):
            continue
        stage_result = dict(block.get("stage_result") or {})
        trace_context = dict(stage_result.get("trace_context") or {})
        deterministic_summary = _stage_deterministic_summary(
            stage_id=str(stage_id),
            output_counts=dict(block.get("output_counts") or {}),
        )
        stage_result_summary[str(stage_id)] = {
            "status": str(block.get("status") or ""),
            "decision": _json_safe(stage_result.get("decision") or {}),
            "policy_version": str(stage_result.get("policy_version") or ""),
            "trace_context": {
                "trace_id": str(trace_context.get("trace_id") or ""),
                "span_id": str(trace_context.get("span_id") or ""),
                "parent_span_id": str(trace_context.get("parent_span_id") or ""),
            },
            "source_stage": deterministic_summary["source_stage"],
            "deterministic_outcome": deterministic_summary["deterministic_outcome"],
            "stage_owned_subreason": deterministic_summary["stage_owned_subreason"],
            "outcome_counts": deterministic_summary["outcome_counts"],
        }
    payload = {
        "run_id": run_id,
        "results_schema_version": "results_job_ledger_v3",
        "status": RunStatus.SUCCEEDED.value,
        "triggered_by": _string_or_none(getattr(run_record, "triggered_by", "")) or "",
        "run_mode": _normalized_run_mode(getattr(run_record, "run_mode", None)),
        "run_mode_label": _RUN_MODE_LABELS[_normalized_run_mode(getattr(run_record, "run_mode", None))],
        "created_at": _iso_or_none(getattr(run_record, "created_at", None)),
        "started_at": _iso_or_none(getattr(run_record, "started_at", None)),
        "finished_at": finished_at.isoformat(),
        "jobs_path": _string_or_none(getattr(run_record, "jobs_path", "")) or "",
        "jobs_input_source": _string_or_none(getattr(run_record, "jobs_input_source", None)),
        "candidate_profile_source": _string_or_none(getattr(run_record, "candidate_profile_source", None)),
        "summary": {
            "total_jobs": int(summary.get("total_jobs", 0)),
            "passed_filter": int(summary.get("passed_filter", 0)),
            "ranked": int(summary.get("ranked", 0)),
            "cvs_generated": int(summary.get("cvs_generated", 0)),
        },
        "late_stage_mode": _build_late_stage_mode_payload(summary=summary),
        "stage_result_summary": stage_result_summary,
        "data_plane": data_plane_contract_payload(effective_config),
        "replay_context": {
            "replay_mode": str(replay_context.get("replay_mode") or "strict"),
            "replay_source_run_id": str(replay_context.get("replay_source_run_id") or run_id),
            "policy_registry_version": str(replay_context.get("policy_registry_version") or "policy_registry.v1"),
            "policy_envelope_signature": str(replay_context.get("policy_envelope_signature") or ""),
        },
        "results": _json_safe(export_results),
    }
    if diagnostic_support["late_stage_reuse_snapshots"]:
        payload["diagnostic_support"] = diagnostic_support
    return json.dumps(payload, ensure_ascii=False)


def _collect_late_stage_reuse_snapshots(
    *,
    current_run_id: str,
    bq: Any,
    project: str,
    dataset: str,
) -> dict[str, Any]:
    snapshots: dict[str, Any] = {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [],
        "cv_analysis_records": [],
    }
    try:
        prior_runs = list_runs(
            bq,
            project=project,
            dataset=dataset,
            limit=_LATE_STAGE_REUSE_RUN_SCAN_LIMIT,
            include_archived=True,
        )
    except Exception as exc:
        logger.warning("[run_id=%s] Failed to list prior runs for reuse lookup: %s", current_run_id, exc)
        return snapshots

    for prior_run in prior_runs:
        if prior_run.run_id == current_run_id:
            continue
        if prior_run.status != RunStatus.SUCCEEDED or not prior_run.results_export_json:
            continue
        try:
            payload = json.loads(prior_run.results_export_json)
        except Exception as exc:
            logger.warning(
                "[run_id=%s] Failed to parse prior results_export_json for reuse lookup [source_run_id=%s]: %s",
                current_run_id,
                prior_run.run_id,
                exc,
            )
            continue
        diagnostic_support = dict(payload.get("diagnostic_support") or {})
        reuse_payload = dict(
            diagnostic_support.get("late_stage_reuse_snapshots")
            or payload.get("late_stage_reuse_snapshots")
            or {}
        )
        snapshots["ranking_ai_scores"].extend(
            [
                dict(item)
                for item in list(reuse_payload.get("ranking_ai_scores") or [])
                if isinstance(item, dict)
            ]
        )
        snapshots["cv_analysis_records"].extend(
            [
                dict(item)
                for item in list(reuse_payload.get("cv_analysis_records") or [])
                if isinstance(item, dict)
            ]
        )
    return snapshots


def _build_cv_generation_debug_payload(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
) -> str:
    def _string_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    def _normalized_run_mode(value: Any) -> str:
        run_mode = _string_or_none(value)
        if run_mode in _RUN_MODE_LABELS:
            return run_mode
        return "run_all"

    def _truncate_large_fields(record: dict[str, Any]) -> dict[str, Any]:
        truncated = dict(record)
        markdown_final = truncated.get("markdown_final")
        if isinstance(markdown_final, str) and len(markdown_final) > _MAX_DEBUG_MARKDOWN_CHARS:
            truncated["markdown_final"] = markdown_final[:_MAX_DEBUG_MARKDOWN_CHARS] + "\n...[truncated]"
        return truncated

    debug_records = [
        _truncate_large_fields(record)
        for record in list(summary.get("cv_generation_debug_records") or [])
    ]
    for record in debug_records:
        if not isinstance(record, dict):
            continue
        ranking_fit_label = record.get("ranking_fit_label")
        reranker_fit_label = record.get("reranker_fit_label")
        if ranking_fit_label is None and reranker_fit_label is not None:
            record["ranking_fit_label"] = reranker_fit_label
        if reranker_fit_label is None and ranking_fit_label is not None:
            record["reranker_fit_label"] = ranking_fit_label
    ranked_jobs_total = int(summary.get("ranked", 0))
    attempted_generation_jobs_total = sum(
        1
        for record in debug_records
        if str(record.get("status") or "") in _CV_GENERATION_ATTEMPTED_STATUSES
    )
    debug_record_job_urls = {
        str(record.get("job_url") or "")
        for record in debug_records
        if str(record.get("job_url") or "")
    }
    omission_reason_counts: dict[str, int] = {}
    for record in debug_records:
        status = str(record.get("status") or "")
        if status in _CV_GENERATION_ATTEMPTED_STATUSES:
            continue
        omission_reason_counts[status] = omission_reason_counts.get(status, 0) + 1
    for record in list(summary.get("cv_analysis_results") or []):
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "")
        if status not in _CV_DEBUG_ANALYSIS_OMISSION_STATUSES:
            continue
        job_url = str(record.get("job_url") or "")
        if job_url and job_url in debug_record_job_urls:
            continue
        omission_reason_counts[status] = omission_reason_counts.get(status, 0) + 1
    non_attempted_ranked_jobs_total = sum(omission_reason_counts.values())
    payload = {
        "run_id": run_id,
        "status": RunStatus.SUCCEEDED.value,
        "debug_schema_version": "cv_generation_debug_v3",
        "run_mode": _normalized_run_mode(getattr(run_record, "run_mode", None)),
        "run_mode_label": _RUN_MODE_LABELS[_normalized_run_mode(getattr(run_record, "run_mode", None))],
        "created_at": finished_at.isoformat(),
        "ranked_jobs_total": ranked_jobs_total,
        "debug_records_captured": len(debug_records),
        "attempted_generation_jobs_total": attempted_generation_jobs_total,
        "non_attempted_ranked_jobs_total": non_attempted_ranked_jobs_total,
        "omission_reason_counts": omission_reason_counts,
        "snapshot_complete": len(debug_records) == ranked_jobs_total,
        "debug_records": debug_records,
    }
    if isinstance(summary.get("agentic_live_trace"), dict):
        payload["agentic_live_trace"] = dict(summary["agentic_live_trace"])
    if isinstance(summary.get("cv_analysis_trace"), dict):
        payload["cv_analysis_trace"] = dict(summary["cv_analysis_trace"])
    return json.dumps(payload, ensure_ascii=False)


def _build_stage_transition_artifacts_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
    run_status: RunStatus = RunStatus.SUCCEEDED,
    degradation_reason: str | None = None,
) -> str:
    stage_artifacts = dict(summary.get("stage_transition_artifacts") or {})
    snapshot_complete = bool(stage_artifacts) and run_status == RunStatus.SUCCEEDED
    resolved_reason = (
        str(degradation_reason or "").strip()
        or ("partial_snapshot_non_terminal_success" if run_status != RunStatus.SUCCEEDED else "")
    )
    payload = {
        "run_id": run_id,
        "status": run_status.value,
        "artifact_schema_version": "stage_transition_artifacts_run_v1",
        "created_at": finished_at.isoformat(),
        "snapshot_complete": snapshot_complete,
        "degradation_reason": resolved_reason,
        "artifacts": stage_artifacts,
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_manual_checkpoint_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    created_at: datetime.datetime,
    replay_context: dict[str, Any],
) -> str:
    payload = {
        "run_id": run_id,
        "checkpoint_schema_version": "manual_checkpoint_v1",
        "created_at": created_at.isoformat(),
        "paused_after_stage": summary.get("paused_after_stage"),
        "next_stage": summary.get("next_stage"),
        "completed_stages": list(summary.get("completed_stages") or []),
        "checkpoint_payload": summary.get("checkpoint_payload") or {},
        "replay_context": {
            "replay_mode": str(replay_context.get("replay_mode") or "strict"),
            "replay_source_run_id": str(replay_context.get("replay_source_run_id") or run_id),
            "policy_registry_version": str(replay_context.get("policy_registry_version") or "policy_registry.v1"),
            "policy_envelope_signature": str(replay_context.get("policy_envelope_signature") or ""),
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_settings_used_payload(
    *,
    run_id: str,
    run_record: Any,
    effective_config: dict[str, Any] | None,
    config_path: str,
    finished_at: datetime.datetime,
    replay_context: dict[str, Any],
) -> str:
    effective_settings = dict(effective_config or {})
    sqlite_mode = resolve_backend_runtime().backend_type == "sqlite"
    if sqlite_mode:
        effective_settings.pop("service_account_key", None)
    compatibility_projection = {
        key: effective_settings.pop(key)
        for key in list(effective_settings.keys())
        if key in _SETTINGS_COMPATIBILITY_KEYS
    }
    if sqlite_mode and isinstance(compatibility_projection, dict):
        compatibility_projection.pop("service_account_key", None)
    payload = {
        "run_id": run_id,
        "settings_schema_version": "settings_used_v2",
        "created_at": finished_at.isoformat(),
        "late_stage_mode": _build_late_stage_mode_payload(
            summary={},
            effective_config=effective_config,
        ),
        "effective_settings": effective_settings,
        "sources": {
            "config_path": str(config_path or getattr(run_record, "config_path", "") or ""),
            "effective_settings_snapshot_present": effective_config is not None,
            "jobs_input_source": getattr(run_record, "jobs_input_source", None),
            "candidate_profile_source": getattr(run_record, "candidate_profile_source", None),
            "skill_synonyms_runtime": (
                dict((effective_config or {}).get("skill_synonyms_runtime") or {})
                if isinstance((effective_config or {}).get("skill_synonyms_runtime"), dict)
                else None
            ),
            "prompts_runtime": (
                dict((effective_config or {}).get("prompts_runtime") or {})
                if isinstance((effective_config or {}).get("prompts_runtime"), dict)
                else None
            ),
        },
        "data_plane": data_plane_contract_payload(effective_config),
        "replay_context": {
            "replay_mode": str(replay_context.get("replay_mode") or "strict"),
            "replay_source_run_id": str(replay_context.get("replay_source_run_id") or run_id),
            "policy_registry_version": str(replay_context.get("policy_registry_version") or "policy_registry.v1"),
            "policy_envelope_signature": str(replay_context.get("policy_envelope_signature") or ""),
        },
    }
    if sqlite_mode:
        data_plane = dict(payload.get("data_plane") or {})
        data_plane["state_backend"] = "sqlite"
        if str(data_plane.get("artifact_backend") or "").strip().lower() in {"", "bigquery_json"}:
            data_plane["artifact_backend"] = "sqlite_json"
        payload["data_plane"] = data_plane
    if compatibility_projection:
        payload["compatibility_projection"] = compatibility_projection
    return json.dumps(payload, ensure_ascii=False)


def _build_mapping_suggestions_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    created_at: datetime.datetime,
) -> str:
    payload = {
        "run_id": run_id,
        "mapping_suggestions_schema_version": "mapping_suggestions_v1",
        "created_at": created_at.isoformat(),
        "suggestions": list(summary.get("mapping_suggestions") or []),
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_synonym_proposals_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    created_at: datetime.datetime,
    existing_payload_json: str | None = None,
    global_synonyms: dict[str, str] | None = None,
) -> str:
    existing_proposals_by_id: dict[str, dict[str, Any]] = {}
    if existing_payload_json:
        try:
            existing_payload = json.loads(existing_payload_json)
        except (TypeError, json.JSONDecodeError):
            existing_payload = None
        if isinstance(existing_payload, dict):
            for existing_proposal in list(existing_payload.get("proposals") or []):
                if not isinstance(existing_proposal, dict):
                    continue
                proposal_id = str(existing_proposal.get("proposal_id") or "").strip()
                if proposal_id:
                    existing_proposals_by_id[proposal_id] = existing_proposal

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for suggestion in list(summary.get("mapping_suggestions") or []):
        if not isinstance(suggestion, dict):
            continue
        field = str(suggestion.get("field") or "skill").strip().lower() or "skill"
        alias = str(suggestion.get("alias") or "").strip().lower()
        canonical = str(suggestion.get("canonical") or "").strip().lower()
        if not alias or not canonical:
            continue
        bucket = grouped.setdefault(
            (field, alias),
            {
                "field": field,
                "alias": alias,
                "candidate_canonicals": {},
                "must_have_skills": set(),
                "job_refs": [],
                "occurrence_count": 0,
                "confidence_sum": 0.0,
            },
        )
        bucket["occurrence_count"] += 1
        confidence = float(suggestion.get("confidence") or 0.0)
        bucket["confidence_sum"] += confidence
        bucket["candidate_canonicals"][canonical] = (
            bucket["candidate_canonicals"].get(canonical, 0) + 1
        )
        must_have_skill = str(suggestion.get("must_have_skill") or "").strip().lower()
        if must_have_skill:
            bucket["must_have_skills"].add(must_have_skill)
        job_url = str(suggestion.get("job_url") or "").strip()
        if job_url and len(bucket["job_refs"]) < 5:
            bucket["job_refs"].append(
                {
                    "job_url": job_url,
                    "job_title": str(suggestion.get("job_title") or "").strip(),
                    "confidence": confidence,
                }
            )

    proposals: list[dict[str, Any]] = []
    normalized_global_synonyms: dict[str, str] = {}
    if isinstance(global_synonyms, dict):
        normalized_global_synonyms = {
            str(alias).strip().lower(): str(canonical).strip().lower()
            for alias, canonical in global_synonyms.items()
            if str(alias).strip() and str(canonical).strip()
        }
    suppressed_as_already_global_count = 0
    suppressed_count_by_field: dict[str, int] = {}
    suppressed_reason_counts_by_field: dict[str, dict[str, int]] = {}
    suppressed_examples: list[dict[str, str]] = []
    for (_field_alias_key, bucket) in grouped.items():
        field = str(bucket.get("field") or "skill")
        alias = str(bucket.get("alias") or "")
        ranked_canonicals = sorted(
            bucket["candidate_canonicals"].items(),
            key=lambda item: (-int(item[1]), item[0]),
        )
        candidate_canonicals = [canonical for canonical, _count in ranked_canonicals]
        primary_canonical = candidate_canonicals[0]
        has_conflict = len(candidate_canonicals) > 1
        proposal_family = "conflict_bundle" if has_conflict else "alias_to_canonical_mapping"
        occurrence_count = int(bucket["occurrence_count"])
        avg_confidence = (
            float(bucket["confidence_sum"]) / occurrence_count if occurrence_count else 0.0
        )
        if field in {"domain", "role_family"} and occurrence_count < _NON_SKILL_MIN_SUPPORT_FOR_PROPOSAL:
            suppressed_count_by_field[field] = suppressed_count_by_field.get(field, 0) + 1
            reason_bucket = suppressed_reason_counts_by_field.setdefault(field, {})
            reason_bucket["insufficient_non_skill_support"] = (
                reason_bucket.get("insufficient_non_skill_support", 0) + 1
            )
            if len(suppressed_examples) < 10:
                suppressed_examples.append(
                    {
                        "field": field,
                        "alias": alias,
                        "canonical": primary_canonical,
                    }
                )
            continue
        identity_seed = f"{run_id}:{field}:{alias}:{'|'.join(candidate_canonicals)}:{proposal_family}"
        proposal_id = f"synprop-{hashlib.sha1(identity_seed.encode('utf-8')).hexdigest()[:12]}"
        existing_proposal = existing_proposals_by_id.get(proposal_id) or {}
        global_canonical = normalized_global_synonyms.get(alias) if field == "skill" else None
        if global_canonical and global_canonical == primary_canonical:
            suppressed_as_already_global_count += 1
            suppressed_count_by_field[field] = suppressed_count_by_field.get(field, 0) + 1
            reason_bucket = suppressed_reason_counts_by_field.setdefault(field, {})
            reason_bucket["already_global_exact"] = reason_bucket.get("already_global_exact", 0) + 1
            if len(suppressed_examples) < 10:
                suppressed_examples.append({"field": field, "alias": alias, "canonical": primary_canonical})
            continue
        proposals.append(
            {
                "proposal_id": proposal_id,
                "run_id": run_id,
                "field": field,
                "alias": alias,
                "canonical": primary_canonical,
                "candidate_aliases": [alias],
                "candidate_canonicals": candidate_canonicals,
                "confidence": round(avg_confidence, 6),
                "rationale": {
                    "kind": "alias_conflict" if has_conflict else "repeated_alias_mapping",
                    "occurrence_count": occurrence_count,
                    "distinct_canonical_count": len(candidate_canonicals),
                },
                "evidence_summary": {
                    "occurrence_count": occurrence_count,
                    "average_confidence": round(avg_confidence, 6),
                    "must_have_skills": sorted(bucket["must_have_skills"]),
                    "sample_job_refs": list(bucket["job_refs"]),
                },
                "conflict_summary": {
                    "has_conflict": has_conflict,
                    "conflicting_canonicals": candidate_canonicals[1:],
                },
                "proposal_status": str(existing_proposal.get("proposal_status") or "proposed_unreviewed"),
                "proposal_scope": "run_scoped_overlay_candidate",
                "proposal_family": proposal_family,
                "source_artifact_refs": {
                    "run_id": run_id,
                    "artifact_type": "mapping_suggestions",
                },
                "review_history": list(existing_proposal.get("review_history") or []),
            }
        )
    proposals.sort(key=lambda item: (-float(item["confidence"]), str(item["alias"])))
    payload = {
        "run_id": run_id,
        "synonym_proposals_schema_version": "synonym_proposals_v1",
        "created_at": created_at.isoformat(),
        "proposal_generation_status": "generated" if proposals else "not_applicable",
        "persistence_status": "persisted" if proposals else "not_applicable",
        "proposals": proposals,
    }
    payload["synonym_proposals_trace"] = _build_synonym_proposals_trace_payload(
        run_id=run_id,
        created_at=created_at,
        proposal_generation_status=str(payload["proposal_generation_status"] or ""),
        persistence_status=str(payload["persistence_status"] or ""),
        proposals=proposals,
        suppression_summary={
            "suppressed_as_already_global_count": suppressed_as_already_global_count,
            "generated_for_review_count": len(proposals),
            "suppressed_count_by_field": suppressed_count_by_field,
            "suppressed_reason_counts_by_field": suppressed_reason_counts_by_field,
            "suppressed_examples": suppressed_examples,
            "suppression_source": (
                "run_effective_skill_synonyms"
                if normalized_global_synonyms
                else "none"
            ),
        },
    )
    return json.dumps(payload, ensure_ascii=False)

def _effective_skill_synonyms_from_run_record(run_record: Any) -> dict[str, str]:
    if run_record is None:
        return {}
    raw_payload = getattr(run_record, "effective_settings_json", None)
    if not raw_payload:
        return {}
    try:
        settings_payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(settings_payload, dict):
        return {}
    raw_synonyms = settings_payload.get("skill_synonyms")
    if not isinstance(raw_synonyms, dict):
        return {}
    return {
        str(alias).strip().lower(): str(canonical).strip().lower()
        for alias, canonical in raw_synonyms.items()
        if str(alias).strip() and str(canonical).strip()
    }

def _synonym_propose_enabled_from_run_record(run_record: Any) -> bool:
    if run_record is None:
        return True
    raw_payload = getattr(run_record, "effective_settings_json", None)
    if not raw_payload:
        return True
    try:
        settings_payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        return True
    if not isinstance(settings_payload, dict):
        return True
    block = dict(settings_payload.get("synonym_management") or {})
    return bool(block.get("propose_enabled", True))


def _build_synonym_proposals_trace_payload(
    *,
    run_id: str,
    created_at: datetime.datetime,
    proposal_generation_status: str,
    persistence_status: str,
    proposals: list[dict[str, Any]],
    suppression_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if proposal_generation_status == "not_applicable":
        return {
            "run_id": run_id,
            "trace_schema_version": "agentic_step_trace_run_v1",
            "trace_family": "agentic_step_trace",
            "step_id": "synonym_proposals",
            "created_at": created_at.isoformat(),
            "trace_status": "not_applicable",
            "trace_summary": {
                "records_total": 0,
                "present_records": 0,
                "proposal_count": 0,
                "suppressed_as_already_global_count": int(
                    (suppression_summary or {}).get("suppressed_as_already_global_count") or 0
                ),
                "generated_for_review_count": int(
                    (suppression_summary or {}).get("generated_for_review_count") or 0
                ),
                "suppression_source": str((suppression_summary or {}).get("suppression_source") or "none"),
                "suppressed_count_by_field": dict((suppression_summary or {}).get("suppressed_count_by_field") or {}),
                "suppressed_reason_counts_by_field": dict((suppression_summary or {}).get("suppressed_reason_counts_by_field") or {}),
            },
            "records": [],
            "degradation": {},
            "artifact_refs": {},
            "suppression_examples": list((suppression_summary or {}).get("suppressed_examples") or []),
        }

    trace_records: list[dict[str, Any]] = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        proposal_id = str(proposal.get("proposal_id") or "").strip()
        alias = str(proposal.get("alias") or "").strip()
        trace_records.append(
            {
                "trace_schema_version": "agentic_step_trace_record_v1",
                "trace_family": "agentic_step_trace",
                "step_id": "synonym_proposals",
                "trace_status": "completed",
                "record_id": proposal_id or alias,
                "scope_type": "alias",
                "scope_key": alias,
                "status": str(proposal.get("proposal_status") or "proposed_unreviewed"),
                "runtime_provenance": {
                    "runtime_path": "fitcv_synonym_proposal_builder_builtin",
                    "provider": "fitcv_builtin",
                    "mode_source": "mapping_suggestions_to_synonym_proposals",
                },
                "attempts": [
                    {
                        "attempt_index": 1,
                        "attempt_type": "proposal_generation",
                        "attempt_status": "completed",
                        "provider_status": "completed",
                    }
                ],
                "input_summary": {
                    "alias": alias,
                    "candidate_canonicals_count": len(list(proposal.get("candidate_canonicals") or [])),
                },
                "output_summary": {
                    "proposal_family": str(proposal.get("proposal_family") or ""),
                    "proposal_scope": str(proposal.get("proposal_scope") or ""),
                    "confidence": float(proposal.get("confidence") or 0.0),
                },
                "validation_summary": {"status": "not_run"},
                "repair_summary": {"repair_attempted": False, "repair_attempts": 0},
                "error_summary": None,
            }
        )

    trace_status = "completed"
    degradation: dict[str, Any] = {}
    if persistence_status == "bundle_only_degraded":
        trace_status = "degraded"
        degradation = {"reason": "synonym_proposals_bundle_only_degraded"}
    elif persistence_status == "failed":
        trace_status = "degraded"
        degradation = {"reason": "synonym_proposals_persistence_failed"}
    elif not trace_records:
        trace_status = "partial"
        degradation = {"reason": "proposal_generation_without_trace_records"}

    return {
        "run_id": run_id,
        "trace_schema_version": "agentic_step_trace_run_v1",
        "trace_family": "agentic_step_trace",
        "step_id": "synonym_proposals",
        "created_at": created_at.isoformat(),
        "trace_status": trace_status,
        "trace_summary": {
            "records_total": len(proposals),
            "present_records": len(trace_records),
            "proposal_count": len(proposals),
            "suppressed_as_already_global_count": int(
                (suppression_summary or {}).get("suppressed_as_already_global_count") or 0
            ),
            "generated_for_review_count": int(
                (suppression_summary or {}).get("generated_for_review_count") or len(proposals)
            ),
            "suppression_source": str((suppression_summary or {}).get("suppression_source") or "none"),
            "suppressed_count_by_field": dict((suppression_summary or {}).get("suppressed_count_by_field") or {}),
            "suppressed_reason_counts_by_field": dict((suppression_summary or {}).get("suppressed_reason_counts_by_field") or {}),
        },
        "records": trace_records,
        "degradation": degradation,
        "artifact_refs": {
            "proposal_artifact": "synonym-proposals.json",
            "stage_artifact": "enrich.json",
        },
        "suppression_examples": list((suppression_summary or {}).get("suppressed_examples") or []),
    }


def _summary_has_reached_stage(summary: dict[str, Any], stage_id: str) -> bool:
    normalized_stage_id = str(stage_id or "").strip()
    if not normalized_stage_id:
        return False
    completed_stages = [
        str(item).strip()
        for item in list(summary.get("completed_stages") or [])
        if str(item).strip()
    ]
    if normalized_stage_id in completed_stages:
        return True
    if str(summary.get("last_completed_stage") or "").strip() == normalized_stage_id:
        return True
    stage_transition_artifacts = summary.get("stage_transition_artifacts")
    if not isinstance(stage_transition_artifacts, dict):
        return False
    artifacts = stage_transition_artifacts.get("artifacts")
    stage_root = artifacts if isinstance(artifacts, dict) else stage_transition_artifacts
    if not isinstance(stage_root, dict):
        return False
    stages = stage_root.get("stages")
    if not isinstance(stages, dict):
        return False
    stage_block = stages.get(normalized_stage_id)
    if not isinstance(stage_block, dict):
        return False
    return str(stage_block.get("status") or "").strip().lower() not in {"", "not_reached"}

def _append_synonym_suppression_summary_event(
    *,
    run_id: str,
    synonym_payload_json: str,
    bq: Any,
    project: str,
    dataset: str,
) -> None:
    try:
        payload = json.loads(synonym_payload_json)
    except (TypeError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    trace_payload = payload.get("synonym_proposals_trace")
    if not isinstance(trace_payload, dict):
        return
    trace_summary = trace_payload.get("trace_summary")
    if not isinstance(trace_summary, dict):
        return
    suppressed_count = int(trace_summary.get("suppressed_as_already_global_count") or 0)
    if suppressed_count <= 0:
        return
    suppression_payload = {
        "suppressed_as_already_global_count": suppressed_count,
        "generated_for_review_count": int(trace_summary.get("generated_for_review_count") or 0),
        "suppression_source": str(trace_summary.get("suppression_source") or "none"),
        "suppression_examples": list(trace_payload.get("suppression_examples") or []),
    }
    suppression_fingerprint = hashlib.sha1(
        json.dumps(suppression_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    try:
        prior_events = get_events(run_id, bq, project=project, dataset=dataset)
    except Exception:
        prior_events = []
    for prior in reversed(prior_events):
        if str(getattr(prior, "stage", "") or "") != "synonym_proposal_suppression_summary":
            continue
        try:
            prior_payload = json.loads(str(getattr(prior, "payload_json", "") or "{}"))
        except (TypeError, json.JSONDecodeError):
            prior_payload = {}
        if str(prior_payload.get("suppression_fingerprint") or "") == suppression_fingerprint:
            return
        break
    append_event(
        RunEvent(
            run_id=run_id,
            event_id=str(uuid.uuid4()),
            stage="synonym_proposal_suppression_summary",
            level="info",
            message=(
                "Suppressed synonym proposals already covered by global map: "
                f"{suppressed_count}"
            ),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            payload_json=json.dumps(
                {**suppression_payload, "suppression_fingerprint": suppression_fingerprint},
                ensure_ascii=False,
            ),
        ),
        bq,
        project=project,
        dataset=dataset,
    )


def _persist_shared_progress_snapshot(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    snapshot_at: datetime.datetime,
    bq: Any,
    project: str,
    dataset: str,
    run_status: RunStatus,
) -> None:
    update_run_status(
        run_id,
        run_status,
        bq,
        project=project,
        dataset=dataset,
        summary=summary,
    )
    update_run_progress(
        run_id,
        bq,
        project=project,
        dataset=dataset,
        last_completed_stage=str(summary.get("last_completed_stage") or "").strip() or None,
        completed_stages=list(summary.get("completed_stages") or []),
    )
    update_run_stage_transition_artifacts(
        run_id,
        _build_stage_transition_artifacts_payload(
            run_id=run_id,
            summary=summary,
            finished_at=snapshot_at,
            run_status=run_status,
            degradation_reason="partial_snapshot",
        ),
        bq,
        project=project,
        dataset=dataset,
    )
    if _summary_has_reached_stage(summary, "enrich"):
        update_run_mapping_suggestions(
            run_id,
            _build_mapping_suggestions_payload(
                run_id=run_id,
                summary=summary,
                created_at=snapshot_at,
            ),
            bq,
            project=project,
            dataset=dataset,
        )
        if _synonym_propose_enabled_from_run_record(run_record):
            synonym_payload_json = _build_synonym_proposals_payload(
                run_id=run_id,
                summary=summary,
                created_at=snapshot_at,
                existing_payload_json=getattr(run_record, "synonym_proposals_json", None),
                global_synonyms=_effective_skill_synonyms_from_run_record(run_record),
            )
            synonym_status = update_run_synonym_proposals(
                run_id,
                synonym_payload_json,
                bq,
                project=project,
                dataset=dataset,
            )
            _append_synonym_suppression_summary_event(
                run_id=run_id,
                synonym_payload_json=synonym_payload_json,
                bq=bq,
                project=project,
                dataset=dataset,
            )
            _append_degraded_snapshot_persistence_warning(
                run_id=run_id,
                snapshot_name="synonym_proposals",
                persistence_status=synonym_status,
                bq=bq,
                project=project,
                dataset=dataset,
            )


def execute_pipeline_run(run_id: str, jobs_path: str, config_path: str) -> None:
    runtime = resolve_backend_runtime()
    project = runtime.project
    dataset = runtime.dataset
    bq = _get_bq() if runtime.backend_type == "bigquery" else None

    # Import here to avoid circular deps at module load time
    from fitcv_cp.reporter import PipelineReporter

    summary: dict[str, Any] = {}
    run_record: Any | None = None

    try:
        current_run_record = get_run(run_id, bq, project=project, dataset=dataset)
        # ── Step 1: Mark running ──────────────────────────────────────────────
        update_run_status(
            run_id, RunStatus.RUNNING, bq, project=project, dataset=dataset,
            started_at=(
                datetime.datetime.now(datetime.timezone.utc)
                if current_run_record is None or getattr(current_run_record, "started_at", None) is None
                else None
            ),
        )

        # ── Step 2: Read current row (reads cancel_requested_at + config snapshot)
        run_record = get_run(run_id, bq, project=project, dataset=dataset)
        effective_config: dict[str, Any] | None = None
        if run_record and run_record.effective_settings_json:
            try:
                effective_config = json.loads(run_record.effective_settings_json)
            except Exception as exc:
                logger.warning("[run_id=%s] Failed to parse effective_settings_json: %s", run_id, exc)
        effective_config = _normalize_runtime_service_account_key(effective_config, run_id=run_id)
        replay_context = _resolve_run_replay_context(
            effective_config=effective_config,
            run_id=run_id,
        )
        run_mode = str(getattr(run_record, "run_mode", "run_all") or "run_all")
        next_stage = getattr(run_record, "next_stage", None) or "normalize"
        checkpoint_payload: dict[str, Any] | None = None
        checkpoint_payload_json = getattr(run_record, "checkpoint_payload_json", None)
        if checkpoint_payload_json:
            try:
                checkpoint_container = json.loads(checkpoint_payload_json)
                checkpoint_payload_candidate = checkpoint_container.get("checkpoint_payload")
                if isinstance(checkpoint_payload_candidate, dict):
                    checkpoint_payload = checkpoint_payload_candidate
            except Exception as exc:
                logger.warning("[run_id=%s] Failed to parse checkpoint payload: %s", run_id, exc)

        # ── Step 3: Early-exit if cancellation already requested ──────────────
        if run_record and run_record.cancel_requested_at is not None:
            logger.info("[run_id=%s] Cancellation already requested — exiting early", run_id)
            update_run_status(
                run_id, RunStatus.CANCELLED, bq, project=project, dataset=dataset,
                finished_at=datetime.datetime.now(datetime.timezone.utc),
            )
            append_event(
                _run_cancelled_event(run_id, "Run cancelled before pipeline execution started"),
                bq, project=project, dataset=dataset,
            )
            return

        # ── Step 4: Run pipeline with cooperative cancellation check ──────────
        reporter = PipelineReporter(run_id=run_id, bq=bq, project=project, dataset=dataset)

        def _cancellation_check() -> bool:
            """Lightweight re-read to check if cancel was requested mid-flight."""
            current = get_run(run_id, bq, project=project, dataset=dataset)
            return current is not None and current.cancel_requested_at is not None

        late_stage_reuse_snapshots = _collect_late_stage_reuse_snapshots(
            current_run_id=run_id,
            bq=bq,
            project=project,
            dataset=dataset,
        )

        def _stage_progress_callback(progress_summary: dict[str, Any]) -> None:
            if run_mode != "run_all":
                return
            snapshot_time = datetime.datetime.now(datetime.timezone.utc)
            try:
                _persist_shared_progress_snapshot(
                    run_id=run_id,
                    run_record=run_record,
                    summary=progress_summary,
                    snapshot_at=snapshot_time,
                    bq=bq,
                    project=project,
                    dataset=dataset,
                    run_status=RunStatus.RUNNING,
                )
            except Exception as exc:
                logger.warning(
                    "[run_id=%s] Failed to persist run-all progress snapshot after %s: %s",
                    run_id,
                    progress_summary.get("last_completed_stage"),
                    exc,
                )
                try:
                    append_event(
                        _snapshot_persist_failed_event(run_id, "stage_progress", str(exc)),
                        bq,
                        project=project,
                        dataset=dataset,
                    )
                except Exception as inner:
                    logger.warning(
                        "[run_id=%s] Failed to append stage progress persistence warning event: %s",
                        run_id,
                        inner,
                    )

        summary = run_pipeline(
            jobs_path=jobs_path,
            config_path=config_path,
            reporter=reporter,
            config=effective_config,
            run_id=run_id,
            cancellation_check=_cancellation_check,
            start_stage=next_stage if run_mode == "manual_staged" else None,
            stop_after_stage=next_stage if run_mode == "manual_staged" else None,
            checkpoint_payload=checkpoint_payload,
            reuse_snapshots=late_stage_reuse_snapshots,
            stage_progress_callback=_stage_progress_callback if run_mode == "run_all" else None,
        )

        paused_after_stage = str(summary.get("paused_after_stage") or "").strip() or None
        if paused_after_stage is not None:
            checkpoint_time = datetime.datetime.now(datetime.timezone.utc)
            update_run_status(
                run_id,
                RunStatus.AWAITING_CONTINUE,
                bq,
                project=project,
                dataset=dataset,
                summary=summary,
            )
            update_run_checkpoint(
                run_id,
                bq,
                project=project,
                dataset=dataset,
                checkpoint_status="awaiting_continue",
                next_stage=summary.get("next_stage"),
                last_completed_stage=paused_after_stage,
                completed_stages=list(summary.get("completed_stages") or []),
                checkpoint_payload_json=_build_manual_checkpoint_payload(
                    run_id=run_id,
                    summary=summary,
                    created_at=checkpoint_time,
                    replay_context=replay_context,
                ),
            )
            try:
                update_run_stage_transition_artifacts(
                    run_id,
                    _build_stage_transition_artifacts_payload(
                        run_id=run_id,
                        summary=summary,
                        finished_at=checkpoint_time,
                        run_status=RunStatus.AWAITING_CONTINUE,
                        degradation_reason="checkpoint_partial_snapshot",
                    ),
                    bq,
                    project=project,
                    dataset=dataset,
                )
            except Exception as exc:
                logger.warning(
                    "[run_id=%s] Failed to persist stage transition artifacts snapshot at checkpoint: %s",
                    run_id,
                    exc,
                )
            if _summary_has_reached_stage(summary, "enrich"):
                try:
                    update_run_mapping_suggestions(
                        run_id,
                        _build_mapping_suggestions_payload(
                            run_id=run_id,
                            summary=summary,
                            created_at=checkpoint_time,
                        ),
                        bq,
                        project=project,
                        dataset=dataset,
                    )
                except Exception as exc:
                    logger.warning(
                        "[run_id=%s] Failed to persist mapping suggestions snapshot at checkpoint: %s",
                        run_id,
                        exc,
                    )
                    try:
                        append_event(
                            _snapshot_persist_failed_event(run_id, "mapping_suggestions", str(exc)),
                            bq,
                            project=project,
                            dataset=dataset,
                        )
                    except Exception as inner:
                        logger.warning(
                            "[run_id=%s] Failed to append mapping suggestions persistence warning event: %s",
                            run_id,
                            inner,
                        )
                if _synonym_propose_enabled_from_run_record(run_record):
                    try:
                        synonym_payload_json = _build_synonym_proposals_payload(
                            run_id=run_id,
                            summary=summary,
                            created_at=checkpoint_time,
                            existing_payload_json=getattr(run_record, "synonym_proposals_json", None),
                            global_synonyms=_effective_skill_synonyms_from_run_record(run_record),
                        )
                        synonym_status = update_run_synonym_proposals(
                            run_id,
                            synonym_payload_json,
                            bq,
                            project=project,
                            dataset=dataset,
                        )
                        _append_synonym_suppression_summary_event(
                            run_id=run_id,
                            synonym_payload_json=synonym_payload_json,
                            bq=bq,
                            project=project,
                            dataset=dataset,
                        )
                        _append_degraded_snapshot_persistence_warning(
                            run_id=run_id,
                            snapshot_name="synonym_proposals",
                            persistence_status=synonym_status,
                            bq=bq,
                            project=project,
                            dataset=dataset,
                        )
                    except Exception as exc:
                        logger.warning(
                            "[run_id=%s] Failed to persist synonym proposals snapshot at checkpoint: %s",
                            run_id,
                            exc,
                        )
                        try:
                            append_event(
                                _snapshot_persist_failed_event(run_id, "synonym_proposals", str(exc)),
                                bq,
                                project=project,
                                dataset=dataset,
                            )
                        except Exception as inner:
                            logger.warning(
                                "[run_id=%s] Failed to append synonym proposals persistence warning event: %s",
                                run_id,
                                inner,
                            )
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="stage_checkpoint",
                    level="info",
                    message=f"Paused after {paused_after_stage}; next stage: {summary.get('next_stage') or 'complete'}",
                    created_at=checkpoint_time,
                ),
                bq,
                project=project,
                dataset=dataset,
            )
            return

        # ── Step 5: Terminalize or park for review ───────────────────────────
        cv_debug_records = [
            item for item in list(summary.get("cv_generation_debug_records") or [])
            if isinstance(item, dict)
        ]
        pending_review_required = sum(
            1
            for record in cv_debug_records
            if str(record.get("status") or "").strip() == "review_required"
        )
        finished_at = datetime.datetime.now(datetime.timezone.utc) if pending_review_required == 0 else None
        terminal_status = RunStatus.SUCCEEDED if pending_review_required == 0 else RunStatus.AWAITING_CONTINUE
        update_run_status(
            run_id,
            terminal_status,
            bq,
            project=project,
            dataset=dataset,
            finished_at=finished_at,
            summary=summary,
        )
        completed_stages = [
            "normalize",
            "enrich",
            "rule_filter",
            "shortlist",
            "ranking",
            "cv_analysis",
            "cv_generation",
        ]
        if pending_review_required > 0:
            update_run_checkpoint(
                run_id,
                bq,
                project=project,
                dataset=dataset,
                checkpoint_status="awaiting_review",
                next_stage=None,
                last_completed_stage="cv_generation",
                completed_stages=completed_stages,
                checkpoint_payload_json=None,
            )
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="cv_review_required",
                    level="warning",
                    message=f"Run paused: {pending_review_required} review-required CV item(s) pending operator action.",
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        elif run_mode == "manual_staged":
            update_run_checkpoint(
                run_id,
                bq,
                project=project,
                dataset=dataset,
                checkpoint_status="completed",
                next_stage=None,
                last_completed_stage="cv_generation",
                completed_stages=completed_stages,
                checkpoint_payload_json=None,
            )
        else:
            update_run_progress(
                run_id,
                bq,
                project=project,
                dataset=dataset,
                last_completed_stage="cv_generation",
                completed_stages=completed_stages,
            )
        export_results = list(summary.get("export_results") or [])
        try:
                update_run_results_export(
                    run_id,
                    _build_results_export_payload(
                        run_id=run_id,
                        run_record=run_record,
                        effective_config=effective_config,
                        summary=summary,
                        export_results=export_results,
                        finished_at=finished_at,
                        replay_context=replay_context,
                    ),
                    bq,
                    project=project,
                    dataset=dataset,
            )
        except Exception as exc:
            logger.warning("[run_id=%s] Failed to persist results export snapshot: %s", run_id, exc)
        try:
            update_run_cv_generation_debug(
                run_id,
                _build_cv_generation_debug_payload(
                    run_id=run_id,
                    run_record=run_record,
                    summary=summary,
                    finished_at=finished_at or datetime.datetime.now(datetime.timezone.utc),
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as exc:
            logger.warning("[run_id=%s] Failed to persist CV generation debug snapshot: %s", run_id, exc)
        try:
            update_run_stage_transition_artifacts(
                run_id,
                _build_stage_transition_artifacts_payload(
                    run_id=run_id,
                    summary=summary,
                    finished_at=finished_at,
                    run_status=RunStatus.SUCCEEDED,
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as exc:
            logger.warning("[run_id=%s] Failed to persist stage transition artifacts snapshot: %s", run_id, exc)
        try:
            update_run_settings_used(
                run_id,
                _build_settings_used_payload(
                    run_id=run_id,
                    run_record=run_record,
                    effective_config=effective_config,
                    config_path=config_path,
                    finished_at=finished_at,
                    replay_context=replay_context,
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as exc:
            logger.warning("[run_id=%s] Failed to persist settings-used snapshot: %s", run_id, exc)
        if _summary_has_reached_stage(summary, "enrich"):
            snapshot_created_at = finished_at or datetime.datetime.now(datetime.timezone.utc)
            try:
                update_run_mapping_suggestions(
                    run_id,
                    _build_mapping_suggestions_payload(
                        run_id=run_id,
                        summary=summary,
                        created_at=snapshot_created_at,
                    ),
                    bq,
                    project=project,
                    dataset=dataset,
                )
            except Exception as exc:
                logger.warning("[run_id=%s] Failed to persist mapping suggestions snapshot: %s", run_id, exc)
                try:
                    append_event(
                        _snapshot_persist_failed_event(run_id, "mapping_suggestions", str(exc)),
                        bq,
                        project=project,
                        dataset=dataset,
                    )
                except Exception as inner:
                    logger.warning(
                        "[run_id=%s] Failed to append mapping suggestions persistence warning event: %s",
                        run_id,
                        inner,
                    )
            if _synonym_propose_enabled_from_run_record(run_record):
                try:
                    synonym_payload_json = _build_synonym_proposals_payload(
                        run_id=run_id,
                        summary=summary,
                        created_at=snapshot_created_at,
                        existing_payload_json=getattr(run_record, "synonym_proposals_json", None),
                        global_synonyms=_effective_skill_synonyms_from_run_record(run_record),
                    )
                    synonym_status = update_run_synonym_proposals(
                        run_id,
                        synonym_payload_json,
                        bq,
                        project=project,
                        dataset=dataset,
                    )
                    _append_synonym_suppression_summary_event(
                        run_id=run_id,
                        synonym_payload_json=synonym_payload_json,
                        bq=bq,
                        project=project,
                        dataset=dataset,
                    )
                    _append_degraded_snapshot_persistence_warning(
                        run_id=run_id,
                        snapshot_name="synonym_proposals",
                        persistence_status=synonym_status,
                        bq=bq,
                        project=project,
                        dataset=dataset,
                    )
                except Exception as exc:
                    logger.warning("[run_id=%s] Failed to persist synonym proposals snapshot: %s", run_id, exc)
                    try:
                        append_event(
                            _snapshot_persist_failed_event(run_id, "synonym_proposals", str(exc)),
                            bq,
                            project=project,
                            dataset=dataset,
                        )
                    except Exception as inner:
                        logger.warning(
                            "[run_id=%s] Failed to append synonym proposals persistence warning event: %s",
                            run_id,
                            inner,
                        )

    except PipelineCancelled as exc:
        # ── Step 5 (alt): Pipeline was cancelled at a checkpoint ──────────────
        logger.info("[run_id=%s] Pipeline cancelled at checkpoint: %s", run_id, exc)
        cancelled_at = datetime.datetime.now(datetime.timezone.utc)
        update_run_status(
            run_id, RunStatus.CANCELLED, bq, project=project, dataset=dataset,
            finished_at=cancelled_at,
            summary=summary if isinstance(summary, dict) else None,
        )
        if isinstance(summary, dict) and summary:
            try:
                _persist_shared_progress_snapshot(
                    run_id=run_id,
                    run_record=run_record,
                    summary=summary,
                    snapshot_at=cancelled_at,
                    bq=bq,
                    project=project,
                    dataset=dataset,
                    run_status=RunStatus.CANCELLED,
                )
            except Exception as persist_exc:
                logger.warning(
                    "[run_id=%s] Failed to persist partial progress snapshot for cancelled run: %s",
                    run_id,
                    persist_exc,
                )
        try:
            append_event(
                _run_cancelled_event(run_id, f"Run cancelled at pipeline checkpoint: {exc}"),
                bq, project=project, dataset=dataset,
            )
        except Exception as inner:
            logger.warning("[run_id=%s] Failed to write cancellation event: %s", run_id, inner)

    except Exception as exc:
        # ── Step 7: Unexpected pipeline failure ───────────────────────────────
        logger.exception("[run_id=%s] Pipeline failed: %s", run_id, exc)
        failed_at = datetime.datetime.now(datetime.timezone.utc)
        update_run_status(
            run_id, RunStatus.FAILED, bq, project=project, dataset=dataset,
            finished_at=failed_at,
            summary=summary if isinstance(summary, dict) else None,
            error_message=str(exc),
        )
        if isinstance(summary, dict) and summary:
            try:
                _persist_shared_progress_snapshot(
                    run_id=run_id,
                    run_record=run_record,
                    summary=summary,
                    snapshot_at=failed_at,
                    bq=bq,
                    project=project,
                    dataset=dataset,
                    run_status=RunStatus.FAILED,
                )
            except Exception as persist_exc:
                logger.warning(
                    "[run_id=%s] Failed to persist partial progress snapshot for failed run: %s",
                    run_id,
                    persist_exc,
                )
        try:
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="pipeline_failed",
                    level="error",
                    message=str(exc),
                    created_at=failed_at,
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as inner:
            logger.warning("[run_id=%s] Failed to write failure event: %s", run_id, inner)

