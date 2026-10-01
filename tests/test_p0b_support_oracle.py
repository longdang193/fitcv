from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
P0B = ROOT / "data/fitcv-p0-corpus/p0b"
LABELS = ROOT / "tests/fixtures/p0b/support_oracle_labels.jsonl"


def test_task4_oracle_is_complete_and_structurally_valid() -> None:
    manifest = json.loads(
        (P0B / "p0b_source_job_support_oracle_v1_manifest.json").read_text(encoding="utf-8")
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_p0b_support_oracle.py"),
            "--oracle",
            str(P0B / "p0b_source_job_support_oracle_v1.jsonl"),
            "--manifest",
            str(P0B / "p0b_source_job_support_oracle_v1_manifest.json"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert manifest["oracle"]["coverage"] == 1.0
    assert manifest["oracle"]["rows"] == 549
    assert manifest["labels"]["human_review_complete"] is True
    assert manifest["promotion_eligible"] is True
    assert manifest["oracle"]["label_counts"].get("unjudged", 0) == 0


def test_task4_labels_cover_requirement_by_projection_product() -> None:
    labels = [
        json.loads(line)
        for line in LABELS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evidence_ids = {
        json.loads(line)["evidence_id"]
        for line in (P0B / "candidate_evidence_projection_source_backed_v1.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    requirement_ids = {row["requirement_instance_id"] for row in labels}

    assert len(labels) == len(requirement_ids) * len(evidence_ids)
    assert {row["support_label"] for row in labels} == {"supported", "unsupported"}
    assert all(row["evidence_id"] in evidence_ids for row in labels)
    assert all(row["human_acceptance"]["accepted_by"].startswith("human:") for row in labels)
