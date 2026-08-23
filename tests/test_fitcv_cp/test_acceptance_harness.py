from __future__ import annotations

from pathlib import Path

import pytest

from fitcv_cp import sqlite_store
from tests.test_fitcv_cp.acceptance_harness import ControlledLocalJobExecutor, create_profile_fixture, create_scan_fixture


def test_controlled_executor_holds_until_release_and_captures_result() -> None:
    with ControlledLocalJobExecutor() as executor:
        future = executor.submit(lambda value: value, "snapshot-A")
        executor.wait_submitted()
        assert not future.done()
        executor.release()
        assert executor.result() == "snapshot-A"


def test_controlled_executor_releases_exactly_once() -> None:
    with ControlledLocalJobExecutor() as executor:
        executor.submit(lambda: None)
        executor.wait_submitted()
        executor.release()
        with pytest.raises(RuntimeError, match="already released"):
            executor.release()


def test_controlled_executor_preserves_worker_exception() -> None:
    def fail() -> None:
        raise ValueError("fixture failure")

    with ControlledLocalJobExecutor() as executor:
        executor.submit(fail)
        executor.wait_submitted()
        executor.release()
        with pytest.raises(ValueError, match="fixture failure"):
            executor.result()

def test_controlled_executor_can_inject_one_local_failure() -> None:
    with ControlledLocalJobExecutor() as executor:
        executor.submit(lambda: None)
        executor.wait_submitted()
        executor.fail_next(RuntimeError("acceptance injected failure"))
        executor.release()
        with pytest.raises(RuntimeError, match="acceptance injected failure"):
            executor.result()


def test_scan_fixture_is_disposable_and_run_eligible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "acceptance.sqlite3"
    profile_path = Path(__file__).parents[2] / "data" / "candidate_profile.private.yaml"
    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))

    jobs = [{
        "jobUrl": "https://acceptance.example/job-1",
        "title": "Data Analyst",
        "companyName": "Acceptance Company",
        "description": "Analyze product data with SQL and Python.",
        "contractType": "Full-time",
        "experienceLevel": "Mid-Senior level",
        "location": "Berlin, Germany",
    }]
    scan = create_scan_fixture(database_path, scan_name="Acceptance Scan A", jobs=jobs)

    assert scan["execution_status"] == "succeeded"
    assert scan["output_record_count"] == 1
    assert scan["output_integrity_valid"] is True
    assert scan["capabilities"]["use_for_run"] is True
    assert sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)["output_json"]


def test_profile_fixture_is_active_and_v2(tmp_path: Path) -> None:
    database_path = tmp_path / "acceptance.sqlite3"
    profile_path = Path(__file__).parents[2] / "data" / "candidate_profile.private.yaml"
    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    from tests.test_fitcv_cp.candidate_profile_fixtures import CandidateProfileMockState, _baseline_document, _derived_document

    canonical = CandidateProfileMockState._canonical(_baseline_document(), _derived_document())
    profile = create_profile_fixture(database_path, canonical)

    assert profile["creation_status"] == "succeeded"
    assert profile["lifecycle"] == "active"
    assert profile["is_active"] is True
    assert profile["profile"]["schema_version"] == "candidate-profile.v2"
