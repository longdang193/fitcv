from unittest.mock import MagicMock, patch

from fitcv.pipeline import run_pipeline
from fitcv.agentic_cv_generation import generate_from_analysis


def _minimal_config() -> dict:
    return {
        "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        "pipeline": {
            "vector_search_top_n": 2,
            "ai_score_top_n": 2,
            "final_top_n": 2,
            "evidence_top_k": 3,
        },
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
            "agentic_late_stage": {"enabled": False},
        },
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


def _minimal_analysis_record() -> dict:
    job = _minimal_job()
    return {
        "job_url": job["job_url"],
        "job_title": job["job_title"],
        "status": "ready_for_generation",
        "fit_classification": "strong",
        "job_snapshot": {
            **job,
            "title": "Data Engineer",
        },
        "evidence_payload": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": []},
    }


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence_bundle")
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
def test_run_pipeline_keeps_original_late_stage_path_by_default(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_to_bigquery: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_to_bigquery: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
    mock_retrieve_evidence_bundle: MagicMock,
    mock_compute_gap: MagicMock,
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
    mock_store_cv_version: MagicMock,
) -> None:
    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()

    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_normalize.return_value = [job]
    mock_enrich.return_value = [job]
    mock_load_run_structured.return_value = [job]
    mock_load_structured.return_value = [job]
    mock_load_profile.return_value = profile
    mock_apply_rule_filters.return_value = {"passed": [job["job_url"]], "rejected": []}
    ranked_job = {
        **job,
        "title": "Data Engineer",
        "fit_label": "strong",
        "fit_label_source": "reranker",
        "shortlist_origin": "vector_search",
    }
    mock_run_vector_search.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.85, "fit_label": "strong"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
    mock_retrieve_evidence_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "selected_evidence_count": 1,
    }
    mock_compute_gap.return_value = {"matched": ["SQL"], "missing": []}
    mock_generate_cv.return_value = "# Test Candidate\n## Summary\nGrounded summary"
    mock_run_all_validations.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
    }

    with patch("fitcv.pipeline.run_agentic_cv_analysis", create=True) as mock_agentic_analysis, patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
    ) as mock_agentic_generation:
        result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="late-stage-default")

    mock_agentic_analysis.assert_not_called()
    mock_agentic_generation.assert_not_called()
    mock_generate_cv.assert_called_once()
    stage_artifacts = result["stage_transition_artifacts"]["stages"]
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["late_stage_mode"] == "non_agentic"
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["agentic_late_stage_enabled"] is False
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["agentic_status"] == "not_applicable"
    assert stage_artifacts["cv_generation"]["late_stage_mode"]["late_stage_mode"] == "non_agentic"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.run_all_validations")
@patch("fitcv.pipeline.generate_cv")
@patch("fitcv.pipeline.compute_gap")
@patch("fitcv.pipeline.retrieve_evidence_bundle")
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
def test_run_pipeline_routes_through_agentic_late_stage_when_enabled(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_to_bigquery: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_to_bigquery: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
    mock_retrieve_evidence_bundle: MagicMock,
    mock_compute_gap: MagicMock,
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
    mock_store_cv_version: MagicMock,
) -> None:
    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    config["cv"]["agentic_late_stage"]["enabled"] = True

    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_normalize.return_value = [job]
    mock_enrich.return_value = [job]
    mock_load_run_structured.return_value = [job]
    mock_load_structured.return_value = [job]
    mock_load_profile.return_value = profile
    mock_apply_rule_filters.return_value = {"passed": [job["job_url"]], "rejected": []}
    ranked_job = {
        **job,
        "title": "Data Engineer",
        "fit_label": "strong",
        "fit_label_source": "reranker",
        "shortlist_origin": "vector_search",
    }
    mock_run_vector_search.return_value = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.85, "fit_label": "strong"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
    mock_retrieve_evidence_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "selected_evidence_count": 1,
    }
    mock_compute_gap.return_value = {"matched": ["SQL"], "missing": []}
    mock_run_all_validations.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
    }

    agentic_analysis_result = {
        "status": "ready_for_generation",
        "analysis_input_fingerprint": "agentic::fingerprint",
        "evidence_payload": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": []},
        "fit_classification": "strong",
        "error": None,
    }
    agentic_generation_result = {
        "status": "accepted",
        "fit_classification": "strong",
        "analysis_input_summary": {"required_skills": ["SQL"]},
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": []},
        "structured_cv_initial": {"sections": {"summary": {"content": ["Grounded summary"]}}},
        "validation_initial": {
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "deterministic_grounding_violations": [],
            "semantic_grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
            "support_source_summary": {},
        },
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": {"sections": {"header": {"name": "Test Candidate"}}},
        "markdown_final": "# Test Candidate\n## Summary\nGrounded summary",
        "error": None,
    }

    with patch(
        "fitcv.pipeline.run_agentic_cv_analysis",
        create=True,
        return_value=agentic_analysis_result,
    ) as mock_agentic_analysis, patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
        return_value=agentic_generation_result,
    ) as mock_agentic_generation:
        result = run_pipeline("data/sample_jobs.json", config_path="config/env.yaml", run_id="late-stage-agentic")

    mock_agentic_analysis.assert_called_once()
    mock_agentic_generation.assert_called_once()
    mock_generate_cv.assert_not_called()
    assert result["cv_generation_debug_records"][0]["status"] == "accepted"
    assert result["cv_generation_debug_records"][0]["markdown_final"].startswith("# Test Candidate")
    stage_artifacts = result["stage_transition_artifacts"]["stages"]
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["late_stage_mode"] == "agentic"
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["agentic_late_stage_enabled"] is True
    assert stage_artifacts["cv_analysis"]["late_stage_mode"]["agentic_status"] == "completed"
    assert stage_artifacts["cv_generation"]["late_stage_mode"]["late_stage_mode"] == "agentic"


@patch("fitcv.agentic_cv_generation.generate_cv")
def test_generate_from_analysis_uses_fitcv_langgraph_live_provider_when_env_present(
    mock_generate_cv: MagicMock,
) -> None:
    analysis_record = _minimal_analysis_record()
    profile = _minimal_profile()
    config = _minimal_config()
    config["cv"]["agentic_late_stage"]["enabled"] = True
    fake_state = {
        "final_result": {
            "status": "accepted",
            "comparison_output": {
                "draft": {
                    "summary": "Grounded summary",
                    "experience": [],
                    "skills": ["SQL"],
                }
            },
            "comparison_validation": {
                "status": "accepted",
                "failure_category": None,
                "missing_sections": [],
                "placeholder_paths": [],
                "unsupported_claim_ids": [],
            },
        },
        "repair_attempts": [],
    }

    with patch(
        "fitcv.agentic_cv_generation.run_cv_generation_from_analysis",
        create=True,
        return_value=fake_state,
    ) as mock_langgraph_run, patch(
        "fitcv.agentic_cv_generation.load_live_provider_config_from_env",
        create=True,
        return_value=object(),
    ):
        result = generate_from_analysis(analysis_record, profile, config)

    mock_langgraph_run.assert_called_once()
    mock_generate_cv.assert_not_called()
    assert result["status"] == "accepted"
