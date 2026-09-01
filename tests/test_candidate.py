"""Tests for fitcv.candidate — all pure unit tests."""

import copy
import hashlib
import json
import uuid
from pathlib import Path

import pytest

from fitcv.candidate import (
    canonical_candidate_checksum,
    candidate_profile_field_schema,
    converge_candidate_profile_for_runtime,
    flatten_skills,
    infer_effective_preferences,
    load_profile_json_text,
    load_profile_yaml,
    prepare_profile_rows,
    validate_profile,
)
import fitcv.candidate as candidate_module
import fitcv.evidence as evidence_module
from fitcv_cp.candidate_profile_seeds import (
    CANDIDATE_PROFILE_SEEDS,
    SEED_MANIFEST_REVISION,
    build_candidate_profile_seeds,
)


_VALID_PROFILE_DICT: dict = {
    "experiences": [{"id": "exp_1", "role": "DE", "company": "X", "bullets": []}],
    "skills": [{"name": "SQL"}],
    "projects": [],
    "achievements": [],
    "preferences": {"seniority_target": "mid", "location_types": ["remote"]},
}

def test_runtime_convergence_adapts_v1_without_mutating_snapshot() -> None:
    profile = {
        "name": "Fresh Graduate",
        "experiences": [],
        "education": [
            {
                "id": "edu_1",
                "degree": "MSc",
                "institution": "Example University",
                "thesis": {"title": "Churn", "summary": "Built Python churn models"},
                "courses": ["Applied Statistics"],
            }
        ],
        "projects": [],
        "achievements": [],
        "certifications": [{"id": "cert_1", "name": "SQL Certificate", "issuer": "Example"}],
        "volunteering": [
            {"id": "vol_1", "organization": "Data Club", "role": "Mentor", "description": "Mentored SQL learners"}
        ],
        "languages": [],
        "skills": [{"id": "skill_1", "name": "Python", "evidence_refs": ["edu_1"]}],
        "preferences": {"target_role": "Data Analyst"},
    }
    before = copy.deepcopy(profile)
    checksum = canonical_candidate_checksum(profile)

    converged = converge_candidate_profile_for_runtime(profile)

    assert converged["schema_version"] == "candidate-profile.v2"
    assert [item["kind"] for item in converged["education"][0]["evidence"]] == ["thesis", "course"]
    assert converged["certifications"][0]["evidence"][0]["kind"] == "certification_proof"
    assert converged["volunteering"][0]["evidence"][0]["kind"] == "volunteer_contribution"
    assert set(converged["skills"][0]["evidence_refs"]) == {
        item["id"] for item in converged["education"][0]["evidence"]
    }
    assert profile == before
    assert canonical_candidate_checksum(profile) == checksum
    assert converge_candidate_profile_for_runtime(profile) == converged

def test_runtime_loader_accepts_canonical_v2_preferences() -> None:
    canonical = converge_candidate_profile_for_runtime({**_VALID_PROFILE_DICT, "name": "Candidate"})

    loaded = load_profile_json_text(json.dumps(canonical))

    assert loaded["schema_version"] == "candidate-profile.v2"
    assert loaded["preferences"] == canonical["search_preferences"]

def test_runtime_convergence_normalizes_legacy_year_only_ranges() -> None:
    converged = converge_candidate_profile_for_runtime(
        {
            "name": "Legacy Candidate",
            "experiences": [
                {
                    "role": "Data Engineer",
                    "company": "Example",
                    "start": "2020",
                    "end": "2022",
                }
            ],
            "projects": [],
            "skills": [],
        }
    )

    assert converged["experiences"][0]["start"] == "2020-01"
    assert converged["experiences"][0]["end"] == "2022-12"

def test_runtime_convergence_rejects_invalid_v2_references() -> None:
    profile = converge_candidate_profile_for_runtime({**_VALID_PROFILE_DICT, "name": "Candidate"})
    profile["skills"][0]["evidence_refs"] = ["missing_evidence"]

    with pytest.raises(ValueError, match="dangling evidence_refs"):
        converge_candidate_profile_for_runtime(profile)

