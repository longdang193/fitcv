"""Tests for fitcv.candidate — all pure unit tests."""

import uuid
from pathlib import Path

import pytest

from fitcv.candidate import (
    flatten_skills,
    load_profile_yaml,
    prepare_profile_rows,
    validate_profile,
)


# ── load_profile_yaml ─────────────────────────────────────────────────────────

def test_load_profile_yaml_returns_dict(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    assert isinstance(profile, dict)


def test_load_profile_yaml_has_required_sections(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    for section in ("experiences", "skills", "projects", "achievements", "preferences"):
        assert section in profile, f"Missing section: {section}"


def test_load_profile_yaml_raises_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_profile_yaml(Path("/nonexistent/profile.yaml"))


# ── validate_profile ────────────────────────────────────────────────────────────

def test_validate_profile_accepts_valid_profile(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    errors = validate_profile(profile)
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_validate_profile_rejects_missing_experiences() -> None:
    errors = validate_profile({"skills": [], "projects": [], "achievements": [], "preferences": {}})
    assert any("experiences" in e for e in errors)


def test_validate_profile_rejects_missing_preferences() -> None:
    errors = validate_profile({"experiences": [], "skills": [], "projects": [], "achievements": {}})
    assert any("preferences" in e for e in errors)


def test_validate_profile_rejects_duplicate_ids() -> None:
    profile = {
        "experiences": [{"id": "exp_1", "bullets": []}],
        "projects": [{"id": "exp_1", "name": "clash"}],  # duplicate
        "achievements": [],
        "skills": [],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert any("Duplicate" in e for e in errors)


def test_validate_profile_rejects_dangling_evidence_ref() -> None:
    profile = {
        "experiences": [{"id": "exp_1", "bullets": []}],
        "projects": [],
        "achievements": [],
        "skills": [{"name": "SQL", "evidence_refs": ["proj_99"]}],  # dangling
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert any("proj_99" in e for e in errors)


# ── flatten_skills ────────────────────────────────────────────────────────────

def test_flatten_skills_extracts_unique() -> None:
    profile = {
        "experiences": [{"bullets": [{"skills": ["SQL", "Python"]}]}],
        "projects": [{"skills": ["SQL", "BigQuery"]}],
    }
    skills = flatten_skills(profile)
    assert "SQL" in skills
    assert len(skills) == len(set(skills))  # no duplicates


def test_flatten_skills_includes_skills_section() -> None:
    profile = {
        "skills": [{"name": "dbt"}, {"name": "Airflow"}],
        "experiences": [],
        "projects": [],
    }
    skills = flatten_skills(profile)
    assert "dbt" in skills
    assert "Airflow" in skills


def test_flatten_skills_empty_profile() -> None:
    profile: dict = {"experiences": [], "projects": [], "skills": []}
    assert flatten_skills(profile) == []


# ── prepare_profile_rows ──────────────────────────────────────────────────────

def test_prepare_profile_rows_returns_all_tables(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    rows = prepare_profile_rows(profile)
    expected_tables = {"profile", "experiences", "projects", "skills", "achievements"}
    assert expected_tables == set(rows.keys())


def test_prepare_profile_rows_profile_has_one_row(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    rows = prepare_profile_rows(profile)
    assert len(rows["profile"]) == 1
    assert "profile_id" in rows["profile"][0]
    assert "preferences" not in rows["profile"][0]  # preferences flattened into columns


def test_prepare_profile_rows_experiences_one_per_bullet(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    total_bullets = sum(
        len(exp.get("bullets", [])) for exp in profile.get("experiences", [])
    )
    rows = prepare_profile_rows(profile)
    assert len(rows["experiences"]) == total_bullets


def test_prepare_profile_rows_skills_has_skill_name(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    rows = prepare_profile_rows(profile)
    assert all("skill_name" in row for row in rows["skills"])


def test_prepare_profile_rows_achievements_has_text(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    rows = prepare_profile_rows(profile)
    assert all("text" in row for row in rows["achievements"])


# ── integration ────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_load_candidate_to_bigquery(sample_profile_path: Path, config: dict) -> None:
    """Integration test — requires GOOGLE_APPLICATION_CREDENTIALS."""
    from fitcv.candidate import load_candidate_to_bigquery
    profile = load_profile_yaml(sample_profile_path)
    load_candidate_to_bigquery(profile, config)  # should not raise
