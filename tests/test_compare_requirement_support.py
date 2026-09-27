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
    }


def test_not_run_arm_keeps_reason() -> None:
    module = _module()
    assert module._current_metrics(
        {"arm": "unsupported", "status": "not_run", "reason": "provider unavailable"}
    ) == {"status": "not_run", "reason": "provider unavailable"}
