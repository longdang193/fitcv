import concurrent.futures
import datetime
import hashlib
import json
import os
import sqlite3
import uuid
from pathlib import Path

import pytest

from fitcv.preference_policy import (
    build_policy_snapshot_identity,
    build_preference_optimization_run_id,
    build_training_run_identity,
)
from fitcv_cp import sqlite_store
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus


@pytest.fixture(autouse=True)
def _sqlite_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv_cp.sqlite3"))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)


def _make_run(run_id: str = "run-1") -> PipelineRun:
    return PipelineRun(
        run_id=run_id,
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def test_control_plane_schema_initializes_normalized_tables_and_foreign_keys() -> None:
    with sqlite3.connect(":memory:") as conn:
        sqlite_store._configure_sqlite_connection(conn)
        sqlite_store._ensure_control_plane_schema(conn)

        tables = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {
            "api_provider_connections",
            "api_provider_models",
            "api_provider_state",
            "candidate_profiles",
            "candidate_profile_revisions",
            "configuration_resources",
            "custom_api_providers",
            "integration_migrations",
            "pipeline_runs",
            "run_inputs",
            "run_stage_executions",
            "run_jobs",
            "run_job_stage_results",
            "cv_versions",
            "cv_evaluations",
            "cv_review_events",
            "bookmarks",
            "run_job_interest",
            "idempotent_actions",
            "synonym_policy_type_revisions",
            "synonym_policy_state",
            "synonym_policy_drafts",
            "synonym_policy_bundle_revisions",
            "synonym_suggestions",
            "synonym_suggestion_sources",
            "synonym_processing_runs",
        } <= tables
        assert sqlite_store.CONTROL_PLANE_SCHEMA_VERSION == 4
        assert conn.execute("PRAGMA user_version").fetchone()[0] == sqlite_store.CONTROL_PLANE_SCHEMA_VERSION
        assert any(row[2] == "pipeline_runs" and row[6] == "CASCADE" for row in conn.execute("PRAGMA foreign_key_list(run_inputs)"))
        assert any(row[2] == "candidate_profiles" and row[6] == "RESTRICT" for row in conn.execute("PRAGMA foreign_key_list(candidate_profile_revisions)"))
        assert any(row[2] == "run_jobs" and row[6] == "CASCADE" for row in conn.execute("PRAGMA foreign_key_list(bookmarks)"))
        assert any(row[2] == "pipeline_runs" and row[6] == "CASCADE" for row in conn.execute("PRAGMA foreign_key_list(bookmarks)"))
        assert any(row[2] == "synonym_suggestions" and row[6] == "CASCADE" for row in conn.execute("PRAGMA foreign_key_list(synonym_suggestion_sources)"))
        assert any(row[2] == "pipeline_runs" and row[6] == "CASCADE" for row in conn.execute("PRAGMA foreign_key_list(synonym_suggestion_sources)"))

        profile_columns = {row[1]: row for row in conn.execute("PRAGMA table_info(candidate_profiles)")}
        assert profile_columns["profile_name"][3] == 0
        assert "profile_json" not in profile_columns
        assert profile_columns["revision"][3] == 1

        bookmark_columns = {row[1]: row for row in conn.execute("PRAGMA table_info(bookmarks)")}
        assert bookmark_columns["run_id"][3] == 1
        assert bookmark_columns["run_job_id"][3] == 1
        assert "display_snapshot_json" not in bookmark_columns

        run_input_columns = {row[1] for row in conn.execute("PRAGMA table_info(run_inputs)")}
        assert {
            "candidate_profile_revision_id",
            "synonym_policy_bundle_revision_id",
            "synonym_policy_bundle_checksum",
            "synonym_policy_bundle_snapshot_json",
        } <= run_input_columns

        idempotency_columns = {row[1] for row in conn.execute("PRAGMA table_info(idempotent_actions)")}
        assert {
            "response_blob",
            "response_media_type",
            "response_filename",
            "response_checksum",
        } <= idempotency_columns

        for table in ("pipeline_runs", "bookmarks", "synonym_suggestions", "synonym_processing_runs"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_control_plane_schema_upgrades_version_3_without_losing_settings() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute(
            """
            CREATE TABLE pipeline_settings (
                setting_key TEXT NOT NULL,
                setting_value_json TEXT NOT NULL,
                updated_by TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO pipeline_settings VALUES (?, ?, ?, ?)",
            ("pipeline.final_top_n", "7", "test", "2026-07-22T00:00:00+00:00"),
        )
        conn.execute("PRAGMA user_version = 3")
        conn.commit()

        sqlite_store._ensure_control_plane_schema(conn)
        sqlite_store._ensure_control_plane_schema(conn)

        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
        assert conn.execute(
            "SELECT setting_value_json FROM pipeline_settings WHERE setting_key = ?",
            ("pipeline.final_top_n",),
        ).fetchone()[0] == "7"
        assert conn.execute(
            "SELECT COUNT(*) FROM configuration_resources"
        ).fetchone()[0] == 6


def test_provider_schema_has_no_secret_bearing_columns() -> None:
    with sqlite3.connect(":memory:") as conn:
        sqlite_store._ensure_control_plane_schema(conn)

        columns = {
            table: {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
            for table in (
                "custom_api_providers",
                "api_provider_connections",
                "api_provider_models",
            )
        }

        assert "credential_account" in columns["api_provider_connections"]
        assert not {
            "api_key",
            "api_key_value",
            "authorization",
            "authorization_header",
            "secret",
        } & set().union(*columns.values())


def test_provider_persistence_enforces_revisions_uniqueness_and_secret_boundary(tmp_path: Path) -> None:
    database_path = tmp_path / "fitcv.sqlite3"
    provider = sqlite_store.create_custom_api_provider(
        "provider-1",
        display_name="Local Gateway",
        compatibility="openai",
        database_path=database_path,
    )
    assert provider["revision"] == 1

    provider = sqlite_store.update_custom_api_provider(
        "provider-1",
        display_name="Local Gateway Updated",
        compatibility="openai",
        expected_revision=1,
        database_path=database_path,
    )
    assert provider["revision"] == 2
    with pytest.raises(sqlite_store.ProviderPersistenceRevisionConflict):
        sqlite_store.update_custom_api_provider(
            "provider-1",
            display_name="Stale",
            compatibility="anthropic",
            expected_revision=1,
            database_path=database_path,
        )

    connection = sqlite_store.save_api_provider_connection(
        "provider-1",
        base_url="https://provider.example/v1",
        api_type="responses",
        verification_status="verified",
        verified_at="2026-07-22T12:00:00+00:00",
        credential_account="fitcv/provider/provider-1",
        expected_revision=provider["provider_revision"],
        database_path=database_path,
    )
    assert connection["connection_revision"] == 1
    assert connection["provider_revision"] == 3

    model = sqlite_store.create_api_provider_model(
        "model-record-1",
        provider_id="provider-1",
        model_id="model-alpha",
        validated_connection_revision=1,
        last_tested_at="2026-07-22T12:01:00+00:00",
        expected_revision=connection["provider_revision"],
        database_path=database_path,
    )
    assert model["validation_status"] == "validated"
    with pytest.raises(sqlite3.IntegrityError):
        sqlite_store.create_api_provider_model(
            "model-record-2",
            provider_id="provider-1",
            model_id="model-alpha",
            validated_connection_revision=1,
            last_tested_at="2026-07-22T12:02:00+00:00",
            expected_revision=model["provider_revision"],
            database_path=database_path,
        )

    sqlite_bytes = database_path.read_bytes()
    assert b"credential-secret-canary" not in sqlite_bytes
    assert sqlite_store.list_custom_api_providers(database_path=database_path) == [
        {**provider, "provider_revision": model["provider_revision"]}
    ]
    assert sqlite_store.list_api_provider_models(
        "provider-1", database_path=database_path
    ) == [model]


def test_integration_migration_record_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "fitcv.sqlite3"

    assert sqlite_store.integration_migration_applied(
        "provider-cutover-v1", database_path=database_path
    ) is False
    first = sqlite_store.record_integration_migration(
        "provider-cutover-v1",
        details={"migrated": 1},
        database_path=database_path,
    )
    second = sqlite_store.record_integration_migration(
        "provider-cutover-v1",
        details={"migrated": 99},
        database_path=database_path,
    )

    assert second == first
    assert sqlite_store.integration_migration_applied(
        "provider-cutover-v1", database_path=database_path
    ) is True


def test_control_plane_schema_allows_duplicate_profile_names_and_enforces_one_active_default() -> None:
    with sqlite3.connect(":memory:") as conn:
        sqlite_store._configure_sqlite_connection(conn)
        sqlite_store._ensure_control_plane_schema(conn)
        row = (
            "candidate-one", "Candidate", "candidate.yaml", "application/yaml", 1, "sha",
            "succeeded", "active", None, None, 1, 1, "seed-v1", "now", "now", None, 1,
        )
        conn.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_profile_id, profile_name, original_filename, media_type, byte_length,
                input_checksum, creation_status, lifecycle, failure_code, failure_message,
                is_default, sort_order, seed_manifest_revision, created_at, updated_at,
                archived_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        duplicate_name = list(row)
        duplicate_name[0] = "candidate-two"
        duplicate_name[5] = "sha2"
        duplicate_name[10] = 0
        conn.execute(
            "INSERT INTO candidate_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            duplicate_name,
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE candidate_profiles SET is_default = 1 WHERE candidate_profile_id = 'candidate-two'")


def test_control_plane_schema_enforces_profile_and_synonym_states() -> None:
    with sqlite3.connect(":memory:") as conn:
        sqlite_store._configure_sqlite_connection(conn)
        sqlite_store._ensure_control_plane_schema(conn)

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO candidate_profiles VALUES (
                    'failed-archived', NULL, 'bad.yaml', 'application/yaml', 3, 'sha',
                    'failed', 'archived', 'invalid_yaml', 'Invalid YAML', 0, 0, NULL,
                    'now', 'now', 'now', 1
                )
                """
            )
        conn.execute(
            """
            INSERT INTO synonym_suggestions (
                suggestion_id, synonym_type, alias, canonical, normalized_alias,
                normalized_canonical, concept_key, review_status, policy_effect,
                created_at, updated_at, revision
            ) VALUES (
                'suggestion-absent', 'skills', 'js', 'javascript', 'js',
                'javascript', 'skills:js:javascript', 'pending', 'absent',
                'now', 'now', 1
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO synonym_suggestions (
                    suggestion_id, synonym_type, alias, canonical, normalized_alias,
                    normalized_canonical, concept_key, review_status, policy_effect,
                    created_at, updated_at, revision
                ) VALUES (
                    'suggestion-none', 'skills', 'ts', 'typescript', 'ts',
                    'typescript', 'skills:ts:typescript', 'pending', 'none',
                    'now', 'now', 1
                )
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO synonym_suggestions (
                    suggestion_id, synonym_type, alias, canonical, normalized_alias,
                    normalized_canonical, concept_key, review_status, policy_effect,
                    created_at, updated_at, revision
                ) VALUES (
                    'suggestion-1', 'skills', 'sql', 'structured query language', 'sql',
                    'structured query language', 'skills:sql:structured query language',
                    'pending', 'active', 'now', 'now', 1
                )
                """
            )


def test_control_plane_schema_requires_one_succeeded_idempotent_response_representation() -> None:
    with sqlite3.connect(":memory:") as conn:
        sqlite_store._configure_sqlite_connection(conn)
        sqlite_store._ensure_control_plane_schema(conn)

        conn.execute(
            """
            INSERT INTO idempotent_actions (
                action_id, action_scope, idempotency_key, request_fingerprint, status,
                response_json, created_at, updated_at
            ) VALUES ('json', 'test', 'json', 'sha-json', 'succeeded', '{}', 'now', 'now')
            """
        )
        conn.execute(
            """
            INSERT INTO idempotent_actions (
                action_id, action_scope, idempotency_key, request_fingerprint, status,
                response_blob, response_media_type, response_filename, response_checksum,
                created_at, updated_at
            ) VALUES (
                'binary', 'test', 'binary', 'sha-binary', 'succeeded', X'504B',
                'application/zip', 'backup.zip', 'sha-response', 'now', 'now'
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO idempotent_actions (
                    action_id, action_scope, idempotency_key, request_fingerprint, status,
                    created_at, updated_at
                ) VALUES ('missing', 'test', 'missing', 'sha-missing', 'succeeded', 'now', 'now')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO idempotent_actions (
                    action_id, action_scope, idempotency_key, request_fingerprint, status,
                    response_json, response_blob, response_media_type, response_filename,
                    response_checksum, created_at, updated_at
                ) VALUES (
                    'both', 'test', 'both', 'sha-both', 'succeeded', '{}', X'504B',
                    'application/zip', 'backup.zip', 'sha-response', 'now', 'now'
                )
                """
            )


def test_control_plane_schema_rejects_unversioned_existing_database() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE local_pipeline_runs (run_id TEXT PRIMARY KEY, run_json TEXT NOT NULL, created_at TEXT NOT NULL)")

        with pytest.raises(sqlite_store.DatabaseSchemaIncompatibleError) as exc_info:
            sqlite_store._ensure_control_plane_schema(conn)

        assert exc_info.value.code == "database_schema_incompatible"


def test_control_plane_schema_rejects_previous_version_database() -> None:
    with sqlite3.connect(":memory:") as conn:
        conn.execute(
            "CREATE TABLE cv_evaluations (cv_evaluation_id TEXT PRIMARY KEY)"
        )
        conn.execute("PRAGMA user_version = 2")

        with pytest.raises(sqlite_store.DatabaseSchemaIncompatibleError) as exc_info:
            sqlite_store._ensure_control_plane_schema(conn)

        assert exc_info.value.found_version == 2

def test_initialize_control_plane_database_seeds_profile_catalog(tmp_path: Path) -> None:
    profile_path = tmp_path / "candidate_profile.yaml"
    profile_path.write_text(
        """
name: Ada Candidate
headline: Data leader
contact:
  email: ada@example.com
experiences:
  - id: exp-1
    role: Data Analyst
    company: Example
    bullets: []
education: []
skills:
  - name: SQL
projects: []
achievements: []
preferences:
  seniority_target: senior
  location_types: [remote]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    database_path = tmp_path / "fitcv.sqlite3"

    sqlite_store.initialize_control_plane_database(database_path, profile_path)

    rows = sqlite_store.list_candidate_profiles(database_path=database_path)
    assert [row["candidate_profile_id"] for row in rows] == [
        "candidate-product-data",
        "candidate-analytics",
        "candidate-platform",
    ]
    assert rows[0]["is_default"] is True
    assert all("profile_json" not in row and row["revision"] == 1 for row in rows)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM candidate_profiles WHERE creation_status = 'succeeded' AND lifecycle = 'active'"
        ).fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM candidate_profile_revisions").fetchone()[0] == 3
    assert sqlite_store.list_startup_warnings(database_path=database_path) == []

def test_initialize_control_plane_database_keeps_empty_catalog_with_setup_warning(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "candidate_profile.yaml"
    profile_path.write_text("name: invalid\n", encoding="utf-8")
    database_path = tmp_path / "fitcv.sqlite3"

    sqlite_store.initialize_control_plane_database(database_path, profile_path)

    assert sqlite_store.list_candidate_profiles(database_path=database_path) == []
    warnings = sqlite_store.list_startup_warnings(database_path=database_path)
    assert [warning["code"] for warning in warnings] == ["candidate_profile_setup_required"]
    assert "candidate profile" in warnings[0]["message"].lower()
    assert warnings[0]["action"] == "Update candidate_profile.yaml, then reset the database."


def _synonym_policy_paths(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "skills": tmp_path / "skill_synonyms.yaml",
        "domain": tmp_path / "domain_synonyms.yaml",
        "role_family": tmp_path / "role_family_synonyms.yaml",
    }
    paths["skills"].write_text("skill_synonyms:\n  js: javascript\n", encoding="utf-8")
    paths["domain"].write_text(
        "domain_alias_map:\n  fintech: financial services\ndomain_neighbors:\n  data: [analytics]\n",
        encoding="utf-8",
    )
    paths["role_family"].write_text(
        "role_family_alias_map:\n  analyst: data analyst\n",
        encoding="utf-8",
    )
    return paths


def test_initialize_control_plane_database_seeds_active_synonym_bundle_and_defaults(tmp_path: Path) -> None:
    profile_path = tmp_path / "candidate_profile.yaml"
    profile_path.write_text("experiences: []\nskills: []\nprojects: []\nachievements: []\npreferences: {}\n", encoding="utf-8")
    database_path = tmp_path / "fitcv.sqlite3"

    sqlite_store.initialize_control_plane_database(
        database_path,
        profile_path,
        synonym_paths=_synonym_policy_paths(tmp_path),
    )

    bundle = sqlite_store.resolve_active_synonym_bundle(database_path=database_path)
    assert bundle["revision"] == 1
    assert bundle["normalized_bundle"] == {
        "skills": {"js": "javascript"},
        "domain": {"fintech": "financial services"},
        "role_family": {"analyst": "data analyst"},
    }
    assert set(bundle["type_revisions"]) == {"skills", "domain", "role_family"}
    assert all(
        revision["revision"] == 1 and revision["type_revision_id"]
        for revision in bundle["type_revisions"].values()
    )
    with sqlite3.connect(database_path) as connection:
        defaults = dict(connection.execute(
            "SELECT setting_key, json_extract(setting_value_json, '$') FROM pipeline_settings"
        ))
    assert defaults == {
        "synonym_management.apply_approved_enabled": 1,
        "synonym_management.auto_accept_suggestions_enabled": 0,
    }


def test_invalid_synonym_draft_preserves_active_bundle(tmp_path: Path) -> None:
    database_path = tmp_path / "fitcv.sqlite3"
    with sqlite3.connect(database_path) as connection:
        sqlite_store._configure_sqlite_connection(connection)
        sqlite_store._ensure_control_plane_schema(connection)
    sqlite_store.activate_synonym_policy_bundle(
        "skills",
        editor_text="js: javascript\n",
        normalized_policy={"js": "javascript"},
        expected_draft_revision=0,
        expected_active_bundle_revision_id=None,
        database_path=database_path,
    )
    active_before = sqlite_store.resolve_active_synonym_bundle(database_path=database_path)

    draft = sqlite_store.save_synonym_policy_draft(
        "skills",
        editor_text="js:\n",
        normalized_policy=None,
        issues=[{"code": "synonym_missing_canonical", "lines": [1]}],
        expected_draft_revision=1,
        database_path=database_path,
    )

    assert draft["validation_status"] == "invalid"
    assert draft["draft_revision"] == 2
    assert sqlite_store.resolve_active_synonym_bundle(database_path=database_path) == active_before


def test_synonym_policy_activation_uses_draft_and_bundle_compare_and_swap(tmp_path: Path) -> None:
    database_path = tmp_path / "fitcv.sqlite3"
    first = sqlite_store.activate_synonym_policy_bundle(
        "skills",
        editor_text="js: javascript\n",
        normalized_policy={"js": "javascript"},
        expected_draft_revision=0,
        expected_active_bundle_revision_id=None,
        database_path=database_path,
    )

    second = sqlite_store.activate_synonym_policy_bundle(
        "domain",
        editor_text="fintech: financial services\n",
        normalized_policy={"fintech": "financial services"},
        expected_draft_revision=0,
        expected_active_bundle_revision_id=first["active_bundle_revision_id"],
        database_path=database_path,
    )

    assert second["active_bundle_revision"] == 2
    assert second["normalized_bundle"]["skills"] == {"js": "javascript"}
    assert second["normalized_bundle"]["domain"] == {"fintech": "financial services"}
    with pytest.raises(sqlite_store.SynonymPolicyRevisionConflict):
        sqlite_store.activate_synonym_policy_bundle(
            "role_family",
            editor_text="analyst: data analyst\n",
            normalized_policy={"analyst": "data analyst"},
            expected_draft_revision=0,
            expected_active_bundle_revision_id=first["active_bundle_revision_id"],
            database_path=database_path,
        )

def test_repair_active_synonym_policy_mirrors_marks_state_in_sync(tmp_path: Path) -> None:
    database_path = tmp_path / "fitcv.sqlite3"
    paths = _synonym_policy_paths(tmp_path)
    activated = sqlite_store.activate_synonym_policy_bundle_set(
        {
            "skills": {"ts": "typescript"},
            "domain": {"payments": "financial services"},
            "role_family": {"developer": "software engineer"},
        },
        expected_active_bundle_revision_id=None,
        database_path=database_path,
    )
    assert activated["mirror_status"] == "repair_required"

    repaired = sqlite_store.repair_active_synonym_policy_mirrors(
        database_path=database_path,
        synonym_paths=paths,
    )

    assert repaired["mirror_status"] == "in_sync"
    assert "ts: typescript" in paths["skills"].read_text(encoding="utf-8")
    assert "domain_neighbors:\n  data: [analytics]\n" in paths["domain"].read_text(encoding="utf-8")

@pytest.mark.parametrize("failure_call", [1, 2, 3])
def test_repair_active_synonym_policy_mirrors_recovers_after_each_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
) -> None:
    database_path = tmp_path / "fitcv.sqlite3"
    paths = _synonym_policy_paths(tmp_path)
    activated = sqlite_store.activate_synonym_policy_bundle_set(
        {
            "skills": {"ts": "typescript"},
            "domain": {"payments": "financial services"},
            "role_family": {"developer": "software engineer"},
        },
        expected_active_bundle_revision_id=None,
        database_path=database_path,
    )
    real_replace = os.replace
    calls = 0

    def fail_selected_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("replace failed")
        real_replace(source, target)

    monkeypatch.setattr("fitcv_cp.synonym_policy_io.os.replace", fail_selected_replace)
    with pytest.raises(OSError, match="replace failed"):
        sqlite_store.repair_active_synonym_policy_mirrors(
            database_path=database_path,
            synonym_paths=paths,
        )

    failed = sqlite_store.resolve_active_synonym_bundle(database_path=database_path)
    assert failed["bundle_revision_id"] == activated["bundle_revision_id"]
    assert failed["mirror_status"] == "repair_failed"
    monkeypatch.setattr("fitcv_cp.synonym_policy_io.os.replace", real_replace)
    repaired = sqlite_store.repair_active_synonym_policy_mirrors(
        database_path=database_path,
        synonym_paths=paths,
    )
    assert repaired["mirror_status"] == "in_sync"


def test_create_run_bundle_atomically_captures_profile_settings_and_apply_off_bundle(tmp_path: Path) -> None:
    database_path = Path(sqlite_store._local_sqlite_path())
    profile = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=b"experiences: []\nskills: []\nprojects: []\nachievements: []\npreferences: {}\n",
        original_filename="profile.yaml",
        profile_name="Candidate",
        database_path=database_path,
    )
    bundle = sqlite_store.activate_synonym_policy_bundle(
        "skills",
        editor_text="js: javascript\n",
        normalized_policy={"js": "javascript"},
        expected_draft_revision=0,
        expected_active_bundle_revision_id=None,
        database_path=database_path,
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO pipeline_settings VALUES (?, ?, ?, ?)",
            ("synonym_management.apply_approved_enabled", "false", "test", "now"),
        )
        connection.commit()
    run = _make_run("run-snapshot")

    sqlite_store.create_run_bundle(
        run,
        input_resource={
            "strict_candidate_profile": True,
            "candidate_profile_id": profile["profile_id"],
            "jobs_snapshot_json": '[{"title":"Analyst"}]',
            "jobs_manifest_json": "{}",
        },
        jobs=[{"title": "Analyst"}],
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """SELECT candidate_profile_revision_id, settings_snapshot_json,
                      synonym_policy_bundle_revision_id, synonym_policy_bundle_snapshot_json
               FROM run_inputs WHERE run_id = ?""",
            (run.run_id,),
        ).fetchone()
    assert row[0] == profile["profile_revision_id"]
    assert json.loads(row[1])["synonym_management.apply_approved_enabled"] is False
    assert row[2] == bundle["active_bundle_revision_id"]
    assert json.loads(row[3])["approved_mapping_projection"]["skills"] == {}


def test_create_run_bundle_rejects_archived_profile_without_run_row(tmp_path: Path) -> None:
    database_path = Path(sqlite_store._local_sqlite_path())
    profile = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=b"experiences: []\nskills: []\nprojects: []\nachievements: []\npreferences: {}\n",
        original_filename="profile.yaml",
        profile_name="Candidate",
        database_path=database_path,
    )
    sqlite_store.transition_candidate_profile_lifecycle(
        profile["profile_id"], lifecycle="archived", expected_revision=1, database_path=database_path
    )

    with pytest.raises(sqlite_store.CandidateProfileUnavailableError):
        sqlite_store.create_run_bundle(
            _make_run("run-stale-profile"),
            input_resource={
                "strict_candidate_profile": True,
                "candidate_profile_id": profile["profile_id"],
                "jobs_snapshot_json": '[{"title":"Analyst"}]',
                "jobs_manifest_json": "{}",
            },
            jobs=[{"title": "Analyst"}],
        )
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE run_id = 'run-stale-profile'"
        ).fetchone()[0] == 0


def test_synonym_suggestions_aggregate_across_runs_and_preserve_approved_decision() -> None:
    for run_id in ("run-source-1", "run-source-2"):
        sqlite_store.insert_run(_make_run(run_id))

    first = sqlite_store.ingest_synonym_suggestions(
        [{"synonym_type": "skills", "alias": "JS", "canonical": "JavaScript", "run_id": "run-source-1", "evidence": {"text": "JS"}}]
    )
    second = sqlite_store.ingest_synonym_suggestions(
        [{"synonym_type": "skills", "alias": "js", "canonical": "javascript", "run_id": "run-source-2", "evidence": {"text": "js"}}]
    )

    assert first["created_count"] == 1
    assert second["created_count"] == 0
    page = sqlite_store.query_synonym_suggestions(synonym_type="skills", review_status="pending")
    assert page["total"] == 1 and page["items"][0]["source_count"] == 2
    suggestion_id = page["items"][0]["suggestion_id"]
    summary = sqlite_store.apply_synonym_suggestion_action(
        [suggestion_id], action="approve", acted_by="admin"
    )
    assert summary["approved_count"] == 1
    assert sqlite_store.get_synonym_suggestion(suggestion_id)["policy_effect"] == "active"

    sqlite_store.delete_run_synonym_sources("run-source-1")
    sqlite_store.delete_run_synonym_sources("run-source-2")
    assert sqlite_store.get_synonym_suggestion(suggestion_id)["source_count"] == 0


def test_synonym_suggestion_detail_pages_evidence_sources() -> None:
    for index in range(11):
        run_id = f"run-evidence-{index:02d}"
        sqlite_store.insert_run(_make_run(run_id))
        sqlite_store.ingest_synonym_suggestions([
            {
                "synonym_type": "skills",
                "alias": "JS",
                "canonical": "JavaScript",
                "run_id": run_id,
                "evidence": {"signals": [{"text": run_id}]},
            }
        ])

    suggestion_id = sqlite_store.query_synonym_suggestions()["items"][0]["suggestion_id"]
    first = sqlite_store.get_synonym_suggestion(
        suggestion_id, evidence_page=1, evidence_page_size=10
    )
    second = sqlite_store.get_synonym_suggestion(
        suggestion_id, evidence_page=2, evidence_page_size=10
    )

    assert first["source_page"] == {
        "page": 1,
        "page_size": 10,
        "total_items": 11,
        "total_pages": 2,
    }
    assert len(first["sources"]) == 10
    assert len(second["sources"]) == 1
    assert first["sources"][0]["run_id"] != second["sources"][0]["run_id"]
    assert set(first["sources"][0]["evidence"]) == {"signals"}
    assert "evidence_json" not in first["sources"][0]

def test_synonym_approval_rolls_back_policy_and_decision_when_processing_log_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sqlite_store.insert_run(_make_run("run-atomic-approval"))
    sqlite_store.ingest_synonym_suggestions([
        {
            "synonym_type": "skills",
            "alias": "JS",
            "canonical": "JavaScript",
            "run_id": "run-atomic-approval",
            "evidence": {},
        }
    ])
    suggestion = sqlite_store.query_synonym_suggestions(review_status="pending")["items"][0]
    monkeypatch.setattr(
        sqlite_store,
        "_record_synonym_processing_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("log failed")),
    )

    with pytest.raises(RuntimeError, match="log failed"):
        sqlite_store.apply_synonym_suggestion_action(
            [suggestion["suggestion_id"]],
            action="approve",
            acted_by="admin",
        )

    assert sqlite_store.get_synonym_suggestion(suggestion["suggestion_id"])["review_status"] == "pending"
    assert sqlite_store.resolve_active_synonym_bundle()["revision"] == 0

def test_synonym_approval_rejects_stale_policy_revision() -> None:
    sqlite_store.insert_run(_make_run("run-stale-approval"))
    sqlite_store.ingest_synonym_suggestions([
        {
            "synonym_type": "skills",
            "alias": "JS",
            "canonical": "JavaScript",
            "run_id": "run-stale-approval",
            "evidence": {},
        }
    ])
    suggestion = sqlite_store.query_synonym_suggestions(review_status="pending")["items"][0]

    with pytest.raises(ValueError, match="revision_conflict"):
        sqlite_store.apply_synonym_suggestion_action(
            [suggestion["suggestion_id"]],
            action="approve",
            acted_by="admin",
            expected_draft_revision=1,
            expected_active_bundle_revision_id=None,
        )

    assert sqlite_store.get_synonym_suggestion(suggestion["suggestion_id"])["review_status"] == "pending"

def test_valid_policy_save_reconciles_matching_approved_blocked_suggestion() -> None:
    sqlite_store.insert_run(_make_run("run-blocked-reconcile"))
    sqlite_store.ingest_synonym_suggestions([
        {"synonym_type": "skills", "alias": "a", "canonical": "b", "run_id": "run-blocked-reconcile", "evidence": {}},
        {"synonym_type": "skills", "alias": "b", "canonical": "a", "run_id": "run-blocked-reconcile", "evidence": {}},
    ])
    items = sqlite_store.query_synonym_suggestions(review_status="pending")["items"]
    sqlite_store.apply_synonym_suggestion_action(
        [item["suggestion_id"] for item in items],
        action="approve",
        acted_by="admin",
    )
    blocked = {item["normalized_alias"]: item for item in sqlite_store.query_synonym_suggestions(review_status="approved")["items"]}
    assert {item["policy_effect"] for item in blocked.values()} == {"blocked"}

    policy = sqlite_store.get_synonym_policy("skills")
    sqlite_store.activate_synonym_policy_bundle(
        "skills",
        editor_text="a: b\n",
        normalized_policy={"a": "b"},
        expected_draft_revision=policy["draft_revision"],
        expected_active_bundle_revision_id=policy["active_bundle_revision_id"],
    )

    assert sqlite_store.get_synonym_suggestion(blocked["a"]["suggestion_id"])["policy_effect"] == "active"
    assert sqlite_store.get_synonym_suggestion(blocked["b"]["suggestion_id"])["policy_effect"] == "blocked"


def test_run_source_cleanup_deletes_zero_source_pending_and_declined() -> None:
    sqlite_store.insert_run(_make_run("run-source-cleanup"))
    sqlite_store.ingest_synonym_suggestions([
        {"synonym_type": "domain", "alias": "fintech", "canonical": "financial services", "run_id": "run-source-cleanup", "evidence": {}},
        {"synonym_type": "domain", "alias": "insurtech", "canonical": "insurance", "run_id": "run-source-cleanup", "evidence": {}},
    ])
    items = sqlite_store.query_synonym_suggestions(synonym_type="domain", review_status="pending")["items"]
    sqlite_store.apply_synonym_suggestion_action([items[1]["suggestion_id"]], action="decline", acted_by="admin")

    cleanup = sqlite_store.delete_run_synonym_sources("run-source-cleanup")

    assert cleanup["deleted_suggestion_count"] == 2
    assert sqlite_store.query_synonym_suggestions(synonym_type="domain")["total"] == 0


def test_bookmark_query_selection_and_removal_share_filtered_intersection() -> None:
    run = _make_run("run-bookmark-selection")
    sqlite_store.create_run_bundle(
        run,
        input_resource={"jobs_snapshot_json": '[{"title":"Alpha"},{"title":"Beta"}]', "jobs_manifest_json": "{}"},
        jobs=[{"title": "Alpha", "company": "One"}, {"title": "Beta", "company": "Two"}],
    )
    jobs = sqlite_store.query_run_jobs(run.run_id, page_size=20)["items"]
    for job in jobs:
        sqlite_store.set_bookmark(job["run_job_id"])

    page = sqlite_store.query_bookmarks(search="Alpha", page_size=20)
    selection = sqlite_store.resolve_job_selection(
        [job["run_job_id"] for job in jobs], scope="bookmarks", search="Alpha"
    )
    removed = sqlite_store.remove_bookmarks(
        [job["run_job_id"] for job in jobs], search="Alpha"
    )

    assert page["total"] == 1 and page["items"][0]["title"] == "Alpha"
    assert selection["matched_count"] == 1 and selection["excluded_count"] == 1
    assert removed["removed_count"] == 1
    assert sqlite_store.query_bookmarks(page_size=20)["total"] == 1


def test_delete_archived_runs_reports_bookmark_loss_and_cleans_zero_source_suggestions() -> None:
    run = _make_run("run-delete-counts")
    run.status = RunStatus.SUCCEEDED
    run.archived_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
    sqlite_store.create_run_bundle(
        run,
        input_resource={"jobs_snapshot_json": '[{"title":"Alpha"}]', "jobs_manifest_json": "{}"},
        jobs=[{"title": "Alpha"}],
    )
    job = sqlite_store.query_run_jobs(run.run_id)["items"][0]
    sqlite_store.set_bookmark(job["run_job_id"])
    sqlite_store.ingest_synonym_suggestions([
        {"synonym_type": "skills", "alias": "js", "canonical": "javascript", "run_id": run.run_id, "evidence": {}}
    ])

    summary = sqlite_store.delete_archived_runs("all", run_ids=[run.run_id])

    assert summary["deleted_count"] == 1
    assert summary["deleted_bookmark_count"] == 1
    assert summary["deleted_synonym_suggestion_count"] == 1

def test_preview_delete_archived_runs_reports_missing_active_and_bookmark_counts() -> None:
    archived = _make_run("run-delete-preview-archived")
    archived.status = RunStatus.SUCCEEDED
    archived.archived_at = datetime.datetime.now(datetime.timezone.utc)
    active = _make_run("run-delete-preview-active")
    sqlite_store.create_run_bundle(
        archived,
        input_resource={"jobs_snapshot_json": '[{"title":"Analyst"}]', "jobs_manifest_json": "{}"},
        jobs=[{"title": "Analyst"}],
    )
    sqlite_store.insert_run(active)
    job = sqlite_store.query_run_jobs(archived.run_id)["items"][0]
    sqlite_store.set_bookmark(job["run_job_id"])

    preview = sqlite_store.preview_delete_archived_runs([
        archived.run_id,
        active.run_id,
        "run-delete-preview-missing",
    ])

    assert preview["eligible_run_ids"] == [archived.run_id]
    assert preview["blocked_run_ids"] == [active.run_id]
    assert preview["missing_run_ids"] == ["run-delete-preview-missing"]
    assert preview["bookmark_count"] == 1
    assert len(preview["state_tokens"]) == 1

def test_delete_archived_runs_rejects_state_change_after_preview() -> None:
    run = _make_run("run-delete-stale")
    run.status = RunStatus.SUCCEEDED
    run.archived_at = datetime.datetime.now(datetime.timezone.utc)
    sqlite_store.create_run_bundle(
        run,
        input_resource={"jobs_snapshot_json": '[{"title":"Analyst"}]', "jobs_manifest_json": "{}"},
        jobs=[{"title": "Analyst"}],
    )
    preview = sqlite_store.preview_delete_archived_runs([run.run_id])
    job = sqlite_store.query_run_jobs(run.run_id)["items"][0]
    sqlite_store.set_bookmark(job["run_job_id"])

    with pytest.raises(ValueError, match="delete_preview_stale"):
        sqlite_store.delete_archived_runs(
            "all",
            run_ids=[run.run_id],
            expected_state_tokens=preview["state_tokens"],
        )

    assert sqlite_store.get_run(run.run_id) is not None

def test_delete_archived_runs_reports_filesystem_cleanup_failure_after_database_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _make_run("run-delete-cleanup-failure")
    run.status = RunStatus.SUCCEEDED
    run.archived_at = datetime.datetime.now(datetime.timezone.utc)
    sqlite_store.insert_run(run)
    monkeypatch.setattr(
        sqlite_store,
        "_cleanup_deleted_run_files",
        lambda _run_id: (_ for _ in ()).throw(OSError("locked")),
    )

    summary = sqlite_store.delete_archived_runs("all", run_ids=[run.run_id])

    assert summary["deleted_run_ids"] == [run.run_id]
    assert summary["filesystem_cleanup_failed_run_ids"] == [run.run_id]
    assert summary["filesystem_cleanup_error_code"] == "run_files_cleanup_failed"
    assert sqlite_store.get_run(run.run_id) is None


def test_candidate_profile_attempts_keep_failed_imports_and_support_lifecycle(tmp_path: Path) -> None:
    database_path = tmp_path / "profiles.sqlite3"
    valid_yaml = b"""
experiences: []
skills: []
projects: []
achievements: []
preferences: {}
""".strip() + b"\n"

    created = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=valid_yaml,
        original_filename=r"C:\uploads\profile.yaml",
        profile_name="  Shared Name  ",
        database_path=database_path,
    )
    duplicate = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=valid_yaml,
        original_filename="second.yaml",
        profile_name="Shared Name",
        database_path=database_path,
    )
    failed = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=b"skills: [",
        original_filename="broken.yaml",
        profile_name="   ",
        database_path=database_path,
    )

    assert created["creation_status"] == "succeeded"
    assert created["profile_name"] == "Shared Name"
    assert created["original_filename"] == "profile.yaml"
    assert created["overview"] is not None and created["failure"] is None
    assert duplicate["profile_id"] != created["profile_id"]
    assert failed["creation_status"] == "failed"
    assert failed["profile_name"] is None
    assert failed["profile_revision_id"] is None
    assert failed["overview"] is None
    assert failed["failure"]["code"] == "invalid_yaml"

    page = sqlite_store.query_candidate_profiles(database_path=database_path)
    assert page["total"] == 3
    assert page["active_count"] == 3 and page["archived_count"] == 0

    archived = sqlite_store.transition_candidate_profile_lifecycle(
        created["profile_id"],
        lifecycle="archived",
        expected_revision=created["revision"],
        database_path=database_path,
    )
    assert archived["lifecycle"] == "archived"
    with pytest.raises(ValueError, match="revision_conflict"):
        sqlite_store.transition_candidate_profile_lifecycle(
            created["profile_id"],
            lifecycle="active",
            expected_revision=created["revision"],
            database_path=database_path,
        )
    with pytest.raises(ValueError, match="profile_transition_unavailable"):
        sqlite_store.transition_candidate_profile_lifecycle(
            failed["profile_id"],
            lifecycle="archived",
            expected_revision=failed["revision"],
            database_path=database_path,
        )


def test_candidate_profile_pre_admission_validation_creates_no_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "profiles.sqlite3"

    for filename, payload, error in (
        ("profile.yml", b"skills: []", "profile_file_type_invalid"),
        ("profile.yaml", b"", "profile_file_empty"),
        ("profile.yaml", b"x" * (1024 * 1024 + 1), "profile_file_too_large"),
    ):
        with pytest.raises(ValueError, match=error):
            sqlite_store.create_candidate_profile_attempt(
                profile_bytes=payload,
                original_filename=filename,
                profile_name=None,
                database_path=database_path,
            )

    assert sqlite_store.query_candidate_profiles(database_path=database_path)["total"] == 0


def test_candidate_profile_unexpected_processing_failure_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "fitcv.candidate.load_profile_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("secret parser detail")),
    )

    failed = sqlite_store.create_candidate_profile_attempt(
        profile_bytes=b"skills: []\n",
        original_filename="profile.yaml",
        profile_name=None,
        database_path=tmp_path / "profiles.sqlite3",
    )

    assert failed["creation_status"] == "failed"
    assert failed["failure"] == {
        "code": "profile_processing_failed",
        "message": "Candidate profile could not be processed.",
    }


def test_insert_run_round_trips_from_sqlite() -> None:
    run = _make_run()

    sqlite_store.insert_run(run)
    stored = sqlite_store.get_run(run.run_id)

    assert stored is not None
    assert stored.run_id == run.run_id
    assert stored.status == RunStatus.QUEUED


def test_update_status_and_events_persist() -> None:
    run = _make_run("run-events")
    sqlite_store.insert_run(run)

    result = sqlite_store.update_run_status(
        run.run_id,
        RunStatus.RUNNING,
        None,
        project = "local",
        dataset = "fitcv",
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    event = RunEvent(
        run_id=run.run_id,
        event_id=str(uuid.uuid4()),
        stage="enrich",
        level="info",
        message="started",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        payload_json=json.dumps({"attempt": 1}),
    )
    sqlite_store.append_event(event)

    stored = sqlite_store.get_run(run.run_id)
    events = sqlite_store.get_events(run.run_id)

    assert result["persistence_status"] == "persisted"
    assert stored is not None
    assert stored.status == RunStatus.RUNNING
    assert len(events) == 1
    assert json.loads(str(events[0].payload_json)) == {"attempt": 1}


def test_run_json_updates_and_schema_status_use_sqlite_only_terms() -> None:
    run = _make_run("run-json")
    sqlite_store.insert_run(run)

    sqlite_store.update_run_results_export(
        run.run_id,
        json.dumps({"jobs": [{"job_url": "https://example.com/1"}]}),
        None,
        project = "local",
        dataset = "fitcv",
    )
    sqlite_store.update_run_stage_transition_artifacts(
        run.run_id,
        json.dumps({"artifacts": {"stages": {"enrich": {"status": "completed"}}}}),
        None,
        project = "local",
        dataset = "fitcv",
    )

    stored = sqlite_store.get_run(run.run_id)
    schema_status = sqlite_store.get_pipeline_runs_schema_status(None, project = "local", dataset = "fitcv")

    assert stored is not None
    assert json.loads(str(stored.results_export_json))["jobs"][0]["job_url"] == "https://example.com/1"
    assert schema_status["warning"] == "sqlite_mode_no_remote_schema_check"


def test_list_filter_results_for_run_decodes_marks_and_reasons() -> None:
    sqlite_store.create_run_bundle(
        _make_run("run-filter"),
        input_resource={"candidate_profile_name": "Profile", "candidate_profile_json": "{}"},
        jobs=[{"title": "Job", "job_url": "https://example.com/job-1"}],
    )
    sqlite_store.replace_filter_results("run-filter", [{
        "job_url": "https://example.com/job-1", "passed": True,
        "reasons": ["matched_required_skills"], "marks": [{"code": "required_skill"}],
    }])

    rows = sqlite_store.list_filter_results_for_run("run-filter")

    assert len(rows) == 1
    assert rows[0]["passed"] is True
    assert rows[0]["reasons"] == ["matched_required_skills"]
    assert rows[0]["marks"] == [{"code": "required_skill"}]


def test_local_sqlite_path_uses_control_plane_config_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FITCV_CP_SQLITE_PATH", raising=False)
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

    assert Path(sqlite_store._local_sqlite_path()) == tmp_path / "from-config.sqlite3"


def _training_row() -> dict[str, object]:
    result = {"status": "candidate_created", "preference_vector": [0.1, -0.1]}
    row: dict[str, object] = {
        "schema_version": "inverse_training_run_v1",
        "domain_id": "ranking_v1",
        "status": "candidate_created",
        "cohort_fingerprint": "cohort",
        "event_watermark": 2,
        "edge_set_fingerprint": "edges",
        "rating_scale_version": "application-interest-v1",
        "compiler_version": "preference-compiler-v1",
        "compiler_policy_fingerprint": "compiler",
        "decision_learning_policy_fingerprint": "decision",
        "optimizer_policy_fingerprint": "optimizer",
        "activation_policy_fingerprint": "activation",
        "baseline_policy_fingerprint": "baseline",
        "ranking_contract_fingerprint": "ranking",
        "embedding_model": "model",
        "embedding_contract_fingerprint": "embedding",
        "embedding_dimension": 2,
        "learned_alpha": 0.05,
        "parent_policy_kind": "zero_residual",
        "parent_policy_ref": "zero_residual:baseline",
        "problem_fingerprint": "problem",
        "evaluation_fingerprint": "evaluation",
        "result_json": result,
    }
    row["training_run_id"] = build_training_run_identity(row)
    return row


def _snapshot_row(training_run_id: str, *, vector: list[float], suffix: str = "") -> dict[str, object]:
    row: dict[str, object] = {
        "schema_version": "ranking_policy_snapshot_v1",
        "domain_id": "ranking_v1",
        "status": "candidate",
        "runtime_contract_fingerprint": "runtime",
        "baseline_policy_fingerprint": "baseline",
        "ranking_contract_fingerprint": "ranking",
        "embedding_model": "model",
        "embedding_contract_fingerprint": "embedding",
        "embedding_dimension": 2,
        "learned_alpha": 0.05,
        "preference_vector_norm_bound": 1.0,
        "parent_policy_kind": "zero_residual",
        "parent_policy_ref": "zero_residual:baseline",
        "preference_vector_json": vector,
        "preference_vector_fingerprint": f"vector{suffix}",
        "training_run_id": training_run_id,
        "event_watermark": 2,
        "cohort_fingerprint": "cohort",
        "edge_set_fingerprint": "edges",
        "rating_scale_version": "application-interest-v1",
        "compiler_version": "preference-compiler-v1",
        "compiler_policy_fingerprint": "compiler",
        "decision_learning_policy_fingerprint": "decision",
        "optimizer_policy_fingerprint": "optimizer",
        "activation_policy_fingerprint": "activation",
        "problem_fingerprint": "problem",
        "solver_metadata_json": {"solver": "CLARABEL"},
        "evaluation_version": "episode-grouped-v1",
        "evaluation_fingerprint": "evaluation",
        "evaluation_json": {"passed": True},
    }
    fingerprint, snapshot_id = build_policy_snapshot_identity(row)
    row["payload_fingerprint"] = fingerprint
    row["policy_snapshot_id"] = snapshot_id
    return row


def _snapshot_row_for_runtime(
    training: dict[str, object],
    *,
    runtime_contract_fingerprint: str,
    vector: list[float],
    suffix: str,
) -> dict[str, object]:
    row = _snapshot_row(str(training["training_run_id"]), vector=vector, suffix=suffix)
    row["runtime_contract_fingerprint"] = runtime_contract_fingerprint
    row["event_watermark"] = training["event_watermark"]
    row.pop("payload_fingerprint")
    row.pop("policy_snapshot_id")
    fingerprint, snapshot_id = build_policy_snapshot_identity(row)
    row["payload_fingerprint"] = fingerprint
    row["policy_snapshot_id"] = snapshot_id
    return row


def _optimization_projection_row(training: dict[str, object]) -> dict[str, object]:
    return {
        "settings_revision": "settings-revision-1",
        "ranking_mode": "personalized",
        "personalization_strength": 0.05,
        "evidence_head_fingerprint": "evidence-head-1",
        "event_watermark": int(training["event_watermark"]),
        "source_rating_event_ids": ["rating-event-1"],
        "rating_evidence_rows": [
            {
                "source_rating_event_id": "rating-event-1",
                "run_id": "run-1",
                "alternative_id": "alternative-1",
                "job_label": "Data Analyst at Example",
                "source_job_url": "https://example.com/job-1",
                "displayed_rank": 1,
                "baseline_fit": 0.8,
                "baseline_fit_label": "Strong",
                "rating": 5,
                "rated_at": "2026-07-23T08:00:00+00:00",
            }
        ],
    }


def _persist_candidate_attempt(
    training: dict[str, object], snapshot: dict[str, object] | None
) -> dict[str, object]:
    return sqlite_store.persist_candidate_attempt(
        training,
        snapshot,
        _optimization_projection_row(training),
    )


def _reset_preference_projection_migration(conn: sqlite3.Connection) -> None:
    conn.execute(
        "DELETE FROM integration_migrations WHERE migration_key = ?",
        (sqlite_store._PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION,),
    )
    conn.execute(
        "DELETE FROM pipeline_settings WHERE setting_key IN (?, ?)",
        (
            "preference_optimization.ranking_mode",
            "preference_optimization.personalization_strength",
        ),
    )
    conn.execute("DROP INDEX IF EXISTS one_active_ranking_policy_per_domain")
    conn.execute("DROP TABLE IF EXISTS preference_optimization_runs")
    conn.commit()


def _activation_provenance(**overrides: str) -> dict[str, str]:
    return {
        "current_runtime_contract_fingerprint": "runtime",
        "current_compiler_policy_fingerprint": "compiler",
        "current_decision_learning_policy_fingerprint": "decision",
        "current_optimizer_policy_fingerprint": "optimizer",
        "current_activation_policy_fingerprint": "activation",
        **overrides,
    }


def test_preference_projection_migration_backfills_legacy_run_and_defaults() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    training = _training_row()
    training["created_at"] = "2026-07-23T08:00:00+00:00"
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_preference_policy_tables(conn)
        original_user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        _reset_preference_projection_migration(conn)
        sqlite_store._insert_policy_row(
            conn,
            "inverse_training_runs",
            sqlite_store._TRAINING_COLUMNS,
            training,
        )
        sqlite_store._apply_preference_optimization_projection_migration(conn)

        public_id = build_preference_optimization_run_id(str(training["training_run_id"]))
        row = conn.execute(
            "SELECT historical_snapshot_status, settings_revision, "
            "source_rating_event_ids_json, rating_evidence_rows_json "
            "FROM preference_optimization_runs WHERE preference_optimization_run_id = ?",
            (public_id,),
        ).fetchone()
        settings = dict(
            conn.execute(
                "SELECT setting_key, setting_value_json FROM pipeline_settings "
                "WHERE setting_key LIKE 'preference_optimization.%'"
            ).fetchall()
        )

        assert row == ("legacy_unavailable", None, "[]", "[]")
        assert json.loads(settings["preference_optimization.ranking_mode"]) == "baseline"
        assert json.loads(
            settings["preference_optimization.personalization_strength"]
        ) == pytest.approx(0.05)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == original_user_version
        assert conn.execute(
            "SELECT 1 FROM integration_migrations WHERE migration_key = ?",
            (sqlite_store._PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION,),
        ).fetchone() is not None


def test_preference_projection_migration_keeps_compatible_active_and_retires_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    training = _training_row()
    training["created_at"] = "2026-07-23T08:00:00+00:00"
    compatible = _snapshot_row(
        str(training["training_run_id"]), vector=[0.1, -0.1], suffix="-compatible"
    )
    compatible.update(
        status="active",
        runtime_contract_fingerprint="runtime-compatible",
        created_at="2026-07-23T08:00:00+00:00",
        activated_at="2026-07-23T08:01:00+00:00",
    )
    incompatible = _snapshot_row(
        str(training["training_run_id"]), vector=[-0.1, 0.1], suffix="-incompatible"
    )
    incompatible.update(
        status="active",
        runtime_contract_fingerprint="runtime-incompatible",
        created_at="2026-07-23T08:00:30+00:00",
        activated_at="2026-07-23T08:02:00+00:00",
    )
    monkeypatch.setattr(
        sqlite_store,
        "_snapshot_matches_current_preference_runtime",
        lambda snapshot, context: snapshot["runtime_contract_fingerprint"]
        == "runtime-compatible",
    )

    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_preference_policy_tables(conn)
        _reset_preference_projection_migration(conn)
        sqlite_store._insert_policy_row(
            conn,
            "inverse_training_runs",
            sqlite_store._TRAINING_COLUMNS,
            training,
        )
        sqlite_store._insert_policy_row(
            conn,
            "ranking_policy_snapshots",
            sqlite_store._SNAPSHOT_COLUMNS,
            compatible,
        )
        sqlite_store._insert_policy_row(
            conn,
            "ranking_policy_snapshots",
            sqlite_store._SNAPSHOT_COLUMNS,
            incompatible,
        )
        conn.execute(
            "CREATE UNIQUE INDEX one_active_ranking_policy "
            "ON ranking_policy_snapshots (domain_id, runtime_contract_fingerprint) "
            "WHERE status = 'active'"
        )
        conn.commit()

        sqlite_store._apply_preference_optimization_projection_migration(conn)

        statuses = dict(
            conn.execute(
                "SELECT policy_snapshot_id, status FROM ranking_policy_snapshots"
            ).fetchall()
        )
        settings = dict(
            conn.execute(
                "SELECT setting_key, setting_value_json FROM pipeline_settings "
                "WHERE setting_key LIKE 'preference_optimization.%'"
            ).fetchall()
        )
        assert statuses[str(compatible["policy_snapshot_id"])] == "active"
        assert statuses[str(incompatible["policy_snapshot_id"])] == "retired"
        assert json.loads(settings["preference_optimization.ranking_mode"]) == "personalized"
        assert json.loads(
            settings["preference_optimization.personalization_strength"]
        ) == pytest.approx(0.05)
        assert conn.execute(
            "SELECT COUNT(*) FROM policy_activation_events "
            "WHERE reason_code = 'domain_single_active_migration'"
        ).fetchone()[0] == 1
        indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(ranking_policy_snapshots)")
        }
        assert "one_active_ranking_policy" not in indexes
        assert "one_active_ranking_policy_per_domain" in indexes


def test_preference_projection_migration_failure_is_atomic() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    malformed = _training_row()
    malformed["training_run_id"] = "bad-training-id"
    malformed["created_at"] = "2026-07-23T08:00:00+00:00"
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_preference_policy_tables(conn)
        _reset_preference_projection_migration(conn)
        sqlite_store._insert_policy_row(
            conn,
            "inverse_training_runs",
            sqlite_store._TRAINING_COLUMNS,
            malformed,
        )
        conn.commit()

        with pytest.raises(ValueError, match="training_run_id"):
            sqlite_store._apply_preference_optimization_projection_migration(conn)

        assert conn.execute(
            "SELECT 1 FROM integration_migrations WHERE migration_key = ?",
            (sqlite_store._PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION,),
        ).fetchone() is None
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'preference_optimization_runs'"
        ).fetchone() is None
        assert conn.execute(
            "SELECT COUNT(*) FROM pipeline_settings "
            "WHERE setting_key LIKE 'preference_optimization.%'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT status FROM inverse_training_runs WHERE training_run_id = ?",
            (malformed["training_run_id"],),
        ).fetchone()[0] == "candidate_created"


def test_preference_policy_schema_enforces_immutable_payload_and_one_active() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    first = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1], suffix="-a")
    second = _snapshot_row(str(training["training_run_id"]), vector=[-0.1, 0.1], suffix="-b")
    sqlite_store.insert_ranking_policy_candidate(first)
    sqlite_store.insert_ranking_policy_candidate(second)

    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE ranking_policy_snapshots SET learned_alpha = 0.1 WHERE policy_snapshot_id = ?",
                (first["policy_snapshot_id"],),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'active' WHERE policy_snapshot_id = ?",
                (second["policy_snapshot_id"],),
            )


def test_preference_policy_lifecycle_is_atomic_and_auditable() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.insert_ranking_policy_candidate(snapshot)

    activated = sqlite_store.activate_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )
    resolved = sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime")
    inspected = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")

    assert activated["status"] == "active"
    assert resolved is not None
    assert resolved["policy_snapshot_id"] == snapshot["policy_snapshot_id"]
    assert [event["action"] for event in inspected["events"]] == ["activate"]

    rolled_back = sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(snapshot["policy_snapshot_id"]),
        target="zero_residual",
        acted_by="operator",
    )

    assert rolled_back["status"] == "zero_residual"
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None


def test_activation_marks_candidate_stale_when_evidence_head_changed() -> None:
    training = _training_row()
    training["result_json"] = {
        **training["result_json"],
        "evidence_head_fingerprint": "head-before",
    }
    training["training_run_id"] = build_training_run_identity(training)
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    _persist_candidate_attempt(training, snapshot)

    with pytest.raises(ValueError, match="candidate evidence changed"):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            evidence_head_fingerprint="head-after",
            acted_by="operator",
            **_activation_provenance(),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "stale"
    assert lifecycle["events"][0]["reason_code"] == "evidence_changed"
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None


@pytest.mark.parametrize(
    ("changed_field", "reason_code", "message"),
    (
        (
            "current_runtime_contract_fingerprint",
            "runtime_contract_changed",
            "candidate runtime contract changed",
        ),
        (
            "current_compiler_policy_fingerprint",
            "compiler_policy_changed",
            "candidate compiler policy changed",
        ),
        (
            "current_activation_policy_fingerprint",
            "activation_policy_changed",
            "candidate activation policy changed",
        ),
        (
            "current_optimizer_policy_fingerprint",
            "optimizer_policy_changed",
            "candidate optimizer policy changed",
        ),
        (
            "current_decision_learning_policy_fingerprint",
            "decision_learning_policy_changed",
            "candidate decision learning policy changed",
        ),
    ),
)
def test_activation_marks_candidate_stale_when_current_provenance_changed(
    changed_field: str,
    reason_code: str,
    message: str,
) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    _persist_candidate_attempt(training, snapshot)

    with pytest.raises(ValueError, match=message):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            acted_by="operator",
            **_activation_provenance(**{changed_field: "changed"}),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "stale"
    assert lifecycle["events"][0]["reason_code"] == reason_code


def test_concurrent_sibling_activation_has_one_winner() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    snapshots = [
        _snapshot_row(str(training["training_run_id"]), vector=vector, suffix=suffix)
        for vector, suffix in (([0.1, -0.1], "-a"), ([-0.1, 0.1], "-b"))
    ]
    for snapshot in snapshots:
        sqlite_store.insert_ranking_policy_candidate(snapshot)

    def activate(snapshot_id: str) -> str:
        try:
            sqlite_store.activate_ranking_policy_candidate(
                snapshot_id,
                expected_parent_ref="zero_residual:baseline",
                acted_by="operator",
                **_activation_provenance(),
            )
        except ValueError as exc:
            return str(exc)
        return "active"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(activate, [str(snapshot["policy_snapshot_id"]) for snapshot in snapshots])
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert sorted(outcomes) == ["active", "candidate parent changed"]
    assert [row["status"] for row in lifecycle["snapshots"]].count("active") == 1
    assert [row["status"] for row in lifecycle["snapshots"]].count("stale") == 1


def test_activation_event_failure_rolls_back_candidate_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    _persist_candidate_attempt(training, snapshot)
    monkeypatch.setattr(
        sqlite_store,
        "_append_policy_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("event failed")),
    )

    with pytest.raises(RuntimeError, match="event failed"):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            acted_by="operator",
            **_activation_provenance(),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "candidate"
    assert lifecycle["events"] == []


def test_rollback_restores_exact_learned_snapshot_then_zero_residual() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    first = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1], suffix="-a")
    sqlite_store.insert_ranking_policy_candidate(first)
    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )
    second = _snapshot_row(str(training["training_run_id"]), vector=[-0.1, 0.1], suffix="-b")
    second["parent_policy_kind"] = "learned"
    second["parent_policy_ref"] = f"learned:{first['policy_snapshot_id']}"
    fingerprint, snapshot_id = build_policy_snapshot_identity(second)
    second["payload_fingerprint"] = fingerprint
    second["policy_snapshot_id"] = snapshot_id
    sqlite_store.insert_ranking_policy_candidate(second)
    sqlite_store.activate_ranking_policy_candidate(
        str(second["policy_snapshot_id"]),
        expected_parent_ref=str(second["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(second["policy_snapshot_id"]),
        target=str(first["policy_snapshot_id"]),
        acted_by="operator",
    )
    restored = sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime")

    assert restored is not None
    assert restored["payload_fingerprint"] == first["payload_fingerprint"]
    assert restored["preference_vector_json"] == first["preference_vector_json"]

    sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(first["policy_snapshot_id"]),
        target="zero_residual",
        acted_by="operator",
    )
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None

def test_training_and_candidate_insert_is_atomic_and_idempotent() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])

    first = _persist_candidate_attempt(training, snapshot)
    second = _persist_candidate_attempt(training, snapshot)

    assert first == second
    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert len(lifecycle["training_runs"]) == 1
    assert len(lifecycle["snapshots"]) == 1


def test_preference_optimization_projection_is_persisted_and_immutable() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])

    persisted = _persist_candidate_attempt(training, snapshot)
    public_id = build_preference_optimization_run_id(str(training["training_run_id"]))

    assert persisted["optimization_run"]["preference_optimization_run_id"] == public_id
    assert sqlite_store.list_preference_optimization_runs()[0][
        "preference_optimization_run_id"
    ] == public_id
    assert sqlite_store.get_preference_optimization_run(public_id)[
        "policy_snapshot_id"
    ] == snapshot["policy_snapshot_id"]

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable optimization run"):
            conn.execute(
                "UPDATE preference_optimization_runs SET settings_revision = 'changed' "
                "WHERE preference_optimization_run_id = ?",
                (public_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="optimization run history"):
            conn.execute(
                "DELETE FROM preference_optimization_runs "
                "WHERE preference_optimization_run_id = ?",
                (public_id,),
            )


def test_preference_optimization_projection_rejects_duplicate_source_events_atomically() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    projection = _optimization_projection_row(training)
    projection["source_rating_event_ids"] = ["rating-event-1", "rating-event-1"]

    with pytest.raises(ValueError, match="ordered unique"):
        sqlite_store.persist_candidate_attempt(training, snapshot, projection)

    assert sqlite_store.list_preference_optimization_runs() == []
    assert sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")["training_runs"] == []


def test_preference_optimization_hide_is_idempotent_and_directly_traceable() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    persisted = _persist_candidate_attempt(training, snapshot)
    public_id = str(persisted["optimization_run"]["preference_optimization_run_id"])

    first = sqlite_store.hide_preference_optimization_run(public_id)
    second = sqlite_store.hide_preference_optimization_run(public_id)

    assert first == second
    assert first["hidden_at"] is not None
    assert first["hidden_by"] == "local_workspace"
    assert sqlite_store.list_preference_optimization_runs() == []
    assert sqlite_store.get_preference_optimization_run(public_id)["hidden_at"] == first["hidden_at"]
    events = sqlite_store.get_process_events("optimization", "ranking_v1")["events"]
    assert [event.operation for event in events].count("optimization_run_hidden") == 1


def test_preference_optimization_hide_blocks_active_policy_owner() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    persisted = _persist_candidate_attempt(training, snapshot)
    sqlite_store.activate_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )

    with pytest.raises(ValueError, match="active_policy_must_be_inactivated"):
        sqlite_store.hide_preference_optimization_run(
            str(persisted["optimization_run"]["preference_optimization_run_id"])
        )

    assert len(sqlite_store.list_preference_optimization_runs()) == 1


def test_public_run_activation_replaces_incompatible_domain_active_policy() -> None:
    first_training = _training_row()
    first_snapshot = _snapshot_row_for_runtime(
        first_training,
        runtime_contract_fingerprint="runtime-old",
        vector=[0.1, -0.1],
        suffix="-old",
    )
    first = _persist_candidate_attempt(first_training, first_snapshot)["optimization_run"]
    sqlite_store.activate_preference_optimization_run(
        str(first["preference_optimization_run_id"]),
        expected_parent_ref="zero_residual:baseline",
        **_activation_provenance(current_runtime_contract_fingerprint="runtime-old"),
    )

    second_training = _training_row()
    second_training["event_watermark"] = 3
    second_training.pop("training_run_id")
    second_training["training_run_id"] = build_training_run_identity(second_training)
    second_snapshot = _snapshot_row_for_runtime(
        second_training,
        runtime_contract_fingerprint="runtime-new",
        vector=[-0.1, 0.1],
        suffix="-new",
    )
    second = _persist_candidate_attempt(second_training, second_snapshot)["optimization_run"]

    activated = sqlite_store.activate_preference_optimization_run(
        str(second["preference_optimization_run_id"]),
        expected_parent_ref="zero_residual:baseline",
        **_activation_provenance(current_runtime_contract_fingerprint="runtime-new"),
    )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle(
        "ranking_v1", runtime_contract_fingerprint="runtime-new"
    )
    assert activated["policy_status"] == "active"
    assert lifecycle["domain_active_snapshot"]["policy_snapshot_id"] == second_snapshot[
        "policy_snapshot_id"
    ]
    assert lifecycle["compatible_active_snapshot"]["policy_snapshot_id"] == second_snapshot[
        "policy_snapshot_id"
    ]
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime-old") is None
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime-new") is not None
    assert sqlite_store.get_preference_optimization_run(
        str(first["preference_optimization_run_id"])
    )["policy_status"] == "retired"
    assert {event["acted_by"] for event in lifecycle["events"]} == {"local_workspace"}


def test_public_run_activation_rejects_hidden_run_without_mutation() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    run = _persist_candidate_attempt(training, snapshot)["optimization_run"]
    public_id = str(run["preference_optimization_run_id"])
    sqlite_store.hide_preference_optimization_run(public_id)

    with pytest.raises(ValueError, match="optimization_run_hidden"):
        sqlite_store.activate_preference_optimization_run(
            public_id,
            expected_parent_ref="zero_residual:baseline",
            **_activation_provenance(),
        )

    assert sqlite_store.get_preference_optimization_run(public_id)["policy_status"] == "candidate"


def test_public_run_inactivation_is_fixed_target_and_preserves_ranking_mode() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    run = _persist_candidate_attempt(training, snapshot)["optimization_run"]
    public_id = str(run["preference_optimization_run_id"])
    sqlite_store.activate_preference_optimization_run(
        public_id,
        expected_parent_ref="zero_residual:baseline",
        **_activation_provenance(),
    )
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO pipeline_settings "
            "(setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
            (
                "preference_optimization.ranking_mode",
                json.dumps("personalized"),
                "test",
                "2026-07-23T08:00:00+00:00",
            ),
        )
        conn.commit()

    result = sqlite_store.inactivate_preference_optimization_run(
        public_id,
        expected_active_snapshot_id=str(snapshot["policy_snapshot_id"]),
    )

    assert result["policy_status"] == "retired"
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None
    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["events"][-1]["reason_code"] == "manual_inactivation"
    assert lifecycle["events"][-1]["acted_by"] == "local_workspace"
    with sqlite_store._sqlite_connection(db_path) as conn:
        mode = conn.execute(
            "SELECT setting_value_json FROM pipeline_settings "
            "WHERE setting_key = 'preference_optimization.ranking_mode' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()[0]
    assert json.loads(mode) == "personalized"


def test_lifecycle_distinguishes_domain_active_from_compatible_active() -> None:
    training = _training_row()
    snapshot = _snapshot_row_for_runtime(
        training,
        runtime_contract_fingerprint="runtime-old",
        vector=[0.1, -0.1],
        suffix="-old",
    )
    run = _persist_candidate_attempt(training, snapshot)["optimization_run"]
    sqlite_store.activate_preference_optimization_run(
        str(run["preference_optimization_run_id"]),
        expected_parent_ref="zero_residual:baseline",
        **_activation_provenance(current_runtime_contract_fingerprint="runtime-old"),
    )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle(
        "ranking_v1", runtime_contract_fingerprint="runtime-new"
    )

    assert lifecycle["domain_active_snapshot"]["policy_snapshot_id"] == snapshot[
        "policy_snapshot_id"
    ]
    assert lifecycle["compatible_active_snapshot"] is None
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime-new") is None


def test_reject_exact_retry_does_not_append_second_event_and_reason_conflicts() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    _persist_candidate_attempt(training, snapshot)

    sqlite_store.reject_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="bad_metrics"
    )
    sqlite_store.reject_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="bad_metrics"
    )
    with pytest.raises(ValueError, match="conflicting rejection reason"):
        sqlite_store.reject_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="other"
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert [event["action"] for event in lifecycle["events"]] == ["reject"]


def test_cv_version_lookup_and_markdown_round_trip() -> None:
    row = {
        "version_id": "ver-1",
        "run_id": "run-cv",
        "job_url": "https://example.com/job-1",
        "fit_classification": "strong",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cv_generation_model": "gpt-test",
        "cv_prompt_version": "v1",
        "cv_schema_version": "cv_doc_v1",
        "cv_structured_json": json.dumps({"schema_version": "cv_doc_v1"}),
        "cv_markdown": "# CV",
        "cv_generation_input_fingerprint": "fp-1",
        "cv_generation_reuse_status": "new",
    }

    sqlite_store.insert_cv_version_row(row)

    rows = sqlite_store.list_cvs_for_run("run-cv")
    indexed = sqlite_store.lookup_reusable_cv_versions(["fp-1"], limit=10)
    markdown = sqlite_store.get_cv_markdown("ver-1")

    assert len(rows) == 1
    assert rows[0]["version_id"] == "ver-1"
    assert indexed["fp-1"]["version_id"] == "ver-1"
    assert markdown == "# CV"


def test_delete_archived_runs_prunes_old_rows_only() -> None:
    old_run = _make_run("run-old")
    recent_run = _make_run("run-recent")
    active_run = _make_run("run-active")
    now = datetime.datetime.now(datetime.timezone.utc)
    old_run.archived_at = now - datetime.timedelta(days=10)
    old_run.archived_by = "admin"
    old_run.status = RunStatus.SUCCEEDED
    recent_run.archived_at = now - datetime.timedelta(days=1)
    recent_run.archived_by = "admin"
    recent_run.status = RunStatus.SUCCEEDED

    for run in (old_run, recent_run, active_run):
        sqlite_store.insert_run(run)

    summary = sqlite_store.delete_archived_runs(older_than_days=5)

    assert summary["deleted_count"] == 1
    assert sqlite_store.get_run("run-old") is None
    assert sqlite_store.get_run("run-recent") is not None
    assert sqlite_store.get_run("run-active") is not None

def test_insert_run_uses_normalized_pipeline_runs_without_legacy_json_table() -> None:
    run = _make_run("run-normalized")

    sqlite_store.insert_run(run)

    database_path = Path(sqlite_store._local_sqlite_path())
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "pipeline_runs" in tables
        assert "local_pipeline_runs" not in tables
        assert connection.execute(
            "SELECT backend_status FROM pipeline_runs WHERE run_id = ?", (run.run_id,)
        ).fetchone() == ("queued",)

def test_create_run_bundle_is_atomic_and_creates_six_stages_and_stable_jobs() -> None:
    run = _make_run("run-bundle")
    jobs = [
        {"title": "zeta", "company": "Z", "job_url": "https://example.com/z"},
        {"title": "Alpha", "company": "A", "job_url": "https://example.com/a"},
    ]

    result = sqlite_store.create_run_bundle(
        run,
        input_resource={
            "original_filename": "jobs.json",
            "media_type": "application/json",
            "jobs_snapshot_json": json.dumps(jobs),
            "jobs_manifest_json": "{}",
            "candidate_profile_id": "candidate-product-data",
            "candidate_profile_revision": 1,
            "candidate_profile_name": "Product Data Specialist",
            "candidate_profile_json": json.dumps({"preferences": {}}),
            "settings_revision": "settings-1",
            "settings_snapshot_json": "{}",
        },
        jobs=jobs,
    )

    assert result["run_id"] == run.run_id
    assert len(result["run_job_ids"]) == 2
    assert len(set(result["run_job_ids"])) == 2
    assert [row["stage_id"] for row in sqlite_store.list_run_stages(run.run_id)] == [
        "enrichment", "screening", "shortlisting", "ranking", "cv-analysis", "cv-generation"
    ]
    assert [row["title"] for row in sqlite_store.query_run_jobs(run.run_id)["items"]] == [
        "Alpha", "zeta"
    ]

def test_idempotent_action_replays_same_fingerprint_and_rejects_conflict() -> None:
    first = sqlite_store.reserve_idempotent_action("runs:create", "key-1", "fingerprint-1")
    sqlite_store.complete_idempotent_action(first["action_id"], {"run_id": "run-1"})

    replay = sqlite_store.reserve_idempotent_action("runs:create", "key-1", "fingerprint-1")

    assert replay["replayed"] is True
    assert replay["response"] == {"run_id": "run-1"}
    with pytest.raises(ValueError, match="idempotency_conflict"):
        sqlite_store.reserve_idempotent_action("runs:create", "key-1", "fingerprint-2")

def test_bookmark_is_deleted_with_archived_run() -> None:
    run = _make_run("run-bookmark")
    run.status = RunStatus.SUCCEEDED
    run.archived_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
    sqlite_store.create_run_bundle(
        run,
        input_resource={
            "original_filename": "jobs.json", "media_type": "application/json",
            "jobs_snapshot_json": '[{"title":"Alpha"}]', "jobs_manifest_json": "{}",
            "candidate_profile_name": "Profile", "candidate_profile_json": "{}",
            "settings_revision": "settings-1", "settings_snapshot_json": "{}",
        },
        jobs=[{"title": "Alpha", "job_url": "https://example.com/a"}],
    )
    run_job_id = sqlite_store.query_run_jobs(run.run_id)["items"][0]["run_job_id"]
    sqlite_store.set_bookmark(run_job_id)

    sqlite_store.delete_archived_runs("all", run_ids=[run.run_id])

    assert sqlite_store.list_bookmarks() == []






def test_rule_filter_schema_upgrade_adds_eligibility_columns() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_filter_results (
                run_id TEXT NOT NULL,
                job_url TEXT NOT NULL,
                passed INTEGER NOT NULL,
                reasons TEXT NOT NULL,
                marks_json TEXT,
                filtered_at TEXT NOT NULL
            )
            """
        )
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(rule_filter_results)").fetchall()
        }

    assert {
        "raw_job_fingerprint",
        "source_job_url",
        "fit_factor_results_json",
        "eligibility_policy_fingerprint",
        "eligibility_decision",
        "eligibility_reason_codes_json",
    }.issubset(columns)


def test_replace_filter_results_round_trips_explicit_eligibility_columns() -> None:
    factor_results = {
        "language_fit": {
            "factor_id": "language_fit",
            "policy_version": "eligibility-v1",
            "mode": "gate_required",
            "eligibility_decision": "reject",
            "ranking_enabled": False,
            "ranking_value": None,
            "diagnostic_code": "language_required_unmet",
            "evaluation": {
                "factor_id": "language_fit",
                "status": "fail",
                "score": 0.0,
                "confidence": 1.0,
                "reason_code": "language_required_unmet",
                "evidence": {},
                "evaluator_version": "language-fit-evaluator-v1",
                "normalizer_version": "language-fit-normalizer-v1",
            },
        }
    }
    sqlite_store.create_run_bundle(
        _make_run("run-eligibility"),
        input_resource={"candidate_profile_name": "Profile", "candidate_profile_json": "{}"},
        jobs=[{"title": "Job", "job_url": "https://example.com/job-1"}],
    )
    sqlite_store.replace_filter_results(
        "run-eligibility",
        [
            {
                "job_url": "https://example.com/job-1",
                "source_job_url": "https://example.com/job-1",
                "raw_job_fingerprint": "raw-1",
                "passed": False,
                "reasons": ["eligibility_language_fit_failed"],
                "marks": [{"code": "legacy_mark"}],
                "filtered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "fit_factor_results": factor_results,
                "eligibility_policy_fingerprint": "policy-fingerprint",
                "eligibility_decision": "reject",
                "eligibility_reason_codes": ["language_required_unmet"],
            }
        ],
    )

    rows = sqlite_store.list_filter_results_for_run("run-eligibility")

    assert rows[0]["fit_factor_results"] == factor_results
    assert rows[0]["eligibility_policy_fingerprint"] == "policy-fingerprint"
    assert rows[0]["eligibility_decision"] == "reject"
    assert rows[0]["eligibility_reason_codes"] == ["language_required_unmet"]
    assert rows[0]["marks"] == [{"code": "legacy_mark"}]
    assert "fit_factor_results" not in rows[0]["marks"][0]


def test_list_filter_results_for_run_defaults_optional_eligibility_fields() -> None:
    sqlite_store.create_run_bundle(
        _make_run("run-minimal-filter"),
        input_resource={"candidate_profile_name": "Profile", "candidate_profile_json": "{}"},
        jobs=[{"title": "Job", "job_url": "https://example.com/minimal"}],
    )
    sqlite_store.replace_filter_results("run-minimal-filter", [{
        "job_url": "https://example.com/minimal", "passed": True, "reasons": [], "marks": [],
    }])

    rows = sqlite_store.list_filter_results_for_run("run-minimal-filter")

    assert rows[0]["fit_factor_results"] == {}
    assert rows[0]["eligibility_reason_codes"] == []
    assert rows[0]["eligibility_policy_fingerprint"] is None
    assert rows[0]["eligibility_decision"] is None

def _decision_records(*, target_alternative: str = "job-1"):
    from fitcv.decision_feedback import (
        DecisionAlternative,
        DecisionEpisode,
        DecisionRatingEvent,
        RatingEventType,
        RatingValue,
    )

    now = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)
    episode = DecisionEpisode(
        episode_id="episode-1",
        domain_id="ranking_v1",
        run_id="run-feedback",
        preference_context_fingerprint="preference",
        qualification_context_fingerprint="qualification",
        ranking_contract_fingerprint="ranking",
        embedding_contract_fingerprint="embedding",
        baseline_policy_fingerprint="baseline",
        embedding_model="model",
        embedding_dimension=2,
        rating_scale_version="application-interest-v1",
        candidate_set_fingerprint="candidates",
        source_stage_artifact_fingerprint="source",
        created_at=now,
    )
    alternatives = (
        DecisionAlternative(
            episode_id=episode.episode_id,
            alternative_id="job-1",
            displayed_rank=1,
            baseline_fit=0.9,
            baseline_fit_label="strong",
            normalized_embedding_json="[1.0,0.0]",
            embedding_vector_fingerprint="vector",
            source_job_url="https://example.test/1",
            shortlist_origin="vector_search",
            created_at=now,
        ),
    )
    event = DecisionRatingEvent(
        event_sequence=None,
        event_id=str(uuid.uuid4()),
        episode_id=episode.episode_id,
        alternative_id=target_alternative,
        event_type=RatingEventType.SET_RATING,
        rating=RatingValue.FOUR,
        rating_scale_version=episode.rating_scale_version,
        acted_by="local_operator",
        created_at=now,
    )
    return episode, alternatives, event


