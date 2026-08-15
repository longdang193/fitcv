"""
@meta
name: test_dcode_project
type: test
scope: unit
domain: runtime
distribution_tier: starter_kit
covers:
  - User-local DeepAgents launcher materializes role views from canonical templates
  - Local role-model binding selects each delegated tier
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_PATH = ROOT / "scripts" / "dcode_project.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LAUNCHER = load_module("dcode_project", LAUNCHER_PATH)


def write_role(
    root: Path,
    name: str,
    *,
    model_provider: str = "9router",
    model: str | None = None,
    rank: int = 20,
) -> None:
    (root / "agents").mkdir(parents=True, exist_ok=True)
    model = model or f"combo-{name}"
    (root / "agents" / f"{name}.toml").write_text(
        f'name = "{name}"\n'
        f'model_provider = "{model_provider}"\n'
        f'model = "{model}"\n'
        f'rank = {rank}\n'
        'description = "Role description"\n'
        'developer_instructions = "Return ROLE_OK."\n',
        encoding="utf-8",
    )


def test_local_role_views_use_canonical_prompt_and_local_model_map(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")

    roles = LAUNCHER._load_roles(tmp_path, "9router")
    agents_root = LAUNCHER._write_role_views(tmp_path, roles)
    rendered = (agents_root / "normal" / "AGENTS.md").read_text(encoding="utf-8")

    assert 'name: "normal"' in rendered
    assert 'model: "openai:combo-normal"' in rendered
    assert rendered.endswith("Return ROLE_OK.\n")
    assert (agents_root / ".dcode-project-owned").exists()


def test_local_role_views_refuse_unowned_directory(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")
    unowned = tmp_path / ".deepagents" / "agents" / "custom"
    unowned.mkdir(parents=True)
    (unowned / "AGENTS.md").write_text("custom\n", encoding="utf-8")

    roles = LAUNCHER._load_roles(tmp_path, "9router")

    with pytest.raises(RuntimeError, match="user-owned"):
        LAUNCHER._write_role_views(tmp_path, roles)


def test_local_role_views_replace_empty_retired_directories(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")
    (tmp_path / ".deepagents" / "agents" / "normal").mkdir(parents=True)

    roles = LAUNCHER._load_roles(tmp_path, "9router")
    agents_root = LAUNCHER._write_role_views(tmp_path, roles)

    assert (agents_root / ".dcode-project-owned").exists()
    assert (agents_root / "normal" / "AGENTS.md").exists()


def test_local_role_view_cleanup_removes_only_owned_files(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")
    roles = LAUNCHER._load_roles(tmp_path, "9router")
    agents_root = LAUNCHER._write_role_views(tmp_path, roles)
    user_file = agents_root / "normal" / "notes.txt"
    user_file.write_text("retain\n", encoding="utf-8")

    LAUNCHER._remove_role_views(tmp_path, roles)

    assert not (agents_root / ".dcode-project-owned").exists()
    assert not (agents_root / "normal" / "AGENTS.md").exists()
    assert user_file.read_text(encoding="utf-8") == "retain\n"


def test_local_role_view_cleanup_keeps_unmarked_matching_view(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")
    roles = LAUNCHER._load_roles(tmp_path, "9router")
    agents_root = tmp_path / ".deepagents" / "agents"
    view = agents_root / "normal" / "AGENTS.md"
    view.parent.mkdir(parents=True)
    view.write_text(LAUNCHER._role_view_content(roles[0]), encoding="utf-8")

    LAUNCHER._remove_role_views(tmp_path, roles)

    assert view.exists()


def test_local_role_views_refuse_user_file_after_owned_generation(tmp_path: Path) -> None:
    write_role(tmp_path, "normal")
    roles = LAUNCHER._load_roles(tmp_path, "9router")
    agents_root = LAUNCHER._write_role_views(tmp_path, roles)
    (agents_root / "custom.txt").write_text("retain\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="user-owned"):
        LAUNCHER._write_role_views(tmp_path, roles)


def test_local_role_view_write_failure_cleans_partial_generated_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    write_role(tmp_path, "normal")
    roles = LAUNCHER._load_roles(tmp_path, "9router")
    original_write_text = Path.write_text

    def fail_role_view(self: Path, data: str, *args: object, **kwargs: object) -> int:
        if self.name == "AGENTS.md":
            raise OSError("disk full")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_role_view)

    with pytest.raises(OSError, match="disk full"):
        LAUNCHER._write_role_views(tmp_path, roles)

    assert not (tmp_path / ".deepagents").exists()


def test_main_cleans_owned_role_views_after_dcode_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    write_role(tmp_path, "normal")
    config_path = tmp_path / "dcode-project.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(LAUNCHER, "_config_path", lambda: config_path)
    monkeypatch.setattr(LAUNCHER, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        LAUNCHER,
        "_runtime_binding",
        lambda config: ("combo-high", "https://provider.example/v1", "secret", "9router"),
    )
    monkeypatch.setattr(LAUNCHER, "_codex_config", lambda config: {})
    monkeypatch.setattr(
        LAUNCHER,
        "_mcp_capabilities",
        lambda config: {
            "mcp_servers": [],
            "mcp_tools": [],
            "server_tools": {},
            "mcp_capability_digest": "digest",
        },
    )
    monkeypatch.setattr(LAUNCHER, "_reject_conflicting_user_openai_base_url", lambda: None)
    monkeypatch.setattr(LAUNCHER, "_find_dcode", lambda: "dcode")

    def fail_dcode(*args: object, **kwargs: object) -> None:
        assert (tmp_path / ".deepagents" / "agents" / "normal" / "AGENTS.md").is_file()
        raise OSError("dcode unavailable")

    monkeypatch.setattr(LAUNCHER.subprocess, "run", fail_dcode)

    with pytest.raises(OSError, match="dcode unavailable"):
        LAUNCHER.main(["--role", "normal", "-n", "task"])

    assert not (tmp_path / ".deepagents").exists()


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["-n", "task"], "requires `--role"),
        (["--role", "missing", "-n", "task"], "Unknown role `missing`"),
    ],
)
def test_main_rejects_missing_or_unknown_role_before_role_view_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
    message: str,
) -> None:
    write_role(tmp_path, "normal")
    config_path = tmp_path / "dcode-project.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(LAUNCHER, "_config_path", lambda: config_path)
    monkeypatch.setattr(LAUNCHER, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        LAUNCHER,
        "_runtime_binding",
        lambda config: ("combo-high", "https://provider.example/v1", "secret", "9router"),
    )
    monkeypatch.setattr(LAUNCHER, "_codex_config", lambda config: {})
    monkeypatch.setattr(
        LAUNCHER,
        "_mcp_capabilities",
        lambda config: {
            "mcp_servers": [],
            "mcp_tools": [],
            "server_tools": {},
            "mcp_capability_digest": "digest",
        },
    )

    with pytest.raises(RuntimeError, match=message):
        LAUNCHER.main(argv)

    assert not (tmp_path / ".deepagents").exists()


@pytest.mark.parametrize(
    "argument",
    [
        "--agent",
        "--model=combo-normal",
        "-Mcombo-normal",
        "--resume",
        "-rthread-id",
        "--yolo",
        "--mcp-config",
        "--trust-project-mcp",
        "--shell-allow-list",
        "--allow-fs-tools",
        "--interpreter-tools",
        "--sandbox",
        "--startup-cmd",
        "--max-retries",
        "--rubric-model",
        "--default-model",
        "--clear-default-model",
        "mcp",
    ],
)
def test_launcher_rejects_unmanaged_runtime_options(argument: str) -> None:
    with pytest.raises(RuntimeError, match="no Codex permission or MCP projection"):
        LAUNCHER._reject_unmanaged_runtime_options([argument])


def test_launcher_rejects_direct_stdin() -> None:
    with pytest.raises(RuntimeError, match="does not accept direct `--stdin`.*--handoff-file"):
        LAUNCHER._reject_unmanaged_runtime_options(["--stdin"])


def test_launcher_allows_bounded_noninteractive_options() -> None:
    LAUNCHER._reject_unmanaged_runtime_options(
        [
            "--print-config",
            "--role",
            "normal",
            "--json",
            "--max-turns",
            "4",
            "--timeout=120",
            "--rubric",
            "@acceptance.md",
            "--no-mcp",
            "-n",
            "task",
        ]
    )


@pytest.mark.parametrize("argument", ["--timeout", "--rubric"])
def test_launcher_rejects_missing_bounded_option_value(argument: str) -> None:
    with pytest.raises(RuntimeError, match="requires a value"):
        LAUNCHER._reject_unmanaged_runtime_options([argument])


@pytest.mark.parametrize(
    ("role_name", "model", "rank"),
    [
        ("low", "combo-low", 10),
        ("normal", "combo-normal", 20),
        ("high", "combo-high", 30),
        ("xhigh", "combo-xhigh", 40),
    ],
)
def test_main_uses_selected_role_model_and_fixed_local_capabilities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    role_name: str,
    model: str,
    rank: int,
) -> None:
    for candidate_name, candidate_model, candidate_rank in [
        ("low", "combo-low", 10),
        ("normal", "combo-normal", 20),
        ("high", "combo-high", 30),
        ("xhigh", "combo-xhigh", 40),
    ]:
        write_role(tmp_path, candidate_name, model=candidate_model, rank=candidate_rank)
    config_path = tmp_path / "dcode-project.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(LAUNCHER, "_config_path", lambda: config_path)
    monkeypatch.setattr(LAUNCHER, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        LAUNCHER,
        "_runtime_binding",
        lambda config: ("combo-high", "https://provider.example/v1", "secret", "9router"),
    )
    monkeypatch.setattr(LAUNCHER, "_codex_config", lambda config: {})
    monkeypatch.setattr(
        LAUNCHER,
        "_mcp_capabilities",
        lambda config: {
            "mcp_servers": [],
            "mcp_tools": [],
            "server_tools": {},
            "mcp_capability_digest": "digest",
        },
    )
    monkeypatch.setattr(LAUNCHER, "_reject_conflicting_user_openai_base_url", lambda: None)
    monkeypatch.setattr(LAUNCHER, "_find_dcode", lambda: "dcode")
    invoked: list[object] = []
    invoked_kwargs: dict[str, object] = {}

    def complete_dcode(*args: object, **kwargs: object) -> subprocess.CompletedProcess[object]:
        invoked.extend(args)
        invoked_kwargs.update(kwargs)
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(LAUNCHER.subprocess, "run", complete_dcode)

    assert LAUNCHER.main(["--role", role_name, "--json", "--no-mcp", "-n", "task"]) == 0
    file_tool_root = "/" + tmp_path.relative_to(tmp_path.anchor).as_posix()
    assert invoked[0] == [
        "dcode",
        "-M",
        f"openai:{model}",
        "--allow-fs-tools",
        "all",
        "--shell-allow-list",
        "git,py",
        "--json",
        "-n",
        (
            "task Native filesystem tool root: "
            f"`{file_tool_root}`. Use this exact prefix for file paths; do not use "
            "`/workspace/...` or Windows drive syntax. Read only named source, test, "
            "and text files with filesystem tools. Never use filesystem tools on "
            "database, binary, archive, or runtime artifacts; examples: `*.sqlite`, "
            "`*.sqlite3`, `*.db`, `*-wal`, `*-shm`, `*-journal`, `*.zip`, `*.tar`, "
            "`*.gz`, `*.7z`, `*.bin`, `*.exe`, images, or media. For SQLite evidence, "
            "use launcher-authorized `py` from repository root with stdlib `sqlite3` "
            "read-only URI mode: `sqlite3.connect(\"file:<repo-relative-path>?mode=ro\", "
            "uri=True)`. Run `py` directly; do not prefix it with `cd`, shell operators, "
            "or wrappers. For `py -c`, use one expression; never use `;`."
        ),
        "--no-mcp",
    ]
    assert invoked_kwargs["cwd"] == tmp_path
    assert not (tmp_path / ".deepagents").exists()


def test_print_config_reports_selected_role_effective_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_role(tmp_path, "normal", model="combo-normal", rank=20)
    config_path = tmp_path / "dcode-project.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(LAUNCHER, "_config_path", lambda: config_path)
    monkeypatch.setattr(LAUNCHER, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        LAUNCHER,
        "_runtime_binding",
        lambda config: ("combo-high", "https://provider.example/v1", "secret", "9router"),
    )
    monkeypatch.setattr(LAUNCHER, "_codex_config", lambda config: {})
    monkeypatch.setattr(
        LAUNCHER,
        "_mcp_capabilities",
        lambda config: {
            "mcp_servers": [],
            "mcp_tools": [],
            "server_tools": {},
            "mcp_capability_digest": "digest",
        },
    )

    assert LAUNCHER.main(["--role", "normal", "--print-config"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_role"] == "normal"
    assert payload["effective_model"] == "openai:combo-normal"
    assert payload["controller_model"] == "openai:combo-high"


def test_role_model_comes_from_canonical_template(tmp_path: Path) -> None:
    write_role(tmp_path, "normal", model="combo-low")

    roles = LAUNCHER._load_roles(tmp_path, "9router")

    assert roles[0]["model"] == "combo-low"
    assert roles[0]["model_provider"] == "9router"


def test_role_loader_rejects_mismatched_runtime_provider(tmp_path: Path) -> None:
    write_role(tmp_path, "normal", model_provider="other")

    with pytest.raises(RuntimeError, match="does not match runtime provider"):
        LAUNCHER._load_roles(tmp_path, "9router")


def test_role_loader_rejects_duplicate_ranks(tmp_path: Path) -> None:
    write_role(tmp_path, "low", rank=10)
    write_role(tmp_path, "normal", rank=10)

    with pytest.raises(RuntimeError, match="ranks must be unique"):
        LAUNCHER._load_roles(tmp_path, "9router")


def test_canonical_role_hierarchy_is_source_owned() -> None:
    roles = {
        role["name"]: (role["model_provider"], role["model"], role["rank"])
        for role in LAUNCHER._load_roles(ROOT, "9router")
    }

    assert roles == {
        "low": ("9router", "combo-low", 10),
        "normal": ("9router", "combo-normal", 20),
        "high": ("9router", "combo-high", 30),
        "xhigh": ("9router", "combo-xhigh", 40),
    }


def test_runtime_environment_reaches_deepagents_server_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    environment = LAUNCHER._runtime_environment("http://127.0.0.1:20128/v1", "test-key")

    assert environment["DEEPAGENTS_CODE_OPENAI_BASE_URL"] == "http://127.0.0.1:20128/v1"
    assert environment["DEEPAGENTS_CODE_OPENAI_API_KEY"] == "test-key"
    assert environment["OPENAI_BASE_URL"] == "http://127.0.0.1:20128/v1"
    assert environment["OPENAI_API_KEY"] == "test-key"

def mcp_config() -> dict[str, object]:
    return {
        "mcp_servers": {
            "context7": {"tools": {"resolve_library_id": {}, "query_docs": {}}},
            "serena": {"tools": {"find_symbol": {}}},
        }
    }

def handoff_payload(capabilities: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "codex.mcp.handoff.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mcp_capability_digest": capabilities["mcp_capability_digest"],
        "sources": [{"server": "context7", "tool": "query_docs"}],
        "facts": [{"source": 0, "value": "DeepAgents supports task-based subagent delegation."}],
        "constraints": ["Do not call MCP tools."],
    }

def test_mcp_capability_projection_omits_runtime_values() -> None:
    capabilities = LAUNCHER._mcp_capabilities(mcp_config())

    assert capabilities["mcp_servers"] == ["context7", "serena"]
    assert capabilities["mcp_tools"] == [
        "context7.query_docs",
        "context7.resolve_library_id",
        "serena.find_symbol",
    ]
    assert "https://" not in json.dumps(capabilities)

def test_mcp_selection_narrows_and_rejects_unknown() -> None:
    capabilities = LAUNCHER._mcp_capabilities(mcp_config())

    assert LAUNCHER._parse_mcp_selection(["context7.query_docs"], capabilities) == [
        "context7.query_docs"
    ]
    with pytest.raises(RuntimeError, match="Unknown MCP tool"):
        LAUNCHER._parse_mcp_selection(["context7.missing"], capabilities)

def test_handoff_validation_accepts_current_selected_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(LAUNCHER, "_handoff_root", lambda: tmp_path)
    capabilities = LAUNCHER._mcp_capabilities(mcp_config())
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(handoff_payload(capabilities)), encoding="utf-8")

    resolved, payload = LAUNCHER._validate_handoff(
        str(path), capabilities, ["context7.query_docs"]
    )

    assert resolved == path
    assert payload["schema"] == "codex.mcp.handoff.v1"

@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda payload: payload["facts"][0]["value"] == "Bearer secret", "sensitive"),
        (lambda payload: payload.update({"schema": "bad"}), "Unsupported handoff schema"),
        (lambda payload: payload.update({"mcp_capability_digest": "bad"}), "digest"),
    ],
)
def test_handoff_validation_rejects_unsafe_or_mismatched_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutator: object,
    message: str,
) -> None:
    monkeypatch.setattr(LAUNCHER, "_handoff_root", lambda: tmp_path)
    capabilities = LAUNCHER._mcp_capabilities(mcp_config())
    payload = handoff_payload(capabilities)
    if message == "sensitive":
        payload["facts"][0]["value"] = "Bearer secret"
    else:
        mutator(payload)
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        LAUNCHER._validate_handoff(str(path), capabilities, ["context7.query_docs"])

def test_handoff_validation_rejects_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(LAUNCHER, "_handoff_root", lambda: tmp_path)
    capabilities = LAUNCHER._mcp_capabilities(mcp_config())
    source = tmp_path / "source.json"
    source.write_text(json.dumps(handoff_payload(capabilities)), encoding="utf-8")
    link = tmp_path / "handoff.json"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("Symlink creation unavailable")

    with pytest.raises(RuntimeError, match="symlink"):
        LAUNCHER._validate_handoff(str(link), capabilities, ["context7.query_docs"])

def test_handoff_instruction_moves_validated_payload_to_stdin() -> None:
    argv = ["-n", "caller task", "--no-mcp"]
    payload = {
        "schema": "codex.mcp.handoff.v1",
        "sources": [{"server": "context7", "tool": "resolve_library_id"}],
        "facts": [{"source": 0, "value": {"official_library_id": "/python/cpython"}}],
        "constraints": ["Do not call MCP tools."],
    }

    task = LAUNCHER._handoff_stdin(argv, payload)

    assert argv == ["--stdin", "--no-mcp"]
    assert task.startswith("caller task")
    assert "Use this validated Codex MCP handoff payload" in task
    assert '"official_library_id":"/python/cpython"' in task
    assert "handoff.json" not in task


def test_handoff_stdin_preserves_binary_file_safety_context(tmp_path: Path) -> None:
    argv = ["-n", "caller task", "--no-mcp"]
    payload = {
        "schema": "codex.mcp.handoff.v1",
        "sources": [],
        "facts": [],
        "constraints": [],
    }

    LAUNCHER._append_bounded_task_context(argv, tmp_path)
    task = LAUNCHER._handoff_stdin(argv, payload)

    assert "Never use filesystem tools on database, binary, archive, or runtime artifacts" in task
    assert '`sqlite3.connect("file:<repo-relative-path>?mode=ro", uri=True)`' in task
    assert "Run `py` directly; do not prefix it with `cd`, shell operators, or wrappers" in task
    assert "For `py -c`, use one expression; never use `;`" in task


def test_setup_launcher_uses_current_repository_source() -> None:
    setup = (ROOT / "scripts" / "setup_deepagents_runtime.ps1").read_text(encoding="utf-8")

    assert "Copy-Item" not in setup
    assert "git rev-parse --show-toplevel" in setup
    assert 'Join-Path $repoRoot "scripts\\dcode_project.py"' in setup
    assert 'dcode-project.ps1' in setup
    assert 'Join-Path $HOME ".deepagents\\.mcp.json"' in setup
    assert "Direct DeepAgents MCP config detected" in setup
