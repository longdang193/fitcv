"""
@meta
type: test
scope: unit
domain: pipeline
covers:
  - create_run_id: UUID4 format
  - build_ranking_features: merges shortlist + ai_scores by job_url
  - run_pipeline: returns correct schema, skips 'skip' fit jobs,
    skips jobs that fail validation
excludes:
  - BigQuery integration (all store_* functions are mocked)
  - LLM calls (generate_cv, run_ai_scoring, run_vector_search mocked)
tags:
  - fast
  - ci-safe
"""

import json
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import ANY, MagicMock, patch

import pytest

from fitcv.agentic_cv_analysis import (
    build_cv_analysis_record as build_agentic_cv_analysis_record,
    build_decision_chain,
)
from fitcv.agentic_cv_generation import (
    build_validation_evidence_fingerprint,
    check_cv_acceptance_policy as _evaluate_cv_acceptance_policy,
    generate_from_analysis as canonical_generate_from_analysis,
    hitl_review_reason_for_case as _hitl_review_reason_for_agentic_case,
    normalize_review_required_reason_code as _normalize_review_required_reason_code,
)
from fitcv.late_stage_contract import (
    CV_DEBUG_ANALYSIS_OMISSION_STATUSES,
    CV_GENERATION_ATTEMPTED_STATUSES,
    canonical_pipeline_outcome_status,
    pipeline_outcome_surface,
)
from fitcv.pipeline import (
    _build_export_results,
    _build_stage_transition_artifacts,
    _build_cv_generation_debug_record as _project_cv_generation_debug_record,
    _collect_mapping_suggestions,
    _enrich_jobs_with_reuse,
    _materialize_scoring_shortlist,
    _reuse_anomaly_payload,
    _stage_block,
    PipelineCancelled,
    build_ranking_features,
    create_run_id,
    run_pipeline,
)
from fitcv.rule_filter import DEFAULT_SELECTED_RULE_FILTERS


def _vector_search_envelope(
    rows: list[dict[str, Any]],
    *,
    audit_rows: list[dict[str, Any]] | None = None,
    diagnostics: dict[str, Any] | None = None,
    candidate_query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "production_rows": rows,
        "audit_rows": list(audit_rows or []),
        "diagnostics": diagnostics
        or {
            "eligible_jobs_total": len(rows),
            "scored_jobs_total": len(rows),
            "production_shortlist_total": len(rows),
            "embedding_coverage_rate": 1.0 if rows else 0.0,
        },
        "candidate_query": candidate_query
        or {
            "components": {},
            "text": "candidate",
            "candidate_query_reuse_status": "fresh_compute",
            "candidate_query_signature": "test-signature",
            "candidate_query_contract_fingerprint": "test-contract",
        },
    }


def test_reuse_anomaly_ignores_fresh_run_without_reused_rows() -> None:
    payload = _reuse_anomaly_payload(
        reuse_metrics={
            "enrich": {
                "total_rows": 100,
                "reused_rows": 0,
                "fresh_rows": 100,
                "reuse_rate": 0.0,
            }
        },
        config={"reuse": {"anomaly_guard": {"min_overlap": 5, "reuse_rate_floor": 0.05}}},
    )

    assert payload is None


def test_reuse_anomaly_keeps_low_nonzero_reuse_warning() -> None:
    payload = _reuse_anomaly_payload(
        reuse_metrics={
            "enrich": {
                "total_rows": 100,
                "reused_rows": 1,
                "fresh_rows": 99,
                "reuse_rate": 0.01,
            }
        },
        config={"reuse": {"anomaly_guard": {"min_overlap": 5, "reuse_rate_floor": 0.05}}},
    )

    assert payload is not None
    assert payload["stages"][0]["reused"] == 1


def _build_cv_generation_debug_record(
    *,
    job: dict[str, Any],
    status: str,
    fit_classification: str | None,
    evidence_used: list[dict[str, Any]],
    evidence_selection_summary: dict[str, Any] | None,
    analysis_input_summary: dict[str, Any] | None,
    gap_summary: dict[str, Any] | None,
    structured_cv_initial: dict[str, Any] | None,
    validation_initial: dict[str, Any] | None,
    repair_attempt: dict[str, Any],
    structured_cv_final: dict[str, Any] | None,
    markdown_final: str | None,
    enabled_sections: list[str] | None,
    cv_generation_model: str | None,
    cv_prompt_id: str | None,
    cv_prompt_template_path: str | None,
    error: dict[str, str] | None,
    validation_final: dict[str, Any] | None = None,
    runtime_provenance: dict[str, Any] | None = None,
    cv_generation_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranking_fit_label = str(job.get("fit_label") or fit_classification or "").strip() or None
    cv_analysis_status = (
        status
        if status in {"blocked_by_reranker_fit", "skipped_fit_gate", "analysis_failed"}
        else "ready_for_generation"
    )
    cv_status = "not_attempted" if status == "blocked_by_reranker_fit" else status
    reason_code = _normalize_review_required_reason_code(
        status=status,
        error=error,
        validation_initial=validation_final or validation_initial,
    )
    generation_result: dict[str, Any] = {
        "job_url": str(job.get("job_url") or ""),
        "job_title": str(job.get("title") or job.get("job_title") or ""),
        "status": status,
        "ranking_fit_label": ranking_fit_label,
        "fit_classification": fit_classification,
        "decision_chain": build_decision_chain(
            job=job,
            fit_classification=fit_classification,
            cv_analysis_status=cv_analysis_status,
            cv_status=cv_status,
        ),
        "analysis_input_summary": dict(analysis_input_summary or {}),
        "evidence_used": list(evidence_used),
        "evidence_selection_summary": dict(evidence_selection_summary or {}),
        "gap_summary": gap_summary,
        "structured_cv_initial": structured_cv_initial,
        "validation_initial": validation_initial,
        "repair_attempt": repair_attempt,
        "structured_cv_final": structured_cv_final,
        "markdown_final": markdown_final,
        "validation": validation_final,
        "outcome_reason": error if status in {"blocked_by_reranker_fit", "skipped_fit_gate"} else None,
        "error": error if status not in {"blocked_by_reranker_fit", "skipped_fit_gate"} else None,
        "review_required_reason_code": reason_code.value if reason_code is not None else None,
    }
    generation_result["validation_evidence_fingerprint"] = build_validation_evidence_fingerprint(
        status=status,
        validation=validation_final or validation_initial,
        error=error,
    )
    if runtime_provenance is not None:
        generation_result["runtime_provenance"] = runtime_provenance
    if cv_generation_trace is not None:
        generation_result["cv_generation_trace"] = cv_generation_trace
    return _project_cv_generation_debug_record(
        generation_result=generation_result,
        enabled_sections=list(enabled_sections or []),
        cv_generation_model=cv_generation_model,
        cv_prompt_id=str(cv_prompt_id or ""),
        cv_prompt_template_path=str(cv_prompt_template_path or ""),
    )

_ROLE_TAXONOMY_CONFIG = {
    "role_taxonomy": {
        "canonical_role_by_alias": {
            "business intelligence analyst": "data analyst",
            "data analyst": "data analyst",
            "analytics engineer": "data engineer",
            "data engineer": "data engineer",
            "ml engineer": "machine learning engineer",
            "machine learning engineer": "machine learning engineer",
        },
        "role_family_by_role": {
            "data analyst": "analytics",
            "data engineer": "data_engineering",
            "machine learning engineer": "ml_engineering",
        },
        "role_family_neighbors": {
            "analytics": ("data_science",),
            "data_engineering": ("ml_engineering",),
            "ml_engineering": ("data_engineering",),
        },
    }
}


# ── create_run_id ─────────────────────────────────────────────────────────────

def test_create_run_id_returns_valid_uuid() -> None:
    run_id = create_run_id()
    uuid.UUID(run_id)  # raises ValueError if not valid


def test_create_run_id_unique() -> None:
    """Each call must return a different ID."""
    assert create_run_id() != create_run_id()


# ── build_ranking_features ────────────────────────────────────────────────────

def _make_shortlist() -> list[dict]:
    return [
        {"job_url": "https://example.com/1", "similarity_score": 0.9, "rank": 1},
        {"job_url": "https://example.com/2", "similarity_score": 0.7, "rank": 2},
    ]


def _make_ai_scores() -> list[dict]:
    return [
        {
            "job_url": "https://example.com/1",
            "ai_score": 0.85,
            "fit_label": "strong",
            "must_have_match": 1.0,
            "title_relevance": 0.8,
            "seniority_fit": 0.9,
            "preference_fit": 0.7,
            "required_skills": ["SQL", "Python"],
            "job_title": "Data Engineer",
            "seniority": "senior",
        },
        {
            "job_url": "https://example.com/2",
            "ai_score": 0.6,
            "fit_label": "stretch",
            "must_have_match": 0.5,
            "title_relevance": 0.6,
            "seniority_fit": 0.8,
            "preference_fit": 0.5,
            "required_skills": ["Spark"],
            "job_title": "ML Engineer",
            "seniority": "mid",
        },
    ]


def test_build_ranking_features_merges_by_job_url() -> None:
    profile: dict = {"preferences": {"target_role": "Data Engineer"}}
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    assert len(features) == 2
    urls = {f["job_url"] for f in features}
    assert urls == {"https://example.com/1", "https://example.com/2"}


def test_build_ranking_features_includes_vector_similarity() -> None:
    profile: dict = {"preferences": {}}
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["vector_similarity"] == pytest.approx(0.9)


@pytest.mark.parametrize(
    ("row", "expected_status", "expected_surface"),
    [
        (
            {
                "source_stage": "cv_generation",
                "deterministic_outcome": "accepted",
                "stage_owned_subreason": "accepted",
            },
            "ranked_with_cv",
            {"label": "CV created", "badge_class": "badge-success"},
        ),
        (
            {
                "source_stage": "cv_generation",
                "stage_owned_subreason": "review_required",
            },
            "ranked_no_cv",
            {"label": "CV review required", "badge_class": "badge-warning"},
        ),
        (
            {
                "source_stage": "cv_analysis",
                "stage_owned_subreason": "blocked_by_reranker_fit",
            },
            "ranked_blocked_by_reranker_fit",
            {"label": "Ranked, blocked by reranker fit", "badge_class": "badge-warning"},
        ),
    ],
)
def test_late_stage_contract_projects_pipeline_outcome_surface(
    row: dict[str, Any],
    expected_status: str,
    expected_surface: dict[str, str],
) -> None:
    assert canonical_pipeline_outcome_status(row) == expected_status
    assert pipeline_outcome_surface(row) == expected_surface

def test_late_stage_contract_exposes_shared_status_families() -> None:
    assert CV_GENERATION_ATTEMPTED_STATUSES == frozenset(
        {"accepted", "review_required", "validation_failed", "generation_failed", "persistence_failed"}
    )
    assert CV_DEBUG_ANALYSIS_OMISSION_STATUSES == frozenset(
        {"blocked_by_reranker_fit", "skipped_fit_gate", "analysis_failed"}
    )


def test_stage_block_orders_outcome_samples_before_inputs() -> None:
    block = _stage_block(
        stage_id="ranking",
        status="completed",
        input_counts={"rows": 3},
        output_counts={"rows": 2},
        decision_summary={"ranked_jobs": 2},
        inputs_sample=[{"job_url": "https://jobs.example.com/in"}],
        outputs_sample=[{"job_url": "https://jobs.example.com/out"}],
        dropped_or_changed_sample=[{"job_url": "https://jobs.example.com/drop"}],
    )

    assert list(block.keys()) == [
        "stage_id",
        "stage",
        "status",
        "stage_result",
        "input_counts",
        "output_counts",
        "decision_summary",
        "outputs_sample",
        "dropped_or_changed_sample",
        "inputs_sample",
    ]

def test_build_export_results_uses_raw_job_fingerprint_when_urls_drift() -> None:
    raw_jobs = [
        {
            "job_url": "https://de.indeed.com/viewjob?jk=abc123",
            "title": "Fingerprint Role",
            "raw_job_fingerprint": "raw-fp-1",
        }
    ]
    enriched = [
        {
            "job_url": "https://jobs.example.com/fingerprint-role",
            "title": "Fingerprint Role",
            "raw_job_fingerprint": "raw-fp-1",
        }
    ]
    ranking_row = {
        "job_url": "https://jobs.example.com/fingerprint-role",
        "title": "Fingerprint Role",
        "raw_job_fingerprint": "raw-fp-1",
        "final_score": 0.82,
        "ai_score": 0.71,
        "vector_similarity": 0.65,
        "fit_label": "strong",
    }

    rows = _build_export_results(
        raw_jobs=raw_jobs,
        enriched=enriched,
        deduplicated_jobs=[],
        pre_filter_rejected=[],
        candidate_filter_rejected=[],
        passed_jobs=[dict(ranking_row)],
        raw_shortlist=[],
        shortlist_for_scoring=[],
        ranking_inputs=[dict(ranking_row)],
        ranked=[dict(ranking_row)],
        cv_analysis_results=[],
        cv_results=[],
        cv_generation_debug_records=[],
        vector_search_top_n=10,
    )

    assert rows[0]["pipeline_status"] == "ranked_no_cv"
    assert rows[0]["scores"]["final_score"] == pytest.approx(0.82)


def test_ready_for_generation_keeps_ranking_fit_as_upstream_authority() -> None:
    job = {
        "job_url": "https://example.com/ready",
        "title": "Ready Job",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }

    record = build_agentic_cv_analysis_record(
        job=job,
        status="ready_for_generation",
        analysis_input_fingerprint="analysis-fp",
        analysis_reuse_status="fresh_compute",
        evidence_payload=[],
        evidence_selection_summary=None,
        gap_summary=None,
        fit_classification="skip",
        error=None,
        requirement_coverage=None,
        section_confidence_hints=None,
        do_not_claim=[],
    )

    assert record["ranking_fit_label"] == "strong"
    assert record["fit_classification"] == "skip"
    assert record["decision_chain"]["primary_fit"] == {
        "source": "reranker",
        "label": "strong",
    }
    assert record["decision_chain"]["cv_analysis"] == {
        "status": "ready_for_generation",
        "completed": True,
    }
    assert record["decision_chain"]["cv_generation"] == {
        "status": "not_attempted",
        "attempted": False,
    }


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
def test_analyze_ranked_job_marks_fallback_retrieval_in_evidence_selection_summary(
    mock_retrieve_bundle: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_compute_gap: MagicMock,
) -> None:
    from fitcv.agentic_cv_analysis import analyze_ranked_job

    job = {
        **_minimal_job("https://example.com/fallback"),
        "title": "Fallback Job",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}

    mock_retrieve_bundle.return_value = {
        "selected_evidence": [],
        "selected_evidence_ids": [],
        "channel_counts": {
            "required_skill_support": 1,
            "role_alignment": 1,
            "domain_alignment": 1,
            "responsibility_alignment": 1,
        },
        "effective_channel_pool_size": 4,
        "merged_pool_size": 0,
        "deduped_pool_size": 0,
        "hybrid_alignment": {
            "required_skill_support": {"lexical_weight": 0.70, "semantic_weight": 0.30},
            "role_alignment": {"lexical_weight": 0.60, "semantic_weight": 0.40},
            "responsibility": {"lexical_weight": 0.25, "semantic_weight": 0.75},
            "domain": {"lexical_weight": 0.40, "semantic_weight": 0.60},
        },
        "semantic_alignment": {
            "enabled": True,
            "semantic_methods": {
                "required_skill_support": "embedding_similarity",
                "role_alignment": "embedding_similarity",
                "responsibility_alignment": "embedding_similarity",
                "domain_alignment": "embedding_similarity",
            },
        },
    }
    mock_retrieve_evidence.return_value = [
        {
            "evidence_id": "exp-fallback-1",
            "evidence_type": "experience_entry",
            "source_ref": "experiences[0]",
            "name": "Fallback Experience",
            "matched_channels": ["required_skill_support"],
            "selection_reasons": ["required_skill_support"],
        }
    ]
    mock_compute_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    record = analyze_ranked_job(job, profile, config)

    assert record["status"] == "ready_for_generation"
    assert record["evidence_selection_summary"]["fallback_used"] is True
    assert record["evidence_selection_summary"]["selected_evidence_ids"] == ["exp-fallback-1"]
    assert record["evidence_selection_summary"]["hybrid_alignment"] == {
        "required_skill_support": {"lexical_weight": 0.70, "semantic_weight": 0.30},
        "role_alignment": {"lexical_weight": 0.60, "semantic_weight": 0.40},
        "responsibility_alignment": {"lexical_weight": 0.25, "semantic_weight": 0.75},
        "domain_alignment": {"lexical_weight": 0.40, "semantic_weight": 0.60},
    }


def test_blocked_by_reranker_fit_keeps_cv_analysis_stage_authority() -> None:
    job = {
        "job_url": "https://example.com/blocked",
        "title": "Blocked Job",
        "fit_label": "stretch",
        "fit_label_source": "reranker",
    }

    record = _build_cv_generation_debug_record(
        job=job,
        status="blocked_by_reranker_fit",
        fit_classification="strong",
        evidence_used=[],
        evidence_selection_summary=None,
        analysis_input_summary=None,
        gap_summary=None,
        structured_cv_initial=None,
        validation_initial=None,
        repair_attempt={"performed": False, "missing_sections": []},
        structured_cv_final=None,
        markdown_final=None,
        enabled_sections=None,
        cv_generation_model=None,
        cv_prompt_id=None,
        cv_prompt_template_path=None,
        error={"stage": "reranker_fit", "message": "blocked"},
    )

    assert record["ranking_fit_label"] == "stretch"
    assert record["fit_classification"] == "strong"
    assert record["decision_chain"]["primary_fit"] == {
        "source": "reranker",
        "label": "stretch",
    }
    assert record["decision_chain"]["cv_analysis"] == {
        "status": "blocked_by_reranker_fit",
        "completed": False,
    }
    assert record["decision_chain"]["cv_generation"] == {
        "status": "not_attempted",
        "attempted": False,
    }


def test_skipped_fit_gate_keeps_cv_analysis_stage_authority() -> None:
    job = {
        "job_url": "https://example.com/skipped",
        "title": "Skipped Job",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    outcome_reason = {"stage": "fit_gate", "message": "skipped"}

    record = build_agentic_cv_analysis_record(
        job=job,
        status="skipped_fit_gate",
        analysis_input_fingerprint="analysis-fp",
        analysis_reuse_status="fresh_compute",
        evidence_payload=[],
        evidence_selection_summary=None,
        gap_summary={"matched": [], "partial": [], "missing": ["SQL"]},
        requirement_coverage=None,
        section_confidence_hints=None,
        do_not_claim=[],
        fit_classification="skip",
        error=outcome_reason,
    )

    assert record["ranking_fit_label"] == "strong"
    assert record["fit_classification"] == "skip"
    assert record["decision_chain"]["primary_fit"] == {
        "source": "reranker",
        "label": "strong",
    }
    assert record["decision_chain"]["cv_analysis"] == {
        "status": "skipped_fit_gate",
        "completed": True,
    }
    assert record["decision_chain"]["cv_generation"] == {
        "status": "not_attempted",
        "attempted": False,
    }
    assert record["outcome_reason"] == outcome_reason
    assert record["error"] is None


@pytest.mark.parametrize(
    ("status", "expected_validation_status"),
    [
        ("validation_failed", "failed"),
        ("generation_failed", "not_run"),
        ("persistence_failed", "accepted"),
    ],
)
def test_ready_for_generation_keeps_generation_terminal_statuses_stage_owned(
    status: str,
    expected_validation_status: str,
) -> None:
    job = {
        "job_url": "https://example.com/generation",
        "title": "Generation Job",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }

    record = _build_cv_generation_debug_record(
        job=job,
        status=status,
        fit_classification="skip",
        evidence_used=[],
        evidence_selection_summary=None,
        analysis_input_summary=None,
        gap_summary=None,
        structured_cv_initial=None,
        validation_initial=None,
        repair_attempt={"performed": False, "missing_sections": []},
        structured_cv_final=None,
        markdown_final=None,
        enabled_sections=None,
        cv_generation_model=None,
        cv_prompt_id=None,
        cv_prompt_template_path=None,
        error={"stage": "cv_generation", "message": status},
    )

    assert record["status"] == status
    assert record["ranking_fit_label"] == "strong"
    assert record["fit_classification"] == "skip"
    assert record["decision_chain"]["primary_fit"] == {
        "source": "reranker",
        "label": "strong",
    }
    assert record["decision_chain"]["cv_analysis"] == {
        "status": "ready_for_generation",
        "completed": True,
    }
    assert record["decision_chain"]["cv_generation"] == {
        "status": status,
        "attempted": True,
    }
    assert record["decision_chain"]["validation"] == {
        "status": expected_validation_status,
    }
    assert "review_required_reason_code" in record
    assert "attempt_count" in record


@pytest.mark.parametrize("status", ["accepted", "review_required", "validation_failed"])
def test_cv_generation_terminal_statuses_keep_reranker_primary_fit_authority_matrix(status: str) -> None:
    job = {
        "job_url": "https://example.com/status-matrix",
        "title": "Status Matrix Job",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }

    record = _build_cv_generation_debug_record(
        job=job,
        status=status,
        fit_classification="skip",
        evidence_used=[],
        evidence_selection_summary=None,
        analysis_input_summary=None,
        gap_summary=None,
        structured_cv_initial=None,
        validation_initial=None,
        repair_attempt={"performed": False, "missing_sections": []},
        structured_cv_final=None,
        markdown_final=None,
        enabled_sections=None,
        cv_generation_model=None,
        cv_prompt_id=None,
        cv_prompt_template_path=None,
        error=None,
    )

    assert record["ranking_fit_label"] == "strong"
    assert record["fit_classification"] == "skip"
    assert record["decision_chain"]["primary_fit"]["label"] == record["ranking_fit_label"]
    assert record["decision_chain"]["primary_fit"]["source"] == "reranker"
def test_review_required_reason_code_mapping_for_markdown_review() -> None:
    reason_code = _normalize_review_required_reason_code(
        status="review_required",
        error={"stage": "markdown_quality_review", "message": "Markdown quality requires review"},
    )
    assert reason_code is not None
    assert reason_code.value == "markdown_structure_violation"


def test_review_required_reason_code_mapping_for_policy_ratio_fail() -> None:
    reason_code = _normalize_review_required_reason_code(
        status="review_required",
        error={"stage": "policy_acceptance", "message": "Policy acceptance blocked (policy_required_ratio_fail): ratio"},
    )
    assert reason_code is not None
    assert reason_code.value == "policy_required_ratio_fail"


def test_evaluate_cv_acceptance_policy_downgrades_stretch_when_missing_above_threshold() -> None:
    policy = {
        "required_match": {
            "min_ratio_by_fit": {"strong": 0.8, "stretch": 0.5},
            "max_missing_by_fit": {"strong": 0, "stretch": 1},
        },
        "force_review_when_any_required_missing_for_fits": [],
    }
    pass_result = _evaluate_cv_acceptance_policy(
        fit_classification="stretch",
        gap_summary={"matched": ["sql"], "missing": ["excel"], "matchable_required_count": 2},
        policy=policy,
    )
    fail_result = _evaluate_cv_acceptance_policy(
        fit_classification="stretch",
        gap_summary={"matched": ["sql"], "missing": ["excel", "jira"], "matchable_required_count": 3},
        policy=policy,
    )
    assert pass_result[0] is True
    assert fail_result[0] is False
    assert fail_result[1] == "policy_required_ratio_fail"

def test_hitl_review_reason_for_unsupported_requirements_is_actionable() -> None:
    reason = _hitl_review_reason_for_agentic_case(
        analysis_record={
            "do_not_claim": ["snowflake"],
            "requirement_coverage": [
                {"requirement": "Snowflake", "support_strength": "unsupported"},
                {"requirement": "Talend", "support_strength": "insufficient"},
            ],
        },
        generation_result={"status": "accepted"},
        validation_snapshot=None,
    )
    assert reason is not None
    assert "Unsupported requirements require review:" in reason
    assert "Review the generated CV output against these requirements" in reason


def test_build_ranking_features_accepts_vector_search_field_names() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.93, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.71, "vector_rank": 2},
    ]
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["vector_similarity"] == pytest.approx(0.93)
    assert job1["vector_rank"] == 1


def test_build_ranking_features_carries_ai_score_fields() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Analyst",
            "seniority_target": "senior",
            "role_families": ["analytics"],
        },
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "similarity_score": 0.9,
            "rank": 1,
            "required_skills": ["SQL", "Python"],
            "job_title": "Business Intelligence Analyst",
            "job_family": "analytics",
            "location_type": "remote",
        },
        {
            "job_url": "https://example.com/2",
            "similarity_score": 0.7,
            "rank": 2,
            "required_skills": ["Spark"],
            "job_title": "ML Engineer",
            "job_family": "ml_engineering",
            "location_type": "onsite",
        },
    ]
    features = build_ranking_features(_make_shortlist(), _make_ai_scores(), profile, _ROLE_TAXONOMY_CONFIG)
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, _ROLE_TAXONOMY_CONFIG)
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["ai_score"] == pytest.approx(0.85)
    assert job1["must_have_match"] == pytest.approx(1.0)
    assert job1["title_relevance"] == pytest.approx(1.0)
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(0.65)
    assert job1["feature_contributions"]["ai_score"] == pytest.approx(0.34)
    assert job1["feature_contributions"]["preference_fit"] == pytest.approx(0.0325)


