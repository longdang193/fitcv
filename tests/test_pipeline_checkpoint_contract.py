import pytest

from fitcv.pipeline import _checkpoint_payload_from_state
from fitcv.pipeline_stage_context import PipelineState, infer_last_completed_stage_from_state


def test_checkpoint_payload_includes_schema_version() -> None:
    payload = _checkpoint_payload_from_state({"raw_jobs": []})
    assert payload["schema_version"] == 1


def test_checkpoint_payload_preserves_explicit_completed_stage_marker() -> None:
    payload = _checkpoint_payload_from_state({"raw_jobs": [], "completed_stage": "cv_generation"})
    assert payload["completed_stage"] == "cv_generation"

def test_checkpoint_payload_preserves_candidate_query_debug_as_dict() -> None:
    payload = _checkpoint_payload_from_state({"candidate_query_debug": {"k": "v"}})
    assert payload["candidate_query_debug"] == {"k": "v"}


def test_pipeline_state_restores_from_wrapped_checkpoint_payload() -> None:
    state = PipelineState.from_checkpoint_payload(
        run_id="run-1",
        checkpoint_payload={
            "schema_version": 1,
            "checkpoint_payload": {"raw_jobs": [{"job_url": "x"}]},
        },
    )
    assert state.raw_jobs == [{"job_url": "x"}]


def test_pipeline_state_rejects_legacy_vector_checkpoint_without_strategy() -> None:
    with pytest.raises(ValueError, match="legacy vector-derived checkpoint missing retrieval_strategy"):
        PipelineState.from_checkpoint_payload(
            run_id="run-1",
            checkpoint_payload={
                "schema_version": 1,
                "shortlist": [{"job_url": "x", "vector_rank": 1, "vector_similarity": 0.9}],
            },
        )


def test_pipeline_state_accepts_vector_checkpoint_with_matching_strategy() -> None:
    state = PipelineState.from_checkpoint_payload(
        run_id="run-1",
        checkpoint_payload={
            "schema_version": 1,
            "shortlist_diagnostics": {"retrieval_strategy": "lexical_v1"},
            "shortlist": [{"job_url": "x", "vector_rank": 1, "vector_similarity": 0.9}],
        },
    )
    assert state.shortlist[0]["job_url"] == "x"


def test_pipeline_state_rejects_vector_rows_with_mismatched_strategies() -> None:
    with pytest.raises(ValueError, match="mismatched retrieval_strategy"):
        PipelineState.from_checkpoint_payload(
            run_id="run-1",
            checkpoint_payload={
                "shortlist": [
                    {"job_url": "x", "vector_rank": 1, "retrieval_strategy": "lexical_v1"},
                    {"job_url": "y", "vector_rank": 2, "retrieval_strategy": "vector_cosine_v1"},
                ],
            },
        )


def test_pipeline_state_rejects_vector_row_mismatch_with_lexical_diagnostics() -> None:
    with pytest.raises(ValueError, match="does not match shortlist diagnostics"):
        PipelineState.from_checkpoint_payload(
            run_id="run-1",
            checkpoint_payload={
                "shortlist_diagnostics": {"retrieval_strategy": "lexical_v1"},
                "shortlist": [{"job_url": "x", "vector_rank": 1, "retrieval_strategy": "vector_cosine_v1"}],
            },
        )


def test_pipeline_resume_rejects_lexical_checkpoint_with_active_vector_policy() -> None:
    from fitcv.pipeline import run_pipeline

    with pytest.raises(ValueError, match="incompatible preference policy in lexical checkpoint"):
        run_pipeline(
            "data/sample_jobs.json",
            config={"pipeline": {}},
            checkpoint_payload={
                "shortlist_diagnostics": {"retrieval_strategy": "lexical_v1"},
                "shortlist": [{"job_url": "x", "vector_rank": 1, "retrieval_strategy": "lexical_v1"}],
                "resolved_preference_policy": {
                    "diagnostic_code": "active_policy",
                    "runtime_contract": {"embedding_contract_fingerprint": "vector_cosine_v1"},
                },
            },
        )


def test_pipeline_resume_rejects_active_vector_policy_with_mixed_shortlist_metadata() -> None:
    from fitcv.pipeline import run_pipeline

    with pytest.raises(ValueError, match="incompatible preference policy in lexical checkpoint"):
        run_pipeline(
            "data/sample_jobs.json",
            config={"pipeline": {}},
            checkpoint_payload={
                "raw_shortlist": [{"job_url": "x", "vector_rank": 1, "retrieval_strategy": "lexical_v1"}],
                "shortlist": [{"job_url": "x", "vector_rank": 1}],
                "resolved_preference_policy": {
                    "resolution_status": "active",
                    "runtime_contract": {"embedding_contract_fingerprint": "vector_cosine_v1"},
                },
            },
        )


def test_pipeline_state_rejects_unsupported_checkpoint_schema_version() -> None:
    with pytest.raises(ValueError, match="Unsupported checkpoint schema version"):
        PipelineState.from_checkpoint_payload(
            run_id="run-1",
            checkpoint_payload={
                "schema_version": PipelineState.CHECKPOINT_SCHEMA_VERSION + 1,
                "checkpoint_payload": {},
            },
        )

def test_infer_last_completed_stage_accepts_explicit_cv_generation_completion_marker() -> None:
    assert infer_last_completed_stage_from_state({"completed_stage": "cv_generation"}) == "cv_generation"

def test_infer_last_completed_stage_recognizes_legacy_cv_generation_outputs() -> None:
    assert infer_last_completed_stage_from_state({"cv_results": [{"markdown": "# CV"}]}) == "cv_generation"
