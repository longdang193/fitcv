from __future__ import annotations

import copy
import json
from pathlib import Path

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
    assert report["predicted_selected"] == 212
    assert report["selected_requirement_recall"] == 1.0
    assert len(report["incorrect_pairs"]) == 2
    assert len(report["hard_negative_false_positives"]) == 67
    assert report["eligible"] is False
