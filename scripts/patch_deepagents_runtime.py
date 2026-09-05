"""Apply local compatibility patches to the pinned DeepAgents runtime."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


_VULNERABLE = """    if explicit_config_path:
        config_path = (
            str(project_context.resolve_user_path(explicit_config_path))
            if project_context is not None
            else explicit_config_path
        )
        configs.append(load_mcp_config(config_path))
"""
_PATCHED = """    if explicit_config_path:
        config_path = Path(explicit_config_path).expanduser()
        if not config_path.is_absolute() and project_context is not None:
            config_path = project_context.user_cwd / config_path
        configs.append(load_mcp_config(str(config_path)))
"""
_STDIO_LOOKUP = """    params = StdioServerParameters(
        command=stdio["command"],
        args=stdio["args"],
        # Already expanded: `_build_connection` runs `resolve_mcp_server_env`
        # over `env` before the connection is built, with a richer grammar
        # (`${VAR:-default}`) that raises on an unset reference. A second pass
        # here could only re-scan resolved secrets and warn about a value that
        # legitimately contains `${`.
        env=stdio.get("env"),
        cwd=stdio.get("cwd"),
        encoding=encoding,
        encoding_error_handler=errors,
    )
"""
_STDIO_LOOKUP_ADD = _STDIO_LOOKUP + """    resolved_command = await asyncio.to_thread(shutil.which, params.command)
    if resolved_command:
        params.command = resolved_command
"""
_WINDOWS_LOOKUP = """    try:
        # First check if command exists on PATH as-is
        if command_path := shutil.which(command):
"""
_WINDOWS_LOOKUP_ADD = """    try:
        if Path(command).is_absolute():
            return command
        # First check if command exists on PATH as-is
        if command_path := shutil.which(command):
"""
_PROCESS_FALLBACK = """    except Exception:
        # Try again without creation flags
        process = await anyio.open_process(
            [command, *args],
            env=env,
            stderr=errlog,
            cwd=cwd,
        )
"""
_PROCESS_FALLBACK_ADD = """    except Exception:
        process = await _create_windows_fallback_process(command, args, env, errlog, cwd)
"""
_FALLBACK_FUNCTION = re.compile(
    r"async def _create_windows_fallback_process\(.*?\n\ndef _create_job_object",
    re.DOTALL,
)
_FALLBACK_REPLACEMENT = """def _spawn_windows_process(
    command: str,
    args: list[str],
    env: dict[str, str] | None,
    errlog: TextIO | None,
    cwd: Path | str | None,
) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errlog,
            env=env,
            cwd=cwd,
            bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errlog,
            env=env,
            cwd=cwd,
            bufsize=0,
        )


async def _create_windows_fallback_process(
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
    errlog: TextIO | None = sys.stderr,
    cwd: Path | str | None = None,
) -> FallbackProcess:
    popen_obj = await to_thread.run_sync(
        _spawn_windows_process,
        command,
        args,
        env,
        errlog,
        cwd,
    )
    return FallbackProcess(popen_obj)


def _create_job_object"""
_HEADLESS_MCP_REJECTION = """    def _rejection(self, request: ToolCallRequest) -> ToolMessage | None:
        if request.tool_call[\"name\"] not in self._tool_names:
            return None
        return ToolMessage(
            content=(
                \"This MCP action requires approval, but the current headless runtime \"
                \"has no approval UI. Run it in the interactive TUI or choose a \"
                \"read-only MCP action.\"
            ),
            name=request.tool_call[\"name\"],
            tool_call_id=_tool_call_id(request.tool_call),
            status=\"error\",
        )
"""
_HEADLESS_MCP_REJECTION_PATCHED = """    def _rejection(self, request: ToolCallRequest) -> ToolMessage | None:
        name = request.tool_call[\"name\"]
        if name not in self._tool_names:
            return None
        args = request.tool_call.get(\"args\")
        if (
            name == \"playwright_browser_tabs\"
            and isinstance(args, dict)
            and args.get(\"action\") == \"list\"
        ):
            return None
        return ToolMessage(
            content=(
                \"This MCP action requires approval, but the current headless runtime \"
                \"has no approval UI. Run it in the interactive TUI or choose a \"
                \"read-only MCP action.\"
            ),
            name=name,
            tool_call_id=_tool_call_id(request.tool_call),
            status=\"error\",
        )
"""


def _replace_once(target: Path, old: str, new: str, label: str) -> bool:
    content = target.read_text(encoding="utf-8")
    if new in content:
        return False
    if old not in content:
        raise RuntimeError(f"Unsupported {label}: {target}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def patch_mcp_tools(target: Path) -> bool:
    return _replace_once(target, _VULNERABLE, _PATCHED, "DeepAgents MCP runtime")


def patch_stdio_lookup(target: Path) -> bool:
    return _replace_once(target, _STDIO_LOOKUP, _STDIO_LOOKUP_ADD, "DeepAgents stdio runtime")


def patch_windows_lookup(target: Path) -> bool:
    return _replace_once(target, _WINDOWS_LOOKUP, _WINDOWS_LOOKUP_ADD, "MCP Windows runtime")


def patch_windows_process(target: Path) -> bool:
    content = target.read_text(encoding="utf-8")
    changed = False
    if _PROCESS_FALLBACK in content:
        content = content.replace(_PROCESS_FALLBACK, _PROCESS_FALLBACK_ADD, 1)
        changed = True
    if "def _spawn_windows_process(" not in content:
        content, count = _FALLBACK_FUNCTION.subn(_FALLBACK_REPLACEMENT, content, count=1)
        if count != 1:
            raise RuntimeError(f"Unsupported MCP Windows process runtime: {target}")
        changed = True
    if changed:
        target.write_text(content, encoding="utf-8")
    return changed


def patch_headless_mcp_guard(target: Path) -> bool:
    return _replace_once(
        target,
        _HEADLESS_MCP_REJECTION,
        _HEADLESS_MCP_REJECTION_PATCHED,
        "DeepAgents headless MCP guard",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mcp_tools", type=Path)
    args = parser.parse_args()
    auto_mode = args.mcp_tools.with_name("auto_mode.py")
    utility = args.mcp_tools.parents[1] / "mcp" / "os" / "win32" / "utilities.py"
    changed = patch_mcp_tools(args.mcp_tools)
    changed = patch_stdio_lookup(args.mcp_tools) or changed
    changed = patch_headless_mcp_guard(auto_mode) or changed
    changed = patch_windows_lookup(utility) or changed
    changed = patch_windows_process(utility) or changed
    status = "patched" if changed else "already patched"
    print(f"DeepAgents MCP runtime {status}: {args.mcp_tools}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
