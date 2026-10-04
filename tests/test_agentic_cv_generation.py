from unittest.mock import Mock

from fitcv.agentic_cv_generation import _run_repair_cycle


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
