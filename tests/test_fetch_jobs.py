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
        "valig/linkedin-jobs-scraper",
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


def test_apify_lifecycle_reports_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        {"data": {"id": "run-1", "status": "READY"}},
        {"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "ds-1"}},
        {"data": [{"id": "job-1"}]},
    ])
    progress: list[str] = []

    monkeypatch.setattr(fetcher, "request_json", lambda *args, **kwargs: next(responses))
    result = fetcher.run_apify_actor(
        "valig/linkedin-jobs-scraper",
        {"rows": 5},
        "token",
        timeout_secs=30,
        poll_timeout_secs=30,
        poll_interval_secs=0,
        progress=progress.append,
    )

    assert result["items"] == [{"id": "job-1"}]
    assert any("starting actor valig/linkedin-jobs-scraper" in message for message in progress)
    assert any("run run-1 status=SUCCEEDED" in message for message in progress)
    assert any("dataset ds-1 returned 1 items" in message for message in progress)


@pytest.mark.parametrize("status", ["FAILED", "TIMED-OUT", "ABORTED"])
def test_apify_terminal_failure_states_raise(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    monkeypatch.setattr(
        fetcher,
        "request_json",
        lambda *args, **kwargs: {"data": {"id": "run-1", "status": status}},
    )

    with pytest.raises(fetcher.FetchError, match=status):
        fetcher.run_apify_actor("actor/name", {}, "token", timeout_secs=30, poll_timeout_secs=30, poll_interval_secs=0)


def test_apify_timeout_error_identifies_actor_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fetcher,
        "request_json",
        lambda *args, **kwargs: {"data": {"id": "run-1", "status": "TIMED-OUT"}},
    )

    with pytest.raises(fetcher.FetchError, match=r"actor/name.*TIMED-OUT.*actor timeout=30s"):
        fetcher.run_apify_actor("actor/name", {}, "token", timeout_secs=30, poll_timeout_secs=30, poll_interval_secs=0)


def test_apify_timeout_salvages_non_empty_partial_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        {"data": {"id": "run-1", "status": "RUNNING"}},
        {"data": {"id": "run-1", "status": "TIMED-OUT", "defaultDatasetId": "ds-1"}},
        {"data": [{"id": "job-1"}]},
    ])
    progress: list[str] = []

    monkeypatch.setattr(fetcher, "request_json", lambda *args, **kwargs: next(responses))
    result = fetcher.run_apify_actor(
        "valig/linkedin-jobs-scraper",
        {"rows": 5},
        "token",
        timeout_secs=30,
        poll_timeout_secs=30,
        poll_interval_secs=0,
        progress=progress.append,
    )

    assert result["status"] == "TIMED-OUT"
    assert result["partial"] is True
    assert result["items"] == [{"id": "job-1"}]
    assert any("salvaging 1 partial items" in message for message in progress)


def test_fetch_sources_uses_configured_actor_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(actor_id, input_payload, token, **kwargs):
        captured.update(kwargs)
        return {"runId": "run-1", "datasetId": "ds-1", "items": []}

    monkeypatch.setattr(fetcher, "run_apify_actor", fake_run)
    records, failures, runs = fetcher.fetch_sources(
        {
            "linkedin": {
                "source": "linkedin",
                "kind": "apify_actor",
                "actor": "actor/name",
                "input": {},
                "run": {"timeoutSecs": 300, "pollIntervalSecs": 7},
            }
        },
        ["linkedin"],
        "token",
        run_timeout_secs=0,
        poll_timeout_secs=0,
    )

    assert records == []
    assert failures == []
    assert runs == {
        "linkedin": {
            "runId": "run-1",
            "datasetId": "ds-1",
            "started": 1,
            "status": "SUCCEEDED",
            "partial": False,
        }
    }
    assert captured["timeout_secs"] == 300
    assert captured["poll_interval_secs"] == 7.0

    fetcher.fetch_sources(
        {
            "linkedin": {
                "source": "linkedin",
                "kind": "apify_actor",
                "actor": "actor/name",
                "input": {},
                "run": {"timeoutSecs": 300, "pollIntervalSecs": 7},
            }
        },
        ["linkedin"],
        "token",
        run_timeout_secs=90,
        poll_timeout_secs=120,
    )

    assert captured["timeout_secs"] == 90
    assert captured["poll_timeout_secs"] == 120


