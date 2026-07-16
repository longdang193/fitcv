import datetime
import json
import sqlite3
import uuid
from pathlib import Path

import pytest

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
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        conn.execute(
            """
            INSERT INTO rule_filter_results (
                run_id,
                job_url,
                passed,
                reasons,
                filtered_at,
                marks_json,
                raw_job_fingerprint,
                source_job_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-filter",
                "https://example.com/job-1",
                1,
                json.dumps(["matched_required_skills"]),
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                json.dumps([{"code": "required_skill"}]),
                "fp-1",
                "https://example.com/job-1",
            ),
        )
        conn.commit()

    rows = sqlite_store.list_filter_results_for_run("run-filter")

    assert len(rows) == 1
    assert rows[0]["passed"] is True
    assert rows[0]["reasons"] == ["matched_required_skills"]
    assert rows[0]["marks"] == [{"code": "required_skill"}]


def test_local_sqlite_path_uses_control_plane_config_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FITCV_CP_SQLITE_PATH", raising=False)
    (tmp_path / "config" / "runtime").mkdir(parents=True)
    (tmp_path / "config" / "runtime" / "control_plane.yaml").write_text(
        "control_plane:\n"
        "  data_backend:\n"
        "    type: sqlite\n"
        "    sqlite:\n"
        f"      path: {tmp_path / 'from-config.sqlite3'}\n",
        encoding="utf-8",
    )

    assert sqlite_store._local_sqlite_path() == str(tmp_path / "from-config.sqlite3")


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
    recent_run.archived_at = now - datetime.timedelta(days=1)
    recent_run.archived_by = "admin"

    for run in (old_run, recent_run, active_run):
        sqlite_store.insert_run(run)

    summary = sqlite_store.delete_archived_runs(older_than_days=5)

    assert summary["deleted_count"] == 1
    assert sqlite_store.get_run("run-old") is None
    assert sqlite_store.get_run("run-recent") is not None
    assert sqlite_store.get_run("run-active") is not None






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


def test_list_filter_results_for_run_defaults_legacy_eligibility_columns() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        conn.execute(
            """
            INSERT INTO rule_filter_results (
                run_id, job_url, passed, reasons, filtered_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "run-legacy-filter",
                "https://example.com/legacy",
                1,
                "[]",
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    rows = sqlite_store.list_filter_results_for_run("run-legacy-filter")

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