"""
@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.run_artifact_contracts run-mode normalization invariants
tags:
  - fast
  - ci-safe
"""

import json
import pytest

from fitcv_cp.run_artifact_contracts import (
    RUN_ATTEMPT_SCHEMA_VERSION,
    decode_json_object_or_none,
    decode_run_attempt_payload_or_none,
    normalized_run_mode,
    pretty_json_string,
    pretty_json_string_or_fallback,
    require_payload_keys,
    run_attempt_payload_v1,
    run_mode_label,
    schema_version_matches,
    schema_version_or_none,
    stable_sha256_fingerprint,
    build_accepted_cv_effort_projection,
    accepted_cv_artifact_event_v1 as _accepted_cv_artifact_event_v1,
    collect_normalized_generation_traces,
)


def accepted_cv_artifact_event_v1(**kwargs):
    kwargs.setdefault("page_fit_status", "pass")
    kwargs.setdefault("render_acceptance", {"page_count": 1, "page_fit_status": "pass"})
    return _accepted_cv_artifact_event_v1(**kwargs)


def test_normalized_run_mode_defaults_unknown_values_to_run_all() -> None:
    assert normalized_run_mode("run_all") == "run_all"
    assert normalized_run_mode("manual_staged") == "manual_staged"
    assert normalized_run_mode("unknown") == "run_all"
    assert normalized_run_mode(None) == "run_all"
    assert normalized_run_mode(123) == "run_all"


def test_run_mode_label_never_leaks_unknown_identifiers() -> None:
    assert run_mode_label("run_all") == "Run All"
    assert run_mode_label("manual_staged") == "Stage by Stage"
    assert run_mode_label("unknown") == "Run All"


def test_decode_json_object_or_none_returns_none_for_non_object_payloads() -> None:
    assert decode_json_object_or_none(None) is None
    assert decode_json_object_or_none("") is None
    assert decode_json_object_or_none(json.dumps(["x"])) is None
    assert decode_json_object_or_none("{") is None


def test_decode_json_object_or_none_parses_objects() -> None:
    assert decode_json_object_or_none(json.dumps({"a": 1})) == {"a": 1}


def test_schema_version_helpers() -> None:
    assert schema_version_or_none(None) is None
    assert schema_version_or_none({}) is None
    assert schema_version_or_none({"schema_version": ""}) is None
    assert schema_version_or_none({"schema_version": "v1"}) == "v1"
    assert schema_version_matches({"schema_version": "v1"}, "v1") is True
    assert schema_version_matches({"schema_version": "v2"}, "v1") is False


def test_pretty_json_string_formats_objects() -> None:
    rendered = pretty_json_string(json.dumps({"a": 1}))
    assert '"a": 1' in rendered

def test_pretty_json_string_or_fallback_handles_empty_and_invalid_payloads() -> None:
    assert pretty_json_string_or_fallback(None) == ""
    assert pretty_json_string_or_fallback("") == ""
    assert pretty_json_string_or_fallback("{") == "{"

def test_pretty_json_string_or_fallback_formats_valid_payloads() -> None:
    rendered = pretty_json_string_or_fallback(json.dumps({"a": 1}))
    assert '"a": 1' in rendered

def test_stable_sha256_fingerprint_is_deterministic_and_sorted() -> None:
    payload = {"b": 2, "a": 1}
    assert stable_sha256_fingerprint(payload) == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"

def test_require_payload_keys_raises_on_missing_keys() -> None:
    with pytest.raises(ValueError) as excinfo:
        require_payload_keys(
            {"run_id": "r1"},
            required_keys={"run_id", "created_at"},
            context="unit_test",
        )
    assert "missing_required_payload_keys:unit_test:created_at" in str(excinfo.value)


def test_run_attempt_payload_v1_encodes_schema_version() -> None:
    payload = run_attempt_payload_v1(attempt_id="a1", status="running")
    assert payload["schema_version"] == RUN_ATTEMPT_SCHEMA_VERSION


def test_decode_run_attempt_payload_or_none_rejects_non_matching_payloads() -> None:
    assert decode_run_attempt_payload_or_none(None) is None
    assert decode_run_attempt_payload_or_none("{") is None
    assert decode_run_attempt_payload_or_none(json.dumps({"schema_version": "other"})) is None


def test_decode_run_attempt_payload_or_none_accepts_minimal_valid_payload() -> None:
    raw = json.dumps(run_attempt_payload_v1(attempt_id="a1", status="running"))
    decoded = decode_run_attempt_payload_or_none(raw)
    assert isinstance(decoded, dict)
    assert decoded["attempt"]["attempt_id"] == "a1"


