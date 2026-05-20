"""
@meta
type: test
scope: unit
domain: settings_store
covers:
  - sqlite-safe local fallback when bq client is absent
excludes:
  - live bigquery operations
tags:
  - fast
  - ci-safe
"""

import sqlite3

from fitcv_cp import settings_store as ss


def test_local_settings_fallback_round_trip_without_bq(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    ss.save_setting(
        "pipeline.final_top_n",
        20,
        updated_by="local",
        bq=None,
        project="local",
        dataset="local",
    )

    active = ss.load_active_settings(bq=None, project="local", dataset="local")

    assert active["pipeline.final_top_n"] == 20


def test_local_settings_group_save_without_bq(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    ss.save_settings_group(
        {"pipeline.vector_search_top_n": 25, "pipeline.final_top_n": 10},
        updated_by="local",
        bq=None,
        project="local",
        dataset="local",
    )

    active = ss.load_active_settings(bq=None, project="local", dataset="local")

    assert active["pipeline.vector_search_top_n"] == 25
    assert active["pipeline.final_top_n"] == 10


def test_local_settings_persist_across_module_reload(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))

    ss.save_setting(
        "cv.agentic_late_stage.enabled",
        True,
        updated_by="local",
        bq=None,
        project="local",
        dataset="local",
    )

    active = ss.load_active_settings(bq=None, project="local", dataset="local")

    assert active["cv.agentic_late_stage.enabled"] is True


def test_local_settings_load_recovers_from_disk_io_error(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    sqlite_path.write_bytes(b"not-a-sqlite-db")
    (tmp_path / "settings.sqlite3-wal").write_bytes(b"wal")
    (tmp_path / "settings.sqlite3-shm").write_bytes(b"shm")

    active = ss.load_active_settings(bq=None, project="local", dataset="local")

    assert active == {}
    backup_dirs = list(tmp_path.glob("settings.corrupt.*"))
    assert backup_dirs
    moved_names = {p.name for p in backup_dirs[0].iterdir()}
    assert "settings.sqlite3" in moved_names
    assert "settings.sqlite3-wal" in moved_names
    assert "settings.sqlite3-shm" in moved_names


def test_local_settings_save_recovers_after_first_disk_io_error(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    sqlite_path.write_text("broken", encoding="utf-8")

    real_connect = ss.sqlite3.connect
    state = {"calls": 0}

    def flaky_connect(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(ss.sqlite3, "connect", flaky_connect)

    ss.save_setting(
        "pipeline.final_top_n",
        15,
        updated_by="local",
        bq=None,
        project="local",
        dataset="local",
    )

    active = ss.load_active_settings(bq=None, project="local", dataset="local")
    assert active["pipeline.final_top_n"] == 15
