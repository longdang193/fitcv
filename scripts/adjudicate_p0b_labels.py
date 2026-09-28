"""Adjudicate two P0-B reviewer label sets conservatively."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _rows(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["requirement_instance_id"]), str(row.get("evidence_id") or ""))
        if key in result:
            raise ValueError(f"duplicate label key at {path}:{line_number}: {key}")
        result[key] = row
    return result


def _adjudicate(
    reviewer_a: dict[str, Any],
    reviewer_b: dict[str, Any],
) -> dict[str, Any]:
    key_a = (str(reviewer_a["requirement_instance_id"]), str(reviewer_a.get("evidence_id") or ""))
    key_b = (str(reviewer_b["requirement_instance_id"]), str(reviewer_b.get("evidence_id") or ""))
    if key_a != key_b:
        raise ValueError(f"reviewers label different requirement/evidence pairs: {key_a} != {key_b}")
    final = dict(reviewer_b)
    a_verdict = str(reviewer_a.get("support_verdict") or "unknown")
    b_verdict = str(reviewer_b.get("support_verdict") or "unknown")
    disagreement = a_verdict != b_verdict
    if disagreement:
        final["support_verdict"] = "unknown"
    final["review_status"] = "reviewed"
    final["adjudication"] = {
        "status": "conservative_unknown" if disagreement else "agreed",
        "reviewer_count": 2,
        "reviewer_a_support_verdict": a_verdict,
        "reviewer_b_support_verdict": b_verdict,
        "note": (
            "Reviewers disagreed; final verdict is unknown and no production claim is allowed."
            if disagreement
            else "Independent reviewers agreed."
        ),
    }
    final["schema_version"] = "p0b.reviewed_requirement_evidence.adjudicated.v1"
    return final


def _payload(rows: list[dict[str, Any]], disagreements: list[str], inputs: dict[str, str]) -> tuple[str, dict[str, Any]]:
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    manifest = {
        "schema_version": "p0b.reviewed_requirement_evidence_adjudicated_manifest.v1",
        "status": "admitted_for_benchmark_only",
        "output": "data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_expanded.jsonl",
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "records": len(rows),
        "requirement_instances": len({row["requirement_instance_id"] for row in rows}),
        "evidence_ids": len({str(row.get("evidence_id") or "") for row in rows}),
        "languages": dict(sorted(Counter(row["language"] for row in rows).items())),
        "splits": dict(sorted(Counter(row["split"] for row in rows).items())),
        "support_verdicts": dict(sorted(Counter(row["support_verdict"] for row in rows).items())),
        "review_statuses": dict(sorted(Counter(row["review_status"] for row in rows).items())),
        "reviewer_agreement": {
            "reviewed_records": len(rows),
            "disagreements": len(disagreements),
            "agreement_rate": round((len(rows) - len(disagreements)) / len(rows), 6) if rows else 0.0,
            "disagreement_requirement_instances": disagreements,
        },
        "inputs": inputs,
        "promotion_blocked": True,
        "blockers": [
            "Labels use one redacted candidate profile and remain benchmark-only.",
            "Translation pairing is unasserted.",
            "Production recall promotion requires broader candidate/job pairing and approved taxonomy coverage.",
        ],
    }
    return text, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--initial-reviewer-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    initial_a = _rows(args.initial)
    initial_b = _rows(args.initial_reviewer_b)
    reviewer_a = _rows(args.reviewer_a)
    reviewer_b = _rows(args.reviewer_b)
    if set(initial_a) != set(initial_b):
        raise ValueError("initial reviewer label keys differ")
    if set(reviewer_a) != set(reviewer_b):
        raise ValueError("expanded reviewer requirement/evidence keys differ")
    if len(reviewer_a) != 50:
        raise ValueError(f"expected 50 expanded rows, got {len(reviewer_a)}")

    final_rows = []
    disagreements: list[str] = []
    for key in sorted(initial_a):
        row = _adjudicate(initial_a[key], initial_b[key])
        if row["adjudication"]["status"] != "agreed":
            disagreements.append(f"{key[0]}|{key[1]}")
        final_rows.append(row)
    for key in sorted(reviewer_a):
        row = _adjudicate(reviewer_a[key], reviewer_b[key])
        if row["adjudication"]["status"] != "agreed":
            disagreements.append(f"{key[0]}|{key[1]}")
        final_rows.append(row)

    final_rows.sort(key=lambda row: (row["language"], row["split"], row["requirement_instance_id"], str(row.get("evidence_id") or "")))
    text, manifest = _payload(
        final_rows,
        disagreements,
        {
            "initial": args.initial.as_posix(),
            "initial_reviewer_b": args.initial_reviewer_b.as_posix(),
            "reviewer_a": args.reviewer_a.as_posix(),
            "reviewer_b": args.reviewer_b.as_posix(),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert len(final_rows) == 60
    assert manifest["reviewer_agreement"]["disagreements"] == len(disagreements)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
