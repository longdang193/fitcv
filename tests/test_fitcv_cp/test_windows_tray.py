"""@meta
name: test_windows_tray
type: test
domain: fitcv_local
ownership: infrastructure
responsibility:
  - Verify tray lifecycle is safe outside Windows.
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from inspect import getsource
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_windows_tray_is_noop_outside_windows() -> None:
    from fitcv_cp.windows_tray import WindowsTray

    tray = WindowsTray(
        url="http://127.0.0.1:1234/",
        on_open=MagicMock(),
        on_shutdown=MagicMock(),
    )

    with patch("fitcv_cp.windows_tray.os.name", "posix"):
        assert tray.start() is False
        tray.stop()


def test_windows_tray_dispatches_open_and_shutdown_commands() -> None:
    from fitcv_cp.windows_tray import ID_OPEN, ID_SHUTDOWN, WindowsTray

    on_open = MagicMock()
    on_shutdown = MagicMock()
    tray = WindowsTray(
        url="http://127.0.0.1:1234/",
        on_open=on_open,
        on_shutdown=on_shutdown,
    )

    tray._dispatch_command(ID_OPEN)
    tray._dispatch_command(ID_SHUTDOWN)

    on_open.assert_called_once_with()
    on_shutdown.assert_called_once_with()


def test_windows_tray_avoids_persistent_shell_icon_identity() -> None:
    from fitcv_cp.windows_tray import WindowsTray

    assert "NIF_GUID" not in getsource(WindowsTray._run_windows)


def test_windows_tray_assigns_owner_window_before_registration() -> None:
    from fitcv_cp.windows_tray import WindowsTray

    source = getsource(WindowsTray._run_windows)

    assert source.index("notify_data.hWnd = hwnd") < source.index(
        "shell32.Shell_NotifyIconW(NIM_ADD"
    )


def test_frozen_tray_icon_resolves_pyinstaller_internal_directory(tmp_path: Path) -> None:
    from fitcv_cp import windows_tray

    icon_path = tmp_path / "_internal" / "fitcv.ico"
    icon_path.parent.mkdir()
    icon_path.write_bytes(b"icon")

    with patch.object(windows_tray.sys, "_MEIPASS", str(tmp_path), create=True):
        assert windows_tray._default_icon_path() == icon_path
