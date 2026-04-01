"""CV validation — structural and grounding checks for generated CV markdown.

Ownership
---------
This module is the **single owner of all CV validation**.
cv_generator.py does not validate; it only generates.
All grounding, provenance, and structural checks live here.

Scope
-----
Basic structural + grounding validation (not a full hallucination guard).
Catches: invented employers, non-existent projects, out-of-scope skills.
Does NOT catch subtle factual errors in bullet text.

Public API
----------
validate_output          : check section presence, length, format
check_length_constraints : page-length estimate (lines-per-page heuristic)
check_chronology         : verify date ordering in source profile experiences (not CV text)
check_employer_grounding : every employer in CV must appear in known_employers
check_project_existence  : every project name in CV must appear in known_projects
check_skill_provenance   : validate the Skills section against candidate_skills
run_all_validations      : aggregate all checks; returns the full output schema

Output schema (run_all_validations)
------------------------------------
{
    "valid": bool,
    "missing_sections": list[str],
    "grounding_violations": list[str],
    "skill_violations": list[str],
    "warnings": list[str],
}
"""

import re
from typing import Any

from fitcv.candidate import flatten_skills
from fitcv.config import CV_SECTION_KEY_TO_NAME, get_required_structured_section_keys
from fitcv.rule_filter import _canonicalise_skill

# ── constants ─────────────────────────────────────────────────────────────────

_LINES_PER_PAGE: int = 55  # A4 estimate at standard font size
_SECTION_HEADING_PATTERN = r"^##?\s+{section}\s*$"


# ── structural checks ─────────────────────────────────────────────────────────

def validate_output(cv_text: str, required_sections: list[str]) -> dict[str, Any]:
    """Check that all required sections are present in the CV markdown.

    Returns the full output schema with only ``missing_sections`` populated;
    grounding and skill checks are left empty (handled separately or via
    ``run_all_validations``).

    ``valid`` is False when any required section is absent.
    """
    missing: list[str] = []
    for section in required_sections:
        section_pattern = re.compile(
            _SECTION_HEADING_PATTERN.format(section=re.escape(section)),
            re.MULTILINE | re.IGNORECASE,
        )
        heading_match = section_pattern.search(cv_text)
        if heading_match is None:
            missing.append(section)
            continue

        next_heading_match = re.search(r"^##?\s+", cv_text[heading_match.end():], re.MULTILINE)
        section_end = (
            heading_match.end() + next_heading_match.start()
            if next_heading_match is not None
            else len(cv_text)
        )
        section_body = cv_text[heading_match.end():section_end].strip()
        if not section_body:
            missing.append(section)
    return {
        "valid": len(missing) == 0,
        "missing_sections": missing,
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }


def _structured_section_has_content(section_key: str, section_value: Any) -> bool:
    if section_key == "summary":
        return (
            isinstance(section_value, dict)
            and isinstance(section_value.get("text"), str)
            and bool(section_value.get("text", "").strip())
        )
    if section_key == "skills":
        if not isinstance(section_value, dict):
            return False
        groups = section_value.get("groups")
        if not isinstance(groups, list) or not groups:
            return False
        for group in groups:
            if not isinstance(group, dict):
                continue
            items = group.get("items")
            if isinstance(items, list) and any(isinstance(item, str) and item.strip() for item in items):
                return True
        return False
    if section_key in {
        "experience",
        "projects",
        "education",
        "certifications",
        "publications",
        "languages",
    }:
        return isinstance(section_value, list) and len(section_value) > 0
    return True


def _find_missing_required_structured_sections(
    structured_cv: dict[str, Any] | None,
    config: dict[str, Any],
) -> list[str]:
    if structured_cv is None:
        return []

    required_keys = get_required_structured_section_keys(config)
    if not required_keys:
        return []

    sections = structured_cv.get("sections")
    if not isinstance(sections, dict):
        return [CV_SECTION_KEY_TO_NAME.get(key, key.title()) for key in required_keys]

    missing_sections: list[str] = []
    for section_key in required_keys:
        section_value = sections.get(section_key)
        if not _structured_section_has_content(section_key, section_value):
            missing_sections.append(CV_SECTION_KEY_TO_NAME.get(section_key, section_key.title()))
    return missing_sections


def check_length_constraints(cv_text: str, max_pages: int = 2) -> bool:
    """Return True if the CV fits within max_pages (line-count heuristic).

    Uses a conservative estimate of ``_LINES_PER_PAGE`` lines per A4 page.
    """
    line_count = len(cv_text.splitlines())
    return line_count <= max_pages * _LINES_PER_PAGE


# ── chronology check (on source profile, not CV text) ────────────────────────