def test_accepted_cv_effort_projection_is_not_run_without_finalized_artifact() -> None:
    result = build_accepted_cv_effort_projection([], [{"action": "regenerate_once"}])

    assert result["status"] == "not_run"
    assert result["denominator"] == {"accepted_cv_count": 0}


def test_accepted_cv_effort_projection_measures_zero_acceptance_workload() -> None:
    result = build_accepted_cv_effort_projection(
        [],
        [],
        generation_trace_records=[
            {
                "scope_key": "job-1",
                "status": "validation_failed",
                "attempts": [{"attempt_index": 1, "provider_status": "error"}],
                "validation_summary": {"final_valid": False},
                "efficiency_summary": {
                    "provider_call_count": 1,
                    "token_usage": [{"total_tokens": 12}],
                },
            }
        ],
    )

    assert result["status"] == "measured"
    assert result["denominator"] == {"accepted_cv_count": 0}
    assert result["aggregate"]["workload"] == {
        "attempted_generation_job_count": 1,
        "terminal_validation_failed_job_count": 1,
        "validation_failure_count": 1,
        "provider_call_count": 1,
        "regeneration_count": 0,
        "render_retry_count": 0,
        "token_total": 12,
    }


def test_accepted_cv_effort_projection_keeps_same_job_lineage_distinct() -> None:
    traces = [
        {
            "scope_key": "job-1",
            "run_id": "run-1",
            "artifact_id": "cv-1",
            "generation_input_fingerprint": "input-1",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 1},
        },
        {
            "scope_key": "job-1",
            "run_id": "run-2",
            "artifact_id": "cv-2",
            "generation_input_fingerprint": "input-2",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 3},
        },
    ]
    artifacts = [
        accepted_cv_artifact_event_v1(
            artifact_id="cv-1",
            job_url="job-1",
            run_id="run-1",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
            generation_input_fingerprint="input-1",
        ),
        accepted_cv_artifact_event_v1(
            artifact_id="cv-2",
            job_url="job-1",
            run_id="run-2",
            acceptance_mode="human_confirmed",
            accepted_at="2026-10-02T00:02:00Z",
            finalized_at="2026-10-02T00:02:00Z",
            generation_input_fingerprint="input-2",
        ),
    ]

    result = build_accepted_cv_effort_projection([], [], artifacts, generation_trace_records=traces)

    by_artifact = {row["artifact_version_id"]: row for row in result["records"]}
    assert by_artifact["cv-1"]["provider_call_count"] == 1
    assert by_artifact["cv-2"]["provider_call_count"] == 3


def test_accepted_cv_effort_projection_deduplicates_top_level_and_embedded_trace() -> None:
    trace = {
        "scope_key": "job-1",
        "run_id": "run-1",
        "trace_id": "trace-1",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {"provider_call_count": 1},
    }
    result = build_accepted_cv_effort_projection(
        [{"job_url": "job-1", "run_id": "run-1", "cv_generation_trace": trace}],
        [],
        [
            accepted_cv_artifact_event_v1(
                artifact_id="cv-1",
                job_url="job-1",
                run_id="run-1",
                trace_id="trace-1",
                acceptance_mode="automatic",
                accepted_at="2026-10-02T00:01:00Z",
                finalized_at="2026-10-02T00:01:00Z",
            )
        ],
        generation_trace_records=[trace],
    )

    assert result["aggregate"]["workload"]["attempted_generation_job_count"] == 1


def test_collect_normalized_generation_traces_merges_embedded_and_top_level_once() -> None:
    trace = {
        "trace_id": "trace-1",
        "run_id": "run-1",
        "scope_key": "job-1",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
    }

    result = collect_normalized_generation_traces(
        [{"run_id": "run-1", "cv_generation_trace": trace}],
        [trace],
    )

    assert len(result["records"]) == 1
    assert result["diagnostics"] == {
        "duplicate_count": 1,
        "conflict_count": 0,
        "conflict_trace_ids": [],
        "source_candidate_count": 2,
        "normalized_trace_count": 1,
    }


