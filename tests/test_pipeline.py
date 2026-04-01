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
from unittest.mock import ANY, MagicMock, patch

import pytest

from fitcv.pipeline import (
    _build_stage_transition_artifacts,
    _materialize_scoring_shortlist,
    build_ranking_features,
    create_run_id,
)


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


def test_build_ranking_features_accepts_vector_search_field_names() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.93, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.71, "vector_rank": 2},
    ]
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["vector_similarity"] == pytest.approx(0.93)
    assert job1["vector_rank"] == 1


def test_build_ranking_features_carries_ai_score_fields() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Engineer",
            "seniority_target": "senior",
        },
    }
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["ai_score"] == pytest.approx(0.85)
    assert job1["must_have_match"] == pytest.approx(1.0)
    assert job1["title_relevance"] == pytest.approx(1.0)
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(0.5)


def test_materialize_scoring_shortlist_excludes_raw_hits_absent_from_passed_jobs() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Engineer"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/999", "vector_similarity": 0.89, "vector_rank": 2},
    ]

    shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs, vector_search_top_n=5)

    assert shortlist == [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "vector_similarity": 0.91,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        }
    ]


def test_materialize_scoring_shortlist_renumbers_sparse_raw_ranks_to_job_level_order() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Engineer"},
        {"job_url": "https://example.com/2", "title": "Analytics Engineer"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.87, "vector_rank": 33},
    ]

    shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs, vector_search_top_n=5)

    assert shortlist == [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "vector_similarity": 0.91,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        },
        {
            "job_url": "https://example.com/2",
            "title": "Analytics Engineer",
            "vector_similarity": 0.87,
            "vector_rank": 2,
            "shortlist_origin": "vector_search",
        },
    ]


def test_build_ranking_features_uses_all_supported_weighted_features() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Engineer",
            "seniority_target": "senior",
            "domains": ["data_science"],
            "location_types": ["remote"],
        },
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Senior Data Engineer",
            "seniority": "senior",
            "job_family": "data_science",
            "location_type": "remote",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.85, "fit_label": "strong"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.40,
            "must_have_match": 0.20,
            "vector_similarity": 0.15,
            "title_relevance": 0.10,
            "seniority_fit": 0.10,
            "preference_fit": 0.05,
        },
        "missing_value_defaults": {
            "ai_score": 0.0,
            "must_have_match": 0.5,
            "vector_similarity": 0.0,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "preference_fit": 0.5,
        },
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)
    job1 = features[0]

    assert job1["must_have_match"] == pytest.approx(1.0)
    assert job1["title_relevance"] == pytest.approx(1.0)
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(1.0)
    assert job1["final_score"] == pytest.approx(
        (0.85 * 0.40) + (1.0 * 0.20) + (0.9 * 0.15) + (1.0 * 0.10) + (1.0 * 0.10) + (1.0 * 0.05)
    )


def test_build_ranking_features_preserves_zero_weight_features_in_payload() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Engineer",
            "seniority_target": "senior",
            "domains": ["data_science"],
            "location_types": ["remote"],
        },
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Senior Data Engineer",
            "seniority": "senior",
            "job_family": "data_science",
            "location_type": "remote",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.85, "fit_label": "strong"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.73,
            "must_have_match": 0.0,
            "vector_similarity": 0.27,
            "title_relevance": 0.0,
            "seniority_fit": 0.0,
            "preference_fit": 0.0,
        },
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)
    job1 = features[0]

    assert job1["must_have_match"] == pytest.approx(1.0)
    assert job1["title_relevance"] == pytest.approx(1.0)
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(1.0)
    assert job1["final_score"] == pytest.approx((0.85 * 0.73) + (0.9 * 0.27))


def test_build_ranking_features_prefers_missing_value_defaults_key() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [{"job_url": "https://example.com/1", "vector_similarity": None, "vector_rank": 1}]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.4, "fit_label": "stretch"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.4,
            "must_have_match": 0.2,
            "vector_similarity": 0.15,
            "title_relevance": 0.1,
            "seniority_fit": 0.1,
            "preference_fit": 0.05,
        },
        "missing_value_defaults": {
            "ai_score": 0.0,
            "vector_similarity": 0.25,
            "must_have_match": 0.5,
            "title_relevance": 0.25,
            "seniority_fit": 0.25,
            "preference_fit": 0.25,
        },
        "ranking_null_defaults": {
            "ai_score": 0.0,
            "vector_similarity": 0.99,
        },
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)

    assert features[0]["final_score"] == pytest.approx(
        (0.4 * 0.4) + (0.5 * 0.2) + (0.25 * 0.15) + (0.5 * 0.1) + (0.5 * 0.1) + (0.5 * 0.05)
    )


def test_build_ranking_features_drops_jobs_missing_from_ai_scores() -> None:
    """Jobs in shortlist but absent from ai_scores (e.g. filtered upstream) are dropped."""
    shortlist = _make_shortlist() + [{"job_url": "https://example.com/99", "similarity_score": 0.5, "rank": 3}]
    profile: dict = {"preferences": {}}
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    assert all(f["job_url"] != "https://example.com/99" for f in features)


