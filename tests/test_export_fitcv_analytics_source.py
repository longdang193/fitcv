import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.export_fitcv_analytics_source import export_bundle, export_to_path
from scripts.fitcv_analytics import rebuild_analytics_bundle, write_analytics_sqlite


def _seed_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE pipeline_runs (
                run_id TEXT PRIMARY KEY, compatibility_json TEXT,
                created_at TEXT, cv_generation_debug_json TEXT
            );
            CREATE TABLE run_inputs (
                run_id TEXT, candidate_profile_id TEXT,
                candidate_profile_revision_id TEXT, candidate_profile_revision INTEGER,
                candidate_profile_schema_version TEXT, candidate_profile_checksum TEXT,
                candidate_profile_json TEXT, created_at TEXT
            );
            CREATE TABLE run_jobs (
                run_job_id TEXT PRIMARY KEY, run_id TEXT, source_fingerprint TEXT,
                source_snapshot_json TEXT, source_url TEXT, title TEXT, company TEXT
            );
            CREATE TABLE cv_versions (
                version_id TEXT PRIMARY KEY, run_job_id TEXT, run_id TEXT,
                ordinal INTEGER, generation_status TEXT, created_at TEXT,
                finished_at TEXT, content_checksum TEXT, content_length INTEGER
            );
            CREATE TABLE cv_review_events (
                review_event_id TEXT PRIMARY KEY, cv_version_id TEXT,
                actor TEXT, to_state TEXT, note TEXT, created_at TEXT
            );
            INSERT INTO pipeline_runs VALUES (
                'run-1', '{"cohort_id":"c1","cohort_type":"fixture"}',
                '2026-10-06T00:00:00Z',
                '{"records":[{"artifact_id":"cv-1","provider_call_count":2,"token_total":10,"api_key":"sk-live","access_token":"secret","render_acceptance":{"render_status":"pass","page_count":1,"page_fit_status":"pass","artifact_checksum":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","content_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","template_sha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","render_config_fingerprint":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","renderer_contract_version":"v1"}}]}'
            );
            INSERT INTO run_inputs VALUES (
                'run-1','profile-1','profile-1:1',1,'v1','profile-hash','{"name":"private"}',
                '2026-10-06T00:00:00Z'
            );
            INSERT INTO run_jobs VALUES (
                'job-1','run-1','posting-hash',
                '{"extraction_status":"valid","requirements":["python"]}',
                'https://example.test/job-1','Example job','Example Co'
            );
            INSERT INTO run_jobs VALUES (
                'job-2','run-1','posting-hash-2',
                '{"extraction_status":"valid-empty","requirements":[]}',
                'https://example.test/job-2','Retry job','Example Co'
            );
            INSERT INTO cv_versions VALUES (
                'cv-1','job-1','run-1',1,'generated','2026-10-06T00:01:00Z',
                '2026-10-06T00:02:00Z','artifact-hash',12
            );
            INSERT INTO cv_versions VALUES (
                'cv-2','job-2','run-1',2,'generation_failed','2026-10-06T00:04:00Z',
                '2026-10-06T00:05:00Z',NULL,NULL
            );
            INSERT INTO cv_review_events VALUES (
                'review-1','cv-1','reviewer','approved','credential=do-not-export','2026-10-06T00:03:00Z'
            );
            """
        )
        connection.execute(
            "UPDATE pipeline_runs SET compatibility_json=?",
            (json.dumps({
                "cohort_id": "c1",
                "cohort_type": "fixture",
                "cv_generation_debug_json": json.dumps({
                    "accepted_artifact_events": [{
                        "artifact_id": "cv-1",
                        "provider_call_count": 2,
                        "token_total": 10,
                        "render_acceptance": {
                            "render_status": "pass",
                            "page_count": 1,
                            "page_fit_status": "pass",
                            "artifact_checksum": "a" * 64,
                            "content_sha256": "b" * 64,
                            "template_sha256": "c" * 64,
                            "render_config_fingerprint": "d" * 64,
                            "renderer_contract_version": "v1",
                        },
                    }],
                    "api_key": "sk-live",
                }),
            }),),
        )
        connection.commit()


def _files_digest(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in path.parent.glob(path.name + "*")
        if item.is_file()
    }


def test_export_is_replayable_sanitized_and_non_mutating(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    before = _files_digest(database)

    bundle = export_bundle(database, source_commit="head")
    after = _files_digest(database)

    assert before == after
    encoded = json.dumps(bundle, sort_keys=True)
    assert "sk-live" not in encoded
    assert "secret" not in encoded
    assert "credential=do-not-export" not in encoded
    assert bundle["sources"]["accepted_artifact"][0]["artifact_id"] == "cv-1"
    assert bundle["sources"]["posting_inventory"][1]["extraction_status"] == "valid-empty"
    assert bundle["sources"]["render_proof"][0]["render_proof_id"] == "cv-1:render"
    assert bundle["sources"]["candidate_profile_revision"][0]["candidate_profile_revision"] == 1
    assert json.dumps(bundle, sort_keys=True, separators=(",", ":")) == json.dumps(
        export_bundle(database, source_commit="head"), sort_keys=True, separators=(",", ":")
    )
    with pytest.raises(ValueError, match="output_aliases_database"):
        export_to_path(database, database, source_commit="head")

    replay = rebuild_analytics_bundle(
        bundle,
        source_commit=bundle["source_commit"],
        declared_input_fingerprint=bundle["input_fingerprint"],
        ingested_at="ignored-for-material-digest",
    )
    job_rows = {row["run_job_id"]: row for row in replay["gold"]["gold_run_job_effort"]}
    assert job_rows["job-1"]["review_action_count"] == 1
    assert job_rows["job-1"]["provider_call_count"] == 2
    assert job_rows["job-1"]["token_total"] == 10
    assert job_rows["job-1"]["first_pass_success_count"] == 1
    assert job_rows["job-1"]["render_proof_count"] == 1
    assert {row["run_job_id"] for row in replay["gold"]["gold_run_job_effort"]} == {"job-1", "job-2"}
    semantic = replay["gold"]["gold_semantic_metric"]
    assert {row["metric_id"] for row in semantic} == {
        "acceptance_yield", "provider_calls_per_accepted_cv", "tokens_per_accepted_cv",
        "first_pass_success", "manual_effort", "verified_one_page_rate", "skill_demand",
        "evidence_gap",
    }

    projection = tmp_path / "analytics.sqlite3"
    write_analytics_sqlite(
        path=projection,
        artifacts=replay["gold"]["gold_cv_artifact"],
        run_jobs=replay["gold"]["gold_run_job_effort"],
        cohorts=replay["gold"]["gold_cohort_effort"],
        acceptance=replay["gold"]["gold_acceptance_state"],
        requirement_demand=replay["gold"]["gold_requirement_demand"],
        candidate_gaps=replay["gold"]["gold_candidate_gap"],
        optimization=replay["gold"]["gold_optimization_state"],
        semantic_metrics=semantic,
    )
    with sqlite3.connect(projection) as connection:
        metric_ids = {
            row[0] for row in connection.execute("SELECT DISTINCT metric_id FROM gold_semantic_metric")
        }
        assert len(metric_ids) == 8


def test_export_rejects_missing_path_and_hash_mismatch(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        export_bundle(tmp_path / "missing.sqlite3", source_commit="head")
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with pytest.raises(ValueError, match="source_hash_mismatch"):
        export_bundle(database, source_commit="head", expected_database_sha256="bad")


def test_export_fails_closed_for_live_wal_without_touching_sidecars(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute("CREATE TABLE t(value TEXT)")
    connection.execute("INSERT INTO t VALUES ('x')")
    connection.commit()
    sidecars_before = _files_digest(database)
    try:
        with pytest.raises(RuntimeError, match="checkpointed_database"):
            export_bundle(database, source_commit="head")
        assert _files_digest(database) == sidecars_before
    finally:
        connection.close()
