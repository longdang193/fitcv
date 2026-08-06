"""
@meta
name: plan_coordination
type: utility
domain: harness
distribution_tier: starter_kit
responsibility:
  - Validate plan-owned coordination manifests for lifecycle and packet resolution.
inputs:
  - Git-tracked implementation plans with optional coordination frontmatter.
outputs:
  - Normalized immutable plan coordination bindings and digest.
tags:
  - harness
  - planning
  - validation
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

import yaml

from planning_artifact_schema import get_allowed_values


class PlanCoordinationError(ValueError):
    pass


TASK_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TASK_HEADING_PATTERN = re.compile(r"^###\s+Task\b.*$", re.MULTILINE)
COORDINATION_ID_LINE_PATTERN = re.compile(r"^\*\*Coordination ID:\*\*\s*(.*?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PlanTask:
    task_id: str
    depends_on: tuple[str, ...]
    execution_mode: str
    planned_write_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "depends_on": list(self.depends_on),
            "execution_mode": self.execution_mode,
            "planned_write_paths": list(self.planned_write_paths),
        }


@dataclass(frozen=True)
class PlanCoordination:
    plan_ref: str
    status: str
    target_branch: str
    base_ref: str
    tasks: tuple[PlanTask, ...]
    digest: str

    def task(self, task_id: str) -> PlanTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise PlanCoordinationError(f"coordination task `{task_id}` does not exist")

    def normalized(self) -> dict[str, Any]:
        return {
            "target_branch": self.target_branch,
            "base_ref": self.base_ref,
            "tasks": [task.as_dict() for task in self.tasks],
        }


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanCoordinationError(f"coordination `{name}` must be a non-empty string")
    return value


def _safe_repository_path(value: Any, name: str) -> str:
    path = _required_string(value, name)
    if "\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise PlanCoordinationError(f"coordination `{name}` must be a safe repository-relative path")
    parts = PurePosixPath(path).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise PlanCoordinationError(f"coordination `{name}` must be a safe repository-relative path")
    return path


def _canonical_modes(root: Path) -> set[str]:
    policy_path = root / "repo_config" / "harness.yaml"
    try:
        payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PlanCoordinationError(f"could not read harness policy: {exc}") from exc
    orchestration = payload.get("orchestration") if isinstance(payload, dict) else None
    if not isinstance(orchestration, dict) or not all(isinstance(name, str) for name in orchestration):
        raise PlanCoordinationError("harness policy has invalid orchestration modes")
    return set(orchestration)


def _normalize_task(value: Any, canonical_modes: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanCoordinationError("coordination `tasks` entries must be objects")
    allowed = {"id", "depends_on", "execution_mode", "planned_write_paths"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PlanCoordinationError(f"coordination task has unknown fields: {', '.join(unknown)}")
    task_id = _required_string(value.get("id"), "tasks.id")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise PlanCoordinationError("coordination `tasks.id` must be an ASCII slug")
    depends_on = value.get("depends_on")
    if not isinstance(depends_on, list) or not all(isinstance(item, str) for item in depends_on):
        raise PlanCoordinationError("coordination `tasks.depends_on` must be a list of task IDs")
    if len(set(depends_on)) != len(depends_on):
        raise PlanCoordinationError("coordination `tasks.depends_on` must not contain duplicates")
    execution_mode = _required_string(value.get("execution_mode"), "tasks.execution_mode")
    if execution_mode not in canonical_modes:
        raise PlanCoordinationError(f"coordination task `{task_id}` has unknown execution mode `{execution_mode}`")
    paths = value.get("planned_write_paths")
    if not isinstance(paths, list) or not paths:
        raise PlanCoordinationError("coordination `tasks.planned_write_paths` must be a non-empty list")
    normalized_paths = [_safe_repository_path(path, "tasks.planned_write_paths") for path in paths]
    if len(set(normalized_paths)) != len(normalized_paths):
        raise PlanCoordinationError("coordination `tasks.planned_write_paths` must not contain duplicates")
    return {
        "id": task_id,
        "depends_on": sorted(depends_on),
        "execution_mode": execution_mode,
        "planned_write_paths": sorted(normalized_paths),
    }


def _validate_dependencies(tasks: list[dict[str, Any]]) -> None:
    task_ids = {task["id"] for task in tasks}
    graph: dict[str, list[str]] = {}
    for task in tasks:
        dependencies = task["depends_on"]
        unknown = sorted(set(dependencies) - task_ids)
        if unknown:
            raise PlanCoordinationError(
                f"coordination task `{task['id']}` has unknown dependencies: {', '.join(unknown)}"
            )
        if task["id"] in dependencies:
            raise PlanCoordinationError(f"coordination task `{task['id']}` cannot depend on itself")
        graph[task["id"]] = dependencies

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise PlanCoordinationError("coordination task dependencies must be acyclic")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in graph[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)


def normalize_coordination(value: Any, canonical_modes: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanCoordinationError("coordination must be an object")
    allowed = {"target_branch", "base_ref", "tasks"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PlanCoordinationError(f"coordination has unknown fields: {', '.join(unknown)}")
    target_branch = _required_string(value.get("target_branch"), "target_branch")
    base_ref = _required_string(value.get("base_ref"), "base_ref")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise PlanCoordinationError("coordination `tasks` must be a non-empty list")
    normalized_tasks = [_normalize_task(task, canonical_modes) for task in tasks]
    task_ids = [task["id"] for task in normalized_tasks]
    if len(set(task_ids)) != len(task_ids):
        raise PlanCoordinationError("coordination task IDs must be unique")
    _validate_dependencies(normalized_tasks)
    return {
        "target_branch": target_branch,
        "base_ref": base_ref,
        "tasks": sorted(normalized_tasks, key=lambda task: task["id"]),
    }


def coordination_digest(normalized: dict[str, Any]) -> str:
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _frontmatter_and_body(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8", errors="ignore").removeprefix("\ufeff")
    if not text.startswith("---"):
        raise PlanCoordinationError("plan is missing valid YAML frontmatter")
    marker_end = text.find("\n---", 3)
    if marker_end == -1:
        raise PlanCoordinationError("plan is missing valid YAML frontmatter")
    payload = yaml.safe_load(text[3:marker_end])
    if not isinstance(payload, dict):
        raise PlanCoordinationError("plan frontmatter must be an object")
    return payload, text[marker_end + 4:]


def _tracked_plan(root: Path, plan_ref: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", plan_ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise PlanCoordinationError(f"coordination plan `{plan_ref}` must be Git-tracked")


def _validate_prose_task_ids(body: str, task_ids: set[str]) -> None:
    headings = list(TASK_HEADING_PATTERN.finditer(body))
    if not headings:
        raise PlanCoordinationError("coordination plan must contain prose task sections")
    prose_ids: list[str] = []
    for index, heading in enumerate(headings):
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        matches = COORDINATION_ID_LINE_PATTERN.findall(body[heading.end():section_end])
        if len(matches) != 1:
            raise PlanCoordinationError("each prose task section must contain exactly one Coordination ID")
        task_id = matches[0].strip("`")
        if not TASK_ID_PATTERN.fullmatch(task_id):
            raise PlanCoordinationError("prose Coordination ID must be an ASCII slug")
        prose_ids.append(task_id)
    if len(set(prose_ids)) != len(prose_ids):
        raise PlanCoordinationError("prose Coordination IDs must be unique")
    missing = sorted(task_ids - set(prose_ids))
    unknown = sorted(set(prose_ids) - task_ids)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise PlanCoordinationError(f"prose Coordination IDs do not match manifest tasks ({'; '.join(details)})")


def load_plan_coordination(root: Path, plan_ref: str, *, require_active: bool = False) -> PlanCoordination | None:
    normalized_ref = _safe_repository_path(plan_ref, "plan_ref")
    plan_path = root.resolve().joinpath(*PurePosixPath(normalized_ref).parts)
    if not plan_path.is_file():
        raise PlanCoordinationError(f"coordination plan does not exist: `{normalized_ref}`")
    payload, body = _frontmatter_and_body(plan_path)
    if payload.get("artifact_type") != "plan":
        raise PlanCoordinationError("coordination source must be a plan artifact")
    if "coordination" not in payload:
        return None
    status = _required_string(payload.get("status"), "plan status")
    if status not in get_allowed_values(root, "status", "plan"):
        raise PlanCoordinationError(f"coordination plan status `{status}` is invalid")
    if require_active and status != "active":
        raise PlanCoordinationError("coordinated managed execution requires an active plan")
    _tracked_plan(root, normalized_ref)
    normalized = normalize_coordination(payload["coordination"], _canonical_modes(root))
    _validate_prose_task_ids(body, {task["id"] for task in normalized["tasks"]})
    tasks = tuple(
        PlanTask(
            task_id=task["id"],
            depends_on=tuple(task["depends_on"]),
            execution_mode=task["execution_mode"],
            planned_write_paths=tuple(task["planned_write_paths"]),
        )
        for task in normalized["tasks"]
    )
    return PlanCoordination(
        plan_ref=normalized_ref,
        status=status,
        target_branch=normalized["target_branch"],
        base_ref=normalized["base_ref"],
        tasks=tasks,
        digest=coordination_digest(normalized),
    )
