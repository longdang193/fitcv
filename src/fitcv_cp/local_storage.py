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
import hashlib
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

import yaml

from fitcv.config import (
    LOCAL_CONTROLLER_OVERLAY_VERSION,
    validate_local_controller_overlay,
)

BOOTSTRAP_VERSION = 1
MINIMUM_RELOCATION_HEADROOM_BYTES = 512 * 1024 * 1024
BACKUP_FORMAT = "fitcv-backup.v1"
DATA_LAYOUT_VERSION = 1
PENDING_OPERATION_VERSION = 1
MAX_BACKUP_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_BACKUP_EXTRACTED_BYTES = 8 * 1024 * 1024 * 1024
MAX_BACKUP_MEMBER_BYTES = 2 * 1024 * 1024 * 1024


class BootstrapError(RuntimeError):
    """Raised when existing bootstrap state cannot be trusted."""

def default_pending_operation_path() -> Path:
    return Path(os.environ["APPDATA"]) / "FitCV" / "pending-operation.json"

def load_pending_operation(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("FitCV Local pending operation is malformed") from exc
    if not isinstance(payload, dict) or payload.get("version") != PENDING_OPERATION_VERSION:
        raise BootstrapError("FitCV Local pending operation has unsupported schema")
    if payload.get("operation") not in {"relocate", "import"}:
        raise BootstrapError("FitCV Local pending operation type is unsupported")
    return payload

def write_pending_operation(path: Path, payload: dict[str, Any]) -> None:
    operation = str(payload.get("operation") or "")
    if operation not in {"relocate", "import"}:
        raise ValueError("pending operation must be relocate or import")
    persisted = {"version": PENDING_OPERATION_VERSION, **payload, "operation": operation}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(persisted, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@dataclass(frozen=True)
class LocalStoragePaths:
    bootstrap_path: Path
    data_root: Path
    sqlite_path: Path
    candidate_profile_path: Path
    controller_overlay_path: Path
    legacy_routing_overlay_path: Path
    migrated_routing_overlay_path: Path
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


def write_controller_overlay(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_local_controller_overlay(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            yaml.safe_dump(normalized, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return normalized


def _legacy_overlay_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"version", "providers", "model_routing"}
    unsupported = sorted(set(payload) - allowed)
    if unsupported:
        raise ValueError(f"legacy routing overlay contains unsupported keys: {unsupported}")
    providers: dict[str, Any] = {}
    for provider_id, raw_provider in dict(payload.get("providers") or {}).items():
        provider = dict(raw_provider or {})
        providers[str(provider_id)] = {
            key: value
            for key, value in provider.items()
            if key in {"base_url", "auth_mode", "wire_api", "timeout_seconds"}
        }
    return validate_local_controller_overlay(
        {
            "version": LOCAL_CONTROLLER_OVERLAY_VERSION,
            "providers": providers,
            "model_routing": dict(payload.get("model_routing") or {}),
        }
    )


def _retire_legacy_overlay(paths: LocalStoragePaths) -> None:
    if not paths.legacy_routing_overlay_path.exists():
        return
    if paths.migrated_routing_overlay_path.exists():
        raise BootstrapError(
            "FitCV Local has both active and retired legacy routing overlays"
        )
    os.replace(paths.legacy_routing_overlay_path, paths.migrated_routing_overlay_path)


def _activate_controller_overlay(paths: LocalStoragePaths) -> None:
    if paths.controller_overlay_path.exists():
        validate_local_controller_overlay(
            yaml.safe_load(paths.controller_overlay_path.read_text(encoding="utf-8"))
            or {}
        )
        _retire_legacy_overlay(paths)
        return
    if paths.migrated_routing_overlay_path.exists():
        write_controller_overlay(
            paths.controller_overlay_path,
            {"version": LOCAL_CONTROLLER_OVERLAY_VERSION},
        )
        return
    if paths.legacy_routing_overlay_path.exists():
        legacy = yaml.safe_load(
            paths.legacy_routing_overlay_path.read_text(encoding="utf-8")
        ) or {}
        write_controller_overlay(
            paths.controller_overlay_path,
            _legacy_overlay_payload(legacy),
        )
        _retire_legacy_overlay(paths)
        return
    write_controller_overlay(
        paths.controller_overlay_path,
        {"version": LOCAL_CONTROLLER_OVERLAY_VERSION},
    )


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
        controller_overlay_path=data_root / "config" / "local_controller_overlay.yaml",
        legacy_routing_overlay_path=data_root / "config" / "local_routing_overlay.yaml",
        migrated_routing_overlay_path=(
            data_root / "config" / "local_routing_overlay.yaml.migrated.bak"
        ),
        artifacts_path=data_root / "artifacts",
        exports_path=data_root / "exports",
        logs_path=data_root / "logs",
        backups_path=data_root / "backups",
        uploads_path=data_root / "uploads",
        temporary_path=data_root / "tmp",
    )

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _sqlite_schema_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])

def sqlite_schema_version(path: Path) -> int:
    return _sqlite_schema_version(path) if path.exists() else 0

def _check_sqlite_integrity(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if result.lower() != "ok":
        raise ValueError(f"SQLite integrity check failed: {result}")

def inspect_local_storage(paths: LocalStoragePaths) -> dict[str, Any]:
    integrity = "missing"
    schema_version = 0
    if paths.sqlite_path.exists():
        try:
            _check_sqlite_integrity(paths.sqlite_path)
            integrity = "ok"
            schema_version = _sqlite_schema_version(paths.sqlite_path)
        except (OSError, sqlite3.Error, ValueError) as exc:
            integrity = f"error:{type(exc).__name__}"
    backups = list(paths.backups_path.glob("*.fitcv.zip")) if paths.backups_path.exists() else []
    latest_backup = max(backups, key=lambda path: path.stat().st_mtime) if backups else None
    return {
        "data_root": str(paths.data_root),
        "database_path": str(paths.sqlite_path),
        "database_size_bytes": paths.sqlite_path.stat().st_size if paths.sqlite_path.exists() else 0,
        "database_schema_version": schema_version,
        "database_integrity": integrity,
        "last_backup_at": (
            datetime.fromtimestamp(latest_backup.stat().st_mtime, timezone.utc).isoformat()
            if latest_backup is not None
            else None
        ),
    }

def create_backup_archive(
    paths: LocalStoragePaths,
    destination: Path,
    *,
    app_version: str,
    completed_run_ids: set[str] | None = None,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed_ids = {str(run_id) for run_id in completed_run_ids or set()}
    with tempfile.TemporaryDirectory(dir=paths.temporary_path if paths.temporary_path.exists() else None) as raw:
        staging = Path(raw)
        staged_db = staging / "fitcv.sqlite3"
        with closing(sqlite3.connect(paths.sqlite_path)) as source_connection, closing(
            sqlite3.connect(staged_db)
        ) as target_connection:
            source_connection.backup(target_connection)
        included: list[tuple[str, Path]] = [("fitcv.sqlite3", staged_db)]
        for relative, source_path in (
            ("candidate_profile.yaml", paths.candidate_profile_path),
            ("config/local_controller_overlay.yaml", paths.controller_overlay_path),
        ):
            if source_path.exists():
                included.append((relative, source_path))
        for run_id in sorted(completed_ids):
            run_root = paths.artifacts_path / run_id
            if run_root.is_dir():
                included.extend(
                    (
                        f"artifacts/{run_id}/{file.relative_to(run_root).as_posix()}",
                        file,
                    )
                    for file in sorted(run_root.rglob("*"))
                    if file.is_file()
                )
        files = [
            {"path": relative, "size": source_path.stat().st_size, "sha256": _sha256(source_path)}
            for relative, source_path in included
        ]
        manifest = {
            "format": BACKUP_FORMAT,
            "app_version": str(app_version),
            "data_layout_version": DATA_LAYOUT_VERSION,
            "db_schema_version": _sqlite_schema_version(staged_db),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "included_paths": [entry["path"] for entry in files],
            "files": files,
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
                for relative, source_path in included:
                    bundle.write(source_path, relative)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination

def _validated_backup_members(bundle: zipfile.ZipFile) -> tuple[dict[str, Any], dict[str, zipfile.ZipInfo]]:
    members: dict[str, zipfile.ZipInfo] = {}
    total_size = 0
    for info in bundle.infolist():
        normalized = info.filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        key = normalized.casefold()
        if path.is_absolute() or ".." in path.parts or not path.parts or ":" in path.parts[0]:
            raise ValueError(f"Backup contains unsafe path: {info.filename}")
        if key in members:
            raise ValueError(f"Backup contains duplicate entry: {info.filename}")
        if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
            raise ValueError(f"Backup contains symlink: {info.filename}")
        if info.file_size > MAX_BACKUP_MEMBER_BYTES:
            raise ValueError(f"Backup member exceeds size limit: {info.filename}")
        total_size += info.file_size
        if total_size > MAX_BACKUP_EXTRACTED_BYTES:
            raise ValueError("Backup extracted content exceeds size limit")
        members[key] = info
    manifest_info = members.get("manifest.json")
    if manifest_info is None:
        raise ValueError("Backup manifest is missing")
    try:
        manifest = json.loads(bundle.read(manifest_info))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Backup manifest is malformed") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
        raise ValueError("Backup format is unsupported")
    if manifest.get("data_layout_version") != DATA_LAYOUT_VERSION:
        raise ValueError("Backup data layout version is unsupported")
    return manifest, members

def restore_backup_archive(
    archive: Path,
    destination: Path,
    *,
    current_db_schema_version: int | None = None,
) -> LocalStoragePaths:
    if archive.stat().st_size > MAX_BACKUP_ARCHIVE_BYTES:
        raise ValueError("Backup archive exceeds size limit")
    if destination.exists():
        raise ValueError("Restore destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="fitcv-restore-", dir=destination.parent))
    try:
        with zipfile.ZipFile(archive) as bundle:
            manifest, members = _validated_backup_members(bundle)
            schema_version = int(manifest.get("db_schema_version") or 0)
            if current_db_schema_version is not None and schema_version > current_db_schema_version:
                raise ValueError("Backup database schema is newer than this FitCV version")
            declared = manifest.get("files")
            if not isinstance(declared, list):
                raise ValueError("Backup manifest file list is malformed")
            expected_names = {"manifest.json"}
            for entry in declared:
                if not isinstance(entry, dict):
                    raise ValueError("Backup manifest file entry is malformed")
                relative = str(entry.get("path") or "")
                info = members.get(relative.casefold())
                if info is None:
                    raise ValueError(f"Backup member is missing: {relative}")
                payload = bundle.read(info)
                if len(payload) != int(entry.get("size") or -1):
                    raise ValueError(f"Backup size mismatch: {relative}")
                if hashlib.sha256(payload).hexdigest() != str(entry.get("sha256") or ""):
                    raise ValueError(f"Backup checksum mismatch: {relative}")
                target = staging / PurePosixPath(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                expected_names.add(relative.casefold())
            if set(members) != expected_names:
                raise ValueError("Backup contains undeclared files")
        restored_db = staging / "fitcv.sqlite3"
        if not restored_db.exists():
            raise ValueError("Backup database is missing")
        _check_sqlite_integrity(restored_db)
        os.replace(staging, destination)
        return _paths(destination.parent / "bootstrap.json", destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

def relocate_data_root(source: Path, destination: Path) -> Path:
    source = source.resolve()
    if not source.is_dir():
        raise ValueError("FitCV Local source data root does not exist")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("FitCV Local destination must be empty")
    source_size = sum(path.stat().st_size for path in source.rglob("*") if path.is_file())
    resolved = validate_data_root_destination(
        destination,
        source_root=source,
        source_size_bytes=source_size,
    )
    resolved.rmdir()
    staging = Path(tempfile.mkdtemp(prefix="fitcv-relocate-", dir=resolved.parent))
    excluded_names = {
        ".fitcv-local-runtime.json",
        "fitcv.sqlite3",
        "fitcv.sqlite3-wal",
        "fitcv.sqlite3-shm",
    }
    try:
        for item in source.rglob("*"):
            relative = item.relative_to(source)
            if relative.parts and relative.parts[0] == "tmp":
                continue
            if item.name in excluded_names:
                continue
            if item.is_symlink():
                raise ValueError(f"FitCV Local data root contains unsupported symlink: {relative}")
            target = staging / relative
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
        source_db = source / "fitcv.sqlite3"
        target_db = staging / "fitcv.sqlite3"
        with closing(sqlite3.connect(source_db)) as source_connection, closing(
            sqlite3.connect(target_db)
        ) as target_connection:
            source_connection.backup(target_connection)
        _check_sqlite_integrity(target_db)
        os.replace(staging, resolved)
        return resolved
    finally:
        if staging.exists():
            shutil.rmtree(staging)


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
        paths.controller_overlay_path.parent,
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
    _activate_controller_overlay(paths)
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
            "FITCV_LOCAL_CONTROLLER_OVERLAY_PATH": str(paths.controller_overlay_path),
            "FITCV_LOCAL_CANDIDATE_PROFILE_PATH": str(paths.candidate_profile_path),
            "FITCV_LOCAL_ARTIFACTS_PATH": str(paths.artifacts_path),
            "FITCV_LOCAL_EXPORTS_PATH": str(paths.exports_path),
            "FITCV_LOCAL_LOGS_PATH": str(paths.logs_path),
            "FITCV_LOCAL_BACKUPS_PATH": str(paths.backups_path),
            "FITCV_LOCAL_UPLOADS_PATH": str(paths.uploads_path),
            "FITCV_LOCAL_TEMP_PATH": str(paths.temporary_path),
        }
    )
    os.environ.pop("FITCV_LOCAL_ROUTING_OVERLAY_PATH", None)
    return paths