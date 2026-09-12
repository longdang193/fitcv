"""
@meta
type: test
scope: unit
domain: ranking
covers:
  - ranking contract invariants
  - fit-label symmetry between pipeline and ranking contract
tags:
  - fast
  - ci-safe
"""

import pytest

from fitcv.pipeline import _resolve_layer4_fit
from fitcv.ranking import rank_jobs
from fitcv.ranking_contract import (
    build_baseline_result,
    fit_label_from_score,
    normalize_score_state,
    validate_weight_contract,
)


def test_fit_label_from_score_rejects_inverted_values() -> None:
    with pytest.raises(ValueError, match="ranking_policy.fit_label_thresholds"):
        fit_label_from_score(
            0.5,
            {"ranking_policy": {"fit_label_thresholds": {"strong": 0.3, "stretch": 0.6}}},
        )


def test_validate_weight_contract_rejects_invalid_sum() -> None:
    with pytest.raises(ValueError, match="Invalid ranking weights sum"):
        validate_weight_contract({"ai_score": 0.6, "must_have_match": 0.3}, expected_sum=1.0)


def test_valid_zero_score_remains_rankable_and_failures_do_not() -> None:
    jobs = [
        {"raw_job_fingerprint": "zero", "job_url": "zero", "ai_score": 0.0, "baseline_fit": 0.1},
        {"raw_job_fingerprint": "failed", "job_url": "failed", "ai_score": None, "score_status": "unscored", "baseline_fit": None},
    ]
    ranked = rank_jobs(jobs, top_n=10)
    assert [row["job_url"] for row in ranked] == ["zero"]
    assert jobs[1]["score_status"] == "unscored"


def test_unknown_score_state_never_gets_baseline_fit_label() -> None:
    context = {
        "ranking_policy": {
            "missing_value_defaults": {
                "holistic_ai_fit": 0.0,
                "must_have_match": 0.5,
                "title_relevance": 0.5,
                "seniority_fit": 0.5,
                "declared_preference_fit": 0.5,
                "location_fit": 0.5,
                "language_fit": 0.5,
            },
            "structured_factor_weights": {
                "must_have_match": 0.25,
                "title_relevance": 0.25,
                "seniority_fit": 0.25,
                "declared_preference_fit": 0.25,
                "location_fit": 0.0,
                "language_fit": 0.0,
            },
            "baseline_weights": {"holistic_ai_fit": 1.0, "structured_fit": 0.0},
            "fit_label_thresholds": {"strong": 0.7, "stretch": 0.4},
            "active_baseline_mode": "test",
            "policy_version": "test",
            "normalizer_version": "test",
        },
        "effective_structured_factor_weights": {
            "must_have_match": 0.25,
            "title_relevance": 0.25,
            "seniority_fit": 0.25,
            "declared_preference_fit": 0.25,
        },
        "ranking_contract_fingerprint": "test",
    }
    result = build_baseline_result(
        holistic_ai_fit=None,
        holistic_score_status="unscored",
        holistic_failure_code="timeout",
        structured_factors={},
        context=context,
    )
    assert result["holistic_ai_fit"] is None
    assert result["baseline_fit"] is None
    assert result["baseline_fit_label"] is None
    assert result["score_status"] == "unscored"
    assert normalize_score_state({"ai_score": 0.0})["score_status"] == "valid"



@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (0.9, "strong"),
        (0.5, "stretch"),
        (0.1, "skip"),
    ],
)
def test_pipeline_layer4_fit_matches_contract(score: float, expected_label: str) -> None:
    config = {"ranking_policy": {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}}
    job = {"baseline_fit": score}
    assert _resolve_layer4_fit(job, gap_fit=None, config=config) == expected_label
    assert fit_label_from_score(score, config=config) == expected_label

