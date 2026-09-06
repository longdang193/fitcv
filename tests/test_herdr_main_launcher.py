from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "herdr_main_launcher", ROOT / "scripts" / "herdr_main_launcher.py"
)
assert SPEC is not None and SPEC.loader is not None
LAUNCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCHER)


def fake_profile(tmp_path: Path, name: str, rank: int | None) -> None:
    agents = tmp_path / "agents"
    agents.mkdir(exist_ok=True)
    rank_line = "" if rank is None else f"rank = {rank}\n"
    (agents / f"{name}.toml").write_text(
        f'name = "{name}"\n'
        'model_provider = "9router"\n'
        f'model = "combo-{name}"\n'
        f"{rank_line}"
        'description = "test"\n'
        'developer_instructions = "do not modify files"\n',
        encoding="utf-8",
    )


def test_codex_arguments_project_complete_contract(tmp_path: Path) -> None:
    fake_profile(tmp_path, "review", None)
    profile = LAUNCHER._profile(tmp_path / "agents", "review")

    arguments = LAUNCHER._codex_arguments(profile, tmp_path)

    assert arguments[:2] == ["-C", str(tmp_path)]
    assert 'model_provider="9router"' in arguments
    assert 'model="combo-review"' in arguments
    assert 'developer_instructions="do not modify files"' in arguments


def test_redaction_hides_developer_instructions() -> None:
    arguments = ["-c", 'model="combo-xhigh"', "-c", 'developer_instructions="secret"']

    assert LAUNCHER._redacted_arguments(arguments) == [
        "-c",
        'model="combo-xhigh"',
        "-c",
        "developer_instructions=<sha256>",
    ]


def test_redaction_hides_deepagents_task() -> None:
    redacted = LAUNCHER._redacted_arguments(["-n", "private task"])

    assert redacted == [
        "-n",
        f"task=<sha256:{LAUNCHER._sha256_text('private task')}>",
    ]


def test_redaction_hides_codex_assignment_task() -> None:
    redacted = LAUNCHER._redacted_arguments(
        ["agent", "prompt", "xhigh-main", "private task", "--wait"],
    )

    assert redacted == [
        "agent",
        "prompt",
        "xhigh-main",
        f"task=<sha256:{LAUNCHER._sha256_text('private task')}>",
        "--wait",
    ]


def test_codex_assignment_command_prompts_started_agent() -> None:
    command = LAUNCHER._codex_assignment_command(
        "herdr.exe", "session", "xhigh-main", "assign lane",
    )

    assert command == [
        "herdr.exe",
        "--session",
        "session",
        "agent",
        "prompt",
        "xhigh-main",
            "assign lane",
            "--wait",
            "--timeout",
            "30000",
    ]


def test_powershell_literal_escapes_apostrophes() -> None:
    assert LAUNCHER._powershell_literal("worker's task") == "'worker''s task'"


def test_resolve_launch_builds_deepagents_pane_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = LAUNCHER.AgentProfile(
        Path("normal.toml"),
        "normal",
        "9router",
        "combo-normal",
        20,
        True,
        "test",
        "do not modify files",
    )
    monkeypatch.setattr(LAUNCHER, "_profile", lambda *args: profile)
    monkeypatch.setattr(LAUNCHER, "_executable", lambda name: f"{name}.exe")
    monkeypatch.setattr(LAUNCHER, "_git_identity", lambda *args: {"head": "head"})
    monkeypatch.setattr(
        LAUNCHER,
        "_herdr_pane",
        lambda cwd, session, pane, herdr, **kwargs: {
            "pane": {"cwd": str(cwd)},
            "process_info": {},
        },
    )

    command, evidence = LAUNCHER.resolve_launch(
        profile_name="normal",
        session="deepagents-probe",
        pane="w1:p1",
        cwd=ROOT,
        expected_base="HEAD",
        executor="deepagents",
        task="Return exactly DEEPAGENTS_ADAPTER_OK",
    )

    assert command == [
        "herdr.exe",
        "--session",
        "deepagents-probe",
        "pane",
        "run",
        "w1:p1",
        "&",
        "'dcode-project.exe'",
        "--role",
        "normal",
        "--json",
        "--quiet",
        "--no-mcp",
        "--max-turns",
        "4",
        "--timeout",
        "600",
        "-n",
        "'Return exactly DEEPAGENTS_ADAPTER_OK'",
    ]
    assert evidence["registry_launcher"]["executor"] == "deepagents"
    assert "--executor" not in command
    assert evidence["registry_launcher"]["redacted_runtime_argv"][-1].startswith(
        "task=<sha256:"
    )


