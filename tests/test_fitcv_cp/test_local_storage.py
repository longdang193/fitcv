"""
@meta
type: test
scope: unit
domain: fitcv_local_storage
covers:
  - atomic bootstrap persistence
  - packaged data-root layout
  - narrow routing overlay validation
excludes:
  - Windows shell folder selection
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
import os
import sqlite3
import zipfile
from pathlib import Path

import pytest

from fitcv.config import validate_local_controller_overlay
from fitcv_cp.local_storage import (
    BootstrapError,
    activate_local_storage,
    create_backup_archive,
    load_pending_operation,
    reset_local_database,
    relocate_data_root,
    restore_backup_archive,
    load_bootstrap,
    validate_data_root_destination,
    write_pending_operation,
    write_bootstrap,
)


_LOCAL_ENV_KEYS = (
    "FITCV_CP_SQLITE_PATH",
    "FITCV_LOCAL_DATA_ROOT",
    "FITCV_LOCAL_CONTROLLER_OVERLAY_PATH",
    "FITCV_LOCAL_CANDIDATE_PROFILE_PATH",
    "FITCV_LOCAL_ARTIFACTS_PATH",
    "FITCV_LOCAL_EXPORTS_PATH",
    "FITCV_LOCAL_LOGS_PATH",
    "FITCV_LOCAL_BACKUPS_PATH",
    "FITCV_LOCAL_UPLOADS_PATH",
    "FITCV_LOCAL_TEMP_PATH",
)


@pytest.fixture(autouse=True)
def _restore_local_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _LOCAL_ENV_KEYS:
        monkeypatch.setenv(key, os.environ.get(key, ""))


def test_activate_local_storage_creates_expected_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    paths = activate_local_storage(app_version="1.2.3")

    assert paths.data_root == tmp_path / "local" / "FitCV" / "data"
    assert paths.sqlite_path == paths.data_root / "fitcv.sqlite3"
    assert paths.controller_overlay_path == paths.data_root / "config" / "local_controller_overlay.yaml"
    assert paths.candidate_profile_path.exists()
    assert paths.controller_overlay_path.read_text(encoding="utf-8") == "version: 1\n"
    assert json.loads(paths.bootstrap_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "data_root": str(paths.data_root),
        "last_application_version": "1.2.3",
    }
    assert os.environ["FITCV_CP_SQLITE_PATH"] == str(paths.sqlite_path)


def test_write_bootstrap_replace_failure_preserves_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap_path = tmp_path / "bootstrap.json"
    write_bootstrap(bootstrap_path, tmp_path / "old", "1")
    previous = bootstrap_path.read_bytes()
    monkeypatch.setattr("fitcv_cp.local_storage.os.replace", lambda *_: (_ for _ in ()).throw(OSError("boom")))

    with pytest.raises(OSError, match="boom"):
        write_bootstrap(bootstrap_path, tmp_path / "new", "2")

    assert bootstrap_path.read_bytes() == previous


def test_load_bootstrap_rejects_malformed_json(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.json"
    bootstrap_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(BootstrapError, match="malformed"):
        load_bootstrap(bootstrap_path)

def test_pending_operation_accepts_database_reset(tmp_path: Path) -> None:
    path = tmp_path / "pending-operation.json"

    write_pending_operation(path, {"operation": "reset_database"})

    assert load_pending_operation(path) == {"version": 1, "operation": "reset_database"}


def test_validate_controller_overlay_rejects_unsupported_keys() -> None:
    with pytest.raises(ValueError, match="unsupported keys"):
        validate_local_controller_overlay({"version": 1, "data_backend": {}})


def test_validate_data_root_destination_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        validate_data_root_destination(Path("relative"))


def test_validate_data_root_destination_rejects_source_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="different"):
        validate_data_root_destination(tmp_path, source_root=tmp_path)


def test_reinstall_reuses_root_without_overwriting_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    first = activate_local_storage(app_version="1")
    first.candidate_profile_path.write_text("user-owned\n", encoding="utf-8")

    second = activate_local_storage(app_version="2")

    assert second.data_root == first.data_root
    assert second.candidate_profile_path.read_text(encoding="utf-8") == "user-owned\n"


def test_explicit_data_root_updates_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    chosen = tmp_path / "chosen"

    paths = activate_local_storage(app_version="1", data_root=chosen)

    assert paths.data_root == chosen
    assert load_bootstrap(paths.bootstrap_path)["data_root"] == str(chosen)


def test_activation_does_not_write_under_bundle_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_root = tmp_path / "bundle"
    (bundle_root / "data").mkdir(parents=True)
    (bundle_root / "data" / "candidate_profile.template.yaml").write_text(
        "name: Candidate\n", encoding="utf-8"
    )
    marker = bundle_root / "read-only-marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    before = {path.relative_to(bundle_root): path.read_bytes() for path in bundle_root.rglob("*") if path.is_file()}
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    activate_local_storage(app_version="1", bundle_root=bundle_root)

    after = {path.relative_to(bundle_root): path.read_bytes() for path in bundle_root.rglob("*") if path.is_file()}
    assert after == before

def test_backup_archive_restores_sqlite_and_user_configuration(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    paths = __import__("fitcv_cp.local_storage", fromlist=["_paths"])._paths(
        tmp_path / "bootstrap.json", source
    )
    paths.controller_overlay_path.parent.mkdir(parents=True)
    paths.candidate_profile_path.write_text("name: User\n", encoding="utf-8")
    paths.controller_overlay_path.write_text("version: 1\n", encoding="utf-8")
    paths.logs_path.mkdir()
    (paths.logs_path / "secret.log").write_text("api-key-canary", encoding="utf-8")
    with sqlite3.connect(paths.sqlite_path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('kept')")
    archive = create_backup_archive(paths, tmp_path / "backup.fitcv.zip", app_version="1.2.3")

    restored = restore_backup_archive(archive, tmp_path / "restored")

    with sqlite3.connect(restored.sqlite_path) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("kept",)
    assert restored.candidate_profile_path.read_text(encoding="utf-8") == "name: User\n"
    with zipfile.ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        names = set(bundle.namelist())
    assert manifest["format"] == "fitcv-backup.v1"
    assert manifest["app_version"] == "1.2.3"
    assert "logs/secret.log" not in names
    assert all(not name.endswith(("-wal", "-shm")) for name in names)

def test_reset_local_database_archives_then_retires_matched_sqlite_set(tmp_path: Path) -> None:
    paths = __import__("fitcv_cp.local_storage", fromlist=["_paths"])._paths(
        tmp_path / "bootstrap.json", tmp_path / "data"
    )
    paths.data_root.mkdir()
    paths.backups_path.mkdir()
    paths.temporary_path.mkdir()
    paths.candidate_profile_path.write_text("name: User\n", encoding="utf-8")
    connection = sqlite3.connect(paths.sqlite_path)
    connection.execute("CREATE TABLE sample (value TEXT)")
    connection.execute("INSERT INTO sample VALUES ('kept')")
    connection.commit()
    connection.close()
    Path(f"{paths.sqlite_path}-wal").write_bytes(b"wal-evidence")
    Path(f"{paths.sqlite_path}-shm").write_bytes(b"shm-evidence")

    evidence = reset_local_database(paths, app_version="1.2.3")

    assert evidence.archive_path.exists()
    assert not paths.sqlite_path.exists()
    assert not Path(f"{paths.sqlite_path}-wal").exists()
    assert not Path(f"{paths.sqlite_path}-shm").exists()
    assert (evidence.retired_directory / "fitcv.sqlite3").exists()
    assert (evidence.retired_directory / "fitcv.sqlite3-wal").read_bytes() == b"wal-evidence"
    assert (evidence.retired_directory / "fitcv.sqlite3-shm").read_bytes() == b"shm-evidence"

def test_reset_local_database_stops_before_retirement_when_backup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = __import__("fitcv_cp.local_storage", fromlist=["_paths"])._paths(
        tmp_path / "bootstrap.json", tmp_path / "data"
    )
    paths.data_root.mkdir()
    paths.backups_path.mkdir()
    paths.temporary_path.mkdir()
    connection = sqlite3.connect(paths.sqlite_path)
    connection.execute("CREATE TABLE sample (value TEXT)")
    connection.commit()
    connection.close()
    monkeypatch.setattr(
        "fitcv_cp.local_storage.create_backup_archive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("backup failed")),
    )

    with pytest.raises(OSError, match="backup failed"):
        reset_local_database(paths, app_version="1.2.3")

    assert paths.sqlite_path.exists()

def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.txt", "bad")

    with pytest.raises(ValueError, match="unsafe path"):
        restore_backup_archive(archive, tmp_path / "restore")

def test_restore_rejects_checksum_drift(tmp_path: Path) -> None:
    archive = tmp_path / "bad-checksum.zip"
    manifest = {
        "format": "fitcv-backup.v1",
        "data_layout_version": 1,
        "db_schema_version": 0,
        "files": [{"path": "candidate_profile.yaml", "size": 4, "sha256": "0" * 64}],
    }
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest))
        bundle.writestr("candidate_profile.yaml", "user")

    with pytest.raises(ValueError, match="checksum"):
        restore_backup_archive(archive, tmp_path / "restore")

def test_pending_operation_is_atomic_and_versioned(tmp_path: Path) -> None:
    path = tmp_path / "pending.json"

    write_pending_operation(path, {"operation": "relocate", "destination": str(tmp_path / "new")})

    assert load_pending_operation(path) == {
        "version": 1,
        "operation": "relocate",
        "destination": str(tmp_path / "new"),
    }

def test_cold_relocation_preserves_source_and_uses_sqlite_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "config").mkdir()
    (source / "candidate_profile.yaml").write_text("name: User\n", encoding="utf-8")
    (source / "config" / "local_routing_overlay.yaml").write_text("version: 1\n", encoding="utf-8")
    with sqlite3.connect(source / "fitcv.sqlite3") as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('kept')")

    destination = relocate_data_root(source, tmp_path / "destination")

    assert source.exists()
    assert (source / "fitcv.sqlite3").exists()
    with sqlite3.connect(destination / "fitcv.sqlite3") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("kept",)
