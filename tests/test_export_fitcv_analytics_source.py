import hashlib
import json
import os
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
                'https://user:password@example.test:not-a-port/job-1?access_token=sk-private&refresh_token=refresh#fragment-token','Example job','Example Co'
            );
            INSERT INTO run_jobs VALUES (
                'job-2','run-1','posting-hash-2',
                '{"extraction_status":"valid-empty","requirements":[]}',
                'https://example.test/job-2','Retry job','Example Co'
            );
            INSERT INTO cv_versions VALUES (
                'cv-1','job-1','run-1',1,'generated','2026-10-06T00:01:00Z',
                '2026-10-06T00:02:00Z','bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',12
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
                        "cv_generation_trace": {
                            "efficiency_summary": {
                                "provider_call_count": 2,
                                "token_usage": [{"total_tokens": 6}, {"prompt_tokens": 2, "completion_tokens": 2}],
                            }
                        },
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
    assert "user:password" not in encoded
    assert "access_token" not in encoded
    assert "refresh_token" not in encoded
    assert "fragment-token" not in encoded
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
    hardlink = tmp_path / "hardlink.json"
    os.link(database, hardlink)
    with pytest.raises(ValueError, match="output_aliases_database"):
        export_to_path(database, hardlink, source_commit="head")

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
    cohort = replay["gold"]["gold_cohort_effort"][0]
    assert cohort["verified_one_page_rate"] == 1.0
    assert cohort["render_proof_coverage"] == "complete"
    assert {row["run_job_id"] for row in replay["gold"]["gold_run_job_effort"]} == {"job-1", "job-2"}
    semantic = replay["gold"]["gold_semantic_metric"]
    assert {row["metric_id"] for row in semantic} == {
        "acceptance_yield", "provider_calls_per_accepted_cv", "tokens_per_accepted_cv",
        "first_pass_success", "manual_effort", "verified_one_page_rate", "skill_demand",
        "evidence_gap",
    }
    assert next(row for row in semantic if row["metric_id"] == "verified_one_page_rate")["value"] == 1.0

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


def test_export_collects_native_requirements_and_evaluation_gaps(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE run_jobs ADD COLUMN skills_json TEXT NOT NULL DEFAULT '[]'")
        connection.execute("UPDATE run_jobs SET skills_json=? WHERE run_job_id='job-1'", (json.dumps([{"canonical": "Python"}, {"canonical": "SQL"}]),))
        connection.execute("UPDATE run_inputs SET candidate_profile_checksum=NULL WHERE run_id='run-1'")
        connection.execute("UPDATE run_jobs SET source_snapshot_json=? WHERE run_job_id='job-1'", (json.dumps({"extraction_status": "valid"}),))
        connection.execute(
            """
            CREATE TABLE cv_evaluations (
                cv_evaluation_id TEXT PRIMARY KEY,
                cv_version_id TEXT,
                status TEXT,
                evidence_json TEXT,
                is_current INTEGER
            )
            """
        )
        connection.execute(
            "INSERT INTO cv_evaluations VALUES (?, ?, ?, ?, ?)",
            ("evaluation-1", "cv-1", "succeeded", json.dumps({"requirement_coverage": [{"requirement": "Python", "selected_support": "unsupported"}]}), 1),
        )
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    assert any(row["requirement"] == "Python" for row in bundle["sources"]["posting_requirement"])
    assert any(row["gap_category"] == "missing_evidence" for row in bundle["sources"]["candidate_gap"])
    assert any(row["gap_category"] == "unevaluated" and row["requirement"] == "SQL" for row in bundle["sources"]["candidate_gap"])
    gap = bundle["sources"]["candidate_gap"][0]
    assert gap["candidate_profile_id"] == "profile-1"
    assert gap["candidate_profile_revision"] == 1
    profile = bundle["sources"]["candidate_profile_revision"][0]
    assert gap["candidate_profile_fingerprint"] == profile["candidate_profile_fingerprint"]
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint=bundle["input_fingerprint"], ingested_at="now")
    assert replay["gold"]["gold_requirement_demand"]
    assert replay["gold"]["gold_candidate_gap"]


def test_export_separates_posting_identity_from_processing_and_keeps_orphan_attempts(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO run_jobs VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("job-3", "run-1", "posting-hash", json.dumps({"extraction_status": "valid", "requirements": ["Python"]}), "https://example.test/job-3", "Duplicate processing", "Example Co"),
        )
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        payload["cv_generation_debug_json"] = json.dumps({
            "debug_records": [{"run_job_id": "job-3", "status": "generation_failed", "provider_call_count": 3}],
        })
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    inventories = [row for row in bundle["sources"]["posting_inventory"] if row["run_job_id"] in {"job-1", "job-3"}]
    assert {row["posting_id"] for row in inventories} == {"posting-hash"}
    assert {row["processing_id"] for row in inventories} == {"job-1", "job-3"}
    orphan = next(row for row in bundle["sources"]["generation_attempt"] if row["run_job_id"] == "job-3")
    assert orphan["status"] == "generation_failed"
    assert next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-3")["provider_call_count"] == 3


def test_export_preserves_native_requirement_instance_identity(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE run_jobs ADD COLUMN skills_json TEXT NOT NULL DEFAULT '[]'")
        connection.execute(
            "UPDATE run_jobs SET source_snapshot_json=? WHERE run_job_id='job-1'",
            (json.dumps({"extraction_status": "valid", "requirements": [{"requirement": "Python", "requirement_instance_id": "native-req-1"}]}),),
        )
        connection.execute(
            """
            CREATE TABLE cv_evaluations (
                cv_evaluation_id TEXT PRIMARY KEY,
                cv_version_id TEXT,
                status TEXT,
                evidence_json TEXT,
                is_current INTEGER
            )
            """
        )
        connection.execute(
            "INSERT INTO cv_evaluations VALUES (?, ?, ?, ?, ?)",
            ("evaluation-1", "cv-1", "succeeded", json.dumps({"requirement_coverage": [{"requirement": "Python", "requirement_instance_id": "native-req-1", "selected_support": "unsupported"}]}), 1),
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    requirements = [row for row in bundle["sources"]["posting_requirement"] if row["posting_id"] == "posting-hash"]
    assert requirements[0]["requirement_instance_id"] == "native-req-1"
    assert not any(row["gap_category"] == "unevaluated" for row in bundle["sources"]["candidate_gap"])


def test_export_rejects_missing_path_and_hash_mismatch(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        export_bundle(tmp_path / "missing.sqlite3", source_commit="head")
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with pytest.raises(ValueError, match="source_hash_mismatch"):
        export_bundle(database, source_commit="head", expected_database_sha256="bad")


def test_export_preserves_native_attempt_count(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["attempt_count"] = 2
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    assert bundle["sources"]["generation_attempt"][0]["attempt_count"] == 2


def test_export_keeps_acceptance_proof_artifact_specific(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO cv_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("cv-3", "job-1", "run-1", 3, "generated", "2026-10-06T00:06:00Z", "2026-10-06T00:07:00Z", "artifact-hash-3", 12),
        )
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["run_job_id"] = "job-1"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    assert [row["artifact_id"] for row in bundle["sources"]["accepted_artifact"]] == ["cv-1"]


def test_export_redacts_malformed_url_without_leaking_fragment_or_credentials(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        for source_url in (
            "https://user:password@example.test:not-a-port/job?refresh_token=secret#jwt",
            "https:///job?access_token=PRIVATE#JWT",
            "https://?api_key=PRIVATE#JWT",
            "https:/job?access_token=PRIVATE#JWT",
            "https:example.test/job?access_token=PRIVATE#JWT",
            " https:/job?access_token=PRIVATE#JWT",
            "//user:PRIVATE@example.test/job?access_token=PRIVATE#JWT",
            "/job?access_token=PRIVATE#JWT",
            "www.example.test/job?api_key=PRIVATE",
            "https://example.test/job?api.key=PRIVATE",
            "https://example.test/job?api+key=PRIVATE",
            "https://example.test/job?X-API-Key=PRIVATE",
            "https://example.test/job?private_key=PRIVATE",
            "/job#access_token=PRIVATE",
            "https://user:PRIVATE",
            "https://example.test/job?api-key=PRIVATE",
        ):
            connection.execute(
                "UPDATE run_jobs SET source_url=? WHERE run_job_id='job-1'",
                (source_url,),
            )
            connection.commit()
            encoded = json.dumps(export_bundle(database, source_commit="head"), sort_keys=True)
            assert "user:password" not in encoded
            assert "refresh_token" not in encoded
            assert "access_token" not in encoded
            assert "api_key" not in encoded
            assert "PRIVATE" not in encoded
            assert "secret#jwt" not in encoded
            assert "#JWT" not in encoded


def test_export_rejects_incomplete_primary_token_source_and_nested_cardinality(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["token_usage_status"] = "incomplete"
        event["token_usage"] = [{"total_tokens": "bad"}]
        event["provider_call_count"] = 2
        event["cv_generation_trace"]["efficiency_summary"].update(
            {"token_usage_status": "available", "token_usage": [{"total_tokens": 9}]}
        )
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None


@pytest.mark.parametrize("primary", [{"usage": {"total_tokens": "bad"}}, {"token_usage": None}])
def test_export_does_not_fall_through_primary_usage(tmp_path: Path, primary: dict[str, object]) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event.pop("cv_generation_trace", None)
        event.update(primary)
        event["cv_generation_trace"] = {"efficiency_summary": {"provider_call_count": 1, "token_usage": [{"total_tokens": 9}]}}
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None


def test_export_uses_nested_usage_source_cardinality(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["provider_call_count"] = 1
        event["cv_generation_trace"]["efficiency_summary"]["provider_call_count"] = 2
        event["cv_generation_trace"]["efficiency_summary"]["token_usage"] = [{"total_tokens": 9}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None


def test_export_rejects_null_nested_provider_count(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["provider_call_count"] = None
        event["cv_generation_trace"]["efficiency_summary"]["provider_call_count"] = 2
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("provider_call_count") is None


def test_export_rejects_malformed_acceptance_event_identity_and_flag(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["artifact_id"] = ["bad"]
        event["version_id"] = "cv-1"
        event["accepted"] = "false"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}
    assert metrics["acceptance_yield"]["value"] is None
    assert metrics["verified_one_page_rate"]["value"] is None


def test_export_binds_conflicting_acceptance_aliases_to_one_invalid_version(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["artifact_id"] = "cv-1"
        event["version_id"] = "cv-2"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")

    artifacts = bundle["sources"].get("accepted_artifact", [])
    assert [item["artifact_id"] for item in artifacts] == ["cv-2"]
    assert artifacts[0]["validity"] == "invalid"


def test_export_rejection_status_blocks_acceptance_metrics(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["status"] = "rejected"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_preserves_unbound_invalid_acceptance_evidence(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [{"run_job_id": "job-1", "accepted": "false"}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_reconciles_rejection_with_positive_acceptance_event(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["debug_records"] = [{"artifact_id": "cv-1", "accepted_outcome": False}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_rejects_acceptance_lineage_from_other_run_job(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["run_job_id"] = "job-2"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_render_proof_must_match_stored_content_checksum(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE cv_versions SET content_checksum=? WHERE version_id='cv-1'",
            ("e" * 64,),
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert replay["gold"]["gold_run_job_effort"][0]["render_proof_count"] == 0
    assert metrics["verified_one_page_rate"]["value"] is None


def test_export_blocks_acceptance_debug_from_other_pipeline_run(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs WHERE run_id='run-1'").fetchone()[0])
        connection.execute(
            "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)",
            ("run-2", json.dumps(payload), "2026-10-06T00:10:00Z", None),
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "valid"
    assert bundle["sources"]["accepted_artifact"][1]["validity"] == "invalid"
    assert bundle["sources"]["accepted_artifact"][1]["run_id"] == "run-2"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_acceptance_when_referenced_run_job_is_missing(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM run_jobs WHERE run_job_id='job-1'")
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_acceptance_when_all_run_jobs_are_missing(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM run_jobs")
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_acceptance_when_run_job_belongs_to_other_run(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE run_jobs SET run_id='run-2' WHERE run_job_id='job-1'")
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_acceptance_when_event_run_id_conflicts(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["run_id"] = "run-2"
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("event_order", [("job-1", "job-2"), ("job-2", "job-1")])
def test_export_blocks_conflicting_acceptance_event_run_jobs(tmp_path: Path, event_order: tuple[str, str]) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [
            {"artifact_id": "cv-1", "run_job_id": run_job_id, "accepted": True}
            for run_job_id in event_order
        ]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_mixed_source_conflicting_acceptance_run_jobs(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [{"artifact_id": "cv-1", "run_job_id": "job-2", "accepted": True}]
        debug["accepted_cv_effort"] = [{"artifact_id": "cv-1", "run_job_id": "job-1", "accepted_outcome": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_consumes_valid_acceptance_aliases_once(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_cv_effort"] = [{"artifact_id": "cv-1", "run_job_id": "job-1", "accepted_outcome": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert not any(item["artifact_id"].startswith("unresolved:") for item in bundle["sources"]["accepted_artifact"])
    assert metrics["acceptance_yield"]["value"] == 0.5


@pytest.mark.parametrize("events", [[None], [{"artifact_id": "cv-1"}, None]])
def test_export_retains_malformed_implicit_acceptance_events(tmp_path: Path, events: list[object]) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = events
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert any(item["validity"] == "invalid" for item in bundle["sources"]["accepted_artifact"])
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("container", [None, True, 1, "accepted", {"artifact_id": "cv-1"}])
def test_export_retains_malformed_acceptance_container(tmp_path: Path, container: object) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = container
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert any(item["validity"] == "invalid" for item in bundle["sources"]["accepted_artifact"])
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize(
    "nested_events",
    [
        [None, {"artifact_id": "unknown"}],
        [[{"artifact_id": "cv-1"}]],
        [{"artifact_id": "cv-1"}, []],
        {"artifact_id": "cv-1", "accepted_outcome": True},
    ],
)
def test_export_retains_nested_acceptance_evidence(tmp_path: Path, nested_events: object) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["debug_records"] = [{"accepted_artifact_events": nested_events}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert any(item["validity"] == "invalid" for item in bundle["sources"]["accepted_artifact"])
    assert metrics["acceptance_yield"]["value"] is None


def test_export_preserves_nested_implicit_acceptance_semantics(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["debug_records"] = [{"accepted_artifact_events": [{"artifact_id": "cv-1"}]}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert not any(item["validity"] == "invalid" for item in bundle["sources"]["accepted_artifact"])
    assert metrics["acceptance_yield"]["value"] == 0.5


def test_export_reconciles_nested_acceptance_rejection(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [{
            "artifact_id": "cv-1",
            "debug_records": [{"artifact_id": "cv-1", "accepted_outcome": False}],
        }]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_blocks_alternate_acceptance_with_foreign_run_id(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = []
        debug["debug_records"] = [{"artifact_id": "cv-1", "run_id": "run-2", "accepted_outcome": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("source_key", ["debug_records", "accepted_cv_effort", "cv_generation_trace"])
@pytest.mark.parametrize("invalid_field", ["run_id", "run_job_id", "artifact_version_id"])
def test_export_preserves_invalid_null_lineage_on_alternate_acceptance_paths(
    tmp_path: Path, source_key: str, invalid_field: str
) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = []
        debug[source_key] = [{"artifact_id": "cv-1", "accepted_outcome": True, invalid_field: None}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("source_key", ["debug_records", "accepted_cv_effort", "cv_generation_trace"])
def test_export_retains_unbound_alternate_acceptance_evidence(tmp_path: Path, source_key: str) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = []
        debug[source_key] = [{"artifact_id": None, "accepted_outcome": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    invalid = [item for item in bundle["sources"]["accepted_artifact"] if item["validity"] == "invalid"]
    assert invalid
    assert invalid[0]["run_id"] == "run-1"
    assert invalid[0]["cohort_id"] == "c1"
    assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("event", [{}, {"artifact_id": None}, {"artifact_id": "unknown"}, {"run_job_id": "job-2"}])
def test_export_retains_implicit_unbound_acceptance_event(tmp_path: Path, event: dict[str, object]) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [event]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    invalid = [item for item in bundle["sources"]["accepted_artifact"] if item["validity"] == "invalid"]
    assert invalid
    assert invalid[0]["run_id"] == "run-1"
    assert invalid[0]["cohort_id"] == "c1"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_keeps_foreign_artifact_acceptance_under_source_run(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)",
            ("run-2", json.dumps({"cohort_id": "c2", "cohort_type": "fixture"}), "2026-10-06T00:10:00Z", None),
        )
        connection.execute("UPDATE run_jobs SET run_id='run-2' WHERE run_job_id='job-2'")
        connection.execute("UPDATE cv_versions SET run_id='run-2' WHERE version_id='cv-2'")
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs WHERE run_id='run-1'").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [{"artifact_id": "cv-2", "accepted_outcome": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=? WHERE run_id='run-1'", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    invalid = [item for item in bundle["sources"]["accepted_artifact"] if item["validity"] == "invalid"]

    assert invalid
    assert invalid[0]["run_id"] == "run-1"
    assert invalid[0]["cohort_id"] == "c1"


def test_export_unbinds_foreign_job_acceptance_reference(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE run_jobs SET run_id='run-2' WHERE run_job_id='job-2'")
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = [{"run_job_id": "job-2", "accepted": True}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    invalid = [item for item in bundle["sources"]["accepted_artifact"] if item["validity"] == "invalid"]

    assert invalid
    assert invalid[0]["run_id"] == "run-1"
    assert invalid[0]["cohort_id"] == "c1"
    assert invalid[0]["run_job_id"].startswith("unbound:run-1:")


def test_export_preserves_same_identifier_acceptance_rejections_per_run(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"] = []
        debug["debug_records"] = [{"artifact_id": "unknown", "accepted_outcome": False}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=? WHERE run_id='run-1'", (json.dumps(payload),))
        run_two_payload = {
            "cohort_id": "c2",
            "cohort_type": "fixture",
            "cv_generation_debug_json": json.dumps({
                "debug_records": [{"artifact_id": "unknown", "accepted_outcome": False}],
            }),
        }
        connection.execute(
            "INSERT INTO pipeline_runs VALUES (?, ?, ?, ?)",
            ("run-2", json.dumps(run_two_payload), "2026-10-06T00:10:00Z", None),
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {
        (item["metric_id"], item["cohort_id"]): item
        for item in replay["gold"]["gold_semantic_metric"]
    }
    invalid = [item for item in bundle["sources"]["accepted_artifact"] if item["validity"] == "invalid"]

    assert {item["cohort_id"] for item in invalid} == {"c1", "c2"}
    assert metrics[("acceptance_yield", "c1")]["value"] is None
    assert metrics[("acceptance_yield", "c2")]["value"] is None


def test_export_preserves_job_rejection_when_job_has_multiple_versions(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["debug_records"] = [{"run_job_id": "job-1", "accepted_outcome": False}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.execute(
            "INSERT INTO cv_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("cv-3", "job-1", "run-1", 2, "generation_failed", "2026-10-06T00:06:00Z", "2026-10-06T00:07:00Z", None, None),
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_applies_run_job_rejection_to_artifact_acceptance(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["debug_records"] = [{"run_job_id": "job-1", "accepted_outcome": False}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()

    bundle = export_bundle(database, source_commit="head")
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}

    assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
    assert metrics["acceptance_yield"]["value"] is None


def test_export_preserves_acceptance_conflict_when_durability_is_missing(tmp_path: Path) -> None:
    for field, value in (("generation_status", "generation_failed"), ("content_checksum", None)):
        database = tmp_path / f"fitcv-{field}.sqlite3"
        _seed_database(database)
        with sqlite3.connect(database) as connection:
            connection.execute(f"UPDATE cv_versions SET {field}=? WHERE version_id='cv-1'", (value,))
            connection.commit()

        bundle = export_bundle(database, source_commit="head")
        replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
        metrics = {item["metric_id"]: item for item in replay["gold"]["gold_semantic_metric"]}
        assert bundle["sources"]["accepted_artifact"][0]["validity"] == "invalid"
        assert metrics["acceptance_yield"]["value"] is None


@pytest.mark.parametrize("attempt_count", [1.9, 10**400])
def test_export_rejects_fractional_and_oversized_attempt_counts(tmp_path: Path, attempt_count: object) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["attempt_count"] = attempt_count
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    generation = next(row for row in bundle["sources"]["generation_attempt"] if row["run_job_id"] == "job-1")
    assert generation["attempt_count"] == 0
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint=bundle["input_fingerprint"], ingested_at="now")
    effort = next(row for row in replay["gold"]["gold_run_job_effort"] if row["run_job_id"] == "job-1")
    assert effort["generation_attempt_coverage"] == "unavailable"


def test_export_rejects_explicit_null_attempt_count(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["attempt_count"] = None
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    generation = next(row for row in bundle["sources"]["generation_attempt"] if row["run_job_id"] == "job-1")
    assert generation["attempt_count"] == 0


def test_export_rejects_nested_null_attempt_count(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["cv_generation_trace"]["efficiency_summary"]["attempt_count"] = None
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    generation = next(row for row in bundle["sources"]["generation_attempt"] if row["run_job_id"] == "job-1")
    assert generation["attempt_count"] == 0


def test_export_uses_outer_provider_count_for_nested_usage(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        event = debug["accepted_artifact_events"][0]
        event["provider_call_count"] = 2
        event["cv_generation_trace"]["efficiency_summary"].pop("provider_call_count", None)
        event["cv_generation_trace"]["efficiency_summary"]["token_usage"] = [{"total_tokens": 9}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None


def test_export_allows_unmanaged_run_without_candidate_profile_identity(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE run_inputs SET candidate_profile_id=NULL, candidate_profile_revision_id=NULL, candidate_profile_revision=NULL, candidate_profile_checksum=NULL, candidate_profile_json=NULL"
        )
        connection.commit()

    bundle = export_bundle(database, source_commit="head")

    assert "candidate_profile_revision" not in bundle["sources"]
    requirement = bundle["sources"]["posting_requirement"][0]
    assert "candidate_profile_id" not in requirement
    assert "candidate_profile_revision" not in requirement


def test_export_redacts_nested_url_query_values(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE run_jobs SET source_url=? WHERE run_job_id='job-1'", ("https://example.test/job?next=https%3A%2F%2Fuser%3APRIVATE%40other.test%2Fpath%3Faccess_token%3DSECRET",))
        connection.commit()
    encoded = json.dumps(export_bundle(database, source_commit="head"), sort_keys=True)
    assert "PRIVATE" not in encoded
    assert "SECRET" not in encoded


def test_requirement_resolution_without_job_lineage_is_not_exported(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE requirement_resolutions (
                resolution_id TEXT PRIMARY KEY, candidate_profile_id TEXT, candidate_profile_revision TEXT,
                source_profile_fingerprint TEXT, resolution_key TEXT, requirement_instance_id TEXT,
                resolution_action TEXT, resolution_payload_json TEXT, actor TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE requirement_resolution_enqueue_intents (
                intent_id TEXT PRIMARY KEY, resolution_id TEXT, run_id TEXT, job_url TEXT,
                actor TEXT, note TEXT, idempotency_key TEXT, action_id TEXT, status TEXT,
                queue_job_id TEXT, error_message TEXT, created_at TEXT, updated_at TEXT
            );
            INSERT INTO requirement_resolutions VALUES ('resolution-1','profile-1','1','hash','key','job-1:0','RESOLVE_WITH_ANSWER','{}','actor','now','now');
            INSERT INTO requirement_resolution_enqueue_intents VALUES ('intent-1','resolution-1','run-1','https://example.test/not-a-job','actor',NULL,'idem','action','enqueued',NULL,NULL,'now','now');
            """
        )
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    assert not any(row["review_action_id"] == "resolution-1" for row in bundle["sources"].get("review_action", []))


@pytest.mark.parametrize(
    "token_usage",
    [[{"total_tokens": 6}, {}], [{"total_tokens": True}], [{"total_tokens": 1.9}], [{"total_tokens": "bad"}]],
)
def test_export_marks_invalid_token_telemetry_unavailable(tmp_path: Path, token_usage: list[dict[str, object]]) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["cv_generation_trace"]["efficiency_summary"]["token_usage"] = token_usage
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None
    replay = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint=bundle["input_fingerprint"], ingested_at="now")
    effort = next(row for row in replay["gold"]["gold_run_job_effort"] if row["run_job_id"] == "job-1")
    assert effort["token_total"] is None
    assert effort["token_coverage"] == "unavailable"


def test_export_marks_oversized_token_telemetry_unavailable(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    _seed_database(database)
    with sqlite3.connect(database) as connection:
        payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
        debug = json.loads(payload["cv_generation_debug_json"])
        debug["accepted_artifact_events"][0]["cv_generation_trace"]["efficiency_summary"]["token_usage"] = [{"total_tokens": 10**400}]
        payload["cv_generation_debug_json"] = json.dumps(debug)
        connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
        connection.commit()
    bundle = export_bundle(database, source_commit="head")
    provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
    assert provider.get("token_total") is None


def test_export_rejects_direct_and_aggregate_token_shortcuts(tmp_path: Path) -> None:
    cases = [
        ({"token_total": "10", "token_usage_status": "available"},),
        ({"token_total": 0, "token_usage_status": "not_run"},),
        ({"token_usage": {"total_tokens": 6}, "token_usage_status": "available"},),
    ]
    for index, (summary,) in enumerate(cases):
        database = tmp_path / f"fitcv-{index}.sqlite3"
        _seed_database(database)
        with sqlite3.connect(database) as connection:
            payload = json.loads(connection.execute("SELECT compatibility_json FROM pipeline_runs").fetchone()[0])
            debug = json.loads(payload["cv_generation_debug_json"])
            efficiency = debug["accepted_artifact_events"][0]["cv_generation_trace"]["efficiency_summary"]
            efficiency.pop("token_usage", None)
            efficiency.update(summary)
            payload["cv_generation_debug_json"] = json.dumps(debug)
            connection.execute("UPDATE pipeline_runs SET compatibility_json=?", (json.dumps(payload),))
            connection.commit()
        bundle = export_bundle(database, source_commit="head")
        provider = next(row for row in bundle["sources"]["provider_attempt"] if row["run_job_id"] == "job-1")
        assert provider.get("token_total") is None


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
