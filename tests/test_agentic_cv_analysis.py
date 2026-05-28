from unittest.mock import patch

from fitcv.agentic_cv_analysis import (
    analyze_ranked_job,
    build_analysis_input_summary,
    resolve_ranked_job_fit,
)


def _job() -> dict:
    return {
        "job_url": "https://example.com/job/1",
        "title": "Data Analyst",
        "fit_label": "strong",
        "fit_label_source": "reranker",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": [],
        "responsibilities": ["Build dashboards"],
    }


def _profile() -> dict:
    return {
        "name": "Candidate",
        "skills": [{"name": "SQL"}],
        "years_experience": 4,
        "experiences": [],
        "projects": [],
    }


def _config() -> dict:
    return {
        "pipeline": {"evidence_top_k": 3},
        "fit_label_thresholds": {"strong": 0.7, "stretch": 0.4},
    }


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
@patch("fitcv.agentic_cv_analysis.time.sleep")
def test_analyze_ranked_job_emits_extended_analysis_fields(
    mock_sleep,
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::1"}
    mock_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "effective_channel_pool_size": 1,
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": ["Python"]}

    result = analyze_ranked_job(_job(), _profile(), _config())

    assert result["status"] == "ready_for_generation"
    assert "requirement_coverage" in result
    assert any(item["requirement"] == "Python" for item in result["requirement_coverage"])
    assert result["do_not_claim"] == ["Python"]
    assert result["section_confidence_hints"]["experience"] in {"medium", "high"}
    mock_sleep.assert_not_called()


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
@patch("fitcv.agentic_cv_analysis.time.sleep")
def test_analyze_ranked_job_preserves_bundle_evidence_summary_fields(
    mock_sleep,
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::2"}
    mock_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "selected_evidence_ids": ["exp-1"],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 2,
        "deduped_pool_size": 1,
        "effective_channel_pool_size": 3,
        "hybrid_alignment": {"responsibility": {"lexical_weight": 0.25, "semantic_weight": 0.75}},
        "semantic_alignment": {"enabled": True},
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}

    result = analyze_ranked_job(_job(), _profile(), _config())
    summary = result["evidence_selection_summary"]

    assert summary["fallback_used"] is False
    assert summary["selected_evidence_count"] == 1
    assert summary["selected_evidence_ids"] == ["exp-1"]
    assert summary["merged_pool_size"] == 2
    assert summary["deduped_pool_size"] == 1
    assert summary["hybrid_alignment"]["responsibility_alignment"] == {
        "lexical_weight": 0.25,
        "semantic_weight": 0.75,
    }
    mock_sleep.assert_not_called()


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
@patch("fitcv.agentic_cv_analysis.time.sleep")
def test_analyze_ranked_job_uses_stage_runtime_cv_analysis_sleep(
    mock_sleep,
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::3"}
    mock_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "effective_channel_pool_size": 1,
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}
    config = _config()
    config["stage_runtime"] = {"cv_analysis": {"sleep_secs": 0.3}}

    analyze_ranked_job(_job(), _profile(), config)

    mock_sleep.assert_called_once_with(0.3)



def test_resolve_ranked_job_fit_ignores_diagnostic_lists_when_fit_label_present() -> None:
    base_job = _job()
    base_job["fit_label"] = "stretch"
    job_a = dict(base_job)
    job_b = dict(base_job)
    job_a["matched_strengths"] = ["SQL"]
    job_a["key_risks"] = ["Missing Spark"]
    job_b["matched_strengths"] = ["Different"]
    job_b["key_risks"] = ["Different"]

    assert resolve_ranked_job_fit(job_a, _config()) == "stretch"
    assert resolve_ranked_job_fit(job_b, _config()) == "stretch"

def test_build_analysis_input_summary_prefers_canonical_skill_lists_when_available() -> None:
    summary = build_analysis_input_summary(
        {
            "required_skills": ["SQL", "Python scripting"],
            "required_skills_canonical": ["sql", "python"],
            "preferred_skills": ["Airflow orchestration"],
            "preferred_skills_canonical": ["apache airflow"],
            "responsibilities": ["Build dashboards"],
            "job_family": "analytics",
        }
    )

    assert summary["required_skills"] == ["sql", "python"]
    assert summary["preferred_skills"] == ["apache airflow"]


def test_build_analysis_input_summary_falls_back_to_raw_skills_when_canonical_missing() -> None:
    summary = build_analysis_input_summary(
        {
            "required_skills": ["SQL", "Python"],
            "preferred_skills": ["Airflow"],
            "responsibilities": ["Build dashboards"],
        }
    )

    assert summary["required_skills"] == ["SQL", "Python"]
    assert summary["preferred_skills"] == ["Airflow"]
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
@patch("fitcv.agentic_cv_analysis.time.sleep")
def test_analyze_ranked_job_trace_input_summary_prefers_canonical_skill_counts(
    mock_sleep,
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::trace-counts"}
    mock_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "effective_channel_pool_size": 1,
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}

    job = _job()
    job["required_skills"] = ["SQL", "Python", "Spark"]
    job["required_skills_canonical"] = ["sql"]
    job["preferred_skills"] = ["Airflow", "dbt"]
    job["preferred_skills_canonical"] = ["apache airflow"]

    result = analyze_ranked_job(job, _profile(), _config())
    input_summary = result["cv_analysis_trace"]["input_summary"]

    assert input_summary["required_skills_count"] == 1
    assert input_summary["preferred_skills_count"] == 1

    job["required_skills_canonical"] = []
    job["preferred_skills_canonical"] = []
    fallback_result = analyze_ranked_job(job, _profile(), _config())
    fallback_input_summary = fallback_result["cv_analysis_trace"]["input_summary"]

    assert fallback_input_summary["required_skills_count"] == 3
    assert fallback_input_summary["preferred_skills_count"] == 2
    mock_sleep.assert_not_called()

