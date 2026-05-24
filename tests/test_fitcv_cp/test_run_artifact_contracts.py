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

from fitcv_cp.run_artifact_contracts import (
    decode_json_object_or_none,
    normalized_run_mode,
    pretty_json_string,
    pretty_json_string_or_fallback,
    run_mode_label,
    schema_version_matches,
    schema_version_or_none,
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