def test_run_pipeline_emits_run_all_stage_progress_after_normalize() -> None:
    progress_snapshots: list[dict[str, object]] = []
    config = {
        "pipeline": {"vector_search_top_n": 25, "final_top_n": 10},
        "paths": {"candidate_profile": "data/profile.yaml"},
    }
    raw_jobs = [{"job_url": "https://example.com/1", "job_title": "Data Analyst"}]
    normalized_jobs = [{"job_url": "https://example.com/1", "job_title": "Data Analyst"}]

    with patch("fitcv.pipeline.parse_jobs_file", return_value=raw_jobs), \
         patch("fitcv.pipeline.normalize_batch", return_value=normalized_jobs), \
         patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=(normalized_jobs, [])), \
         patch("fitcv.pipeline.prepare_raw_rows", return_value=[]), \
         patch("fitcv.pipeline.load_raw_jobs"), \
         patch(
             "fitcv.pipeline.apply_pre_enrichment_global_filters",
             return_value={"passed": ["https://example.com/1"], "rejected": []},
         ):
        with pytest.raises(PipelineCancelled):
            run_pipeline(
                jobs_path="data/jobs.json",
                config=config,
                run_id="run-progress-1",
                cancellation_check=lambda: True,
                stage_progress_callback=progress_snapshots.append,
            )

    assert len(progress_snapshots) == 1
    assert progress_snapshots[0]["last_completed_stage"] == "normalize"
    assert progress_snapshots[0]["completed_stages"] == ["normalize"]


def test_materialize_scoring_shortlist_excludes_raw_hits_absent_from_passed_jobs() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Engineer"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/999", "vector_similarity": 0.89, "vector_rank": 2},
    ]

    shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs)

    assert shortlist == [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "vector_similarity": 0.91,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        }
    ]


def test_materialize_scoring_shortlist_preserves_global_vector_ranks() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Engineer"},
        {"job_url": "https://example.com/2", "title": "Analytics Engineer"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.87, "vector_rank": 33},
    ]

    shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs)

    assert shortlist == [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "vector_similarity": 0.91,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        },
        {
            "job_url": "https://example.com/2",
            "title": "Analytics Engineer",
            "vector_similarity": 0.87,
            "vector_rank": 33,
            "shortlist_origin": "vector_search",
        },
    ]


def test_materialize_scoring_shortlist_preserves_only_retrieved_rows() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Engineer"},
        {"job_url": "https://example.com/2", "title": "Analytics Engineer"},
    ]

    shortlist = _materialize_scoring_shortlist(
        [{"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1}],
        passed_jobs,
    )

    assert [row["job_url"] for row in shortlist] == ["https://example.com/1"]


def test_build_ranking_features_uses_all_supported_weighted_features() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Analyst",
            "seniority_target": "senior",
            "domains": ["data_science"],
            "location_types": ["remote"],
            "role_families": ["analytics"],
        },
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Business Intelligence Analyst",
            "seniority": "senior",
            "job_family": "analytics",
            "location_type": "remote",
            "domain": "data_science",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.85, "fit_label": "strong"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.40,
            "must_have_match": 0.20,
            "vector_similarity": 0.15,
            "title_relevance": 0.10,
            "seniority_fit": 0.10,
            "preference_fit": 0.05,
        },
        "missing_value_defaults": {
            "ai_score": 0.0,
            "must_have_match": 0.5,
            "vector_similarity": 0.0,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "preference_fit": 0.5,
        },
        "preference_fit_weights": {
            "domain": 0.5,
            "role_family": 0.3,
            "location_type": 0.2,
        },
        **_ROLE_TAXONOMY_CONFIG,
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)
    job1 = features[0]

    assert job1["must_have_match"] == pytest.approx(1.0)
    assert job1["title_relevance"] == pytest.approx(1.0)
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(1.0)
    assert job1["feature_contributions"] == {
        "ai_score": pytest.approx(0.34),
        "must_have_match": pytest.approx(0.2),
        "vector_similarity": pytest.approx(0.135),
        "title_relevance": pytest.approx(0.1),
        "seniority_fit": pytest.approx(0.1),
        "preference_fit": pytest.approx(0.05),
    }
    assert job1["final_score"] == pytest.approx(
        (0.85 * 0.40) + (1.0 * 0.20) + (0.9 * 0.15) + (1.0 * 0.10) + (1.0 * 0.10) + (1.0 * 0.05)
    )


def test_build_ranking_features_preserves_zero_weight_features_in_payload() -> None:
    profile: dict = {
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {
            "target_role": "Data Engineer",
            "seniority_target": "senior",
            "domains": ["data_science"],
            "location_types": ["remote"],
        },
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Senior Data Engineer",
            "seniority": "senior",
            "job_family": "data_science",
            "location_type": "remote",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.85, "fit_label": "strong"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.73,
            "must_have_match": 0.0,
            "vector_similarity": 0.27,
            "title_relevance": 0.0,
            "seniority_fit": 0.0,
            "preference_fit": 0.0,
        },
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)
    job1 = features[0]

    assert job1["must_have_match"] == pytest.approx(1.0)
    assert "title_relevance" in job1
    assert job1["seniority_fit"] == pytest.approx(1.0)
    assert job1["preference_fit"] == pytest.approx(0.35)
    assert job1["final_score"] == pytest.approx((0.85 * 0.73) + (0.9 * 0.27))
    assert job1["feature_contributions"]["must_have_match"] == pytest.approx(0.0)
    assert job1["feature_contributions"]["title_relevance"] == pytest.approx(0.0)
    assert job1["feature_contributions"]["seniority_fit"] == pytest.approx(0.0)
    assert job1["feature_contributions"]["preference_fit"] == pytest.approx(0.0)


def test_build_ranking_features_prefers_missing_value_defaults_key() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [{"job_url": "https://example.com/1", "vector_similarity": None, "vector_rank": 1}]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.4, "fit_label": "stretch"}]
    config = {
        "ranking_weights": {
            "ai_score": 0.4,
            "must_have_match": 0.2,
            "vector_similarity": 0.15,
            "title_relevance": 0.1,
            "seniority_fit": 0.1,
            "preference_fit": 0.05,
        },
        "missing_value_defaults": {
            "ai_score": 0.0,
            "vector_similarity": 0.25,
            "must_have_match": 0.5,
            "title_relevance": 0.25,
            "seniority_fit": 0.25,
            "preference_fit": 0.25,
        },
        "ranking_null_defaults": {
            "ai_score": 0.0,
            "vector_similarity": 0.99,
        },
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)

    assert features[0]["final_score"] == pytest.approx(
        (0.4 * 0.4) + (0.5 * 0.2) + (0.25 * 0.15) + (0.5 * 0.1) + (0.5 * 0.1) + (0.5 * 0.05)
    )


def test_build_ranking_features_drops_jobs_missing_from_ai_scores() -> None:
    """Jobs in shortlist but absent from ai_scores (e.g. filtered upstream) are dropped."""
    shortlist = _make_shortlist() + [{"job_url": "https://example.com/99", "similarity_score": 0.5, "rank": 3}]
    profile: dict = {"preferences": {}}
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    assert all(f["job_url"] != "https://example.com/99" for f in features)


def test_stage_transition_artifacts_include_ranking_and_cv_generation_prompt_provenance() -> None:
    config = _minimal_config()
    config["prompts_runtime"] = {
        "enrich": {"extraction": {"prompt_id": "enrich.extraction.v1", "template_path": "enrich.md"}},
        "ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v1", "template_path": "ranking_ai_score_v1.md"}},
        "cv_generation": {
            "structured_write": {
                "prompt_id": "cv_generation.structured_write.v1",
                "template_path": "cv_generation_structured_write_v1.md",
            }
        },
    }
    raw_job = _minimal_job()
    enriched_job = {**raw_job, "title": "Data Analyst"}
    ai_score_row = {
        "job_url": raw_job["job_url"],
        "ai_score": 0.8,
        "fit_label": "strong",
        "score_reasoning": "Good fit",
        "matched_strengths": ["SQL"],
        "key_risks": [],
        "ai_score_reuse_status": "fresh_compute",
        "ai_score_input_fingerprint": "ai-score-fp",
    }
    ranked_row = {
        "job_url": raw_job["job_url"],
        "title": "Data Analyst",
        "final_score": 0.82,
        "ai_score": 0.8,
        "fit_label": "strong",
        "vector_similarity": 0.9,
        "vector_rank": 1,
    }
    cv_debug_record = _build_cv_generation_debug_record(
        job=ranked_row,
        status="accepted",
        fit_classification="strong",
        evidence_used=[],
        evidence_selection_summary={"selected_evidence_count": 1},
        analysis_input_summary={"required_skills": ["SQL"]},
        gap_summary={"matched": ["SQL"], "partial": [], "missing": []},
        structured_cv_initial={"schema_version": "cv_doc_v1"},
        validation_initial={"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
        repair_attempt={"performed": False, "missing_sections": []},
        structured_cv_final={"schema_version": "cv_doc_v1"},
        markdown_final="# CV",
        enabled_sections=["Experience", "Skills"],
        cv_generation_model="cx/gpt-5.4-mini",
        cv_prompt_id="cv_generation.structured_write.v1",
        cv_prompt_template_path="cv_generation_structured_write_v1.md",
        error=None,
    )

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[raw_job],
        normalized=[raw_job],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[enriched_job],
        passed_jobs=[enriched_job],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[{"job_url": raw_job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        shortlist=[{"job_url": raw_job["job_url"], "vector_similarity": 0.9, "vector_rank": 1, "shortlist_origin": "vector_search"}],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate summary",
        candidate_query_components={},
        candidate_query_debug={},
        ai_scores=[ai_score_row],
        ranking_inputs=[ranked_row],
        ranked=[ranked_row],
        cv_analysis_results=[{"job_url": raw_job["job_url"], "status": "ready_for_generation", "evidence_selection_summary": {"selected_evidence_count": 1}}],
        final_top_n=5,
        cv_generation_debug_records=[cv_debug_record],
        profile=_minimal_profile(),
        config=config,
        enrich_llm_runtime_observations=[
            {
                "contract_version": "llm_runtime_observation_v1",
                "scope_key": "enrich-1",
                "input_index": 0,
                "invocation_index": 1,
                "evidence": {
                    "contract_version": "llm_runtime_evidence_v1",
                    "status": "succeeded",
                    "provenance": {"adapter": "default", "runtime_path": "direct"},
                    "failure": None,
                },
            }
        ],
        ranking_llm_runtime_observations=[
            {
                "contract_version": "llm_runtime_observation_v1",
                "scope_key": "ranking-1",
                "input_index": 0,
                "invocation_index": 1,
                "evidence": {
                    "contract_version": "llm_runtime_evidence_v1",
                    "status": "succeeded",
                    "provenance": {"adapter": "default", "runtime_path": "direct"},
                    "failure": None,
                },
            }
        ],
    )

    ranking_summary = artifacts["stages"]["ranking"]["decision_summary"]
    assert ranking_summary["ranking_prompt_id"] == "ranking.ai_score.v1"
    assert ranking_summary["ranking_prompt_template_path"] == "ranking_ai_score_v1.md"
    assert ranking_summary["ai_score_model"] == "cx/gpt-5.4-mini"
    assert artifacts["stages"]["enrich"]["llm_runtime_summary"]["calls_total"] == 1
    assert artifacts["stages"]["ranking"]["llm_runtime_summary"]["calls_total"] == 1

    cv_generation_summary = artifacts["stages"]["cv_generation"]["decision_summary"]
    assert cv_generation_summary["cv_prompt_id"] == "cv_generation.structured_write.v1"
    assert cv_generation_summary["cv_prompt_template_path"] == "cv_generation_structured_write_v1.md"
    assert cv_generation_summary["cv_generation_model"] == "cx/gpt-5.4-mini"


def test_build_ranking_features_preserves_structured_job_fields_from_shortlist() -> None:
    profile: dict = {"preferences": {}}
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.93,
            "vector_rank": 1,
            "required_skills": ["SQL", "Python"],
            "title": "Structured Data Engineer",
            "years_required": 4,
        },
        {
            "job_url": "https://example.com/2",
            "vector_similarity": 0.71,
            "vector_rank": 2,
            "required_skills": ["Spark"],
            "title": "Structured ML Engineer",
            "years_required": 3,
        },
    ]
    features = build_ranking_features(shortlist, _make_ai_scores(), profile, {})
    job1 = next(f for f in features if f["job_url"] == "https://example.com/1")
    assert job1["required_skills"] == ["SQL", "Python"]
    assert job1["title"] == "Structured Data Engineer"
    assert job1["years_required"] == 4


def test_build_ranking_features_uses_inferred_effective_preferences_when_yaml_is_sparse() -> None:
    profile: dict = {
        "preferences": {"location_types": ["remote", "hybrid"]},
        "experiences": [
            {"role": "Senior Data Analyst", "role_family": "analytics", "domain_tags": ["banking"], "bullets": []},
            {"role": "BI Analyst", "domain_tags": ["retail"], "bullets": []},
        ],
        "projects": [],
        "skills": [{"name": "SQL"}],
        "achievements": [],
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "required_skills": ["SQL"],
            "title": "Business Intelligence Analyst",
            "job_family": "analytics",
            "domain": "banking",
            "location_type": "hybrid",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.8, "fit_label": "stretch"}]
    config = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "senior data analyst": "data analyst",
                "bi analyst": "data analyst",
                "business intelligence analyst": "data analyst",
                "data analyst": "data analyst",
            },
            "role_family_by_role": {
                "data analyst": "analytics",
            },
            "role_family_neighbors": {
                "analytics": ("data_science",),
            },
        }
    }

    features = build_ranking_features(shortlist, ai_scores, profile, config)

    assert features[0]["title_relevance"] == pytest.approx(1.0)
    assert features[0]["preference_fit"] == pytest.approx(1.0)
    assert features[0]["effective_preferences"]["target_role"] == "Data Analyst"
    assert features[0]["preference_sources"]["target_role"] == "inferred_recent_experience"


def test_build_ranking_features_prefers_required_skills_canonical_when_present() -> None:
    profile: dict = {
        "skills": [{"name": "Python"}],
        "preferences": {"target_role": "Data Engineer"},
    }
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "vector_similarity": 0.93,
            "vector_rank": 1,
            "required_skills": ["Python programming for data science"],
            "required_skills_canonical": ["python"],
            "title": "Structured Data Engineer",
        },
    ]
    ai_scores = [{"job_url": "https://example.com/1", "ai_score": 0.85, "fit_label": "strong"}]

    features = build_ranking_features(shortlist, ai_scores, profile, {})

    assert features[0]["must_have_match"] == pytest.approx(1.0)


@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_manual_pause_after_enrich_returns_checkpoint_summary(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_pre_filter: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_enrich.return_value = [job]

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="manual-enrich",
        stop_after_stage="enrich",
    )

    assert result["paused_after_stage"] == "enrich"
    assert result["next_stage"] == "rule_filter"
    assert result["completed_stages"] == ["normalize", "enrich"]
    assert len(result["checkpoint_payload"]["enriched"]) == 1
    assert result["checkpoint_payload"]["enriched"][0]["job_url"] == job["job_url"]


@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_resume_from_ranking_uses_checkpoint_payload(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_ai: MagicMock,
    mock_build_features: MagicMock,
    mock_rank: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    profile = _minimal_profile()
    shortlist = [{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}]
    checkpoint_payload = {
        "raw_jobs": [_minimal_job("https://example.com/1")],
        "normalized": [_minimal_job("https://example.com/1")],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [_minimal_job("https://example.com/1")],
        "passed_jobs": [_minimal_job("https://example.com/1")],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": shortlist,
        "shortlist": shortlist,
        "shortlist_diagnostics": {},
        "ai_scores": [],
        "ranking_inputs": [],
        "ranked": [],
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = profile
    mock_ai.return_value = [{"job_url": "https://example.com/1", "ai_score": 0.8, "fit_label": "strong"}]
    mock_build_features.return_value = [{"job_url": "https://example.com/1", "final_score": 0.9, "fit_label": "strong"}]
    mock_rank.return_value = []

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="resume-ranking",
        start_stage="ranking",
        stop_after_stage="ranking",
        checkpoint_payload=checkpoint_payload,
    )

    assert result["paused_after_stage"] == "ranking"
    assert result["next_stage"] == "cv_analysis"
    assert mock_ai.call_args.args[0] == shortlist


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_resume_from_checkpoint_uses_canonical_next_stage_only(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_candidate: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_compute_gap: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    profile = _minimal_profile()
    job = _minimal_job("https://example.com/1")
    ranked = [{
        **job,
        "job_url": job["job_url"],
        "final_score": 0.9,
        "ai_score": 0.8,
        "vector_rank": 1,
        "ranking_fit_label": "stretch",
        "fit_label": "stretch",
    }]
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist_diagnostics": {},
        "ai_scores": [{"job_url": job["job_url"], "ai_score": 0.8, "fit_label": "stretch"}],
        "ranking_inputs": ranked,
        "ranked": ranked,
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": [], "passed_records": [{"job_url": job["job_url"], "marks": []}]}
    mock_retrieve_evidence.return_value = [{"evidence_id": "e1", "evidence_type": "project", "source_ref": "p1", "name": "SQL"}]
    mock_compute_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="resume-canonical-next-stage",
        start_stage="rule_filter",
        stop_after_stage="cv_analysis",
        checkpoint_payload=checkpoint_payload,
    )

    assert result["paused_after_stage"] == "cv_analysis"
    assert result["completed_stages"] == ["normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis"]
    assert len(result["checkpoint_payload"]["cv_analysis_results"]) == 1
    assert result["checkpoint_payload"]["cv_analysis_results"][0]["job_url"] == job["job_url"]
    mock_filter.assert_not_called()
    mock_store_filter.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_compute_gap: MagicMock,
    mock_generate_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_cv: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    profile = _minimal_profile()
    job = _minimal_job("https://example.com/1")
    shortlist = [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}]
    ranked = [{
        **job,
        "job_url": job["job_url"],
        "final_score": 0.9,
        "ai_score": 0.8,
        "vector_rank": 1,
        "ranking_fit_label": "stretch",
        "fit_label": "stretch",
    }]
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": shortlist,
        "shortlist": shortlist,
        "shortlist_diagnostics": {},
        "ai_scores": [{"job_url": job["job_url"], "ai_score": 0.8, "fit_label": "stretch"}],
        "ranking_inputs": ranked,
        "ranked": ranked,
        "cv_analysis_results": [
                {
                    "job_url": job["job_url"],
                    "job_title": job["job_title"],
                    "status": "ready_for_generation",
                "ranking_fit_label": "stretch",
                "fit_classification": "stretch",
                "job_snapshot": ranked[0],
                "evidence_payload": [],
                "evidence_used": [],
                "gap_summary": {"matched": ["SQL"], "partial": [], "missing": [], "matchable_required_count": 1},
                "error": None,
            }
        ],
        "cv_results": [],
        "cv_generation_debug_records": [],
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = profile
    mock_retrieve_evidence.return_value = []
    mock_compute_gap.return_value = {"matched": [], "partial": [], "missing": []}
    mock_generate_cv.return_value = "# CV"
    mock_validate.return_value = {"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []}
    mock_store_cv.return_value = None

    with (
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="resume-cv-generation",
            start_stage="cv_generation",
            checkpoint_payload=checkpoint_payload,
        )

    assert result["cvs_generated"] == 1
    assert "shortlist_debug" not in result
    assert result["export_results"][0]["pipeline_status"] == "ranked_with_cv"
def test_pipeline_source_has_no_direct_ranking_fit_label_assignment_in_fresh_compute_branch() -> None:
    source = Path("src/fitcv/pipeline.py").read_text(encoding="utf-8")
    assert '"ranking_fit_label": fit' not in source


def test_pipeline_source_has_no_direct_ranking_fit_label_assignment_in_reuse_branch() -> None:
    source = Path("src/fitcv/pipeline.py").read_text(encoding="utf-8")
    assert '"ranking_fit_label": fit' not in source

@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_manual_pause_after_cv_analysis_returns_checkpoint_summary(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_compute_gap: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    profile = _minimal_profile()
    job = _minimal_job("https://example.com/1")
    ranked = [{
        **job,
        "job_url": job["job_url"],
        "final_score": 0.9,
        "ai_score": 0.8,
        "vector_rank": 1,
        "ranking_fit_label": "stretch",
        "fit_label": "stretch",
    }]
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist_diagnostics": {},
        "ai_scores": [{"job_url": job["job_url"], "ai_score": 0.8, "fit_label": "stretch"}],
        "ranking_inputs": ranked,
        "ranked": ranked,
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = profile
    mock_retrieve_evidence.return_value = [{"evidence_id": "e1", "evidence_type": "project", "source_ref": "p1", "name": "SQL"}]
    mock_compute_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="pause-cv-analysis",
        start_stage="cv_analysis",
        stop_after_stage="cv_analysis",
        checkpoint_payload=checkpoint_payload,
    )

    assert result["paused_after_stage"] == "cv_analysis"
    assert result["next_stage"] == "cv_generation"
    assert len(result["checkpoint_payload"]["cv_analysis_results"]) == 1
    assert result["checkpoint_payload"]["cv_analysis_results"][0]["status"] == "ready_for_generation"
    assert result["checkpoint_payload"]["cv_generation_debug_records"] == []


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_manual_pause_after_cv_analysis_preserves_reranker_blocked_debug_records(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_retrieve_bundle: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_gap: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job("https://example.com/blocked"),
        "title": "Blocked Before Analysis",
        "job_title": "Blocked Before Analysis",
        "required_skills": ["SQL"],
        "fit_label": "skip",
        "fit_label_source": "reranker",
        "final_rank": 1,
        "shortlist_origin": "vector_search",
    }
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1, "shortlist_origin": "vector_search"}],
        "shortlist_diagnostics": {},
        "ai_scores": [job],
        "ranking_inputs": [job],
        "ranked": [job],
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = _minimal_profile()

    with patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="pause-cv-analysis-reranker-block",
            start_stage="cv_analysis",
            stop_after_stage="cv_analysis",
            checkpoint_payload=checkpoint_payload,
        )

    mock_retrieve_bundle.assert_not_called()
    mock_retrieve_evidence.assert_not_called()
    mock_gap.assert_not_called()

    assert result["paused_after_stage"] == "cv_analysis"
    assert result["next_stage"] == "cv_generation"
    assert result["checkpoint_payload"]["cv_analysis_results"][0]["status"] == "blocked_by_reranker_fit"
    assert result["checkpoint_payload"]["cv_generation_debug_records"][0]["status"] == "blocked_by_reranker_fit"
    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_analysis_item"]
    assert len(item_calls) == 1
    metadata = json.loads(item_calls[0]["langfuse.observation.metadata"])
    assert metadata["deterministic_gate_result"] == "blocked_by_reranker_fit"
    assert metadata["output_structured"]["generation_readiness"] is False
    assert metadata["output_structured"]["disposition"] == "blocked_by_reranker_fit"
    assert metadata["output_structured"]["failure_summary"] == "Blocked https://example.com/blocked before CV analysis (reranker fit=skip)"
    assert "## Failure Summary" in item_calls[0]["langfuse.observation.output"]


@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job("https://example.com/blocked"),
        "title": "Blocked Before Analysis",
        "job_title": "Blocked Before Analysis",
        "required_skills": ["SQL"],
        "fit_label": "skip",
        "fit_label_source": "reranker",
        "final_rank": 1,
        "shortlist_origin": "vector_search",
    }
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1, "shortlist_origin": "vector_search"}],
        "shortlist_diagnostics": {},
        "ai_scores": [job],
        "ranking_inputs": [job],
        "ranked": [job],
        "cv_analysis_results": [
            {
                "job_url": job["job_url"],
                "status": "blocked_by_reranker_fit",
                "analysis_reuse_status": "not_run_reranker_skip",
                "fit_classification": "stretch",
                "outcome_reason": {
                    "stage": "reranker_fit",
                    "message": f"Blocked {job['job_url']} before CV analysis (reranker fit=skip)",
                },
            }
        ],
        "cv_generation_debug_records": [
            {
                "job_url": job["job_url"],
                "job_title": job["job_title"],
                "status": "blocked_by_reranker_fit",
                "fit_classification": "stretch",
                "ranking_fit_label": "skip",
                "decision_chain": {
                    "shortlist": {
                        "status": "returned_by_vector_search",
                        "advanced_to_scoring": True,
                    },
                    "ranking": {
                        "fit_label": "skip",
                        "fit_source": "reranker",
                    },
                    "cv_analysis": {
                        "status": "blocked_by_reranker_fit",
                        "completed": False,
                    },
                    "cv_generation": {
                        "status": "not_attempted",
                        "attempted": False,
                    },
                    "validation": {
                        "status": "not_applicable",
                        "passed": False,
                    },
                },
                "outcome_reason": {
                    "stage": "reranker_fit",
                    "message": f"Blocked {job['job_url']} before CV analysis (reranker fit=skip)",
                },
                "error": None,
            }
        ],
        "cv_results": [],
    }
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_profile_yaml.return_value = _minimal_profile()

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="resume-cv-generation-reranker-block",
        start_stage="cv_generation",
        checkpoint_payload=checkpoint_payload,
    )

    assert result["cvs_generated"] == 0
    assert result["cv_generation_debug_records"][0]["status"] == "blocked_by_reranker_fit"
    assert result["export_results"][0]["pipeline_status"] == "ranked_blocked_by_reranker_fit"
    assert result["export_results"][0]["decision_chain"]["cv_analysis"] == {
        "status": "blocked_by_reranker_fit",
        "completed": False,
    }


