"""@meta
name: worker_job
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.worker_job.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import datetime
import hashlib
import json
import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from fitcv.decision_feedback import build_decision_feedback_source
from fitcv.agentic_cv_analysis import analyze_ranked_job
from fitcv.agentic_cv_generation import generate_from_analysis
from fitcv.config import (
    apply_runtime_skill_synonym_overlay,
    get_stage_runtime_concurrency,
    parse_skill_synonym_overlay_yaml,
)
from fitcv.late_stage_contract import (
    CV_DEBUG_ANALYSIS_OMISSION_STATUSES,
    CV_GENERATION_ATTEMPTED_STATUSES,
)
from fitcv.runtime_routing import build_runtime_routing_snapshot
from fitcv.reuse import build_reuse_decision, resolve_reuse_stage_policy
from fitcv.contracts import (
    MAPPING_SUGGESTIONS_SCHEMA_VERSION,
    STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION,
    SETTINGS_USED_SCHEMA_VERSION,
)
from fitcv.pipeline import PipelineCancelled, run_pipeline
from fitcv.preference_policy import (
    PreferenceRuntimeContract,
    ResolvedPreferencePolicy,
    resolve_zero_residual_policy,
    resolved_preference_policy_from_snapshot,
)
from fitcv.telemetry import (
    build_langfuse_trace_attributes,
    observe_span,
    set_span_attributes,
)
from fitcv_cp.backend_runtime import resolve_backend_runtime, resolve_backend_runtime_or_active, set_backend_runtime
from fitcv_cp.sqlite_store import (
    append_event,
    apply_synonym_suggestion_action,
    get_events,
    get_run,
    ingest_synonym_suggestions,
    insert_cv_evaluation_row,
    insert_cv_review_event,
    list_runs,
    list_run_structured_jobs,
    persist_pipeline_snapshot,
    reserve_cv_regeneration,
    update_cv_evaluation,
    update_cv_version,
    update_run_checkpoint,
    update_run_progress,
    update_run_cv_generation_debug,
    update_run_mapping_suggestions,
    update_run_effective_settings,
    update_run_synonym_proposals,
    update_run_results_export,
    update_run_settings_used,
    update_run_stage_transition_artifacts,
    update_run_status,
    resolve_active_ranking_policy,
)
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.data_plane import data_plane_contract_payload
from fitcv_cp.env_defaults import load_dotenv_defaults
from fitcv_cp.run_artifact_mirror import persist_terminal_run_artifact_mirror
from fitcv_cp.synonym_proposals import (
    resolve_synonym_management_mode,
    build_synonym_proposals_payload,
    evaluate_synonym_triage_reuse,
    transition_synonym_proposal_status,
)
from fitcv_cp.synonym_policy_io import (
    compile_global_synonym_map,
    load_global_synonym_map,
    persist_global_synonym_map,
    replace_yaml_top_level_mapping_block,
    synonym_policy_error_reason,
)
from fitcv_cp.review_identity import ensure_review_item_id, is_review_resolution_pending
from fitcv_cp.retry_policy import classify_exception_for_retry
from fitcv_cp.run_artifact_contracts import (
    encode_json_object,
    iso_or_none,
    decode_json_object_or_none,
    decode_json_object_or_raise,
    json_safe,
    normalized_run_mode,
    replay_context_payload,
    run_attempt_payload_v1,
    run_mode_label,
    require_payload_keys,
    stable_json_dumps,
    stable_sha256_fingerprint,
    string_or_none,
)

from fitcv_cp.worker_run_support import (
    _auto_accept_ai_action_enabled_from_run_record,
    _build_mapping_suggestions_payload,
    _build_manual_checkpoint_payload,
    _build_settings_used_payload,
    _build_settings_used_payload_dict,
    _build_stage_transition_artifacts_payload,
    _build_stage_transition_artifacts_payload_dict,
    _effective_settings_payload_from_run_record,
    _effective_skill_synonyms_from_run_record,
    _synonym_management_mode_from_run_record,
    _synonym_propose_enabled_from_run_record,
    _triage_synonym_proposal_recommendation_builtin,
)

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


def _cv_review_state(
    *,
    fit_classification: str | None,
    generation_status: str,
    has_content: bool,
) -> str:
    if fit_classification == "stretch" and has_content:
        return "stretch"
    if generation_status == "review_required" and has_content:
        return "manual_required"
    if generation_status == "generated" and has_content:
        return "approved"
    return "none"


def _resolve_worker_preference_policy(
    runtime_contract: PreferenceRuntimeContract,
) -> ResolvedPreferencePolicy:
    snapshot = resolve_active_ranking_policy(
        runtime_contract.domain_id,
        runtime_contract.runtime_contract_fingerprint,
    )
    if snapshot is None:
        return resolve_zero_residual_policy(
            runtime_contract,
            status="zero_residual_no_active",
        )
    try:
        return resolved_preference_policy_from_snapshot(runtime_contract, snapshot)
    except (TypeError, ValueError):
        return resolve_zero_residual_policy(
            runtime_contract,
            status="zero_residual_invalid",
            diagnostic_code="invalid_active_snapshot",
        )
_NON_SKILL_MIN_SUPPORT_FOR_PROPOSAL = 2
_WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
LOW_RISK_AUTO_ACCEPT_REASON_CODES = {
    "provider_response_unusable",
}

def _builtin_synonym_triage_runtime() -> dict[str, Any]:
    snapshot = build_runtime_routing_snapshot(
        provider="fitcv_builtin",
        model="synonym_triage_v1",
        base_url=None,
        wire_api="builtin",
        api_key="",
        default_provider="fitcv_builtin",
        default_model="synonym_triage_v1",
        default_wire_api="builtin",
    )
    snapshot["sleep_secs"] = 0.0
    snapshot["concurrency"] = 1
    return snapshot


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
        "ranking_contract_fingerprint": str(
            (cfg.get("ranking_contract") or {}).get("ranking_contract_fingerprint") or ""
        ),
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


def _get_bq() -> None:
    return None

def _bounded_markdown_preview(markdown_text: str) -> str:
    preview = str(markdown_text or "")
    if len(preview) > _MAX_DEBUG_MARKDOWN_CHARS:
        return preview[:_MAX_DEBUG_MARKDOWN_CHARS] + "\n...[truncated]"
    return preview

def execute_cv_regenerate_once(
    *,
    run_id: str,
    job_url: str,
    actor: str = "admin",
    note: str | None = None,
    cv_version_id: str | None = None,
    parent_cv_version_id: str | None = None,
    idempotency_key: str | None = None,
    action_id: str | None = None,
) -> None:
    load_dotenv_defaults()
    from fitcv_cp.reporter import retry_pending_process_event_deliveries

    try:
        retry_pending_process_event_deliveries(limit=20)
    except Exception as exc:
        logger.warning("Pending process-event delivery retry failed at CV worker start: %s", exc)
    runtime = resolve_backend_runtime()
    set_backend_runtime(runtime)
    client = None
    now = datetime.datetime.now(datetime.timezone.utc)
    reserved_version_id: str | None = None
    evaluation_id: str | None = None

    append_event(
        RunEvent(
            run_id=run_id,
            event_id=str(uuid.uuid4()),
            stage="cv_regenerate_once_started",
            level="info",
            message="Regenerate-once worker started",
            created_at=now,
            payload_json=json.dumps(
                {
                    "job_url": job_url,
                    "actor": actor,
                    "note": note,
                },
                ensure_ascii=False,
            ),
        ),
        client,
    )
    try:
        run = get_run(run_id, client=client)
        if run is None:
            raise ValueError("run_not_found")
        raw_payload = str(getattr(run, "cv_generation_debug_json", "") or "").strip()
        if not raw_payload:
            raise ValueError("missing_cv_generation_debug")
        payload = decode_json_object_or_raise(raw_payload)
        records_key = "debug_records" if isinstance(payload.get("debug_records"), list) else "cv_generation_debug_records"
        records = payload.get(records_key)
        if not isinstance(records, list):
            raise ValueError("missing_debug_records")
        target_record: dict[str, Any] | None = None
        for item in records:
            if not isinstance(item, dict):
                continue
            if str(item.get("job_url") or "").strip() != str(job_url or "").strip():
                continue
            if str(item.get("status") or "").strip() != "review_required":
                continue
            target_record = item
            break
        if target_record is None:
            raise ValueError("review_required_record_not_found")
        normalized_job_url = str(job_url or "").strip()
        job = next(
            (
                dict(item)
                for item in list_run_structured_jobs(run_id)
                if str(item.get("job_url") or item.get("jobUrl") or item.get("url") or "").strip()
                == normalized_job_url
            ),
            None,
        )
        if job is None:
            raise ValueError("job_not_found")
        run_job_id = str(job.get("run_job_id") or "").strip()
        if not run_job_id:
            raise ValueError("run_job_id_missing")
        profile = decode_json_object_or_raise(str(getattr(run, "candidate_profile_json", "") or "{}"))
        config = decode_json_object_or_raise(str(getattr(run, "effective_settings_json", "") or "{}"))
        input_snapshot = {"job": job, "profile": profile, "settings": config}
        normalized_key = str(idempotency_key or "").strip() or f"legacy:{run_id}:{normalized_job_url}"
        normalized_action_id = str(action_id or "").strip() or str(uuid.uuid4())
        reservation = reserve_cv_regeneration(
            run_job_id,
            version_id=str(cv_version_id or uuid.uuid4()),
            parent_cv_version_id=parent_cv_version_id,
            idempotency_key=normalized_key,
            action_id=normalized_action_id,
            input_snapshot=input_snapshot,
            source_profile_revision=stable_sha256_fingerprint(profile),
            source_settings_revision=stable_sha256_fingerprint(config),
        )
        reserved_version_id = str(reservation["version_id"])
        if bool(reservation.get("idempotent_replay")) and str(
            reservation.get("generation_status") or ""
        ) not in {"pending", "running"}:
            return
        update_cv_version(reserved_version_id, generation_status="running")
        evaluation_id = f"{reserved_version_id}:evaluation:1"
        insert_cv_evaluation_row(
            row={
                "cv_evaluation_id": evaluation_id,
                "cv_version_id": reserved_version_id,
                "status": "pending",
                "evaluator_id": "fitcv.agentic_cv_analysis.analyze_ranked_job",
                "started_at": now.isoformat(),
                "is_current": True,
            }
        )
        update_cv_evaluation(evaluation_id, status="running")
        analysis = dict(analyze_ranked_job(job, profile, config))
        generation = dict(generate_from_analysis(analysis, profile, config))
        fit_classification = str(
            analysis.get("fit_classification") or generation.get("fit_classification") or ""
        ).strip()
        update_cv_evaluation(
            evaluation_id,
            status="succeeded",
            fit_classification=fit_classification,
            reason=json.dumps(analysis.get("gap_summary"), sort_keys=True)
            if analysis.get("gap_summary") is not None else None,
            evidence={
                "requirement_coverage": analysis.get("requirement_coverage") or [],
                "evidence_selection_summary": analysis.get("evidence_selection_summary") or {},
            },
        )
        generation_status = {
            "accepted": "generated",
            "review_required": "review_required",
            "validation_failed": "validation_failed",
            "generation_failed": "generation_failed",
            "persistence_failed": "persistence_failed",
        }.get(str(generation.get("status") or ""), "generation_failed")
        markdown = str(generation.get("markdown_final") or "")
        content = markdown.encode("utf-8") if generation_status in {"generated", "review_required"} else None
        terminal = update_cv_version(
            reserved_version_id,
            generation_status=generation_status,
            content=content,
            metadata={
                "generator_id": "fitcv.agentic_cv_generation.generate_from_analysis",
                "model_id": generation.get("model") or config.get("cv_generation_model"),
                "prompt_id": config.get("cv_generation_prompt_version") or config.get("cv_prompt_version"),
                "schema_id": generation.get("result_contract_version"),
                "fit_classification": fit_classification or None,
                "cv_generation_model": generation.get("model") or config.get("cv_generation_model"),
                "cv_prompt_version": config.get("cv_generation_prompt_version") or config.get("cv_prompt_version"),
                "cv_schema_version": generation.get("result_contract_version"),
                "cv_structured_json": generation.get("structured_cv_final"),
                "cv_generation_input_fingerprint": generation.get("cv_generation_input_fingerprint"),
                "cv_generation_reuse_status": generation.get("cv_generation_reuse_status"),
            },
            error_code=(str((generation.get("error") or {}).get("stage") or "") or None),
            error_message=(str((generation.get("error") or {}).get("message") or "") or None),
        )
        review_state = _cv_review_state(
            fit_classification=fit_classification or None,
            generation_status=generation_status,
            has_content=content is not None,
        )
        if review_state != "none":
            insert_cv_review_event(
                row={
                    "review_event_id": str(uuid.uuid4()),
                    "cv_version_id": reserved_version_id,
                    "cv_evaluation_id": evaluation_id,
                    "from_state": "none",
                    "to_state": review_state,
                    "actor": "system",
                    "note": note,
                    "action_id": normalized_action_id,
                    "idempotency_key": normalized_key,
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
            )
        append_event(
            RunEvent(
                run_id=run_id,
                event_id=str(uuid.uuid4()),
                stage="cv_regenerate_once_succeeded",
                level="info",
                message="Regenerate-once worker completed",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                payload_json=json.dumps(
                    {
                        "job_url": job_url,
                        "actor": actor,
                        "note": note,
                        "cv_version_id": reserved_version_id,
                        "generation_status": terminal.get("generation_status"),
                        "content_checksum": terminal.get("content_checksum"),
                        "review_state": review_state,
                    },
                    ensure_ascii=False,
                ),
            ),
            client=client,
        )
    except Exception as exc:
        if evaluation_id is not None:
            try:
                update_cv_evaluation(
                    evaluation_id,
                    status="failed",
                    error_code="provider_or_generation_failure",
                    error_message=str(exc),
                    retry_count=1,
                )
            except Exception:
                pass
        if reserved_version_id is not None:
            try:
                update_cv_version(
                    reserved_version_id,
                    generation_status="generation_failed",
                    error_code="cv_regeneration_failed",
                    error_message=str(exc),
                )
            except Exception:
                pass
        append_event(
            RunEvent(
                run_id=run_id,
                event_id=str(uuid.uuid4()),
                stage="cv_regenerate_once_failed",
                level="error",
                message=f"Regenerate-once worker failed: {exc}",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                payload_json=json.dumps(
                    {
                        "job_url": job_url,
                        "actor": actor,
                        "note": note,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                ),
            ),
            client=client,
        )
        raise




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
    client: Any,
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
        client,
    )


class JobsInputIntegrityError(RuntimeError):
    pass


def _verify_jobs_input_projection(run_record: Any, jobs_path: str) -> None:
    contract_version = getattr(run_record, "run_input_contract_version", None)
    snapshot_value = getattr(run_record, "jobs_input_json", None)
    if not isinstance(snapshot_value, str) or not snapshot_value:
        if contract_version == "managed_v1":
            raise JobsInputIntegrityError("managed run input snapshot is missing")
        return

    persisted_path_value = getattr(run_record, "jobs_path", None)
    if not isinstance(persisted_path_value, str) or not persisted_path_value.strip():
        raise JobsInputIntegrityError("persisted run projection path is missing")
    persisted_path = persisted_path_value.strip()
    if Path(persisted_path).resolve() != Path(jobs_path).resolve():
        raise JobsInputIntegrityError("queued jobs_path does not match persisted run projection")

    snapshot_bytes = snapshot_value.encode("utf-8")
    snapshot_digest = hashlib.sha256(snapshot_bytes).hexdigest()
    manifest_value = getattr(run_record, "jobs_input_manifest_json", None)
    if not isinstance(manifest_value, str):
        raise JobsInputIntegrityError("jobs input manifest is missing")
    try:
        manifest = json.loads(manifest_value)
    except json.JSONDecodeError as exc:
        raise JobsInputIntegrityError("jobs input manifest is invalid JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("canonical_sha256") != snapshot_digest:
        raise JobsInputIntegrityError("jobs input manifest digest does not match snapshot")
    try:
        projection_bytes = Path(persisted_path).read_bytes()
    except OSError as exc:
        raise JobsInputIntegrityError("jobs input projection is missing or unreadable") from exc
    if projection_bytes != snapshot_bytes:
        raise JobsInputIntegrityError("jobs input projection bytes do not match snapshot")


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
    diagnostic_support = {
        "late_stage_reuse_snapshots": json_safe(summary.get("late_stage_reuse_snapshots") or {}),
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
            "decision": json_safe(stage_result.get("decision") or {}),
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
        "results_schema_version": "results_job_ledger_v4",
        "schema_version": "results_job_ledger_v4",
        "status": RunStatus.SUCCEEDED.value,
        "triggered_by": string_or_none(getattr(run_record, "triggered_by", "")) or "",
        "run_mode": normalized_run_mode(getattr(run_record, "run_mode", None)),
        "run_mode_label": run_mode_label(getattr(run_record, "run_mode", None)),
        "created_at": iso_or_none(getattr(run_record, "created_at", None)),
        "started_at": iso_or_none(getattr(run_record, "started_at", None)),
        "finished_at": finished_at.isoformat(),
        "jobs_path": string_or_none(getattr(run_record, "jobs_path", "")) or "",
        "jobs_input_source": string_or_none(getattr(run_record, "jobs_input_source", None)),
        "candidate_profile_source": string_or_none(getattr(run_record, "candidate_profile_source", None)),
        "summary": {
            "total_jobs": int(summary.get("total_jobs", 0)),
            "passed_filter": int(summary.get("passed_filter", 0)),
            "ranked": int(summary.get("ranked", 0)),
            "cvs_generated": int(summary.get("cvs_generated", 0)),
        },
        "stage_result_summary": stage_result_summary,
        "data_plane": data_plane_contract_payload(effective_config),
        "replay_context": replay_context_payload(replay_context=replay_context, run_id=run_id),
        "results": json_safe(export_results),
    }
    candidate_profile: dict[str, Any] = {}
    candidate_profile_raw = getattr(run_record, "candidate_profile_json", None)
    if isinstance(candidate_profile_raw, dict):
        candidate_profile = candidate_profile_raw
    elif str(candidate_profile_raw or "").strip():
        try:
            decoded_profile = json.loads(str(candidate_profile_raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            decoded_profile = None
        if isinstance(decoded_profile, dict):
            candidate_profile = decoded_profile
    if effective_config and candidate_profile:
        try:
            payload["decision_feedback_source"] = build_decision_feedback_source(
                run_id=run_id,
                candidate_profile=candidate_profile,
                config=effective_config,
                scoring_rows=export_results,
            )
        except ValueError as exc:
            logger.warning("[run_id=%s] Decision feedback unavailable: %s", run_id, exc)
    if diagnostic_support["late_stage_reuse_snapshots"]:
        payload["diagnostic_support"] = diagnostic_support
    require_payload_keys(
        payload,
        required_keys={"run_id", "schema_version", "created_at", "replay_context"},
        context="results_export_payload",
    )
    return encode_json_object(payload)


def _collect_late_stage_reuse_snapshots(
    *,
    current_run_id: str,
    allow_checkpointed_sources: bool,
    client: Any,
) -> dict[str, Any]:
    snapshots: dict[str, Any] = {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [],
        "cv_analysis_records": [],
    }
    try:
        prior_runs = list_runs(
            client=client,
            limit=_LATE_STAGE_REUSE_RUN_SCAN_LIMIT,
            include_archived=True,
        )
    except Exception as exc:
        logger.warning("[run_id=%s] Failed to list prior runs for reuse lookup: %s", current_run_id, exc)
        return snapshots

    def _merge_reuse_payload(source_payload: dict[str, Any]) -> None:
        diagnostic_support = dict(source_payload.get("diagnostic_support") or {})
        reuse_payload = dict(
            diagnostic_support.get("late_stage_reuse_snapshots")
            or source_payload.get("late_stage_reuse_snapshots")
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
        if snapshots["ranking_ai_scores"] or snapshots["cv_analysis_records"]:
            return
        stage_root = dict(source_payload.get("artifacts") or source_payload)
        stage_blocks = dict(stage_root.get("stages") or {})
        ranking_block = dict(stage_blocks.get("ranking") or {})
        ranking_rows = [item for item in list(ranking_block.get("outputs_sample") or []) if isinstance(item, dict)]
        for row in ranking_rows:
            fingerprint = str(row.get("ai_score_input_fingerprint") or "").strip()
            job_url = str(row.get("job_url") or "").strip()
            if not fingerprint or not job_url:
                continue
            snapshots["ranking_ai_scores"].append(
                {
                    "job_url": job_url,
                    "ai_score_input_fingerprint": fingerprint,
                    "ai_score_row": dict(row),
                }
            )
        cv_analysis_block = dict(stage_blocks.get("cv_analysis") or {})
        cv_analysis_rows = []
        cv_analysis_rows.extend(
            [item for item in list(cv_analysis_block.get("outputs_sample") or []) if isinstance(item, dict)]
        )
        cv_analysis_rows.extend(
            [item for item in list(cv_analysis_block.get("dropped_or_changed_sample") or []) if isinstance(item, dict)]
        )
        for row in cv_analysis_rows:
            fingerprint = str(row.get("analysis_input_fingerprint") or "").strip()
            job_url = str(row.get("job_url") or "").strip()
            if not fingerprint or not job_url:
                continue
            snapshots["cv_analysis_records"].append(
                {
                    "job_url": job_url,
                    "analysis_input_fingerprint": fingerprint,
                    "analysis_record": dict(row),
                }
            )

    for prior_run in prior_runs:
        if prior_run.run_id == current_run_id:
            continue
        if prior_run.status == RunStatus.SUCCEEDED and prior_run.results_export_json:
            try:
                payload = json.loads(prior_run.results_export_json)
            except Exception as exc:
                logger.warning(
                    "[run_id=%s] Failed to parse prior results_export_json for reuse lookup [source_run_id=%s]: %s",
                    current_run_id,
                    prior_run.run_id,
                    exc,
                )
            else:
                _merge_reuse_payload(payload)
                continue
        if not allow_checkpointed_sources:
            continue
        stage_payload_raw = str(getattr(prior_run, "stage_transition_artifacts_json", "") or "").strip()
        if not stage_payload_raw:
            continue
        try:
            stage_payload = json.loads(stage_payload_raw)
        except Exception as exc:
            logger.warning(
                "[run_id=%s] Failed to parse prior stage_transition_artifacts_json for reuse lookup [source_run_id=%s]: %s",
                current_run_id,
                prior_run.run_id,
                exc,
            )
            continue
        _merge_reuse_payload(stage_payload)
    return snapshots


def _build_cv_generation_debug_payload(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
) -> str:
    def _truncate_large_fields(record: dict[str, Any]) -> dict[str, Any]:
        truncated = dict(record)
        markdown_final = truncated.get("markdown_final")
        if isinstance(markdown_final, str):
            markdown_preview = markdown_final
            if len(markdown_preview) > _MAX_DEBUG_MARKDOWN_CHARS:
                markdown_preview = markdown_preview[:_MAX_DEBUG_MARKDOWN_CHARS] + "\n...[truncated]"
            # Keep authoritative draft separate from bounded preview/debug payload.
            truncated["markdown_full"] = markdown_final
            truncated["markdown_preview"] = markdown_preview
            # Legacy field remains bounded for compatibility with older readers.
            truncated["markdown_final"] = markdown_preview
        return truncated

    debug_records = [
        _truncate_large_fields(record)
        for record in list(summary.get("cv_generation_debug_records") or [])
    ]
    for idx, record in enumerate(debug_records):
        if not isinstance(record, dict):
            continue
        if str(record.get("status") or "").strip() == "review_required":
            ensure_review_item_id(
                run_id=run_id,
                record=record,
                fallback_index=idx + 1,
            )
        ranking_fit_label = record.get("ranking_fit_label")
        reranker_fit_label = record.get("reranker_fit_label")
        if ranking_fit_label is None and reranker_fit_label is not None:
            record["ranking_fit_label"] = reranker_fit_label
        if reranker_fit_label is None and ranking_fit_label is not None:
            record["reranker_fit_label"] = ranking_fit_label
    debug_records = json_safe(debug_records)
    ranked_jobs_total = int(summary.get("ranked", 0))
    attempted_generation_jobs_total = sum(
        1
        for record in debug_records
        if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
    )
    debug_record_job_urls = {
        str(record.get("job_url") or "")
        for record in debug_records
        if str(record.get("job_url") or "")
    }
    omission_reason_counts: dict[str, int] = {}
    for record in debug_records:
        status = str(record.get("status") or "")
        if status in CV_GENERATION_ATTEMPTED_STATUSES:
            continue
        omission_reason_counts[status] = omission_reason_counts.get(status, 0) + 1
    for record in list(summary.get("cv_analysis_results") or []):
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "")
        if status not in CV_DEBUG_ANALYSIS_OMISSION_STATUSES:
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
        "schema_version": "cv_generation_debug_v3",
        "run_mode": normalized_run_mode(getattr(run_record, "run_mode", None)),
        "run_mode_label": run_mode_label(getattr(run_record, "run_mode", None)),
        "created_at": finished_at.isoformat(),
        "ranked_jobs_total": ranked_jobs_total,
        "debug_records_captured": len(debug_records),
        "attempted_generation_jobs_total": attempted_generation_jobs_total,
        "non_attempted_ranked_jobs_total": non_attempted_ranked_jobs_total,
        "omission_reason_counts": omission_reason_counts,
        "snapshot_complete": len(debug_records) == ranked_jobs_total,
        "debug_records": debug_records,
    }
    if isinstance(summary.get("cv_generation_trace"), dict):
        payload["cv_generation_trace"] = dict(summary["cv_generation_trace"])
    if isinstance(summary.get("cv_analysis_trace"), dict):
        payload["cv_analysis_trace"] = dict(summary["cv_analysis_trace"])
    require_payload_keys(
        payload,
        required_keys={"run_id", "schema_version", "created_at", "debug_records"},
        context="cv_generation_debug_payload",
    )
    return encode_json_object(payload)


def _replace_yaml_top_level_mapping_block(
    *,
    raw_yaml: str,
    key: str,
    mappings: dict[str, str],
) -> str:
    return replace_yaml_top_level_mapping_block(
        raw_yaml=raw_yaml,
        key=key,
        mappings=mappings,
    )

def _load_global_skill_synonyms_map() -> dict[str, str]:
    return load_global_synonym_map("skill")

def _build_synonym_overlay_yaml(overlay: dict[str, str]) -> str:
    if not overlay:
        return ""
    payload = {
        "skill_synonyms": {
            str(alias): str(canonical)
            for alias, canonical in sorted(overlay.items())
        }
    }
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

def _persist_global_skill_synonyms_map(mappings: dict[str, str]) -> None:
    persist_global_synonym_map("skill", mappings)

def _load_global_domain_alias_map() -> dict[str, str]:
    return load_global_synonym_map("domain")

def _persist_global_domain_alias_map(mappings: dict[str, str]) -> None:
    persist_global_synonym_map("domain", mappings)

def _load_global_role_family_alias_map() -> dict[str, str]:
    return load_global_synonym_map("role_family")

def _persist_global_role_family_alias_map(mappings: dict[str, str]) -> None:
    persist_global_synonym_map("role_family", mappings)


def _map_review_required_reason_code(record: dict[str, Any]) -> str:
    explicit_code = str(record.get("review_required_reason_code") or "").strip()
    from fitcv.pipeline_contracts import ReviewRequiredReasonCode, is_review_required_reason_code

    if is_review_required_reason_code(explicit_code):
        return explicit_code
    error = dict(record.get("error") or {})
    stage = str(error.get("stage") or "").strip().lower()
    message = str(error.get("message") or record.get("operator_note") or "").strip().lower()
    if "unsupported requirements require review" in message:
        return ReviewRequiredReasonCode.UNSUPPORTED_REQUIREMENT_GAP.value
    if stage == "markdown_quality_review" or "markdown quality" in message:
        return ReviewRequiredReasonCode.QUALITY_GATE_FAILED.value
    if stage == "validation" or "validation failed" in message or "guardrail" in message:
        return ReviewRequiredReasonCode.VALIDATION_GUARDRAIL_FAILED.value
    if "insufficient evidence" in message or "evidence coverage" in message:
        return ReviewRequiredReasonCode.EVIDENCE_COVERAGE_INSUFFICIENT.value
    if stage in {"provider", "llm"} or "provider" in message or "response unusable" in message:
        return ReviewRequiredReasonCode.PROVIDER_RESPONSE_UNUSABLE.value
    return ReviewRequiredReasonCode.MANUAL_REVIEW_OTHER.value


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
    client: Any,
) -> None:
    payload = decode_json_object_or_none(synonym_payload_json)
    if not payload:
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
    suppression_fingerprint_sha256 = stable_sha256_fingerprint(suppression_payload)
    suppression_fingerprint_sha1 = hashlib.sha1(
        json.dumps(suppression_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    try:
        prior_events = get_events(run_id, client)
    except Exception:
        prior_events = []
    for prior in reversed(prior_events):
        if str(getattr(prior, "stage", "") or "") != "synonym_proposal_suppression_summary":
            continue
        prior_payload = decode_json_object_or_none(str(getattr(prior, "payload_json", "") or "")) or {}
        prior_fingerprint = str(prior_payload.get("suppression_fingerprint") or "").strip()
        if not prior_fingerprint:
            break
        if prior_fingerprint in {suppression_fingerprint_sha256, suppression_fingerprint_sha1}:
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
                {
                    **suppression_payload,
                    "suppression_fingerprint": suppression_fingerprint_sha256,
                    "suppression_fingerprint_legacy_sha1": suppression_fingerprint_sha1,
                    "suppression_payload_canonical_json": stable_json_dumps(suppression_payload),
                },
                ensure_ascii=False,
            ),
        ),
        client,
    )

def _run_synonym_automation_for_payload(
    *,
    run_id: str,
    run_record: Any,
    payload: dict[str, Any],
    run_status: RunStatus,
    client: Any,
) -> None:
    mode = _synonym_management_mode_from_run_record(run_record)
    proposals = [item for item in list(payload.get("proposals") or []) if isinstance(item, dict)]
    if not proposals:
        return
    trace_payload = dict(payload.get("synonym_proposals_trace") or {})
    trace_summary = dict(trace_payload.get("trace_summary") or {})
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    triaged_count = 0
    reused_count = 0
    reused_strict_count = 0
    reused_core_count = 0
    fresh_count = 0
    skipped_count = 0
    failed_count = 0
    fallback_count = 0
    reuse_reason = "reuse_enabled"
    if not bool(mode.get("auto_triage_recommendation_enabled")):
        reuse_reason = "auto_triage_disabled"
    elif not bool(mode.get("triage_recommendation_reuse_enabled")):
        reuse_reason = "reuse_disabled"

    if bool(mode.get("auto_triage_recommendation_enabled")):
        for idx, proposal in enumerate(proposals):
            status = str(proposal.get("proposal_status") or "").strip() or "proposed_unreviewed"
            if status not in {"proposed_unreviewed", "in_review", "deferred"}:
                skipped_count += 1
                continue
            runtime_meta = dict(proposal.get("recommendation_runtime") or {})
            reuse_eval = evaluate_synonym_triage_reuse(
                proposal=proposal,
                runtime=_builtin_synonym_triage_runtime(),
                runtime_meta=runtime_meta,
            )
            reuse_enabled = bool(mode.get("triage_recommendation_reuse_enabled"))
            triage_fingerprint = str(reuse_eval.get("strict_fingerprint") or "")
            runtime_meta["reuse_decision"] = build_reuse_decision(
                decision=(
                    "reused_exact_match"
                    if reuse_enabled and str(reuse_eval.get("decision") or "") in {"strict_reuse", "core_reuse"}
                    else "fresh_compute"
                ),
                reason_code=(
                    "exact_fingerprint_match"
                    if reuse_enabled and str(reuse_eval.get("decision") or "") in {"strict_reuse", "core_reuse"}
                    else str(reuse_eval.get("reason") or "no_reusable_snapshot_match")
                ),
                fingerprint=triage_fingerprint,
                source_artifact_type="synonym_triage",
            )
            proposal["recommendation_runtime"] = runtime_meta
            if reuse_enabled and str(reuse_eval.get("decision") or "") in {"strict_reuse", "core_reuse"}:
                reused_count += 1
                if str(reuse_eval.get("decision") or "") == "strict_reuse":
                    reused_strict_count += 1
                else:
                    reused_core_count += 1
                triaged_count += 1
                continue
            try:
                recommendation = _triage_synonym_proposal_recommendation_builtin(proposal, now_iso=now_iso)
            except Exception:
                failed_count += 1
                fallback_count += 1
                continue
            recommendation_runtime = dict(recommendation.get("recommendation_runtime") or {})
            recommendation_runtime["triage_fingerprint"] = str(reuse_eval.get("strict_fingerprint") or "")
            recommendation_runtime["triage_fingerprint_strict"] = str(reuse_eval.get("strict_fingerprint") or "")
            recommendation_runtime["triage_fingerprint_core"] = str(reuse_eval.get("core_fingerprint") or "")
            gate = dict(reuse_eval.get("gate") or {})
            recommendation_runtime["triage_gate_status"] = str(gate.get("status") or "")
            recommendation_runtime["triage_gate_has_conflict"] = bool(gate.get("has_conflict"))
            recommendation_runtime["triage_gate_canonical"] = str(gate.get("canonical") or "")
            recommendation_runtime["triage_gate_candidate_canonicals"] = list(gate.get("candidate_canonicals") or [])
            updated = dict(proposal)
            updated.update(
                {
                    "recommended_action": str(recommendation.get("recommended_action") or "").strip() or None,
                    "recommendation_confidence": round(float(recommendation.get("recommendation_confidence") or 0.0), 3),
                    "recommendation_rationale": str(recommendation.get("recommendation_rationale") or "").strip() or None,
                    "recommendation_risk_flags": [
                        str(flag).strip()
                        for flag in list(recommendation.get("recommendation_risk_flags") or [])
                        if str(flag).strip()
                    ],
                    "recommendation_runtime": recommendation_runtime,
                }
            )
            proposals[idx] = updated
            fresh_count += 1
            triaged_count += 1

        event_payload = {
            "triaged_count": triaged_count,
            "reused_count": reused_count,
            "reused_strict_count": reused_strict_count,
            "reused_core_count": reused_core_count,
            "fresh_count": fresh_count,
            "fallback_count": fallback_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "reuse_reason": reuse_reason,
            "auto_triage_recommendation_enabled": bool(mode.get("auto_triage_recommendation_enabled")),
            "triage_recommendation_reuse_enabled": bool(mode.get("triage_recommendation_reuse_enabled")),
            **_builtin_synonym_triage_runtime(),
        }
        event_fingerprint = hashlib.sha256(
            json.dumps(event_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        last_fingerprint = str(trace_summary.get("triage_recommendation_event_fingerprint") or "").strip()
        already_emitted = False
        if event_fingerprint == last_fingerprint:
            already_emitted = True
        else:
            try:
                prior_events = get_events(run_id, client)
            except Exception:
                prior_events = []
            for prior_event in reversed(prior_events):
                if str(prior_event.stage or "").strip() != "synonym_proposal_triage_completed":
                    continue
                try:
                    prior_payload = json.loads(str(prior_event.payload_json or "{}"))
                except Exception:
                    prior_payload = {}
                prior_fp = hashlib.sha256(
                    json.dumps(dict(prior_payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                if prior_fp == event_fingerprint:
                    already_emitted = True
                break
        if not already_emitted:
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="synonym_proposal_triage_completed",
                    level="info",
                    message=(
                        "Synonym triage refresh completed: "
                        f"triaged={triaged_count}, reused={reused_count}, "
                        f"fallback={fallback_count}, skipped={skipped_count}, failed={failed_count}"
                    ),
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    payload_json=json.dumps(event_payload, ensure_ascii=False),
                ),
                client=client,
            )
        trace_summary["triage_recommendation_event_fingerprint"] = event_fingerprint

    trace_summary["triage_recommendation_generated_total"] = int(triaged_count)
    trace_summary["triage_recommendation_reused_total"] = int(reused_count)
    trace_summary["triage_recommendation_reused_strict_total"] = int(reused_strict_count)
    trace_summary["triage_recommendation_reused_core_total"] = int(reused_core_count)
    trace_summary["triage_recommendation_fresh_total"] = int(fresh_count)
    trace_summary["triage_recommendation_suppressed_total"] = 0
    trace_summary["triage_recommendation_reuse_reason"] = reuse_reason
    trace_summary["triage_recommendation_fingerprint"] = stable_sha256_fingerprint(
        _builtin_synonym_triage_runtime()
    )
    trace_payload["trace_summary"] = trace_summary
    payload["proposals"] = proposals
    payload["synonym_proposals_trace"] = trace_payload


def _sync_central_synonym_suggestions(
    *,
    run_id: str,
    run_record: Any,
    payload: dict[str, Any],
) -> None:
    field_types = {"skill": "skills", "domain": "domain", "role_family": "role_family"}
    suggestions = []
    for proposal in list(payload.get("proposals") or []):
        if not isinstance(proposal, dict):
            continue
        synonym_type = field_types.get(str(proposal.get("field") or "skill").strip().lower())
        alias = str(proposal.get("alias") or "").strip()
        canonical = str(proposal.get("canonical") or "").strip()
        if not synonym_type or not alias or not canonical:
            continue
        suggestions.append(
            {
                "synonym_type": synonym_type,
                "alias": alias,
                "canonical": canonical,
                "run_id": run_id,
                "confidence": proposal.get("confidence"),
                "candidate_canonicals": list(proposal.get("candidate_canonicals") or []),
                "evidence_note": str((proposal.get("rationale") or {}).get("kind") or "").replace("_", " ").strip().capitalize() or None,
                "evidence": {
                    "evidence_summary": dict(proposal.get("evidence_summary") or {}),
                    "conflict_summary": dict(proposal.get("conflict_summary") or {}),
                },
            }
        )
    if not suggestions:
        return
    result = ingest_synonym_suggestions(suggestions)
    mode = _synonym_management_mode_from_run_record(run_record)
    if not bool(mode.get("auto_accept_suggestions_enabled")):
        return
    actionable_ids = list(
        result.get("actionable_suggestion_ids") or result.get("suggestion_ids") or []
    )
    if actionable_ids:
        apply_synonym_suggestion_action(
            actionable_ids,
            action="approve",
            acted_by="automation",
        )

def _persist_shared_progress_snapshot(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    snapshot_at: datetime.datetime,
    client: Any,
    run_status: RunStatus,
) -> None:
    update_run_status(
        run_id,
        run_status,
        client=client,
        summary=summary,
    )
    update_run_progress(
        run_id,
        client=client,
        last_completed_stage=str(summary.get("last_completed_stage") or "").strip() or None,
        completed_stages=list(summary.get("completed_stages") or []),
    )
    if isinstance(run_record, PipelineRun):
        persist_pipeline_snapshot(
            run_id,
            summary,
            run_status=run_status,
            snapshot_at=snapshot_at,
        )
    update_run_stage_transition_artifacts(
        run_id,
        _build_stage_transition_artifacts_payload(
            run_id=run_id,
            summary=summary,
            finished_at=snapshot_at,
            run_status=run_status,
            degradation_reason="partial_snapshot",
            prior_stage_transition_artifacts=getattr(run_record, "stage_transition_artifacts_json", None),
            stages_completed_before_segment=list(getattr(run_record, "completed_stages", None) or []),
        ),
        client=client,
    )
    if _summary_has_reached_stage(summary, "enrich"):
        _persist_mapping_suggestions_snapshot(
            run_id=run_id,
            summary=summary,
            created_at=snapshot_at,
            client=client,
        )
    if _synonym_propose_enabled_from_run_record(run_record):
        _persist_synonym_proposals_snapshot(
                run_id=run_id,
                run_record=run_record,
                summary=summary,
                created_at=snapshot_at,
                run_status=run_status,
            client=client,
        )


def _persist_terminal_pipeline_snapshot(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    run_status: RunStatus,
    snapshot_at: datetime.datetime,
) -> None:
    if isinstance(run_record, PipelineRun):
        persist_pipeline_snapshot(
            run_id,
            summary,
            run_status=run_status,
            snapshot_at=snapshot_at,
        )


def _persist_mapping_suggestions_snapshot(
    *,
    run_id: str,
    summary: dict[str, Any],
    created_at: datetime.datetime,
    client: Any,
) -> None:
    update_run_mapping_suggestions(
        run_id,
        _build_mapping_suggestions_payload(
            run_id=run_id,
            summary=summary,
            created_at=created_at,
        ),
        client=client,
    )


def _persist_synonym_proposals_snapshot(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    created_at: datetime.datetime,
    run_status: RunStatus,
    client: Any,
) -> str:
    """Persist run-scoped synonym proposals snapshot with shared behavior."""
    existing_payload_json = _resolve_synonym_proposals_seed_payload_json(
        run_id=run_id,
        run_record=run_record,
        client=client,
    )
    synonym_payload_json = build_synonym_proposals_payload(
        run_id=run_id,
        summary=summary,
        created_at=created_at,
        existing_payload_json=existing_payload_json,
        global_synonyms=_effective_skill_synonyms_from_run_record(run_record),
    )
    synonym_payload = decode_json_object_or_raise(synonym_payload_json)
    _run_synonym_automation_for_payload(
        run_id=run_id,
        run_record=run_record,
        payload=synonym_payload,
        run_status=run_status,
        client=client,
    )
    _sync_central_synonym_suggestions(
        run_id=run_id,
        run_record=run_record,
        payload=synonym_payload,
    )
    synonym_payload_json = encode_json_object(synonym_payload)

    synonym_status = update_run_synonym_proposals(
        run_id,
        synonym_payload_json,
        client=client,
    )
    _append_synonym_suppression_summary_event(
        run_id=run_id,
        synonym_payload_json=synonym_payload_json,
        client=client,
    )
    _append_degraded_snapshot_persistence_warning(
        run_id=run_id,
        snapshot_name="synonym_proposals",
        persistence_status=synonym_status,
        client=client,
    )
    return str(synonym_status or "")

def _resolve_synonym_proposals_seed_payload_json(
    *,
    run_id: str,
    run_record: Any,
    client: Any,
) -> str | None:
    current_payload = str(getattr(run_record, "synonym_proposals_json", "") or "").strip()
    if current_payload:
        return current_payload

    current_jobs_path = str(getattr(run_record, "jobs_path", "") or "").strip()
    current_run_mode = str(getattr(run_record, "run_mode", "") or "").strip()
    try:
        runs = list_runs(client=client, include_archived=False)
    except Exception:
        return None

    latest_payload: str | None = None
    latest_ts: datetime.datetime | None = None
    for candidate in runs:
        candidate_run_id = str(getattr(candidate, "run_id", "") or "").strip()
        if not candidate_run_id or candidate_run_id == run_id:
            continue
        payload = str(getattr(candidate, "synonym_proposals_json", "") or "").strip()
        if not payload:
            continue
        if current_jobs_path and str(getattr(candidate, "jobs_path", "") or "").strip() != current_jobs_path:
            continue
        if current_run_mode and str(getattr(candidate, "run_mode", "") or "").strip() != current_run_mode:
            continue

        status_raw = getattr(candidate, "status", "")
        status = str(getattr(status_raw, "value", status_raw) or "").strip().lower()
        if status not in {"succeeded", "awaiting_continue"}:
            continue

        candidate_ts = getattr(candidate, "finished_at", None) or getattr(candidate, "created_at", None)
        if not isinstance(candidate_ts, datetime.datetime):
            continue
        if latest_ts is None or candidate_ts > latest_ts:
            latest_ts = candidate_ts
            latest_payload = payload
    return latest_payload


def execute_pipeline_run(
    run_id: str,
    jobs_path: str,
    config_path: str,
    *,
    attempt_id: str | None = None,
    queue_job_id: str | None = None,
) -> None:
    load_dotenv_defaults()
    from fitcv_cp.reporter import PipelineReporter, retry_pending_process_event_deliveries

    try:
        retry_pending_process_event_deliveries(limit=20)
    except Exception as exc:
        logger.warning("Pending process-event delivery retry failed at pipeline worker start: %s", exc)
    runtime = resolve_backend_runtime()
    set_backend_runtime(runtime)
    client = None

    summary: dict[str, Any] = {}
    run_record: Any | None = None
    attempt_id = str(attempt_id or uuid.uuid4())
    attempt_queue_job_id = str(queue_job_id or "").strip() or None

    if attempt_queue_job_id is None:
        try:
            from rq import get_current_job

            job = get_current_job()
            if job is not None and getattr(job, "id", None):
                attempt_queue_job_id = str(job.id)
        except Exception:
            pass

    with observe_span(
        "fitcv.worker_job",
        attributes={
            "run_id": run_id,
            "backend_type": str(runtime.backend_type),
            **build_langfuse_trace_attributes(
                trace_name="fitcv.worker_job",
                session_id=run_id,
                input_payload={
                    "run_id": run_id,
                    "jobs_path": jobs_path,
                    "config_path": config_path,
                    "backend_type": str(runtime.backend_type),
                },
                metadata={
                    "scope": "control_plane_worker",
                    "backend_type": str(runtime.backend_type),
                },
            ),
        },
    ):
        try:
            current_run_record = get_run(run_id, client=client)
            if current_run_record and current_run_record.cancel_requested_at is not None:
                logger.info("[run_id=%s] Cancellation already requested — exiting early", run_id)
                cancelled_at = datetime.datetime.now(datetime.timezone.utc)
                update_run_status(
                    run_id, RunStatus.CANCELLED, client=client,
                    finished_at=cancelled_at,
                )
                _persist_terminal_pipeline_snapshot(
                    run_id=run_id,
                    run_record=current_run_record,
                    summary={},
                    run_status=RunStatus.CANCELLED,
                    snapshot_at=cancelled_at,
                )
                append_event(
                    _run_cancelled_event(run_id, "Run cancelled before pipeline execution started"),
                    client=client,
                )
                set_span_attributes({"run_terminal_status": str(RunStatus.CANCELLED)})
                return
            # ── Step 1: Mark running ──────────────────────────────────────────────
            update_run_status(
                run_id, RunStatus.RUNNING, client=client,
                started_at=(
                    datetime.datetime.now(datetime.timezone.utc)
                    if current_run_record is None or getattr(current_run_record, "started_at", None) is None
                    else None
                ),
            )

            from fitcv_cp.retry_settings import load_retry_settings

            settings = load_retry_settings()
            lease_seconds = settings.lease_seconds
            lease_started_at = datetime.datetime.now(datetime.timezone.utc)
            lease_expires_at = lease_started_at + datetime.timedelta(seconds=max(1, lease_seconds))
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="run_attempt",
                    level="info",
                    message="Run attempt started",
                    created_at=lease_started_at,
                    payload_json=json.dumps(
                        run_attempt_payload_v1(
                            attempt_id=attempt_id,
                            status=RunStatus.RUNNING.value,
                            rq_job_id=attempt_queue_job_id,
                            worker_id=os.environ.get("HOSTNAME"),
                            lease_started_at=lease_started_at,
                            lease_expires_at=lease_expires_at,
                        ),
                        ensure_ascii=False,
                    ),
                ),
                client=client,
            )

            _last_lease_renew_at = 0.0

            def _maybe_renew_attempt_lease() -> None:
                nonlocal _last_lease_renew_at
                if lease_seconds <= 0:
                    return
                now_monotonic = time.monotonic()
                renew_interval = max(5.0, float(lease_seconds) / 3.0)
                if (now_monotonic - _last_lease_renew_at) < renew_interval:
                    return
                _last_lease_renew_at = now_monotonic
                renewed_at = datetime.datetime.now(datetime.timezone.utc)
                renewed_expires_at = renewed_at + datetime.timedelta(seconds=max(1, lease_seconds))
                try:
                    append_event(
                        RunEvent(
                            run_id=run_id,
                            event_id=str(uuid.uuid4()),
                            stage="run_attempt",
                            level="info",
                            message="Run attempt lease renewed",
                            created_at=renewed_at,
                            payload_json=json.dumps(
                                run_attempt_payload_v1(
                                    attempt_id=attempt_id,
                                    status=RunStatus.RUNNING.value,
                                    rq_job_id=attempt_queue_job_id,
                                    worker_id=os.environ.get("HOSTNAME"),
                                    lease_started_at=renewed_at,
                                    lease_expires_at=renewed_expires_at,
                                ),
                                ensure_ascii=False,
                            ),
                        ),
                        client=client,
                    )
                except Exception as inner:
                    logger.warning("[run_id=%s] Failed to renew run attempt lease: %s", run_id, inner)

            # ── Step 2: Read current row (reads cancel_requested_at + config snapshot)
            with observe_span(
                "run.resolve_context",
                attributes={
                    "run_id": run_id,
                    "backend_type": str(runtime.backend_type),
                },
            ):
                run_record = get_run(run_id, client=client)
                effective_config: dict[str, Any] | None = None
                if run_record and run_record.effective_settings_json:
                    try:
                        effective_config = json.loads(run_record.effective_settings_json)
                    except Exception as exc:
                        logger.warning("[run_id=%s] Failed to parse effective_settings_json: %s", run_id, exc)
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

                set_span_attributes(
                    {
                        "run_mode": run_mode,
                        "next_stage": next_stage,
                        "has_effective_config": effective_config is not None,
                        "has_replay_context": replay_context is not None,
                        "has_checkpoint_payload": checkpoint_payload is not None,
                        **build_langfuse_trace_attributes(
                            session_id=run_id,
                            user_id=str(getattr(run_record, "triggered_by", "") or "").strip() or None,
                            input_payload={
                                "run_id": run_id,
                                "jobs_path": str(getattr(run_record, "jobs_path", "") or jobs_path or ""),
                                "config_path": str(getattr(run_record, "config_path", "") or config_path or ""),
                                "run_mode": run_mode,
                                "next_stage": next_stage if run_mode == "manual_staged" else None,
                                "jobs_input_source": getattr(run_record, "jobs_input_source", None),
                                "candidate_profile_source": getattr(run_record, "candidate_profile_source", None),
                            },
                            metadata={
                                "scope": "control_plane_worker",
                                "backend_type": str(runtime.backend_type),
                                "trigger_source": getattr(run_record, "trigger_source", None),
                                "run_mode": run_mode,
                                "next_stage": next_stage,
                                "has_effective_config": effective_config is not None,
                                "has_replay_context": replay_context is not None,
                                "has_checkpoint_payload": checkpoint_payload is not None,
                                "jobs_input_source": getattr(run_record, "jobs_input_source", None),
                                "candidate_profile_source": getattr(run_record, "candidate_profile_source", None),
                            },
                            extra_attributes={
                                "langfuse.user.id": str(getattr(run_record, "triggered_by", "") or "").strip() or None,
                            },
                        ),
                    }
                )

            # ── Step 3: Early-exit if cancellation already requested ──────────────
            if run_record and run_record.cancel_requested_at is not None:
                logger.info("[run_id=%s] Cancellation already requested — exiting early", run_id)
                cancelled_at = datetime.datetime.now(datetime.timezone.utc)
                update_run_status(
                    run_id, RunStatus.CANCELLED, client=client,
                    finished_at=cancelled_at,
                )
                _persist_terminal_pipeline_snapshot(
                    run_id=run_id,
                    run_record=run_record,
                    summary={},
                    run_status=RunStatus.CANCELLED,
                    snapshot_at=cancelled_at,
                )
                append_event(
                    _run_cancelled_event(run_id, "Run cancelled before pipeline execution started"),
                    client=client,
                )
                set_span_attributes({"run_terminal_status": str(RunStatus.CANCELLED)})
                return

            # ── Step 4: Run pipeline with cooperative cancellation check ──────────
            reporter = PipelineReporter(run_id=run_id)

            def _cancellation_check() -> bool:
                """Lightweight re-read to check if cancel was requested mid-flight."""
                nonlocal _last_cancel_check_at, _last_cancel_check_result
                now = time.monotonic()
                if (now - _last_cancel_check_at) < 2.0:
                    return _last_cancel_check_result
                _last_cancel_check_at = now
                try:
                    current = get_run(run_id, client=client)
                    _last_cancel_check_result = current is not None and current.cancel_requested_at is not None
                    _maybe_renew_attempt_lease()
                except Exception:  # noqa: BLE001
                    # Cancellation is best-effort; if run state store is transiently unavailable,
                    # keep pipeline progressing instead of failing mid-run.
                    return _last_cancel_check_result
                return _last_cancel_check_result

            _last_cancel_check_at = 0.0
            _last_cancel_check_result = False

            reuse_policy_stages = ("ranking", "cv_analysis", "cv_generation", "synonym_triage")
            allow_checkpointed_sources = any(
                resolve_reuse_stage_policy(effective_config or {}, stage).source_scope == "succeeded_or_checkpointed"
                for stage in reuse_policy_stages
            )
            late_stage_reuse_snapshots = _collect_late_stage_reuse_snapshots(
                current_run_id=run_id,
                allow_checkpointed_sources=allow_checkpointed_sources,
                client=client,
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
                        client=client,
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
                            client=client,
                        )
                    except Exception as inner:
                        logger.warning(
                            "[run_id=%s] Failed to append stage progress persistence warning event: %s",
                            run_id,
                            inner,
                        )

            _verify_jobs_input_projection(run_record, jobs_path)

            with observe_span(
                "run.execute_pipeline",
                attributes={
                    "run_id": run_id,
                    "run_mode": run_mode,
                    "start_stage": next_stage if run_mode == "manual_staged" else None,
                    "stop_after_stage": next_stage if run_mode == "manual_staged" else None,
                },
            ):
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
                    preference_policy_resolver=_resolve_worker_preference_policy,
                )

            paused_after_stage = str(summary.get("paused_after_stage") or "").strip() or None
            if paused_after_stage is not None:
                checkpoint_time = datetime.datetime.now(datetime.timezone.utc)
                update_run_status(
                    run_id,
                    RunStatus.AWAITING_CONTINUE,
                    client=client,
                    summary=summary,
                )
                update_run_checkpoint(
                    run_id,
                    client=client,
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
                if isinstance(run_record, PipelineRun):
                    persist_pipeline_snapshot(
                        run_id,
                        summary,
                        run_status=RunStatus.AWAITING_CONTINUE,
                        snapshot_at=checkpoint_time,
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
                            prior_stage_transition_artifacts=getattr(
                                run_record,
                                "stage_transition_artifacts_json",
                                None,
                            ),
                            stages_completed_before_segment=list(
                                getattr(run_record, "completed_stages", None) or []
                            ),
                        ),
                        client=client,
                    )
                except Exception as exc:
                    logger.warning(
                        "[run_id=%s] Failed to persist stage transition artifacts snapshot at checkpoint: %s",
                        run_id,
                        exc,
                    )
                if _summary_has_reached_stage(summary, "enrich"):
                    try:
                        _persist_mapping_suggestions_snapshot(
                            run_id=run_id,
                            summary=summary,
                            created_at=checkpoint_time,
                            client=client,
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
                                client=client,
                            )
                        except Exception as inner:
                            logger.warning(
                                "[run_id=%s] Failed to append mapping suggestions persistence warning event: %s",
                                run_id,
                                inner,
                            )
                    if _synonym_propose_enabled_from_run_record(run_record):
                        try:
                            _persist_synonym_proposals_snapshot(
                                run_id=run_id,
                                run_record=run_record,
                                summary=summary,
                                created_at=checkpoint_time,
                                run_status=RunStatus.AWAITING_CONTINUE,
                                client=client,
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
                                    client=client,
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
                    client=client,
                )
                set_span_attributes({
                    "run_terminal_status": str(RunStatus.AWAITING_CONTINUE),
                    "paused_after_stage": paused_after_stage,
                })
                return

            # ── Step 5: Terminalize or park for review ───────────────────────────
            with observe_span(
                "run.finalize_status",
                attributes={
                    "run_id": run_id,
                    "run_mode": run_mode,
                },
            ):
                cv_debug_records = [
                    item for item in list(summary.get("cv_generation_debug_records") or [])
                    if isinstance(item, dict)
                ]
                auto_accept_enabled = _auto_accept_ai_action_enabled_from_run_record(run_record)
                auto_accepted_count = 0
                pending_review_required = 0
                pending_review_required_missing_job_url = 0
                review_reason_counts: dict[str, int] = {}
                for record in cv_debug_records:
                    if str(record.get("status") or "").strip() != "review_required":
                        continue
                    reason_code = _map_review_required_reason_code(record)
                    review_reason_counts[reason_code] = int(review_reason_counts.get(reason_code, 0)) + 1
                    if run_mode == "run_all" and auto_accept_enabled and reason_code in LOW_RISK_AUTO_ACCEPT_REASON_CODES:
                        auto_accepted_count += 1
                        continue
                    if not is_review_resolution_pending(record.get("resolution_status")):
                        continue
                    pending_review_required += 1
                    if not str(record.get("job_url") or "").strip():
                        pending_review_required_missing_job_url += 1
                summary["review_required_total"] = int(sum(review_reason_counts.values()))
                summary["review_required_auto_accepted"] = int(auto_accepted_count)
                summary["review_required_remaining"] = int(pending_review_required)
                summary["review_required_remaining_missing_job_url"] = int(pending_review_required_missing_job_url)
                summary["review_required_reason_counts"] = dict(review_reason_counts)
                current_determinism_index: dict[tuple[str, str], tuple[str, str]] = {}
                for record in cv_debug_records:
                    status_value = str(record.get("status") or "").strip()
                    if status_value not in {"accepted", "review_required", "validation_failed", "generation_failed", "persistence_failed"}:
                        continue
                    input_fp = str(record.get("cv_generation_input_fingerprint") or "").strip()
                    evidence_fp = str(record.get("validation_evidence_fingerprint") or "").strip()
                    job_url = str(record.get("job_url") or "").strip()
                    if not input_fp or not evidence_fp:
                        continue
                    current_determinism_index[(input_fp, evidence_fp)] = (status_value, job_url)

                if current_determinism_index:
                    try:
                        prior_runs = list_runs(
                            client=client,
                            include_archived=True,
                        )
                    except Exception:
                        prior_runs = []
                    mismatches: list[dict[str, str]] = []
                    for prior in prior_runs:
                        if str(getattr(prior, "run_id", "") or "").strip() == run_id:
                            continue
                        prior_debug_json = str(getattr(prior, "cv_generation_debug_json", "") or "").strip()
                        if not prior_debug_json:
                            continue
                        try:
                            prior_payload = json.loads(prior_debug_json)
                        except Exception:
                            continue
                        prior_records = list(prior_payload.get("debug_records") or prior_payload.get("cv_generation_debug_records") or [])
                        for prior_record in prior_records:
                            if not isinstance(prior_record, dict):
                                continue
                            prior_status = str(prior_record.get("status") or "").strip()
                            prior_input_fp = str(prior_record.get("cv_generation_input_fingerprint") or "").strip()
                            prior_evidence_fp = str(prior_record.get("validation_evidence_fingerprint") or "").strip()
                            if not prior_input_fp or not prior_evidence_fp:
                                continue
                            key = (prior_input_fp, prior_evidence_fp)
                            current = current_determinism_index.get(key)
                            if current is None:
                                continue
                            current_status, current_job_url = current
                            if current_status == prior_status:
                                continue
                            mismatches.append(
                                {
                                    "prior_run_id": str(getattr(prior, "run_id", "") or ""),
                                    "job_url": current_job_url,
                                    "input_fingerprint": prior_input_fp,
                                    "validation_evidence_fingerprint": prior_evidence_fp,
                                    "current_status": current_status,
                                    "prior_status": prior_status,
                                }
                            )
                            if len(mismatches) >= 10:
                                break
                        if len(mismatches) >= 10:
                            break
                    if mismatches:
                        append_event(
                            RunEvent(
                                run_id=run_id,
                                event_id=str(uuid.uuid4()),
                                stage="determinism_violation",
                                level="warning",
                                message=(
                                    "Determinism violation: same input+validation evidence fingerprint yielded "
                                    f"different terminal status in {len(mismatches)} case(s)."
                                ),
                                created_at=datetime.datetime.now(datetime.timezone.utc),
                                payload_json=json.dumps(
                                    {
                                        "mismatch_count": len(mismatches),
                                        "mismatches": mismatches,
                                    },
                                    ensure_ascii=False,
                                ),
                            ),
                            client=client,
                        )
                review_pending = pending_review_required > 0
                terminal_status = (
                    RunStatus.AWAITING_CONTINUE
                    if (review_pending and run_mode == "manual_staged")
                    else RunStatus.SUCCEEDED
                )
                finished_at = (
                    None
                    if terminal_status == RunStatus.AWAITING_CONTINUE
                    else datetime.datetime.now(datetime.timezone.utc)
                )
                set_span_attributes(
                    {
                        "review_required_total": int(sum(review_reason_counts.values())),
                        "review_required_remaining": int(pending_review_required),
                        "review_required_remaining_missing_job_url": int(pending_review_required_missing_job_url),
                        "run_terminal_status": str(terminal_status),
                    }
                )
                attempt_terminal_persisted = False
                try:
                    append_event(
                        RunEvent(
                            run_id=run_id,
                            event_id=str(uuid.uuid4()),
                            stage="run_attempt",
                            level="info",
                            message="Run attempt finished",
                            created_at=datetime.datetime.now(datetime.timezone.utc),
                            payload_json=json.dumps(
                                run_attempt_payload_v1(
                                    attempt_id=attempt_id,
                                    status=str(terminal_status.value),
                                    rq_job_id=attempt_queue_job_id,
                                    worker_id=os.environ.get("HOSTNAME"),
                                    finished_at=finished_at,
                                ),
                                ensure_ascii=False,
                            ),
                        ),
                        client=client,
                    )
                    attempt_terminal_persisted = True
                except Exception as inner:
                    logger.warning("[run_id=%s] Failed to append run attempt terminal event: %s", run_id, inner)

                if terminal_status == RunStatus.SUCCEEDED and not attempt_terminal_persisted:
                    update_run_status(
                        run_id,
                        RunStatus.FAILED,
                        client=client,
                        finished_at=datetime.datetime.now(datetime.timezone.utc),
                        summary=summary,
                        error_message="attempt_terminal_event_persist_failed",
                        error_stage="run_attempt_terminalization",
                    )
                    raise RuntimeError("attempt_terminal_event_persist_failed")

                if isinstance(run_record, PipelineRun):
                    persist_pipeline_snapshot(
                        run_id,
                        summary,
                        run_status=terminal_status,
                        snapshot_at=finished_at or datetime.datetime.now(datetime.timezone.utc),
                    )
                update_run_status(
                    run_id,
                    terminal_status,
                    client=client,
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
                        client=client,
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
                            message=(
                                f"Review required: {pending_review_required} CV item(s) pending operator action. "
                                f"Auto-accepted={auto_accepted_count}."
                            ),
                            created_at=datetime.datetime.now(datetime.timezone.utc),
                            payload_json=json.dumps(
                                {
                                    "review_required_total": int(sum(review_reason_counts.values())),
                                    "auto_accepted": int(auto_accepted_count),
                                    "remaining": int(pending_review_required),
                                    "remaining_missing_job_url": int(pending_review_required_missing_job_url),
                                    "reason_counts": dict(review_reason_counts),
                                },
                                ensure_ascii=False,
                            ),
                        ),
                        client=client,
                    )
                elif run_mode == "manual_staged":
                    update_run_checkpoint(
                        run_id,
                        client=client,
                        checkpoint_status="completed",
                        next_stage=None,
                        last_completed_stage="cv_generation",
                        completed_stages=completed_stages,
                        checkpoint_payload_json=None,
                    )
                else:
                    update_run_progress(
                        run_id,
                        client=client,
                        last_completed_stage="cv_generation",
                        completed_stages=completed_stages,
                    )
                export_results = list(summary.get("export_results") or [])
                artifact_snapshot_at = finished_at or datetime.datetime.now(datetime.timezone.utc)
                try:
                        update_run_results_export(
                            run_id,
                            _build_results_export_payload(
                                run_id=run_id,
                                run_record=run_record,
                                effective_config=effective_config,
                                summary=summary,
                                export_results=export_results,
                                finished_at=artifact_snapshot_at,
                                replay_context=replay_context,
                            ),
                            client=client,
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
                        client=client,
                    )
                except Exception as exc:
                    logger.warning("[run_id=%s] Failed to persist CV generation debug snapshot: %s", run_id, exc)
                try:
                    update_run_stage_transition_artifacts(
                        run_id,
                        _build_stage_transition_artifacts_payload(
                            run_id=run_id,
                            summary=summary,
                            finished_at=artifact_snapshot_at,
                            run_status=terminal_status,
                            prior_stage_transition_artifacts=getattr(
                                run_record,
                                "stage_transition_artifacts_json",
                                None,
                            ),
                            stages_completed_before_segment=list(
                                getattr(run_record, "completed_stages", None) or []
                            ),
                        ),
                        client=client,
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
                            finished_at=artifact_snapshot_at,
                            replay_context=replay_context,
                        ),
                        client=client,
                    )
                except Exception as exc:
                    logger.warning("[run_id=%s] Failed to persist settings-used snapshot: %s", run_id, exc)

                accepted_debug_count = sum(
                    1
                    for record in cv_debug_records
                    if str(record.get("status") or "").strip() == "accepted"
                )
                attempted_debug_count = sum(
                    1
                    for record in cv_debug_records
                    if str(record.get("status") or "").strip()
                    in {"accepted", "review_required", "validation_failed", "generation_failed", "persistence_failed"}
                )
                attempted_summary_count = int(summary.get("cv_generation_attempted") or 0)
                if attempted_summary_count > 0 and not cv_debug_records:
                    append_event(
                        RunEvent(
                            run_id=run_id,
                            event_id=str(uuid.uuid4()),
                            stage="artifact_persist_incomplete",
                            level="warning",
                            message="CV debug artifact empty despite CV generation terminal events.",
                            created_at=datetime.datetime.now(datetime.timezone.utc),
                        ),
                        client=client,
                    )
                if int(summary.get("cvs_generated") or 0) < accepted_debug_count:
                    append_event(
                        RunEvent(
                            run_id=run_id,
                            event_id=str(uuid.uuid4()),
                            stage="artifact_invariant_warning",
                            level="warning",
                            message=(
                                f"Accepted CV invariant mismatch: accepted_debug={accepted_debug_count}, "
                                f"cvs_generated={int(summary.get('cvs_generated') or 0)}"
                            ),
                            created_at=datetime.datetime.now(datetime.timezone.utc),
                        ),
                        client=client,
                    )

                persisted_run = get_run(run_id, client=client)
                missing_effective = not str(getattr(persisted_run, "effective_settings_json", "") or "").strip()
                missing_debug = not str(getattr(persisted_run, "cv_generation_debug_json", "") or "").strip()
                missing_settings_used = not str(getattr(persisted_run, "settings_used_json", "") or "").strip()
                missing_stage_artifacts = not str(getattr(persisted_run, "stage_transition_artifacts_json", "") or "").strip()
                if missing_effective or missing_debug or missing_settings_used or missing_stage_artifacts:
                    append_event(
                        RunEvent(
                            run_id=run_id,
                            event_id=str(uuid.uuid4()),
                            stage="artifact_persist_incomplete",
                            level="warning",
                            message=(
                                "Detected missing persisted artifacts; retrying once "
                                f"(effective={missing_effective}, cv_debug={missing_debug}, settings_used={missing_settings_used}, stage_artifacts={missing_stage_artifacts})."
                            ),
                            created_at=datetime.datetime.now(datetime.timezone.utc),
                        ),
                        client=client,
                    )
                    if missing_effective:
                        update_run_effective_settings(
                            run_id,
                            json.dumps(effective_config, ensure_ascii=False),
                            client=client,
                        )
                    if missing_debug:
                        update_run_cv_generation_debug(
                            run_id,
                            _build_cv_generation_debug_payload(
                                run_id=run_id,
                                run_record=run_record,
                                summary=summary,
                                finished_at=artifact_snapshot_at,
                            ),
                            client=client,
                        )
                    if missing_settings_used:
                        update_run_settings_used(
                            run_id,
                            _build_settings_used_payload(
                                run_id=run_id,
                                run_record=run_record,
                                effective_config=effective_config,
                                config_path=config_path,
                                finished_at=artifact_snapshot_at,
                                replay_context=replay_context,
                            ),
                            client=client,
                        )
                    if missing_stage_artifacts:
                        update_run_stage_transition_artifacts(
                            run_id,
                            _build_stage_transition_artifacts_payload(
                                run_id=run_id,
                                summary=summary,
                                finished_at=artifact_snapshot_at,
                                run_status=terminal_status,
                                prior_stage_transition_artifacts=getattr(
                                    run_record,
                                    "stage_transition_artifacts_json",
                                    None,
                                ),
                                stages_completed_before_segment=list(
                                    getattr(run_record, "completed_stages", None) or []
                                ),
                            ),
                            client=client,
                        )
                if _summary_has_reached_stage(summary, "enrich"):
                    snapshot_created_at = finished_at or datetime.datetime.now(datetime.timezone.utc)
                    try:
                        _persist_mapping_suggestions_snapshot(
                            run_id=run_id,
                            summary=summary,
                            created_at=snapshot_created_at,
                            client=client,
                        )
                    except Exception as exc:
                        logger.warning("[run_id=%s] Failed to persist mapping suggestions snapshot: %s", run_id, exc)
                        try:
                            append_event(
                                _snapshot_persist_failed_event(run_id, "mapping_suggestions", str(exc)),
                                client=client,
                            )
                        except Exception as inner:
                            logger.warning(
                                "[run_id=%s] Failed to append mapping suggestions persistence warning event: %s",
                                run_id,
                                inner,
                            )
                    if _synonym_propose_enabled_from_run_record(run_record):
                        try:
                            _persist_synonym_proposals_snapshot(
                                run_id=run_id,
                                run_record=run_record,
                                summary=summary,
                                created_at=snapshot_created_at,
                                run_status=terminal_status,
                                client=client,
                            )
                        except Exception as exc:
                            logger.warning("[run_id=%s] Failed to persist synonym proposals snapshot: %s", run_id, exc)
                            try:
                                append_event(
                                    _snapshot_persist_failed_event(run_id, "synonym_proposals", str(exc)),
                                    client=client,
                                )
                            except Exception as inner:
                                logger.warning(
                                    "[run_id=%s] Failed to append synonym proposals persistence warning event: %s",
                                    run_id,
                                    inner,
                                )
                try:
                    persist_terminal_run_artifact_mirror(run_id=run_id)
                except Exception as mirror_exc:
                    logger.warning("[run_id=%s] Failed to persist terminal artifact mirror: %s", run_id, mirror_exc)

        except PipelineCancelled as exc:
            # ── Step 5 (alt): Pipeline was cancelled at a checkpoint ──────────────
            logger.info("[run_id=%s] Pipeline cancelled at checkpoint: %s", run_id, exc)
            cancelled_at = datetime.datetime.now(datetime.timezone.utc)
            set_span_attributes({"run_terminal_status": str(RunStatus.CANCELLED)})
            update_run_status(
                run_id, RunStatus.CANCELLED, client=client,
                finished_at=cancelled_at,
                summary=summary if isinstance(summary, dict) else None,
            )
            try:
                append_event(
                    RunEvent(
                        run_id=run_id,
                        event_id=str(uuid.uuid4()),
                        stage="run_attempt",
                        level="info",
                        message="Run attempt cancelled",
                        created_at=cancelled_at,
                        payload_json=json.dumps(
                            run_attempt_payload_v1(
                                attempt_id=attempt_id,
                                status=RunStatus.CANCELLED.value,
                                rq_job_id=attempt_queue_job_id,
                                worker_id=os.environ.get("HOSTNAME"),
                                finished_at=cancelled_at,
                                error_classification="canceled",
                                error_summary="cancel_requested",
                                retry_eligible=False,
                            ),
                            ensure_ascii=False,
                        ),
                    ),
                    client=client,
                )
            except Exception as inner:
                logger.warning("[run_id=%s] Failed to append run attempt cancelled event: %s", run_id, inner)
            if isinstance(summary, dict) and summary:
                try:
                    _persist_shared_progress_snapshot(
                        run_id=run_id,
                        run_record=run_record,
                        summary=summary,
                        snapshot_at=cancelled_at,
                        client=client,
                        run_status=RunStatus.CANCELLED,
                    )
                except Exception as persist_exc:
                    logger.warning(
                        "[run_id=%s] Failed to persist partial progress snapshot for cancelled run: %s",
                        run_id,
                        persist_exc,
                    )
            else:
                try:
                    _persist_terminal_pipeline_snapshot(
                        run_id=run_id,
                        run_record=run_record,
                        summary={},
                        run_status=RunStatus.CANCELLED,
                        snapshot_at=cancelled_at,
                    )
                except Exception as persist_exc:
                    logger.warning(
                        "[run_id=%s] Failed to terminalize normalized cancelled run: %s",
                        run_id,
                        persist_exc,
                    )
            try:
                append_event(
                    _run_cancelled_event(run_id, f"Run cancelled at pipeline checkpoint: {exc}"),
                    client=client,
                )
            except Exception as inner:
                logger.warning("[run_id=%s] Failed to write cancellation event: %s", run_id, inner)
            try:
                persist_terminal_run_artifact_mirror(run_id=run_id)
            except Exception as mirror_exc:
                logger.warning("[run_id=%s] Failed to persist terminal artifact mirror: %s", run_id, mirror_exc)

        except Exception as exc:
            # ── Step 7: Unexpected pipeline failure ───────────────────────────────
            logger.exception("[run_id=%s] Pipeline failed: %s", run_id, exc)
            failed_at = datetime.datetime.now(datetime.timezone.utc)
            set_span_attributes({
                "run_terminal_status": str(RunStatus.FAILED),
                "error.message": str(exc),
            })
            update_run_status(
                run_id, RunStatus.FAILED, client=client,
                finished_at=failed_at,
                summary=summary if isinstance(summary, dict) else None,
                error_message=str(exc),
                error_stage=(
                    "jobs_input_integrity"
                    if isinstance(exc, JobsInputIntegrityError)
                    else None
                ),
            )
            try:
                classification = classify_exception_for_retry(exc)
                append_event(
                    RunEvent(
                        run_id=run_id,
                        event_id=str(uuid.uuid4()),
                        stage="run_attempt",
                        level="error",
                        message="Run attempt failed",
                        created_at=failed_at,
                        payload_json=json.dumps(
                            run_attempt_payload_v1(
                                attempt_id=attempt_id,
                                status=RunStatus.FAILED.value,
                                rq_job_id=attempt_queue_job_id,
                                worker_id=os.environ.get("HOSTNAME"),
                                finished_at=failed_at,
                                error_classification=classification.classification,
                                error_summary=classification.summary,
                                error_details=classification.details,
                                error_details_max_chars=settings.error_detail_limit,
                                retry_eligible=(classification.classification in {"transient", "unknown"}),
                            ),
                            ensure_ascii=False,
                        ),
                    ),
                    client=client,
                )
            except Exception as inner:
                logger.warning("[run_id=%s] Failed to append run attempt failed event: %s", run_id, inner)
            if isinstance(summary, dict) and summary:
                try:
                    _persist_shared_progress_snapshot(
                        run_id=run_id,
                        run_record=run_record,
                        summary=summary,
                        snapshot_at=failed_at,
                        client=client,
                        run_status=RunStatus.FAILED,
                    )
                except Exception as persist_exc:
                    logger.warning(
                        "[run_id=%s] Failed to persist partial progress snapshot for failed run: %s",
                        run_id,
                        persist_exc,
                    )
            else:
                try:
                    _persist_terminal_pipeline_snapshot(
                        run_id=run_id,
                        run_record=run_record,
                        summary={},
                        run_status=RunStatus.FAILED,
                        snapshot_at=failed_at,
                    )
                except Exception as persist_exc:
                    logger.warning(
                        "[run_id=%s] Failed to terminalize normalized failed run: %s",
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
                    client=client,
                )
            except Exception as inner:
                logger.warning("[run_id=%s] Failed to write failure event: %s", run_id, inner)
            try:
                persist_terminal_run_artifact_mirror(run_id=run_id)
            except Exception as mirror_exc:
                logger.warning("[run_id=%s] Failed to persist terminal artifact mirror: %s", run_id, mirror_exc)



