def test_runtime_convergence_rejects_duplicate_evidence_ids() -> None:
    profile = converge_candidate_profile_for_runtime({**_VALID_PROFILE_DICT, "name": "Candidate"})
    profile["experiences"][0]["evidence"] = [
        {
            "id": "ev_duplicate",
            "kind": "work_achievement",
            "text": "First",
            "source_refs": profile["experiences"][0]["source_refs"],
        },
        {
            "id": "ev_duplicate",
            "kind": "work_achievement",
            "text": "Second",
            "source_refs": profile["experiences"][0]["source_refs"],
        },
    ]

    with pytest.raises(ValueError, match="duplicate ID: ev_duplicate"):
        converge_candidate_profile_for_runtime(profile)


def test_candidate_profile_v2_field_schema_is_stable_and_symmetric() -> None:
    schema = candidate_profile_field_schema()

    assert schema["schema_version"] == "candidate-profile-fields.v1"
    assert len(schema["checksum"]) == 64
    assert schema["date_grammar"] == {
        "format": "YYYY-MM",
        "present_value": "Present",
        "optional": True,
    }
    assert [section["id"] for section in schema["sections"]] == [
        "identity",
        "contact",
        "experiences",
        "education",
        "projects",
        "achievements",
        "certifications",
        "volunteering",
        "languages",
        "interests",
        "search_preferences",
        "skills",
        "role_families",
        "domain_tags",
        "responsibility_themes",
    ]
    collections = {
        section["id"]: section
        for section in schema["sections"]
        if section["shape"] == "collection"
    }
    assert collections["experiences"]["item"]["evidence"]["shape"] == "collection"
    assert collections["education"]["item"]["evidence"] == collections["experiences"]["item"]["evidence"]
    evidence_item = collections["experiences"]["item"]["evidence"]["item"]
    assert list(evidence_item) == ["id", "kind", "title", "start", "end", "text", "source_refs"]
    assert evidence_item["kind"]["options"] == [
        {"value": "work_achievement", "label": "Work achievement"},
        {"value": "work_responsibility", "label": "Work responsibility"},
        {"value": "thesis", "label": "Thesis"},
        {"value": "seminar", "label": "Seminar"},
        {"value": "course", "label": "Course"},
        {"value": "academic_project", "label": "Academic project"},
        {"value": "project_highlight", "label": "Project highlight"},
        {"value": "achievement", "label": "Achievement"},
        {"value": "certification_proof", "label": "Certification proof"},
        {"value": "volunteer_contribution", "label": "Volunteer contribution"},
    ]
    assert evidence_item["text"] == {
        "shape": "textarea",
        "label": "Evidence text",
        "description": "Reviewed statement projected into runtime candidate evidence.",
        "required": True,
    }
    identity = next(section for section in schema["sections"] if section["id"] == "identity")
    contact = next(section for section in schema["sections"] if section["id"] == "contact")
    education = collections["education"]
    projects = collections["projects"]
    certifications = collections["certifications"]
    languages = collections["languages"]
    assert identity["label"] == "Profile"
    assert identity["fields"]["headline"]["label"] == "Professional headline"
    assert contact["fields"]["linkedin"]["label"] == "LinkedIn URL"
    assert contact["fields"]["github"]["label"] == "GitHub URL"
    assert contact["fields"]["website"]["label"] == "Website URL"
    assert education["required_one_of"] == ["degree", "field"]
    assert education["item"]["degree"]["label"] == "Degree or credential"
    assert education["item"]["field"]["label"] == "Field of study"
    assert projects["item"]["name"]["label"] == "Project name"
    assert projects["item"]["context"]["label"] == "Context or organization"
    assert projects["item"]["url"]["label"] == "Project URL"
    assert certifications["item"]["name"]["label"] == "Certification"
    assert certifications["item"]["url"]["label"] == "Credential URL"
    assert languages["item"]["name"]["label"] == "Language"
    assert collections["role_families"]["label"] == "Role Families"
    assert collections["role_families"]["item_label"] == "Role Family"
    assert collections["domain_tags"]["label"] == "Domain Tags"
    assert collections["responsibility_themes"]["label"] == "Responsibility Themes"
    assert collections["skills"]["item"] == collections["domain_tags"]["item"]
    assert collections["skills"]["item"]["support_status"] == {
        "shape": "status",
        "label": "Support status",
        "required": True,
    }
    assert collections["skills"]["description"] == "Each skill is independently editable and traceable."
    assert collections["skills"]["item_label"] == "Skill"
    for section in schema["sections"]:
        if section["stage"] != "baseline" or section["id"] in {"interests", "search_preferences"}:
            continue
        fields = section.get("fields") or section.get("item") or {}
        if section["shape"] == "collection":
            assert section.get("description"), section["id"]
            assert section.get("item_label"), section["id"]
        for field_name, field in fields.items():
            if field_name in {"id", "source_refs", "evidence"}:
                continue
            assert field.get("description"), f"{section['id']}.{field_name}"
    serialized = json.dumps(schema, sort_keys=True)
    assert '"current"' not in serialized
    assert schema == candidate_profile_field_schema()


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