@patch("fitcv.pipeline.logger")
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_logs_full_validation_reasons(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
    mock_logger: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    job["fit_label"] = "strong"
    job["final_score"] = 0.91
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    validation = {
        "valid": False,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": ["Skill 'Rust' in CV Skills section is not in candidate knowledge base"],
        "warnings": [],
    }
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="validation_failed",
                markdown="# CV Markdown",
                validation_initial=validation,
                error={"stage": "validation", "message": "Skill mismatch"},
            ),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    record = result["cv_generation_debug_records"][0]
    assert record["status"] == "validation_failed"
    assert record["validation_initial"]["skill_violations"] == [
        "Skill 'Rust' in CV Skills section is not in candidate knowledge base"
    ]


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_generation.render_cv_markdown")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_retries_once_for_missing_sections_only(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_render_cv_markdown: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    job["fit_label"] = "strong"
    job["final_score"] = 0.91
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_create_version.return_value = {"version_id": "cv-1"}
    canonical_result = _agentic_generation_result(
        status="accepted",
        markdown="# Repaired Draft",
        validation_initial={
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
        },
    )
    canonical_result["repair_attempt"] = {
        "performed": True,
        "missing_sections": ["Experience"],
        "reason": "missing_or_shallow_sections",
    }
    canonical_result["cv_generation_trace"] = {"attempts": [{"attempt_index": 1}, {"attempt_index": 2}]}
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=canonical_result) as mock_agentic_gen,
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert result["cvs_generated"] == 1
    mock_agentic_gen.assert_called_once()
    mock_store_ver.assert_called_once()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_generation.render_cv_markdown")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_repairs_candidate_name_placeholder_without_llm_retry(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_render_cv_markdown: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """@proves cv_system.header-placeholder-repair"""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    job["fit_label"] = "strong"
    job["final_score"] = 0.91
    profile = _minimal_profile()
    placeholder_structured_cv = {
        "schema_version": "cv_doc_v1",
        "preset": "europass",
        "locale": "en",
        "job_url": job["job_url"],
        "fit_classification": "strong",
        "target_role": "Data Engineer",
        "sections": {
            "header": {
                "name": "Candidate Name",
                "title": "Data Engineer",
                "location": None,
                "contact": {"email": None, "phone": None, "linkedin": None},
            },
            "summary": {"text": "Grounded summary"},
            "experience": [
                {
                    "role": "Data Engineer",
                    "company": "ACME",
                    "start": None,
                    "end": None,
                    "location": None,
                    "bullets": ["Built pipelines"],
                }
            ],
            "projects": [],
            "education": [],
            "skills": {"groups": [{"label": "Core", "items": ["SQL"]}]},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

    cfg = _minimal_config()
    cfg["stage_runtime"] = {"cv_analysis": {"concurrency": 3}}
    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "text": "built pipelines"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_gen_cv.return_value = {
        "structured_cv": placeholder_structured_cv,
        "markdown": "# Candidate Name\n## Summary\nGrounded summary\n## Skills\nSQL\n## Experience\nBuilt pipelines",
    }
    mock_render_cv_markdown.return_value = "# Test Candidate\n## Summary\nGrounded summary\n## Skills\nSQL\n## Experience\nBuilt pipelines"
    mock_validate.side_effect = [
        {
            "valid": False,
            "missing_sections": [],
            "grounding_violations": [
                "Unresolved candidate-name placeholder detected in CV header: Candidate Name"
            ],
            "deterministic_grounding_violations": [],
            "semantic_grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
            "support_source_summary": {},
        },
        {
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "deterministic_grounding_violations": [],
            "semantic_grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
            "support_source_summary": {},
        },
    ]
    mock_create_version.return_value = {"version_id": "cv-1", "generated_at": "2026-04-08T12:00:00+00:00"}

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="accepted",
                structured_cv={
                    **placeholder_structured_cv,
                    "sections": {
                        **placeholder_structured_cv["sections"],
                        "header": {
                            **placeholder_structured_cv["sections"]["header"],
                            "name": "Test Candidate",
                        },
                    },
                },
                markdown="# Test Candidate\n## Summary\nGrounded summary\n## Skills\nSQL\n## Experience\nBuilt pipelines",
            ),
        ),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert result["cvs_generated"] == 1
    mock_gen_cv.assert_not_called()
    mock_validate.assert_not_called()
    mock_render_cv_markdown.assert_not_called()
    mock_store_ver.assert_called_once()


# ── run_pipeline (integrated, with all I/O mocked) ───────────────────────────

def _minimal_config() -> dict:
    return {
        "paths": {"candidate_profile": "data/candidate_profile.yaml"},
        "pipeline": {
            "vector_search_top_n": 2,
            "ai_score_top_n": 2,
            "final_top_n": 2,
            "evidence_top_k": 3,
        },
        "reuse": {"enrich": {"enabled": False}},
        # Nested CV config (preset-based)
        "cv": {
            "generation": {
                "model": "cx/gpt-5.4-mini",
                "prompt_version": "v1",
            },
            "preset": "europass",
            "composition": {
                "summary": {"enabled": True},
                "experience": {"enabled": True, "required": True},
                "skills": {"enabled": True, "required": True},
            },
            "content_rules": {"evidence_grounded_only": True},
            "validation": {"max_pages": 2},
            "agentic_late_stage": {"enabled": False},
        },
        # Compatibility flat keys (produced by _apply_cv_compatibility_projection)
        "cv_generation_model": "cx/gpt-5.4-mini",
        "required_cv_sections": ["Experience", "Skills"],
        "cv_max_pages": 2,
        "prompt_version": "v1",
    }


def _minimal_profile() -> dict:
    return {
        "name": "Test Candidate",
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "years_experience": 5,
        "preferences": {"target_role": "Data Engineer", "domains": []},
        "experiences": [{"role": "DE", "company": "ACME", "start": "2020", "end": "2022"}],
        "projects": [],
    }


def _minimal_job(url: str = "https://example.com/1") -> dict:
    return {
        "job_url": url,
        "job_title": "Data Engineer",
        "required_skills": ["SQL"],
        "years_required": 3,
        "vector_rank": 1,
        "ai_score": 0.85,
        "final_score": 0.80,
        "seniority": "senior",
        "location_type": "remote",
        "preferences": {},
    }


def test_cv_analysis_stage_concurrency_defaults_to_one() -> None:
    from fitcv.pipeline import _cv_analysis_stage_concurrency

    assert _cv_analysis_stage_concurrency({}) == 1
    assert _cv_analysis_stage_concurrency({"stage_runtime": {}}) == 1
    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {}}}) == 1


def test_cv_analysis_stage_concurrency_coerces_and_clamps() -> None:
    from fitcv.pipeline import _cv_analysis_stage_concurrency

    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {"concurrency": 4}}}) == 4
    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {"concurrency": "3"}}}) == 3
    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {"concurrency": 0}}}) == 1
    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {"concurrency": -2}}}) == 1
    assert _cv_analysis_stage_concurrency({"stage_runtime": {"cv_analysis": {"concurrency": "bad"}}}) == 1


def test_effective_stage_concurrency_caps_to_work_items() -> None:
    import fitcv.pipeline as pipeline

    effective_stage_concurrency = getattr(pipeline, "_effective_stage_concurrency", None)
    assert effective_stage_concurrency is not None
    assert effective_stage_concurrency(4, 0) == 0
    assert effective_stage_concurrency(4, 3) == 3
    assert effective_stage_concurrency(4, 5) == 4

def _canonical_reusable_cv_analysis_record(
    job: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    from fitcv.agentic_cv_analysis import analyze_ranked_job
    from fitcv.enrich import build_raw_job_fingerprint

    job["raw_job_fingerprint"] = build_raw_job_fingerprint(job)["fingerprint"]
    evidence = {
        "evidence_id": "e1",
        "evidence_type": "experience_entry",
        "source_ref": "experiences[0]",
        "name": "DE",
    }
    with (
        patch(
            "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
            return_value={
                "selected_evidence": [evidence],
                "selected_evidence_ids": ["e1"],
                "selected_evidence_count": 1,
            },
        ),
        patch(
            "fitcv.agentic_cv_analysis.compute_gap",
            return_value={"matched": ["SQL"], "partial": [], "missing": []},
        ),
    ):
        return dict(analyze_ranked_job(job, profile, config))


def _agentic_analysis_ready(
    job: dict[str, Any],
    *,
    fit_classification: str = "strong",
    evidence_payload: list[dict[str, Any]] | None = None,
    gap_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence_payload or [
        {
            "evidence_id": "e1",
            "evidence_type": "experience_entry",
            "source_ref": "experience[0]",
            "name": "Data Engineer at Fintech Startup GmbH",
            "matched_channels": ["required_skill_support"],
            "selection_reasons": ["required_skill_support"],
        }
    ]
    return build_agentic_cv_analysis_record(
        job=job,
        status="ready_for_generation",
        analysis_input_fingerprint="analysis-fp",
        analysis_reuse_status="fresh_compute",
        evidence_payload=evidence,
        evidence_selection_summary={"selected_evidence_ids": [str(evidence[0].get("evidence_id") or "e1")]},
        gap_summary=gap_summary or {"matched": ["SQL"], "partial": [], "missing": []},
        fit_classification=fit_classification,
        error=None,
        requirement_coverage=None,
        section_confidence_hints=None,
        do_not_claim=[],
    )

def _agentic_generation_result(
    *,
    status: str = "accepted",
    fit_classification: str = "strong",
    structured_cv: dict[str, Any] | None = None,
    markdown: str | None = "# CV Markdown",
    validation_initial: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
    job_url: str = "https://example.com/1",
    job_title: str = "Data Engineer",
) -> dict[str, Any]:
    resolved_structured_cv = structured_cv or {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer"},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    resolved_validation_initial = validation_initial
    if status == "accepted" and resolved_validation_initial is None:
        resolved_validation_initial = {
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "deterministic_grounding_violations": [],
            "semantic_grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
            "support_source_summary": {},
        }
    if status == "validation_failed" and resolved_validation_initial is not None:
        resolved_validation_initial = {
            **resolved_validation_initial,
            "deterministic_grounding_violations": list(
                resolved_validation_initial.get("deterministic_grounding_violations") or []
            ),
            "semantic_grounding_violations": list(
                resolved_validation_initial.get("semantic_grounding_violations") or []
            ),
            "support_source_summary": dict(resolved_validation_initial.get("support_source_summary") or {}),
        }

    validation = resolved_validation_initial
    review_reason_code = _normalize_review_required_reason_code(
        status=status,
        error=error,
        validation_initial=validation,
    )
    result = {
        "result_contract_version": "cv_generation_result_v2",
        "raw_job_fingerprint": "raw-job-fp",
        "job_url": job_url,
        "job_title": job_title,
        "analysis_input_fingerprint": "analysis-fp",
        "cv_generation_input_fingerprint": "generation-fp",
        "cv_generation_input_components": {"schema_version": "cv_generation_input_v2"},
        "cv_generation_reuse_status": "fresh_compute",
        "reuse_decision": {"decision": "fresh_compute", "reason_code": "fresh_compute_required"},
        "reused_cv_version_id": None,
        "status": status,
        "ranking_fit_label": fit_classification,
        "fit_classification": fit_classification,
        "decision_chain": build_decision_chain(
            job={"job_url": job_url, "title": job_title, "fit_label": fit_classification},
            fit_classification=fit_classification,
            cv_analysis_status="ready_for_generation",
            cv_status=status,
        ),
        "analysis_input_summary": {"job_excerpt": "Data engineer role"},
        "evidence_used": [
            {
                "evidence_type": "experience_entry",
                "source_ref": "experience[0]",
                "name": "Data Engineer at Fintech Startup GmbH",
                "matched_channels": [],
                "selection_reasons": [],
            }
        ],
        "evidence_selection_summary": {"selected_evidence_ids": ["e1"]},
        "gap_summary": {"matched": ["SQL"], "partial": [], "missing": []},
        "structured_cv_initial": resolved_structured_cv if status != "generation_failed" else None,
        "validation_initial": resolved_validation_initial,
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": (
            resolved_structured_cv if status in {"accepted", "persistence_failed", "review_required"} else None
        ),
        "markdown_final": markdown if status in {"accepted", "persistence_failed", "review_required"} else None,
        "validation": validation,
        "outcome_reason": None,
        "review_required_reason_code": review_reason_code.value if review_reason_code is not None else None,
        "runtime_provenance": {
            "route_part": "cv_generation",
            "runtime_path": "fitcv_cv_generation_openai_compatible",
            "adapter": "direct",
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "wire_api": "chat_completions",
        },
        "llm_runtime_observations": [
            {
                "contract_version": "llm_runtime_observation_v1",
                "scope_key": job_url,
                "input_index": 0,
                "invocation_index": 1,
                "evidence": {
                    "contract_version": "llm_runtime_evidence_v1",
                    "status": "succeeded",
                    "provenance": {
                        "routing_part": "cv_generation_structured_write",
                        "runtime_path": "fitcv_cv_generation_openai_compatible",
                        "adapter": "direct",
                        "provider": "openai_compatible",
                        "model": "cx/gpt-5.2",
                        "wire_api": "chat_completions",
                        "attempt_count": 1,
                    },
                    "failure": None,
                },
            }
        ],
        "cv_generation_trace": {},
        "error": error,
    }
    result["validation_evidence_fingerprint"] = build_validation_evidence_fingerprint(
        status=status,
        validation=validation,
        error=error,
    )
    return result

def _raw_scraper_job(url: str = "https://example.com/1") -> dict:
    return {
        "jobUrl": url,
        "title": "Data Engineer",
        "location": "Remote",
        "postedTime": "1 day ago",
        "publishedAt": "2026-03-24",
        "companyName": "ACME",
        "companyUrl": "https://example.com/company",
        "companyId": "123",
        "description": "Build data pipelines",
        "applicationsCount": "10 applicants",
        "contractType": "Full-time",
        "experienceLevel": "Mid-Senior level",
        "workType": "Engineering",
        "sector": "Software",
        "salary": "",
        "applyUrl": "https://example.com/apply",
        "applyType": "EXTERNAL",
        "posterFullName": "Hiring Manager",
        "posterProfileUrl": "https://example.com/poster",
    }


def test_build_ai_score_input_fingerprint_changes_when_reranker_contract_changes() -> None:
    from fitcv.ai_score import build_ai_score_input_fingerprint
    from fitcv.vector_search import build_candidate_query_text

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    candidate_summary = build_candidate_query_text(profile, config)

    baseline = build_ai_score_input_fingerprint(
        job,
        candidate_summary,
        [],
        config,
    )["fingerprint"]

    changed = build_ai_score_input_fingerprint(
        job,
        candidate_summary,
        [],
        {
            **config,
            "ai_score_model": "cx/gpt-5.5",
        },
    )["fingerprint"]

    assert changed == baseline


def test_build_cv_analysis_input_fingerprint_changes_when_semantic_alignment_changes() -> None:
    from fitcv.evidence import build_cv_analysis_input_fingerprint

    profile = _minimal_profile()
    job = _minimal_job()
    config = _minimal_config()

    baseline = build_cv_analysis_input_fingerprint(
        profile,
        job,
        config,
    )["fingerprint"]

    changed = build_cv_analysis_input_fingerprint(
        profile,
        job,
        {
            **config,
            "cv_analysis": {
                "semantic_alignment": {
                    "enabled": True,
                    "responsibility_lexical_weight": 0.10,
                    "responsibility_semantic_weight": 0.90,
                    "domain_lexical_weight": 0.30,
                    "domain_semantic_weight": 0.70,
                    "channel_pool_size": 6,
                }
            },
        },
    )["fingerprint"]

    assert changed != baseline


def test_build_cv_analysis_input_fingerprint_ignores_runtime_entry_count_only() -> None:
    from fitcv.evidence import build_cv_analysis_input_fingerprint

    profile = _minimal_profile()
    job = _minimal_job()
    config = _minimal_config()
    config["skill_synonyms"] = {"sql": "structured query language"}
    config["skill_synonyms_runtime"] = {
        "base_policy_path": "/app/config/taxonomy/skill_synonyms.yaml",
        "overlay_paths": [],
        "has_overlay": False,
        "entry_count": 159,
    }

    baseline = build_cv_analysis_input_fingerprint(
        profile,
        job,
        config,
    )["fingerprint"]

    changed_runtime_only = {
        **config,
        "skill_synonyms_runtime": {
            **config["skill_synonyms_runtime"],
            "entry_count": 310,
        },
    }
    stable = build_cv_analysis_input_fingerprint(
        profile,
        job,
        changed_runtime_only,
    )["fingerprint"]

    assert stable == baseline


def test_run_pipeline_reuses_exact_match_ai_scores() -> None:
    """@proves cv_system.exact-match-late-stage-reuse"""
    from fitcv.ai_score import build_ai_score_input_fingerprint
    from fitcv.pipeline import run_pipeline
    from fitcv.vector_search import build_candidate_query_text

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    candidate_summary = build_candidate_query_text(profile, config)
    ai_score_fingerprint = build_ai_score_input_fingerprint(
        job,
        candidate_summary,
        [],
        config,
    )["fingerprint"]
    reused_ai_row = {
        "job_url": job["job_url"],
        "ai_score": 0.92,
        "fit_label": "strong",
        "score_reasoning": "Exact-match reused AI score.",
        "matched_strengths": ["SQL"],
        "key_risks": [],
        "ai_score_input_fingerprint": ai_score_fingerprint,
        "ai_score_reuse_status": "reused_exact_match",
    }
    reuse_snapshots = {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [
            {
                "job_url": job["job_url"],
                "ai_score_input_fingerprint": ai_score_fingerprint,
                "ai_score_row": reused_ai_row,
            }
        ],
        "cv_analysis_records": [],
    }

    with patch("fitcv.pipeline.load_config", return_value=config), \
         patch("fitcv.pipeline.parse_jobs_file", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])), \
         patch("fitcv.pipeline.load_raw_jobs"), \
         patch("fitcv.pipeline.apply_pre_enrichment_global_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}), \
         patch("fitcv.pipeline.enrich_batch", return_value=[job]), \
         patch("fitcv.pipeline.load_structured_jobs"), \
         patch("fitcv.pipeline.load_run_structured_jobs"), \
         patch("fitcv.pipeline.load_profile_yaml", return_value=profile), \
         patch("fitcv.pipeline.load_candidate_profile"), \
         patch("fitcv.pipeline.apply_rule_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.store_filter_results"), \
         patch("fitcv.pipeline.embed_and_store_jobs"), \
         patch(
             "fitcv.pipeline.run_vector_search",
             return_value=_vector_search_envelope(
                 [{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}],
                 candidate_query={"components": {}, "text": candidate_summary},
             ),
         ), \
         patch("fitcv.pipeline.run_ai_scoring") as mock_ai_scoring, \
         patch("fitcv.pipeline.store_final_ranking"):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            reuse_snapshots=reuse_snapshots,
            stop_after_stage="ranking",
        )

    mock_ai_scoring.assert_not_called()
    ranking_block = result["stage_transition_artifacts"]["stages"]["ranking"]
    assert ranking_block["decision_summary"]["reuse_metrics"] == {
        "reused_ai_scores": 1,
        "fresh_ai_scores": 0,
        "total_ai_scores": 1,
    }
    assert ranking_block["inputs_sample"][0]["ai_score_reuse_status"] == "reused_exact_match"
    assert ranking_block["inputs_sample"][0]["ai_score_input_fingerprint"] == ai_score_fingerprint


def test_run_pipeline_reuses_exact_match_cv_analysis_records() -> None:
    """@proves cv_system.exact-match-late-stage-reuse"""
    from fitcv.evidence import build_cv_analysis_input_fingerprint
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "required_skills": ["SQL"],
        "preferred_skills": ["Python"],
        "responsibilities": ["Build data pipelines for stakeholders."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    reused_analysis_record = _canonical_reusable_cv_analysis_record(job, profile, config)
    analysis_fingerprint = str(reused_analysis_record["analysis_input_fingerprint"])
    reuse_snapshots = {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [],
        "cv_analysis_records": [
            {
                "job_url": job["job_url"],
                "analysis_input_fingerprint": analysis_fingerprint,
                "analysis_record": reused_analysis_record,
            }
        ],
    }

    with patch("fitcv.pipeline.load_config", return_value=config), \
         patch("fitcv.pipeline.parse_jobs_file", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])), \
         patch("fitcv.pipeline.load_raw_jobs"), \
         patch("fitcv.pipeline.apply_pre_enrichment_global_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}), \
         patch("fitcv.pipeline.enrich_batch", return_value=[job]), \
         patch("fitcv.pipeline.load_structured_jobs"), \
         patch("fitcv.pipeline.load_run_structured_jobs"), \
         patch("fitcv.pipeline.load_profile_yaml", return_value=profile), \
         patch("fitcv.pipeline.load_candidate_profile"), \
         patch("fitcv.pipeline.apply_rule_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.store_filter_results"), \
         patch("fitcv.pipeline.embed_and_store_jobs"), \
         patch("fitcv.pipeline.run_vector_search", return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}])), \
         patch("fitcv.pipeline.run_ai_scoring", return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}]), \
         patch("fitcv.pipeline.store_final_ranking"), \
         patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle") as mock_retrieve_bundle, \
         patch("fitcv.agentic_cv_analysis.compute_gap") as mock_compute_gap:
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            reuse_snapshots=reuse_snapshots,
            stop_after_stage="cv_analysis",
        )

    mock_retrieve_bundle.assert_not_called()
    mock_compute_gap.assert_not_called()
    cv_analysis_block = result["stage_transition_artifacts"]["stages"]["cv_analysis"]
    assert cv_analysis_block["decision_summary"]["reuse_metrics"] == {
        "analysis_rows_executed": 1,
        "reused_analysis_rows": 1,
        "fresh_analysis_rows": 0,
        "blocked_before_analysis_rows": 0,
        "analysis_reuse_rate": 1.0,
    }
    assert cv_analysis_block["outputs_sample"][0]["analysis_reuse_status"] == "reused_exact_match"
    assert cv_analysis_block["outputs_sample"][0]["analysis_input_fingerprint"] == analysis_fingerprint



def test_run_pipeline_emits_cv_analysis_item_observation_for_reused_analysis() -> None:
    from fitcv.evidence import build_cv_analysis_input_fingerprint
    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "required_skills": ["SQL"],
        "preferred_skills": ["Python"],
        "responsibilities": ["Build data pipelines for stakeholders."],
        "description": "Need strong SQL and pipeline delivery experience.",
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    reused_analysis_record = _canonical_reusable_cv_analysis_record(job, profile, config)
    analysis_fingerprint = str(reused_analysis_record["analysis_input_fingerprint"])
    reuse_snapshots = {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [],
        "cv_analysis_records": [
            {
                "job_url": job["job_url"],
                "analysis_input_fingerprint": analysis_fingerprint,
                "analysis_record": reused_analysis_record,
            }
        ],
    }

    with patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span), \
         patch("fitcv.pipeline.load_config", return_value=config), \
         patch("fitcv.pipeline.parse_jobs_file", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch", return_value=[job]), \
         patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])), \
         patch("fitcv.pipeline.load_raw_jobs"), \
         patch("fitcv.pipeline.apply_pre_enrichment_global_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}), \
         patch("fitcv.pipeline.enrich_batch", return_value=[job]), \
         patch("fitcv.pipeline.load_structured_jobs"), \
         patch("fitcv.pipeline.load_run_structured_jobs"), \
         patch("fitcv.pipeline.load_profile_yaml", return_value=profile), \
         patch("fitcv.pipeline.load_candidate_profile"), \
         patch("fitcv.pipeline.apply_rule_filters", return_value={"passed": [job["job_url"]], "rejected": []}), \
         patch("fitcv.pipeline.store_filter_results"), \
         patch("fitcv.pipeline.embed_and_store_jobs"), \
         patch("fitcv.pipeline.run_vector_search", return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}])), \
         patch("fitcv.pipeline.run_ai_scoring", return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}]), \
         patch("fitcv.pipeline.store_final_ranking"), \
         patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle") as mock_retrieve_bundle, \
         patch("fitcv.agentic_cv_analysis.compute_gap") as mock_compute_gap:
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            reuse_snapshots=reuse_snapshots,
            stop_after_stage="cv_analysis",
        )

    mock_retrieve_bundle.assert_not_called()
    mock_compute_gap.assert_not_called()
    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_analysis_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    assert item_attributes["langfuse.observation.name"] == "cv_analysis_item"
    assert item_attributes["langfuse.observation.input"].startswith("## Job")
    assert "### Requirements Excerpt" in item_attributes["langfuse.observation.input"]
    assert "## Candidate" in item_attributes["langfuse.observation.input"]
    assert item_attributes["langfuse.observation.output"].startswith("## Fit Decision")
    assert "## Generation Readiness" in item_attributes["langfuse.observation.output"]
    metadata = json.loads(item_attributes["langfuse.observation.metadata"])
    assert metadata["analysis_reuse_status"] == "reused_exact_match"
    assert metadata["reuse_status"] == "reused_exact_match"
    assert metadata["selected"] is True
    assert metadata["input_structured"]["job_id"] == job["job_url"]
    assert metadata["input_structured"]["requirements_excerpt"] == ["SQL"]

def test_run_pipeline_emits_cv_generation_item_observation_for_accepted_generation() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Test Candidate", "title": "Data Engineer"},
            "summary": {"text": "Grounded summary."},
            "experience": [{"role": "DE", "company": "ACME"}],
            "skills": {"groups": [{"name": "Core", "items": ["SQL", "Python"]}]},
        },
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.generate_cv",
                return_value={"structured_cv": structured_cv, "markdown": "# Test Candidate\n\n## Summary\nGrounded summary."},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.run_all_validations",
                return_value={"valid": True, "missing_sections": [], "grounding_violations": [], "skill_violations": [], "warnings": []},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.create_cv_version_record",
                return_value={"version_id": "v1", "generated_at": "2026-05-09T00:00:00Z"},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.PipelineStore.store_cv_version"))
        generation_result = _agentic_generation_result(
            status="accepted",
            structured_cv=structured_cv,
            markdown="# Test Candidate\n\n## Summary\nGrounded summary.",
            validation_initial={
                "valid": True,
                "missing_sections": [],
                "grounding_violations": [],
                "skill_violations": [],
                "warnings": [],
            },
        )
        generation_result["analysis_input_summary"] = {
            "job_id": job["job_url"],
            "constraints": ["SQL", "Python"],
        }
        stack.enter_context(patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)))
        stack.enter_context(patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result))
        stack.enter_context(patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None))
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    assert item_attributes["langfuse.observation.name"] == "cv_generation_item"
    assert item_attributes["langfuse.observation.input"].startswith("## Job")
    assert "## Selected Evidence" in item_attributes["langfuse.observation.input"]
    assert item_attributes["langfuse.observation.output"].startswith("## Status")
    assert "## Generated CV Markdown" in item_attributes["langfuse.observation.output"]
    metadata = json.loads(item_attributes["langfuse.observation.metadata"])
    assert metadata["status"] == "accepted"
    assert metadata["job_url"] == job["job_url"]
    assert metadata["analysis_input_fingerprint"]
    assert metadata["parent_observation_name"] == "cv_analysis_item"
    assert metadata["input_structured"]["job_id"] == job["job_url"]
    assert metadata["input_structured"]["constraints"] == ["SQL", "Python"]
    assert metadata["output_structured"]["cv_markdown"].startswith("# Test Candidate")
    assert metadata["output_structured"]["validation_summary"]["valid"] is True
    assert metadata["output_structured"]["persistence_outcome"] == "stored"



def test_run_pipeline_emits_cv_generation_item_observation_for_validation_failed() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Test Candidate", "title": "Data Engineer"},
            "summary": {"text": "Grounded summary."},
            "experience": [{"role": "DE", "company": "ACME"}],
            "skills": {"groups": [{"name": "Core", "items": ["SQL", "Python"]}]},
        },
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.generate_cv",
                return_value={"structured_cv": structured_cv, "markdown": "# Test Candidate\n\n## Summary\nGrounded summary."},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.run_all_validations",
                return_value={
                    "valid": False,
                    "missing_sections": ["Skills"],
                    "grounding_violations": [],
                    "deterministic_grounding_violations": [],
                    "semantic_grounding_violations": [],
                    "skill_violations": [],
                    "markdown_quality_blocking_issues": [],
                    "markdown_quality_review_flags": [],
                    "warnings": [],
                    "support_source_summary": {},
                },
            )
        )
        stack.enter_context(patch("fitcv.pipeline.create_cv_version_record"))
        stack.enter_context(patch("fitcv.pipeline.PipelineStore.store_cv_version"))
        generation_result = _agentic_generation_result(
            status="validation_failed",
            structured_cv=structured_cv,
            markdown="# Test Candidate\n\n## Summary\nGrounded summary.",
            validation_initial={
                "valid": False,
                "missing_sections": ["Skills"],
                "grounding_violations": [],
                "deterministic_grounding_violations": [],
                "semantic_grounding_violations": [],
                "skill_violations": [],
                "markdown_quality_blocking_issues": [],
                "markdown_quality_review_flags": [],
                "warnings": [],
                "support_source_summary": {},
            },
            error={"stage": "validation", "message": "Missing sections: Skills"},
        )
        generation_result["analysis_input_summary"] = {
            "job_id": job["job_url"],
            "constraints": ["SQL", "Python"],
        }
        stack.enter_context(patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)))
        stack.enter_context(patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result))
        stack.enter_context(patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None))
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    assert item_attributes["langfuse.observation.name"] == "cv_generation_item"
    assert item_attributes["langfuse.observation.output"].startswith("## Status")
    assert "## Review Issues" in item_attributes["langfuse.observation.output"]
    metadata = json.loads(item_attributes["langfuse.observation.metadata"])
    assert metadata["status"] == "validation_failed"
    assert metadata["job_url"] == job["job_url"]
    assert metadata["parent_observation_name"] == "cv_analysis_item"
    assert metadata["output_structured"]["status"] == "validation_failed"
    assert metadata["output_structured"]["validation_summary"]["valid"] is False
    assert metadata["output_structured"]["validation_summary"]["review_issues"] == ["Skills"]
    assert metadata["output_structured"]["persistence_outcome"] == "validation_failed"



def test_run_pipeline_emits_cv_generation_item_observation_for_review_required() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Test Candidate", "title": "Data Engineer"},
            "summary": {"text": "Grounded summary."},
            "experience": [{"role": "DE", "company": "ACME"}],
            "skills": {"groups": [{"name": "Core", "items": ["SQL", "Python"]}]},
        },
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.generate_cv",
                return_value={"structured_cv": structured_cv, "markdown": "# Test Candidate\n\n## Summary\nGrounded summary."},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_generation.run_all_validations",
                return_value={
                    "valid": True,
                    "missing_sections": [],
                    "grounding_violations": [],
                    "deterministic_grounding_violations": [],
                    "semantic_grounding_violations": [],
                    "skill_violations": [],
                    "markdown_quality_blocking_issues": [],
                    "markdown_quality_review_flags": ["bullets too dense"],
                    "warnings": [],
                    "support_source_summary": {},
                },
            )
        )
        stack.enter_context(patch("fitcv.pipeline.create_cv_version_record"))
        stack.enter_context(patch("fitcv.pipeline.PipelineStore.store_cv_version"))
        generation_result = _agentic_generation_result(
            status="review_required",
            structured_cv=structured_cv,
            markdown="# Test Candidate\n\n## Summary\nGrounded summary.",
            validation_initial={
                "valid": True,
                "missing_sections": [],
                "grounding_violations": [],
                "deterministic_grounding_violations": [],
                "semantic_grounding_violations": [],
                "skill_violations": [],
                "markdown_quality_blocking_issues": [],
                "markdown_quality_review_flags": ["bullets too dense"],
                "warnings": [],
                "support_source_summary": {},
            },
        )
        generation_result["analysis_input_summary"] = {
            "job_id": job["job_url"],
            "constraints": ["SQL", "Python"],
        }
        generation_result["validation"] = dict(generation_result["validation_initial"])
        generation_result["review_required_reason_code"] = "markdown_structure_violation"
        generation_result["validation_evidence_fingerprint"] = "validation::markdown-review"
        generation_result["outcome_reason"] = {
            "stage": "review",
            "code": "markdown_structure_violation",
            "message": "Markdown quality requires review: bullets too dense",
        }
        stack.enter_context(patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)))
        stack.enter_context(patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result))
        stack.enter_context(
            patch(
                "fitcv.pipeline._hitl_review_reason_for_agentic_case",
                return_value="Markdown quality requires review: bullets too dense",
            )
        )
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert result["cv_generation_debug_records"][0]["status"] == "review_required"
    if item_calls:
        item_attributes = item_calls[0]
        metadata = json.loads(item_attributes["langfuse.observation.metadata"])
        assert metadata["status"] == "review_required"
        assert metadata["output_structured"]["status"] == "review_required"
        assert metadata["output_structured"]["validation_summary"]["valid"] is True
        assert metadata["output_structured"]["validation_summary"]["review_issues"] == ["bullets too dense"]
        assert metadata["output_structured"]["persistence_outcome"] == "review_required"
        assert "## Review Issues" in item_attributes["langfuse.observation.output"]



def test_run_pipeline_emits_cv_generation_item_observation_for_persistence_failed() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Test Candidate", "title": "Data Engineer"},
            "summary": {"text": "Grounded summary."},
            "experience": [{"role": "DE", "company": "ACME"}],
            "skills": {"groups": [{"name": "Core", "items": ["SQL", "Python"]}]},
        },
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_agentic_cv_generation",
                return_value=_agentic_generation_result(
                    status="persistence_failed",
                    structured_cv=structured_cv,
                    markdown="# Test Candidate\n\n## Summary\nGrounded summary.",
                    error={"stage": "persistence", "message": "db down"},
                ),
            )
        )
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    metadata = json.loads(item_attributes["langfuse.observation.metadata"])
    assert metadata["status"] == "persistence_failed"
    assert metadata["output_structured"]["status"] == "persistence_failed"
    assert metadata["output_structured"]["cv_markdown"].startswith("# Test Candidate")
    assert metadata["output_structured"]["persistence_outcome"] == "persistence_failed"
    assert metadata["output_structured"]["failure_summary"] == "db down"
    assert "## Failure Summary" in item_attributes["langfuse.observation.output"]



def test_run_pipeline_emits_cv_generation_item_observation_for_generation_failed() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_agentic_cv_generation",
                return_value=_agentic_generation_result(
                    status="generation_failed",
                    error={"stage": "generation", "message": "llm down"},
                ),
            )
        )
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    metadata = json.loads(item_attributes["langfuse.observation.metadata"])
    assert metadata["status"] == "generation_failed"
    assert metadata["output_structured"]["status"] == "generation_failed"
    assert metadata["output_structured"]["failure_summary"] == "llm down"
    assert metadata["output_structured"]["persistence_outcome"] == "generation_failed"
    assert "## Failure Summary" in item_attributes["langfuse.observation.output"]



def test_run_pipeline_emits_cv_generation_item_retry_metadata_for_agentic_generation_failure() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    failed_result = {
        "status": "generation_failed",
        "fit_classification": "strong",
        "analysis_input_summary": {"job_excerpt": "Data engineer role"},
        "evidence_used": [{"name": "ACME Data Engineering", "source_ref": "experiences[0]", "evidence_type": "experience_entry"}],
        "evidence_selection_summary": {"selected_evidence_ids": ["e1"]},
        "gap_summary": {"matched": ["SQL"], "partial": [], "missing": []},
        "structured_cv_initial": None,
        "validation_initial": None,
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": None,
        "markdown_final": None,
        "runtime_provenance": {"provider": "gemini", "model": "gemini-test"},
        "cv_generation_trace": {"attempts": [{"attempt_index": 1}, {"attempt_index": 2}]},
        "error": {"stage": "generation", "message": "model timeout"},
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_agentic_cv_generation",
                return_value=dict(failed_result),
            )
        )
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    metadata = json.loads(item_calls[0]["langfuse.observation.metadata"])
    assert metadata["status"] == "generation_failed"
    assert metadata["attempt_count"] == 2
    assert metadata["output_structured"]["failure_summary"] == "model timeout"
    assert metadata["output_structured"]["persistence_outcome"] == "generation_failed"
    assert "## Failure Summary" in item_attributes["langfuse.observation.output"]



def test_run_pipeline_emits_cv_generation_item_selected_retry_success_metadata() -> None:
    from contextlib import ExitStack

    from fitcv.pipeline import run_pipeline

    observed_calls: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def _capture_observe_span(name: str, *, attributes: dict[str, Any] | None = None):
        observed_calls.append((name, dict(attributes or {})))
        yield None

    job = {
        **_minimal_job(),
        "title": "Data Engineer",
        "description": "Build reliable data pipelines and analytics products.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Airflow"],
        "responsibilities": ["Own ELT workflows."],
        "domain": "banking",
        "job_family": "analytics",
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    failed_result = {
        "status": "generation_failed",
        "fit_classification": "strong",
        "analysis_input_summary": {"job_excerpt": "Data engineer role"},
        "evidence_used": [{"name": "ACME Data Engineering", "source_ref": "experiences[0]", "evidence_type": "experience_entry"}],
        "evidence_selection_summary": {"selected_evidence_ids": ["e1"]},
        "gap_summary": {"matched": ["SQL"], "partial": [], "missing": []},
        "structured_cv_initial": None,
        "validation_initial": None,
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": None,
        "markdown_final": None,
        "runtime_provenance": {"provider": "gemini", "model": "gemini-test"},
        "cv_generation_trace": {},
        "error": {"stage": "generation", "message": "model timeout"},
    }
    accepted_result = {
        "status": "accepted",
        "fit_classification": "strong",
        "analysis_input_summary": {"job_excerpt": "Data engineer role"},
        "evidence_used": [{"name": "ACME Data Engineering", "source_ref": "experiences[0]", "evidence_type": "experience_entry"}],
        "evidence_selection_summary": {"selected_evidence_ids": ["e1"]},
        "gap_summary": {"matched": ["SQL"], "partial": [], "missing": []},
        "structured_cv_initial": {"schema_version": "cv_doc_v1", "sections": {"header": {"name": "Test Candidate"}}},
        "validation_initial": {"valid": True, "missing_sections": []},
        "repair_attempt": {"performed": False, "missing_sections": []},
        "structured_cv_final": {"schema_version": "cv_doc_v1", "sections": {"header": {"name": "Test Candidate"}}},
        "markdown_final": "# Test Candidate\n\n## Summary\nGrounded summary.",
        "runtime_provenance": {"provider": "gemini", "model": "gemini-test"},
        "cv_generation_trace": {"attempts": [{"attempt_index": 1}, {"attempt_index": 2}]},
        "error": None,
    }

    with ExitStack() as stack:
        stack.enter_context(patch("fitcv.pipeline.observe_span", side_effect=_capture_observe_span))
        stack.enter_context(patch("fitcv.pipeline.load_config", return_value=config))
        stack.enter_context(patch("fitcv.pipeline.parse_jobs_file", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.normalize_batch_with_exclusions", return_value=([job], [])))
        stack.enter_context(patch("fitcv.pipeline.load_raw_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_pre_enrichment_global_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.lookup_reusable_structured_jobs", return_value={}))
        stack.enter_context(patch("fitcv.pipeline.enrich_batch", return_value=[job]))
        stack.enter_context(patch("fitcv.pipeline.load_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_run_structured_jobs"))
        stack.enter_context(patch("fitcv.pipeline.load_profile_yaml", return_value=profile))
        stack.enter_context(patch("fitcv.pipeline.load_candidate_profile"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.apply_rule_filters",
                return_value={"passed": [job["job_url"]], "rejected": []},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_filter_results"))
        stack.enter_context(patch("fitcv.pipeline.embed_and_store_jobs"))
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_vector_search",
                return_value=_vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.91, "vector_rank": 1}]),
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_ai_scoring",
                return_value=[{"job_url": job["job_url"], "ai_score": 0.92, "fit_label": "strong"}],
            )
        )
        stack.enter_context(patch("fitcv.pipeline.store_final_ranking"))
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.retrieve_evidence_bundle",
                return_value={
                    "selected_evidence": [
                        {
                            "evidence_id": "e1",
                            "evidence_type": "experience_entry",
                            "source_ref": "experiences[0]",
                            "name": "ACME Data Engineering",
                        }
                    ],
                    "selected_evidence_ids": ["e1"],
                    "effective_channel_pool_size": 1,
                    "merged_pool_size": 1,
                    "deduped_pool_size": 1,
                    "channel_counts": {"experience_entry": 1},
                },
            )
        )
        stack.enter_context(
            patch(
                "fitcv.agentic_cv_analysis.compute_gap",
                return_value={"matched": ["SQL", "Python"], "partial": [], "missing": []},
            )
        )
        stack.enter_context(
            patch(
                "fitcv.pipeline.run_agentic_cv_generation",
                return_value=dict(accepted_result),
            )
        )
        stack.enter_context(patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None))
        stack.enter_context(
            patch(
                "fitcv.pipeline.create_cv_version_record",
                return_value={"version_id": "v1", "generated_at": "2026-05-09T00:00:00Z"},
            )
        )
        stack.enter_context(patch("fitcv.pipeline.PipelineStore.store_cv_version"))
        run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
        )

    item_calls = [attributes for name, attributes in observed_calls if name == "pipeline.cv_generation_item"]
    assert len(item_calls) == 1
    item_attributes = item_calls[0]
    metadata = json.loads(item_calls[0]["langfuse.observation.metadata"])
    assert metadata["status"] == "accepted"
    assert metadata["selected"] is True
    assert metadata["attempt_count"] == 2
    assert metadata["output_structured"]["validation_summary"]["valid"] is True
    assert metadata["output_structured"]["persistence_outcome"] == "stored"
    assert "## Generated CV Markdown" in item_attributes["langfuse.observation.output"]
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_supplied_run_id_for_summary_and_cv_records(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_create_version.return_value = {"version_id": "v1"}

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="cp-run-123",
        )

    assert result["run_id"] == "cp-run-123"
    assert mock_create_version.call_args.kwargs["run_id"] == "cp-run-123"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_profile_json_text")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
def test_run_pipeline_uses_runtime_profile_json_without_touching_profile_path(
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_json: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
    }
    profile = _minimal_profile()
    cfg = _minimal_config()
    cfg["runtime_inputs"] = {"candidate_profile_json": "{\"name\": \"Runtime Candidate\"}"}

    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_json.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    run_pipeline("data/sample_jobs.json", config=cfg, run_id="runtime-profile")

    mock_profile_json.assert_called_once_with("{\"name\": \"Runtime Candidate\"}")
    mock_profile_yaml.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_json_text")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_manual_staged_resume_matches_run_all_outcome_semantics_for_candidate_profile_json(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_profile_json: MagicMock,
    mock_load_candidate: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_candidate: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_cv: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job("https://example.com/1"),
        "job_title": "Data Engineer",
        "title": "Data Engineer",
        "fit_label": "strong",
        "ai_score": 0.91,
        "final_score": 0.91,
        "ranking_fit_label": "strong",
    }
    profile = _minimal_profile()
    run_all_config = _minimal_config()
    staged_config = _minimal_config()
    staged_config["runtime_inputs"] = {"candidate_profile_json": json.dumps(profile)}

    mock_config.return_value = run_all_config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_profile_json.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": [], "passed_records": [{"job_url": job["job_url"], "marks": []}]}
    mock_vec.return_value = _vector_search_envelope(
        [{"job_url": job["job_url"], "vector_similarity": 0.95, "vector_rank": 1}],
        candidate_query={"components": {}, "text": "candidate"},
    )
    mock_ai.return_value = [{"job_url": job["job_url"], "ai_score": 0.91, "fit_label": "strong"}]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "name": "Python", "evidence_type": "project", "source_ref": "p1"}]
    mock_gap.return_value = {"matched": ["Python"], "partial": [], "missing": []}
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    run_all_result = run_pipeline("data/sample_jobs.json", config=run_all_config, run_id="run-all-parity")
    pause_result = run_pipeline(
        "data/sample_jobs.json",
        config=staged_config,
        run_id="run-staged-parity",
        stop_after_stage="ranking",
    )
    resumed_result = run_pipeline(
        "data/sample_jobs.json",
        config=staged_config,
        run_id="run-staged-parity",
        start_stage="cv_analysis",
        checkpoint_payload=pause_result["checkpoint_payload"],
    )

    assert pause_result["next_stage"] == "cv_analysis"
    assert run_all_result["export_results"] == resumed_result["export_results"]
    assert run_all_result["cv_generation_debug_records"] == resumed_result["cv_generation_debug_records"]
    assert json.loads(staged_config["runtime_inputs"]["candidate_profile_json"]) == profile
    assert mock_profile_json.called


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_persists_structured_cv_and_includes_it_in_export(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_create_version.return_value = {
        "version_id": "v-structured",
        "generated_at": "2026-03-29T12:00:00+00:00",
    }

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(structured_cv=structured_cv),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="structured-run")

    create_kwargs = mock_create_version.call_args.kwargs
    assert create_kwargs["cv_structured"] == structured_cv
    assert create_kwargs["cv_generation_model"] == "cx/gpt-5.2"
    assert create_kwargs["cv_prompt_version"] == "v1"
    export_cv = result["export_results"][0]["cv"]
    assert export_cv["schema_version"] == "cv_doc_v1"
    assert export_cv["model_used"] == "cx/gpt-5.2"
    assert result["cv_generation_debug_records"][0]["structured_cv_final"] == structured_cv


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_accepted_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    evidence = [
        {
            "evidence_id": "e1",
            "evidence_type": "experience_entry",
            "source_ref": "experience[0]",
            "name": "Data Engineer at Fintech Startup GmbH",
            "skills": ["SQL", "Python"],
        }
    ]
    gap = {"matched": ["SQL"], "partial": [], "missing": []}

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_create_version.return_value = {
        "version_id": "v-debug",
        "generated_at": "2026-03-31T12:00:00+00:00",
    }

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(job, evidence_payload=evidence, gap_summary=gap),
        ),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(structured_cv=structured_cv, markdown="# CV Markdown"),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="debug-accepted")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["job_url"] == job["job_url"]
    assert record["status"] == "accepted"
    assert record["fit_classification"] == "strong"
    assert record["evidence_used"] == [
        {
            "evidence_type": "experience_entry",
            "source_ref": "experience[0]",
            "name": "Data Engineer at Fintech Startup GmbH",
            "matched_channels": [],
            "selection_reasons": [],
        }
    ]
    assert record["gap_summary"] == gap
    assert record["structured_cv_initial"] == structured_cv
    assert record["validation_initial"]["valid"] is True
    assert record["repair_attempt"] == {"performed": False, "missing_sections": []}
    assert record["structured_cv_final"] == structured_cv
    assert record["markdown_final"] == "# CV Markdown"
    assert record["error"] is None
    assert record["runtime_provenance"] == {
        "route_part": "cv_generation",
        "runtime_path": "fitcv_cv_generation_openai_compatible",
        "adapter": "direct",
        "provider": "openai_compatible",
        "model": "cx/gpt-5.2",
        "wire_api": "chat_completions",
    }
    assert result["export_results"][0]["cv"]["runtime_path"] == "fitcv_cv_generation_openai_compatible"

@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    job_a = _minimal_job(url="https://example.com/job-a")
    job_b = _minimal_job(url="https://example.com/job-b")
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    cv_generation_runtime = config.setdefault("stage_runtime", {}).setdefault("cv_generation", {})
    cv_generation_runtime["concurrency"] = 4
    cv_generation_runtime["sleep_secs"] = 0.25

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(
            self,
            stage: str,
            level: str,
            message: str,
            payload: dict[str, Any] | None = None,
        ) -> None:
            self.events.append((stage, level, message, payload))

    reporter = _Reporter()
    from concurrent.futures import wait as real_wait

    wait_call_count = 0

    def _wait_with_initial_timeout(futures: Any, *, timeout: float, return_when: Any) -> Any:
        nonlocal wait_call_count
        wait_call_count += 1
        if wait_call_count == 1:
            return set(), set(futures)
        return real_wait(futures, timeout=timeout, return_when=return_when)

    mock_config.return_value = config
    mock_parse.return_value = [job_a, job_b]
    mock_norm.return_value = [job_a, job_b]
    mock_norm_with_exclusions.return_value = ([job_a, job_b], [])
    mock_enrich.return_value = [job_a, job_b]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job_a["job_url"], job_b["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([
        {"job_url": job_a["job_url"], "similarity_score": 0.91, "rank": 1},
        {"job_url": job_b["job_url"], "similarity_score": 0.90, "rank": 2},
    ])
    mock_ai.return_value = [job_a, job_b]
    mock_build_feat.return_value = [job_a, job_b]
    mock_rank.return_value = [job_a, job_b]

    def _create_version(*, job_url: str, **_: Any) -> dict[str, Any]:
        suffix = "a" if job_url.endswith("job-a") else "b"
        return {"version_id": f"v-{suffix}", "generated_at": "2026-03-31T12:00:00+00:00"}

    mock_create_version.side_effect = _create_version

    def _agentic_generation_side_effect(*, analysis_record: dict[str, Any], **_: Any) -> dict[str, Any]:
        job = dict(analysis_record.get("job_snapshot") or {})
        job_url = str(job.get("job_url") or "")
        if job_url.endswith("job-a"):
            import time as _time
            _time.sleep(0.08)
        return _agentic_generation_result(
            markdown="# CV",
            job_url=job_url,
            job_title=str(job.get("title") or job.get("job_title") or ""),
        )

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            side_effect=[
                _agentic_analysis_ready(job_a),
                _agentic_analysis_ready(job_b),
            ],
        ),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            side_effect=_agentic_generation_side_effect,
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
        patch("fitcv.pipeline.wait", side_effect=_wait_with_initial_timeout, create=True),
        patch("fitcv.pipeline.time.sleep") as mock_generation_sleep,
    ):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="parallel-order",
            reporter=reporter,
        )

    heartbeat = next(event for event in reporter.events if event[0] == "cv_generation_heartbeat")
    assert heartbeat[3] is not None
    assert heartbeat[3]["completed_items"] == 0
    assert heartbeat[3]["pending_items"] == 2
    assert heartbeat[3]["configured_concurrency"] == 4
    assert heartbeat[3]["cv_generation_concurrency_effective"] == 2
    mock_generation_sleep.assert_any_call(0.25)
    debug_urls = [str(r.get("job_url") or "") for r in result["cv_generation_debug_records"]]
    assert debug_urls == [job_a["job_url"], job_b["job_url"]]
    assert result["export_results"][0]["cv"]["provider"] == "openai_compatible"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_validation_failed_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }
    validation = {
        "valid": False,
        "missing_sections": ["experience"],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="validation_failed",
                structured_cv=structured_cv,
                markdown="# Broken CV",
                validation_initial=validation,
                error={"stage": "validation", "message": "Missing sections: experience"},
            ),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="debug-validation")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["status"] == "validation_failed"
    assert record["structured_cv_initial"] == structured_cv
    assert record["validation_initial"] == {
        **validation,
        "deterministic_grounding_violations": [],
        "semantic_grounding_violations": [],
        "support_source_summary": {},
    }
    assert record["structured_cv_final"] is None
    assert record["markdown_final"] is None
    assert record["error"]["stage"] == "validation"
    changed_sample = result["stage_transition_artifacts"]["stages"]["cv_generation"]["dropped_or_changed_sample"][0]
    assert changed_sample["deterministic_outcome"] == "rejected"
    assert changed_sample["stage_owned_subreason"] == "validation_failed"
    assert changed_sample["source_stage"] == "cv_generation"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch_with_exclusions")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_debug_record_for_persistence_failed_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_norm_with_exclusions: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    structured_cv = {
        "schema_version": "cv_doc_v1",
        "sections": {
            "header": {"name": "Jane Doe", "title": "Data Engineer", "location": None, "contact": {"email": None, "phone": None, "linkedin": None}},
            "summary": {"text": "Grounded summary."},
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {"groups": []},
            "certifications": [],
            "publications": [],
            "languages": [],
        },
    }

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_norm_with_exclusions.return_value = ([job], [])
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="persistence_failed",
                structured_cv=structured_cv,
                markdown="# CV Markdown",
                validation_initial={
                    "valid": True,
                    "missing_sections": [],
                    "grounding_violations": [],
                    "skill_violations": [],
                    "warnings": [],
                },
                error={"stage": "persistence", "message": "BigQuery insert errors for cv_versions: boom"},
            ),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="debug-persist")

    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 1
    record = debug_records[0]
    assert record["status"] == "persistence_failed"
    assert record["structured_cv_initial"] == structured_cv
    assert record["structured_cv_final"] == structured_cv
    assert record["markdown_final"] == "# CV Markdown"
    assert record["error"]["stage"] == "persistence"
    output_sample = result["stage_transition_artifacts"]["stages"]["cv_generation"]["outputs_sample"][0]
    assert output_sample["deterministic_outcome"] == "rejected"
    assert output_sample["stage_owned_subreason"] == "persistence_failed"
    assert output_sample["source_stage"] == "cv_generation"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_correct_schema(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    job["fit_label"] = "strong"
    job["final_score"] = 0.91
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_store_ver.return_value = None
    # create_cv_version_record is NOT mocked — it runs for real
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert "run_id" in result
    assert "total_jobs" in result
    assert "passed_filter" in result
    assert "ranked" in result
    assert "cvs_generated" in result
    assert "stage_quality_metrics" not in result
    assert "late_stage_reuse_metrics" not in result
    assert "shortlist_debug" not in result
    assert "stage_transition_artifacts" in result
    assert result["total_jobs"] == 1
    assert result["cvs_generated"] == 1
    stage_artifacts = result["stage_transition_artifacts"]
    assert stage_artifacts["schema_version"] == "stage_transition_artifacts_v7"
    assert set(stage_artifacts["stages"]) == {
        "normalize",
        "enrich",
        "rule_filter",
        "shortlist",
        "ranking",
        "cv_analysis",
        "cv_generation",
    }
    for stage_id, block in stage_artifacts["stages"].items():
        assert block["stage_id"] == stage_id
        assert block["stage_result"]["stage_id"] == stage_id
        assert "policy_version" in block["stage_result"]
        assert "trace_context" in block["stage_result"]
        assert "decision" in block["stage_result"]
        assert "input_counts" in block
        assert "output_counts" in block
        assert "decision_summary" in block
        assert "inputs_sample" in block
        assert "outputs_sample" in block
        assert "dropped_or_changed_sample" in block
    assert stage_artifacts["stages"]["normalize"]["input_counts"]["raw_jobs"] == 1
    assert stage_artifacts["stages"]["ranking"]["output_counts"]["ranked_jobs"] == 1
    assert stage_artifacts["stages"]["cv_analysis"]["output_counts"]["ready_for_generation"] == 1
    assert stage_artifacts["stages"]["cv_generation"]["output_counts"]["accepted"] == 1
    assert stage_artifacts["stages"]["cv_generation"]["outputs_sample"][0]["job_url"] == job["job_url"]


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_prepares_raw_rows_before_bigquery_insert(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    raw_job = _raw_scraper_job()
    normalized_job = _minimal_job(url=raw_job["jobUrl"])
    profile = _minimal_profile()

    cfg = _minimal_config()
    cfg["stage_runtime"] = {"cv_analysis": {"concurrency": 3}}
    mock_config.return_value = cfg
    mock_parse.return_value = [raw_job]
    mock_norm.return_value = [normalized_job]
    mock_enrich.return_value = [normalized_job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [normalized_job], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": normalized_job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [normalized_job]
    mock_build_feat.return_value = [normalized_job]
    mock_rank.return_value = [normalized_job]
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(normalized_job)),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    inserted_rows = mock_load_bq.call_args.args[0]
    assert inserted_rows[0]["job_url"] == raw_job["jobUrl"]
    assert "posterProfileUrl" not in inserted_rows[0]
    assert "poster_profile_url" not in inserted_rows[0]
    assert "raw_json" in inserted_rows[0]


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_passes_job_dicts_to_embeddings_and_urls_to_vector_search(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
                return_value=_agentic_analysis_ready(job, fit_classification="stretch"),
        ),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(status="accepted", fit_classification="stretch"),
        ),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    embed_jobs_arg = mock_embed_jobs.call_args.args[0]
    vector_urls_arg = mock_vec.call_args.args[1]
    assert len(embed_jobs_arg) == 1
    assert embed_jobs_arg[0]["job_url"] == job["job_url"]
    assert embed_jobs_arg[0]["raw_job_fingerprint"]
    assert embed_jobs_arg[0]["enrich_contract_fingerprint"]
    assert embed_jobs_arg[0]["enrich_reuse_status"] in {"fresh_enrichment", "reused_cached_enrichment"}
    assert vector_urls_arg == [job["job_url"]]
    cv_block = result["stage_transition_artifacts"]["stages"]["cv_generation"]
    assert cv_block["status"] == "not_reached"
    assert cv_block["stage_result"]["status"] == "not_reached"
    trace_context = cv_block["stage_result"]["trace_context"]
    assert isinstance(trace_context, dict)
    assert str(trace_context.get("trace_id") or "").strip()
    assert str(trace_context.get("span_id") or "").strip()
    assert str(trace_context.get("parent_span_id") or "").strip()
    assert cv_block["input_counts"] == {}
    assert cv_block["output_counts"] == {}
    assert cv_block["inputs_sample"] == []
    assert cv_block["outputs_sample"] == []
    assert cv_block["dropped_or_changed_sample"] == []


def test_build_stage_transition_artifacts_includes_changed_state_samples() -> None:
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Data Analyst"},
        {"job_url": "https://example.com/2", "title": "ML Analyst"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
    ]
    shortlist = [
        {"job_url": "https://example.com/1", "title": "Data Analyst", "vector_similarity": 0.91, "vector_rank": 1, "shortlist_origin": "vector_search"},
    ]
    ranking_inputs = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Analyst",
            "ai_score": 0.9,
            "must_have_match": 1.0,
            "vector_similarity": 0.91,
            "title_relevance": 1.0,
            "seniority_fit": 1.0,
            "preference_fit": 0.5,
            "fit_label": "strong",
            "final_score": 0.905,
        },
    ]
    ranked: list[dict[str, Any]] = []
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=passed_jobs,
        normalized=passed_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=passed_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        shortlist_audit_rows=[
            {
                "job_url": "https://example.com/2",
                "vector_similarity": 0.8,
                "vector_rank": 2,
                "shortlist_origin": "audit",
                "retrieval_strategy": "vector_cosine_v1",
                "audit_selection_hash": "audit-hash",
            }
        ],
        shortlist_diagnostics={"raw_hit_anomaly_total": 0, "raw_hit_anomaly_sample": []},
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        candidate_query_components={},
        ai_scores=ranking_inputs,
        ranking_inputs=ranking_inputs,
        ranked=ranked,
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL", "Python"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    shortlist_block = artifacts["stages"]["shortlist"]
    ranking_block = artifacts["stages"]["ranking"]

    assert shortlist_block["dropped_or_changed_sample"][0]["change_type"] == "not_returned_in_raw_hits"
    assert shortlist_block["dropped_or_changed_sample"][0]["shortlist_outcome"] == "not_returned_in_raw_hits"
    assert shortlist_block["dropped_or_changed_sample"][0]["raw_hit_present"] is False
    assert shortlist_block["audit_sample"][0]["job_url"] == "https://example.com/2"
    assert shortlist_block["production_retrieval_rows"] == raw_shortlist
    assert ranking_block["dropped_or_changed_sample"][0]["change_type"] == "scored_not_ranked"
    assert ranking_block["dropped_or_changed_sample"][0]["title_relevance"] == pytest.approx(1.0)


def test_build_stage_transition_artifacts_enrich_sample_includes_canonical_fields() -> None:
    enriched_job = {
        "job_url": "https://example.com/1",
        "title": "Data Scientist",
        "company_name": "Acme",
        "location_type_raw": "mostly remote",
        "location_type": "remote",
        "seniority_raw": "staff",
        "seniority": "senior",
        "required_skills": ["Python programming for data science", "SQL"],
        "required_skills_canonical": ["python", "sql"],
        "required_skill_entities": [
            {"raw_text": "Python programming for data science", "canonical": "python"},
        ],
        "preferred_skills_canonical": ["airflow"],
        "mapping_suggestions": [
            {
                "must_have_skill": "Python",
                "matches": True,
                "confidence": 0.91,
                "alias": "python programming for data science",
                "canonical": "python",
            }
        ],
    }

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[enriched_job],
        normalized=[enriched_job],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[enriched_job],
        passed_jobs=[enriched_job],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate: Data Scientist",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Scientist"}, "skills": ["Python"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    enrich_sample = artifacts["stages"]["enrich"]["outputs_sample"][0]
    assert enrich_sample["location_type"] == "remote"
    assert enrich_sample["seniority"] == "senior"
    assert enrich_sample["required_skills_canonical"] == ["python", "sql"]
    assert enrich_sample["required_skill_entities"][0]["canonical"] == "python"
    assert enrich_sample["mapping_suggestions"][0]["alias"] == "python programming for data science"


def test_build_stage_transition_artifacts_enrich_sample_keeps_full_list_fields() -> None:
    enriched_job = {
        "job_url": "https://example.com/2",
        "title": "Analytics Engineer",
        "required_skills": ["SQL", "Python", "dbt", "Airflow", "BigQuery", "Looker"],
        "required_skills_canonical": ["sql", "python", "dbt", "apache airflow", "google bigquery", "looker"],
    }

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[enriched_job],
        normalized=[enriched_job],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[enriched_job],
        passed_jobs=[enriched_job],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate: Analytics Engineer",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Analytics Engineer"}, "skills": ["SQL"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    enrich_sample = artifacts["stages"]["enrich"]["outputs_sample"][0]
    assert enrich_sample["required_skills"] == ["SQL", "Python", "dbt", "Airflow", "BigQuery", "Looker"]
    assert enrich_sample["required_skills_canonical"] == [
        "sql",
        "python",
        "dbt",
        "apache airflow",
        "google bigquery",
        "looker",
    ]


def test_build_stage_transition_artifacts_enrich_summary_reports_reuse_counts() -> None:
    enriched_jobs = [
        {
            "job_url": "https://example.com/1",
            "title": "Reused role",
            "enrich_reuse_status": "reused_cached_enrichment",
            "raw_job_fingerprint": "raw-1",
            "enrich_contract_fingerprint": "contract-1",
        },
        {
            "job_url": "https://example.com/2",
            "title": "Fresh role",
            "enrich_reuse_status": "fresh_enrichment",
            "raw_job_fingerprint": "raw-2",
            "enrich_contract_fingerprint": "contract-1",
        },
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=enriched_jobs,
        normalized=enriched_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=enriched_jobs,
        passed_jobs=enriched_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate: Data Scientist",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Scientist"}, "skills": ["Python"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    summary = artifacts["stages"]["enrich"]["decision_summary"]
    assert summary["reused_rows"] == 1
    assert summary["fresh_rows"] == 1
    assert summary["total_enriched_rows"] == 2


@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.lookup_reusable_structured_jobs")
@patch("fitcv.pipeline.build_enrich_contract_fingerprint")
@patch("fitcv.pipeline.build_raw_job_fingerprint")
def test_enrich_jobs_with_reuse_preserves_order_and_separates_shared_upserts(
    mock_raw_job_fingerprint: MagicMock,
    mock_contract_fingerprint: MagicMock,
    mock_lookup_reusable: MagicMock,
    mock_enrich_batch: MagicMock,
) -> None:
    jobs = [
        {
            "job_url": "https://example.com/1",
            "title": "Reused role",
            "description": "Reuse me",
        },
        {
            "job_url": "https://example.com/2",
            "title": "Fresh role",
            "description": "Enrich me",
        },
    ]
    mock_raw_job_fingerprint.side_effect = [
        {"payload": {"job_url": jobs[0]["job_url"]}, "fingerprint": "raw-1"},
        {"payload": {"job_url": jobs[1]["job_url"]}, "fingerprint": "raw-2"},
    ]
    mock_contract_fingerprint.return_value = {
        "payload": {"prompt_id": "enrich.extraction.v1"},
        "fingerprint": "contract-1",
    }
    mock_lookup_reusable.return_value = {
        jobs[0]["job_url"]: {
            "job_url": jobs[0]["job_url"],
            "title": jobs[0]["title"],
            "enrichment_version": "v1",
            "enrichment_model": "cx/gpt-5.4-mini",
            "enriched_at": "2026-04-03T00:00:00+00:00",
        }
    }
    mock_enrich_batch.return_value = [
        {
            "job_url": jobs[1]["job_url"],
            "title": jobs[1]["title"],
            "enrichment_version": "v1",
            "enrichment_model": "cx/gpt-5.4-mini",
            "enriched_at": "2026-04-03T00:01:00+00:00",
        }
    ]

    enriched_rows, fresh_rows = _enrich_jobs_with_reuse(
        jobs,
        {"ai_score_model": "cx/gpt-5.4-mini"},
    )

    assert [row["job_url"] for row in enriched_rows] == [
        "https://example.com/1",
        "https://example.com/2",
    ]
    assert enriched_rows[0]["enrich_reuse_status"] == "reused_cached_enrichment"
    assert enriched_rows[1]["enrich_reuse_status"] == "fresh_enrichment"
    assert enriched_rows[0]["raw_job_fingerprint"] == "raw-1"
    assert enriched_rows[1]["raw_job_fingerprint"] == "raw-2"
    assert all(row["enrich_contract_fingerprint"] == "contract-1" for row in enriched_rows)
    assert [row["job_url"] for row in fresh_rows] == ["https://example.com/2"]
    mock_enrich_batch.assert_called_once_with(
        [jobs[1]],
        {"ai_score_model": "cx/gpt-5.4-mini"},
        job_event_callback=None,
        runtime_observation_callback=None,
        on_chunk_complete=None,
    )


def test_collect_mapping_suggestions_deduplicates_per_run_by_alias_canonical_and_must_have_skill() -> None:
    enriched = [
        {
            "job_url": "https://example.com/1",
            "title": "Role A",
            "mapping_suggestions": [
                {
                    "must_have_skill": "Python",
                    "matches": True,
                    "confidence": 0.91,
                    "alias": "Python programming for data science",
                    "canonical": "python",
                }
            ],
        },
        {
            "job_url": "https://example.com/2",
            "title": "Role B",
            "mapping_suggestions": [
                {
                    "must_have_skill": " python ",
                    "matches": True,
                    "confidence": 0.88,
                    "alias": "python programming for data science ",
                    "canonical": "PYTHON",
                },
                {
                    "must_have_skill": "SQL",
                    "matches": True,
                    "confidence": 0.87,
                    "alias": "python programming for data science",
                    "canonical": "python",
                },
            ],
        },
    ]

    suggestions = _collect_mapping_suggestions(enriched, run_id="run-123")

    assert suggestions == [
        {
            "run_id": "run-123",
            "job_url": "https://example.com/1",
            "job_title": "Role A",
            "must_have_skill": "Python",
            "matches": True,
            "confidence": 0.91,
            "alias": "Python programming for data science",
            "canonical": "python",
            "field": "skill",
        },
        {
            "run_id": "run-123",
            "job_url": "https://example.com/2",
            "job_title": "Role B",
            "must_have_skill": "SQL",
            "matches": True,
            "confidence": 0.87,
            "alias": "python programming for data science",
            "canonical": "python",
            "field": "skill",
        },
    ]

def test_collect_mapping_suggestions_includes_domain_and_role_family_fields() -> None:
    enriched = [
        {
            "job_url": "https://example.com/1",
            "title": "Role A",
            "domain_mapping_suggestions": [
                {"alias": "fintech", "canonical": "financial services", "confidence": 0.9}
            ],
            "role_family_mapping_suggestions": [
                {"alias": "bi analyst", "canonical": "analytics", "confidence": 0.8}
            ],
        }
    ]

    suggestions = _collect_mapping_suggestions(enriched, run_id="run-xyz")
    fields = {(row["field"], row["alias"], row["canonical"]) for row in suggestions}
    assert ("domain", "fintech", "financial services") in fields
    assert ("role_family", "bi analyst", "analytics") in fields


def test_build_stage_transition_artifacts_enrich_decision_summary_includes_prompt_provenance() -> None:
    enriched_job = {
        "job_url": "https://example.com/job/1",
        "title": "Data Analyst",
        "required_skills": ["SQL"],
        "required_skills_canonical": ["sql"],
        "required_skill_entities": [{"raw_text": "SQL", "canonical": "sql", "confidence": 1.0}],
        "enrichment_model": "cx/gpt-5.4-mini",
    }

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[enriched_job],
        normalized=[enriched_job],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[enriched_job],
        passed_jobs=[enriched_job],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="candidate summary",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={},
        config={
            "ai_score_model": "cx/gpt-5.4-mini",
            "prompts": {"enrich": {"extraction": {"prompt_id": "enrich.extraction.v1"}}},
            "cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}},
        },
    )

    enrich_summary = artifacts["stages"]["enrich"]["decision_summary"]
    assert enrich_summary["enrich_prompt_id"] == "enrich.extraction.v1"
    assert enrich_summary["enrich_prompt_version"] == "v1"
    assert enrich_summary["enrich_prompt_model"] == "cx/gpt-5.4-mini"


def test_build_stage_transition_artifacts_rule_filter_includes_marks_and_selected_filters() -> None:
    enriched_jobs = [
        {"job_url": "https://example.com/1", "title": "Job 1"},
        {"job_url": "https://example.com/2", "title": "Job 2"},
    ]
    passed_jobs = [
        {
            "job_url": "https://example.com/1",
            "title": "Job 1",
            "marks": [
                {
                    "code": "must_have_skill_missing",
                    "message": "Missing must-have skills",
                    "details": {"missing_count": 1, "missing_skills": ["dbt"]},
                }
            ],
        }
    ]
    rejected_jobs = [
        {
            "job_url": "https://example.com/2",
            "title": "Job 2",
            "reasons": ["seniority_mismatch"],
            "marks": [
                {
                    "code": "domain_not_preferred",
                    "message": "Job domain is outside preferred domains",
                }
            ],
        }
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=enriched_jobs,
        normalized=enriched_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=enriched_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=rejected_jobs,
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="candidate summary",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={},
        config={
            "rule_filter": {
                "selected_filters": [
                    "seniority_mismatch",
                    "location_type_excluded",
                ]
            },
            "cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}},
        },
    )

    rule_filter_summary = artifacts["stages"]["rule_filter"]["decision_summary"]
    assert rule_filter_summary["selected_filters"] == [
        "seniority_mismatch",
        "location_type_excluded",
    ]
    assert rule_filter_summary["mark_code_counts"] == {
        "must_have_skill_missing": 1,
        "domain_not_preferred": 1,
    }
    assert artifacts["stages"]["rule_filter"]["outputs_sample"][0]["filter_outcome"] == "pass"
    assert artifacts["stages"]["rule_filter"]["outputs_sample"][0]["marks"] == [
        {
            "code": "must_have_skill_missing",
            "message": "Missing must-have skills",
            "details": {"missing_count": 1, "missing_skills": ["dbt"]},
        }
    ]
    assert "reasons" not in artifacts["stages"]["rule_filter"]["outputs_sample"][0]
    assert artifacts["stages"]["rule_filter"]["dropped_or_changed_sample"][0]["filter_outcome"] == "reject"
    assert artifacts["stages"]["rule_filter"]["dropped_or_changed_sample"][0]["reasons"] == [
        "seniority_mismatch"
    ]
    assert artifacts["stages"]["rule_filter"]["dropped_or_changed_sample"][0]["marks"] == [
        {
            "code": "domain_not_preferred",
            "message": "Job domain is outside preferred domains",
        }
    ]


def test_build_stage_transition_artifacts_rule_filter_default_selected_filters_match_runtime_contract() -> None:
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[],
        normalized=[],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[],
        passed_jobs=[],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="candidate summary",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=5,
        cv_generation_debug_records=[],
        profile={},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    selected_filters = artifacts["stages"]["rule_filter"]["decision_summary"]["selected_filters"]
    assert selected_filters == DEFAULT_SELECTED_RULE_FILTERS


def test_build_stage_transition_artifacts_reports_unique_job_and_raw_row_shortlist_counts() -> None:
    passed_jobs = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Analyst",
            "embedding_reuse_status": "reused_cached_embedding",
            "embedding_input_signature": "sig-1",
            "embedding_contract_fingerprint": "contract-1",
        },
        {
            "job_url": "https://example.com/2",
            "title": "ML Analyst",
            "embedding_reuse_status": "fresh_embedding",
            "embedding_input_signature": "sig-2",
            "embedding_contract_fingerprint": "contract-1",
        },
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 2},
        {"job_url": "https://example.com/2", "vector_similarity": 0.83, "vector_rank": 33},
    ]
    shortlist = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Analyst",
            "vector_similarity": 0.91,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
            "embedding_reuse_status": "reused_cached_embedding",
            "embedding_input_signature": "sig-1",
            "embedding_contract_fingerprint": "contract-1",
        },
        {
            "job_url": "https://example.com/2",
            "title": "ML Analyst",
            "vector_similarity": 0.83,
            "vector_rank": 2,
            "shortlist_origin": "vector_search",
            "embedding_reuse_status": "fresh_embedding",
            "embedding_input_signature": "sig-2",
            "embedding_contract_fingerprint": "contract-1",
        },
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=passed_jobs,
        normalized=passed_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=passed_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        candidate_query_components={
            "headline": "Analyst",
            "target_role": "Data Analyst",
            "recent_roles": ["Data Analyst"],
            "role_family_hints": ["analytics"],
            "flattened_skills": ["SQL", "Python"],
            "domain_hints": ["banking"],
        },
        candidate_query_debug={
            "candidate_query_reuse_status": "reused_cached_query_embedding",
            "candidate_query_signature": "candidate-query-sig-1",
            "candidate_query_contract_fingerprint": "candidate-query-contract-1",
            "components_hash": "components-hash-1",
            "canonical_text_hash": "canonical-text-hash-1",
        },
        ai_scores=[],
        ranking_inputs=[],
        ranked=[],
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL", "Python"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    shortlist_block = artifacts["stages"]["shortlist"]

    assert shortlist_block["output_counts"]["raw_vector_rows"] == 3
    assert shortlist_block["output_counts"]["raw_vector_unique_jobs"] == 2
    assert shortlist_block["output_counts"]["raw_vector_hits"] == 2
    assert shortlist_block["output_counts"]["embedding_reused_jobs"] == 1
    assert shortlist_block["output_counts"]["embedding_fresh_jobs"] == 1
    assert shortlist_block["output_counts"]["embedding_total_jobs"] == 2
    assert shortlist_block["decision_summary"]["candidate_query_reuse_status"] == "reused_cached_query_embedding"
    assert shortlist_block["decision_summary"]["candidate_query_signature"] == "candidate-query-sig-1"
    assert shortlist_block["decision_summary"]["candidate_query_contract_fingerprint"] == "candidate-query-contract-1"
    assert shortlist_block["decision_summary"]["components_hash"] == "components-hash-1"
    assert shortlist_block["decision_summary"]["canonical_text_hash"] == "canonical-text-hash-1"
    assert shortlist_block["outputs_sample"][1]["vector_rank"] == 2
    assert shortlist_block["outputs_sample"][1]["shortlist_outcome"] == "returned_by_vector_search"
    assert shortlist_block["outputs_sample"][1]["raw_hit_present"] is True
    assert shortlist_block["outputs_sample"][1]["embedding_reuse_status"] == "fresh_embedding"
    assert shortlist_block["outputs_sample"][1]["embedding_input_signature"] == "sig-2"
    assert shortlist_block["outputs_sample"][1]["embedding_contract_fingerprint"] == "contract-1"


def test_build_stage_transition_artifacts_reports_six_feature_ranking_contract() -> None:
    ranking_inputs = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "ai_score": 0.85,
            "must_have_match": 1.0,
            "vector_similarity": 0.9,
            "title_relevance": 1.0,
            "seniority_fit": 1.0,
            "preference_fit": 1.0,
            "fit_label": "strong",
            "final_score": 0.925,
            "shortlist_origin": "vector_search",
        }
    ]
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=ranking_inputs,
        normalized=ranking_inputs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=ranking_inputs,
        passed_jobs=ranking_inputs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=ranking_inputs,
        shortlist=ranking_inputs,
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate: Data Engineer",
        candidate_query_components={},
        ai_scores=ranking_inputs,
        ranking_inputs=ranking_inputs,
        ranked=ranking_inputs,
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Engineer"}},
        config={
            "ranking_weights": {
                "ai_score": 0.73,
                "must_have_match": 0.0,
                "vector_similarity": 0.27,
                "title_relevance": 0.0,
                "seniority_fit": 0.0,
                "preference_fit": 0.0,
            },
            "missing_value_defaults": {
                "ai_score": 0.0,
                "must_have_match": 0.5,
                "vector_similarity": 0.0,
                "title_relevance": 0.5,
                "seniority_fit": 0.5,
                "preference_fit": 0.5,
            },
            "cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}},
        },
    )

    ranking_block = artifacts["stages"]["ranking"]
    decision_summary = ranking_block["decision_summary"]

    assert decision_summary["configured_ranking_weights"] == {
        "ai_score": 0.73,
        "must_have_match": 0.0,
        "vector_similarity": 0.27,
        "title_relevance": 0.0,
        "seniority_fit": 0.0,
        "preference_fit": 0.0,
    }
    assert decision_summary["configured_missing_value_defaults"] == {
        "ai_score": 0.0,
        "must_have_match": 0.5,
        "vector_similarity": 0.0,
        "title_relevance": 0.5,
        "seniority_fit": 0.5,
        "preference_fit": 0.5,
    }
    assert decision_summary["zero_weight_features"] == [
        "must_have_match",
        "title_relevance",
        "seniority_fit",
        "preference_fit",
    ]
    assert decision_summary["contributing_features"] == [
        "ai_score",
        "vector_similarity",
    ]
    assert ranking_block["inputs_sample"][0]["must_have_match"] == pytest.approx(1.0)
    assert ranking_block["inputs_sample"][0]["preference_fit"] == pytest.approx(1.0)


def test_build_stage_transition_artifacts_emits_stage_quality_metrics() -> None:
    """@proves cv_system.stage-artifact-diagnostics"""
    passed_jobs = [
        {"job_url": "https://example.com/1", "title": "Job 1"},
        {"job_url": "https://example.com/2", "title": "Job 2"},
        {"job_url": "https://example.com/3", "title": "Job 3"},
    ]
    raw_shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.82, "vector_rank": 2},
    ]
    shortlist = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.91, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.82, "vector_rank": 2},
        {"job_url": "https://example.com/3", "vector_similarity": 0.61, "vector_rank": 3},
    ]
    ranking_inputs = [
        {
            "job_url": "https://example.com/1",
            "title": "Job 1",
            "fit_label": "strong",
            "final_score": 0.92,
        },
        {
            "job_url": "https://example.com/2",
            "title": "Job 2",
            "fit_label": "stretch",
            "final_score": 0.61,
        },
        {
            "job_url": "https://example.com/3",
            "title": "Job 3",
            "fit_label": "skip",
            "final_score": 0.22,
        },
    ]
    cv_analysis_results = [
        {"job_url": "https://example.com/1", "status": "ready_for_generation"},
        {"job_url": "https://example.com/2", "status": "ready_for_generation"},
        {"job_url": "https://example.com/3", "status": "skipped_fit_gate"},
    ]
    cv_generation_debug_records = [
        {"job_url": "https://example.com/1", "status": "accepted"},
        {"job_url": "https://example.com/2", "status": "validation_failed"},
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=passed_jobs,
        normalized=passed_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=passed_jobs,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        shortlist_audit_rows=[],
        shortlist_diagnostics={
            "eligible_jobs_total": 3,
            "scored_jobs_total": 2,
            "production_shortlist_total": 2,
            "production_cutoff_rank": 2,
            "production_cutoff_similarity": 0.7,
            "missing_job_embedding_total": 1,
            "invalid_job_embedding_total": 0,
            "embedding_coverage_rate": 2 / 3,
            "audit_candidate_total": 0,
            "audit_sample_total": 0,
            "audit_sample_fingerprint": "",
        },
        vector_top_n=10,
        candidate_summary="Candidate: Data Analyst",
        candidate_query_components={"skills": ["sql", "python"]},
        ai_scores=ranking_inputs,
        ranking_inputs=ranking_inputs,
        ranked=ranking_inputs[:2],
        cv_analysis_results=cv_analysis_results,
        final_top_n=10,
        cv_generation_debug_records=cv_generation_debug_records,
        profile={"preferences": {"target_role": "Data Analyst"}},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    shortlist_metrics = artifacts["stages"]["shortlist"]["decision_summary"]["quality_metrics"]
    assert shortlist_metrics == {
        "eligible_jobs_total": 3,
        "scored_jobs_total": 2,
        "production_shortlist_total": 2,
        "production_cutoff_rank": 2,
        "production_cutoff_similarity": 0.7,
        "missing_job_embedding_total": 1,
        "invalid_job_embedding_total": 0,
        "embedding_coverage_rate": pytest.approx(2 / 3),
        "audit_candidate_total": 0,
        "audit_sample_total": 0,
        "audit_sample_fingerprint": "",
    }

    ranking_metrics = artifacts["stages"]["ranking"]["decision_summary"]["quality_metrics"]
    assert ranking_metrics == {
        "label_distribution": {
            "strong_count": 1,
            "stretch_count": 1,
            "skip_count": 1,
            "strong_rate": pytest.approx(1 / 3),
            "stretch_rate": pytest.approx(1 / 3),
            "skip_rate": pytest.approx(1 / 3),
            "total_scored": 3,
        }
    }

    cv_analysis_metrics = artifacts["stages"]["cv_analysis"]["decision_summary"]["quality_metrics"]
    assert cv_analysis_metrics == {
        "blocked_by_reranker_fit_rate": pytest.approx(0.0),
        "skip_rate": pytest.approx(1 / 3),
        "ready_for_generation_rate": pytest.approx(2 / 3),
        "analysis_failed_rate": pytest.approx(0.0),
        "blocked_by_reranker_fit": 0,
        "skipped_fit_gate": 1,
        "ready_for_generation": 2,
        "analysis_failed": 0,
        "total_processed": 3,
    }

    cv_generation_metrics = artifacts["stages"]["cv_generation"]["decision_summary"]["quality_metrics"]
    assert cv_generation_metrics == {
        "validation_fail_rate": pytest.approx(0.5),
        "accepted_rate": pytest.approx(0.5),
        "review_required_rate": pytest.approx(0.0),
        "generation_failed_rate": pytest.approx(0.0),
        "persistence_failed_rate": pytest.approx(0.0),
        "accepted": 1,
        "review_required": 0,
        "validation_failed": 1,
        "generation_failed": 0,
        "persistence_failed": 0,
        "total_attempted": 2,
    }


def test_build_stage_transition_artifacts_does_not_sum_cumulative_cv_analysis_embedding_counts() -> None:
    cv_analysis_results = [
        {
            "job_url": "https://example.com/1",
            "job_title": "Role 1",
            "status": "ready_for_generation",
            "evidence_selection_summary": {
                "selected_evidence_count": 2,
                "merged_pool_size": 5,
                "semantic_alignment": {
                    "embedding_counts": {
                        "candidate_evidence": {"fresh": 3, "reused": 2},
                        "job_context": {"fresh": 1, "reused": 6},
                    }
                },
            },
        },
        {
            "job_url": "https://example.com/2",
            "job_title": "Role 2",
            "status": "skipped_fit_gate",
            "evidence_selection_summary": {
                "selected_evidence_count": 3,
                "merged_pool_size": 7,
                "semantic_alignment": {
                    "embedding_counts": {
                        "candidate_evidence": {"fresh": 3, "reused": 5},
                        "job_context": {"fresh": 2, "reused": 10},
                    }
                },
            },
        },
    ]

    artifacts = _build_stage_transition_artifacts(
        raw_jobs=[],
        normalized=[],
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=[],
        passed_jobs=[],
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=10,
        candidate_summary="Candidate: Data Analyst",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=[{"job_url": "https://example.com/1"}, {"job_url": "https://example.com/2"}],
        cv_analysis_results=cv_analysis_results,
        final_top_n=10,
        cv_generation_debug_records=[],
        profile={"preferences": {"target_role": "Data Analyst"}},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    decision_summary = artifacts["stages"]["cv_analysis"]["decision_summary"]

    assert "candidate_evidence_embeddings_fresh" not in decision_summary
    assert "candidate_evidence_embeddings_reused" not in decision_summary
    assert "job_context_embeddings_fresh" not in decision_summary
    assert "job_context_embeddings_reused" not in decision_summary


def test_build_stage_transition_artifacts_caps_samples_at_20_and_truncates_text() -> None:
    raw_jobs = [
        {
            "job_url": f"https://example.com/{i}",
            "title": f"Role {i}",
            "description_cleaned": "x" * 800,
        }
        for i in range(25)
    ]
    debug_records = [
        {
            "job_url": f"https://example.com/{i}",
            "job_title": f"Role {i}",
            "status": "accepted",
            "decision_chain": {"primary_fit": {"label": "strong"}},
            "markdown_final": "y" * 1000,
            "validation_initial": {"valid": True},
            "repair_attempt": {"performed": False, "missing_sections": []},
            "gap_summary": {"matched": ["SQL"]},
            "evidence_used": [
                {
                    "evidence_type": "experience_entry",
                    "source_ref": "experiences[0]",
                    "name": "Data Analyst - Bank Corp",
                    "matched_channels": ["required_skill_support"],
                    "selection_reasons": ["required_skill_support"],
                }
            ],
            "evidence_selection_summary": {
                "selected_evidence_count": 1,
                "selected_evidence_ids": ["exp-1"],
            },
            "analysis_input_summary": {
                "required_skills": ["SQL"],
                "domain": "banking",
            },
            "error": None,
        }
        for i in range(25)
    ]
    artifacts = _build_stage_transition_artifacts(
        raw_jobs=raw_jobs,
        normalized=raw_jobs,
        deduplicated_jobs=[],
        pre_filter_rejected_jobs=[],
        enriched=raw_jobs,
        passed_jobs=raw_jobs,
        candidate_filter_rejected_jobs=[],
        raw_shortlist=[],
        shortlist=[],
        shortlist_audit_rows=[],
        shortlist_diagnostics={},
        vector_top_n=50,
        candidate_summary="Candidate: Analyst",
        candidate_query_components={},
        ai_scores=[],
        ranking_inputs=[],
        ranked=raw_jobs,
        final_top_n=10,
        cv_generation_debug_records=debug_records,
        profile={"preferences": {"target_role": "Data Analyst"}, "skills": ["SQL"]},
        config={"cv": {"generation": {"model": "cx/gpt-5.4-mini", "prompt_version": "v1"}}},
    )

    normalize_block = artifacts["stages"]["normalize"]
    cv_block = artifacts["stages"]["cv_generation"]
    assert len(normalize_block["inputs_sample"]) == 20
    assert len(cv_block["outputs_sample"]) == 20
    assert "markdown_final" not in cv_block["outputs_sample"][0]
    assert "structured_cv_final" not in cv_block["outputs_sample"][0]
    assert cv_block["outputs_sample"][0]["evidence_selection_summary"] == {
        "selected_evidence_count": 1,
        "selected_evidence_ids": ["exp-1"],
    }
    assert cv_block["outputs_sample"][0]["analysis_input_summary"] == {
        "required_skills": ["SQL"],
        "domain": "banking",
    }


def test_build_cv_generation_debug_record_preserves_cv_analysis_context() -> None:
    from fitcv.pipeline import _debug_record_output_sample

    record = _build_cv_generation_debug_record(
        job={
            "job_url": "https://example.com/1",
            "title": "Data Analyst - Retail Banking",
            "required_skills": ["SQL", "Python"],
            "domain": "banking",
            "job_family": "analytics",
            "fit_label": "strong",
        },
        status="accepted",
        fit_classification="strong",
        evidence_used=[
            {
                "evidence_type": "experience_entry",
                "source_ref": "experiences[0]",
                "name": "Data Analyst - Bank Corp",
                "matched_channels": ["required_skill_support", "responsibility_alignment"],
                "selection_reasons": ["required_skill_support", "responsibility_alignment"],
            }
        ],
        evidence_selection_summary={
            "selected_evidence_count": 1,
            "selected_evidence_ids": ["exp-1"],
            "channel_counts": {"required_skill_support": 1},
        },
        analysis_input_summary={
            "required_skills": ["SQL", "Python"],
            "domain": "banking",
            "job_family": "analytics",
        },
        gap_summary={"matched": ["SQL"], "partial": [], "missing": ["dbt"]},
        structured_cv_initial={"schema_version": "cv_doc_v1"},
        validation_initial={"valid": True},
        repair_attempt={"performed": False, "missing_sections": []},
        structured_cv_final={"schema_version": "cv_doc_v1"},
        markdown_final="# CV",
        enabled_sections=["summary", "experience", "skills"],
        cv_generation_model="cx/gpt-5.4-mini",
        cv_prompt_id="cv_generation.structured_write.v1",
        cv_prompt_template_path="cv_generation_structured_write_v1.md",
        error=None,
    )

    assert record["evidence_selection_summary"] == {
        "selected_evidence_count": 1,
        "selected_evidence_ids": ["exp-1"],
        "channel_counts": {"required_skill_support": 1},
    }
    assert record["analysis_input_summary"] == {
        "required_skills": ["SQL", "Python"],
        "domain": "banking",
        "job_family": "analytics",
    }

    sample = _debug_record_output_sample(record)

    assert sample is not None
    assert sample["evidence_used"][0]["matched_channels"] == [
        "required_skill_support",
        "responsibility_alignment",
    ]
    assert sample["evidence_selection_summary"]["selected_evidence_ids"] == ["exp-1"]
    assert sample["analysis_input_summary"]["job_family"] == "analytics"
    assert sample["enabled_sections"] == ["summary", "experience", "skills"]
    assert sample["cv_generation_model"] == "cx/gpt-5.4-mini"
    assert sample["cv_prompt_id"] == "cv_generation.structured_write.v1"
    assert sample["cv_prompt_template_path"] == "cv_generation_structured_write_v1.md"
    assert sample["structured_cv_final"] == {"schema_version": "cv_doc_v1"}


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_passes_enriched_shortlist_rows_to_ai_scoring(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "title": "Structured Data Engineer",
        "required_skills": ["SQL", "Python"],
        "responsibilities": ["Build data pipelines"],
        "job_family": "data_engineering",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    shortlist_arg = mock_ai.call_args.args[0]
    assert len(shortlist_arg) == 1
    assert shortlist_arg[0]["job_url"] == job["job_url"]
    assert shortlist_arg[0]["vector_similarity"] == pytest.approx(0.9)
    assert shortlist_arg[0]["vector_rank"] == 1
    assert shortlist_arg[0]["shortlist_origin"] == "vector_search"
    assert shortlist_arg[0]["raw_job_fingerprint"]
    assert shortlist_arg[0]["enrich_contract_fingerprint"]
    assert shortlist_arg[0]["enrich_reuse_status"] == "fresh_enrichment"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_does_not_score_missing_vector_rows(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    first_job = {
        **_minimal_job("https://example.com/1"),
        "title": "Structured Data Engineer",
    }
    second_job = {
        **_minimal_job("https://example.com/2"),
        "title": "Retail Banking Analyst",
        "required_skills": ["SQL", "Power BI"],
        "job_family": "analytics",
    }
    profile = _minimal_profile()
    cfg = _minimal_config()
    cfg["pipeline"]["vector_search_top_n"] = 5

    mock_config.return_value = cfg
    mock_parse.return_value = [_raw_scraper_job(first_job["job_url"]), _raw_scraper_job(second_job["job_url"])]
    mock_norm.return_value = [first_job, second_job]
    mock_enrich.return_value = [first_job, second_job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [first_job["job_url"], second_job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope(
        [{"job_url": first_job["job_url"], "similarity_score": 0.9, "rank": 1}],
        candidate_query={
            "text": "Candidate: Data Engineer\nTarget role: Data Engineer\nRecent roles: DE\nRole families: data_engineering\nSkills: SQL, Python",
            "components": {
                "headline": "Data Engineer",
                "target_role": "Data Engineer",
                "recent_roles": ["DE"],
                "role_family_hints": ["data_engineering"],
                "flattened_skills": ["SQL", "Python"],
            },
            "candidate_query_reuse_status": "reused_cached_query_embedding",
            "candidate_query_signature": "candidate-query-sig-1",
            "candidate_query_contract_fingerprint": "candidate-query-contract-1",
        },
    )
    mock_ai.return_value = [first_job, second_job]
    mock_build_feat.return_value = [first_job, second_job]
    mock_rank.return_value = []

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(first_job, fit_classification="stretch"),
        ),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(status="accepted", fit_classification="stretch"),
        ),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    shortlist_arg = mock_ai.call_args.args[0]
    assert shortlist_arg == [
        {
            **first_job,
            "marks": [],
            "vector_similarity": 0.9,
            "vector_rank": 1,
            "shortlist_origin": "vector_search",
        }
    ]
    second_export_row = next(
        row for row in result["export_results"]
        if row["job_url"] == second_job["job_url"]
    )
    assert second_export_row["pipeline_status"] != "scored_not_ranked"
    assert "shortlist_debug" not in result
    mock_embed_cand.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_ranked_fit_label_as_floor_for_layer4_fit_gate(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "stretch",
        "ai_score": 0.5,
        "final_score": 0.4,
        "title": "Retail Banking Analyst",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": ["Power BI"]}
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {
        "version_id": "v1",
        "generated_at": "2026-03-29T16:11:40Z",
    }

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(job, fit_classification="stretch"),
        ),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(status="accepted", fit_classification="stretch"),
        ),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert result["cvs_generated"] == 1
    assert result["cv_generation_debug_records"][0]["status"] == "accepted"
    assert result["cv_generation_debug_records"][0]["fit_classification"] == "stretch"
    assert result["export_results"][0]["pipeline_status"] == "ranked_with_cv"
def test_pipeline_source_has_no_direct_ranking_fit_label_assignment_in_fresh_compute_branch() -> None:
    source = Path("src/fitcv/pipeline.py").read_text(encoding="utf-8")
    assert '"ranking_fit_label": fit' not in source


def test_pipeline_source_has_no_direct_ranking_fit_label_assignment_in_reuse_branch() -> None:
    source = Path("src/fitcv/pipeline.py").read_text(encoding="utf-8")
    assert '"ranking_fit_label": fit' not in source

@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_reranker_fit_as_sole_post_filter_cv_gate(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """@proves cv_system.fit-gate-resolution"""
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
        "title": "Retail Banking Analyst",
    }
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [_raw_scraper_job()]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    mock_gen_cv.assert_not_called()
    mock_validate.assert_not_called()
    assert result["cv_generation_debug_records"][0]["status"] == "blocked_by_reranker_fit"
    assert result["cv_generation_debug_records"][0]["fit_classification"] == "skip"
    assert result["export_results"][0]["pipeline_status"] == "ranked_blocked_by_reranker_fit"
    assert result["export_results"][0]["decision_chain"]["cv_analysis"] == {
        "status": "blocked_by_reranker_fit",
        "completed": False,
    }
    cv_analysis_block = result["stage_transition_artifacts"]["stages"]["cv_analysis"]
    assert cv_analysis_block["output_counts"]["blocked_by_reranker_fit"] == 1
    assert cv_analysis_block["output_counts"]["ready_for_generation"] == 0


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_skips_reranker_skip_fit_jobs(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job(),
        "fit_label": "skip",
        "ai_score": 0.2,
        "final_score": 0.2,
    }
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.4, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = []
    mock_gap.return_value = {"matched": [], "partial": [], "missing": ["SQL"]}
    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")
    assert result["cvs_generated"] == 0


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_skips_invalid_cv(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="validation_failed",
                markdown="# Broken CV",
                validation_initial={
                    "valid": False,
                    "missing_sections": ["Experience"],
                    "grounding_violations": [],
                    "skill_violations": [],
                    "warnings": [],
                },
                error={"stage": "validation", "message": "Missing sections: Experience"},
            ),
        ),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")
    assert result["cvs_generated"] == 0


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_per_job_failure_skips_not_crashes(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """A per-job exception must not crash the pipeline — only that job is skipped."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.side_effect = RuntimeError("BQ connection failed")
    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")
    # Pipeline should still return without raising
    assert result["cvs_generated"] == 0
    assert result["total_jobs"] == 1


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_layer4_cv_error_for_analysis_failed_record(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
            self.events.append((stage, level, message, payload))

    job = {
        **_minimal_job(),
        "fit_label": "strong",
        "ai_score": 0.91,
        "final_score": 0.95,
    }
    profile = _minimal_profile()
    reporter = _Reporter()

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    analysis_record = build_agentic_cv_analysis_record(
        job=job,
        status="analysis_failed",
        analysis_input_fingerprint=None,
        analysis_reuse_status="fresh_compute",
        evidence_payload=[],
        evidence_selection_summary=None,
        gap_summary=None,
        requirement_coverage=None,
        section_confidence_hints=None,
        do_not_claim=[],
        fit_classification="strong",
        error={"stage": "analysis", "message": "BQ connection failed"},
    )
    with patch("fitcv.pipeline.analyze_ranked_job", return_value=analysis_record):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    assert (
        "layer4_cv_error",
        "error",
        f"CV analysis failed for {job['job_url']}: BQ connection failed",
        {
            "event_name": "cv_analysis_decision",
            "event_family": "decision",
            "source_stage": "cv_analysis",
            "job_url": job["job_url"],
            "event_status": "completed",
            "deterministic_outcome": "rejected",
            "stage_owned_subreason": "analysis_failed",
            "fallback_used": False,
            "input_snapshot": {
                "ranking_fit_label": "strong",
            },
            "output_snapshot": {
                "error_stage": "analysis",
            },
            "artifact_refs": {
                "stage_id": "cv_analysis",
            },
        },
    ) in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_shortlist_and_ai_score_counts(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
            self.events.append((stage, level, message, payload))

    jobs = [_minimal_job("https://example.com/1"), _minimal_job("https://example.com/2")]
    profile = _minimal_profile()
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = jobs
    mock_norm.return_value = jobs
    mock_enrich.return_value = jobs
    mock_profile_yaml.return_value = profile
    mock_pre_filter.return_value = {"passed": [job["job_url"] for job in jobs], "rejected": []}
    mock_filter.return_value = {"passed": [job["job_url"] for job in jobs], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([
        {"job_url": jobs[0]["job_url"], "similarity_score": 0.95, "rank": 1},
        {"job_url": jobs[1]["job_url"], "similarity_score": 0.80, "rank": 2},
    ])
    mock_ai.return_value = [jobs[0]]
    mock_build_feat.return_value = [jobs[0]]
    mock_rank.return_value = [jobs[0]]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1"}

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(jobs[0])),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    assert ("layer3_shortlist", "info", "Vector shortlist: 2 raw hits", None) in reporter.events
    assert any(event[0] == "layer3_ai_score" for event in reporter.events)


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_normalization_dedupe_event(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
            self.events.append((stage, level, message, payload))

    duplicate_jobs = [
        _raw_scraper_job("https://example.com/1"),
        _raw_scraper_job("https://example.com/2"),
    ]
    duplicate_jobs[1]["companyId"] = duplicate_jobs[0]["companyId"]
    duplicate_jobs[1]["title"] = duplicate_jobs[0]["title"]
    duplicate_jobs[1]["description"] = duplicate_jobs[0]["description"]
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = duplicate_jobs
    mock_enrich.return_value = [_minimal_job("https://example.com/1")]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [_minimal_job("https://example.com/1")]
    mock_build_feat.return_value = [_minimal_job("https://example.com/1")]
    mock_rank.return_value = []

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(_minimal_job("https://example.com/1")),
        ),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    assert (
        "layer1_normalize",
        "info",
        "Normalization dedupe: kept 1 of 2 jobs, removed 1 duplicate(s)",
        None,
    ) in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_normalize_event_even_when_no_duplicates_removed(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(
            self,
            stage: str,
            level: str,
            message: str,
            payload: dict[str, Any] | None = None,
        ) -> None:
            self.events.append((stage, level, message, payload))

    reporter = _Reporter()
    raw_job = _raw_scraper_job("https://example.com/1")

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [raw_job]
    mock_enrich.return_value = [_minimal_job("https://example.com/1")]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [_minimal_job("https://example.com/1")]
    mock_build_feat.return_value = [_minimal_job("https://example.com/1")]
    mock_rank.return_value = []

    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(_minimal_job("https://example.com/1")),
        ),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    assert (
        "layer1_normalize",
        "info",
        "Normalization dedupe: kept 1 of 1 jobs, removed 0 duplicate(s)",
        None,
    ) in reporter.events


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_pipeline_complete_event_omits_export_rows(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(
            self,
            stage: str,
            level: str,
            message: str,
            payload: dict[str, Any] | None = None,
        ) -> None:
            self.events.append((stage, level, message, payload))

    job = _minimal_job()
    profile = _minimal_profile()
    reporter = _Reporter()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_gen_cv.return_value = "# CV Markdown"
    mock_validate.return_value = {
        "valid": True,
        "missing_sections": [],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }
    mock_create_version.return_value = {"version_id": "v1", "generated_at": "2026-03-29T16:11:40Z"}

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=_agentic_generation_result()),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    assert all("export_results" not in str(event[2]) for event in reporter.events)


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_emits_bounded_cv_analysis_event_payload(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
            self.events.append((stage, level, message, payload))

    job = _minimal_job()
    profile = _minimal_profile()
    reporter = _Reporter()

    cfg = _minimal_config()
    cfg["stage_runtime"] = {"cv_analysis": {"concurrency": 3}}
    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [{**job, "fit_label": "skip", "fit_label_source": "reranker"}]
    mock_build_feat.return_value = [{**job, "fit_label": "skip", "fit_label_source": "reranker"}]
    mock_rank.return_value = [{**job, "fit_label": "skip", "fit_label_source": "reranker"}]

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter)

    cv_analysis_event = next(event for event in reporter.events if event[0] == "layer4_cv_analysis")
    payload = cv_analysis_event[3] or {}
    assert payload.get("event_name") == "cv_analysis_decision"
    assert payload.get("event_family") == "decision"
    assert payload.get("source_stage") == "cv_analysis"
    assert payload.get("event_status") == "completed"
    assert payload.get("stage_owned_subreason") == "stage_summary"
    assert payload.get("input_snapshot") == {
        "ranked_jobs": 1,
        "cv_analysis_concurrency_configured": 3,
    }
    output_snapshot = dict(payload.get("output_snapshot") or {})
    assert output_snapshot["ready_for_generation"] == 0
    assert output_snapshot["blocked_by_reranker_fit"] == 1
    assert output_snapshot["skipped_fit_gate"] == 0
    assert output_snapshot["analysis_failed"] == 0
    assert output_snapshot["cv_analysis_concurrency_effective"] == 1
    assert output_snapshot["fresh_analysis_reuse_mismatch_reasons"] == {}
    assert output_snapshot["fresh_analysis_overlap_urls"] == 0
    assert output_snapshot["fresh_analysis_no_overlap_urls"] == 0


@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_cv_analysis_concurrency_preserves_result_order(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_store_rank: MagicMock,
    mock_rank: MagicMock,
    mock_build_feat: MagicMock,
    mock_ai: MagicMock,
    mock_vec: MagicMock,
    mock_embed_cand: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job_a = _minimal_job("https://example.com/a")
    job_b = _minimal_job("https://example.com/b")

    cfg = _minimal_config()
    cfg.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    cfg["stage_runtime"] = {"cv_analysis": {"concurrency": 2}}
    mock_config.return_value = cfg
    mock_parse.return_value = [job_a, job_b]
    mock_norm.return_value = [job_a, job_b]
    mock_pre_filter.return_value = {"passed": [job_a["job_url"], job_b["job_url"]], "rejected": []}
    mock_enrich.return_value = [job_a, job_b]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_filter.return_value = {"passed": [job_a["job_url"], job_b["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([
        {"job_url": job_a["job_url"], "similarity_score": 0.9, "rank": 1},
        {"job_url": job_b["job_url"], "similarity_score": 0.89, "rank": 2},
    ])
    mock_ai.return_value = [
        {**job_a, "fit_label": "strong", "fit_label_source": "reranker"},
        {**job_b, "fit_label": "strong", "fit_label_source": "reranker"},
    ]
    mock_build_feat.return_value = [
        {**job_a, "fit_label": "strong", "fit_label_source": "reranker", "final_rank": 1},
        {**job_b, "fit_label": "strong", "fit_label_source": "reranker", "final_rank": 2},
    ]
    mock_rank.return_value = [
        {**job_a, "fit_label": "strong", "fit_label_source": "reranker", "final_rank": 1},
        {**job_b, "fit_label": "strong", "fit_label_source": "reranker", "final_rank": 2},
    ]

    import threading
    import time

    active_calls = 0
    max_active_calls = 0
    active_calls_lock = threading.Lock()

    def _analyze_with_overlap(job: dict[str, Any], *_: Any, **__: Any) -> dict[str, Any]:
        nonlocal active_calls, max_active_calls
        with active_calls_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        time.sleep(0.05)
        with active_calls_lock:
            active_calls -= 1
        return _agentic_analysis_ready(job)

    with patch("fitcv.pipeline.analyze_ranked_job", side_effect=_analyze_with_overlap):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            stop_after_stage="cv_analysis",
        )

    assert result["paused_after_stage"] == "cv_analysis"
    assert [row["job_url"] for row in result["checkpoint_payload"]["cv_analysis_results"]] == [
        job_a["job_url"],
        job_b["job_url"],
    ]
    assert max_active_calls == 2


def test_normalize_late_stage_reuse_snapshots_skips_poisoned_runtime_exception_rows() -> None:
    from fitcv.pipeline import _normalize_late_stage_reuse_snapshots

    payload = {
        "ranking_ai_scores": [
            {
                "ai_score_row": {
                    "parser_status": "runtime_exception",
                    "score_reasoning": "Scoring error: Your default credentials were not found.",
                }
            },
            {
                "ai_score_row": {
                    "parser_status": "ok",
                    "score_reasoning": "Valid",
                }
            },
        ],
        "cv_analysis_records": [],
    }

    normalized = _normalize_late_stage_reuse_snapshots(payload)

    assert len(normalized["ranking_ai_scores"]) == 1
    assert normalized["ranking_ai_scores"][0]["ai_score_row"]["parser_status"] == "ok"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
@patch("fitcv.pipeline.resolve_model_routing_part")
def test_run_pipeline_emits_bounded_cv_generation_event_payload_for_validation_failed_job(
    mock_resolve_model_routing: MagicMock,
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    class _Reporter:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

        def emit(self, stage: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
            self.events.append((stage, level, message, payload))

    job = _minimal_job()
    profile = _minimal_profile()
    reporter = _Reporter()
    mock_resolve_model_routing.return_value = {
        "provider": "openai_compatible",
        "model": "cx/gpt-5.2",
        "base_url": "http://localhost:20128/v1",
    }

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_pre_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = [job]
    mock_evidence.return_value = [{"evidence_id": "e1", "source_ref": "profile:experience"}]
    mock_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}
    mock_gen_cv.return_value = "# Broken CV"
    mock_validate.return_value = {
        "valid": False,
        "missing_sections": ["experience"],
        "grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
    }

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=_agentic_analysis_ready(job)),
        patch(
            "fitcv.pipeline.run_agentic_cv_generation",
            return_value=_agentic_generation_result(
                status="validation_failed",
                validation_initial={
                    "valid": False,
                    "missing_sections": ["experience"],
                    "grounding_violations": [],
                    "skill_violations": [],
                    "warnings": [],
                },
            ),
        ),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", reporter=reporter, run_id="run-validation-event")

    decision_event = next(
        event
        for event in reporter.events
        if isinstance(event[3], dict)
        and event[3].get("event_family") == "decision"
        and event[3].get("source_stage") == "cv_generation"
    )
    assert decision_event[3]["deterministic_outcome"] in {"validation_failed", "rejected"}


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_returns_export_results_sorted_and_statused(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    ranked_with_cv = {
        **_minimal_job("https://example.com/1"),
        "title": "Ranked With CV",
        "job_title": "Ranked With CV",
        "required_skills": ["SQL"],
        "ai_score": 0.91,
        "final_score": 0.95,
        "vector_similarity": 0.88,
        "fit_label": "strong",
        "final_rank": 1,
    }
    ranked_no_cv = {
        **_minimal_job("https://example.com/2"),
        "title": "Ranked No CV",
        "job_title": "Ranked No CV",
        "required_skills": ["Python"],
        "ai_score": 0.20,
        "final_score": 0.80,
        "vector_similarity": 0.70,
        "fit_label": "skip",
        "final_rank": 2,
    }
    not_shortlisted = {
        **_minimal_job("https://example.com/3"),
        "title": "Not Shortlisted",
        "job_title": "Not Shortlisted",
        "required_skills": ["Spark"],
    }
    shortlisted_not_scored = {
        **_minimal_job("https://example.com/5"),
        "title": "Shortlisted Not Scored",
        "job_title": "Shortlisted Not Scored",
        "required_skills": ["dbt"],
    }
    scored_not_ranked = {
        **_minimal_job("https://example.com/6"),
        "title": "Scored Not Ranked",
        "job_title": "Scored Not Ranked",
        "required_skills": ["Airflow"],
        "ai_score": 0.44,
        "final_score": 0.45,
        "vector_similarity": 0.52,
        "fit_label": "stretch",
    }
    rejected_raw = _raw_scraper_job("https://example.com/4")

    cfg = _minimal_config()
    cfg["pipeline"]["final_top_n"] = 2
    cfg.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = cfg
    mock_parse.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        rejected_raw,
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_norm.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        {"job_url": "https://example.com/4", "title": "Rejected Raw"},
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_enrich.return_value = [
        ranked_with_cv,
        ranked_no_cv,
        not_shortlisted,
        shortlisted_not_scored,
        scored_not_ranked,
    ]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {
        "passed": [
            ranked_with_cv["job_url"],
            ranked_no_cv["job_url"],
            not_shortlisted["job_url"],
            shortlisted_not_scored["job_url"],
            scored_not_ranked["job_url"],
        ],
        "rejected": [{"job_url": "https://example.com/4", "reasons": ["applications_count_exceeded"]}],
    }
    mock_filter.return_value = {
        "passed": [
            ranked_with_cv["job_url"],
            ranked_no_cv["job_url"],
            not_shortlisted["job_url"],
            shortlisted_not_scored["job_url"],
            scored_not_ranked["job_url"],
        ],
        "passed_records": [
            {
                "job_url": not_shortlisted["job_url"],
                "marks": [
                    {
                        "code": "must_have_skill_missing",
                        "message": "Missing must-have skills",
                        "details": {"missing_count": 1, "missing_skills": ["dbt"]},
                    }
                ],
            }
        ],
        "rejected": [],
    }
    mock_vec.return_value = _vector_search_envelope([
        {"job_url": ranked_with_cv["job_url"], "vector_similarity": 0.88, "vector_rank": 1},
        {"job_url": ranked_no_cv["job_url"], "vector_similarity": 0.70, "vector_rank": 2},
        {"job_url": shortlisted_not_scored["job_url"], "vector_similarity": 0.55, "vector_rank": 3},
        {"job_url": scored_not_ranked["job_url"], "vector_similarity": 0.52, "vector_rank": 4},
    ])
    mock_ai.return_value = [ranked_with_cv, ranked_no_cv, scored_not_ranked]
    mock_build_feat.return_value = [ranked_with_cv, ranked_no_cv, scored_not_ranked]
    mock_rank.return_value = [ranked_with_cv, ranked_no_cv]
    mock_create_version.return_value = {
        "version_id": "v1",
        "generated_at": "2026-03-29T16:11:40Z",
    }
    analysis_ready = _agentic_analysis_ready(
        ranked_with_cv,
        fit_classification="strong",
        gap_summary={"matched": ["SQL"], "partial": [], "missing": []},
    )
    analysis_blocked = build_agentic_cv_analysis_record(
        job=ranked_no_cv,
        status="blocked_by_reranker_fit",
        analysis_input_fingerprint="analysis-fp-skip",
        analysis_reuse_status="not_run_reranker_skip",
        evidence_payload=[],
        evidence_selection_summary={},
        gap_summary={"matched": [], "partial": [], "missing": []},
        fit_classification="skip",
        error={
            "stage": "reranker_fit",
            "message": f"Blocked {ranked_no_cv['job_url']} before CV analysis (reranker fit=skip)",
        },
        requirement_coverage=None,
        section_confidence_hints=None,
        do_not_claim=[],
    )
    def _generation_result_for_analysis(
        analysis_record: dict[str, Any],
        profile: dict[str, Any],
        config: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any]:
        if str(analysis_record.get("status") or "") != "ready_for_generation":
            return dict(canonical_generate_from_analysis(analysis_record, profile, config))
        job = dict(analysis_record.get("job_snapshot") or {})
        return _agentic_generation_result(
            job_url=str(job.get("job_url") or ""),
            job_title=str(job.get("title") or job.get("job_title") or ""),
        )

    with (
        patch("fitcv.pipeline.analyze_ranked_job", side_effect=[analysis_ready, analysis_blocked]),
        patch("fitcv.pipeline.run_agentic_cv_generation", side_effect=_generation_result_for_analysis),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="run-export")

    export_results = result["export_results"]
    assert [row["job_url"] for row in export_results] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/5",
        "https://example.com/6",
        "https://example.com/4",
    ]
    assert export_results[0]["pipeline_status"] == "ranked_with_cv"
    assert export_results[0]["deterministic_outcome"] == "accepted"
    assert export_results[0]["stage_owned_subreason"] == "accepted"
    assert export_results[0]["source_stage"] == "cv_generation"
    assert export_results[0]["cv"]["version_id"] == "v1"
    assert export_results[0]["cv"]["ranking_fit_label"] == "strong"
    assert export_results[0]["location_type"] == "remote"
    assert "job_family" in export_results[0]
    assert "seniority" in export_results[0]
    assert "original_job" not in export_results[0]
    assert "enriched_job" not in export_results[0]
    assert "feature_contributions" not in export_results[0]["scores"]
    assert "preference_fit_components" not in export_results[0]["scores"]
    assert "structured" not in export_results[0]["cv"]
    assert "markdown" not in export_results[0]["cv"]
    assert export_results[0]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "strong",
        },
        "cv_analysis": {
            "status": "ready_for_generation",
            "completed": True,
        },
        "cv_generation": {
            "status": "accepted",
            "attempted": True,
        },
        "validation": {
            "status": "accepted",
        },
    }
    assert export_results[1]["pipeline_status"] == "ranked_blocked_by_reranker_fit"
    assert export_results[1]["deterministic_outcome"] == "blocked"
    assert export_results[1]["stage_owned_subreason"] == "blocked_by_reranker_fit"
    assert export_results[1]["source_stage"] == "cv_analysis"
    assert export_results[1]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "skip",
        },
        "cv_analysis": {
            "status": "blocked_by_reranker_fit",
            "completed": False,
        },
        "cv_generation": {
            "status": "not_attempted",
            "attempted": False,
        },
        "validation": {
            "status": "not_run",
        },
    }
    assert export_results[2]["pipeline_status"] == "not_shortlisted"
    assert export_results[2]["rule_filter_marks"] == [
        {
            "code": "must_have_skill_missing",
            "message": "Missing must-have skills",
            "details": {"missing_count": 1, "missing_skills": ["dbt"]},
        }
    ]
    assert export_results[2]["scores"]["vector_score"] is None
    assert "shortlist_debug" not in export_results[2]
    assert export_results[3]["pipeline_status"] == "shortlisted_not_scored"
    assert export_results[3]["scores"]["vector_score"] == pytest.approx(0.55)
    assert "shortlist_debug" not in export_results[3]
    assert export_results[4]["pipeline_status"] == "scored_not_ranked"
    assert export_results[4]["scores"]["final_score"] == pytest.approx(0.45)
    assert export_results[5]["pipeline_status"] == "rejected_before_enrichment"
    debug_records = result["cv_generation_debug_records"]
    assert len(debug_records) == 2
    debug_by_status = {record["status"]: record for record in debug_records}
    assert debug_by_status["accepted"]["ranking_fit_label"] == "strong"
    assert "reranker_fit_label" not in debug_by_status["accepted"]
    assert debug_by_status["accepted"]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "strong",
        },
        "cv_analysis": {
            "status": "ready_for_generation",
            "completed": True,
        },
        "cv_generation": {
            "status": "accepted",
            "attempted": True,
        },
        "validation": {
            "status": "accepted",
        },
    }
    assert debug_by_status["blocked_by_reranker_fit"]["ranking_fit_label"] == "skip"
    assert "reranker_fit_label" not in debug_by_status["blocked_by_reranker_fit"]
    assert debug_by_status["blocked_by_reranker_fit"]["decision_chain"] == {
        "shortlist": {
            "status": "returned_by_vector_search",
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": "reranker",
            "label": "skip",
        },
        "cv_analysis": {
            "status": "blocked_by_reranker_fit",
            "completed": False,
        },
        "cv_generation": {
            "status": "not_attempted",
            "attempted": False,
        },
        "validation": {
            "status": "not_run",
        },
    }
    assert debug_by_status["blocked_by_reranker_fit"]["outcome_reason"] == {
        "stage": "reranker_fit",
        "message": f"Blocked {ranked_no_cv['job_url']} before CV analysis (reranker fit=skip)",
    }
    assert debug_by_status["blocked_by_reranker_fit"]["error"] is None


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_short_circuits_reranker_skip_before_cv_analysis_dependencies(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_retrieve_bundle: MagicMock,
    mock_retrieve_evidence: MagicMock,
    mock_gap: MagicMock,
) -> None:
    """@proves pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis"""
    from fitcv.pipeline import run_pipeline

    job = {
        **_minimal_job("https://example.com/blocked"),
        "title": "Blocked Before Analysis",
        "job_title": "Blocked Before Analysis",
        "required_skills": ["SQL"],
        "fit_label": "skip",
        "fit_label_source": "reranker",
        "final_rank": 1,
        "shortlist_origin": "vector_search",
    }
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1, "shortlist_origin": "vector_search"}],
        "shortlist_diagnostics": {},
        "ai_scores": [job],
        "ranking_inputs": [job],
        "ranked": [job],
    }
    mock_config.return_value = _minimal_config()
    mock_profile_yaml.return_value = _minimal_profile()

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        start_stage="cv_analysis",
        checkpoint_payload=checkpoint_payload,
    )

    mock_retrieve_bundle.assert_not_called()
    mock_retrieve_evidence.assert_not_called()
    mock_gap.assert_not_called()

    changed_sample = result["stage_transition_artifacts"]["stages"]["cv_analysis"]["dropped_or_changed_sample"][0]
    assert changed_sample["change_type"] == "blocked_by_reranker_fit"
    assert changed_sample["deterministic_outcome"] == "blocked"
    assert changed_sample["stage_owned_subreason"] == "blocked_by_reranker_fit"
    assert changed_sample["source_stage"] == "cv_analysis"
    assert changed_sample["analysis_reuse_status"] == "not_run_reranker_skip"
    assert "analysis_input_fingerprint" not in changed_sample
    assert changed_sample["outcome_reason"] == {
        "stage": "reranker_fit",
        "message": f"Blocked {job['job_url']} before CV analysis (reranker fit=skip)",
    }

    debug_record = result["cv_generation_debug_records"][0]
    assert debug_record["status"] == "blocked_by_reranker_fit"
    assert debug_record["decision_chain"]["cv_generation"] == {
        "status": "not_attempted",
        "attempted": False,
    }
    assert result["export_results"][0]["pipeline_status"] == "ranked_blocked_by_reranker_fit"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_layer4_uses_enriched_job_fields_for_gap_and_debug(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    raw_job = _raw_scraper_job("https://example.com/1")
    enriched_job = {
        **_minimal_job("https://example.com/1"),
        "title": "Enriched Title",
        "required_skills": ["Python", "SQL"],
        "years_experience_min": 4,
        "years_experience_max": 6,
    }
    ranked_feature = {
        "job_url": "https://example.com/1",
        "ai_score": 0.91,
        "final_score": 0.95,
        "vector_similarity": 0.88,
        "fit_label": "strong",
        "final_rank": 1,
    }

    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    mock_config.return_value = config
    mock_parse.return_value = [raw_job]
    mock_norm.return_value = [{"job_url": "https://example.com/1", "title": "Normalized"}]
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_enrich.return_value = [enriched_job]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": "https://example.com/1", "vector_similarity": 0.88, "vector_rank": 1}])
    mock_ai.return_value = [{"job_url": "https://example.com/1", "ai_score": 0.91, "fit_label": "strong"}]
    mock_build_feat.return_value = [ranked_feature]
    mock_rank.return_value = [dict(ranked_feature)]
    mock_create_version.return_value = {"version_id": "v1", "generated_at": "2026-03-29T16:11:40Z"}
    analysis_gap = {"matched": ["Python"], "partial": [], "missing": ["SQL"]}
    analysis_job_snapshot = {
        **enriched_job,
        **ranked_feature,
        "job_title": "Enriched Title",
        "fit_label_source": "reranker",
    }
    generation_result = _agentic_generation_result(
        job_url=analysis_job_snapshot["job_url"],
        job_title=analysis_job_snapshot["title"],
    )
    generation_result["gap_summary"] = analysis_gap
    with (
        patch(
            "fitcv.pipeline.analyze_ranked_job",
            return_value=_agentic_analysis_ready(
                analysis_job_snapshot,
                fit_classification="strong",
                gap_summary=analysis_gap,
            ),
        ) as mock_agentic_analysis,
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result),
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="run-gap")

    analysis_job = mock_agentic_analysis.call_args.args[0]
    assert analysis_job["required_skills"] == ["Python", "SQL"]
    assert analysis_job["years_experience_min"] == 4
    assert analysis_job["years_experience_max"] == 6
    assert analysis_job["title"] == "Enriched Title"
    assert result["cv_generation_debug_records"][0]["job_title"] == "Enriched Title"
    assert result["cv_generation_debug_records"][0]["gap_summary"] == analysis_gap
    expected_embedding_job = {**enriched_job, "marks": []}
    mock_embed_jobs.assert_called_once_with([expected_embedding_job], mock_config.return_value)


