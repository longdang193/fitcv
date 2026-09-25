from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "benchmark_requirement_support.py"
COMPARE_PATH = REPO_ROOT / "scripts" / "compare_requirement_support.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "requirement_support_benchmark.json"


def _benchmark_module() -> Any:
    spec = importlib.util.spec_from_file_location("benchmark_requirement_support", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _comparison_module() -> Any:
    spec = importlib.util.spec_from_file_location("compare_requirement_support", COMPARE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_contains_positive_and_negative_grounding_cases() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert fixture["evaluation_schema_version"] == 1
    assert len(fixture["scenarios"]) == 16
    assert len({scenario["scenario_id"] for scenario in fixture["scenarios"]}) == 16
    assert set(fixture["expected_support"]) == {
        "required_skill:sql",
        "required_skill:python",
        "required_skill:kubernetes",
        "required_skill:power bi",
    }
    assert {case["name"] for case in fixture["negative_cases"]} == {
        "wrong_evidence_id",
        "canonical_synonym",
        "unsupported_structured_skill",
        "responsibility_only",
    }


def test_support_metrics_separate_retrieval_and_selection_loss() -> None:
    module = _benchmark_module()
    metrics = module._support_metrics(
        {
            "requirement_support": {
                "canonical": {"required_skill:sql": ["ev-1", "ev-2"]},
                "pool": {"required_skill:sql": ["ev-1"]},
                "selected": {"required_skill:sql": []},
            },
            "selected_evidence_ids": [],
        },
        {"required_skill:sql": ["ev-1", "ev-2"]},
    )

    assert metrics["canonical_to_retrieved_loss"]["required_skill:sql"] == ["ev-2"]
    assert metrics["retrieved_to_selected_loss"]["required_skill:sql"] == ["ev-1"]
    assert metrics["canonical_to_retrieved_loss"]["required_skill:sql"] == ["ev-2"]
    assert metrics["direct_support_opportunities"]["required_skill:sql"] == []
    assert metrics["requirement_recall"]["retrieved"] == 1.0
    assert metrics["requirement_recall"]["selected"] == 0.0
    assert metrics["evidence_pair_recall"]["retrieved"] == 0.5


def test_support_metrics_include_unexpected_requirement_ids() -> None:
    module = _benchmark_module()
    metrics = module._support_metrics(
        {
            "requirement_support": {
                "canonical": {"required_skill:sql": ["ev-1"]},
                "pool": {"required_skill:sql": ["ev-1"]},
                "selected": {
                    "required_skill:sql": ["ev-1"],
                    "required_skill:unexpected": ["ev-x"],
                },
            },
            "selected_evidence_ids": ["ev-1", "ev-x"],
        },
        {"required_skill:sql": ["ev-1"]},
    )

    assert metrics["incorrect_pairs"] == [["required_skill:unexpected", "ev-x"]]
    assert metrics["missed_pairs"] == []
    assert metrics["assignment_precision"] == 0.5


def test_validation_uses_production_requirement_coverage_contract() -> None:
    module = _benchmark_module()
    evidence = module._item("ev-sql", ["SQL"], "SQL reporting")
    result, _ = module._run_validation(
        {
            "validation": {
                "config": {"required_cv_sections": ["Skills"]},
                "cv_text": "## Skills\nSQL\n",
            }
        },
        {"skills": [{"name": "SQL"}], "experiences": [], "projects": []},
        {
            "selected_evidence": [evidence],
            "selected_evidence_ids": ["ev-sql"],
            "evidence_selection_summary": {"selected_evidence_ids": ["ev-sql"]},
        },
        requirement_coverage=[
            {
                "canonical_skill": "sql",
                "selected_support": "verified",
                "supporting_evidence_ids": ["ev-sql"],
            }
        ],
    )

    assert result["grounding_violations"] == []


def test_lexical_pool_eight_recovers_pool_four_support_loss() -> None:
    module = _benchmark_module()
    pool_four = module.run_benchmark(arm="lexical", pool_size=4, fixture_path=FIXTURE_PATH)
    pool_eight = module.run_benchmark(arm="lexical", pool_size=8, fixture_path=FIXTURE_PATH)

    assert pool_four["requirement_support"]["direct_support_opportunities"]["required_skill:sql"] == []
    assert pool_eight["requirement_support"]["evidence_pair_recall"]["retrieved"] > pool_four["requirement_support"]["evidence_pair_recall"]["retrieved"]
    assert pool_eight["backend"]["backend_id"] == "disabled"


def test_benchmark_reports_generation_prompt_build_timing() -> None:
    module = _benchmark_module()
    result = module.run_benchmark(
        arm="lexical",
        pool_size=4,
        fixture_path=FIXTURE_PATH,
        runs=1,
        warmups=0,
    )

    assert "generation_prompt_build_ms" in result["timing_ms"]
    assert "prompt_ms" not in result["timing_ms"]


def test_benchmark_validation_matrix_has_no_declared_misses() -> None:
    module = _benchmark_module()
    result = module.run_benchmark(
        arm="lexical",
        pool_size=4,
        fixture_path=FIXTURE_PATH,
        runs=1,
        warmups=0,
    )

    assert result["validation"]["passed_cases"] == result["validation"]["case_count"]


def test_comparison_rejects_mismatched_fixture_fingerprints(tmp_path: Path) -> None:
    module = _comparison_module()
    baseline = {
        "fixture_sha256": "one",
        "top_k": 2,
        "selected_metrics": {"requirement_recall": 1.0, "evidence_pair_recall": 1.0},
    }
    current = {
        "fixture_sha256": "two",
        "top_k": 2,
        "requirement_support": {},
    }
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    try:
        module.run(baseline_path, current_path, [])
    except ValueError as exc:
        assert "fixture SHA-256" in str(exc)
    else:
        raise AssertionError("fixture mismatch must fail closed")