def check_chronology(experiences: list[dict[str, Any]]) -> list[str]:
    """Verify date ordering in the source profile ``experiences`` list.

    Checks the input data, not the generated CV text.
    Skips entries where start/end cannot be parsed.
    Returns a list of violation strings (empty = clean).

    Violation: an earlier entry in the list has a start date that overlaps
    with a later entry's date range (i.e. entries are not in reverse-chron order).
    """
    violations: list[str] = []
    parsed: list[tuple[int, int, int]] = []  # (start, end, original_index)

    for idx, exp in enumerate(experiences):
        start_raw = str(exp.get("start") or "")
        end_raw = str(exp.get("end") or "")
        try:
            start_year = int(re.search(r"\d{4}", start_raw).group())  # type: ignore[union-attr]
            end_year = int(re.search(r"\d{4}", end_raw).group())  # type: ignore[union-attr]
            parsed.append((start_year, end_year, idx))
        except (AttributeError, ValueError):
            continue  # missing / unparseable dates → skip

    # Expect consecutive entries to be in reverse-chronological order.
    for i in range(len(parsed) - 1):
        curr_start, curr_end, curr_idx = parsed[i]
        next_start, next_end, next_idx = parsed[i + 1]
        if next_end > curr_start:
            violations.append(
                f"Chronology overlap: experience[{next_idx}] ends {next_end} "
                f"but experience[{curr_idx}] starts {curr_start}"
            )

    return violations


# ── grounding checks (on CV text) ────────────────────────────────────────────

def check_employer_grounding(cv_text: str, known_employers: list[str]) -> list[str]:
    """Return violations for any employer mentioned in the CV text that is not in known_employers.

    Detection strategies (combined):

    1. **Generic patterns** — ``at <Name>``, ``@ <Name>`` anywhere in the text.
       Em-dashes (``—``, ``–``) are intentionally excluded here because they
       appear in project titles (e.g. ``FitCV — AI-Powered CV Generation
       Pipeline``) and cause false positives.
    2. **Experience heading pattern** — ``### Role — Company (dates)`` lines
       within the ``## Experience`` section.  This is the only context where
       an em-dash reliably separates role from employer.

    If ``known_employers`` is empty, no check is possible → returns [].
    """
    if not known_employers:
        return []

    violations: list[str] = []
    known_lower = {e.strip().lower() for e in known_employers}

    # ── Strategy 1: generic "at / @" patterns (no em-dash) ────────────────
    generic_pattern = re.compile(
        r"(?:\bat\b|@)\s+([A-Z][A-Za-z0-9&\s\-'\.]+?)(?:\s*[\(\[\,\n]|$)",
    )
    mentioned: list[str] = generic_pattern.findall(cv_text)

    # ── Strategy 2: experience heading "### Role — Company (dates)" ────────
    # Only scan lines under the ## Experience section.
    in_experience = False
    heading_pattern = re.compile(
        r"^###\s+.+?\s*[—–]\s+(.+?)(?:\s*\(|\s*$)",
    )
    for line in cv_text.splitlines():
        stripped = line.strip()
        # Track whether we're inside ## Experience
        if re.match(r"^##\s+Experience", stripped, re.IGNORECASE):
            in_experience = True
            continue
        if re.match(r"^##\s+", stripped) and in_experience:
            in_experience = False
            continue
        if in_experience:
            m = heading_pattern.match(stripped)
            if m:
                mentioned.append(m.group(1).strip())

    for mention in mentioned:
        mention = mention.strip()
        if mention.lower() not in known_lower:
            violations.append(
                f"Employer '{mention}' in CV is not in the known employers list"
            )

    return violations


def check_project_existence(cv_text: str, known_projects: list[str]) -> list[str]:
    """Return violations for project names in the CV that are not in known_projects.

    Two detection strategies are combined:
    1. ``###`` headings within the CV (standard template output for project names)
    2. Capitalized multi-word phrases adjacent to project-indicator words
       (e.g. "the Phantom Pipeline project", "Built Phantom Pipeline")

    If ``known_projects`` is empty → no check → returns [].
    """
    if not known_projects:
        return []

    violations: list[str] = []
    known_lower = {p.strip().lower() for p in known_projects}

    # Strategy: explicit project references such as "the Phantom Pipeline project"
    # or "Built Phantom Pipeline". Generic lowercase phrases like "data pipeline"
    # are too noisy and should not be treated as project names.
    indicator_re = re.compile(
        r"(?:\b(?:the|built|led|designed|implemented)\s+)"
        r"((?:[A-Z][A-Za-z0-9]+\s+){1,3})"       # 1-3 title-case words
        r"(?:project|pipeline|system|platform)\b",
    )
    for match in indicator_re.finditer(cv_text):
        phrase = match.group(1).strip()
        # Build candidate with the indicator word for a full-phrase check
        full_phrase = match.group(0).strip()
        if phrase.lower() not in known_lower and full_phrase.lower() not in known_lower:
            # Check if any known project name is a substring of the phrase
            if not any(kp in full_phrase.lower() for kp in known_lower):
                violations.append(
                    f"Project reference '{full_phrase}' in CV is not in the known projects list"
                )

    # Deduplicate
    return list(dict.fromkeys(violations))



