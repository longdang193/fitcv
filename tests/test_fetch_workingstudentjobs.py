from __future__ import annotations

from urllib.request import Request

import scripts.fetch_workingstudentjobs as fetcher
from scripts.fetch_workingstudentjobs import (
    build_structured_summary,
    extract_job_posting_json_ld,
    job_to_fitcv_record,
)


def test_default_http_opener_loads_certifi_bundle(monkeypatch) -> None:
    calls = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(request, *, timeout, context):
        calls["timeout"] = timeout
        calls["context"] = context
        return Response()

    monkeypatch.setattr(fetcher, "urlopen", fake_urlopen)

    assert fetcher._open_url(Request("https://example.com"), timeout=7).read() == b"ok"
    assert calls["timeout"] == 7
    assert calls["context"].verify_mode == fetcher.ssl.CERT_REQUIRED


def test_extract_job_posting_json_ld() -> None:
    page = """
    <script type="application/ld+json">
    {"@type":"WebSite","description":"not a job"}
    </script>
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Werkstudent","description":"<p>Build pipelines</p><ul><li>Python</li></ul>","applyLink":"https://example.com/apply"}
    </script>
    """

    record = extract_job_posting_json_ld(page)

    assert record is not None
    assert record["description"] == "<p>Build pipelines</p><ul><li>Python</li></ul>"
    assert record["applyLink"] == "https://example.com/apply"


def test_job_to_fitcv_record_keeps_source_and_uses_page_description() -> None:
    job = {
        "id": "job-1",
        "url": "https://www.workingstudentjobs.de/jobs/job-1",
        "title": "Working Student Data",
        "company": {"name": "ACME", "slug": "acme", "url": "https://example.com/company"},
        "location": {"city": "Berlin", "state": "Berlin", "country_code": "DE"},
        "types": ["working_student"],
        "field": "tech",
        "working_mode": "hybrid",
        "skills": ["Python"],
        "languages": {"english": "required"},
        "details": {"study_levels": ["bachelor"]},
    }
    page_record = {"@type": "JobPosting", "description": "<p>Build pipelines</p>", "applyLink": "https://example.com/apply"}

    record = job_to_fitcv_record(job, page_record)

    assert record["jobUrl"] == job["url"]
    assert record["description"] == "Build pipelines"
    assert record["applyUrl"] == "https://example.com/apply"
    assert record["source"] == "workingstudentjobs"
    assert record["sourceRecord"] == job
    assert record["sourcePageRecord"] == page_record
    assert {"jobUrl", "title", "companyName", "description", "contractType", "experienceLevel"} <= record.keys()


def test_structured_summary_is_available_when_page_details_fail() -> None:
    summary = build_structured_summary(
        {
            "types": ["working_student"],
            "field": "tech",
            "skills": ["Python"],
            "languages": {"english": "required"},
        }
    )

    assert "Working Student" in summary
    assert "Python" in summary
    assert "full posting text" in summary