@patch("fitcv.embeddings.embed_and_store_candidate")
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_shortlist_does_not_write_candidate_chunk_embeddings(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
    mock_embed_cand_chunks: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    raw_job = _raw_scraper_job("https://example.com/1")
    enriched_job = _minimal_job("https://example.com/1")
    ranked_feature = {
        "job_url": "https://example.com/1",
        "ai_score": 0.91,
        "final_score": 0.95,
        "vector_similarity": 0.88,
        "fit_label": "strong",
        "final_rank": 1,
    }
    job_url = enriched_job["job_url"]

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [raw_job]
    mock_norm.return_value = [{"job_url": job_url, "title": "Normalized"}]
    mock_pre_filter.return_value = {"passed": [job_url], "rejected": []}
    mock_enrich.return_value = [enriched_job]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_filter.return_value = {"passed": [job_url], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job_url, "vector_similarity": 0.88, "vector_rank": 1}])
    mock_ai.return_value = [{"job_url": job_url, "ai_score": 0.91, "fit_label": "strong"}]
    mock_build_feat.return_value = [ranked_feature]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="run-no-candidate-chunks")

    mock_embed_jobs.assert_called_once()
    embed_jobs_args = mock_embed_jobs.call_args.args
    assert embed_jobs_args[0][0]["job_url"] == job_url
    assert embed_jobs_args[1] == mock_config.return_value
    mock_embed_cand_chunks.assert_not_called()


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.pipeline.create_cv_version_record")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_export_marks_deduplicated_rows_explicitly(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_pre_filter: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_create_version: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    kept = _raw_scraper_job("https://example.com/1")
    deduped = _raw_scraper_job("https://example.com/2")
    deduped["companyId"] = kept["companyId"]
    deduped["title"] = kept["title"]
    deduped["description"] = kept["description"]

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [kept, deduped]
    enriched_job = _minimal_job("https://example.com/1")
    mock_enrich.return_value = [enriched_job]
    mock_profile_yaml.return_value = _minimal_profile()
    mock_pre_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_filter.return_value = {"passed": ["https://example.com/1"], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [enriched_job]
    mock_build_feat.return_value = [enriched_job]
    mock_rank.return_value = []

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    assert len(result["export_results"]) == 2
    assert result["export_results"][0]["pipeline_status"] == "scored_not_ranked"
    assert result["export_results"][1]["pipeline_status"] == "deduplicated_before_enrichment"
    assert result["export_results"][1]["reject_reasons"] == ["near_duplicate_job_posting"]


@patch("fitcv.pipeline.load_config")
def test_run_pipeline_uses_shared_config_loader(mock_config: MagicMock) -> None:
    from fitcv.pipeline import run_pipeline

    mock_config.side_effect = RuntimeError("shared loader called")

    with pytest.raises(RuntimeError, match="shared loader called"):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml")

    mock_config.assert_called_once_with(".env.yaml")


@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_cv_analysis_persists_evidence_selection_provenance(
    mock_config: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_compute_gap: MagicMock,
) -> None:
    """@proves cv_system.analysis-evidence-selection"""
    from fitcv.pipeline import run_pipeline

    profile = _minimal_profile()
    job = {
        **_minimal_job("https://example.com/1"),
        "title": "Data Analyst - Retail Banking",
        "job_family": "analytics",
        "domain": "banking",
        "required_skills_canonical": ["sql"],
        "responsibilities": ["Build KPI dashboards for banking stakeholders"],
    }
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [job],
        "passed_jobs": [job],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist": [{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}],
        "shortlist_diagnostics": {},
        "ai_scores": [],
        "ranking_inputs": [],
        "ranked": [job],
    }
    mock_config.return_value = _minimal_config()
    mock_profile_yaml.return_value = profile
    evidence_bundle = {
        "selected_evidence": [
            {
                "evidence_id": "exp-1",
                "evidence_type": "experience_entry",
                "source_ref": "experiences[0]",
                "name": "Data Analyst - Bank Corp",
                "matched_channels": ["required_skill_support", "responsibility_alignment"],
                "selection_reasons": ["required_skill_support", "responsibility_alignment"],
                "channel_subscores": {
                    "responsibility_alignment": {
                        "lexical": 0.2,
                        "semantic": 0.8,
                        "hybrid": 0.65,
                    },
                    "domain_alignment": {
                        "lexical": 0.4,
                        "semantic": 0.6,
                        "hybrid": 0.52,
                    },
                },
                "semantic_alignment": {
                    "enabled": True,
                    "semantic_methods": {
                        "required_skill_support": "embedding_similarity",
                        "role_alignment": "embedding_similarity",
                        "responsibility_alignment": "embedding_similarity",
                        "domain_alignment": "embedding_similarity",
                    },
                    "reuse_state": {
                        "candidate_evidence": "fresh_embedding",
                        "job_context": "fresh_embedding",
                    },
                },
                "selection_score": 0.91,
            }
        ],
        "selected_evidence_ids": ["exp-1"],
        "channel_counts": {
            "required_skill_support": 1,
            "role_alignment": 1,
            "domain_alignment": 1,
            "responsibility_alignment": 1,
        },
        "effective_channel_pool_size": 4,
        "merged_pool_size": 4,
        "deduped_pool_size": 2,
        "selected_evidence_count": 1,
        "unselected_top_candidates": [
            {
                "evidence_id": "proj-2",
                "evidence_type": "project_entry",
                "name": "Near Miss Project",
                "matched_channels": ["domain_alignment"],
                "selection_score": 0.41,
            }
        ],
        "hybrid_alignment": {
            "required_skill_support": {"lexical_weight": 0.70, "semantic_weight": 0.30},
            "role_alignment": {"lexical_weight": 0.60, "semantic_weight": 0.40},
            "responsibility": {"lexical_weight": 0.25, "semantic_weight": 0.75},
            "domain": {"lexical_weight": 0.40, "semantic_weight": 0.60},
        },
        "semantic_alignment": {
            "enabled": True,
            "semantic_methods": {
                "required_skill_support": "embedding_similarity",
                "role_alignment": "embedding_similarity",
                "responsibility_alignment": "embedding_similarity",
                "domain_alignment": "embedding_similarity",
            },
            "reuse_state": {
                "candidate_evidence": "mixed_fresh_and_reused",
                "job_context": "fresh_embedding",
            },
            "embedding_counts": {
                "candidate_evidence": {"fresh": 2, "reused": 3},
                "job_context": {"fresh": 1, "reused": 4},
            },
        },
    }
    mock_compute_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    with patch(
        "fitcv.pipeline.analyze_ranked_job",
        return_value=_agentic_analysis_ready(
            job,
            evidence_payload=evidence_bundle["selected_evidence"],
            gap_summary=mock_compute_gap.return_value,
        ),
    ):
        result = run_pipeline(
            "data/sample_jobs.json",
            config_path=".env.yaml",
            run_id="cv-analysis-provenance",
            start_stage="cv_analysis",
            stop_after_stage="cv_analysis",
            checkpoint_payload=checkpoint_payload,
        )

    analysis_record = result["checkpoint_payload"]["cv_analysis_results"][0]

    assert analysis_record["evidence_selection_summary"]["selected_evidence_ids"] == ["exp-1"]
    assert analysis_record["evidence_used"][0]["matched_channels"] == [
        "required_skill_support",
        "responsibility_alignment",
    ]
    assert analysis_record["evidence_used"][0]["selection_reasons"] == [
        "required_skill_support",
        "responsibility_alignment",
    ]
    assert analysis_record["evidence_used"][0]["channel_subscores"]["responsibility_alignment"]["semantic"] == 0.8
    assert analysis_record["evidence_used"][0]["semantic_alignment"]["semantic_methods"] == {
        "required_skill_support": "embedding_similarity",
        "role_alignment": "embedding_similarity",
        "responsibility_alignment": "embedding_similarity",
        "domain_alignment": "embedding_similarity",
    }
    assert analysis_record["gap_summary"]["matched"] == ["SQL"]


