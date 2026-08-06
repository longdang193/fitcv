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
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib
from typing import Any, Callable
import uuid

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_coordination import PlanCoordination, PlanCoordinationError, PlanTask, load_plan_coordination


class HarnessError(ValueError):
    pass


class ClaimError(HarnessError):
    pass


CheckRunner = Callable[[list[str]], tuple[int, str, str]]
ChangeCollector = Callable[[Path, str], list[dict[str, str]]]

MANAGED_VERSION = 3
LEGACY_MANAGED_VERSION = 2
CAPABILITY_LEVELS = {"enforced", "advisory", "unavailable"}
CRITERION_KINDS = {"check", "change_set", "review", "manual", "validator"}
DECISION_KINDS = {"accept", "retry", "escalate", "request_approval", "waive", "block"}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")
FRICTION_EVENT_VERSION = 1
FRICTION_EVENT_KINDS = {"observed", "resolution"}
FRICTION_SOURCES = {"agent", "host", "validator", "check", "controller"}
FRICTION_PHASES = {"claim", "dispatch", "integration", "check", "validator", "decision"}
FRICTION_RESOLUTIONS = {"keep", "revise", "remove", "pending"}


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


def _friction_policy(root: Path) -> dict[str, int]:
    policy = _load_policy(root)
    friction_policy = policy.get("friction_policy")
    if not isinstance(friction_policy, dict):
        raise HarnessError("missing friction policy")
    expected = {"event_version", "minimum_distinct_runs", "window_days"}
    if set(friction_policy) != expected:
        raise HarnessError("invalid friction policy")
    if friction_policy["event_version"] != FRICTION_EVENT_VERSION:
        raise HarnessError("unsupported friction event version")
    if any(
        not isinstance(friction_policy[name], int)
        or isinstance(friction_policy[name], bool)
        or friction_policy[name] < 1
        for name in ("minimum_distinct_runs", "window_days")
    ):
        raise HarnessError("invalid friction policy")
    return friction_policy


