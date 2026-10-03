"""Summarize frozen CV generation evidence without inventing missing metrics."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("records", "results", "jobs", "artifacts", "outcomes"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _number(record: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def summarize(payload: Any, *, arm: str = "incumbent") -> dict[str, Any]:
    # ponytail: one reader, one summary; add richer experiment arms only when measured data needs them.
    records = _records(payload)
    accepted = [
        row for row in records
        if str(row.get("status") or row.get("final_status") or "").lower() in {"accepted", "generated"}
    ]
    latencies = [
        value for row in records
        if (value := _number(row, "whole_run_latency_ms", "generation_elapsed_ms", "elapsed_ms")) is not None
    ]
    provider_calls = [
        value for row in records
        if (value := _number(row, "provider_call_count", "provider_calls")) is not None
    ]
    token_totals = [
        value for row in records
        if (value := _number(row, "token_total", "tokens")) is not None
    ]
    first_pass = sum(
        str(row.get("status") or row.get("final_status") or "").lower() in {"accepted", "generated"}
        and int(_number(row, "attempt_count", "attempts") or 0) <= 1
        for row in records
    )
    one_page = sum(
        bool(row.get("accepted_final_one_page"))
        or row.get("render_page_count") == 1
        or row.get("page_count") == 1
        for row in accepted
    )
    failure_categories: dict[str, int] = {}
    for row in records:
        category = str(row.get("failure_category") or row.get("reason_code") or "").strip()
        if category:
            failure_categories[category] = failure_categories.get(category, 0) + 1
    top_level = payload.get("metrics") if isinstance(payload, dict) else None
    if isinstance(top_level, dict):
        for category, count in dict(top_level.get("failure_category_counts") or {}).items():
            if isinstance(count, int):
                failure_categories[str(category)] = count
    metrics = {
        "attempted_generation_jobs": len(records),
        "accepted_final_cvs": len(accepted),
        "first_pass_acceptance_count": first_pass,
        "first_pass_acceptance_rate": first_pass / len(records) if records else None,
        "accepted_final_one_page_count": one_page,
        "accepted_final_one_page_rate": one_page / len(accepted) if accepted else None,
        "provider_calls": sum(provider_calls) if provider_calls else None,
        "tokens": sum(token_totals) if token_totals else None,
        "latency_ms": {
            "measured_count": len(latencies),
            "p50": statistics.median(latencies) if latencies else None,
            "p95": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else None,
        },
        "failure_category_counts": failure_categories,
    }
    comparability = dict(payload.get("comparability") or {}) if isinstance(payload, dict) else {}
    return {
        "schema_version": "fitcv_efficiency_baseline_v1",
        "arm": arm,
        "status": "measured" if records else "insufficient_data",
        "comparability": comparability,
        "metrics": metrics,
        "promotion_allowed": bool(records) and comparability.get("comparable_to_historical_169_job_workload", True),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", default="incumbent")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summarize(payload, arm=args.arm), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
