from unittest.mock import Mock

from fitcv.agentic_cv_generation import _run_repair_cycle


def test_missing_mandatory_section_uses_provider_retry_before_local_backfill(monkeypatch) -> None:
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
    retry_executor = Mock(
        return_value=(
            {
                "sections": {
                    "experience": [{"role": "Data Engineer", "company": "ACME", "bullets": ["Built pipelines"]}]
                }
            },
            "# CV",
            validation,
            None,
        )
    )
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

    retry_executor.assert_called_once_with(["experience"])
    assert repaired_validation["valid"] is True
    assert repair_attempt["missing_sections"] == ["experience"]
