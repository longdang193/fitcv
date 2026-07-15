"""
@meta
type: test
scope: unit
domain: ranking
covers:
  - ranking behavior
excludes:
  - live reranker APIs
tags:
  - fast
  - ci-safe
"""

import pytest
import fitcv.ranking as ranking_module
import fitcv.ranking_contract as ranking_contract

from fitcv.ranking import (
    compute_declared_preference_fit_details,
    compute_must_have_match,
    compute_ranking_runtime_diagnostics,
    compute_seniority_fit,
    compute_title_relevance,
    rank_jobs,
    store_final_ranking,
)



def test_canonicalization_helpers_resolve_domain_and_role_family_aliases() -> None:
    config = {
        "domain_alias_map": {"fintech": "financial services"},
        "role_family_alias_map": {"bi analyst": "analytics"},
    }
    assert ranking_module._canonical_domain("FinTech", config) == "financial services"
    assert ranking_module._canonical_role_family("BI Analyst", config) == "analytics"

def test_domain_neighbors_helper_normalizes_values() -> None:
    config = {
        "domain_neighbors": {
            "Financial Services": ["FinTech", "Banking"],
        }
    }
    neighbors = ranking_module._domain_neighbors(config)
    assert neighbors["financial services"] == frozenset({"fintech", "banking"})


# ── compute_must_have_match ───────────────────────────────────────────────────

def test_compute_must_have_match_ratio():
    score = compute_must_have_match(
        job_skills=["SQL", "Python", "BigQuery"],
        candidate_skills=["SQL", "BigQuery"],
    )
    assert abs(score - (2 / 3)) < 0.001


def test_compute_must_have_match_synonym_canonicalization():
    """GCP == Google Cloud via synonym map."""
    config = {"skill_synonyms": {"gcp": "google cloud"}}
    score = compute_must_have_match(
        job_skills=["Google Cloud"],
        candidate_skills=["GCP"],
        config=config,
    )
    assert score == 1.0


def test_compute_must_have_match_empty_job_skills():
    """No required skills → neutral 0.5 (not a penalty)."""
    assert compute_must_have_match(job_skills=[], candidate_skills=["SQL"]) == 0.5


def test_compute_must_have_match_empty_candidate_skills():
    """Candidate has no skills → 0.0 (cannot satisfy any requirement)."""
    assert compute_must_have_match(job_skills=["SQL"], candidate_skills=[]) == 0.0


def test_compute_must_have_match_case_insensitive():
    score = compute_must_have_match(job_skills=["bigquery"], candidate_skills=["BigQuery"])
    assert score == 1.0


# ── compute_seniority_fit ─────────────────────────────────────────────────────

def test_compute_seniority_fit():
    cfg = {"seniority": {"ladder": ["entry", "mid", "senior"]}}
    assert compute_seniority_fit("mid", "mid", cfg) == 1.0
    assert compute_seniority_fit("entry", "mid", cfg) == 0.5  # target=mid, job=entry (distance 1)
    assert compute_seniority_fit("entry", "senior", cfg) == 0.0  # target=senior, job=entry (distance 2)
    assert compute_seniority_fit(None, "mid", cfg) == 0.5  # unknown target
    assert compute_seniority_fit("mid", None, cfg) == 0.5  # unknown job


# ── compute_title_relevance ───────────────────────────────────────────────────

def test_compute_title_relevance():
    # overlap = 2 (data, engineer) / len(target)=2 → 1.0
    assert compute_title_relevance("Data Engineer", "Data Engineer") == 1.0
    assert compute_title_relevance("Senior Data Engineer", "Data Engineer") == 1.0
    # overlap = 1 (engineer) / len(target)=2 → 0.5
    assert compute_title_relevance("Software Engineer", "Data Engineer") == 0.5
    # overlap = 0 → 0.0
    assert compute_title_relevance("Product Manager", "Data Engineer") == 0.0
    # missing → 0.5 neutral
    assert compute_title_relevance(None, "Data") == 0.5
    assert compute_title_relevance("Data", None) == 0.5


def test_compute_title_relevance_uses_semantic_role_alignment() -> None:
    config = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "business intelligence analyst": "data analyst",
                "data analyst": "data analyst",
                "analytics engineer": "analytics engineer",
                "data engineer": "data engineer",
                "machine learning engineer": "machine learning engineer",
            },
            "role_family_by_role": {
                "data analyst": "analytics",
                "analytics engineer": "data_engineering",
                "data engineer": "data_engineering",
                "machine learning engineer": "ml_engineering",
            },
            "role_family_neighbors": {
                "analytics": ("data_science",),
                "data_engineering": ("ml_engineering",),
                "ml_engineering": ("data_engineering",),
            },
        }
    }
    assert compute_title_relevance("Business Intelligence Analyst", "Data Analyst", config=config) == 1.0
    assert compute_title_relevance("Analytics Engineer", "Data Engineer", config=config) == 1.0
    assert compute_title_relevance("Machine Learning Engineer", "Data Analyst", config=config) == 0.0


