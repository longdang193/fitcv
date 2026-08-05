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

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "harness_task.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harness_task", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
        "acceptance_criteria": [{"id": "diff", "kind": "check", "check": "diff"}],
        "allowed_paths": ["scripts/**", "tests/**"],
        "planned_write_paths": ["scripts/harness_task.py"],
        "base_ref": "HEAD",
    }
    payload.update(overrides)
    return payload


class FakeAdapter:
    def __init__(self, capabilities, claim_payload=None, dispatch_error=None):
        self.capabilities_value = capabilities
        self.claim_payload = claim_payload
        self.dispatch_error = dispatch_error
        self.calls = []

    def capabilities(self):
        self.calls.append("capabilities")
        return self.capabilities_value

    def prepare_workspace(self, lane, packet):
        self.calls.append("prepare_workspace")
        return {"kind": "current", "path": str(ROOT)}

    def dispatch_lane(self, lane, packet, workspace, cancellation_token):
        self.calls.append("dispatch_lane")
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return {"lane_id": lane["lane_id"]}

    def cancel_lane(self, handle):
        self.calls.append("cancel_lane")

    def collect_claim(self, handle):
        self.calls.append("collect_claim")
        if self.claim_payload is not None:
            return self.claim_payload
        return {
            "kind": "claimed_result",
            "summary": "done",
            "changed_files": ["scripts/harness_task.py"],
        }


def test_resolve_task_returns_route_packet() -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task())

    assert packet["template"] == "normal"
    assert packet["role"] == "implement"
    assert packet["checks"] == {"diff": ["git", "diff", "--check"]}
    assert packet["orchestration"]["name"] == "single_agent"


def test_resolve_task_selects_validated_sequential_orchestration() -> None:
    harness = load_module()

    packet = harness.resolve_task(ROOT, task(execution_mode="sequential_agents"))

    assert packet["orchestration"] == {
        "name": "sequential_agents",
        "max_parallel_writers": 1,
        "workspace_mode": "current",
        "review_required": True,
    }
    assert "multi-agent-orchestration-rule" in packet["rules"]


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
    adapter = FakeAdapter({"single_agent": "enforced"})
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
                    "workspace_mode": "current",
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


def test_run_managed_records_evidence_then_controller_accepts(tmp_path: Path) -> None:
    harness = load_module()
    adapter = FakeAdapter({"single_agent": "enforced"})
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
        assert adapter.calls == ["capabilities", "prepare_workspace", "dispatch_lane", "collect_claim"]

        accepted = harness.apply_controller_decision(ROOT, run_id, {"kind": "accept"})

        assert accepted["state"] == "accepted"
        run = json.loads((run_dir / "run.json").read_text())
        assert [item["state"] for item in run["state_history"]] == [
            "classified", "planned", "running", "observed", "verifying", "awaiting_decision", "accepted"
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
            FakeAdapter({"single_agent": "enforced"}, claim_payload),
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
            FakeAdapter({"single_agent": "enforced"}),
            run_check=lambda command: (0, "ok", ""),
            collect_changes=lambda root, base_commit: [],
        )

        assert result["outcome"]["reason"] == "review_required"
        evidence = json.loads((run_dir / "run.json").read_text())["attempts"][0]["evidence"]
        assert [criterion["status"] for criterion in evidence["criteria"]] == ["proven", "review_required"]
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
            FakeAdapter({"single_agent": "enforced"}),
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
            FakeAdapter({"single_agent": "enforced"}),
            run_id=run_id,
            run_check=lambda command: (1, "", "failed"),
            collect_changes=lambda root, base_commit: [],
        )
        assert second["outcome"]["reason"] == "verification_failed"
        exhausted = harness.apply_controller_decision(ROOT, run_id, {"kind": "retry"})

        run = json.loads((run_dir / "run.json").read_text())
        assert exhausted["state"] == "blocked"
        assert len(run["attempts"]) == 2
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
        blocked_adapter = FakeAdapter({"single_agent": "enforced"})
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
            FakeAdapter({"single_agent": "enforced"}),
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
            FakeAdapter({"single_agent": "enforced"}, dispatch_error=RuntimeError("offline")),
        )

        assert result["state"] == "awaiting_decision"
        assert result["outcome"]["reason"] == "dispatch_failed"
        assert result["outcome"]["allowed_decisions"] == ["retry", "escalate", "block"]
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
            FakeAdapter({"single_agent": "enforced"}),
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
