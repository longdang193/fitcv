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


# ── constants ─────────────────────────────────────────────────────────────────

_LINES_PER_PAGE: int = 55  # A4 estimate at standard font size


# ── structural checks ─────────────────────────────────────────────────────────

def validate_output(cv_text: str, required_sections: list[str]) -> dict[str, Any]:
    """Check that all required sections are present in the CV markdown.

    Returns the full output schema with only ``missing_sections`` populated;
    grounding and skill checks are left empty (handled separately or via
    ``run_all_validations``).

    ``valid`` is False when any required section is absent.
    """
    missing: list[str] = [
        section for section in required_sections
        if not re.search(rf"^##?\s+{re.escape(section)}", cv_text, re.MULTILINE | re.IGNORECASE)
    ]
    return {
        "valid": len(missing) == 0,
        "missing_sections": missing,
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }


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

    Detection strategy: look for patterns like "at <Name>" or "— <Name>" in the CV.
    Checks each known employer for presence; if fewer employers appear than mentioned
    in the text, return a conservative warning.

    If ``known_employers`` is empty, no check is possible → returns [].
    """
    if not known_employers:
        return []

    violations: list[str] = []

    # Find candidate employer tokens: capitalised words/phrases near "at", "—", "@"
    employer_pattern = re.compile(
        r"(?:at|@|–|—)\s+([A-Z][A-Za-z0-9&\s\-'\.]+?)(?:\s*[\(\[\,\n]|$)",
    )
    mentioned: list[str] = employer_pattern.findall(cv_text)

    known_lower = {e.strip().lower() for e in known_employers}

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

    # Strategy 1: ### headings (generated from template Projects section)
    heading_re = re.compile(r"^###\s+(.+)$", re.MULTILINE)
    for heading in heading_re.findall(cv_text):
        heading_stripped = heading.strip()
        if heading_stripped.lower() not in known_lower:
            violations.append(
                f"Project '{heading_stripped}' in CV is not in the known projects list"
            )

    # Strategy 2: capitalized phrases adjacent to project-indicator words
    # Pattern: optional "the " + 1-3 Title-Case words + optional "project|pipeline|system|platform"
    indicator_re = re.compile(
        r"(?:the\s+)?"
        r"((?:[A-Z][A-Za-z0-9]+\s+){1,3})"       # 1-3 title-case words
        r"(?:project|pipeline|system|platform)\b",
        re.IGNORECASE,
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

def check_skill_provenance(cv_text: str, candidate_skills: list[str]) -> list[str]:
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
    violations: list[str] = []

    for skill in cv_skills:
        if skill.lower() not in candidate_lower:
            violations.append(
                f"Skill '{skill}' in CV Skills section is not in candidate knowledge base"
            )

    return violations


# ── aggregate orchestrator ────────────────────────────────────────────────────

def run_all_validations(
    cv_text: str,
    profile: dict[str, Any],
    config: dict[str, Any],
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
    required_sections: list[str] = list(
        config.get("required_cv_sections") or ["Summary", "Skills", "Experience"]
    )
    max_pages: int = int(config.get("cv_max_pages") or 2)

    # Structural section check
    section_result = validate_output(cv_text, required_sections)
    missing_sections: list[str] = section_result["missing_sections"]

    # Grounding checks
    known_employers: list[str] = [
        str(exp.get("company") or "") for exp in (profile.get("experiences") or [])
        if exp.get("company")
    ]
    known_projects: list[str] = [
        str(proj.get("name") or "") for proj in (profile.get("projects") or [])
        if proj.get("name")
    ]
    candidate_skills: list[str] = list(profile.get("skills") or [])

    grounding_violations: list[str] = (
        check_employer_grounding(cv_text, known_employers)
        + check_project_existence(cv_text, known_projects)
    )
    skill_violations: list[str] = check_skill_provenance(cv_text, candidate_skills)

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
