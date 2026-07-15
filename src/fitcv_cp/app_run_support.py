"""@meta
name: app_run_support
type: module
domain: admin_ui
ownership: infrastructure
responsibility:
  - Hold extracted review/debug/export helper shaping shared by control-plane app routes.
inputs:
  - pipeline run records and persisted run-scoped payload JSON
outputs:
  - normalized review/debug/export payloads for control-plane surfaces
lifecycle:
  - status: active
"""

import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.review_identity import (
    ensure_review_item_id,
    is_review_resolution_pending,
    normalize_review_resolution_status,
)
from fitcv_cp.run_artifact_contracts import decode_json_object_or_none

GERMANY_TZ = ZoneInfo("Europe/Berlin")


def _load_json_object(raw_payload: str | None) -> dict[str, Any] | None:
    return decode_json_object_or_none(raw_payload)


def _load_run_cv_generation_debug_payload(run: PipelineRun) -> dict[str, Any] | None:
    payload = _load_json_object(run.cv_generation_debug_json)
    if not isinstance(payload, dict):
        return None
    copied = dict(payload)
    records = [
        item
        for item in list(copied.get("debug_records") or copied.get("cv_generation_debug_records") or [])
        if isinstance(item, dict)
    ]
    normalized_records: list[dict[str, Any]] = []
    run_id_value = str(getattr(run, "run_id", "") or payload.get("run_id") or "")
    for index, record in enumerate(records):
        row = dict(record)
        if str(row.get("status") or "").strip() == "review_required":
            ensure_review_item_id(
                run_id=run_id_value,
                record=row,
                fallback_index=index + 1,
            )
        ranking_fit_label = row.get("ranking_fit_label")
        reranker_fit_label = row.get("reranker_fit_label")
        if ranking_fit_label is None and reranker_fit_label is not None:
            row["ranking_fit_label"] = reranker_fit_label
        if reranker_fit_label is None and ranking_fit_label is not None:
            row["reranker_fit_label"] = ranking_fit_label
        normalized_records.append(row)
    if "debug_records" in copied:
        copied["debug_records"] = normalized_records
    if "cv_generation_debug_records" in copied:
        copied["cv_generation_debug_records"] = normalized_records
    return copied

def _run_status_allows_export(run: PipelineRun) -> bool:
    if run.status == RunStatus.SUCCEEDED:
        return True
    return run.status == RunStatus.AWAITING_CONTINUE and str(run.checkpoint_status or "").strip() == "awaiting_review"


def _is_hitl_review_pending_state(run: PipelineRun) -> bool:
    return (
        run.status in {RunStatus.AWAITING_CONTINUE, RunStatus.SUCCEEDED}
        and str(run.checkpoint_status or "").strip() == "awaiting_review"
    )


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

def _extract_unsupported_requirements(record: dict[str, Any]) -> list[str]:
    gap_summary = dict(record.get("gap_summary") or {})
    structured_missing = [
        str(item).strip()
        for item in list(gap_summary.get("missing") or [])
        if str(item).strip()
    ]
    if structured_missing:
        return structured_missing

    message = str((dict(record.get("error") or {})).get("message") or "").strip()
    marker = "Unsupported requirements require review:"
    if marker not in message:
        return []
    suffix = message.split(marker, 1)[1].strip()
    if not suffix:
        return []
    guidance_marker = ". Review the generated CV output"
    if guidance_marker in suffix:
        suffix = suffix.split(guidance_marker, 1)[0].strip()
    parsed = [item.strip() for item in suffix.split(",") if item.strip()]
    banned_tokens = ("approve", "regenerate", "reject", "review the generated cv output")
    cleaned: list[str] = []
    for token in parsed:
        lowered = token.lower()
        if any(banned in lowered for banned in banned_tokens):
            continue
        cleaned.append(token)
    return cleaned

def _review_target_for_reason_code(reason_code: str) -> str:
    if reason_code == "unsupported_requirement_gap":
        return "requirements_alignment"
    if reason_code in {"quality_gate_failed", "validation_guardrail_failed"}:
        return "cv_output"
    if reason_code == "evidence_coverage_insufficient":
        return "cv_output"
    if reason_code == "provider_response_unusable":
        return "other"
    return "other"

