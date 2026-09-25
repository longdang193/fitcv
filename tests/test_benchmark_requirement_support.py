from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "benchmark_requirement_support.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "requirement_support_benchmark.json"


def _benchmark_module() -> Any:
    spec = importlib.util.spec_from_file_location("benchmark_requirement_support", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_contains_positive_and_negative_grounding_cases() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

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
    assert metrics["direct_support_opportunities"]["required_skill:sql"] == ["ev-2"]


def test_lexical_pool_eight_recovers_pool_four_support_loss() -> None:
    module = _benchmark_module()
    pool_four = module.run_benchmark(arm="lexical", pool_size=4, fixture_path=FIXTURE_PATH)
    pool_eight = module.run_benchmark(arm="lexical", pool_size=8, fixture_path=FIXTURE_PATH)

    assert pool_four["requirement_support"]["direct_support_opportunities"]["required_skill:sql"]
    assert pool_eight["requirement_support"]["direct_support_opportunities"]["required_skill:sql"] == []
    assert pool_eight["backend"]["backend_id"] == "disabled"
