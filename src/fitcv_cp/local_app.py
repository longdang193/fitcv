"""@meta
name: local_app
type: script
domain: fitcv_local
ownership: infrastructure
responsibility:
  - Launch one loopback-bound packaged FitCV process.
  - Serialize packaged background work without Redis or RQ workers.
inputs:
  - Packaged application resources
  - User-owned local storage bootstrap
outputs:
  - Browser-accessible local control plane
  - Sanitized runtime metadata
lifecycle:
  - status: active
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import webbrowser
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable, TypeVar

from fitcv_cp.local_storage import LocalStoragePaths, activate_local_storage


_Result = TypeVar("_Result")
logger = logging.getLogger(__name__)


class LocalAppBusyError(RuntimeError):
    """Raised when packaged runtime already owns active work."""


class LocalJobExecutor:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fitcv-local")
        self._lock = threading.Lock()
        self._active: Future[object] | None = None

    def submit(
        self, function: Callable[..., _Result], *args: object
    ) -> Future[_Result]:
        with self._lock:
            if self._active is not None and not self._active.done():
                raise LocalAppBusyError("FitCV Local is already running a job")
            future = self._executor.submit(function, *args)
            self._active = future
            return future

    def is_busy(self) -> bool:
        with self._lock:
            return self._active is not None and not self._active.done()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)


_LOCAL_EXECUTOR = LocalJobExecutor()


def get_local_job_executor() -> LocalJobExecutor:
    return _LOCAL_EXECUTOR


def prepare_local_environment() -> None:
    os.environ["FITCV_LOCAL_MODE"] = "1"
    os.environ["FITCV_CP_INLINE_EXECUTION"] = "1"
    os.environ.pop("REDIS_URL", None)


def _bundle_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(str(frozen_root)).resolve() if frozen_root else Path.cwd().resolve()


def _prebound_socket() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(socket.SOMAXCONN)
    return listener


def _runtime_metadata_path(paths: LocalStoragePaths) -> Path:
    return paths.data_root / ".fitcv-local-runtime.json"


def _write_runtime_metadata(path: Path, *, url: str) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"url": url, "pid": os.getpid()}, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class _WindowsMutex:
    def __init__(self, name: str) -> None:
        self._handle: int | None = None
        self.already_exists = False
        if os.name != "nt":
            return
        import ctypes

        self._handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        self.already_exists = ctypes.windll.kernel32.GetLastError() == 183

    def close(self) -> None:
        if self._handle is None:
            return
        import ctypes

        ctypes.windll.kernel32.CloseHandle(self._handle)
        self._handle = None


def main() -> int:
    prepare_local_environment()
    bundle_root = _bundle_root()
    os.chdir(bundle_root)
    paths = activate_local_storage(bundle_root=bundle_root)
    metadata_path = _runtime_metadata_path(paths)
    mutex = _WindowsMutex("Local\\FitCV.Local")
    if mutex.already_exists:
        try:
            url = str(json.loads(metadata_path.read_text(encoding="utf-8"))["url"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            mutex.close()
            return 1
        webbrowser.open(url)
        mutex.close()
        return 0

    import uvicorn
    from fitcv_cp.main import build_app

    listener = _prebound_socket()
    port = int(listener.getsockname()[1])
    url = f"http://127.0.0.1:{port}/"
    _write_runtime_metadata(metadata_path, url=url)
    application = build_app()
    from fitcv_cp.reconciler import reconcile_abandoned_attempts

    try:
        reconcile_abandoned_attempts(application.state.run_store)
    except Exception as exc:
        logger.warning("FitCV Local startup reconciliation failed: %s", type(exc).__name__)
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port))
    application.state.local_job_executor = get_local_job_executor()
    application.state.local_shutdown_callback = lambda: setattr(server, "should_exit", True)
    webbrowser.open(url)
    try:
        server.run(sockets=[listener])
    finally:
        listener.close()
        metadata_path.unlink(missing_ok=True)
        get_local_job_executor().shutdown()
        mutex.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
