"""Tests for requirement-support arm comparison."""

import importlib.util
import json
from pathlib import Path

import pytest


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


def test_canonical_comparison_preserves_lexical_only_arm(tmp_path: Path) -> None:
    result = _comparison_module().run_inputs(
        [
            _payload(tmp_path, "production", 0.5),
            _payload(tmp_path, "full_pool_diagnostic", 0.75),
            _payload(tmp_path, "lexical_only", 0.25),
        ]
    )

    assert set(result["arms"]) == {"production", "full_pool_diagnostic", "lexical_only"}
    assert "reviewed held-out promotion readiness" in result["limitations"][1]


def test_legacy_comparison_preserves_supplied_lexical_arm(tmp_path: Path) -> None:
    result = _comparison_module().run_inputs([
        _payload(tmp_path, "current", 0.5),
        _payload(tmp_path, "full-pool", 0.75),
        _payload(tmp_path, "lexical_only", 0.25),
    ])
    assert set(result["arms"]) == {"current", "full-pool", "lexical_only"}


@pytest.mark.parametrize("fixture_hash", ["", "   "])
def test_comparison_rejects_all_blank_fixture_hashes(tmp_path: Path, fixture_hash: str) -> None:
    paths = [_payload(tmp_path, "production", 0.5), _payload(tmp_path, "full_pool_diagnostic", 0.75)]
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["fixture_sha256"] = fixture_hash
        path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="fixture SHA-256"):
        _comparison_module().run_inputs(paths)


def test_canonical_comparison_rejects_missing_selected_metric(tmp_path: Path) -> None:
    production = _payload(tmp_path, "production", 0.5)
    payload = json.loads(production.read_text(encoding="utf-8"))
    del payload["requirement_support"]["micro_coverage"]["requirement_recall"]
    production.write_text(json.dumps(payload), encoding="utf-8")

    try:
        _comparison_module().run_inputs(
            [production, _payload(tmp_path, "full_pool_diagnostic", 0.75)]
        )
    except ValueError as exc:
        assert "requirement_recall" in str(exc)
    else:
        raise AssertionError("missing selected metric must fail closed")


@pytest.mark.parametrize("recall", [True, False, float("nan"), float("inf"), -0.01, 1.01])
def test_current_comparison_rejects_invalid_recall(tmp_path: Path, recall: object) -> None:
    production = _payload(tmp_path, "production", 0.5)
    payload = json.loads(production.read_text(encoding="utf-8"))
    payload["requirement_support"]["micro_coverage"]["requirement_recall"]["selected"] = recall
    production.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")

    with pytest.raises(ValueError, match="requirement_recall"):
        _comparison_module().run_inputs(
            [production, _payload(tmp_path, "full_pool_diagnostic", 0.75)]
        )


@pytest.mark.parametrize("branch", [("production", "full_pool_diagnostic"), ("current", "full-pool")])
def test_current_comparison_rejects_missing_hash_and_incorrect_pairs(
    tmp_path: Path, branch: tuple[str, str]
) -> None:
    left, right = branch
    missing_hash = _payload(tmp_path, left, 0.5)
    payload = json.loads(missing_hash.read_text(encoding="utf-8"))
    payload["fixture_sha256"] = ""
    missing_hash.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="fixture SHA-256"):
        _comparison_module().run_inputs([missing_hash, _payload(tmp_path, right, 0.75)])

    missing_pairs = _payload(tmp_path, left, 0.5)
    payload = json.loads(missing_pairs.read_text(encoding="utf-8"))
    del payload["requirement_support"]["incorrect_pairs"]
    missing_pairs.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="incorrect_pairs"):
        _comparison_module().run_inputs([missing_pairs, _payload(tmp_path, right, 0.75)])


def test_comparison_rejects_missing_or_duplicate_arm_provenance(tmp_path: Path) -> None:
    module = _comparison_module()
    with_missing = _payload(tmp_path, "production", 0.5)
    payload = json.loads(with_missing.read_text(encoding="utf-8"))
    payload["arm"] = ""
    with_missing.write_text(json.dumps(payload), encoding="utf-8")
    try:
        module.run_inputs([with_missing, _payload(tmp_path, "full_pool_diagnostic", 0.75)])
    except ValueError as exc:
        assert "arm" in str(exc)
    else:
        raise AssertionError("missing arm provenance must fail closed")

    duplicate = _payload(tmp_path, "production", 0.75)
    try:
        module.run_inputs(
            [duplicate, _payload(tmp_path, "production", 0.5), _payload(tmp_path, "full_pool_diagnostic", 0.75)]
        )
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate arm provenance must fail closed")


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
