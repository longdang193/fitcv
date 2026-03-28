"""CV generation — prompt assembly, template rendering, and LLM invocation.

Scope
-----
This module is responsible for:
  1. Assembling the LLM prompt from evidence, gap analysis, and the Jinja2 template
  2. Rendering the Jinja2 template with selected evidence slots
  3. Calling the LLM to produce a CV markdown string

All validation (grounding, provenance, structural checks) is owned by validator.py.

Config contract (preset-based)
------------------------------
config["cv"]["generation"]["model"]        : LLM model name
config["cv"]["generation"]["prompt_version"] : version tag (for record only)
config["cv"]["preset"]                   : preset name — used to resolve template path
config["cv"]["composition"]             : section composition rules (informative in generator)
config["cv"]["content_rules"]           : content constraints

Template resolution uses cv_presets.get_template_path(config["cv"]["preset"]).
Direct cv_template_path reads are no longer the primary path.

Public API
----------
build_generation_prompt  : assemble the LLM system+user prompt
render_cv_template       : render a Jinja2 template with selected evidence slots
select_template_variant  : read job_family from enriched JD and return a template hint
generate_cv             : call the LLM and return CV markdown (integration)
"""

import textwrap
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateError

from fitcv.candidate import flatten_skills

# ── template variant map ─────────────────────────────────────────────────────
# Maps job_family values (populated by enrichment) to styling hints.
# No new classification is performed here — job_family is read as-is.

_TEMPLATE_VARIANTS: dict[str, str] = {
    "data_engineering": "engineering",
    "analytics":        "analytics",
    "data_science":     "science",
    "ml_engineering":   "engineering",
}

_DEFAULT_VARIANT = "standard"
_SECTION_DISPLAY_NAMES: dict[str, str] = {
    "summary": "Summary",
    "education": "Education",
    "experience": "Experience",
    "skills": "Skills",
    "certifications": "Certifications",
    "projects": "Projects",
    "publications": "Publications",
    "languages": "Languages",
}


# ── template variant selector ─────────────────────────────────────────────────

def select_template_variant(jd: dict[str, Any]) -> str:
    """Return a template variant name for the given enriched job description.

    Reads ``jd["job_family"]`` (populated by the enrichment stage).
    No new classification is performed — the value is used as a lookup key only.
    Unknown or missing job_family → ``"standard"`` (safe default).
    """
    family = str(jd.get("job_family") or "").strip().lower()
    return _TEMPLATE_VARIANTS.get(family, _DEFAULT_VARIANT)


def _get_enabled_section_names(config: dict[str, Any] | None) -> list[str]:
    if config is None:
        return []
    composition = (config.get("cv") or {}).get("composition") or {}
    enabled_sections: list[str] = []
    for section_key, section_cfg in composition.items():
        if isinstance(section_cfg, dict) and section_cfg.get("enabled", True):
            enabled_sections.append(_SECTION_DISPLAY_NAMES.get(section_key, section_key.title()))
    return enabled_sections


def _filter_template_by_enabled_sections(template: str, enabled_sections: list[str]) -> str:
    if not enabled_sections:
        return template

    preamble_lines: list[str] = []
    section_blocks: dict[str, list[str]] = {}
    current_section: str | None = None
    has_seen_section = False

    for line in template.splitlines():
        if line.startswith("## "):
            has_seen_section = True
            current_section = line[3:].strip()
            section_blocks[current_section] = [line]
            continue
        if not has_seen_section:
            preamble_lines.append(line)
            continue
        if current_section is not None:
            section_blocks[current_section].append(line)

    filtered_blocks: list[str] = []
    for section_name in enabled_sections:
        block = section_blocks.get(section_name)
        if block:
            filtered_blocks.append("\n".join(block).strip())

    if not filtered_blocks:
        return template

    preamble = "\n".join(preamble_lines).strip()
    parts = [part for part in [preamble, *filtered_blocks] if part]
    return "\n\n".join(parts) + "\n"


