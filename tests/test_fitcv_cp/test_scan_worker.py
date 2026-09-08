import json
import sqlite3
from pathlib import Path

import pytest

from fitcv.ingest import canonicalize_jobs
from fitcv.job_sources import JobSourceError, build_scanner_request
from fitcv_cp import scan_worker, sqlite_store


def test_execute_scan_claims_and_commits_canonical_output(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "scan-worker.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    company = sqlite_store.create_tracked_company(
        company_name="Acme", careers_url="https://acme.jobs.personio.de/",
        provider_id="personio", provider_label="Personio", database_path=database_path,
    )
    scan = sqlite_store.create_scan(
        request={"company_ids": [company["company_id"]], "job_titles": [], "locations": [], "published_window": "any", "total_rows": 10},
        database_path=database_path,
    )
    artifact = canonicalize_jobs([{"jobUrl": "https://jobs.example/1", "title": "Data Engineer", "companyName": "Acme", "description": "Build data systems", "location": "Berlin", "contractType": "Full-time", "experienceLevel": "Mid-level"}])
    monkeypatch.setattr(scan_worker, "acquire_scanner_jobs", lambda _request: type("Result", (), {"artifact": artifact})())

    scan_worker.execute_scan(scan["scan_id"])

    detail = sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)
    output = sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)
    assert detail["execution_status"] == "succeeded"
    assert json.loads(output["output_json"])[0]["title"] == "Data Engineer"
    events = sqlite_store.get_process_events("scan", scan["scan_id"], limit=20)
    assert {event.operation for event in events["events"]} >= {"claim", "provider", "output"}


def test_execute_scan_applies_global_cap_to_provider_requests(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "scan-worker-cap.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    companies = [
        sqlite_store.create_tracked_company(
            company_name=f"Acme {index}",
            careers_url=f"https://acme-{index}.jobs.personio.de/",
            provider_id="personio",
            provider_label="Personio",
            database_path=database_path,
        )
        for index in range(2)
    ]
    scan = sqlite_store.create_scan(
        request={
            "company_ids": [company["company_id"] for company in companies],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": 3,
        },
        database_path=database_path,
    )
    jobs = [
        {
            "jobUrl": f"https://jobs.example/{index}",
            "title": f"Data Engineer {index}",
            "companyName": "Acme",
            "description": "Build data systems",
            "contractType": "Full-time",
            "experienceLevel": "Mid-level",
        }
        for index in range(5)
    ]
    artifact = canonicalize_jobs(jobs)
    requested_limits: list[int] = []

    def acquire(request):
        requested_limits.append(request.max_jobs)
        return type("Result", (), {"artifact": artifact})()

    monkeypatch.setattr(scan_worker, "acquire_scanner_jobs", acquire)
    scan_worker.execute_scan(scan["scan_id"])

    output = sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)
    assert requested_limits == [3]
    assert output["record_count"] == 3


def test_execute_scan_cancels_after_provider_result_without_output(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "scan-worker-cancel.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    company = sqlite_store.create_tracked_company(
        company_name="Acme",
        careers_url="https://acme.jobs.personio.de/",
        provider_id="personio",
        provider_label="Personio",
        database_path=database_path,
    )
    scan = sqlite_store.create_scan(
        request={
            "company_ids": [company["company_id"]],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": 10,
        },
        database_path=database_path,
    )
    artifact = canonicalize_jobs([{
        "jobUrl": "https://jobs.example/cancel",
        "title": "Data Engineer",
        "companyName": "Acme",
        "description": "Build data systems",
        "contractType": "Full-time",
        "experienceLevel": "Mid-level",
    }])

    def acquire(_request):
        current = sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)
        sqlite_store.request_scan_cancel(
            scan["scan_id"],
            expected_revision=current["row_revision"],
            database_path=database_path,
        )
        return type("Result", (), {"artifact": artifact})()

    monkeypatch.setattr(scan_worker, "acquire_scanner_jobs", acquire)
    scan_worker.execute_scan(scan["scan_id"])

    detail = sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)
    assert detail["execution_status"] == "cancelled"
    with pytest.raises(ValueError, match="scan_output_unavailable"):
        sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)


