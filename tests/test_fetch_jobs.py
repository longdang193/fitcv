from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.fetch_jobs as fetcher


def _long_description(prefix: str = "job") -> str:
    return " ".join(f"{prefix}{index}" for index in range(50))


def test_direct_script_entrypoint_can_load_sibling_helper() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/fetch_jobs.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--source" in result.stdout


def test_source_configs_are_symmetric_and_stepstone_is_not_enabled() -> None:
    configs = fetcher.load_source_configs(Path("config/job_sources"))

    assert tuple(configs) == fetcher.SUPPORTED_SOURCES
    assert all(configs[source]["source"] == source for source in fetcher.SUPPORTED_SOURCES)
    assert "stepstone" not in configs
    assert configs["workingstudentjobs"]["details"]["require"] is True
    assert "type" not in configs["workingstudentjobs"]["request"]


def test_load_env_file_does_not_override_process_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("APIFY_API_TOKEN=file-token\nFETCH_JOBS_TIMEOUT=12\n", encoding="utf-8")
    monkeypatch.setenv("APIFY_API_TOKEN", "process-token")

    loaded = fetcher.load_env_file(env_path)

    assert loaded["APIFY_API_TOKEN"] == "file-token"
    assert loaded["FETCH_JOBS_TIMEOUT"] == "12"
    assert fetcher.resolve_env("APIFY_API_TOKEN", loaded) == "process-token"


def test_linkedin_mapping_preserves_full_description_and_identity() -> None:
    raw = {
        "id": "li-1",
        "jobUrl": "https://linkedin.example/job/li-1",
        "applyUrl": "https://company.example/apply/li-1",
        "title": "Intern",
        "companyName": "ACME",
        "location": "Berlin, Germany",
        "description": _long_description(),
        "publishedAt": "2026-11-04",
    }

    record = fetcher.linkedin_to_fitcv_record(raw, {"runId": "run-li", "datasetId": "ds-li"})

    assert record["jobUrl"] == raw["jobUrl"]
    assert record["applyUrl"] == raw["applyUrl"]
    assert record["sourceJobId"] == "li-1"
    assert record["sourceDescription"] == "description"
    assert record["descriptionStatus"] == "full"
    assert record["sourceRecord"] == raw
    assert record["sourceRunId"] == "run-li"


def test_indeed_mapping_distinguishes_listing_and_application_urls() -> None:
    raw = {
        "key": "in-1",
        "url": "https://de.indeed.com/viewjob?jk=in-1",
        "jobUrl": "https://company.example/apply/in-1",
        "title": "Intern",
        "employer": {"name": "ACME"},
        "location": {"city": "Berlin", "country": "Germany"},
        "description": {"text": _long_description("indeed")},
        "datePublished": "2026-11-04T00:00:00Z",
    }

    record = fetcher.indeed_to_fitcv_record(raw, {"runId": "run-in", "datasetId": "ds-in"})

    assert record["jobUrl"] == raw["url"]
    assert record["applyUrl"] == raw["jobUrl"]
    assert record["companyName"] == "ACME"
    assert record["location"] == "Berlin, Germany"
    assert record["sourceJobId"] == "in-1"
    assert record["descriptionStatus"] == "full"


def test_workingstudentjobs_detail_failure_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    job = {"id": "wsj-1", "url": "https://workingstudentjobs.example/job-1", "title": "Intern"}
    monkeypatch.setattr(fetcher.workingstudentjobs, "fetch_all_jobs", lambda *args, **kwargs: [job])
    monkeypatch.setattr(fetcher.workingstudentjobs, "_request_bytes", lambda *args, **kwargs: b"<html></html>")
    monkeypatch.setattr(fetcher.workingstudentjobs, "extract_job_posting_json_ld", lambda value: None)

    records, failures = fetcher.fetch_workingstudentjobs_source(
        {"request": {"ref": "fitcv", "pageSize": 5, "maxJobs": 1}, "details": {"require": True}},
        max_records=5,
    )

    assert records == []
    assert failures == [{"sourceJobId": "wsj-1", "reason": "missing_full_description"}]


def test_workingstudentjobs_summary_fallback_is_never_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    job = {"id": "wsj-2", "url": "https://workingstudentjobs.example/job-2", "title": "Intern"}
    monkeypatch.setattr(fetcher.workingstudentjobs, "fetch_all_jobs", lambda *args, **kwargs: [job])
    monkeypatch.setattr(fetcher.workingstudentjobs, "_request_bytes", lambda *args, **kwargs: b"<html></html>")
    monkeypatch.setattr(fetcher.workingstudentjobs, "extract_job_posting_json_ld", lambda value: None)

    records, failures = fetcher.fetch_workingstudentjobs_source(
        {"request": {"ref": "fitcv", "pageSize": 5, "maxJobs": 1}, "details": {"require": False}},
        max_records=5,
    )

    assert records == []
    assert failures == [{"sourceJobId": "wsj-2", "reason": "missing_full_description"}]


