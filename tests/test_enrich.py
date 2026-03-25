"""Tests for fitcv.enrich — all pure unit tests (no LLM calls)."""

import sys
import types

import pytest

from fitcv.enrich import (
    build_extraction_prompt,
    enrich_job,
    load_run_structured_jobs,
    load_structured_jobs,
    merge_scraped_and_enriched,
    parse_extraction_response,
)


# ── build_extraction_prompt ───────────────────────────────────────────────────

def test_build_extraction_prompt_includes_required_fields() -> None:
    prompt = build_extraction_prompt(
        description="Deine Aufgaben\n * Du arbeitest im Bereich Business Intelligence...",
        scraped_metadata={"title": "Data Analyst", "experienceLevel": "Entry level"},
    )
    assert "required_skills" in prompt
    assert "location_type" in prompt
    assert "job_family" in prompt
    assert "seniority" in prompt
    # must_have_vs_nice_to_have must NOT appear — deferred to v2
    assert "must_have_vs_nice_to_have" not in prompt


def test_build_extraction_prompt_includes_domain_and_job_family() -> None:
    prompt = build_extraction_prompt(
        description="Role in the banking sector",
        scraped_metadata={"sector": "Banking"},
    )
    assert "job_family" in prompt
    assert "domain" in prompt


def test_build_extraction_prompt_contains_description_text() -> None:
    description = "We need SQL and Python skills for this unique role."
    prompt = build_extraction_prompt(description=description, scraped_metadata={})
    assert "SQL" in prompt


def test_build_extraction_prompt_requires_all_keys_present() -> None:
    prompt = build_extraction_prompt(description="Remote SQL role", scraped_metadata={})
    assert "Every schema key must be present" in prompt
    assert "Use [] for unknown list fields" in prompt
    assert "Use null for unknown scalar fields" in prompt


# ── parse_extraction_response — valid JSON ────────────────────────────────────

def test_parse_extraction_response_valid_json() -> None:
    raw = '{"required_skills": ["SQL", "Python"], "location_type": "hybrid", "job_family": "data_analytics"}'
    result = parse_extraction_response(raw)
    assert result["errors"] == []
    assert "SQL" in result["parsed"]["required_skills"]
    assert result["parsed"]["location_type"] == "hybrid"
    assert result["raw_response"] == raw


def test_parse_extraction_response_malformed_json() -> None:
    result = parse_extraction_response("not json at all")
    assert len(result["errors"]) > 0
    assert result["parsed"] == {}     # empty fallback, not a crash
    assert result["raw_response"] == "not json at all"


def test_parse_extraction_response_markdown_fenced_json() -> None:
    raw = '```json\n{"required_skills": ["SQL"]}\n```'
    result = parse_extraction_response(raw)
    assert result["errors"] == []
    assert result["parsed"]["required_skills"] == ["SQL"]


def test_parse_extraction_response_repairs_missing_array_commas() -> None:
    raw = '{"required_skills": ["SQL" "Python"], "location_type": "remote"}'
    result = parse_extraction_response(raw)
    assert result["errors"] == []
    assert result["parsed"]["required_skills"] == ["SQL", "Python"]
    assert result["parsed"]["location_type"] == "remote"


def test_parse_extraction_response_missing_fields_get_defaults() -> None:
    raw = '{"required_skills": ["SQL"]}'
    result = parse_extraction_response(raw)
    assert result["parsed"].get("preferred_skills", []) == []
    assert result["parsed"].get("location_type") is None


def test_parse_extraction_response_normalizes_location_type_enum() -> None:
    raw = '{"location_type": "Remote"}'
    result = parse_extraction_response(raw)
    assert result["parsed"]["location_type"] == "remote"  # lowercased


def test_parse_extraction_response_bad_enum_returns_none() -> None:
    raw = '{"location_type": "in-person-hybrid-flexible"}'
    result = parse_extraction_response(raw)
    assert result["parsed"]["location_type"] is None     # unknown enum → null


