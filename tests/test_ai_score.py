"""Tests for fitcv.ai_score — all pure unit tests (no cloud calls)."""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import fitcv.ai_score as ai_score_module
from fitcv.ai_score import (
    RankingInputBudgetExceeded,
    RankingInputIncomplete,
    build_ai_score_contract_fingerprint,
    build_ranking_input_diagnostics,
    build_ranking_job_input,
    build_ranking_request,
    build_scoring_prompt,
    parse_score_response,
    run_ai_scoring,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_VALID_RESPONSE = json.dumps({
    "ai_score": 0.85,
    "fit_label": "strong",
    "score_reasoning": "Candidate has SQL, Python, and BigQuery experience matching JD.",
    "matched_strengths": ["SQL", "Python", "BigQuery"],
    "key_risks": [],
})


def test_ranking_ai_prompt_v2_requests_score_without_fit_label() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )

    assert '"ai_score"' in prompt
    assert "fit_label" not in prompt
    assert "strong_threshold" not in prompt
    assert "stretch_threshold" not in prompt


def test_parse_score_response_keeps_legacy_label_diagnostic_only() -> None:
    result = parse_score_response(_VALID_RESPONSE)

    assert "fit_label" not in result
    assert result["legacy_model_fit_label"] == "strong"


def test_ai_score_contract_fingerprint_excludes_fit_thresholds() -> None:
    base = {
        "ai_score_model": "cx/test-model",
        "prompts": {"ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v2"}}},
    }
    first = build_ai_score_contract_fingerprint(
        {**base, "fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}
    )
    second = build_ai_score_contract_fingerprint(
        {**base, "fit_label_thresholds": {"strong": 0.9, "stretch": 0.8}}
    )

    assert first == second
    assert "strong_threshold" not in first["payload"]
    assert "stretch_threshold" not in first["payload"]


# ── build_scoring_prompt ──────────────────────────────────────────────────────

def test_build_scoring_prompt_includes_jd_summary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="Data Engineer role requiring SQL, Python",
        candidate_summary="3 years experience in SQL, Python, BigQuery",
        top_evidence=["Built GA4 pipeline reducing latency 40%"],
    )
    assert "Data Engineer" in prompt
    assert "SQL" in prompt


def test_build_scoring_prompt_includes_candidate_summary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="3 years experience in SQL, Python, BigQuery",
        top_evidence=[],
    )
    assert "BigQuery" in prompt or "3 years" in prompt


def test_build_scoring_prompt_includes_score_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "score" in prompt.lower()


def test_build_scoring_prompt_includes_rubric_range() -> None:
    """Rubric range 0.0-1.0 must appear in prompt."""
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "0.0" in prompt or "1.0" in prompt


def test_build_scoring_prompt_excludes_fit_labels() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "fit_label" not in prompt


def test_build_scoring_prompt_includes_top_evidence() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=["Built GA4 pipeline reducing latency 40%"],
    )
    assert "GA4" in prompt


def test_build_scoring_prompt_contains_required_skills_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="mid-level engineer",
        top_evidence=[],
    )
    assert "required-skill" in prompt.lower()


def test_build_scoring_prompt_makes_preferences_secondary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="Analytics role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "secondary" in prompt.lower()
    assert "preferences" in prompt.lower()


def test_build_scoring_prompt_contains_seniority_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="mid-level engineer",
        top_evidence=[],
    )
    assert "seniority" in prompt.lower()


def test_build_scoring_prompt_specifies_json_output() -> None:
    """Prompt must tell model to return JSON only, no prose."""
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "json" in prompt.lower()


def test_build_scoring_prompt_ignores_ranking_threshold_config() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
        config={"fit_label_thresholds": {"strong": 0.8, "stretch": 0.55}},
    )
    assert "0.8" not in prompt
    assert "0.55" not in prompt


def test_build_scoring_prompt_empty_evidence_does_not_crash() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# ── parse_score_response ──────────────────────────────────────────────────────

def test_parse_score_response_valid_json() -> None:
    result = parse_score_response(_VALID_RESPONSE)
    assert result["ai_score"] == 0.85
    assert result["legacy_model_fit_label"] == "strong"
    assert result["matched_strengths"] == ["SQL", "Python", "BigQuery"]
    assert isinstance(result["key_risks"], list)


def test_parse_score_response_returns_all_required_keys() -> None:
    result = parse_score_response(_VALID_RESPONSE)
    assert {
        "ai_score",
        "legacy_model_fit_label",
        "score_reasoning",
        "matched_strengths",
        "key_risks",
    } <= set(result.keys())


