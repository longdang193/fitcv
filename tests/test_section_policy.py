from fitcv.section_policy import (
    SECTION_POLICY_GROUP_BY_KEY,
    SECTION_POLICY_GROUP_PROFILE_BASELINE,
    SECTION_POLICY_GROUP_ROLE_TAILORED,
    SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA,
    SECTION_POLICY_STATE_INCLUDED,
    section_policy_decisions,
)


def _config(enabled: bool = True) -> dict:
    return {
        "cv": {
            "composition": {
                "summary": {"enabled": enabled},
                "education": {"enabled": enabled},
                "experience": {"enabled": enabled},
                "skills": {"enabled": enabled},
                "certifications": {"enabled": enabled},
                "projects": {"enabled": enabled},
                "publications": {"enabled": enabled},
                "languages": {"enabled": enabled},
            }
        }
    }


def test_section_policy_groups_are_mece_for_all_composition_sections() -> None:
    expected_sections = {
        "summary",
        "education",
        "experience",
        "skills",
        "certifications",
        "projects",
        "publications",
        "languages",
    }
    assert set(SECTION_POLICY_GROUP_BY_KEY) == expected_sections
    assert set(SECTION_POLICY_GROUP_BY_KEY.values()) == {
        SECTION_POLICY_GROUP_PROFILE_BASELINE,
        SECTION_POLICY_GROUP_ROLE_TAILORED,
    }


def test_section_policy_profile_baseline_sections_require_meaningful_profile_rows() -> None:
    empty_profile = {"education": [], "languages": []}
    education_policy = section_policy_decisions(
        section_key="education",
        config=_config(),
        profile=empty_profile,
    )
    languages_policy = section_policy_decisions(
        section_key="languages",
        config=_config(),
        profile=empty_profile,
    )
    assert education_policy["state"] == SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA
    assert education_policy["required"] is False
    assert languages_policy["state"] == SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA
    assert languages_policy["required"] is False


def test_section_policy_languages_included_when_profile_has_meaningful_data() -> None:
    policy = section_policy_decisions(
        section_key="languages",
        config=_config(),
        profile={"languages": [{"name": "English", "level": "C2"}]},
    )
    assert policy["state"] == SECTION_POLICY_STATE_INCLUDED
    assert policy["required"] is True
    assert policy["reason_code"] == "eligible_profile_data"


def test_section_policy_certifications_require_selected_evidence() -> None:
    config = _config()
    profile = {"certifications": [{"name": "AWS SA", "issuer": "AWS", "year": "2024"}]}

    without_evidence = section_policy_decisions(
        section_key="certifications",
        config=config,
        profile=profile,
        evidence_selected_certifications=[],
    )
    with_evidence = section_policy_decisions(
        section_key="certifications",
        config=config,
        profile=profile,
        evidence_selected_certifications=[{"name": "AWS SA", "issuer": "AWS", "year": "2024"}],
    )

    assert without_evidence["state"] == SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA
    assert without_evidence["required"] is False
    assert with_evidence["state"] == SECTION_POLICY_STATE_INCLUDED
    assert with_evidence["required"] is True


def test_section_policy_role_tailored_non_certification_sections_include_when_enabled() -> None:
    policy = section_policy_decisions(
        section_key="summary",
        config=_config(),
        profile={},
    )
    assert policy["state"] == SECTION_POLICY_STATE_INCLUDED
    assert policy["required"] is True