def test_resolve_launch_enables_direct_mcp_only_for_explicit_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = LAUNCHER.AgentProfile(
        Path("normal.toml"),
        "normal",
        "9router",
        "combo-normal",
        20,
        True,
        "test",
        "do not modify files",
    )
    monkeypatch.setattr(LAUNCHER, "_profile", lambda *args: profile)
    monkeypatch.setattr(LAUNCHER, "_executable", lambda name: f"{name}.exe")
    monkeypatch.setattr(LAUNCHER, "_git_identity", lambda *args: {"head": "head"})
    monkeypatch.setattr(
        LAUNCHER,
        "_herdr_pane",
        lambda cwd, session, pane, herdr, **kwargs: {
            "pane": {"cwd": str(cwd)},
            "process_info": {},
        },
    )

    command, evidence = LAUNCHER.resolve_launch(
        profile_name="normal",
        session="deepagents-probe",
        pane="w1:p1",
        cwd=ROOT,
        expected_base="HEAD",
        executor="deepagents",
        mcp_select=["context7.query_docs"],
        task="Return exactly DIRECT_MCP_OK",
    )

    assert "--no-mcp" not in command
    assert command[command.index("--mcp-select") + 1] == "'context7.query_docs'"
    assert evidence["deepagents"]["mcp_mode"] == "direct"
    assert evidence["deepagents"]["mcp_selection"] == ["context7.query_docs"]


def test_resolve_launch_quotes_mcp_selectors_for_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = LAUNCHER.AgentProfile(
        Path("normal.toml"),
        "normal",
        "9router",
        "combo-normal",
        20,
        True,
        "test",
        "do not modify files",
    )
    monkeypatch.setattr(LAUNCHER, "_profile", lambda *args: profile)
    monkeypatch.setattr(LAUNCHER, "_executable", lambda name: f"{name}.exe")
    monkeypatch.setattr(LAUNCHER, "_git_identity", lambda *args: {"head": "head"})
    monkeypatch.setattr(
        LAUNCHER,
        "_herdr_pane",
        lambda cwd, session, pane, herdr, **kwargs: {
            "pane": {"cwd": str(cwd)},
            "process_info": {},
        },
    )

    command, _ = LAUNCHER.resolve_launch(
        profile_name="normal",
        session="deepagents-probe",
        pane="w1:p1",
        cwd=ROOT,
        expected_base="HEAD",
        executor="deepagents",
        mcp_select=["context7'; Write-Output hacked"],
        task="task",
    )

    assert "'context7''; Write-Output hacked'" in command


