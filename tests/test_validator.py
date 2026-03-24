"""
@meta
type: test
scope: unit
domain: validator
covers:
  - validate_output: missing section detection, valid flag
  - check_length_constraints: character/line-based page estimate
  - check_chronology: date ordering in source profile experiences
  - check_employer_grounding: invented employer detection in CV text
  - check_project_existence: unknown project detection in CV text
  - check_skill_provenance: skill section validation against candidate knowledge base
  - run_all_validations: aggregated output schema
excludes:
  - Subtle factual errors in bullet text (out of scope for basic grounding)
tags:
  - fast
  - ci-safe
"""

from fitcv.validator import (
    check_chronology,
    check_employer_grounding,
    check_length_constraints,
    check_project_existence,
    check_skill_provenance,
    run_all_validations,
    validate_output,
)


# ── validate_output ───────────────────────────────────────────────────────────

def test_validate_output_catches_missing_sections() -> None:
    cv = "# Name\n## Summary\nHello"
    required_sections = ["Summary", "Skills", "Experience"]
    result = validate_output(cv, required_sections)
    assert result["valid"] is False
    assert "Skills" in result["missing_sections"]
    assert "Experience" in result["missing_sections"]


def test_validate_output_passes_complete_cv() -> None:
    cv = "# Name\n## Summary\nX\n## Skills\nY\n## Experience\nZ"
    required_sections = ["Summary", "Skills", "Experience"]
    result = validate_output(cv, required_sections)
    assert result["valid"] is True
    assert result["missing_sections"] == []


def test_validate_output_empty_required_sections() -> None:
    """No required sections → always valid."""
    result = validate_output("any text", [])
    assert result["valid"] is True


def test_validate_output_returns_full_schema() -> None:
    """validate_output result must include all schema keys."""
    result = validate_output("# CV\n## Skills\nSQL", ["Skills"])
    for key in ("valid", "missing_sections", "grounding_violations", "skill_violations", "warnings"):
        assert key in result


# ── check_length_constraints ──────────────────────────────────────────────────

def test_check_length_constraints_short_cv_passes() -> None:
    """A short CV (< 2 pages) must pass."""
    cv = "# Name\n## Summary\nShort text."
    assert check_length_constraints(cv, max_pages=2) is True


def test_check_length_constraints_very_long_cv_fails() -> None:
    """A very long CV (>> 2 pages) should fail."""
    cv = "\n".join(f"Line {i}: some content here" for i in range(200))
    assert check_length_constraints(cv, max_pages=2) is False


# ── check_chronology ──────────────────────────────────────────────────────────

def test_check_chronology_ordered_returns_empty() -> None:
    """Chronologically ordered experiences → no violations."""
    experiences = [
        {"start": "2022", "end": "2024"},
        {"start": "2019", "end": "2022"},
    ]
    assert check_chronology(experiences) == []


def test_check_chronology_overlap_returns_violation() -> None:
    """Overlapping dates in source profile experiences → violation message."""
    experiences = [
        {"start": "2019", "end": "2024"},
        {"start": "2022", "end": "2024"},
    ]
    violations = check_chronology(experiences)
    assert len(violations) > 0


def test_check_chronology_missing_dates_no_violation() -> None:
    """Missing start/end → skip (cannot determine ordering)."""
    experiences = [{"role": "DE"}]
    assert check_chronology(experiences) == []


# ── check_employer_grounding ──────────────────────────────────────────────────

def test_check_employer_grounding_catches_invented_employer() -> None:
    cv_text = "Worked at InventedCorp from 2020"
    violations = check_employer_grounding(cv_text, known_employers=["ACME", "TechCo"])
    assert len(violations) > 0
    assert any("InventedCorp" in v for v in violations)


def test_check_employer_grounding_passes_known_employer() -> None:
    cv_text = "Engineer at ACME (2019–2022)"
    violations = check_employer_grounding(cv_text, known_employers=["ACME"])
    assert violations == []


def test_check_employer_grounding_empty_known_list_returns_no_violations() -> None:
    """Empty known_employers → no grounding check possible → no violations."""
    violations = check_employer_grounding("Worked at Foo", known_employers=[])
    assert violations == []


# ── check_project_existence ───────────────────────────────────────────────────

def test_check_project_existence_catches_unknown_project() -> None:
    cv_text = "Built the Phantom Pipeline project"
    violations = check_project_existence(cv_text, known_projects=["GA4 Pipeline", "ETL System"])
    assert len(violations) > 0


def test_check_project_existence_passes_known_project() -> None:
    cv_text = "Led the GA4 Pipeline initiative"
    violations = check_project_existence(cv_text, known_projects=["GA4 Pipeline", "ETL System"])
    assert violations == []


def test_check_project_existence_empty_projects_no_violations() -> None:
    """No known_projects → nothing to check → no violations."""
    assert check_project_existence("any text", known_projects=[]) == []


# ── check_skill_provenance ────────────────────────────────────────────────────

def test_check_skill_provenance_catches_unsupported_skill() -> None:
    """Skills section is validated; skill not in candidate knowledge base flagged."""
    cv_text = "## Skills\nSQL, Rust, Python"
    violations = check_skill_provenance(cv_text, candidate_skills=["SQL", "Python"])
    assert any("Rust" in v for v in violations)


def test_check_skill_provenance_passes_known_skills() -> None:
    cv_text = "## Skills\nSQL, Python"
    violations = check_skill_provenance(cv_text, candidate_skills=["SQL", "Python", "BigQuery"])
    assert violations == []


def test_check_skill_provenance_ignores_bullet_text() -> None:
    """Skill-like words in bullet text outside the Skills section must not be flagged."""
    cv_text = "## Experience\n- Built Rust-based tools\n## Skills\nSQL, Python"
    violations = check_skill_provenance(cv_text, candidate_skills=["SQL", "Python"])
    # Rust in bullet text should NOT trigger a violation (Skills section only)
    assert violations == []


# ── run_all_validations ───────────────────────────────────────────────────────

def test_run_all_validations_output_schema() -> None:
    """run_all_validations must return the full schema."""
    profile = {
        "experiences": [{"role": "DE", "company": "ACME", "start": "2020", "end": "2022"}],
        "projects": [{"name": "GA4 Pipeline"}],
        "skills": ["SQL", "Python"],
    }
    cv_text = "# Name\n## Summary\nX\n## Skills\nSQL, Python\n## Experience\nACME"
    result = run_all_validations(cv_text, profile=profile, config={})
    for key in ("valid", "missing_sections", "grounding_violations", "skill_violations", "warnings"):
        assert key in result


def test_run_all_validations_length_warning() -> None:
    """Overly long CV adds a warning but does not flip valid=False on its own."""
    profile: dict = {"experiences": [], "projects": [], "skills": ["SQL"]}
    long_cv = "# CV\n## Summary\nX\n## Skills\nSQL\n## Experience\nACME\n" + "\n".join(
        f"- Bullet {i}" for i in range(200)
    )
    result = run_all_validations(long_cv, profile=profile, config={})
    assert any("length" in w.lower() for w in result["warnings"])