def _declared_preference_config(**extra: object) -> dict[str, object]:
    return {
        "ranking_policy": {
            "declared_preference_component_weights": {
                "domain": 0.5,
                "role_family": 0.3,
                "work_mode": 0.2,
            }
        },
        **extra,
    }


def test_compute_declared_preference_fit_uses_canonical_components() -> None:
    details = compute_declared_preference_fit_details(
        {"domain": "fintech", "location_type": "remote"},
        {"domains": ["fintech"], "location_types": ["remote"]},
        _declared_preference_config(),
    )

    assert details["score"] == pytest.approx(0.85)
    assert details["components"] == {
        "domain": 1.0,
        "role_family": 0.5,
        "work_mode": 1.0,
    }
    assert details["match_details"]["work_mode"] == "exact"


def test_compute_declared_preference_fit_uses_aliases_and_neighbors() -> None:
    details = compute_declared_preference_fit_details(
        {"domain": "banking", "job_family": "BI Analyst", "location_type": "onsite"},
        {"domains": ["financial services"], "role_families": ["analytics"]},
        _declared_preference_config(
            domain_alias_map={"banking": "banking"},
            domain_neighbors={"financial services": ["banking"]},
            role_family_alias_map={"bi analyst": "analytics"},
        ),
    )

    assert details["components"]["domain"] == pytest.approx(0.7)
    assert details["components"]["role_family"] == pytest.approx(1.0)
    assert details["match_details"]["domain"] == "neighbor"
    assert details["canonical_values"]["job"]["work_mode"] == "onsite"


def test_compute_declared_preference_fit_requires_policy_weights() -> None:
    with pytest.raises(ValueError, match="declared_preference_component_weights"):
        compute_declared_preference_fit_details({}, {}, {})


