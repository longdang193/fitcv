from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "fitcv.acceptance_state.v1"
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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_state(state: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    _require(state.get("schema_version") == SCHEMA_VERSION, "schema_version invalid")
    _require(state.get("repository") == REPOSITORY, "repository invalid")
    source_commit = state.get("source_commit")
    _require(
        isinstance(source_commit, str) and re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None,
        "source_commit invalid",
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

    statuses = state.get("statuses")
    _require(isinstance(statuses, dict), "statuses invalid")
    _require(set(statuses) == REQUIRED_STATUSES, "statuses keys invalid")
    _require(all(value in ALLOWED_STATUSES for value in statuses.values()), "status value invalid")

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
