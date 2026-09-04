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

import json
import sqlite3
from pathlib import Path

import pytest

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

def test_local_settings_prunes_retired_runtime_rows(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "settings.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    ss.save_setting("pipeline.final_top_n", 10, updated_by="local")

    retired_keys = [
        "stage_runtime.enrich.sleep_secs",
        "stage_runtime.enrich.batch_size",
        "enrichment_concurrency",
        "rerank_sleep_secs",
    ]
    with sqlite3.connect(sqlite_path) as conn:
        conn.executemany(
            "INSERT INTO pipeline_settings (setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
            [(key, "1", "legacy", "9999-01-01T00:00:00+00:00") for key in retired_keys],
        )
        conn.commit()

    active = ss.load_active_settings()

    assert set(active) == {"pipeline.final_top_n"}
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT setting_key FROM pipeline_settings WHERE setting_key IN (?, ?, ?, ?)",
            retired_keys,
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


def test_configuration_resources_hydrate_legacy_llm_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    ss.load_llm_configuration()
    with sqlite3.connect(tmp_path / "settings.sqlite3") as conn:
        value, revision = conn.execute(
            "SELECT resource_json, revision FROM configuration_resources WHERE resource_name = ?",
            ("llm_configuration",),
        ).fetchone()
        configuration = json.loads(value)
        configuration["tasks"].pop("candidate_profile_base_mapping")
        configuration["tasks"].pop("candidate_profile_derived_claims")
        configuration["tasks"]["enrich_extraction"]["model_ref"] = "kept-model"
        configuration["default_model_ref"] = "kept-model"
        conn.execute(
            "UPDATE configuration_resources SET resource_json = ?, revision = ? WHERE resource_name = ?",
            (json.dumps(configuration), revision, "llm_configuration"),
        )
        conn.commit()

    hydrated = ss.load_llm_configuration()

    assert set(hydrated["tasks"]) == set(ss.LLM_TASK_IDS)
    assert hydrated["tasks"]["enrich_extraction"]["model_ref"] == "kept-model"
    assert hydrated["tasks"]["candidate_profile_derived_claims"] == {
        "model_ref": None,
        "timeout_seconds": 120,
        "temperature": 0.2,
    }
    assert hydrated["revision"] == revision
    monkeypatch.setattr(
        "fitcv_cp.provider_registry.list_eligible_models",
        lambda: [{"model_record_id": "kept-model"}],
    )

    updated = ss.patch_llm_configuration(
        {"tasks": {"enrich_extraction": {"timeout_seconds": 90}}},
        expected_revision=revision,
    )
    assert updated["tasks"]["enrich_extraction"]["timeout_seconds"] == 90
    assert set(updated["tasks"]) == set(ss.LLM_TASK_IDS)


def test_configuration_resources_have_independent_revisions(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))

    llm = ss.load_llm_configuration()
    system = ss.load_system_settings()
    prompts = ss.load_prompt_configurations()

    updated_llm = ss.patch_llm_configuration(
        {"tasks": {"enrich_extraction": {"timeout_seconds": 90}}},
        expected_revision=llm["revision"],
    )

    assert updated_llm["revision"] == llm["revision"] + 1
    assert updated_llm["tasks"]["enrich_extraction"]["timeout_seconds"] == 90
    assert ss.load_system_settings()["revision"] == system["revision"]
    assert ss.load_prompt_configurations()["ranking_ai_score"]["revision"] == prompts["ranking_ai_score"]["revision"]


def test_configuration_resource_rejects_stale_revision_without_writing(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    current = ss.load_system_settings()
    updated = ss.patch_system_settings(
        {"maximum_attempts": 4},
        expected_revision=current["revision"],
    )

    with pytest.raises(ss.SettingsRevisionConflict):
        ss.patch_system_settings(
            {"initial_backoff_seconds": 20},
            expected_revision=current["revision"],
        )

    assert ss.load_system_settings() == updated


def test_configuration_resource_validation_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    current = ss.load_llm_configuration()

    with pytest.raises(ValueError, match="timeout_seconds"):
        ss.patch_llm_configuration(
            {
                "tasks": {
                    "enrich_extraction": {"timeout_seconds": 45},
                    "ranking_ai_score": {"timeout_seconds": 0},
                }
            },
            expected_revision=current["revision"],
        )

    assert ss.load_llm_configuration() == current


def test_llm_configuration_rejects_unavailable_model_reference(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    current = ss.load_llm_configuration()

    with pytest.raises(ValueError, match="unavailable provider models"):
        ss.patch_llm_configuration(
            {"default_model_ref": "missing-model"},
            expected_revision=current["revision"],
        )

    assert ss.load_llm_configuration() == current


def test_prompt_configuration_normalizes_newlines_and_enforces_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    current = ss.load_prompt_configurations()["cv_generation_structured_write"]
    from fitcv.config import load_prompt_task_registry
    from fitcv.prompts.loader import load_prompt_template

    prompt = load_prompt_task_registry()["cv_generation_structured_write"]
    default_text = load_prompt_template(Path(prompt["template_path"]))
    replacement = default_text.replace("You are", "You are precise and", 1)

    updated = ss.patch_prompt_configuration(
        "cv_generation_structured_write",
        replacement_text=replacement.replace("\n", "\r\n"),
        expected_revision=current["revision"],
    )

    assert updated["replacement_text"] == replacement
    with pytest.raises(ValueError, match="4000"):
        ss.patch_prompt_configuration(
            "cv_generation_structured_write",
            replacement_text="x" * 4001,
            expected_revision=updated["revision"],
        )

    with pytest.raises(ValueError, match="current default"):
        ss.patch_prompt_configuration(
            "cv_generation_structured_write",
            replacement_text=default_text,
            expected_revision=updated["revision"],
        )

    with pytest.raises(ValueError, match="canonical prompt variables"):
        ss.patch_prompt_configuration(
            "cv_generation_structured_write",
            replacement_text=replacement + "\n${unknown_variable}",
            expected_revision=updated["revision"],
        )

    reset = ss.patch_prompt_configuration(
        "cv_generation_structured_write",
        replacement_text=None,
        expected_revision=updated["revision"],
    )
    assert reset["replacement_text"] is None
    assert reset["migration_state"] == "clean"
