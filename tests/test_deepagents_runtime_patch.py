from pathlib import Path

from scripts.patch_deepagents_runtime import (
    patch_headless_mcp_guard,
    patch_mcp_tools,
    patch_stdio_lookup,
)


def test_patch_mcp_tools_avoids_async_path_resolution(tmp_path: Path) -> None:
    target = tmp_path / "mcp_tools.py"
    target.write_text(
        "    if explicit_config_path:\n"
        "        config_path = (\n"
        "            str(project_context.resolve_user_path(explicit_config_path))\n"
        "            if project_context is not None\n"
        "            else explicit_config_path\n"
        "        )\n"
        "        configs.append(load_mcp_config(config_path))\n",
        encoding="utf-8",
    )

    assert patch_mcp_tools(target) is True
    patched = target.read_text(encoding="utf-8")
    assert "resolve_user_path(explicit_config_path)" not in patched
    assert "Path(explicit_config_path).expanduser()" in patched
    assert patch_mcp_tools(target) is False


def test_patch_stdio_lookup_offloads_windows_command_resolution(tmp_path: Path) -> None:
    target = tmp_path / "mcp_tools.py"
    target.write_text(
        '    params = StdioServerParameters(\n'
        '        command=stdio["command"],\n'
        '        args=stdio["args"],\n'
        '        # Already expanded: `_build_connection` runs `resolve_mcp_server_env`\n'
        '        # over `env` before the connection is built, with a richer grammar\n'
        '        # (`${VAR:-default}`) that raises on an unset reference. A second pass\n'
        '        # here could only re-scan resolved secrets and warn about a value that\n'
        '        # legitimately contains `${`.\n'
        '        env=stdio.get("env"),\n'
        '        cwd=stdio.get("cwd"),\n'
        '        encoding=encoding,\n'
        '        encoding_error_handler=errors,\n'
        '    )\n',
        encoding="utf-8",
    )

    assert patch_stdio_lookup(target) is True
    patched = target.read_text(encoding="utf-8")
    assert "await asyncio.to_thread(shutil.which, params.command)" in patched
    assert patch_stdio_lookup(target) is False


def test_patch_headless_mcp_guard_allows_only_browser_list_probe(
    tmp_path: Path,
) -> None:
    target = tmp_path / "auto_mode.py"
    target.write_text(
        "    def _rejection(self, request: ToolCallRequest) -> ToolMessage | None:\n"
        "        if request.tool_call[\"name\"] not in self._tool_names:\n"
        "            return None\n"
        "        return ToolMessage(\n"
        "            content=(\n"
        "                \"This MCP action requires approval, but the current headless runtime \"\n"
        "                \"has no approval UI. Run it in the interactive TUI or choose a \"\n"
        "                \"read-only MCP action.\"\n"
        "            ),\n"
        "            name=request.tool_call[\"name\"],\n"
        "            tool_call_id=_tool_call_id(request.tool_call),\n"
        "            status=\"error\",\n"
        "        )\n",
        encoding="utf-8",
    )

    assert patch_headless_mcp_guard(target) is True
    patched = target.read_text(encoding="utf-8")
    assert 'args.get("action") == "list"' in patched
    assert "name == \"playwright_browser_tabs\"" in patched
    assert patch_headless_mcp_guard(target) is False