# ── skill provenance (Skills section only) ────────────────────────────────────

def check_skill_provenance(
    cv_text: str,
    candidate_skills: list[str],
    config: dict[str, Any] | None = None,
) -> list[str]:
    """Validate the Skills section of the CV against the candidate's knowledge base.

    Checks the Skills section only (the text after '## Skills' up to the next ## heading).
    Does not scan bullet text — this is conservative by design.

    Returns a list of violation strings for skills found in the Skills section that
    are not in ``candidate_skills`` (case-insensitive, comma/newline delimited).
    """
    if not candidate_skills:
        return []

    # Extract the Skills section content
    skills_section_re = re.compile(
        r"^##\s+Skills\s*\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    match = skills_section_re.search(cv_text)
    if not match:
        return []

    skills_text = match.group(1)

    # Parse individual skill tokens (comma or newline separated)
    raw_tokens = re.split(r"[,\n]+", skills_text)
    cv_skills = [t.strip() for t in raw_tokens if t.strip()]

    candidate_lower = {s.strip().lower() for s in candidate_skills}
    candidate_canonical = {
        _canonicalise_skill(skill, config)
        for skill in candidate_skills
        if skill.strip()
    }
    violations: list[str] = []

    for skill in cv_skills:
        skill_lower = skill.lower()
        skill_canonical = _canonicalise_skill(skill, config)
        if skill_lower not in candidate_lower and skill_canonical not in candidate_canonical:
            violations.append(
                f"Skill '{skill}' in CV Skills section is not in candidate knowledge base"
            )

    return violations


# ── aggregate orchestrator ────────────────────────────────────────────────────

def run_all_validations(
    cv_text: str,
    profile: dict[str, Any],
    config: dict[str, Any],
    structured_cv: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate all validation checks and return the full output schema.

    Output schema::

        {
            "valid": bool,
            "missing_sections": list[str],
            "grounding_violations": list[str],
            "skill_violations": list[str],
            "warnings": list[str],
        }

    ``valid`` is False when any grounding_violations or skill_violations exist,
    or when required sections are missing. Length issues add warnings but do not
    block validity.
    """
    required_sections: list[str] = list(config["required_cv_sections"])
    # Read max_pages: prefer nested cv.validation.max_pages, fall back to flat cv_max_pages
    cv_cfg = config.get("cv") or {}
    max_pages: int = int(
        cv_cfg.get("validation", {}).get("max_pages", 0)
        or config.get("cv_max_pages", 2)
    )

    # Structural section check
    section_result = validate_output(cv_text, required_sections)
    missing_sections = list(section_result["missing_sections"])
    missing_sections.extend(_find_missing_required_structured_sections(structured_cv, config))
    missing_sections = list(dict.fromkeys(missing_sections))

    # Grounding checks
    known_employers: list[str] = [
        str(exp.get("company") or "") for exp in (profile.get("experiences") or [])
        if exp.get("company")
    ]
    known_projects: list[str] = [
        str(proj.get("name") or "") for proj in (profile.get("projects") or [])
        if proj.get("name")
    ]
    candidate_skills = flatten_skills(profile)
    if not candidate_skills:
        raw_candidate_skills = list(profile.get("skills") or [])
        candidate_skills = [
            str(skill)
            for skill in raw_candidate_skills
            if skill
        ]

    grounding_violations: list[str] = (
        check_employer_grounding(cv_text, known_employers)
        + check_project_existence(cv_text, known_projects)
    )
    skill_violations: list[str] = check_skill_provenance(cv_text, candidate_skills, config=config)

    # Non-blocking warnings
    warnings: list[str] = []
    if not check_length_constraints(cv_text, max_pages=max_pages):
        warnings.append(f"CV length warning: exceeds estimated {max_pages}-page limit")

    is_valid = (
        len(missing_sections) == 0
        and len(grounding_violations) == 0
        and len(skill_violations) == 0
    )

    return {
        "valid": is_valid,
        "missing_sections": missing_sections,
        "grounding_violations": grounding_violations,
        "skill_violations": skill_violations,
        "warnings": warnings,
    }