def test_apify_lifecycle_uses_bearer_header_and_default_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict | None]] = []
    responses = iter([
        {"data": {"id": "run-1", "status": "READY"}},
        {"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "ds-1"}},
        {"data": [{"id": "job-1"}]},
    ])

    def fake_request(method, url, token, payload=None, timeout=0):
        calls.append((method, url, payload))
        return next(responses)

    monkeypatch.setattr(fetcher, "request_json", fake_request)
    result = fetcher.run_apify_actor(
        "bebity/linkedin-jobs-scraper",
        {"rows": 5},
        "secret-token",
        timeout_secs=30,
        poll_timeout_secs=30,
        poll_interval_secs=0,
        max_items=5,
    )

    assert result["items"] == [{"id": "job-1"}]
    assert result["runId"] == "run-1"
    assert result["datasetId"] == "ds-1"
    assert "secret-token" not in " ".join(url for _, url, _ in calls)
    assert calls[0][0] == "POST"
    assert "timeout=30" in calls[0][1]
    assert "maxItems=5" in calls[0][1]


@pytest.mark.parametrize("status", ["FAILED", "TIMED-OUT", "ABORTED"])
def test_apify_terminal_failure_states_raise(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    monkeypatch.setattr(
        fetcher,
        "request_json",
        lambda *args, **kwargs: {"data": {"id": "run-1", "status": status}},
    )

    with pytest.raises(fetcher.FetchError, match=status):
        fetcher.run_apify_actor("actor/name", {}, "token", timeout_secs=30, poll_timeout_secs=30, poll_interval_secs=0)


def test_apify_client_deadline_aborts_running_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    times = iter([0.0, 0.0, 2.0])

    def fake_request(method, url, token, payload=None, timeout=0):
        calls.append((method, url))
        if method == "POST":
            return {"data": {"id": "run-1", "status": "RUNNING"}}
        if method == "GET":
            return {"data": {"id": "run-1", "status": "RUNNING"}}
        return {"data": {"status": "ABORTED"}}

    monkeypatch.setattr(fetcher, "request_json", fake_request)
    monkeypatch.setattr(fetcher.time, "monotonic", lambda: next(times))

    with pytest.raises(fetcher.FetchError, match="deadline"):
        fetcher.run_apify_actor("actor/name", {}, "token", timeout_secs=30, poll_timeout_secs=1, poll_interval_secs=0)

    assert any(method == "PUT" and "/abort" in url for method, url in calls)


def test_fuzzy_dedupe_requires_strictly_more_than_ninety_percent_and_same_bucket() -> None:
    base = _long_description("same")
    same_at_threshold = {**fetcher.linkedin_to_fitcv_record({"id": "a", "jobUrl": "https://a", "title": "Intern", "companyName": "ACME", "location": "Berlin", "description": base}, None)}
    other = {**same_at_threshold, "sourceJobId": "b", "jobUrl": "https://b", "description": base + " extra"}
    different_location = {**other, "sourceJobId": "c", "jobUrl": "https://c", "location": "Munich"}

    kept, excluded = fetcher.deduplicate_records([different_location, other, same_at_threshold])

    assert len(kept) == 2
    assert len(excluded) == 1
    assert excluded[0]["duplicateOf"] == fetcher.record_identity(same_at_threshold)


def test_description_intersection_exactly_ninety_percent_survives() -> None:
    left = " ".join(f"token{index}" for index in range(40))
    right = " ".join(f"token{index}" for index in range(36)) + " " + " ".join(f"other{index}" for index in range(4))

    assert fetcher.description_intersection_rate(left, right) == 0.9

    first = fetcher.linkedin_to_fitcv_record(
        {"id": "threshold-a", "jobUrl": "https://threshold-a", "title": "Intern", "companyName": "ACME", "location": "Berlin", "description": left},
        None,
    )
    second = fetcher.linkedin_to_fitcv_record(
        {"id": "threshold-b", "jobUrl": "https://threshold-b", "title": "Intern", "companyName": "ACME", "location": "Berlin", "description": right},
        None,
    )

    kept, excluded = fetcher.deduplicate_records([first, second])

    assert len(kept) == 2
    assert excluded == []


def test_output_report_digest_and_duplicate_references_match(tmp_path: Path) -> None:
    jobs = [{"source": "linkedin", "sourceJobId": "a", "jobUrl": "https://a", "title": "Intern", "companyName": "ACME", "location": "Berlin", "description": _long_description(), "descriptionStatus": "full", "contractType": "", "experienceLevel": ""}]
    output = tmp_path / "jobs.json"
    report = tmp_path / "jobs.dedupe.json"

    fetcher.write_outputs(output, report, jobs, [], {"linkedin": {"runId": "run-1", "datasetId": "ds-1"}})

    output_bytes = output.read_bytes()
    report_value = json.loads(report.read_text(encoding="utf-8"))
    assert report_value["outputSha256"] == hashlib.sha256(output_bytes).hexdigest()
    assert report_value["runId"]