def test_load_profile_yaml_validates_required_sections(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("skills: []\nprojects: []\nachievements: []\npreferences: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="validation failed"):
        load_profile_yaml(profile_path)

def test_candidate_profile_seed_manifest_builds_exact_validated_overlays(
    sample_profile_path: Path,
) -> None:
    base_profile = load_profile_yaml(sample_profile_path)

    rows = build_candidate_profile_seeds(base_profile)

    assert SEED_MANIFEST_REVISION == "candidate-profile-seeds.v1"
    assert [seed["candidate_profile_id"] for seed in CANDIDATE_PROFILE_SEEDS] == [
        "candidate-product-data",
        "candidate-analytics",
        "candidate-platform",
    ]
    assert [row["name"] for row in rows] == [
        "Product Data Specialist",
        "Analytics & Operations",
        "Data Platform Engineer",
    ]
    assert [row["sort_order"] for row in rows] == [10, 20, 30]
    assert [row["is_default"] for row in rows] == [True, False, False]
    assert all(row["is_active"] is True and row["revision"] == 1 for row in rows)
    assert all(row["seed_manifest_revision"] == SEED_MANIFEST_REVISION for row in rows)

    expected_preferences = [
        ("Product Data Specialist", ["analytics"], ["product"]),
        ("Analytics & Operations", ["analytics"], ["operations"]),
        ("Data Platform Engineer", ["data_engineering"], ["data platform"]),
    ]
    preserved = {key: value for key, value in base_profile.items() if key != "preferences"}
    for row, (target_role, role_families, domains) in zip(rows, expected_preferences):
        profile = json.loads(row["profile_json"])
        assert {key: value for key, value in profile.items() if key != "preferences"} == preserved
        assert profile["preferences"] == {
            **base_profile["preferences"],
            "target_role": target_role,
            "role_families": role_families,
            "domains": domains,
        }
        assert validate_profile(profile) == []
        assert row["checksum"] == hashlib.sha256(row["profile_json"].encode("utf-8")).hexdigest()


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


def test_validate_profile_accepts_certification_evidence_ref() -> None:
    """Skills may reference certification IDs without being flagged as dangling."""
    profile = {
        "experiences": [],
        "projects": [],
        "achievements": [],
        "certifications": [
            {
                "id": "cert_1",
                "name": "Azure AI Engineer Associate",
                "issuer": "Microsoft",
            }
        ],
        "skills": [{"name": "Azure AI", "evidence_refs": ["cert_1"]}],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert errors == [], f"Unexpected errors: {errors}"


def test_validate_profile_accepts_education_evidence_ref() -> None:
    """Skills may reference education IDs without being flagged as dangling."""
    profile = {
        "experiences": [],
        "projects": [],
        "achievements": [],
        "education": [{"id": "edu_1", "degree": "M.Sc.", "institution": "TU Berlin"}],
        "skills": [{"name": "Apache Spark", "evidence_refs": ["edu_1"]}],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert errors == [], f"Unexpected errors: {errors}"

def test_validate_profile_accepts_string_skill_entry_type_for_compatibility() -> None:
    profile = {
        "experiences": [{"id": "exp_1", "bullets": []}],
        "projects": [],
        "achievements": [],
        "skills": ["SQL"],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert errors == []


def test_validate_profile_rejects_non_string_non_dict_skill_entry_type() -> None:
    profile = {
        "experiences": [{"id": "exp_1", "bullets": []}],
        "projects": [],
        "achievements": [],
        "skills": [123],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert any("Invalid skill entry type" in e for e in errors)

def test_validate_profile_rejects_invalid_achievement_entry_type() -> None:
    profile = {
        "experiences": [{"id": "exp_1", "bullets": []}],
        "projects": [],
        "achievements": ["Won prize"],
        "skills": [],
        "preferences": {},
    }
    errors = validate_profile(profile)
    assert any("Invalid achievement entry type" in e for e in errors)


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


def test_infer_effective_preferences_fills_missing_values_from_recent_profile_evidence() -> None:
    profile = {
        "preferences": {"location_types": ["remote", "hybrid"]},
        "experiences": [
            {"role": "Senior Data Analyst", "role_family": "analytics", "domain_tags": ["banking"], "bullets": []},
            {"role": "BI Analyst", "domain_tags": ["retail"], "bullets": []},
        ],
        "projects": [{"name": "KPI Dashboard", "domain_tags": ["retail"]}],
        "skills": [],
        "achievements": [],
    }
    config = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "data analyst": "data analyst",
                "senior data analyst": "data analyst",
                "bi analyst": "data analyst",
            },
            "role_family_by_role": {
                "data analyst": "analytics",
            },
        }
    }

    result = infer_effective_preferences(profile, config)

    assert result["effective_preferences"] == {
        "target_role": "Data Analyst",
        "role_families": ["analytics"],
        "domains": ["banking", "retail"],
        "location_types": ["remote", "hybrid"],
    }
    assert result["preference_sources"]["target_role"] == "inferred_recent_experience"
    assert result["preference_sources"]["role_families"] == "inferred_role_family_map"
    assert result["preference_sources"]["domains"] == "inferred_profile_domain_tags"
    assert result["preference_sources"]["location_types"] == "explicit_yaml"


def test_infer_effective_preferences_preserves_explicit_preferences() -> None:
    profile = {
        "preferences": {
            "target_role": "Analytics Engineer",
            "role_families": ["data_engineering"],
            "domains": ["fintech"],
        },
        "experiences": [
            {"role": "Senior Data Analyst", "role_family": "analytics", "domain_tags": ["banking"], "bullets": []},
        ],
        "projects": [],
        "skills": [],
        "achievements": [],
    }
    config = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "senior data analyst": "data analyst",
                "data analyst": "data analyst",
            },
            "role_family_by_role": {
                "data analyst": "analytics",
            },
        }
    }

    result = infer_effective_preferences(profile, config)

    assert result["effective_preferences"]["target_role"] == "Analytics Engineer"
    assert result["effective_preferences"]["role_families"] == ["data_engineering"]
    assert result["effective_preferences"]["domains"] == ["fintech"]
    assert result["preference_sources"]["target_role"] == "explicit_yaml"
    assert result["preference_sources"]["role_families"] == "explicit_yaml"
    assert result["preference_sources"]["domains"] == "explicit_yaml"


