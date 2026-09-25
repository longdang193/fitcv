from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "tests" / "fixtures" / "rag_impact_review_agent_outputs.example.json"
AGENTS = ROOT / "docs" / "rag-impact-review-agents.md"


def _load() -> dict[str, Any]:
    return json.loads(OUTPUTS.read_text(encoding="utf-8"))


def _validate_receipt(receipt: dict[str, Any]) -> None:
    required = {
        "run_id",
        "fixture_sha256",
        "rubric_version",
        "input_artifact_path",
        "output_artifact_path",
        "timeout_seconds",
        "delivery_status",
    }
    assert required <= receipt.keys()
    assert receipt["run_id"]
    assert len(receipt["fixture_sha256"]) == 64
    assert receipt["rubric_version"] == "rag-human-review-v1"
    assert receipt["input_artifact_path"].startswith("artifacts/")
    assert receipt["output_artifact_path"].startswith("artifacts/")
    assert receipt["timeout_seconds"] > 0
    assert receipt["delivery_status"] in {"delivered", "failed", "timed_out"}


def test_agent_examples_have_bounded_contracts_and_receipts() -> None:
    payload = _load()
    assert payload["schema_version"] == "rag-impact-review-agent-output-v1"
    assert set(payload["agents"]) == {
        "grounding-reviewer",
        "recruiter-quality-reviewer",
        "review-adjudicator",
    }
    for name, output in payload["agents"].items():
        assert output["agent_name"] == name
        _validate_receipt(output["herdr_receipt"])
        serialized = json.dumps(output, sort_keys=True).casefold()
        assert "raw cv text" not in serialized
        assert "baseline" not in serialized
        assert "fitcv" not in serialized
        assert "arm_identity" not in serialized
    grounding = payload["agents"]["grounding-reviewer"]["annotation"]
    assert grounding["evidence_references"]
    assert isinstance(grounding["unsupported_claims"], list)
    assert grounding["review_status"] in {"reviewed", "needs_review", "failed"}
    quality = payload["agents"]["recruiter-quality-reviewer"]["annotation"]
    assert set(quality["scores"]) == {
        "requirement_relevance",
        "factual_accuracy",
        "completeness",
        "readability",
        "recruiter_usefulness",
    }
    assert quality["pairwise_preference"] in {"arm_a", "arm_b", "tie", "no_preference"}
    adjudication = payload["agents"]["review-adjudicator"]["annotation"]
    assert adjudication["decision"] in {"arm_a", "arm_b", "tie", "unresolved"}
    assert adjudication["source_output_mutation"] is False
    assert "disagreements" in adjudication


def test_agent_docs_define_dispatch_and_failure_boundaries() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    for marker in (
        "grounding-reviewer",
        "recruiter-quality-reviewer",
        "review-adjudicator",
        "read-only",
        "delivery_status",
        "unresolved",
        "raw CV text",
    ):
        assert marker in text


def test_receipt_rejects_missing_run_identity() -> None:
    receipt = dict(_load()["agents"]["grounding-reviewer"]["herdr_receipt"])
    del receipt["run_id"]
    with pytest.raises(AssertionError):
        _validate_receipt(receipt)
