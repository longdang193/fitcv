from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ROOT / "tests" / "fixtures" / "rag_impact_review_annotations.example.json"
PROTOCOL = ROOT / "docs" / "rag-impact-review-protocol.md"


def _load() -> dict[str, Any]:
    return json.loads(ANNOTATIONS.read_text(encoding="utf-8"))


def _validate(record: dict[str, Any]) -> None:
    required = {
        "annotation_schema_version",
        "pair_id",
        "blinded_arm_labels",
        "fixture_sha256",
        "evaluator_version",
        "rubric_version",
        "reviewer_id",
        "reviewer_role",
        "scores",
        "pairwise_preference",
        "confidence",
        "issue_tags",
        "reviewer_notes",
        "adjudication_status",
    }
    assert required <= record.keys()
    assert record["annotation_schema_version"] == "rag-human-review-annotation-v1"
    assert record["pair_id"]
    assert set(record["blinded_arm_labels"]) == {"arm_a", "arm_b"}
    assert all(record["blinded_arm_labels"].values())
    assert record["fixture_sha256"] and len(record["fixture_sha256"]) == 64
    assert record["evaluator_version"]
    assert record["rubric_version"] == "rag-human-review-v1"
    assert record["reviewer_id"]
    assert record["reviewer_role"] == "human-reviewer"
    assert set(record["scores"]) == {
        "requirement_relevance",
        "factual_accuracy",
        "completeness",
        "readability",
        "recruiter_usefulness",
    }
    assert all(isinstance(value, int) and 1 <= value <= 5 for value in record["scores"].values())
    assert record["pairwise_preference"] in {"arm_a", "arm_b", "tie", "no_preference"}
    assert record["confidence"] in {"low", "medium", "high"}
    assert isinstance(record["issue_tags"], list)
    assert isinstance(record["reviewer_notes"], str)
    assert record["adjudication_status"] in {"single_review", "adjudicated", "unresolved"}
    if record["adjudication_status"] == "unresolved":
        assert record.get("adjudication") is None or record["adjudication"].get("decision") == "unresolved"
    assert not any(key in record for key in {"arm_identity", "baseline_output", "fitcv_output", "raw_cv_text"})


def test_annotation_fixture_is_valid_and_protocol_documents_contract() -> None:
    payload = _load()
    assert payload["schema_version"] == "rag-human-review-annotation-v1"
    assert payload["records"]
    for record in payload["records"]:
        _validate(record)
    text = PROTOCOL.read_text(encoding="utf-8")
    for marker in (
        "rag-human-review-v1",
        "single_review",
        "adjudicated",
        "unresolved",
        "raw CV text",
        "fixture_sha256",
        "Herdr",
    ):
        assert marker in text


def test_annotation_rejects_unblinded_record() -> None:
    record = copy.deepcopy(_load()["records"][0])
    record["arm_identity"] = "baseline"
    with pytest.raises(AssertionError):
        _validate(record)


def test_annotation_rejects_incomplete_record() -> None:
    record = copy.deepcopy(_load()["records"][0])
    del record["scores"]
    with pytest.raises(AssertionError):
        _validate(record)


def test_annotation_rejects_unresolved_as_accepted() -> None:
    record = copy.deepcopy(_load()["records"][0])
    record["adjudication_status"] = "unresolved"
    record["adjudication"] = {"decision": "arm_a", "accepted": True}
    with pytest.raises(AssertionError):
        _validate(record)
