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
from fitcv_cp.synonym_proposals import resolve_synonym_management_mode

_SETTINGS_COMPATIBILITY_KEYS = {
    "vector_top_n",
    "rerank_top_n",
    "cv_generation_model",
    "prompt_version",
    "cv_max_pages",
    "required_cv_sections",
}


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
        normalized = dict(existing_payload)
        normalized["late_stage_mode"] = "agentic"
        normalized["agentic_late_stage_enabled"] = True
        normalized["mode_source"] = "cv.agentic_late_stage.unified_runtime"
        normalized["agentic_status"] = "completed"
        return normalized
    _ = _config_agentic_late_stage_enabled(effective_config)
    return {
        "late_stage_mode": "agentic",
        "agentic_late_stage_enabled": True,
        "mode_source": "cv.agentic_late_stage.unified_runtime",
        "agentic_status": "completed",
    }

def _build_stage_transition_artifacts_payload_dict(
    *,
    run_id: str,
    summary: dict[str, Any],
    finished_at: datetime.datetime,
    run_status: RunStatus = RunStatus.SUCCEEDED,
    degradation_reason: str | None = None,
) -> dict[str, Any]:
    stage_artifacts = dict(summary.get("stage_transition_artifacts") or {})
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
) -> str:
    return encode_json_object(
        _build_stage_transition_artifacts_payload_dict(
            run_id=run_id,
            summary=summary,
            finished_at=finished_at,
            run_status=run_status,
            degradation_reason=degradation_reason,
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
    alias = str(proposal.get("alias") or "").strip().lower()
    canonical = str(proposal.get("canonical") or "").strip().lower()
    confidence = float(proposal.get("confidence") or 0.0)
    candidate_canonicals = [
        str(item).strip().lower()
        for item in list(proposal.get("candidate_canonicals") or [])
        if str(item).strip()
    ]
    risk_flags: list[str] = []
    rationale = "Alias/canonical pair appears stable for run-scoped overlay."
    recommended_action = "approve"
    recommendation_confidence = min(max(confidence, 0.0), 1.0)

    if not alias or not canonical:
        recommended_action = "reject"
        recommendation_confidence = 0.98
        rationale = "Alias or canonical is empty after normalization."
        risk_flags.append("invalid_mapping_shape")
    elif len(set(candidate_canonicals)) > 1:
        recommended_action = "defer"
        recommendation_confidence = max(0.55, min(confidence, 0.85))
        rationale = "Alias maps to multiple canonical candidates; review conflict manually."
        risk_flags.append("alias_canonical_conflict")
    elif confidence < 0.50:
        recommended_action = "reject"
        recommendation_confidence = min(0.95, 1.0 - confidence + 0.2)
        rationale = "Low confidence mapping is likely noisy and should be rejected."
        risk_flags.append("low_confidence")
    elif confidence < 0.75:
        recommended_action = "defer"
        recommendation_confidence = min(0.85, confidence + 0.1)
        rationale = "Moderate confidence mapping should be deferred for review."
        risk_flags.append("moderate_confidence")

    return {
        "recommended_action": recommended_action,
        "recommendation_confidence": round(float(recommendation_confidence), 3),
        "recommendation_rationale": rationale,
        "recommendation_risk_flags": risk_flags,
        "recommendation_runtime": {
            "provider": "fitcv_builtin",
            "model": "synonym_triage_v1",
            "wire_api": "builtin",
            "triage_at": now_iso,
            "triage_version": "synonym_triage_v1",
        },
    }
