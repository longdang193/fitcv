from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "fitcv.acceptance_state.v2"
REPOSITORY = "longdang193/fitcv"
REQUIRED_STATUSES = {
    "p0_a",
    "p0_b",
    "p0_c",
    "p1_a",
    "p1_b",
    "p1_c",
    "p2",
}
ALLOWED_STATUSES = {
    "rejected",
    "blocked",
    "protected",
    "maintenance_only",
    "measurement_only",
    "deferred",
    "passed",
}
STATUS_DIMENSION_FIELDS = {
    "implementation_status",
    "acceptance_status",
    "measurement_status",
}
ALLOWED_IMPLEMENTATION_STATUSES = {
    "verified",
    "unverified",
    "not_in_scope",
    "maintenance_only",
    "deferred",
    "rejected",
}
ALLOWED_ACCEPTANCE_STATUSES = {
    "passed",
    "blocked",
    "maintenance_only",
    "deferred",
    "rejected",
}
ALLOWED_MEASUREMENT_STATUSES = {
    "frozen_scope_only",
    "measured",
    "incomplete",
    "not_applicable",
    "not_run",
    "blocked",
}
ALLOWED_RUNTIME_MEASUREMENT_STATUSES = {"measured", "incomplete", "blocked"}
OPTIMIZATION_RESULT_FIELDS = {
    "experiment",
    "promotion",
    "production_default",
    "evidence",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_state(state: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    _require(state.get("schema_version") == SCHEMA_VERSION, "schema_version invalid")
    _require(state.get("repository") == REPOSITORY, "repository invalid")
    evaluation_freeze_commit = state.get("evaluation_freeze_commit")
    _require(
        isinstance(evaluation_freeze_commit, str)
        and re.fullmatch(r"[0-9a-f]{40}", evaluation_freeze_commit) is not None,
        "evaluation_freeze_commit invalid",
    )
    sanitizer_version = state.get("sanitizer_version")
    _require(isinstance(sanitizer_version, str) and sanitizer_version.strip(), "sanitizer_version invalid")
    contract_versions = state.get("contract_versions")
    _require(isinstance(contract_versions, dict) and contract_versions, "contract_versions invalid")

    manifests = state.get("corpus_manifests")
    _require(isinstance(manifests, list) and manifests and all(isinstance(item, str) for item in manifests), "corpus_manifests invalid")
    evidence_paths = state.get("evidence_paths")
    _require(isinstance(evidence_paths, list) and evidence_paths and all(isinstance(item, str) for item in evidence_paths), "evidence_paths invalid")
    for relative_path in [*manifests, *evidence_paths]:
        _require((repo_root / relative_path).is_file(), f"missing reference: {relative_path}")

    current_evidence = state.get("current_contract_evidence")
    if current_evidence is not None:
        _require(isinstance(current_evidence, dict), "current_contract_evidence invalid")
        for key in ("json", "markdown", "sha256"):
            relative_path = current_evidence.get(key)
            _require(
                isinstance(relative_path, str) and (repo_root / relative_path).is_file(),
                f"current_contract_evidence missing reference: {key}",
            )
        digest_text = (repo_root / str(current_evidence["sha256"])).read_text(encoding="utf-8").strip()
        _require(
            re.fullmatch(r"[0-9a-f]{64}\s+\S+", digest_text) is not None,
            "current_contract_evidence digest invalid",
        )

    optimization_result = state.get("optimization_result")
    if optimization_result is not None:
        _require(isinstance(optimization_result, dict), "optimization_result invalid")
        _require(set(optimization_result) == OPTIMIZATION_RESULT_FIELDS, "optimization_result fields invalid")
        _require(optimization_result.get("experiment") == "complete", "optimization experiment invalid")
        _require(optimization_result.get("promotion") == "rejected", "optimization promotion invalid")
        _require(optimization_result.get("production_default") == "unchanged", "optimization default invalid")
        _require(isinstance(optimization_result.get("evidence"), list), "optimization evidence invalid")

    statuses = state.get("statuses")
    _require(isinstance(statuses, dict), "statuses invalid")
    _require(set(statuses) == REQUIRED_STATUSES, "statuses keys invalid")
    _require(all(value in ALLOWED_STATUSES for value in statuses.values()), "status value invalid")

    status_dimensions = state.get("status_dimensions")
    _require(isinstance(status_dimensions, dict), "status_dimensions invalid")
    _require(set(status_dimensions) == REQUIRED_STATUSES, "status_dimensions keys invalid")
    for priority, dimensions in status_dimensions.items():
        _require(isinstance(dimensions, dict), f"{priority} status_dimensions invalid")
        _require(set(dimensions) == STATUS_DIMENSION_FIELDS, f"{priority} status_dimensions fields invalid")
        _require(
            dimensions.get("implementation_status") in ALLOWED_IMPLEMENTATION_STATUSES,
            f"{priority} implementation_status invalid",
        )
        _require(
            dimensions.get("acceptance_status") in ALLOWED_ACCEPTANCE_STATUSES,
            f"{priority} acceptance_status invalid",
        )
        _require(
            dimensions.get("measurement_status") in ALLOWED_MEASUREMENT_STATUSES,
            f"{priority} measurement_status invalid",
        )

    runtime_efficiency = state.get("runtime_efficiency")
    _require(isinstance(runtime_efficiency, dict), "runtime_efficiency invalid")
    _require(
        runtime_efficiency.get("measurement_status") in ALLOWED_RUNTIME_MEASUREMENT_STATUSES,
        "runtime_efficiency measurement_status invalid",
    )
    baseline_evidence = runtime_efficiency.get("baseline_evidence")
    _require(isinstance(baseline_evidence, dict), "runtime_efficiency baseline_evidence invalid")
    for key in ("json", "markdown"):
        relative_path = baseline_evidence.get(key)
        _require(
            isinstance(relative_path, str) and (repo_root / relative_path).is_file(),
            f"runtime_efficiency missing reference: {key}",
        )
    _require(
        runtime_efficiency.get("accepted_artifact_and_total_workload_metrics") is True,
        "runtime_efficiency metric families invalid",
    )
    _require(runtime_efficiency.get("p1_c") == "deferred", "runtime_efficiency p1_c invalid")
    _require(runtime_efficiency.get("p2") == "deferred", "runtime_efficiency p2 invalid")

    thresholds = state.get("support_thresholds")
    _require(isinstance(thresholds, dict), "support_thresholds invalid")
    _require(thresholds.get("maximum_pair_false_positives") == 0, "maximum_pair_false_positives invalid")
    for key in ("minimum_review_completeness", "minimum_oracle_coverage"):
        value = thresholds.get(key)
        _require(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1, f"{key} invalid")
    recall_threshold = thresholds.get("support_recall_threshold")
    _require(
        recall_threshold is None
        or (isinstance(recall_threshold, (int, float)) and not isinstance(recall_threshold, bool) and 0 <= recall_threshold <= 1),
        "support_recall_threshold invalid",
    )
    return state


def render_acceptance_state(
    input_path: Path,
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[1]
    raw = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    _require(isinstance(raw, dict), "acceptance state must be an object")
    state = _validate_state(raw, root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render_acceptance_state(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
