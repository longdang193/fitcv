import datetime
import json
import sqlite3
from pathlib import Path

import pytest

from fitcv_cp import sqlite_store
from fitcv_cp.models import PipelineRun, RunStatus, build_process_event


def _run_payload(
    run_id: str,
    *,
    status: str = "succeeded",
    jobs: list[dict[str, object]] | None = None,
    completed_stages: list[str] | None = None,
    next_stage: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "run_id": run_id,
        "status": status,
        "triggered_by": "legacy-user",
        "trigger_source": "legacy-test",
        "jobs_path": "legacy-jobs.json",
        "config_path": "legacy-config.yaml",
        "created_at": "2026-09-05T10:00:00+00:00",
        "total_jobs": len(jobs or []),
        "passed_filter": 1 if jobs else 0,
        "rejected_jobs": max(0, len(jobs or []) - 1),
        "jobs_input_source": "upload",
        "jobs_input_json": json.dumps(jobs or [], ensure_ascii=False),
        "jobs_input_manifest_json": json.dumps({"source_filenames": ["legacy-jobs.json"]}),
        "completed_stages": completed_stages or [],
    }
    if next_stage is not None:
        payload["next_stage"] = next_stage
    return payload


def _make_canonical_run(run_id: str) -> PipelineRun:
    return PipelineRun(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        triggered_by="canonical",
        trigger_source="canonical-test",
        jobs_path="canonical.json",
        config_path="canonical.yaml",
        created_at=datetime.datetime(2026, 9, 5, 9, tzinfo=datetime.timezone.utc),
        total_jobs=0,
        passed_filter=0,
        rejected_jobs=0,
    )


@pytest.fixture
def migration_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    with sqlite3.connect(database_path) as conn:
        sqlite_store._configure_sqlite_connection(conn)
        sqlite_store._ensure_control_plane_schema(conn)
    sqlite_store.insert_run(_make_canonical_run("canonical-conflict"))
    sqlite_store.append_process_event(
        build_process_event(
            process_type="pipeline",
            process_id="canonical-conflict",
            operation="screening",
            state="recorded",
            level="info",
            message="canonical message",
            payload={"source": "canonical"},
            event_id="event-conflict",
            recorded_at=datetime.datetime(2026, 9, 5, 10, tzinfo=datetime.timezone.utc),
        )
    )
    sqlite_store.append_process_event(
        build_process_event(
            process_type="pipeline",
            process_id="canonical-conflict",
            operation="screening",
            state="recorded",
            level="info",
            message="equal message",
            payload={"source": "equal"},
            event_id="event-equal",
            recorded_at=datetime.datetime(2026, 9, 5, 10, tzinfo=datetime.timezone.utc),
        )
    )
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "CREATE TABLE local_pipeline_runs (run_id TEXT PRIMARY KEY, run_json TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE local_pipeline_run_events (
                run_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        complete_jobs = [
            {"title": "Analyst", "job_url": "https://jobs.example/1", "skills": ["sql"]},
            {"title": "Analyst", "job_url": "https://jobs.example/1", "skills": ["python"]},
        ]
        rows = [
            ("legacy-complete", _run_payload("legacy-complete", jobs=complete_jobs, completed_stages=["normalize", "rule_filter"])),
            ("legacy-incomplete", _run_payload("legacy-incomplete", status="running", completed_stages=["normalize"], next_stage="screening")),
            ("legacy-malformed", "{malformed-run-json"),
            ("canonical-conflict", _run_payload("canonical-conflict", status="failed")),
        ]
        for run_id, payload in rows:
            raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
            conn.execute(
                "INSERT INTO local_pipeline_runs(run_id, run_json, created_at) VALUES (?, ?, ?)",
                (run_id, raw, "2026-09-05T10:00:00+00:00"),
            )
        created_at = "2026-09-05T10:00:00+00:00"
        conn.executemany(
            "INSERT INTO local_pipeline_run_events(run_id, event_id, stage, level, message, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("canonical-conflict", "event-conflict", "screening", "info", "legacy message", "{\"source\":\"legacy\"}", created_at),
                ("canonical-conflict", "event-equal", "screening", "info", "equal message", "{\"source\":\"equal\"}", created_at),
                ("legacy-complete", "event-malformed", "screening", "warning", "bad payload", "{bad-payload", created_at),
                ("missing-run", "event-orphan", "screening", "error", "orphan", "{}", created_at),
            ],
        )
        conn.commit()
    return database_path


def _counts(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as conn:
        counts = {}
        for table_name in (
            "pipeline_runs",
            "run_inputs",
            "run_stage_executions",
            "run_jobs",
            "process_events",
            "run_history_migration_ledger",
            "run_history_migration_quarantine",
        ):
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            ).fetchone()
            counts[table_name] = int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]) if exists else 0
    return counts


