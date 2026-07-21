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

import argparse
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

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from fitcv_cp.local_storage import (
    LocalStoragePaths,
    activate_local_storage,
    default_pending_operation_path,
    load_bootstrap,
    load_pending_operation,
    local_storage_paths,
    relocate_data_root,
    reset_local_database,
    restore_backup_archive,
    sqlite_schema_version,
    write_bootstrap,
    write_pending_operation,
)
from fitcv_cp.sqlite_store import ensure_control_plane_database, initialize_control_plane_database
from fitcv_cp.windows_tray import WindowsTray


_Result = TypeVar("_Result")
logger = logging.getLogger(__name__)
LOCAL_APP_VERSION = "0.1.0"


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

def process_pending_storage_operation(*, app_version: str) -> Path | None:
    pending_path = default_pending_operation_path()
    pending = load_pending_operation(pending_path)
    if pending is None:
        return None
    bootstrap_path = Path(os.environ["APPDATA"]) / "FitCV" / "bootstrap.json"
    bootstrap = load_bootstrap(bootstrap_path)
    if bootstrap is None:
        raise RuntimeError("FitCV Local cannot apply pending storage operation without bootstrap")
    previous_root = Path(str(bootstrap["data_root"])).resolve()
    if pending["operation"] == "reset_database":
        paths = local_storage_paths(bootstrap_path, previous_root)
        reset_local_database(paths, app_version=app_version)
        initialize_control_plane_database(paths.sqlite_path, paths.candidate_profile_path)
        pending_path.unlink()
        return None

    destination = Path(str(pending.get("destination") or ""))
    if pending["operation"] == "relocate":
        new_root = relocate_data_root(previous_root, destination)
    else:
        archive = Path(str(pending.get("archive") or ""))
        new_root = restore_backup_archive(
            archive,
            destination,
            current_db_schema_version=sqlite_schema_version(previous_root / "fitcv.sqlite3"),
        ).data_root
    write_bootstrap(bootstrap_path, new_root, app_version)
    pending_path.unlink()
    return previous_root


def _parse_local_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fitcv-local")
    parser.add_argument("--reset-database", action="store_true")
    parser.add_argument("--change-log", action="store_true")
    args, _unknown = parser.parse_known_args(argv)
    return args


def _bundle_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(str(frozen_root)).resolve() if frozen_root else Path.cwd().resolve()

def _open_browser(url: str) -> None:
    if str(os.environ.get("FITCV_NO_BROWSER") or "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        webbrowser.open(url)


def _prebound_socket() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(socket.SOMAXCONN)
    return listener

def build_recovery_app(error: Exception) -> FastAPI:
    application = FastAPI(title="FitCV Local Recovery")
    templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))

    async def recovery(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="local_recovery.html",
            context={"error_type": type(error).__name__},
        )

    application.add_api_route("/", recovery, methods=["GET"])
    application.add_api_route("/local/recovery", recovery, methods=["GET"])
    return application

def _run_recovery(error: Exception) -> int:
    import uvicorn

    listener = _prebound_socket()
    port = int(listener.getsockname()[1])
    server = uvicorn.Server(
        uvicorn.Config(build_recovery_app(error), host="127.0.0.1", port=port)
    )
    _open_browser(f"http://127.0.0.1:{port}/local/recovery")
    try:
        server.run(sockets=[listener])
    finally:
        listener.close()
    return 1


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


def main(argv: list[str] | None = None) -> int:
    prepare_local_environment()
    args = _parse_local_args(sys.argv[1:] if argv is None else argv)
    if args.reset_database:
        write_pending_operation(
            default_pending_operation_path(),
            {"operation": "reset_database"},
        )
    bundle_root = _bundle_root()
    os.chdir(bundle_root)
    previous_root: Path | None = None
    try:
        previous_root = process_pending_storage_operation(app_version=LOCAL_APP_VERSION)
        paths = activate_local_storage(app_version=LOCAL_APP_VERSION, bundle_root=bundle_root)
        ensure_control_plane_database(paths.sqlite_path, paths.candidate_profile_path)
    except Exception as exc:
        if previous_root is not None:
            write_bootstrap(
                Path(os.environ["APPDATA"]) / "FitCV" / "bootstrap.json",
                previous_root,
                LOCAL_APP_VERSION,
            )
        return _run_recovery(exc)
    metadata_path = _runtime_metadata_path(paths)
    launch_path = "/local/system#change-log" if args.change_log else "/"
    mutex = _WindowsMutex("Local\\FitCV.Local")
    if mutex.already_exists:
        try:
            url = str(json.loads(metadata_path.read_text(encoding="utf-8"))["url"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            mutex.close()
            return 1
        _open_browser(url.rstrip("/") + launch_path)
        mutex.close()
        return 0

    import uvicorn
    from fitcv_cp.main import build_app

    listener = _prebound_socket()
    port = int(listener.getsockname()[1])
    url = f"http://127.0.0.1:{port}/"
    _write_runtime_metadata(metadata_path, url=url)
    try:
        application = build_app()
    except Exception as exc:
        listener.close()
        mutex.close()
        if previous_root is not None:
            write_bootstrap(paths.bootstrap_path, previous_root, LOCAL_APP_VERSION)
        return _run_recovery(exc)
    from fitcv_cp.reconciler import reconcile_abandoned_attempts

    try:
        reconcile_abandoned_attempts(application.state.run_store)
    except Exception as exc:
        logger.warning("FitCV Local startup reconciliation failed: %s", type(exc).__name__)
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port))
    application.state.local_job_executor = get_local_job_executor()
    application.state.app_version = LOCAL_APP_VERSION
    application.state.build_id = str(os.environ.get("FITCV_BUILD_ID") or "development")
    shutdown_lock = threading.Lock()

    def request_shutdown() -> None:
        with shutdown_lock:
            if not server.should_exit:
                server.should_exit = True

    application.state.local_shutdown_callback = request_shutdown
    tray = WindowsTray(
        url=url,
        on_open=lambda: _open_browser(url.rstrip("/") + launch_path),
        on_shutdown=request_shutdown,
    )
    try:
        tray.start()
    except Exception:
        logger.warning("FitCV tray startup failed; continuing without tray", exc_info=True)
    _open_browser(url.rstrip("/") + launch_path)
    try:
        server.run(sockets=[listener])
    finally:
        tray.stop()
        listener.close()
        metadata_path.unlink(missing_ok=True)
        get_local_job_executor().shutdown()
        mutex.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
