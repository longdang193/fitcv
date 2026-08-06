"""
@meta
# distribution_tier: starter_kit
name: test_plan_coordination
type: test
scope: unit
domain: harness
covers:
  - Plan coordination manifest normalization and digest.
  - Git-tracked plan, task identity, dependency, topology, and path validation.
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from shutil import copy2, rmtree
import subprocess
import sys
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_coordination.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))


def load_module():
    spec = importlib.util.spec_from_file_location("plan_coordination", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_root() -> Path:
    root = ROOT / ".tmp-tests" / f"plan-coordination-{uuid.uuid4().hex}"
    (root / "repo_config").mkdir(parents=True, exist_ok=False)
    copy2(ROOT / "repo_config" / "planning_artifact_schema.yaml", root / "repo_config" / "planning_artifact_schema.yaml")
    copy2(ROOT / "repo_config" / "harness.yaml", root / "repo_config" / "harness.yaml")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def plan_text(*, status: str = "proposed", coordination: str | None = None, prose_ids: tuple[str, ...] = ("task-1",)) -> str:
    frontmatter = "---\nartifact_type: plan\nstatus: " + status + "\nlayer: change\n"
    if coordination is not None:
        frontmatter += coordination
    frontmatter += "---\n# Plan\n\n## Task Breakdown\n"
    return frontmatter + "".join(
        f"\n### Task {index}: Fixture\n\n**Coordination ID:** `{task_id}`\n"
        for index, task_id in enumerate(prose_ids, start=1)
    )


def write_plan(root: Path, text: str, *, tracked: bool = True) -> str:
    path = root / "docs" / "superpowers" / "plans" / "fixture.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if tracked:
        subprocess.run(["git", "add", path.relative_to(root).as_posix()], cwd=root, check=True)
    return path.relative_to(root).as_posix()


VALID_COORDINATION = """coordination:
  target_branch: main
  base_ref: HEAD
  tasks:
    - id: task-1
      depends_on: []
      execution_mode: single_work_lane
      planned_write_paths: [scripts/**]
"""


def test_loads_tracked_proposed_plan_and_normalizes_digest() -> None:
    root = make_root()
    try:
        module = load_module()
        plan_ref = write_plan(root, plan_text(coordination=VALID_COORDINATION))

        coordination = module.load_plan_coordination(root, plan_ref)

        assert coordination.status == "proposed"
        assert coordination.task("task-1").planned_write_paths == ("scripts/**",)
        assert coordination.digest == module.coordination_digest(coordination.normalized())
        with pytest.raises(module.PlanCoordinationError, match="active plan"):
            module.load_plan_coordination(root, plan_ref, require_active=True)
    finally:
        rmtree(root, ignore_errors=True)


@pytest.mark.parametrize(
    ("coordination", "prose_ids", "message"),
    [
        (VALID_COORDINATION.replace("single_work_lane", "single_agent"), ("task-1",), "unknown execution mode"),
        (VALID_COORDINATION.replace("depends_on: []", "depends_on: [missing]"), ("task-1",), "unknown dependencies"),
        (VALID_COORDINATION.replace("scripts/**", "../escape"), ("task-1",), "safe repository-relative"),
        (VALID_COORDINATION.replace("id: task-1", "id: Task_1"), ("Task_1",), "ASCII slug"),
        (VALID_COORDINATION, ("missing",), "do not match manifest"),
    ],
)
def test_rejects_invalid_manifest_contract(coordination: str, prose_ids: tuple[str, ...], message: str) -> None:
    root = make_root()
    try:
        module = load_module()
        plan_ref = write_plan(root, plan_text(coordination=coordination, prose_ids=prose_ids))

        with pytest.raises(module.PlanCoordinationError, match=message):
            module.load_plan_coordination(root, plan_ref)
    finally:
        rmtree(root, ignore_errors=True)


def test_rejects_untracked_and_cyclic_manifest() -> None:
    root = make_root()
    try:
        module = load_module()
        untracked = write_plan(root, plan_text(coordination=VALID_COORDINATION), tracked=False)
        with pytest.raises(module.PlanCoordinationError, match="Git-tracked"):
            module.load_plan_coordination(root, untracked)

        cyclic = VALID_COORDINATION.replace(
            "depends_on: []",
            "depends_on: [task-2]",
        ) + """    - id: task-2
      depends_on: [task-1]
      execution_mode: single_work_lane
      planned_write_paths: [tests/**]
"""
        plan_ref = write_plan(root, plan_text(coordination=cyclic, prose_ids=("task-1", "task-2")))
        with pytest.raises(module.PlanCoordinationError, match="acyclic"):
            module.load_plan_coordination(root, plan_ref)
    finally:
        rmtree(root, ignore_errors=True)


def test_manifest_free_plan_returns_none() -> None:
    root = make_root()
    try:
        module = load_module()
        plan_ref = write_plan(root, plan_text(coordination=None, prose_ids=()))

        assert module.load_plan_coordination(root, plan_ref) is None
    finally:
        rmtree(root, ignore_errors=True)
