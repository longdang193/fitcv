from unittest.mock import Mock

import pytest

from fitcv.agentic_cv_generation import (
    _backfill_required_sections_from_profile,
    _run_repair_cycle,
)


def test_local_backfill_does_not_include_unselected_generated_nested_claims() -> None:
    for section, profile_key, entry, selected_id, expected_bullets in (
        (
            "experience",
            "experiences",
            {
                "id": "exp_shared",
                "role": "Data Analyst",
                "company": "ACME",
                "evidence": [
                    {"id": "ev_exp_shared_selected", "text": "Built SQL pipelines"},
                    {"id": "ev_exp_shared_other", "text": "Processed 999 million records"},
                ],
            },
            "ev_exp_shared_selected",
            ["Built SQL pipelines"],
        ),
        (
            "projects",
            "projects",
            {
                "id": "project_shared",
                "name": "Analytics Platform",
                "evidence": [
                    {"id": "ev_project_shared_selected", "text": "Built SQL pipelines"},
                    {"id": "ev_project_shared_other", "text": "Processed 999 million records"},
                ],
            },
            "ev_project_shared_selected",
            ["Built SQL pipelines"],
        ),
    ):
        repaired, repaired_keys = _backfill_required_sections_from_profile(
            structured_cv={"sections": {section: []}},
            profile={profile_key: [entry]},
            missing_sections=[section],
            selected_evidence_ids=[selected_id],
        )

        assert repaired_keys == [section]
        assert repaired["sections"][section][0]["bullets"] == expected_bullets


@pytest.mark.parametrize(
    ("section", "profile_key", "entries", "selected_id", "expected_name"),
    [
        (
            "experience",
            "experiences",
            [
                {"id": "exp_1", "company": "OTHER-1", "bullets": ["Other work 1"]},
                {"id": "exp_2", "company": "OTHER-2", "bullets": ["Other work 2"]},
                {"id": "exp_3", "company": "OTHER-3", "bullets": ["Other work 3"]},
                {"id": "exp_4", "company": "ACME", "bullets": ["Built SQL pipelines"]},
            ],
            "ev_exp_4_selected",
            "ACME",
        ),
        (
            "projects",
            "projects",
            [
                {"id": "project_1", "name": "OTHER-1", "highlights": ["Other work 1"]},
                {"id": "project_2", "name": "OTHER-2", "highlights": ["Other work 2"]},
                {"id": "project_3", "name": "OTHER-3", "highlights": ["Other work 3"]},
                {"id": "project_4", "name": "ACME", "highlights": ["Built SQL pipelines"]},
            ],
            "ev_project_4_selected",
            "ACME",
        ),
    ],
)
def test_local_backfill_filters_selected_entries_before_limit(
    section, profile_key, entries, selected_id, expected_name
) -> None:
    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {section: []}},
        profile={profile_key: entries},
        missing_sections=[section],
        selected_evidence_ids=[selected_id],
    )

    assert repaired_keys == [section]
    assert len(repaired["sections"][section]) == 1
    field = "company" if section == "experience" else "name"
    assert repaired["sections"][section][0][field] == expected_name


