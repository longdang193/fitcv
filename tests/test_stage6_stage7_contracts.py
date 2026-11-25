import pytest

from fitcv.contracts import (
    build_coverage_fingerprints,
    build_stage_6_to_7_failure,
    build_stage_6_to_7_handoff,
    deserialize_stage_6_to_7_handoff,
    validate_coverage_fingerprints,
    validate_stage_6_to_7_handoff,
)
from fitcv.shortlist_selection import build_evidence_manifest, validate_evidence_manifest


def _job():
    return {
        "job_url": "https://example.com/job/1",
        "title": "Analyst",
        "score_status": "valid",
        "ai_score": 0.8,
        "final_rank": 1,
        "baseline_rank": 1,
        "stage5_admission": {"admitted": True, "status": "admitted"},
    }

def test_stage6_handoff_round_trips_and_validates():
    profile = {"candidate_profile_id": "candidate-1", "revision": "r1"}
    payload = build_stage_6_to_7_handoff(_job(), profile=profile)
    assert deserialize_stage_6_to_7_handoff(payload)["handoff_fingerprint"] == payload["handoff_fingerprint"]
    assert validate_stage_6_to_7_handoff(payload, job=_job(), profile=profile)["final_rank"] == 1

def test_stage6_handoff_rejects_missing_and_conflicting_fields():
    profile = {"candidate_profile_id": "candidate-1", "revision": "r1"}
    payload = build_stage_6_to_7_handoff(_job(), profile=profile)
    with pytest.raises(ValueError, match="handoff_fingerprint_conflict"):
        validate_stage_6_to_7_handoff({**payload, "final_rank": 2}, job=_job(), profile=profile)
    with pytest.raises(ValueError, match="handoff_fingerprint_conflict"):
        validate_stage_6_to_7_handoff(
            {**payload, "job_url": "https://example.com/job/2"},
            job=_job(),
            profile=profile,
        )


def test_stage6_technical_failure_round_trips_and_corrected_handoff_validates():
    profile = {"candidate_profile_id": "candidate-1", "revision": "r1"}
    failure = build_stage_6_to_7_failure(
        _job(),
        failure_code="handoff_fingerprint_conflict",
        scope={"job_identity": "https://example.com/job/1", "handoff_fingerprint": "old"},
    )
    assert failure["status"] == "handoff_contract_failed"
    assert failure["terminal"] is True
    assert failure["retry_eligible"] is True
    assert failure["scope"]["handoff_fingerprint"] == "old"

    corrected = build_stage_6_to_7_handoff(_job(), profile=profile)
    assert validate_stage_6_to_7_handoff(corrected, job=_job(), profile=profile)["final_rank"] == 1

def test_coverage_fingerprints_are_order_independent_and_revision_sensitive():
    first = build_coverage_fingerprints(
        requirement_contract=["b", "a", "a"],
        assessment_inputs={"x": 1},
        evidence_compatibility=[{"id": "e1", "revision": "1"}],
        retrieval_policy={"top_k": 3},
        support_policy={"mode": "strict"},
    )
    second = build_coverage_fingerprints(
        requirement_contract=["a", "b"],
        assessment_inputs={"x": 1},
        evidence_compatibility=[{"revision": "1", "id": "e1"}],
        retrieval_policy={"top_k": 3},
        support_policy={"mode": "strict"},
    )
    changed = build_coverage_fingerprints(
        requirement_contract=["a", "b"],
        assessment_inputs={"x": 1},
        evidence_compatibility=[{"id": "e1", "revision": "2"}],
        retrieval_policy={"top_k": 3},
        support_policy={"mode": "strict"},
    )
    assert first["fingerprint"] == second["fingerprint"]
    assert first["fingerprint"] != changed["fingerprint"]
    assert validate_coverage_fingerprints(first)["schema_version"] == "fitcv.coverage_fingerprint.v1"