def test_infer_role_family_uses_builtin_fallbacks_without_taxonomy_config() -> None:
    from fitcv.candidate import infer_role_family

    assert infer_role_family("Data Scientist") == "data_science"
    assert infer_role_family("Business Intelligence Analyst") == "analytics"


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

def test_prepare_profile_rows_supports_string_skills() -> None:
    profile = {
        "name": "Candidate",
        "headline": "",
        "summary": "",
        "preferences": {},
        "experiences": [],
        "projects": [],
        "skills": ["SQL"],
        "achievements": [],
    }
    rows = prepare_profile_rows(profile)
    assert rows["skills"] == [{
        "skill_name": "SQL",
        "level": "",
        "years": None,
        "evidence_refs": [],
        "updated_at": rows["skills"][0]["updated_at"],
    }]

def test_normalize_text_list_case_insensitive_parity_candidate_vs_evidence() -> None:
    values = [" Banking ", "banking", "BANKING", "", "  "]
    candidate_values = candidate_module._normalize_text_list(values)
    evidence_values = evidence_module._normalize_text_list(values)
    assert candidate_values == ["banking"]
    assert [v.lower() for v in evidence_values] == candidate_values


def test_prepare_profile_rows_achievements_has_text(sample_profile_path: Path) -> None:
    profile = load_profile_yaml(sample_profile_path)
    rows = prepare_profile_rows(profile)
    assert all("text" in row for row in rows["achievements"])


# ── integration ────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_load_candidate_profile(sample_profile_path: Path, config: dict) -> None:
    """Integration test — requires FITCV_LLM_API_KEY."""
    from fitcv.candidate import load_candidate_profile
    profile = load_profile_yaml(sample_profile_path)
    load_candidate_profile(profile, config)  # should not raise


# ── Task 3: load_profile_json_text ───────────────────────────────────────────

import json as _json


