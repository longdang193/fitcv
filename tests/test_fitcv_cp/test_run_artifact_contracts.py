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
    accepted_cv_artifact_event_v1,
    build_final_cv_evidence_envelope,
)


def test_build_final_cv_evidence_envelope_requires_bound_native_one_page_proof() -> None:
    missing = build_final_cv_evidence_envelope(
        artifact_version_id="cv-1",
        run_job_id="job-1",
        run_id="run-1",
        content_checksum="sha-1",
        generation={},
    )
    assert missing["evidence_state"] == "missing"
    assert "native_one_page_render_unverified" in missing["warnings"]

    passed = build_final_cv_evidence_envelope(
        artifact_version_id="cv-1",
        run_job_id="job-1",
        run_id="run-1",
        content_checksum="a" * 64,
        generation={
            "render_proof": {
                "page_count": 1,
                "page_fit_status": "pass",
                "render_acceptance": "passed",
                "content_sha256": "a" * 64,
            }
        },
    )
    assert passed["evidence_state"] == "passed"
    assert passed["warnings"] == []


def test_build_final_cv_evidence_envelope_accepts_generation_render_acceptance() -> None:
    envelope = build_final_cv_evidence_envelope(
        artifact_version_id="cv-2",
        run_job_id="job-2",
        run_id="run-2",
        content_checksum="b" * 64,
        generation={
            "page_fit_status": "pass",
            "render_acceptance": {
                "render_status": "pass",
                "page_count": 1,
                "page_fit_status": "pass",
                "content_sha256": "b" * 64,
            },
        },
    )

    assert envelope["evidence_state"] == "passed"
    assert envelope["page_count"] == 1


def test_build_final_cv_evidence_envelope_rejects_mismatched_render_identity() -> None:
    envelope = build_final_cv_evidence_envelope(
        artifact_version_id="cv-3",
        run_job_id="job-3",
        run_id="run-3",
        content_checksum="c" * 64,
        generation={
            "render_proof": {
                "artifact_version_id": "cv-wrong",
                "run_job_id": "job-wrong",
                "content_sha256": "d" * 64,
                "page_count": 1,
                "page_fit_status": "pass",
                "render_acceptance": "passed",
            }
        },
    )

    assert envelope["evidence_state"] == "missing"
    assert "native_one_page_render_unverified" in envelope["warnings"]


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


def test_accepted_cv_effort_projection_deduplicates_replayed_action() -> None:
    record = {
        "job_url": "job-1",
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


def test_accepted_cv_effort_projection_measures_existing_run_to_artifact_timestamps() -> None:
    record = {
        "job_url": "job-1",
        "started_at": "2026-09-29T00:00:00Z",
        "cv_generation_trace": {"efficiency_summary": {"provider_call_count": 1}},
    }
    action = {
        "job_url": "job-1",
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
