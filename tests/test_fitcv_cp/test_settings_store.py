"""
@meta
type: test
scope: unit
domain: pipeline_config
covers:
  - control-plane settings store behavior
excludes:
  - remote database access
tags:
  - fast
  - ci-safe
"""

import json
import os
import sqlite3
from pathlib import Path

import pytest
from fitcv_cp.backend_runtime import set_backend_runtime

from fitcv_cp.settings_store import (
    load_active_editable_settings,
    load_active_settings,
    save_setting,
    save_settings_group,
)


@pytest.fixture(autouse=True)
def _sqlite_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_backend_runtime(None)
    sqlite_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    yield
    set_backend_runtime(None)


def test_save_setting_persists_sqlite_row() -> None:
    """@proves settings_system.sqlite-backed-pipeline-settings-store"""
    save_setting("pipeline.final_top_n", 5, updated_by="admin")

    result = load_active_settings()

    assert result["pipeline.final_top_n"] == 5


def test_load_active_settings_returns_latest_per_key() -> None:
    """@proves settings_system.sqlite-backed-pipeline-settings-store"""
    save_setting("pipeline.final_top_n", 10, updated_by="admin")
    save_setting("pipeline.final_top_n", 5, updated_by="admin")

    result = load_active_settings()

    assert result["pipeline.final_top_n"] == 5
    assert isinstance(result["pipeline.final_top_n"], int)


def test_load_active_settings_empty_table() -> None:
    assert load_active_settings() == {}


def test_load_active_editable_settings_excludes_metadata_only_keys() -> None:
    save_settings_group(
        {
            "cv_preset": "europass",
            "cv_analysis.semantic_alignment.model": "text-embedding-005",
            "cv_generation_model": "cx/gpt-5.5",
        },
        updated_by="admin",
    )

    result = load_active_editable_settings()

    assert result == {
        "cv_generation_model": "cx/gpt-5.5",
    }


def test_load_active_settings_falls_back_to_older_valid_row_when_latest_is_invalid() -> None:
    save_setting("pipeline.final_top_n", 7, updated_by="admin")
    with pytest.raises(ValueError):
        save_setting("pipeline.final_top_n", "not-an-int", updated_by="admin")

    result = load_active_settings()

    assert result["pipeline.final_top_n"] == 7

def test_load_active_settings_prunes_stale_invalid_rows() -> None:
    save_setting("pipeline.final_top_n", 7, updated_by="admin")

    sqlite_path = Path(os.environ["FITCV_CP_SQLITE_PATH"])
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO pipeline_settings (setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
            ("pipeline.final_top_n", json.dumps("not-an-int"), "admin", "9999-01-01T00:00:00+00:00"),
        )
        conn.commit()

    result = load_active_settings()

    assert result["pipeline.final_top_n"] == 7
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT setting_value_json FROM pipeline_settings WHERE setting_key = ? ORDER BY updated_at DESC, rowid DESC",
            ("pipeline.final_top_n",),
        ).fetchall()
    assert [row[0] for row in rows] == [json.dumps(7)]

