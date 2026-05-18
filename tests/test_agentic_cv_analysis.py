from unittest.mock import patch

from fitcv.agentic_cv_analysis import analyze_ranked_job


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
def test_analyze_ranked_job_emits_extended_analysis_fields(
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


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_preserves_bundle_evidence_summary_fields(
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

