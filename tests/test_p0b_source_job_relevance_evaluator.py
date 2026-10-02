from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.evaluate_p0b_source_job_relevance as evaluator
from scripts.evaluate_p0b_source_job_relevance import (
    evaluate_documents,
    evaluate_actual_fitcv,
    evaluate_evidence_link_review,
)


ROOT = Path(__file__).resolve().parents[1]
P0B = ROOT / "data/fitcv-p0-corpus/p0b"


def _documents() -> tuple[dict, dict, dict]:
    required = [
        P0B / "p0b_source_job_relevance_fixture_v2_human_frozen.json",
        P0B / "p0b_source_job_review_packet_v2_human_adjudicated.json",
        P0B / "p0b_source_job_source_group_map_v2.json",
    ]
    if not all(path.is_file() for path in required):
        pytest.skip("private relevance fixtures unavailable; public evaluator tests are authoritative")

    def load(name: str) -> dict:
        return json.loads((P0B / name).read_text(encoding="utf-8"))

    return (
        load("p0b_source_job_relevance_fixture_v2_human_frozen.json"),
        load("p0b_source_job_review_packet_v2_human_adjudicated.json"),
        load("p0b_source_job_source_group_map_v2.json"),
    )


def test_current_fixture_evaluates_both_reviewer_arms() -> None:
    report = evaluate_documents(*_documents())

    assert report["validation"]["passed"] is True
    assert report["validation"]["validation_cases"] == {"passed": 25, "total": 25}
    reviewer_a = report["arms"]["reviewer_a"]
    assert reviewer_a["true_positive"] == 131
    assert reviewer_a["false_negative"] == 12
    assert reviewer_a["selected_requirement_recall"] == 131 / 143
    assert reviewer_a["minimum_source_group_recall"] == 2 / 3
    assert reviewer_a["incorrect_pairs"] == []
    assert reviewer_a["hard_negative_false_positives"] == []
    assert reviewer_a["eligible"] is True

    reviewer_b = report["arms"]["reviewer_b"]
    assert reviewer_b["selected_requirement_recall"] == 1.0
    assert len(reviewer_b["incorrect_pairs"]) == 2
    assert len(reviewer_b["hard_negative_false_positives"]) == 57
    assert reviewer_b["eligible"] is False


def test_id_drift_fails_closed() -> None:
    fixture, packet, group_map = _documents()
    drifted = copy.deepcopy(packet)
    drifted["unanimous_rows"][0]["requirement_instance_id"] = "req-drift"

    report = evaluate_documents(fixture, drifted, group_map)

    assert report["validation"]["passed"] is False
    assert "packet_requirement_not_in_fixture:req-drift" in report["validation"]["errors"]
    assert report["arms"] == {}


def test_actual_fitcv_output_is_evaluated_separately_from_reviewer_arms() -> None:
    fixture, packet, group_map = _documents()

    report = evaluate_actual_fitcv(fixture, packet, group_map)

    assert report["validation"]["passed"] is True
    assert report["status"] == "comparable"
    assert len(report["job_outputs"]) == 25
    assert all("selected_evidence_ids" in output for output in report["job_outputs"])
    actual = report["actual_metrics"]
    assert actual["selected_requirement_recall"] == 6 / 143
    assert actual["true_positive"] == 6
    assert actual["minimum_source_group_recall"] == 0.0
    assert actual["gates"]["incorrect_pairs"] is True
    assert actual["hard_negative_false_positive_count"] == 6
    assert actual["gates"]["hard_negative_false_positives"] is False
    links = report["evidence_link_review"]
    assert links["status"] == "clean"
    assert links["rows"] == 212
    assert links["accepted_pairs"] == 12
    assert links["supported_requirement_recall"] == 1.0
    assert links["unsupported_selected_rows"] == 0
    assert report["eligible"] is False


