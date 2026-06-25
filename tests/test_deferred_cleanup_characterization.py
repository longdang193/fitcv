"""
@meta
type: test
scope: unit
domain: architecture
covers:
  - deferred cleanup modules remain outside active src/tests import graph
excludes:
  - runtime execution parity
  - deletion or adoption of deferred modules
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
TESTS_ROOT = REPO_ROOT / "tests"
DEFERRED_MODULES = {
    "fitcv.pipeline_stage_runner",
    "fitcv.reuse_law_engine",
}
EXCLUDED_PATHS = {
    SRC_ROOT / "fitcv" / "pipeline_stage_runner.py",
    SRC_ROOT / "fitcv" / "reuse_law_engine.py",
    Path(__file__).resolve(),
}


def _python_files() -> list[Path]:
    files = list(SRC_ROOT.rglob("*.py")) + list(TESTS_ROOT.rglob("*.py"))
    return [path for path in files if path.resolve() not in EXCLUDED_PATHS]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_deferred_cleanup_modules_have_no_active_src_or_test_importers() -> None:
    importers: dict[str, list[str]] = {module: [] for module in DEFERRED_MODULES}

    for path in _python_files():
        modules = _imported_modules(path)
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for deferred_module in DEFERRED_MODULES:
            if deferred_module in modules:
                importers[deferred_module].append(rel_path)

    assert importers == {
        "fitcv.pipeline_stage_runner": [],
        "fitcv.reuse_law_engine": [],
    }
