from fitcv.ingest import validate_linkedin_schema
from fitcv.personio_export import (
    build_personio_feed_url,
    extract_personio_job_page_description,
    parse_personio_jobs,
)


PERSONIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>2337942</id>
    <office>Berlin</office>
    <additionalOffices><office>deutschlandweit</office></additionalOffices>
    <name>Data Engineer – Databricks (m/w/d)</name>
    <jobDescriptions>
      <jobDescription>
        <name>Tasks</name>
        <value><![CDATA[<ul><li>Build pipelines</li><li>Use Databricks</li></ul>]]></value>
      </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <yearsOfExperience>2-5</yearsOfExperience>
    <createdAt>2025-09-16T06:25:26+00:00</createdAt>
  </position>
  <position>
    <id>2</id>
    <office>Hamburg</office>
    <name>Sales Manager</name>
    <jobDescriptions>
      <jobDescription><name>Tasks</name><value><![CDATA[Sell products]]></value></jobDescription>
    </jobDescriptions>
  </position>
</workzag-jobs>
"""


def test_parse_personio_jobs_emits_fitcv_contract() -> None:
    jobs = parse_personio_jobs(
        PERSONIO_XML,
        company_name="areto consulting",
        careers_url="https://areto.jobs.personio.de",
        keywords=("data engineer",),
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert validate_linkedin_schema(job) == []
    assert job["jobUrl"] == "https://areto.jobs.personio.de/job/2337942"
    assert job["companyName"] == "areto consulting"
    assert job["location"] == "Berlin, deutschlandweit"
    assert job["publishedAt"] == "2025-09-16"
    assert job["contractType"] == "Full-time"
    assert job["experienceLevel"] == "Experienced (2-5 years)"
    assert "Build pipelines" in job["description"]
    assert "<li>" not in job["description"]


def test_build_personio_feed_url_rejects_non_personio_host() -> None:
    try:
        build_personio_feed_url("https://example.com/jobs")
    except ValueError as exc:
        assert "Personio" in str(exc)
    else:
        raise AssertionError("non-Personio host accepted")


def test_parse_personio_jobs_uses_detail_page_when_feed_description_is_empty() -> None:
    xml = PERSONIO_XML.replace(
        "<jobDescriptions>\n      <jobDescription>\n        <name>Tasks</name>\n"
        "        <value><![CDATA[<ul><li>Build pipelines</li><li>Use Databricks</li></ul>]]></value>\n"
        "      </jobDescription>\n    </jobDescriptions>",
        "<jobDescriptions />",
        1,
    )
    page_html = """
    <html><body><header>Navigation noise</header><main><h1>Your Responsibilities</h1>
    <p>Build a Microsoft Fabric data platform.</p></main><footer>Footer noise</footer></body></html>
    """

    jobs = parse_personio_jobs(
        xml,
        company_name="areto consulting",
        careers_url="https://areto.jobs.personio.de",
        keywords=("data engineer",),
        description_loader=lambda _: extract_personio_job_page_description(page_html),
    )

    assert len(jobs) == 1
    assert jobs[0]["description"] == "Your Responsibilities\nBuild a Microsoft Fabric data platform."
