from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fitcv.pipeline_contracts import (
    JOB_OUTCOME_REQUIRED_KEYS,
    build_job_outcome_fact,
    count_job_outcomes,
    job_outcome_event_reference,
    job_outcome_fingerprint,
    job_outcome_surface,
    project_job_outcome,
    project_pipeline_status_outcome,
    resolve_job_outcome_fact,
    validate_job_outcome_fact,
)


def _fact(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": "run-1",
        "input_index": 42,
        "job_url": "https://example.com/jobs/42",
        "attempt_id": None,
        "stage_status": "ranked_skipped_fit_gate",
        "reason_facts": {"observed": 0.41, "required": 0.6},
        "policy_version": "cv_analysis.v3",
        "trace_id": "trace-1",
        "evidence_ref": {
            "artifact": "cv_analysis.json",
            "fingerprint": "sha256:evidence",
            "record_key": "input:42",
        },
        "occurred_at": datetime(2026, 7, 17, 18, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_job_outcome_fact(**values)


def test_native_fact_has_exact_required_keys_and_input_occurrence_identity() -> None:
    fact = _fact()

    assert set(fact) == JOB_OUTCOME_REQUIRED_KEYS
    assert fact["job_key"] == "input:42"
    assert fact["schema_version"] == "job_outcome.v1"
    assert fact["projection_status"] == "native"


@pytest.mark.parametrize(
    ("status", "outcome", "stage", "reason", "projection_status"),
    [
        ("ranked_with_cv", "accepted", "cv_generation", "accepted", "native"),
        ("review_required", "held", "cv_generation", "review_gate_manual_required", "native"),
        ("ranked_blocked_by_reranker_fit", "blocked", "cv_analysis", "reranker_fit_below_threshold", "native"),
        ("blocked_by_reranker_fit", "blocked", "cv_analysis", "reranker_fit_below_threshold", "native"),
        ("ranked_skipped_fit_gate", "skipped", "cv_analysis", "cv_analysis_fit_gate_skipped", "native"),
        ("skipped_fit_gate", "skipped", "cv_analysis", "cv_analysis_fit_gate_skipped", "native"),
        ("validation_failed", "rejected", "cv_generation", "post_validation_failed", "native"),
        ("generation_failed", "blocked", "cv_generation", "cv_generation_failed", "native"),
        ("persistence_failed", "blocked", "cv_generation", "cv_persistence_failed", "native"),
        ("analysis_failed", "blocked", "cv_analysis", "cv_analysis_failed", "native"),
        ("not_shortlisted", "skipped", "shortlist", "not_selected_by_shortlist", "native"),
        ("shortlisted_not_scored", "skipped", "ranking", "not_selected_for_scoring", "native"),
        ("scored_not_ranked", "skipped", "ranking", "not_selected_in_final_ranking", "native"),
        ("rejected_after_enrichment", "rejected", "rule_filter", "rule_filter_rejected", "native"),
        ("rejected_before_enrichment", "rejected", "normalize", "pre_enrichment_filter_rejected", "native"),
        ("deduplicated_before_enrichment", "skipped", "normalize", "duplicate_job_url", "native"),
        ("unknown_pipeline_state", "blocked", "pipeline", "pipeline_state_unclassified", "native"),
        ("ranked_no_cv", "blocked", "cv_generation", "legacy_ranked_no_cv_unclassified", "incomplete"),
    ],
)
def test_pipeline_status_mapping_is_exhaustive(
    status: str,
    outcome: str,
    stage: str,
    reason: str,
    projection_status: str,
) -> None:
    assert project_pipeline_status_outcome(status) == {
        "outcome": outcome,
        "stage": stage,
        "reason_code": reason,
        "projection_status": projection_status,
    }


@pytest.mark.parametrize(
    "reason_facts",
    [
        {str(index): index for index in range(17)},
        {"nested": {"a": {"b": {"c": True}}}},
        {"items": list(range(17))},
        {"text": "x" * 513},
        {"value": float("inf")},
        {"payload": "x" * 4090},
    ],
)
def test_reason_facts_bounds_are_fixed(reason_facts: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _fact(reason_facts=reason_facts)


def test_evidence_reference_requires_exact_shape_and_matching_record_key() -> None:
    with pytest.raises(ValueError):
        _fact(
            evidence_ref={
                "artifact": "cv_analysis.json",
                "fingerprint": "sha256:x",
                "record_key": "input:7",
            }
        )
    with pytest.raises(ValueError):
        _fact(
            evidence_ref={
                "artifact": "cv_analysis.json",
                "fingerprint": "sha256:x",
                "record_key": "input:42",
                "extra": True,
            }
        )


def test_fingerprint_is_deterministic_for_canonical_json() -> None:
    first = _fact(reason_facts={"required": 0.6, "observed": 0.41})
    second = _fact(reason_facts={"observed": 0.41, "required": 0.6})

    assert job_outcome_fingerprint(first) == job_outcome_fingerprint(second)
    assert job_outcome_fingerprint(first).startswith("sha256:")


def test_unknown_reason_code_remains_valid_and_visible() -> None:
    fact = _fact(stage_status="future_status", reason_code="future_reason")

    assert validate_job_outcome_fact(fact) == fact
    assert fact["reason_code"] == "future_reason"


@pytest.mark.parametrize(
    "native",
    [
        {"schema_version": "job_outcome.v1"},
        {"schema_version": "job_outcome.v2"},
    ],
)
def test_invalid_or_unknown_native_schema_never_falls_back(
    native: dict[str, object],
) -> None:
    projected = project_job_outcome(
        {"job_outcome": native, "pipeline_status": "ranked_with_cv"},
        run_id="run-1",
        input_index=0,
    )

    assert projected["outcome"] == "blocked"
    assert projected["reason_code"] == "invalid_native_outcome"
    assert projected["projection_status"] == "incomplete"


def test_held_resolution_replaces_current_snapshot() -> None:
    held = _fact(stage_status="review_required")
    resolved = _fact(
        stage_status="ranked_with_cv",
        occurred_at=datetime(2026, 7, 17, 19, tzinfo=timezone.utc),
    )
    row = {"job_outcome": held}

    row["job_outcome"] = resolved

    assert row["job_outcome"]["outcome"] == "accepted"
    assert "history" not in row["job_outcome"]

def test_export_results_emit_one_native_fact_per_input_occurrence() -> None:
    from fitcv.pipeline import _build_export_results

    stage_artifacts = {
        "schema_version": "stage_transition_artifacts_v8",
        "stages": {"normalize": {}, "pipeline": {}},
    }
    rows = _build_export_results(
        run_id="run-native",
        stage_transition_artifacts=stage_artifacts,
        raw_jobs=[
            {"job_url": "https://example.com/1", "raw_job_fingerprint": "raw-1"},
            {"job_url": "https://example.com/1", "raw_job_fingerprint": "raw-1"},
        ],
        enriched=[{"job_url": "https://example.com/1", "raw_job_fingerprint": "raw-1"}],
        deduplicated_jobs=[{"input_index": 1, "dedupe_reason": "duplicate_job_url"}],
        pre_filter_rejected=[],
        candidate_filter_rejected=[],
        passed_jobs=[],
        raw_shortlist=[],
        shortlist_for_scoring=[],
        ranking_inputs=[],
        ranked=[],
        cv_analysis_results=[],
        cv_results=[],
        cv_generation_debug_records=[],
        vector_search_top_n=10,
    )

    facts = {row["job_outcome"]["job_key"]: row["job_outcome"] for row in rows}
    assert set(facts) == {"input:0", "input:1"}
    assert facts["input:0"]["projection_status"] == "native"
    assert facts["input:1"]["reason_code"] == "duplicate_job_url"
    assert facts["input:1"]["outcome"] == "skipped"
    evidence_records = stage_artifacts["stages"]["normalize"]["outcome_evidence_records"]
    evidence = next(record for record in evidence_records if record["record_key"] == "input:1")
    assert evidence["fingerprint"] == facts["input:1"]["evidence_ref"]["fingerprint"]

def test_counts_derive_only_from_current_projected_facts() -> None:
    rows = [
        {"job_outcome": _fact(stage_status="ranked_with_cv")},
        {"job_outcome": _fact(stage_status="review_required")},
        {"job_outcome": _fact(stage_status="ranked_skipped_fit_gate")},
        {"job_outcome": _fact(stage_status="validation_failed")},
        {"job_outcome": _fact(stage_status="generation_failed")},
    ]

    assert count_job_outcomes(rows, run_id="run-1") == {
        "accepted": 1,
        "held": 1,
        "blocked": 1,
        "rejected": 1,
        "skipped": 1,
    }

def test_surface_uses_canonical_outcome_and_reason() -> None:
    surface = job_outcome_surface({"job_outcome": _fact(stage_status="review_required")}, run_id="run-1", input_index=0)

    assert surface == {
        "status": "held",
        "label": "Held",
        "badge_class": "badge-warning",
        "stage": "cv_generation",
        "reason_code": "review_gate_manual_required",
        "reason_label": "Manual review required",
        "projection_status": "native",
        "why": {
            "stage_status": "review_required",
            "reason_facts": {"observed": 0.41, "required": 0.6},
            "policy_version": "cv_analysis.v3",
            "attempt_id": None,
            "trace_id": "trace-1",
            "evidence_ref": {
                "artifact": "cv_analysis.json",
                "fingerprint": "sha256:evidence",
                "record_key": "input:42",
            },
        },
    }

def test_review_resolution_builds_replacement_fact_without_history() -> None:
    held = _fact(stage_status="review_required")

    resolved = resolve_job_outcome_fact(
        held,
        resolution="accepted",
        occurred_at=datetime(2026, 7, 17, 20, tzinfo=timezone.utc),
    )

    assert resolved["outcome"] == "accepted"
    assert resolved["reason_code"] == "accepted"
    assert resolved["stage_status"] == "review_accepted"
    assert resolved["job_key"] == held["job_key"]
    assert "history" not in resolved

def test_outcome_event_reference_contains_no_duplicate_fact_fields() -> None:
    fact = _fact()

    reference = job_outcome_event_reference(fact)

    assert set(reference) == {
        "job_key",
        "stage",
        "outcome",
        "reason_code",
        "outcome_fingerprint",
        "evidence_ref",
    }
    assert reference["outcome_fingerprint"] == job_outcome_fingerprint(fact)
    assert "reason_facts" not in reference