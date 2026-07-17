"""Tests for the shared prompt registry and renderer."""

import pytest

from fitcv.prompts import get_prompt_definition, render_prompt


def test_get_prompt_definition_returns_enrich_extraction_metadata() -> None:
    definition = get_prompt_definition("enrich.extraction.v1")

    assert definition.prompt_id == "enrich.extraction.v1"
    assert definition.stage_id == "enrich"
    assert definition.version == "v1"
    assert definition.template_path.name == "enrich_extraction_v1.md"


def test_get_prompt_definition_returns_ranking_ai_score_metadata() -> None:
    definition = get_prompt_definition("ranking.ai_score.v1")

    assert definition.prompt_id == "ranking.ai_score.v1"
    assert definition.stage_id == "ranking"
    assert definition.version == "v1"
    assert definition.template_path.name == "ranking_ai_score_v1.md"


def test_get_prompt_definition_returns_cv_generation_write_metadata() -> None:
    definition = get_prompt_definition("cv_generation.write.v1")

    assert definition.prompt_id == "cv_generation.write.v1"
    assert definition.stage_id == "cv_generation"
    assert definition.version == "v1"
    assert definition.template_path.name == "cv_generation_write_v1.md"


def test_get_prompt_definition_returns_cv_generation_structured_write_metadata() -> None:
    definition = get_prompt_definition("cv_generation.structured_write.v1")

    assert definition.prompt_id == "cv_generation.structured_write.v1"
    assert definition.stage_id == "cv_generation"
    assert definition.version == "v1"
    assert definition.template_path.name == "cv_generation_structured_write_v1.md"


def test_render_prompt_includes_expected_runtime_context() -> None:
    rendered = render_prompt(
        "enrich.extraction.v1",
        {
            "metadata_block": '{"title": "Data Analyst"}',
            "extraction_schema": '{"required_skills": []}',
            "description": "Need SQL and Python skills.",
        },
    )

    assert rendered.prompt_id == "enrich.extraction.v1"
    assert "Data Analyst" in rendered.text
    assert "required_skills" in rendered.text
    assert "Need SQL and Python skills." in rendered.text


def test_render_prompt_ranking_ai_score_includes_thresholds() -> None:
    rendered = render_prompt(
        "ranking.ai_score.v1",
        {
            "jd_summary": "Data Analyst",
            "candidate_summary": "SQL, Python",
            "evidence_section": "",
            "strong_threshold": "0.7",
            "stretch_threshold": "0.4",
        },
    )

    assert "Data Analyst" in rendered.text
    assert "0.7" in rendered.text
    assert "0.4" in rendered.text


def test_render_prompt_cv_generation_write_includes_sections() -> None:
    rendered = render_prompt(
        "cv_generation.write.v1",
        {
            "title": "Data Analyst",
            "required_skills": "SQL, Python",
            "selected_evidence": "- Experience",
            "evidence_usage_guidance": "- Use evidence",
            "analysis_summary": "Selected evidence count: 2",
            "constraints": "Do not invent claims.",
            "section_evidence": "(none)",
            "output_template": "## Summary",
            "output_instruction": "Write only the completed CV markdown. Do not add commentary.",
        },
    )

    assert "Data Analyst" in rendered.text
    assert "Do not invent claims." in rendered.text
    assert "## Summary" in rendered.text


def test_render_prompt_cv_generation_structured_write_includes_schema() -> None:
    rendered = render_prompt(
        "cv_generation.structured_write.v1",
        {
            "title": "Data Analyst",
            "required_skills": "SQL, Python",
            "selected_evidence": "- Experience",
            "allowed_skills": "SQL, Python",
            "allowed_certifications": "(none)",
            "evidence_usage_guidance": "- Use evidence",
            "analysis_summary": "Selected evidence count: 2",
            "constraints": "Do not invent claims.",
            "section_evidence": "(none)",
            "output_template": "## Summary",
            "structured_schema": '{"sections": {}}',
            "output_instruction": "Write only valid JSON matching the schema below.",
        },
    )

    assert "structured JSON document" in rendered.text
    assert "## Structured JSON Schema" in rendered.text
    assert '{"sections": {}}' in rendered.text


