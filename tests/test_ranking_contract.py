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
from fitcv.pipeline_stages.common import job_identity_index_keys, job_identity_keys
from fitcv.ranking import rank_jobs
from fitcv.ranking_contract import (
    build_baseline_result,
    fit_label_from_score,
    normalize_score_state,
    normalize_score_state_for_export,
    resolve_fit_label_for_row,
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


def test_export_score_state_keeps_stage_disposition_unscored_without_failure() -> None:
    assert normalize_score_state_for_export(
        {
            "pipeline_status": "not_shortlisted",
            "job_outcome": {"reason_code": "not_selected_by_shortlist"},
        }
    ) == {"ai_score": None, "score_status": "unscored", "failure_code": None}


@pytest.mark.parametrize(
    ("field", "value", "expected_status", "expected_failure"),
    [
        ("parser_status", "missing_ai_score", "invalid", "missing_ai_score"),
        ("reranker_parser_status", "runtime_exception", "unscored", "provider_failure"),
        ("score_reasoning", "parse failure: malformed", "invalid", "parser_failure"),
        ("reranker_score_reasoning", "scoring error: provider", "unscored", "provider_failure"),
    ],
)
def test_export_score_state_preserves_legacy_failure_contract(
    field: str,
    value: str,
    expected_status: str,
    expected_failure: str,
) -> None:
    normalized = normalize_score_state_for_export({field: value})

    assert normalized["score_status"] == expected_status
    assert normalized["failure_code"] == expected_failure


def test_job_identity_keys_prefer_run_then_fingerprint_and_suppress_url_aliases() -> None:
    job = {
        "run_job_id": "run-job-1",
        "raw_job_fingerprint": "raw-1",
        "job_url": "https://example.com/same",
    }

    assert job_identity_keys(job) == [
        "run:run-job-1",
        "fp:raw-1",
        "url:https://example.com/same",
    ]
    assert job_identity_index_keys(job) == ["run:run-job-1", "fp:raw-1"]
    assert job_identity_index_keys({"job_url": job["job_url"]}) == [
        "url:https://example.com/same"
    ]


def test_present_unmatched_stable_identity_does_not_match_url_alias() -> None:
    indexed = {"url:https://example.com/same": {"ai_score": 0.9}}
    candidate = {"run_job_id": "run-job-missing", "job_url": "https://example.com/same"}

    assert not any(key in indexed for key in job_identity_index_keys(candidate))


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


def test_resolve_fit_label_for_row_recomputes_contradictory_persisted_label() -> None:
    config = {"ranking_policy": {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}}
    assert resolve_fit_label_for_row(
        {"baseline_fit": 0.8, "baseline_fit_label": "skip"}, config
    ) == "strong"

