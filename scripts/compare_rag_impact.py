"""Compare paired RAG impact metrics without provider access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _delta(baseline: Any, fitcv: Any) -> float | str:
    left = _number(baseline)
    right = _number(fitcv)
    return round(right - left, 6) if left is not None and right is not None else "not_applicable"


def _gate(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "reason": reason}


def _quality_gate(delta: Any, maximum_loss: Any, label: str) -> dict[str, str]:
    value = _number(delta)
    threshold = _number(maximum_loss)
    if value is None or threshold is None:
        return _gate("not_applicable", f"{label} requires complete paired metrics")
    return _gate("pass" if value >= -threshold else "fail", f"FitCV-minus-baseline {label}: {value}")


def compare_report(report: dict[str, Any]) -> dict[str, Any]:
    metrics = dict(report.get("metrics") or {})
    arms = dict(metrics.get("by_variant") or {})
    baseline = dict(arms.get("baseline") or {})
    fitcv = dict(arms.get("fitcv") or {})
    metric_names = (
        "requirement_coverage",
        "reviewed_factual_precision",
        "human_quality_score",
        "generation_input_tokens",
        "total_generation_tokens",
        "cost",
        "latency_ms",
    )
    arm_metrics = {
        variant: {name: values.get(name) for name in metric_names}
        for variant, values in (("baseline", baseline), ("fitcv", fitcv))
    }
    deltas = {
        name: _delta(baseline.get(name), fitcv.get(name))
        for name in metric_names
    }
    thresholds = dict(report.get("thresholds") or {})
    thresholds.setdefault("human_quality_loss_points", 0.25)
    thresholds.setdefault("max_mean_qualification_coverage_loss", 0.05)
    thresholds.setdefault("max_mean_reviewed_factual_precision_loss", 0.02)
    reduction_threshold = thresholds.get(
        "held_out_generation_input_reduction_fraction",
        thresholds.get("rag_generation_input_tokens_lower_in_fraction", 0.8),
    )
    context = dict(metrics.get("context") or {})
    lower_fraction = context.get(
        "fitcv_input_tokens_lower_fraction",
        metrics.get("fitcv_input_tokens_lower_fraction"),
    )
    coverage_gate = _quality_gate(
        deltas["requirement_coverage"],
        thresholds.get("max_mean_qualification_coverage_loss"),
        "requirement coverage",
    )
    precision_gate = _quality_gate(
        deltas["reviewed_factual_precision"],
        thresholds.get("max_mean_reviewed_factual_precision_loss"),
        "reviewed factual precision",
    )
    human_gate = _quality_gate(
        deltas["human_quality_score"],
        thresholds.get("human_quality_loss_points"),
        "human quality",
    )
    lower_value = _number(lower_fraction)
    reduction_gate = (
        _gate(
            "pass" if lower_value >= float(reduction_threshold) else "fail",
            f"FitCV input-token reduction fraction: {lower_value}",
        )
        if lower_value is not None
        else _gate("not_applicable", "generation-input token telemetry is unavailable")
    )
    cost_delta = _number(deltas["cost"])
    cost_gate = (
        _gate("pass" if cost_delta <= 0 else "fail", f"FitCV-minus-baseline cost: {cost_delta}")
        if cost_delta is not None
        else _gate("not_applicable", "paired provider cost telemetry is unavailable")
    )
    latency_value = _number(deltas["latency_ms"])
    latency_gate = (
        _gate("pass" if latency_value <= 0 else "fail", f"FitCV-minus-baseline latency: {latency_value}")
        if latency_value is not None
        else _gate("not_applicable", "latency telemetry is unavailable")
    )
    quality_statuses = {coverage_gate["status"], precision_gate["status"], human_gate["status"]}
    quality_gate = (
        _gate("fail", "one or more quality gates failed")
        if "fail" in quality_statuses
        else _gate("not_applicable", "human or deterministic quality data is incomplete")
        if "not_applicable" in quality_statuses
        else _gate("pass", "quality loss stays within thresholds")
    )
    rollout_status = "pass" if all(
        gate["status"] == "pass" for gate in (quality_gate, reduction_gate, cost_gate, latency_gate)
    ) else "not_applicable" if any(
        gate["status"] == "not_applicable" for gate in (quality_gate, reduction_gate, cost_gate, latency_gate)
    ) else "fail"
    return {
        "evaluation_schema_version": 1,
        "fixture_sha256": report.get("fixture_sha256"),
        "rubric_fingerprint": report.get("rubric_fingerprint"),
        "config_fingerprint": report.get("config_fingerprint"),
        "pair_count": report.get("pair_count", 0),
        "raw_counts": {
            variant: {
                key: values.get(key)
                for key in ("attempted_calls", "succeeded_calls", "failed_calls", "first_pass_accepted", "final_accepted", "unresolved_review_count")
            }
            for variant, values in arms.items()
        },
        "arm_metrics": arm_metrics,
        "deltas": deltas,
        "confidence_intervals": dict(metrics.get("confidence_intervals") or {}),
        "gates": {
            "quality_parity": quality_gate,
            "requirement_coverage": coverage_gate,
            "reviewed_factual_precision": precision_gate,
            "human_quality": human_gate,
            "context_reduction": reduction_gate,
            "cost": cost_gate,
            "latency": latency_gate,
            "production_rollout": _gate(rollout_status, "all required gates pass" if rollout_status == "pass" else "missing or failed gate evidence"),
        },
        "thresholds": thresholds,
        "limitations": [
            "Human quality and preference claims remain not_applicable when review coverage is incomplete.",
            "Actual cost remains not_applicable without provider cost telemetry; estimates are not actual cost.",
            "This report compares supplied evaluator artifacts and makes no provider calls.",
        ],
    }


def compare_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one evaluator report is required")
    for field in ("fixture_sha256", "rubric_fingerprint", "config_fingerprint"):
        values = {str(report.get(field) or "") for report in reports}
        if len(values) > 1:
            raise ValueError(f"reports use different {field}")
    return compare_report(reports[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--inputs", type=str)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.inputs:
        paths = [Path(value) for value in args.inputs.split(",") if value]
    elif args.input:
        paths = [args.input]
    else:
        parser.error("provide --input or --inputs")
    result = compare_reports([_load_json(path) for path in paths])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