def test_load_profile_json_text_valid_returns_dict() -> None:
    payload = _json.dumps(_VALID_PROFILE_DICT)
    result = load_profile_json_text(payload)
    assert isinstance(result, dict)
    assert "experiences" in result


def test_load_profile_json_text_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_profile_json_text("{not json}")


def test_load_profile_text_json_hint_matches_load_profile_json_text_error_contract() -> None:
    from fitcv.candidate import load_profile_text

    with pytest.raises(ValueError, match="Invalid JSON in candidate profile:"):
        load_profile_json_text("{not json}")
    with pytest.raises(ValueError, match="Invalid JSON in candidate profile:"):
        load_profile_text("{not json}", format_hint="json")


def test_load_profile_json_text_array_raises() -> None:
    """Top-level array is not a valid candidate profile (must be an object)."""
    with pytest.raises(ValueError, match="JSON object"):
        load_profile_json_text("[]")


def test_load_profile_json_text_missing_section_raises() -> None:
    """Profile missing required sections fails validate_profile."""
    incomplete = {"experiences": [], "skills": []}
    with pytest.raises(ValueError, match="validation failed"):
        load_profile_json_text(_json.dumps(incomplete))


def test_load_profile_json_text_preserves_all_required_sections() -> None:
    result = load_profile_json_text(_json.dumps(_VALID_PROFILE_DICT))
    for section in ("experiences", "skills", "projects", "achievements", "preferences"):
        assert section in result


def test_load_profile_json_text_normalizes_additive_alignment_metadata() -> None:
    payload = _json.dumps(
        {
            "experiences": [
                {
                    "id": "exp_1",
                    "role": "Data Analyst",
                    "company": "Acme",
                    "role_family": " analytics ",
                    "domain_tags": [" banking ", "", None, "fintech"],
                    "responsibility_themes": [" dashboarding ", " ", "kpi_reporting"],
                    "bullets": [],
                }
            ],
            "skills": [{"name": "SQL"}],
            "projects": [
                {
                    "id": "proj_1",
                    "name": "Dashboards",
                    "domain_tags": [" banking "],
                    "responsibility_themes": ["reporting_automation", ""],
                }
            ],
            "achievements": [
                {
                    "id": "ach_1",
                    "text": "Improved reporting",
                    "domain_tags": [" banking ", ""],
                }
            ],
            "preferences": {
                "target_role": " Data Analyst ",
                "seniority_target": " senior ",
                "salary_range": " €80,000 — €100,000 ",
                "notice_period": " 3 months ",
                "location_types": [" Remote ", "", "HYBRID", "remote"],
                "locations": [" Berlin ", "", "Munich", "berlin"],
                "role_families": [" analytics ", "", "data_science"],
                "domains": [" banking ", "", "fintech"],
                "exclude_contract_types": [" Internship ", "", "Contract", "internship"],
                "exclude_experience_levels": [" Internship ", "", "Entry level", "internship"],
            },
        }
    )

    result = load_profile_json_text(payload)

    assert result["preferences"]["target_role"] == "Data Analyst"
    assert result["preferences"]["seniority_target"] == "senior"
    assert result["preferences"]["salary_range"] == "€80,000 — €100,000"
    assert result["preferences"]["notice_period"] == "3 months"
    assert result["preferences"]["location_types"] == ["remote", "hybrid"]
    assert result["preferences"]["locations"] == ["berlin", "munich"]
    assert result["preferences"]["role_families"] == ["analytics", "data_science"]
    assert result["preferences"]["domains"] == ["banking", "fintech"]
    assert result["preferences"]["exclude_contract_types"] == ["internship", "contract"]
    assert result["preferences"]["exclude_experience_levels"] == ["internship", "entry level"]
    assert result["experiences"][0]["role_family"] == "analytics"
    assert result["experiences"][0]["domain_tags"] == ["banking", "fintech"]
    assert result["experiences"][0]["responsibility_themes"] == ["dashboarding", "kpi_reporting"]
    assert result["projects"][0]["domain_tags"] == ["banking"]
    assert result["projects"][0]["responsibility_themes"] == ["reporting_automation"]
    assert result["achievements"][0]["domain_tags"] == ["banking"]
"""
@meta
type: test
scope: unit
domain: candidate
covers:
  - candidate model behavior
excludes:
  - external persistence
tags:
  - fast
  - ci-safe
"""
