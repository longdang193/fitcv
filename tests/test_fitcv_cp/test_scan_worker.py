import json
from pathlib import Path

import pytest

from fitcv.ingest import canonicalize_jobs
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