def _canonical_execution_mode(
    policy: dict[str, Any], value: Any, *, allow_alias: bool, default: str
) -> str:
    execution_mode = _required_string(value if value is not None else default, "execution_mode")
    orchestration = policy["orchestration"]
    if execution_mode in orchestration:
        return execution_mode
    for name, topology in orchestration.items():
        if execution_mode in topology["aliases"]:
            if allow_alias:
                return name
            raise HarnessError(
                f"legacy execution mode `{execution_mode}`; use canonical execution mode `{name}`"
            )
    raise HarnessError(f"unknown execution mode `{execution_mode}`")


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
    execution_mode = _canonical_execution_mode(
        policy,
        task.get("execution_mode"),
        allow_alias=True,
        default="single_agent",
    )
    if execution_mode not in route["execution_modes"]:
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
        "agent_identity": _load_agent_identity(root, route["template"]),
        "role": route["role"],
        "rules": list(dict.fromkeys([*route["rules"], *orchestration["rules"]])),
        "skills": route["skills"],
        "tools": route["tools"],
        "workspace": route["workspace"],
        "orchestration": {
            "name": execution_mode,
            "work_scheduling": orchestration["work_scheduling"],
            "max_parallel_writers": orchestration["max_parallel_writers"],
            "workspace_mode": orchestration["workspace_mode"],
            "validator_role": orchestration["validator_role"],
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


def _load_agent_identity(root: Path, template: str) -> dict[str, str]:
    path = root / "agents" / f"{template}.toml"
    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise HarnessError(f"invalid agent template `{template}`") from exc
    if payload.get("name") != template:
        raise HarnessError(f"agent template `{template}` has mismatched name")
    fields = {
        "model_provider": payload.get("model_provider"),
        "model": payload.get("model"),
        "reasoning_effort": payload.get("model_reasoning_effort"),
    }
    if not all(isinstance(value, str) and value for value in fields.values()):
        raise HarnessError(f"agent template `{template}` has invalid model identity")
    return {"template": template, **fields}


def _route_packet(policy: dict[str, Any], task_type: str, execution_mode: str) -> dict[str, Any]:
    route = policy["routes"].get(task_type)
    if not isinstance(route, dict):
        raise HarnessError(f"unknown task type `{task_type}`")
    if execution_mode not in route["execution_modes"]:
        raise HarnessError(f"unsupported execution mode `{execution_mode}` for task type `{task_type}`")
    orchestration = policy["orchestration"][execution_mode]
    tool_bindings = [
        {
            "tool": name,
            "host_kind": policy["tools"][name]["host_kind"],
            "writer_access": policy["tools"][name]["writer_access"],
            "validator_access": policy["tools"][name]["validator_access"],
            "root_probe": policy["tools"][name]["root_probe"],
        }
        for name in route["tools"]
    ]
    return {
        "task_type": task_type,
        "template": route["template"],
        "role": route["role"],
        "rules": list(dict.fromkeys([*route["rules"], *orchestration["rules"]])),
        "skills": route["skills"],
        "tools": route["tools"],
        "tool_bindings": tool_bindings,
        "workspace": route["workspace"],
        "orchestration": {
            "name": execution_mode,
            "work_scheduling": orchestration["work_scheduling"],
            "max_parallel_writers": orchestration["max_parallel_writers"],
            "workspace_mode": orchestration["workspace_mode"],
            "validator_role": orchestration["validator_role"],
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


def _resolve_runtime_provider(policy: dict[str, Any], task_type: str, value: Any) -> dict[str, Any]:
    route = policy["routes"].get(task_type)
    if not isinstance(route, dict):
        raise HarnessError(f"unknown task type `{task_type}`")
    provider_id = route["default_runtime_provider"] if value is None else _required_string(value, "runtime_provider_id")
    if provider_id not in route["runtime_providers"]:
        raise HarnessError(f"runtime provider `{provider_id}` is not allowed for task type `{task_type}`")
    provider = policy["runtime_providers"].get(provider_id)
    if not isinstance(provider, dict) or not isinstance(provider.get("contract_version"), int):
        raise HarnessError(f"unknown runtime provider `{provider_id}`")
    return {"provider_id": provider_id, "contract_version": provider["contract_version"]}


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


ACTIVE_RUN_STATES = {"planned", "running", "observed", "verifying", "awaiting_decision"}
TERMINAL_RUN_STATES = {"accepted", "unvalidated", "blocked"}
HANDOFF_FIELDS = {"last_verified_fact", "next_action", "blocker_or_decision"}


def _all_runs(root: Path) -> list[dict[str, Any]]:
    runs_root = root / ".harness" / "runs"
    if not runs_root.is_dir():
        return []
    runs: list[dict[str, Any]] = []
    for path in sorted(runs_root.glob("*/run.json")):
        payload = _load_json(path)
        run_id = payload.get("run_id")
        if not isinstance(run_id, str):
            raise HarnessError(f"invalid run record `{path}`")
        runs.append(_load_run(root, run_id))
    return runs


def _run_sort_key(run: dict[str, Any]) -> tuple[str, str]:
    history = run.get("state_history")
    if isinstance(history, list) and history and isinstance(history[-1], dict):
        timestamp = history[-1].get("at")
        if isinstance(timestamp, str):
            return timestamp, run["run_id"]
    return "", run["run_id"]


def _matching_plan_runs(root: Path, plan_ref: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for run in _all_runs(root):
        if not run["attempts"] or not isinstance(run["attempts"][-1], dict):
            continue
        attempt = run["attempts"][-1]
        packet = attempt.get("packet")
        if isinstance(packet, dict) and packet.get("plan_ref") == plan_ref:
            matches.append((run, attempt))
    return matches


def coordination_status(root: Path, plan_ref: str) -> dict[str, Any]:
    try:
        coordination = load_plan_coordination(root, plan_ref, require_active=True)
    except PlanCoordinationError as exc:
        raise HarnessError(str(exc)) from exc
    if coordination is None:
        raise HarnessError(f"plan `{plan_ref}` has no coordination manifest")
    runs_by_task: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {
        task.task_id: [] for task in coordination.tasks
    }
    for run, attempt in _matching_plan_runs(root, coordination.plan_ref):
        packet = attempt.get("packet", {})
        task_id = packet.get("plan_task_id") if isinstance(packet, dict) else None
        if task_id in runs_by_task:
            runs_by_task[task_id].append((run, attempt))

    statuses: dict[str, dict[str, Any]] = {}

    def derive(task: PlanTask) -> dict[str, Any]:
        if task.task_id in statuses:
            return statuses[task.task_id]
        matching = sorted(runs_by_task[task.task_id], key=lambda item: _run_sort_key(item[0]))
        if matching:
            run, attempt = matching[-1]
            state = run["state"]
            if state in ACTIVE_RUN_STATES:
                status = {"id": task.task_id, "state": "active", "run_id": run["run_id"], "reason": state}
            elif state == "accepted":
                status = {"id": task.task_id, "state": "done", "run_id": run["run_id"], "reason": state}
            elif state in TERMINAL_RUN_STATES:
                status = {"id": task.task_id, "state": "blocked", "run_id": run["run_id"], "reason": state}
            else:
                raise HarnessError(f"run `{run['run_id']}` has unsupported coordination state `{state}`")
            handoff = attempt.get("handoff")
            if isinstance(handoff, dict):
                status["handoff"] = copy.deepcopy(handoff)
            statuses[task.task_id] = status
            return status
        dependency_states = [derive(coordination.task(task_id))["state"] for task_id in task.depends_on]
        status = {
            "id": task.task_id,
            "state": "ready" if all(state == "done" for state in dependency_states) else "blocked",
            "reason": "ready" if all(state == "done" for state in dependency_states) else "waiting_dependencies",
        }
        statuses[task.task_id] = status
        return status

    return {
        "plan_ref": coordination.plan_ref,
        "target_branch": coordination.target_branch,
        "base_ref": coordination.base_ref,
        "plan_digest": coordination.digest,
        "tasks": [derive(task) for task in coordination.tasks],
    }


def record_controller_handoff(root: Path, run_id: str, handoff: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(handoff, dict) or set(handoff) != HANDOFF_FIELDS:
        raise HarnessError(f"handoff must contain only: {', '.join(sorted(HANDOFF_FIELDS))}")
    normalized = {field: _required_string(handoff.get(field), f"handoff {field}") for field in HANDOFF_FIELDS}
    run = _load_run(root, _safe_run_id(run_id))
    if run["state"] in TERMINAL_RUN_STATES:
        raise HarnessError("cannot record handoff for terminal run")
    attempt = _active_attempt(run)
    packet = attempt.get("packet")
    if not isinstance(packet, dict) or "plan_ref" not in packet or "plan_task_id" not in packet:
        raise HarnessError("controller handoff requires a coordinated run")
    attempt["handoff"] = {**normalized, "timestamp": _timestamp()}
    _write_run(root, run)
    return {"run_id": run["run_id"], "handoff": copy.deepcopy(attempt["handoff"])}


def _planned_paths_overlap(left: list[str], right: list[str]) -> bool:
    return any(_path_matches(left_path, [right_path]) or _path_matches(right_path, [left_path]) for left_path in left for right_path in right)


def _admit_coordinated_packet(root: Path, packet: dict[str, Any]) -> None:
    if "plan_ref" not in packet:
        return
    plan_ref = _required_string(packet.get("plan_ref"), "packet plan_ref")
    task_id = _required_string(packet.get("plan_task_id"), "packet plan_task_id")
    status = coordination_status(root, plan_ref)
    task_status = next((task for task in status["tasks"] if task["id"] == task_id), None)
    if not isinstance(task_status, dict) or task_status["state"] != "ready":
        reason = task_status.get("reason", "missing") if isinstance(task_status, dict) else "missing"
        raise HarnessError(f"coordinated task `{task_id}` is not ready: {reason}")
    for run in _all_runs(root):
        if run["state"] not in ACTIVE_RUN_STATES or not run["attempts"]:
            continue
        active_packet = run["attempts"][-1].get("packet")
        if not isinstance(active_packet, dict) or "plan_ref" not in active_packet:
            continue
        if active_packet["plan_ref"] == plan_ref:
            raise HarnessError(f"coordinated task activation blocked by active run `{run['run_id']}`")
        try:
            active_coordination = load_plan_coordination(root, active_packet["plan_ref"], require_active=False)
        except PlanCoordinationError as exc:
            raise HarnessError(f"cannot evaluate active coordinated run `{run['run_id']}`: {exc}") from exc
        if active_coordination is None or active_coordination.target_branch != status["target_branch"]:
            continue
        if _planned_paths_overlap(packet["planned_write_paths"], active_packet.get("planned_write_paths", [])):
            raise HarnessError(f"coordinated task paths conflict with active run `{run['run_id']}`")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HarnessError("approval issued_at must be an ISO-8601 timestamp") from exc


def _friction_events_path(root: Path) -> Path:
    return root / ".harness" / "friction-events.jsonl"


def _friction_time(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HarnessError("friction event timestamp must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None:
        raise HarnessError("friction event timestamp must include timezone")
    return timestamp.astimezone(UTC)


def _friction_fingerprint(
    *,
    route: str,
    provider: str,
    mode: str,
    lane_kind: str,
    phase: str,
    source: str,
    code: str,
) -> str:
    payload = {
        "version": FRICTION_EVENT_VERSION,
        "route": route,
        "provider": provider,
        "mode": mode,
        "lane_kind": lane_kind,
        "phase": phase,
        "source": source,
        "code": code,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return f"v{FRICTION_EVENT_VERSION}:{digest}"


def _append_friction_event(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    path = _friction_events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def _read_friction_events(root: Path) -> list[dict[str, Any]]:
    path = _friction_events_path(root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"invalid friction event at line {line_number}") from exc
        if not isinstance(event, dict) or event.get("version") != FRICTION_EVENT_VERSION:
            raise HarnessError(f"invalid friction event at line {line_number}")
        if event.get("kind") not in FRICTION_EVENT_KINDS or not isinstance(event.get("event_id"), str) or not event["event_id"]:
            raise HarnessError(f"invalid friction event at line {line_number}")
        _friction_time(_required_string(event.get("occurred_at"), "friction event occurred_at"))
        if event["kind"] == "observed":
            required = {
                "run_id", "attempt_id", "route", "provider", "mode", "lane_kind",
                "phase", "source", "code", "evidence_ref", "fingerprint",
            }
            if (
                not required.issubset(event)
                or not all(isinstance(event[name], str) and event[name] for name in required)
                or event["source"] not in FRICTION_SOURCES
                or event["phase"] not in FRICTION_PHASES
            ):
                raise HarnessError(f"invalid friction event at line {line_number}")
        else:
            required = {"run_id", "fingerprint", "decision", "observed_event_ids"}
            observed_event_ids = event.get("observed_event_ids")
            if (
                not required.issubset(event)
                or not all(isinstance(event[name], str) and event[name] for name in required - {"observed_event_ids"})
                or not isinstance(observed_event_ids, list)
                or not observed_event_ids
                or not all(isinstance(event_id, str) and event_id for event_id in observed_event_ids)
                or event["decision"] not in FRICTION_RESOLUTIONS
            ):
                raise HarnessError(f"invalid friction event at line {line_number}")
        events.append(event)
    return events


def record_friction_event(
    root: Path,
    *,
    run_id: str,
    attempt_id: str,
    packet: dict[str, Any],
    lane: dict[str, Any] | None,
    source: str,
    phase: str,
    code: str,
    evidence_ref: str,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    _friction_policy(root)
    if source not in FRICTION_SOURCES:
        raise HarnessError("unsupported friction source")
    if phase not in FRICTION_PHASES:
        raise HarnessError("unsupported friction phase")
    route = _required_string(packet.get("task_type"), "friction route")
    provider = packet.get("runtime_provider")
    if not isinstance(provider, dict):
        raise HarnessError("friction packet lacks runtime provider")
    provider_id = _required_string(provider.get("provider_id"), "friction provider")
    contract_version = provider.get("contract_version")
    if not isinstance(contract_version, int):
        raise HarnessError("friction packet has invalid runtime provider")
    orchestration = packet.get("orchestration")
    if not isinstance(orchestration, dict):
        raise HarnessError("friction packet lacks orchestration")
    mode = _required_string(orchestration.get("name"), "friction mode")
    lane_kind = "system" if lane is None else _required_string(lane.get("kind"), "friction lane kind")
    timestamp = (occurred_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    event = {
        "version": FRICTION_EVENT_VERSION,
        "kind": "observed",
        "event_id": f"friction-{uuid.uuid4().hex}",
        "run_id": _safe_run_id(run_id),
        "attempt_id": _required_string(attempt_id, "friction attempt_id"),
        "route": route,
        "provider": f"{provider_id}:{contract_version}",
        "mode": mode,
        "lane_kind": lane_kind,
        "phase": phase,
        "source": source,
        "code": _required_string(code, "friction code"),
        "evidence_ref": _required_string(evidence_ref, "friction evidence_ref"),
        "occurred_at": timestamp,
    }
    event["fingerprint"] = _friction_fingerprint(
        route=event["route"],
        provider=event["provider"],
        mode=event["mode"],
        lane_kind=event["lane_kind"],
        phase=event["phase"],
        source=event["source"],
        code=event["code"],
    )
    return _append_friction_event(root, event)


def friction_report(root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    policy = _friction_policy(root)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = current - timedelta(days=policy["window_days"])
    events = _read_friction_events(root)
    resolved_at: dict[str, datetime] = {}
    for event in events:
        if event["kind"] != "resolution":
            continue
        resolved = _friction_time(event["occurred_at"])
        if resolved <= current:
            resolved_at[event["fingerprint"]] = max(resolved_at.get(event["fingerprint"], resolved), resolved)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event["kind"] != "observed":
            continue
        occurred_at = _friction_time(event["occurred_at"])
        if not cutoff <= occurred_at <= current or occurred_at <= resolved_at.get(event["fingerprint"], datetime.min.replace(tzinfo=UTC)):
            continue
        grouped.setdefault(event["fingerprint"], []).append(event)
    candidates = []
    for fingerprint, observed in sorted(grouped.items()):
        run_ids = sorted({event["run_id"] for event in observed})
        if len(run_ids) < policy["minimum_distinct_runs"]:
            continue
        candidates.append({
            "fingerprint": fingerprint,
            "event_ids": sorted(event["event_id"] for event in observed),
            "run_ids": run_ids,
            "event_count": len(observed),
            "distinct_run_count": len(run_ids),
            "first_observed_at": min(event["occurred_at"] for event in observed),
            "last_observed_at": max(event["occurred_at"] for event in observed),
        })
    return {
        "version": FRICTION_EVENT_VERSION,
        "minimum_distinct_runs": policy["minimum_distinct_runs"],
        "window_days": policy["window_days"],
        "candidates": candidates,
    }


def resolve_friction(
    root: Path,
    run_id: str,
    fingerprint: str,
    decision: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if decision not in FRICTION_RESOLUTIONS:
        raise HarnessError("unsupported friction resolution")
    run = _load_run(root, _safe_run_id(run_id))
    if run.get("state") != "accepted" or run.get("request", {}).get("task_type") != "harness_improvement":
        raise HarnessError("friction resolution requires accepted harness_improvement run")
    candidate = next((item for item in friction_report(root, now=now)["candidates"] if item["fingerprint"] == fingerprint), None)
    if candidate is None:
        raise HarnessError("friction resolution requires current candidate")
    event = {
        "version": FRICTION_EVENT_VERSION,
        "kind": "resolution",
        "event_id": f"friction-resolution-{uuid.uuid4().hex}",
        "run_id": run["run_id"],
        "fingerprint": fingerprint,
        "decision": decision,
        "observed_event_ids": candidate["event_ids"],
        "occurred_at": ((now or datetime.now(UTC)).astimezone(UTC).isoformat()),
    }
    return _append_friction_event(root, event)


def _validate_criteria(value: Any, checks: dict[str, list[str]]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise HarnessError("acceptance_criteria must be a non-empty list")
    criteria: list[dict[str, Any]] = []
    seen: set[str] = set()
    validator_count = 0
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
        if kind == "validator":
            if criterion_id != "validator" or set(raw) != {"id", "kind"}:
                raise HarnessError("validator criterion must be exactly `{id: validator, kind: validator}`")
            validator_count += 1
        criteria.append(criterion)
    if validator_count > 1:
        raise HarnessError("duplicate validator criterion")
    if not validator_count:
        criteria.append({"id": "validator", "kind": "validator"})
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
    if packet["orchestration"]["work_scheduling"] == "single":
        role = packet["role"]
        work_lanes = [{
            "lane_id": "primary",
            "kind": "work",
            "role": role,
            "allowed_paths": allowed_paths,
            "dependencies": [],
            "workspace_mode": packet["orchestration"]["workspace_mode"],
            "write_capable": bool(roles[role]["writes"]),
            "required_claim_kind": roles[role]["result_kind"],
            "claim_schema": {
                "required_fields": copy.deepcopy(roles[role]["required_fields"]),
                "field_constraints": copy.deepcopy(roles[role].get("field_constraints", {})),
            },
            "claim_schema": {
                "required_fields": copy.deepcopy(roles[role]["required_fields"]),
                "field_constraints": copy.deepcopy(roles[role].get("field_constraints", {})),
            },
        }]
    else:
        if not isinstance(value, list) or not value:
            raise HarnessError("lanes must be a non-empty list for non-single topology")
        work_lanes = []
        lane_ids: set[str] = set()
        for raw in value:
            if not isinstance(raw, dict):
                raise HarnessError("lane must be an object")
            lane_id = _required_string(raw.get("lane_id"), "lane_id")
            if lane_id in {"integrate", "validate"} or lane_id in lane_ids:
                raise HarnessError(f"duplicate or reserved lane_id `{lane_id}`")
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
            work_lanes.append({
                "lane_id": lane_id,
                "kind": "work",
                "role": role,
                "allowed_paths": _safe_paths(raw.get("allowed_paths"), "lane allowed_paths", required=True),
                "dependencies": dependencies,
                "workspace_mode": workspace_mode,
                "write_capable": write_capable,
                "required_claim_kind": roles[role]["result_kind"],
                "claim_schema": {
                    "required_fields": copy.deepcopy(roles[role]["required_fields"]),
                    "field_constraints": copy.deepcopy(roles[role].get("field_constraints", {})),
                },
                "claim_schema": {
                    "required_fields": copy.deepcopy(roles[role]["required_fields"]),
                    "field_constraints": copy.deepcopy(roles[role].get("field_constraints", {})),
                },
            })
    lane_ids = {lane["lane_id"] for lane in work_lanes}
    for lane in work_lanes:
        for dependency in lane["dependencies"]:
            if dependency == lane["lane_id"] or dependency not in lane_ids:
                raise HarnessError(f"lane `{lane['lane_id']}` has invalid dependency `{dependency}`")
    visiting: set[str] = set()
    visited: set[str] = set()
    dependencies = {lane["lane_id"]: lane["dependencies"] for lane in work_lanes}

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
    writable = [lane for lane in work_lanes if lane["write_capable"]]
    for index, lane in enumerate(writable):
        for other in writable[index + 1:]:
            if any(_patterns_overlap(path, other_path) for path in lane["allowed_paths"] for other_path in other["allowed_paths"]):
                raise HarnessError(f"writable lanes `{lane['lane_id']}` and `{other['lane_id']}` overlap")
    validator_role = packet["orchestration"]["validator_role"]
    validator = roles.get(validator_role)
    if not isinstance(validator, dict) or validator["writes"]:
        raise HarnessError(f"invalid validator role `{validator_role}`")
    workspace_mode = packet["orchestration"]["workspace_mode"]
    return [
        *work_lanes,
        {
            "lane_id": "integrate",
            "kind": "integrate",
            "role": None,
            "allowed_paths": allowed_paths,
            "dependencies": [lane["lane_id"] for lane in work_lanes],
            "workspace_mode": workspace_mode,
            "write_capable": False,
            "required_claim_kind": "integration_result",
        },
        {
            "lane_id": "validate",
            "kind": "validate",
            "role": validator_role,
            "allowed_paths": allowed_paths,
            "dependencies": ["integrate"],
            "workspace_mode": workspace_mode,
            "write_capable": False,
            "required_claim_kind": validator["result_kind"],
            "claim_schema": {
                "required_fields": copy.deepcopy(validator["required_fields"]),
                "field_constraints": copy.deepcopy(validator.get("field_constraints", {})),
            },
            "claim_schema": {
                "required_fields": copy.deepcopy(validator["required_fields"]),
                "field_constraints": copy.deepcopy(validator.get("field_constraints", {})),
            },
        },
    ]


def _normalize_managed_request(
    root: Path,
    policy: dict[str, Any],
    request: dict[str, Any],
) -> tuple[dict[str, Any], PlanCoordination | None, PlanTask | None]:
    version = request.get("version")
    if version not in {LEGACY_MANAGED_VERSION, MANAGED_VERSION}:
        raise HarnessError(f"managed request version must be {LEGACY_MANAGED_VERSION} or {MANAGED_VERSION}")
    normalized = copy.deepcopy(request)
    normalized["version"] = MANAGED_VERSION
    normalized["execution_mode"] = _canonical_execution_mode(
        policy,
        normalized.get("execution_mode"),
        allow_alias=version == LEGACY_MANAGED_VERSION,
        default="single_agent" if version == LEGACY_MANAGED_VERSION else "single_work_lane",
    )
    has_plan_ref = "plan_ref" in normalized
    has_plan_task_id = "plan_task_id" in normalized
    if has_plan_ref != has_plan_task_id:
        raise HarnessError("managed request requires both `plan_ref` and `plan_task_id`")
    if not has_plan_ref:
        return normalized, None, None
    plan_ref = _required_string(normalized["plan_ref"], "plan_ref")
    plan_task_id = _required_string(normalized["plan_task_id"], "plan_task_id")
    try:
        coordination = load_plan_coordination(root, plan_ref, require_active=True)
        if coordination is None:
            raise HarnessError(f"plan `{plan_ref}` has no coordination manifest")
        plan_task = coordination.task(plan_task_id)
    except PlanCoordinationError as exc:
        raise HarnessError(str(exc)) from exc
    derived = {
        "execution_mode": plan_task.execution_mode,
        "base_ref": coordination.base_ref,
        "planned_write_paths": list(plan_task.planned_write_paths),
    }
    for field, value in derived.items():
        if field in request and normalized.get(field) != value:
            raise HarnessError(f"managed request `{field}` conflicts with plan coordination")
        normalized[field] = value
    normalized["plan_ref"] = coordination.plan_ref
    normalized["plan_task_id"] = plan_task.task_id
    return normalized, coordination, plan_task


def resolve_managed_packet(root: Path, request: dict[str, Any], *, attempt_id: str) -> dict[str, Any]:
    _validate_policy(root)
    policy = _load_policy(root)
    request, coordination, plan_task = _normalize_managed_request(root, policy, request)
    task_type = _required_string(request.get("task_type"), "task_type")
    execution_mode = _required_string(request.get("execution_mode"), "execution_mode")
    packet = _route_packet(policy, task_type, execution_mode)
    runtime_provider = _resolve_runtime_provider(policy, task_type, request.get("runtime_provider_id"))
    role = _load_roles(root).get(packet["role"])
    if not isinstance(role, dict):
        raise HarnessError(f"unknown route role `{packet['role']}`")
    allowed_paths = _safe_paths(request.get("allowed_paths"), "allowed_paths", required=True)
    planned_write_paths = _safe_paths(request.get("planned_write_paths"), "planned_write_paths", required=bool(role["writes"]))
    if coordination is not None and any(not _path_matches(path, allowed_paths) for path in planned_write_paths):
        raise HarnessError("plan planned_write_paths must stay within managed allowed_paths")
    base_ref = _required_string(request.get("base_ref"), "base_ref")
    user_request = _required_string(request.get("user_request"), "user_request")
    packet.update({
        "version": MANAGED_VERSION,
        "attempt_id": attempt_id,
        "base_ref": base_ref,
        "base_commit": _resolve_commit(root, base_ref),
        "user_request": user_request,
        "runtime_provider": runtime_provider,
        "agent_identity": _load_agent_identity(root, packet["template"]),
        "allowed_paths": allowed_paths,
        "planned_write_paths": planned_write_paths,
        "acceptance_criteria": _validate_criteria(request.get("acceptance_criteria"), packet["checks"]),
        "approvals": _validate_approvals(request.get("approvals")),
        "review_evidence": copy.deepcopy(request.get("review_evidence")),
        "manual_evidence": copy.deepcopy(request.get("manual_evidence")),
    })
    if coordination is not None and plan_task is not None:
        packet.update({
            "plan_ref": coordination.plan_ref,
            "plan_task_id": plan_task.task_id,
            "plan_digest": coordination.digest,
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
        "friction_event_ids": [],
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


def _adapter_capabilities(adapter: Any, canonical_modes: set[str]) -> dict[str, str]:
    capabilities = _adapter_call(adapter, "capabilities")
    if not isinstance(capabilities, dict):
        raise HarnessError("host adapter capabilities must be a mapping")
    for mode, level in capabilities.items():
        if not isinstance(mode, str) or mode not in canonical_modes or level not in CAPABILITY_LEVELS:
            raise HarnessError("host adapter capabilities contain invalid entry")
    return capabilities


def _adapter_identity(adapter: Any, runtime_provider: dict[str, Any]) -> dict[str, Any]:
    identity = _adapter_call(adapter, "identity")
    if (
        not isinstance(identity, dict)
        or set(identity) != {"provider_id", "contract_version"}
        or not isinstance(identity.get("provider_id"), str)
        or not identity["provider_id"]
        or not isinstance(identity.get("contract_version"), int)
        or isinstance(identity["contract_version"], bool)
        or identity["contract_version"] < 1
    ):
        raise HarnessError("host adapter identity must contain provider_id and contract_version")
    if identity != runtime_provider:
        raise HarnessError("host adapter identity conflicts with packet runtime provider")
    return copy.deepcopy(identity)


def _record_tool_binding_evidence(
    attempt: dict[str, Any],
    lane: dict[str, Any],
    packet: dict[str, Any],
    workspace: dict[str, Any],
    evidence: Any,
) -> None:
    if not isinstance(workspace.get("path"), str) or not workspace["path"]:
        raise HarnessError("host adapter workspace must include path")
    if not isinstance(evidence, list):
        raise HarnessError("host adapter tool binding evidence must be a list")
    expected_access_key = "validator_access" if lane["kind"] == "validate" else "writer_access"
    expected = {binding["tool"]: binding for binding in packet["tool_bindings"]}
    observed: dict[str, dict[str, Any]] = {}
    for binding in evidence:
        if not isinstance(binding, dict) or not isinstance(binding.get("tool"), str):
            raise HarnessError("host adapter tool binding evidence contains invalid entry")
        tool = binding["tool"]
        if tool in observed or tool not in expected:
            raise HarnessError("host adapter tool binding evidence conflicts with packet")
        required = expected[tool]
        if (
            binding.get("host_kind") != required["host_kind"]
            or binding.get("access") != required[expected_access_key]
            or binding.get("root_probe") != required["root_probe"]
            or binding.get("workspace_root") != workspace["path"]
            or binding.get("verified") is not True
            or binding.get("runtime_provider") != packet["runtime_provider"]
        ):
            raise HarnessError(f"host adapter tool binding `{tool}` is not verified for packet workspace")
        observed[tool] = binding
    if set(observed) != set(expected):
        raise HarnessError("host adapter did not verify every packet-selected tool")
    attempt.setdefault("tool_binding_evidence", []).append({
        "lane_id": lane["lane_id"],
        "workspace": copy.deepcopy(workspace),
        "bindings": copy.deepcopy(evidence),
    })


def _record_lane_execution_evidence(
    attempt: dict[str, Any],
    lane: dict[str, Any],
    packet: dict[str, Any],
    workspace: dict[str, Any],
    evidence: Any,
) -> None:
    workspace_root = workspace.get("path")
    if not isinstance(workspace_root, str) or not workspace_root:
        raise HarnessError("host adapter workspace must include path")
    if not isinstance(evidence, dict):
        raise HarnessError("host adapter lane execution evidence must be an object")
    expected_sandbox = "read-only" if lane["kind"] == "validate" else "workspace-write"
    if (
        evidence.get("lane_id") != lane["lane_id"]
        or evidence.get("workspace_root") != workspace_root
        or evidence.get("sandbox") != expected_sandbox
        or evidence.get("ambient_mcp") is not False
        or evidence.get("runtime_provider") != packet["runtime_provider"]
        or evidence.get("agent_identity") != packet["agent_identity"]
        or not isinstance(evidence.get("thread_id"), str)
        or not evidence["thread_id"]
        or not isinstance(evidence.get("turn_id"), str)
        or not evidence["turn_id"]
        or not isinstance(evidence.get("workspace_status_before"), str)
        or not isinstance(evidence.get("workspace_status_after"), str)
    ):
        raise HarnessError("host adapter lane execution evidence conflicts with packet")
    selected_tools = evidence.get("selected_tools_used")
    tool_calls = evidence.get("tool_calls")
    command_results = evidence.get("command_results")
    if (
        not isinstance(selected_tools, list)
        or not selected_tools
        or not all(isinstance(tool, str) and tool for tool in selected_tools)
        or len(set(selected_tools)) != len(selected_tools)
        or not isinstance(tool_calls, list)
        or not all(isinstance(call, str) and call for call in tool_calls)
        or not isinstance(command_results, list)
        or not all(
            isinstance(result, dict)
            and result.get("cwd") == workspace_root
            and result.get("runtime_provider") == packet["runtime_provider"]
            for result in command_results
        )
    ):
        raise HarnessError("host adapter lane execution evidence lacks packet tool proof")
    access_key = "validator_access" if lane["kind"] == "validate" else "writer_access"
    required_access = "read_only" if lane["kind"] == "validate" else "workspace_write"
    bindings = {binding["tool"]: binding for binding in packet["tool_bindings"]}
    if any(tool not in bindings for tool in selected_tools) or not any(
        bindings[tool][access_key] == required_access for tool in selected_tools
    ):
        raise HarnessError("host adapter lane did not use a packet-selected tool with required access")
    if lane["kind"] == "validate" and evidence["workspace_status_before"] != evidence["workspace_status_after"]:
        raise HarnessError("read-only validator changed final packet workspace")
    records = attempt.setdefault("execution_evidence", [])
    if any(record.get("lane_id") == lane["lane_id"] for record in records):
        raise HarnessError("host adapter produced duplicate lane execution evidence")
    records.append(copy.deepcopy(evidence))


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
    for field, allowed_values in role.get("field_constraints", {}).items():
        if claim.get(field) not in allowed_values:
            raise HarnessError(f"managed claim field `{field}` has unsupported value")
    frictions = claim.get("frictions", [])
    if not isinstance(frictions, list):
        raise HarnessError("managed claim frictions must be a list")
    for friction in frictions:
        if not isinstance(friction, dict) or not isinstance(friction.get("category"), str) or not friction["category"]:
            raise HarnessError("managed claim friction must have category")
    return copy.deepcopy(claim)


def _validator_criterion(root: Path, attempt: dict[str, Any]) -> dict[str, str]:
    lanes = {lane.get("lane_id"): lane for lane in attempt["lanes"] if isinstance(lane, dict)}
    validator_lane = lanes.get("validate")
    integration_lane = lanes.get("integrate")
    claims = {
        record.get("lane_id"): record.get("claim")
        for record in attempt["claims"]
        if isinstance(record, dict)
    }
    integration_claim = claims.get("integrate")
    validator_claim = claims.get("validate")
    if (
        not isinstance(validator_lane, dict)
        or not isinstance(integration_lane, dict)
        or not isinstance(integration_claim, dict)
        or integration_claim.get("kind") != integration_lane.get("required_claim_kind")
        or not isinstance(integration_claim.get("workspace"), dict)
        or not isinstance(validator_claim, dict)
    ):
        return {"status": "failed", "evidence_ref": "validator_claim"}
    try:
        role = _load_roles(root)[validator_lane["role"]]
        claim = _validate_managed_claim(validator_claim, role)
    except (HarnessError, KeyError, TypeError):
        return {"status": "failed", "evidence_ref": "validator_claim"}
    if (
        claim.get("kind") != validator_lane.get("required_claim_kind")
        or claim.get("verdict") != "pass"
        or validator_lane.get("workspace") != integration_claim["workspace"]
    ):
        return {"status": "failed", "evidence_ref": "validator_claim"}
    return {"status": "proven", "evidence_ref": "validator_claim"}


def _verification_workspace(attempt: dict[str, Any]) -> Path:
    integration_claim = next(
        (
            record.get("claim")
            for record in attempt["claims"]
            if isinstance(record, dict) and record.get("lane_id") == "integrate"
        ),
        None,
    )
    if not isinstance(integration_claim, dict) or not isinstance(integration_claim.get("workspace"), dict):
        raise HarnessError("verification requires integrated workspace")
    path = integration_claim["workspace"].get("path")
    if not isinstance(path, str) or not Path(path).is_dir():
        raise HarnessError("verification workspace is unavailable")
    return Path(path).resolve()


def _require_lane_execution_evidence(attempt: dict[str, Any]) -> None:
    lanes = {
        lane["lane_id"]: lane
        for lane in attempt["lanes"]
        if isinstance(lane, dict) and lane.get("kind") in {"work", "validate"}
    }
    records = attempt.get("execution_evidence")
    if not isinstance(records, list) or {record.get("lane_id") for record in records if isinstance(record, dict)} != set(lanes):
        raise HarnessError("verification requires host execution evidence for every dispatched lane")
    for record in records:
        lane = lanes[record["lane_id"]]
        workspace = lane.get("workspace")
        if not isinstance(workspace, dict) or record.get("workspace_root") != workspace.get("path"):
            raise HarnessError("host execution evidence workspace conflicts with lane")


def _verify_managed(
    root: Path,
    packet: dict[str, Any],
    attempt: dict[str, Any],
    *,
    adapter: Any,
    run_check: CheckRunner | None,
    collect_changes: ChangeCollector,
    now: datetime,
) -> dict[str, Any]:
    _require_lane_execution_evidence(attempt)
    verification_root = _verification_workspace(attempt)
    changes = collect_changes(verification_root, packet["base_commit"])
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

    host_checks = None if run_check else _adapter_call(adapter, "run_checks", packet, {"path": str(verification_root)})
    if host_checks is not None and not isinstance(host_checks, dict):
        raise HarnessError("host adapter checks must be a mapping")
    checks: dict[str, dict[str, Any]] = {}
    for name, command in packet["checks"].items():
        if run_check:
            code, stdout, stderr = run_check(command)
            checks[name] = {"name": name, "command": command, "exit_code": code, "stdout": stdout[:1000], "stderr": stderr[:1000]}
        else:
            check = host_checks.get(name)
            if (
                not isinstance(check, dict)
                or check.get("command") != command
                or check.get("workspace_root") != str(verification_root)
                or check.get("tool") != "shell"
                or check.get("binding_verified") is not True
                or check.get("runtime_provider") != packet["runtime_provider"]
                or not isinstance(check.get("exit_code"), int)
                or not isinstance(check.get("stdout"), str)
                or not isinstance(check.get("stderr"), str)
            ):
                raise HarnessError(f"host adapter check `{name}` lacks packet workspace evidence")
            checks[name] = {"name": name, **check}
        code = checks[name]["exit_code"]
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
        elif kind == "validator":
            result.update(_validator_criterion(root, attempt))
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


def _record_attempt_friction(
    root: Path,
    run: dict[str, Any],
    attempt: dict[str, Any],
    *,
    lane: dict[str, Any] | None,
    source: str,
    phase: str,
    code: str,
    evidence_ref: str,
) -> dict[str, Any]:
    event = record_friction_event(
        root,
        run_id=run["run_id"],
        attempt_id=attempt["attempt_id"],
        packet=attempt["packet"],
        lane=lane,
        source=source,
        phase=phase,
        code=code,
        evidence_ref=evidence_ref,
    )
    attempt["friction_event_ids"].append(event["event_id"])
    return event


def _record_failure(
    root: Path,
    run: dict[str, Any],
    policy: dict[str, Any],
    attempt: dict[str, Any],
    reason: str,
    detail: str,
    *,
    phase: str,
) -> dict[str, Any]:
    _record_attempt_friction(
        root,
        run,
        attempt,
        lane=None,
        source="host",
        phase=phase,
        code=reason,
        evidence_ref=f"outcome.{reason}",
    )
    decisions = ["block"]
    if reason in attempt["packet"]["retry_policy"]["retryable_reasons"]:
        decisions = ["retry", "escalate", "block"]
    _set_outcome(attempt, reason, decisions, ["friction_event_ids"])
    _transition(run, policy["states"], "awaiting_decision", reason)
    _write_run(root, run)
    return _managed_result(run)


def _cancel_active_lanes(
    root: Path,
    run: dict[str, Any],
    attempt: dict[str, Any],
    adapter: Any,
    active_handles: list[tuple[dict[str, Any], Any]],
    *,
    phase: str,
) -> None:
    for lane, handle in active_handles:
        try:
            _adapter_call(adapter, "cancel_lane", handle)
        except Exception:
            _record_attempt_friction(
                root,
                run,
                attempt,
                lane=lane,
                source="host",
                phase=phase,
                code="cancellation_failed",
                evidence_ref=f"lanes.{lane['lane_id']}.cancellation",
            )


def _record_lane_claim(root: Path, run: dict[str, Any], attempt: dict[str, Any], lane: dict[str, Any], claim: Any) -> None:
    try:
        role_name = lane.get("role")
        if not isinstance(role_name, str):
            raise HarnessError(f"lane `{lane['lane_id']}` cannot collect an agent claim")
        role = _load_roles(root).get(role_name)
        if not isinstance(role, dict):
            raise HarnessError(f"lane `{lane['lane_id']}` has unknown role `{role_name}`")
        normalized_claim = _validate_managed_claim(claim, role)
        if normalized_claim["kind"] != lane["required_claim_kind"]:
            raise HarnessError(f"lane `{lane['lane_id']}` claim kind conflicts with packet")
    except HarnessError as exc:
        raise ClaimError(str(exc)) from exc
    attempt["claims"].append({"lane_id": lane["lane_id"], "claim": normalized_claim})
    for friction in normalized_claim.get("frictions", []):
        _record_attempt_friction(
            root,
            run,
            attempt,
            lane=lane,
            source="validator" if lane["kind"] == "validate" else "agent",
            phase="validator" if lane["kind"] == "validate" else "claim",
            code=friction["category"],
            evidence_ref=f"claims.{lane['lane_id']}",
        )


def _record_verification_frictions(root: Path, run: dict[str, Any], attempt: dict[str, Any], verification: dict[str, Any]) -> None:
    for blocker in verification["blockers"]:
        kind = blocker["kind"]
        if kind == "check":
            source, phase, code = "check", "check", "check_failed"
        elif kind == "criterion" and blocker.get("id") == "validator":
            source, phase, code = "validator", "validator", "validator_failed"
        elif kind in {"scope", "approval"}:
            source, phase, code = "controller", "decision", f"{kind}_blocked"
        else:
            source, phase, code = "host", "integration", "verification_failed"
        _record_attempt_friction(
            root,
            run,
            attempt,
            lane=None,
            source=source,
            phase=phase,
            code=code,
            evidence_ref="evidence.blockers",
        )


def _execute_attempt(
    root: Path,
    run: dict[str, Any],
    policy: dict[str, Any],
    adapter: Any,
    *,
    run_check: CheckRunner | None,
    collect_changes: ChangeCollector,
    now: datetime,
) -> dict[str, Any]:
    attempt = _active_attempt(run)
    packet = attempt["packet"]
    planned_blockers = _gate_blockers(packet, packet["planned_write_paths"], now)
    attempt["authorization"] = {"planned_write_paths": packet["planned_write_paths"], "blockers": planned_blockers}
    if planned_blockers:
        _record_attempt_friction(
            root,
            run,
            attempt,
            lane=None,
            source="controller",
            phase="decision",
            code="approval_required",
            evidence_ref="authorization.blockers",
        )
        _set_outcome(attempt, "approval_required", ["request_approval", "retry", "block"], ["authorization"])
        _transition(run, policy["states"], "awaiting_decision", "approval_required")
        _write_run(root, run)
        return _managed_result(run)
    try:
        capabilities = _adapter_capabilities(adapter, set(policy["orchestration"]))
    except Exception as exc:
        return _record_failure(root, run, policy, attempt, "dispatch_failed", str(exc), phase="dispatch")
    mode = packet["orchestration"]["name"]
    if capabilities.get(mode) != "enforced":
        _record_attempt_friction(
            root,
            run,
            attempt,
            lane=None,
            source="host",
            phase="dispatch",
            code="execution_mode_unavailable",
            evidence_ref="capabilities",
        )
        _set_outcome(attempt, "execution_mode_unavailable", ["waive", "block"], ["capabilities"])
        _transition(run, policy["states"], "awaiting_decision", "execution_mode_unavailable")
        _write_run(root, run)
        return _managed_result(run)
    try:
        attempt["adapter_identity"] = _adapter_identity(adapter, packet["runtime_provider"])
    except Exception as exc:
        return _record_failure(root, run, policy, attempt, "dispatch_failed", str(exc), phase="dispatch")

    _transition(run, policy["states"], "running", "dispatch")
    pending = {lane["lane_id"]: lane for lane in attempt["lanes"]}
    workspaces: dict[str, dict[str, Any]] = {}
    active_handles: list[tuple[dict[str, Any], Any]] = []
    failure_phase = "dispatch"
    try:
        while pending:
            completed = {
                lane["lane_id"]
                for lane in attempt["lanes"]
                if lane.get("status") == "succeeded"
            }
            ready = [
                lane for lane in pending.values()
                if all(dependency in completed for dependency in lane["dependencies"])
            ]
            if not ready:
                raise HarnessError("lane scheduler found unresolved dependencies")

            work_lanes = [lane for lane in ready if lane["kind"] == "work"]
            if work_lanes:
                writer_slots = packet["orchestration"]["max_parallel_writers"]
                scheduled: list[dict[str, Any]] = []
                for lane in work_lanes:
                    if lane["write_capable"]:
                        if not writer_slots:
                            continue
                        writer_slots -= 1
                    scheduled.append(lane)
                for lane in scheduled:
                    workspace = _adapter_call(adapter, "prepare_workspace", lane, packet)
                    if not isinstance(workspace, dict):
                        raise HarnessError("host adapter workspace must be an object")
                    lane["workspace"] = copy.deepcopy(workspace)
                    bindings = _adapter_call(adapter, "verify_tool_bindings", lane, packet, workspace)
                    _record_tool_binding_evidence(attempt, lane, packet, workspace, bindings)
                    handle = _adapter_call(adapter, "dispatch_lane", lane, packet, workspace, None)
                    active_handles.append((lane, handle))
                for lane, handle in active_handles[:]:
                    claim = _adapter_call(adapter, "collect_claim", handle)
                    _record_lane_claim(root, run, attempt, lane, claim)
                    evidence = _adapter_call(adapter, "collect_lane_evidence", handle, lane, packet, lane["workspace"])
                    _record_lane_execution_evidence(attempt, lane, packet, lane["workspace"], evidence)
                    lane["status"] = "succeeded"
                    workspaces[lane["lane_id"]] = copy.deepcopy(lane["workspace"])
                    pending.pop(lane["lane_id"])
                    active_handles.remove((lane, handle))
                continue

            integration = next((lane for lane in ready if lane["kind"] == "integrate"), None)
            if integration is not None:
                failure_phase = "integration"
                workspace = _adapter_call(adapter, "materialize_final_state", integration, packet, workspaces)
                if not isinstance(workspace, dict):
                    raise HarnessError("host adapter final workspace must be an object")
                integration["workspace"] = copy.deepcopy(workspace)
                integration["status"] = "succeeded"
                attempt["claims"].append({
                    "lane_id": integration["lane_id"],
                    "claim": {"kind": integration["required_claim_kind"], "workspace": copy.deepcopy(workspace)},
                })
                pending.pop(integration["lane_id"])
                continue

            validator = next((lane for lane in ready if lane["kind"] == "validate"), None)
            if validator is None:
                raise HarnessError("lane scheduler found unsupported lane kind")
            failure_phase = "validator"
            integration = next(lane for lane in attempt["lanes"] if lane["lane_id"] == "integrate")
            workspace = integration.get("workspace")
            if not isinstance(workspace, dict):
                raise HarnessError("validator requires final workspace")
            validator["workspace"] = copy.deepcopy(workspace)
            bindings = _adapter_call(adapter, "verify_tool_bindings", validator, packet, workspace)
            _record_tool_binding_evidence(attempt, validator, packet, workspace, bindings)
            handle = _adapter_call(adapter, "dispatch_lane", validator, packet, workspace, None)
            active_handles.append((validator, handle))
            claim = _adapter_call(adapter, "collect_claim", handle)
            _record_lane_claim(root, run, attempt, validator, claim)
            evidence = _adapter_call(adapter, "collect_lane_evidence", handle, validator, packet, workspace)
            _record_lane_execution_evidence(attempt, validator, packet, workspace, evidence)
            validator["status"] = "succeeded"
            pending.pop(validator["lane_id"])
            active_handles.remove((validator, handle))
    except ClaimError as exc:
        _cancel_active_lanes(root, run, attempt, adapter, active_handles, phase="claim")
        return _record_failure(root, run, policy, attempt, "claim_invalid", str(exc), phase="claim")
    except Exception as exc:
        _cancel_active_lanes(root, run, attempt, adapter, active_handles, phase=failure_phase)
        return _record_failure(root, run, policy, attempt, "dispatch_failed", str(exc), phase=failure_phase)
    _transition(run, policy["states"], "observed", "claim_collected")
    _transition(run, policy["states"], "verifying", "verify")
    try:
        verification = _verify_managed(
            root,
            packet,
            attempt,
            adapter=adapter,
            run_check=run_check,
            collect_changes=collect_changes,
            now=now,
        )
    except Exception as exc:
        return _record_failure(root, run, policy, attempt, "verification_failed", str(exc), phase="check")
    attempt["evidence"] = verification
    _record_verification_frictions(root, run, attempt, verification)
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
        _admit_coordinated_packet(root, packet)
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
        attempt = _active_attempt(run)
        packet = attempt["packet"]
        if "plan_ref" in packet:
            try:
                plan_ref = _required_string(packet.get("plan_ref"), "packet plan_ref")
                plan_task_id = _required_string(packet.get("plan_task_id"), "packet plan_task_id")
                plan_digest = _required_string(packet.get("plan_digest"), "packet plan_digest")
                coordination = load_plan_coordination(root, plan_ref, require_active=True)
                if coordination is None or coordination.task(plan_task_id).task_id != plan_task_id:
                    raise HarnessError("coordinated packet no longer resolves to its plan task")
                if plan_digest != coordination.digest:
                    raise HarnessError("coordinated packet plan digest changed")
                if packet["base_commit"] != _resolve_commit(root, coordination.base_ref):
                    raise HarnessError("coordinated packet base commit changed")
            except (PlanCoordinationError, HarnessError):
                _set_outcome(attempt, "plan_binding_changed", ["retry", "block"], ["packet"])
                _transition(run, policy["states"], "awaiting_decision", "plan_binding_changed")
                _write_run(root, run)
                return _managed_result(run)
    collector = collect_changes or _collect_changes
    return _execute_attempt(root, run, policy, adapter, run_check=run_check, collect_changes=collector, now=now or datetime.now(UTC))


def _successor_request(run: dict[str, Any], successor: Any) -> dict[str, Any]:
    request = copy.deepcopy(run["request"])
    if "plan_ref" in _active_attempt(run)["packet"]:
        for field in ("execution_mode", "base_ref", "planned_write_paths"):
            request.pop(field, None)
    if successor is None:
        return request
    if not isinstance(successor, dict):
        raise HarnessError("decision successor must be an object")
    allowed = {"execution_mode", "runtime_provider_id", "user_request", "allowed_paths", "planned_write_paths", "acceptance_criteria", "base_ref", "approvals", "review_evidence", "manual_evidence", "lanes", "plan_ref", "plan_task_id"}
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
    elif kind == "waive":
        _required_string(decision.get("reason"), "waiver reason")
        _transition(run, policy["states"], "unvalidated", "controller_waive")
    elif kind == "block":
        _transition(run, policy["states"], "blocked", "controller_block")
    elif kind == "request_approval":
        _transition(run, policy["states"], "awaiting_decision", "controller_request_approval")
    else:
        retry_policy = attempt["packet"]["retry_policy"]
        if outcome["reason"] not in retry_policy["retryable_reasons"] and outcome["reason"] not in {"approval_required", "plan_binding_changed"}:
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
    coordination_status_command = subparsers.add_parser("coordination-status")
    coordination_status_command.add_argument("--plan", required=True)
    handoff_command = subparsers.add_parser("handoff")
    handoff_command.add_argument("--run-id", required=True)
    handoff_command.add_argument("--handoff", required=True)
    subparsers.add_parser("friction-report")
    friction_resolve_command = subparsers.add_parser("friction-resolve")
    friction_resolve_command.add_argument("--run-id", required=True)
    friction_resolve_command.add_argument("--fingerprint", required=True)
    friction_resolve_command.add_argument("--decision", required=True, choices=sorted(FRICTION_RESOLUTIONS))
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
        elif args.command == "friction-report":
            result = friction_report(root)
        elif args.command == "friction-resolve":
            result = resolve_friction(root, args.run_id, args.fingerprint, args.decision)
        elif args.command == "coordination-status":
            result = coordination_status(root, args.plan)
        elif args.command == "handoff":
            try:
                handoff = json.loads(args.handoff)
            except json.JSONDecodeError as exc:
                raise HarnessError("handoff must be JSON") from exc
            result = record_controller_handoff(root, args.run_id, handoff)
        else:
            result = apply_controller_decision(root, args.run_id, _load_json(Path(args.decision)))
    except HarnessError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if args.command in {"preflight", "friction-report", "friction-resolve", "coordination-status", "handoff"} or result.get("status") == "verified" or result.get("state") == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