def test_build_ranking_features_preserves_structured_job_fields_from_shortlist() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.93,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Structured Data Engineer",
            "years_required": 4,
        },
        {
            "job_url": "https://example.com/2",
            "vector_similarity": 0.71,
            "vector_rank": 2,
            "required_skills": ["Spark"],
            "title": "Structured ML Engineer",
            "years_required": 3,
        },
    ]
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["required_skills"] == ["SQL", "Python"]
    assert job1["title"] == "Structured Data Engineer"
    assert job1["years_required"] == 4


@patch("fitcv.pipeline.logger")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_logs_full_validation_reasons(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_logger: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": False,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": ["Skill 'Rust' in CV Skills section is not in candidate knowledge base"],
        "warnings": [],
    }

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    mock_logger.warning.assert_called_with(
        "[run_id=%s] CV for %s failed validation: %s",
        ANY,
        job["job_url"],
        {
            "missing_sections": [],
            "grounding_violations": [],
            "skill_violations": ["Skill 'Rust' in CV Skills section is not in candidate knowledge base"],
            "warnings": [],
        },
    )


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_retries_once_for_missing_sections_only(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
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
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.side_effect = ["# First Draft", "# Repaired Draft"]
    mock_validate.side_effect = [
        {
            "valid": False,
            "missing_sections": ["Certifications"],
            "grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
        },
        {
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
        },
    ]
    mock_create_version.return_value = {"version_id": "cv-1"}

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    assert result["cvs_generated"] == 1
    assert mock_gen_cv.call_count == 2
    assert mock_validate.call_count == 2
    retry_call = mock_gen_cv.call_args_list[1]
    assert retry_call.kwargs["repair_missing_sections"] == ["Certifications"]
    mock_store_ver.assert_called_once()


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
        # Nested CV config (preset-based)
        "cv": {
            "generation": {
                "model": "gemini-2.5-flash",
                "prompt_version": "v1",
            },
            "preset": "europass",
            "composition": {
                "summary": {"enabled": True},
                "experience": {"enabled": True, "required": True},
                "skills": {"enabled": True, "required": True},
            },
            "content_rules": {"evidence_grounded_only": True},
            "validation": {"max_pages": 2},
        },
        # Compatibility flat keys (produced by _apply_cv_compatibility_projection)
        "cv_generation_model": "gemini-2.5-flash",
        "required_cv_sections": ["Experience", "Skills"],
        "cv_max_pages": 2,
        "prompt_version": "v1",
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


def _raw_scraper_job(url: str = "https://example.com/1") -> dict:
    return {
        "jobUrl": url,
        "title": "Data Engineer",
        "location": "Remote",
        "postedTime": "1 day ago",
        "publishedAt": "2026-03-24",
        "companyName": "ACME",
        "companyUrl": "https://example.com/company",
        "companyId": "123",
        "description": "Build data pipelines",
        "applicationsCount": "10 applicants",
        "contractType": "Full-time",
        "experienceLevel": "Mid-Senior level",
        "workType": "Engineering",
        "sector": "Software",
        "salary": "",
        "applyUrl": "https://example.com/apply",
        "applyType": "EXTERNAL",
        "posterFullName": "Hiring Manager",
        "posterProfileUrl": "https://example.com/poster",
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_supplied_run_id_for_summary_and_cv_records(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
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
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path="config/env.yaml",
        run_id="cp-run-123",
    )

    assert result["run_id"] == "cp-run-123"
    assert mock_create_version.call_args.kwargs["run_id"] == "cp-run-123"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_profile_json_text")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
def test_run_pipeline_uses_runtime_profile_json_without_touching_profile_path(
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_json: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
    }
    profile = _minimal_profile()
    cfg = _minimal_config()
    cfg["runtime_inputs"] = {"candidate_profile_json": "{\"name\": \"Runtime Candidate\"}"}

    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_json.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    run_pipeline("data/sample_jobs.json", config=cfg, run_id="runtime-profile")

    mock_profile_json.assert_called_once_with("{\"name\": \"Runtime Candidate\"}")
    mock_profile_yaml.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_persists_structured_cv_and_includes_it_in_export(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = {"structured_cv": structured_cv, "markdown": "# CV Markdown"}
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v-structured",
        "generated_at": "2026-03-29T12:00:00+00:00",
    }

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="structured-run")

    create_kwargs = mock_create_version.call_args.kwargs
    assert create_kwargs["cv_structured"] == structured_cv
    assert create_kwargs["cv_generation_model"] == "gemini-2.5-flash"
    assert create_kwargs["cv_prompt_version"] == "v1"
    export_cv = result["export_results"][0]["cv"]
    assert export_cv["structured"] == structured_cv
    assert export_cv["schema_version"] == "cv_doc_v1"
    assert export_cv["model_used"] == "gemini-2.5-flash"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_accepted_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    evidence = [
        {
            "evidence_id": "e1",
            "evidence_type": "experience_entry",
            "source_ref": "experience[0]",
            "name": "Data Engineer at Fintech Startup GmbH",
            "skills": ["SQL", "Python"],
        }
    ]
    gap = {"matched": ["SQL"], "partial": [], "missing": []}

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = evidence
    mock_gap.return_value = gap
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = {"structured_cv": structured_cv, "markdown": "# CV Markdown"}
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v-debug",
        "generated_at": "2026-03-31T12:00:00+00:00",
    }

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="debug-accepted")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["job_url"] == job["job_url"]
    assert record["status"] == "accepted"
    assert record["fit_classification"] == "strong"
    assert record["evidence_used"] == [
        {
            "evidence_type": "experience_entry",
            "source_ref": "experience[0]",
            "name": "Data Engineer at Fintech Startup GmbH",
        }
    ]
    assert record["gap_summary"] == gap
    assert record["structured_cv_initial"] == structured_cv
    assert record["validation_initial"]["valid"] is True
    assert record["repair_attempt"] == {"performed": False, "missing_sections": []}
    assert record["structured_cv_final"] == structured_cv
    assert record["markdown_final"] == "# CV Markdown"
    assert record["error"] is None


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_validation_failed_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = {"structured_cv": structured_cv, "markdown": "# Broken CV"}
    mock_validate.return_value = validation

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="debug-validation")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["status"] == "validation_failed"
    assert record["structured_cv_initial"] == structured_cv
    assert record["validation_initial"] == validation
    assert record["structured_cv_final"] is None
    assert record["markdown_final"] is None
    assert record["error"]["stage"] == "validation"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_persistence_failed_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = {"structured_cv": structured_cv, "markdown": "# CV Markdown"}
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v-debug",
        "generated_at": "2026-03-31T12:00:00+00:00",
    }
    mock_store_ver.side_effect = RuntimeError("BigQuery insert errors for cv_versions: boom")

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="debug-persist")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["status"] == "persistence_failed"
    assert record["structured_cv_initial"] == structured_cv
    assert record["structured_cv_final"] == structured_cv
    assert record["markdown_final"] == "# CV Markdown"
    assert record["error"]["stage"] == "persistence"


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
@patch("fitcv.pipeline.load_run_structured_jobs")
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
    mock_load_run_struct: MagicMock,
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
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
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
    assert "stage_transition_artifacts" in result
    assert result["total_jobs"] == 1
    assert result["cvs_generated"] == 1
    stage_artifacts = result["stage_transition_artifacts"]
    assert stage_artifacts["schema_version"] == "stage_transition_artifacts_v2"
    assert set(stage_artifacts["stages"]) == {
        "normalize",
        "enrich",
        "rule_filter",
        "shortlist",
        "ranking",
        "cv_generation",
    }
    for stage_id, block in stage_artifacts["stages"].items():
        assert block["stage_id"] == stage_id
        assert "input_counts" in block
        assert "output_counts" in block
        assert "decision_summary" in block
        assert "inputs_sample" in block
        assert "outputs_sample" in block
        assert "dropped_or_changed_sample" in block
    assert stage_artifacts["stages"]["normalize"]["input_counts"]["raw_jobs"] == 1
    assert stage_artifacts["stages"]["ranking"]["output_counts"]["ranked_jobs"] == 1
    assert stage_artifacts["stages"]["cv_generation"]["output_counts"]["accepted"] == 1
    assert stage_artifacts["stages"]["cv_generation"]["outputs_sample"][0]["job_url"] == job["job_url"]


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_prepares_raw_rows_before_bigquery_insert(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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

    raw_job = _raw_scraper_job()
    normalized_job = _minimal_job(url=raw_job["jobUrl"])
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [raw_job]
    mock_norm.return_value = [normalized_job]
    mock_enrich.return_value = [normalized_job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [normalized_job], "rejected": []}
    mock_vec.return_value = [{"job_url": normalized_job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [normalized_job]
    mock_build_feat.return_value = [normalized_job]
    mock_rank.return_value = [normalized_job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []}

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    inserted_rows = mock_load_bq.call_args.args[0]
    assert inserted_rows[0]["job_url"] == raw_job["jobUrl"]
    assert "posterProfileUrl" not in inserted_rows[0]
    assert "poster_profile_url" not in inserted_rows[0]
    assert "raw_json" in inserted_rows[0]


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_passes_job_dicts_to_embeddings_and_urls_to_vector_search(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    embed_jobs_arg = mock_embed_jobs.call_args.args[0]
    vector_urls_arg = mock_vec.call_args.args[1]
    assert embed_jobs_arg == [job]
    assert vector_urls_arg == [job["job_url"]]
    cv_block = result["stage_transition_artifacts"]["stages"]["cv_generation"]
    assert cv_block["status"] == "not_reached"
    assert cv_block["input_counts"] == {}
    assert cv_block["output_counts"] == {}
    assert cv_block["inputs_sample"] == []
    assert cv_block["outputs_sample"] == []
    assert cv_block["dropped_or_changed_sample"] == []


def test_build_stage_transition_artifacts_includes_changed_state_samples() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Analyst"},
        {"job_url": "https://example.com/2", "title": "ML Analyst"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
    ]
    shortlist = [
        {"job_url": "https://example.com/1", "title": "Data Analyst", "vector_similarity": 0.91, "vector_rank": 1, "shortlist_origin": "vector_search"},
        {"job_url": "https://example.com/2", "title": "ML Analyst", "vector_similarity": 0.0, "vector_rank": 2, "shortlist_origin": "backfill"},
    ]
    ranking_inputs = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Analyst",
            "ai_score": 0.9,
            "must_have_match": 1.0,
            "vector_similarity": 0.91,
            "title_relevance": 1.0,
            "seniority_fit": 1.0,
            "preference_fit": 0.5,
            "fit_label": "strong",
            "final_score": 0.905,
        },
        {
            "job_url": "https://example.com/2",
            "title": "ML Analyst",
            "ai_score": 0.5,
            "must_have_match": 0.5,
            "vector_similarity": 0.0,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "preference_fit": 0.5,
            "fit_label": "stretch",
            "final_score": 0.25,
        },
    ]
    ranked = [ranking_inputs[0]]
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=passed_jobs,
        normalized=passed_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=passed_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        backfilled_job_urls=["https://example.com/2"],
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        ai_scores=ranking_inputs,
        ranking_inputs=ranking_inputs,
        ranked=ranked,
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL", "Python"]},
        config={"cv": {"generation": {"model": "gemini-2.5-flash", "prompt_version": "v1"}}},
    )

    shortlist_block = artifacts["stages"]["shortlist"]
    ranking_block = artifacts["stages"]["ranking"]

    assert shortlist_block["dropped_or_changed_sample"][0]["change_type"] == "missed_by_vector_search"
    assert shortlist_block["dropped_or_changed_sample"][1]["change_type"] == "backfilled_for_scoring"
    assert ranking_block["dropped_or_changed_sample"][0]["change_type"] == "scored_not_ranked"
    assert ranking_block["outputs_sample"][0]["job_url"] == "https://example.com/1"
    assert ranking_block["outputs_sample"][0]["must_have_match"] == pytest.approx(1.0)
    assert ranking_block["dropped_or_changed_sample"][0]["title_relevance"] == pytest.approx(0.5)


def test_build_stage_transition_artifacts_reports_unique_job_and_raw_row_shortlist_counts() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Analyst"},
        {"job_url": "https://example.com/2", "title": "ML Analyst"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 2},
        {"job_url": "https://example.com/2", "vector_similarity": 0.83, "vector_rank": 33},
    ]
    shortlist = [
        {"job_url": "https://example.com/1", "title": "Data Analyst", "vector_similarity": 0.91, "vector_rank": 1, "shortlist_origin": "vector_search"},
        {"job_url": "https://example.com/2", "title": "ML Analyst", "vector_similarity": 0.83, "vector_rank": 2, "shortlist_origin": "vector_search"},
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=passed_jobs,
        normalized=passed_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=passed_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        backfilled_job_urls=[],
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL", "Python"]},
        config={"cv": {"generation": {"model": "gemini-2.5-flash", "prompt_version": "v1"}}},
    )

    shortlist_block = artifacts["stages"]["shortlist"]

    assert shortlist_block["output_counts"]["raw_vector_rows"] == 3
    assert shortlist_block["output_counts"]["raw_vector_hits"] == 2
    assert shortlist_block["outputs_sample"][1]["vector_rank"] == 2


