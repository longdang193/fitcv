"""
@meta
name: harness_task
type: script
domain: harness
distribution_tier: starter_kit
responsibility:
  - Resolve controller task metadata through canonical harness policy.
  - Verify task claims with fresh repository evidence.
inputs:
  - Versioned task and claimed-result JSON.
  - repo_config/harness.yaml
outputs:
  - Normalized task packet or verification evidence JSON.
tags:
  - harness
  - routing
  - verification
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import copy
from datetime import UTC, datetime, timedelta
import fnmatch
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Callable
import uuid

import yaml


class HarnessError(ValueError):
    pass


CheckRunner = Callable[[list[str]], tuple[int, str, str]]
ChangeCollector = Callable[[Path, str], list[dict[str, str]]]

MANAGED_VERSION = 2
CAPABILITY_LEVELS = {"enforced", "advisory", "unavailable"}
CRITERION_KINDS = {"check", "change_set", "review", "manual"}
DECISION_KINDS = {"accept", "retry", "escalate", "request_approval", "block"}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"invalid JSON input: {path}") from exc
    if not isinstance(payload, dict):
        raise HarnessError("JSON input must be an object")
    return payload


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / "repo_config" / "harness.yaml"
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise HarnessError("harness policy must be an object")
    return payload


def _validate_policy(root: Path) -> None:
    path = root / "scripts" / "validate_harness_config.py"
    spec = importlib.util.spec_from_file_location("validate_harness_config", path)
    if spec is None or spec.loader is None:
        raise HarnessError("unable to load harness configuration validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors = module.validate(root)
    if errors:
        raise HarnessError("invalid harness policy: " + "; ".join(errors))


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise HarnessError(f"{name} must be a non-empty list of strings")
    return value


def _safe_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or value.startswith("."):
        raise HarnessError(f"unsafe relative path `{value}`")
    return path.as_posix()


def resolve_task(root: Path, task: dict[str, Any]) -> dict[str, Any]:
    _validate_policy(root)
    if task.get("version") != 1:
        raise HarnessError("task version must be 1")
    task_type = task.get("task_type")
    if not isinstance(task_type, str):
        raise HarnessError("task_type must be a string")
    criteria = _string_list(task.get("acceptance_criteria"), "acceptance_criteria")
    allowed_paths = [_safe_path(path) for path in _string_list(task.get("allowed_paths"), "allowed_paths")]
    base_ref = task.get("base_ref")
    if not isinstance(base_ref, str) or not base_ref:
        raise HarnessError("base_ref must be a non-empty string")

    policy = _load_policy(root)
    route = policy["routes"].get(task_type)
    if route is None:
        raise HarnessError(f"unknown task type `{task_type}`")
    execution_mode = task.get("execution_mode", "single_agent")
    if not isinstance(execution_mode, str) or execution_mode not in route["execution_modes"]:
        raise HarnessError(f"unsupported execution mode `{execution_mode}` for task type `{task_type}`")
    orchestration = policy["orchestration"][execution_mode]
    checks = {name: policy["checks"][name]["command"] for name in route["checks"]}
    gates = {
        name: policy["approval_gates"][name]["paths"]
        for name in route.get("approval_gates", policy.get("defaults", {}).get("approval_gates", []))
    }
    return {
        "version": 1,
        "task_type": task_type,
        "template": route["template"],
        "role": route["role"],
        "rules": list(dict.fromkeys([*route["rules"], *orchestration["rules"]])),
        "skills": route["skills"],
        "tools": route["tools"],
        "workspace": route["workspace"],
        "orchestration": {
            "name": execution_mode,
            "max_parallel_writers": orchestration["max_parallel_writers"],
            "workspace_mode": orchestration["workspace_mode"],
            "review_required": orchestration["review_required"],
        },
        "checks": checks,
        "approval_gates": gates,
        "allowed_next_states": policy["states"],
        "acceptance_criteria": criteria,
        "allowed_paths": allowed_paths,
        "base_ref": base_ref,
    }


def _path_matches(path: str, patterns: list[str]) -> bool:
    return any(
        path == pattern[:-3] or path.startswith(pattern[:-2]) if pattern.endswith("/**") else fnmatch.fnmatchcase(path, pattern)
        for pattern in patterns
    )


def _run_command(root: Path, command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def _changed_paths(root: Path, base_ref: str) -> list[str]:
    status, stdout, stderr = _run_command(root, ["git", "diff", "--name-only", base_ref, "--"])
    if status:
        raise HarnessError(f"could not read changed paths: {stderr.strip()}")
    return [line for line in stdout.splitlines() if line]


def _validate_claim(claim: dict[str, Any]) -> None:
    if claim.get("kind") != "claimed_result":
        raise HarnessError("claim kind must be `claimed_result`")
    _string_list(claim.get("changed_files"), "changed_files")
    for name in ("from_state", "next_state"):
        if not isinstance(claim.get(name), str) or not claim[name]:
            raise HarnessError(f"{name} must be a non-empty string")
    approved = claim.get("approved_gates", [])
    if not isinstance(approved, list) or not all(isinstance(item, str) for item in approved):
        raise HarnessError("approved_gates must be a list of strings")


def verify_task(
    root: Path,
    task: dict[str, Any],
    claim: dict[str, Any],
    *,
    changed_paths: list[str] | None = None,
    run_check: CheckRunner | None = None,
) -> dict[str, Any]:
    packet = resolve_task(root, task)
    _validate_claim(claim)
    changed = changed_paths if changed_paths is not None else _changed_paths(root, packet["base_ref"])
    runner = run_check or (lambda command: _run_command(root, command))
    blockers: list[dict[str, str]] = []
    for path in changed:
        safe_path = _safe_path(path)
        if not _path_matches(safe_path, packet["allowed_paths"]):
            blockers.append({"kind": "scope", "path": safe_path})
        for gate, patterns in packet["approval_gates"].items():
            if _path_matches(safe_path, patterns) and gate not in claim.get("approved_gates", []):
                blockers.append({"kind": "approval", "gate": gate, "path": safe_path})

    states = packet["allowed_next_states"]
    if claim["next_state"] not in states.get(claim["from_state"], []):
        blockers.append({"kind": "transition", "from": claim["from_state"], "to": claim["next_state"]})

    checks = []
    for name, command in packet["checks"].items():
        code, stdout, stderr = runner(command)
        checks.append({"name": name, "command": command, "exit_code": code, "stdout": stdout[:1000], "stderr": stderr[:1000]})
        if code:
            blockers.append({"kind": "check", "name": name})

    for friction in claim.get("frictions", []):
        if isinstance(friction, dict) and isinstance(friction.get("category"), str):
            blockers.append({"kind": "friction", "category": friction["category"]})

    result = {
        "version": 1,
        "status": "verified" if not blockers else "observed",
        "packet": packet,
        "changed_paths": changed,
        "checks": checks,
        "blockers": blockers,
        "acceptance": [{"criterion": criterion, "proven": not blockers} for criterion in packet["acceptance_criteria"]],
    }
    run_dir = task.get("run_dir")
    if isinstance(run_dir, str) and run_dir:
        target = Path(run_dir)
        allowed_root = (root / ".harness").resolve()
        try:
            target.resolve().relative_to(allowed_root)
        except ValueError as exc:
            raise HarnessError(f"run_dir must stay under `{allowed_root}`") from exc
        target.mkdir(parents=True, exist_ok=True)
        (target / "evidence.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise HarnessError(f"{name} must be a non-empty string")
    return value


def _safe_paths(value: Any, name: str, *, required: bool) -> list[str]:
    if value is None and not required:
        return []
    if not required:
        if not isinstance(value, list) or not all(isinstance(path, str) and path for path in value):
            raise HarnessError(f"{name} must be a list of strings")
        return [_safe_path(path) for path in value]
    return [_safe_path(path) for path in _string_list(value, name)]


def _load_roles(root: Path) -> dict[str, dict[str, Any]]:
    with (root / "agents" / "roles.yaml").open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    roles = payload.get("roles") if isinstance(payload, dict) else None
    if not isinstance(roles, dict):
        raise HarnessError("roles must be a mapping")
    return roles


def _route_packet(policy: dict[str, Any], task_type: str, execution_mode: str) -> dict[str, Any]:
    route = policy["routes"].get(task_type)
    if not isinstance(route, dict):
        raise HarnessError(f"unknown task type `{task_type}`")
    if execution_mode not in route["execution_modes"]:
        raise HarnessError(f"unsupported execution mode `{execution_mode}` for task type `{task_type}`")
    orchestration = policy["orchestration"][execution_mode]
    return {
        "task_type": task_type,
        "template": route["template"],
        "role": route["role"],
        "rules": list(dict.fromkeys([*route["rules"], *orchestration["rules"]])),
        "skills": route["skills"],
        "tools": route["tools"],
        "workspace": route["workspace"],
        "orchestration": {
            "name": execution_mode,
            "max_parallel_writers": orchestration["max_parallel_writers"],
            "workspace_mode": orchestration["workspace_mode"],
            "review_required": orchestration["review_required"],
        },
        "checks": {name: policy["checks"][name]["command"] for name in route["checks"]},
        "approval_gates": {
            name: policy["approval_gates"][name]["paths"]
            for name in route.get("approval_gates", policy.get("defaults", {}).get("approval_gates", []))
        },
        "retry_policy": copy.deepcopy(policy["retry_policies"][route["retry_policy"]]),
        "allowed_next_states": copy.deepcopy(policy["states"]),
    }


def _resolve_commit(root: Path, base_ref: str) -> str:
    status, stdout, stderr = _run_command(root, ["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"])
    if status:
        raise HarnessError(f"could not resolve base commit `{base_ref}`: {stderr.strip()}")
    return stdout.strip()


def _safe_run_id(value: Any) -> str:
    run_id = _required_string(value, "run_id")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise HarnessError("run_id must contain only letters, digits, underscores, and hyphens")
    return run_id


def _run_path(root: Path, run_id: str) -> Path:
    return root / ".harness" / "runs" / _safe_run_id(run_id) / "run.json"


def _write_run(root: Path, run: dict[str, Any]) -> None:
    target = _run_path(root, run["run_id"])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def _load_run(root: Path, run_id: str) -> dict[str, Any]:
    run = _load_json(_run_path(root, run_id))
    if run.get("version") != 1 or run.get("run_id") != run_id or not isinstance(run.get("attempts"), list):
        raise HarnessError(f"invalid run record `{run_id}`")
    return run


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HarnessError("approval issued_at must be an ISO-8601 timestamp") from exc


def _validate_criteria(value: Any, checks: dict[str, list[str]]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise HarnessError("acceptance_criteria must be a non-empty list")
    criteria: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise HarnessError("managed acceptance criterion must be an object")
        criterion_id = _required_string(raw.get("id"), "criterion id")
        if criterion_id in seen:
            raise HarnessError(f"duplicate criterion id `{criterion_id}`")
        seen.add(criterion_id)
        kind = _required_string(raw.get("kind"), "criterion kind")
        if kind not in CRITERION_KINDS:
            raise HarnessError(f"unsupported criterion kind `{kind}`")
        criterion = copy.deepcopy(raw)
        if kind == "check":
            check = _required_string(raw.get("check"), "criterion check")
            if check not in checks:
                raise HarnessError(f"unknown criterion check `{check}`")
        if kind == "change_set":
            criterion["paths"] = _safe_paths(raw.get("paths"), "criterion paths", required=True)
        criteria.append(criterion)
    return criteria


def _validate_approvals(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise HarnessError("approvals must be a list")
    approvals: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise HarnessError("approval record must be an object")
        approval = copy.deepcopy(raw)
        approval["gate"] = _required_string(raw.get("gate"), "approval gate")
        approval["approver"] = _required_string(raw.get("approver"), "approval approver")
        approval["attempt_id"] = _required_string(raw.get("attempt_id"), "approval attempt_id")
        approval["issued_at"] = _required_string(raw.get("issued_at"), "approval issued_at")
        _parse_timestamp(approval["issued_at"])
        approval["paths"] = _safe_paths(raw.get("paths"), "approval paths", required=True)
        approvals.append(approval)
    return approvals


def _patterns_overlap(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.endswith("/**"):
        return _path_matches(right, [left])
    if right.endswith("/**"):
        return _path_matches(left, [right])
    return fnmatch.fnmatchcase(left, right) or fnmatch.fnmatchcase(right, left)


def _normalize_lanes(root: Path, packet: dict[str, Any], allowed_paths: list[str], value: Any) -> list[dict[str, Any]]:
    roles = _load_roles(root)
    if packet["orchestration"]["name"] == "single_agent":
        role = packet["role"]
        return [{
            "lane_id": "primary",
            "role": role,
            "allowed_paths": allowed_paths,
            "dependencies": [],
            "workspace_mode": packet["orchestration"]["workspace_mode"],
            "write_capable": bool(roles[role]["writes"]),
        }]
    if not isinstance(value, list) or not value:
        raise HarnessError("lanes must be a non-empty list for non-single-agent mode")
    lanes: list[dict[str, Any]] = []
    lane_ids: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise HarnessError("lane must be an object")
        lane_id = _required_string(raw.get("lane_id"), "lane_id")
        if lane_id in lane_ids:
            raise HarnessError(f"duplicate lane_id `{lane_id}`")
        lane_ids.add(lane_id)
        role = _required_string(raw.get("role"), "lane role")
        if role not in roles:
            raise HarnessError(f"unknown lane role `{role}`")
        write_capable = raw.get("write_capable")
        if not isinstance(write_capable, bool) or write_capable != bool(roles[role]["writes"]):
            raise HarnessError(f"lane `{lane_id}` has invalid write_capable")
        dependencies = _safe_paths(raw.get("dependencies", []), "lane dependencies", required=False)
        workspace_mode = _required_string(raw.get("workspace_mode"), "lane workspace_mode")
        if workspace_mode != packet["orchestration"]["workspace_mode"]:
            raise HarnessError(f"lane `{lane_id}` workspace_mode conflicts with execution mode")
        lanes.append({
            "lane_id": lane_id,
            "role": role,
            "allowed_paths": _safe_paths(raw.get("allowed_paths"), "lane allowed_paths", required=True),
            "dependencies": dependencies,
            "workspace_mode": workspace_mode,
            "write_capable": write_capable,
        })
    for lane in lanes:
        for dependency in lane["dependencies"]:
            if dependency == lane["lane_id"] or dependency not in lane_ids:
                raise HarnessError(f"lane `{lane['lane_id']}` has invalid dependency `{dependency}`")
    visiting: set[str] = set()
    visited: set[str] = set()
    dependencies = {lane["lane_id"]: lane["dependencies"] for lane in lanes}

    def visit(lane_id: str) -> None:
        if lane_id in visiting:
            raise HarnessError("lane dependencies contain a cycle")
        if lane_id in visited:
            return
        visiting.add(lane_id)
        for dependency in dependencies[lane_id]:
            visit(dependency)
        visiting.remove(lane_id)
        visited.add(lane_id)

    for lane_id in lane_ids:
        visit(lane_id)
    writable = [lane for lane in lanes if lane["write_capable"]]
    for index, lane in enumerate(writable):
        for other in writable[index + 1:]:
            if any(_patterns_overlap(path, other_path) for path in lane["allowed_paths"] for other_path in other["allowed_paths"]):
                raise HarnessError(f"writable lanes `{lane['lane_id']}` and `{other['lane_id']}` overlap")
    return lanes


def resolve_managed_packet(root: Path, request: dict[str, Any], *, attempt_id: str) -> dict[str, Any]:
    _validate_policy(root)
    if request.get("version") != MANAGED_VERSION:
        raise HarnessError(f"managed request version must be {MANAGED_VERSION}")
    task_type = _required_string(request.get("task_type"), "task_type")
    execution_mode = _required_string(request.get("execution_mode", "single_agent"), "execution_mode")
    packet = _route_packet(_load_policy(root), task_type, execution_mode)
    role = _load_roles(root).get(packet["role"])
    if not isinstance(role, dict):
        raise HarnessError(f"unknown route role `{packet['role']}`")
    allowed_paths = _safe_paths(request.get("allowed_paths"), "allowed_paths", required=True)
    planned_write_paths = _safe_paths(request.get("planned_write_paths"), "planned_write_paths", required=bool(role["writes"]))
    base_ref = _required_string(request.get("base_ref"), "base_ref")
    packet.update({
        "version": MANAGED_VERSION,
        "attempt_id": attempt_id,
        "base_ref": base_ref,
        "base_commit": _resolve_commit(root, base_ref),
        "allowed_paths": allowed_paths,
        "planned_write_paths": planned_write_paths,
        "acceptance_criteria": _validate_criteria(request.get("acceptance_criteria"), packet["checks"]),
        "approvals": _validate_approvals(request.get("approvals")),
        "review_evidence": copy.deepcopy(request.get("review_evidence")),
        "manual_evidence": copy.deepcopy(request.get("manual_evidence")),
    })
    packet["lanes"] = _normalize_lanes(root, packet, allowed_paths, request.get("lanes"))
    return packet


def _transition(run: dict[str, Any], states: dict[str, list[str]], next_state: str, reason: str) -> None:
    current_state = run["state"]
    if next_state not in states.get(current_state, []):
        raise HarnessError(f"invalid managed transition `{current_state}` to `{next_state}`")
    run["state"] = next_state
    run["state_history"].append({"state": next_state, "reason": reason, "at": _timestamp()})


def _new_run(request: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "version": 1,
        "run_id": run_id,
        "request": copy.deepcopy(request),
        "state": "classified",
        "state_history": [{"state": "classified", "reason": "created", "at": _timestamp()}],
        "attempts": [],
    }


def _append_attempt(run: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    attempt = {
        "attempt_id": packet["attempt_id"],
        "packet": copy.deepcopy(packet),
        "lanes": copy.deepcopy(packet["lanes"]),
        "claims": [],
        "evidence": {},
        "frictions": [],
        "outcome": None,
        "decision": None,
        "decision_history": [],
    }
    run["attempts"].append(attempt)
    return attempt


def _active_attempt(run: dict[str, Any]) -> dict[str, Any]:
    if not run["attempts"] or not isinstance(run["attempts"][-1], dict):
        raise HarnessError("run has no active attempt")
    return run["attempts"][-1]


def _set_outcome(attempt: dict[str, Any], reason: str, allowed_decisions: list[str], evidence_refs: list[str]) -> dict[str, Any]:
    outcome = {"reason": reason, "allowed_decisions": allowed_decisions, "evidence_refs": evidence_refs}
    attempt["outcome"] = outcome
    return outcome


def _managed_result(run: dict[str, Any]) -> dict[str, Any]:
    attempt = _active_attempt(run)
    return {"run_id": run["run_id"], "state": run["state"], "attempt_id": attempt["attempt_id"], "outcome": attempt["outcome"]}


def _adapter_call(adapter: Any, name: str, *args: Any) -> Any:
    method = adapter.get(name) if isinstance(adapter, dict) else getattr(adapter, name, None)
    if not callable(method):
        raise HarnessError(f"host adapter missing `{name}`")
    return method(*args)


def _adapter_capabilities(adapter: Any) -> dict[str, str]:
    capabilities = _adapter_call(adapter, "capabilities")
    if not isinstance(capabilities, dict):
        raise HarnessError("host adapter capabilities must be a mapping")
    for mode, level in capabilities.items():
        if not isinstance(mode, str) or level not in CAPABILITY_LEVELS:
            raise HarnessError("host adapter capabilities contain invalid entry")
    return capabilities


def _approval_matches(approval: dict[str, Any], gate: str, path: str, attempt_id: str, ttl_seconds: int, now: datetime) -> bool:
    if approval["gate"] != gate or approval["attempt_id"] != attempt_id:
        return False
    issued_at = _parse_timestamp(approval["issued_at"])
    if issued_at > now or now - issued_at > timedelta(seconds=ttl_seconds):
        return False
    return _path_matches(path, approval["paths"])


def _gate_blockers(packet: dict[str, Any], paths: list[str], now: datetime) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for path in paths:
        for gate, patterns in packet["approval_gates"].items():
            if not _path_matches(path, patterns):
                continue
            approved = any(
                _approval_matches(
                    approval,
                    gate,
                    path,
                    packet["attempt_id"],
                    packet["retry_policy"]["approval_ttl_seconds"],
                    now,
                )
                for approval in packet["approvals"]
            )
            if not approved:
                blockers.append({"kind": "approval", "gate": gate, "path": path})
    return blockers


def _collect_changes(root: Path, base_commit: str) -> list[dict[str, str]]:
    status, stdout, stderr = _run_command(root, ["git", "diff", "--name-status", "-z", base_commit, "--"])
    if status:
        raise HarnessError(f"could not read changed paths: {stderr.strip()}")
    tokens = stdout.split("\0")
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status_code = tokens[index]
        index += 1
        if status_code[:1] in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise HarnessError("malformed renamed change-set entry")
            changes.append({"path": _safe_path(tokens[index]), "kind": "renamed_from"})
            changes.append({"path": _safe_path(tokens[index + 1]), "kind": "renamed_to"})
            index += 2
            continue
        if index >= len(tokens):
            raise HarnessError("malformed change-set entry")
        kind = {"A": "added", "M": "modified", "D": "deleted", "T": "type_changed", "U": "unmerged"}.get(status_code[:1], status_code[:1].lower())
        changes.append({"path": _safe_path(tokens[index]), "kind": kind})
        index += 1
    status, stdout, stderr = _run_command(root, ["git", "ls-files", "--others", "--exclude-standard", "-z"])
    if status:
        raise HarnessError(f"could not read untracked paths: {stderr.strip()}")
    seen = {(change["path"], change["kind"]) for change in changes}
    for path in stdout.split("\0"):
        if path and (_safe_path(path), "untracked") not in seen:
            changes.append({"path": _safe_path(path), "kind": "untracked"})
    return changes


def _validate_managed_claim(claim: Any, role: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(claim, dict) or claim.get("kind") != role["result_kind"]:
        raise HarnessError("managed claim has invalid result kind")
    for field in role["required_fields"]:
        value = claim.get(field)
        if field in {"changed_files", "findings"}:
            _string_list(value, f"managed claim {field}")
        elif not isinstance(value, str) or not value:
            raise HarnessError(f"managed claim missing required field `{field}`")
    frictions = claim.get("frictions", [])
    if not isinstance(frictions, list):
        raise HarnessError("managed claim frictions must be a list")
    for friction in frictions:
        if not isinstance(friction, dict) or not isinstance(friction.get("category"), str) or not friction["category"]:
            raise HarnessError("managed claim friction must have category")
    return copy.deepcopy(claim)


def _verify_managed(
    root: Path,
    packet: dict[str, Any],
    *,
    run_check: CheckRunner,
    collect_changes: ChangeCollector,
    now: datetime,
) -> dict[str, Any]:
    changes = collect_changes(root, packet["base_commit"])
    normalized_changes: list[dict[str, str]] = []
    blockers: list[dict[str, str]] = []
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("path"), str) or not isinstance(change.get("kind"), str):
            raise HarnessError("change-set entry must contain path and kind")
        path = _safe_path(change["path"])
        normalized_changes.append({"path": path, "kind": change["kind"]})
        if not _path_matches(path, packet["allowed_paths"]):
            blockers.append({"kind": "scope", "path": path})
    blockers.extend(_gate_blockers(packet, [change["path"] for change in normalized_changes], now))

    checks: dict[str, dict[str, Any]] = {}
    for name, command in packet["checks"].items():
        code, stdout, stderr = run_check(command)
        checks[name] = {"name": name, "command": command, "exit_code": code, "stdout": stdout[:1000], "stderr": stderr[:1000]}
        if code:
            blockers.append({"kind": "check", "name": name})

    criteria: list[dict[str, Any]] = []
    for criterion in packet["acceptance_criteria"]:
        kind = criterion["kind"]
        result: dict[str, Any] = {"id": criterion["id"], "kind": kind}
        if kind == "check":
            check = checks[criterion["check"]]
            result.update({"status": "proven" if check["exit_code"] == 0 else "failed", "evidence_ref": f"checks.{criterion['check']}"})
        elif kind == "change_set":
            proven = all(any(_path_matches(change["path"], [pattern]) for change in normalized_changes) for pattern in criterion["paths"])
            result.update({"status": "proven" if proven else "failed", "evidence_ref": "change_set"})
        else:
            evidence = packet["review_evidence"] if kind == "review" else packet["manual_evidence"]
            result.update({"status": "proven" if isinstance(evidence, dict) else "review_required", "evidence_ref": kind})
        if result["status"] == "failed":
            blockers.append({"kind": "criterion", "id": criterion["id"]})
        criteria.append(result)
    return {"change_set": normalized_changes, "checks": list(checks.values()), "criteria": criteria, "blockers": blockers}


def _outcome_for_verification(verification: dict[str, Any], retry_policy: dict[str, Any]) -> tuple[str, list[str]]:
    kinds = {blocker["kind"] for blocker in verification["blockers"]}
    if "scope" in kinds:
        return "scope_escape", ["block"]
    if "approval" in kinds:
        return "approval_required", ["request_approval", "retry", "block"]
    if kinds:
        decisions = ["block"]
        if "verification_failed" in retry_policy["retryable_reasons"]:
            decisions = ["retry", "escalate", "block"]
        return "verification_failed", decisions
    if any(criterion["status"] == "review_required" for criterion in verification["criteria"]):
        decisions = ["block"]
        if "review_required" in retry_policy["retryable_reasons"]:
            decisions = ["retry", "block"]
        return "review_required", decisions
    return "verification_passed", ["accept", "block"]


def _record_failure(root: Path, run: dict[str, Any], policy: dict[str, Any], attempt: dict[str, Any], reason: str, detail: str) -> dict[str, Any]:
    attempt["frictions"].append({"category": "adapter", "detail": detail})
    decisions = ["block"]
    if reason in attempt["packet"]["retry_policy"]["retryable_reasons"]:
        decisions = ["retry", "escalate", "block"]
    _set_outcome(attempt, reason, decisions, ["frictions"])
    _transition(run, policy["states"], "awaiting_decision", reason)
    _write_run(root, run)
    return _managed_result(run)


def _execute_attempt(
    root: Path,
    run: dict[str, Any],
    policy: dict[str, Any],
    adapter: Any,
    *,
    run_check: CheckRunner,
    collect_changes: ChangeCollector,
    now: datetime,
) -> dict[str, Any]:
    attempt = _active_attempt(run)
    packet = attempt["packet"]
    planned_blockers = _gate_blockers(packet, packet["planned_write_paths"], now)
    attempt["authorization"] = {"planned_write_paths": packet["planned_write_paths"], "blockers": planned_blockers}
    if planned_blockers:
        _set_outcome(attempt, "approval_required", ["request_approval", "retry", "block"], ["authorization"])
        _transition(run, policy["states"], "awaiting_decision", "approval_required")
        _write_run(root, run)
        return _managed_result(run)
    try:
        capabilities = _adapter_capabilities(adapter)
    except Exception as exc:
        return _record_failure(root, run, policy, attempt, "dispatch_failed", str(exc))
    mode = packet["orchestration"]["name"]
    if mode != "single_agent" or capabilities.get(mode) != "enforced":
        _set_outcome(attempt, "execution_mode_unavailable", ["block"], ["capabilities"])
        _transition(run, policy["states"], "awaiting_decision", "execution_mode_unavailable")
        _write_run(root, run)
        return _managed_result(run)

    _transition(run, policy["states"], "running", "dispatch")
    lane = attempt["lanes"][0]
    handle = None
    try:
        workspace = _adapter_call(adapter, "prepare_workspace", lane, packet)
        if not isinstance(workspace, dict):
            raise HarnessError("host adapter workspace must be an object")
        lane["workspace"] = copy.deepcopy(workspace)
        handle = _adapter_call(adapter, "dispatch_lane", lane, packet, workspace, None)
        claim = _adapter_call(adapter, "collect_claim", handle)
    except Exception as exc:
        if handle is not None:
            try:
                _adapter_call(adapter, "cancel_lane", handle)
            except Exception:
                pass
        return _record_failure(root, run, policy, attempt, "dispatch_failed", str(exc))
    try:
        role = _load_roles(root)[lane["role"]]
        normalized_claim = _validate_managed_claim(claim, role)
    except (HarnessError, KeyError) as exc:
        return _record_failure(root, run, policy, attempt, "claim_invalid", str(exc))
    attempt["claims"].append({"lane_id": lane["lane_id"], "claim": normalized_claim})
    for friction in normalized_claim.get("frictions", []):
        record = {"category": friction["category"], "lane_id": lane["lane_id"]}
        if isinstance(friction.get("detail"), str) and friction["detail"]:
            record["detail"] = friction["detail"]
        attempt["frictions"].append(record)
    _transition(run, policy["states"], "observed", "claim_collected")
    _transition(run, policy["states"], "verifying", "verify")
    try:
        verification = _verify_managed(root, packet, run_check=run_check, collect_changes=collect_changes, now=now)
    except Exception as exc:
        return _record_failure(root, run, policy, attempt, "verification_failed", str(exc))
    attempt["evidence"] = verification
    reason, decisions = _outcome_for_verification(verification, packet["retry_policy"])
    _set_outcome(attempt, reason, decisions, ["evidence"])
    _transition(run, policy["states"], "awaiting_decision", reason)
    _write_run(root, run)
    return _managed_result(run)


def run_managed(
    root: Path,
    request: dict[str, Any] | None,
    adapter: Any,
    *,
    run_id: str | None = None,
    run_check: CheckRunner | None = None,
    collect_changes: ChangeCollector | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    _validate_policy(root)
    policy = _load_policy(root)
    if run_id is None:
        if request is None:
            raise HarnessError("managed run request is required")
        run_id = _safe_run_id(request.get("run_id") or uuid.uuid4().hex)
        if _run_path(root, run_id).exists():
            raise HarnessError(f"run `{run_id}` already exists")
        packet = resolve_managed_packet(root, request, attempt_id="attempt-1")
        run = _new_run(request, run_id)
        _transition(run, policy["states"], "planned", "preflight")
        _append_attempt(run, packet)
        _write_run(root, run)
    else:
        run_id = _safe_run_id(run_id)
        run = _load_run(root, run_id)
        if request is not None and request != run["request"]:
            raise HarnessError("managed continuation request does not match run record")
        if run["state"] != "planned":
            raise HarnessError(f"run `{run_id}` is not ready to execute")
    runner = run_check or (lambda command: _run_command(root, command))
    collector = collect_changes or _collect_changes
    return _execute_attempt(root, run, policy, adapter, run_check=runner, collect_changes=collector, now=now or datetime.now(UTC))


def _successor_request(run: dict[str, Any], successor: Any) -> dict[str, Any]:
    request = copy.deepcopy(run["request"])
    if successor is None:
        return request
    if not isinstance(successor, dict):
        raise HarnessError("decision successor must be an object")
    allowed = {"execution_mode", "allowed_paths", "planned_write_paths", "acceptance_criteria", "base_ref", "approvals", "review_evidence", "manual_evidence", "lanes"}
    unknown = set(successor) - allowed
    if unknown:
        raise HarnessError(f"decision successor has unsupported fields: {', '.join(sorted(unknown))}")
    request.update(copy.deepcopy(successor))
    request["run_id"] = run["run_id"]
    return request


def apply_controller_decision(root: Path, run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    _validate_policy(root)
    policy = _load_policy(root)
    run = _load_run(root, _safe_run_id(run_id))
    if run["state"] != "awaiting_decision":
        raise HarnessError(f"run `{run_id}` is not awaiting controller decision")
    kind = _required_string(decision.get("kind"), "decision kind")
    if kind not in DECISION_KINDS:
        raise HarnessError(f"unsupported decision kind `{kind}`")
    attempt = _active_attempt(run)
    outcome = attempt.get("outcome")
    if not isinstance(outcome, dict) or kind not in outcome.get("allowed_decisions", []):
        raise HarnessError(f"decision `{kind}` is not allowed for current outcome")
    stored = copy.deepcopy(decision)
    stored["at"] = _timestamp()
    attempt["decision"] = stored
    attempt.setdefault("decision_history", []).append(stored)
    if kind == "accept":
        criteria = attempt.get("evidence", {}).get("criteria", [])
        if not criteria or any(criterion.get("status") != "proven" for criterion in criteria):
            raise HarnessError("cannot accept run without proven criteria")
        _transition(run, policy["states"], "accepted", "controller_accept")
    elif kind == "block":
        _transition(run, policy["states"], "blocked", "controller_block")
    elif kind == "request_approval":
        _transition(run, policy["states"], "awaiting_decision", "controller_request_approval")
    else:
        retry_policy = attempt["packet"]["retry_policy"]
        if outcome["reason"] not in retry_policy["retryable_reasons"] and outcome["reason"] != "approval_required":
            raise HarnessError(f"outcome `{outcome['reason']}` is not retryable")
        if len(run["attempts"]) >= retry_policy["max_attempts"]:
            _set_outcome(attempt, "retry_exhausted", ["block"], ["decision"])
            _transition(run, policy["states"], "blocked", "retry_exhausted")
        else:
            packet = resolve_managed_packet(
                root,
                _successor_request(run, decision.get("successor")),
                attempt_id=f"attempt-{len(run['attempts']) + 1}",
            )
            _append_attempt(run, packet)
            _transition(run, policy["states"], "planned", f"controller_{kind}")
    _write_run(root, run)
    return _managed_result(run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve, run, and verify harness tasks.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "verify"):
        command = subparsers.add_parser(name)
        command.add_argument("--task", required=True)
        if name == "verify":
            command.add_argument("--claim", required=True)
    run_command = subparsers.add_parser("run")
    run_command.add_argument("--task")
    run_command.add_argument("--run-id")
    decision_command = subparsers.add_parser("decision")
    decision_command.add_argument("--run-id", required=True)
    decision_command.add_argument("--decision", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo_root).resolve()
        if args.command == "preflight":
            result = resolve_task(root, _load_json(Path(args.task)))
        elif args.command == "verify":
            result = verify_task(root, _load_json(Path(args.task)), _load_json(Path(args.claim)))
        elif args.command == "run":
            if not args.task and not args.run_id:
                raise HarnessError("run requires --task or --run-id")
            task = _load_json(Path(args.task)) if args.task else None
            result = run_managed(root, task, {"capabilities": lambda: {}}, run_id=args.run_id)
        else:
            result = apply_controller_decision(root, args.run_id, _load_json(Path(args.decision)))
    except HarnessError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if args.command == "preflight" or result.get("status") == "verified" or result.get("state") == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
