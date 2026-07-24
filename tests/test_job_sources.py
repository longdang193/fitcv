from datetime import date
from pathlib import Path

import pytest

import fitcv.job_sources as job_sources
from fitcv.ingest import validate_linkedin_schema


PERSONIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>2337942</id>
    <office>Berlin</office>
    <additionalOffices><office>deutschlandweit</office></additionalOffices>
    <name>Data Engineer – Databricks (m/w/d)</name>
    <jobDescriptions><jobDescription><name>Tasks</name><value><![CDATA[<ul><li>Build pipelines</li><li>Use Databricks</li></ul>]]></value></jobDescription></jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <yearsOfExperience>2-5</yearsOfExperience>
    <createdAt>2025-09-16T06:25:26+00:00</createdAt>
  </position>
  <position><id>2</id><office>Hamburg</office><name>Sales Manager</name><jobDescriptions><jobDescription><name>Tasks</name><value>Sell</value></jobDescription></jobDescriptions></position>
</workzag-jobs>
"""


def _job(**overrides: str) -> dict[str, str]:
    job = {
        "title": "Data Engineer",
        "jobUrl": "https://example.com/jobs/1",
        "companyName": "ACME",
        "description": "Build pipelines",
        "contractType": "Full-time",
        "experienceLevel": "Senior",
    }
    job.update(overrides)
    return job


def test_build_scanner_request_normalizes_shared_contract() -> None:
    request = job_sources.build_scanner_request(
        provider="AUTO",
        company_name="  ACME GmbH  ",
        careers_url="https://job-boards.eu.greenhouse.io/acme/",
        keywords=[" Data Engineer ", "data engineer", "Analytics"],
    )

    assert request.provider == "auto"
    assert request.company_name == "ACME GmbH"
    assert request.careers_url == "https://job-boards.eu.greenhouse.io/acme"
    assert request.keywords == ("Data Engineer", "Analytics")
    assert request.max_jobs == 50
    assert request.timeout_seconds == 60


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"company_name": ""}, "company_name"),
        ({"company_name": "x" * 201}, "company_name"),
        ({"careers_url": "http://example.com"}, "HTTPS"),
        ({"careers_url": "https://user:pass@example.com/jobs"}, "credentials"),
        ({"careers_url": "https://example.com:444/jobs"}, "custom port"),
        ({"careers_url": "https://example.com/jobs?q=x"}, "query"),
        ({"max_jobs": 0}, "max_jobs"),
        ({"max_jobs": 201}, "max_jobs"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"timeout_seconds": 121}, "timeout_seconds"),
    ],
)
def test_build_scanner_request_rejects_invalid_shared_fields(
    kwargs: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "company_name": "ACME",
        "careers_url": "https://job-boards.eu.greenhouse.io/acme",
    }
    values.update(kwargs)

    with pytest.raises(job_sources.JobSourceError, match=message) as error:
        job_sources.build_scanner_request(**values)

    assert error.value.code == "invalid_scanner_request"


def test_provider_options_and_resolution_come_from_registry() -> None:
    options = job_sources.list_provider_options()
    assert [option["id"] for option in options] == ["personio", "greenhouse", "workday"]

    request = job_sources.build_scanner_request(
        company_name="ACME",
        careers_url="https://job-boards.eu.greenhouse.io/acme",
    )
    assert job_sources.resolve_provider(request).provider_id == "greenhouse"


def test_provider_resolution_rejects_unknown_unsupported_and_ambiguous() -> None:
    with pytest.raises(job_sources.JobSourceError) as unknown:
        job_sources.build_scanner_request(
            provider="missing",
            company_name="ACME",
            careers_url="https://example.com/jobs",
        )
    assert unknown.value.code == "unknown_provider"

    unsupported = job_sources.build_scanner_request(
        company_name="ACME", careers_url="https://example.com/jobs"
    )
    with pytest.raises(job_sources.JobSourceError) as no_match:
        job_sources.resolve_provider(unsupported)
    assert no_match.value.code == "unsupported_provider_url"

    providers = {
        "one": job_sources.ProviderDefinition("one", "One", lambda _: True, lambda _: []),
        "two": job_sources.ProviderDefinition("two", "Two", lambda _: True, lambda _: []),
    }
    with pytest.raises(job_sources.JobSourceError) as ambiguous:
        job_sources.resolve_provider(unsupported, providers=providers)
    assert ambiguous.value.code == "ambiguous_provider_url"
    assert "one" in str(ambiguous.value) and "two" in str(ambiguous.value)


def test_acquire_scanner_jobs_uses_resolved_provider_and_canonicalizes() -> None:
    providers = {
        "one": job_sources.ProviderDefinition("one", "One", lambda _: True, lambda _: [_job()])
    }
    request = job_sources.build_scanner_request(
        provider="one",
        company_name="ACME",
        careers_url="https://example.com/jobs",
        providers=providers,
    )

    result = job_sources.acquire_scanner_jobs(request, providers=providers)

    assert result.provider_id == "one"
    assert result.artifact.jobs == [_job()]


def test_export_scanner_jobs_allows_empty_array(tmp_path: Path) -> None:
    providers = {
        "one": job_sources.ProviderDefinition("one", "One", lambda _: True, lambda _: [])
    }
    request = job_sources.build_scanner_request(
        provider="one",
        company_name="ACME",
        careers_url="https://example.com/jobs",
        providers=providers,
    )
    output = tmp_path / "jobs.json"

    result = job_sources.export_scanner_jobs(request, output, providers=providers)

    assert result.artifact.jobs == []
    assert output.read_text(encoding="utf-8") == "[]"


def test_parse_personio_jobs_emits_fitcv_contract() -> None:
    jobs = job_sources.parse_personio_jobs(
        PERSONIO_XML,
        company_name="areto consulting",
        careers_url="https://areto.jobs.personio.de",
        keywords=("data engineer",),
    )

    assert len(jobs) == 1
    assert validate_linkedin_schema(jobs[0]) == []
    assert jobs[0]["location"] == "Berlin, deutschlandweit"
    assert "Build pipelines" in jobs[0]["description"]


def test_parse_greenhouse_jobs_emits_fitcv_contract() -> None:
    jobs = job_sources.parse_greenhouse_jobs(
        {"jobs": [{
            "id": 4929240101,
            "title": "Data Engineer (all genders)",
            "absolute_url": "https://job-boards.eu.greenhouse.io/gropyus/jobs/4929240101",
            "location": {"name": "Berlin, Germany"},
            "first_published": "2026-07-15T17:56:24-04:00",
            "content": "<h2>Your role</h2><ul><li>Build data products</li></ul>",
            "metadata": [{"name": "Type of Employment", "value": ["Employee"]}],
        }]},
        company_name="GROPYUS",
        careers_url="https://job-boards.eu.greenhouse.io/gropyus",
        keywords=("data engineer",),
    )

    assert validate_linkedin_schema(jobs[0]) == []
    assert jobs[0]["description"] == "Your role\n- Build data products"


def test_parse_workday_jobs_uses_public_page_description() -> None:
    jobs = job_sources.parse_workday_jobs(
        {"jobPostings": [{
            "title": "Senior Data Engineer",
            "externalPath": "/job/Berlin/Senior-Data-Engineer_1",
            "timeType": "Full time",
            "locationsText": "Berlin",
            "postedOn": "Posted 3 Days Ago",
        }]},
        company_name="Zalando",
        careers_url="https://zalando.wd3.myworkdayjobs.com/ZalandoSiteWD",
        keywords=("data engineer",),
        today=date(2026, 7, 24),
        description_loader=lambda _: '<meta property="og:description" content="Build Databricks pipelines.">',
    )

    assert validate_linkedin_schema(jobs[0]) == []
    assert jobs[0]["publishedAt"] == "2026-07-21"
    assert jobs[0]["description"] == "Build Databricks pipelines."