def test_evidence_manifest_keeps_invalid_reference_diagnostics_and_rejects_it():
    manifest = build_evidence_manifest(
        [
            {"occurrence_id": "occ-1", "evidence_id": "ev-1", "revision": "r1"},
            {"occurrence_id": "occ-2", "evidence_id": "ev-2"},
        ]
    )
    assert manifest["invalid_references"][0]["reason"] == "evidence_revision_or_content_hash_missing"
    assert manifest["integrity_complete"] is False
    with pytest.raises(ValueError, match="evidence_manifest_reference_invalid"):
        validate_evidence_manifest(manifest)


def test_evidence_manifest_overflow_is_not_hydratable():
    manifest = build_evidence_manifest(
        [
            {"occurrence_id": "occ-1", "evidence_id": "ev-1", "revision": "r1"},
            {"occurrence_id": "occ-2", "evidence_id": "ev-2", "revision": "r1"},
        ],
        max_items=1,
    )
    assert manifest["overflow"] == 1
    with pytest.raises(ValueError, match="evidence_manifest_overflow"):
        validate_evidence_manifest(manifest)


def test_evidence_manifest_rejects_stale_hydration_reference():
    manifest = build_evidence_manifest(
        [{"occurrence_id": "occ-1", "evidence_id": "ev-1", "revision": "r1"}]
    )
    with pytest.raises(ValueError, match="evidence_manifest_reference_stale"):
        validate_evidence_manifest(
            manifest,
            [{"occurrence_id": "occ-1", "evidence_id": "ev-1", "revision": "r2"}],
        )

from fitcv.pipeline import _canonical_resume_start_stage, _checkpoint_payload_from_state
from fitcv.pipeline_stage_context import PipelineState
from fitcv.resume_invalidation import ResumeDecisionError, decide_resume_invalidation


def _checkpoint(**overrides):
    payload = {
        "resume_contract": {
            "current_stage": "cv_generation",
            "next_stage": "cv_generation",
            "handoff_fingerprint": "handoff-1",
            "contract_revision": "contract-1",
            "policy_revision": "policy-1",
            "profile_revision": "profile-1",
            "evidence_revision": "evidence-1",
            "predecessor_revision": "pred-1",
            "coverage_fingerprint": "coverage-1",
            "coverage_required": True,
            "valid_current_handoff": True,
            "terminal": False,
        }
    }
    payload["resume_contract"].update(overrides)
    return payload


def _current(**overrides):
    payload = {
        "handoff_fingerprint": "handoff-1",
        "contract_revision": "contract-1",
        "policy_revision": "policy-1",
        "profile_revision": "profile-1",
        "evidence_revision": "evidence-1",
        "predecessor_revision": "pred-1",
        "coverage_fingerprint": "coverage-1",
    }
    payload.update(overrides)
    return payload


def test_resume_matrix_compatible_checkpoint_resumes_without_invalidation():
    decision = decide_resume_invalidation(
        _checkpoint(), current=_current(), worker_projection={"next_stage": "cv_generation"}
    )
    assert decision["status"] == "resume"
    assert decision["decision_owner"] == "active_contract"
    assert decision["invalidated_stages"] == []
    assert decision["reused_downstream_state"] is True


def test_resume_matrix_legacy_fit_gate_recomputes_stage7():
    decision = decide_resume_invalidation(
        _checkpoint(analysis_status="skipped_fit_gate"), current=_current()
    )
    assert decision["status"] == "recompute"
    assert decision["restart_boundary"] == "cv_analysis"
    assert "cv_generation" in decision["invalidated_stages"]
    assert decision["reason_code"] == "legacy_fit_gate_requires_recompute"


def test_resume_matrix_missing_coverage_restarts_at_shortlist():
    checkpoint = _checkpoint()
    checkpoint["resume_contract"].pop("coverage_fingerprint")
    decision = decide_resume_invalidation(checkpoint, current=_current())
    assert decision["status"] == "restart"
    assert decision["restart_boundary"] == "shortlist"
    assert decision["invalidated_stages"] == [
        "shortlist", "ranking", "cv_analysis", "cv_generation"
    ]