def test_execute_scan_uses_immutable_snapshot_config_after_registry_mutation(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "scan-worker-snapshot.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    company = sqlite_store.create_tracked_company(
        company_name="Acme",
        careers_url="https://acme.jobs.personio.de/",
        provider_id="personio",
        provider_label="Personio",
        database_path=database_path,
    )
    scan = sqlite_store.create_scan(
        request={
            "company_ids": [company["company_id"]],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": 10,
        },
        database_path=database_path,
    )
    snapshot = sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)["company_snapshots"][0]
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE tracked_companies SET careers_url=?, provider_config_json=? WHERE company_id=?",
            (
                "https://changed.jobs.personio.de/",
                json.dumps({
                    "schema_version": 1,
                    "provider_id": "personio",
                    "host": "changed.jobs.personio.de",
                    "region": "de",
                    "company_slug": "changed",
                }),
                company["company_id"],
            ),
        )
        connection.commit()
    captured = []
    monkeypatch.setattr(
        scan_worker,
        "acquire_scanner_jobs",
        lambda request: captured.append(request) or type(
            "Result", (), {"artifact": canonicalize_jobs([])}
        )(),
    )

    scan_worker.execute_scan(scan["scan_id"])

    assert captured[0].provider == snapshot["provider_id"]
    assert captured[0].careers_url == snapshot["careers_url"].rstrip("/")
    assert captured[0].trusted_provider_config == snapshot["provider_config"]
    assert sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)["execution_status"] == "succeeded"


def test_build_scanner_request_accepts_locale_prefixed_workday_snapshot() -> None:
    config = {
        "schema_version": 1,
        "provider_id": "workday",
        "host": "acme.wd3.myworkdayjobs.com",
        "region": "global",
        "tenant": "acme",
        "instance": "wd3",
        "site_path": "/Careers",
    }

    request = build_scanner_request(
        provider="workday",
        company_name="Acme",
        careers_url="https://acme.wd3.myworkdayjobs.com/en-US/Careers",
        trusted_provider_config=config,
    )

    assert request.careers_url == "https://acme.wd3.myworkdayjobs.com/Careers"
    assert request.trusted_provider_config is config


def test_build_scanner_request_rejects_trusted_config_url_disagreement() -> None:
    with pytest.raises(JobSourceError) as error:
        build_scanner_request(
            provider="personio",
            company_name="Acme",
            careers_url="https://acme.jobs.personio.de",
            trusted_provider_config={
                "schema_version": 1,
                "provider_id": "personio",
                "host": "changed.jobs.personio.de",
                "region": "de",
                "company_slug": "changed",
            },
        )

    assert error.value.code == "invalid_scanner_request"


def test_execute_scan_provider_failure_has_no_output_success_row(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "scan-worker-failure.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)
    company = sqlite_store.create_tracked_company(
        company_name="Acme",
        careers_url="https://acme.jobs.personio.de/",
        provider_id="personio",
        provider_label="Personio",
        database_path=database_path,
    )
    scan = sqlite_store.create_scan(
        request={
            "company_ids": [company["company_id"]],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": 10,
        },
        database_path=database_path,
    )
    monkeypatch.setattr(
        scan_worker,
        "acquire_scanner_jobs",
        lambda _request: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        scan_worker.execute_scan(scan["scan_id"])

    detail = sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path)
    assert detail["execution_status"] == "failed"
    assert detail["capabilities"]["use_for_run"] is False
    with pytest.raises(ValueError, match="scan_output_unavailable"):
        sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM scan_outputs WHERE scan_id=?", (scan["scan_id"],)
        ).fetchone()[0] == 0