def test_parse_score_response_score_clamped_below_upper_bound() -> None:
    raw = json.dumps({
        "ai_score": 1.5, "fit_label": "strong",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["ai_score"] is None
    assert result["score_status"] == "invalid"
    assert result["failure_code"] == "invalid_ai_score"


def test_parse_score_response_score_clamped_above_lower_bound() -> None:
    raw = json.dumps({
        "ai_score": -0.5, "fit_label": "skip",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["ai_score"] is None
    assert result["score_status"] == "invalid"
    assert result["failure_code"] == "invalid_ai_score"


def test_parse_score_response_bad_fit_label_dropped() -> None:
    raw = json.dumps({
        "ai_score": 0.3, "fit_label": "maybe",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["legacy_model_fit_label"] is None


def test_parse_score_response_malformed_json_is_unscored() -> None:
    result = parse_score_response("not json at all")
    assert result["ai_score"] is None
    assert result["score_status"] == "invalid"
    assert result["failure_code"] == "malformed_json"
    assert result["legacy_model_fit_label"] is None
    assert result["score_reasoning"] == "Scoring response parse failure: malformed_json"
    assert result["parser_status"] == "malformed_json"
    assert result["matched_strengths"] == []
    assert result["key_risks"] == []


def test_parse_score_response_markdown_fenced_json() -> None:
    """Model sometimes wraps response in ```json ... ``` fences."""
    raw = '```json\n{"ai_score": 0.75, "fit_label": "strong", "score_reasoning": "good", "matched_strengths": [], "key_risks": []}\n```'
    result = parse_score_response(raw)
    assert result["ai_score"] == 0.75
    assert result["legacy_model_fit_label"] == "strong"


def test_parse_score_response_does_not_derive_fit_label() -> None:
    raw = json.dumps({
        "ai_score": 0.8,
        "score_reasoning": "good match",
        "matched_strengths": ["SQL"],
        "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["legacy_model_fit_label"] is None


@pytest.mark.parametrize(
    ("payload", "failure_code"),
    [
        ({}, "missing_ai_score"),
        ({"ai_score": None}, "missing_ai_score"),
        ({"ai_score": "NaN"}, "invalid_ai_score"),
        ({"ai_score": True}, "invalid_ai_score"),
    ],
)
def test_parse_score_response_invalid_scores_are_not_fit(payload: dict[str, Any], failure_code: str) -> None:
    result = parse_score_response(json.dumps(payload))
    assert result["ai_score"] is None
    assert result["score_status"] == "invalid"
    assert result["failure_code"] == failure_code


def test_parse_score_response_preserves_valid_zero() -> None:
    result = parse_score_response(json.dumps({
        "ai_score": 0.0,
        "score_reasoning": "no match",
        "matched_strengths": [],
        "key_risks": ["missing experience"],
    }))
    assert result["ai_score"] == 0.0
    assert result["score_status"] == "valid"
    assert result["failure_code"] is None


def test_build_ranking_job_input_is_bounded_and_uses_supplied_projection() -> None:
    profile = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "_projected_evidence_pool": [
            {"evidence_id": "ev-1", "kind": "experience", "title": "SQL", "text": "Built SQL pipelines."},
        ],
    }
    job = {
        "title": "Data Engineer",
        "required_skills": ["SQL", "Airflow"],
        "years_experience_min": 3,
        "years_experience_max": 6,
    }

    with patch("fitcv.evidence.project_candidate_evidence", side_effect=AssertionError("projection rebuilt")):
        result = build_ranking_job_input(job, profile)

    requirements = json.loads(result["job_requirements"])
    assert requirements["years_experience_min"] == 3
    assert requirements["years_experience_max"] == 6
    assert requirements["skill_coverage"] == {
        "matched": ["SQL"],
        "missing": ["Airflow"],
        "matched_count": 1,
        "required_count": 2,
    }
    assert result["candidate_evidence"][0]["evidence_id"] == "ev-1"


def test_build_ranking_job_input_preserves_mandatory_clause_facts_and_spans() -> None:
    result = build_ranking_job_input(
        {
            "title": "Data Engineer",
            "required_skills": ["Python"],
            "qualifications": ["Bachelor's degree in computer science"],
            "education_requirements": ["Bachelor's degree"],
            "certification_requirements": ["AWS Certified Solutions Architect"],
            "employment_constraints": ["Must be eligible to work in the US"],
            "mandatory_clauses": [{
                "clause_id": "education:1",
                "clause_type": "education",
                "value": "Bachelor's degree in computer science",
                "normalized_value": "bachelor's degree in computer science",
                "required": True,
                "source_span": {"start": 42, "end": 82, "quote": "Bachelor's degree in computer science"},
            }],
        },
        {"skills": [{"name": "Python"}]},
    )

    requirements = json.loads(result["job_requirements"])
    assert requirements["qualifications"] == ["Bachelor's degree in computer science"]
    assert requirements["certification_requirements"] == ["AWS Certified Solutions Architect"]
    assert requirements["employment_constraints"] == ["Must be eligible to work in the US"]
    assert requirements["mandatory_clauses"][0]["source_span"]["quote"] == "Bachelor's degree in computer science"
    assert "mandatory:education:1" in result["contract_metadata"]["requirement_ids"]


def test_fallback_enrichment_requires_retry_even_when_raw_description_exists() -> None:
    ranking_input = build_ranking_job_input(
        {
            "enrich_reuse_status": "enrichment_fallback",
            "description_cleaned": "Requirements: German C1 and AWS certification",
        },
        {"skills": []},
    )

    with pytest.raises(RankingInputIncomplete):
        build_ranking_request(
            {},
            ranking_input["candidate_summary"],
            [],
            {},
            ranking_input=ranking_input,
        )


def test_build_ranking_request_drops_optional_raw_description_before_budget_failure(monkeypatch) -> None:
    monkeypatch.setattr("fitcv.ai_score.RANKING_REQUEST_MAX_CHARS", 3_000)
    ranking_input = build_ranking_job_input(
        {
            "title": "Data Engineer",
            "required_skills": ["Python"],
            "description": "optional context " * 3000,
        },
        {"skills": [{"name": "Python"}]},
    )

    request = build_ranking_request(
        {},
        ranking_input["candidate_summary"],
        [],
        {},
        ranking_input=ranking_input,
    )

    assert "raw_description" not in request["request"].prompt
    assert "job_optional" in request["prompt_truncation_steps"]


def test_job_relevant_late_certification_is_preserved_in_mandatory_facts() -> None:
    required_certification = "AWS Certified Solutions Architect"
    profile = {
        "certifications": [
            {"name": f"Unrelated {index}", "issuer": "Issuer"}
            for index in range(1, 5)
        ] + [{"name": required_certification, "issuer": "Amazon"}],
    }
    ranking_input = build_ranking_job_input(
        {"certification_requirements": [required_certification]},
        profile,
    )

    candidate = json.loads(ranking_input["candidate_summary"])
    assert candidate["certifications"][0]["name"] == required_certification
    assert candidate["mandatory_facts"]["certifications"][0]["name"] == required_certification


def test_late_education_and_certification_match_ordinary_requirement_wording() -> None:
    profile = {
        "education": [
            {"degree": f"Unrelated {index}", "field": "History", "institution": "Example University"}
            for index in range(15)
        ] + [{"degree": "Bachelor of Science", "field": "Computer Science", "institution": "Example University"}],
        "certifications": [
            {"name": f"Unrelated {index}", "issuer": "Issuer"}
            for index in range(15)
        ] + [{"name": "AWS Certified Solutions Architect", "issuer": "Amazon"}],
    }
    ranking_input = build_ranking_job_input(
        {
            "education_requirements": ["Bachelor's degree in Computer Science or a related field"],
            "certification_requirements": ["AWS Certified Solutions Architect certification required"],
        },
        profile,
    )

    candidate = json.loads(ranking_input["candidate_summary"])
    assert candidate["education"][0]["field"] == "Computer Science"
    assert candidate["certifications"][0]["name"] == "AWS Certified Solutions Architect"
    assert candidate["mandatory_facts"]["education"]
    assert candidate["mandatory_facts"]["certifications"]


def test_request_refuses_to_hide_the_only_attributable_evidence() -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )
    requirement = "Mandatory requirement " + ("context " * 700)
    ranking_input = {
        "job_requirements": json.dumps({
            "mandatory_clauses": [{
                "clause_id": "qualification-1",
                "clause_type": "qualification",
                "value": requirement,
                "normalized_value": requirement.casefold(),
                "required": True,
            }],
        }),
        "candidate_summary": "candidate",
        "candidate_evidence": [{
            "evidence_id": "ev-source",
            "title": "Source-backed project",
            "text": "Built the required system.",
            "source_ref": "cv:page-1",
        }],
    }

    with pytest.raises(RankingInputBudgetExceeded):
        build_ranking_request(
            {},
            "candidate",
            [],
            {},
            ranking_input=ranking_input,
            resolved_route=route,
        )


def test_build_ranking_request_preserves_long_mandatory_clause_before_budgeting() -> None:
    requirement = "Bachelor's degree in computer science with German C1 is mandatory for this role."
    quote = requirement + " " + ("Additional context. " * 8)
    job = {
        "mandatory_clauses": [{
            "clause_id": "qualification-1",
            "clause_type": "qualification",
            "value": requirement,
            "normalized_value": requirement.casefold(),
            "required": True,
            "source_span": {"start": 0, "end": len(quote), "quote": quote},
        }],
    }
    ranking_input = build_ranking_job_input(job, {"skills": []})
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )

    request = build_ranking_request(
        job,
        ranking_input["candidate_summary"],
        [],
        {},
        ranking_input=ranking_input,
        resolved_route=route,
    )

    requirements = json.loads(ranking_input["job_requirements"])
    assert requirements["mandatory_clauses"][0]["value"] == requirement
    assert requirements["mandatory_clauses"][0]["source_span"]["quote"] == quote
    assert requirement in request["request"].prompt
    assert quote in request["request"].prompt
    assert request["visibility_manifest"]["mandatory_core_complete"] is True


def test_build_ranking_job_input_preserves_mandatory_skills_before_request_budgeting() -> None:
    from fitcv.ai_score import build_ranking_job_input

    profile = {
        "skills": [{"name": f"Skill {index}"} for index in range(1, 10)],
        "_projected_evidence_pool": [],
    }
    job = {
        "required_skills": [f"Skill {index}" for index in range(1, 10)],
    }

    result = build_ranking_job_input(job, profile)
    requirements = json.loads(result["job_requirements"])

    assert len(requirements["required_skills"]) == 9
    assert len(requirements["skill_coverage"]["matched"]) == 8
    assert requirements["skill_coverage"]["matched_count"] == 9
    assert requirements["skill_coverage"]["required_count"] == 9
    assert requirements["skill_coverage"]["missing"] == []


def test_build_ranking_job_input_preserves_three_project_evidence_items() -> None:
    profile = {
        "skills": [{"name": "SQL"}],
        "_projected_evidence_pool": [
            {
                "evidence_id": f"project-{index}",
                "kind": "project",
                "title": f"Project {index}",
                "text": f"Built project {index} with SQL.",
                "source_section": "projects",
                "skills": ["SQL"],
            }
            for index in range(1, 4)
        ],
    }

    result = build_ranking_job_input({"required_skills": ["SQL"]}, profile)

    assert [item["evidence_id"] for item in result["candidate_evidence"]] == [
        "project-1",
        "project-2",
        "project-3",
    ]


def test_build_ranking_job_input_prioritizes_late_required_technology_skills() -> None:
    profile = {
        "skills": [{"name": f"Skill {index}"} for index in range(1, 10)]
        + [{"name": "agentic ai"}, {"name": "OpenAI"}],
        "_projected_evidence_pool": [
            {
                "evidence_id": "ev-agent",
                "kind": "project_highlight",
                "title": "LightRSI",
                "text": "Built a Claude Code host integration.",
                "parent_title": "LightRSI",
                "organization": "Personal project",
                "scoring_context": "Claude Code host integration and OpenAI-compatible APIs",
                "skills": ["agentic ai", "OpenAI"],
            }
        ],
    }
    job = {
        "required_skills": ["agentic ai"],
        "tech_stack_canonical": ["OpenAI"],
    }

    result = build_ranking_job_input(job, profile)
    requirements = json.loads(result["job_requirements"])

    assert requirements["technology_requirements"] == ["OpenAI"]
    assert requirements["skill_coverage"]["matched_count"] == 1
    assert requirements["skill_coverage"]["required_count"] == 1
    assert json.loads(result["candidate_summary"])["skills"][:2] == ["agentic ai", "OpenAI"]
    assert result["candidate_evidence"][0]["parent_title"] == "LightRSI"
    assert result["candidate_evidence"][0]["skills"] == ["agentic ai", "OpenAI"]


def test_build_ranking_request_serializes_bounded_evidence_context_into_prompt() -> None:
    route = SimpleNamespace(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="test-model",
        timeout_seconds=12.0,
        request_start_interval_secs=0.0,
        auth_mode="env",
        temperature=0.0,
        model_record_id="model-record",
        configuration_revision="config-revision",
    )
    request = build_ranking_request(
        {},
        "candidate",
        [],
        {},
        ranking_input={
            "job_requirements": "OpenAI agent builder",
            "candidate_summary": "candidate",
            "candidate_evidence": [
                {
                    "title": "LightRSI",
                    "parent_title": "LightRSI",
                    "organization": "Personal project",
                    "scoring_context": "Claude Code host integration and OpenAI-compatible APIs",
                    "skills": ["agentic ai", "OpenAI"],
                    "text": "Built the host integration.",
                }
            ],
        },
        resolved_route=route,
    )

    assert "Claude Code host integration" in request["request"].prompt
    assert "OpenAI" in request["request"].prompt


def test_ranking_input_diagnostics_are_bounded_and_track_the_final_request() -> None:
    profile = {
        "skills": [{"name": f"Skill {index}"} for index in range(1, 10)],
        "_projected_evidence_pool": [
            {"evidence_id": "ev-1", "parent_title": "Project One", "text": "One"},
            {"evidence_id": "ev-2", "parent_title": "Project Two", "text": "Two"},
            {"evidence_id": "ev-3", "parent_title": "Project Three", "text": "Three"},
        ],
    }
    ranking_input = build_ranking_job_input(
        {"required_skills": ["Skill 1"]},
        profile,
    )
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config-revision",
    )
    request = build_ranking_request(
        {}, "candidate", [], {}, ranking_input=ranking_input, resolved_route=route,
    )
    diagnostics = build_ranking_input_diagnostics(ranking_input, request)

    assert diagnostics["contract_version"] == "ranking_input_v3"
    assert diagnostics["selected_evidence_count"] == 3
    assert diagnostics["selected_evidence_ids"] == ["ev-1", "ev-2", "ev-3"]
    assert diagnostics["candidate_skill_count"] == 9
    assert diagnostics["request_within_budget"] is True
    assert len(json.dumps(request["request_payload"], ensure_ascii=False)) <= 12_000


def test_ranking_input_does_not_reject_nine_mandatory_skills_before_budgeting() -> None:
    required_skills = [f"Required Skill {index}" for index in range(1, 10)]
    job = {"job_url": "https://example.com/over-budget", "required_skills": required_skills}
    profile = {"skills": [{"name": skill} for skill in required_skills]}
    ranking_input = build_ranking_job_input(job, profile)

    assert ranking_input["contract_metadata"]["mandatory_omissions"]["job_required_skills"] == 0
    assert ranking_input["contract_metadata"]["mandatory_omissions"]["candidate_required_skills"] == 0
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )
    request = build_ranking_request(
        job,
        ranking_input["candidate_summary"],
        [],
        {},
        ranking_input=ranking_input,
        resolved_route=route,
    )
    assert request["visibility_manifest"]["mandatory_core_complete"] is True
    assert len(json.dumps(request["request_payload"], ensure_ascii=False)) <= 12_000


def test_ranking_request_preserves_full_mandatory_requirement_text() -> None:
    required_skill = "Kubernetes " + ("production-cluster " * 12)
    job = {"job_url": "https://example.com/kubernetes", "required_skills": [required_skill]}
    ranking_input = build_ranking_job_input(job, {"skills": [{"name": required_skill}]})
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )

    request = build_ranking_request(
        job,
        ranking_input["candidate_summary"],
        [],
        {},
        ranking_input=ranking_input,
        resolved_route=route,
    )

    required_text = required_skill.strip()
    assert required_text in ranking_input["job_requirements"]
    assert required_text in request["request"].prompt
    assert request["visibility_manifest"]["mandatory_core_complete"] is True


def test_ranking_request_renders_one_evidence_excerpt_with_metadata() -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )
    excerpt = "UNIQUE_EVIDENCE_PASSAGE"
    request = build_ranking_request(
        {},
        "candidate",
        [],
        {},
        ranking_input={
            "job_requirements": "OpenAI agent builder",
            "candidate_summary": "candidate",
            "candidate_evidence": [{
                "evidence_id": "ev-1",
                "text": excerpt,
                "scoring_context": excerpt,
                "support_state": "supported",
            }],
        },
        resolved_route=route,
    )

    assert request["request"].prompt.count(excerpt) == 1


def test_ranking_request_preserves_structured_source_provenance() -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="config",
    )
    request = build_ranking_request(
        {},
        "candidate",
        [],
        {},
        ranking_input={
            "job_requirements": "OpenAI agent builder",
            "candidate_summary": "candidate",
            "candidate_evidence": [{
                "evidence_id": "ev-residual",
                "text": "Residual source evidence",
                "source_refs": [{
                    "document_id": "doc_cv",
                    "source_block_id": "block_7",
                    "locator": {"page": 3, "paragraph": 2},
                }],
            }],
        },
        resolved_route=route,
    )

    assert '"source_block_id": "block_7"' in request["request"].prompt
    assert '"page": 3' in request["request"].prompt


