from __future__ import annotations

from scripts.calibrate_p0b_recovery import classify_pairs, evaluate_protected_selection


def test_classification_is_disjoint_and_exhaustive() -> None:
    oracle = [
        {"requirement_instance_id": "req", "evidence_id": "canonical", "support_label": "supported"},
        {"requirement_instance_id": "req", "evidence_id": "retrieval", "support_label": "supported"},
        {"requirement_instance_id": "req", "evidence_id": "fp", "support_label": "unsupported"},
        {"requirement_instance_id": "req", "evidence_id": "miss", "support_label": "supported"},
    ]
    stage_pairs = {
        "canonical_pool": {"req::canonical", "req::retrieval"},
        "candidate_retrieval": {"req::canonical"},
        "verification": {"req::canonical"},
        "qualification": {"req::canonical"},
        "selection": {"req::canonical", "req::fp"},
        "assignment": {"req::canonical", "req::fp"},
    }

    result = classify_pairs(oracle, stage_pairs)

    assert result["errors"] == []
    assert result["counts"] == {
        "not_in_canonical_pool": 1,
        "retrieval_loss": 1,
        "verification_failure": 0,
        "qualification_failure": 0,
        "selection_loss": 0,
        "assignment_loss": 0,
        "supported_through_pipeline": 1,
        "unsupported_selected": 1,
        "unsupported_not_selected": 0,
        "unjudged": 0,
    }
    assert result["support_false_negatives"] == 2
    assert result["pair_false_positives"] == 1


def test_protected_selection_uses_review_surface_metrics() -> None:
    oracle = [
        {"requirement_instance_id": "req", "evidence_id": "good", "support_label": "supported"},
        {"requirement_instance_id": "req", "evidence_id": "bad", "support_label": "unsupported"},
        {"requirement_instance_id": "req", "evidence_id": "miss", "support_label": "supported"},
    ]

    result = evaluate_protected_selection(oracle, {"req::good", "req::bad"})

    assert result == {
        "true_positive": 1,
        "false_negative": 1,
        "pair_false_positive": 1,
        "unjudged_selected": 0,
        "support_recall": 0.5,
        "errors": [],
    }