def test_backfill_preserves_legacy_rows_and_reconciles_all_dispositions(migration_db: Path) -> None:
    with sqlite3.connect(migration_db) as conn:
        before = conn.execute("SELECT run_id, run_json, created_at FROM local_pipeline_runs ORDER BY run_id").fetchall()
    first = sqlite_store.backfill_legacy_run_history(migration_db, batch_size=100)
    after_first = _counts(migration_db)
    second = sqlite_store.backfill_legacy_run_history(migration_db, batch_size=100)
    after_second = _counts(migration_db)

    assert first["runs"]["inserted"] == 2
    assert first["runs"]["degraded"] == 1
    assert first["runs"]["conflict"] == 1
    assert first["events"]["inserted"] == 1
    assert first["events"]["equal"] == 1
    assert first["events"]["conflict"] == 1
    assert first["events"]["quarantined"] == 1
    assert second["runs"]["processed"] == 0
    assert second["events"]["processed"] == 0
    assert after_second == after_first
    with sqlite3.connect(migration_db) as conn:
        assert conn.execute("SELECT run_json FROM local_pipeline_runs WHERE run_id='legacy-malformed'").fetchone()[0] == "{malformed-run-json"
        assert conn.execute("SELECT COUNT(*) FROM run_stage_executions WHERE run_id='legacy-complete'").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM run_stage_executions WHERE run_id='legacy-incomplete'").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM run_stage_executions WHERE run_id='legacy-malformed'").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM run_jobs WHERE run_id='legacy-complete'").fetchone()[0] == 2
        compatibility = json.loads(conn.execute("SELECT compatibility_json FROM pipeline_runs WHERE run_id='legacy-malformed'").fetchone()[0])
        assert compatibility["legacy_run"]["raw_run_json"] == "{malformed-run-json"
        payload = json.loads(conn.execute("SELECT payload_json FROM process_events WHERE event_id='event-malformed'").fetchone()[0])
        assert payload["legacy_payload_json"] == "{bad-payload"
        assert conn.execute("SELECT backend_status FROM pipeline_runs WHERE run_id='canonical-conflict'").fetchone()[0] == "succeeded"
        assert conn.execute("SELECT message FROM process_events WHERE event_id='event-conflict'").fetchone()[0] == "canonical message"
        assert conn.execute("SELECT COUNT(*) FROM process_events WHERE event_id='event-orphan'").fetchone()[0] == 0
        quarantine = conn.execute("SELECT raw_payload FROM run_history_migration_quarantine WHERE source_identity='run_id:legacy-malformed'").fetchone()[0]
        assert bytes(quarantine) == b"{malformed-run-json"
        assert conn.execute("SELECT COUNT(*) FROM run_history_migration_ledger WHERE disposition='equal'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM run_history_migration_ledger WHERE disposition='quarantined'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM run_history_migration_ledger WHERE disposition='conflict'").fetchone()[0] == 2
        assert conn.execute("SELECT run_id, run_json, created_at FROM local_pipeline_runs ORDER BY run_id").fetchall() == before


def test_backfill_changed_source_fingerprint_conflicts_without_overwrite(migration_db: Path) -> None:
    sqlite_store.backfill_legacy_run_history(migration_db, batch_size=100)
    with sqlite3.connect(migration_db) as conn:
        payload = _run_payload("legacy-complete", status="failed")
        conn.execute(
            "UPDATE local_pipeline_runs SET run_json=? WHERE run_id='legacy-complete'",
            (json.dumps(payload, ensure_ascii=False),),
        )
        conn.commit()
    result = sqlite_store.backfill_legacy_run_history(migration_db, batch_size=100)
    assert result["runs"]["conflict"] == 1
    with sqlite3.connect(migration_db) as conn:
        assert conn.execute("SELECT backend_status FROM pipeline_runs WHERE run_id='legacy-complete'").fetchone()[0] == "succeeded"
        assert conn.execute(
            "SELECT COUNT(*) FROM run_history_migration_ledger WHERE source_identity='run_id:legacy-complete'"
        ).fetchone()[0] == 2


def test_backfill_dry_run_and_bundle_failure_leave_state_unchanged(migration_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = _counts(migration_db)
    dry_run = sqlite_store.backfill_legacy_run_history(migration_db, batch_size=1, dry_run=True)
    assert dry_run["runs"]["processed"] == 1
    assert _counts(migration_db) == before

    def fail_bundle(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected bundle failure")

    monkeypatch.setattr(sqlite_store, "_run_history_backfill_run_bundle", fail_bundle)
    with pytest.raises(RuntimeError, match="injected bundle failure"):
        sqlite_store.backfill_legacy_run_history(migration_db, batch_size=1)
    with sqlite3.connect(migration_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM pipeline_runs WHERE run_id='legacy-complete'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM run_history_migration_ledger").fetchone()[0] == 0