def test_decision_feedback_ledger_is_atomic_ordered_and_append_only() -> None:
    from dataclasses import replace
    from fitcv.decision_feedback import RatingValue

    episode, alternatives, event = _decision_records()
    sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)
    _, _, second = _decision_records()
    later = episode.created_at + datetime.timedelta(minutes=1)
    repeated_episode = replace(episode, created_at=later)
    repeated_alternatives = tuple(replace(item, created_at=later) for item in alternatives)
    second = replace(second, event_id=str(uuid.uuid4()), rating=RatingValue.FIVE, created_at=later)
    sqlite_store.materialize_episode_and_append_rating(repeated_episode, repeated_alternatives, second)

    events = sqlite_store.list_decision_rating_events_for_run("run-feedback")
    assert [item.event_sequence for item in events] == [1, 2]
    assert [int(item.rating) for item in events if item.rating is not None] == [4, 5]

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE decision_rating_events SET acted_by = 'other'")


def test_decision_feedback_first_write_rolls_back_on_unknown_alternative() -> None:
    episode, alternatives, event = _decision_records(target_alternative="missing")
    with pytest.raises(ValueError, match="unknown decision alternative"):
        sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_decision_feedback_tables(conn)
        assert conn.execute("SELECT COUNT(*) FROM decision_episodes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM decision_episode_alternatives").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM decision_rating_events").fetchone()[0] == 0

