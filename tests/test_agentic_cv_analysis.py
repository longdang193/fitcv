"""
@meta
type: test
scope: unit
domain: cv_analysis
covers:
  - canonical CV-analysis statuses, identity, reuse, evidence, gap, and failure envelopes
excludes:
  - provider network calls
  - persistence
tags:
  - fast
  - ci-safe
"""

from unittest.mock import patch
from pathlib import Path

import yaml

from fitcv.agentic_cv_analysis import (
    analyze_ranked_job,
    build_analysis_input_summary,
    extract_job_url,
    resolve_ranked_job_fit,
)
from fitcv.contracts import CV_ANALYSIS_REUSE_SCHEMA_VERSION
from fitcv.evidence import build_cv_analysis_input_fingerprint


def _job() -> dict:
    return {
        "job_url": "https://example.com/job/1",
        "title": "Data Analyst",
        "baseline_fit": 0.8,
        "baseline_fit_label": "strong",
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
        "ranking_policy": {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}},
    }


def test_extract_job_url_accepts_indeed_url_alias() -> None:
    assert extract_job_url(
        {
            "url": "https://de.indeed.com/viewjob?jk=indeed123",
            "jobUrl": "https://employer.example/apply/indeed123",
        }
    ) == (
        "https://de.indeed.com/viewjob?jk=indeed123"
    )


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
        "source_profile_schema_version": "candidate-profile.v2",
        "projection_schema_version": "candidate-evidence.v1",
        "projection_fingerprint": "projection::1",
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
def test_analyze_ranked_job_converges_legacy_profile_before_evidence(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::legacy"}
    mock_bundle.return_value = {
        "source_profile_schema_version": "candidate-profile.v2",
        "selected_evidence": [],
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}
    profile = {
        "name": "Legacy Candidate",
        "experiences": [
            {
                "id": "exp_1",
                "role": "Data Engineer",
                "company": "Example",
                "bullets": [{"text": "Built SQL pipelines.", "skills": ["SQL"]}],
            }
        ],
        "education": [{"id": "edu_1", "degree": "MSc", "institution": "Example", "gpa": "1.0"}],
        "projects": [],
        "achievements": [{"id": "ach_1", "text": "Improved reporting", "category": "performance", "evidence_refs": ["exp_1"]}],
        "certifications": [],
        "volunteering": [],
        "languages": [{"id": "lang_1", "name": "English", "native": False}],
        "skills": [{"id": "skill_1", "name": "SQL", "category": "Data", "level": "advanced", "years": 5, "evidence_refs": ["exp_1"]}],
        "interests": [],
        "preferences": {},
    }

    result = analyze_ranked_job(_job(), profile, _config())

    assert result["status"] == "ready_for_generation"
    assert mock_bundle.called
    assert mock_bundle.call_args.args[0]["schema_version"] == "candidate-profile.v2"


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
        "source_profile_schema_version": "candidate-profile.v2",
        "projection_schema_version": "candidate-evidence.v1",
        "projection_fingerprint": "projection::1",
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
    assert summary["source_profile_schema_version"] == "candidate-profile.v2"
    assert summary["projection_schema_version"] == "candidate-evidence.v1"
    assert summary["projection_fingerprint"] == "projection::1"
    assert summary["merged_pool_size"] == 2
    assert summary["deduped_pool_size"] == 1
    assert summary["hybrid_alignment"]["responsibility_alignment"] == {
        "lexical_weight": 0.25,
        "semantic_weight": 0.75,
    }


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_ignores_retired_cv_analysis_sleep(
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




def test_resolve_ranked_job_fit_uses_persisted_baseline_label_only() -> None:
    base_job = _job()
    base_job["baseline_fit_label"] = "stretch"
    base_job["fit_label"] = "skip"
    base_job["ai_score"] = 0.99
    job_a = dict(base_job)
    job_b = dict(base_job)
    job_a["matched_strengths"] = ["SQL"]
    job_a["key_risks"] = ["Missing Spark"]
    job_b["matched_strengths"] = ["Different"]
    job_b["key_risks"] = ["Different"]

    assert resolve_ranked_job_fit(job_a, _config()) == "stretch"
    assert resolve_ranked_job_fit(job_b, _config()) == "stretch"


def test_resolve_ranked_job_fit_derives_from_baseline_score_then_marks_missing_score_unknown() -> None:
    assert resolve_ranked_job_fit({"baseline_fit": 0.55}, _config()) == "stretch"
    assert resolve_ranked_job_fit({"ai_score": 0.99, "fit_label": "strong"}, _config()) is None

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
def test_analyze_ranked_job_trace_input_summary_prefers_canonical_skill_counts(
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

def _complete_reusable_record() -> dict:
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"
    return {
        "raw_job_fingerprint": "raw-job-1",
        "job_url": job["job_url"],
        "job_title": job["title"],
        "status": "ready_for_generation",
        "analysis_input_fingerprint": "analysis::reuse",
        "analysis_input_components": {
            "contract_fingerprint": "contract::1",
            "profile_payload_hash": "profile::1",
            "job_payload_hash": "job::1",
        },
        "analysis_reuse_status": "fresh_compute",
        "reuse_decision": {"decision": "fresh_compute"},
        "ranking_fit_label": "strong",
        "fit_classification": "strong",
        "decision_chain": {},
        "job_snapshot": dict(job),
        "evidence_payload": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "evidence_used": [{"evidence_type": "experience_entry"}],
        "evidence_selection_summary": {"selected_evidence_count": 1, "fallback_used": False},
        "gap_summary": {"matched": ["SQL"], "missing": ["Python"]},
        "requirement_coverage": [],
        "section_confidence_hints": {"experience": "medium"},
        "do_not_claim": ["Python"],
        "outcome_reason": None,
        "error": None,
        "cv_analysis_trace": {"step_id": "cv_analysis"},
    }


def test_cv_analysis_fingerprint_uses_raw_identity_not_mutable_url() -> None:
    job_a = _job()
    job_a["raw_job_fingerprint"] = "raw-job-1"
    job_b = dict(job_a)
    job_b["job_url"] = "https://destination.example.com/job/1"

    fingerprint_a = build_cv_analysis_input_fingerprint(_profile(), job_a, _config())
    fingerprint_b = build_cv_analysis_input_fingerprint(_profile(), job_b, _config())

    assert CV_ANALYSIS_REUSE_SCHEMA_VERSION == "cv_analysis_reuse_v3"
    assert fingerprint_a["fingerprint"] == fingerprint_b["fingerprint"]
    assert fingerprint_a["payload"]["job"]["raw_job_fingerprint"] == "raw-job-1"
    assert "job_url" not in fingerprint_a["payload"]["job"]


def test_real_canonical_profile_emits_requirement_coverage_without_mocks() -> None:
    profile = yaml.safe_load(
        Path("data/candidate_profile.v2.sample.yaml").read_text(encoding="utf-8")
    )
    job = {
        "job_url": "https://example.com/job/live-probe",
        "title": "Data Analyst",
        "baseline_fit": 0.8,
        "baseline_fit_label": "strong",
        "required_skills": ["SQL", "Python"],
        "required_skill_entities": [
            {"raw_text": "SQL", "canonical": "sql"},
            {"raw_text": "Python", "canonical": "python"},
        ],
        "preferred_skills": [],
        "responsibilities": ["Build dashboards"],
    }
    result = analyze_ranked_job(
        job,
        profile,
        {
            "pipeline": {"evidence_top_k": 2},
            "ranking_policy": {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}},
            "cv_analysis": {
                "semantic_alignment": {"enabled": False},
                "selection_policy": {"requirement_gain_weight": 0.10},
            },
        },
    )

    assert result["status"] == "ready_for_generation"
    assert {
        str(row["canonical_skill"]): row["selected_support"]
        for row in result["requirement_coverage"]
    } == {"sql": "verified", "python": "verified"}


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_requirement_coverage_does_not_infer_support_from_profile_match(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::support"}
    mock_bundle.return_value = {
        "selected_evidence": [{
            "evidence_id": "ev-java",
            "skills": ["Java"],
            "channel_scores": {"required_skill_support": 0.8},
        }],
        "requirement_support": {"pool": {}, "selected": {}},
    }
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = analyze_ranked_job(
        {**_job(), "required_skills": ["SQL"], "required_skill_entities": [{"raw_text": "SQL", "canonical": "sql"}]},
        _profile(),
        _config(),
    )

    row = result["requirement_coverage"][0]
    assert row["profile_match"] == "matched"
    assert row["selected_support"] == "unsupported"
    assert row["support_strength"] == "unsupported"
    assert row["evidence_support_count"] == 0


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_requirement_coverage_preserves_partial_and_collapses_canonical_duplicates(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::partial"}
    mock_bundle.return_value = {
        "selected_evidence": [],
        "requirement_support": {"pool": {}, "selected": {}},
    }
    mock_gap.return_value = {
        "matched": [],
        "partial": [{"required": "Python programming", "candidate": "Python", "canonical": "python"}],
        "missing": [],
    }

    result = analyze_ranked_job(
        {
            **_job(),
            "required_skills": ["Python programming", "Python"],
            "required_skills_canonical": ["python", "python"],
            "required_skill_entities": [
                {"raw_text": "Python programming", "canonical": "python"},
                {"raw_text": "Python", "canonical": "python"},
            ],
        },
        _profile(),
        _config(),
    )

    assert len(result["requirement_coverage"]) == 1
    row = result["requirement_coverage"][0]
    assert row["profile_match"] == "partial"
    assert row["original_requirements"] == ["Python programming", "Python"]


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_requirement_coverage_marks_relevant_without_canonical_link_as_unverified(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::relevant"}
    mock_bundle.return_value = {
        "deduped_pool_size": 1,
        "selected_evidence": [{
            "evidence_id": "ev-relevant",
            "skills": ["Java"],
            "channel_scores": {"required_skill_support": 0.8},
            "scoring_context": "SQL dashboard reporting",
        }],
        "requirement_support": {"pool": {}, "selected": {}},
    }
    mock_gap.return_value = {"matched": [], "partial": [], "missing": ["SQL"]}

    result = analyze_ranked_job(
        {**_job(), "required_skills": ["SQL"], "required_skill_entities": [{"raw_text": "SQL", "canonical": "sql"}]},
        _profile(),
        _config(),
    )

    assert result["requirement_coverage"][0]["selected_support"] == "relevant_unverified"


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_requirement_coverage_drops_support_ids_not_present_after_selection(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {"fingerprint": "analysis::trim"}
    mock_bundle.return_value = {
        "deduped_pool_size": 2,
        "selected_evidence": [{"evidence_id": "ev-selected", "skills": ["Java"]}],
        "requirement_support": {
            "pool": {"required_skill:sql": ["ev-trimmed"]},
            "selected": {"required_skill:sql": ["ev-trimmed"]},
        },
    }
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = analyze_ranked_job(
        {**_job(), "required_skills": ["SQL"], "required_skill_entities": [{"raw_text": "SQL", "canonical": "sql"}]},
        _profile(),
        _config(),
    )

    row = result["requirement_coverage"][0]
    assert row["selected_support"] == "not_selected"
    assert row["supporting_evidence_ids"] == []


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_emits_canonical_identity_and_reuse_fields(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::canonical",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"raw_job_fingerprint": "raw-job-1"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {"selected_evidence": []}
    mock_gap.return_value = {"matched": ["SQL"], "missing": ["Python"]}
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"

    result = analyze_ranked_job(job, _profile(), _config())

    assert result["raw_job_fingerprint"] == "raw-job-1"
    assert result["analysis_input_components"]["contract_fingerprint"] == "contract::1"
    assert result["reuse_decision"]["decision"] == "fresh_compute"
    assert result["cv_analysis_trace"]["record_id"] == "fp:raw-job-1"
    assert result["cv_analysis_trace"]["scope_key"] == "fp:raw-job-1"


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_rebuilds_complete_exact_reuse_without_analysis(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::reuse",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"raw_job_fingerprint": "raw-job-1"},
            "contract_fingerprint": "contract::1",
        },
    }
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"
    job["job_url"] = "https://destination.example.com/job/1"

    result = analyze_ranked_job(
        job,
        _profile(),
        _config(),
        reusable_record=_complete_reusable_record(),
    )

    assert result["analysis_reuse_status"] == "reused_exact_match"
    assert result["reuse_decision"]["reason_code"] == "exact_fingerprint_match"
    assert result["job_url"] == job["job_url"]
    assert result["job_snapshot"] == job
    assert result["cv_analysis_trace"]["record_id"] == "fp:raw-job-1"
    mock_bundle.assert_not_called()
    mock_gap.assert_not_called()


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_recomputes_incomplete_reuse_candidate(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::reuse",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"raw_job_fingerprint": "raw-job-1"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {"selected_evidence": []}
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}
    incomplete = _complete_reusable_record()
    incomplete.pop("cv_analysis_trace")
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"

    result = analyze_ranked_job(
        job,
        _profile(),
        _config(),
        reusable_record=incomplete,
    )

    assert result["analysis_reuse_status"] == "fresh_compute"
    assert result["reuse_decision"]["reason_code"] == "incomplete_reusable_record"
    mock_bundle.assert_called_once()
    mock_gap.assert_called_once()


@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_converts_fingerprint_failure_to_record(mock_fingerprint) -> None:
    mock_fingerprint.side_effect = RuntimeError("fingerprint failed")
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"

    result = analyze_ranked_job(job, _profile(), _config())

    assert result["status"] == "analysis_failed"
    assert result["analysis_input_fingerprint"] is None
    assert result["error"] == {"stage": "analysis", "message": "fingerprint failed"}
    assert result["cv_analysis_trace"]["record_id"] == "fp:raw-job-1"

@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_reuses_skipped_fit_gate_record(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::reuse",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"raw_job_fingerprint": "raw-job-1"},
            "contract_fingerprint": "contract::1",
        },
    }
    reusable_record = _complete_reusable_record()
    reusable_record.update(
        {
            "status": "skipped_fit_gate",
            "fit_classification": "skip",
            "outcome_reason": {"stage": "fit_gate", "message": "cached skip"},
            "error": None,
        }
    )
    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"

    result = analyze_ranked_job(job, _profile(), _config(), reusable_record=reusable_record)

    assert result["status"] == "skipped_fit_gate"
    assert result["analysis_reuse_status"] == "reused_exact_match"
    assert result["outcome_reason"] == {"stage": "fit_gate", "message": "cached skip"}
    assert result["error"] is None
    mock_bundle.assert_not_called()
    mock_gap.assert_not_called()


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_recomputes_all_ineligible_reuse_candidates(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::reuse",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"raw_job_fingerprint": "raw-job-1"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {"selected_evidence": []}
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}
    candidates: list[tuple[dict, str]] = []

    failed = _complete_reusable_record()
    failed["status"] = "analysis_failed"
    candidates.append((failed, "reusable_status_not_eligible"))

    blocked = _complete_reusable_record()
    blocked["status"] = "blocked_by_reranker_fit"
    candidates.append((blocked, "reusable_status_not_eligible"))

    mismatched = _complete_reusable_record()
    mismatched["analysis_input_fingerprint"] = "analysis::old"
    candidates.append((mismatched, "analysis_input_fingerprint_mismatch"))

    fingerprintless = _complete_reusable_record()
    fingerprintless["analysis_input_fingerprint"] = None
    candidates.append((fingerprintless, "analysis_input_fingerprint_mismatch"))

    contract_mismatch = _complete_reusable_record()
    contract_mismatch["analysis_input_components"] = {
        **contract_mismatch["analysis_input_components"],
        "contract_fingerprint": "contract::old",
    }
    candidates.append((contract_mismatch, "contract_fingerprint_changed"))

    job = _job()
    job["raw_job_fingerprint"] = "raw-job-1"
    for candidate, expected_reason in candidates:
        result = analyze_ranked_job(job, _profile(), _config(), reusable_record=candidate)
        assert result["analysis_reuse_status"] == "fresh_compute"
        assert result["reuse_decision"]["reason_code"] == expected_reason

    assert mock_bundle.call_count == len(candidates)
    assert mock_gap.call_count == len(candidates)


def test_cv_analysis_fingerprint_distinguishes_duplicate_url_by_raw_identity() -> None:
    job_a = _job()
    job_a["raw_job_fingerprint"] = "raw-job-1"
    job_b = dict(job_a)
    job_b["raw_job_fingerprint"] = "raw-job-2"

    fingerprint_a = build_cv_analysis_input_fingerprint(_profile(), job_a, _config())
    fingerprint_b = build_cv_analysis_input_fingerprint(_profile(), job_b, _config())

    assert fingerprint_a["fingerprint"] != fingerprint_b["fingerprint"]


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_uses_url_identity_when_raw_fingerprint_missing(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::url-fallback",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"job_title": "Data Analyst"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {"selected_evidence": []}
    mock_gap.return_value = {"matched": ["SQL"], "missing": []}

    result = analyze_ranked_job(_job(), _profile(), _config())

    assert result["raw_job_fingerprint"] == ""
    assert result["cv_analysis_trace"]["record_id"] == "url:https://example.com/job/1"
    assert result["cv_analysis_trace"]["scope_key"] == "url:https://example.com/job/1"


@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
@patch("fitcv.agentic_cv_analysis.resolve_ranked_job_fit")
def test_analyze_ranked_job_converts_reranker_resolution_failure_to_record(
    mock_resolve_fit,
    mock_fingerprint,
) -> None:
    mock_resolve_fit.side_effect = RuntimeError("reranker resolution failed")

    result = analyze_ranked_job(_job(), _profile(), _config())

    assert result["status"] == "analysis_failed"
    assert result["error"] == {"stage": "analysis", "message": "reranker resolution failed"}
    mock_fingerprint.assert_not_called()


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_compatibility_label_does_not_change_semantics(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::parity",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"job_title": "Data Analyst"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}]
    }
    mock_gap.return_value = {"matched": ["SQL"], "missing": ["Python"]}
    builtin_config = _config()
    builtin_config["cv"] = {"agentic_late_stage": {"enabled": False}}
    compatibility_config = _config()
    compatibility_config["cv"] = {"agentic_late_stage": {"enabled": True}}

    builtin_result = analyze_ranked_job(_job(), _profile(), builtin_config)
    compatibility_result = analyze_ranked_job(_job(), _profile(), compatibility_config)

    assert builtin_result == compatibility_result

@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_blocks_reranker_skip_before_analysis_dependencies(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
) -> None:
    job = _job()
    job["baseline_fit_label"] = "skip"

    result = analyze_ranked_job(job, _profile(), _config())

    assert result["status"] == "blocked_by_reranker_fit"
    assert result["outcome_reason"]["stage"] == "reranker_fit"
    assert result["error"] is None
    mock_fingerprint.assert_not_called()
    mock_bundle.assert_not_called()
    mock_gap.assert_not_called()


@patch("fitcv.agentic_cv_analysis.resolve_ranked_job_fit", side_effect=["strong", "skip"])
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.agentic_cv_analysis.build_cv_analysis_input_fingerprint")
def test_analyze_ranked_job_emits_fresh_skipped_fit_gate_record(
    mock_fingerprint,
    mock_bundle,
    mock_gap,
    mock_resolve_fit,
) -> None:
    mock_fingerprint.return_value = {
        "fingerprint": "analysis::skip",
        "payload": {
            "profile": {"name": "Candidate"},
            "job": {"job_title": "Data Analyst"},
            "contract_fingerprint": "contract::1",
        },
    }
    mock_bundle.return_value = {"selected_evidence": []}
    mock_gap.return_value = {"matched": [], "missing": ["SQL", "Python"]}

    result = analyze_ranked_job(_job(), _profile(), _config())

    assert result["status"] == "skipped_fit_gate"
    assert result["analysis_reuse_status"] == "fresh_compute"
    assert result["outcome_reason"]["stage"] == "fit_gate"
    assert result["error"] is None
    assert mock_resolve_fit.call_count == 2

