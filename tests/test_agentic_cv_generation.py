from unittest.mock import Mock, call

import pytest

from fitcv.agentic_cv_generation import (
    _backfill_required_sections_from_profile,
    _empty_cv_generation_trace,
    _update_efficiency_summary,
    _run_repair_cycle,
)
from unittest.mock import Mock


def test_generation_trace_declares_owned_stage_metrics_and_unavailable_savings() -> None:
    trace = _empty_cv_generation_trace(template_path=None, trace_id="trace-test")
    stages = trace["efficiency_summary"]["stage_timings"]
    assert stages["queue_wait_ms"]["status"] == "unavailable"
    assert stages["queue_wait_ms"]["owner"] == "worker_boundary"
    assert stages["persistence_ms"]["denominator"] == "persisted_artifacts"
    assert trace["efficiency_summary"]["savings"]["tokens_avoided"]["status"] == "unavailable"


def test_generation_trace_measures_provider_latency_without_inventing_other_stages() -> None:
    trace = _empty_cv_generation_trace(template_path=None, trace_id="trace-test")
    trace["attempts"] = [{
        "llm_runtime_evidence": {"provenance": {"latency_ms": 17}},
    }]
    _update_efficiency_summary(
        trace,
        input_metrics={},
        started_at=0,
        status="accepted",
        review_question_count=0,
    )
    assert trace["efficiency_summary"]["stage_timings"]["provider_ms"]["value"] == 17
    assert trace["efficiency_summary"]["stage_timings"]["provider_ms"]["status"] == "measured"
    assert trace["efficiency_summary"]["stage_timings"]["render_ms"]["status"] == "unavailable"


def test_provider_retry_does_not_count_as_local_repair() -> None:
    trace = _empty_cv_generation_trace(template_path=None, trace_id="trace-provider-retry")
    trace["repair_summary"] = {
        "repair_attempted": True,
        "repair_kind": "provider_retry",
    }

    _update_efficiency_summary(
        trace,
        input_metrics={},
        started_at=0,
        status="accepted",
        review_question_count=0,
    )

    savings = trace["efficiency_summary"]["savings"]
    assert savings["local_repair_attempted"] is False
    assert savings["local_repair_succeeded"] is False


def test_uncertain_validation_stops_for_review_without_retry() -> None:
    retry_executor = Mock()
    validation = {
        "valid": False,
        "missing_sections": [],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": ["ambiguous_section_attribution"],
    }

    _, _, final_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=None,
        markdown="# CV",
        validation=validation,
        profile={},
        config={},
        analysis_grounding={},
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    assert final_validation["valid"] is False
    assert repair_attempt["failure_category"] == "uncertainty"
    assert repair_attempt["review_required"] is True
    retry_executor.assert_not_called()


def test_uncertainty_after_targeted_retry_stops_before_full_regeneration() -> None:
    initial_validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }
    uncertain_validation = {
        **initial_validation,
        "missing_sections": [],
        "markdown_quality_review_flags": ["ambiguous_section_attribution"],
    }
    retry_executor = Mock(
        return_value=(None, "# retry", uncertain_validation, None)
    )

    _, _, final_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=None,
        markdown="# CV",
        validation=initial_validation,
        profile={},
        config={},
        analysis_grounding={},
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    assert final_validation["valid"] is False
    assert repair_attempt["failure_category"] == "uncertainty"
    assert repair_attempt["review_required"] is True
    assert repair_attempt.get("full_regeneration_attempted") is not True
    retry_executor.assert_called_once_with(["experience"])


def test_uncertainty_after_full_regeneration_stops_for_review(monkeypatch) -> None:
    initial_validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }
    uncertain_validation = {
        **initial_validation,
        "missing_sections": [],
        "markdown_quality_review_flags": ["ambiguous_section_attribution"],
    }
    retry_executor = Mock(
        side_effect=[
            (None, "# targeted", initial_validation, None),
            (None, "# full", uncertain_validation, None),
        ]
    )
    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        lambda *args, **kwargs: uncertain_validation,
    )

    _, _, final_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=None,
        markdown="# CV",
        validation=initial_validation,
        profile={},
        config={},
        analysis_grounding={},
        retry_executor=retry_executor,
        runtime_provenance=None,
    )

    assert final_validation["valid"] is False
    assert repair_attempt["failure_category"] == "uncertainty"
    assert repair_attempt["review_required"] is True
    assert repair_attempt["full_regeneration_attempted"] is True


