from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "compare_rag_impact.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("compare_rag_impact", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report() -> dict[str, Any]:
    return {
        "evaluation_schema_version": 2,
        "fixture_sha256": "fixture",
        "rubric_fingerprint": "rubric",
        "config_fingerprint": "config",
        "pair_count": 2,
        "metrics": {
            "by_variant": {
                "baseline": {
                    "requirement_coverage": 0.9,
                    "reviewed_factual_precision": 0.95,
                    "human_quality_score": 4.0,
                    "generation_input_tokens": 100,
                    "latency_ms": 20,
                },
                "fitcv": {
                    "requirement_coverage": 0.9,
                    "reviewed_factual_precision": 0.96,
                    "human_quality_score": 4.1,
                    "generation_input_tokens": 70,
                    "latency_ms": 18,
                },
            },
            "fitcv_minus_baseline": {
                "requirement_coverage": 0.0,
                "reviewed_factual_precision": 0.01,
                "human_quality_score": 0.1,
                "generation_input_tokens": -30,
                "latency_ms": -2,
            },
            "confidence_intervals": {
                "requirement_coverage": {
                    "point": 0.0,
                    "lower": 0.0,
                    "upper": 0.0,
                    "sample_count": 2,
                }
            },
            "context": {"fitcv_input_tokens_lower_fraction": 1.0},
        },
        "thresholds": {
            "max_mean_qualification_coverage_loss": 0.05,
            "max_mean_reviewed_factual_precision_loss": 0.02,
            "human_quality_loss_points": 0.25,
            "rag_generation_input_tokens_lower_in_fraction": 0.8,
        },
        "pair_results": [],
    }


def test_compare_emits_gates_deltas_intervals_and_limitations() -> None:
    module = _module()

    result = module.compare_report(_report())

    assert result["arm_metrics"]["fitcv"]["generation_input_tokens"] == 70
    assert result["deltas"]["generation_input_tokens"] == -30
    assert result["confidence_intervals"]["requirement_coverage"]["sample_count"] == 2
    assert result["gates"]["quality_parity"]["status"] == "pass"
    assert result["gates"]["context_reduction"]["status"] == "pass"
    assert result["limitations"]


def test_compare_rejects_incompatible_fingerprints() -> None:
    module = _module()
    report = _report()
    report["fixture_sha256"] = "other"

    with pytest.raises(ValueError, match="fixture"):
        module.compare_reports([_report(), report])