def test_decision_evidence_head_characterization_and_request_loading() -> None:
    from dataclasses import replace

    from fitcv.shortlist_runtime import build_contract_fingerprint

    episode, alternatives, event = _decision_records()
    event = replace(event, event_id="event-fixed")
    sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)

    expected_payload = {
        "schema_version": "decision_evidence_head_v1",
        "domain_id": "ranking_v1",
        "event_watermark": 1,
        "episodes": [
            {
                "episode_id": "episode-1",
                "domain_id": "ranking_v1",
                "preference_context_fingerprint": "preference",
                "qualification_context_fingerprint": "qualification",
                "ranking_contract_fingerprint": "ranking",
                "embedding_contract_fingerprint": "embedding",
                "baseline_policy_fingerprint": "baseline",
                "embedding_model": "model",
                "embedding_dimension": 2,
                "rating_scale_version": "application-interest-v1",
                "candidate_set_fingerprint": "candidates",
                "source_stage_artifact_fingerprint": "source",
                "alternatives": [
                    {
                        "alternative_id": "job-1",
                        "displayed_rank": 1,
                        "baseline_fit": 0.9,
                        "baseline_fit_label": "strong",
                        "normalized_embedding": [1.0, 0.0],
                        "embedding_vector_fingerprint": "vector",
                        "shortlist_origin": "vector_search",
                    }
                ],
                "events": [
                    {
                        "event_sequence": 1,
                        "event_id": "event-fixed",
                        "episode_id": "episode-1",
                        "alternative_id": "job-1",
                        "event_type": "set_rating",
                        "rating": 4,
                        "rating_scale_version": "application-interest-v1",
                    }
                ],
            }
        ],
    }
    head = sqlite_store.get_decision_evidence_head("ranking_v1")
    assert head == {
        **expected_payload,
        "evidence_head_fingerprint": build_contract_fingerprint(expected_payload),
    }

    request = sqlite_store.load_inverse_optimization_request("ranking_v1")
    assert request.schema_version == "inverse_optimization_request_v1"
    assert request.event_watermark == 1
    assert len(request.episodes) == 1
    training_episode = request.episodes[0]
    assert training_episode.episode.run_id == "run-feedback"
    assert training_episode.alternatives[0].source_job_url == "https://example.test/1"
    assert training_episode.events[0].acted_by == "local_operator"
    assert training_episode.events_loaded_through_sequence == 1
    assert training_episode.evaluation_context is None