def test_ranking_request_keeps_candidate_skills_and_languages_when_facts_overflow() -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="configuration",
    )
    candidate_summary = json.dumps(
        {
            "skills": [f"Skill {index}" for index in range(1, 9)],
            "languages": [{"name": "German", "level": "professional"}] * 8,
            "employment": [{"role": "Data Engineer", "company": "Example" * 40}] * 8,
            "education": [{"degree": "MSc", "field": "Computer Science" * 20}] * 4,
            "certifications": [{"name": "Certification", "issuer": "Issuer" * 20}] * 4,
            "years_experience": 4,
            "target_role": "Data Engineer",
        },
        ensure_ascii=False,
    )
    request = build_ranking_request(
        {},
        candidate_summary,
        [],
        {},
        ranking_input={"job_requirements": "Build data systems", "candidate_summary": candidate_summary},
        resolved_route=route,
    )

    assert '"Skill 1"' in request["request"].prompt
    assert "German" in request["request"].prompt
    assert request["prompt_truncated"] is True
    assert len(json.dumps(request["request_payload"], ensure_ascii=False)) <= 12_000


def test_final_ranking_request_retains_language_dimensions() -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="configuration",
    )
    candidate_summary = json.dumps(
        {
            "skills": ["SQL"],
            "languages": [{
                "name": "German",
                "level": "B1",
                "native": False,
                "read": "B2",
                "write": "B1",
                "speak": "B1",
            }],
            "employment": [],
            "education": [{"degree": "MSc", "field": "Data Science", "start": "2024-10", "end": "Present"}],
            "certifications": [],
            "years_experience": 2,
            "target_role": "Data Analyst",
        },
        ensure_ascii=False,
    )
    request = build_ranking_request(
        {},
        candidate_summary,
        [],
        {},
        ranking_input={"job_requirements": "German B1 and analytics", "candidate_summary": candidate_summary},
        resolved_route=route,
    )

    prompt = request["request"].prompt
    assert '"read": "B2"' in prompt
    assert '"write": "B1"' in prompt
    assert '"speak": "B1"' in prompt
    assert '"end": "Present"' in prompt
    assert len(json.dumps(request["request_payload"], ensure_ascii=False)) <= 12_000


