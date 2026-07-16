"""
@meta
type: test
scope: integration
domain: cv_generation
covers:
  - canonical CV-analysis pipeline routing and late-stage generation adapters
excludes:
  - live provider network calls
  - persistent storage integration
tags:
  - fast
  - ci-safe
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from fitcv.pipeline import run_pipeline
from fitcv.agentic_cv_generation import (
    _LIVE_TRACE_DEBUG_ENV_KEYS,
    _backfill_required_sections_from_profile,
    _shallow_section_repair_targets,
    build_cv_generation_input_fingerprint,
    generate_from_analysis,
    transition_cv_generation_persistence_failed,
)


def _minimal_config() -> dict:
    return {
        "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        "pipeline": {
            "vector_search_top_n": 2,
            "ai_score_top_n": 2,
            "final_top_n": 2,
            "evidence_top_k": 3,
        },
        "ranking_policy": {"policy_version": "ranking-v2"},
        "decision_learning_policy": {
            "domain_id": "ranking_v1",
            "inverse_optimization": {
                "learned_alpha": 0.05,
                "preference_vector_norm_bound": 1.0,
            },
        },
        "cv": {
            "generation": {
                "model": "cx/gpt-5.4-mini",
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
        "cv_generation_model": "cx/gpt-5.4-mini",
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
        "certifications": [],
        "languages": [],
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


def _minimal_structured_cv() -> dict:
    return {
        "schema_version": "structured_cv.v1",
        "preset": "europass",
        "locale": "en",
        "job_url": "https://example.com/1",
        "fit_classification": "strong",
        "target_role": "Data Engineer",
        "sections": {
            "header": {
                "name": "Test Candidate",
                "title": "Data Engineer",
                "location": None,
                "contact": {"email": None, "phone": None, "linkedin": None},
            },
            "summary": {"text": "Grounded summary"},
            "experience": [
                {
                    "role": "Data Engineer",
                    "company": "ACME",
                    "start": None,
                    "end": None,
                    "location": None,
                    "bullets": ["Built grounded reporting workflows."],
                }
            ],
            "projects": [],
            "education": [],
            "skills": {"groups": [{"label": "Core", "items": ["SQL", "Python"]}]},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

def _minimal_runtime_evidence(
    *,
    adapter: str = "openai_compatible",
    runtime_path: str = "fitcv_llm_openai_compatible",
    provider: str = "openai",
    model: str = "cx/gpt-5.5",
    response_id: str = "resp-1",
) -> dict:
    return {
        "contract_version": "llm_runtime_evidence_v1",
        "status": "succeeded",
        "provenance": {
            "adapter": adapter,
            "runtime_path": runtime_path,
            "provider": provider,
            "model": model,
            "routing_part": "cv_generation_structured_write",
            "wire_api": "responses",
            "response_id": response_id,
            "attempt_count": 1,
        },
        "failure": None,
    }


def _minimal_runtime_observation(*, invocation_index: int = 1, **evidence_kwargs: str) -> dict:
    return {
        "contract_version": "llm_runtime_observation_v1",
        "scope_key": "https://example.com/1",
        "input_index": 0,
        "invocation_index": invocation_index,
        "evidence": _minimal_runtime_evidence(**evidence_kwargs),
    }


def _minimal_cv_generation_trace() -> dict:
    return {
        "trace_schema_version": "stage_execution_trace_record_v1",
        "trace_family": "stage_execution_trace",
        "step_id": "cv_generation",
        "trace_status": "completed",
        "trace_metadata": {
            "prompt_contract": "fitcv_structured_generation_prompt",
            "template_path": "src/fitcv/prompts/templates/europass.md",
            "response_schema_name": "fitcv_structured_cv_document",
        },
        "attempts": [
            {
                "attempt_index": 1,
                "provider_status": "accepted",
                "attempt_type": "initial_generation",
                "input_character_count": 512,
                "input_item_count": 1,
            }
        ],
        "input_summary": {"attempt_count": 1, "input_item_count": 1},
        "output_summary": {"accepted_output_present": True, "final_status": "accepted"},
        "validation_summary": {
            "initial_valid": True,
            "final_valid": True,
            "initial_missing_fields": [],
            "final_missing_fields": [],
            "violation_count": 0,
            "warning_count": 0,
        },
        "repair_summary": {
            "repair_attempted": False,
            "repair_attempt_count": 0,
            "repair_targets": [],
        },
        "error_summary": None,
    }


def test_shallow_section_repair_targets_flags_context_only_projects() -> None:
    structured_cv = _minimal_structured_cv()
    structured_cv["sections"]["projects"] = [
        {
            "name": "Project A",
            "context": "2022-06 - 2022-10",
            "bullets": [],
        }
    ]
    assert _shallow_section_repair_targets(structured_cv) == ["projects"]

def test_shallow_section_repair_targets_flags_empty_experience_bullets() -> None:
    structured_cv = _minimal_structured_cv()
    structured_cv["sections"]["experience"][0]["bullets"] = []
    assert _shallow_section_repair_targets(structured_cv) == ["experience"]

def test_backfill_required_sections_from_profile_populates_missing_required_sections() -> None:
    profile = _minimal_profile()
    profile["projects"] = [{"name": "FitCV", "highlights": ["Built CV-job matching workflow."]}]
    structured = _minimal_structured_cv()
    structured["sections"]["skills"] = {"groups": []}
    structured["sections"]["experience"] = []
    structured["sections"]["projects"] = []

    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv=structured,
        profile=profile,
        missing_sections=["Skills", "Experience", "Projects"],
    )

    assert repaired is not None
    assert set(repaired_keys) == {"skills", "experience", "projects"}
    assert repaired["sections"]["skills"]["groups"][0]["items"]
    assert repaired["sections"]["experience"]
    assert repaired["sections"]["projects"]


@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_effective_concurrency_for_enrich_and_ranking_events(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_raw_jobs: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_profile: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict | None = None) -> None:
            self.events.append((stage, level, message, payload))

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("stage_runtime", {})
    config["stage_runtime"]["enrich"] = {"concurrency": 2, "batch_size": 10}
    config["stage_runtime"]["ranking"] = {"concurrency": 3, "sleep_secs": 0.0}
    reporter = _Reporter()

    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_normalize.return_value = [job]
    mock_enrich.return_value = [job]
    mock_load_run_structured.return_value = [job]
    mock_load_structured.return_value = [job]
    mock_load_profile.return_value = profile
    mock_apply_rule_filters.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_run_vector_search.return_value = {"production_rows": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]}
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.85, "fit_label": "strong"}]
    ranked_job = {
        **job,
        "title": "Data Engineer",
        "fit_label": "strong",
        "fit_label_source": "reranker",
        "shortlist_origin": "vector_search",
    }
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]

    with patch.dict("os.environ", {"FITCV_ENRICH_HEARTBEAT_EVENTS": ""}, clear=False):
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="timeline-concurrency-check",
            stop_after_stage="ranking",
            reporter=reporter,
        )

    enrich_heartbeat_event = next(event for event in reporter.events if event[0] == "enrich_heartbeat")
    assert enrich_heartbeat_event[3] is not None
    assert enrich_heartbeat_event[3]["configured_concurrency"] == 2
    assert enrich_heartbeat_event[3]["enrich_concurrency_effective"] == 1
    ai_score_event = next(event for event in reporter.events if event[0] == "layer3_ai_score")
    assert ai_score_event[3] is not None
    assert ai_score_event[3]["output_snapshot"]["configured_concurrency"] == 3
    assert ai_score_event[3]["output_snapshot"]["ranking_concurrency_effective"] == 1
    ranking_event = next(event for event in reporter.events if event[0] == "layer3_ranking")
    assert ranking_event[3] is not None
    assert ranking_event[3]["output_snapshot"]["configured_concurrency"] == 3
    assert ranking_event[3]["output_snapshot"]["ranking_concurrency_effective"] == 1

@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_agentic_late_stage_path_under_hard_flip(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_raw_jobs: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_profile: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
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
    mock_run_vector_search.return_value = {"production_rows": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]}
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.85, "fit_label": "strong"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
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

    analysis_record = {
        "status": "ready_for_generation",
        "job_url": ranked_job["job_url"],
        "fit_classification": "strong",
        "analysis_input_summary": {"job_url": ranked_job["job_url"]},
        "evidence_used": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_selection_summary": {"selected_evidence_ids": ["exp-1"], "selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": []},
    }

    with patch("fitcv.pipeline.analyze_ranked_job", create=True, return_value=analysis_record) as mock_agentic_analysis, patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
        return_value={
            "status": "accepted",
            "fit_classification": "strong",
            "analysis_input_summary": {},
            "evidence_used": analysis_record["evidence_used"],
            "evidence_selection_summary": analysis_record["evidence_selection_summary"],
            "gap_summary": analysis_record["gap_summary"],
            "structured_cv_initial": _minimal_structured_cv(),
            "validation_initial": {"valid": True, "missing_sections": []},
            "repair_attempt": {"performed": False, "missing_sections": []},
            "structured_cv_final": _minimal_structured_cv(),
            "markdown_final": "# Test Candidate\n## Summary\nGrounded summary",
            "llm_runtime_observations": [_minimal_runtime_observation(model="cx/gpt-5.2")],
            "cv_generation_trace": _minimal_cv_generation_trace(),
            "error": None,
        },
    ) as mock_agentic_generation:
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="late-stage-default")

    mock_agentic_analysis.assert_called_once()
    mock_agentic_generation.assert_called_once()
    mock_generate_cv.assert_not_called()
    stage_artifacts = result["stage_transition_artifacts"]["stages"]
    assert "late_stage_mode" not in stage_artifacts["cv_analysis"]
    assert "late_stage_mode" not in stage_artifacts["cv_generation"]
    assert stage_artifacts["cv_analysis"]["llm_runtime_summary"]["calls_total"] == 0
    assert stage_artifacts["cv_generation"]["llm_runtime_summary"]["calls_total"] == 1


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_routes_through_agentic_late_stage_when_enabled(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_raw_jobs: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_profile: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
    mock_store_cv_version: MagicMock,
) -> None:
    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict | None = None) -> None:
            self.events.append((stage, level, message, payload))

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    config["cv"]["agentic_late_stage"]["enabled"] = True
    reporter = _Reporter()
    from concurrent.futures import wait as real_wait

    wait_call_count = 0

    def _wait_with_initial_timeout(futures: Any, *, timeout: float, return_when: Any) -> Any:
        nonlocal wait_call_count
        wait_call_count += 1
        if wait_call_count == 1:
            return set(), set(futures)
        return real_wait(futures, timeout=timeout, return_when=return_when)

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
    mock_run_vector_search.return_value = {"production_rows": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]}
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.85, "fit_label": "strong"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
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
        "llm_runtime_observations": [_minimal_runtime_observation()],
        "cv_generation_trace": _minimal_cv_generation_trace(),
    }

    with patch(
        "fitcv.pipeline.analyze_ranked_job",
        create=True,
        return_value=agentic_analysis_result,
    ) as mock_agentic_analysis, patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
        return_value=agentic_generation_result,
    ) as mock_agentic_generation, patch(
        "fitcv.pipeline.wait",
        side_effect=_wait_with_initial_timeout,
    ):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="late-stage-agentic",
            reporter=reporter,
        )

    mock_agentic_analysis.assert_called_once()
    mock_agentic_generation.assert_called_once()
    mock_generate_cv.assert_not_called()
    assert result["cv_generation_debug_records"][0]["status"] == "accepted"
    assert result["cv_generation_debug_records"][0]["cv_generation_model"] == "cx/gpt-5.5"
    observation = result["cv_generation_debug_records"][0]["llm_runtime_observations"][0]
    assert observation["evidence"]["provenance"]["provider"] == "openai"
    assert result["cv_generation_debug_records"][0]["cv_generation_trace"]["trace_status"] == "completed"
    assert result["cv_generation_debug_records"][0]["markdown_final"].startswith("# Test Candidate")
    assert result["cv_generation_trace"]["trace_status"] == "completed"
    assert result["cv_generation_trace"]["trace_family"] == "stage_execution_trace"
    assert result["cv_generation_trace"]["step_id"] == "cv_generation"
    assert result["cv_generation_trace"]["records"][0]["attempts"][0]["provider_status"] == "accepted"
    stage_artifacts = result["stage_transition_artifacts"]["stages"]
    assert "late_stage_mode" not in stage_artifacts["cv_analysis"]
    assert "late_stage_mode" not in stage_artifacts["cv_generation"]
    assert stage_artifacts["cv_analysis"]["llm_runtime_summary"]["calls_total"] == 0
    assert stage_artifacts["cv_generation"]["llm_runtime_summary"]["calls_total"] == 1
    assert stage_artifacts["cv_generation"]["decision_summary"]["cv_generation_model"] == "cx/gpt-5.5"
    assert stage_artifacts["cv_generation"]["decision_summary"]["cv_generation_provider"] == "openai"
    cv_generation_heartbeat_event = next(
        event for event in reporter.events if event[0] == "cv_generation_heartbeat"
    )
    assert cv_generation_heartbeat_event[3] is not None
    assert cv_generation_heartbeat_event[3]["pending_items"] == 1
    assert cv_generation_heartbeat_event[3]["cv_generation_concurrency_effective"] == 1
    cv_generation_started_event = next(event for event in reporter.events if event[0] == "layer4_cv_generation_started")
    assert cv_generation_started_event[3]["output_snapshot"]["configured_concurrency"] >= 1
    assert cv_generation_started_event[3]["output_snapshot"]["cv_generation_concurrency_effective"] >= 1
    assert "started_at" in cv_generation_started_event[3]["output_snapshot"]
    assert "worker_slot" in cv_generation_started_event[3]["output_snapshot"]
    cv_analysis_invoked_event = next(event for event in reporter.events if event[0] == "layer4_cv_analysis_invoked")
    assert cv_analysis_invoked_event[3]["output_snapshot"]["ranked_jobs"] == 1
    assert cv_analysis_invoked_event[3]["output_snapshot"]["configured_concurrency"] == 1
    assert cv_analysis_invoked_event[3]["output_snapshot"]["cv_analysis_concurrency_effective"] == 1
    cv_generation_invoked_event = next(event for event in reporter.events if event[0] == "layer4_cv_generation_invoked")
    assert cv_generation_invoked_event[3]["provenance"]["cv_generation_model"] == "cx/gpt-5.5"
    assert cv_generation_invoked_event[3]["output_snapshot"]["configured_concurrency"] == 1
    assert cv_generation_invoked_event[3]["output_snapshot"]["cv_generation_concurrency_effective"] == 1
    cv_generation_result_event = next(event for event in reporter.events if event[0] == "layer4_cv_generation_result")
    assert cv_generation_result_event[3]["output_snapshot"]["cv_generation_concurrency_effective"] >= 1
    assert "started_at" in cv_generation_result_event[3]["output_snapshot"]
    assert "finished_at" in cv_generation_result_event[3]["output_snapshot"]


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_marks_review_required_and_skips_persist_when_agentic_gate_triggers(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_raw_jobs: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_profile: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
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
    ranked_job = {**job, "fit_label": "stretch", "fit_label_source": "reranker", "shortlist_origin": "vector_search"}
    mock_run_vector_search.return_value = {"production_rows": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]}
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.7, "fit_label": "stretch"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
    mock_run_all_validations.return_value = {"valid": True, "missing_sections": []}

    agentic_analysis_result = {
        "status": "ready_for_generation",
        "analysis_input_fingerprint": "agentic::fingerprint",
        "evidence_payload": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": ["Python"]},
        "fit_classification": "stretch",
        "requirement_coverage": [{"requirement": "Python", "support_strength": "unsupported"}],
        "section_confidence_hints": {"experience": "low"},
        "do_not_claim": ["Python"],
        "error": None,
    }
    agentic_generation_result = {
        "status": "review_required",
        "fit_classification": "stretch",
        "analysis_input_summary": {"required_skills": ["SQL", "Python"]},
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": ["Python"]},
        "structured_cv_initial": {"sections": {"summary": {"content": ["Grounded summary"]}}},
        "validation_initial": {"valid": True, "missing_sections": []},
        "validation": {"valid": True, "missing_sections": []},
        "review_required_reason_code": "low_confidence_sections",
        "validation_evidence_fingerprint": "validation::low-confidence",
        "outcome_reason": {
            "stage": "review",
            "code": "low_confidence_sections",
            "message": "Low confidence sections: experience",
        },
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": {"sections": {"header": {"name": "Test Candidate"}}},
        "markdown_final": "# Test Candidate\n## Summary\nGrounded summary",
        "error": None,
        "llm_runtime_observations": [_minimal_runtime_observation(model="cx/gpt-5.2")],
        "cv_generation_trace": _minimal_cv_generation_trace(),
    }

    with patch("fitcv.pipeline.analyze_ranked_job", create=True, return_value=agentic_analysis_result), patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
        return_value=agentic_generation_result,
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="late-stage-agentic-review")

    assert result["cvs_generated"] == 0
    assert result["cv_generation_debug_records"][0]["status"] == "review_required"
    assert result["cv_generation_debug_records"][0]["error"] is None
    assert result["cv_generation_debug_records"][0]["outcome_reason"]["stage"] == "review"
    assert "Low confidence sections" in str(result["cv_generation_debug_records"][0]["outcome_reason"]["message"])
    mock_store_cv_version.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_marks_review_required_from_markdown_quality_flags(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_normalize: MagicMock,
    mock_load_raw_jobs: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_structured: MagicMock,
    mock_load_structured: MagicMock,
    mock_load_profile: MagicMock,
    mock_load_candidate_profile: MagicMock,
    mock_apply_rule_filters: MagicMock,
    mock_store_filter_results: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_run_vector_search: MagicMock,
    mock_run_ai_scoring: MagicMock,
    mock_build_ranking_features: MagicMock,
    mock_rank_jobs: MagicMock,
    mock_store_final_ranking: MagicMock,
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
    ranked_job = {**job, "fit_label": "stretch", "fit_label_source": "reranker", "shortlist_origin": "vector_search"}
    mock_run_vector_search.return_value = {"production_rows": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]}
    mock_run_ai_scoring.return_value = [{"job_url": job["job_url"], "ai_score": 0.7, "fit_label": "stretch"}]
    mock_build_ranking_features.return_value = [ranked_job]
    mock_rank_jobs.return_value = [ranked_job]
    mock_run_all_validations.return_value = {"valid": True, "missing_sections": []}

    agentic_analysis_result = {
        "status": "ready_for_generation",
        "analysis_input_fingerprint": "agentic::fingerprint",
        "evidence_payload": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": ["Python"]},
        "fit_classification": "stretch",
        "requirement_coverage": [{"requirement": "Python", "support_strength": "supported"}],
        "section_confidence_hints": {"experience": "high"},
        "do_not_claim": [],
        "error": None,
    }
    agentic_generation_result = {
        "status": "review_required",
        "fit_classification": "stretch",
        "analysis_input_summary": {"required_skills": ["SQL", "Python"]},
        "evidence_used": [{"evidence_id": "exp-1"}],
        "evidence_selection_summary": {"selected_evidence_count": 1},
        "gap_summary": {"matched": ["SQL"], "missing": ["Python"]},
        "structured_cv_initial": {"sections": {"summary": {"content": ["Grounded summary"]}}},
        "validation_initial": {
            "valid": True,
            "missing_sections": [],
            "markdown_quality_review_flags": ["Experience section appears shallow (fewer than 2 bullets)."],
            "markdown_quality_blocking_issues": [],
        },
        "validation": {
            "valid": True,
            "missing_sections": [],
            "markdown_quality_review_flags": ["Experience section appears shallow (fewer than 2 bullets)."],
            "markdown_quality_blocking_issues": [],
        },
        "review_required_reason_code": "markdown_structure_violation",
        "validation_evidence_fingerprint": "validation::markdown-review",
        "outcome_reason": {
            "stage": "review",
            "code": "markdown_structure_violation",
            "message": "Markdown quality requires review: Experience section appears shallow (fewer than 2 bullets).",
        },
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": {"sections": {"header": {"name": "Test Candidate"}}},
        "markdown_final": "# Test Candidate\n## Summary\nGrounded summary",
        "error": None,
        "llm_runtime_observations": [_minimal_runtime_observation(model="cx/gpt-5.2")],
        "cv_generation_trace": _minimal_cv_generation_trace(),
    }

    with patch("fitcv.pipeline.analyze_ranked_job", create=True, return_value=agentic_analysis_result), patch(
        "fitcv.pipeline.run_agentic_cv_generation",
        create=True,
        return_value=agentic_generation_result,
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="late-stage-agentic-markdown-review")

    assert result["cvs_generated"] == 0
    assert result["cv_generation_debug_records"][0]["status"] == "review_required"
    assert result["cv_generation_debug_records"][0]["error"] is None
    assert result["cv_generation_debug_records"][0]["outcome_reason"]["stage"] == "review"
    assert "Markdown quality requires review" in str(result["cv_generation_debug_records"][0]["outcome_reason"]["message"])
    mock_store_cv_version.assert_not_called()




@patch("fitcv.agentic_cv_generation.generate_cv")
def test_generate_from_analysis_direct_path_has_canonical_trace(
    mock_generate_cv: MagicMock,
) -> None:
    analysis_record = _minimal_analysis_record()
    profile = _minimal_profile()
    config = _minimal_config()
    config["cv"]["agentic_late_stage"]["enabled"] = True

    mock_generate_cv.return_value = {
        "structured_cv": _minimal_structured_cv(),
        "markdown": "# Test Candidate\n## Summary\nGrounded summary",
        "llm_runtime_evidence": _minimal_runtime_evidence(
            adapter="direct",
            runtime_path="fitcv_llm_direct",
            provider="openai_compatible",
            model="cx/gpt-5.4-mini",
        ),
    }

    result = generate_from_analysis(analysis_record, profile, config)

    assert result["status"] in {"accepted", "validation_failed"}
    observation = result["llm_runtime_observations"][0]
    assert observation["evidence"]["provenance"]["adapter"] == "direct"
    assert observation["evidence"]["provenance"]["runtime_path"] == "fitcv_llm_direct"
    trace = result["cv_generation_trace"]
    assert trace["trace_status"] == "completed"
    assert trace["trace_family"] == "stage_execution_trace"
    assert trace["step_id"] == "cv_generation"
    assert trace["input_summary"]["attempt_count"] == len(trace["attempts"])
    assert trace["attempts"]
    assert all(attempt["provider_status"] == "accepted" for attempt in trace["attempts"])
    assert all(attempt["accepted_output_present"] is True for attempt in trace["attempts"])
    assert all(
        attempt["llm_runtime_evidence"]["provenance"]["adapter"] == "direct"
        for attempt in trace["attempts"]
    )
    assert trace["validation_summary"]["final_valid"] is (result["status"] == "accepted")



def test_cv_generation_fingerprint_ignores_mode_labels_and_mutable_job_url() -> None:
    analysis_record = _minimal_analysis_record()
    analysis_record["analysis_input_fingerprint"] = "analysis::stable"
    config = _minimal_config()

    baseline = build_cv_generation_input_fingerprint(analysis_record, config)

    analysis_record["job_url"] = "https://example.com/moved"
    analysis_record["job_snapshot"]["job_url"] = "https://example.com/moved"
    config["cv"]["agentic_late_stage"]["enabled"] = True
    toggled = build_cv_generation_input_fingerprint(analysis_record, config)

    assert toggled == baseline


@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
def test_generate_from_analysis_returns_complete_canonical_result(
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
) -> None:
    analysis_record = _minimal_analysis_record()
    analysis_record["raw_job_fingerprint"] = "raw::job"
    analysis_record["analysis_input_fingerprint"] = "analysis::input"
    config = _minimal_config()
    mock_generate_cv.return_value = {
        "structured_cv": _minimal_structured_cv(),
        "markdown": "# Test Candidate\n## Experience\nBuilt grounded reporting workflows.\n## Skills\nSQL",
        "llm_runtime_evidence": _minimal_runtime_evidence(
            adapter="direct",
            runtime_path="fitcv_llm_direct",
            provider="openai_compatible",
            model="cx/gpt-5.4-mini",
        ),
    }
    mock_run_all_validations.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }

    result = generate_from_analysis(analysis_record, _minimal_profile(), config)

    assert result["status"] == "accepted"
    assert result["raw_job_fingerprint"] == "raw::job"
    assert result["analysis_input_fingerprint"] == "analysis::input"
    assert result["cv_generation_input_fingerprint"]
    assert result["cv_generation_input_components"]["schema_version"] == "cv_generation_input_fingerprint_v2"
    assert result["cv_generation_reuse_status"] == "fresh_compute"
    assert result["reuse_decision"]["decision"] == "fresh_compute"
    assert result["review_required_reason_code"] is None
    assert result["validation_evidence_fingerprint"]
    observation = result["llm_runtime_observations"][0]
    provenance = observation["evidence"]["provenance"]
    assert provenance["routing_part"] == "cv_generation_structured_write"
    assert provenance["adapter"] == "direct"
    assert provenance["wire_api"]


@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
def test_generate_from_analysis_emits_review_required_as_outcome(
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
) -> None:
    analysis_record = _minimal_analysis_record()
    analysis_record["analysis_input_fingerprint"] = "analysis::review"
    analysis_record["do_not_claim"] = ["Python"]
    analysis_record["requirement_coverage"] = [
        {"requirement": "Python", "support_strength": "unsupported"},
    ]
    mock_generate_cv.return_value = {
        "structured_cv": _minimal_structured_cv(),
        "markdown": "# Test Candidate\n## Experience\nBuilt grounded reporting workflows.\n## Skills\nSQL",
    }
    mock_run_all_validations.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }

    result = generate_from_analysis(analysis_record, _minimal_profile(), _minimal_config())

    assert result["status"] == "review_required"
    assert result["review_required_reason_code"] == "unsupported_requirement_gap"
    assert result["outcome_reason"]["stage"] == "review"
    assert result["outcome_reason"]["code"] == "unsupported_requirement_gap"
    assert result["error"] is None
    assert result["structured_cv_final"] is not None
    assert result["markdown_final"]
    assert result["validation_evidence_fingerprint"]


@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
def test_generate_from_analysis_reuses_exact_canonical_result(
    mock_generate_cv: MagicMock,
    mock_run_all_validations: MagicMock,
) -> None:
    analysis_record = _minimal_analysis_record()
    analysis_record["analysis_input_fingerprint"] = "analysis::reuse"
    config = _minimal_config()
    validation = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }
    mock_run_all_validations.return_value = validation
    mock_generate_cv.return_value = {
        "structured_cv": _minimal_structured_cv(),
        "markdown": "# Test Candidate\n## Experience\nBuilt grounded reporting workflows.\n## Skills\nSQL",
    }

    fresh = generate_from_analysis(analysis_record, _minimal_profile(), config)
    mock_generate_cv.reset_mock()
    reused = generate_from_analysis(
        analysis_record,
        _minimal_profile(),
        config,
        reusable_record={**fresh, "version_id": "cv-version-1"},
    )

    mock_generate_cv.assert_not_called()
    assert reused["status"] == "accepted"
    assert reused["cv_generation_reuse_status"] == "reused_exact_match"
    assert reused["reused_cv_version_id"] == "cv-version-1"
    assert reused["structured_cv_final"] == fresh["structured_cv_final"]
    assert reused["markdown_final"] == fresh["markdown_final"]


def test_persistence_failure_transition_preserves_accepted_artifacts() -> None:
    accepted = {
        "status": "accepted",
        "structured_cv_final": _minimal_structured_cv(),
        "markdown_final": "# Test Candidate",
        "validation": {"valid": True},
        "validation_evidence_fingerprint": "validation::accepted",
    }

    failed = transition_cv_generation_persistence_failed(
        accepted,
        message="BigQuery insert failed",
    )

    assert failed["status"] == "persistence_failed"
    assert failed["structured_cv_final"] == accepted["structured_cv_final"]
    assert failed["markdown_final"] == accepted["markdown_final"]
    assert failed["validation"] == accepted["validation"]
    assert failed["error"] == {
        "stage": "persistence",
        "code": "persistence_failed",
        "message": "BigQuery insert failed",
    }



def test_live_trace_debug_env_keys_use_repo_native_vocabulary() -> None:
    assert _LIVE_TRACE_DEBUG_ENV_KEYS == (
        "FITCV_LLM_DEBUG_LIVE",
        "FITCV_LLM_DEBUG_LIVE_DUMP_PATH",
    )





def test_agentic_cv_generation_exposes_no_external_langgraph_runtime() -> None:
    from fitcv import agentic_cv_generation

    assert not hasattr(agentic_cv_generation, "_discover_fitcv_langgraph_repo_root")
    assert not hasattr(agentic_cv_generation, "_build_fitcv_langgraph_env_values")
    assert not hasattr(agentic_cv_generation, "_live_runtime_provenance_or_none")
    assert not hasattr(agentic_cv_generation, "_langgraph_runtime_adapter")
    assert not hasattr(agentic_cv_generation, "_generate_cv_with_live_provider")