def test_collect_normalized_generation_traces_merges_enriched_top_level_duplicate() -> None:
    embedded = {
        "trace_id": "trace-enriched-duplicate",
        "run_id": "run-1",
        "scope_key": "job-1",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {"elapsed_ms": 100},
        "output_summary": {"final_status": "accepted"},
    }
    top_level = {
        **embedded,
        "record_id": "job-1",
        "status": "accepted",
        "artifact_refs": {"stage_artifact": "cv_generation.json"},
    }

    result = collect_normalized_generation_traces(
        [{"run_id": "run-1", "cv_generation_trace": embedded}],
        [top_level],
    )

    assert len(result["records"]) == 1
    assert result["records"][0]["status"] == "accepted"
    assert result["records"][0]["artifact_refs"] == {"stage_artifact": "cv_generation.json"}
    assert result["diagnostics"] == {
        "duplicate_count": 1,
        "conflict_count": 0,
        "conflict_trace_ids": [],
        "source_candidate_count": 2,
        "normalized_trace_count": 1,
    }


def test_collect_normalized_generation_traces_excludes_conflicting_identity() -> None:
    first = {"trace_id": "trace-1", "run_id": "run-1", "scope_key": "job-1"}
    second = {"trace_id": "trace-1", "run_id": "run-1", "scope_key": "job-1", "status": "failed"}

    result = collect_normalized_generation_traces([], [first, second])

    assert result["records"] == []
    assert result["diagnostics"] == {
        "duplicate_count": 0,
        "conflict_count": 1,
        "conflict_trace_ids": ["trace-1"],
        "source_candidate_count": 2,
        "normalized_trace_count": 0,
    }


def test_accepted_cv_artifact_event_preserves_trace_id() -> None:
    event = accepted_cv_artifact_event_v1(
        artifact_id="cv-1",
        job_url="job-1",
        run_id="run-1",
        trace_id="trace-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        render_acceptance={
            "render_status": "pass",
            "renderer_status": "rendered",
            "page_count": 1,
            "page_fit_status": "pass",
            "artifact_checksum": "a" * 64,
            "content_sha256": "b" * 64,
            "template_sha256": "c" * 64,
            "render_config_fingerprint": "d" * 64,
            "renderer_contract_version": "fitcv_native_render_v1",
        },
    )

    assert event["trace_id"] == "trace-1"
    assert event["final_artifact_contract_version"] == "fitcv.final_artifact.v1"
    assert event["event_id"]


def test_accepted_cv_artifact_event_preserves_render_acceptance() -> None:
    event = accepted_cv_artifact_event_v1(
        artifact_id="cv-rendered",
        job_url="job-rendered",
        run_id="run-rendered",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        page_fit_status="pass",
        render_acceptance={"page_count": 1, "page_fit_status": "pass"},
    )

    assert event["page_fit_status"] == "pass"
    assert event["render_acceptance"] == {"page_count": 1, "page_fit_status": "pass"}
    assert event["render_proof_status"] == "incomplete"


