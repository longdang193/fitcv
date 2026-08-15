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
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

import pytest
from fitcv_cp.backend_runtime import set_backend_runtime
from fitcv_cp import settings_store as ss

from fitcv_cp.settings_store import (
    SettingsRevisionConflict,
    load_active_editable_settings,
    load_active_settings,
    load_llm_configuration,
    mutate_settings_atomically,
    save_setting,
    save_settings_group,
    settings_revision,
)


@pytest.fixture(autouse=True)
def _sqlite_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_backend_runtime(None)
    sqlite_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    yield
    set_backend_runtime(None)


def test_load_llm_configuration_hydrates_missing_declared_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    load_llm_configuration()
    with sqlite3.connect(tmp_path / "settings.sqlite3") as conn:
        value, revision = conn.execute(
            "SELECT resource_json, revision FROM configuration_resources WHERE resource_name = ?",
            ("llm_configuration",),
        ).fetchone()
        configuration = json.loads(value)
        configuration["tasks"].pop("candidate_profile_base_mapping")
        configuration["tasks"].pop("candidate_profile_derived_claims")
        conn.execute(
            "UPDATE configuration_resources SET resource_json = ?, revision = ? WHERE resource_name = ?",
            (json.dumps(configuration), revision + 3, "llm_configuration"),
        )
        conn.commit()

    hydrated = load_llm_configuration()

    assert set(hydrated["tasks"]) == set(ss.LLM_TASK_IDS)
    assert hydrated["revision"] == revision + 3
    assert hydrated["tasks"]["candidate_profile_base_mapping"] == {
        "model_ref": None,
        "timeout_seconds": 120,
        "temperature": 0.2,
    }


def test_load_llm_configuration_preserves_existing_task_values(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    load_llm_configuration()
    with sqlite3.connect(tmp_path / "settings.sqlite3") as conn:
        value, revision = conn.execute(
            "SELECT resource_json, revision FROM configuration_resources WHERE resource_name = ?",
            ("llm_configuration",),
        ).fetchone()
        configuration = json.loads(value)
        configuration["tasks"].pop("candidate_profile_base_mapping")
        configuration["tasks"].pop("candidate_profile_derived_claims")
        configuration["tasks"]["enrich_extraction"] = {
            "model_ref": "existing-model",
            "timeout_seconds": 45,
            "temperature": 0.7,
        }
        conn.execute(
            "UPDATE configuration_resources SET resource_json = ?, revision = ? WHERE resource_name = ?",
            (json.dumps(configuration), revision, "llm_configuration"),
        )
        conn.commit()

    hydrated = load_llm_configuration()

    assert hydrated["revision"] == revision
    assert hydrated["tasks"]["enrich_extraction"] == {
        "model_ref": "existing-model",
        "timeout_seconds": 45,
        "temperature": 0.7,
    }


def test_save_setting_persists_sqlite_row() -> None:
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


def test_load_active_settings_ignores_corrupt_json_row() -> None:
    save_setting("pipeline.final_top_n", 7, updated_by="admin")
    sqlite_path = Path(os.environ["FITCV_CP_SQLITE_PATH"])
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO pipeline_settings (setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
            ("pipeline.final_top_n", "{broken", "admin", "9999-01-01T00:00:00+00:00"),
        )
        conn.commit()

    assert load_active_settings()["pipeline.final_top_n"] == 7


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


def test_mutate_settings_atomically_rolls_back_invalid_effective_state() -> None:
    save_settings_group(
        {
            "pipeline.vector_search_top_n": 100,
            "pipeline.ai_score_top_n": 50,
            "pipeline.final_top_n": 10,
        },
        updated_by="admin",
    )

    with pytest.raises(ValueError, match="final_top_n"):
        mutate_settings_atomically(
            changes={"pipeline.final_top_n": 60},
            updated_by="admin",
        )

    assert load_active_settings()["pipeline.final_top_n"] == 10


def test_mutate_settings_atomically_resets_only_requested_key() -> None:
    save_settings_group(
        {
            "pipeline.vector_search_top_n": 100,
            "pipeline.ai_score_top_n": 40,
            "pipeline.final_top_n": 8,
        },
        updated_by="admin",
    )

    active = mutate_settings_atomically(
        changes={},
        reset_keys=["pipeline.final_top_n"],
        updated_by="admin",
    )

    assert "pipeline.final_top_n" not in active
    assert active["pipeline.ai_score_top_n"] == 40


def test_mutate_settings_atomically_rejects_stale_revision_without_writing() -> None:
    save_setting("pipeline.final_top_n", 10, updated_by="admin")
    current_revision = settings_revision(load_active_settings())
    mutate_settings_atomically(
        changes={"pipeline.final_top_n": 8},
        updated_by="admin",
        expected_revision=current_revision,
    )

    with pytest.raises(SettingsRevisionConflict):
        mutate_settings_atomically(
            changes={"pipeline.final_top_n": 6},
            updated_by="admin",
            expected_revision=current_revision,
        )

    assert load_active_settings()["pipeline.final_top_n"] == 8


def test_mutate_settings_atomically_serializes_relational_updates() -> None:
    save_settings_group(
        {
            "pipeline.vector_search_top_n": 100,
            "pipeline.ai_score_top_n": 50,
            "pipeline.final_top_n": 10,
        },
        updated_by="admin",
    )
    barrier = Barrier(2)

    def mutate(changes: dict[str, int]) -> str:
        barrier.wait()
        try:
            mutate_settings_atomically(changes=changes, updated_by="admin")
        except ValueError:
            return "rejected"
        return "saved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(mutate, [
            {"pipeline.vector_search_top_n": 60},
            {"pipeline.ai_score_top_n": 80},
        ]))

    assert sorted(results) == ["rejected", "saved"]
    active = load_active_settings()
    assert active["pipeline.ai_score_top_n"] <= active["pipeline.vector_search_top_n"]