def test_build_stage_transition_artifacts_reports_six_feature_ranking_contract() -> None:
    ranking_inputs = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "ai_score": 0.85,
            "must_have_match": 1.0,
            "vector_similarity": 0.9,
            "title_relevance": 1.0,
            "seniority_fit": 1.0,
            "preference_fit": 1.0,
            "fit_label": "strong",
            "final_score": 0.925,
            "shortlist_origin": "vector_search",
        }
    ]
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=ranking_inputs,
        normalized=ranking_inputs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=ranking_inputs,
        passed_jobs=ranking_inputs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=ranking_inputs,
        shortlist=ranking_inputs,
        backfilled_job_urls=[],
        vector_top_n=10,
        candidate_summary="Candidate: Data Engineer",
        ai_scores=ranking_inputs,
        ranking_inputs=ranking_inputs,
        ranked=ranking_inputs,
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Engineer"}},
        config={
            "ranking_weights": {
                "ai_score": 0.73,
                "must_have_match": 0.0,
                "vector_similarity": 0.27,
                "title_relevance": 0.0,
                "seniority_fit": 0.0,
                "preference_fit": 0.0,
            },
            "missing_value_defaults": {
                "ai_score": 0.0,
                "must_have_match": 0.5,
                "vector_similarity": 0.0,
                "title_relevance": 0.5,
                "seniority_fit": 0.5,
                "preference_fit": 0.5,
            },
            "cv": {"generation": {"model": "gemini-2.5-flash", "prompt_version": "v1"}},
        },
    )

    ranking_block = artifacts["stages"]["ranking"]
    decision_summary = ranking_block["decision_summary"]

    assert decision_summary["configured_ranking_weights"] == {
        "ai_score": 0.73,
        "must_have_match": 0.0,
        "vector_similarity": 0.27,
        "title_relevance": 0.0,
        "seniority_fit": 0.0,
        "preference_fit": 0.0,
    }
    assert decision_summary["configured_missing_value_defaults"] == {
        "ai_score": 0.0,
        "must_have_match": 0.5,
        "vector_similarity": 0.0,
        "title_relevance": 0.5,
        "seniority_fit": 0.5,
        "preference_fit": 0.5,
    }
    assert decision_summary["zero_weight_features"] == [
        "must_have_match",
        "title_relevance",
        "seniority_fit",
        "preference_fit",
    ]
    assert decision_summary["contributing_features"] == [
        "ai_score",
        "vector_similarity",
    ]
    assert ranking_block["inputs_sample"][0]["must_have_match"] == pytest.approx(1.0)
    assert ranking_block["inputs_sample"][0]["preference_fit"] == pytest.approx(1.0)


