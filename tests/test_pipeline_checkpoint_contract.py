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
