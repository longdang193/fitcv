from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import scripts.evaluate_p0b_source_job_relevance as evaluator
from scripts.evaluate_p0b_source_job_relevance import evaluate_documents, evaluate_actual_fitcv


ROOT = Path(__file__).resolve().parents[1]
P0B = ROOT / "data/fitcv-p0-corpus/p0b"


def _documents() -> tuple[dict, dict, dict]:
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
    assert actual["selected_requirement_recall"] == 52 / 143
    assert actual["minimum_source_group_recall"] == 0.0
    assert actual["gates"]["incorrect_pairs"] is True
    assert actual["gates"]["hard_negative_false_positives"] is False
    links = report["evidence_link_review"]
    assert links["status"] == "clean"
    assert links["rows"] == 212
    assert links["accepted_pairs"] == 12
    assert links["supported_requirement_recall"] == 2 / 3
    assert links["unsupported_selected_rows"] == 35
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