def test_ranking_request_rejects_unbounded_custom_prompt_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    route = SimpleNamespace(
        provider="openai_compatible", base_url="https://provider.example/v1", wire_api="responses",
        model="test-model", timeout_seconds=12.0, request_start_interval_secs=0.0,
        auth_mode="env", temperature=0.0, model_record_id="model-record", configuration_revision="configuration",
    )
    noisy = ('"\\\n' * 2_000)
    monkeypatch.setattr(ai_score_module, "build_scoring_prompt", lambda *args, **kwargs: noisy)
    with pytest.raises(ValueError, match="mandatory"):
        build_ranking_request(
            {},
            noisy,
            [],
            {},
            ranking_input={"job_requirements": noisy, "candidate_summary": noisy, "candidate_evidence": []},
            resolved_route=route,
        )


def test_ranking_input_diagnostics_include_bounded_visible_requirements_and_backend() -> None:
    ranking_input = {
        "candidate_summary": json.dumps({"skills": [f"Skill {index}" for index in range(1, 12)]}),
        "candidate_evidence": [{"evidence_id": "ev-1", "title": "Project", "text": "Evidence"}],
        "contract_metadata": {
            "version": "ranking_input_v3",
            "requirement_ids": [f"required:{index}" for index in range(100)],
            "canonical_checksums": {"candidate_facts": "candidate-checksum"},
        },
    }

    diagnostics = build_ranking_input_diagnostics(
        ranking_input,
        {
            "request_payload": {"prompt": "bounded"},
            "prompt_truncated": True,
            "prompt_truncation_steps": ["candidate_facts:field_aware_bound"],
        },
        retrieval_metadata={
            "retrieval_strategy": "lexical_v1",
            "effective_strategy": "lexical_v1",
            "backend_id": "disabled",
            "effective_embedding_backend_metadata": {"backend_id": "disabled", "dimension": 0},
        },
    )

    assert diagnostics["visible_candidate_skills"] == [f"Skill {index}" for index in range(1, 9)]
    assert diagnostics["bounded_requirement_ids"] == [f"required:{index}" for index in range(32)]
    assert diagnostics["effective_retrieval_metadata"] == {
        "retrieval_strategy": "lexical_v1",
        "effective_strategy": "lexical_v1",
        "backend_id": "disabled",
        "effective_embedding_backend_metadata": {"backend_id": "disabled", "dimension": 0},
    }


