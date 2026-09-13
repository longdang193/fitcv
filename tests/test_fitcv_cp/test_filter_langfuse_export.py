"""
@meta
type: test
scope: unit
domain: observability
covers:
  - langfuse export analysis-ready filtering
excludes:
  - live Langfuse network calls
tags:
  - fast
  - ci-safe
"""

import json
import sys

import pytest

from scripts.filter_langfuse_export import _is_analysis_ready, main


def test_analysis_ready_accepts_rich_io_with_stringified_output() -> None:
    row = {
        "name": "layer4_cv_generation_result:rich_io",
        "input": None,
        "output": json.dumps({"stage_family": "cv_generation", "latency_ms": 1200}),
    }
    assert _is_analysis_ready(row) is True


def test_analysis_ready_rejects_unknown_stage_family_rich_io() -> None:
    row = {
        "name": "misc:rich_io",
        "input": None,
        "output": json.dumps({"stage_family": "misc"}),
    }
    assert _is_analysis_ready(row) is False


def test_analysis_ready_rejects_string_null_payloads() -> None:
    row = {
        "name": "some_event",
        "input": "null",
        "output": "null",
    }
    assert _is_analysis_ready(row) is False


def test_filter_rejects_same_input_and_output_paths(tmp_path, monkeypatch) -> None:
    source = tmp_path / "export.json"
    original = '[{"name": "event", "input": {}}]\n'
    source.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["filter_langfuse_export", "--input", str(source), "--output", str(source)],
    )

    with pytest.raises(SystemExit):
        main()

    assert source.read_text(encoding="utf-8") == original
