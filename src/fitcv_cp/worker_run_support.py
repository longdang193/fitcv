"""@meta
name: worker_run_support
type: module
domain: run_orchestration
ownership: infrastructure
responsibility:
  - Hold extracted worker snapshot/settings/synonym payload helpers shared by control-plane worker entrypoints.
inputs:
  - run records, effective config payloads, and pipeline summary snapshots
outputs:
  - persisted worker payloads for settings-used, stage artifacts, and mapping/synonym support
lifecycle:
  - status: active
"""

import datetime
import hashlib
import json
from typing import Any

from fitcv.config import get_stage_runtime_concurrency, get_stage_runtime_sleep_secs
from fitcv.contracts import (
    MAPPING_SUGGESTIONS_SCHEMA_VERSION,
    SETTINGS_USED_SCHEMA_VERSION,
    STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION,
)
from fitcv_cp.backend_runtime import resolve_backend_runtime_or_active
from fitcv_cp.data_plane import data_plane_contract_payload
from fitcv_cp.models import RunStatus
from fitcv_cp.run_artifact_contracts import (
    decode_json_object_or_none,
    encode_json_object,
    json_safe,
    replay_context_payload,
    require_payload_keys,
)
from fitcv_cp.synonym_proposals import (
    build_builtin_synonym_triage_recommendation,
    resolve_synonym_management_mode,
)

_SETTINGS_COMPATIBILITY_KEYS = {
    "vector_top_n",
    "rerank_top_n",
    "cv_generation_model",
    "prompt_version",
    "cv_max_pages",
    "required_cv_sections",
}




def _build_stage_transition_artifacts_payload_dict(
    *,
    run_id: str,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
    run_status: RunStatus = RunStatus.SUCCEEDED,
    degradation_reason: str | None = None,
    prior_stage_transition_artifacts: dict[str, Any] | str | None = None,
    stages_completed_before_segment: list[str] | None = None,
) -> dict[str, Any]:
    stage_artifacts = dict(summary.get("stage_transition_artifacts") or {})
    prior_payload = (
        decode_json_object_or_none(prior_stage_transition_artifacts)
        if isinstance(prior_stage_transition_artifacts, str)
        else prior_stage_transition_artifacts
    )
    prior_root = dict(prior_payload or {})
    if isinstance(prior_root.get("artifacts"), dict):
        prior_root = dict(prior_root["artifacts"])
    prior_stages = prior_root.get("stages")
    current_stages = stage_artifacts.get("stages")
    if isinstance(prior_stages, dict) and isinstance(current_stages, dict):
        merged_stages = dict(current_stages)
        for stage_id in list(stages_completed_before_segment or []):
            if stage_id in prior_stages:
                merged_stages[stage_id] = prior_stages[stage_id]
        stage_artifacts["stages"] = merged_stages
    snapshot_complete = bool(stage_artifacts) and run_status == RunStatus.SUCCEEDED
    resolved_reason = (
        str(degradation_reason or "").strip()
        or ("partial_snapshot_non_terminal_success" if run_status != RunStatus.SUCCEEDED else "")
    )
    return {
        "run_id": run_id,
        "status": run_status.value,
        "artifact_schema_version": STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION,
        "schema_version": STAGE_TRANSITION_ARTIFACTS_RUN_SCHEMA_VERSION,
        "created_at": finished_at.isoformat(),
        "snapshot_complete": snapshot_complete,
        "degradation_reason": resolved_reason,
        "artifacts": stage_artifacts,
    }

def _build_stage_transition_artifacts_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
    run_status: RunStatus = RunStatus.SUCCEEDED,
    degradation_reason: str | None = None,
    prior_stage_transition_artifacts: dict[str, Any] | str | None = None,
    stages_completed_before_segment: list[str] | None = None,
) -> str:
    return encode_json_object(
        _build_stage_transition_artifacts_payload_dict(
            run_id=run_id,
            summary=summary,
            finished_at=finished_at,
            run_status=run_status,
            degradation_reason=degradation_reason,
            prior_stage_transition_artifacts=prior_stage_transition_artifacts,
            stages_completed_before_segment=stages_completed_before_segment,
        )
    )


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
        "schema_version": "manual_checkpoint_v1",
        "created_at": created_at.isoformat(),
        "paused_after_stage": summary.get("paused_after_stage"),
        "next_stage": summary.get("next_stage"),
        "completed_stages": list(summary.get("completed_stages") or []),
        "checkpoint_payload": summary.get("checkpoint_payload") or {},
        "replay_context": replay_context_payload(replay_context=replay_context, run_id=run_id),
    }
    require_payload_keys(
        payload,
        required_keys={"run_id", "schema_version", "created_at", "replay_context"},
        context="manual_checkpoint_payload",
    )
    return encode_json_object(payload)


