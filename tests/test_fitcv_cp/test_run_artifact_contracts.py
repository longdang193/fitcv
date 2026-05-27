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
)


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