def test_parse_extraction_response_null_list_coerced_to_empty() -> None:
    raw = '{"required_skills": null, "location_type": "remote"}'
    result = parse_extraction_response(raw)
    assert result["parsed"]["required_skills"] == []     # null list → []
    assert result["errors"] == []


def test_parse_extraction_response_unknown_keys_ignored() -> None:
    raw = '{"required_skills": ["SQL"], "invented_field": "foo"}'
    result = parse_extraction_response(raw)
    assert "invented_field" not in result["parsed"]
    assert result["errors"] == []


def test_parse_extraction_response_seniority_normalized() -> None:
    raw = '{"seniority": "Senior"}'
    result = parse_extraction_response(raw)
    assert result["parsed"]["seniority"] == "senior"


def test_parse_extraction_response_bad_seniority_returns_none() -> None:
    raw = '{"seniority": "very experienced"}'
    result = parse_extraction_response(raw)
    assert result["parsed"]["seniority"] is None


# ── merge_scraped_and_enriched ────────────────────────────────────────────────

def test_merge_scraped_and_enriched_preserves_scraped_fields() -> None:
    scraped = {"job_url": "url1", "title": "DA", "company_name": "ACME", "contract_type": "Full-time"}
    enriched = {"required_skills": ["SQL"], "job_family": "analytics"}
    merged = merge_scraped_and_enriched(scraped, enriched)
    assert merged["title"] == "DA"
    assert merged["required_skills"] == ["SQL"]


def test_merge_scraped_and_enriched_adds_audit_fields() -> None:
    scraped = {"job_url": "url1", "title": "DE"}
    enriched = {"required_skills": ["SQL"]}
    merged = merge_scraped_and_enriched(scraped, enriched)
    assert "enrichment_model" in merged
    assert "enrichment_version" in merged
    assert "enriched_at" in merged


def test_merge_scraped_and_enriched_uses_config_model() -> None:
    scraped = {"job_url": "url1", "title": "DE"}
    enriched = {}
    config = {"ai_score_model": "gemini-2.0-flash", "enrichment_version": "v1"}
    merged = merge_scraped_and_enriched(scraped, enriched, config=config)
    assert merged["enrichment_model"] == "gemini-2.0-flash"
    assert merged["enrichment_version"] == "v1"


def test_load_structured_jobs_uses_explicit_staging_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeSchemaField:
        def __init__(self, name: str, field_type: str, mode: str = "NULLABLE") -> None:
            self.name = name
            self.field_type = field_type
            self.mode = mode

    class FakeLoadJobConfig:
        def __init__(self, **kwargs: object) -> None:
            captured["job_config"] = kwargs

    class FakeJob:
        def result(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        def load_table_from_json(self, rows: list[dict[str, object]], table: str, job_config: object) -> FakeJob:
            captured["rows"] = rows
            captured["table"] = table
            captured["load_job_config_obj"] = job_config
            return FakeJob()

        def query(self, sql: str) -> FakeJob:
            captured["merge_sql"] = sql
            return FakeJob()

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        LoadJobConfig=FakeLoadJobConfig,
        SchemaField=FakeSchemaField,
        SourceFormat=types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON"),
    )
    fake_service_account = types.SimpleNamespace(
        Credentials=types.SimpleNamespace(
            from_service_account_file=lambda path: "creds"
        )
    )
    fake_google_cloud = types.SimpleNamespace(bigquery=fake_bigquery)
    fake_google_oauth2 = types.SimpleNamespace(service_account=fake_service_account)

    monkeypatch.setitem(sys.modules, "google.cloud", fake_google_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.oauth2", fake_google_oauth2)
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_service_account)

    load_structured_jobs(
        enriched=[{"job_url": "url1", "salary_min": None, "salary_max": None}],
        config={
            "gcp_project": "fitcv-491123",
            "bigquery_dataset": "fitcv",
            "service_account_key": "/tmp/key.json",
        },
    )

    job_config_kwargs = captured["job_config"]
    assert isinstance(job_config_kwargs, dict)
    schema = job_config_kwargs["schema"]
    assert isinstance(schema, list)
    salary_min = next(field for field in schema if field.name == "salary_min")
    salary_max = next(field for field in schema if field.name == "salary_max")
    applications_count = next(field for field in schema if field.name == "applications_count")
    assert salary_min.field_type == "FLOAT64"
    assert salary_max.field_type == "FLOAT64"
    assert applications_count.field_type == "INT64"


