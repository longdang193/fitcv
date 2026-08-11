"""
@meta
name: test_harness_task
type: test
domain: harness
distribution_tier: starter_kit
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "harness_task.py"
FRICTION_EVENTS_ROOT: Path | None = None


@pytest.fixture(autouse=True)
def isolate_root_friction_events(tmp_path: Path) -> None:
    global FRICTION_EVENTS_ROOT
    FRICTION_EVENTS_ROOT = tmp_path / "friction-events.jsonl"


def load_module():
    spec = importlib.util.spec_from_file_location("harness_task", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_friction_events_path = module._friction_events_path
    if FRICTION_EVENTS_ROOT is not None:
        module._friction_events_path = lambda root: FRICTION_EVENTS_ROOT if root == ROOT else original_friction_events_path(root)
    return module


def task(**overrides):
    payload = {
        "version": 1,
        "task_type": "local_change",
        "acceptance_criteria": ["focused test passes"],
        "allowed_paths": ["scripts/**", "tests/**"],
        "base_ref": "HEAD",
    }
    payload.update(overrides)
    return payload


def claim(**overrides):
    payload = {
        "kind": "claimed_result",
        "changed_files": ["scripts/example.py"],
        "from_state": "verifying",
        "next_state": "accepted",
    }
    payload.update(overrides)
    return payload


def managed_request(**overrides):
    payload = {
        "version": 2,
        "run_id": "managed-test",
        "task_type": "local_change",
        "execution_mode": "single_agent",
        "user_request": "Update managed harness fixture.",
        "acceptance_criteria": [{"id": "diff", "kind": "check", "check": "diff"}],
        "allowed_paths": ["scripts/**", "tests/**"],
        "planned_write_paths": ["scripts/harness_task.py"],
        "base_ref": "HEAD",
    }
    payload.update(overrides)
    return payload


def plan_coordination(*, digest="plan-digest", execution_mode="single_work_lane", paths=("scripts/harness_task.py",)):
    task = SimpleNamespace(
        task_id="task-1",
        execution_mode=execution_mode,
        planned_write_paths=paths,
    )
    return SimpleNamespace(
        plan_ref="docs/superpowers/plans/fixture.md",
        base_ref="HEAD",
        digest=digest,
        task=lambda task_id: task if task_id == "task-1" else (_ for _ in ()).throw(ValueError(task_id)),
    )


def plan_coordination_with_tasks(*tasks, plan_ref="docs/superpowers/plans/fixture.md", target_branch="main"):
    by_id = {task.task_id: task for task in tasks}
    return SimpleNamespace(
        plan_ref=plan_ref,
        base_ref="HEAD",
        digest=f"digest-{plan_ref}",
        target_branch=target_branch,
        tasks=tuple(tasks),
        task=lambda task_id: by_id[task_id],
    )


def coordinated_task(task_id, *, depends_on=(), execution_mode="single_work_lane", paths=("scripts/harness_task.py",)):
    return SimpleNamespace(
        task_id=task_id,
        depends_on=depends_on,
        execution_mode=execution_mode,
        planned_write_paths=paths,
    )


def write_coordinated_run(harness, root, run_id, *, state, plan_ref, task_id, paths=("scripts/harness_task.py",)):
    harness._write_run(root, {
        "version": 1,
        "run_id": run_id,
        "request": {},
        "state": state,
        "state_history": [{"state": state, "reason": "fixture", "at": f"2026-08-06T00:00:0{len(run_id)}+00:00"}],
        "attempts": [{
            "packet": {
                "plan_ref": plan_ref,
                "plan_task_id": task_id,
                "planned_write_paths": list(paths),
            },
        }],
    })


class FakeAdapter:
    def __init__(self, capabilities, claim_payload=None, validator_claim=None, dispatch_error=None, identity=None, workspace_root=None):
        self.capabilities_value = capabilities
        self.claim_payload = claim_payload
        self.validator_claim = validator_claim
        self.dispatch_error = dispatch_error
        self.identity_value = identity or {"provider_id": "codex_app_server", "contract_version": 2}
        self.workspace_root = str(workspace_root or ROOT)
        self.calls = []

    def identity(self):
        return self.identity_value

    def capabilities(self):
        self.calls.append("capabilities")
        return self.capabilities_value

    def prepare_workspace(self, lane, packet):
        self.calls.append("prepare_workspace")
        return {"kind": "current", "path": self.workspace_root}

    def verify_tool_bindings(self, lane, packet, workspace):
        self.calls.append("verify_tool_bindings")
        access_key = "validator_access" if lane["kind"] == "validate" else "writer_access"
        return [{
            "tool": binding["tool"],
            "host_kind": binding["host_kind"],
            "access": binding[access_key],
            "root_probe": binding["root_probe"],
            "workspace_root": workspace["path"],
            "verified": True,
            "runtime_provider": packet["runtime_provider"],
        } for binding in packet["tool_bindings"]]

    def run_checks(self, packet, workspace):
        self.calls.append("run_checks")
        return {
            name: {
                "command": command,
                "workspace_root": workspace["path"],
                "tool": "shell",
                "binding_verified": True,
                "runtime_provider": packet["runtime_provider"],
                "exit_code": 0,
                "stdout": "ok",
                "stderr": "",
            }
            for name, command in packet["checks"].items()
        }

    def dispatch_lane(self, lane, packet, workspace, cancellation_token):
        self.calls.append("dispatch_lane")
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return {"lane_id": lane["lane_id"]}

    def materialize_final_state(self, lane, packet, workspaces):
        self.calls.append("materialize_final_state")
        return {"kind": "isolated", "path": self.workspace_root}

    def cancel_lane(self, handle):
        self.calls.append("cancel_lane")

    def collect_claim(self, handle):
        self.calls.append("collect_claim")
        if handle["lane_id"] == "validate":
            if self.validator_claim is not None:
                return self.validator_claim
            return {
                "kind": "claimed_result",
                "summary": "validated",
                "findings": ["ok"],
                "verdict": "pass",
            }
        if self.claim_payload is not None:
            return self.claim_payload
        return {
            "kind": "claimed_result",
            "summary": "done",
            "changed_files": ["scripts/harness_task.py"],
        }

    def collect_lane_evidence(self, handle, lane, packet, workspace):
        self.calls.append("collect_lane_evidence")
        return {
            "lane_id": lane["lane_id"],
            "workspace_root": workspace["path"],
            "thread_id": "thread",
            "turn_id": f"turn-{lane['lane_id']}",
            "sandbox": "read-only" if lane["kind"] == "validate" else "workspace-write",
            "selected_tools_used": ["shell"],
            "tool_calls": ["shell"],
            "command_results": [{
                "cwd": workspace["path"],
                "exit_code": 0,
                "runtime_provider": packet["runtime_provider"],
            }],
            "ambient_mcp": False,
            "runtime_provider": packet["runtime_provider"],
            "agent_identity": packet["agent_identity"],
            "workspace_status_before": "",
            "workspace_status_after": "",
        }


def assert_provider_conformance(harness, adapter, run_id, workspace_root):
    run_dir = ROOT / ".harness" / "runs" / run_id
    Path(workspace_root).mkdir(parents=True, exist_ok=True)
    result = harness.run_managed(
        ROOT,
        managed_request(run_id=run_id),
        adapter,
        collect_changes=lambda root, base_commit: [],
    )

    assert result["outcome"]["reason"] == "verification_passed"
    run = json.loads((run_dir / "run.json").read_text())
    attempt = run["attempts"][0]
    provider = attempt["packet"]["runtime_provider"]
    assert provider == adapter.identity()
    assert attempt["adapter_identity"] == provider
    assert [record["sandbox"] for record in attempt["execution_evidence"]] == ["workspace-write", "read-only"]
    assert {record["workspace_root"] for record in attempt["execution_evidence"]} == {str(workspace_root)}
    assert all(record["runtime_provider"] == provider for record in attempt["execution_evidence"])
    assert all(
        command["runtime_provider"] == provider
        for record in attempt["execution_evidence"]
        for command in record["command_results"]
    )
    assert all(
        binding["workspace_root"] == str(workspace_root) and binding["runtime_provider"] == provider
        for record in attempt["tool_binding_evidence"]
        for binding in record["bindings"]
    )
    assert all(
        check["workspace_root"] == str(workspace_root) and check["runtime_provider"] == provider
        for check in attempt["evidence"]["checks"]
    )
    return run


def test_resolve_task_returns_route_packet() -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task())

    assert packet["template"] == "normal"
    assert packet["agent_identity"]["model"] == "combo-normal"
    assert packet["role"] == "implement"
    assert packet["checks"] == {"diff": ["git", "diff", "--check"]}
    assert packet["orchestration"]["name"] == "single_work_lane"


def test_resolve_task_selects_validated_sequential_orchestration() -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task(execution_mode="sequential_agents"))

    assert packet["orchestration"] == {
        "name": "sequential_work_lanes",
        "work_scheduling": "sequential",
        "max_parallel_writers": 1,
        "workspace_mode": "isolated",
        "validator_role": "validate",
        "review_required": True,
    }
    assert "multi-agent-orchestration-rule" in packet["rules"]


@pytest.mark.parametrize(("task_type", "skills"), [
    ("research", ["skill-repository-research"]),
    ("design_exploration", ["skill-brainstorming"]),
    ("plan_writing", ["skill-writing-plans"]),
    ("skill_authoring", [
        "skill-writing-skills",
        "skill-test-driven-development",
        "skill-verification-before-completion",
    ]),
    ("harness_improvement", [
        "skill-improve-harness",
        "skill-code-standards",
        "skill-test-driven-development",
        "skill-verification-before-completion",
    ]),
])
def test_route_packet_selects_owned_skill_set(task_type, skills) -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task(task_type=task_type))

    assert packet["skills"] == skills


def test_protected_policy_includes_canonical_skill_sources() -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task())

    assert ".agents/skills/**" in packet["approval_gates"]["protected_policy"]


def test_resolve_managed_packet_normalizes_v2_alias_to_v3_lane_dag() -> None:
    harness = load_module()

    packet = harness.resolve_managed_packet(ROOT, managed_request(), attempt_id="attempt-1")

    assert packet["version"] == 3
    assert packet["user_request"] == "Update managed harness fixture."
    assert packet["runtime_provider"] == {"provider_id": "codex_app_server", "contract_version": 2}
    assert packet["execution_budget"] == {
        "profile": "default",
        "turn_timeout_seconds": 300,
        "timeout_decisions": ["escalate", "block"],
        "escalation_profile": "extended",
    }
    assert packet["agent_identity"] == {
        "template": "normal",
        "model_provider": "9router",
        "model": "combo-normal",
        "reasoning_effort": "medium",
    }
    assert packet["lanes"][0]["claim_schema"]["required_fields"] == ["summary", "changed_files"]
    assert packet["lanes"][0]["claim_schema"]["required_fields"] == ["summary", "changed_files"]
    assert packet["orchestration"]["name"] == "single_work_lane"
    assert [(lane["lane_id"], lane["kind"], lane["dependencies"]) for lane in packet["lanes"]] == [
        ("primary", "work", []),
        ("integrate", "integrate", ["primary"]),
        ("validate", "validate", ["integrate"]),
    ]
    assert packet["lanes"][2]["role"] == "validate"
    assert packet["lanes"][2]["write_capable"] is False
    assert packet["tool_bindings"] == [
        {"tool": "shell", "host_kind": "app_server_shell", "writer_access": "workspace_write", "validator_access": "read_only", "root_probe": "shell_root_probe"},
        {"tool": "serena", "host_kind": "local_serena", "writer_access": "workspace_write", "validator_access": "read_only", "root_probe": "serena_root_probe"},
        {"tool": "ast_grep_preview", "host_kind": "local_ast_grep", "writer_access": "read_only", "validator_access": "read_only", "root_probe": "ast_grep_root_probe"},
    ]


def test_resolve_managed_packet_derives_immutable_plan_binding(monkeypatch) -> None:
    harness = load_module()
    coordination = plan_coordination(execution_mode="sequential_work_lanes")
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    request = managed_request(
        version=3,
        plan_ref=coordination.plan_ref,
        plan_task_id="task-1",
        lanes=[{
            "lane_id": "work",
            "role": "implement",
            "allowed_paths": ["scripts/**"],
            "dependencies": [],
            "workspace_mode": "isolated",
            "write_capable": True,
        }],
    )
    for field in ("execution_mode", "base_ref", "planned_write_paths"):
        request.pop(field)

    packet = harness.resolve_managed_packet(ROOT, request, attempt_id="attempt-1")

    assert packet["orchestration"]["name"] == "sequential_work_lanes"
    assert packet["base_ref"] == "HEAD"
    assert packet["planned_write_paths"] == ["scripts/harness_task.py"]
    assert {key: packet[key] for key in ("plan_ref", "plan_task_id", "plan_digest")} == {
        "plan_ref": coordination.plan_ref,
        "plan_task_id": "task-1",
        "plan_digest": "plan-digest",
    }


@pytest.mark.parametrize(
    ("execution_mode", "lanes"),
    [
        ("single_work_lane", None),
        (
            "sequential_work_lanes",
            [
                {"lane_id": "first", "role": "implement", "allowed_paths": ["scripts/**"], "dependencies": [], "workspace_mode": "isolated", "write_capable": True},
                {"lane_id": "second", "role": "implement", "allowed_paths": ["tests/**"], "dependencies": ["first"], "workspace_mode": "isolated", "write_capable": True},
            ],
        ),
        (
            "parallel_work_lanes",
            [
                {"lane_id": "scripts", "role": "implement", "allowed_paths": ["scripts/**"], "dependencies": [], "workspace_mode": "isolated", "write_capable": True},
                {"lane_id": "tests", "role": "implement", "allowed_paths": ["tests/**"], "dependencies": [], "workspace_mode": "isolated", "write_capable": True},
            ],
        ),
    ],
)
def test_plan_bound_packet_uses_same_binding_for_every_canonical_topology(monkeypatch, execution_mode, lanes) -> None:
    harness = load_module()
    coordination = plan_coordination(execution_mode=execution_mode)
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    request = managed_request(version=3, plan_ref=coordination.plan_ref, plan_task_id="task-1")
    for field in ("execution_mode", "base_ref", "planned_write_paths"):
        request.pop(field)
    if lanes is not None:
        request["lanes"] = lanes

    packet = harness.resolve_managed_packet(ROOT, request, attempt_id="attempt-1")

    assert packet["orchestration"]["name"] == execution_mode
    assert packet["plan_ref"] == coordination.plan_ref
    assert packet["plan_task_id"] == "task-1"
    assert packet["plan_digest"] == coordination.digest


def test_resolve_managed_packet_rejects_conflicting_plan_field(monkeypatch) -> None:
    harness = load_module()
    coordination = plan_coordination(execution_mode="sequential_work_lanes")
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)

    with pytest.raises(harness.HarnessError, match="execution_mode.*conflicts"):
        harness.resolve_managed_packet(
            ROOT,
            managed_request(version=3, plan_ref=coordination.plan_ref, plan_task_id="task-1", execution_mode="single_work_lane"),
            attempt_id="attempt-1",
        )


def test_resolve_managed_packet_rejects_plan_path_outside_allowed_scope(monkeypatch) -> None:
    harness = load_module()
    coordination = plan_coordination(paths=("repo_config/harness.yaml",))
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    request = managed_request(version=3, plan_ref=coordination.plan_ref, plan_task_id="task-1")
    for field in ("execution_mode", "base_ref", "planned_write_paths"):
        request.pop(field)

    with pytest.raises(harness.HarnessError, match="planned_write_paths.*allowed_paths"):
        harness.resolve_managed_packet(ROOT, request, attempt_id="attempt-1")


def test_successor_re_resolves_coordinated_manifest_fields() -> None:
    harness = load_module()
    request = managed_request(version=3, plan_ref="docs/superpowers/plans/fixture.md", plan_task_id="task-1")
    run = {"run_id": "run-1", "request": request, "attempts": [{"packet": {"plan_ref": request["plan_ref"]}}]}

    successor = harness._successor_request(run, {"plan_task_id": "task-2"})

    assert successor["plan_task_id"] == "task-2"
    assert {"execution_mode", "base_ref", "planned_write_paths"}.isdisjoint(successor)


def test_managed_continuation_blocks_changed_plan_digest_before_dispatch(monkeypatch, tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    original = plan_coordination(digest="original")
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: original)
    request = managed_request(
        version=3,
        run_id=run_id,
        execution_mode="single_work_lane",
        plan_ref=original.plan_ref,
        plan_task_id="task-1",
    )
    packet = harness.resolve_managed_packet(ROOT, request, attempt_id="attempt-1")
    policy = harness._load_policy(ROOT)
    run = harness._new_run(request, run_id)
    harness._transition(run, policy["states"], "planned", "preflight")
    harness._append_attempt(run, packet)
    harness._write_run(ROOT, run)
    adapter = FakeAdapter({"single_work_lane": "enforced"})
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: plan_coordination(digest="changed"))
    try:
        result = harness.run_managed(ROOT, None, adapter, run_id=run_id)

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "plan_binding_changed"
        assert adapter.calls == []
    finally:
        shutil.rmtree(ROOT / ".harness" / "runs" / run_id, ignore_errors=True)


def test_managed_continuation_blocks_changed_plan_base_commit_before_dispatch(monkeypatch, tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    coordination = plan_coordination(digest="stable")
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    request = managed_request(
        version=3,
        run_id=run_id,
        execution_mode="single_work_lane",
        plan_ref=coordination.plan_ref,
        plan_task_id="task-1",
    )
    packet = harness.resolve_managed_packet(ROOT, request, attempt_id="attempt-1")
    policy = harness._load_policy(ROOT)
    run = harness._new_run(request, run_id)
    harness._transition(run, policy["states"], "planned", "preflight")
    harness._append_attempt(run, packet)
    harness._write_run(ROOT, run)
    adapter = FakeAdapter({"single_work_lane": "enforced"})
    monkeypatch.setattr(harness, "_resolve_commit", lambda *_args: "different-base")
    try:
        result = harness.run_managed(ROOT, None, adapter, run_id=run_id)

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "plan_binding_changed"
        assert adapter.calls == []
    finally:
        shutil.rmtree(ROOT / ".harness" / "runs" / run_id, ignore_errors=True)


def test_coordination_status_derives_dependency_and_active_states(monkeypatch, tmp_path: Path) -> None:
    harness = load_module()
    first = coordinated_task("task-1")
    second = coordinated_task("task-2", depends_on=("task-1",))
    coordination = plan_coordination_with_tasks(first, second)
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    write_coordinated_run(harness, tmp_path, "done", state="accepted", plan_ref=coordination.plan_ref, task_id="task-1")

    status = harness.coordination_status(tmp_path, coordination.plan_ref)

    assert [(task["id"], task["state"]) for task in status["tasks"]] == [("task-1", "done"), ("task-2", "ready")]
    write_coordinated_run(harness, tmp_path, "active", state="planned", plan_ref=coordination.plan_ref, task_id="task-2")
    status = harness.coordination_status(tmp_path, coordination.plan_ref)
    assert status["tasks"][1]["state"] == "active"


def test_controller_handoff_is_run_owned_and_rejects_terminal_run(monkeypatch, tmp_path: Path) -> None:
    harness = load_module()
    coordination = plan_coordination_with_tasks(coordinated_task("task-1"))
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    write_coordinated_run(harness, tmp_path, "handoff", state="planned", plan_ref=coordination.plan_ref, task_id="task-1")

    result = harness.record_controller_handoff(tmp_path, "handoff", {
        "last_verified_fact": "packet is valid",
        "next_action": "dispatch",
        "blocker_or_decision": "none",
    })

    assert result["handoff"]["next_action"] == "dispatch"
    assert result["handoff"]["timestamp"]
    write_coordinated_run(harness, tmp_path, "terminal", state="accepted", plan_ref=coordination.plan_ref, task_id="task-1")
    with pytest.raises(harness.HarnessError, match="terminal"):
        harness.record_controller_handoff(tmp_path, "terminal", {
            "last_verified_fact": "complete",
            "next_action": "none",
            "blocker_or_decision": "accepted",
        })


def test_coordination_status_and_handoff_cli_use_run_owned_state(tmp_path: Path) -> None:
    root = tmp_path / "harness"
    (root / "repo_config").mkdir(parents=True)
    shutil.copy2(ROOT / "repo_config" / "harness.yaml", root / "repo_config" / "harness.yaml")
    shutil.copy2(ROOT / "repo_config" / "planning_artifact_schema.yaml", root / "repo_config" / "planning_artifact_schema.yaml")
    plan_ref = "docs/superpowers/plans/fixture.md"
    plan_path = root / plan_ref
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(
        "---\nartifact_type: plan\nstatus: active\nlayer: change\ncoordination:\n"
        "  target_branch: main\n  base_ref: HEAD\n  tasks:\n"
        "    - id: task-1\n      depends_on: []\n"
        "      execution_mode: single_work_lane\n      planned_write_paths: [scripts/**]\n"
        "---\n# Fixture\n\n### Task 1: Fixture\n\n**Coordination ID:** `task-1`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", plan_ref], cwd=root, check=True)
    run_path = root / ".harness" / "runs" / "run-1" / "run.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(json.dumps({
        "version": 1,
        "run_id": "run-1",
        "request": {},
        "state": "planned",
        "state_history": [{"state": "planned", "reason": "fixture", "at": "2026-08-06T00:00:00+00:00"}],
        "attempts": [{"packet": {"plan_ref": plan_ref, "plan_task_id": "task-1", "planned_write_paths": ["scripts/**"]}}],
    }), encoding="utf-8")

    status = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "coordination-status", "--plan", plan_ref],
        capture_output=True,
        text=True,
        check=False,
    )
    handoff = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(root),
            "handoff",
            "--run-id",
            "run-1",
            "--handoff",
            json.dumps({"last_verified_fact": "packet valid", "next_action": "dispatch", "blocker_or_decision": "none"}),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert status.returncode == 0
    assert json.loads(status.stdout)["tasks"][0]["state"] == "active"
    assert handoff.returncode == 0
    assert json.loads(handoff.stdout)["handoff"]["next_action"] == "dispatch"
    assert json.loads(run_path.read_text(encoding="utf-8"))["attempts"][0]["handoff"]["timestamp"]


def test_coordinated_admission_blocks_unmet_dependencies_and_path_conflicts(monkeypatch, tmp_path: Path) -> None:
    harness = load_module()
    first = coordinated_task("task-1")
    second = coordinated_task("task-2", depends_on=("task-1",))
    current = plan_coordination_with_tasks(first, second)
    other = plan_coordination_with_tasks(
        coordinated_task("other-task"),
        plan_ref="docs/superpowers/plans/other.md",
    )
    manifests = {current.plan_ref: current, other.plan_ref: other}
    monkeypatch.setattr(harness, "load_plan_coordination", lambda _root, plan_ref, **_kwargs: manifests[plan_ref])
    packet = {
        "plan_ref": current.plan_ref,
        "plan_task_id": "task-2",
        "planned_write_paths": ["scripts/harness_task.py"],
    }

    with pytest.raises(harness.HarnessError, match="waiting_dependencies"):
        harness._admit_coordinated_packet(tmp_path, packet)

    write_coordinated_run(harness, tmp_path, "done", state="accepted", plan_ref=current.plan_ref, task_id="task-1")
    harness._admit_coordinated_packet(tmp_path, packet)
    write_coordinated_run(harness, tmp_path, "other", state="planned", plan_ref=other.plan_ref, task_id="other-task")
    with pytest.raises(harness.HarnessError, match="paths conflict"):
        harness._admit_coordinated_packet(tmp_path, packet)


def test_resolve_managed_packet_rejects_disallowed_runtime_provider() -> None:
    harness = load_module()

    with pytest.raises(harness.HarnessError, match="runtime provider `missing` is not allowed"):
        harness.resolve_managed_packet(
            ROOT,
            managed_request(runtime_provider_id="missing"),
            attempt_id="attempt-1",
        )


def test_resolve_managed_packet_accepts_allowed_runtime_provider() -> None:
    harness = load_module()

    packet = harness.resolve_managed_packet(
        ROOT,
        managed_request(runtime_provider_id="codex_app_server"),
        attempt_id="attempt-1",
    )

    assert packet["runtime_provider"] == {"provider_id": "codex_app_server", "contract_version": 2}


@pytest.mark.parametrize(("task_type", "template", "model"), [
    ("research", "low", "combo-low"),
    ("local_change", "normal", "combo-normal"),
    ("plan_review", "high", "combo-high"),
])
def test_managed_packet_copies_template_model_identity(task_type, template, model) -> None:
    harness = load_module()

    packet = harness.resolve_managed_packet(
        ROOT,
        managed_request(task_type=task_type),
        attempt_id="attempt-1",
    )

    assert packet["agent_identity"] == {
        "template": template,
        "model_provider": "9router",
        "model": model,
        "reasoning_effort": "medium",
    }


def test_resolve_managed_packet_rejects_v3_legacy_mode_alias() -> None:
    harness = load_module()

    with pytest.raises(harness.HarnessError, match="canonical execution mode"):
        harness.resolve_managed_packet(ROOT, managed_request(version=3), attempt_id="attempt-1")


def test_resolve_managed_packet_adds_system_lanes_after_v3_work_lane() -> None:
    harness = load_module()

    packet = harness.resolve_managed_packet(
        ROOT,
        managed_request(
            version=3,
            execution_mode="sequential_work_lanes",
            lanes=[{
                "lane_id": "work",
                "role": "implement",
                "allowed_paths": ["scripts/**"],
                "dependencies": [],
                "workspace_mode": "isolated",
                "write_capable": True,
            }],
        ),
        attempt_id="attempt-1",
    )

    assert [(lane["lane_id"], lane["kind"], lane["dependencies"]) for lane in packet["lanes"]] == [
        ("work", "work", []),
        ("integrate", "integrate", ["work"]),
        ("validate", "validate", ["integrate"]),
    ]


def test_preflight_cli_prints_only_packet_json(tmp_path: Path) -> None:
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(ROOT), "preflight", "--task", str(task_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["template"] == "normal"


@pytest.mark.parametrize(
    "payload",
    [
        task(task_type="missing"),
        task(acceptance_criteria=[]),
        task(allowed_paths=["../escape"]),
        task(execution_mode="missing"),
    ],
)
def test_resolve_task_rejects_invalid_input(payload) -> None:
    harness = load_module()

    with pytest.raises(harness.HarnessError):
        harness.resolve_task(ROOT, payload)


def test_verify_rejects_scope_escape_and_approval_gate() -> None:
    harness = load_module()
    protected = task(allowed_paths=["repo_config/**"])

    result = harness.verify_task(
        ROOT,
        protected,
        claim(changed_files=["repo_config/harness.yaml"]),
        changed_paths=["repo_config/harness.yaml"],
        run_check=lambda command: (0, "", ""),
    )

    assert result["status"] == "observed"
    assert result["blockers"] == [
        {"kind": "approval", "gate": "protected_policy", "path": "repo_config/harness.yaml"}
    ]


def test_verify_produces_verified_evidence_and_optional_run_file(tmp_path: Path) -> None:
    harness = load_module()
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.verify_task(
            ROOT,
            task(run_dir=str(run_dir)),
            claim(),
            changed_paths=["scripts/example.py"],
            run_check=lambda command: (0, "ok", ""),
        )

        assert result["status"] == "verified"
        assert result["acceptance"] == [{"criterion": "focused test passes", "proven": True}]
        assert (run_dir / "evidence.json").is_file()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_verify_rejects_run_path_outside_harness(tmp_path: Path) -> None:
    harness = load_module()

    with pytest.raises(harness.HarnessError, match="run_dir must stay under"):
        harness.verify_task(
            ROOT,
            task(run_dir=str(tmp_path)),
            claim(),
            changed_paths=["scripts/example.py"],
            run_check=lambda command: (0, "", ""),
        )


def test_verify_rejects_failed_check_and_invalid_transition() -> None:
    harness = load_module()

    result = harness.verify_task(
        ROOT,
        task(),
        claim(from_state="running", next_state="accepted"),
        changed_paths=["scripts/example.py"],
        run_check=lambda command: (1, "", "failed"),
    )

    assert result["status"] == "observed"
    assert {blocker["kind"] for blocker in result["blockers"]} == {"check", "transition"}


def test_run_managed_blocks_unavailable_mode_without_dispatch(tmp_path: Path) -> None:
    harness = load_module()
    adapter = FakeAdapter({"single_work_lane": "enforced"})
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(
                execution_mode="sequential_agents",
                run_id=tmp_path.name,
                lanes=[{
                    "lane_id": "primary",
                    "role": "implement",
                    "allowed_paths": ["scripts/**", "tests/**"],
                    "dependencies": [],
                    "workspace_mode": "isolated",
                    "write_capable": True,
                }],
            ),
            adapter,
        )

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "execution_mode_unavailable"
        assert adapter.calls == ["capabilities"]
        assert (run_dir / "run.json").is_file()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_adapter_identity_mismatch_blocks_before_workspace_preparation(tmp_path: Path) -> None:
    harness = load_module()
    adapter = FakeAdapter(
        {"single_work_lane": "enforced"},
        identity={"provider_id": "codex_app_server", "contract_version": 1},
    )
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(ROOT, managed_request(run_id=tmp_path.name), adapter)

        assert result["outcome"]["reason"] == "dispatch_failed"
        assert adapter.calls == ["capabilities"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_unavailable_managed_run_requires_explicit_unvalidated_waiver(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(ROOT, managed_request(run_id=run_id), FakeAdapter({}))

        assert result["outcome"]["reason"] == "execution_mode_unavailable"
        assert result["outcome"]["allowed_decisions"] == ["waive", "block"]
        with pytest.raises(harness.HarnessError, match="waiver reason"):
            harness.apply_controller_decision(ROOT, run_id, {"kind": "waive"})

        waived = harness.apply_controller_decision(
            ROOT,
            run_id,
            {"kind": "waive", "reason": "host adapter unavailable"},
        )

        assert waived["state"] == "unvalidated"
        run = json.loads((run_dir / "run.json").read_text())
        assert run["attempts"][0]["decision"]["reason"] == "host adapter unavailable"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_generic_cli_records_unavailable_adapter_proof(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    task_path = tmp_path / "task.json"
    decision_path = tmp_path / "decision.json"
    task_path.write_text(json.dumps(managed_request(run_id=run_id)), encoding="utf-8")
    decision_path.write_text(
        json.dumps({"kind": "waive", "reason": "generic CLI has no host adapter"}),
        encoding="utf-8",
    )
    try:
        assert harness.main(["--repo-root", str(ROOT), "run-unavailable", "--task", str(task_path)]) == 1
        assert harness.main(
            ["--repo-root", str(ROOT), "decision", "--run-id", run_id, "--decision", str(decision_path)]
        ) == 1

        run = json.loads((run_dir / "run.json").read_text())
        assert run["state"] == "unvalidated"
        assert run["attempts"][0]["outcome"]["reason"] == "execution_mode_unavailable"
        assert run["attempts"][0]["outcome"]["detail"] == (
            "Generic harness CLI has no injected host adapter; use a provider host entrypoint."
        )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_generic_cli_rejects_managed_run_command(tmp_path: Path) -> None:
    harness = load_module()
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(managed_request(run_id=tmp_path.name)), encoding="utf-8")
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        with pytest.raises(SystemExit) as error:
            harness.main(["--repo-root", str(ROOT), "run", "--task", str(task_path)])

        assert error.value.code == 2
        assert not (run_dir / "run.json").exists()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_run_managed_records_evidence_then_controller_accepts(tmp_path: Path) -> None:
    harness = load_module()
    adapter = FakeAdapter({"single_work_lane": "enforced"})
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            adapter,
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "verification_passed"
        assert adapter.calls == [
            "capabilities",
            "prepare_workspace",
            "verify_tool_bindings",
            "dispatch_lane",
            "collect_claim",
            "collect_lane_evidence",
            "materialize_final_state",
            "verify_tool_bindings",
            "dispatch_lane",
            "collect_claim",
            "collect_lane_evidence",
        ]

        accepted = harness.apply_controller_decision(ROOT, run_id, {"kind": "accept"})

        assert accepted["state"] == "accepted"
        run = json.loads((run_dir / "run.json").read_text())
        assert [item["state"] for item in run["state_history"]] == [
            "classified", "planned", "running", "observed", "verifying", "awaiting_decision", "accepted"
        ]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_run_managed_records_host_preflight_evidence(tmp_path: Path) -> None:
    harness = load_module()

    class PreflightAdapter(FakeAdapter):
        def preflight_evidence(self):
            return {
                "protocol": "initialize",
                "server_uri": "ws://127.0.0.1:4500",
            }

    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            PreflightAdapter({"single_work_lane": "enforced"}),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["state"] == "awaiting_decision"
        run = json.loads((run_dir / "run.json").read_text())
        assert run["attempts"][0]["host_preflight"] == {
            "protocol": "initialize",
            "server_uri": "ws://127.0.0.1:4500",
        }
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_provider_conformance_vector_accepts_adapter_implementation(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    workspace = tmp_path / "adapter-workspace"
    adapter = FakeAdapter({"single_work_lane": "enforced"}, workspace_root=workspace)
    try:
        run = assert_provider_conformance(harness, adapter, run_id, workspace)

        accepted = harness.apply_controller_decision(ROOT, run_id, {"kind": "accept"})

        assert accepted["state"] == "accepted"
        assert run["state"] == "awaiting_decision"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_unverified_packet_tool_blocks_before_writer_dispatch(tmp_path: Path) -> None:
    class UnboundToolAdapter(FakeAdapter):
        def verify_tool_bindings(self, lane, packet, workspace):
            self.calls.append("verify_tool_bindings")
            raise RuntimeError("packet-scoped native tool roots unavailable: serena")

    harness = load_module()
    adapter = UnboundToolAdapter({"single_work_lane": "enforced"})
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(ROOT, managed_request(run_id=run_id), adapter)

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "dispatch_failed"
        assert result["outcome"]["detail"] == "packet-scoped native tool roots unavailable: serena"
        run = json.loads((run_dir / "run.json").read_text())
        assert run["attempts"][0]["evidence"]["failure"] == {
            "detail": "packet-scoped native tool roots unavailable: serena",
            "phase": "dispatch",
            "reason": "dispatch_failed",
        }
        assert adapter.calls == ["capabilities", "prepare_workspace", "verify_tool_bindings"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_mismatched_tool_binding_provider_blocks_before_writer_dispatch(tmp_path: Path) -> None:
    class MismatchedProviderAdapter(FakeAdapter):
        def verify_tool_bindings(self, lane, packet, workspace):
            bindings = super().verify_tool_bindings(lane, packet, workspace)
            bindings[0]["runtime_provider"] = {"provider_id": "other", "contract_version": 1}
            return bindings

    harness = load_module()
    adapter = MismatchedProviderAdapter({"single_work_lane": "enforced"})
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(ROOT, managed_request(run_id=tmp_path.name), adapter)

        assert result["outcome"]["reason"] == "dispatch_failed"
        assert adapter.calls == ["capabilities", "prepare_workspace", "verify_tool_bindings"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_missing_command_result_provider_blocks_before_verification(tmp_path: Path) -> None:
    class MissingCommandProviderAdapter(FakeAdapter):
        def collect_lane_evidence(self, handle, lane, packet, workspace):
            evidence = super().collect_lane_evidence(handle, lane, packet, workspace)
            del evidence["command_results"][0]["runtime_provider"]
            return evidence

    harness = load_module()
    adapter = MissingCommandProviderAdapter({"single_work_lane": "enforced"})
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(ROOT, managed_request(run_id=tmp_path.name), adapter)

        assert result["outcome"]["reason"] == "dispatch_failed"
        assert adapter.calls == [
            "capabilities",
            "prepare_workspace",
            "verify_tool_bindings",
            "dispatch_lane",
            "collect_claim",
            "collect_lane_evidence",
            "cancel_lane",
        ]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


@pytest.mark.parametrize("field", ["agent_identity", "model", "reasoning_effort"])
def test_missing_or_mismatched_agent_identity_blocks_before_verification(tmp_path: Path, field: str) -> None:
    class MismatchedAgentAdapter(FakeAdapter):
        def collect_lane_evidence(self, handle, lane, packet, workspace):
            evidence = super().collect_lane_evidence(handle, lane, packet, workspace)
            if field == "agent_identity":
                del evidence[field]
            else:
                evidence["agent_identity"] = dict(evidence["agent_identity"])
                evidence["agent_identity"][field] = "wrong"
            return evidence

    harness = load_module()
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=tmp_path.name),
            MismatchedAgentAdapter({"single_work_lane": "enforced"}),
        )

        assert result["outcome"]["reason"] == "dispatch_failed"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_cancellation_failure_records_normalized_friction(tmp_path: Path) -> None:
    class CancellationFailureAdapter(FakeAdapter):
        def collect_lane_evidence(self, handle, lane, packet, workspace):
            raise RuntimeError("evidence unavailable")

        def cancel_lane(self, handle):
            super().cancel_lane(handle)
            raise RuntimeError("cancellation unavailable")

    harness = load_module()
    run_dir = ROOT / ".harness" / "runs" / tmp_path.name
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=tmp_path.name),
            CancellationFailureAdapter({"single_work_lane": "enforced"}),
        )

        assert result["outcome"]["reason"] == "dispatch_failed"
        events = [json.loads(line) for line in FRICTION_EVENTS_ROOT.read_text().splitlines()]
        assert [event["code"] for event in events] == ["cancellation_failed", "dispatch_failed"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_managed_run_uses_host_check_evidence(tmp_path: Path) -> None:
    harness = load_module()
    adapter = FakeAdapter({"single_work_lane": "enforced"})
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            adapter,
            collect_changes=lambda root, base_commit: [],
        )

        assert result["outcome"]["reason"] == "verification_passed"
        run = json.loads((run_dir / "run.json").read_text())
        assert len(run["attempts"][0]["tool_binding_evidence"]) == 2
        assert [record["lane_id"] for record in run["attempts"][0]["execution_evidence"]] == ["primary", "validate"]
        assert run["attempts"][0]["evidence"]["checks"][0]["workspace_root"] == str(ROOT)
        assert "run_checks" in adapter.calls
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_managed_validator_fail_blocks_acceptance(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            FakeAdapter(
                {"single_work_lane": "enforced"},
                validator_claim={
                    "kind": "claimed_result",
                    "summary": "validation failed",
                    "findings": ["failure"],
                    "verdict": "fail",
                },
            ),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["outcome"]["reason"] == "verification_failed"
        evidence = json.loads((run_dir / "run.json").read_text())["attempts"][0]["evidence"]
        assert evidence["criteria"][-1] == {
            "id": "validator",
            "kind": "validator",
            "status": "failed",
            "evidence_ref": "validator_claim",
        }
        with pytest.raises(harness.HarnessError, match="not allowed for current outcome"):
            harness.apply_controller_decision(ROOT, run_id, {"kind": "accept"})
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_managed_validator_rejects_invalid_verdict(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            FakeAdapter(
                {"single_work_lane": "enforced"},
                validator_claim={
                    "kind": "claimed_result",
                    "summary": "invalid validation",
                    "findings": ["invalid"],
                    "verdict": "unknown",
                },
            ),
        )

        assert result["outcome"]["reason"] == "claim_invalid"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("execution_mode", "lanes", "work_lane_ids"),
    [
        ("single_work_lane", None, ["primary"]),
        (
            "sequential_work_lanes",
            [
                {
                    "lane_id": "first",
                    "role": "implement",
                    "allowed_paths": ["scripts/**"],
                    "dependencies": [],
                    "workspace_mode": "isolated",
                    "write_capable": True,
                },
                {
                    "lane_id": "second",
                    "role": "implement",
                    "allowed_paths": ["tests/**"],
                    "dependencies": ["first"],
                    "workspace_mode": "isolated",
                    "write_capable": True,
                },
            ],
            ["first", "second"],
        ),
        (
            "parallel_work_lanes",
            [
                {
                    "lane_id": "scripts",
                    "role": "implement",
                    "allowed_paths": ["scripts/**"],
                    "dependencies": [],
                    "workspace_mode": "isolated",
                    "write_capable": True,
                },
                {
                    "lane_id": "tests",
                    "role": "implement",
                    "allowed_paths": ["tests/**"],
                    "dependencies": [],
                    "workspace_mode": "isolated",
                    "write_capable": True,
                },
            ],
            ["scripts", "tests"],
        ),
    ],
)
def test_plan_bound_managed_scheduler_proves_every_canonical_topology(
    tmp_path: Path,
    monkeypatch,
    execution_mode: str,
    lanes: list[dict[str, object]] | None,
    work_lane_ids: list[str],
) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    coordination = plan_coordination_with_tasks(
        coordinated_task("task-1", execution_mode=execution_mode),
    )
    monkeypatch.setattr(harness, "load_plan_coordination", lambda *_args, **_kwargs: coordination)
    request = managed_request(version=3, run_id=run_id, plan_ref=coordination.plan_ref, plan_task_id="task-1")
    for field in ("execution_mode", "base_ref", "planned_write_paths"):
        request.pop(field)
    if lanes is not None:
        request["lanes"] = lanes
    try:
        result = harness.run_managed(
            ROOT,
            request,
            FakeAdapter({execution_mode: "enforced"}),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["outcome"]["reason"] == "verification_passed"
        attempt = json.loads((run_dir / "run.json").read_text())["attempts"][0]
        assert {key: attempt["packet"][key] for key in ("plan_ref", "plan_task_id", "plan_digest")} == {
            "plan_ref": coordination.plan_ref,
            "plan_task_id": "task-1",
            "plan_digest": coordination.digest,
        }
        assert [record["lane_id"] for record in attempt["claims"]] == [
            *work_lane_ids,
            "integrate",
            "validate",
        ]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_managed_verification_rejects_forged_claim_approval(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    claim_payload = {
        "kind": "claimed_result",
        "summary": "done",
        "changed_files": ["repo_config/harness.yaml"],
        "approved_gates": ["protected_policy"],
    }
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(
                run_id=run_id,
                allowed_paths=["scripts/**", "repo_config/**"],
            ),
            FakeAdapter({"single_work_lane": "enforced"}, claim_payload),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [{"path": "repo_config/harness.yaml", "kind": "modified"}],
        )

        assert result["outcome"]["reason"] == "approval_required"
        with pytest.raises(harness.HarnessError, match="not allowed"):
            harness.apply_controller_decision(ROOT, run_id, {"kind": "accept"})
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_managed_review_criterion_never_auto_proves(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(
                run_id=run_id,
                acceptance_criteria=[
                    {"id": "diff", "kind": "check", "check": "diff"},
                    {"id": "review", "kind": "review"},
                ],
            ),
            FakeAdapter({"single_work_lane": "enforced"}),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["outcome"]["reason"] == "review_required"
        evidence = json.loads((run_dir / "run.json").read_text())["attempts"][0]["evidence"]
        assert [criterion["status"] for criterion in evidence["criteria"]] == [
            "proven",
            "review_required",
            "proven",
        ]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_retry_creates_immutable_successor_then_exhausts(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        first = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            FakeAdapter({"single_work_lane": "enforced"}),
            run_check=lambda command: (1, "", "failed"),
            collect_changes=lambda root, base_commit: [],
        )
        assert first["outcome"]["reason"] == "verification_failed"

        retry = harness.apply_controller_decision(ROOT, run_id, {"kind": "retry"})
        assert retry["state"] == "planned"
        before = json.loads((run_dir / "run.json").read_text())["attempts"][0]["packet"]

        second = harness.run_managed(
            ROOT,
            None,
            FakeAdapter({"single_work_lane": "enforced"}),
            run_id=run_id,
            run_check=lambda command: (1, "", "failed"),
            collect_changes=lambda root, base_commit: [],
        )
        assert second["outcome"]["reason"] == "verification_failed"
        exhausted = harness.apply_controller_decision(ROOT, run_id, {"kind": "retry"})

        run = json.loads((run_dir / "run.json").read_text())
        assert exhausted["state"] == "blocked"
        assert len(run["attempts"]) == 2
        assert run["attempts"][0]["packet"]["runtime_provider"] == {
            "provider_id": "codex_app_server",
            "contract_version": 2,
        }
        assert run["attempts"][1]["packet"]["runtime_provider"] == run["attempts"][0]["packet"]["runtime_provider"]
        assert run["attempts"][0]["packet"] == before
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_collect_changes_includes_untracked_paths(tmp_path: Path) -> None:
    harness = load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")

    changes = harness._collect_changes(repo, "HEAD")

    assert changes == [{"path": "untracked.txt", "kind": "untracked"}]


def test_managed_planned_gate_blocks_before_dispatch_and_accepts_controller_approval(tmp_path: Path) -> None:
    harness = load_module()
    now = datetime.now(UTC)
    blocked_id = f"{tmp_path.name}-blocked"
    blocked_dir = ROOT / ".harness" / "runs" / blocked_id
    approved_id = f"{tmp_path.name}-approved"
    approved_dir = ROOT / ".harness" / "runs" / approved_id
    request = {
        "allowed_paths": ["repo_config/**"],
        "planned_write_paths": ["repo_config/harness.yaml"],
    }
    try:
        blocked_adapter = FakeAdapter({"single_work_lane": "enforced"})
        blocked = harness.run_managed(
            ROOT,
            managed_request(run_id=blocked_id, **request),
            blocked_adapter,
            now=now,
        )
        assert blocked["outcome"]["reason"] == "approval_required"
        assert blocked_adapter.calls == []

        approved = harness.run_managed(
            ROOT,
            managed_request(
                run_id=approved_id,
                **request,
                approvals=[{
                    "gate": "protected_policy",
                    "approver": "controller",
                    "paths": ["repo_config/**"],
                    "attempt_id": "attempt-1",
                    "issued_at": now.isoformat(),
                }],
            ),
            FakeAdapter({"single_work_lane": "enforced"}),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
            now=now,
        )
        assert approved["outcome"]["reason"] == "verification_passed"
    finally:
        shutil.rmtree(blocked_dir, ignore_errors=True)
        shutil.rmtree(approved_dir, ignore_errors=True)


def test_managed_dispatch_failure_becomes_retryable_outcome(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            FakeAdapter({"single_work_lane": "enforced"}, dispatch_error=RuntimeError("offline")),
        )

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "dispatch_failed"
        assert result["outcome"]["allowed_decisions"] == ["retry", "escalate", "block"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_timeout_escalation_uses_packet_named_budget_profile(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id

    class TimedOutTurn(RuntimeError):
        timeout_evidence = {
            "lane_id": "primary",
            "turn_timeout_seconds": 300,
            "elapsed_seconds": 300.0,
            "terminal_status": "interrupted",
            "event_summary": ["turn/completed"],
            "last_tool_call": "shell",
            "completed_command_count": 1,
        }

    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id),
            FakeAdapter({"single_work_lane": "enforced"}, dispatch_error=TimedOutTurn("turn timed out")),
        )

        assert result["outcome"] == {
            "reason": "dispatch_timeout",
            "allowed_decisions": ["escalate", "block"],
            "evidence_refs": ["friction_event_ids", "evidence.failure", "evidence.timeout"],
            "detail": "turn timed out",
        }
        with pytest.raises(harness.HarnessError, match="decision `retry` is not allowed"):
            harness.apply_controller_decision(ROOT, run_id, {"kind": "retry"})

        resumed = harness.apply_controller_decision(ROOT, run_id, {"kind": "escalate"})
        run = json.loads((run_dir / "run.json").read_text())

        assert resumed["state"] == "planned"
        assert run["attempts"][0]["packet"]["execution_budget"]["profile"] == "default"
        assert run["attempts"][1]["packet"]["execution_budget"]["profile"] == "extended"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_failed_integration_skips_validator_dispatch(tmp_path: Path) -> None:
    harness = load_module()
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id

    class IntegrationFailureAdapter(FakeAdapter):
        def __init__(self):
            super().__init__({"sequential_work_lanes": "enforced"})
            self.dispatched_lanes = []

        def dispatch_lane(self, lane, packet, workspace, cancellation_token):
            self.dispatched_lanes.append(lane["lane_id"])
            return super().dispatch_lane(lane, packet, workspace, cancellation_token)

        def materialize_final_state(self, lane, packet, workspaces):
            self.calls.append("materialize_final_state")
            raise RuntimeError("integration conflict")

    lanes = [
        {"lane_id": "first", "role": "implement", "allowed_paths": ["scripts/**"], "dependencies": [], "workspace_mode": "isolated", "write_capable": True},
        {"lane_id": "second", "role": "implement", "allowed_paths": ["tests/**"], "dependencies": ["first"], "workspace_mode": "isolated", "write_capable": True},
    ]
    adapter = IntegrationFailureAdapter()
    try:
        result = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id, execution_mode="sequential_work_lanes", lanes=lanes),
            adapter,
        )

        assert result["outcome"]["reason"] == "dispatch_failed"
        assert adapter.dispatched_lanes == ["first", "second"]
        assert "run_checks" not in adapter.calls
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_approval_resume_creates_successor_attempt(tmp_path: Path) -> None:
    harness = load_module()
    now = datetime.now(UTC)
    run_id = tmp_path.name
    run_dir = ROOT / ".harness" / "runs" / run_id
    request = {
        "allowed_paths": ["repo_config/**"],
        "planned_write_paths": ["repo_config/harness.yaml"],
    }
    try:
        first = harness.run_managed(
            ROOT,
            managed_request(run_id=run_id, **request),
            FakeAdapter({"single_work_lane": "enforced"}),
            now=now,
        )
        assert first["outcome"]["reason"] == "approval_required"

        waiting = harness.apply_controller_decision(ROOT, run_id, {"kind": "request_approval"})
        assert waiting["state"] == "awaiting_decision"
        resumed = harness.apply_controller_decision(
            ROOT,
            run_id,
            {"kind": "retry", "successor": {"approvals": [{
                "gate": "protected_policy",
                "approver": "controller",
                "paths": ["repo_config/**"],
                "attempt_id": "attempt-2",
                "issued_at": now.isoformat(),
            }]}},
        )
        assert resumed["state"] == "planned"

        run = json.loads((run_dir / "run.json").read_text())
        assert [decision["kind"] for decision in run["attempts"][0]["decision_history"]] == ["request_approval", "retry"]
        assert run["attempts"][1]["packet"]["approvals"][0]["attempt_id"] == "attempt-2"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_friction_report_uses_distinct_runs_and_accepted_resolution(tmp_path: Path) -> None:
    harness = load_module()
    root = tmp_path / "harness"
    (root / "repo_config").mkdir(parents=True)
    shutil.copy2(ROOT / "repo_config" / "harness.yaml", root / "repo_config" / "harness.yaml")
    packet = {
        "task_type": "local_change",
        "runtime_provider": {"provider_id": "codex_app_server", "contract_version": 2},
        "orchestration": {"name": "single_work_lane"},
    }
    now = datetime(2026, 8, 6, tzinfo=UTC)

    first = harness.record_friction_event(
        root,
        run_id="run-1",
        attempt_id="attempt-1",
        packet=packet,
        lane={"kind": "work"},
        source="host",
        phase="dispatch",
        code="tool_unavailable",
        evidence_ref="attempt.execution_evidence[0]",
        occurred_at=now,
    )
    harness.record_friction_event(
        root,
        run_id="run-1",
        attempt_id="attempt-1",
        packet=packet,
        lane={"kind": "work"},
        source="host",
        phase="dispatch",
        code="tool_unavailable",
        evidence_ref="attempt.execution_evidence[1]",
        occurred_at=now,
    )
    harness.record_friction_event(
        root,
        run_id="run-2",
        attempt_id="attempt-1",
        packet=packet,
        lane={"kind": "work"},
        source="host",
        phase="dispatch",
        code="tool_unavailable",
        evidence_ref="attempt.execution_evidence[0]",
        occurred_at=now,
    )
    assert harness.friction_report(root, now=now)["candidates"] == []
    for run_id in ("run-3",):
        harness.record_friction_event(
            root,
            run_id=run_id,
            attempt_id="attempt-1",
            packet=packet,
            lane={"kind": "work"},
            source="host",
            phase="dispatch",
            code="tool_unavailable",
            evidence_ref="attempt.execution_evidence[0]",
            occurred_at=now,
        )

    report = harness.friction_report(root, now=now)

    assert [candidate["fingerprint"] for candidate in report["candidates"]] == [first["fingerprint"]]
    assert report["candidates"][0]["distinct_run_count"] == 3
    assert report["candidates"][0]["event_count"] == 4
    resolution_run = root / ".harness" / "runs" / "improvement"
    resolution_run.mkdir(parents=True)
    (resolution_run / "run.json").write_text(json.dumps({
        "version": 1,
        "run_id": "improvement",
        "request": {"task_type": "local_change"},
        "state": "accepted",
        "attempts": [{}],
    }), encoding="utf-8")
    with pytest.raises(harness.HarnessError, match="accepted harness_improvement"):
        harness.resolve_friction(root, "improvement", first["fingerprint"], "keep", now=now)
    (resolution_run / "run.json").write_text(json.dumps({
        "version": 1,
        "run_id": "improvement",
        "request": {"task_type": "harness_improvement"},
        "state": "planned",
        "attempts": [{}],
    }), encoding="utf-8")
    with pytest.raises(harness.HarnessError, match="accepted harness_improvement"):
        harness.resolve_friction(root, "improvement", first["fingerprint"], "keep", now=now)
    (resolution_run / "run.json").write_text(json.dumps({
        "version": 1,
        "run_id": "improvement",
        "request": {"task_type": "harness_improvement"},
        "state": "accepted",
        "attempts": [{}],
    }), encoding="utf-8")

    resolution = harness.resolve_friction(
        root,
        "improvement",
        first["fingerprint"],
        "keep",
        now=now,
    )

    assert resolution["kind"] == "resolution"
    assert harness.friction_report(root, now=now)["candidates"] == []


def test_friction_report_cli_is_read_only(tmp_path: Path) -> None:
    root = tmp_path / "harness"
    (root / "repo_config").mkdir(parents=True)
    shutil.copy2(ROOT / "repo_config" / "harness.yaml", root / "repo_config" / "harness.yaml")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "friction-report"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["candidates"] == []
    assert not (root / ".harness").exists()


def test_friction_report_rejects_malformed_event(tmp_path: Path) -> None:
    harness = load_module()
    root = tmp_path / "harness"
    (root / "repo_config").mkdir(parents=True)
    shutil.copy2(ROOT / "repo_config" / "harness.yaml", root / "repo_config" / "harness.yaml")
    events_path = root / ".harness" / "friction-events.jsonl"
    events_path.parent.mkdir()
    events_path.write_text(json.dumps({
        "version": 1,
        "kind": "observed",
        "event_id": "friction-malformed",
        "run_id": "run-1",
        "attempt_id": "attempt-1",
        "route": "local_change",
        "provider": "codex_app_server:1",
        "mode": "single_work_lane",
        "lane_kind": "work",
        "phase": "dispatch",
        "source": [],
        "code": "tool_unavailable",
        "evidence_ref": "evidence",
        "fingerprint": "fingerprint",
        "occurred_at": "2026-08-06T00:00:00+00:00",
    }) + "\n", encoding="utf-8")

    with pytest.raises(harness.HarnessError, match="invalid friction event at line 1"):
        harness.friction_report(root)