def test_actual_fitcv_evaluation_uses_job_level_output(monkeypatch) -> None:
    fixture, packet, group_map = _documents()
    calls = []

    def fake_retrieve(profile, job_context, top_k, config):
        calls.append(job_context)
        first_requirement_id = job_context["responsibility_entities"][0]["source_requirement_id"]
        return {
            "selected_evidence_ids": ["ev-job-output"],
            "retrieved_evidence_ids": ["ev-job-output", "ev-other"],
            "selected_evidence_count": 1,
            "requirement_support": {
                "responsibility": {
                    "selected": {first_requirement_id: ["ev-job-output"]},
                }
            },
        }

    monkeypatch.setattr(evaluator, "retrieve_evidence_bundle", fake_retrieve)
    monkeypatch.setattr(evaluator, "_load_evidence_link_review", lambda path: [])
    report = evaluator.evaluate_actual_fitcv(fixture, packet, group_map)

    assert report["validation"]["passed"] is True
    assert len(calls) == len(group_map["source_groups"])
    assert all(len(call["responsibilities"]) > 1 for call in calls)
    assert all(
        len(call["responsibility_entities"]) == len(call["responsibilities"])
        for call in calls
    )
    assert len(report["job_outputs"]) == len(calls)
    assert report["job_outputs"][0]["selected_evidence_ids"] == ["ev-job-output"]
    assert len(report["job_outputs"][0]["selected_evidence_by_requirement"]) == 1
    assert report["status"] == "comparable"
    assert "selected_requirement_recall" in report["actual_metrics"]


