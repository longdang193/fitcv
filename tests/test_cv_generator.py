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
            "cv": {
                "generation": {
                    "model": "gemini-2.5-flash",
                    "prompt_version": "v1",
                },
                "preset": "europass",
                "composition": {"summary": {"enabled": True}},
                "content_rules": {"evidence_grounded_only": True},
                "validation": {"max_pages": 2},
            },
            "_template_path": str(template_path),
        },
    )

    assert result == "# Generated CV"
    assert captured["model"] == "gemini-2.5-flash"
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs["vertexai"] is True
    assert client_kwargs["location"] == "us-central1"


# ── preset-based config reads ──────────────────────────────────────────────────

def test_generate_cv_reads_model_from_nested_cv_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """generate_cv must read cv.generation.model, not flat cv_generation_model."""
    from fitcv.cv_generator import generate_cv

    template_path_str = "templates/cv_template.md"
    captured_model: list[str] = []

    class FakeResponse:
        text = "# Test CV"

    class FakeModels:
        def generate_content(self, *, model: str, contents: str) -> FakeResponse:
            captured_model.append(model)
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            self.models = FakeModels()

    fake_genai = types.SimpleNamespace(Client=FakeClient)
    fake_google = types.SimpleNamespace(
        auth=types.SimpleNamespace(default=lambda scopes=None: ("creds", "project"))
    )

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.auth", fake_google.auth)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    setattr(fake_google, "genai", fake_genai)

    nested_config = {
        "gcp_project": "fitcv-491123",
        "vertex_location": "us-central1",
        "cv": {
            "generation": {
                "model": "gemini-3-pro",
                "prompt_version": "v2",
            },
            "preset": "europass",
            "composition": {
                "summary": {"enabled": True},
                "experience": {"enabled": True},
                "skills": {"enabled": True},
            },
            "content_rules": {
                "evidence_grounded_only": True,
                "align_jd_terminology": True,
            },
            "validation": {"max_pages": 2},
        },
        # Compatibility: flat key should NOT be used by generate_cv directly
        "cv_generation_model": "WRONG_MODEL",
    }

    template_path = tmp_path / "cv_template.md"
    template_path.write_text("# Template", encoding="utf-8")
    nested_config["_template_path"] = str(template_path)

    generate_cv(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[{"name": "Project", "skills": ["SQL"]}],
        gap={"matched": ["SQL"], "missing": []},
        profile={"name": "Jane Doe"},
        config=nested_config,
    )

    assert captured_model == ["gemini-3-pro"]


def test_get_template_path_for_preset() -> None:
    """cv_generator can resolve template path from preset via cv_presets registry."""
    from fitcv.cv_presets import get_template_path

    preset_path = get_template_path("europass")
    # Both paths should resolve to the same template
    resolved = preset_path
    assert resolved == "templates/cv_template.md"


# ── disabled-section constraints via config ───────────────────────────────────


def test_build_generation_prompt_excludes_disabled_sections() -> None:
    """When config has a section with enabled:false, prompt must contain a 'Do NOT include' constraint."""
    config = {
        "cv": {
            "composition": {
                "education": {"enabled": False},
                "publications": {"enabled": False},
                "experience": {"enabled": True},
                "summary": {"enabled": True},
            }
        }
    }
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[],
        gap={"matched": [], "missing": []},
        template="",
        config=config,
    )
    assert "Do NOT include a 'Education' section" in prompt
    assert "Do NOT include a 'Publications' section" in prompt
    # Enabled sections must NOT have a negative constraint
    assert "Do NOT include a 'Experience' section" not in prompt
    assert "Do NOT include a 'Summary' section" not in prompt


def test_build_generation_prompt_omits_constraint_for_enabled_sections() -> None:
    """When all sections are enabled, no 'Do NOT include' constraint should appear."""
    config = {
        "cv": {
            "composition": {
                "education": {"enabled": True},
                "experience": {"enabled": True},
                "skills": {"enabled": True},
                "summary": {"enabled": True},
            }
        }
    }
    prompt = build_generation_prompt(
        jd={"title": "DE", "required_skills": []},
        evidence=[],
        gap={"matched": [], "missing": []},
        template="",
        config=config,
    )
    assert "Do NOT include" not in prompt


def test_build_generation_prompt_requires_enabled_sections_and_filters_template() -> None:
    """Prompt should explicitly require enabled sections and show only enabled template sections."""
    config = {
        "cv": {
            "composition": {
                "summary": {"enabled": True},
                "education": {"enabled": False},
                "experience": {"enabled": True},
                "skills": {"enabled": False},
                "certifications": {"enabled": True},
                "projects": {"enabled": True},
                "publications": {"enabled": False},
                "languages": {"enabled": True},
            }
        }
    }
    template = """# {{ candidate.name }}

## Summary
{{ summary }}

## Experience
...

## Education
...

## Skills
...

## Certifications
...

## Projects
...

## Publications
...

## Languages
...
"""
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[],
        gap={"matched": [], "missing": []},
        template=template,
        config=config,
    )
    assert "The generated CV MUST include these sections in this order: Summary, Experience, Certifications, Projects, Languages" in prompt
    assert "## Summary" in prompt
    assert "## Experience" in prompt
    assert "## Certifications" in prompt
    assert "## Projects" in prompt
    assert "## Languages" in prompt
    assert "## Education" not in prompt
    assert "## Skills" not in prompt
    assert "## Publications" not in prompt


def test_build_generation_prompt_includes_certification_and_language_evidence() -> None:
    config = {
        "cv": {
            "composition": {
                "certifications": {"enabled": True},
                "languages": {"enabled": True},
            }
        }
    }
    profile = {
        "certifications": [
            {"name": "Google Professional Data Engineer", "issuer": "Google Cloud", "year": 2023},
        ],
        "languages": [
            {"name": "English", "read": "C2", "write": "C2", "speak": "C2"},
        ],
    }
    prompt = build_generation_prompt(
        jd={"title": "Data Engineer", "required_skills": ["SQL"]},
        evidence=[],
        gap={"matched": [], "missing": []},
        template="## Certifications\n...\n## Languages\n...",
        profile=profile,
        config=config,
    )
    assert "Use these candidate certifications when filling the Certifications section" in prompt
    assert "Google Professional Data Engineer — Google Cloud (2023)" in prompt
    assert "Use these candidate languages when filling the Languages section" in prompt
    assert "English (read: C2, write: C2, speak: C2)" in prompt


def test_europass_template_includes_publications_section() -> None:
    template = Path("templates/cv_template.md").read_text(encoding="utf-8")
    assert "## Publications" in template
