"""Compare normalized requirement-support benchmark outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _validate_compatibility(payloads: list[dict[str, Any]]) -> None:
    fixture_hashes = {str(payload.get("fixture_sha256") or "") for payload in payloads}
    top_ks = {json.dumps(payload.get("top_k"), sort_keys=True) for payload in payloads}
    if len(fixture_hashes) != 1:
        raise ValueError("Benchmark outputs use different fixture SHA-256 values")
    if len(top_ks) != 1:
        raise ValueError("Benchmark outputs use different top_k values")


def _validate_impact_compatibility(payloads: list[dict[str, Any]]) -> None:
    _validate_compatibility(payloads)
    schema_versions = {int(payload.get("evaluation_schema_version") or 0) for payload in payloads}
    scenario_sets = {tuple(payload.get("scenario_set") or []) for payload in payloads}
    evidence_budgets = {tuple(payload.get("evidence_budgets") or []) for payload in payloads}
    if len(schema_versions) != 1:
        raise ValueError("Benchmark outputs use different evaluation schema versions")
    if len(scenario_sets) != 1:
        raise ValueError("Benchmark outputs use different scenario sets")
    if len(evidence_budgets) != 1:
        raise ValueError("Benchmark outputs use different evidence budgets")


def _current_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    support = dict(payload.get("requirement_support") or {})
    return {
        "implementation_ref": payload.get("implementation_ref"),
        "requirement_recall": dict(support.get("requirement_recall") or {}),
        "evidence_pair_recall": dict(support.get("evidence_pair_recall") or {}),
        "incorrect_pairs": list(support.get("incorrect_pairs") or []),
        "missed_pairs": list(support.get("missed_pairs") or []),
        "timing_ms": dict(payload.get("timing_ms") or {}),
        "context": dict(payload.get("context") or {}),
        "validation": dict(payload.get("validation") or {}),
        "micro_coverage": dict(support.get("micro_coverage") or {}),
        "macro_coverage": dict(support.get("macro_coverage") or {}),
        "assignment_precision": support.get("assignment_precision"),
    }


def _impact_delta(left: dict[str, Any], right: dict[str, Any], metric: str, stage: str) -> float | str:
    left_value = left.get(metric, {}).get(stage)
    right_value = right.get(metric, {}).get(stage)
    if isinstance(left_value, dict):
        left_value = left_value.get("selected")
    if isinstance(right_value, dict):
        right_value = right_value.get("selected")
    if not isinstance(left_value, (int, float)) or not isinstance(right_value, (int, float)):
        return "not_applicable"
    return round(float(right_value) - float(left_value), 6)


def run_inputs(input_paths: list[Path]) -> dict[str, Any]:
    if len(input_paths) < 2:
        raise ValueError("at least two benchmark inputs are required")
    payloads = [_load_json(path) for path in input_paths]
    _validate_impact_compatibility(payloads)
    by_arm = {str(payload.get("arm") or ""): payload for payload in payloads}
    required_arms = {
        "lexical-baseline",
        "lexical-ablation",
        "lexical-requirement-aware",
        "current-hash",
    }
    missing = sorted(required_arms - set(by_arm))
    if missing:
        raise ValueError(f"Benchmark inputs missing arms: {', '.join(missing)}")
    metrics = {arm: _current_metrics(by_arm[arm]) for arm in sorted(required_arms)}
    comparisons = {
        "baseline_vs_fitcv": {
            "from": "lexical-baseline",
            "to": "lexical-requirement-aware",
            "selected_requirement_recall_delta": _impact_delta(
                metrics["lexical-baseline"], metrics["lexical-requirement-aware"], "micro_coverage", "requirement_recall"
            ),
            "selected_evidence_pair_recall_delta": _impact_delta(
                metrics["lexical-baseline"], metrics["lexical-requirement-aware"], "micro_coverage", "evidence_pair_recall"
            ),
        },
        "ablation_vs_fitcv": {
            "from": "lexical-ablation",
            "to": "lexical-requirement-aware",
            "selected_requirement_recall_delta": _impact_delta(
                metrics["lexical-ablation"], metrics["lexical-requirement-aware"], "micro_coverage", "requirement_recall"
            ),
            "selected_evidence_pair_recall_delta": _impact_delta(
                metrics["lexical-ablation"], metrics["lexical-requirement-aware"], "micro_coverage", "evidence_pair_recall"
            ),
        },
        "fitcv_vs_current_hash": {
            "from": "lexical-requirement-aware",
            "to": "current-hash",
            "selected_requirement_recall_delta": _impact_delta(
                metrics["lexical-requirement-aware"], metrics["current-hash"], "micro_coverage", "requirement_recall"
            ),
            "selected_evidence_pair_recall_delta": _impact_delta(
                metrics["lexical-requirement-aware"], metrics["current-hash"], "micro_coverage", "evidence_pair_recall"
            ),
        },
    }
    return {
        "evaluation_schema_version": 1,
        "fixture_sha256": payloads[0].get("fixture_sha256"),
        "scenario_set": payloads[0].get("scenario_set"),
        "evidence_budgets": payloads[0].get("evidence_budgets"),
        "arms": metrics,
        "comparisons": comparisons,
        "limitations": [
            "Offline prompt token estimates do not support provider cost claims.",
            "Selected-evidence metrics do not measure final provider-generated CV quality.",
        ],
    }


def _legacy_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    selected = dict(payload.get("selected_metrics") or {})
    return {
        "implementation_ref": payload.get("implementation_ref"),
        "requirement_recall": {"selected": selected.get("requirement_recall")},
        "evidence_pair_recall": {"selected": selected.get("evidence_pair_recall")},
        "incorrect_pairs": list(selected.get("incorrect_pairs") or []),
        "missed_pairs": list(selected.get("missed_pairs") or []),
        "validation": {"status": "not_comparable"},
        "known_limitations": list(payload.get("known_limitations") or []),
    }


def run(
    baseline_path: Path,
    current_path: Path,
    retrieval_paths: list[Path],
) -> dict[str, Any]:
    baseline = _load_json(baseline_path)
    current = _load_json(current_path)
    retrieval = [_load_json(path) for path in retrieval_paths]
    _validate_compatibility([baseline, current, *retrieval])
    baseline_metrics = _legacy_metrics(baseline)
    current_metrics = _current_metrics(current)
    return {
        "evaluation_schema_version": 1,
        "fixture_sha256": current.get("fixture_sha256"),
        "top_k": current.get("top_k"),
        "experiments": {
            "feature_impact": {
                "baseline": baseline_metrics,
                "current": current_metrics,
                "selected_requirement_recall_delta": round(
                    float(current_metrics["requirement_recall"].get("selected") or 0.0)
                    - float(baseline_metrics["requirement_recall"].get("selected") or 0.0),
                    6,
                ),
                "selected_evidence_pair_recall_delta": round(
                    float(current_metrics["evidence_pair_recall"].get("selected") or 0.0)
                    - float(baseline_metrics["evidence_pair_recall"].get("selected") or 0.0),
                    6,
                ),
            },
            "retrieval_configuration": [
                {
                    "arm": payload.get("arm"),
                    "pool_size": payload.get("pool_size"),
                    "metrics": _current_metrics(payload),
                }
                for payload in retrieval
            ],
        },
        "limitations": [
            "Feature comparison uses selected evidence IDs because historical FitCV has no current requirement-support contract.",
            "Final provider-generated CV quality is not measured.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--current", type=Path)
    parser.add_argument("--retrieval", type=str)
    parser.add_argument("--inputs", type=str)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.inputs:
        result = run_inputs([Path(value) for value in args.inputs.split(",") if value])
    elif args.baseline and args.current and args.retrieval:
        retrieval_paths = [Path(value) for value in args.retrieval.split(",") if value]
        result = run(args.baseline, args.current, retrieval_paths)
    else:
        parser.error("provide --inputs or --baseline, --current, and --retrieval")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
