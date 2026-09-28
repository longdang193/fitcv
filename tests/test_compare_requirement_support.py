"""Tests for requirement-support arm comparison."""

import importlib.util
import json
from pathlib import Path


def _comparison_module():
    path = Path("scripts/compare_requirement_support.py")
    spec = importlib.util.spec_from_file_location("compare_requirement_support", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(tmp_path: Path, arm: str, recall: float) -> Path:
    path = tmp_path / f"{arm}.json"
    path.write_text(
        json.dumps(
            {
                "arm": arm,
                "fixture_sha256": "fixture",
                "scenario_set": ["one"],
                "evidence_budgets": [2],
                "requirement_support": {
                    "micro_coverage": {
                        "requirement_recall": {"selected": recall},
                        "evidence_pair_recall": {"selected": recall},
                    },
                    "incorrect_pairs": [],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_compare_current_and_full_pool_reports_qualified_support_gates(tmp_path: Path) -> None:
    result = _comparison_module().run_inputs(
        [_payload(tmp_path, "current", 0.5), _payload(tmp_path, "full-pool", 0.75)]
    )

    comparison = result["comparisons"]["current_vs_full_pool"]
    assert comparison["qualified_requirement_recall_non_decreasing"] is True
    assert comparison["qualified_evidence_pair_recall_non_decreasing"] is True
    assert comparison["false_qualified_pairs"] == 0


def test_compare_canonical_production_and_diagnostic_arms(tmp_path: Path) -> None:
    result = _comparison_module().run_inputs(
        [
            _payload(tmp_path, "production", 0.5),
            _payload(tmp_path, "full_pool_diagnostic", 0.75),
        ]
    )

    comparison = result["comparisons"]["production_vs_full_pool_diagnostic"]
    assert comparison["from"] == "production"
    assert comparison["to"] == "full_pool_diagnostic"
    assert comparison["qualified_requirement_recall_non_decreasing"] is True