def test_deepagents_profile_binding_uses_lane_worktree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lane_root = tmp_path / "lane"
    lane_root.mkdir()
    lead_profile = LAUNCHER.AgentProfile(
        ROOT / "agents" / "normal.toml",
        "normal",
        "9router",
        "model-A",
        20,
        True,
        "lead",
        "lead instructions",
    )
    lane_profile = LAUNCHER.AgentProfile(
        lane_root / "agents" / "normal.toml",
        "normal",
        "9router",
        "model-B",
        20,
        True,
        "lane",
        "lane instructions",
    )
    seen_roots: list[Path] = []

    def select_profile(agents_root: Path, name: str) -> LAUNCHER.AgentProfile:
        seen_roots.append(agents_root)
        return lane_profile if agents_root == lane_root / "agents" else lead_profile

    monkeypatch.setattr(LAUNCHER, "_profile", select_profile)
    monkeypatch.setattr(LAUNCHER, "_executable", lambda name: f"{name}.exe")
    monkeypatch.setattr(LAUNCHER, "_version", lambda *args, **kwargs: "test")
    monkeypatch.setattr(LAUNCHER, "_git_identity", lambda *args: {"head": "head"})
    monkeypatch.setattr(
        LAUNCHER,
        "_herdr_pane",
        lambda cwd, session, pane, herdr, **kwargs: {
            "pane": {"cwd": str(cwd)},
            "process_info": {},
        },
    )

    command, evidence = LAUNCHER.resolve_launch(
        profile_name="normal",
        session="deepagents-probe",
        pane="w1:p1",
        cwd=lane_root,
        expected_base="HEAD",
        executor="deepagents",
        task="lane task",
    )

    assert seen_roots == [lane_root / "agents"]
    assert evidence["registry_launcher"]["model"] == "model-B"
    assert evidence["registry_launcher"]["profile_source"] == str(lane_profile.source)
    assert command[6] == "&"
    assert command[7] == "'dcode-project.exe'"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"task": None},
        {"task": " "},
        {"task": "x" * (LAUNCHER._MAX_TASK_LENGTH + 1)},
    ],
)
def test_deepagents_task_is_required_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, str | None],
) -> None:
    with pytest.raises(LAUNCHER.LaunchBlocked, match="text"):
        LAUNCHER.resolve_launch(
            profile_name="normal",
            session="session",
            pane="pane",
            cwd=ROOT,
            expected_base="HEAD",
            executor="deepagents",
            **kwargs,
        )


@pytest.mark.parametrize("task", [None, " ", "x" * (LAUNCHER._MAX_TASK_LENGTH + 1), "line1\nline2"])
def test_codex_task_is_required_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    task: str | None,
) -> None:
    with pytest.raises(LAUNCHER.LaunchBlocked, match="(?i)text"):
        LAUNCHER.resolve_launch(
            profile_name="normal",
            session="session",
            pane="pane",
            cwd=ROOT,
            expected_base="HEAD",
            executor="codex",
            task=task,
        )


def test_deepagents_rejects_incompatible_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = LAUNCHER.AgentProfile(
        Path("review.toml"),
        "review",
        "9router",
        "combo-review",
        None,
        False,
        "test",
        "review only",
    )
    monkeypatch.setattr(LAUNCHER, "_profile", lambda *args: profile)

    with pytest.raises(LAUNCHER.LaunchBlocked, match="not compatible"):
        LAUNCHER.resolve_launch(
            profile_name="review",
            session="session",
            pane="pane",
            cwd=ROOT,
            expected_base="HEAD",
            executor="deepagents",
            task="task",
        )


