"""
@meta
type: test
scope: unit
domain: settings_store
covers:
  - sqlite-safe local fallback when bq client is absent
excludes:
  - live remote database operations
tags:
  - fast
  - ci-safe
"""

import sqlite3

from fitcv_cp.backend_runtime import BackendRuntime, set_backend_runtime
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


def test_local_settings_path_prefers_active_backend_runtime_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SETTINGS_SQLITE_PATH", str(tmp_path / "env-settings.sqlite3"))
    set_backend_runtime(
        BackendRuntime(
            backend_type="sqlite",
            project="local",
            dataset="fitcv",
            sqlite_path=str(tmp_path / "runtime-settings.sqlite3"),
        )
    )

    try:
        assert ss._local_sqlite_path() == tmp_path / "runtime-settings.sqlite3"
    finally:
        set_backend_runtime(None)


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


def test_bookmark_upsert_delete_and_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    key = ss.upsert_bookmarked_job(
        job_id="job-1",
        title="Data Engineer",
        company="Acme",
        location="Remote",
        url="https://example.com/jobs/1",
        fit_classification="STRETCH",
        source_run_id="run-1",
        source="pipeline_results",
    )

    assert key == "job_id:job-1"
    assert ss.is_job_bookmarked(
        job_id="job-1",
        title="Data Engineer",
        url="https://example.com/jobs/1",
    )

    removed = ss.delete_bookmarked_job(key)
    assert removed is True
    assert not ss.is_job_bookmarked(
        job_id="job-1",
        title="Data Engineer",
        url="https://example.com/jobs/1",
    )


def test_bookmark_upsert_is_idempotent_for_same_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    ss.upsert_bookmarked_job(
        job_id="job-2",
        title="Analyst",
        company="A",
        location="Berlin",
        url="https://example.com/jobs/2",
        fit_classification="STRETCH",
        source_run_id="run-1",
        source="pipeline_results",
    )
    ss.upsert_bookmarked_job(
        job_id="job-2",
        title="Analyst Updated",
        company="A2",
        location="Berlin",
        url="https://example.com/jobs/2",
        fit_classification="GOOD",
        source_run_id="run-2",
        source="pipeline_results",
    )

    items = ss.list_bookmarked_jobs()
    assert len(items) == 1
    assert items[0]["title"] == "Analyst Updated"
    assert items[0]["fit_classification"] == "GOOD"
    assert items[0]["source_run_id"] == "run-2"


def test_bookmark_persists_across_module_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    ss.upsert_bookmarked_job(
        job_id=None,
        title="Product Manager",
        company="Contoso",
        location="Munich",
        url="https://example.com/jobs/3",
        source_run_id="run-3",
        source="pipeline_results",
    )

    items = ss.list_bookmarked_jobs()
    assert len(items) == 1
    assert items[0]["title"] == "Product Manager"
    assert items[0]["snapshot"]["source_run_id"] == "run-3"