@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_builds_cv_analysis_trace_for_agentic_analysis_stage(
    mock_load_config: MagicMock,
    mock_load_profile: MagicMock,
    mock_retrieve_bundle: MagicMock,
    mock_compute_gap: MagicMock,
    mock_load_run_structured_jobs: MagicMock,
) -> None:
    job = {
        "job_url": "https://example.com/trace-analysis",
        "title": "Trace Analysis Job",
        "required_skills": ["SQL"],
        "preferred_skills": ["Python"],
        "responsibilities": ["Build pipelines"],
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }
    config = _minimal_config()
    config["cv"]["agentic_late_stage"]["enabled"] = True
    profile = _minimal_profile()
    checkpoint_payload = {
        "raw_jobs": [job],
        "normalized": [job],
        "enriched": [job],
        "passed_jobs": [job],
        "shortlist": [job],
        "ranked": [job],
        "cv_analysis_results": [],
    }
    mock_load_config.return_value = config
    mock_load_profile.return_value = profile
    mock_load_run_structured_jobs.return_value = [job]
    mock_retrieve_bundle.return_value = {
        "selected_evidence": [{"evidence_id": "exp-1", "evidence_type": "experience_entry"}],
        "channel_counts": {"required_skill_support": 1},
        "effective_channel_pool_size": 1,
        "merged_pool_size": 1,
        "deduped_pool_size": 1,
        "selected_evidence_ids": ["exp-1"],
    }
    mock_compute_gap.return_value = {"matched": ["SQL"], "partial": [], "missing": []}

    result = run_pipeline(
        "data/sample_jobs.json",
        config_path=".env.yaml",
        run_id="cv-analysis-trace",
        start_stage="cv_analysis",
        stop_after_stage="cv_analysis",
        checkpoint_payload=checkpoint_payload,
    )

    trace_payload = result["cv_analysis_trace"]
    assert trace_payload["trace_family"] == "stage_execution_trace"
    assert trace_payload["step_id"] == "cv_analysis"
    assert trace_payload["trace_status"] == "completed"
    assert trace_payload["trace_summary"]["records_total"] == 1
    record = trace_payload["records"][0]
    assert record["scope_type"] == "job"
    assert record["scope_key"] == "url:https://example.com/trace-analysis"
    assert record["status"] == "ready_for_generation"
    assert "runtime_provenance" not in record
    assert record["attempts"][0]["attempt_type"] == "analysis"
    assert record["input_summary"]["analysis_input_fingerprint"]
    assert record["output_summary"]["selected_evidence_count"] == 1
    assert record["repair_summary"]["repair_attempted"] is False
    assert record["error_summary"] is None