def test_actual_fitcv_cli_fails_when_actual_gates_fail(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_p0b_source_job_relevance.py"),
            "--output",
            str(tmp_path / "evaluation.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1


def test_evidence_link_review_fails_closed_when_review_is_incomplete() -> None:
    result = evaluate_evidence_link_review(
        review_rows=[],
        fixture_by_id={"req-1": {"source_record_id": "job-1"}},
        selected_by_source={"job-1": set()},
        selected_by_requirement={},
        projection_ids=set(),
        support_recall_threshold=1.0,
    )

    assert result["status"] == "invalid"
    assert "review_coverage_incomplete" in result["validation_errors"]
    assert result["support_gate"]["passed"] is False
    assert result["support_gate"]["complete_review"] is False


def test_evidence_link_review_ignores_current_selection_snapshot_for_gold() -> None:
    result = evaluate_evidence_link_review(
        review_rows=[
            {
                "requirement_instance_id": "req-1",
                "source_record_id": "job-1",
                "selected_evidence_ids": "ev-gold;ev-old",
                "accepted_evidence_ids": "ev-gold",
                "support_verdict": "supported",
                "qualifier_verdict": "supported",
            }
        ],
        fixture_by_id={"req-1": {"source_record_id": "job-1"}},
        selected_by_source={"job-1": {"ev-gold"}},
        selected_by_requirement={"req-1": {"ev-gold"}},
        projection_ids={"ev-gold", "ev-old"},
        support_recall_threshold=1.0,
    )

    assert result["status"] == "clean"
    assert result["validation_errors"] == []
    assert result["support_gate"]["passed"] is True
    assert result["supported_requirement_recall"] == 1.0


def test_evidence_link_review_rejects_invalid_gold_and_zero_support_denominator() -> None:
    result = evaluate_evidence_link_review(
        review_rows=[
            {
                "requirement_instance_id": "req-1",
                "source_record_id": "job-1",
                "selected_evidence_ids": "ev-selected",
                "accepted_evidence_ids": "ev-missing",
                "support_verdict": "unsupported",
                "qualifier_verdict": "unknown",
            }
        ],
        fixture_by_id={"req-1": {"source_record_id": "job-1"}},
        selected_by_source={"job-1": {"ev-current"}},
        selected_by_requirement={"req-1": {"ev-current"}},
        projection_ids={"ev-selected"},
        support_recall_threshold=0.0,
    )

    assert "review_accepted_ids_not_in_projection:req-1" in result["validation_errors"]
    assert result["supported_requirement_recall"] is None
    assert result["support_gate"]["supported_link_recall"] is False
    assert result["support_gate"]["passed"] is False


def _public_inputs() -> tuple[list[dict], list[dict], list[dict], dict]:
    projection = [
        {"evidence_id": "ev-good", "schema_version": "candidate-evidence.v1"},
        {"evidence_id": "ev-bad", "schema_version": "candidate-evidence.v1"},
    ]
    review = [{
        "requirement_instance_id": "req-1",
        "source_record_id": "job-1",
        "requirement_text": "Build reports using Python",
        "selected_evidence_ids": "ev-good;ev-bad",
        "accepted_evidence_ids": "ev-good",
        "support_verdict": "supported",
        "qualifier_verdict": "supported",
    }]
    oracle = [
        {
            "pair_id": "req-1::ev-good",
            "requirement_instance_id": "req-1",
            "evidence_id": "ev-good",
            "support_state": "supported",
            "adjudicator_id": "reviewer-a",
            "reviewed_at": "2026-10-01T00:00:00Z",
            "source_ref": "fixture:req-1::ev-good",
        },
        {
            "pair_id": "req-1::ev-bad",
            "requirement_instance_id": "req-1",
            "evidence_id": "ev-bad",
            "support_state": "unsupported",
            "adjudicator_id": "reviewer-a",
            "reviewed_at": "2026-10-01T00:00:00Z",
            "source_ref": "fixture:req-1::ev-bad",
        },
    ]
    state = {
        "statuses": {"p0_b": "blocked"},
        "support_thresholds": {
            "maximum_pair_false_positives": 0,
            "minimum_review_completeness": 1.0,
            "minimum_oracle_coverage": 1.0,
            "support_recall_threshold": 1.0,
        },
    }
    return projection, review, oracle, state


def test_public_evaluator_counts_unsupported_assigned_pairs() -> None:
    inputs = _public_inputs()
    validation = evaluator.validate_public_inputs(*inputs)

    assert validation["passed"] is True
    selected = validation["selected_pairs"]
    assert "req-1::ev-bad" in selected


def test_public_evaluator_fails_closed_on_missing_threshold() -> None:
    projection, review, oracle, state = _public_inputs()
    state["support_thresholds"]["support_recall_threshold"] = None

    validation = evaluator.validate_public_inputs(projection, review, oracle, state)

    assert validation["passed"] is False
    assert "support_recall_threshold_missing_or_invalid" in validation["errors"]


def test_public_evaluator_rejects_dangling_and_private_inputs() -> None:
    projection, review, oracle, state = _public_inputs()
    review[0]["selected_evidence_ids"] = "ev-missing"

    validation = evaluator.validate_public_inputs(projection, review, oracle, state)

    assert validation["passed"] is False
    assert "selected_not_in_projection:req-1" in validation["errors"]

    with pytest.raises(ValueError, match="private_or_external_input"):
        evaluator._public_path(Path("C:/private/oracle.json"))


def _manifest_for(path: Path, rows: list[dict]) -> dict:
    labels = {}
    for row in rows:
        state = evaluator._oracle_state(row)
        labels[state] = labels.get(state, 0) + 1
    requirements = {str(row["requirement_instance_id"]) for row in rows}
    evidence = {str(row["evidence_id"]) for row in rows}
    return {
        "schema_version": "p0b.source_job_support_oracle_manifest.v1",
        "oracle": {
            "path": path.name,
            "sha256": evaluator._sha256_file(path),
            "rows": len(rows),
            "requirements": len(requirements),
            "evidence_rows": len(evidence),
            "label_counts": dict(sorted(labels.items())),
        },
        "labels": {"rows": len(rows), "human_review_complete": True},
        "promotion_eligible": True,
    }


def test_oracle_manifest_rejects_truncated_oracle_before_metrics(tmp_path: Path) -> None:
    rows = _public_inputs()[2]
    oracle_path = tmp_path / "oracle.jsonl"
    oracle_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest_for(oracle_path, rows)), encoding="utf-8")

    truncated = rows[:-1]
    errors = evaluator._validate_oracle_manifest(oracle_path, manifest_path, truncated)

    assert "oracle_manifest_row_count_mismatch" in errors
    assert "oracle_manifest_hash_mismatch" not in errors


def test_oracle_manifest_rejects_hash_mismatch(tmp_path: Path) -> None:
    rows = _public_inputs()[2]
    oracle_path = tmp_path / "oracle.jsonl"
    oracle_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = _manifest_for(oracle_path, rows)
    oracle_path.write_text(oracle_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = evaluator._validate_oracle_manifest(oracle_path, manifest_path, rows)

    assert "oracle_manifest_hash_mismatch" in errors


def test_runtime_metrics_use_runtime_assignments_not_historical_selection() -> None:
    oracle = {
        "req-1::ev-good": {"requirement_instance_id": "req-1", "evidence_id": "ev-good", "support_state": "supported"},
        "req-1::ev-bad": {"requirement_instance_id": "req-1", "evidence_id": "ev-bad", "support_state": "unsupported"},
    }

    metrics = evaluator._runtime_requirement_metrics(
        oracle,
        {"req-1": {"ev-bad"}},
        {"req-1": {"ev-bad"}},
    )

    assert metrics["selected_pairs"] == 1
    assert metrics["supported_selected_pairs"] == 0
    assert metrics["unsupported_or_unknown_assignments"] == 1