def test_ranking_job_input_dedupes_aliases_and_keeps_required_priority() -> None:
    policy = {
        "schema_version": "semantic_policy_v2",
        "resolver_contract_version": "semantic_resolver_v2",
        "maps": {"skill": {"py": "python", "python": "python"}, "domain": {}, "role_family": {}},
    }
    result = build_ranking_job_input(
        {
            "required_skills": ["C"],
            "tech_stack": [f"Tool {index}" for index in range(1, 6)],
            "preferred_skills": ["C"],
        },
        {"skills": [{"name": value} for value in ["Python", "py", "C", *[f"Tool {index}" for index in range(1, 6)]]]},
        {"semantic_policy": policy},
    )

    selected = json.loads(result["candidate_summary"])["skills"]
    assert selected[0] == "C"
    assert sum(value.casefold() in {"python", "py"} for value in selected) == 1


def test_explicit_empty_candidate_evidence_does_not_fall_back_to_legacy_evidence() -> None:
    route = SimpleNamespace(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="test-model",
        timeout_seconds=12.0,
        request_start_interval_secs=0.0,
        auth_mode="env",
        temperature=0.0,
        model_record_id="model-record",
        configuration_revision="config-revision",
    )

    request = build_ranking_request(
        {},
        "candidate",
        ["legacy evidence must not be used"],
        {},
        ranking_input={
            "job_requirements": "OpenAI agent builder",
            "candidate_summary": "candidate",
            "candidate_evidence": [],
        },
        resolved_route=route,
    )

    assert "legacy evidence must not be used" not in request["request"].prompt


def test_score_job_uses_shared_runtime_contract() -> None:
    from unittest.mock import patch

    from fitcv.ai_score import _execute_ranking_runtime, score_job
    from fitcv.llm_runtime import LlmAdapterResponse
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="cx/test-model",
        timeout_seconds=12.0,
    )
    captured: dict[str, object] = {}

    def adapter(request, routing, api_key):
        captured["request"] = request
        return LlmAdapterResponse(
            raw_text=(
                '{"ai_score":0.8,"fit_label":"strong","score_reasoning":"good",'
                '"matched_strengths":[],"key_risks":[]}'
            ),
            adapter="fake",
            runtime_path="test",
        )

    job = {"job_url": "http://test.url/1", "title": "Data Engineer"}
    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=route),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        runtime_result = _execute_ranking_runtime(
            job,
            "candidate summary",
            [],
            {},
            adapter=adapter,
        )

    with patch("fitcv.ai_score._execute_ranking_runtime", return_value=runtime_result):
        result = score_job(job, "candidate summary", [], {})

    request = captured["request"]
    assert request.routing_part == "ranking_ai_score"
    assert request.response_mode == "json_object"
    assert result["job_url"] == "http://test.url/1"
    assert result["ai_score"] == 0.8

def test_run_ai_scoring_prefers_nested_pipeline_top_n_over_legacy_flat_key() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep"):
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 1},
                "rerank_top_n": 3,
                "rerank_sleep_secs": 0.0,
            },
        )

    assert len(results) == 1
    assert mock_score_job.call_count == 1
    assert results[0]["job_url"] == "https://example.com/1"

def test_run_ai_scoring_ignores_retired_ranking_sleep_settings() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]
    sleep_calls: list[float] = []

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep") as mock_sleep:
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        mock_sleep.side_effect = lambda secs: sleep_calls.append(float(secs))
        run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "rerank_sleep_secs": 0.9,
                "stage_runtime": {"ranking": {"sleep_secs": 0.2}},
            },
        )

    assert sleep_calls == []


def test_run_ai_scoring_parallel_path_preserves_input_order() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]

    def _slow_score_job(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        if job["job_url"].endswith("/1"):
            time.sleep(0.03)
        elif job["job_url"].endswith("/2"):
            time.sleep(0.01)
        return {
            "job_url": job["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_slow_score_job):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 3},
                "stage_runtime": {"ranking": {"concurrency": 3, "sleep_secs": 0.0}},
            },
        )

    assert [row["job_url"] for row in results] == [job["job_url"] for job in shortlist]


def test_run_ai_scoring_parallel_path_isolates_runtime_exceptions() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]

    def _score_or_fail(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        if job["job_url"].endswith("/2"):
            raise RuntimeError("boom")
        return {
            "job_url": job["job_url"],
            "ai_score": 0.8,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_score_or_fail):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "stage_runtime": {"ranking": {"concurrency": 2, "sleep_secs": 0.0}},
            },
        )

    assert results[0]["job_url"] == "https://example.com/1"
    assert results[0]["legacy_model_fit_label"] == "strong"
    assert results[1]["job_url"] == "https://example.com/2"
    assert results[1]["legacy_model_fit_label"] is None
    assert results[1]["parser_status"] == "runtime_exception"

