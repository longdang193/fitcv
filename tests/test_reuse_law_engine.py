import pytest

from fitcv.reuse_law_engine import build_identity, emit_provenance, evaluate_gate
from fitcv.reuse import affected_reuse_units, build_reuse_decision


def _identity(**kwargs):
    return build_identity(
        "cv_generation",
        {"canonical": "data engineering", "candidate_profile_revision": "r1"},
        {"provider": "fixture", "model": "fixture-model"},
        **kwargs,
    )


def test_identity_changes_when_stage_input_or_candidate_revision_changes() -> None:
    baseline = _identity(stage_input_fingerprint="input-1", candidate_revision_fingerprint="r1")
    changed_input = _identity(stage_input_fingerprint="input-2", candidate_revision_fingerprint="r1")
    changed_revision = _identity(stage_input_fingerprint="input-1", candidate_revision_fingerprint="r2")

    assert baseline.final_reuse_key != changed_input.final_reuse_key
    assert baseline.final_reuse_key != changed_revision.final_reuse_key


def test_identity_rejects_empty_inputs_instead_of_hashing_blanks() -> None:
    with pytest.raises(ValueError, match="reuse_identity_inputs_required"):
        build_identity("cv_generation", {}, {})


def test_provenance_distinguishes_hit_invalidation_and_rejection() -> None:
    identity = _identity(stage_input_fingerprint="input-1")

    hit = emit_provenance(
        evaluate_gate(
            identity,
            {"seed_available": True, "runtime_match": True, "semantic_match": True},
            {"enabled": True},
        )
    )
    invalidation = emit_provenance(
        evaluate_gate(
            identity,
            {
                "seed_available": True,
                "runtime_match": True,
                "semantic_match": True,
                "identity_match": False,
                "invalidated_units": ["generation:summary"],
            },
            {"enabled": True},
        )
    )
    rejection = emit_provenance(
        evaluate_gate(
            identity,
            {"seed_available": False},
            {"enabled": True},
        )
    )

    assert hit["provenance_event"] == "hit"
    assert invalidation["provenance_event"] == "invalidation"
    assert invalidation["invalidated_units"] == ["generation:summary"]
    assert rejection["provenance_event"] == "rejection"


def test_invalidation_stops_at_affected_downstream_units() -> None:
    assert affected_reuse_units("cv_analysis") == ["cv_analysis", "cv_generation", "render"]
    assert affected_reuse_units("cv_generation") == ["cv_generation", "render"]
    assert affected_reuse_units("cv_generation", changed=False) == []

    decision = build_reuse_decision(
        decision="fresh_compute",
        reason_code="analysis_input_fingerprint_mismatch",
        fingerprint="input-2",
        source_artifact_type="cv_analysis",
    )
    assert decision["provenance_event"] == "invalidation"
    assert decision["affected_units"] == ["cv_analysis", "cv_generation", "render"]
    assert decision["identity_source"] == "reuse_law_engine"