def _operator_prompt_for_review_required(
    *,
    reason_code: str,
    unsupported_requirements: list[str],
) -> str:
    if reason_code == "unsupported_requirement_gap":
        missing = ", ".join(unsupported_requirements[:6]) if unsupported_requirements else "listed requirements"
        return (
            "Review the generated CV output against required stack coverage "
            f"({missing}), then choose approve as-is, regenerate once, or reject."
        )
    if reason_code in {"quality_gate_failed", "validation_guardrail_failed"}:
        return "Review CV output quality/guardrail issues, then choose approve as-is, regenerate once, or reject."
    if reason_code == "evidence_coverage_insufficient":
        return "Review whether evidence coverage is acceptable, then choose approve as-is, regenerate once, or reject."
    return "Review this CV outcome and choose approve as-is, regenerate once, or reject."

def load_cv_generation_trace_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    current = payload.get("cv_generation_trace")
    if isinstance(current, dict):
        return dict(current)
    historical = payload.get("agentic_live_trace")
    if isinstance(historical, dict):
        return dict(historical)
    return None


def _latest_llm_runtime_provenance(record: dict[str, Any]) -> dict[str, Any]:
    observations = list(record.get("llm_runtime_observations") or [])
    for observation in reversed(observations):
        if not isinstance(observation, dict):
            continue
        evidence = observation.get("evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("provenance"), dict):
            return dict(evidence["provenance"])
    return {}


def _extract_review_required_request_id(record: dict[str, Any]) -> str | None:
    runtime_provenance = _latest_llm_runtime_provenance(record)
    for key in ("request_id", "response_id"):
        value = str(runtime_provenance.get(key) or "").strip()
        if value:
            return value
    trace = dict(record.get("cv_generation_trace") or {})
    for attempt in list(trace.get("attempts") or []):
        if not isinstance(attempt, dict):
            continue
        for key in ("request_id", "response_id"):
            value = str(attempt.get(key) or "").strip()
            if value:
                return value
    return None


def _normalized_cv_debug_payload_for_export(run: PipelineRun) -> dict[str, Any] | None:
    payload = _load_run_cv_generation_debug_payload(run)
    if not isinstance(payload, dict):
        return None
    copied = dict(payload)
    records = [item for item in list(copied.get("debug_records") or copied.get("cv_generation_debug_records") or []) if isinstance(item, dict)]
    normalized_records: list[dict[str, Any]] = []
    run_id_value = str(getattr(run, "run_id", "") or payload.get("run_id") or "")
    for index, record in enumerate(records):
        row = dict(record)
        if str(row.get("status") or "").strip() == "review_required":
            ensure_review_item_id(
                run_id=run_id_value,
                record=row,
                fallback_index=index + 1,
            )
        ranking_fit_label = row.get("ranking_fit_label")
        reranker_fit_label = row.get("reranker_fit_label")
        if ranking_fit_label is None and reranker_fit_label is not None:
            row["ranking_fit_label"] = reranker_fit_label
        if reranker_fit_label is None and ranking_fit_label is not None:
            row["reranker_fit_label"] = ranking_fit_label
        if str(row.get("status") or "").strip() == "review_required":
            row["review_required_reason_code"] = _map_review_required_reason_code(row)
        normalized_records.append(row)
    if "debug_records" in copied:
        copied["debug_records"] = normalized_records
    if "cv_generation_debug_records" in copied:
        copied["cv_generation_debug_records"] = normalized_records
    return copied

def _build_cv_generation_review_required_payload(run: PipelineRun) -> dict[str, Any] | None:
    payload = _load_run_cv_generation_debug_payload(run)
    if not isinstance(payload, dict):
        return None
    records = [item for item in list(payload.get("debug_records") or payload.get("cv_generation_debug_records") or []) if isinstance(item, dict)]

    rows: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("status") or "").strip() != "review_required":
            continue
        reason_code = _map_review_required_reason_code(record)
        unsupported_requirements = _extract_unsupported_requirements(record)
        rows.append(
            {
                "job_url": str(record.get("job_url") or ""),
                "job_title": str(record.get("job_title") or ""),
                "reason_code": reason_code,
                "review_target": _review_target_for_reason_code(reason_code),
                "operator_prompt": _operator_prompt_for_review_required(
                    reason_code=reason_code,
                    unsupported_requirements=unsupported_requirements,
                ),
                "unsupported_requirements": unsupported_requirements,
                "generated_draft_present": bool(str(record.get("markdown_final") or "").strip()),
                "accepted_cv_artifact_present": False,
                "attempt_count": int(record.get("attempt_count") or 1),
                "failed_rule_ids": list(record.get("failed_rule_ids") or []),
                "first_failing_section_key": record.get("first_failing_section_key"),
                "operator_note": record.get("operator_note"),
                "provider_name": str(_latest_llm_runtime_provenance(record).get("provider") or ""),
                "model_name": str(record.get("cv_generation_model") or ""),
                "request_id": _extract_review_required_request_id(record),
            }
        )
    if not rows:
        return None
    return {
        "run_id": run.run_id,
        "schema_version": "cv_generation_review_required_v1",
        "rows": rows,
    }