def test_rank_jobs_sorts_descending():
    jobs = [
        {"job_url": "u1", "raw_job_fingerprint": "f1", "baseline_fit": 0.5},
        {"job_url": "u2", "raw_job_fingerprint": "f2", "baseline_fit": 0.9},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert ranked[0]["job_url"] == "u2"


def test_rank_jobs_respects_top_n():
    jobs = [
        {"job_url": "u1", "raw_job_fingerprint": "f1", "baseline_fit": 0.9},
        {"job_url": "u2", "raw_job_fingerprint": "f2", "baseline_fit": 0.8},
        {"job_url": "u3", "raw_job_fingerprint": "f3", "baseline_fit": 0.7},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert len(ranked) == 2


def test_rank_jobs_breaks_ties_by_fingerprint_then_url():
    jobs = [
        {"job_url": "u2", "raw_job_fingerprint": "f2", "baseline_fit": 0.8},
        {"job_url": "u3", "raw_job_fingerprint": "f1", "baseline_fit": 0.8},
        {"job_url": "u1", "raw_job_fingerprint": "f1", "baseline_fit": 0.8},
    ]
    ranked = rank_jobs(jobs, top_n=3)
    assert [row["job_url"] for row in ranked] == ["u1", "u3", "u2"]


def test_rank_jobs_assigns_baseline_rank():
    jobs = [
        {"job_url": "u1", "raw_job_fingerprint": "f1", "baseline_fit": 0.5},
        {"job_url": "u2", "raw_job_fingerprint": "f2", "baseline_fit": 0.9},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert ranked[0]["baseline_rank"] == 1
    assert ranked[1]["baseline_rank"] == 2
def test_compute_ranking_runtime_diagnostics_counts_fallback_and_taxonomy_drift() -> None:
    diagnostics = compute_ranking_runtime_diagnostics(
        [
            {
                "normalized_factors": {
                    "must_have_match": {"missing_default_applied": True},
                    "title_relevance": {"missing_default_applied": False},
                    "seniority_fit": {"missing_default_applied": False},
                    "declared_preference_fit": {"missing_default_applied": True},
                    "location_fit": {"missing_default_applied": False},
                    "language_fit": {"missing_default_applied": False},
                },
                "declared_preference_fit_match_details": {
                    "domain": "none",
                    "role_family": "neighbor",
                    "work_mode": "exact",
                },
            },
            {
                "normalized_factors": {
                    factor_id: {"missing_default_applied": False}
                    for factor_id in ranking_contract.STRUCTURED_FACTOR_IDS
                },
                "declared_preference_fit_match_details": {
                    "domain": "exact",
                    "role_family": "neutral",
                    "work_mode": "neutral",
                },
            },
        ]
    )
    assert diagnostics["missing_feature_fallbacks"]["total_applied"] == 2
    assert diagnostics["missing_feature_fallbacks"]["by_feature"]["must_have_match"]["count"] == 1
    assert diagnostics["missing_feature_fallbacks"]["by_feature"]["declared_preference_fit"]["count"] == 1
    assert diagnostics["taxonomy_drift"]["domain_unmatched_count"] == 1
    assert diagnostics["taxonomy_drift"]["role_family_unmatched_count"] == 0
    assert diagnostics["taxonomy_drift"]["neighbor_match_count"] == 1
    assert diagnostics["taxonomy_drift"]["active_comparisons"] == 3
    assert diagnostics["taxonomy_drift"]["unmatched_total"] == 1
    assert diagnostics["taxonomy_drift"]["unmatched_rate"] == pytest.approx(1 / 3)
    # alert threshold is added at pipeline aggregation level, not ranking helper level




def test_eligibility_artifacts_do_not_change_ranking_order_or_fit_labels() -> None:
    baseline_jobs = [
        {
            "job_url": "u1",
            "raw_job_fingerprint": "f1",
            "baseline_fit": 0.8,
            "baseline_fit_label": "strong",
        },
        {
            "job_url": "u2",
            "raw_job_fingerprint": "f2",
            "baseline_fit": 0.6,
            "baseline_fit_label": "stretch",
        },
    ]
    artifact = {
        "fit_factor_results": {
            "location_fit": {"ranking_enabled": True, "ranking_value": 0.0},
            "language_fit": {"ranking_enabled": True, "ranking_value": 1.0},
        },
        "eligibility_policy_fingerprint": "policy-fingerprint",
        "eligibility_decision": "retain",
        "eligibility_reason_codes": ["location_no_match"],
    }

    baseline = rank_jobs(baseline_jobs, top_n=2)
    with_artifacts = rank_jobs(
        [{**job, **artifact} for job in baseline_jobs],
        top_n=2,
    )

    assert [job["job_url"] for job in with_artifacts] == [
        job["job_url"] for job in baseline
    ]
    assert [job["baseline_fit"] for job in with_artifacts] == [
        job["baseline_fit"] for job in baseline
    ]
    assert [job["baseline_fit_label"] for job in with_artifacts] == [
        job["baseline_fit_label"] for job in baseline
    ]


def _ranking_v2_policy() -> dict[str, object]:
    return {
        "policy_version": "ranking-v2",
        "normalizer_version": "absolute-fit-v1",
        "active_baseline_mode": "holistic_ai_only",
        "baseline_weights": {"holistic_ai_fit": 1.0, "structured_fit": 0.0},
        "structured_factor_weights": {
            "must_have_match": 0.30,
            "title_relevance": 0.20,
            "seniority_fit": 0.15,
            "declared_preference_fit": 0.15,
            "location_fit": 0.10,
            "language_fit": 0.10,
        },
        "declared_preference_component_weights": {
            "domain": 0.50,
            "role_family": 0.30,
            "work_mode": 0.20,
        },
        "missing_value_defaults": {
            "holistic_ai_fit": 0.0,
            "must_have_match": 0.5,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "declared_preference_fit": 0.5,
            "location_fit": 0.5,
            "language_fit": 0.5,
        },
        "fit_label_thresholds": {"strong": 0.70, "stretch": 0.40},
        "label_migration_gate": {
            "maximum_total_label_migration_rate": 0.10,
            "maximum_strong_skip_crossings": 0,
        },
    }


def test_ranking_v2_contract_builds_one_effective_policy_fingerprint() -> None:
    context = ranking_contract.build_ranking_contract_context(
        _ranking_v2_policy(),
        eligibility_policy={
            "policy_version": "eligibility-v1",
            "factors": {
                "location_fit": {"mode": "ranking_only"},
                "language_fit": {"mode": "hard_gate"},
            },
        },
        eligibility_policy_fingerprint="eligibility-fingerprint",
    )

    assert set(context["effective_structured_factor_weights"]) == {
        "must_have_match",
        "title_relevance",
        "seniority_fit",
        "declared_preference_fit",
        "location_fit",
    }
    assert sum(context["effective_structured_factor_weights"].values()) == pytest.approx(1.0)
    assert len(context["ranking_contract_fingerprint"]) == 64
    assert "baseline_policy_fingerprint" not in context


def test_ranking_v2_rejects_non_holistic_baseline_weights() -> None:
    policy = _ranking_v2_policy()
    policy["baseline_weights"] = {"holistic_ai_fit": 0.8, "structured_fit": 0.2}

    with pytest.raises(ValueError, match="active_baseline_mode is holistic_ai_only"):
        ranking_contract.validate_ranking_policy(policy)


def test_build_baseline_result_is_absolute_and_vector_independent() -> None:
    context = ranking_contract.build_ranking_contract_context(
        _ranking_v2_policy(),
        eligibility_policy={
            "policy_version": "eligibility-v1",
            "factors": {
                "location_fit": {"mode": "ranking_only"},
                "language_fit": {"mode": "ranking_only"},
            },
        },
        eligibility_policy_fingerprint="eligibility-fingerprint",
    )
    result = ranking_contract.build_baseline_result(
        holistic_ai_fit=0.72,
        structured_factors={
            "must_have_match": 1.0,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "declared_preference_fit": 0.5,
            "location_fit": 0.0,
            "language_fit": 1.0,
        },
        context=context,
    )

    assert result["baseline_fit"] == pytest.approx(0.72)
    assert result["baseline_fit_label"] == "strong"
    assert result["normalized_factors"]["location_fit"]["effective_weight"] == 0.10
    assert "vector_similarity" not in result["normalized_factors"]


def test_build_baseline_result_uses_policy_default_for_missing_holistic_ai_fit() -> None:
    context = ranking_contract.build_ranking_contract_context(
        _ranking_v2_policy(),
        eligibility_policy={
            "policy_version": "eligibility-v1",
            "factors": {
                "location_fit": {"mode": "ranking_only"},
                "language_fit": {"mode": "ranking_only"},
            },
        },
        eligibility_policy_fingerprint="eligibility-fingerprint",
    )

    result = ranking_contract.build_baseline_result(
        holistic_ai_fit=None,
        structured_factors={},
        context=context,
    )

    assert result["holistic_ai_fit"] == 0.0
    assert result["holistic_ai_fit_missing_default_applied"] is True
    assert result["baseline_fit"] == 0.0
    assert result["baseline_fit_label"] == "skip"


def test_rank_jobs_uses_stable_fingerprint_before_url() -> None:
    jobs = [
        {"job_url": "same", "raw_job_fingerprint": "b", "baseline_fit": 0.8},
        {"job_url": "same", "raw_job_fingerprint": "a", "baseline_fit": 0.8},
    ]

    ranked = rank_jobs(jobs, top_n=2)

    assert [row["raw_job_fingerprint"] for row in ranked] == ["a", "b"]
    assert [row["baseline_rank"] for row in ranked] == [1, 2]


def test_rank_jobs_rejects_missing_stable_fingerprint() -> None:
    with pytest.raises(ValueError, match="raw_job_fingerprint"):
        rank_jobs([{"job_url": "u1", "baseline_fit": 0.8}], top_n=1)


def test_legacy_adapter_normalizes_equivalent_values_and_rejects_conflicts() -> None:
    adapted = ranking_contract.adapt_legacy_ranking_row(
        {
            "job_url": "u1",
            "raw_job_fingerprint": "fp1",
            "baseline_fit": 0.7,
            "final_score": "0.70",
            "baseline_fit_label": "strong",
            "fit_label": " Strong ",
            "baseline_rank": 1,
            "final_rank": "1",
        }
    )
    assert adapted["baseline_fit"] == 0.7
    assert adapted["baseline_fit_label"] == "strong"
    assert "final_score" not in adapted

    with pytest.raises(ValueError, match="conflicting"):
        ranking_contract.adapt_legacy_ranking_row(
            {"baseline_fit": 0.7, "final_score": 0.6}
        )


def test_label_migration_summary_reports_crossings_and_insufficient_evidence() -> None:
    failed = ranking_contract.build_label_migration_summary(
        [
            {"legacy_model_fit_label": "strong", "baseline_fit_label": "skip"},
            {"legacy_model_fit_label": "stretch", "baseline_fit_label": "stretch"},
        ],
        _ranking_v2_policy()["label_migration_gate"],
    )
    assert failed["status"] == "failed"
    assert failed["strong_skip_crossings"] == 1

    insufficient = ranking_contract.build_label_migration_summary(
        [{"baseline_fit_label": "strong"}],
        _ranking_v2_policy()["label_migration_gate"],
    )
    assert insufficient["status"] == "insufficient_evidence"
