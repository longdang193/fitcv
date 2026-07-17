"""@meta
name: windows_tray
type: module
domain: fitcv_local
ownership: infrastructure
responsibility:
  - Provide a lightweight native Windows tray menu for FitCV Local.
inputs:
  - Local app URL
  - Open and shutdown callbacks
outputs:
  - Tray icon with Open and Shutdown actions
lifecycle:
  - status: active
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Callable


logger = logging.getLogger(__name__)

WM_USER = 0x0400
WM_TRAY = WM_USER + 1
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203
WM_CONTEXTMENU = 0x007B
WM_NULL = 0x0000
NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NOTIFYICON_VERSION_4 = 4
MF_STRING = 0x00000000
TPM_RIGHTBUTTON = 0x00000002
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040
IDC_ARROW = 32512
HWND_MESSAGE = -3
ID_OPEN = 1001
ID_SHUTDOWN = 1002
def _default_icon_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        root = Path(str(frozen_root))
        direct = root / "fitcv.ico"
        internal = root / "_internal" / "fitcv.ico"
        return direct if direct.exists() else internal
    return Path(__file__).resolve().parents[2] / "packaging" / "windows" / "fitcv.ico"


class WindowsTray:
    def __init__(
        self,
        *,
        url: str,
        on_open: Callable[[], None],
        on_shutdown: Callable[[], None],
        icon_path: Path | None = None,
    ) -> None:
        self.url = url
        self.on_open = on_open
        self.on_shutdown = on_shutdown
        self.icon_path = icon_path or _default_icon_path()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._started = False

    def start(self) -> bool:
        if os.name != "nt":
            return False
        if self._thread is not None and self._thread.is_alive():
            return self._started
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="fitcv-tray",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=2)
        return self._started

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            return
        if self._hwnd is not None and os.name == "nt":
            try:
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                user32.PostMessageW.argtypes = [
                    wintypes.HWND,
                    wintypes.UINT,
                    wintypes.WPARAM,
                    wintypes.LPARAM,
                ]
                user32.PostMessageW.restype = wintypes.BOOL
                user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
            except (AttributeError, OSError):
                logger.debug("FitCV tray shutdown message failed", exc_info=True)
        if thread is not threading.current_thread():
            thread.join(timeout=2)
        self._thread = None

    def _dispatch_command(self, command_id: int) -> None:
        if command_id == ID_OPEN:
            self.on_open()
        elif command_id == ID_SHUTDOWN:
            self.on_shutdown()

    def _run(self) -> None:
        try:
            self._run_windows()
        except Exception:
            logger.warning("FitCV tray startup failed; continuing without tray", exc_info=True)
        finally:
            self._started = False
            self._hwnd = None
            self._ready.set()

    def _run_windows(self) -> None:
        if not self.icon_path.exists():
            logger.warning("FitCV tray icon not found: %s", self.icon_path)
            self._ready.set()
            return

        from ctypes import wintypes

        handle_type = ctypes.c_void_p

        class Guid(ctypes.Structure):
            _fields_ = [
                ("data1", wintypes.DWORD),
                ("data2", wintypes.WORD),
                ("data3", wintypes.WORD),
                ("data4", wintypes.BYTE * 8),
            ]

        class NotifyIconData(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", handle_type),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", handle_type),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", Guid),
                ("hBalloonIcon", handle_type),
            ]

        class Point(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class WindowClassEx(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("lpfnWndProc", handle_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", handle_type),
                ("hIcon", handle_type),
                ("hCursor", handle_type),
                ("hbrBackground", handle_type),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
                ("hIconSm", handle_type),
            ]

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32
        user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyWindow.restype = wintypes.BOOL
        shell32.Shell_NotifyIconW.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(NotifyIconData),
        ]
        shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        class_name = f"FitCVTrayWindow_{os.getpid()}"
        hinstance = kernel32.GetModuleHandleW(None)
        icon = user32.LoadImageW(
            None,
            str(self.icon_path),
            IMAGE_ICON,
            0,
            0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        if not icon:
            raise OSError(f"LoadImageW failed for {self.icon_path}")

        def show_menu(hwnd: int) -> None:
            menu = user32.CreatePopupMenu()
            if not menu:
                return
            try:
                user32.InsertMenuW(menu, 0, MF_STRING, ID_OPEN, "Open FitCV")
                user32.InsertMenuW(menu, 1, MF_STRING, ID_SHUTDOWN, "Shutdown FitCV")
                point = Point()
                user32.GetCursorPos(ctypes.byref(point))
                user32.SetForegroundWindow(hwnd)
                user32.TrackPopupMenu(
                    menu,
                    TPM_RIGHTBUTTON,
                    point.x,
                    point.y,
                    0,
                    hwnd,
                    None,
                )
                user32.PostMessageW(hwnd, WM_NULL, 0, 0)
            finally:
                user32.DestroyMenu(menu)

        @ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        def window_proc(hwnd, message, wparam, lparam):
            if message == WM_TRAY:
                event = int(lparam) & 0xFFFF
                if event in {WM_RBUTTONUP, WM_CONTEXTMENU}:
                    show_menu(hwnd)
                elif event == WM_LBUTTONDBLCLK:
                    self._dispatch_command(ID_OPEN)
                return 0
            if message == WM_COMMAND:
                self._dispatch_command(int(wparam) & 0xFFFF)
                return 0
            if message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(notify_data))
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        window_class = WindowClassEx()
        window_class.cbSize = ctypes.sizeof(WindowClassEx)
        window_class.lpfnWndProc = ctypes.cast(window_proc, handle_type)
        window_class.hInstance = hinstance
        window_class.hCursor = user32.LoadCursorW(None, IDC_ARROW)
        window_class.lpszClassName = class_name
        if not user32.RegisterClassExW(ctypes.byref(window_class)):
            raise OSError(f"RegisterClassExW failed for {class_name}")

        notify_data = NotifyIconData()
        notify_data.cbSize = ctypes.sizeof(NotifyIconData)
        notify_data.uID = 1
        notify_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        notify_data.uCallbackMessage = WM_TRAY
        notify_data.hIcon = icon
        notify_data.szTip = "FitCV"
        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "FitCV",
            0,
            0,
            0,
            0,
            0,
            handle_type(HWND_MESSAGE),
            None,
            hinstance,
            None,
        )
        if not hwnd:
            user32.UnregisterClassW(class_name, hinstance)
            raise OSError("CreateWindowExW failed for FitCV tray")
        notify_data.hWnd = hwnd
        self._hwnd = int(hwnd)
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(notify_data)):
            user32.DestroyWindow(hwnd)
            user32.UnregisterClassW(class_name, hinstance)
            raise OSError("Shell_NotifyIconW failed for FitCV tray")
        notify_data.uVersion = NOTIFYICON_VERSION_4
        shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(notify_data))
        self._started = True
        self._ready.set()

        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

        user32.UnregisterClassW(class_name, hinstance)