def test_run_ai_scoring_parallel_path_overlaps_workers_when_sleep_zero() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]
    barrier = threading.Barrier(2)

    def _score_with_barrier(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        barrier.wait(timeout=0.5)
        return {
            "job_url": job["job_url"],
            "ai_score": 0.6,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_score_with_barrier):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "stage_runtime": {"ranking": {"concurrency": 2, "sleep_secs": 0.0}},
            },
        )

    assert len(results) == 2

def test_run_ai_scoring_parallel_path_does_not_pace_executor_submission() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]
    sleep_calls: list[float] = []

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep") as mock_sleep:
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        mock_sleep.side_effect = lambda secs: sleep_calls.append(float(secs))
        run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 3},
                "stage_runtime": {"ranking": {"concurrency": 3, "sleep_secs": 0.2}},
            },
        )

    assert sleep_calls == []


# ── store_ai_scores ───────────────────────────────────────────────────────────


def test_run_ai_scoring_submits_one_future_per_item() -> None:
    from fitcv.ai_score import run_ai_scoring
    from concurrent.futures import ThreadPoolExecutor as RealThreadPoolExecutor

    shortlist = [{"job_url": f"https://example.com/{index}"} for index in range(4)]
    sleep_calls: list[float] = []
    submissions: list[tuple[Any, ...]] = []

    class RecordingThreadPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            self.executor = RealThreadPoolExecutor(max_workers=max_workers)

        def __enter__(self):
            self.executor.__enter__()
            return self

        def __exit__(self, *args: Any) -> None:
            self.executor.__exit__(*args)

        def submit(self, fn: Any, *args: Any):
            submissions.append(args)
            return self.executor.submit(fn, *args)

    with patch("fitcv.ai_score.score_job") as mock_score_job, \
         patch.object(time, "sleep") as mock_sleep, \
         patch("fitcv.ai_score.ThreadPoolExecutor", RecordingThreadPoolExecutor):
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        mock_sleep.side_effect = lambda secs: sleep_calls.append(float(secs))
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 4},
                "stage_runtime": {
                    "ranking": {"batch_size": 2, "concurrency": 2, "sleep_secs": 0.2}
                },
            },
        )

    assert [row["job_url"] for row in results] == [job["job_url"] for job in shortlist]
    assert len(submissions) == len(shortlist)
    assert all(len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], dict) for args in submissions)
    assert sleep_calls == []


def test_store_ai_scores_writes_sqlite_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.ai_score import store_ai_scores

    db_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))

    scores = [
        {
            "job_url": "https://example.com/job-1",
            "ai_score": 0.91,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "Strong SQL and Python fit",
            "matched_strengths": ["SQL", "Python"],
            "key_risks": ["No dbt"],
        },
        {
            "job_url": "https://example.com/job-2",
            "ai_score": 0.55,
            "legacy_model_fit_label": "stretch",
            "score_reasoning": "Partial analytics overlap",
            "matched_strengths": ["Looker"],
            "key_risks": [],
        },
    ]

    store_ai_scores(scores, config={})

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT job_url, ai_score, fit_label, score_reasoning,
                   matched_strengths_json, key_risks_json
            FROM ai_score_results
            ORDER BY job_url
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "https://example.com/job-1"
    assert float(rows[0][1]) == 0.91
    assert rows[0][2] == "strong"
    assert json.loads(str(rows[0][4])) == ["SQL", "Python"]
    assert json.loads(str(rows[0][5])) == ["No dbt"]
    assert rows[1][0] == "https://example.com/job-2"
    assert float(rows[1][1]) == 0.55
    assert rows[1][2] == "stretch"
    assert json.loads(str(rows[1][4])) == ["Looker"]
    assert json.loads(str(rows[1][5])) == []



# ── integration tests ─────────────────────────────────────────────────────────

@pytest.mark.integration
def test_score_job_integration(config: dict) -> None:
    """Integration — calls routed OpenAI-compatible scoring provider and returns a parsed score."""
    from fitcv.ai_score import score_job
    job = {
        "job_url": "http://test.url/1",
        "title": "Data Engineer",
        "required_skills": ["SQL", "Python"],
        "seniority": "mid",
        "job_family": "data_engineering",
        "responsibilities": ["Build pipelines", "Write tests"],
    }
    result = score_job(
        job=job,
        candidate_summary="Experienced data engineer with 4 years SQL and Python.",
        top_evidence=["Built GA4 pipeline reducing latency 40%."],
        config=config,
    )
    assert 0.0 <= result["ai_score"] <= 1.0
    assert "fit_label" not in result
"""
@meta
type: test
scope: unit
domain: ranking
covers:
  - AI scoring behavior
excludes:
  - live model calls
tags:
  - fast
  - ci-safe
"""


def test_execute_ranking_runtime_keeps_empty_output_stage_owned() -> None:
    from unittest.mock import patch

    from fitcv.ai_score import _execute_ranking_runtime
    from fitcv.llm_runtime import LlmAdapterResponse
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="cx/test-model",
        timeout_seconds=12.0,
    )
    captured: dict[str, object] = {}

    def adapter(request, routing, api_key):
        captured["request"] = request
        return LlmAdapterResponse(raw_text="", adapter="fake", runtime_path="test")

    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=route),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        result = _execute_ranking_runtime(
            {"job_url": "https://example.com/1", "title": "Data Engineer"},
            "candidate",
            [],
            {},
            adapter=adapter,
        )

    request = captured["request"]
    assert request.routing_part == "ranking_ai_score"
    assert request.response_mode == "json_object"
    assert result.status == "failed"
    assert result.failure.code == "validation_error"
    assert result.parsed_value["score_status"] == "invalid"