def _build_ranked_cv_outcome_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "ranked_total": 0,
        "ranked_cv_created_count": 0,
        "ranked_fit_gated_count": 0,
        "ranked_review_required_count": 0,
        "ranked_generation_failed_count": 0,
        "ranked_other_no_cv_count": 0,
    }
    for row in rows:
        if row.get("rank") is None:
            continue
        summary["ranked_total"] += 1
        pipeline_status = str(row.get("pipeline_status") or "").strip()
        stage_owned_subreason = str(row.get("stage_owned_subreason") or "").strip()
        cv_gen_status = str((((row.get("decision_chain") or {}).get("cv_generation") or {}).get("status")) or "").strip()
        if pipeline_status == "ranked_with_cv":
            summary["ranked_cv_created_count"] += 1
        elif pipeline_status in {"ranked_blocked_by_reranker_fit", "ranked_skipped_fit_gate"}:
            summary["ranked_fit_gated_count"] += 1
        elif pipeline_status == "ranked_no_cv" and (
            stage_owned_subreason == "review_required" or cv_gen_status == "review_required"
        ):
            summary["ranked_review_required_count"] += 1
        elif pipeline_status == "ranked_no_cv" and (
            stage_owned_subreason in {"validation_failed", "generation_failed", "persistence_failed"}
            or cv_gen_status in {"validation_failed", "generation_failed", "persistence_failed"}
        ):
            summary["ranked_generation_failed_count"] += 1
        elif pipeline_status == "ranked_no_cv":
            # Preserve stage-owned "no CV yet" versus "CV generation failed"
            # truth in summary counters for run detail.
            summary["ranked_other_no_cv_count"] += 1
        else:
            summary["ranked_other_no_cv_count"] += 1
    return summary


def _build_cv_generation_failure_reason_summary(run: PipelineRun) -> dict[str, Any]:
    payload = _load_run_cv_generation_debug_payload(run)
    if not isinstance(payload, dict):
        return {"total_failed": 0, "reason_rows": []}
    records = [
        item
        for item in list(payload.get("debug_records") or payload.get("cv_generation_debug_records") or [])
        if isinstance(item, dict)
    ]
    reason_counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status") or "").strip()
        if status not in {"generation_failed", "persistence_failed", "validation_failed"}:
            continue
        error_payload = record.get("error") if isinstance(record.get("error"), dict) else {}
        error_stage = str(error_payload.get("stage") or "").strip()
        error_message = str(error_payload.get("message") or "").strip()
        if error_stage or error_message:
            reason_label = f"{error_stage}: {error_message}".strip(": ").strip()
        else:
            reason_label = status
        reason_counts[reason_label] = int(reason_counts.get(reason_label, 0)) + 1
    reason_rows = [
        {"reason": reason, "count": count}
        for reason, count in reason_counts.items()
    ]
    reason_rows.sort(key=lambda row: (-int(row["count"]), str(row["reason"])))
    return {
        "total_failed": int(sum(reason_counts.values())),
        "reason_rows": reason_rows,
    }

def _format_compact_utc_timestamp(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        germany_value = parsed.astimezone(GERMANY_TZ)
        return germany_value.strftime("%d.%m.%Y %H:%M %Z")
    except ValueError:
        return raw

def _fit_classification_badge_class(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"stretch", "strong"}:
        return "badge-info"
    if normalized in {"target", "good"}:
        return "badge-success"
    return "badge-neutral"

_TRUNCATED_MARKDOWN_SENTINELS = (
    "...[truncated]",
    "...[truncated in review queue]",
)


def _normalize_hitl_resolution_status(action_name: str | None, explicit_status: str | None) -> str:
    return normalize_review_resolution_status(action_name, explicit_status)

def _is_hitl_resolution_pending(resolution_status: str | None) -> bool:
    return is_review_resolution_pending(resolution_status)
