"""
@meta
repo: private
name: validate_component_boundaries
type: script
domain: architecture
responsibility:
  - Enforce lightweight component-boundary import rules for key runtime modules.
  - Enforce package-level ownership map import rules.
  - Honor explicit, documented temporary exceptions.
inputs:
  - src/fitcv/**/*.py
  - src/fitcv_cp/**/*.py
  - docs/operating_system/component_boundary_exceptions.yaml
  - docs/operating_system/component_ownership_map.yaml
outputs:
  - Exit status and human-readable component-boundary validation results.
tags:
  - architecture
  - validation
  - boundaries
lifecycle:
  status: active
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import sys
from typing import Any

import yaml


@dataclass(frozen=True)
class BoundaryRule:
    source: str
    forbidden_prefix: str
    reason: str


RULES: tuple[BoundaryRule, ...] = (
    BoundaryRule(
        source="src/fitcv/pipeline.py",
        forbidden_prefix="fitcv_cp.",
        reason="pipeline runtime must not depend on control-plane modules",
    ),
    BoundaryRule(
        source="src/fitcv_cp/reporter.py",
        forbidden_prefix="fitcv.pipeline",
        reason="telemetry adapter must not depend on pipeline orchestration logic",
    ),
    BoundaryRule(
        source="src/fitcv_cp/bq_store.py",
        forbidden_prefix="fitcv.pipeline",
        reason="data-plane adapter must not depend on pipeline execution logic",
    ),
    BoundaryRule(
        source="src/fitcv_cp/app.py",
        forbidden_prefix="fitcv_cp.worker_job",
        reason="control-plane UI/API must not import worker execution module directly",
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_exceptions(root: Path) -> set[tuple[str, str]]:
    path = root / "docs" / "operating_system" / "component_boundary_exceptions.yaml"
    if not path.exists():
        return set()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return set()
    rows = payload.get("exceptions")
    if not isinstance(rows, list):
        return set()
    result: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source") or "").strip()
        imported = str(row.get("import") or "").strip()
        if source and imported:
            result.add((source, imported))
    return result


def _load_component_map(root: Path) -> dict[str, Any]:
    path = root / "docs" / "operating_system" / "component_ownership_map.yaml"
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(str(name.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(str(node.module))
    return imports


def _matches_any_glob(rel_path: str, globs: list[str]) -> bool:
    for pattern in globs:
        if fnmatch(rel_path, pattern):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    exceptions = _load_exceptions(root)
    component_map = _load_component_map(root)
    violations: list[str] = []

    for rule in RULES:
        source_path = root / rule.source
        if not source_path.exists():
            continue
        for imported in sorted(_imported_modules(source_path)):
            if not imported.startswith(rule.forbidden_prefix):
                continue
            if (rule.source, imported) in exceptions:
                continue
            violations.append(
                f"{rule.source}: forbidden import `{imported}` ({rule.reason})"
            )

    components = component_map.get("components")
    if isinstance(components, dict):
        for _, spec in components.items():
            if not isinstance(spec, dict):
                continue
            source_globs = [str(item) for item in list(spec.get("source_globs") or [])]
            forbidden_prefixes = [str(item) for item in list(spec.get("forbidden_import_prefixes") or [])]
            if not source_globs or not forbidden_prefixes:
                continue
            for py_path in root.rglob("*.py"):
                rel = py_path.resolve().relative_to(root.resolve()).as_posix()
                if not _matches_any_glob(rel, source_globs):
                    continue
                for imported in sorted(_imported_modules(py_path)):
                    for forbidden_prefix in forbidden_prefixes:
                        if forbidden_prefix and imported.startswith(forbidden_prefix):
                            if (rel, imported) in exceptions:
                                continue
                            violations.append(
                                f"{rel}: forbidden import `{imported}` (component-map rule `{forbidden_prefix}`)"
                            )

    if violations:
        print("Component-boundary validation failed:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "Add a temporary exception in docs/operating_system/component_boundary_exceptions.yaml "
            "only when justified and time-bounded."
        )
        return 1

    print("Component-boundary validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