def test_run_ai_scoring_emits_stable_runtime_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    from fitcv.ai_score import run_ai_scoring
    from fitcv.llm_runtime import LlmRuntimeProvenance, LlmRuntimeResult, LlmValidationResult

    runtime_result = LlmRuntimeResult(
        status="succeeded",
        parsed_value={
            "ai_score": 0.9,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "match",
            "matched_strengths": [],
            "key_risks": [],
            "parser_status": "ok",
        },
        validation=LlmValidationResult(valid=True, errors=[], details={}),
        failure=None,
        provenance=LlmRuntimeProvenance(
            routing_part="ranking_ai_score",
            runtime_path="test",
            adapter="fake",
            provider="test",
            model="test",
            wire_api="responses",
            attempt_count=1,
            response_id=None,
            trace_id=None,
            latency_ms=1,
        ),
        adapter_response=None,
    )
    monkeypatch.setattr("fitcv.ai_score._execute_ranking_runtime", lambda *args, **kwargs: runtime_result)
    observations: list[dict[str, Any]] = []

    rows = run_ai_scoring(
        [{"job_url": "https://example.com/jobs/1", "raw_job_fingerprint": "raw-1"}],
        "candidate",
        {"stage_runtime": {"ranking": {"sleep_secs": 0}}},
        runtime_observation_callback=observations.append,
    )

    assert rows[0]["job_url"] == "https://example.com/jobs/1"
    assert observations == [
        {
            "contract_version": "llm_runtime_observation_v1",
            "scope_key": "raw-1",
            "input_index": 0,
            "invocation_index": 1,
            "evidence": {
                "contract_version": "llm_runtime_evidence_v1",
                "status": "succeeded",
                "provenance": {
                    "routing_part": "ranking_ai_score",
                    "runtime_path": "test",
                    "adapter": "fake",
                    "provider": "test",
                    "model": "test",
                    "wire_api": "responses",
                    "attempt_count": 1,
                    "response_id": None,
                    "trace_id": None,
                    "latency_ms": 1,
                    "model_record_id": None,
                    "configuration_revision": None,
                    "temperature": None,
                },
                "failure": None,
            },
        }
    ]


def test_build_scoring_prompt_uses_full_replacement() -> None:
    from fitcv.prompts.loader import load_prompt_template
    from fitcv.prompts.registry import get_prompt_definition

    default_text = load_prompt_template(
        get_prompt_definition("ranking.ai_score.v2").template_path
    )
    replacement = default_text.replace("Return JSON only", "Penalize unsupported claims.\n\nReturn JSON only", 1)
    with patch("fitcv.ai_score.get_prompt_replacement", return_value=replacement):
        prompt = build_scoring_prompt(
            jd_summary="Data Analyst",
            candidate_summary="SQL",
            top_evidence=[],
            config={"prompts": {"ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v2"}}}},
        )

    assert prompt.count("Penalize unsupported claims.") == 1
    assert prompt.index("Penalize unsupported claims.") < prompt.index("Return JSON only")

def test_ai_score_contract_fingerprint_uses_hash_only_prompt_customization() -> None:
    raw = "Private ranking guidance"
    with patch(
        "fitcv.ai_score.get_prompt_replacement_metadata",
        return_value={
            "customized": True,
            "replacement_sha256": __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest(),
            "replacement_char_count": len(raw),
        },
    ):
        record = build_ai_score_contract_fingerprint(
            {
                "ai_score_model": "cx/test-model",
                "prompts": {"ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v2"}}},
            }
        )

    assert record["payload"]["prompt_customized"] is True
    assert record["payload"]["prompt_replacement_char_count"] == len(raw)
    assert raw not in str(record)


def test_observation_toggle_keeps_identical_model_input(monkeypatch: pytest.MonkeyPatch) -> None:
    from fitcv.ai_score import run_ai_scoring
    from fitcv.llm_runtime import LlmRuntimeProvenance, LlmRuntimeResult, LlmValidationResult
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting("test", "https://test.example", "responses", "model-a", 12.0)
    captured: list[tuple[str, str, str]] = []
    result = LlmRuntimeResult(
        status="succeeded", parsed_value={"ai_score": .5, "legacy_model_fit_label": None,
        "score_reasoning": "ok", "matched_strengths": [], "key_risks": [], "parser_status": "ok"},
        validation=LlmValidationResult(True, [], {}), failure=None,
        provenance=LlmRuntimeProvenance("ranking_ai_score", "test", "fake", "test", "model-a", "responses", 1, None, None, 1),
        adapter_response=None,
    )

    def execute(*args: Any, **kwargs: Any) -> LlmRuntimeResult:
        request = kwargs["ranking_request"]["request"]
        captured.append((request.prompt, request.routing_part, request.response_mode))
        return result

    monkeypatch.setattr("fitcv.ai_score._execute_ranking_runtime", execute)
    job = {"job_url": "u", "title": "Data Engineer", "required_skills": ["SQL"]}
    run_ai_scoring([job], "candidate", {}, resolved_route=route)
    run_ai_scoring([job], "candidate", {}, runtime_observation_callback=lambda _: None, resolved_route=route)
    assert captured[0] == captured[1]


def test_ranking_stage_freezes_route_until_next_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import nullcontext
    from fitcv.pipeline_stage_runner import execute_ranking_stage
    from fitcv.runtime_routing import LlmRouting

    first = LlmRouting("test", "https://one.example", "responses", "model-one", 10.0, temperature=.1)
    second = LlmRouting("test", "https://two.example", "responses", "model-two", 20.0, temperature=.9)
    config = {"pipeline": {"ai_score_top_n": 2}, "reuse": {"ranking": {"enabled": False}}}
    seen: list[tuple[str, str, float]] = []

    def fingerprint(job: dict[str, Any], *_: Any, **kwargs: Any) -> dict[str, str]:
        route = kwargs["resolved_route"]
        seen.append(("fingerprint", route.model, route.temperature))
        config["changed"] = True
        return {"fingerprint": job["job_url"]}

    def score(jobs: list[dict[str, Any]], *_: Any, **kwargs: Any) -> list[dict[str, Any]]:
        route = kwargs["resolved_route"]
        seen.extend(("execute", route.model, route.temperature) for _ in jobs)
        return [{"job_url": job["job_url"], "ai_score": .5} for job in jobs]

    class Store:
        def store_final_ranking(self, *_: Any) -> None: pass

    def invoke(job_url: str) -> None:
        execute_ranking_stage(
            run_id="r", state={}, shortlist=[{"job_url": job_url}], candidate_summary="candidate", profile={},
            config=config, final_top_n=1, reporter=None, pipeline_store=Store(), observe_span=lambda *_a, **_k: nullcontext(),
            set_span_attributes=lambda _: None, cancellation_check=None, cancellation_error_cls=RuntimeError,
            ranking_ai_score_reuse_index={}, build_ai_score_input_fingerprint=fingerprint, extract_job_url=lambda job: job["job_url"],
            run_ai_scoring=score, build_ranking_features=lambda *_a, **_k: [], rank_jobs=lambda *_a, **_k: [],
            preference_policy_resolver=lambda _: None,
        )

    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolve_llm_routing", lambda *_a, **_k: first if len(seen) < 2 else second)
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolve_run_preference_policy", lambda **_: object())
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolved_preference_policy_to_dict", lambda _: {})
    invoke("one")
    assert seen == [("fingerprint", "model-one", .1), ("execute", "model-one", .1)]
    invoke("two")
    assert seen[-2:] == [("fingerprint", "model-two", .9), ("execute", "model-two", .9)]