def test_accepted_cv_effort_projection_does_not_use_content_plan_page_fit() -> None:
    record = {
        "job_url": "job-unverified-page-fit",
        "run_id": "run-unverified-page-fit",
        "cv_generation_trace": {
            "cv_content_plan": {"space_budget": {"page_fit_status": "one_page"}},
            "efficiency_summary": {"provider_call_count": 1},
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-unverified-page-fit",
        job_url="job-unverified-page-fit",
        run_id="run-unverified-page-fit",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        render_acceptance={"page_count": 1, "page_fit_status": "pass"},
    )

    result = build_accepted_cv_effort_projection([record], [], [artifact])

    row = result["records"][0]
    assert row["page_fit_status"] == "not_recorded"
    assert row["page_fit_verified"] is False
    assert result["aggregate"]["page_fit_coverage"] == {"verified": 0, "eligible": 1}


def test_accepted_cv_effort_projection_counts_only_verified_render_proof() -> None:
    proof = {
        "render_status": "pass",
        "page_count": 1,
        "page_fit_status": "pass",
        "artifact_checksum": "a" * 64,
        "content_sha256": "b" * 64,
        "template_sha256": "c" * 64,
        "render_config_fingerprint": "d" * 64,
        "renderer_contract_version": "fitcv_native_render_v1",
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-verified-page-fit",
        job_url="job-verified-page-fit",
        run_id="run-verified-page-fit",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        page_fit_status="pass",
        render_acceptance=proof,
    )

    result = build_accepted_cv_effort_projection(
        [],
        [],
        [artifact],
        generation_trace_records=[
            {
                "run_id": "run-verified-page-fit",
                "job_url": "job-verified-page-fit",
                "efficiency_summary": {"provider_call_count": 1},
            }
        ],
    )

    assert artifact["render_proof_status"] == "verified"
    assert result["records"][0]["page_fit_verified"] is True
    assert result["aggregate"]["page_fit_coverage"] == {"verified": 1, "eligible": 1}
    assert result["aggregate"]["page_fit_success"] == {"verified_one_page": 1}


def test_accepted_cv_artifact_event_rejects_non_one_page_render() -> None:
    with pytest.raises(ValueError, match="final artifact acceptance"):
        accepted_cv_artifact_event_v1(
            artifact_id="cv-two-page",
            job_url="job-two-page",
            run_id="run-two-page",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
            page_fit_status="fail",
            render_acceptance={"page_count": 2, "page_fit_status": "fail"},
        )


def test_accepted_cv_artifact_event_requires_native_render_proof() -> None:
    with pytest.raises(ValueError, match="render proof required"):
        _accepted_cv_artifact_event_v1(
            artifact_id="cv-unproven",
            job_url="job-unproven",
            run_id="run-unproven",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
            page_fit_status="pass",
        )


def test_accepted_cv_effort_projection_marks_ambiguous_legacy_trace_unmatched() -> None:
    traces = [
        {
            "run_id": "run-1",
            "job_url": "same-url",
            "efficiency_summary": {"provider_call_count": 2},
        },
        {
            "run_id": "run-1",
            "job_url": "same-url",
            "efficiency_summary": {"provider_call_count": 3},
        },
    ]
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-ambiguous",
        job_url="same-url",
        run_id="run-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    result = build_accepted_cv_effort_projection([], [], [artifact], generation_trace_records=traces)

    row = result["records"][0]
    assert row["attribution_status"] == "ambiguous"
    assert row["provider_call_count"] is None
    assert result["aggregate"]["workload"]["provider_call_count"] == 5
    assert result["unmatched_trace_count"] == 1
    assert result["unattributed_accepted_artifact_count"] == 1


def test_accepted_cv_effort_projection_requires_job_identity_within_run() -> None:
    traces = [
        {
            "run_id": "run-1",
            "run_job_id": "job-1",
            "job_url": "same-url",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 1},
        },
        {
            "run_id": "run-1",
            "run_job_id": "job-2",
            "job_url": "same-url",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 3},
        },
    ]
    artifacts = [
        accepted_cv_artifact_event_v1(
            artifact_id="cv-1",
            job_url="same-url",
            run_id="run-1",
            run_job_id="job-1",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
        ),
        accepted_cv_artifact_event_v1(
            artifact_id="cv-2",
            job_url="same-url",
            run_id="run-1",
            run_job_id="job-2",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:02:00Z",
            finalized_at="2026-10-02T00:02:00Z",
        ),
    ]

    result = build_accepted_cv_effort_projection([], [], artifacts, generation_trace_records=traces)
    by_artifact = {row["artifact_version_id"]: row for row in result["records"]}

    assert by_artifact["cv-1"]["provider_call_count"] == 1
    assert by_artifact["cv-2"]["provider_call_count"] == 3


