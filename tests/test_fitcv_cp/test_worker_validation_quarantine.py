import sqlite3
from pathlib import Path

import pytest

from fitcv_cp import sqlite_store
from fitcv_cp.backend_runtime import set_backend_runtime
from fitcv.late_stage_contract import derive_lifecycle_dimensions, derive_submission_clearance
from fitcv.pipeline import _is_persistable_cv_generation_result
from fitcv_cp.worker_job import _persist_cv_validation_quarantine_records


@pytest.fixture(autouse=True)
def _sqlite_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    set_backend_runtime(None)
    database_path = tmp_path / "fitcv-cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    sqlite_store.initialize_control_plane_database(
        database_path,
        tmp_path / "missing-candidate-profile.yaml",
    )
    yield
    set_backend_runtime(None)


def _record(*, structured=None, markdown=None, attempt_count=2, job_url="https://example.test/job/1"):
    return {
        "status": "validation_failed",
        "job_url": job_url,
        "run_job_id": f"run-job-{attempt_count}",
        "attempt_count": attempt_count,
        "validation": {"valid": False, "missing_sections": ["Experience"]},
        "diagnostic_registry": {
            "diagnostics": [
                {
                    "code": "validation_failed",
                    "source": "validator",
                    "facts": {"missing_sections": ["Experience"]},
                    "message": "original validation message",
                }
            ]
        },
        "quarantined_structured_cv": structured,
        "quarantined_markdown": markdown,
        "cv_generation_input_fingerprint": "generation-fp",
        "validation_evidence_fingerprint": "validation-fp",
        "trace_id": "trace-1",
        "error": {
            "code": "validation_failed",
            "message": "original validation message",
        },
    }


def test_worker_persists_complete_partial_and_unavailable_quarantines_without_accepted_fields():
    records = [
        _record(structured={"schema_version": "cv.v1"}, markdown="# draft"),
        _record(structured={"schema_version": "cv.v1"}, markdown=None, attempt_count=3, job_url="https://example.test/job/2"),
        _record(structured=None, markdown=None, attempt_count=4, job_url="https://example.test/job/3"),
    ]

    _persist_cv_validation_quarantine_records(run_id="run-1", records=records)

    stored = sqlite_store.list_cv_validation_quarantines(run_id="run-1")
    assert {item["availability"] for item in stored} == {"complete", "partial", "unavailable"}
    assert all("structured_cv_final" not in item and "markdown_final" not in item for item in stored)
    assert all(record["quarantine_persistence_status"] == "persisted" for record in records)
    assert all(record.get("submission_clearance") == "blocked" for record in records)
    assert all(record.get("structured_cv_final") is None for record in records)
    assert all(record.get("markdown_final") is None for record in records)


def test_quarantined_drafts_project_to_quarantined_lifecycle_disposition():
    dimensions = derive_lifecycle_dimensions(
        {
            "status": "validation_failed",
            "quarantined_structured_cv": {"schema_version": "cv.v1"},
            "structured_cv_final": None,
            "markdown_final": None,
        }
    )

    assert dimensions["draft_disposition"] == "quarantined"


def test_worker_quarantine_persistence_is_idempotent():
    record = _record(structured={"schema_version": "cv.v1"}, markdown="# draft")

    _persist_cv_validation_quarantine_records(run_id="run-1", records=[record])
    first = sqlite_store.list_cv_validation_quarantines(run_id="run-1")
    _persist_cv_validation_quarantine_records(run_id="run-1", records=[record])
    second = sqlite_store.list_cv_validation_quarantines(run_id="run-1")

    assert len(first) == len(second) == 1
    assert second[0]["quarantine_id"] == first[0]["quarantine_id"]
    assert second[0]["idempotency_key"] == first[0]["idempotency_key"]


def test_quarantine_schema_is_additive_and_idempotent_on_existing_db(tmp_path: Path):
    database_path = tmp_path / "existing.sqlite3"
    profile_path = tmp_path / "missing-candidate-profile.yaml"
    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE legacy_marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO legacy_marker(value) VALUES ('kept')")
        connection.execute("DROP TABLE cv_validation_quarantine")
        connection.commit()

    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    sqlite_store.insert_cv_validation_quarantine(
        {"run_id": "run-legacy", "availability": "complete", "structured_cv": {"v": 1}, "markdown": "# draft", "idempotency_key": "legacy-complete"}
    )
    sqlite_store.insert_cv_validation_quarantine(
        {"run_id": "run-legacy", "availability": "partial", "markdown": "# partial", "idempotency_key": "legacy-partial"}
    )
    sqlite_store.initialize_control_plane_database(database_path, profile_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT value FROM legacy_marker").fetchone()[0] == "kept"
    assert len(sqlite_store.list_cv_validation_quarantines(run_id="run-legacy")) == 2


def test_quarantine_is_not_an_accepted_persistence_or_submission_projection():
    record = _record(structured={"schema_version": "cv.v1"}, markdown="# draft")
    record.update(
        {
            "structured_cv_final": None,
            "markdown_final": None,
            "draft_disposition": "quarantined",
            "content_validity": "invalid",
        }
    )

    assert not _is_persistable_cv_generation_result(record)
    assert derive_submission_clearance(record)["submission_permitted"] is False


def test_worker_retry_creates_a_new_immutable_quarantine_attempt():
    first = _record(structured={"schema_version": "cv.v1"}, markdown="# draft", attempt_count=1)
    retry = _record(
        structured={"schema_version": "cv.v1", "attempt": 2},
        markdown="# retry",
        attempt_count=2,
    )

    _persist_cv_validation_quarantine_records(run_id="run-1", records=[first])
    _persist_cv_validation_quarantine_records(run_id="run-1", records=[retry])

    stored = sqlite_store.list_cv_validation_quarantines(run_id="run-1")
    assert len(stored) == 2
    assert {item["attempt_id"] for item in stored} == {
        "run-job-1:attempt:1",
        "run-job-2:attempt:2",
    }
    assert {item["markdown"] for item in stored} == {"# draft", "# retry"}


def test_worker_preserves_validation_failure_when_quarantine_write_fails(monkeypatch: pytest.MonkeyPatch):
    from fitcv_cp import worker_job

    record = _record(structured={"schema_version": "cv.v1"}, markdown="# draft")
    original_error = dict(record["error"])
    monkeypatch.setattr(
        worker_job,
        "insert_cv_validation_quarantine",
        lambda row: (_ for _ in ()).throw(RuntimeError("quarantine unavailable")),
    )

    _persist_cv_validation_quarantine_records(run_id="run-1", records=[record])

    assert record["status"] == "validation_failed"
    assert record["error"] == original_error
    assert record["submission_clearance"] == "blocked"
    assert record["quarantine_persistence_status"] == "failed"
    assert record["quarantine_persistence_error"]["code"] == "quarantine_persistence_failed"
    codes = [item["code"] for item in record["diagnostic_registry"]["diagnostics"]]
    assert codes == ["validation_failed", "quarantine_persistence_failed"]
    assert sqlite_store.list_cv_validation_quarantines(run_id="run-1") == []