def test_build_stage_transition_artifacts_caps_samples_at_20_and_truncates_text() -> None:
    raw_jobs = [
        {
            "job_url": f"https://example.com/{i}",
            "title": f"Role {i}",
            "description_cleaned": "x" * 800,
        }
        for i in range(25)
    ]
    debug_records = [
        {
            "job_url": f"https://example.com/{i}",
            "job_title": f"Role {i}",
            "status": "accepted",
            "decision_chain": {"primary_fit": {"label": "strong"}},
            "markdown_final": "y" * 1000,
            "validation_initial": {"valid": True},
            "repair_attempt": {"performed": False, "missing_sections": []},
            "gap_summary": {"matched": ["SQL"]},
            "evidence_used": [],
            "error": None,
        }
        for i in range(25)
    ]
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=raw_jobs,
        normalized=raw_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=raw_jobs,
        passed_jobs=raw_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        backfilled_job_urls=[],
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        ai_scores=[],
        ranking_inputs=[],
        ranked=raw_jobs,
        final_top_n=10,
        cv_generation_debug_records=debug_records,
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL"]},
        config={"cv": {"generation": {"model": "gemini-2.5-flash", "prompt_version": "v1"}}},
    )

    normalize_block = artifacts["stages"]["normalize"]
    cv_block = artifacts["stages"]["cv_generation"]
    assert len(normalize_block["inputs_sample"]) == 20
    assert len(cv_block["outputs_sample"]) == 20
    assert normalize_block["inputs_sample"][0]["description_cleaned"].endswith("...[truncated]")
    assert cv_block["outputs_sample"][0]["markdown_final"].endswith("...[truncated]")


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_passes_enriched_shortlist_rows_to_ai_scoring(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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

    job = {
        **_minimal_job(),
        "title": "Structured Data Engineer",
        "required_skills": ["SQL", "Python"],
        "responsibilities": ["Build data pipelines"],
        "job_family": "data_engineering",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    shortlist_arg = mock_ai.call_args.args[0]
    assert shortlist_arg == [
        {
            **job,
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        }
    ]


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_backfills_missing_passed_jobs_into_shortlist_when_capacity_allows(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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

    first_job = {
        **_minimal_job("https://example.com/1"),
        "title": "Structured Data Engineer",
    }
    second_job = {
        **_minimal_job("https://example.com/2"),
        "title": "Retail Banking Analyst",
        "required_skills": ["SQL", "Power BI"],
        "job_family": "analytics",
    }
    profile = _minimal_profile()
    cfg = _minimal_config()
    cfg["pipeline"]["vector_search_top_n"] = 5

    mock_config.return_value = cfg
    mock_parse.return_value = [_raw_scraper_job(first_job["job_url"]), _raw_scraper_job(second_job["job_url"])]
    mock_norm.return_value = [first_job, second_job]
    mock_enrich.return_value = [first_job, second_job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [first_job["job_url"], second_job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": first_job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [first_job, second_job]
    mock_build_feat.return_value = [first_job, second_job]
    mock_rank.return_value = []

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    shortlist_arg = mock_ai.call_args.args[0]
    assert shortlist_arg == [
        {
            **first_job,
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        },
        {
            **second_job,
            "vector_similarity": 0.0,
            "vector_rank": 2,
            "shortlist_origin": "backfill",
        },
    ]
    second_export_row = next(
        row for row in result["export_results"]
        if row["job_url"] == second_job["job_url"]
    )
    assert second_export_row["pipeline_status"] != "not_shortlisted"
    assert result["shortlist_debug"] == {
        "vector_search_top_n": 5,
        "passed_jobs_total": 2,
        "raw_vector_rows_total": 1,
        "shortlisted_jobs_total": 1,
        "scoring_shortlisted_jobs_total": 2,
        "backfilled_jobs_total": 1,
        "retrieval_anomaly_urls": [],
        "candidate_query_text": "Candidate: Data Engineer\nTarget role: Data Engineer\nRecent roles: DE\nSkills: SQL, Python",
        "not_shortlisted_job_urls": [second_job["job_url"]],
        "backfilled_job_urls": [second_job["job_url"]],
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_ranked_fit_label_as_floor_for_layer4_fit_gate(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "stretch",
        "ai_score": 0.5,
        "final_score": 0.4,
        "title": "Retail Banking Analyst",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = []
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": ["Power BI"]}
    mock_classify.return_value = "skip"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v1",
        "generated_at": "2026-03-29T16:11:40Z",
    }

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert result["cvs_generated"] == 1
    assert result["cv_generation_debug_records"][0]["status"] == "accepted"
    assert result["cv_generation_debug_records"][0]["fit_classification"] == "stretch"
    assert result["export_results"][0]["pipeline_status"] == "ranked_with_cv"
    assert result["export_results"][0]["cv"]["fit_classification"] == "stretch"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_reranker_fit_as_sole_post_filter_cv_gate(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
        "title": "Retail Banking Analyst",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = []
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    mock_gen_cv.assert_not_called()
    mock_validate.assert_not_called()
    mock_classify.assert_not_called()
    assert result["cv_generation_debug_records"][0]["status"] == "skipped_fit_gate"
    assert result["cv_generation_debug_records"][0]["fit_classification"] == "skip"
    assert result["export_results"][0]["pipeline_status"] == "ranked_skipped_fit_gate"


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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_skips_reranker_skip_fit_jobs(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
    }
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
    mock_classify.return_value = "strong"
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
@patch("fitcv.pipeline.load_run_structured_jobs")
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
    mock_load_run_struct: MagicMock,
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
@patch("fitcv.pipeline.load_run_structured_jobs")
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
    mock_load_run_struct: MagicMock,
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_layer4_cv_error_for_per_job_exception(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_pre_filter: MagicMock,
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

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def emit(self, stage: str, level: str, message: str) -> None:
            self.events.append((stage, level, message))

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
    }
    profile = _minimal_profile()
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.side_effect = RuntimeError("BQ connection failed")

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", reporter=reporter)

    assert (
        "layer4_cv_error",
        "error",
        f"CV generation failed for {job['job_url']}: BQ connection failed",
    ) in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_shortlist_and_ai_score_counts(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def emit(self, stage: str, level: str, message: str) -> None:
            self.events.append((stage, level, message))

    jobs = [_minimal_job("https://example.com/1"), _minimal_job("https://example.com/2")]
    profile = _minimal_profile()
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = jobs
    mock_norm.return_value = jobs
    mock_enrich.return_value = jobs
    mock_profile_yaml.return_value = profile
    mock_pre_filter.return_value = {"passed": [job["job_url"] for job in jobs], "rejected": []}
    mock_filter.return_value = {"passed": [job["job_url"] for job in jobs], "rejected": []}
    mock_vec.return_value = [
        {"job_url": jobs[0]["job_url"], "similarity_score": 0.95, "rank": 1},
        {"job_url": jobs[1]["job_url"], "similarity_score": 0.80, "rank": 2},
    ]
    mock_ai.return_value = [jobs[0]]
    mock_build_feat.return_value = [jobs[0]]
    mock_rank.return_value = [jobs[0]]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", reporter=reporter)

    assert ("layer3_shortlist", "info", "Vector shortlist: 2 raw hits") in reporter.events
    assert ("layer3_ai_score", "info", "AI scored: 1 jobs") in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_normalization_dedupe_event(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def emit(self, stage: str, level: str, message: str) -> None:
            self.events.append((stage, level, message))

    duplicate_jobs = [
        _raw_scraper_job("https://example.com/1"),
        _raw_scraper_job("https://example.com/2"),
    ]
    duplicate_jobs[1]["companyId"] = duplicate_jobs[0]["companyId"]
    duplicate_jobs[1]["title"] = duplicate_jobs[0]["title"]
    duplicate_jobs[1]["description"] = duplicate_jobs[0]["description"]
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = duplicate_jobs
    mock_enrich.return_value = [_minimal_job("https://example.com/1")]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = [{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [_minimal_job("https://example.com/1")]
    mock_build_feat.return_value = [_minimal_job("https://example.com/1")]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", reporter=reporter)

    assert (
        "layer1_normalize",
        "info",
        "Normalization dedupe: kept 1 of 2 jobs, removed 1 duplicate(s)",
    ) in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_pipeline_complete_event_omits_export_rows(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def emit(self, stage: str, level: str, message: str) -> None:
            self.events.append((stage, level, message))

    job = _minimal_job()
    profile = _minimal_profile()
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1", "generated_at": "2026-03-29T16:11:40Z"}

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", reporter=reporter)

    pipeline_complete = next(event for event in reporter.events if event[0] == "pipeline_complete")
    assert "export_results" not in pipeline_complete[2]


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_export_results_sorted_and_statused(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    ranked_with_cv = {
        **_minimal_job("https://example.com/1"),
        "title": "Ranked With CV",
        "job_title": "Ranked With CV",
        "required_skills": ["SQL"],
        "ai_score": 0.91,
        "final_score": 0.95,
        "vector_similarity": 0.88,
        "fit_label": "strong",
        "final_rank": 1,
    }
    ranked_no_cv = {
        **_minimal_job("https://example.com/2"),
        "title": "Ranked No CV",
        "job_title": "Ranked No CV",
        "required_skills": ["Python"],
        "ai_score": 0.20,
        "final_score": 0.80,
        "vector_similarity": 0.70,
        "fit_label": "skip",
        "final_rank": 2,
    }
    not_shortlisted = {
        **_minimal_job("https://example.com/3"),
        "title": "Not Shortlisted",
        "job_title": "Not Shortlisted",
        "required_skills": ["Spark"],
    }
    shortlisted_not_scored = {
        **_minimal_job("https://example.com/5"),
        "title": "Shortlisted Not Scored",
        "job_title": "Shortlisted Not Scored",
        "required_skills": ["dbt"],
    }
    scored_not_ranked = {
        **_minimal_job("https://example.com/6"),
        "title": "Scored Not Ranked",
        "job_title": "Scored Not Ranked",
        "required_skills": ["Airflow"],
        "ai_score": 0.44,
        "final_score": 0.45,
        "vector_similarity": 0.52,
        "fit_label": "stretch",
    }
    rejected_raw = _raw_scraper_job("https://example.com/4")

    cfg = _minimal_config()
    cfg["pipeline"]["final_top_n"] = 2
    mock_config.return_value = cfg
    mock_parse.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        rejected_raw,
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_norm.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        {"job_url": "https://example.com/4", "title": "Rejected Raw"},
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_enrich.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {
        "passed": [
            ranked_with_cv["job_url"],
            ranked_no_cv["job_url"],
            not_shortlisted["job_url"],
            shortlisted_not_scored["job_url"],
            scored_not_ranked["job_url"],
        ],
        "rejected": [{"job_url": "https://example.com/4", "reasons": ["applications_count_exceeded"]}],
    }
    mock_filter.return_value = {
        "passed": [
            ranked_with_cv["job_url"],
            ranked_no_cv["job_url"],
            not_shortlisted["job_url"],
            shortlisted_not_scored["job_url"],
            scored_not_ranked["job_url"],
        ],
        "rejected": [],
    }
    mock_vec.return_value = [
        {"job_url": ranked_with_cv["job_url"], "vector_similarity": 0.88, "vector_rank": 1},
        {"job_url": ranked_no_cv["job_url"], "vector_similarity": 0.70, "vector_rank": 2},
        {"job_url": shortlisted_not_scored["job_url"], "vector_similarity": 0.55, "vector_rank": 3},
        {"job_url": scored_not_ranked["job_url"], "vector_similarity": 0.52, "vector_rank": 4},
    ]
    mock_ai.return_value = [ranked_with_cv, ranked_no_cv, scored_not_ranked]
    mock_build_feat.return_value = [ranked_with_cv, ranked_no_cv, scored_not_ranked]
    mock_rank.return_value = [ranked_with_cv, ranked_no_cv]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_classify.side_effect = ["strong", "skip"]
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v1",
        "generated_at": "2026-03-29T16:11:40Z",
    }

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="run-export")

    export_results = result["export_results"]
    assert [row["job_url"] for row in export_results] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/5",
        "https://example.com/6",
        "https://example.com/4",
    ]
    assert export_results[0]["pipeline_status"] == "ranked_with_cv"
    assert export_results[0]["cv"]["version_id"] == "v1"
    assert export_results[0]["cv"]["ranking_fit_label"] == "strong"
    assert export_results[0]["enriched_job"]["required_skills"] == ["SQL"]
    assert "title" not in export_results[0]["enriched_job"]
    assert "job_url" not in export_results[0]["enriched_job"]
    assert "location_type" not in export_results[0]["enriched_job"]
    assert "domain" not in export_results[0]["enriched_job"]
    assert export_results[0]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "strong",
        },
        "cv_generation": {
            "status": "accepted",
            "attempted": True,
        },
        "validation": {
            "status": "accepted",
        },
    }
    assert export_results[1]["pipeline_status"] == "ranked_skipped_fit_gate"
    assert export_results[1]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "skip",
        },
        "cv_generation": {
            "status": "skipped_fit_gate",
            "attempted": False,
        },
        "validation": {
            "status": "not_run",
        },
    }
    assert export_results[2]["pipeline_status"] == "not_shortlisted"
    assert export_results[2]["scores"]["vector_score"] is None
    assert export_results[2]["shortlist_debug"] == {
        "passed_rule_filter": True,
        "returned_by_vector_search": False,
        "reason": "job_url_not_returned_in_raw_hits",
        "vector_search_top_n": 2,
        "vector_rank": None,
        "vector_similarity": None,
        "shortlist_origin": "not_returned_in_raw_hits",
    }
    assert export_results[3]["pipeline_status"] == "shortlisted_not_scored"
    assert export_results[3]["scores"]["vector_score"] == pytest.approx(0.55)
    assert export_results[3]["shortlist_debug"] == {
        "passed_rule_filter": True,
        "returned_by_vector_search": True,
        "reason": None,
        "vector_search_top_n": 2,
        "vector_rank": 3,
        "vector_similarity": pytest.approx(0.55),
        "shortlist_origin": "returned_by_vector_search",
    }
    assert export_results[4]["pipeline_status"] == "scored_not_ranked"
    assert export_results[4]["scores"]["final_score"] == pytest.approx(0.45)
    assert export_results[5]["pipeline_status"] == "rejected_before_enrichment"
    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 2
    assert debug_records[0]["status"] == "accepted"
    assert debug_records[0]["ranking_fit_label"] == "strong"
    assert debug_records[0]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "strong",
        },
        "cv_generation": {
            "status": "accepted",
            "attempted": True,
        },
        "validation": {
            "status": "accepted",
        },
    }
    assert debug_records[1]["status"] == "skipped_fit_gate"
    assert debug_records[1]["ranking_fit_label"] == "skip"
    assert debug_records[1]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "skip",
        },
        "cv_generation": {
            "status": "skipped_fit_gate",
            "attempted": False,
        },
        "validation": {
            "status": "not_run",
        },
    }
    assert debug_records[1]["error"] == {
        "stage": "fit_gate",
        "message": f"Skipped {ranked_no_cv['job_url']} (fit=skip)",
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_layer4_uses_enriched_job_fields_for_gap_and_debug(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    raw_job = _raw_scraper_job("https://example.com/1")
    enriched_job = {
        **_minimal_job("https://example.com/1"),
        "title": "Enriched Title",
        "required_skills": ["Python", "SQL"],
        "years_experience_min": 4,
        "years_experience_max": 6,
    }
    ranked_feature = {
        "job_url": "https://example.com/1",
        "ai_score": 0.91,
        "final_score": 0.95,
        "vector_similarity": 0.88,
        "fit_label": "strong",
        "final_rank": 1,
    }

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [raw_job]
    mock_norm.return_value = [{"job_url": "https://example.com/1", "title": "Normalized"}]
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_enrich.return_value = [enriched_job]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = [{"job_url": "https://example.com/1", "vector_similarity": 0.88, "vector_rank": 1}]
    mock_ai.return_value = [{"job_url": "https://example.com/1", "ai_score": 0.91, "fit_label": "strong"}]
    mock_build_feat.return_value = [ranked_feature]
    mock_rank.return_value = [dict(ranked_feature)]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["Python"], "partial": [], "missing": ["SQL"]}
    mock_classify.return_value = "strong"
    mock_gen_cv.return_value = {"structured_cv": {"schema_version": "cv_doc_v1"}, "markdown": "# CV Markdown"}
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1", "generated_at": "2026-03-29T16:11:40Z"}

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="run-gap")

    assert mock_gap.call_args.kwargs["required_skills"] == ["Python", "SQL"]
    assert mock_gap.call_args.kwargs["candidate_skills"] == ["SQL", "Python"]
    assert mock_gap.call_args.kwargs["years_experience_min"] == 4
    assert mock_gap.call_args.kwargs["years_experience_max"] == 6
    assert mock_gen_cv.call_args.args[0]["title"] == "Enriched Title"
    assert result["cv_generation_debug_records"][0]["job_title"] == "Enriched Title"
    assert result["cv_generation_debug_records"][0]["gap_summary"] == {
        "matched": ["Python"],
        "partial": [],
        "missing": ["SQL"],
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
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
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_to_bigquery")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_export_marks_deduplicated_rows_explicitly(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
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
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    kept = _raw_scraper_job("https://example.com/1")
    deduped = _raw_scraper_job("https://example.com/2")
    deduped["companyId"] = kept["companyId"]
    deduped["title"] = kept["title"]
    deduped["description"] = kept["description"]

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [kept, deduped]
    enriched_job = _minimal_job("https://example.com/1")
    mock_enrich.return_value = [enriched_job]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = [{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}]
    mock_ai.return_value = [enriched_job]
    mock_build_feat.return_value = [enriched_job]
    mock_rank.return_value = []

    result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    assert len(result["export_results"]) == 2
    assert result["export_results"][0]["pipeline_status"] == "scored_not_ranked"
    assert result["export_results"][1]["pipeline_status"] == "deduplicated_before_enrichment"
    assert result["export_results"][1]["reject_reasons"] == ["near_duplicate_job_posting"]


@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_shared_config_loader(mock_config: MagicMock) -> None:
    from fitcv.pipeline import run_pipeline

    mock_config.side_effect = RuntimeError("shared loader called")

    with pytest.raises(RuntimeError, match="shared loader called"):
        run_pipeline("data/sample_jobs.json", config_path="config/env.yaml")

    mock_config.assert_called_once_with("config/env.yaml")


# ── run_pipeline calls load_run_structured_jobs ──────────────────────────────

@patch("fitcv.pipeline.load_run_structured_jobs")
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
def test_run_pipeline_calls_load_run_structured_jobs(
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
    mock_load_run_struct: MagicMock,
) -> None:
    """pipeline must call load_run_structured_jobs with enriched rows and run_id."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="test-run-id")

    # load_structured_jobs must also be called (existing behavior preserved)
    mock_load_struct.assert_called_once()

    # load_run_structured_jobs must be called with the enriched rows and run_id
    mock_load_run_struct.assert_called_once()
    call_kwargs = mock_load_run_struct.call_args
    # first positional arg: enriched rows
    assert call_kwargs.args[0] == [job]
    # second positional arg: run_id
    assert call_kwargs.args[1] == "test-run-id"



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
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_to_bigquery")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_forwards_enrichment_parallelism_config_to_enrich_batch(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
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
    """enrich_batch must receive enrichment_batch_size and enrichment_concurrency from config."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    cfg = dict(_minimal_config())
    cfg["enrichment_batch_size"] = 5
    cfg["enrichment_concurrency"] = 3

    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = [{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}]
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="reg-test-id")

    args, kwargs = mock_enrich.call_args
    passed_config = kwargs.get("config", args[1] if len(args) > 1 else {})
    assert passed_config.get("enrichment_batch_size") == 5, (
        f"enrichment_batch_size not forwarded. config={passed_config}"
    )
    assert passed_config.get("enrichment_concurrency") == 3, (
        f"enrichment_concurrency not forwarded. config={passed_config}"
    )
