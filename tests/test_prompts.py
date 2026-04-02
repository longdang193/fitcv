"""Tests for the shared prompt registry and renderer."""

import pytest

from fitcv.prompts import get_prompt_definition, render_prompt


def test_get_prompt_definition_returns_enrich_extraction_metadata() -> None:
    definition = get_prompt_definition("enrich.extraction.v1")

    assert definition.prompt_id == "enrich.extraction.v1"
    assert definition.stage_id == "enrich"
    assert definition.version == "v1"
    assert definition.template_path.name == "enrich_extraction_v1.md"


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


def test_render_prompt_raises_for_missing_required_variables() -> None:
    with pytest.raises(ValueError, match="missing template variables"):
        render_prompt("enrich.extraction.v1", {"description": "Only description"})


def test_get_prompt_definition_rejects_unknown_prompt_id() -> None:
    with pytest.raises(KeyError):
        get_prompt_definition("enrich.extraction.v999")