def test_codex_home_rejects_duplicate_stop_hook_scopes(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    project = tmp_path / "project"
    (project / ".codex").mkdir(parents=True)
    hooks = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "probe"}]}]}}
    (codex_home / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
    (project / ".codex" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")

    with pytest.raises(LAUNCHER.LaunchBlocked, match="duplicate Stop-hook scopes"):
        LAUNCHER._codex_runtime(project, codex_home)


def test_main_starts_with_selected_codex_home(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    evidence = {
        "registry_launcher": {
            "assignment_task_sha256": LAUNCHER._sha256_text("assign lane"),
        },
        "codex": {"codex_home": str(codex_home)},
        "herdr": {"executable": "herdr.exe", "agent_name": "xhigh-main"},
    }
    captured: dict[str, object] = {}
    commands: list[list[str]] = []

    monkeypatch.setattr(LAUNCHER, "resolve_launch", lambda **kwargs: (["herdr"], evidence))

    def fake_run(command, **kwargs):
        commands.append(command)
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(LAUNCHER, "_run", fake_run)

    assert LAUNCHER.main(
        [
            "--profile",
            "xhigh",
            "--session",
            "codex-probe",
            "--pane",
            "w1:p5",
            "--cwd",
            str(ROOT),
            "--expected-base",
            "HEAD",
            "--task",
            "assign lane",
        ]
    ) == 0
    assert captured["env"]["CODEX_HOME"] == str(codex_home.resolve())
    assert commands == [
        ["herdr"],
        [
            "herdr.exe",
            "--session",
            "codex-probe",
            "agent",
            "prompt",
            "xhigh-main",
            "assign lane",
            "--wait",
            "--timeout",
            "30000",
        ],
    ]
    output = capsys.readouterr().out.splitlines()
    assert json.loads(output[-1])["assignment"] == {
        "agent_name": "xhigh-main",
        "exit_code": 0,
        "phase": "prompt",
        "prompt_accepted": True,
        "session": "codex-probe",
        "status": "delivered",
        "task_sha256": LAUNCHER._sha256_text("assign lane"),
        "wait": "settled",
    }


def test_main_reports_failed_assignment_after_start(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    evidence = {
        "registry_launcher": {
            "assignment_task_sha256": LAUNCHER._sha256_text("assign lane"),
        },
        "codex": {"codex_home": str(codex_home)},
        "herdr": {"executable": "herdr.exe", "agent_name": "xhigh-main"},
    }
    calls = 0

    monkeypatch.setattr(LAUNCHER, "resolve_launch", lambda **kwargs: (["herdr"], evidence))

    def fake_run(command, **kwargs):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 7 if calls == 1 else 0, "", "start failed")

    monkeypatch.setattr(LAUNCHER, "_run", fake_run)

    assert LAUNCHER.main(
        [
            "--profile", "xhigh", "--session", "codex-probe", "--pane", "w1:p5",
            "--cwd", str(ROOT), "--expected-base", "HEAD", "--task", "assign lane",
        ]
    ) == 7
    output = capsys.readouterr().out.splitlines()
    assert json.loads(output[-1])["assignment"] == {
        "agent_name": "xhigh-main",
        "exit_code": 7,
        "phase": "start",
        "session": "codex-probe",
        "status": "failed",
        "task_sha256": LAUNCHER._sha256_text("assign lane"),
    }


def test_launcher_allows_external_codex_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_ENV", raising=False)

    environment = LAUNCHER._herdr_environment()

    assert "HERDR_ENV" not in environment


def test_profiles_share_launch_shape(tmp_path: Path) -> None:
    fake_profile(tmp_path, "normal", 20)
    fake_profile(tmp_path, "ui", None)
    profiles = LAUNCHER.load_agent_profiles(tmp_path / "agents")

    shapes = {
        tuple(LAUNCHER._redacted_arguments(LAUNCHER._codex_arguments(profile, tmp_path)))
        for profile in profiles.values()
    }

    assert len(shapes) == 2
    assert all(shape[:2] == ("-C", str(tmp_path)) for shape in shapes)


def test_missing_executable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LAUNCHER.shutil, "which", lambda name: None)

    with pytest.raises(LAUNCHER.LaunchBlocked, match="herdr"):
        LAUNCHER._executable("herdr")


def test_pane_safety_rejects_existing_agent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = {"result": {"panes": [{"pane_id": "p1", "cwd": str(tmp_path), "agent": "codex"}]}}
    monkeypatch.setattr(LAUNCHER, "_json_command", lambda command, **kwargs: payload)

    with pytest.raises(LAUNCHER.LaunchBlocked, match="already has agent"):
        LAUNCHER._herdr_pane(tmp_path, "session", "p1", "herdr")


def test_git_identity_rejects_non_root_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    values = iter([str(tmp_path), str(tmp_path / ".git"), "main", "head", "base"])
    monkeypatch.setattr(LAUNCHER, "_git_value", lambda cwd, *args: next(values))

    with pytest.raises(LAUNCHER.LaunchBlocked, match="exact Git worktree root"):
        LAUNCHER._git_identity(tmp_path / "subdir", "base")


def test_main_dry_run_emits_json_and_does_not_start(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    evidence = {"registry_launcher": {"profile": "xhigh"}}
    monkeypatch.setattr(LAUNCHER, "resolve_launch", lambda **kwargs: (["herdr"], evidence))
    run = monkeypatch.setattr(LAUNCHER, "_run", lambda command: (_ for _ in ()).throw(AssertionError()))

    assert LAUNCHER.main(
        [
            "--profile",
            "xhigh",
            "--session",
            "codex-probe",
            "--pane",
            "w1:p5",
            "--cwd",
            str(ROOT),
            "--expected-base",
            "HEAD",
            "--task",
            "dry run",
            "--dry-run",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == evidence
