from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "compare_requirement_support.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("compare_requirement_support", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_arm_registry_preserves_normalized_names() -> None:
    module = _module()
    assert set(module.ARM_REGISTRY) == {
        "lexical-baseline",
        "lexical-ablation",
        "lexical-requirement-aware",
        "current-hash",
        "full-pool",
    }


def test_not_run_arm_keeps_reason() -> None:
    module = _module()
    assert module._current_metrics(
        {"arm": "unsupported", "status": "not_run", "reason": "provider unavailable"}
    ) == {"status": "not_run", "reason": "provider unavailable"}


def test_pairwise_inputs_return_recommendation() -> None:
    module = _module()
    common = {
        "evaluation_schema_version": 1,
        "fixture_sha256": "fixture",
        "scenario_set": ["one"],
        "evidence_budgets": [1],
        "top_k": [1],
        "requirement_support": {
            "micro_coverage": {
                "requirement_recall": {"selected": 0.5},
                "evidence_pair_recall": {"selected": 0.5},
            }
        },
        "timing_ms": {"total_ms": {"p95": 10}},
        "context": {"estimated_prompt_tokens": 10},
        "validation": {"passed_cases": 1, "case_count": 1},
    }
    paths = []
    for arm, pair_recall in (("current-hash", 0.5), ("full-pool", 0.6)):
        payload = dict(common)
        payload["arm"] = arm
        payload["requirement_support"] = {"micro_coverage": {
            "requirement_recall": {"selected": 0.5},
            "evidence_pair_recall": {"selected": pair_recall},
        }}
        path = Path(__file__).parent / f"{arm}-comparison-test.json"
        path.write_text(__import__("json").dumps(payload), encoding="utf-8")
        paths.append(path)
    try:
        result = module.run_inputs(paths)
    finally:
        for path in paths:
            path.unlink()
    comparison = result["comparisons"]["pairwise"]["current-hash_vs_full-pool"]
    assert comparison["qualified"] is True
    assert comparison["recommendation"] == "retain full-pool"
