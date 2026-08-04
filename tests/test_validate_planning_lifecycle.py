"""
@meta
# distribution_tier: starter_kit
name: test_validate_planning_lifecycle
type: test
scope: unit
domain: docs
covers:
  - Optional roadmap validation
  - Existing specification and plan metadata validation
  - Optional plan-to-spec reference validation
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

from pathlib import Path
from shutil import copy2, rmtree
import subprocess
import sys
import uuid

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_planning_lifecycle.py"


def make_test_root() -> Path:
    root = REPO_ROOT / ".tmp-tests" / f"validate-planning-{uuid.uuid4().hex}"
    (root / "repo_config").mkdir(parents=True, exist_ok=False)
    copy2(
        REPO_ROOT / "repo_config" / "planning_artifact_schema.yaml",
        root / "repo_config" / "planning_artifact_schema.yaml",
    )
    return root


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_validator(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_empty_repo_does_not_require_roadmap() -> None:
    root = make_test_root()
    try:
        result = run_validator(root)
        assert result.returncode == 0
        assert "passed" in result.stdout.lower()
    finally:
        rmtree(root, ignore_errors=True)


def test_optional_roadmap_is_validated_when_present() -> None:
    root = make_test_root()
    try:
        write_text(
            root / "docs" / "intent" / "master-workstream-roadmap.md",
            "---\nartifact_type: roadmap\nstatus: active\nlayer: change\n---\n# Roadmap\n",
        )
        result = run_validator(root, "--strict")
        assert result.returncode == 1
        assert "`layer` must be `intent`" in result.stdout
    finally:
        rmtree(root, ignore_errors=True)


def test_plan_parent_spec_must_resolve() -> None:
    root = make_test_root()
    try:
        write_text(
            root / "docs" / "superpowers" / "plans" / "demo-plan.md",
            "---\nartifact_type: plan\nstatus: proposed\nlayer: change\nparent_spec: docs/superpowers/specs/missing.md\n---\n# Plan\n",
        )
        result = run_validator(root)
        assert result.returncode == 1
        assert "parent_spec does not resolve" in result.stdout
    finally:
        rmtree(root, ignore_errors=True)


def test_existing_spec_and_linked_plan_pass() -> None:
    root = make_test_root()
    try:
        write_text(
            root / "docs" / "superpowers" / "specs" / "demo-spec.md",
            "---\nartifact_type: spec\nstatus: active\nlayer: change\n---\n# Spec\n",
        )
        write_text(
            root / "docs" / "superpowers" / "plans" / "demo-plan.md",
            "---\nartifact_type: plan\nstatus: proposed\nlayer: change\nparent_spec: docs/superpowers/specs/demo-spec.md\n---\n# Plan\n",
        )
        result = run_validator(root)
        assert result.returncode == 0
    finally:
        rmtree(root, ignore_errors=True)