def test_resume_matrix_unavailable_recompute_persists_retryable_unknown():
    decision = decide_resume_invalidation(
        _checkpoint(coverage_incomplete=True, failure_derived=True),
        current=_current(),
        recomputation_available=False,
    )
    assert decision["status"] == "technical_resume_failure"
    assert decision["reason_code"] == "coverage_recomputation_unavailable"
    assert decision["retryable"] is True
    assert decision["checkpoint_action"] == "persist_incomplete_failure_derived_u"


def test_resume_matrix_changed_revisions_restart_at_first_affected_boundary():
    decision = decide_resume_invalidation(
        _checkpoint(), current=_current(profile_revision="profile-2", evidence_revision="evidence-2")
    )
    assert decision["status"] == "restart"
    assert decision["restart_boundary"] == "enrich"
    assert decision["changed_revisions"] == ["profile_revision", "evidence_revision"]
    assert decision["invalidated_stages"][0] == "enrich"


def test_resume_matrix_display_only_change_preserves_admission():
    decision = decide_resume_invalidation(
        _checkpoint(
            display_metadata_changed=True,
            metadata_dependent_stages=["cv_analysis", "cv_generation"],
        ),
        current=_current(),
    )
    assert decision["status"] == "metadata_refresh"
    assert decision["worker_action"] == "preserve_admission"
    assert decision["invalidated_stages"] == ["cv_analysis", "cv_generation"]
    assert decision["reused_downstream_state"] is True


def test_resume_matrix_conflicting_worker_projection_stops_without_continuation():
    decision = decide_resume_invalidation(
        _checkpoint(),
        current=_current(),
        worker_projection={"terminal": True, "next_stage": "cv_generation"},
    )
    assert decision["status"] == "technical_resume_failure"
    assert decision["reason_code"] == "worker_checkpoint_state_conflict"
    assert decision["worker_action"] == "stop_without_continuation"
    assert decision["reused_downstream_state"] is False


def test_pipeline_checkpoint_round_trip_preserves_resume_contract():
    contract = _checkpoint()["resume_contract"]
    state = PipelineState(run_id="run-resume", resume_contract=contract)
    payload = _checkpoint_payload_from_state(state.as_state_dict())

    restored = PipelineState.from_checkpoint_payload(
        run_id="run-resume",
        checkpoint_payload=payload,
    )

    assert restored.resume_contract == contract

def test_pipeline_checkpoint_restore_preserves_missing_ranking_values():
    payload = _checkpoint_payload_from_state(
        PipelineState(
            run_id="run-resume",
            ranking_inputs=[
                {
                    "job_url": "https://example.com/job/1",
                    "raw_job_fingerprint": "fp1",
                    "baseline_fit": None,
                    "baseline_fit_label": None,
                    "baseline_rank": None,
                }
            ],
        ).as_state_dict()
    )

    restored = PipelineState.from_checkpoint_payload(
        run_id="run-resume",
        checkpoint_payload=payload,
    )

    assert restored.ranking_inputs[0]["baseline_fit"] is None
    assert restored.ranking_inputs[0]["baseline_fit_label"] == ""
    assert restored.ranking_inputs[0]["baseline_rank"] is None


def test_pipeline_resume_entrypoint_applies_matrix_boundary_and_stops_on_conflict():
    checkpoint = _checkpoint()
    checkpoint["resume_contract"].pop("coverage_fingerprint")
    assert _canonical_resume_start_stage(
        requested_start_stage="cv_generation",
        checkpoint_payload=checkpoint,
        run_id="run-resume",
        config={"resume_inputs": _current()},
    ) == "shortlist"

    conflicting = _checkpoint()
    conflicting["worker_projection"] = {"terminal": True, "next_stage": "cv_generation"}
    with pytest.raises(ResumeDecisionError, match="worker_checkpoint_state_conflict"):
        _canonical_resume_start_stage(
            requested_start_stage="cv_generation",
            checkpoint_payload=conflicting,
            run_id="run-resume",
            config={"resume_inputs": _current()},
        )