def _build_settings_used_payload_dict(
    *,
    run_id: str,
    run_record: Any,
    effective_config: dict[str, Any] | None,
    config_path: str,
    finished_at: datetime.datetime,
    replay_context: dict[str, Any],
) -> dict[str, Any]:
    effective_settings = dict(effective_config or {})

    def _materialize_stage_runtime_snapshot(settings: dict[str, Any]) -> None:
        """Persist canonical stage_runtime values in settings-used snapshots."""
        stage_runtime = dict(settings.get("stage_runtime") or {})

        def _stage_block(stage: str) -> dict[str, Any]:
            block = dict(stage_runtime.get(stage) or {})
            stage_runtime[stage] = block
            return block

        enrich = _stage_block("enrich")
        if "sleep_secs" not in enrich:
            enrich["sleep_secs"] = settings.get("enrichment_sleep_secs", 0.5)
        if "batch_size" not in enrich:
            enrich["batch_size"] = settings.get("enrichment_batch_size", 10)
        if "concurrency" not in enrich:
            enrich["concurrency"] = settings.get("enrichment_concurrency", 1)

        ranking = _stage_block("ranking")
        if "sleep_secs" not in ranking:
            ranking["sleep_secs"] = get_stage_runtime_sleep_secs(
                settings,
                stage="ranking",
                default=0.5,
                compatibility_fallback_key="rerank_sleep_secs",
            )
        if "concurrency" not in ranking:
            ranking["concurrency"] = get_stage_runtime_concurrency(
                settings,
                stage="ranking",
                default=1,
            )

        cv_analysis = _stage_block("cv_analysis")
        cv_analysis.setdefault("sleep_secs", 0.0)
        cv_analysis.setdefault("concurrency", 1)

        cv_generation = _stage_block("cv_generation")
        cv_generation.setdefault("sleep_secs", 0.0)
        cv_generation.setdefault("concurrency", 1)

        settings["stage_runtime"] = stage_runtime

    _materialize_stage_runtime_snapshot(effective_settings)
    cv_settings = dict(effective_settings.get("cv") or {})
    cv_settings.pop("agentic_late_stage", None)
    effective_settings["cv"] = cv_settings
    sqlite_mode = resolve_backend_runtime_or_active().backend_type == "sqlite"
    compatibility_projection = {
        key: effective_settings.pop(key)
        for key in list(effective_settings.keys())
        if key in _SETTINGS_COMPATIBILITY_KEYS
    }
    payload = {
        "run_id": run_id,
        "settings_schema_version": SETTINGS_USED_SCHEMA_VERSION,
        "schema_version": SETTINGS_USED_SCHEMA_VERSION,
        "created_at": finished_at.isoformat(),
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
        "replay_context": replay_context_payload(replay_context=replay_context, run_id=run_id),
    }
    if sqlite_mode:
        data_plane = dict(payload.get("data_plane") or {})
        data_plane["state_backend"] = "sqlite"
        if str(data_plane.get("artifact_backend") or "").strip().lower() == "":
            data_plane["artifact_backend"] = "sqlite_json"
        payload["data_plane"] = data_plane
    if compatibility_projection:
        payload["compatibility_projection"] = compatibility_projection
    require_payload_keys(
        payload,
        required_keys={"run_id", "schema_version", "created_at", "effective_settings", "data_plane"},
        context="settings_used_payload",
    )
    return payload

def _build_settings_used_payload(
    *,
    run_id: str,
    run_record: Any,
    effective_config: dict[str, Any] | None,
    config_path: str,
    finished_at: datetime.datetime,
    replay_context: dict[str, Any],
) -> str:
    return encode_json_object(
        json_safe(
            _build_settings_used_payload_dict(
                run_id=run_id,
                run_record=run_record,
                effective_config=effective_config,
                config_path=config_path,
                finished_at=finished_at,
                replay_context=replay_context,
            )
        )
    )


def _build_mapping_suggestions_payload(
    *,
    run_id: str,
    summary: dict[str, Any],
    created_at: datetime.datetime,
) -> str:
    payload = {
        "run_id": run_id,
        "mapping_suggestions_schema_version": MAPPING_SUGGESTIONS_SCHEMA_VERSION,
        "schema_version": MAPPING_SUGGESTIONS_SCHEMA_VERSION,
        "created_at": created_at.isoformat(),
        "suggestions": list(summary.get("mapping_suggestions") or []),
    }
    require_payload_keys(
        payload,
        required_keys={"run_id", "schema_version", "created_at", "suggestions"},
        context="mapping_suggestions_payload",
    )
    return encode_json_object(payload)



def _effective_skill_synonyms_from_run_record(run_record: Any) -> dict[str, str]:
    settings_payload = _effective_settings_payload_from_run_record(run_record)
    if not settings_payload:
        return {}
    raw_synonyms = settings_payload.get("skill_synonyms")
    if not isinstance(raw_synonyms, dict):
        return {}
    return {
        str(alias).strip().lower(): str(canonical).strip().lower()
        for alias, canonical in raw_synonyms.items()
        if str(alias).strip() and str(canonical).strip()
    }


def _effective_settings_payload_from_run_record(run_record: Any) -> dict[str, Any] | None:
    if run_record is None:
        return None
    raw_payload = getattr(run_record, "effective_settings_json", None)
    if not raw_payload:
        return None
    return decode_json_object_or_none(str(raw_payload))

def _synonym_propose_enabled_from_run_record(run_record: Any) -> bool:
    return bool(_synonym_management_mode_from_run_record(run_record).get("propose_enabled", True))


def _auto_accept_ai_action_enabled_from_run_record(run_record: Any) -> bool:
    return bool(_synonym_management_mode_from_run_record(run_record).get("auto_accept_ai_action_enabled", True))

def _synonym_management_mode_from_run_record(run_record: Any) -> dict[str, bool]:
    settings_payload = _effective_settings_payload_from_run_record(run_record)
    # Keep worker policy flags fully sourced from shared synonym policy resolver.
    return resolve_synonym_management_mode(settings_payload)

def _triage_synonym_proposal_recommendation_builtin(proposal: dict[str, Any], *, now_iso: str) -> dict[str, Any]:
    return build_builtin_synonym_triage_recommendation(proposal, now_iso=now_iso)
