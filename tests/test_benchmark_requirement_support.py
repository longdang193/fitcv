from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


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


def test_scenarios_resolve_independent_inputs_without_shared_fallback() -> None:
    module = _benchmark_module()
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    resolved = module._resolve_scenarios(fixture)

    assert len(resolved) == len(fixture["scenarios"])
    assert len({json.dumps(item["profile"], sort_keys=True) for item in resolved}) == len(resolved)
    assert len({json.dumps(item["job_context"], sort_keys=True) for item in resolved}) == len(resolved)
    assert len({scenario["expected_support_ref"] for scenario in fixture["scenarios"]}) == len(resolved)
    resolved[0]["job_context"]["title"] = "mutated"
    assert resolved[1]["job_context"]["title"] != "mutated"


def test_fixture_validation_rejects_missing_scenario_reference() -> None:
    module = _benchmark_module()
    fixture = {
        "evaluation_schema_version": 1,
        "scenarios": [
            {
                "scenario_id": "case",
                "purpose": "case",
                "profile_ref": "missing",
                "job_context_ref": "job",
                "expected_support_ref": "support",
                "validation_case_ids": ["validation"],
            }
        ],
        "profiles": {},
        "job_contexts": {"job": {}},
        "expected_support_maps": {"support": {}},
        "validation_cases": [
            {"case_id": "validation", "expected_valid": True, "expected_violation_class": "none"}
        ],
    }

    try:
        module._validate_fixture(fixture)
    except ValueError as exc:
        assert "profile_ref" in str(exc)
    else:
        raise AssertionError("missing scenario reference must fail closed")


def test_fixture_validation_rejects_shared_scenario_inputs() -> None:
    module = _benchmark_module()
    fixture = {
        "evaluation_schema_version": 1,
        "scenarios": [
            {
                "scenario_id": "one",
                "purpose": "one",
                "profile_ref": "profile",
                "job_context_ref": "job-one",
                "expected_support_ref": "support-one",
                "validation_case_ids": ["validation"],
            },
            {
                "scenario_id": "two",
                "purpose": "two",
                "profile_ref": "profile",
                "job_context_ref": "job-two",
                "expected_support_ref": "support-two",
                "validation_case_ids": ["validation"],
            },
        ],
        "profiles": {"profile": {}},
        "job_contexts": {"job-one": {}, "job-two": {}},
        "expected_support_maps": {"support-one": {}, "support-two": {}},
        "validation_cases": [
            {"case_id": "validation", "expected_valid": True, "expected_violation_class": "none"}
        ],
    }

    with pytest.raises(ValueError, match="profile_ref values must be unique"):
        module._validate_fixture(fixture)