def test_fetch_sources_bounds_valig_linkedin_without_mutating_input(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(actor_id, input_payload, token, **kwargs):
        captured["actor_id"] = actor_id
        captured["input"] = input_payload
        captured.update(kwargs)
        return {"runId": "run-1", "datasetId": "ds-1", "items": []}

    input_payload = {
        "datePosted": "r86400",
        "easyApply": False,
        "keywords": "student",
        "location": "Germany",
        "under10Applicants": False,
    }
    monkeypatch.setattr(fetcher, "run_apify_actor", fake_run)
    fetcher.fetch_sources(
        {
            "linkedin": {
                "source": "linkedin",
                "kind": "apify_actor",
                "actor": "valig/linkedin-jobs-scraper",
                "input": input_payload,
                "run": {"timeoutSecs": 300, "pollIntervalSecs": 2},
            }
        },
        ["linkedin"],
        "token",
        max_records_per_source=5,
    )

    assert captured["actor_id"] == "valig/linkedin-jobs-scraper"
    assert captured["input"] == input_payload
    assert captured["max_items"] == 5


def test_fetch_sources_runs_named_inputs_sequentially(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    progress: list[str] = []

    def fake_run(actor_id, input_payload, token, **kwargs):
        calls.append({"actor": actor_id, "input": input_payload})
        job_id = str(len(calls))
        return {
            "runId": f"run-{job_id}",
            "datasetId": f"ds-{job_id}",
            "items": [{
                "id": f"job-{job_id}",
                "url": f"https://linkedin.example/{job_id}",
                "title": "Working Student AI",
                "companyName": "Example",
                "location": "Berlin, Germany",
                "description": "A full job description with enough detail to pass the normalized description requirement.",
            }],
        }

    monkeypatch.setattr(fetcher, "run_apify_actor", fake_run)
    records, failures, runs = fetcher.fetch_sources(
        {
            "linkedin": {
                "source": "linkedin",
                "kind": "apify_actor",
                "actor": "valig/linkedin-jobs-scraper",
                "runs": [
                    {"name": "ai", "input": {"keywords": "AI"}},
                    {"name": "broad", "input": {"keywords": "student"}},
                ],
                "run": {"timeoutSecs": 300},
            }
        },
        ["linkedin"],
        "token",
        progress=progress.append,
    )

    assert [call["input"] for call in calls] == [{"keywords": "AI"}, {"keywords": "student"}]
    assert [record["sourceJobId"] for record in records] == ["job-1", "job-2"]
    assert failures == []
    assert list(runs) == ["linkedin/ai", "linkedin/broad"]
    assert any("run 1/2 ai: starting" in message for message in progress)
    assert any("run 2/2 broad: starting" in message for message in progress)


def test_fetch_sources_retains_incomplete_records_for_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(actor_id, input_payload, token, **kwargs):
        return {
            "runId": "run-1",
            "datasetId": "ds-1",
            "items": [{
                "id": "job-footer",
                "url": "https://linkedin.example/footer",
                "title": "Data Engineer",
                "companyName": "Example",
                "location": "Berlin, Germany",
                "description": "Lebenslauf Telefon +49 89 236139465",
            }],
        }

    monkeypatch.setattr(fetcher, "run_apify_actor", fake_run)
    records, failures, _runs = fetcher.fetch_sources(
        {
            "linkedin": {
                "source": "linkedin",
                "kind": "apify_actor",
                "actor": "actor/name",
                "input": {},
            }
        },
        ["linkedin"],
        "token",
    )

    assert [record["sourceJobId"] for record in records] == ["job-footer"]
    assert records[0]["descriptionStatus"] == "boilerplate_only"
    assert failures == [{"sourceJobId": "job-footer", "reason": "incomplete_description"}]


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


def test_fuzzy_dedupe_retains_linkedin_over_workingstudentjobs() -> None:
    linkedin = fetcher.linkedin_to_fitcv_record(
        {
            "id": "linkedin-job",
            "jobUrl": "https://linkedin.example/job/linkedin-job",
            "title": "Intern",
            "companyName": "ACME",
            "location": "Berlin",
            "description": _long_description("same"),
        },
        None,
    )
    workingstudentjobs = {
        **linkedin,
        "source": "workingstudentjobs",
        "sourceJobId": "workingstudentjobs-job",
        "jobUrl": "https://workingstudentjobs.example/job/workingstudentjobs-job",
    }

    kept, excluded = fetcher.deduplicate_records([workingstudentjobs, linkedin])

    assert [record["source"] for record in kept] == ["linkedin"]
    assert len(excluded) == 1
    assert excluded[0]["duplicateOf"] == fetcher.record_identity(linkedin)


def test_fuzzy_dedupe_retains_linkedin_even_when_other_source_is_newer() -> None:
    linkedin = fetcher.linkedin_to_fitcv_record(
        {
            "id": "linkedin-job",
            "jobUrl": "https://linkedin.example/job/linkedin-job",
            "title": "Intern",
            "companyName": "ACME",
            "location": "Berlin",
            "description": _long_description("same"),
            "publishedAt": "2026-01-01",
        },
        None,
    )
    workingstudentjobs = {
        **linkedin,
        "source": "workingstudentjobs",
        "sourceJobId": "workingstudentjobs-job",
        "publishedAt": "2026-11-04",
        "jobUrl": "https://workingstudentjobs.example/job/workingstudentjobs-job",
    }

    kept, excluded = fetcher.deduplicate_records([workingstudentjobs, linkedin])

    assert [record["source"] for record in kept] == ["linkedin"]
    assert len(excluded) == 1


def test_fuzzy_dedupe_normalizes_country_aliases_in_location_bucket() -> None:
    linkedin = fetcher.linkedin_to_fitcv_record(
        {
            "id": "linkedin-job",
            "jobUrl": "https://linkedin.example/job/linkedin-job",
            "title": "Intern",
            "companyName": "ACME",
            "location": "Berlin, Berlin, Germany",
            "description": _long_description("same"),
        },
        None,
    )
    workingstudentjobs = {
        **linkedin,
        "source": "workingstudentjobs",
        "sourceJobId": "workingstudentjobs-job",
        "location": "Berlin, Berlin, DE",
        "jobUrl": "https://workingstudentjobs.example/job/workingstudentjobs-job",
    }

    kept, excluded = fetcher.deduplicate_records([workingstudentjobs, linkedin])

    assert [record["source"] for record in kept] == ["linkedin"]
    assert len(excluded) == 1
    assert excluded[0]["duplicateOf"] == fetcher.record_identity(linkedin)


def test_fuzzy_dedupe_normalizes_company_suffix_and_city_aliases() -> None:
    linkedin = fetcher.linkedin_to_fitcv_record(
        {
            "id": "linkedin-job",
            "jobUrl": "https://linkedin.example/job/linkedin-job",
            "title": "Intern",
            "companyName": "Solactive",
            "location": "Frankfurt, Hessen, Germany",
            "description": _long_description("same"),
        },
        None,
    )
    indeed = {
        **linkedin,
        "source": "indeed",
        "sourceJobId": "indeed-job",
        "companyName": "Solactive AG",
        "location": "Frankfurt am Main, Deutschland",
        "jobUrl": "https://indeed.example/job/indeed-job",
    }

    kept, excluded = fetcher.deduplicate_records([indeed, linkedin])

    assert [record["source"] for record in kept] == ["linkedin"]
    assert len(excluded) == 1
    assert excluded[0]["duplicateOf"] == fetcher.record_identity(linkedin)


def test_fuzzy_dedupe_collapses_exact_jd_with_company_aliases() -> None:
    first = fetcher.linkedin_to_fitcv_record(
        {
            "id": "first-job",
            "jobUrl": "https://jobs.example/job/first-job",
            "title": "Working Student",
            "companyName": "Krieger Digital",
            "location": "Schönefeld, Brandenburg, DE",
            "description": _long_description("same"),
        },
        None,
    )
    second = {
        **first,
        "sourceJobId": "second-job",
        "companyName": "Krieger Gruppe",
        "jobUrl": "https://jobs.example/job/second-job",
    }

    kept, excluded = fetcher.deduplicate_records([second, first])

    assert len(kept) == 1
    assert len(excluded) == 1
    assert excluded[0]["similarity"] == 1.0


def test_fuzzy_dedupe_keeps_different_company_jds_below_alias_similarity() -> None:
    shared = " ".join(f"shared{index}" for index in range(48))
    first = fetcher.linkedin_to_fitcv_record(
        {
            "id": "first-job",
            "jobUrl": "https://jobs.example/job/first-job",
            "title": "Retail Sales Intern",
            "companyName": "BYTECLUB",
            "location": "Hude, Niedersachsen, DE",
            "description": f"{shared} unique-first-a unique-first-b",
        },
        None,
    )
    second = {
        **first,
        "sourceJobId": "second-job",
        "companyName": "COMSPOT",
        "jobUrl": "https://jobs.example/job/second-job",
        "description": f"{shared} unique-second-a unique-second-b",
    }

    kept, excluded = fetcher.deduplicate_records([first, second])

    assert len(kept) == 2
    assert excluded == []


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