def test_enrich_batch_retries_resource_exhausted_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.enrich import enrich_batch

    attempts = {"count": 0}
    sleeps: list[float] = []

    class FakeResourceExhausted(Exception):
        pass

    def fake_enrich_job(job: dict[str, object], config: dict[str, object]) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise FakeResourceExhausted("quota")
        return {"job_url": "url1"}

    fake_exceptions = types.SimpleNamespace(ResourceExhausted=FakeResourceExhausted)

    monkeypatch.setattr("fitcv.enrich.enrich_job", fake_enrich_job)
    monkeypatch.setitem(sys.modules, "google.api_core.exceptions", fake_exceptions)
    monkeypatch.setattr("time.sleep", lambda secs: sleeps.append(secs))

    result = enrich_batch(
        normalized_jobs=[{"job_url": "url1"}],
        config={"enrichment_sleep_secs": 1.5, "enrichment_max_retries": 1},
    )

    assert result == [{"job_url": "url1"}]
    assert attempts["count"] == 2
    assert sleeps == [1.5]


def test_enrich_batch_retries_genai_client_error_429_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.enrich import enrich_batch

    attempts = {"count": 0}
    sleeps: list[float] = []

    class FakeResourceExhausted(Exception):
        pass

    class FakeClientError(Exception):
        def __init__(self, status_code: int) -> None:
            super().__init__(f"status={status_code}")
            self.status_code = status_code

    def fake_enrich_job(job: dict[str, object], config: dict[str, object]) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise FakeClientError(429)
        return {"job_url": "url1"}

    fake_exceptions = types.SimpleNamespace(ResourceExhausted=FakeResourceExhausted)
    fake_errors = types.SimpleNamespace(ClientError=FakeClientError)
    fake_genai = types.SimpleNamespace(errors=fake_errors)
    fake_google = types.SimpleNamespace(genai=fake_genai)

    monkeypatch.setattr("fitcv.enrich.enrich_job", fake_enrich_job)
    monkeypatch.setitem(sys.modules, "google.api_core.exceptions", fake_exceptions)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.errors", fake_errors)
    monkeypatch.setattr("time.sleep", lambda secs: sleeps.append(secs))

    result = enrich_batch(
        normalized_jobs=[{"job_url": "url1"}],
        config={"enrichment_sleep_secs": 2.0, "enrichment_max_retries": 1},
    )

    assert result == [{"job_url": "url1"}]
    assert attempts["count"] == 2
    assert sleeps == [2.0]


def test_enrich_batch_uses_exponential_backoff_for_repeated_429s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.enrich import enrich_batch

    attempts = {"count": 0}
    sleeps: list[float] = []

    class FakeResourceExhausted(Exception):
        pass

    class FakeClientError(Exception):
        def __init__(self, status_code: int) -> None:
            super().__init__(f"status={status_code}")
            self.status_code = status_code

    def fake_enrich_job(job: dict[str, object], config: dict[str, object]) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise FakeClientError(429)
        return {"job_url": "url1"}

    fake_exceptions = types.SimpleNamespace(ResourceExhausted=FakeResourceExhausted)
    fake_errors = types.SimpleNamespace(ClientError=FakeClientError)
    fake_genai = types.SimpleNamespace(errors=fake_errors)
    fake_google = types.SimpleNamespace(genai=fake_genai)

    monkeypatch.setattr("fitcv.enrich.enrich_job", fake_enrich_job)
    monkeypatch.setitem(sys.modules, "google.api_core.exceptions", fake_exceptions)
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.errors", fake_errors)
    monkeypatch.setattr("time.sleep", lambda secs: sleeps.append(secs))

    result = enrich_batch(
        normalized_jobs=[{"job_url": "url1"}],
        config={"enrichment_sleep_secs": 1.5, "enrichment_max_retries": 2},
    )

    assert result == [{"job_url": "url1"}]
    assert attempts["count"] == 3
    assert sleeps == [1.5, 3.0]


