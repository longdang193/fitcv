from __future__ import annotations

import json
from pathlib import Path

from fitcv.shortlist_evaluation import evaluate_shortlist_pool


def _frozen_kwargs() -> dict[str, str]:
    return {
        "profile_revision": "profile-r7",
        "as_of": "2026-11-21T00:00:00+00:00",
        "split_id": "heldout-2026-11-21",
        "requirement_contract_fingerprint": "requirements-v1",
        "eligibility_policy_fingerprint": "shortlist-eligibility-v1",
        "cache_condition": "warm",
    }


def _labeled_fixture() -> dict:
    return {
        "schema_version": "requirement_aware_admission_pool_v1",
        "fixture_role": "promotion_evaluation",
        "admission_capacity": 2,
        "relevance_grade_threshold": 2,
        "jobs": [
            {
                "canonical_job_identity": "job-a",
                "relevance_grade": 3,
                "legacy_excluded": False,
                "coverage": {
                    "states": [
                        {"occurrence_id": "a-s", "state": "S", "oracle_state": "supported"},
                        {"occurrence_id": "a-p", "state": "P", "oracle_state": "partial"},
                    ],
                    "required": {"ratio": 1.0},
                    "duties": {"ratio": 1.0},
                    "preferred": {"ratio": 0.0},
                },
            },
            {
                "canonical_job_identity": "job-b",
                "relevance_grade": 3,
                "legacy_excluded": True,
                "coverage": {
                    "states": [{"occurrence_id": "b-e", "state": "E", "oracle_state": "no_support"}],
                    "required": {"ratio": 0.5},
                    "duties": {"ratio": 0.5},
                    "preferred": {"ratio": 0.0},
                },
            },
            {
                "canonical_job_identity": "job-c",
                "relevance_grade": 0,
                "legacy_excluded": False,
                "coverage": {
                    "states": [],
                    "required": {"ratio": 0.0},
                    "duties": {"ratio": 0.0},
                    "preferred": {"ratio": 0.0},
                },
            },
        ],
    }


def test_frozen_evaluation_reports_metrics_and_passes_gates() -> None:
    artifact = evaluate_shortlist_pool(
        _labeled_fixture(),
        **_frozen_kwargs(),
        legacy_baseline={"recall_at_50": 0.5, "p95_latency_ms": 5, "retrieval_cost": {"total": 1}},
        latency_samples_ms=[3, 4, 5],
        retrieval_cost={"total": 1.5},
    )

    assert artifact["promotion_eligible"] is True
    assert artifact["metrics"]["evidence_correctness"] == 1.0
    assert artifact["metrics"]["unknown_rate"] == 0.0
    assert artifact["metrics"]["contradiction_accuracy"] is None
    assert artifact["metrics"]["determinism"] == 1
    assert artifact["metadata"]["split_id"] == "heldout-2026-11-21"
    assert len(artifact["artifact_fingerprint"]) == 64


def test_evaluation_blocks_without_reviewed_labels_or_baseline() -> None:
    fixture = json.loads(Path("tests/fixtures/requirement_aware_admission_pool.json").read_text())
    artifact = evaluate_shortlist_pool(fixture, **_frozen_kwargs())

    assert artifact["promotion_eligible"] is False
    assert "evidence_correctness" in artifact["blocked_reasons"]
    assert "unknown_rate" in artifact["blocked_reasons"]
    assert "recall_at_50" in artifact["blocked_reasons"]
    assert artifact["metrics"]["legacy_recall_at_50"] < artifact["metrics"]["recall_at_50"]


def test_evaluation_input_is_order_independent() -> None:
    fixture = _labeled_fixture()
    first = evaluate_shortlist_pool(fixture, **_frozen_kwargs())
    reversed_fixture = {**fixture, "jobs": list(reversed(fixture["jobs"]))}
    second = evaluate_shortlist_pool(reversed_fixture, **_frozen_kwargs())

    assert first["selection"]["decision_fingerprint"] == second["selection"]["decision_fingerprint"]
    assert first["metrics"]["recall_at_50"] == second["metrics"]["recall_at_50"]
