"""
@meta
type: test
scope: unit
domain: pipeline
covers:
  - create_run_id: UUID4 format
  - build_ranking_features: merges shortlist + ai_scores by job_url
  - run_pipeline: returns correct schema, skips 'skip' fit jobs,
    skips jobs that fail validation
excludes:
  - BigQuery integration (all store_* functions are mocked)
  - LLM calls (generate_cv, run_ai_scoring, run_vector_search mocked)
tags:
  - fast
  - ci-safe
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from fitcv.pipeline import build_ranking_features, create_run_id


# ── create_run_id ─────────────────────────────────────────────────────────────

def test_create_run_id_returns_valid_uuid() -> None:
    run_id = create_run_id()
    uuid.UUID(run_id)  # raises ValueError if not valid


def test_create_run_id_unique() -> None:
    """Each call must return a different ID."""
    assert create_run_id() != create_run_id()


# ── build_ranking_features ────────────────────────────────────────────────────

def _make_shortlist() -> list[dict]:
    return [
        {"job_url": "https://example.com/1", "similarity_score": 0.9, "rank": 1},
        {"job_url": "https://example.com/2", "similarity_score": 0.7, "rank": 2},
    ]


def _make_ai_scores() -> list[dict]:
    return [
        {
            "job_url": "https://example.com/1",
            "ai_score": 0.85,
            "fit_label": "strong",
            "must_have_match": 1.0,
            "title_relevance": 0.8,
            "seniority_fit": 0.9,
            "preference_fit": 0.7,
            "required_skills": ["SQL", "Python"],
            "job_title": "Data Engineer",
            "seniority": "senior",
        },
        {
            "job_url": "https://example.com/2",
            "ai_score": 0.6,
            "fit_label": "stretch",
            "must_have_match": 0.5,
            "title_relevance": 0.6,
            "seniority_fit": 0.8,
            "preference_fit": 0.5,
            "required_skills": ["Spark"],
            "job_title": "ML Engineer",
            "seniority": "mid",
        },
    ]


def test_build_ranking_features_merges_by_job_url() -> None:
    profile: dict = {"preferences": {"target_role": "Data Engineer"}}
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    assert len(features) == 2
    urls = {f["job_url"] for f in features}
    assert urls == {"https://example.com/1", "https://example.com/2"}


def test_build_ranking_features_includes_vector_similarity() -> None:
    profile: dict = {"preferences": {}}
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["vector_similarity"] == pytest.approx(0.9)


def test_build_ranking_features_carries_ai_score_fields() -> None:
    profile: dict = {"preferences": {}}
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["ai_score"] == pytest.approx(0.85)
    assert job1["must_have_match"] == pytest.approx(1.0)


def test_build_ranking_features_drops_jobs_missing_from_ai_scores() -> None:
    """Jobs in shortlist but absent from ai_scores (e.g. filtered upstream) are dropped."""
    shortlist = _make_shortlist() + [{"job_url": "https://example.com/99", "similarity_score": 0.5, "rank": 3}]
    profile: dict = {"preferences": {}}
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    assert all(f["job_url"] != "https://example.com/99" for f in features)


# ── run_pipeline (integrated, with all I/O mocked) ───────────────────────────

def _minimal_config() -> dict:
    return {
        "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        "pipeline": {
            "vector_search_top_n": 2,
            "ai_score_top_n": 2,
            "final_top_n": 2,
            "evidence_top_k": 3,
        },
    }


def _minimal_profile() -> dict:
    return {
        "name": "Test Candidate",
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "years_experience": 5,
        "preferences": {"target_role": "Data Engineer", "domains": []},
        "experiences": [{"role": "DE", "company": "ACME", "start": "2020", "end": "2022"}],
        "projects": [],
    }


def _minimal_job(url: str = "https://example.com/1") -> dict:
    return {
        "job_url": url,
        "job_title": "Data Engineer",
        "required_skills": ["SQL"],
        "years_required": 3,
        "vector_rank": 1,
        "ai_score": 0.85,
        "final_score": 0.80,
        "seniority": "senior",
        "location_type": "remote",
        "preferences": {},
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.classify_fit")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_correct_schema(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_classify: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []}
    mock_store_ver.return_value = None
    # create_cv_version_record is NOT mocked — it runs for real
    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    assert "run_id" in result
    assert "total_jobs" in result
    assert "passed_filter" in result
    assert "ranked" in result
    assert "cvs_generated" in result
    assert result["total_jobs"] == 1
    assert result["cvs_generated"] == 1


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.classify_fit")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_skips_skip_fit_jobs(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_classify: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.4, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = []
    mock_gap.return_value = {"matched": [], "partial": [], "missing": ["SQL"]}
    mock_classify.return_value = "skip"   # <── should be excluded
    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")
    assert result["cvs_generated"] == 0


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.classify_fit")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_skips_invalid_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_classify: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = []
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# Broken CV"
    mock_validate.return_value = {
        "valid": False,
        "missing_sections": ["Experience"],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")
    assert result["cvs_generated"] == 0


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.classify_fit")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_per_job_failure_skips_not_crashes(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_classify: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """A per-job exception must not crash the pipeline — only that job is skipped."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.side_effect = RuntimeError("BQ connection failed")
    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")
    # Pipeline should still return without raising
    assert result["cvs_generated"] == 0
    assert result["total_jobs"] == 1


@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_shared_config_loader(mock_config: MagicMock) -> None:
    from fitcv.pipeline import run_pipeline

    mock_config.side_effect = RuntimeError("shared loader called")

    with pytest.raises(RuntimeError, match="shared loader called"):
        run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    mock_config.assert_called_once_with("config/env.yaml")
