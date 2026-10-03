"""@meta
name: run_artifact_contracts
type: module
domain: run_orchestration
ownership: infrastructure
responsibility:
  - Provide shared SSOT helper contracts for run artifact payload construction.
inputs:
  - run records, replay context, and runtime artifact values
outputs:
  - normalized run-mode labels and JSON-safe artifact payload fragments
  - shared JSON decode helpers for run artifacts
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
import hashlib
import json as _json
import re
from typing import Any

RUN_MODE_LABELS = {
    "run_all": "Run All",
    "manual_staged": "Stage by Stage",
}

RUN_ATTEMPT_SCHEMA_VERSION = "run_attempt.v1"
ACCEPTED_CV_ARTIFACT_SCHEMA_VERSION = "accepted_cv_artifact.v1"
ACCEPTED_CV_FAILURE_CATEGORIES = (
    "unsupported_claim",
    "missing_requirement_evidence",
    "generation_format_defect",
    "page_overflow",
    "render_failure",
    "provider_failure",
    "other",
)
_LINEAGE_FIELDS = ("run_id", "run_job_id", "artifact_id", "generation_input_fingerprint", "attempt_id", "trace_id")
_TRACE_IDENTITY_FIELDS = (
    "trace_id",
    "run_id",
    "run_job_id",
    "artifact_id",
    "generation_input_fingerprint",
    "attempt_id",
    "job_url",
)
_LEGACY_STRONG_MATCH_FIELDS = ("run_job_id", "generation_input_fingerprint", "attempt_id")
_LEGACY_MATCH_FIELDS = _LEGACY_STRONG_MATCH_FIELDS + ("job_url",)
_DEFAULT_ERROR_DETAILS_MAX_CHARS = 2048


def _parse_timestamp(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def accepted_cv_artifact_event_v1(
    *,
    artifact_id: str,
    job_url: str,
    run_id: str | None,
    trace_id: str | None = None,
    run_job_id: str | None = None,
    acceptance_mode: str,
    accepted_at: Any,
    finalized_at: Any,
    generation_input_fingerprint: str | None = None,
    attempt_id: str | None = None,
    page_fit_status: str | None = None,
    render_acceptance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_artifact_id = str(artifact_id or "").strip()
    normalized_job_url = str(job_url or "").strip()
    normalized_mode = str(acceptance_mode or "").strip()
    if not normalized_artifact_id or not normalized_job_url:
        raise ValueError("accepted_cv_artifact requires artifact_id and job_url")
    if normalized_mode not in {"automatic", "human_confirmed"}:
        raise ValueError("accepted_cv_artifact acceptance_mode invalid")
    normalized_render_acceptance = (
        dict(render_acceptance) if isinstance(render_acceptance, dict) else None
    )
    normalized_page_fit_status = str(page_fit_status or "").strip() or None
    if normalized_page_fit_status is None and normalized_render_acceptance:
        normalized_page_fit_status = str(
            normalized_render_acceptance.get("page_fit_status") or ""
        ).strip() or None
    return {
        "schema_version": ACCEPTED_CV_ARTIFACT_SCHEMA_VERSION,
        "event_id": stable_sha256_fingerprint(
            {
                "artifact_id": normalized_artifact_id,
                "trace_id": trace_id,
                "run_job_id": run_job_id,
                "acceptance_mode": normalized_mode,
                "generation_input_fingerprint": generation_input_fingerprint,
                "attempt_id": attempt_id,
            }
        ),
        "artifact_id": normalized_artifact_id,
        "job_url": normalized_job_url,
        "run_id": str(run_id or "").strip() or None,
        "trace_id": str(trace_id or "").strip() or None,
        "run_job_id": str(run_job_id or "").strip() or None,
        "acceptance_mode": normalized_mode,
        "accepted_at": accepted_at,
        "finalized_at": finalized_at,
        "generation_input_fingerprint": str(generation_input_fingerprint or "").strip() or None,
        "attempt_id": str(attempt_id or "").strip() or None,
        "page_fit_status": normalized_page_fit_status,
        "render_acceptance": normalized_render_acceptance,
        "render_proof_status": (
            "verified" if _render_acceptance_is_verified(normalized_render_acceptance) else "incomplete"
        ),
    }


def _render_acceptance_is_verified(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        str(value.get("render_status") or "").strip() == "pass"
        and int(value.get("page_count") or 0) == 1
        and str(value.get("page_fit_status") or "").strip() == "pass"
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(value.get("artifact_checksum") or "")))
        and bool(str(value.get("content_sha256") or "").strip())
        and bool(str(value.get("template_sha256") or "").strip())
        and bool(str(value.get("render_config_fingerprint") or "").strip())
        and bool(str(value.get("renderer_contract_version") or "").strip())
    )


def _nonnegative_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _failure_category(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in ACCEPTED_CV_FAILURE_CATEGORIES:
        return normalized
    if "unsupported" in normalized or "grounding" in normalized or "claim" in normalized:
        return "unsupported_claim"
    if "requirement" in normalized and ("missing" in normalized or "evidence" in normalized):
        return "missing_requirement_evidence"
    if any(token in normalized for token in ("format", "schema", "parse", "section")):
        return "generation_format_defect"
    if any(token in normalized for token in ("overflow", "page_fit", "page_count")):
        return "page_overflow"
    if any(token in normalized for token in ("render", "pdf", "pandoc", "xelatex", "latex")):
        return "render_failure"
    if any(token in normalized for token in ("provider", "timeout", "transport", "llm", "rate_limit")):
        return "provider_failure"
    return "other"


def _attempt_failure_category(attempt: dict[str, Any]) -> str | None:
    explicit = attempt.get("failure_category") or attempt.get("failure_reason")
    if explicit:
        return _failure_category(explicit)
    if str(attempt.get("provider_status") or "").strip().lower() in {"error", "failed", "failure"}:
        return _failure_category(attempt.get("error_message") or attempt.get("error_stage") or "provider_failure")
    if attempt.get("error_message") or attempt.get("error_stage"):
        return _failure_category(attempt.get("error_message") or attempt.get("error_stage"))
    return None


def _trace_attempts(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in list(trace.get("attempts") or []) if isinstance(item, dict)]


def _normalize_trace_record(
    trace: dict[str, Any],
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = dict(trace)
    if record:
        for field in (
            *_LINEAGE_FIELDS,
            "job_url",
            "render_retry_count",
            "cv_content_plan",
            "page_fit_status",
            "page_fit_verified",
            "page_fit_source",
            "render_acceptance",
            "reused_resolution_count",
            "run_started_at",
            "started_at",
            "created_at",
        ):
            if field not in normalized and record.get(field) is not None:
                normalized[field] = record.get(field)
    return normalized


def _trace_identity(trace: dict[str, Any]) -> str:
    explicit_trace_id = _lineage_value(trace, "trace_id")
    if explicit_trace_id:
        return stable_sha256_fingerprint({"trace_id": explicit_trace_id})
    identity = {
        field: _lineage_value(trace, field)
        for field in _TRACE_IDENTITY_FIELDS
        if _lineage_value(trace, field)
    }
    return stable_sha256_fingerprint({"identity": identity, "trace": trace})


def collect_normalized_generation_traces(
    records: list[dict[str, Any]],
    generation_trace_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates: list[tuple[dict[str, Any], str]] = []
    for trace_record in list(generation_trace_records or []):
        if isinstance(trace_record, dict):
            candidates.append((_normalize_trace_record(trace_record), "top_level"))
    for record in records:
        trace_record = record.get("cv_generation_trace")
        if isinstance(trace_record, dict):
            candidates.append((_normalize_trace_record(trace_record, record), "embedded"))

    normalized_by_identity: dict[str, dict[str, Any]] = {}
    source_by_identity: dict[str, str] = {}
    conflicted_identities: set[str] = set()
    duplicate_count = 0
    conflict_count = 0
    conflict_trace_ids: list[str] = []
    for trace, source in candidates:
        identity = _trace_identity(trace)
        if identity in conflicted_identities:
            continue
        existing = normalized_by_identity.get(identity)
        if existing is None:
            normalized_by_identity[identity] = trace
            source_by_identity[identity] = source
            continue
        if stable_json_dumps(existing) == stable_json_dumps(trace):
            duplicate_count += 1
            continue
        existing_source = source_by_identity[identity]
        if existing_source != source:
            shared_keys = set(existing) & set(trace)
            if all(existing[key] == trace[key] for key in shared_keys):
                if source == "top_level":
                    normalized_by_identity[identity] = {**existing, **trace}
                else:
                    normalized_by_identity[identity] = {**trace, **existing}
                source_by_identity[identity] = "top_level"
                duplicate_count += 1
                continue
        conflicted_identities.add(identity)
        normalized_by_identity.pop(identity, None)
        source_by_identity.pop(identity, None)
        conflict_count += 1
        conflict_trace_ids.append(_lineage_value(trace, "trace_id") or identity)

    return {
        "records": list(normalized_by_identity.values()),
        "diagnostics": {
            "duplicate_count": duplicate_count,
            "conflict_count": conflict_count,
            "conflict_trace_ids": sorted(conflict_trace_ids),
        },
    }


def _lineage_value(item: dict[str, Any], field: str) -> str:
    aliases = {
        "artifact_id": ("artifact_id", "artifact_version_id"),
        "job_url": ("job_url", "scope_key", "record_id"),
    }
    for key in aliases.get(field, (field,)):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    trace = item.get("cv_generation_trace")
    if isinstance(trace, dict):
        return _lineage_value(trace, field)
    return ""


def _lineage_matches(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_trace_id = _lineage_value(left, "trace_id")
    right_trace_id = _lineage_value(right, "trace_id")
    if left_trace_id or right_trace_id:
        return bool(left_trace_id and right_trace_id and left_trace_id == right_trace_id)
    left_run = _lineage_value(left, "run_id")
    right_run = _lineage_value(right, "run_id")
    if not left_run or not right_run or left_run != right_run:
        return False
    for field in _LEGACY_MATCH_FIELDS:
        left_value = _lineage_value(left, field)
        right_value = _lineage_value(right, field)
        if left_value or right_value:
            return bool(left_value and right_value and left_value == right_value)
    return False


def match_trace_record(
    artifact: dict[str, Any],
    traces: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    """Match accepted artifact to one trace without widening legacy identity."""
    trace_id = _lineage_value(artifact, "trace_id")
    if trace_id:
        matches = [trace for trace in traces if _lineage_value(trace, "trace_id") == trace_id]
        return (matches[0], "matched") if len(matches) == 1 else (None, "unmatched")

    run_id = _lineage_value(artifact, "run_id")
    if not run_id:
        return None, "unmatched"
    run_traces = [trace for trace in traces if _lineage_value(trace, "run_id") == run_id]
    if not run_traces:
        return None, "unmatched"
    artifact_strong = {
        field: _lineage_value(artifact, field)
        for field in _LEGACY_STRONG_MATCH_FIELDS
    }
    artifact_has_strong = any(artifact_strong.values())
    compatible: list[dict[str, Any]] = []
    conflict_found = False
    for trace in run_traces:
        trace_strong = {
            field: _lineage_value(trace, field)
            for field in _LEGACY_STRONG_MATCH_FIELDS
        }
        shared_fields = [
            field
            for field in _LEGACY_STRONG_MATCH_FIELDS
            if artifact_strong[field] and trace_strong[field]
        ]
        if any(artifact_strong[field] != trace_strong[field] for field in shared_fields):
            conflict_found = True
            continue
        if shared_fields:
            compatible.append(trace)
            continue
        if artifact_has_strong or any(trace_strong.values()):
            continue
        if _lineage_value(artifact, "job_url") and _lineage_value(artifact, "job_url") == _lineage_value(trace, "job_url"):
            compatible.append(trace)
    if len(compatible) == 1:
        return compatible[0], "matched"
    if len(compatible) > 1:
        return None, "ambiguous"
    if conflict_found:
        return None, "conflict"
    return None, "unmatched"


def _token_total(token_usage: Any) -> int:
    total = 0
    for usage in list(token_usage or []):
        if not isinstance(usage, dict):
            continue
        total += _nonnegative_int(
            usage.get("total_tokens")
            or (_nonnegative_int(usage.get("input_tokens")) + _nonnegative_int(usage.get("output_tokens")))
        )
    return total


def build_accepted_cv_effort_projection(
    records: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    accepted_artifacts: list[dict[str, Any]] | None = None,
    *,
    generation_trace_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    deduplicated_actions: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for action in actions:
        action_key = stable_sha256_fingerprint(
            {
                key: action.get(key)
                for key in (
                    "review_item_id",
                    "job_url",
                    "action",
                    "created_at",
                    "artifact_version_id",
                    "run_id",
                    "run_job_id",
                    "generation_input_fingerprint",
                    "attempt_id",
                )
            }
        )
        if action_key in seen_actions:
            continue
        seen_actions.add(action_key)
        deduplicated_actions.append(action)
    accepted_actions = [
        action
        for action in deduplicated_actions
        if bool(action.get("artifact_finalized")) and str(action.get("artifact_version_id") or "").strip()
    ]
    deduplicated_artifacts: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    for artifact in list(accepted_artifacts or []):
        artifact_id = str(artifact.get("artifact_id") or artifact.get("artifact_version_id") or "").strip()
        if not artifact_id or artifact_id in seen_artifacts:
            continue
        seen_artifacts.add(artifact_id)
        deduplicated_artifacts.append(artifact)
    if deduplicated_artifacts:
        accepted_actions = [
            {
                "job_url": artifact.get("job_url"),
                "artifact_version_id": artifact.get("artifact_id") or artifact.get("artifact_version_id"),
                "artifact_finalized": True,
                "artifact_finalized_at": artifact.get("finalized_at") or artifact.get("accepted_at"),
                "acceptance_mode": artifact.get("acceptance_mode"),
                "run_id": artifact.get("run_id"),
                "run_job_id": artifact.get("run_job_id"),
                "generation_input_fingerprint": artifact.get("generation_input_fingerprint"),
                "attempt_id": artifact.get("attempt_id"),
                "trace_id": artifact.get("trace_id"),
                "page_fit_status": artifact.get("page_fit_status"),
                "render_acceptance": artifact.get("render_acceptance"),
            }
            for artifact in deduplicated_artifacts
        ]

    normalized_traces = collect_normalized_generation_traces(records, generation_trace_records)
    trace_records = list(normalized_traces["records"])
    trace_diagnostics = dict(normalized_traces["diagnostics"])

    if not accepted_actions and not trace_records:
        return {
            "schema_version": "accepted_cv_effort_v1",
            "status": "not_run",
            "blocker": "no_accepted_artifact_event",
            "denominator": {"accepted_cv_count": 0},
            "records": [],
            "trace_normalization": trace_diagnostics,
        }
    projected: list[dict[str, Any]] = []
    unmatched_trace_count = 0
    unattributed_accepted_artifact_count = 0
    for action in accepted_actions:
        job_url = _lineage_value(action, "job_url")
        trace, attribution_status = match_trace_record(action, trace_records)
        matched_traces = [trace] if trace is not None else []
        if trace is None:
            unmatched_trace_count += 1
            unattributed_accepted_artifact_count += 1
        trace = trace or {}
        efficiency = dict(dict(trace.get("efficiency_summary") or {}))
        related_actions = [item for item in deduplicated_actions if _lineage_matches(action, item)]
        attempts: list[dict[str, Any]] = []
        seen_attempts: set[str] = set()
        for matched_trace in matched_traces:
            for attempt in _trace_attempts(matched_trace):
                attempt_id = stable_sha256_fingerprint(attempt)
                if attempt_id not in seen_attempts:
                    seen_attempts.add(attempt_id)
                    attempts.append(attempt)
        attempt_categories = [
            category
            for category in (_attempt_failure_category(item) for item in attempts)
            if category
        ]
        validation_summary = dict(trace.get("validation_summary") or {})
        validation_failure_count = _nonnegative_int(efficiency.get("validation_failure_count"))
        if validation_failure_count == 0 and validation_summary.get("initial_valid") is False:
            validation_failure_count = 1
        if validation_failure_count == 0 and validation_summary.get("final_valid") is False:
            validation_failure_count = 1
        if validation_failure_count and not attempt_categories:
            if validation_summary.get("initial_grounding_violation_count") or validation_summary.get(
                "final_grounding_violation_count"
            ):
                attempt_categories.append("unsupported_claim")
            elif validation_summary.get("initial_missing_fields") or validation_summary.get("final_missing_fields"):
                attempt_categories.append("generation_format_defect")
            else:
                attempt_categories.append("other")
        error_summary = trace.get("error_summary")
        if isinstance(error_summary, dict) and not attempt_categories:
            attempt_categories.append(
                _failure_category(error_summary.get("failure_category") or error_summary.get("error_stage"))
            )
        render_retry_count = max(
            _nonnegative_int(efficiency.get("render_retry_count")),
            _nonnegative_int(trace.get("render_retry_count")),
        )
        provider_call_count = max(_nonnegative_int(efficiency.get("provider_call_count")), len(attempts))
        regeneration_count = max(
            _nonnegative_int(efficiency.get("regeneration_count")),
            max(len(attempts) - 1, 0),
            sum(str(item.get("action") or "") == "regenerate_once" for item in related_actions),
        )
        token_usage = efficiency.get("token_usage")
        elapsed_from_trace = efficiency.get("elapsed_ms")
        output_summary = dict(trace.get("output_summary") or {})
        content_plan = dict(trace.get("cv_content_plan") or {})
        artifact_render_acceptance = dict(action.get("render_acceptance") or {})
        artifact_render_verified = _render_acceptance_is_verified(artifact_render_acceptance)
        page_fit_candidates = (
            artifact_render_acceptance.get("page_fit_status"),
            action.get("page_fit_status"),
            output_summary.get("page_fit_status"),
            dict(output_summary.get("render_acceptance") or {}).get("page_fit_status"),
            trace.get("page_fit_status"),
        )
        page_fit_status = next(
            (
                str(value).strip()
                for value in page_fit_candidates
                if str(value or "").strip().lower()
                not in {"", "not_recorded", "not_run", "not_applicable", "unverified"}
            ),
            "not_recorded",
        )
        reused_resolution_count = int(
            trace.get("reused_resolution_count")
            or sum(
                str(item.get("resolution_status") or "").strip().startswith("reused")
                for item in related_actions
            )
        )
        start = None
        for key in ("run_started_at", "started_at", "created_at"):
            start = _parse_timestamp(trace.get(key))
            if start is not None:
                break
        end = None
        for key in ("artifact_finalized_at", "finalized_at", "created_at"):
            end = _parse_timestamp(action.get(key))
            if end is not None:
                break
        elapsed_ms = None
        elapsed_status = "not_run"
        if start is not None and end is not None and end >= start:
            elapsed_ms = (end - start).total_seconds() * 1000
            elapsed_status = "measured"
        elif elapsed_from_trace is not None:
            elapsed_ms = _nonnegative_int(elapsed_from_trace)
            elapsed_status = "measured"
        generation_elapsed_ms = None
        generation_elapsed_status = "not_run"
        if elapsed_from_trace is not None:
            generation_elapsed_ms = _nonnegative_int(elapsed_from_trace)
            generation_elapsed_status = "measured"
        attempt_rows = [
            {
                "attempt_index": item.get("attempt_index"),
                "attempt_type": item.get("attempt_type"),
                "provider_status": item.get("provider_status"),
                "failure_category": _attempt_failure_category(item),
            }
            for item in attempts
        ]
        page_fit_source = "artifact_render_acceptance" if artifact_render_verified else (
            "trace_unverified" if page_fit_status != "not_recorded" else "not_recorded"
        )
        row = {
                "job_url": job_url,
                "artifact_version_id": str(action.get("artifact_version_id") or "").strip(),
                "run_id": _lineage_value(action, "run_id") or None,
                "run_job_id": _lineage_value(action, "run_job_id") or None,
                "generation_input_fingerprint": _lineage_value(action, "generation_input_fingerprint") or None,
                "attempt_id": _lineage_value(action, "attempt_id") or None,
                "trace_id": _lineage_value(action, "trace_id") or None,
                "page_fit_status": action.get("page_fit_status"),
                "render_acceptance": action.get("render_acceptance"),
                "acceptance_mode": str(action.get("acceptance_mode") or "human_confirmed"),
                "final_status": "accepted",
                "attribution_status": attribution_status,
                "attempt_count": max(len(attempts), provider_call_count),
                "attempts": attempt_rows,
                "provider_call_count": provider_call_count,
                "regeneration_count": regeneration_count,
                "validation_failure_count": validation_failure_count,
                "failure_category_counts": {
                    category: attempt_categories.count(category) for category in ACCEPTED_CV_FAILURE_CATEGORIES
                    if category in attempt_categories
                },
                "render_retry_count": render_retry_count,
                "review_question_count": efficiency.get("review_question_count", "not_run"),
                "human_action_count": len(related_actions),
                "reused_resolution_count": reused_resolution_count,
                "page_fit_status": page_fit_status,
                "page_fit_verified": artifact_render_verified,
                "page_fit_source": page_fit_source,
                "accepted_outcome": True,
                "token_usage": token_usage,
                "token_total": _token_total(token_usage),
                "token_usage_status": str(efficiency.get("token_usage_status") or "not_run"),
                "generation_elapsed_ms": generation_elapsed_ms,
                "generation_elapsed_status": generation_elapsed_status,
                "elapsed_ms": elapsed_ms,
                "elapsed_status": elapsed_status,
            }
        if attribution_status != "matched":
            for field in (
                "attempt_count",
                "attempts",
                "provider_call_count",
                "regeneration_count",
                "validation_failure_count",
                "failure_category_counts",
                "render_retry_count",
                "review_question_count",
                "reused_resolution_count",
            "page_fit_status",
                "page_fit_verified",
                "page_fit_source",
                "token_usage",
                "token_total",
                "generation_elapsed_ms",
                "elapsed_ms",
            ):
                row[field] = None
            row["generation_elapsed_status"] = "unmatched"
            row["elapsed_status"] = "unmatched"
        projected.append(row)
    workload_records = trace_records or [
        dict(record.get("cv_generation_trace") or {})
        for record in records
        if isinstance(record.get("cv_generation_trace"), dict)
    ]
    workload_attempted_jobs = len(workload_records)
    workload_validation_failures = 0
    workload_provider_calls = 0
    workload_regenerations = 0
    workload_render_retries = 0
    workload_token_total = 0
    for trace_record in workload_records:
        trace = trace_record
        efficiency = dict(trace.get("efficiency_summary") or {})
        attempts = _trace_attempts(trace)
        workload_provider_calls += max(_nonnegative_int(efficiency.get("provider_call_count")), len(attempts))
        workload_regenerations += max(_nonnegative_int(efficiency.get("regeneration_count")), max(len(attempts) - 1, 0))
        workload_render_retries += max(
            _nonnegative_int(efficiency.get("render_retry_count")),
            _nonnegative_int(trace.get("render_retry_count")),
        )
        workload_token_total += _token_total(efficiency.get("token_usage"))
        output_summary = dict(trace.get("output_summary") or {})
        validation_summary = dict(trace.get("validation_summary") or {})
        if (
            str(output_summary.get("final_status") or trace.get("status") or "").strip() == "validation_failed"
            or validation_summary.get("final_valid") is False
        ):
            workload_validation_failures += 1
    generation_elapsed_values = [
        float(row["generation_elapsed_ms"])
        for row in projected
        if row["generation_elapsed_ms"] is not None
    ]
    aggregate = {
        "attempt_count": sum(row["attempt_count"] or 0 for row in projected),
        "provider_call_count": sum(row["provider_call_count"] or 0 for row in projected),
        "regeneration_count": sum(row["regeneration_count"] or 0 for row in projected),
        "validation_failure_count": sum(row["validation_failure_count"] or 0 for row in projected),
        "render_retry_count": sum(row["render_retry_count"] or 0 for row in projected),
        "review_question_count": sum(
            value for value in (_nonnegative_int(row["review_question_count"]) for row in projected)
        ),
        "human_action_count": sum(row["human_action_count"] for row in projected if isinstance(row["human_action_count"], int)),
        "reused_resolution_count": sum(row["reused_resolution_count"] or 0 for row in projected),
        "generation_elapsed_ms": sum(generation_elapsed_values) if generation_elapsed_values else None,
        "generation_timing_coverage": {
            "measured": len(generation_elapsed_values),
            "unavailable": sum(row["generation_elapsed_ms"] is None for row in projected),
        },
        "elapsed_ms": sum(row["elapsed_ms"] or 0 for row in projected),
        "token_total": sum(row["token_total"] or 0 for row in projected),
        "unmatched_trace_count": unmatched_trace_count,
        "unattributed_accepted_artifact_count": unattributed_accepted_artifact_count,
        "page_fit_coverage": {
            "verified": sum(bool(row.get("page_fit_verified")) for row in projected),
            "eligible": len(projected),
        },
        "page_fit_success": {
            "verified_one_page": sum(
                bool(row.get("page_fit_verified")) and row.get("page_fit_status") == "pass"
                for row in projected
            ),
        },
        "failure_category_counts": {
                category: sum((row["failure_category_counts"] or {}).get(category, 0) for row in projected)
                for category in ACCEPTED_CV_FAILURE_CATEGORIES
                if any((row["failure_category_counts"] or {}).get(category, 0) for row in projected)
        },
        "workload_status": "complete" if not unmatched_trace_count and not unattributed_accepted_artifact_count else "incomplete",
        "workload": {
            "attempted_generation_job_count": workload_attempted_jobs,
            "validation_failure_count": workload_validation_failures,
            "provider_call_count": workload_provider_calls,
            "regeneration_count": workload_regenerations,
            "render_retry_count": workload_render_retries,
            "token_total": workload_token_total,
        },
    }
    return {
        "schema_version": "accepted_cv_effort_v1",
        "status": "measured",
        "attribution_status": "complete" if not unattributed_accepted_artifact_count else "incomplete",
        "trace_normalization": trace_diagnostics,
        "denominator": {"accepted_cv_count": len(projected)},
        "unmatched_trace_count": unmatched_trace_count,
        "unattributed_accepted_artifact_count": unattributed_accepted_artifact_count,
        "aggregate": aggregate,
        "records": projected,
    }


def string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def normalized_run_mode(value: Any) -> str:
    run_mode = string_or_none(value)
    if run_mode in RUN_MODE_LABELS:
        return run_mode
    return "run_all"


def run_mode_label(value: Any) -> str:
    return RUN_MODE_LABELS[normalized_run_mode(value)]


def iso_or_none(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime.datetime) else None


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return [json_safe(item) for item in sorted(value)]
    return value


def decode_json_object_or_none(raw_payload: str | None) -> dict[str, Any] | None:
    if not raw_payload:
        return None
    try:
        payload = _json.loads(raw_payload)
    except (_json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def decode_json_object_or_raise(raw_payload: str | None) -> dict[str, Any]:
    payload = _json.loads(raw_payload or "")
    if not isinstance(payload, dict):
        raise ValueError("decoded_json_not_object")
    return payload


def encode_json_object(payload: dict[str, Any]) -> str:
    return _json.dumps(payload, ensure_ascii=False)


def stable_json_dumps(payload: Any) -> str:
    return _json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_sha256_fingerprint(payload: Any) -> str:
    raw = stable_json_dumps(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def require_payload_keys(
    payload: dict[str, Any],
    *,
    required_keys: set[str],
    context: str,
) -> dict[str, Any]:
    missing = sorted(key for key in required_keys if key not in payload)
    if missing:
        raise ValueError(f"missing_required_payload_keys:{context}:{','.join(missing)}")
    return payload


def schema_version_or_none(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    value = payload.get("schema_version")
    return value if isinstance(value, str) and value.strip() else None


def schema_version_matches(payload: dict[str, Any] | None, expected: str) -> bool:
    return schema_version_or_none(payload) == expected


def pretty_json_string(raw_json: str) -> str:
    return _json.dumps(_json.loads(raw_json), ensure_ascii=False, indent=2)


def pretty_json_string_or_fallback(raw_json: str | None) -> str:
    if not raw_json:
        return ""
    try:
        return pretty_json_string(str(raw_json))
    except (_json.JSONDecodeError, TypeError, ValueError):
        return str(raw_json)


def replay_context_payload(*, replay_context: dict[str, Any], run_id: str) -> dict[str, str]:
    return {
        "replay_mode": str(replay_context.get("replay_mode") or "strict"),
        "replay_source_run_id": str(replay_context.get("replay_source_run_id") or run_id),
        "policy_registry_version": str(replay_context.get("policy_registry_version") or "policy_registry.v1"),
        "policy_envelope_signature": str(replay_context.get("policy_envelope_signature") or ""),
    }


def _bounded_error_details(
    details: dict[str, Any] | None,
    *,
    max_chars: int | None,
) -> dict[str, Any] | None:
    if details is None:
        return None
    max_chars = int(max_chars) if isinstance(max_chars, int) else _DEFAULT_ERROR_DETAILS_MAX_CHARS
    if max_chars <= 0:
        return None
    try:
        raw = stable_json_dumps(details)
    except Exception:
        raw = stable_json_dumps({"unserializable": True, "type": str(type(details))})
        details = {"unserializable": True, "type": str(type(details))}

    if len(raw) <= max_chars:
        return details

    fingerprint = stable_sha256_fingerprint(details)
    return {
        "truncated": True,
        "sha256": fingerprint,
        "original_chars": len(raw),
        "max_chars": max_chars,
    }


def run_attempt_payload_v1(
    *,
    attempt_id: str,
    status: str,
    rq_job_id: str | None = None,
    worker_id: str | None = None,
    lease_started_at: datetime.datetime | None = None,
    lease_expires_at: datetime.datetime | None = None,
    finished_at: datetime.datetime | None = None,
    error_classification: str | None = None,
    error_summary: str | None = None,
    error_details: dict[str, Any] | None = None,
    error_details_max_chars: int | None = None,
    retry_eligible: bool | None = None,
    retry_after_seconds: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": RUN_ATTEMPT_SCHEMA_VERSION,
        "attempt": {
            "attempt_id": str(attempt_id),
            "status": str(status),
            "rq_job_id": string_or_none(rq_job_id),
            "worker_id": string_or_none(worker_id),
            "lease_started_at": lease_started_at,
            "lease_expires_at": lease_expires_at,
            "finished_at": finished_at,
            "error": {
                "classification": string_or_none(error_classification),
                "summary": string_or_none(error_summary),
                "details": _bounded_error_details(error_details, max_chars=error_details_max_chars),
            },
            "retry": {
                "eligible": retry_eligible,
                "after_seconds": retry_after_seconds,
            },
        },
    }
    return json_safe(payload)


def decode_run_attempt_payload_or_none(raw_payload: str | None) -> dict[str, Any] | None:
    payload = decode_json_object_or_none(raw_payload)
    if not schema_version_matches(payload, RUN_ATTEMPT_SCHEMA_VERSION):
        return None
    attempt = payload.get("attempt") if isinstance(payload, dict) else None
    if not isinstance(attempt, dict):
        return None
    attempt_id = attempt.get("attempt_id")
    status = attempt.get("status")
    if not (isinstance(attempt_id, str) and attempt_id.strip()):
        return None
    if not (isinstance(status, str) and status.strip()):
        return None
    return payload