def _format_certification_lines(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    lines: list[str] = []
    for cert in profile.get("certifications") or []:
        if not isinstance(cert, dict):
            continue
        name = str(cert.get("name") or "").strip()
        if not name:
            continue
        issuer = str(cert.get("issuer") or "").strip()
        year = cert.get("year")
        parts = [name]
        if issuer:
            parts.append(issuer)
        line = " — ".join(parts)
        if year:
            line = f"{line} ({year})"
        lines.append(line)
    return lines


def _format_language_lines(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    lines: list[str] = []
    for language in profile.get("languages") or []:
        if not isinstance(language, dict):
            continue
        name = str(language.get("name") or "").strip()
        if not name:
            continue
        if language.get("native"):
            lines.append(f"{name} (native)")
            continue

        proficiency_parts: list[str] = []
        for label, key in (("read", "read"), ("write", "write"), ("speak", "speak")):
            level = str(language.get(key) or "").strip()
            if level:
                proficiency_parts.append(f"{label}: {level}")

        line = name
        if proficiency_parts:
            line = f"{line} ({', '.join(proficiency_parts)})"
        notes = str(language.get("notes") or "").strip()
        if notes:
            line = f"{line} — {notes}"
        lines.append(line)
    return lines


# ── prompt assembly ───────────────────────────────────────────────────────────

def build_generation_prompt(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    template: str,
    profile: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
) -> str:
    """Assemble the full LLM prompt for CV generation.

    The prompt contains:
    - JD context (title + required skills)
    - Selected evidence items (name + skills)
    - Gap constraints (matched and missing skills)
    - The Jinja2 template string as the output format guide

    Returns a plain string suitable for sending to an LLM as a single user message.
    """
    title = str(jd.get("title") or "")
    required_skills = list(jd.get("required_skills") or [])

    evidence_lines = "\n".join(
        f"- {item.get('name', 'Unknown')}: {', '.join(item.get('skills') or [])}"
        for item in evidence
    ) or "(none)"

    matched_skills = list(gap.get("matched") or [])
    missing_skills = list(gap.get("missing") or [])

    constraint_lines: list[str] = []
    if missing_skills:
        constraint_lines.append(
            "Do NOT claim the candidate has the following skills "
            f"(they are missing from their profile): {', '.join(missing_skills)}"
        )
    if matched_skills:
        constraint_lines.append(
            f"The candidate does have: {', '.join(matched_skills)}"
        )
    if profile:
        approved_skills = flatten_skills(profile)
        known_employers = [
            str(exp.get("company") or "")
            for exp in (profile.get("experiences") or [])
            if exp.get("company")
        ]
        known_projects = [
            str(project.get("name") or "")
            for project in (profile.get("projects") or [])
            if project.get("name")
        ]
        if known_employers:
            constraint_lines.append(
                "Do not invent employer names. Only use employers from the candidate profile: "
                + ", ".join(known_employers)
            )
        if known_projects:
            constraint_lines.append(
                "Do not invent project names. Only use project names from the candidate profile: "
                + ", ".join(known_projects)
            )
        if approved_skills:
            constraint_lines.append(
                "In the Skills section, only use skills from this approved list: "
                + ", ".join(approved_skills)
            )
    enabled_section_names = _get_enabled_section_names(config)
    if enabled_section_names:
        constraint_lines.append(
            "The generated CV MUST include these sections in this order: "
            + ", ".join(enabled_section_names)
        )
    if repair_missing_sections:
        constraint_lines.append(
            "Regenerate the CV and fix the previous structural failure by including these missing sections with grounded content: "
            + ", ".join(repair_missing_sections)
        )
        constraint_lines.append(
            "Do not leave required sections empty. Each required section must contain at least one grounded line or bullet."
        )

    # Disabled-section constraints: tell the LLM to omit sections the
    # admin has turned off in the composition config.
    if config is not None:
        composition = (config.get("cv") or {}).get("composition") or {}
        for section_key, section_cfg in composition.items():
            if isinstance(section_cfg, dict) and not section_cfg.get("enabled", True):
                display_name = _SECTION_DISPLAY_NAMES.get(section_key, section_key.title())
                constraint_lines.append(
                    f"Do NOT include a '{display_name}' section."
                )

    constraints = "\n".join(constraint_lines) or "(no specific constraints)"
    filtered_template = _filter_template_by_enabled_sections(template, enabled_section_names)
    section_evidence_lines: list[str] = []
    if "Certifications" in enabled_section_names:
        certification_lines = _format_certification_lines(profile)
        if certification_lines:
            section_evidence_lines.append(
                "Use these candidate certifications when filling the Certifications section:\n"
                + "\n".join(f"- {line}" for line in certification_lines)
            )
    if "Languages" in enabled_section_names:
        language_lines = _format_language_lines(profile)
        if language_lines:
            section_evidence_lines.append(
                "Use these candidate languages when filling the Languages section:\n"
                + "\n".join(f"- {line}" for line in language_lines)
            )
    section_evidence = "\n\n".join(section_evidence_lines) or "(no additional section-specific evidence)"

    return textwrap.dedent(f"""\
        You are a professional CV writer. Generate a tailored CV in markdown format.

        ## Job Description
        Title: {title}
        Required skills: {', '.join(required_skills) or '(none specified)'}

        ## Selected Evidence
        {evidence_lines}

        ## Constraints
        {constraints}

        ## Section-Specific Evidence
        {section_evidence}

        ## Output Template
        {filtered_template}

        Write only the completed CV markdown. Do not add commentary.
    """)


# ── template rendering ────────────────────────────────────────────────────────

def render_cv_template(
    template_str: str,
    selected_skills: list[str],
    selected_experiences: list[dict[str, Any]],
    selected_projects: list[dict[str, Any]],
    candidate: dict[str, Any],
    headline: str,
    summary: str,
) -> str:
    """Render a Jinja2 CV template with the selected evidence slots.

    Args:
        template_str:          Jinja2 template source string.
        selected_skills:       Skills to populate the Skills section.
        selected_experiences:  Experience dicts (role, company, start, end, bullets).
        selected_projects:     Project dicts (name, description).
        candidate:             Candidate metadata dict (must include ``name``).
        headline:              One-line professional headline.
        summary:               Professional summary paragraph.

    Returns the rendered markdown string.
    Raises TemplateError on rendering failure (propagated to caller).
    """
    env = Environment(loader=BaseLoader(), autoescape=False)  # noqa: S701 — output is markdown, not HTML
    tmpl = env.from_string(template_str)
    return tmpl.render(
        selected_skills=selected_skills,
        selected_experiences=selected_experiences,
        selected_projects=selected_projects,
        candidate=candidate,
        headline=headline,
        summary=summary,
    )


# ── LLM generation (integration) ─────────────────────────────────────────────

def _resolve_template_path(config: dict[str, Any]) -> str:
    """Resolve the CV template path from the preset-based config.

    Priority:
    1. config["_template_path"] — test shim (used by generate_cv test fixtures)
    2. cv_presets.get_template_path(config["cv"]["preset"])
    3. Fallback to flat cv_template_path for legacy compatibility
    """
    if "_template_path" in config:
        return str(config["_template_path"])
    cv_cfg = config.get("cv") or {}
    preset = str(cv_cfg.get("preset", ""))
    if preset:
        from fitcv.cv_presets import get_template_path

        return get_template_path(preset)
    return str(config.get("cv_template_path", "templates/cv_template.md"))


def generate_cv(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    repair_missing_sections: list[str] | None = None,
) -> str:
    """Call the LLM to generate a tailored CV markdown string.

    Reads template from cv_presets.get_template_path(config["cv"]["preset"])
    (via _resolve_template_path), not from cv_template_path directly.
    Reads model from config["cv"]["generation"]["model"] (nested; falls back to
    flat cv_generation_model for compatibility).

    Uses ``google.genai`` against Vertex AI.
    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    import pathlib
    import google.auth  # type: ignore[import-untyped]
    from google import genai  # type: ignore[import-untyped]

    from fitcv.config import get_vertex_location

    template_path = _resolve_template_path(config)
    template_str = pathlib.Path(template_path).read_text(encoding="utf-8")

    prompt = build_generation_prompt(
        jd=jd,
        evidence=evidence,
        gap=gap,
        template=template_str,
        profile=profile,
        config=config,
        repair_missing_sections=repair_missing_sections,
    )

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = genai.Client(
        vertexai=True,
        project=str(config.get("gcp_project", "")),
        location=get_vertex_location(config),
        credentials=creds,
    )

    # Read model from nested cv.generation.model (primary); fall back to flat key
    cv_cfg = config.get("cv") or {}
    model_name = str(cv_cfg.get("generation", {}).get("model") or config.get("cv_generation_model", ""))
    response = client.models.generate_content(model=model_name, contents=prompt)
    return str(response.text)