def test_stage_runner_recomputes_invalid_cached_score(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import nullcontext
    from fitcv.pipeline_stage_runner import execute_ranking_stage
    from fitcv.runtime_routing import LlmRouting

    calls: list[str] = []
    route = LlmRouting("test", "https://test.example", "responses", "model", 10.0)

    class Store:
        def store_final_ranking(self, *_: Any) -> None: pass

    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolve_llm_routing", lambda *_a, **_k: route)
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolve_run_preference_policy", lambda **_: object())
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolved_preference_policy_to_dict", lambda _: {})
    execute_ranking_stage(
        run_id="r", state={}, shortlist=[{"job_url": "u"}], candidate_summary="candidate", profile={},
        config={"pipeline": {"ai_score_top_n": 1}, "reuse": {"ranking": {"enabled": True}}}, final_top_n=1,
        reporter=None, pipeline_store=Store(), observe_span=lambda *_a, **_k: nullcontext(), set_span_attributes=lambda _: None,
        cancellation_check=None, cancellation_error_cls=RuntimeError,
        ranking_ai_score_reuse_index={"fp": {"job_url": "u", "ai_score": "malformed", "score_status": "invalid"}},
        build_ai_score_input_fingerprint=lambda *_a, **_k: {"fingerprint": "fp"}, extract_job_url=lambda job: job["job_url"],
        run_ai_scoring=lambda jobs, *_a, **_k: calls.extend(["recomputed"]) or [{"job_url": jobs[0]["job_url"], "ai_score": .5}],
        build_ranking_features=lambda *_a, **_k: [], rank_jobs=lambda *_a, **_k: [], preference_policy_resolver=lambda _: None,
    )
    assert calls == ["recomputed"]


def test_ranking_stage_persists_selected_evidence_and_scorer_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import nullcontext
    from fitcv.pipeline_stage_runner import execute_ranking_stage

    captured: dict[str, Any] = {}

    class Store:
        def store_final_ranking(self, *_: Any) -> None:
            return None

    job = {
        "job_url": "https://example.com/agent-role",
        "title": "AI Agent Builder",
        "required_skills_canonical": ["Python", "OpenAI"],
        "tech_stack_canonical": ["OpenAI"],
        "responsibilities": ["Build agent workflows"],
    }
    profile = {
        "skills": [{"name": "Python"}, {"name": "OpenAI"}],
        "projects": [
            {
                "id": "agent-project",
                "name": "Agent Platform",
                "skills": ["Python", "OpenAI"],
                "tech_stack": ["OpenAI"],
                "highlights": ["Built agent workflows with OpenAI APIs."],
            }
        ],
    }

    def score(jobs: list[dict[str, Any]], *_args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        captured["ranking_inputs"] = kwargs["ranking_inputs"]
        return [{"job_url": jobs[0]["job_url"], "ai_score": 0.8, "score_status": "valid"}]

    state: dict[str, Any] = {
        "shortlist_diagnostics": {
            "requested_strategy": "lexical_v1",
            "effective_strategy": "lexical_v1",
            "backend_id": "structured_jobs_lexical",
        }
    }
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolve_run_preference_policy", lambda **_kwargs: object())
    monkeypatch.setattr("fitcv.pipeline_stage_runner.resolved_preference_policy_to_dict", lambda _policy: {})
    execute_ranking_stage(
        run_id="run-1",
        state=state,
        shortlist=[job],
        candidate_summary="Candidate builder",
        profile=profile,
        config={"pipeline": {"ai_score_top_n": 1}, "reuse": {"ranking": {"enabled": False}}},
        final_top_n=1,
        reporter=None,
        pipeline_store=Store(),
        observe_span=lambda *_args, **_kwargs: nullcontext(),
        set_span_attributes=lambda _attrs: None,
        cancellation_check=None,
        cancellation_error_cls=RuntimeError,
        ranking_ai_score_reuse_index={},
        build_ai_score_input_fingerprint=lambda *_args, **_kwargs: {"fingerprint": "fp"},
        extract_job_url=lambda row: row["job_url"],
        run_ai_scoring=score,
        build_ranking_features=lambda *_args, **_kwargs: [],
        rank_jobs=lambda *_args, **_kwargs: [],
        preference_policy_resolver=lambda _contract: None,
    )

    identity = "url:https://example.com/agent-role"
    assert identity in captured["ranking_inputs"]
    assert captured["ranking_inputs"][identity]["candidate_evidence"]
    assert state["ranking_input_diagnostics_by_identity"][identity]["selected_evidence_ids"]
    assert state["ranking_admission_manifest"]["counts"]["ai_score_selected"] == 1
    assert state["ranking_admission_manifest"]["rows"][0]["score_execution"] == "fresh"
    assert state["ranking_admission_manifest"]["rows"][0]["request_fingerprint"] == "fp"


def test_route_resolution_failure_maps_to_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from fitcv.ai_score import run_ai_scoring

    monkeypatch.setattr("fitcv.ai_score.resolve_llm_routing", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("routing unavailable")))
    rows = run_ai_scoring([{"job_url": "u"}], "candidate", {})
    assert rows[0]["failure_code"] == "provider_failure"
    assert rows[0]["score_status"] == "unscored"
