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
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

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
    assert payload["stage_artifacts_schema_version"] == "stage_transition_artifacts_v7"
    assert payload["event_count"] >= 1
    assert "pipeline_start" in payload["event_stages_head"]


def test_checkpointed_run_snapshot_contract_parity() -> None:
    payload = _load("checkpointed_run_snapshot.json")

    assert payload["status"] == "failed"
    assert payload["checkpoint_status"] == "queued_for_continue"
    assert payload["next_stage"] == "enrich"
    assert payload["last_completed_stage"] == "normalize"
    assert payload["completed_stages"] == ["normalize"]
    assert payload["stage_artifacts_schema_version"] == "stage_transition_artifacts_v7"
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


def test_pipeline_state_persists_shortlist_diagnostics_without_audit_or_backfill() -> None:
    state = PipelineState(
        run_id="run-1",
        raw_shortlist=[{"job_url": "https://example.com/production"}],
        shortlist_diagnostics={"embedding_coverage_rate": 0.5},
    )

    payload = state.as_state_dict()
    restored = PipelineState.from_checkpoint_payload(
        run_id="run-1",
        checkpoint_payload={
            **payload,
            "backfilled_job_urls": ["https://example.com/legacy"],
            "_shortlist_audit_rows": [{"job_url": "https://example.com/audit"}],
        },
    )

    assert payload["raw_shortlist"] == [{"job_url": "https://example.com/production"}]
    assert payload["shortlist_diagnostics"] == {"embedding_coverage_rate": 0.5}
    assert "backfilled_job_urls" not in payload
    assert "_shortlist_audit_rows" not in payload
    assert restored.shortlist_diagnostics == {"embedding_coverage_rate": 0.5}
    assert not hasattr(restored, "backfilled_job_urls")


def test_shortlist_stage_consumes_vector_envelope_without_persisting_audit() -> None:
    from fitcv.pipeline_stage_runner import execute_shortlist_stage

    production_row = {
        "job_url": "https://example.com/production",
        "vector_rank": 1,
        "vector_similarity": 0.9,
        "shortlist_origin": "vector_search",
        "retrieval_strategy": "vector_cosine_v1",
    }
    audit_row = {
        "job_url": "https://example.com/audit",
        "vector_rank": 2,
        "vector_similarity": 0.8,
        "shortlist_origin": "audit",
        "retrieval_strategy": "vector_cosine_v1",
        "audit_selection_hash": "hash",
    }
    diagnostics = {
        "eligible_jobs_total": 2,
        "scored_jobs_total": 2,
        "embedding_coverage_rate": 1.0,
    }
    candidate_query = {
        "text": "candidate query",
        "components": {"headline": "Data Engineer"},
        "candidate_query_reuse_status": "fresh_compute",
        "candidate_query_signature": "signature",
        "candidate_query_contract_fingerprint": "contract",
    }
    stored: list[list[dict]] = []
    state: dict = {}

    execute_shortlist_stage(
        run_id="run-1",
        state=state,
        profile={"preferences": {}},
        passed_jobs=[
            {"job_url": production_row["job_url"], "title": "Production"},
            {"job_url": audit_row["job_url"], "title": "Audit"},
        ],
        config={"pipeline": {}},
        vector_top_n=1,
        reporter=None,
        pipeline_store=SimpleNamespace(
            embed_and_store_jobs=lambda jobs, config: None,
            store_shortlist=lambda rows, config: stored.append(rows),
        ),
        observe_span=lambda *args, **kwargs: nullcontext(),
        set_span_attributes=lambda attributes: None,
        run_vector_search=lambda profile, urls, config, *, top_n: {
            "production_rows": [production_row],
            "audit_rows": [audit_row],
            "diagnostics": diagnostics,
            "candidate_query": candidate_query,
        },
        materialize_scoring_shortlist=lambda rows, jobs: [
            {**jobs[0], **rows[0]}
        ],
        unique_job_urls=lambda rows: [str(row["job_url"]) for row in rows],
        raw_shortlist_anomaly_urls=lambda rows, jobs: [],
    )

    assert stored == [[{**state["shortlist"][0]}]]
    assert state["raw_shortlist"] == [production_row]
    assert state["shortlist_diagnostics"] == diagnostics
    assert state["_shortlist_audit_rows"] == [audit_row]
    assert all(row["job_url"] != audit_row["job_url"] for row in stored[0])


def test_rule_filter_stage_builds_context_once_and_preserves_full_payload() -> None:
    from contextlib import nullcontext
    from types import SimpleNamespace

    from fitcv.pipeline_stage_runner import execute_rule_filter_stage

    enriched_job = {
        "job_url": "https://example.com/job-1",
        "title": "Data Engineer",
        "actual_location": {"city": "Berlin", "extraction_status": "complete"},
        "language_requirements": [],
    }
    profile = {
        "preferences": {"locations": ["Berlin"], "location_types": ["remote"]},
        "languages": [{"name": "English", "level": "C1"}],
    }
    eligibility_payload = {
        "fit_factor_results": {"location_fit": {"diagnostic_code": "location_exact_city"}},
        "eligibility_policy_fingerprint": "policy-fingerprint",
        "eligibility_decision": "retain",
        "eligibility_reason_codes": [],
    }
    captured_contexts: list[dict] = []

    def fake_apply_rule_filters(
        jobs: list[dict],
        preferences: dict,
        config: dict,
        *,
        candidate_fit_context: dict,
    ) -> dict:
        captured_contexts.append(candidate_fit_context)
        return {
            "passed": [jobs[0]["job_url"]],
            "passed_records": [
                {
                    "job_url": jobs[0]["job_url"],
                    "source_job_url": jobs[0]["job_url"],
                    "raw_job_fingerprint": "raw-1",
                    "marks": [{"code": "legacy"}],
                    **eligibility_payload,
                }
            ],
            "rejected": [],
        }

    stored: list[dict] = []
    pipeline_store = SimpleNamespace(
        load_candidate_profile=lambda *_args: None,
        store_filter_results=lambda result, *_args: stored.append(result),
    )
    state = {"pre_filter_rejected_jobs": [], "enriched": [enriched_job]}

    execute_rule_filter_stage(
        run_id="run-1",
        state=state,
        config={
            "paths": {"candidate_profile": "unused"},
            "valid_location_types": ["remote", "hybrid", "onsite"],
        },
        reporter=None,
        pipeline_store=pipeline_store,
        observe_span=lambda *_args, **_kwargs: nullcontext(),
        set_span_attributes=lambda _attrs: None,
        load_profile_json_text=lambda _text: profile,
        load_profile_yaml=lambda _path: profile,
        flatten_skills=lambda _profile: ["SQL"],
        apply_rule_filters=fake_apply_rule_filters,
    )

    assert len(captured_contexts) == 1
    assert captured_contexts[0]["language_inventory_status"] == "complete"
    assert state["passed_jobs"] == [
        {
            **enriched_job,
            "source_job_url": enriched_job["job_url"],
            "raw_job_fingerprint": "raw-1",
            "marks": [{"code": "legacy"}],
            **eligibility_payload,
        }
    ]
    assert stored[0]["passed_records"][0]["eligibility_policy_fingerprint"] == (
        "policy-fingerprint"
    )
