"""Compare paired FitCV efficiency reports without changing runtime defaults."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LOWER_IS_BETTER = (
    "provider_calls",
    "token_total",
    "regeneration_count",
    "generation_p95_ms",
    "human_actions",
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"report_not_object:{path}")
    return payload


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in {float("inf"), float("-inf")} else None


def _metric(report: dict[str, Any], name: str) -> float | None:
    aggregate = dict(report.get("aggregate") or {})
    timing = dict(report.get("timing") or {})
    yield_block = dict(report.get("yield") or {})
    if name == "generation_p95_ms":
        return _number(dict(dict(timing.get("stage_latency_ms") or {}).get("provider_generation") or {}).get("p95_ms"))
    if name == "human_actions":
        return _number(dict(report.get("optimization_scorecard") or {}).get("human_actions", {}).get("count"))
    source = {
        "provider_calls": aggregate.get("provider_call_count"),
        "token_total": aggregate.get("token_total"),
        "regeneration_count": aggregate.get("regeneration_count"),
    }.get(name)
    return _number(source)


def _quality(report: dict[str, Any]) -> dict[str, Any]:
    coverage = dict(report.get("coverage") or {})
    page_fit = dict(coverage.get("page_fit_success") or {})
    accepted = dict(report.get("accepted_cv") or {})
    return {
        "accepted_artifact_count": _number(accepted.get("count", report.get("gold_cv_effort", {}).get("accepted_artifact_count"))),
        "grounding": dict(coverage.get("grounding") or coverage.get("attribution") or {}),
        "one_page": page_fit,
    }


def _quality_complete(block: dict[str, Any]) -> bool:
    return bool(block) and bool(block.get("complete")) and _number(block.get("rate")) is not None


def _same_workload(baseline: dict[str, Any], optimized: dict[str, Any]) -> tuple[bool, str | None]:
    left = dict(baseline.get("input_manifest") or {})
    right = dict(optimized.get("input_manifest") or {})
    if not left or not right:
        return False, "workload_manifest_missing"
    for key in ("declared_input_fingerprint", "fixture_sha256", "repeat_count"):
        if not left.get(key) or not right.get(key) or left.get(key) != right.get(key):
            return False, f"workload_mismatch:{key}"
    return True, None


def compare_reports(
    baseline: dict[str, Any],
    optimized: dict[str, Any],
    *,
    min_relative_improvement: float,
) -> dict[str, Any]:
    same_workload, mismatch = _same_workload(baseline, optimized)
    metrics: dict[str, Any] = {}
    improvements: list[float] = []
    for name in LOWER_IS_BETTER:
        before = _metric(baseline, name)
        after = _metric(optimized, name)
        relative = None if before in (None, 0) or after is None else (before - after) / before
        metrics[name] = {"baseline": before, "optimized": after, "relative_improvement": relative}
        if relative is not None:
            improvements.append(relative)

    baseline_quality = _quality(baseline)
    optimized_quality = _quality(optimized)
    quality_regression = (
        optimized_quality["accepted_artifact_count"] is not None
        and baseline_quality["accepted_artifact_count"] is not None
        and optimized_quality["accepted_artifact_count"] < baseline_quality["accepted_artifact_count"]
    )
    page_fit_regression = bool(
        _quality_complete(baseline_quality["one_page"])
        and (
            not _quality_complete(optimized_quality["one_page"])
            or _number(optimized_quality["one_page"].get("rate"))
            < _number(baseline_quality["one_page"].get("rate"))
        )
    )
    grounding_regression = bool(
        _quality_complete(baseline_quality["grounding"])
        and (
            not _quality_complete(optimized_quality["grounding"])
            or _number(optimized_quality["grounding"].get("rate"))
            < _number(baseline_quality["grounding"].get("rate"))
        )
    )
    quality_evidence_missing = not all(
        _quality_complete(baseline_quality[name]) and _quality_complete(optimized_quality[name])
        for name in ("grounding", "one_page")
    )
    cost_regression = any(
        metrics[name]["baseline"] is not None
        and metrics[name]["optimized"] is not None
        and metrics[name]["optimized"] > metrics[name]["baseline"]
        for name in ("provider_calls", "token_total")
    )
    eligible = bool(
        same_workload
        and improvements
        and max(improvements) >= min_relative_improvement
        and not quality_evidence_missing
    )
    decision = (
        "promote"
        if eligible
        and not quality_regression
        and not page_fit_regression
        and not grounding_regression
        and not cost_regression
        else "hold"
    )
    return {
        "schema_version": "fitcv.optimization_comparison.v1",
        "status": "complete",
        "decision": decision,
        "minimum_relative_improvement": min_relative_improvement,
        "workload_match": same_workload,
        "workload_mismatch_reason": mismatch,
        "metrics": metrics,
        "quality": {
            "baseline": baseline_quality,
            "optimized": optimized_quality,
            "quality_regression": quality_regression,
            "one_page_regression": page_fit_regression,
            "grounding_regression": grounding_regression,
            "quality_evidence_missing": quality_evidence_missing,
            "cost_regression": cost_regression,
        },
        "production_defaults_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--optimized", type=Path, required=True)
    parser.add_argument("--min-relative-improvement", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare_reports(
        _load(args.baseline),
        _load(args.optimized),
        min_relative_improvement=args.min_relative_improvement,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "decision": result["decision"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