def test_failed_local_repair_is_preserved_when_provider_retry_succeeds(monkeypatch) -> None:
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "missing_required_fields": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "markdown_quality_blocking_issues": [],
    }
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
    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._backfill_required_sections_from_profile",
        lambda **kwargs: (structured_cv, ["experience"]),
    )
    validation_results = iter(
        [
            {**validation, "valid": False},
            {**validation, "valid": True, "missing_sections": []},
        ]
    )
    monkeypatch.setattr(
        "fitcv.agentic_cv_generation._run_generation_validations",
        lambda *args, **kwargs: next(validation_results),
    )

    _, _, final_validation, repair_attempt, _ = _run_repair_cycle(
        structured_cv=structured_cv,
        markdown="# CV",
        validation=validation,
        profile={"experiences": [{"company": "ACME"}]},
        config={},
        analysis_grounding={},
        retry_executor=Mock(return_value=(structured_cv, "# retry", validation, {"provider": "retry"})),
        runtime_provenance=None,
        repair_arm="local_first",
    )

    assert final_validation["valid"] is True
    assert repair_attempt["reason"] == "provider_retry"
    assert repair_attempt["local_repair_attempted"] is True
    assert repair_attempt["local_repair_failed"] is True
    assert repair_attempt["provider_retry_attempted"] is True
    assert repair_attempt["provider_retry_succeeded"] is True


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


def test_absent_selection_preserves_legacy_profile_backfill() -> None:
    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"experience": []}},
        profile={
            "experiences": [
                {"company": "ACME", "bullets": ["Built pipelines"]},
            ]
        },
        missing_sections=["experience"],
    )

    assert repaired_keys == ["experience"]
    assert repaired["sections"]["experience"][0]["company"] == "ACME"


def test_explicit_empty_selection_disables_profile_backfill_and_generic_prose() -> None:
    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"experience": [], "skills": {"groups": []}}},
        profile={
            "experiences": [{"company": "ACME", "bullets": ["Built pipelines"]}],
            "skills": ["Python"],
        },
        missing_sections=["experience", "skills"],
        selected_evidence_ids=[],
        selection_present=True,
    )

    assert repaired_keys == []
    assert repaired["sections"]["experience"] == []
    assert repaired["sections"]["skills"] == {"groups": []}
    assert "Delivered cross-functional work aligned with business goals." not in str(repaired)


def test_explicit_empty_selection_disables_plain_string_language_backfill() -> None:
    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"languages": []}},
        profile={"languages": ["English", "German"]},
        missing_sections=["languages"],
        selected_evidence_ids=[],
        selection_present=True,
    )

    assert repaired_keys == []
    assert repaired["sections"]["languages"] == []


def test_local_backfill_filters_selected_education_before_limit() -> None:
    profile = {
        "education": [
            {"id": "edu-1", "institution": "Other 1", "evidence": [{"id": "ev-1"}]},
            {"id": "edu-2", "institution": "Other 2", "evidence": [{"id": "ev-2"}]},
            {"id": "edu-3", "institution": "ACME University", "evidence": [{"id": "ev-3"}]},
        ]
    }

    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"education": []}},
        profile=profile,
        missing_sections=["education"],
        selected_evidence_ids=["ev-3"],
    )

    assert repaired_keys == ["education"]
    assert repaired["sections"]["education"][0]["institution"] == "ACME University"


def test_local_backfill_filters_selected_languages_before_limit() -> None:
    languages = [
        {"id": f"lang-{index}", "name": f"Other {index}", "evidence": [{"id": f"ev-lang-{index}"}]}
        for index in range(1, 7)
    ]
    languages[-1] = {
        "id": "lang-6",
        "name": "German",
        "evidence": [{"id": "ev-lang-6"}],
    }

    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"languages": []}},
        profile={"languages": languages},
        missing_sections=["languages"],
        selected_evidence_ids=["ev-lang-6"],
    )

    assert repaired_keys == ["languages"]
    assert repaired["sections"]["languages"] == [{"name": "German", "level": None}]


def test_plain_string_skill_requires_selected_projected_evidence() -> None:
    repaired, repaired_keys = _backfill_required_sections_from_profile(
        structured_cv={"sections": {"skills": {"groups": []}}},
        profile={
            "skills": ["Python", "JavaScript"],
            "_projected_evidence_pool": [
                {"evidence_id": "ev_python", "skills": ["Python"]},
                {"evidence_id": "ev_javascript", "skills": ["JavaScript"]},
            ],
        },
        missing_sections=["skills"],
        selected_evidence_ids=["ev_python"],
        selection_present=True,
    )

    assert repaired_keys == ["skills"]
    assert repaired["sections"]["skills"]["groups"][0]["items"] == ["Python"]


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
        repair_arm="local_first",
    )

    retry_executor.assert_not_called()
    assert repaired_validation["valid"] is True
    assert repair_attempt["missing_sections"] == ["experience"]
    assert repair_attempt["reason"] == "deterministic_section_backfill"
    assert repaired_cv["sections"]["experience"][0]["company"] == "ACME"


def test_missing_mandatory_section_default_preserves_committed_local_backfill(monkeypatch) -> None:
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
        repair_arm="local_first",
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
        repair_arm="local_first",
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

    repaired_cv, _, _, repair_attempt, _ = _run_repair_cycle(
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
        repair_arm="local_first",
    )

    assert retry_executor.call_args_list == [call(["experience"]), call([])]
    assert repair_attempt["targeted_generation_attempted"] is True
    assert repair_attempt["full_regeneration_attempted"] is True
    assert [
        item["company"] for item in repaired_cv["sections"]["experience"]
    ] == ["ACME"]