def test_enrich_job_uses_google_genai_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        text = '{"required_skills": ["SQL"], "location_type": "remote"}'

    class FakeModels:
        def generate_content(
            self, *, model: str, contents: str, config: dict[str, object]
        ) -> FakeResponse:
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs
            self.models = FakeModels()

    fake_genai = types.SimpleNamespace(Client=FakeClient)
    fake_google = types.SimpleNamespace(
        auth=types.SimpleNamespace(default=lambda scopes=None: ("creds", "project"))
    )

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.auth", fake_google.auth)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    setattr(fake_google, "genai", fake_genai)

    result = enrich_job(
        job={
            "job_url": "https://example.com/jobs/1",
            "title": "Data Engineer",
            "description": "Build pipelines with SQL.",
            "experience_level": "Mid-Senior level",
            "contract_type": "Full-time",
            "sector": "Software",
            "location": "Remote",
        },
        config={
            "gcp_project": "fitcv-491123",
            "vertex_location": "us-central1",
            "gemini_model": "gemini-2.5-flash",
            "ai_score_model": "gemini-2.5-flash",
        },
    )

    assert result["required_skills"] == ["SQL"]
    assert result["location_type"] == "remote"
    assert captured["model"] == "gemini-2.5-flash"
    config = captured["config"]
    assert isinstance(config, dict)
    assert config["response_mime_type"] == "application/json"
    schema = config["response_json_schema"]
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert schema["required"] == [
        "required_skills",
        "preferred_skills",
        "responsibilities",
        "tech_stack",
        "keywords",
        "location_type",
        "seniority",
        "domain",
        "job_family",
        "years_experience_min",
        "years_experience_max",
    ]
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert properties["required_skills"]["type"] == "array"
    assert properties["location_type"]["enum"] == ["remote", "hybrid", "onsite"]
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs["vertexai"] is True
    assert client_kwargs["location"] == "us-central1"


def test_enrich_job_prefers_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        text = '{"required_skills": ["SQL"]}'

    class FakeModels:
        def generate_content(
            self, *, model: str, contents: str, config: dict[str, object]
        ) -> FakeResponse:
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs
            self.models = FakeModels()

    fake_genai = types.SimpleNamespace(Client=FakeClient)
    fake_google = types.SimpleNamespace(
        auth=types.SimpleNamespace(default=lambda scopes=None: (_ for _ in ()).throw(AssertionError("google.auth.default should not be called")))
    )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.auth", fake_google.auth)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    setattr(fake_google, "genai", fake_genai)

    result = enrich_job(
        job={"job_url": "https://example.com/jobs/1", "description": "SQL"},
        config={"gcp_project": "fitcv-491123", "gemini_model": "gemini-2.5-flash"},
    )

    assert result["required_skills"] == ["SQL"]
    client_kwargs = captured["client_kwargs"]
    assert isinstance(client_kwargs, dict)
    assert client_kwargs["api_key"] == "test-key"
    assert "vertexai" not in client_kwargs
    config = captured["config"]
    assert isinstance(config, dict)
    assert config["response_mime_type"] == "application/json"


# ── load_run_structured_jobs ──────────────────────────────────────────────────

