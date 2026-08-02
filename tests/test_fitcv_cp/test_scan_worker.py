import json
from pathlib import Path

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