# ── run_pipeline calls load_run_structured_jobs ──────────────────────────────

@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_calls_load_run_structured_jobs(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
    mock_load_run_struct: MagicMock,
) -> None:
    """pipeline must call load_run_structured_jobs with enriched rows and run_id."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="test-run-id")

    # load_structured_jobs must also be called (existing behavior preserved)
    mock_load_struct.assert_called_once()

    # load_run_structured_jobs must be called with the enriched rows and run_id
    mock_load_run_struct.assert_called_once()
    call_kwargs = mock_load_run_struct.call_args
    # first positional arg: enriched rows
    assert len(call_kwargs.args[0]) == 1
    assert call_kwargs.args[0][0]["job_url"] == job["job_url"]
    # second positional arg: run_id
    assert call_kwargs.args[1] == "test-run-id"


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_forwards_analysis_grounding_payload_to_validation(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_retrieve_bundle: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    job["job_family"] = "analytics"
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    config["run_mode"] = "full"
    config["stop_after_stage"] = None

    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_load_run_struct.return_value = [job]
    mock_load_struct.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [{"job_url": job["job_url"], "ai_score": 0.8, "fit_label": "strong"}]
    mock_build_feat.return_value = [{
        **job,
        "job_url": job["job_url"],
        "title": "Retail Data Analyst",
        "final_score": 0.81,
        "ai_score": 0.8,
        "vector_rank": 1,
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }]
    mock_rank.return_value = [{
        **job,
        "job_url": job["job_url"],
        "title": "Retail Data Analyst",
        "final_score": 0.81,
        "ai_score": 0.8,
        "vector_rank": 1,
        "fit_label": "strong",
        "fit_label_source": "reranker",
    }]
    analysis_record = _agentic_analysis_ready(
        {
            **job,
            "title": "Retail Data Analyst",
            "fit_label": "strong",
            "fit_label_source": "reranker",
        },
        evidence_payload=[
            {
                "evidence_id": "exp-1",
                "evidence_type": "experience_entry",
                "company": "ACME",
                "role": "Data Analyst",
                "skills": ["SQL", "Power BI"],
                "bullets": ["Maintained Power BI dashboards for retail reporting."],
                "domain_tags": ["retail"],
                "matched_channels": ["required_skill_support", "responsibility_alignment"],
                "selection_reasons": ["required_skill_support", "responsibility_alignment"],
            }
        ],
        gap_summary={"matched": ["SQL"], "missing": []},
    )
    generation_result = _agentic_generation_result(
        status="accepted",
        validation_initial={
            "valid": True,
            "missing_sections": [],
            "grounding_violations": [],
            "skill_violations": [],
            "warnings": [],
        },
    )
    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=analysis_record),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result) as mock_agentic_generation,
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="run-123")

    passed_analysis_record = mock_agentic_generation.call_args.kwargs["analysis_record"]
    assert passed_analysis_record["evidence_payload"][0]["evidence_id"] == "exp-1"
    assert passed_analysis_record["evidence_selection_summary"]["selected_evidence_ids"] == ["exp-1"]
    assert passed_analysis_record["job_snapshot"]["job_family"] == job["job_family"]



@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_forwards_enrichment_parallelism_config_to_enrich_batch(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """@proves bounded_parallel_enrichment.enrichment-batch-size-setting
    @proves bounded_parallel_enrichment.enrichment-concurrency-setting
    """
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    cfg = dict(_minimal_config())
    cfg["enrichment_batch_size"] = 5
    cfg["enrichment_concurrency"] = 3

    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="reg-test-id")

    args, kwargs = mock_enrich.call_args
    passed_config = kwargs.get("config", args[1] if len(args) > 1 else {})
    assert passed_config.get("enrichment_batch_size") == 5, (
        f"enrichment_batch_size not forwarded. config={passed_config}"
    )
    assert passed_config.get("enrichment_concurrency") == 3, (
        f"enrichment_concurrency not forwarded. config={passed_config}"
    )


@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_projects_canonical_enrich_runtime_to_legacy_keys(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    cfg = dict(_minimal_config())
    cfg["stage_runtime"] = {"enrich": {"sleep_secs": 0.3, "batch_size": 7, "concurrency": 2}}

    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="reg-test-canonical-enrich")

    args, kwargs = mock_enrich.call_args
    passed_config = kwargs.get("config", args[1] if len(args) > 1 else {})
    assert passed_config.get("enrichment_sleep_secs") == 0.3
    assert passed_config.get("enrichment_batch_size") == 7
    assert passed_config.get("enrichment_concurrency") == 2

@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_canonical_enrich_runtime_overrides_legacy_throughput_keys(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    cfg = dict(_minimal_config())
    cfg["enrichment_sleep_secs"] = 9.0
    cfg["enrichment_batch_size"] = 99
    cfg["enrichment_concurrency"] = 11
    cfg["stage_runtime"] = {"enrich": {"sleep_secs": 0.2, "batch_size": 6, "concurrency": 3}}

    mock_config.return_value = cfg
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="reg-test-canonical-precedence")

    args, kwargs = mock_enrich.call_args
    passed_config = kwargs.get("config", args[1] if len(args) > 1 else {})
    assert passed_config.get("enrichment_sleep_secs") == 0.2
    assert passed_config.get("enrichment_batch_size") == 6
    assert passed_config.get("enrichment_concurrency") == 3


@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.apply_pre_enrichment_global_filters")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_pre_filter: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    """@proves bounded_parallel_enrichment.pre-enrichment-global-filters-run-first"""
    from fitcv.pipeline import run_pipeline

    kept_job = _minimal_job()
    rejected_job = {
        **_minimal_job(),
        "job_url": "https://example.com/rejected",
        "title": "Rejected Before Enrich",
    }
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [kept_job, rejected_job]
    mock_norm.return_value = [kept_job, rejected_job]
    mock_pre_filter.return_value = {
        "passed": [kept_job["job_url"]],
        "rejected": [
            {
                "job_url": rejected_job["job_url"],
                "title": rejected_job["title"],
                "pre_filter_marks": [{"code": "global_job_filter", "message": "Too old"}],
            }
        ],
    }
    mock_enrich.return_value = [kept_job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [kept_job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": kept_job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [kept_job]
    mock_build_feat.return_value = [kept_job]
    mock_rank.return_value = []

    result = run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="pre-filter-proof")

    args, kwargs = mock_enrich.call_args
    enriched_input = args[0] if args else kwargs.get("normalized_jobs", [])
    assert enriched_input == [kept_job]
    rejected_export = next(
        row for row in result["export_results"] if row["job_url"] == rejected_job["job_url"]
    )
    assert rejected_export["pipeline_status"] == "rejected_before_enrichment"

@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_preserves_agentic_evidence_selection_summary_contract(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_run_struct: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
) -> None:
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()
    config = _minimal_config()
    config.setdefault("cv", {})["agentic_late_stage"] = {"enabled": True}
    config["run_mode"] = "full"
    config["stop_after_stage"] = None

    mock_config.return_value = config
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_enrich.return_value = [job]
    mock_load_run_struct.return_value = [job]
    mock_load_struct.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "vector_similarity": 0.9, "vector_rank": 1}])
    mock_ai.return_value = [{"job_url": job["job_url"], "ai_score": 0.8, "fit_label": "strong"}]
    mock_build_feat.return_value = [{**job, "fit_label": "strong", "fit_label_source": "reranker"}]
    mock_rank.return_value = [{**job, "fit_label": "strong", "fit_label_source": "reranker"}]

    analysis_record = _agentic_analysis_ready(
        {**job, "fit_label": "strong", "fit_label_source": "reranker"},
    )
    analysis_record["evidence_selection_summary"] = {
        "selected_evidence_ids": ["exp-1"],
        "selected_evidence_count": 1,
        "fallback_used": False,
        "hybrid_alignment": {"responsibility_alignment": {"lexical_weight": 0.25, "semantic_weight": 0.75}},
        "semantic_alignment": {"enabled": True},
    }
    generation_result = _agentic_generation_result(status="accepted")

    with (
        patch("fitcv.pipeline.analyze_ranked_job", return_value=analysis_record),
        patch("fitcv.pipeline.run_agentic_cv_generation", return_value=generation_result) as mock_agentic_generation,
        patch("fitcv.pipeline._hitl_review_reason_for_agentic_case", return_value=None),
    ):
        run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="run-124")

    passed_analysis_record = mock_agentic_generation.call_args.kwargs["analysis_record"]
    summary = passed_analysis_record["evidence_selection_summary"]
    assert summary["selected_evidence_ids"] == ["exp-1"]
    assert summary["selected_evidence_count"] == 1
    assert summary["fallback_used"] is False
    assert summary["hybrid_alignment"]["responsibility_alignment"]["semantic_weight"] == 0.75


def test_bounded_event_payload_uses_canonical_observability_builder() -> None:
    from fitcv.pipeline import _bounded_event_payload
    from fitcv.pipeline_observability import build_bounded_event_payload

    payload_kwargs = {
        "event_name": "cv_generation_result",
        "event_family": "decision",
        "source_stage": "cv_generation",
        "event_status": "completed",
        "job_url": "https://example.com/job",
        "deterministic_outcome": "accepted",
        "stage_owned_subreason": "accepted",
        "confidence": 0.9,
        "fallback_used": False,
        "provenance": {"source": "test"},
        "input_snapshot": {"k": "v"},
        "output_snapshot": {"status": "ok"},
        "artifact_refs": {"stage_id": "cv_generation"},
        "latency_ms": 123,
        "usage": {"input_tokens": 10},
        "cost": {"usd": 0.01},
    }
    assert _bounded_event_payload(**payload_kwargs) == build_bounded_event_payload(**payload_kwargs)

def test_build_ranking_features_ignores_diagnostic_reranker_lists_for_scoring() -> None:
    profile: dict = {"preferences": {"target_role": "Data Engineer"}}
    config: dict = {}

    ai_scores_a = _make_ai_scores()
    ai_scores_b = _make_ai_scores()
    ai_scores_a[0]["matched_strengths"] = ["SQL", "Python"]
    ai_scores_a[0]["key_risks"] = ["No Spark"]
    ai_scores_b[0]["matched_strengths"] = ["Completely different"]
    ai_scores_b[0]["key_risks"] = ["Completely different"]

    features_a = build_ranking_features(_make_shortlist(), ai_scores_a, profile, config)
    features_b = build_ranking_features(_make_shortlist(), ai_scores_b, profile, config)

    by_url_a = {row["job_url"]: row for row in features_a}
    by_url_b = {row["job_url"]: row for row in features_b}
    assert by_url_a.keys() == by_url_b.keys()
    for url in by_url_a:
        assert by_url_a[url]["final_score"] == pytest.approx(by_url_b[url]["final_score"])








@patch("fitcv.pipeline.load_run_structured_jobs")
@patch("fitcv.pipeline.store_cv_version")
@patch("fitcv.agentic_cv_generation.run_all_validations")
@patch("fitcv.agentic_cv_generation.generate_cv")
@patch("fitcv.agentic_cv_analysis.compute_gap")
@patch("fitcv.agentic_cv_analysis.retrieve_evidence_bundle")
@patch("fitcv.pipeline.store_final_ranking")
@patch("fitcv.pipeline.rank_jobs")
@patch("fitcv.pipeline.build_ranking_features")
@patch("fitcv.pipeline.run_ai_scoring")
@patch("fitcv.pipeline.run_vector_search")
@patch("fitcv.pipeline.embed_and_store_candidate")
@patch("fitcv.pipeline.embed_and_store_jobs")
@patch("fitcv.pipeline.store_filter_results")
@patch("fitcv.pipeline.apply_rule_filters")
@patch("fitcv.pipeline.load_candidate_profile")
@patch("fitcv.pipeline.load_profile_yaml")
@patch("fitcv.pipeline.load_structured_jobs")
@patch("fitcv.pipeline.enrich_batch")
@patch("fitcv.pipeline.load_raw_jobs")
@patch("fitcv.pipeline.normalize_batch")
@patch("fitcv.pipeline.parse_jobs_file")
@patch("fitcv.pipeline.load_config")
def test_run_pipeline_incremental_enrich_persists_each_store_exactly_once(
    mock_config: MagicMock,
    mock_parse: MagicMock,
    mock_norm: MagicMock,
    mock_load_bq: MagicMock,
    mock_enrich: MagicMock,
    mock_load_struct: MagicMock,
    mock_profile_yaml: MagicMock,
    mock_load_cand: MagicMock,
    mock_filter: MagicMock,
    mock_store_filter: MagicMock,
    mock_embed_jobs: MagicMock,
    mock_embed_cand: MagicMock,
    mock_vec: MagicMock,
    mock_ai: MagicMock,
    mock_build_feat: MagicMock,
    mock_rank: MagicMock,
    mock_store_rank: MagicMock,
    mock_evidence: MagicMock,
    mock_gap: MagicMock,
    mock_gen_cv: MagicMock,
    mock_validate: MagicMock,
    mock_store_ver: MagicMock,
    mock_load_run_struct: MagicMock,
) -> None:
    """Incremental enrich persistence must not duplicate structured or run-scoped writes."""
    from fitcv.pipeline import run_pipeline

    job = _minimal_job()
    profile = _minimal_profile()

    mock_config.return_value = _minimal_config()
    mock_parse.return_value = [job]
    mock_norm.return_value = [job]
    mock_profile_yaml.return_value = profile
    mock_filter.return_value = {"passed": [job["job_url"]], "rejected": []}
    mock_vec.return_value = _vector_search_envelope([{"job_url": job["job_url"], "similarity_score": 0.9, "rank": 1}])
    mock_ai.return_value = [job]
    mock_build_feat.return_value = [job]
    mock_rank.return_value = []

    def enrich_side_effect(
        rows,
        config,
        job_event_callback=None,
        runtime_observation_callback=None,
        on_chunk_complete=None,
    ):
        enriched = [
            {
                **row,
                "enrichment_version": "v1",
                "enrichment_model": "cx/gpt-5.4-mini",
                "enriched_at": "2026-04-03T00:01:00+00:00",
            }
            for row in rows
        ]
        if on_chunk_complete is not None:
            on_chunk_complete(enriched)
        return enriched

    mock_enrich.side_effect = enrich_side_effect

    run_pipeline("data/sample_jobs.json", config_path=".env.yaml", run_id="test-run-id")

    assert mock_load_struct.call_count == 1
    assert mock_load_run_struct.call_count == 1


def test_llm_runtime_summary_is_deterministic_and_stage_neutral() -> None:
    from fitcv.pipeline_stage_artifacts import build_llm_runtime_summary

    def observation(scope_key: str, input_index: int, status: str, code: str | None = None) -> dict[str, Any]:
        return {
            "contract_version": "llm_runtime_observation_v1",
            "scope_key": scope_key,
            "input_index": input_index,
            "invocation_index": 1,
            "evidence": {
                "contract_version": "llm_runtime_evidence_v1",
                "status": status,
                "provenance": {"adapter": "fake", "runtime_path": "test"},
                "failure": None if code is None else {"stage": "adapter", "code": code},
            },
        }

    summary = build_llm_runtime_summary(
        [observation("b", 1, "succeeded"), observation("a", 0, "failed", "adapter_timeout")],
        sample_limit=1,
    )

    assert summary["contract_version"] == "llm_stage_runtime_summary_v1"
    assert summary["calls_total"] == 2
    assert summary["succeeded_total"] == 1
    assert summary["failed_total"] == 1
    assert summary["failure_counts_by_stage"] == {"adapter": 1}
    assert summary["failure_counts_by_code"] == {"adapter_timeout": 1}
    assert summary["adapters"] == ["fake"]
    assert summary["runtime_paths"] == ["test"]
    assert [item["scope_key"] for item in summary["evidence_sample"]] == ["a"]
