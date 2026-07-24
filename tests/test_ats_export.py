from datetime import date

import fitcv.ats_export as ats_export
from fitcv.ats_export import parse_greenhouse_jobs, parse_workday_jobs
from fitcv.ingest import validate_linkedin_schema


def test_parse_greenhouse_jobs_emits_fitcv_contract() -> None:
    jobs = parse_greenhouse_jobs(
        {
            "jobs": [
                {
                    "id": 4929240101,
                    "title": "Data Engineer (all genders)",
                    "absolute_url": "https://job-boards.eu.greenhouse.io/gropyus/jobs/4929240101",
                    "location": {"name": "Berlin, Berlin, Germany"},
                    "first_published": "2026-07-15T17:56:24-04:00",
                    "content": "<h2>Your role</h2><ul><li>Build data products</li></ul>",
                    "metadata": [
                        {"name": "Team", "value": ["Tech"]},
                        {"name": "Type of Employment", "value": ["Employee"]},
                    ],
                },
                {
                    "id": 2,
                    "title": "Product Manager",
                    "absolute_url": "https://job-boards.eu.greenhouse.io/gropyus/jobs/2",
                    "content": "Product work",
                },
            ]
        },
        company_name="GROPYUS",
        careers_url="https://job-boards.eu.greenhouse.io/gropyus",
        keywords=("data engineer",),
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert validate_linkedin_schema(job) == []
    assert job["publishedAt"] == "2026-07-15"
    assert job["contractType"] == "Employee"
    assert job["experienceLevel"] == ""
    assert job["workType"] == "Tech"
    assert job["description"] == "Your role\n- Build data products"


def test_parse_workday_jobs_uses_public_page_description() -> None:
    jobs = parse_workday_jobs(
        {
            "jobPostings": [
                {
                    "title": "Senior Data Engineer - Marketing Platform (all genders)",
                    "externalPath": "/job/Berlin/Software-Engineer---Marketing-Platform_2724020-1",
                    "timeType": "Full time",
                    "locationsText": "Berlin",
                    "postedOn": "Posted 3 Days Ago",
                },
                {
                    "title": "Product Designer",
                    "externalPath": "/job/Berlin/Product-Designer_1",
                },
            ]
        },
        company_name="Zalando",
        careers_url="https://zalando.wd3.myworkdayjobs.com/ZalandoSiteWD",
        keywords=("data engineer",),
        today=date(2026, 7, 24),
        description_loader=lambda _: (
            '<meta property="og:description" content="Build Databricks and Delta Lake pipelines.">'
        ),
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert validate_linkedin_schema(job) == []
    assert job["jobUrl"].endswith("/job/Berlin/Software-Engineer---Marketing-Platform_2724020-1")
    assert job["publishedAt"] == "2026-07-21"
    assert job["contractType"] == "Full time"
    assert job["experienceLevel"] == "Senior"
    assert job["description"] == "Build Databricks and Delta Lake pipelines."


def test_https_opener_adds_certifi_to_default_trust(monkeypatch) -> None:
    loaded: list[str] = []

    class FakeContext:
        def load_verify_locations(self, *, cafile: str) -> None:
            loaded.append(cafile)

    monkeypatch.setattr(ats_export.ssl, "create_default_context", FakeContext)
    monkeypatch.setattr(ats_export.certifi, "where", lambda: "current-ca.pem")
    monkeypatch.setattr(ats_export, "HTTPSHandler", lambda *, context: context)
    monkeypatch.setattr(ats_export, "build_opener", lambda *handlers: handlers)

    ats_export._build_https_opener()

    assert loaded == ["current-ca.pem"]
