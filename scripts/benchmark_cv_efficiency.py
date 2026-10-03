"""Report CV runtime efficiency from persisted ordinary pipeline runs."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv_cp import sqlite_store
from fitcv_cp.run_artifact_contracts import (
    FINAL_ARTIFACT_CONTRACT_VERSION,
    TRACE_CONTRACT_VERSION,
    build_accepted_cv_effort_projection,
    collect_normalized_generation_traces,
)
from fitcv.contracts import EFFICIENCY_CONTRACT_VERSION

DEFAULT_JSON = REPO_ROOT / "docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md"
STAGE_NAMES = (
    "analysis",
    "retrieval",
    "content_planning",
    "provider_generation",
    "validation",
    "render",
    "repair",
    "persistence",
)


def _value(run: Any, field: str, default: Any = None) -> Any:
    if isinstance(run, dict):
        return run.get(field, default)
    return getattr(run, field, default)


def _status(run: Any) -> str:
    value = _value(run, "status", "")
    return str(getattr(value, "value", value) or "").strip().lower()


def _json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _timestamp(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def _run_payload(run: Any) -> dict[str, Any]:
    for field in ("cv_generation_debug_json", "results_export_json"):
        payload = _json_object(_value(run, field))
        if payload:
            return payload
    compatibility = _json_object(_value(run, "compatibility_json"))
    for field in ("cv_generation_debug_json", "results_export_json"):
        payload = _json_object(compatibility.get(field))
        if payload:
            return payload
    return {}


def _trace_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    block = payload.get("cv_generation_trace")
    if not isinstance(block, dict):
        return []
    records = [item for item in list(block.get("records") or []) if isinstance(item, dict)]
    if records:
        return records
    return [block] if block.get("attempts") else []


def _trace_generation_elapsed_ms(trace: dict[str, Any]) -> float | None:
    efficiency = dict(trace.get("efficiency_summary") or {})
    raw_elapsed = efficiency.get("elapsed_ms")
    if raw_elapsed is not None:
        try:
            return max(float(raw_elapsed), 0.0)
        except (TypeError, ValueError):
            return None
    started = _timestamp(trace.get("generation_started_at") or trace.get("started_at"))
    finished = _timestamp(trace.get("generation_finished_at") or trace.get("finished_at"))
    if started is not None and finished is not None and finished >= started:
        return (finished - started).total_seconds() * 1000
    return None


def _trace_final_accepted(trace: dict[str, Any], attempts: list[dict[str, Any]]) -> bool:
    output_summary = dict(trace.get("output_summary") or {})
    final_status = str(output_summary.get("final_status") or trace.get("status") or "").strip().lower()
    if final_status:
        return final_status in {"accepted", "succeeded", "success"}
    return bool(attempts and str(attempts[-1].get("provider_status") or "").strip().lower() == "accepted")


def _is_recorded(value: Any) -> bool:
    return value not in {None, "", "not_recorded", "not_run", "not_applicable", "unverified"}


def _coverage(values: list[Any]) -> dict[str, Any]:
    measured = sum(_is_recorded(value) for value in values)
    return {
        "measured": measured,
        "unavailable": len(values) - measured,
        "total": len(values),
        "rate": measured / len(values) if values else 0.0,
    }


def _numeric_values(values: Any) -> list[float]:
    if not isinstance(values, list):
        values = [values]
    result: list[float] = []
    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            result.append(parsed)
    return result


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _stage_latency_samples(payload: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, list[float]]:
    samples = {stage: [] for stage in STAGE_NAMES}

    def add(stage: str, values: Any) -> None:
        if stage in samples:
            samples[stage].extend(_numeric_values(values))

    for stage, values in dict(payload.get("stage_timings_ms") or {}).items():
        add(str(stage), values)
    for trace in traces:
        for stage, values in dict(trace.get("stage_timings_ms") or {}).items():
            add(str(stage), values)
        for attempt in list(trace.get("attempts") or []):
            if not isinstance(attempt, dict):
                continue
            for stage, values in dict(attempt.get("stage_timings_ms") or {}).items():
                add(str(stage), values)
            provenance = dict(dict(attempt.get("llm_runtime_evidence") or {}).get("provenance") or {})
            add("provider_generation", provenance.get("latency_ms"))
        for field, stage in (
            ("analysis_elapsed_ms", "analysis"),
            ("retrieval_elapsed_ms", "retrieval"),
            ("content_planning_elapsed_ms", "content_planning"),
            ("validation_elapsed_ms", "validation"),
            ("render_elapsed_ms", "render"),
            ("repair_elapsed_ms", "repair"),
            ("persistence_elapsed_ms", "persistence"),
        ):
            add(stage, trace.get(field))
    return samples


def _stage_latency_report(samples: dict[str, list[float]]) -> dict[str, dict[str, Any]]:
    return {
        stage: {
            "p50_ms": _percentile(list(samples.get(stage) or []), 0.50),
            "p95_ms": _percentile(list(samples.get(stage) or []), 0.95),
            "measured": len(list(samples.get(stage) or [])),
            "coverage": bool(samples.get(stage)),
        }
        for stage in STAGE_NAMES
    }


def _run_snapshot(run: Any) -> dict[str, Any] | None:
    run_id = str(_value(run, "run_id", "") or "").strip()
    if not run_id:
        return None
    payload = _run_payload(run)
    if not payload:
        return None
    records = [
        item
        for item in list(payload.get("debug_records") or payload.get("cv_generation_debug_records") or [])
        if isinstance(item, dict)
    ]
    raw_traces = _trace_records(payload)
    normalized_traces = collect_normalized_generation_traces(records, raw_traces)
    traces = list(normalized_traces["records"])
    stage_latency_samples = _stage_latency_samples(payload, traces)
    actions = [item for item in list(payload.get("hitl_review_actions") or []) if isinstance(item, dict)]
    artifacts = [item for item in list(payload.get("accepted_artifact_events") or []) if isinstance(item, dict)]
    projection = build_accepted_cv_effort_projection(
        records,
        actions,
        artifacts,
        generation_trace_records=normalized_traces,
    )
    if projection.get("status") == "not_run":
        return None
    projected_records = [
        item for item in list(projection.get("records") or []) if isinstance(item, dict)
    ]
    generation_elapsed_values = [
        elapsed
        for elapsed in (_trace_generation_elapsed_ms(trace) for trace in traces)
        if elapsed is not None
    ]
    generation_elapsed_ms = sum(generation_elapsed_values) if generation_elapsed_values else None
    first_pass_acceptance_count = 0
    retry_success_count = 0
    retry_failure_count = 0
    for trace in traces:
        attempts = [item for item in list(trace.get("attempts") or []) if isinstance(item, dict)]
        final_accepted = _trace_final_accepted(trace, attempts)
        if len(attempts) == 1 and final_accepted:
            first_pass_acceptance_count += 1
        elif len(attempts) > 1:
            if final_accepted:
                retry_success_count += 1
            else:
                retry_failure_count += 1
    created_at = _timestamp(_value(run, "created_at"))
    started_at = _timestamp(_value(run, "started_at"))
    finished_at = _timestamp(_value(run, "finished_at"))
    elapsed_wall_ms = None
    if started_at and finished_at and finished_at >= started_at:
        elapsed_wall_ms = (finished_at - started_at).total_seconds() * 1000
    status_counts = Counter(str(item.get("status") or "unknown") for item in records)
    page_fit_values = [
        item.get("page_fit_status") if bool(item.get("page_fit_verified")) else None
        for item in projected_records
    ]
    page_fit_reported_values = [item.get("page_fit_status") for item in projected_records]
    page_fit_success_values = [
        item.get("accepted_final_one_page") for item in projected_records
    ]
    current_contract_records = [
        item
        for item in projected_records
        if item.get("final_artifact_contract_version") == FINAL_ARTIFACT_CONTRACT_VERSION
        and item.get("trace_contract_version") == TRACE_CONTRACT_VERSION
    ]
    page_fit_success_measured = [
        value for value in page_fit_success_values if _is_recorded(value)
    ]
    page_fit_success_pass = sum(value is True for value in page_fit_success_measured)
    page_fit_success_fail = sum(value is False for value in page_fit_success_measured)
    review_question_values = [item.get("review_question_count") for item in projected_records]
    human_action_values = [item.get("human_action_count") for item in projected_records]
    resolution_values = [item.get("reused_resolution_count") for item in projected_records]
    token_status_values = [item.get("token_usage_status") for item in projected_records]
    job_types = {
        str(trace.get("job_type") or "").strip()
        for trace in traces
        if str(trace.get("job_type") or "").strip()
    }
    return {
        "run_id": run_id,
        "created_at": created_at.isoformat() if created_at else None,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "elapsed_wall_ms": elapsed_wall_ms,
        "generation_elapsed_ms": generation_elapsed_ms,
        "timing": {
            "generation_elapsed_ms": generation_elapsed_ms,
            "generation_timing_coverage": {
                "measured": len(generation_elapsed_values),
                "unavailable": len(traces) - len(generation_elapsed_values),
            },
            "stage_latency_ms": _stage_latency_report(stage_latency_samples),
        },
        "stage_latency_samples_ms": stage_latency_samples,
        "yield": {
            "attempted_generation_job_count": len(traces),
            "first_pass_acceptance_count": first_pass_acceptance_count,
            "retry_success_count": retry_success_count,
            "retry_failure_count": retry_failure_count,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "accepted_record_count": status_counts.get("accepted", 0),
        "projection": projection,
        "contract_coverage": {
            "current": len(current_contract_records),
            "historical": len(projected_records) - len(current_contract_records),
            "total": len(projected_records),
            "complete": bool(projected_records and len(current_contract_records) == len(projected_records)),
        },
        "trace_normalization": dict(normalized_traces.get("diagnostics") or {}),
        "_trace_records_for_diversity": traces,
        "coverage": {
            "attribution": {
                "matched": sum(item.get("attribution_status") == "matched" for item in projected_records),
                "unmatched": sum(item.get("attribution_status") != "matched" for item in projected_records),
                "total": len(projected_records),
            },
            "cost": _coverage(token_status_values),
            "timing": {
                "measured": len(generation_elapsed_values),
                "unavailable": len(traces) - len(generation_elapsed_values),
                "total": len(traces),
                "rate": len(generation_elapsed_values) / len(traces) if traces else 0.0,
            },
            "page_fit": _coverage(page_fit_values),
            "page_fit_reported": _coverage(page_fit_reported_values),
            "page_fit_coverage": _coverage(page_fit_values),
            "page_fit_success": {
                "measured": len(page_fit_success_measured),
                "unavailable": len(page_fit_success_values) - len(page_fit_success_measured),
                "total": len(page_fit_success_values),
                "rate": (
                    page_fit_success_pass / len(page_fit_success_values)
                    if page_fit_success_values else 0.0
                ),
                "pass": page_fit_success_pass,
                "fail": page_fit_success_fail,
                "complete": bool(
                    page_fit_success_values
                    and len(page_fit_success_measured) == len(page_fit_success_values)
                ),
            },
            "review_questions": _coverage(review_question_values),
            "human_actions": _coverage(human_action_values),
            "resolution_reuse": _coverage(resolution_values),
            "run_job_diversity": {
                "run_count": 1,
                "job_count": len(traces),
                "job_type_count": len(job_types),
                "job_types": sorted(job_types),
            },
        },
    }


def _sum_workload(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "attempted_generation_job_count",
        "terminal_validation_failed_job_count",
        "validation_failure_event_count",
        "validation_failure_count",
        "provider_call_count",
        "regeneration_count",
        "render_retry_count",
        "token_total",
    )
    return {
        field: sum(
            int(dict(snapshot["projection"].get("aggregate") or {}).get("workload", {}).get(field) or 0)
            for snapshot in snapshots
        )
        for field in fields
    }


def _source_job_type(source_snapshot: Any) -> str | None:
    if not isinstance(source_snapshot, dict):
        return None
    for field in (
        "job_type",
        "jobType",
        "contract_type",
        "contractType",
        "work_type",
        "workType",
        "employment_type",
        "employmentType",
    ):
        value = str(source_snapshot.get(field) or "").strip()
        if value:
            return value
    return None


def _run_job_types(traces: Iterable[dict[str, Any]], run_jobs: Iterable[Any]) -> set[str]:
    by_run_job_id: dict[str, dict[str, Any]] = {}
    by_job_url: dict[str, dict[str, Any]] = {}
    for item in run_jobs:
        if not isinstance(item, dict):
            continue
        source_snapshot = item.get("source_snapshot")
        if not isinstance(source_snapshot, dict):
            source_snapshot = item
        row = {"source_snapshot": source_snapshot, **item}
        run_job_id = str(item.get("run_job_id") or source_snapshot.get("run_job_id") or "").strip()
        job_url = str(
            item.get("source_url")
            or source_snapshot.get("job_url")
            or source_snapshot.get("jobUrl")
            or source_snapshot.get("url")
            or ""
        ).strip()
        if run_job_id:
            by_run_job_id[run_job_id] = row
        if job_url:
            by_job_url[job_url] = row
    job_types: set[str] = set()
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        run_job_id = str(trace.get("run_job_id") or "").strip()
        job_url = str(trace.get("job_url") or trace.get("scope_key") or trace.get("record_id") or "").strip()
        row = by_run_job_id.get(run_job_id) or by_job_url.get(job_url)
        if row is None:
            continue
        source_snapshot = row["source_snapshot"]
        job_type = _source_job_type(source_snapshot)
        if job_type:
            job_types.add(job_type)
    return job_types


def build_baseline(
    runs: Iterable[Any],
    *,
    run_jobs_by_run_id: dict[str, Iterable[Any]] | None = None,
) -> dict[str, Any]:
    snapshots = []
    exclusions: Counter[str] = Counter()
    seen_run_ids: set[str] = set()
    for run in runs:
        run_id = str(_value(run, "run_id", "") or "").strip()
        if run_id in seen_run_ids:
            exclusions["duplicate_run_id"] += 1
            continue
        seen_run_ids.add(run_id)
        snapshot = _run_snapshot(run)
        if snapshot is None:
            exclusions[_status(run) or "missing_run_id_or_payload"] += 1
            continue
        source_job_types = _run_job_types(
            snapshot.pop("_trace_records_for_diversity", []),
            (run_jobs_by_run_id or {}).get(run_id, []),
        )
        if source_job_types:
            snapshot["coverage"]["run_job_diversity"]["job_types"] = sorted(source_job_types)
        snapshots.append(snapshot)

    accepted_count = sum(
        int(dict(snapshot["projection"].get("denominator") or {}).get("accepted_cv_count") or 0)
        for snapshot in snapshots
    )
    accepted_record_count = sum(int(snapshot.get("accepted_record_count") or 0) for snapshot in snapshots)
    unmatched_trace_count = sum(
        int(snapshot["projection"].get("unmatched_trace_count") or 0) for snapshot in snapshots
    )
    unattributed_count = sum(
        int(snapshot["projection"].get("unattributed_accepted_artifact_count") or 0)
        for snapshot in snapshots
    )
    unattributed_count += max(accepted_record_count - accepted_count, 0)
    workload = _sum_workload(snapshots)
    trace_normalization = {
        "duplicate_count": sum(
            int(dict(snapshot.get("trace_normalization") or {}).get("duplicate_count") or 0)
            for snapshot in snapshots
        ),
        "conflict_count": sum(
            int(dict(snapshot.get("trace_normalization") or {}).get("conflict_count") or 0)
            for snapshot in snapshots
        ),
        "conflict_trace_ids": sorted({
            str(trace_id)
            for snapshot in snapshots
            for trace_id in list(dict(snapshot.get("trace_normalization") or {}).get("conflict_trace_ids") or [])
            if str(trace_id).strip()
        }),
        "source_candidate_count": sum(
            int(dict(snapshot.get("trace_normalization") or {}).get("source_candidate_count") or 0)
            for snapshot in snapshots
        ),
        "normalized_trace_count": sum(
            int(dict(snapshot.get("trace_normalization") or {}).get("normalized_trace_count") or 0)
            for snapshot in snapshots
        ),
    }
    generation_elapsed_values = [
        float(snapshot["generation_elapsed_ms"])
        for snapshot in snapshots
        if snapshot.get("generation_elapsed_ms") is not None
    ]
    workload["generation_elapsed_ms"] = sum(generation_elapsed_values) if generation_elapsed_values else None
    generation_timing_coverage = {
        "measured": sum(
            int(dict(snapshot.get("timing") or {}).get("generation_timing_coverage", {}).get("measured") or 0)
            for snapshot in snapshots
        ),
        "unavailable": sum(
            int(dict(snapshot.get("timing") or {}).get("generation_timing_coverage", {}).get("unavailable") or 0)
            for snapshot in snapshots
        ),
    }
    coverage_names = (
        "attribution",
        "cost",
        "timing",
        "page_fit",
        "review_questions",
        "human_actions",
        "resolution_reuse",
    )
    coverage: dict[str, Any] = {}
    for name in coverage_names:
        values = [dict(snapshot.get("coverage") or {}).get(name) or {} for snapshot in snapshots]
        total = sum(int(item.get("total") or 0) for item in values)
        measured = sum(int(item.get("measured") or item.get("matched") or 0) for item in values)
        unavailable = sum(int(item.get("unavailable") or item.get("unmatched") or 0) for item in values)
        coverage[name] = {
            "measured": measured,
            "unavailable": unavailable,
            "total": total,
            "rate": measured / total if total else 0.0,
            "complete": bool(total and measured == total),
        }
    coverage["attribution"]["matched"] = sum(
        int(dict(snapshot.get("coverage") or {}).get("attribution", {}).get("matched") or 0)
        for snapshot in snapshots
    )
    coverage["attribution"]["unmatched"] = sum(
        int(dict(snapshot.get("coverage") or {}).get("attribution", {}).get("unmatched") or 0)
        for snapshot in snapshots
    )
    coverage["attribution"]["complete"] = bool(
        coverage["attribution"]["total"]
        and coverage["attribution"]["unmatched"] == 0
    )
    page_fit_success_values = [
        value
        for snapshot in snapshots
        for value in [
            item.get("accepted_final_one_page")
            for item in list(dict(snapshot.get("projection") or {}).get("records") or [])
            if isinstance(item, dict)
        ]
    ]
    page_fit_success_measured = [value for value in page_fit_success_values if _is_recorded(value)]
    page_fit_success_pass = sum(value is True for value in page_fit_success_measured)
    page_fit_success_fail = sum(value is False for value in page_fit_success_measured)
    page_fit_success_total = len(page_fit_success_values)
    accepted_non_one_page_count = page_fit_success_fail
    coverage["page_fit_success"] = {
        "measured": len(page_fit_success_measured),
        "unavailable": page_fit_success_total - len(page_fit_success_measured),
        "total": page_fit_success_total,
        "rate": page_fit_success_pass / page_fit_success_total if page_fit_success_total else 0.0,
        "complete": bool(page_fit_success_total and len(page_fit_success_measured) == page_fit_success_total),
    }
    run_types = sorted({
        job_type
        for snapshot in snapshots
        for job_type in dict(snapshot.get("coverage") or {}).get("run_job_diversity", {}).get("job_types", [])
    })
    aggregate_end_to_end_wall = sum(float(snapshot.get("elapsed_wall_ms") or 0) for snapshot in snapshots)
    yield_totals = {
        field: sum(int(dict(snapshot.get("yield") or {}).get(field) or 0) for snapshot in snapshots)
        for field in (
            "attempted_generation_job_count",
            "first_pass_acceptance_count",
            "retry_success_count",
            "retry_failure_count",
        )
    }
    yield_totals["first_pass_acceptance_rate"] = (
        yield_totals["first_pass_acceptance_count"] / yield_totals["attempted_generation_job_count"]
        if yield_totals["attempted_generation_job_count"]
        else None
    )
    aggregate_provider_calls = sum(
        int(dict(snapshot["projection"].get("aggregate") or {}).get("provider_call_count") or 0)
        for snapshot in snapshots
    )
    aggregate_tokens = sum(
        int(dict(snapshot["projection"].get("aggregate") or {}).get("token_total") or 0)
        for snapshot in snapshots
    )
    aggregate_regenerations = sum(
        int(dict(snapshot["projection"].get("aggregate") or {}).get("regeneration_count") or 0)
        for snapshot in snapshots
    )
    aggregate_validation_failures = sum(
        int(dict(snapshot["projection"].get("aggregate") or {}).get("validation_failure_event_count") or 0)
        for snapshot in snapshots
    )
    terminal_validation_failed_jobs = sum(
        int(
            dict(dict(snapshot["projection"].get("aggregate") or {}).get("workload") or {}).get(
                "terminal_validation_failed_job_count"
            ) or 0
        )
        for snapshot in snapshots
    )
    aggregate_elapsed = sum(
        float(dict(snapshot["projection"].get("aggregate") or {}).get("elapsed_ms") or 0)
        for snapshot in snapshots
    )
    accepted_generation_elapsed_values = [
        float(dict(snapshot["projection"].get("aggregate") or {}).get("generation_elapsed_ms"))
        for snapshot in snapshots
        if dict(snapshot["projection"].get("aggregate") or {}).get("generation_elapsed_ms") is not None
    ]
    aggregate_generation_elapsed = (
        sum(accepted_generation_elapsed_values) if accepted_generation_elapsed_values else None
    )
    aggregate_stage_latency_samples = {stage: [] for stage in STAGE_NAMES}
    for snapshot in snapshots:
        for stage, values in dict(snapshot.get("stage_latency_samples_ms") or {}).items():
            if stage in aggregate_stage_latency_samples:
                aggregate_stage_latency_samples[stage].extend(_numeric_values(values))
    complete = (
        bool(snapshots)
        and accepted_count == accepted_record_count
        and unmatched_trace_count == 0
        and unattributed_count == 0
        and trace_normalization["conflict_count"] == 0
        and accepted_non_one_page_count == 0
        and bool(coverage.get("page_fit", {}).get("complete"))
        and bool(coverage.get("page_fit_success", {}).get("complete"))
        and page_fit_success_fail == 0
        and sum(int(snapshot.get("contract_coverage", {}).get("historical") or 0) for snapshot in snapshots) == 0
    )
    status = "complete" if complete else "incomplete" if snapshots else "not_available"
    per_accepted = None
    total_workload_per_accepted = None
    if accepted_count and accepted_count == accepted_record_count and unattributed_count == 0:
        per_accepted = {
            "provider_call_count": aggregate_provider_calls / accepted_count,
            "token_total": aggregate_tokens / accepted_count,
            "regeneration_count": aggregate_regenerations / accepted_count,
                "validation_failure_event_count": aggregate_validation_failures / accepted_count,
            "validation_failure_count": aggregate_validation_failures / accepted_count,
            "generation_elapsed_ms": (
                aggregate_generation_elapsed / accepted_count
                if aggregate_generation_elapsed is not None
                else None
            ),
            "elapsed_ms": aggregate_elapsed / accepted_count,
        }
        if complete:
            total_workload_per_accepted = {
                field: workload[field] / accepted_count if workload[field] is not None else None
                for field in (
                    "provider_call_count",
                    "token_total",
                    "regeneration_count",
                    "validation_failure_event_count",
                    "generation_elapsed_ms",
                )
            }
            total_workload_per_accepted["end_to_end_wall_ms"] = aggregate_end_to_end_wall / accepted_count
    generation_status_counts: Counter[str] = Counter()
    for snapshot in snapshots:
        generation_status_counts.update(snapshot["status_counts"])
    return {
        "schema_version": "fitcv_runtime_efficiency_baseline_v3",
        "contract_versions": {
            "final_artifact": FINAL_ARTIFACT_CONTRACT_VERSION,
            "trace": TRACE_CONTRACT_VERSION,
            "efficiency": EFFICIENCY_CONTRACT_VERSION,
        },
        "status": status,
        "trace_normalization": trace_normalization,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "selection": {
            "ordinary_runs_only": True,
            "measurable_generation_work_only": True,
            "contract_versions": {
                "final_artifact": FINAL_ARTIFACT_CONTRACT_VERSION,
                "trace": TRACE_CONTRACT_VERSION,
                "efficiency": EFFICIENCY_CONTRACT_VERSION,
            },
            "current_contract_record_count": sum(
                int(snapshot.get("contract_coverage", {}).get("current") or 0)
                for snapshot in snapshots
            ),
            "historical_record_count": sum(
                int(snapshot.get("contract_coverage", {}).get("historical") or 0)
                for snapshot in snapshots
            ),
            "run_count": len(snapshots),
            "run_ids": [snapshot["run_id"] for snapshot in snapshots],
            "exclusions": dict(sorted(exclusions.items())),
        },
        "workload": workload,
        "timing": {
            "generation_elapsed_ms": workload["generation_elapsed_ms"],
            "generation_timing_coverage": generation_timing_coverage,
            "artifact_acceptance_latency_ms": aggregate_elapsed,
            "run_wall_ms": aggregate_end_to_end_wall,
            "stage_latency_ms": _stage_latency_report(aggregate_stage_latency_samples),
        },
        "coverage": coverage,
        "run_job_diversity": {
            "run_count": len(snapshots),
            "job_count": workload["attempted_generation_job_count"],
            "job_type_count": len(run_types),
            "job_types": run_types,
        },
        "accepted_cv": {
            "count": accepted_count,
            "recorded_acceptance_count": accepted_record_count,
            "cost_per_accepted_cv": per_accepted,
            "accepted_artifact_cost_per_accepted_cv": per_accepted,
            "total_workload_cost_per_accepted_cv": total_workload_per_accepted,
            "accepted_non_one_page_count": accepted_non_one_page_count,
            "page_fit_success": {
                "count": page_fit_success_pass,
                "pass": page_fit_success_pass,
                "fail": page_fit_success_fail,
                "total": page_fit_success_total,
                "rate": page_fit_success_pass / page_fit_success_total if page_fit_success_total else 0.0,
            },
        },
        "attribution": {
            "unmatched_trace_count": unmatched_trace_count,
            "unattributed_accepted_artifact_count": unattributed_count,
            "accepted_non_one_page_count": accepted_non_one_page_count,
        },
        "yield": yield_totals,
        "aggregate": {
            "provider_call_count": aggregate_provider_calls,
            "token_total": aggregate_tokens,
            "regeneration_count": aggregate_regenerations,
            "validation_failure_event_count": aggregate_validation_failures,
            "validation_failure_count": aggregate_validation_failures,
            "terminal_validation_failed_job_count": terminal_validation_failed_jobs,
            "generation_elapsed_ms": aggregate_generation_elapsed,
            "end_to_end_wall_ms": aggregate_end_to_end_wall,
            "elapsed_ms": aggregate_elapsed,
        },
        "outcomes": {
            "generation_status_counts": dict(sorted(generation_status_counts.items())),
            "page_fit": {
                "pass": page_fit_success_pass,
                "fail": page_fit_success_fail,
                "total": page_fit_success_total,
                "rate": page_fit_success_pass / page_fit_success_total if page_fit_success_total else 0.0,
            },
            "render_retry_count": workload["render_retry_count"],
            "compiler_outcome_counts": {},
            "render_outcome_counts": {},
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "runs": snapshots,
    }


def material_report_metrics(report: dict[str, Any]) -> dict[str, Any]:
    return {
        field: report.get(field)
        for field in (
            "schema_version",
            "status",
            "selection",
            "workload",
            "accepted_cv",
            "attribution",
            "yield",
            "timing",
            "coverage",
            "run_job_diversity",
            "aggregate",
            "outcomes",
            "runs",
        )
    }


def material_report_digest(report: dict[str, Any]) -> str:
    payload = json.dumps(
        material_report_metrics(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _markdown(report: dict[str, Any]) -> str:
    workload = dict(report.get("workload") or {})
    accepted = dict(report.get("accepted_cv") or {})
    attribution = dict(report.get("attribution") or {})
    timing = dict(report.get("timing") or {})
    return "\n".join(
        [
            "# FitCV Runtime Efficiency Baseline",
            "",
            f"- Evidence status: `{report.get('evidence_status', 'generated')}`",
            f"- Status: `{report.get('status')}`",
            f"- Persisted ordinary runs: `{report.get('selection', {}).get('run_count', 0)}`",
            f"- Accepted CVs: `{accepted.get('count', 0)}`",
            f"- Recorded accepted generation outcomes: `{accepted.get('recorded_acceptance_count', 0)}`",
            f"- Attempted generation jobs: `{workload.get('attempted_generation_job_count', 0)}`",
            f"- Provider calls: `{workload.get('provider_call_count', 0)}`",
            f"- Tokens: `{workload.get('token_total', 0)}`",
            f"- Regenerations: `{workload.get('regeneration_count', 0)}`",
            f"- Render retries: `{workload.get('render_retry_count', 0)}`",
            f"- Unmatched traces: `{attribution.get('unmatched_trace_count', 0)}`",
            f"- Unattributed accepted artifacts: `{attribution.get('unattributed_accepted_artifact_count', 0)}`",
            f"- Accepted-artifact cost per accepted CV: `{accepted.get('accepted_artifact_cost_per_accepted_cv')}`",
            f"- Total-workload cost per accepted CV: `{accepted.get('total_workload_cost_per_accepted_cv')}`",
            f"- First-pass acceptance rate: `{dict(report.get('yield') or {}).get('first_pass_acceptance_rate')}`",
            f"- Retry success/failure: `{dict(report.get('yield') or {}).get('retry_success_count', 0)}` / `{dict(report.get('yield') or {}).get('retry_failure_count', 0)}`",
            f"- Generation duration aggregate: `{timing.get('generation_elapsed_ms')}`",
            f"- Generation timing coverage: `{timing.get('generation_timing_coverage')}`",
            f"- Artifact acceptance latency aggregate: `{timing.get('artifact_acceptance_latency_ms')}`",
            f"- Run wall-clock aggregate: `{timing.get('run_wall_ms')}`",
            f"- Measurement coverage: `{report.get('coverage', {})}`",
            f"- Run/job diversity: `{report.get('run_job_diversity', {})}`",
            "",
            "Stage latency p50/p95 is reported from explicit stage samples; missing stages stay unavailable.",
            "Generation duration, artifact acceptance latency, and run wall-clock time are separate metrics.",
            "Accepted-artifact and total-workload per-CV metrics stay null unless attribution is complete.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=None, help="SQLite control-plane database path")
    parser.add_argument("--run-id", action="append", dest="run_ids", help="Restrict selection to run ID")
    parser.add_argument("--limit", type=int, default=100, help="Maximum persisted runs to inspect")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    if args.database:
        os.environ["FITCV_CP_SQLITE_PATH"] = str(args.database)
    runs = sqlite_store.list_runs(limit=max(args.limit, 1), include_archived=True)
    if args.run_ids:
        selected = set(args.run_ids)
        runs = [run for run in runs if str(run.run_id) in selected]
    run_jobs_by_run_id = {
        str(run.run_id): list(sqlite_store.iter_run_jobs_for_export(str(run.run_id)))
        for run in runs
    }
    report = build_baseline(runs, run_jobs_by_run_id=run_jobs_by_run_id)
    report["material_metrics_sha256"] = material_report_digest(report)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.output_markdown.write_text(_markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "run_count": report["selection"]["run_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