def test_benchmark_executes_each_scenario_once_per_run() -> None:
    module = _benchmark_module()
    result = module.run_benchmark(
        arm="lexical-requirement-aware",
        fixture_path=FIXTURE_PATH,
        runs=1,
        warmups=0,
    )

    assert result["scenario_count"] == len(json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"])
    assert len(result["scenarios"]) == result["scenario_count"]
    assert result["workload_count"] == result["scenario_count"]


def test_tight_top_k_exposes_requirement_gain_ranking_conflict() -> None:
    module = _benchmark_module()
    results = {
        arm: module.run_benchmark(
            arm=arm,
            fixture_path=FIXTURE_PATH,
            runs=1,
            warmups=0,
        )
        for arm in (
            "lexical-baseline",
            "lexical-ablation",
            "lexical-requirement-aware",
            "current-hash",
        )
    }

    selected_recall = {
        arm: next(
            scenario["metrics"]["requirement_recall"]["selected"]
            for scenario in result["scenarios"]
            if scenario["scenario_id"] == "tight_top_k"
        )
        for arm, result in results.items()
    }

    assert selected_recall == {
        "lexical-baseline": 0.0,
        "lexical-ablation": 0.0,
        "lexical-requirement-aware": 1.0,
        "current-hash": 1.0,
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


def test_support_metrics_mark_non_linking_arm_precision_not_applicable() -> None:
    module = _benchmark_module()
    metrics = module._support_metrics(
        {
            "requirement_support": {
                "canonical": {},
                "pool": {},
                "selected": {},
            },
            "selected_evidence_ids": [],
        },
        {"required_skill:sql": []},
        explicit_requirement_links=False,
    )

    assert metrics["requirement_recall"]["selected"] == "not_applicable"
    assert metrics["evidence_pair_recall"]["selected"] == "not_applicable"
    assert metrics["assignment_precision"] == "not_applicable"


def test_benchmark_arm_configs_keep_comparison_questions_separate() -> None:
    module = _benchmark_module()
    base = {"cv_analysis": {"selection_policy": {"requirement_gain_weight": 0.10}}}

    baseline = module._runtime_config(base, "lexical-baseline", 4)
    ablation = module._runtime_config(base, "lexical-ablation", 4)
    fitcv = module._runtime_config(base, "lexical-requirement-aware", 4)
    current_hash = module._runtime_config(base, "current-hash", 4)

    assert baseline["cv_analysis"]["selection_policy"]["requirement_gain_weight"] == 0.0
    assert baseline["cv_analysis"]["selection_policy"]["multi_channel_bonus"] == 0.0
    assert ablation["cv_analysis"]["selection_policy"]["requirement_gain_weight"] == 0.0
    assert fitcv["cv_analysis"]["selection_policy"]["requirement_gain_weight"] == 0.10
    assert current_hash["cv_analysis"]["semantic_alignment"]["enabled"] is True


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
    assert pool_eight["requirement_support"]["evidence_pair_recall"]["retrieved"] >= pool_four["requirement_support"]["evidence_pair_recall"]["retrieved"]
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


def test_benchmark_validation_matrix_records_declared_outcomes() -> None:
    module = _benchmark_module()
    result = module.run_benchmark(
        arm="lexical",
        pool_size=4,
        fixture_path=FIXTURE_PATH,
        runs=1,
        warmups=0,
    )

    assert result["validation"]["case_count"] == sum(
        item["case_count"] for item in result["validation"]["scenario_results"]
    )
    assert all(
        "pass" in case
        for scenario in result["scenarios"]
        for case in scenario["validation"]["case_results"]
    )


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


def test_impact_comparison_keeps_arm_questions_separate(tmp_path: Path) -> None:
    module = _comparison_module()
    common = {
        "evaluation_schema_version": 1,
        "fixture_sha256": "fixture",
        "scenario_set": ["one"],
        "evidence_budgets": [2],
        "top_k": [2],
        "validation": {},
        "requirement_support": {
            "micro_coverage": {
                "requirement_recall": {"selected": 0.5},
                "evidence_pair_recall": {"selected": 0.5},
            },
            "macro_coverage": {},
            "assignment_precision": 1.0,
        },
    }
    paths = []
    for arm, recall in (
        ("lexical-baseline", 0.2),
        ("lexical-ablation", 0.3),
        ("lexical-requirement-aware", 0.6),
        ("current-hash", 0.7),
    ):
        payload = json.loads(json.dumps(common))
        payload["arm"] = arm
        payload["requirement_support"]["micro_coverage"]["requirement_recall"]["selected"] = recall
        path = tmp_path / f"{arm}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)

    result = module.run_inputs(paths)

    assert result["comparisons"]["baseline_vs_fitcv"]["selected_requirement_recall_delta"] == 0.4
    assert result["comparisons"]["ablation_vs_fitcv"]["selected_requirement_recall_delta"] == 0.3
    assert result["comparisons"]["fitcv_vs_current_hash"]["selected_requirement_recall_delta"] == 0.1


def test_impact_comparison_rejects_scenario_and_budget_mismatch(tmp_path: Path) -> None:
    module = _comparison_module()
    common = {
        "evaluation_schema_version": 1,
        "fixture_sha256": "fixture",
        "scenario_set": ["one"],
        "evidence_budgets": [2],
        "top_k": [2],
        "requirement_support": {},
    }
    paths = []
    for arm in ("lexical-baseline", "lexical-ablation", "lexical-requirement-aware", "current-hash"):
        payload = json.loads(json.dumps(common))
        payload["arm"] = arm
        path = tmp_path / f"{arm}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)

    mismatched = json.loads(paths[-1].read_text(encoding="utf-8"))
    mismatched["scenario_set"] = ["two"]
    paths[-1].write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(ValueError, match="scenario sets"):
        module.run_inputs(paths)

    mismatched["scenario_set"] = ["one"]
    mismatched["evidence_budgets"] = [4]
    paths[-1].write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence budgets"):
        module.run_inputs(paths)