def test_missing_mandatory_section_uses_local_backfill_before_provider_retry(monkeypatch) -> None:
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
    }
    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        lambda *args, **kwargs: {**validation, "valid": True, "missing_sections": []},
    )
    retry_executor = Mock()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "preset": "europass",
        "locale": "en",
        "job_url": "https://example.com/job",
        "fit_classification": "strong",
        "target_role": "Data Engineer",
        "sections": {
            "header": {"name": "Jane Doe"},
            "summary": {"text": "Summary"},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    profile = {
        "name": "Jane Doe",
        "experiences": [{"role": "Data Engineer", "company": "ACME", "bullets": ["Built pipelines"]}],
    }

    repaired_cv, _, repaired_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=structured_cv,
        markdown="# CV",
        validation=validation,
        profile=profile,
        config={},
        analysis_grounding={},
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    retry_executor.assert_not_called()
    assert repaired_validation["valid"] is True
    assert repair_attempt["missing_sections"] == ["experience"]
    assert repair_attempt["reason"] == "deterministic_section_backfill"
    assert repaired_cv["sections"]["experience"][0]["company"] == "ACME"


def test_local_backfill_uses_only_selected_experience_evidence(monkeypatch) -> None:
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
    }

    def validate(*args, **kwargs):
        structured_cv = kwargs["structured_cv"]
        companies = {
            item.get("company")
            for item in structured_cv["sections"]["experience"]
        }
        if "Long Hung ITS" in companies:
            return {
                **validation,
                "grounding_violations": ["unsupported employer"],
            }
        return {**validation, "valid": True, "missing_sections": []}

    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        validate,
    )
    retry_executor = Mock(
        return_value=(
            None,
            "# retry",
            {**validation, "grounding_violations": ["unsupported employer"]},
            None,
        )
    )
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "preset": "europass",
        "locale": "en",
        "job_url": "https://example.com/job",
        "fit_classification": "strong",
        "target_role": "Data Analyst",
        "sections": {
            "header": {"name": "Jane Doe"},
            "summary": {"text": "Summary"},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        }
    }
    profile = {
        "experiences": [
            {
                "id": "exp_kokuyo_vn_2021_2023",
                "role": "R&D Staff",
                "company": "KOKUYO Vietnam Trading",
                "bullets": ["Improved NPD process"],
            },
            {
                "id": "exp_longhung_pushmax_2019_2021",
                "role": "Brand Marketing Executive",
                "company": "Long Hung ITS",
                "bullets": ["Managed campaigns"],
            },
        ]
    }

    repaired_cv, _, repaired_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=structured_cv,
        markdown="# CV",
        validation=validation,
        profile=profile,
        config={},
        analysis_grounding={
            "evidence_selection_summary": {
                "selected_evidence_ids": [
                    "ev_exp_kokuyo_vn_2021_2023_evidence"
                ]
            }
        },
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    retry_executor.assert_not_called()
    assert repaired_validation["valid"] is True
    assert repair_attempt["reason"] == "deterministic_section_backfill"
    assert [
        item["company"] for item in repaired_cv["sections"]["experience"]
    ] == ["KOKUYO Vietnam Trading"]


def test_local_backfill_uses_selected_nested_evidence_claims(monkeypatch) -> None:
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
    }

    def validate(*args, **kwargs):
        bullets = kwargs["structured_cv"]["sections"]["experience"][0]["bullets"]
        if bullets == ["Built SQL pipelines"]:
            return {**validation, "valid": True, "missing_sections": []}
        return {**validation, "grounding_violations": ["unselected claim"]}

    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        validate,
    )
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "preset": "europass",
        "locale": "en",
        "job_url": "https://example.com/job",
        "fit_classification": "strong",
        "target_role": "Data Analyst",
        "sections": {
            "header": {"name": "Jane Doe"},
            "summary": {"text": "Summary"},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    retry_executor = Mock(
        return_value=(structured_cv, "# retry", validation, None)
    )

    repaired_cv, _, repaired_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=structured_cv,
        markdown="# CV",
        validation=validation,
        profile={
            "experiences": [
                {
                    "id": "exp_shared",
                    "role": "Data Analyst",
                    "company": "ACME",
                    "evidence": [
                        {"id": "ev-independent-acme", "text": "Built SQL pipelines"},
                        {"id": "ev-independent-other", "text": "Processed 999 million records"},
                    ],
                }
            ]
        },
        config={},
        analysis_grounding={
            "evidence_selection_summary": {
                "selected_evidence_ids": ["ev-independent-acme"]
            }
        },
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    retry_executor.assert_not_called()
    assert repaired_validation["valid"] is True
    assert repair_attempt["reason"] == "deterministic_section_backfill"
    assert repaired_cv["sections"]["experience"][0]["bullets"] == [
        "Built SQL pipelines"
    ]


def test_retry_fallback_preserves_selected_evidence_scope(monkeypatch) -> None:
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
    }
    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        lambda *args, **kwargs: {**validation, "grounding_violations": ["retry failed"]},
    )
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "preset": "europass",
        "locale": "en",
        "job_url": "https://example.com/job",
        "fit_classification": "strong",
        "target_role": "Data Analyst",
        "sections": {
            "header": {"name": "Jane Doe"},
            "summary": {"text": "Summary"},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    retry_executor = Mock(return_value=(structured_cv, "# retry", validation, None))

    repaired_cv, _, _, _, _ = _run_repair_cycle(
        structured_cv=structured_cv,
        markdown="# CV",
        validation=validation,
        profile={
            "experiences": [
                {
                    "id": "exp_acme",
                    "role": "Data Analyst",
                    "company": "ACME",
                    "bullets": ["Built SQL pipelines"],
                },
                {
                    "id": "exp_other",
                    "role": "Data Analyst",
                    "company": "OTHER",
                    "bullets": ["Processed 999 million records"],
                },
            ]
        },
        config={},
        analysis_grounding={
            "evidence_selection_summary": {
                "selected_evidence_ids": ["ev_exp_acme_selected"]
            }
        },
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    retry_executor.assert_called_once_with(["experience"])
    assert [
        item["company"] for item in repaired_cv["sections"]["experience"]
    ] == ["ACME"]
