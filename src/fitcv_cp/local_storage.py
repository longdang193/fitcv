"""@meta
name: local_storage
type: utility
domain: fitcv_local
ownership: infrastructure
responsibility:
  - Own FitCV Local bootstrap and user data-root layout.
  - Activate packaged mutable paths before application construction.
inputs:
  - Windows application data directories
  - Optional existing bootstrap pointer
outputs:
  - Atomic bootstrap file
  - User-owned local data layout and environment paths
lifecycle:
  - status: active
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BOOTSTRAP_VERSION = 1
OVERLAY_VERSION = 1
MINIMUM_RELOCATION_HEADROOM_BYTES = 512 * 1024 * 1024


class BootstrapError(RuntimeError):
    """Raised when existing bootstrap state cannot be trusted."""


@dataclass(frozen=True)
class LocalStoragePaths:
    bootstrap_path: Path
    data_root: Path
    sqlite_path: Path
    candidate_profile_path: Path
    routing_overlay_path: Path
    artifacts_path: Path
    exports_path: Path
    logs_path: Path
    backups_path: Path
    uploads_path: Path
    temporary_path: Path


def is_local_mode() -> bool:
    return str(os.environ.get("FITCV_LOCAL_MODE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_bootstrap(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"FitCV Local bootstrap is malformed: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != BOOTSTRAP_VERSION:
        raise BootstrapError(f"FitCV Local bootstrap has unsupported schema: {path}")
    data_root = str(payload.get("data_root") or "").strip()
    if not data_root or not Path(data_root).is_absolute():
        raise BootstrapError(f"FitCV Local bootstrap has invalid data_root: {path}")
    return payload


def write_bootstrap(path: Path, data_root: Path, app_version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": BOOTSTRAP_VERSION,
        "data_root": str(data_root.resolve()),
        "last_application_version": str(app_version),
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def validate_routing_overlay(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"version", "providers", "model_routing"}
    unsupported = sorted(set(payload) - allowed_keys)
    if unsupported:
        raise ValueError(f"local routing overlay contains unsupported keys: {unsupported}")
    if payload.get("version") != OVERLAY_VERSION:
        raise ValueError("local routing overlay version must be 1")
    model_routing = payload.get("model_routing") or {}
    if not isinstance(model_routing, dict) or set(model_routing) - {"parts"}:
        raise ValueError("local routing overlay model_routing may contain only parts")
    if not isinstance(payload.get("providers") or {}, dict):
        raise ValueError("local routing overlay providers must be a mapping")
    if not isinstance(model_routing.get("parts") or {}, dict):
        raise ValueError("local routing overlay model_routing.parts must be a mapping")
    return payload


def validate_data_root_destination(
    destination: Path, *, source_root: Path | None = None, source_size_bytes: int = 0
) -> Path:
    if not destination.is_absolute():
        raise ValueError("FitCV Local data root must be an absolute path")
    resolved = destination.resolve()
    if str(resolved).startswith("\\\\"):
        raise ValueError("FitCV Local data root cannot use a network path")
    if os.name == "nt":
        import ctypes

        drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{resolved.drive}\\")
        if drive_type in {2, 4}:
            raise ValueError("FitCV Local data root cannot use removable or network storage")
    if source_root is not None and resolved == source_root.resolve():
        raise ValueError("FitCV Local destination must be different from source")
    resolved.mkdir(parents=True, exist_ok=True)
    probe = resolved / ".fitcv-write-test"
    try:
        probe.write_bytes(b"")
    finally:
        probe.unlink(missing_ok=True)
    required = max(0, source_size_bytes) * 2 + MINIMUM_RELOCATION_HEADROOM_BYTES
    if shutil.disk_usage(resolved).free < required:
        raise ValueError("FitCV Local destination has insufficient free space")
    return resolved


def _paths(bootstrap_path: Path, data_root: Path) -> LocalStoragePaths:
    return LocalStoragePaths(
        bootstrap_path=bootstrap_path,
        data_root=data_root,
        sqlite_path=data_root / "fitcv.sqlite3",
        candidate_profile_path=data_root / "candidate_profile.yaml",
        routing_overlay_path=data_root / "config" / "local_routing_overlay.yaml",
        artifacts_path=data_root / "artifacts",
        exports_path=data_root / "exports",
        logs_path=data_root / "logs",
        backups_path=data_root / "backups",
        uploads_path=data_root / "uploads",
        temporary_path=data_root / "tmp",
    )


def activate_local_storage(
    *,
    app_version: str = "0.1.0",
    data_root: Path | None = None,
    bundle_root: Path | None = None,
) -> LocalStoragePaths:
    appdata = Path(os.environ["APPDATA"])
    local_appdata = Path(os.environ["LOCALAPPDATA"])
    bootstrap_path = appdata / "FitCV" / "bootstrap.json"
    bootstrap = load_bootstrap(bootstrap_path)
    selected_root = (
        validate_data_root_destination(data_root)
        if data_root is not None
        else Path(str(bootstrap["data_root"]))
        if bootstrap is not None
        else local_appdata / "FitCV" / "data"
    )
    paths = _paths(bootstrap_path, selected_root.resolve())
    resources_root = (bundle_root or Path.cwd()).resolve()
    for directory in (
        paths.data_root,
        paths.routing_overlay_path.parent,
        paths.artifacts_path,
        paths.exports_path,
        paths.logs_path,
        paths.backups_path,
        paths.uploads_path,
        paths.temporary_path,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if not paths.candidate_profile_path.exists():
        shutil.copyfile(
            resources_root / "data" / "candidate_profile.template.yaml",
            paths.candidate_profile_path,
        )
    if not paths.routing_overlay_path.exists():
        paths.routing_overlay_path.write_text(
            "version: 1\nproviders: {}\nmodel_routing:\n  parts: {}\n",
            encoding="utf-8",
        )
    if (
        bootstrap is None
        or bootstrap.get("last_application_version") != app_version
        or Path(str(bootstrap["data_root"])).resolve() != paths.data_root
    ):
        write_bootstrap(paths.bootstrap_path, paths.data_root, app_version)
    os.environ.update(
        {
            "FITCV_CP_SQLITE_PATH": str(paths.sqlite_path),
            "FITCV_LOCAL_DATA_ROOT": str(paths.data_root),
            "FITCV_LOCAL_ROUTING_OVERLAY_PATH": str(paths.routing_overlay_path),
            "FITCV_LOCAL_CANDIDATE_PROFILE_PATH": str(paths.candidate_profile_path),
            "FITCV_LOCAL_ARTIFACTS_PATH": str(paths.artifacts_path),
            "FITCV_LOCAL_EXPORTS_PATH": str(paths.exports_path),
            "FITCV_LOCAL_LOGS_PATH": str(paths.logs_path),
            "FITCV_LOCAL_BACKUPS_PATH": str(paths.backups_path),
            "FITCV_LOCAL_UPLOADS_PATH": str(paths.uploads_path),
            "FITCV_LOCAL_TEMP_PATH": str(paths.temporary_path),
        }
    )
    return paths
