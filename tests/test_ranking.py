import pytest

from fitcv.ranking import (
    compute_final_score,
    compute_must_have_match,
    compute_preference_fit,
    compute_seniority_fit,
    compute_title_relevance,
    rank_jobs,
    store_final_ranking,
)


_DEFAULT_WEIGHTS = {
    "ai_score": 0.40,
    "must_have_match": 0.20,
    "vector_similarity": 0.15,
    "title_relevance": 0.10,
    "seniority_fit": 0.10,
    "preference_fit": 0.05,
}

_NULL_DEFAULTS = {
    "ai_score": 0.0,
    "must_have_match": 0.0,
    "vector_similarity": 0.0,
    "title_relevance": 0.5,
    "seniority_fit": 0.5,
    "preference_fit": 0.5,
}


# ── compute_final_score ───────────────────────────────────────────────────────

def test_compute_final_score_weighted():
    features = {
        "ai_score": 0.8,
        "must_have_match": 0.9,
        "vector_similarity": 0.7,
        "title_relevance": 0.6,
        "seniority_fit": 1.0,
        "preference_fit": 0.5,
    }
    score = compute_final_score(features, _DEFAULT_WEIGHTS, _NULL_DEFAULTS)
    expected = 0.40 * 0.8 + 0.20 * 0.9 + 0.15 * 0.7 + 0.10 * 0.6 + 0.10 * 1.0 + 0.05 * 0.5
    assert abs(score - expected) < 0.001


def test_compute_final_score_handles_missing_ai_score():
    """Missing ai_score → fallback 0.0 (conservative)."""
    features = {
        "must_have_match": 1.0,
        "vector_similarity": 1.0,
        "title_relevance": 1.0,
        "seniority_fit": 1.0,
        "preference_fit": 1.0,
    }
    score = compute_final_score(features, _DEFAULT_WEIGHTS, _NULL_DEFAULTS)
    # Without ai_score (0.0 default), score must be < 1.0
    assert score < 1.0
    # Expected: sum of all other weights = 0.60
    assert abs(score - 0.60) < 0.001


def test_compute_final_score_handles_missing_title_relevance():
    """Missing title_relevance → fallback 0.5 (neutral)."""
    features = {
        "ai_score": 0.8,
        "must_have_match": 0.8,
        "vector_similarity": 0.8,
        "seniority_fit": 0.8,
        "preference_fit": 0.8,
    }
    score = compute_final_score(features, _DEFAULT_WEIGHTS, _NULL_DEFAULTS)
    # title_relevance defaults to 0.5
    expected = (0.4+0.2+0.15+0.1+0.05)*0.8 + 0.1*0.5
    assert abs(score - expected) < 0.001


def test_compute_final_score_accepts_config_weights():
    """Weights must come from the weights dict, not hardcoded."""
    features = {
        "ai_score": 1.0,
        "must_have_match": 0.0,
        "vector_similarity": 0.0,
        "title_relevance": 0.0,
        "seniority_fit": 0.0,
        "preference_fit": 0.0,
    }
    custom_weights = {
        **_DEFAULT_WEIGHTS,
        "ai_score": 1.0,
        "must_have_match": 0.0,
        "vector_similarity": 0.0,
        "title_relevance": 0.0,
        "seniority_fit": 0.0,
        "preference_fit": 0.0,
    }
    # With weight fully on ai_score=1.0, final score should be 1.0
    assert abs(compute_final_score(features, custom_weights, _NULL_DEFAULTS) - 1.0) < 0.001


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


# ── compute_preference_fit ────────────────────────────────────────────────────

def test_compute_preference_fit():
    prefs = {"domains": ["fintech", "health"], "location_types": ["remote"]}
    assert compute_preference_fit({"domain": "fintech", "location_type": "remote"}, prefs) == 1.0
    assert compute_preference_fit({"domain": "fintech", "location_type": "onsite"}, prefs) == 0.5
    assert compute_preference_fit({"domain": "retail", "location_type": "onsite"}, prefs) == 0.0
    # no preferences = 0.5 neutral
    assert compute_preference_fit({"domain": "fintech"}, {}) == 0.5


def test_compute_preference_fit_matches_job_family_when_domains_are_role_categories():
    prefs = {"domains": ["data_science"], "location_types": []}
    assert compute_preference_fit({"domain": "finance", "job_family": "data_science"}, prefs) == 1.0


# ── rank_jobs ─────────────────────────────────────────────────────────────────

def test_rank_jobs_sorts_descending():
    jobs = [
        {"job_url": "u1", "final_score": 0.5, "ai_score": 0.5, "vector_similarity": 0.5},
        {"job_url": "u2", "final_score": 0.9, "ai_score": 0.9, "vector_similarity": 0.9},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert ranked[0]["job_url"] == "u2"


def test_rank_jobs_respects_top_n():
    jobs = [
        {"job_url": "u1", "final_score": 0.9, "ai_score": 0.9, "vector_similarity": 0.9},
        {"job_url": "u2", "final_score": 0.8, "ai_score": 0.8, "vector_similarity": 0.8},
        {"job_url": "u3", "final_score": 0.7, "ai_score": 0.7, "vector_similarity": 0.7},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert len(ranked) == 2


def test_rank_jobs_breaks_ties_by_ai_score_then_vector():
    """Tie in final_score → higher ai_score wins; tie in ai_score → higher vector_similarity wins."""
    jobs = [
        {"job_url": "u1", "final_score": 0.8, "ai_score": 0.7, "vector_similarity": 0.8},
        {"job_url": "u2", "final_score": 0.8, "ai_score": 0.9, "vector_similarity": 0.6},
        {"job_url": "u3", "final_score": 0.8, "ai_score": 0.9, "vector_similarity": 0.7},
    ]
    ranked = rank_jobs(jobs, top_n=3)
    # tie break 1: u3 and u2 have higher ai_score than u1 (0.9 vs 0.7)
    # tie break 2: u3 has higher vector_similarity than u2 (0.7 vs 0.6)
    assert ranked[0]["job_url"] == "u3"
    assert ranked[1]["job_url"] == "u2"
    assert ranked[2]["job_url"] == "u1"


def test_rank_jobs_assigns_final_rank():
    """rank_jobs must add a final_rank field (1-indexed)."""
    jobs = [
        {"job_url": "u1", "final_score": 0.5, "ai_score": 0.5, "vector_similarity": 0.5},
        {"job_url": "u2", "final_score": 0.9, "ai_score": 0.9, "vector_similarity": 0.9},
    ]
    ranked = rank_jobs(jobs, top_n=2)
    assert ranked[0]["final_rank"] == 1
    assert ranked[1]["final_rank"] == 2