def test_inverse_request_marks_every_episode_loaded_through_global_watermark() -> None:
    from dataclasses import replace

    first_episode, first_alternatives, first_event = _decision_records()
    sqlite_store.materialize_episode_and_append_rating(
        first_episode, first_alternatives, first_event
    )

    second_episode = replace(
        first_episode,
        episode_id="episode-2",
        run_id="run-feedback-2",
    )
    second_alternatives = tuple(
        replace(alternative, episode_id=second_episode.episode_id)
        for alternative in first_alternatives
    )
    second_event = replace(
        first_event,
        event_id=str(uuid.uuid4()),
        episode_id=second_episode.episode_id,
    )
    sqlite_store.materialize_episode_and_append_rating(
        second_episode, second_alternatives, second_event
    )

    request = sqlite_store.load_inverse_optimization_request("ranking_v1")

    assert request.event_watermark == 2
    assert {
        item.events_loaded_through_sequence for item in request.episodes
    } == {request.event_watermark}


def test_policy_lifecycle_inspection_limits_in_sql_and_marks_rollback_eligibility() -> None:
    first_training = _training_row()
    first_snapshot = _snapshot_row(str(first_training["training_run_id"]), vector=[0.1, -0.1])
    first = _persist_candidate_attempt(first_training, first_snapshot)["snapshot"]
    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref=str(first["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    second_training = _training_row()
    second_training["problem_fingerprint"] = "problem-2"
    second_training["training_run_id"] = build_training_run_identity(second_training)
    second_snapshot = _snapshot_row(
        str(second_training["training_run_id"]), vector=[0.2, -0.2], suffix="-2"
    )
    second_snapshot["parent_policy_kind"] = "learned"
    second_snapshot["parent_policy_ref"] = f"learned:{first['policy_snapshot_id']}"
    second_snapshot["payload_fingerprint"], second_snapshot["policy_snapshot_id"] = (
        build_policy_snapshot_identity(second_snapshot)
    )
    second = _persist_candidate_attempt(second_training, second_snapshot)["snapshot"]
    sqlite_store.activate_ranking_policy_candidate(
        str(second["policy_snapshot_id"]),
        expected_parent_ref=str(second["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    inspected = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1", limit=1)
    assert len(inspected["training_runs"]) == 1
    assert len(inspected["snapshots"]) == 1
    assert len(inspected["events"]) == 1
    assert inspected["snapshots"][0]["policy_snapshot_id"] == second["policy_snapshot_id"]
    assert inspected["active_snapshot"]["policy_snapshot_id"] == second["policy_snapshot_id"]

    unbounded = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    first_row = next(
        row for row in unbounded["snapshots"]
        if row["policy_snapshot_id"] == first["policy_snapshot_id"]
    )
    assert first_row["rollback_eligible"] is True


def test_process_event_ledger_merges_sqlite_and_atomic_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fitcv_cp.models import build_process_event

    monkeypatch.setenv("FITCV_CP_LOCAL_EVENT_HISTORY_DIR", str(tmp_path / "events"))
    first = build_process_event(
        process_type="pipeline",
        process_id="a/b",
        operation="start",
        state="started",
        level="info",
        message="started",
        payload={"attempt": 1},
        event_id="event-1",
    )
    second = build_process_event(
        process_type="pipeline",
        process_id="a:b",
        operation="finish",
        state="succeeded",
        level="info",
        message="finished",
        payload={"attempt": 1},
        event_id="event-2",
    )

    sqlite_store.append_process_event(first)
    monkeypatch.setattr(
        sqlite_store,
        "_insert_process_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("disk I/O error")),
    )
    result = sqlite_store.append_process_event(second)

    page = sqlite_store.get_process_events("pipeline", "a/b")
    other_page = sqlite_store.get_process_events("pipeline", "a:b")

    assert result["persistence_backend"] == "journal"
    assert [event.event_id for event in page["events"]] == ["event-1"]
    assert [event.event_id for event in other_page["events"]] == ["event-2"]
    assert sqlite_store._process_event_journal_dir("pipeline", "a/b") != sqlite_store._process_event_journal_dir("pipeline", "a:b")


def test_process_event_contract_freezes_sanitizer_and_fingerprint() -> None:
    from fitcv_cp.models import build_process_event

    left = build_process_event(
        process_type="pipeline",
        process_id="run-1",
        operation="enrich",
        state="started",
        level="info",
        message="x" * 600,
        payload={"z": 1, "password_value": "secret", "a": [1] * 25},
        event_id="event-stable",
    )
    right = build_process_event(
        process_type="pipeline",
        process_id="run-1",
        operation="enrich",
        state="started",
        level="info",
        message="x" * 600,
        payload={"a": [1] * 25, "password_value": "different", "z": 1},
        event_id="event-stable",
        recorded_at=left.recorded_at,
    )

    assert left.payload_json == right.payload_json
    assert left.event_fingerprint == right.event_fingerprint
    assert len(left.message) == 514
    assert json.loads(left.payload_json or "{}") ["password_value"] == "[REDACTED]"


def test_candidate_attempt_process_event_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])

    persisted = _persist_candidate_attempt(training, snapshot)
    page = sqlite_store.get_process_events("optimization", "ranking_v1")

    assert persisted["snapshot"] is not None
    assert [(event.operation, event.state) for event in page["events"]] == [("candidate_create", "succeeded")]

    failing_training = _training_row()
    failing_training["event_watermark"] = 3
    failing_training.pop("training_run_id")
    failing_training["training_run_id"] = build_training_run_identity(failing_training)
    failing_snapshot = _snapshot_row(str(failing_training["training_run_id"]), vector=[0.2, -0.2], suffix="-atomic")
    original_insert = sqlite_store._insert_process_event
    monkeypatch.setattr(
        sqlite_store,
        "_insert_process_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("event failed")),
    )
    with pytest.raises(RuntimeError, match="event failed"):
        _persist_candidate_attempt(failing_training, failing_snapshot)
    monkeypatch.setattr(sqlite_store, "_insert_process_event", original_insert)

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert len(lifecycle["training_runs"]) == 1
    assert len(lifecycle["snapshots"]) == 1


def _create_normalized_run_with_jobs(run_id: str, jobs: list[dict[str, object]]) -> list[str]:
    run = _make_run(run_id)
    result = sqlite_store.create_run_bundle(
        run,
        input_resource={
            "original_filename": "jobs.json",
            "media_type": "application/json",
            "jobs_snapshot_json": json.dumps(jobs),
            "jobs_manifest_json": "{}",
            "candidate_profile_id": "candidate-product-data",
            "candidate_profile_revision": 1,
            "candidate_profile_name": "Product Data Specialist",
            "candidate_profile_json": "{}",
            "settings_revision": "settings-1",
            "settings_snapshot_json": "{}",
        },
        jobs=jobs,
    )
    return list(result["run_job_ids"])


def test_run_detail_projects_input_capabilities_and_integrity_warning() -> None:
    run_job_ids = _create_normalized_run_with_jobs(
        "run-detail",
        [{"title": "Analyst", "company": "Example", "job_url": "https://example.com/1"}],
    )
    with sqlite_store._sqlite_connection(Path(sqlite_store._local_sqlite_path())) as conn:
        conn.execute(
            "UPDATE pipeline_runs SET passed_jobs=1, rejected_jobs=0 WHERE run_id='run-detail'"
        )
        conn.execute(
            """UPDATE run_stage_executions SET status='succeeded', passed_count=1,
                      progress_completed=1, progress_total=1 WHERE run_id='run-detail' AND stage_id='screening'"""
        )
        conn.execute(
            """INSERT INTO run_job_stage_results
               (run_job_id, stage_id, status, outcome_code, reason_code, evidence_json)
               VALUES (?, 'screening', 'rejected', 'screened_out', 'missing_skill', '{}')""",
            (run_job_ids[0],),
        )
        conn.commit()

    detail = sqlite_store.get_run_detail("run-detail")

    assert detail is not None
    assert detail["input"]["original_filename"] == "jobs.json"
    assert detail["input"]["candidate_profile_name"] == "Product Data Specialist"
    assert detail["capabilities"]["inspect"] is True
    assert len(detail["stages"]) == 6
    screening = next(stage for stage in detail["stages"] if stage["stage_id"] == "screening")
    assert screening["results_available"] is True
    assert detail["integrity_warnings"][0]["code"] == "run_count_mismatch"


def test_job_query_and_export_share_exhaustive_result_predicate() -> None:
    run_job_ids = _create_normalized_run_with_jobs(
        "run-results",
        [
            {"title": "beta", "company": "Z", "job_url": "https://example.com/2"},
            {"title": "Alpha", "company": "A", "job_url": "https://example.com/1"},
            {"title": "Gamma", "company": "G", "job_url": "https://example.com/3"},
            {"title": "Delta", "company": "D", "job_url": "https://example.com/4"},
        ],
    )
    statuses = ["passed", "rejected", "pending", "skipped"]
    with sqlite_store._sqlite_connection(Path(sqlite_store._local_sqlite_path())) as conn:
        for run_job_id, status in zip(run_job_ids, statuses):
            evidence = {"skip_is_terminal_rejection": status == "skipped"}
            conn.execute(
                """INSERT INTO run_job_stage_results
                   (run_job_id, stage_id, status, outcome_code, reason_code, evidence_json)
                   VALUES (?, 'screening', ?, ?, ?, ?)""",
                (run_job_id, status, f"outcome-{status}", f"reason-{status}", json.dumps(evidence)),
            )
        conn.commit()

    page = sqlite_store.query_run_jobs(
        "run-results", stage="screening", result_bucket="all", page=1, page_size=10
    )
    rejected = sqlite_store.query_run_jobs(
        "run-results", stage="screening", result_bucket="rejected", page=1, page_size=10
    )
    exported = list(
        sqlite_store.iter_run_jobs_for_export(
            "run-results", stage="screening", result_bucket="rejected"
                )
            )

    assert [row["title"] for row in page["items"]] == ["Alpha", "beta", "Delta"]
    assert page["total_evaluated"] == 3
    assert page["passed"] == 1 and page["rejected"] == 2
    assert [row["run_job_id"] for row in rejected["items"]] == [
        row["run_job_id"] for row in exported
    ]
    assert all(row["result_bucket"] == "rejected" for row in exported)

def test_binary_idempotent_action_replays_exact_bytes_and_metadata() -> None:
    reserved = sqlite_store.reserve_idempotent_action("backup", "key-1", "request-sha")
    sqlite_store.complete_idempotent_binary_action(
        reserved["action_id"],
        b"PK\x03\x04payload",
        media_type="application/zip",
        filename="fitcv-synonyms.zip",
    )

    replay = sqlite_store.reserve_idempotent_action("backup", "key-1", "request-sha")

    assert replay["binary_response"] == {
        "content": b"PK\x03\x04payload",
        "media_type": "application/zip",
        "filename": "fitcv-synonyms.zip",
        "checksum": hashlib.sha256(b"PK\x03\x04payload").hexdigest(),
    }


def test_list_run_structured_jobs_is_not_truncated_at_fifty() -> None:
    jobs = [{"title": f"Job {index:03d}"} for index in range(55)]
    _create_normalized_run_with_jobs("run-many", jobs)

    assert len(sqlite_store.list_run_structured_jobs("run-many")) == 55

def test_list_run_structured_jobs_projects_canonical_bookmark_state() -> None:
    run_job_id = _create_normalized_run_with_jobs(
        "run-structured-bookmark", [{"title": "Bookmarked Job"}]
    )[0]
    sqlite_store.set_bookmark(run_job_id)

    rows = sqlite_store.list_run_structured_jobs("run-structured-bookmark")

    assert rows[0]["run_job_id"] == run_job_id
    assert rows[0]["bookmarked"] is True


def test_cv_versions_are_immutable_and_download_verifies_checksum() -> None:
    run_job_id = _create_normalized_run_with_jobs("run-cv-normalized", [{"title": "CV Job"}])[0]
    content = b"# Generated CV\n"
    checksum = __import__("hashlib").sha256(content).hexdigest()
    sqlite_store.insert_cv_version_row(
        {
            "version_id": "cv-1",
            "run_job_id": run_job_id,
            "ordinal": 1,
            "generation_status": "generated",
            "filename": "cv.md",
            "media_type": "text/markdown; charset=utf-8",
            "content_blob": content,
            "content_length": len(content),
            "content_checksum": checksum,
            "created_at": "2026-07-20T10:00:00+00:00",
        }
    )
    sqlite_store.insert_cv_evaluation_row(
        {
            "cv_evaluation_id": "eval-1",
            "cv_version_id": "cv-1",
            "status": "succeeded",
            "fit_classification": "stretch",
            "reason": "Close fit",
            "is_current": True,
        }
    )
    sqlite_store.insert_cv_review_event(
        {
            "review_event_id": "review-1",
            "cv_version_id": "cv-1",
            "cv_evaluation_id": "eval-1",
            "from_state": "none",
            "to_state": "stretch",
            "actor": "system",
            "created_at": "2026-07-20T10:01:00+00:00",
        }
    )

    versions = sqlite_store.list_cv_versions(run_job_id)
    download = sqlite_store.get_cv_download("cv-1")

    assert versions[0]["evaluation"]["fit_classification"] == "stretch"
    assert versions[0]["review_state"] == "stretch"
    assert download is not None and download["content"] == content
    with pytest.raises(sqlite3.IntegrityError):
        sqlite_store.insert_cv_version_row(
            {"version_id": "cv-1", "generation_status": "pending"}
        )

    with sqlite_store._sqlite_connection(Path(sqlite_store._local_sqlite_path())) as conn:
        conn.execute("UPDATE cv_versions SET content_blob=? WHERE version_id='cv-1'", (b"tampered",))
        conn.commit()
    with pytest.raises(ValueError, match="artifact_integrity_mismatch"):
        sqlite_store.get_cv_download("cv-1")


def test_cv_regeneration_reservation_is_idempotent_and_blocks_concurrent_action() -> None:
    run_job_id = _create_normalized_run_with_jobs("run-cv-reserve", [{"title": "CV Job"}])[0]
    snapshot = {"job": {"title": "CV Job"}, "profile": {"name": "Candidate"}, "settings": {}}

    reserved = sqlite_store.reserve_cv_regeneration(
        run_job_id,
        version_id="cv-reserved-1",
        idempotency_key="idem-1",
        action_id="action-1",
        input_snapshot=snapshot,
    )
    replayed = sqlite_store.reserve_cv_regeneration(
        run_job_id,
        version_id="cv-reserved-other",
        idempotency_key="idem-1",
        action_id="action-other",
        input_snapshot=snapshot,
    )

    assert reserved["generation_status"] == "pending"
    assert replayed["version_id"] == "cv-reserved-1"
    assert replayed["idempotent_replay"] is True
    with pytest.raises(ValueError, match="cv_regeneration_not_allowed:cv-reserved-1"):
        sqlite_store.reserve_cv_regeneration(
            run_job_id,
            version_id="cv-reserved-2",
            idempotency_key="idem-2",
            action_id="action-2",
            input_snapshot=snapshot,
        )


def test_cv_regeneration_completion_preserves_parent_and_creates_new_checksum() -> None:
    run_job_id = _create_normalized_run_with_jobs("run-cv-complete", [{"title": "CV Job"}])[0]
    sqlite_store.insert_cv_version_row(
        {
            "version_id": "cv-parent",
            "run_job_id": run_job_id,
            "generation_status": "generated",
            "content_blob": b"# Parent\n",
            "created_at": "2026-07-20T10:00:00+00:00",
        }
    )
    sqlite_store.reserve_cv_regeneration(
        run_job_id,
        version_id="cv-child",
        parent_cv_version_id="cv-parent",
        idempotency_key="idem-child",
        action_id="action-child",
        input_snapshot={"job": {"title": "CV Job"}},
    )

    sqlite_store.update_cv_version(
        "cv-child",
        generation_status="generated",
        content=b"# Child\n",
        metadata={"fit_classification": "strong", "generator_id": "canonical"},
    )

    versions = sqlite_store.list_cv_versions(run_job_id)
    child = next(row for row in versions if row["version_id"] == "cv-child")
    parent = next(row for row in versions if row["version_id"] == "cv-parent")
    assert child["parent_cv_version_id"] == "cv-parent"
    assert child["content_checksum"] != parent["content_checksum"]
    assert sqlite_store.get_cv_download("cv-parent")["content"] == b"# Parent\n"
    assert sqlite_store.get_cv_download("cv-child")["content"] == b"# Child\n"


def test_process_event_cursor_pages_forward_without_deletion() -> None:
    from fitcv_cp.models import build_process_event

    for index in range(3):
        sqlite_store.append_process_event(
            build_process_event(
                process_type="pipeline",
                process_id="run-cursor",
                operation=f"step-{index}",
                state="progress",
                level="info",
                message=f"event {index}",
                event_id=f"event-{index}",
                recorded_at=datetime.datetime(2026, 7, 20, 10, index, tzinfo=datetime.timezone.utc),
            )
        )

    first = sqlite_store.get_process_events("pipeline", "run-cursor", limit=2)
    second = sqlite_store.get_process_events(
        "pipeline", "run-cursor", limit=2, cursor=first["next_cursor"]
    )
    reloaded = sqlite_store.get_process_events("pipeline", "run-cursor", limit=10)

    assert [event.event_id for event in first["events"]] == ["event-0", "event-1"]
    assert [event.event_id for event in second["events"]] == ["event-2"]
    assert second["next_cursor"] is None
    assert len(reloaded["events"]) == 3


def test_debug_bundle_availability_uses_persisted_run_evidence() -> None:
    run = _make_run("run-debug")
    sqlite_store.insert_run(run)
    assert sqlite_store.get_debug_bundle_availability(run.run_id)["status"] == "not_ready"

    sqlite_store.update_run_cv_generation_debug(run.run_id, '{"debug_records": []}')
    available = sqlite_store.get_debug_bundle_availability(run.run_id)
    assert available["status"] == "available"


def test_insert_run_with_snapshot_creates_atomic_normalized_bundle() -> None:
    run = _make_run("run-trigger-bundle")
    run.jobs_input_json = json.dumps(
        [{"title": "One", "job_url": "https://example.com/one"}]
    )
    run.jobs_input_manifest_json = json.dumps({"source_filenames": ["jobs.json"]})
    run.candidate_profile_json = json.dumps({"name": "Candidate"})
    run.candidate_profile_source = "candidate-product-data"
    run.effective_settings_json = json.dumps({"pipeline": {"final_top_n": 10}})

    sqlite_store.insert_run(run)

    detail = sqlite_store.get_run_detail(run.run_id)
    assert detail is not None
    assert detail["input"]["record_count"] == 1
    assert len(detail["stages"]) == 6
    assert sqlite_store.query_run_jobs(run.run_id)["total"] == 1


def test_insert_run_persists_explicit_run_name() -> None:
    run = _make_run("run-named")
    run.run_name = "Senior data product search"
    run.jobs_input_json = json.dumps(
        [{"title": "One", "job_url": "https://example.com/one"}]
    )
    run.jobs_input_manifest_json = json.dumps({"source_filenames": ["jobs.json"]})
    run.candidate_profile_json = json.dumps({"name": "Candidate"})
    run.effective_settings_json = "{}"

    sqlite_store.insert_run(run)

    assert sqlite_store.get_run_detail(run.run_id)["run_name"] == "Senior data product search"


def test_insert_run_uses_original_upload_metadata_from_manifest() -> None:
    run = _make_run("run-upload-metadata")
    run.jobs_input_json = json.dumps(
        [{"title": "One", "job_url": "https://example.com/one"}]
    )
    run.jobs_input_manifest_json = json.dumps(
        {
            "source_filenames": ["original.jsonl"],
            "media_type": "application/x-ndjson",
            "byte_length": 123,
            "sha256": "original-sha256",
        }
    )
    run.candidate_profile_json = json.dumps({"name": "Candidate"})
    run.effective_settings_json = "{}"

    sqlite_store.insert_run(run)

    input_resource = sqlite_store.get_run_detail(run.run_id)["input"]
    assert input_resource["original_filename"] == "original.jsonl"
    assert input_resource["media_type"] == "application/x-ndjson"
    assert input_resource["byte_length"] == 123
    assert input_resource["sha256"] == "original-sha256"


def test_insert_run_rejects_empty_snapshot_without_creating_run() -> None:
    run = _make_run("run-empty")
    run.jobs_input_json = "[]"
    run.candidate_profile_json = "{}"
    run.effective_settings_json = "{}"

    with pytest.raises(ValueError, match="jobs_input_empty"):
        sqlite_store.insert_run(run)

    assert sqlite_store.get_run(run.run_id) is None


def test_persist_pipeline_snapshot_maps_stage_aliases_and_job_outcomes() -> None:
    run_job_id = _create_normalized_run_with_jobs(
        "run-snapshot", [{"title": "Analyst", "job_url": "https://example.com/1"}]
    )[0]
    summary = {
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist"],
        "last_completed_stage": "shortlist",
        "stage_transition_artifacts": {
            "stages": {
                "enrich": {"status": "completed", "output_counts": {"enriched_jobs": 1}},
                "rule_filter": {"status": "completed", "output_counts": {"passed": 1}},
                "shortlist": {"status": "completed", "output_counts": {"shortlisted": 1}},
            }
        },
        "export_results": [
            {
                "job_url": "https://example.com/1",
                "job_outcome": {
                    "job_key": "input:0",
                    "stage": "ranking",
                    "outcome": "skipped",
                    "reason_code": "not_selected_in_final_ranking",
                    "evidence_ref": {"artifact": "ranking.json"},
                },
            }
        ],
    }

    sqlite_store.persist_pipeline_snapshot(
        "run-snapshot",
        summary,
        run_status=RunStatus.RUNNING,
        snapshot_at=datetime.datetime(2026, 7, 20, 12, tzinfo=datetime.timezone.utc),
    )

    stages = {row["stage_id"]: row for row in sqlite_store.list_run_stages("run-snapshot")}
    assert stages["enrichment"]["status"] == "succeeded"
    assert stages["screening"]["status"] == "succeeded"
    assert stages["shortlisting"]["status"] == "succeeded"
    with sqlite_store._sqlite_connection(Path(sqlite_store._local_sqlite_path())) as conn:
        rows = conn.execute(
            "SELECT stage_id, status FROM run_job_stage_results WHERE run_job_id=? ORDER BY stage_id",
            (run_job_id,),
        ).fetchall()
    assert ("ranking", "skipped") in rows


def test_insert_run_with_snapshot_creates_atomic_normalized_bundle() -> None:
    run = _make_run("run-trigger-bundle")
    run.jobs_input_json = json.dumps(
        [{"title": "One", "job_url": "https://example.com/one"}]
    )
    run.jobs_input_manifest_json = json.dumps({"source_filenames": ["jobs.json"]})
    run.candidate_profile_json = json.dumps({"name": "Candidate"})
    run.candidate_profile_source = "candidate-product-data"
    run.effective_settings_json = json.dumps({"pipeline": {"final_top_n": 10}})

    sqlite_store.insert_run(run)

    detail = sqlite_store.get_run_detail(run.run_id)
    assert detail is not None
    assert detail["input"]["record_count"] == 1
    assert len(detail["stages"]) == 6
    assert sqlite_store.query_run_jobs(run.run_id)["total"] == 1


def test_insert_run_rejects_empty_snapshot_without_creating_run() -> None:
    run = _make_run("run-empty")
    run.jobs_input_json = "[]"
    run.candidate_profile_json = "{}"
    run.effective_settings_json = "{}"

    with pytest.raises(ValueError, match="jobs_input_empty"):
        sqlite_store.insert_run(run)

    assert sqlite_store.get_run(run.run_id) is None


def test_persist_pipeline_snapshot_maps_stage_aliases_and_job_outcomes() -> None:
    run_job_id = _create_normalized_run_with_jobs(
        "run-snapshot", [{"title": "Analyst", "job_url": "https://example.com/1"}]
    )[0]
    summary = {
        "total_jobs": 1,
        "passed_filter": 1,
        "ranked": 1,
        "cvs_generated": 0,
        "completed_stages": ["normalize", "enrich", "rule_filter", "shortlist"],
        "last_completed_stage": "shortlist",
        "stage_transition_artifacts": {
            "stages": {
                "enrich": {"status": "completed", "output_counts": {"enriched_jobs": 1}},
                "rule_filter": {"status": "completed", "output_counts": {"passed": 1}},
                "shortlist": {"status": "completed", "output_counts": {"shortlisted": 1}},
            }
        },
        "export_results": [
            {
                "job_url": "https://example.com/1",
                "job_outcome": {
                    "job_key": "input:0",
                    "stage": "ranking",
                    "outcome": "skipped",
                    "reason_code": "not_selected_in_final_ranking",
                    "evidence_ref": {"artifact": "ranking.json"},
                },
            }
        ],
    }

    sqlite_store.persist_pipeline_snapshot(
        "run-snapshot",
        summary,
        run_status=RunStatus.RUNNING,
        snapshot_at=datetime.datetime(2026, 7, 20, 12, tzinfo=datetime.timezone.utc),
    )

    stages = {row["stage_id"]: row for row in sqlite_store.list_run_stages("run-snapshot")}
    assert stages["enrichment"]["status"] == "succeeded"
    assert stages["screening"]["status"] == "succeeded"
    assert stages["shortlisting"]["status"] == "succeeded"
    with sqlite_store._sqlite_connection(Path(sqlite_store._local_sqlite_path())) as conn:
        rows = conn.execute(
            "SELECT stage_id, status FROM run_job_stage_results WHERE run_job_id=? ORDER BY stage_id",
            (run_job_id,),
        ).fetchall()
    assert ("ranking", "skipped") in rows
