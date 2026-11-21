from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_cli_loads_frozen_baseline_and_retrieval_cost(tmp_path: Path) -> None:
    output = tmp_path / "evaluation.json"
    baseline = tmp_path / "baseline.json"
    cost = tmp_path / "cost.json"
    baseline.write_text(
        json.dumps({"recall_at_50": 0.4, "p95_latency_ms": 10, "retrieval_cost": {"total": 1}}),
        encoding="utf-8",
    )
    cost.write_text(json.dumps({"total": 1.5}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_requirement_aware_shortlisting.py",
            "--fixture",
            "tests/fixtures/requirement_aware_admission_pool.json",
            "--output",
            str(output),
            "--profile-revision",
            "profile-r7",
            "--as-of",
            "2026-11-21T21:05:46Z",
            "--split-id",
            "heldout-2026-11-21",
            "--requirement-contract-fingerprint",
            "requirements-v1",
            "--eligibility-policy-fingerprint",
            "shortlist-eligibility-v1",
            "--cache-condition",
            "warm",
            "--latency-sample-ms",
            "5",
            "--legacy-baseline",
            str(baseline),
            "--retrieval-cost",
            str(cost),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["baseline"]["recall_at_50"] == 0.4
    assert artifact["metrics"]["retrieval_cost"] == {"total": 1.5}
    assert artifact["gates"]["recall_at_50"] is True
    assert artifact["gates"]["latency"] is True
    assert artifact["gates"]["cost"] is True
    assert artifact["gates"]["evidence_correctness"] is False
