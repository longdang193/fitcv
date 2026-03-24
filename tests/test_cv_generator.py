"""
@meta
type: test
scope: unit
domain: cv_generator
covers:
  - build_generation_prompt: evidence and gap constraints appear in prompt
  - select_template_variant: reads job_family from enriched JD, no new classification
  - render_cv_template: Jinja2 rendering with selected evidence slots
excludes:
  - LLM call (generate_cv requires live model — not tested here)
  - CV validation (owned by Task 14, validator.py)
tags:
  - fast
  - ci-safe
"""

import sys
import types
from pathlib import Path

import pytest

from fitcv.cv_generator import build_generation_prompt, render_cv_template, select_template_variant


# ── build_generation_prompt ───────────────────────────────────────────────────

def test_build_generation_prompt_contains_evidence() -> None:
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[{"name": "GA4 Project", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": []},
        template="# {{ candidate.name }}",
    )
    assert "GA4 Project" in prompt
    assert "SQL" in prompt


def test_build_generation_prompt_includes_missing_skills() -> None:
    """Missing skills from the gap should appear in the prompt as constraints."""
    prompt = build_generation_prompt(
        jd={"title": "DE", "required_skills": ["SQL", "Terraform"]},
        evidence=[{"name": "X", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": ["Terraform"]},
        template="",
    )
    assert "Terraform" in prompt


def test_build_generation_prompt_includes_jd_title() -> None:
    prompt = build_generation_prompt(
        jd={"title": "Analytics Engineer", "required_skills": []},
        evidence=[],
        gap={"matched": [], "missing": []},
        template="",
    )
    assert "Analytics Engineer" in prompt


def test_build_generation_prompt_empty_evidence_no_crash() -> None:
    """Empty evidence list must not crash."""
    prompt = build_generation_prompt(
        jd={"title": "DE", "required_skills": []},
        evidence=[],
        gap={"matched": [], "missing": []},
        template="",
    )
    assert isinstance(prompt, str)


def test_build_generation_prompt_includes_grounding_constraints_from_profile() -> None:
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[{"name": "GA4 Project", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": []},
        template="",
        profile={
            "experiences": [{"company": "Acme Analytics GmbH"}],
            "projects": [{"name": "FitCV Pipeline"}],
        },
    )
    assert "Acme Analytics GmbH" in prompt
    assert "FitCV Pipeline" in prompt
    assert "Do not invent employer names" in prompt
    assert "Do not invent project names" in prompt


def test_build_generation_prompt_restricts_skills_section_to_candidate_skill_whitelist() -> None:
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[{"name": "GA4 Project", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": []},
        template="",
        profile={
            "skills": [{"name": "SQL"}, {"name": "Python"}],
            "experiences": [],
            "projects": [],
        },
    )
    assert "In the Skills section, only use skills from this approved list" in prompt
    assert "SQL, Python" in prompt


# ── select_template_variant ───────────────────────────────────────────────────

def test_select_template_variant_returns_known_string() -> None:
    """select_template_variant reads job_family from enriched JD — no new classification."""
    jd = {"job_family": "data_engineering"}
    variant = select_template_variant(jd)
    assert isinstance(variant, str)
    assert len(variant) > 0


def test_select_template_variant_known_families() -> None:
    """Each documented job_family returns a non-empty variant string."""
    families = ["data_engineering", "analytics", "data_science", "ml_engineering"]
    for family in families:
        variant = select_template_variant({"job_family": family})
        assert isinstance(variant, str) and len(variant) > 0


def test_select_template_variant_unknown_family_returns_default() -> None:
    """Unknown or missing job_family → a safe default (not a crash)."""
    assert isinstance(select_template_variant({}), str)
    assert isinstance(select_template_variant({"job_family": None}), str)
    assert isinstance(select_template_variant({"job_family": "unknown_role"}), str)


# ── render_cv_template ────────────────────────────────────────────────────────

def test_render_cv_template_fills_slots() -> None:
    """Jinja2 template renders with selected_skills, selected_experiences, selected_projects."""
    template_str = "Skills: {{ selected_skills | join(', ') }}"
    rendered = render_cv_template(
        template_str=template_str,
        selected_skills=["SQL", "Python"],
        selected_experiences=[],
        selected_projects=[],
        candidate={"name": "Jane Doe"},
        headline="Senior Data Engineer",
        summary="Experienced DE.",
    )
    assert "SQL" in rendered
    assert "Python" in rendered


def test_render_cv_template_candidate_name() -> None:
    template_str = "# {{ candidate.name }}"
    rendered = render_cv_template(
        template_str=template_str,
        selected_skills=[],
        selected_experiences=[],
        selected_projects=[],
        candidate={"name": "Alice"},
        headline="",
        summary="",
    )
    assert "Alice" in rendered


def test_render_cv_template_experience_bullets() -> None:
    template_str = (
        "{% for exp in selected_experiences %}"
        "{{ exp.role }} at {{ exp.company }}"
        "{% endfor %}"
    )
    rendered = render_cv_template(
        template_str=template_str,
        selected_skills=[],
        selected_experiences=[
            {"role": "DE", "company": "Acme", "start": "2021", "end": "2023", "bullets": []}
        ],
        selected_projects=[],
        candidate={"name": "Bob"},
        headline="",
        summary="",
    )
    assert "DE" in rendered
    assert "Acme" in rendered


def test_generate_cv_uses_google_genai_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fitcv.cv_generator import generate_cv

    template_path = tmp_path / "cv_template.md"
    template_path.write_text("# CV Template", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeResponse:
        text = "# Generated CV"

    class FakeModels:
        def generate_content(self, *, model: str, contents: str) -> FakeResponse:
            captured["model"] = model
            captured["contents"] = contents
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs
            self.models = FakeModels()

    fake_genai = types.SimpleNamespace(Client=FakeClient)
    fake_google = types.SimpleNamespace(
        auth=types.SimpleNamespace(default=lambda scopes=None: ("creds", "project"))
    )

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.auth", fake_google.auth)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    setattr(fake_google, "genai", fake_genai)

    result = generate_cv(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[{"name": "GA4 Project", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": []},
        profile={"name": "Jane Doe"},
        config={
            "gcp_project": "fitcv-491123",
            "vertex_location": "us-central1",
            "cv_template_path": str(template_path),
            "cv_generation_model": "gemini-2.5-flash",
        },
    )

    assert result == "# Generated CV"
    assert captured["model"] == "gemini-2.5-flash"
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs["vertexai"] is True
    assert client_kwargs["location"] == "us-central1"
