"""Focused regressions for admission-to-scoring information preservation."""

import json
from types import SimpleNamespace

import pytest

import fitcv.ai_score as ai_score_module
from fitcv.ai_score import (
    RankingInputEvidenceLimited,
    build_ranking_input_diagnostics,
    build_ranking_job_input,
    build_ranking_request,
    run_ai_scoring,
)
from fitcv.evidence import retrieve_evidence_bundle, select_ranking_evidence


def _route() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="test-model",
        timeout_seconds=12.0,
        request_start_interval_secs=0.0,
        auth_mode="env",
        temperature=0.0,
        model_record_id="model-record",
        configuration_revision="config",
    )


def test_ranking_input_preserves_source_text_and_decisive_scoring_context() -> None:
    profile = {
        "_projected_evidence_pool": [{
            "evidence_id": "ev-agent",
            "kind": "project",
            "title": "Agent platform",
            "text": "Generic source summary.",
            "scoring_context": "OpenAI-compatible APIs and Claude Code integration",
            "source_ref": "projects[0]",
            "skills": [],
        }],
    }

    ranking_input = build_ranking_job_input(
        {"tech_stack": ["OpenAI-compatible APIs"]},
        profile,
    )

    evidence = ranking_input["candidate_evidence"][0]
    assert evidence["text"] == "Generic source summary."
    assert evidence["scoring_context"] == "OpenAI-compatible APIs and Claude Code integration"


def test_rare_required_skill_support_is_reserved_before_channel_cutoff() -> None:
    profile = {
        "_projected_evidence_pool": [
            {
                "evidence_id": "ev-common",
                "kind": "project",
                "title": "Common work",
                "text": "Built Python services.",
                "scoring_context": "Python services",
                "skills": ["Python"],
                "source_ref": "projects[0]",
            },
            {
                "evidence_id": "ev-rare",
                "kind": "project",
                "title": "Rare system",
                "text": "Built production systems with RareTool.",
                "scoring_context": "RareTool production system",
                "skills": ["RareTool"],
                "source_ref": "projects[1]",
            },
        ]
    }
    job = {
        "title": "Platform Engineer",
        "required_skills": ["RareTool"],
        "required_skills_canonical": ["raretool"],
    }

    bundle = retrieve_evidence_bundle(
        profile,
        job,
        top_k=1,
        config={"cv_analysis": {"semantic_alignment": {"channel_pool_size": 1}}},
    )

    assert bundle["selected_evidence_ids"] == ["ev-rare"]


def test_only_zero_evidence_prompt_fits_returns_explicit_evidence_limited_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ai_score_module,
        "build_scoring_prompt",
        lambda _job, _candidate, evidence, **_kwargs: "x" * (13_000 if evidence else 100),
    )
    monkeypatch.setattr(ai_score_module, "resolve_llm_routing", lambda *_args, **_kwargs: _route())

    rows = run_ai_scoring(
        [{
            "job_url": "https://example.com/job",
            "ranking_input": {
                "job_requirements": "Small job",
                "candidate_summary": "Small candidate",
                "candidate_evidence": [{
                    "evidence_id": "ev-1",
                    "text": "Attributable evidence",
                    "source_ref": "cv:1",
                }],
            },
        }],
        "candidate",
        {},
    )

    assert rows[0]["score_status"] == "unscored"
    assert rows[0]["score_state"] == "evidence_limited"
    assert rows[0]["evidence_limited"] is True
    assert rows[0]["failure_code"] == "evidence_limited"
    assert rows[0]["retry_eligible"] is False


def test_candidate_overflow_reports_optional_field_ownership_and_keeps_skills() -> None:
    candidate_summary = json.dumps({
        "skills": ["RareTool", "Python"],
        "languages": [{"name": "German", "level": "professional"}] * 12,
        "employment": [{"role": "Platform Engineer", "company": "Company" * 80}] * 12,
        "education": [{"degree": "MSc", "field": "Computer Science" * 20}] * 4,
        "certifications": [{"name": "Certification", "issuer": "Issuer" * 20}] * 4,
        "years_experience": 5,
        "target_role": "Platform Engineer",
    }, ensure_ascii=False)

    request = build_ranking_request(
        {},
        candidate_summary,
        [],
        {},
        ranking_input={
            "job_requirements": json.dumps({"language_requirements": ["German"]}),
            "candidate_summary": candidate_summary,
        },
        resolved_route=_route(),
    )

    candidate = json.loads(request["bounded_ranking_input"]["candidate_summary"])
    visibility = request["visibility_manifest"]["candidate"]
    assert candidate["skills"] == ["RareTool", "Python"]
    assert visibility["omitted_counts"].get("employment", 0) > 0
    assert visibility["mandatory_omitted_fields"] == []