def test_load_run_structured_jobs_inserts_to_correct_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeSchemaField:
        def __init__(self, name: str, field_type: str, mode: str = "NULLABLE") -> None:
            self.name = name
            self.field_type = field_type
            self.mode = mode

    class FakeLoadJobConfig:
        def __init__(self, **kwargs: object) -> None:
            captured["job_config"] = kwargs

    class FakeJob:
        def result(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        def load_table_from_json(
            self, rows: list[dict[str, object]], table: str, job_config: object
        ) -> FakeJob:
            captured["rows"] = rows
            captured["table"] = table
            captured["load_job_config_obj"] = job_config
            return FakeJob()

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        LoadJobConfig=FakeLoadJobConfig,
        SchemaField=FakeSchemaField,
        SourceFormat=types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON"),
        WriteDisposition=types.SimpleNamespace(WRITE_APPEND="WRITE_APPEND"),
    )
    fake_service_account = types.SimpleNamespace(
        Credentials=types.SimpleNamespace(
            from_service_account_file=lambda path: "creds"
        )
    )
    fake_google_cloud = types.SimpleNamespace(bigquery=fake_bigquery)
    fake_google_oauth2 = types.SimpleNamespace(service_account=fake_service_account)

    monkeypatch.setitem(sys.modules, "google.cloud", fake_google_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.oauth2", fake_google_oauth2)
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_service_account)

    enriched = [
        {
            "job_url": "https://example.com/1",
            "title": "Data Engineer",
            "company_name": "ACME",
            "location": "Remote",
            "contract_type": "Full-time",
            "experience_level": "mid",
            "published_at": "2026-01-01",
            "location_type": "remote",
            "seniority": "senior",
            "required_skills": ["SQL", "Python"],
            "preferred_skills": [],
            "responsibilities": [],
            "domain": "fintech",
            "tech_stack": [],
            "years_experience_min": 3,
            "years_experience_max": None,
            "keywords": [],
            "job_family": "data_engineering",
            "description_cleaned": "Build pipelines.",
            "enrichment_version": "v1",
            "enrichment_model": "gemini-2.0-flash",
            "enriched_at": "2026-01-01T00:00:00+00:00",
            # extra fields NOT in run_structured_jobs schema:
            "company_id": "123",
            "sector": "Software",
            "salary_min": 50000.0,
            "salary_max": 80000.0,
            "salary_currency": "EUR",
            "applications_count": 10,
        }
    ]

    load_run_structured_jobs(
        enriched=enriched,
        run_id="run-abc",
        config={
            "gcp_project": "fitcv-491123",
            "bigquery_dataset": "fitcv",
            "service_account_key": "/tmp/key.json",
        },
    )

    table = captured["table"]
    assert "run_structured_jobs" in table, f"Expected run_structured_jobs table, got: {table}"
    assert "structured_jobs" not in table.replace("run_structured_jobs", ""), (
        "Table must be run_structured_jobs, not structured_jobs"
    )


def test_load_run_structured_jobs_injects_run_id_into_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeJob:
        def result(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_table_from_json(
            self, rows: list[dict[str, object]], table: str, job_config: object
        ) -> FakeJob:
            captured["rows"] = rows
            return FakeJob()

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        LoadJobConfig=lambda **kw: None,
        SchemaField=lambda name, ft, mode="NULLABLE": None,
        SourceFormat=types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON"),
        WriteDisposition=types.SimpleNamespace(WRITE_APPEND="WRITE_APPEND"),
    )
    fake_service_account = types.SimpleNamespace(
        Credentials=types.SimpleNamespace(
            from_service_account_file=lambda path: "creds"
        )
    )
    monkeypatch.setitem(sys.modules, "google.cloud", types.SimpleNamespace(bigquery=fake_bigquery))
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.oauth2", types.SimpleNamespace(service_account=fake_service_account))
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_service_account)

    enriched = [{"job_url": "https://example.com/1", "title": "DE"}]
    load_run_structured_jobs(
        enriched=enriched,
        run_id="run-xyz",
        config={
            "gcp_project": "fitcv-491123",
            "bigquery_dataset": "fitcv",
            "service_account_key": "/tmp/key.json",
        },
    )

    rows = captured["rows"]
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-xyz"
    assert rows[0]["job_url"] == "https://example.com/1"


