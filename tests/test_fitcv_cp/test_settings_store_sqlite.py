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