@pytest.mark.parametrize("candidate_level", ["C1", "A2"])
def test_candidate_overflow_protects_mandatory_language_identity(candidate_level: str) -> None:
    candidate_summary = json.dumps({
        "skills": ["RareTool", "Python"] + [f"Skill{index}" * 8 for index in range(80)],
        "languages": [
            {"name": "French", "level": "B2"},
            {"name": "German", "level": candidate_level},
        ],
        "employment": [{"role": "Platform Engineer" * 10, "company": "Company" * 80}] * 12,
        "years_experience": 5,
        "target_role": "Platform Engineer",
    }, ensure_ascii=False)

    request = build_ranking_request(
        {},
        candidate_summary,
        [],
        {},
        ranking_input={
            "job_requirements": json.dumps({"language_requirements": ["German B2"]}),
            "candidate_summary": candidate_summary,
        },
        resolved_route=_route(),
    )

    candidate = json.loads(request["bounded_ranking_input"]["candidate_summary"])
    visibility = request["visibility_manifest"]["candidate"]
    assert {item["name"] for item in candidate["languages"]} == {"German"}
    assert candidate["languages"][0]["level"] == candidate_level
    assert visibility["mandatory_omitted_fields"] == []


def test_diagnostics_use_exact_final_bounded_payload() -> None:
    ranking_input = {
        "job_requirements": json.dumps({"title": "Platform Engineer"}),
        "candidate_summary": json.dumps({"skills": ["RareTool", "Python"]}),
        "candidate_evidence": [{
            "evidence_id": "ev-1",
            "title": "Rare system",
            "text": "Generic source",
            "scoring_context": "RareTool production system",
            "source_ref": "projects[1]",
        }],
        "contract_metadata": {"version": "ranking_input_v3"},
    }
    request = build_ranking_request(
        {},
        ranking_input["candidate_summary"],
        ranking_input["candidate_evidence"],
        {},
        ranking_input=ranking_input,
        resolved_route=_route(),
    )

    diagnostics = build_ranking_input_diagnostics(ranking_input, request)
    final_payload = request["bounded_ranking_input"]
    assert diagnostics["bounded_ranking_input"] == final_payload
    assert diagnostics["selected_evidence_ids"] == ["ev-1"]
    assert diagnostics["visible_candidate_skills"] == ["RareTool", "Python"]
    assert final_payload["candidate_evidence"][0]["text"] in request["request"].prompt


def test_admitted_job_handoff_keeps_required_skill_and_attributable_evidence() -> None:
    job = {
        "title": "Platform Engineer",
        "required_skills": ["RareTool"],
        "required_skills_canonical": ["raretool"],
        "tech_stack": ["RareTool"],
    }
    profile = {
        "skills": [{"name": "RareTool"}],
        "_projected_evidence_pool": [{
            "evidence_id": "ev-rare",
            "kind": "project",
            "title": "Rare system",
            "text": "Generic source summary.",
            "scoring_context": "Built production systems with RareTool",
            "source_refs": [{"document_id": "cv", "locator": {"page": 2}}],
            "source_ref": "projects[0]",
            "skills": ["RareTool"],
        }],
    }

    selected = select_ranking_evidence(profile["_projected_evidence_pool"], job, limit=1)
    ranking_input = build_ranking_job_input(
        job,
        {**profile, "_projected_evidence_pool": selected},
    )
    request = build_ranking_request(
        job,
        ranking_input["candidate_summary"],
        ranking_input["candidate_evidence"],
        {},
        ranking_input=ranking_input,
        resolved_route=_route(),
    )

    visible_job = json.loads(request["bounded_ranking_input"]["job_requirements"])
    visible_evidence = request["bounded_ranking_input"]["candidate_evidence"][0]
    assert any(value.casefold() == "raretool" for value in visible_job["required_skills"])
    assert visible_evidence["evidence_id"] == "ev-rare"
    assert "RareTool" in visible_evidence["scoring_context"]
    assert visible_evidence["source_refs"] == [{"document_id": "cv", "locator": {"page": 2}}]


def test_build_ranking_request_raises_evidence_limited_when_zero_evidence_is_only_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ai_score_module,
        "build_scoring_prompt",
        lambda _job, _candidate, evidence, **_kwargs: "x" * (13_000 if evidence else 100),
    )

    with pytest.raises(RankingInputEvidenceLimited):
        build_ranking_request(
            {},
            "candidate",
            [],
            {},
            ranking_input={
                "job_requirements": "job",
                "candidate_summary": "candidate",
                "candidate_evidence": [{"evidence_id": "ev-1", "text": "proof"}],
            },
            resolved_route=_route(),
        )
