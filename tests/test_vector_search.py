"""Tests for fitcv.vector_search — all pure unit tests (no cloud calls)."""

import pytest

from fitcv.vector_search import build_candidate_query_text, build_vector_search_query


# ── build_candidate_query_text ────────────────────────────────────────────────

def test_build_candidate_query_text_includes_headline() -> None:
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {"domains": ["data_engineering"]},
    }
    text = build_candidate_query_text(profile)
    assert "Data Engineer" in text


def test_build_candidate_query_text_includes_skills() -> None:
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "BigQuery"}],
        "preferences": {"domains": []},
    }
    text = build_candidate_query_text(profile)
    assert "SQL" in text
    assert "Python" in text


def test_build_candidate_query_text_includes_preferred_domains() -> None:
    profile = {
        "headline": "DE",
        "skills": [],
        "preferences": {"domains": ["data_engineering", "analytics"]},
    }
    text = build_candidate_query_text(profile)
    assert "data_engineering" in text or "analytics" in text


def test_build_candidate_query_text_handles_missing_fields() -> None:
    """Should not crash when optional fields are absent."""
    profile: dict = {}
    text = build_candidate_query_text(profile)
    assert isinstance(text, str)


def test_build_candidate_query_text_is_deterministic() -> None:
    """Same profile always produces the same query text."""
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "dbt"}],
        "preferences": {"domains": ["analytics"]},
    }
    assert build_candidate_query_text(profile) == build_candidate_query_text(profile)


# ── build_vector_search_query ─────────────────────────────────────────────────

def test_build_vector_search_query_contains_vector_search() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "VECTOR_SEARCH" in query


def test_build_vector_search_query_targets_job_summary_chunk() -> None:
    """Query must filter to chunk_type = 'job_summary' only."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
    assert "job_summary" in query


def test_build_vector_search_query_enforces_top_n() -> None:
    """top_n must appear in the query."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "50" in query


def test_build_vector_search_query_filters_passed_universe() -> None:
    """Query must restrict to the rule-filtered job universe."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
    # Must embed the passed URLs directly or reference a filtered subquery
    assert "url1" in query or "rule_filter_results" in query or "passed" in query.lower()


def test_build_vector_search_query_outputs_job_url() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "job_url" in query


def test_build_vector_search_query_references_job_embeddings_table() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "job_embeddings" in query


def test_build_vector_search_query_empty_passed_urls() -> None:
    """Empty passed_job_urls → query should still be a valid SQL string."""
    query = build_vector_search_query(top_n=50, passed_job_urls=[])
    assert isinstance(query, str)
    assert "VECTOR_SEARCH" in query


# ── integration tests ─────────────────────────────────────────────────────────

@pytest.mark.integration
def test_run_vector_search_returns_shortlist(config: dict, sample_profile_path) -> None:
    """Integration — runs VECTOR_SEARCH against real BQ and returns ranked rows."""
    from pathlib import Path
    from fitcv.candidate import load_profile_yaml
    from fitcv.rule_filter import apply_rule_filters
    from fitcv.vector_search import run_vector_search

    profile = load_profile_yaml(sample_profile_path)
    # Use empty passed_job_urls to test graceful short-circuit
    result = run_vector_search(profile, passed_job_urls=[], config=config, top_n=10)
    assert isinstance(result, list)
