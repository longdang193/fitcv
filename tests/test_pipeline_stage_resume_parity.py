"""
@meta
type: test
scope: unit
domain: pipeline
covers:
  - baseline parity guard for run summary snapshots used during pipeline refactor
excludes:
  - live pipeline execution
  - network and database I/O
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
from pathlib import Path

from fitcv.pipeline_contracts import (
    PIPELINE_STAGE_SEQUENCE,
    build_stage_dispatch_map,
    completed_pipeline_stages_through,
    next_pipeline_stage,
)

from fitcv.pipeline_stage_context import PipelineState

_FIXTURE_DIR = Path("tests/golden/pipeline_refactor")


def _load(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_full_run_snapshot_contract_parity() -> None:
    payload = _load("full_run_snapshot.json")

    assert payload["status"] == "succeeded"
    assert payload["checkpoint_status"] == "completed"
    assert payload["next_stage"] is None
    assert payload["last_completed_stage"] == "cv_generation"
    assert payload["completed_stages"] == list(PIPELINE_STAGE_SEQUENCE)
    assert payload["stage_artifacts_schema_version"] == "stage_transition_artifacts_v6"
    assert payload["event_count"] >= 1
    assert "pipeline_start" in payload["event_stages_head"]


def test_checkpointed_run_snapshot_contract_parity() -> None:
    payload = _load("checkpointed_run_snapshot.json")

    assert payload["status"] == "failed"
    assert payload["checkpoint_status"] == "queued_for_continue"
    assert payload["next_stage"] == "enrich"
    assert payload["last_completed_stage"] == "normalize"
    assert payload["completed_stages"] == ["normalize"]
    assert payload["stage_artifacts_schema_version"] == "stage_transition_artifacts_v6"
    assert payload["event_count"] >= 1
    assert "pipeline_failed" in payload["event_stages_tail"]


def test_stage_sequence_resume_contract() -> None:
    assert next_pipeline_stage("normalize") == "enrich"
    assert next_pipeline_stage("cv_generation") is None
    assert completed_pipeline_stages_through("ranking") == [
        "normalize",
        "enrich",
        "rule_filter",
        "shortlist",
        "ranking",
    ]


def test_stage_dispatch_map_scaffold_matches_sequence() -> None:
    dispatch_map = build_stage_dispatch_map()
    assert list(dispatch_map.keys()) == list(PIPELINE_STAGE_SEQUENCE)
    assert list(dispatch_map.values()) == list(PIPELINE_STAGE_SEQUENCE)



def test_pipeline_state_round_trips_llm_runtime_observations() -> None:
    observation = {
        "contract_version": "llm_runtime_observation_v1",
        "scope_key": "job-1",
        "input_index": 0,
        "invocation_index": 1,
        "evidence": {"contract_version": "llm_runtime_evidence_v1", "status": "succeeded"},
    }
    state = PipelineState(
        run_id="run-1",
        enrich_llm_runtime_observations=[observation],
        ranking_llm_runtime_observations=[observation],
    )

    restored = PipelineState.from_checkpoint_payload(
        run_id="run-1",
        checkpoint_payload=state.as_state_dict(),
    )

    assert restored.enrich_llm_runtime_observations == [observation]
    assert restored.ranking_llm_runtime_observations == [observation]