def test_accepted_cv_effort_projection_rejects_conflicting_shared_legacy_identity() -> None:
    trace = {
        "run_id": "run-1",
        "run_job_id": "job-1",
        "generation_input_fingerprint": "old-input",
        "job_url": "same-url",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {"provider_call_count": 7},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-conflict",
        job_url="same-url",
        run_id="run-1",
        run_job_id="job-1",
        generation_input_fingerprint="new-input",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    result = build_accepted_cv_effort_projection(
        [], [], [artifact], generation_trace_records=[trace]
    )

    row = result["records"][0]
    assert row["attribution_status"] == "conflict"
    assert row["provider_call_count"] is None
    assert row["attempt_count"] is None
    assert result["unmatched_trace_count"] == 1
    assert result["unattributed_accepted_artifact_count"] == 1


def test_accepted_cv_effort_projection_does_not_fallback_across_run_or_job() -> None:
    trace = {
        "run_id": "run-2",
        "run_job_id": "job-2",
        "job_url": "same-url",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {"provider_call_count": 99},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-1",
        job_url="same-url",
        run_id="run-1",
        run_job_id="job-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    result = build_accepted_cv_effort_projection(
        [], [], [artifact], generation_trace_records=[trace]
    )

    assert result["records"][0]["provider_call_count"] is None
    assert result["records"][0]["attribution_status"] == "unmatched"
    assert result["unattributed_accepted_artifact_count"] == 1
    assert result["records"][0]["attempt_count"] is None


def test_accepted_cv_effort_projection_deduplicates_replayed_action() -> None:
    record = {
        "job_url": "job-1",
        "run_id": "run-1",
        "cv_generation_trace": {
            "efficiency_summary": {
                "provider_call_count": 2,
                "regeneration_count": 1,
                "review_question_count": 1,
                "token_usage_status": "not_run",
            }
        },
    }
    action = {
        "job_url": "job-1",
        "run_id": "run-1",
        "action": "approve_as_is",
        "created_at": "2026-09-29T00:00:00Z",
        "artifact_finalized": True,
        "artifact_version_id": "cv-v1",
    }

    result = build_accepted_cv_effort_projection([record], [action, dict(action)])

    assert result["status"] == "measured"
    assert result["denominator"] == {"accepted_cv_count": 1}
    assert result["records"][0]["provider_call_count"] == 2
    assert result["records"][0]["human_action_count"] == 1
    assert result["records"][0]["reused_resolution_count"] == 0
    assert result["records"][0]["page_fit_status"] == "not_recorded"
    assert result["records"][0]["accepted_outcome"] is True
    assert result["records"][0]["elapsed_status"] == "not_run"


def test_accepted_cv_effort_projection_prefers_finalized_page_fit_over_plan_default() -> None:
    record = {
        "job_url": "job-page-fit",
        "run_id": "run-page-fit",
        "cv_generation_trace": {
            "output_summary": {"page_fit_status": "one_page"},
            "cv_content_plan": {"space_budget": {"page_fit_status": "unverified"}},
            "efficiency_summary": {"provider_call_count": 1},
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-page-fit",
        job_url="job-page-fit",
        run_id="run-page-fit",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        render_acceptance={
            "render_status": "pass",
            "renderer_status": "rendered",
            "page_count": 1,
            "page_fit_status": "pass",
            "artifact_checksum": "a" * 64,
            "content_sha256": "b" * 64,
            "template_sha256": "c" * 64,
            "render_config_fingerprint": "d" * 64,
            "renderer_contract_version": "fitcv_native_render_v1",
        },
    )

    result = build_accepted_cv_effort_projection([record], [], [artifact])

    assert result["records"][0]["page_fit_status"] == "pass"


def test_accepted_cv_effort_projection_prefers_artifact_render_acceptance() -> None:
    trace = {
        "job_url": "job-page-fit-artifact",
        "run_id": "run-page-fit-artifact",
        "cv_content_plan": {"space_budget": {"page_fit_status": "unverified"}},
        "efficiency_summary": {"provider_call_count": 1},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-page-fit-artifact",
        job_url="job-page-fit-artifact",
        run_id="run-page-fit-artifact",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
        page_fit_status="pass",
        render_acceptance={
            "render_status": "pass",
            "renderer_status": "rendered",
            "page_count": 1,
            "page_fit_status": "pass",
            "artifact_checksum": "a" * 64,
            "content_sha256": "b" * 64,
            "template_sha256": "c" * 64,
            "render_config_fingerprint": "d" * 64,
            "renderer_contract_version": "fitcv_native_render_v1",
        },
    )

    result = build_accepted_cv_effort_projection([], [], [artifact], generation_trace_records=[trace])

    assert result["records"][0]["page_fit_status"] == "pass"


def test_accepted_cv_effort_projection_measures_existing_run_to_artifact_timestamps() -> None:
    record = {
        "job_url": "job-1",
        "run_id": "run-1",
        "started_at": "2026-09-29T00:00:00Z",
        "cv_generation_trace": {"efficiency_summary": {"provider_call_count": 1}},
    }
    action = {
        "job_url": "job-1",
        "run_id": "run-1",
        "action": "approve_as_is",
        "created_at": "2026-09-29T00:00:01Z",
        "artifact_finalized": True,
        "artifact_version_id": "cv-v1",
    }

    result = build_accepted_cv_effort_projection([record], [action])

    assert result["status"] == "measured"
    assert result["records"][0]["elapsed_ms"] == 1000.0
    assert result["records"][0]["elapsed_status"] == "measured"


def test_accepted_cv_effort_projection_uses_idempotent_automatic_and_hitl_events() -> None:
    records = [
        {
            "job_url": "job-auto",
            "run_started_at": "2026-10-02T00:00:00Z",
            "cv_generation_trace": {"efficiency_summary": {"provider_call_count": 2}},
        },
        {
            "job_url": "job-hitl",
            "run_started_at": "2026-10-02T00:00:00Z",
            "cv_generation_trace": {"efficiency_summary": {"provider_call_count": 1}},
        },
    ]
    automatic = accepted_cv_artifact_event_v1(
        artifact_id="cv-auto",
        job_url="job-auto",
        run_id="run-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )
    human = accepted_cv_artifact_event_v1(
        artifact_id="cv-hitl",
        job_url="job-hitl",
        run_id="run-1",
        acceptance_mode="human_confirmed",
        accepted_at="2026-10-02T00:02:00Z",
        finalized_at="2026-10-02T00:02:00Z",
    )

    result = build_accepted_cv_effort_projection(
        records,
        [],
        [automatic, dict(automatic), human],
    )

    assert result["denominator"] == {"accepted_cv_count": 2}
    assert {row["acceptance_mode"] for row in result["records"]} == {"automatic", "human_confirmed"}
    assert {row["artifact_version_id"] for row in result["records"]} == {"cv-auto", "cv-hitl"}


def test_accepted_cv_effort_projection_keeps_all_attempts_and_failure_taxonomy() -> None:
    record = {
        "job_url": "job-1",
        "run_id": "run-1",
        "cv_generation_trace": {
            "attempts": [
                {"attempt_index": 1, "attempt_type": "initial_generation", "provider_status": "accepted"},
                {"attempt_index": 2, "attempt_type": "repair_retry", "provider_status": "accepted"},
                {"attempt_index": 3, "attempt_type": "repair_retry", "provider_status": "error", "error_stage": "provider_timeout"},
            ],
            "validation_summary": {"initial_valid": False, "final_valid": True},
            "efficiency_summary": {
                "provider_call_count": 3,
                "regeneration_count": 2,
                "review_question_count": 2,
                "render_retry_count": 1,
                "token_usage": [{"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}],
                "elapsed_ms": 123,
            },
        },
    }
    event = accepted_cv_artifact_event_v1(
        artifact_id="cv-1",
        job_url="job-1",
        run_id="run-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    result = build_accepted_cv_effort_projection([record], [], [event])
    row = result["records"][0]

    assert row["attempt_count"] == 3
    assert row["provider_call_count"] == 3
    assert row["validation_failure_count"] == 1
    assert row["render_retry_count"] == 1
    assert row["token_total"] == 15
    assert row["failure_category_counts"] == {"provider_failure": 1}
    assert result["aggregate"]["attempt_count"] == 3


def test_accepted_cv_effort_projection_preserves_workload_attempt_baseline() -> None:
    trace_records = []
    accepted_artifacts = []
    for index in range(17):
        accepted = index < 11
        regeneration_count = 1 if index < 9 else 0
        trace_records.append(
            {
                "scope_key": f"job-{index}",
                "status": "accepted" if accepted else "validation_failed",
                "output_summary": {"final_status": "accepted" if accepted else "validation_failed"},
                "validation_summary": {"final_valid": accepted},
                "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
                "efficiency_summary": {
                    "provider_call_count": 1,
                    "regeneration_count": regeneration_count,
                    "token_usage": [{"total_tokens": 10}],
                },
            }
        )
        if accepted:
            accepted_artifacts.append(
                accepted_cv_artifact_event_v1(
                    artifact_id=f"cv-{index}",
                    job_url=f"job-{index}",
                    run_id="run-1",
                    acceptance_mode="automatic",
                    accepted_at="2026-10-02T00:01:00Z",
                    finalized_at="2026-10-02T00:01:00Z",
                )
            )

    result = build_accepted_cv_effort_projection(
        [],
        [],
        accepted_artifacts,
        generation_trace_records=trace_records,
    )

    assert result["denominator"] == {"accepted_cv_count": 11}
    assert result["aggregate"]["workload"] == {
        "attempted_generation_job_count": 17,
        "terminal_validation_failed_job_count": 6,
        "validation_failure_count": 6,
        "provider_call_count": 17,
        "regeneration_count": 9,
        "render_retry_count": 0,
        "token_total": 170,
    }

def test_run_attempt_payload_v1_truncates_error_details_when_over_cap() -> None:
    payload = run_attempt_payload_v1(
        attempt_id="a1",
        status="failed",
        error_classification="transient",
        error_summary="timeout",
        error_details={"blob": "x" * 5000},
        error_details_max_chars=200,
    )
    details = payload["attempt"]["error"]["details"]
    assert isinstance(details, dict)
    assert details.get("truncated") is True
    assert details.get("max_chars") == 200