def test_render_prompt_raises_for_missing_required_variables() -> None:
    with pytest.raises(ValueError, match="missing template variables"):
        render_prompt("enrich.extraction.v1", {"description": "Only description"})


def test_get_prompt_definition_rejects_unknown_prompt_id() -> None:
    with pytest.raises(KeyError):
        get_prompt_definition("enrich.extraction.v999")


def test_get_prompt_definition_returns_synonym_triage_metadata() -> None:
    definition = get_prompt_definition("synonym_triage.recommendation.v1")

    assert definition.prompt_id == "synonym_triage.recommendation.v1"
    assert definition.stage_id == "synonym_triage"
    assert definition.version == "v1"
    assert definition.template_path.name == "synonym_triage_recommendation_v1.md"


def test_render_prompt_synonym_triage_includes_proposal_and_timestamp() -> None:
    rendered = render_prompt(
        "synonym_triage.recommendation.v1",
        {
            "proposal_json": '{"proposal_id":"proposal-a","alias":"gcp"}',
            "now_iso": "2026-05-14T10:35:00Z",
        },
    )

    assert "You are a synonym triage assistant." in rendered.text
    assert '"proposal_id":"proposal-a"' in rendered.text
    assert "2026-05-14T10:35:00Z" in rendered.text
"""
@meta
type: test
scope: unit
domain: prompts
covers:
  - prompt registry and prompt-loading behavior
excludes:
  - live model inference
tags:
  - fast
  - ci-safe
"""

@pytest.mark.parametrize(
    ("prompt_id", "context", "contract_anchor"),
    [
        (
            "enrich.extraction.v1",
            {
                "metadata_block": "{}",
                "extraction_schema": '{"required_skills": []}',
                "description": "Need SQL.",
            },
            "Return ONLY a valid JSON object",
        ),
        (
            "ranking.ai_score.v2",
            {
                "jd_summary": "Data Analyst",
                "candidate_summary": "SQL",
                "evidence_section": "",
            },
            "Return JSON only",
        ),
        (
            "cv_generation.structured_write.v1",
            {
                "title": "Data Analyst",
                "required_skills": "SQL",
                "selected_evidence": "- Evidence",
                "allowed_skills": "SQL",
                "allowed_certifications": "(none)",
                "evidence_usage_guidance": "Use evidence",
                "analysis_summary": "Summary",
                "constraints": "Do not invent claims.",
                "section_evidence": "(none)",
                "output_template": "## Summary",
                "structured_schema": '{"sections": {}}',
                "output_instruction": "Write only valid JSON matching the schema below.",
            },
            "## Structured JSON Schema",
        ),
        (
            "synonym_triage.recommendation.v1",
            {"proposal_json": "{}", "now_iso": "2026-07-17T00:00:00Z"},
            "Return strict JSON only",
        ),
    ],
)
def test_render_prompt_addendum_is_literal_bounded_and_before_contract(
    prompt_id: str,
    context: dict[str, str],
    contract_anchor: str,
) -> None:
    rendered = render_prompt(
        prompt_id,
        context,
        additional_instructions="  Keep $literal and ${not_a_variable}.\r\nPrefer concise output.  ",
    )

    normalized = "Keep $literal and ${not_a_variable}.\nPrefer concise output."
    assert rendered.text.count(normalized) == 1
    assert rendered.text.index(normalized) < rendered.text.index(contract_anchor)
    assert rendered.customized is True
    assert rendered.addendum_char_count == len(normalized)
    assert rendered.addendum_sha256 == __import__("hashlib").sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def test_render_prompt_without_addendum_keeps_private_provenance_empty() -> None:
    rendered = render_prompt(
        "synonym_triage.recommendation.v1",
        {"proposal_json": "{}", "now_iso": "2026-07-17T00:00:00Z"},
    )

    assert "Additional User Instructions" not in rendered.text
    assert rendered.customized is False
    assert rendered.addendum_sha256 is None
    assert rendered.addendum_char_count == 0


def test_render_prompt_rejects_oversized_addendum() -> None:
    with pytest.raises(ValueError, match="exceeds 4000 characters"):
        render_prompt(
            "synonym_triage.recommendation.v1",
            {"proposal_json": "{}", "now_iso": "2026-07-17T00:00:00Z"},
            additional_instructions="x" * 4001,
        )