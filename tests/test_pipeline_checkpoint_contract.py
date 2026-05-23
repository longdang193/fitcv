from fitcv.pipeline import _checkpoint_payload_from_state
from fitcv.pipeline_stage_context import PipelineState


def test_checkpoint_payload_includes_schema_version() -> None:
    payload = _checkpoint_payload_from_state({"raw_jobs": []})
    assert payload["schema_version"] == 1


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
