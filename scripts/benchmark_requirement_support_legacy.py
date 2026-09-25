"""Run selected-evidence baseline probe against a historical FitCV checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(source_root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _selected_pairs(selected_ids: list[str], expected_support: dict[str, list[str]]) -> set[tuple[str, str]]:
    selected = set(selected_ids)
    return {
        (requirement_id, evidence_id)
        for requirement_id, evidence_ids in expected_support.items()
        for evidence_id in evidence_ids
        if evidence_id in selected
    }


def run(source_root: Path, fixture_path: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    fixture = _load_json(fixture_path)
    source_src = source_root / "src"
    if not source_src.is_dir():
        raise RuntimeError(f"Historical source root has no src directory: {source_root}")
    sys.path.insert(0, str(source_src))
    from fitcv.evidence import retrieve_evidence_bundle

    profile = dict(fixture.get("profile") or {})
    job_context = dict(fixture.get("job_context") or {})
    expected_support = {
        str(key): [str(value) for value in list(values or [])]
        for key, values in dict(fixture.get("expected_support") or {}).items()
    }
    bundle = retrieve_evidence_bundle(
        profile,
        job_context,
        int(fixture.get("top_k") or 0),
        config=None,
    )
    selected_ids = [
        str(item.get("evidence_id") or "")
        for item in list(bundle.get("selected_evidence") or [])
        if str(item.get("evidence_id") or "")
    ]
    selected_pairs = _selected_pairs(selected_ids, expected_support)
    expected_pairs = {
        (requirement_id, evidence_id)
        for requirement_id, evidence_ids in expected_support.items()
        for evidence_id in evidence_ids
    }
    positive_requirements = {key for key, values in expected_support.items() if values}
    selected_requirements = {requirement_id for requirement_id, _ in selected_pairs}
    return {
        "evaluation_schema_version": 1,
        "implementation_ref": _git_head(source_root),
        "fixture_sha256": _fixture_sha256(fixture_path),
        "top_k": int(fixture.get("top_k") or 0),
        "selected_evidence_ids": selected_ids,
        "selected_metrics": {
            "requirement_recall": round(
                len(selected_requirements) / len(positive_requirements), 6
            )
            if positive_requirements
            else 1.0,
            "evidence_pair_recall": round(
                len(selected_pairs & expected_pairs) / len(expected_pairs), 6
            )
            if expected_pairs
            else 1.0,
            "incorrect_pairs": [],
            "missed_pairs": [list(pair) for pair in sorted(expected_pairs - selected_pairs)],
        },
        "baseline_adapter_status": "selected_evidence_only",
        "known_limitations": [
            "Historical bundle has no current requirement-support maps.",
            "Historical validation contract is not comparable to current grounding cases.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source_root, args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
