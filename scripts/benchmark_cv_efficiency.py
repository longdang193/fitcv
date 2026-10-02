"""Report CV runtime efficiency from persisted ordinary pipeline runs."""

from __future__ import annotations

import argparse
import datetime
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
from fitcv_cp.run_artifact_contracts import build_accepted_cv_effort_projection

DEFAULT_JSON = REPO_ROOT / "docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md"


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


def _trace_generation_elapsed_ms(trace: dict[str, Any]) -> float:
    efficiency = dict(trace.get("efficiency_summary") or {})
    raw_elapsed = efficiency.get("elapsed_ms")
    if raw_elapsed is not None:
        try:
            return max(float(raw_elapsed), 0.0)
        except (TypeError, ValueError):
            return 0.0
    started = _timestamp(trace.get("generation_started_at") or trace.get("started_at"))
    finished = _timestamp(trace.get("generation_finished_at") or trace.get("finished_at"))
    if started is not None and finished is not None and finished >= started:
        return (finished - started).total_seconds() * 1000
    return 0.0


def _trace_final_accepted(trace: dict[str, Any], attempts: list[dict[str, Any]]) -> bool:
    output_summary = dict(trace.get("output_summary") or {})
    final_status = str(output_summary.get("final_status") or trace.get("status") or "").strip().lower()
    if final_status:
        return final_status in {"accepted", "succeeded", "success"}
    return bool(attempts and str(attempts[-1].get("provider_status") or "").strip().lower() == "accepted")


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
    traces = _trace_records(payload)
    actions = [item for item in list(payload.get("hitl_review_actions") or []) if isinstance(item, dict)]
    artifacts = [item for item in list(payload.get("accepted_artifact_events") or []) if isinstance(item, dict)]
    projection = build_accepted_cv_effort_projection(
        records,
        actions,
        artifacts,
        generation_trace_records=traces,
    )
    if projection.get("status") == "not_run":
        return None
    generation_elapsed_ms = sum(_trace_generation_elapsed_ms(trace) for trace in traces)
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
    return {
        "run_id": run_id,
        "created_at": created_at.isoformat() if created_at else None,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "elapsed_wall_ms": elapsed_wall_ms,
        "generation_elapsed_ms": generation_elapsed_ms,
        "yield": {
            "attempted_generation_job_count": len(traces),
            "first_pass_acceptance_count": first_pass_acceptance_count,
            "retry_success_count": retry_success_count,
            "retry_failure_count": retry_failure_count,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "accepted_record_count": status_counts.get("accepted", 0),
        "projection": projection,
    }


def _sum_workload(snapshots: list[dict[str, Any]]) -> dict[str, int]:
    fields = (
        "attempted_generation_job_count",
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


def build_baseline(runs: Iterable[Any]) -> dict[str, Any]:
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
    workload["generation_elapsed_ms"] = sum(
        float(snapshot.get("generation_elapsed_ms") or 0) for snapshot in snapshots
    )
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
        int(dict(snapshot["projection"].get("aggregate") or {}).get("validation_failure_count") or 0)
        for snapshot in snapshots
    )
    aggregate_elapsed = sum(
        float(dict(snapshot["projection"].get("aggregate") or {}).get("elapsed_ms") or 0)
        for snapshot in snapshots
    )
    aggregate_generation_elapsed = sum(
        float(dict(snapshot["projection"].get("aggregate") or {}).get("generation_elapsed_ms") or 0)
        for snapshot in snapshots
    )
    complete = (
        bool(snapshots)
        and accepted_count == accepted_record_count
        and unmatched_trace_count == 0
        and unattributed_count == 0
    )
    status = "complete" if complete else "incomplete" if snapshots else "not_available"
    per_accepted = None
    total_workload_per_accepted = None
    if complete and accepted_count:
        per_accepted = {
            "provider_call_count": aggregate_provider_calls / accepted_count,
            "token_total": aggregate_tokens / accepted_count,
            "regeneration_count": aggregate_regenerations / accepted_count,
            "validation_failure_count": aggregate_validation_failures / accepted_count,
            "generation_elapsed_ms": aggregate_generation_elapsed / accepted_count,
            "elapsed_ms": aggregate_elapsed / accepted_count,
        }
        total_workload_per_accepted = {
            field: workload[field] / accepted_count
            for field in (
                "provider_call_count",
                "token_total",
                "regeneration_count",
                "validation_failure_count",
                "generation_elapsed_ms",
            )
        }
        total_workload_per_accepted["end_to_end_wall_ms"] = aggregate_end_to_end_wall / accepted_count
    generation_status_counts: Counter[str] = Counter()
    for snapshot in snapshots:
        generation_status_counts.update(snapshot["status_counts"])
    return {
        "schema_version": "fitcv_runtime_efficiency_baseline_v1",
        "status": status,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "selection": {
            "ordinary_runs_only": True,
            "measurable_generation_work_only": True,
            "run_count": len(snapshots),
            "run_ids": [snapshot["run_id"] for snapshot in snapshots],
            "exclusions": dict(sorted(exclusions.items())),
        },
        "workload": workload,
        "accepted_cv": {
            "count": accepted_count,
            "recorded_acceptance_count": accepted_record_count,
            "cost_per_accepted_cv": per_accepted,
            "accepted_artifact_cost_per_accepted_cv": per_accepted,
            "total_workload_cost_per_accepted_cv": total_workload_per_accepted,
        },
        "attribution": {
            "unmatched_trace_count": unmatched_trace_count,
            "unattributed_accepted_artifact_count": unattributed_count,
        },
        "yield": yield_totals,
        "aggregate": {
            "provider_call_count": aggregate_provider_calls,
            "token_total": aggregate_tokens,
            "regeneration_count": aggregate_regenerations,
            "validation_failure_count": aggregate_validation_failures,
            "generation_elapsed_ms": aggregate_elapsed,
            "end_to_end_wall_ms": aggregate_end_to_end_wall,
            "elapsed_ms": aggregate_elapsed,
        },
        "outcomes": {
            "generation_status_counts": dict(sorted(generation_status_counts.items())),
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


def _markdown(report: dict[str, Any]) -> str:
    workload = dict(report.get("workload") or {})
    accepted = dict(report.get("accepted_cv") or {})
    attribution = dict(report.get("attribution") or {})
    return "\n".join(
        [
            "# FitCV Runtime Efficiency Baseline",
            "",
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
            "",
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
    report = build_baseline(runs)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.output_markdown.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "run_count": report["selection"]["run_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
