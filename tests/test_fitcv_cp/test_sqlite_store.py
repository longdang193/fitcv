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




