"""Classify P0-B oracle pairs against current runtime stage traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    import scripts.evaluate_p0b_source_job_relevance as evaluator
except ModuleNotFoundError:
    import evaluate_p0b_source_job_relevance as evaluator


STAGE_ORDER = (
    "canonical_pool",
    "candidate_retrieval",
    "verification",
    "qualification",
    "selection",
    "assignment",
)
CATEGORIES = (
    "not_in_canonical_pool",
    "retrieval_loss",
    "verification_failure",
    "qualification_failure",
    "selection_loss",
    "assignment_loss",
    "supported_through_pipeline",
    "unsupported_selected",
    "unsupported_not_selected",
    "unjudged",
)
DEFAULT_OUTPUT = evaluator.REPO_ROOT / ".tmp/p0b-recovery-calibration.json"


def _pair_id(row: dict[str, Any]) -> str:
    return evaluator._public_pair_id(
        str(row.get("requirement_instance_id") or ""),
        str(row.get("evidence_id") or ""),
    )


def _trace_pairs(job_outputs: list[dict[str, Any]]) -> dict[str, set[str]]:
    pairs = {stage: set() for stage in STAGE_ORDER}
    for output in job_outputs:
        trace = dict(output.get("stage_traces") or {})
        for stage in STAGE_ORDER:
            pairs[stage].update(str(pair) for pair in list(trace.get(stage) or []))
    return pairs


def selected_pairs_from_review(review_rows: list[dict[str, Any]]) -> set[str]:
    selected: set[str] = set()
    for row in review_rows:
        requirement_id = str(row.get("requirement_instance_id") or "")
        for evidence_id in str(row.get("selected_evidence_ids") or "").split(";"):
            evidence_id = evidence_id.strip()
            if requirement_id and evidence_id:
                selected.add(f"{requirement_id}::{evidence_id}")
    return selected


def evaluate_protected_selection(
    oracle_rows: list[dict[str, Any]],
    selected_pairs: set[str],
) -> dict[str, Any]:
    oracle_by_pair = {_pair_id(row): row for row in oracle_rows}
    errors = [f"duplicate_pair:{_pair_id(row)}" for row in oracle_rows if list(oracle_by_pair).count(_pair_id(row)) > 1]
    judged_selected = selected_pairs & set(oracle_by_pair)
    supported_pairs = {
        pair_id for pair_id, row in oracle_by_pair.items()
        if evaluator._oracle_state(row) == "supported"
    }
    unsupported_selected = {
        pair_id for pair_id in judged_selected
        if evaluator._oracle_state(oracle_by_pair[pair_id]) == "unsupported"
    }
    unjudged_selected = {
        pair_id for pair_id in judged_selected
        if evaluator._oracle_state(oracle_by_pair[pair_id]) == "unjudged"
    }
    true_positive = len(judged_selected & supported_pairs)
    false_negative = len(supported_pairs - judged_selected)
    return {
        "true_positive": true_positive,
        "false_negative": false_negative,
        "pair_false_positive": len(unsupported_selected),
        "unjudged_selected": len(unjudged_selected),
        "support_recall": true_positive / len(supported_pairs) if supported_pairs else None,
        "errors": sorted(set(errors)),
    }


def classify_pairs(
    oracle_rows: list[dict[str, Any]],
    stage_pairs: dict[str, set[str]],
) -> dict[str, Any]:
    counts = {category: 0 for category in CATEGORIES}
    classified: dict[str, str] = {}
    examples: dict[str, list[str]] = {category: [] for category in CATEGORIES}
    errors: list[str] = []

    for row in oracle_rows:
        pair_id = _pair_id(row)
        if pair_id in classified:
            errors.append(f"duplicate_pair:{pair_id}")
            continue
        state = evaluator._oracle_state(row)
        if state == "unjudged":
            category = "unjudged"
        elif state == "unsupported":
            category = "unsupported_selected" if pair_id in stage_pairs["assignment"] else "unsupported_not_selected"
        elif state == "supported":
            if pair_id in stage_pairs["assignment"]:
                category = "supported_through_pipeline"
            else:
                missing = next(
                    (stage for stage in STAGE_ORDER if pair_id not in stage_pairs[stage]),
                    None,
                )
                category = {
                    "canonical_pool": "not_in_canonical_pool",
                    "candidate_retrieval": "retrieval_loss",
                    "verification": "verification_failure",
                    "qualification": "qualification_failure",
                    "selection": "selection_loss",
                    "assignment": "assignment_loss",
                }.get(missing or "", "assignment_loss")
        else:
            errors.append(f"invalid_oracle_state:{pair_id}:{state}")
            continue
        classified[pair_id] = category
        counts[category] += 1
        if len(examples[category]) < 20:
            examples[category].append(pair_id)

    if sum(counts.values()) != len(oracle_rows):
        errors.append("classification_not_exhaustive")
    if len(classified) != len(oracle_rows):
        errors.append("classification_not_unique")
    return {
        "counts": counts,
        "classified_pairs": classified,
        "examples": examples,
        "errors": sorted(set(errors)),
        "total_pairs": len(oracle_rows),
        "support_false_negatives": sum(
            counts[category]
            for category in (
                "not_in_canonical_pool",
                "retrieval_loss",
                "verification_failure",
                "qualification_failure",
                "selection_loss",
                "assignment_loss",
            )
        ),
        "pair_false_positives": counts["unsupported_selected"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    oracle = evaluator._load_jsonl(evaluator._public_path(args.oracle))
    review_rows = evaluator._load_evidence_link_review(
        evaluator._public_path(args.evidence_link_review)
    )
    acceptance_state = evaluator._load_acceptance_state(args.acceptance_state)
    projection = evaluator._load_jsonl(evaluator._public_path(args.projection))
    public_validation = evaluator.validate_public_inputs(
        projection,
        review_rows,
        oracle,
        acceptance_state,
    )
    manifest_path = evaluator.DEFAULT_ORACLE_MANIFEST
    manifest_errors = evaluator._validate_oracle_manifest(args.oracle, manifest_path, oracle)
    public_validation["errors"] = sorted(set([*public_validation["errors"], *manifest_errors]))
    public_validation["passed"] = not public_validation["errors"]
    config = evaluator.yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    config.setdefault("cv_analysis", {}).setdefault("diagnostics", {})["full_stage_traces"] = True
    if not public_validation["passed"]:
        return {
            "schema_version": "p0b.recovery_calibration.v1",
            "source": "current_runtime_stage_traces_against_accepted_oracle",
            "protected_result_reused": False,
            "validation": {
                "public_inputs_passed": False,
                "public_input_errors": list(public_validation["errors"]),
                "review_rows": len(review_rows),
                "source_jobs": 0,
                "classification_errors": [],
            },
            "stage_counts": {stage: 0 for stage in STAGE_ORDER},
            "classification": {"counts": {}, "errors": list(public_validation["errors"])},
            "dominant_loss": "validation_failure",
        }
    profile = {
        "schema_version": "candidate-profile.v1",
        "_projected_evidence_pool": projection,
    }
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in review_rows:
        rows_by_source.setdefault(str(row.get("source_record_id") or ""), []).append(row)
    job_outputs: list[dict[str, Any]] = []
    for source_record_id, rows in sorted(rows_by_source.items()):
        job_context = {
            "responsibilities": [str(row.get("requirement_text") or "") for row in rows],
            "responsibility_entities": [
                {
                    "source_requirement_id": str(row.get("requirement_instance_id") or ""),
                    "text": str(row.get("requirement_text") or ""),
                }
                for row in rows
            ],
            "title": "",
            "required_skills": [],
            "required_skill_entities": [],
        }
        bundle = evaluator.retrieve_evidence_bundle(profile, job_context, top_k=2, config=config)
        job_outputs.append({"source_record_id": source_record_id, "stage_traces": bundle.get("stage_traces") or {}})
    stage_pairs = _trace_pairs(job_outputs)
    classification = classify_pairs(oracle, stage_pairs)
    protected_selection = evaluate_protected_selection(
        oracle,
        selected_pairs_from_review(review_rows),
    )
    return {
        "schema_version": "p0b.recovery_calibration.v1",
        "source": "current_runtime_stage_traces_against_accepted_oracle",
        "protected_result_reused": False,
        "validation": {
            "public_inputs_passed": bool(public_validation.get("passed")),
            "public_input_errors": list(public_validation.get("errors") or []),
            "review_rows": len(review_rows),
            "source_jobs": len(job_outputs),
            "classification_errors": list(classification["errors"]),
        },
        "stage_counts": {stage: len(values) for stage, values in stage_pairs.items()},
        "protected_surface": {
            "prediction_source": "review_rows.selected_evidence_ids",
            **protected_selection,
        },
        "classification": {
            key: value
            for key, value in classification.items()
            if key != "classified_pairs"
        },
        "dominant_loss": max(
            (
                category
                for category in CATEGORIES
                if category in {
                    "not_in_canonical_pool",
                    "retrieval_loss",
                    "verification_failure",
                    "qualification_failure",
                    "selection_loss",
                    "assignment_loss",
                }
            ),
            key=lambda category: classification["counts"][category],
            default="none",
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection", type=Path, default=evaluator.DEFAULT_PROJECTION)
    parser.add_argument("--evidence-link-review", type=Path, default=evaluator.DEFAULT_EVIDENCE_LINK_REVIEW)
    parser.add_argument("--oracle", type=Path, default=evaluator.REPO_ROOT / "data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl")
    parser.add_argument("--acceptance-state", type=Path, default=evaluator.DEFAULT_ACCEPTANCE_STATE)
    parser.add_argument("--policy", type=Path, default=evaluator.DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation"]["public_inputs_passed"] and not report["validation"]["classification_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
