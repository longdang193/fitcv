"""
@meta
type: test
scope: unit
domain: settings_store
covers:
  - sqlite-safe local fallback when client client is absent
excludes:
  - live remote database operations
tags:
  - fast
  - ci-safe
"""

import sqlite3
from pathlib import Path

from fitcv_cp.backend_runtime import BackendRuntime, set_backend_runtime
from fitcv_cp import settings_store as ss


def setup_function(_function) -> None:
    set_backend_runtime(None)


def teardown_function(_function) -> None:
    set_backend_runtime(None)


def test_local_settings_fallback_round_trip_without_bq(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    ss.save_setting(
        "pipeline.final_top_n",
        20,
        updated_by="local",
    )

    active = ss.load_active_settings()

    assert active["pipeline.final_top_n"] == 20


def test_local_settings_group_save_without_bq(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    ss.save_settings_group(
        {
            "pipeline.vector_search_top_n": 25,
            "pipeline.ai_score_top_n": 20,
            "pipeline.final_top_n": 10,
        },
        updated_by="local",
    )

    active = ss.load_active_settings()

    assert active["pipeline.vector_search_top_n"] == 25
    assert active["pipeline.ai_score_top_n"] == 20
    assert active["pipeline.final_top_n"] == 10


def test_local_settings_prunes_removed_agentic_late_stage_row(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    ss.save_setting("pipeline.final_top_n", 10, updated_by="local")

    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO pipeline_settings (setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
            ("cv.agentic_late_stage.enabled", "true", "legacy", "9999-01-01T00:00:00+00:00"),
        )
        conn.commit()

    active = ss.load_active_settings()

    assert "cv.agentic_late_stage.enabled" not in active
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT setting_key FROM pipeline_settings WHERE setting_key = ?",
            ("cv.agentic_late_stage.enabled",),
        ).fetchall()
    assert rows == []


def test_local_settings_load_recovers_from_disk_io_error(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    sqlite_path.write_bytes(b"not-a-sqlite-db")
    (tmp_path / "settings.sqlite3-wal").write_bytes(b"wal")
    (tmp_path / "settings.sqlite3-shm").write_bytes(b"shm")

    active = ss.load_active_settings()

    assert active == {}
    backup_dirs = list(tmp_path.glob("settings.corrupt.*"))
    assert backup_dirs
    moved_names = {p.name for p in backup_dirs[0].iterdir()}
    assert "settings.sqlite3" in moved_names
    assert "settings.sqlite3-wal" in moved_names
    assert "settings.sqlite3-shm" in moved_names


def test_local_settings_path_prefers_active_backend_runtime_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "env-settings.sqlite3"))
    set_backend_runtime(
        BackendRuntime(
            backend_type="sqlite",
            sqlite_path=str(tmp_path / "runtime-settings.sqlite3"),
        )
    )

    try:
        assert ss._local_sqlite_path() == tmp_path / "runtime-settings.sqlite3"
    finally:
        set_backend_runtime(None)


def test_local_settings_path_ignores_retired_settings_env_and_uses_config_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config" / "runtime" / "control_plane.yaml"
    config_path.parent.mkdir(parents=True)
    canonical_text = (
        Path(__file__).parents[2] / "config" / "runtime" / "control_plane.yaml"
    ).read_text(encoding="utf-8")
    assert "path: data/fitcv_cp.sqlite3" in canonical_text
    config_path.write_text(
        canonical_text.replace(
            "path: data/fitcv_cp.sqlite3",
            f"path: {(tmp_path / 'from-config.sqlite3').as_posix()}",
        ),
        encoding="utf-8",
    )
    retired_env_key = "FITCV_CP_" + "SETTINGS_SQLITE_PATH"
    monkeypatch.setenv(retired_env_key, str(tmp_path / "retired.sqlite3"))
    monkeypatch.delenv("FITCV_CP_SQLITE_PATH", raising=False)

    assert ss._local_sqlite_path() == tmp_path / "from-config.sqlite3"


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
    )

    active = ss.load_active_settings()
    assert active["pipeline.final_top_n"] == 15