def test_load_run_structured_jobs_uses_write_append(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeJob:
        def result(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_table_from_json(
            self, rows: list[dict[str, object]], table: str, job_config: object
        ) -> FakeJob:
            captured["job_config_kwargs"] = getattr(job_config, "_kwargs", {})
            return FakeJob()

    class FakeLoadJobConfig:
        def __init__(self, **kwargs: object) -> None:
            self._kwargs = kwargs

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        LoadJobConfig=FakeLoadJobConfig,
        SchemaField=lambda name, ft, mode="NULLABLE": None,
        SourceFormat=types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON"),
        WriteDisposition=types.SimpleNamespace(WRITE_APPEND="WRITE_APPEND"),
    )
    fake_service_account = types.SimpleNamespace(
        Credentials=types.SimpleNamespace(
            from_service_account_file=lambda path: "creds"
        )
    )
    monkeypatch.setitem(sys.modules, "google.cloud", types.SimpleNamespace(bigquery=fake_bigquery))
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.oauth2", types.SimpleNamespace(service_account=fake_service_account))
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_service_account)

    enriched = [{"job_url": "https://example.com/1"}]
    load_run_structured_jobs(
        enriched=enriched,
        run_id="run-xyz",
        config={
            "gcp_project": "fitcv-491123",
            "bigquery_dataset": "fitcv",
            "service_account_key": "/tmp/key.json",
        },
    )

    kwargs = captured["job_config_kwargs"]
    assert kwargs.get("write_disposition") == "WRITE_APPEND", (
        f"Expected WRITE_APPEND, got: {kwargs.get('write_disposition')}"
    )


def test_load_run_structured_jobs_excludes_schema_extra_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extra fields from structured_jobs (company_id, sector, salary_*) must not appear in rows."""
    captured: dict[str, object] = {}

    class FakeJob:
        def result(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def load_table_from_json(
            self, rows: list[dict[str, object]], table: str, job_config: object
        ) -> FakeJob:
            captured["rows"] = rows
            return FakeJob()

    fake_bigquery = types.SimpleNamespace(
        Client=FakeClient,
        LoadJobConfig=lambda **kw: None,
        SchemaField=lambda name, ft, mode="NULLABLE": None,
        SourceFormat=types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON"),
        WriteDisposition=types.SimpleNamespace(WRITE_APPEND="WRITE_APPEND"),
    )
    fake_service_account = types.SimpleNamespace(
        Credentials=types.SimpleNamespace(
            from_service_account_file=lambda path: "creds"
        )
    )
    monkeypatch.setitem(sys.modules, "google.cloud", types.SimpleNamespace(bigquery=fake_bigquery))
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.oauth2", types.SimpleNamespace(service_account=fake_service_account))
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", fake_service_account)

    enriched = [
        {
            "job_url": "https://example.com/1",
            "company_id": "SHOULD_NOT_APPEAR",
            "sector": "SHOULD_NOT_APPEAR",
            "salary_min": 99999.0,
            "salary_max": 99999.0,
            "salary_currency": "USD",
            "applications_count": 42,
        }
    ]
    load_run_structured_jobs(
        enriched=enriched,
        run_id="run-abc",
        config={
            "gcp_project": "fitcv-491123",
            "bigquery_dataset": "fitcv",
            "service_account_key": "/tmp/key.json",
        },
    )

    row = captured["rows"][0]  # type: ignore[index]
    for excluded in ("company_id", "sector", "salary_min", "salary_max", "salary_currency", "applications_count"):
        assert excluded not in row, f"Field {excluded!r} should not be in run_structured_jobs row"
