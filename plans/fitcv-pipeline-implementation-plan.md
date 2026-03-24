# FitCV Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end pipeline that ingests raw job postings, enriches them into structured fields, builds a structured candidate profile, performs hybrid matching (rule + vector + AI), retrieves per-job evidence, generates tailored CVs, and tracks versions with a feedback loop—all on BigQuery.

**Architecture:** Four-layer design — (1) Understanding Jobs (normalize → enrich → structured JD schema), (2) Understanding You (structured candidate profile with projects / skills / achievements), (3) Matching (rule filter → VECTOR_SEARCH → AI.SCORE → composite final score), (4) Personalization (per-job evidence retrieval → gap analysis → template-based CV generation → validation → versioned output + feedback loop). Data lives in BigQuery dataset `fitcv`. Python orchestration scripts live under `src/fitcv/`. Bruin is used for BigQuery asset management. Service account: `fitcv-491123-51c030d71e07.json`.

**Tech Stack:** BigQuery (storage + ML + vector search), Python 3.11+, `google-cloud-bigquery`, `google-cloud-aiplatform`, Bruin CLI, Vertex AI text-embedding model, JSON/YAML config.

**Data Source:** LinkedIn Jobs Scraper (Apify). Sample file: `sample/data-dataset_linkedin-jobs-scraper_*.json`.

---

## Data Source Reference — LinkedIn Jobs Scraper Schema

The input data is a **flat JSON array** of job objects. Each object has these fields:

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `title` | string | `"Data Analyst - Retail Banking"` | Already structured |
| `location` | string | `"Berlin, Berlin, Germany"` | City, state, country |
| `postedTime` | string | `"3 weeks ago"` | Relative human-readable |
| `publishedAt` | string | `"2026-01-29"` | ISO date |
| `jobUrl` | string | LinkedIn URL | **Natural unique key** |
| `companyName` | string | `"DKB Service GmbH"` | Already structured |
| `companyUrl` | string | LinkedIn company URL | |
| `description` | string | Full JD text | **`\n`-delimited, NOT HTML** |
| `applicationsCount` | string | `"61 applicants"` / `"Over 200 applicants"` | Parse to int |
| `contractType` | string | `"Full-time"` / `"Part-time"` / `"Internship"` / `"Contract"` | Already structured |
| `experienceLevel` | string | `"Entry level"` / `"Mid-Senior level"` / `"Associate"` / `"Director"` / `"Internship"` | Already structured |
| `workType` | string | `"Information Technology"` | |
| `sector` | string | `"Banking"` | |
| `salary` | string | `""` or `"€45,000.00/yr - €55,000.00/yr"` | Often empty |
| `posterFullName` | string | `""` or name | |
| `posterProfileUrl` | string | `""` or URL | |
| `companyId` | string | `"1355705"` | LinkedIn internal ID |
| `applyUrl` | string | URL | External or LinkedIn |
| `applyType` | string | `"EASY_APPLY"` / `"EXTERNAL"` | |
| `benefits` | string | `""` | Usually empty (in description instead) |

### Key observations for pipeline design

1. **No HTML to strip** — `description` uses `\n` newlines and `*` bullet points, not `<p>` tags
2. **Structured metadata already available** — `companyName`, `contractType`, `experienceLevel`, `sector`, `location` are pre-extracted by the scraper
3. **Heavy deduplication needed** — same company (e.g. Mindrift) posts identical JDs across multiple cities with different `jobUrl`s. Dedupe by `companyId` + `title` + `description` hash, not just by URL
4. **`jobUrl` as natural key** — no need to hash source+URL; `jobUrl` is unique per posting
5. **Enrichment is targeted** — only fields *not* in the scraped metadata need LLM extraction: `required_skills`, `preferred_skills`, `responsibilities`, `domain`, `tech_stack`, `years_experience_*`, `keywords`, `job_family`, `location_type`, `must_have_vs_nice_to_have`
6. **`salary` is sparse** — most entries are `""`. Parse when available, skip when not
7. **`experienceLevel` may be unreliable** — e.g. "5+ years required" JDs labeled `"Entry level"`. Cross-check with enriched `years_experience_min`

---

## File Structure

```text
JOB-PROJECT/
├── .env.yaml                      # credentials & project config
├── bruin.yml                      # Bruin pipeline config (fitcv)
├── src/
│   └── fitcv/
│       ├── __init__.py
│       ├── config.py              # load .env.yaml, project constants
│       ├── ingest.py              # read raw jobs JSON, push to BQ
│       ├── normalize.py           # clean / deduplicate / standardize
│       ├── enrich.py              # LLM-based structured field extraction
│       ├── candidate.py           # structured candidate profile CRUD
│       ├── embeddings.py          # generate embeddings (JD + candidate)
│       ├── rule_filter.py         # rule-based pre-filter
│       ├── vector_search.py       # BQ VECTOR_SEARCH wrapper
│       ├── ai_score.py            # BQ AI.SCORE wrapper
│       ├── ranking.py             # composite final score
│       ├── evidence.py            # per-job evidence retrieval
│       ├── gap_analysis.py        # matched / missing / risk
│       ├── cv_generator.py        # template-based CV generation
│       ├── validator.py           # hallucination / constraint checks
│       ├── tracker.py             # versioning + feedback loop
│       └── pipeline.py            # orchestrate full run
├── assets/
│   └── bigquery/
│       ├── raw_jobs.sql           # Bruin DDL asset
│       ├── structured_jobs.sql
│       ├── candidate_profile.sql
│       ├── candidate_experiences.sql
│       ├── candidate_projects.sql
│       ├── candidate_skills.sql
│       ├── candidate_achievements.sql
│       ├── job_embeddings.sql
│       ├── candidate_embeddings.sql
│       ├── rule_filter_results.sql
│       ├── vector_shortlist.sql
│       ├── ai_score_results.sql
│       ├── final_ranking.sql
│       ├── evidence_retrieval.sql
│       ├── gap_analysis.sql
│       ├── generated_cvs.sql
│       ├── cv_versions.sql
│       └── application_tracker.sql
├── sample/
│   └── data-dataset_linkedin-jobs-scraper_*.json  # real LinkedIn scraper data
├── data/
│   ├── sample_jobs.json           # small test fixture (5–10 jobs from sample/)
│   └── candidate_profile.yaml    # your structured profile seed
├── templates/
│   └── cv_template.md             # CV markdown template
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_ingest.py
│   ├── test_normalize.py
│   ├── test_enrich.py
│   ├── test_candidate.py
│   ├── test_embeddings.py
│   ├── test_rule_filter.py
│   ├── test_vector_search.py
│   ├── test_ai_score.py
│   ├── test_ranking.py
│   ├── test_evidence.py
│   ├── test_gap_analysis.py
│   ├── test_cv_generator.py
│   ├── test_validator.py
│   └── test_tracker.py
├── requirements.txt
└── pyproject.toml
```

---

## Layer 1 — Understanding Jobs

### Task 1: Project Scaffold & Configuration

**Files:**

- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/fitcv/__init__.py`
- Create: `src/fitcv/config.py`
- Create: `.env.yaml`
- Create: `data/sample_jobs.json`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [x] **Step 1: Create `pyproject.toml`**

  Minimal project metadata. Set `name = "fitcv"`, `requires-python = ">=3.11"`.

- [x] **Step 2: Create `requirements.txt`**

  ```text
  google-cloud-bigquery>=3.20
  google-cloud-aiplatform>=1.40
  pyyaml>=6.0
  jinja2>=3.1
  pytest>=8.0
  ```

- [x] **Step 3: Write `.env.yaml`**

  ```yaml
  gcp_project: "fitcv-491123"
  bigquery_dataset: "fitcv"
  service_account_key: "fitcv-491123-51c030d71e07.json"
  embedding_model: "text-embedding-005"
  ai_score_model: "gemini-2.0-flash"
  location: "US"
  # Apify source (optional — leave blank to load from local file instead)
  apify_dataset_id: "your-dataset-id"   # from the Apify console
  apify_token: "your-token"             # keep out of git; set via env var in CI
  ```

  > **Secret handling:** `apify_token` is sensitive. For local dev it can live in `.env.yaml` (which must be in `.gitignore`). In CI/CD, inject it as an environment variable and read it in `config.py` via `os.environ.get("APIFY_TOKEN")`.

- [x] **Step 4: Create `src/fitcv/__init__.py`**

  Empty `__init__.py`.

- [x] **Step 5: Write the failing test for config loading**

  ```python
  # tests/test_config.py
  from fitcv.config import load_config

  def test_load_config_returns_dict():
      cfg = load_config("../../.env.yaml")
      assert isinstance(cfg, dict)
      assert "gcp_project" in cfg
      assert "bigquery_dataset" in cfg
  ```

- [x] **Step 6: Run test — expect FAIL**

  ```bash
  pytest tests/test_config.py -v
  ```

  Expected: FAIL — `ModuleNotFoundError: No module named 'fitcv'`

- [x] **Step 7: Implement `src/fitcv/config.py`**

  ```python
  """Load project configuration from .env.yaml."""
  from pathlib import Path
  import yaml

  # Keys that must always be present
  _REQUIRED_KEYS = ["gcp_project", "bigquery_dataset", "service_account_key"]
  # Optional keys — present only when using Apify API source
  _APIFY_KEYS = ["apify_dataset_id", "apify_token"]

  def load_config(path: str | Path = ".env.yaml") -> dict:
      path = Path(path)
      if not path.exists():
          raise FileNotFoundError(f"Config file not found: {path}")
      with open(path) as f:
          cfg = yaml.safe_load(f)
      missing = [k for k in _REQUIRED_KEYS if k not in cfg]
      if missing:
          raise ValueError(f"Missing config keys: {missing}")
      return cfg
  ```

- [x] **Step 8: Run test — expect PASS**

  ```bash
  pytest tests/test_config.py -v
  ```

- [x] **Step 9: Create `data/sample_jobs.json`**

  Extract 5–10 representative jobs from `sample/data-dataset_linkedin-jobs-scraper_*.json`. Include:
  - 2 near-duplicate Mindrift postings (same company, different cities) for dedup testing
  - 1 job with salary data (e.g. YouLend `"€45,000.00/yr - €55,000.00/yr"`)
  - 1 internship (`contractType: "Internship"`, `experienceLevel: "Internship"`)
  - 1 German-language JD (e.g. DKB or AMAZONE)
  - 1 senior-level (`experienceLevel: "Mid-Senior level"`)
  
  The fixture must use the exact LinkedIn scraper field names (`title`, `location`, `jobUrl`, `companyName`, `description`, `contractType`, `experienceLevel`, `sector`, `salary`, etc.).

- [x] **Step 10: Create `tests/conftest.py`**

  Shared fixtures `sample_jobs_path` and `config`, plus an `integration` marker that auto-skips cloud-dependent tests when credentials are absent:

  ```python
  # tests/conftest.py
  import os
  from pathlib import Path
  import pytest

  def pytest_configure(config):
      config.addinivalue_line(
          "markers",
          "integration: mark test as requiring live GCP credentials (skipped by default)",
      )

  @pytest.fixture(autouse=True)
  def skip_integration_without_creds(request):
      if request.node.get_closest_marker("integration"):
          if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
              pytest.skip("Set GOOGLE_APPLICATION_CREDENTIALS to run integration tests")

  @pytest.fixture
  def sample_jobs_path() -> Path:
      return Path(__file__).parent.parent / "data" / "sample_jobs.json"

  @pytest.fixture
  def config() -> dict:
      from fitcv.config import load_config
      return load_config(Path(__file__).parent.parent / ".env.yaml")
  ```

  **Rule:** any test that calls BigQuery, Vertex AI, or Gemini **must** be decorated with `@pytest.mark.integration`. Pure logic (parsing, normalization, prompt construction, score math) has no marker and runs offline.

- [x] **Step 11: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): scaffold project with config loader and test fixtures"
  ```

---

### Task 2: Ingest Raw Jobs JSON

**Files:**

- Create: `src/fitcv/ingest.py`
- Create: `tests/test_ingest.py`
- Create: `assets/bigquery/raw_jobs.sql`

- [x] **Step 1: Define `raw_jobs` BigQuery schema**

  Write `assets/bigquery/raw_jobs.sql` — Bruin DDL asset creating table `fitcv.raw_jobs`. Schema mirrors the LinkedIn scraper output **1:1**, plus an ingestion audit column:

  | Column | Type | Description |
  |--------|------|-------------|
  | `job_url` | STRING | **Primary key** — the LinkedIn `jobUrl` |
  | `title` | STRING | Job title as scraped |
  | `location` | STRING | e.g. `"Berlin, Berlin, Germany"` |
  | `posted_time` | STRING | Relative time (`"3 weeks ago"`) |
  | `published_at` | DATE | ISO date from `publishedAt` |
  | `company_name` | STRING | From `companyName` |
  | `company_url` | STRING | From `companyUrl` |
  | `company_id` | STRING | LinkedIn internal company ID |
  | `description` | STRING | Full JD text (`\n`-delimited) |
  | `applications_count` | STRING | Raw string (`"61 applicants"`) |
  | `contract_type` | STRING | `"Full-time"` / `"Part-time"` / `"Internship"` etc. |
  | `experience_level` | STRING | `"Entry level"` / `"Mid-Senior level"` etc. |
  | `work_type` | STRING | e.g. `"Information Technology"` |
  | `sector` | STRING | e.g. `"Banking"` |
  | `salary` | STRING | Raw salary string or empty |
  | `apply_url` | STRING | External application URL |
  | `apply_type` | STRING | `"EASY_APPLY"` / `"EXTERNAL"` |
  | `raw_json` | JSON | Full original JSON object for auditability |
  | `ingested_at` | TIMESTAMP | Pipeline ingestion timestamp |

- [x] **Step 2: Write failing test for ingest**

  ```python
  # tests/test_ingest.py
  from fitcv.ingest import parse_jobs_file, validate_linkedin_schema

  def test_parse_jobs_file_returns_list(sample_jobs_path):
      jobs = parse_jobs_file(sample_jobs_path)
      assert isinstance(jobs, list)
      assert len(jobs) > 0

  def test_parse_jobs_file_has_required_fields(sample_jobs_path):
      jobs = parse_jobs_file(sample_jobs_path)
      required = ["title", "jobUrl", "companyName", "description", "contractType", "experienceLevel"]
      for job in jobs:
          for field in required:
              assert field in job, f"Missing field: {field}"

  def test_validate_linkedin_schema_rejects_malformed():
      bad_job = {"title": "Test"}  # missing jobUrl
      errors = validate_linkedin_schema(bad_job)
      assert len(errors) > 0
  ```

- [x] **Step 3: Run test — expect FAIL**

- [x] **Step 4: Implement `src/fitcv/ingest.py`**

  Functions:
  - `parse_jobs_file(path) -> list[dict]` — load JSON array from local file, validate it's a list
  - `fetch_from_apify(config) -> list[dict]` — fetch latest dataset items from Apify REST API using `apify_dataset_id` and `apify_token` from config; returns the same list[dict] format as `parse_jobs_file` so the rest of the pipeline is source-agnostic
  - `validate_linkedin_schema(job) -> list[str]` — check required LinkedIn scraper fields exist
  - `snake_case_keys(job) -> dict` — convert `companyName` → `company_name`, `jobUrl` → `job_url`, etc.
  - `prepare_raw_rows(jobs) -> list[dict]` — map LinkedIn scraper fields to `raw_jobs` BQ schema, store original JSON in `raw_json`
  - `load_to_bigquery(rows, config) -> int` — insert rows into `fitcv.raw_jobs` (`@pytest.mark.integration`)

  `fetch_from_apify` implementation:

  ```python
  def fetch_from_apify(config: dict) -> list[dict]:
      """Fetch all items from an Apify dataset via the REST API."""
      import json
      import urllib.request
      dataset_id = config["apify_dataset_id"]
      token = config["apify_token"]
      url = (
          f"https://api.apify.com/v2/datasets/{dataset_id}/items"
          f"?format=json&clean=true"
      )
      req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
      with urllib.request.urlopen(req) as resp:
          data = json.loads(resp.read())
      if not isinstance(data, list):
          raise ValueError("Apify API did not return a JSON array")
      return data
  ```

  Add a unit test for the Apify path using `unittest.mock.patch`:

  ```python
  # tests/test_ingest.py
  from unittest.mock import patch, MagicMock
  import json

  def test_fetch_from_apify_returns_list(sample_jobs_path):
      """Unit test — mocks urllib so no real HTTP call is made."""
      import urllib.request
      from fitcv.ingest import fetch_from_apify

      real_jobs = json.loads(sample_jobs_path.read_text())
      mock_resp = MagicMock()
      mock_resp.read.return_value = json.dumps(real_jobs).encode()
      mock_resp.__enter__ = lambda s: s
      mock_resp.__exit__ = MagicMock(return_value=False)

      with patch("urllib.request.urlopen", return_value=mock_resp):
          result = fetch_from_apify({"apify_dataset_id": "abc", "apify_token": "tok"})

      assert isinstance(result, list)
      assert len(result) == len(real_jobs)
  ```

- [x] **Step 5: Run test — expect PASS**

- [x] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): ingest LinkedIn scraper JSON into BigQuery"
  ```

---

### Task 3: Normalize Raw JDs

**Files:**

- Create: `src/fitcv/normalize.py`
- Create: `tests/test_normalize.py`

> **Note:** The LinkedIn scraper data is already well-structured (no HTML, consistent field names). Normalization focuses on: whitespace cleanup, near-duplicate detection (same JD posted in multiple cities), `applicationsCount` parsing, and `salary` parsing.

- [x] **Step 1: Write failing tests for normalization functions**

  ```python
  # tests/test_normalize.py
  from fitcv.normalize import (
      normalize_whitespace,
      deduplicate_jobs,
      deduplicate_near_duplicates,
      parse_applications_count,
      parse_salary,
  )

  def test_normalize_whitespace():
      assert normalize_whitespace("  hello   world  \n\n") == "hello world"

  def test_deduplicate_jobs_by_url():
      jobs = [
          {"job_url": "https://linkedin.com/job/1", "title": "DE"},
          {"job_url": "https://linkedin.com/job/1", "title": "DE"},
      ]
      assert len(deduplicate_jobs(jobs)) == 1

  def test_deduplicate_near_duplicates_same_company_same_description():
      jobs = [
          {"job_url": "url1", "company_id": "101", "title": "AI Trainer", "description": "Same JD text..."},
          {"job_url": "url2", "company_id": "101", "title": "AI Trainer", "description": "Same JD text..."},
      ]
      result = deduplicate_near_duplicates(jobs)
      assert len(result) == 1  # keeps first occurrence

  def test_parse_applications_count():
      assert parse_applications_count("61 applicants") == 61
      assert parse_applications_count("Over 200 applicants") == 200
      assert parse_applications_count("Be among the first 25 applicants") == 0
      assert parse_applications_count("") is None

  def test_parse_salary():
      result = parse_salary("€45,000.00/yr - €55,000.00/yr")
      assert result["min"] == 45000
      assert result["max"] == 55000
      assert result["currency"] == "EUR"
      assert parse_salary("") is None
  ```

- [x] **Step 2: Run test — expect FAIL**

- [x] **Step 3: Implement `src/fitcv/normalize.py`**

  Functions:
  - `normalize_whitespace(text) -> str` — collapse excessive whitespace/newlines
  - `deduplicate_jobs(jobs) -> list[dict]` — exact dedupe by `job_url`
  - `deduplicate_near_duplicates(jobs) -> list[dict]` — group by `company_id` + `title` + SHA-256 of `description`, keep first
  - `parse_applications_count(raw) -> int | None` — extract integer from `"61 applicants"`, `"Over 200 applicants"`, etc.
  - `parse_salary(raw) -> dict | None` — extract `{min, max, currency, period}` from salary strings
  - `normalize_job(job) -> dict` — orchestrate cleaning on one job
  - `normalize_batch(jobs) -> list[dict]` — apply normalization + deduplication to full list

- [x] **Step 4: Run test — expect PASS**

- [x] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): normalize LinkedIn scraper data with near-duplicate detection"
  ```

---

### Task 4: Enrich / Extract Structured JD Fields

**Files:**

- Create: `src/fitcv/enrich.py`
- Create: `tests/test_enrich.py`
- Create: `assets/bigquery/structured_jobs.sql`

> **Note:** The LinkedIn scraper already provides `title`, `companyName`, `location`, `contractType`, `experienceLevel`, `sector`. The enrichment step only needs to extract fields that are *buried in the `description` text* and not available as structured metadata. The enrichment prompt receives both the `description` text AND the scraped metadata so the LLM can cross-reference.

- [x] **Step 1: Define `structured_jobs` BigQuery schema**

  `assets/bigquery/structured_jobs.sql` — table `fitcv.structured_jobs`:

  | Column | Type | Source |
  |--------|------|--------|
  | `job_url` | STRING | **PK** — from scraper |
  | `title` | STRING | scraper `title` |
  | `company_name` | STRING | scraper `companyName` |
  | `company_id` | STRING | scraper `companyId` |
  | `location` | STRING | scraper `location` |
  | `contract_type` | STRING | scraper `contractType` |
  | `experience_level` | STRING | scraper `experienceLevel` — **raw LinkedIn label** (e.g. `"Entry level"`) |
  | `sector` | STRING | scraper `sector` |
  | `salary_min` | FLOAT64 | parsed from scraper `salary` |
  | `salary_max` | FLOAT64 | parsed from scraper `salary` |
  | `salary_currency` | STRING | parsed from scraper `salary` |
  | `applications_count` | INT64 | parsed from scraper |
  | `published_at` | DATE | scraper `publishedAt` |
  | `location_type` | STRING | **LLM-enriched**: canonical `remote` / `hybrid` / `onsite` (lowercase, no other values) |
  | `seniority` | STRING | **LLM-enriched**: normalized level inferred from JD text — `junior` / `mid` / `senior` / `lead`. **Distinct from `experience_level`**: e.g. scraper says `"Entry level"` but JD text says `"5+ years required"` → `seniority = mid` |
  | `required_skills` | ARRAY\<STRING\> | **LLM-enriched** |
  | `preferred_skills` | ARRAY\<STRING\> | **LLM-enriched** |
  | `responsibilities` | ARRAY\<STRING\> | **LLM-enriched** |
  | `domain` | STRING | **LLM-enriched**: **business/industry domain** (e.g. `banking`, `fintech`, `healthcare`, `retail`) |
  | `tech_stack` | ARRAY\<STRING\> | **LLM-enriched** |
  | `years_experience_min` | INT64 | **LLM-enriched** |
  | `years_experience_max` | INT64 | **LLM-enriched** |
  | `keywords` | ARRAY\<STRING\> | **LLM-enriched** |
  | `job_family` | STRING | **LLM-enriched**: **role category** (e.g. `data_engineering`, `analytics`, `data_science`, `ml_engineering`). Distinct from `domain`: `job_family` = what you do, `domain` = what industry you do it in |
  | `description_cleaned` | STRING | normalized `description` text |
  | `enrichment_version` | STRING | prompt/schema version (e.g. `"v1"`) |
  | `enrichment_model` | STRING | model name used (e.g. `"gemini-2.0-flash"`) — required for reproducibility |
  | `enriched_at` | TIMESTAMP | |

  > **Note:** `must_have_vs_nice_to_have` is **deferred to v2**. Most JDs do not cleanly separate these, and LLM inference is too unreliable for v1. Remove from prompt and schema.

- [ ] **Step 2: Write failing tests**

  ```python
  # tests/test_enrich.py
  from fitcv.enrich import build_extraction_prompt, parse_extraction_response, merge_scraped_and_enriched

  # ── prompt construction ───────────────────────────────────────────────

  def test_build_extraction_prompt_includes_required_fields():
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

  def test_build_extraction_prompt_includes_domain_job_family_distinction():
      prompt = build_extraction_prompt(
          description="Role in the banking sector",
          scraped_metadata={"sector": "Banking"},
      )
      # Prompt must clarify: job_family = role category, domain = industry
      assert "job_family" in prompt
      assert "domain" in prompt

  # ── parse_extraction_response contract ───────────────────────────────

  def test_parse_extraction_response_valid_json():
      raw = '{"required_skills": ["SQL", "Python"], "location_type": "hybrid", "job_family": "data_analytics"}'
      result = parse_extraction_response(raw)
      assert result["errors"] == []
      assert "SQL" in result["parsed"]["required_skills"]
      assert result["parsed"]["location_type"] == "hybrid"

  def test_parse_extraction_response_malformed_json():
      result = parse_extraction_response("not json at all")
      assert len(result["errors"]) > 0
      assert result["parsed"] == {}  # empty fallback, not a crash
      assert result["raw_response"] == "not json at all"

  def test_parse_extraction_response_markdown_fenced_json():
      raw = '```json\n{"required_skills": ["SQL"]}\n```'
      result = parse_extraction_response(raw)
      assert result["errors"] == []
      assert result["parsed"]["required_skills"] == ["SQL"]

  def test_parse_extraction_response_missing_fields_get_defaults():
      raw = '{"required_skills": ["SQL"]}'
      result = parse_extraction_response(raw)
      assert result["parsed"].get("preferred_skills", []) == []
      assert result["parsed"].get("location_type") is None

  def test_parse_extraction_response_normalizes_location_type_enum():
      raw = '{"location_type": "Remote"}'
      result = parse_extraction_response(raw)
      assert result["parsed"]["location_type"] == "remote"  # lowercased

  def test_parse_extraction_response_bad_enum_returns_none():
      raw = '{"location_type": "in-person-hybrid-flexible"}'
      result = parse_extraction_response(raw)
      assert result["parsed"]["location_type"] is None  # unknown enum → null

  def test_parse_extraction_response_null_value_in_valid_json():
      raw = '{"required_skills": null, "location_type": "remote"}'
      result = parse_extraction_response(raw)
      assert result["parsed"]["required_skills"] == []  # null list → empty list
      assert result["errors"] == []

  def test_parse_extraction_response_unknown_keys_ignored():
      raw = '{"required_skills": ["SQL"], "invented_field": "foo"}'
      result = parse_extraction_response(raw)
      assert "invented_field" not in result["parsed"]
      assert result["errors"] == []

  # ── merge ─────────────────────────────────────────────────────────────

  def test_merge_scraped_and_enriched():
      scraped = {"job_url": "url1", "title": "DA", "company_name": "ACME", "contract_type": "Full-time"}
      enriched = {"required_skills": ["SQL"], "job_family": "analytics"}
      merged = merge_scraped_and_enriched(scraped, enriched)
      assert merged["title"] == "DA"            # from scraper
      assert merged["required_skills"] == ["SQL"]  # from LLM
      assert "enrichment_model" in merged       # audit field must be present
      assert "enrichment_version" in merged
  ```

- [x] **Step 3: Run test — expect FAIL**

- [x] **Step 4: Implement `src/fitcv/enrich.py`**

  Functions:
  - `build_extraction_prompt(description, scraped_metadata) -> str` — prompt instructing LLM to extract only fields absent from scraped metadata; must define `job_family` = role category and `domain` = industry domain explicitly; must **not** request `must_have_vs_nice_to_have` (deferred to v2)
  - `parse_extraction_response(response_text) -> dict` — returns `{"parsed": {...}, "errors": [...], "raw_response": str}`. Contract:
    - strips Markdown code fences before parsing
    - invalid JSON → `parsed = {}`, error in `errors` list, no crash
    - missing field → fill with `[]` for arrays, `None` for scalars
    - unknown keys → silently ignored
    - null list values → coerced to `[]`
    - enum fields (`location_type`, `seniority`, `job_family`) → lowercased; unrecognized values → `None`
  - `merge_scraped_and_enriched(scraped, enriched, config) -> dict` — combines scraper metadata + LLM `parsed` dict into `structured_jobs` schema; adds `enrichment_version` and `enrichment_model` from config
  - `enrich_job(job, config) -> dict` — call Vertex AI / Gemini for extraction (`@pytest.mark.integration`)
  - `enrich_batch(normalized_jobs, config) -> list[dict]` — batch with rate limiting (`@pytest.mark.integration`)
  - `load_structured_jobs(enriched, config) -> int` — **upsert** into `fitcv.structured_jobs` via `MERGE ON job_url`; updates all enriched columns if row exists, inserts otherwise (`@pytest.mark.integration`)

- [x] **Step 5: Run test — expect PASS**

- [x] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): enrich JDs with LLM + merge with scraped metadata, parse contract with fallback"
  ```

---

## Layer 2 — Understanding You

### Task 5: Build Structured Candidate Profile

**Files:**

- Create: `src/fitcv/candidate.py`
- Create: `tests/test_candidate.py`
- Create: `data/candidate_profile.yaml`
- Create: `assets/bigquery/candidate_profile.sql`
- Create: `assets/bigquery/candidate_experiences.sql`
- Create: `assets/bigquery/candidate_projects.sql`
- Create: `assets/bigquery/candidate_skills.sql`
- Create: `assets/bigquery/candidate_achievements.sql`

- [x] **Step 1: Write `data/candidate_profile.yaml`**

  Seed file with your structured profile:

  ```yaml
  name: "Your Name"
  headline: "Data Engineer"
  summary: "..."
  experiences:
    - role: "Data Engineer"
      company: "..."
      start: "2023-01"
      end: "present"
      bullets:
        - text: "Built GA4 to BigQuery pipeline..."
          skills: ["BigQuery", "SQL", "ETL"]
          measurable_impact: "Reduced reporting latency by 40%"
  projects:
    - name: "GA4 to BigQuery Pipeline"
      skills: ["BigQuery", "SQL", "ETL", "dbt"]
      business_value: "Built reusable analytics tables"
      evidence: "https://github.com/..."
  skills:
    - name: "SQL"
      level: "advanced"
      years: 3
      evidence_refs: ["exp_1", "proj_1"]
  achievements:
    - text: "Reduced pipeline latency by 40%"
      category: "performance"
      evidence_refs: ["exp_1"]
  education:
    - degree: "..."
      institution: "..."
      year: 2022
  certifications:
    - name: "..."
      issuer: "..."
      year: 2024
  preferences:
    location_types: ["remote", "hybrid"]
    domains: ["data_engineering", "analytics"]
    seniority_target: "mid"
  ```

- [x] **Step 2: Define BigQuery tables**

  Create **7** Bruin DDL assets:
  - `candidate_profile` — name, headline, summary, preferences (location_types, domains, seniority_target, exclude_contract_types, exclude_experience_levels)
  - `candidate_experiences` — `exp_id` (stable, e.g. `exp_1`), role, company, dates, bullets (one row per bullet)
  - `candidate_projects` — `project_id` (stable, e.g. `proj_1`), name, skills[], business_value, evidence
  - `candidate_skills` — name, level, years, evidence_refs[]
  - `candidate_achievements` — `achievement_id` (stable, e.g. `ach_1`), text, category, evidence_refs[]
  - `candidate_education` — degree, institution, year
  - `candidate_certifications` — name, issuer, year

  > **Stable ID rule:** every `experience`, `project`, and `achievement` in the YAML must have an explicit `id` field (e.g. `exp_1`, `proj_1`, `ach_1`). These IDs are used as `evidence_refs` in skills and achievements and as `evidence_id` in embedding rows. Without stable IDs the evidence-reference design is broken.

- [x] **Step 3: Write failing tests**

  ```python
  # tests/test_candidate.py
  from fitcv.candidate import load_profile_yaml, flatten_skills, validate_profile, prepare_profile_rows

  # ── loading ──
  def test_load_profile_yaml_returns_dict():
      profile = load_profile_yaml("data/candidate_profile.yaml")
      assert "experiences" in profile
      assert "skills" in profile

  # ── skills ──
  def test_flatten_skills_extracts_unique():
      profile = {
          "experiences": [{"bullets": [{"skills": ["SQL", "Python"]}]}],
          "projects": [{"skills": ["SQL", "BigQuery"]}],
      }
      skills = flatten_skills(profile)
      assert "SQL" in skills
      assert len(skills) == len(set(skills))

  # ── reference integrity ──
  def test_profile_ids_are_unique():
      """All exp_id / project_id / achievement_id values must be globally unique."""
      profile = load_profile_yaml("data/candidate_profile.yaml")
      ids = (
          [e["id"] for e in profile.get("experiences", [])]
          + [p["id"] for p in profile.get("projects", [])]
          + [a["id"] for a in profile.get("achievements", [])]
      )
      assert len(ids) == len(set(ids)), "Duplicate IDs found in candidate profile"

  def test_evidence_refs_are_valid():
      """Every evidence_ref must resolve to an existing exp/proj/ach ID."""
      profile = load_profile_yaml("data/candidate_profile.yaml")
      known_ids = (
          {e["id"] for e in profile.get("experiences", [])}
          | {p["id"] for p in profile.get("projects", [])}
          | {a["id"] for a in profile.get("achievements", [])}
      )
      for skill in profile.get("skills", []):
          for ref in skill.get("evidence_refs", []):
              assert ref in known_ids, f"Dangling evidence_ref '{ref}' in skill '{skill['name']}'"
      for ach in profile.get("achievements", []):
          for ref in ach.get("evidence_refs", []):
              assert ref in known_ids, f"Dangling evidence_ref '{ref}' in achievement '{ach.get('id')}'"

  # ── prepare_profile_rows ──
  def test_prepare_profile_rows_returns_expected_tables():
      profile = load_profile_yaml("data/candidate_profile.yaml")
      rows = prepare_profile_rows(profile)
      expected = {"profile", "experiences", "projects", "skills", "achievements"}
      assert expected == set(rows.keys())
  ```

- [x] **Step 4: Run test — expect FAIL**

- [x] **Step 5: Implement `src/fitcv/candidate.py`**

  Functions:
  - `load_profile_yaml(path) -> dict` — parse YAML
  - `validate_profile(profile) -> list[str]` — check required sections + ID uniqueness + no dangling evidence_refs
  - `flatten_skills(profile) -> list[str]` — deduplicated skill list
  - `prepare_profile_rows(profile) -> dict[str, list[dict]]` — returns `{"profile": [...], "experiences": [...], "projects": [...], "skills": [...], "achievements": [...]}`, one row per bullet in experiences
  - `load_candidate_to_bigquery(profile, config) -> None` — insert into all candidate tables (`@pytest.mark.integration`)

- [x] **Step 6: Run test — expect PASS**

- [x] **Step 7: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): structured candidate profile with YAML seed and BQ tables"
  ```

---

## Layer 3 — Matching

### Task 6: Generate Embeddings

**Files:**

- Create: `src/fitcv/embeddings.py`
- Create: `tests/test_embeddings.py`
- Create: `assets/bigquery/job_embeddings.sql`
- Create: `assets/bigquery/candidate_embeddings.sql`

- [ ] **Step 1: Define embedding tables DDL**

  - `fitcv.job_embeddings` — `job_url STRING`, `chunk_type STRING`, `chunk_text STRING`, `embedding ARRAY<FLOAT64>`, `created_at TIMESTAMP`
    - **v1 rule:** always store one row with `chunk_type = "job_summary"` per job. This is the single vector used in `VECTOR_SEARCH` for shortlist ranking. Finer-grained chunk rows (`responsibilities`, `required_skills`, etc.) are optional and reserved for future evidence retrieval — do not add them in v1.
  - `fitcv.candidate_embeddings` — `evidence_id STRING` (e.g. `proj_1`), `source_ref_id STRING` (maps back to the originating `exp_id`/`proj_id`/`ach_id`), `evidence_type STRING` (`project` / `experience_bullet` / `achievement`), `chunk_text STRING`, `embedding ARRAY<FLOAT64>`, `created_at TIMESTAMP`

  > **`source_ref_id`:** makes retrieval traceable. Without it, `evidence_id` alone is ambiguous across types.

- [ ] **Step 2: Write failing tests**

  ```python
  # tests/test_embeddings.py
  # ── unit tests (no cloud calls) ──────────────────────────────────────────────
  from fitcv.embeddings import build_job_summary_text, build_job_summary_chunk, build_candidate_chunks

  def test_build_job_summary_text_structured_format():
      """Summary text must use labelled sections, not free concatenation."""
      jd = {
          "title": "Data Engineer",
          "seniority": "mid",
          "job_family": "data_engineering",
          "required_skills": ["SQL", "Python"],
          "responsibilities": ["Build pipelines"],
      }
      text = build_job_summary_text(jd)
      assert "Title:" in text
      assert "Data Engineer" in text
      assert "Required skills:" in text
      assert "SQL" in text
      assert "Seniority:" in text

  def test_build_job_summary_chunk_returns_exactly_one():
      """v1: must produce exactly one job_summary chunk for VECTOR_SEARCH ranking."""
      structured_jd = {
          "title": "Data Engineer",
          "responsibilities": ["Build pipelines"],
          "required_skills": ["SQL"],
      }
      chunks = build_job_summary_chunk(structured_jd)
      summary_chunks = [c for c in chunks if c["chunk_type"] == "job_summary"]
      assert len(summary_chunks) == 1
      assert "Data Engineer" in summary_chunks[0]["chunk_text"]

  def test_build_candidate_chunks_one_per_project():
      """Each project produces exactly one chunk with correct shape."""
      profile = {
          "projects": [{"id": "proj_1", "name": "GA4 Pipeline", "skills": ["SQL"], "business_value": "analytics"}],
          "experiences": [],
          "achievements": [],
      }
      chunks = build_candidate_chunks(profile)
      proj_chunks = [c for c in chunks if c["evidence_type"] == "project"]
      assert len(proj_chunks) == 1
      assert proj_chunks[0]["evidence_id"] == "proj_1"
      assert "GA4 Pipeline" in proj_chunks[0]["chunk_text"]
      # Verify shape: must have evidence_id, evidence_type, source_ref_id, chunk_text
      assert "source_ref_id" in proj_chunks[0]

  def test_build_candidate_chunks_one_per_experience_bullet():
      """Each experience bullet produces one chunk."""
      profile = {
          "experiences": [{
              "id": "exp_1", "role": "Data Engineer", "company": "ACME",
              "bullets": [
                  {"text": "Built pipelines", "skills": ["SQL"]},
                  {"text": "Automated tests", "skills": ["Python"]},
              ],
          }],
          "projects": [],
          "achievements": [],
      }
      chunks = build_candidate_chunks(profile)
      bullet_chunks = [c for c in chunks if c["evidence_type"] == "experience_bullet"]
      assert len(bullet_chunks) == 2

  def test_build_candidate_chunks_one_per_achievement():
      profile = {
          "achievements": [{"id": "ach_1", "text": "Reduced latency by 40%", "category": "performance"}],
          "projects": [],
          "experiences": [],
      }
      chunks = build_candidate_chunks(profile)
      ach_chunks = [c for c in chunks if c["evidence_type"] == "achievement"]
      assert len(ach_chunks) == 1
      assert ach_chunks[0]["evidence_id"] == "ach_1"

  # ── integration tests (require GOOGLE_APPLICATION_CREDENTIALS) ───────────────
  # @pytest.mark.integration
  # def test_generate_embedding_returns_floats(config): ...
  # @pytest.mark.integration
  # def test_embed_and_store_jobs_integration(config): ...
  ```

- [x] **Step 3: Run test — expect FAIL**

- [x] **Step 4: Implement `src/fitcv/embeddings.py`**

  Functions:
  - `build_job_summary_text(structured_jd) -> str` — produces a **deterministic labelled-section string** for embedding. Format:

    ```
    Title: <title>
    Required skills: <comma-joined required_skills>
    Preferred skills: <comma-joined preferred_skills>
    Responsibilities: <semicolon-joined responsibilities>
    Seniority: <seniority>
    Job family: <job_family>
    ```

    Structured text (not free concatenation) gives better embedding quality.
  - `build_job_summary_chunk(structured_jd) -> list[dict]` — returns a list containing **exactly one** `{"chunk_type": "job_summary", "chunk_text": ...}` row using `build_job_summary_text`; reserved for future multi-chunk expansion. *Renamed from `chunk_jd_by_section` for clarity.*
  - `build_candidate_chunks(profile) -> list[dict]` — v1 granularity:
    - **one chunk per project** (`evidence_type = "project"`)
    - **one chunk per experience bullet** (`evidence_type = "experience_bullet"`)
    - **one chunk per achievement** (`evidence_type = "achievement"`)

    Each chunk has this shape:

    ```python
    {
        "evidence_id":   "proj_1",          # stable ID from YAML
        "source_ref_id": "proj_1",          # maps back to exp_id/proj_id/ach_id
        "evidence_type": "project",          # project | experience_bullet | achievement
        "chunk_text":    "...",              # human-readable text for embedding
    }
    ```

  - `generate_embedding(text, config) -> list[float]` — call Vertex AI `text-embedding-005` (`@pytest.mark.integration`)
  - `embed_and_store_jobs(structured_jobs, config) -> int` — batch embed + insert into `job_embeddings` (`@pytest.mark.integration`)
  - `embed_and_store_candidate(profile, config) -> int` — batch embed + insert into `candidate_embeddings` (`@pytest.mark.integration`)

- [x] **Step 5: Run test — expect PASS**

- [x] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): semantic chunking and embedding generation"
  ```

---

### Task 7: Rule-Based Filtering

**Files:**

- Create: `src/fitcv/rule_filter.py`
- Create: `tests/test_rule_filter.py`
- Create: `assets/bigquery/rule_filter_results.sql`

> **v1 data contract:**
> - **Input:** list of structured job dicts + candidate preferences dict
> - **Output:** `{"passed": [job_url, ...], "rejected": [{"job_url": ..., "reasons": [...]}]}`
> - The rejection reason list is used for debugging, feedback loops, and tracker tables.

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_rule_filter.py
  from fitcv.rule_filter import apply_rule_filters, check_seniority

  # ── return structure ──
  def test_apply_rule_filters_returns_passed_and_rejected():
      """Return value must always be {passed, rejected} dicts, never a flat list."""
      jobs = [{"job_url": "url1", "seniority": "senior", "location_type": "remote",
               "contract_type": "Full-time", "experience_level": "Mid-Senior level",
               "required_skills": ["SQL"], "published_at": "2026-03-01", "domain": "fintech"}]
      prefs = {"seniority_target": "mid", "location_types": ["remote"],
               "contract_types": ["Full-time"], "exclude_experience_levels": ["Internship"],
               "must_have_skills": [], "preferred_domains": [], "max_age_days": 30}
      result = apply_rule_filters(jobs, prefs)
      assert "passed" in result and "rejected" in result

  def test_rejected_jobs_include_reasons():
      """Each rejected job must include a non-empty reasons list."""
      jobs = [{"job_url": "url1", "seniority": "senior", "location_type": "remote",
               "contract_type": "Full-time", "experience_level": "Mid-Senior level",
               "required_skills": ["SQL"], "published_at": "2026-03-01", "domain": "fintech"}]
      prefs = {"seniority_target": "mid", "location_types": ["remote"],
               "contract_types": ["Full-time"], "exclude_experience_levels": ["Internship"],
               "must_have_skills": [], "preferred_domains": [], "max_age_days": 30}
      result = apply_rule_filters(jobs, prefs)
      assert len(result["rejected"]) > 0
      assert all(len(r["reasons"]) > 0 for r in result["rejected"])

  # ── seniority ladder ──
  def test_seniority_ladder_rejects_senior_for_mid_target():
      """target=mid, job=senior → reject (one level above)."""
      job = {"seniority": "senior"}
      assert not check_seniority(job, {"seniority_target": "mid"})

  def test_seniority_ladder_accepts_mid_for_mid_target():
      job = {"seniority": "mid"}
      assert check_seniority(job, {"seniority_target": "mid"})

  def test_seniority_unknown_keeps_with_flag():
      """unknown seniority → keep (return True) but log a warning, not immediate reject."""
      job = {"seniority": None}
      assert check_seniority(job, {"seniority_target": "mid"})  # keep, not reject

  # ── canonical skill matching ──
  def test_must_have_skills_synonym_match():
      """GCP must match Google Cloud via synonym map."""
      from fitcv.rule_filter import check_must_have_skills
      job = {"required_skills": ["Google Cloud"]}
      prefs = {"must_have_skills": ["GCP"]}
      assert check_must_have_skills(job, prefs)  # synonym resolves

  # ── additional filters ──
  def test_filters_out_excluded_contract_type():
      from fitcv.rule_filter import apply_rule_filters
      jobs = [{"job_url": "url1", "seniority": "mid", "location_type": "remote",
               "contract_type": "Internship", "experience_level": "Internship",
               "required_skills": [], "published_at": "2026-03-01", "domain": "fintech"}]
      prefs = {"seniority_target": "mid", "location_types": ["remote"],
               "contract_types": ["Full-time"], "exclude_experience_levels": ["Internship"],
               "must_have_skills": [], "preferred_domains": [], "max_age_days": 30}
      result = apply_rule_filters(jobs, prefs)
      assert len(result["passed"]) == 0
      assert any("contract_type" in r["reasons"][0] for r in result["rejected"])

  def test_passes_when_no_filters_violated():
      jobs = [{"job_url": "url1", "seniority": "mid", "location_type": "remote",
               "contract_type": "Full-time", "experience_level": "Entry level",
               "required_skills": ["SQL"], "published_at": "2026-03-01", "domain": "fintech"}]
      prefs = {"seniority_target": "mid", "location_types": ["remote"],
               "contract_types": ["Full-time"], "exclude_experience_levels": ["Internship"],
               "must_have_skills": ["SQL"], "preferred_domains": [], "max_age_days": 30}
      result = apply_rule_filters(jobs, prefs)
      assert len(result["passed"]) == 1
  ```

- [x] **Step 2: Run test — expect FAIL**

- [x] **Step 3: Implement `src/fitcv/rule_filter.py`**

  > **Seniority ladder** (ordered, lower index = more junior):
  > `["intern", "entry", "associate", "mid", "senior", "lead", "manager", "director"]`
  >
  > **Seniority matching rules:**
  > - target ladder position ±1 step → **pass**
  > - target ladder position +2 or more above → **reject** (too senior)
  > - target ladder position -2 or more below → **reject** (too junior)
  > - `seniority = None` or unknown → **pass** (keep with warning, do not hard-reject)
  >
  > **`experience_level` vs `seniority` hierarchy:**
  > - `seniority` (LLM-normalized) is the **primary** filter signal
  > - `experience_level` (raw LinkedIn label) is used only for **exclusion** (e.g. `exclude_experience_levels = ["Internship"]`)
  > - Conflicts (`experience_level=Entry` + `seniority=mid` + `years_experience_min=5`) should be logged but not auto-rejected
  >
  > **Skill canonicalization (v1 synonym map):**
  > A curated dict maps common aliases before comparison:
  > `{"GCP": "Google Cloud", "BigQuery": "Google BigQuery", "K8s": "Kubernetes", ...}`
  > Do not rely on raw string overlap only.

  **Return contract:**
  ```python
  {
      "passed": ["url1", "url3", ...],       # job_urls that passed all rules
      "rejected": [
          {"job_url": "url2", "reasons": ["seniority_mismatch", "contract_type_excluded"]}
      ]
  }
  ```

  Functions:
  - `check_seniority(job, prefs) -> bool` — uses the seniority ladder, passes unknown
  - `check_location_type(job, prefs) -> bool`
  - `check_contract_type(job, prefs) -> bool`
  - `check_experience_level(job, prefs) -> bool` — exclusion only (LinkedIn label)
  - `check_must_have_skills(job, prefs) -> bool` — uses synonym map before comparison
  - `check_freshness(job, prefs) -> bool` — `published_at` within `prefs["max_age_days"]` (default 30)
  - `check_domain_preference(job, prefs) -> bool` — pass when `preferred_domains` is empty; reject if job domain not in list
  - `apply_rule_filters(jobs, prefs) -> dict` — composes all checks, returns `{passed, rejected}`
  - `store_filter_results(result, config) -> None` — log passed/rejected to BQ (`@pytest.mark.integration`)

- [x] **Step 4: Run test — expect PASS**

- [x] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): rule-based filtering with seniority ladder, rejection reasons, synonym map"
  ```

---

### Task 8: Semantic Retrieval with VECTOR_SEARCH

**Files:**

- Create: `src/fitcv/vector_search.py`
- Create: `tests/test_vector_search.py`
- Create: `assets/bigquery/vector_shortlist.sql`

> **v1 retrieval design (Option A — one candidate summary embedding):**
> Build one candidate query embedding from: headline + top skills + target role family (from preferences).
> Match that single vector against `job_embeddings` where `chunk_type = "job_summary"`.
> Restrict the search universe to `job_url IN (SELECT job_url FROM rule_filter_results WHERE passed = TRUE)`.
> Option B (multi-evidence aggregation) is deferred to v2.

> **v1 data contract:**
> - **Input:** candidate query text + list of passed `job_url`s from Task 7
> - **Output:** rows in `fitcv.vector_shortlist` with schema below

> **`vector_shortlist` schema:**
> | Column | Type | Description |
> |--------|------|-------------|
> | `job_url` | STRING | FK → structured_jobs |
> | `vector_rank` | INT64 | Rank within this retrieval run (1 = most similar) |
> | `vector_similarity` | FLOAT64 | Cosine similarity score from VECTOR_SEARCH |
> | `retrieval_strategy` | STRING | `"job_summary_v1"` for v1 Option A |
> | `retrieved_at` | TIMESTAMP | |

- [x] **Step 1: Define `vector_shortlist` DDL** in `assets/bigquery/vector_shortlist.sql`

- [x] **Step 2: Write failing tests**

  ```python
  # tests/test_vector_search.py
  from fitcv.vector_search import build_vector_search_query, build_candidate_query_text

  def test_build_candidate_query_text_uses_headline_and_skills():
      profile = {
          "headline": "Data Engineer",
          "skills": [{"name": "SQL"}, {"name": "Python"}],
          "preferences": {"domains": ["data_engineering"]},
      }
      text = build_candidate_query_text(profile)
      assert "Data Engineer" in text
      assert "SQL" in text

  def test_build_vector_search_query_targets_job_summary_chunk():
      """Query must filter to chunk_type = job_summary, not all embeddings."""
      query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
      assert "VECTOR_SEARCH" in query
      assert "job_summary" in query   # must filter chunk_type
      assert "50" in query             # top_n must appear

  def test_build_vector_search_query_filters_to_passed_universe():
      """Query must restrict to rule-filtered job universe, not full job_embeddings table."""
      query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
      # The query must reference the passed universe (subquery or temp table)
      assert "url1" in query or "rule_filter_results" in query or "passed" in query.lower()

  def test_build_vector_search_query_outputs_job_url():
      query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
      assert "job_url" in query
  ```

- [x] **Step 3: Run test — expect FAIL**

- [x] **Step 4: Implement `src/fitcv/vector_search.py`**

  Functions:
  - `build_candidate_query_text(profile) -> str` — builds the single candidate query string: `headline + top N skills + preferred domains` (deterministic, no embedding call)
  - `build_vector_search_query(top_n, passed_job_urls) -> str` — BigQuery `VECTOR_SEARCH` SQL that:
    - matches against `fitcv.job_embeddings` WHERE `chunk_type = 'job_summary'`
    - restricts to `job_url IN (passed_job_urls)` (the rule-filtered universe)
    - returns `job_url`, `distance` (cosine similarity), rank
    - enforces `top_k = top_n`
  - `run_vector_search(profile, passed_job_urls, config, top_n=50) -> list[dict]` — generate embedding for candidate query + execute VECTOR_SEARCH + return shortlist rows (`@pytest.mark.integration`)
  - `store_shortlist(shortlist, config) -> None` — insert into `fitcv.vector_shortlist` (`@pytest.mark.integration`)

- [x] **Step 5: Run test — expect PASS**

- [x] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): BigQuery VECTOR_SEARCH semantic retrieval over rule-filtered universe"
  ```

---

### Task 9: AI Reranking

**Files:**

- Create: `src/fitcv/ai_score.py`
- Create: `tests/test_ai_score.py`
- Create: `assets/bigquery/ai_score_results.sql`

> **Scope constraint:** Reranking is for **shortlist only** — never the full job universe. Only score the top 20–50 jobs returned by `VECTOR_SEARCH` after rule filtering. Enforced via `LIMIT top_n`.

> **Primary scoring path:** `ML.GENERATE_TEXT` (Vertex AI call from Python, not BigQuery SQL `AI.SCORE`). Rationale: gives full control over prompt + structured JSON output. `AI.SCORE` is not used in v1.

> **v1 data contract:**
> - **Input:** vector shortlist (top 20–50 `job_url`s) + per-job context: JD summary, required skills, seniority, top matched evidence snippets from retrieval
> - **Output:** rows in `fitcv.ai_score_results` with schema below

> **`ai_score_results` schema:**
> | Column | Type | Description |
> |--------|------|-------------|
> | `job_url` | STRING | FK → structured_jobs |
> | `ai_score` | FLOAT64 | 0.0 – 1.0 |
> | `fit_label` | STRING | `strong` / `stretch` / `skip` |
> | `score_reasoning` | STRING | Free-text explanation |
> | `matched_strengths` | ARRAY\<STRING\> | Candidate strengths relevant to this JD |
> | `key_risks` | ARRAY\<STRING\> | Gaps or risks flagged by the model |
> | `scored_at` | TIMESTAMP | |

- [x] **Step 1: Define `ai_score_results` DDL** in `assets/bigquery/ai_score_results.sql`

- [x] **Step 2: Write failing tests**

  ```python
  # tests/test_ai_score.py
  from fitcv.ai_score import build_scoring_prompt, parse_score_response

  # ── prompt construction ──
  def test_build_scoring_prompt_includes_jd_and_candidate():
      prompt = build_scoring_prompt(
          jd_summary="Data Engineer role requiring SQL, Python",
          candidate_summary="3 years experience in SQL, Python, BigQuery",
          top_evidence=["Built GA4 pipeline reducing latency 40%"],
      )
      assert "Data Engineer" in prompt
      assert "SQL" in prompt
      assert "score" in prompt.lower()
      assert "0.0" in prompt or "1.0" in prompt   # rubric range must be in prompt
      assert "strong" in prompt.lower()            # fit labels must be in prompt
      assert "GA4" in prompt                       # top evidence must be included

  def test_build_scoring_prompt_contains_rubric():
      prompt = build_scoring_prompt(
          jd_summary="DE role",
          candidate_summary="mid-level engineer",
          top_evidence=[],
      )
      assert "required_skills" in prompt or "required skills" in prompt.lower()
      assert "seniority" in prompt.lower()

  # ── response parsing ──
  def test_parse_score_response_valid_json():
      raw = '{"ai_score": 0.85, "fit_label": "strong", "score_reasoning": "SQL match", "matched_strengths": ["SQL"], "key_risks": []}'
      result = parse_score_response(raw)
      assert result["ai_score"] == 0.85
      assert result["fit_label"] == "strong"
      assert result["matched_strengths"] == ["SQL"]

  def test_parse_score_response_score_clamped_0_to_1():
      raw = '{"ai_score": 1.5, "fit_label": "strong", "score_reasoning": "", "matched_strengths": [], "key_risks": []}'
      result = parse_score_response(raw)
      assert result["ai_score"] <= 1.0

  def test_parse_score_response_bad_fit_label_mapped_to_skip():
      raw = '{"ai_score": 0.3, "fit_label": "maybe", "score_reasoning": "", "matched_strengths": [], "key_risks": []}'
      result = parse_score_response(raw)
      assert result["fit_label"] in ("strong", "stretch", "skip")

  def test_parse_score_response_malformed_json_returns_defaults():
      result = parse_score_response("not json")
      assert result["ai_score"] == 0.0
      assert result["fit_label"] == "skip"
  ```

- [x] **Step 3: Run test — expect FAIL**

- [x] **Step 4: Implement `src/fitcv/ai_score.py`**

  > **Scoring rubric** (must appear verbatim in the prompt):
  > - Score the match from `0.0` (no fit) to `1.0` (perfect fit)
  > - **Heavily weight:** required skills coverage
  > - **Penalize:** missing core technologies, seniority mismatch, years-of-experience gap
  > - **Reward:** strong project evidence matching JD requirements, domain relevance
  > - **Classify** into exactly one: `strong` (score ≥ 0.7), `stretch` (0.4 – 0.69), `skip` (< 0.4)
  > - Return a JSON object only, no prose

  > **Reranking input** (what `build_scoring_prompt` receives per job):
  > - JD summary text (from `build_job_summary_text`)
  > - Required skills + seniority from `structured_jobs`
  > - Candidate summary paragraph
  > - Top 2 matched evidence snippets (`chunk_text`) from `vector_shortlist` retrieval

  Functions:
  - `build_scoring_prompt(jd_summary, candidate_summary, top_evidence) -> str` — embeds rubric + structured input; `top_evidence` is a list of candidate evidence `chunk_text` strings
  - `parse_score_response(response_text) -> dict` — returns `{ai_score, fit_label, score_reasoning, matched_strengths, key_risks}`; clamps score to [0, 1]; maps unknown `fit_label` → `skip`; malformed JSON → safe defaults
  - `score_job(job, candidate_summary, top_evidence, config) -> dict` — calls Vertex AI `ML.GENERATE_TEXT`, parses response (`@pytest.mark.integration`)
  - `run_ai_scoring(shortlist, candidate_summary, config, top_n=50) -> list[dict]` — score at most `top_n` shortlisted jobs (`@pytest.mark.integration`)
  - `store_ai_scores(scores, config) -> None` (`@pytest.mark.integration`)

- [x] **Step 5: Run test — expect PASS**

- [x] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): AI reranking with ML.GENERATE_TEXT, structured rubric, evidence-grounded input"
  ```

---

### Task 10: Composite Final Ranking

**Files:**

- Create: `src/fitcv/ranking.py`
- Create: `tests/test_ranking.py`
- Create: `assets/bigquery/final_ranking.sql`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_ranking.py
  from fitcv.ranking import compute_final_score, rank_jobs

  def test_compute_final_score_weighted():
      score = compute_final_score(
          ai_score=0.8,
          must_have_match=0.9,
          vector_similarity=0.7,
          title_relevance=0.6,
          seniority_fit=1.0,
          preference_fit=0.5,
      )
      expected = 0.40*0.8 + 0.20*0.9 + 0.15*0.7 + 0.10*0.6 + 0.10*1.0 + 0.05*0.5
      assert abs(score - expected) < 0.001

  def test_rank_jobs_sorts_descending():
      jobs = [
          {"job_url": "https://linkedin.com/jobs/view/1", "final_score": 0.5},
          {"job_url": "https://linkedin.com/jobs/view/2", "final_score": 0.9},
      ]
      ranked = rank_jobs(jobs, top_n=2)
      assert ranked[0]["job_url"] == "https://linkedin.com/jobs/view/2"
  ```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement `src/fitcv/ranking.py`**

  Functions:
  - `compute_final_score(ai_score, must_have_match, vector_similarity, title_relevance, seniority_fit, preference_fit) -> float`
  - `compute_must_have_match(job_skills, candidate_skills) -> float`
  - `rank_jobs(jobs, top_n) -> list[dict]`
  - `store_final_ranking(ranked, config) -> None`

  Weight formula:

  ```text
  final_score =
      0.40 * ai_score
    + 0.20 * must_have_skill_match
    + 0.15 * vector_similarity
    + 0.10 * title_relevance
    + 0.10 * seniority_fit
    + 0.05 * preference_fit
  ```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): composite final ranking with configurable weights"
  ```

---

## Layer 4 — Personalization

### Task 11: Per-Job Evidence Retrieval

**Files:**

- Create: `src/fitcv/evidence.py`
- Create: `tests/test_evidence.py`
- Create: `assets/bigquery/evidence_retrieval.sql`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_evidence.py
  from fitcv.evidence import retrieve_evidence

  def test_retrieve_evidence_returns_structured_evidence():
      mock_profile = {
          "projects": [
              {"name": "GA4", "skills": ["SQL", "BigQuery"], "business_value": "analytics"},
              {"name": "ETL", "skills": ["Python", "Airflow"], "business_value": "automation"},
          ],
          "achievements": [{"text": "Reduced latency", "category": "performance"}],
      }
      jd_skills = ["SQL", "BigQuery"]
      evidence = retrieve_evidence(mock_profile, jd_skills, top_k=3)
      assert len(evidence) <= 3
      assert evidence[0]["name"] == "GA4"  # best match first
  ```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement `src/fitcv/evidence.py`**

  Functions:
  - `score_evidence_item(item, jd_skills) -> float` — skill overlap ratio
  - `retrieve_evidence(profile, jd_skills, top_k) -> list[dict]` — rank and select best projects, achievements, experience bullets
  - `store_evidence_selection(job_url, evidence, config) -> None` (`@pytest.mark.integration`)

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): per-job evidence retrieval from candidate profile"
  ```

---

### Task 12: Gap Analysis

**Files:**

- Create: `src/fitcv/gap_analysis.py`
- Create: `tests/test_gap_analysis.py`
- Create: `assets/bigquery/gap_analysis.sql`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_gap_analysis.py
  from fitcv.gap_analysis import compute_gap

  def test_compute_gap_identifies_missing_skills():
      result = compute_gap(
          required_skills=["SQL", "Python", "Airflow", "Terraform"],
          candidate_skills=["SQL", "Python", "dbt"],
          years_required=5,
          years_candidate=3,
      )
      assert "SQL" in result["matched"]
      assert "Airflow" in result["missing"]
      assert "dbt" not in result["missing"]
      assert result["years_risk"] is True
  ```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement `src/fitcv/gap_analysis.py`**

  Functions:
  - `compute_gap(required_skills, candidate_skills, years_required, years_candidate) -> dict`
    Returns: `{"matched": [...], "partial": [...], "missing": [...], "years_risk": bool, "overclaim_risk": [...]}`
  - `classify_fit(gap) -> str` — returns `"strong"`, `"stretch"`, or `"skip"`
  - `store_gap_analysis(job_id, gap, config) -> None`

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): gap analysis for matched/missing skills and risk"
  ```

---

### Task 13: Template-Based CV Generation

**Files:**

- Create: `src/fitcv/cv_generator.py`
- Create: `tests/test_cv_generator.py`
- Create: `templates/cv_template.md`

- [ ] **Step 1: Write `templates/cv_template.md`**

  Jinja2 template:

  ```markdown
  # {{ candidate.name }}
  **{{ headline }}**

  ## Summary
  {{ summary }}

  ## Skills
  {{ skills | join(", ") }}

  ## Experience
  {% for exp in experiences %}
  ### {{ exp.role }} — {{ exp.company }} ({{ exp.start }}–{{ exp.end }})
  {% for bullet in exp.bullets %}
  - {{ bullet }}
  {% endfor %}
  {% endfor %}

  ## Projects
  {% for proj in projects %}
  ### {{ proj.name }}
  {{ proj.description }}
  {% endfor %}
  ```

- [ ] **Step 2: Write failing tests**

  ```python
  # tests/test_cv_generator.py
  from fitcv.cv_generator import build_generation_prompt, validate_cv_constraints

  def test_build_generation_prompt_contains_evidence():
      prompt = build_generation_prompt(
          jd={"title": "Data Engineer", "required_skills": ["SQL"]},
          evidence=[{"name": "GA4 Project", "skills": ["SQL"]}],
          gap={"matched": ["SQL"], "missing": []},
          template="# {{ candidate.name }}",
      )
      assert "GA4 Project" in prompt
      assert "SQL" in prompt

  def test_validate_cv_constraints_rejects_invented_employer():
      cv_text = "Worked at InventedCorp for 5 years"
      known_employers = ["ACME", "TechCo"]
      violations = validate_cv_constraints(cv_text, known_employers)
      assert len(violations) > 0
  ```

- [ ] **Step 3: Run test — expect FAIL**

- [ ] **Step 4: Implement `src/fitcv/cv_generator.py`**

  Functions:
  - `build_generation_prompt(jd, evidence, gap, template) -> str` — assemble LLM prompt with constraints
  - `generate_cv(jd, evidence, gap, profile, config) -> str` — call LLM, return CV markdown
  - `validate_cv_constraints(cv_text, known_employers, known_skills) -> list[str]` — check for hallucinations
  - `classify_job_family(jd) -> str` — select CV emphasis based on job family

- [ ] **Step 5: Run test — expect PASS**

- [ ] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): template-based CV generation with hallucination guard"
  ```

---

### Task 14: Validation

**Files:**

- Create: `src/fitcv/validator.py`
- Create: `tests/test_validator.py`

- [ ] **Step 1: Write failing tests**

  ```python
  # tests/test_validator.py
  from fitcv.validator import validate_output

  def test_validate_output_catches_missing_sections():
      cv = "# Name\n## Summary\nHello"
      required_sections = ["Summary", "Skills", "Experience"]
      result = validate_output(cv, required_sections)
      assert result["valid"] is False
      assert "Skills" in result["missing_sections"]

  def test_validate_output_passes_complete_cv():
      cv = "# Name\n## Summary\nX\n## Skills\nY\n## Experience\nZ"
      required_sections = ["Summary", "Skills", "Experience"]
      result = validate_output(cv, required_sections)
      assert result["valid"] is True
  ```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement `src/fitcv/validator.py`**

  Functions:
  - `validate_output(cv_text, required_sections) -> dict` — check section presence, length, format
  - `check_length_constraints(cv_text, max_pages=2) -> bool`
  - `check_chronology(experiences) -> list[str]` — verify date ordering
  - `check_employer_grounding(cv_text, known_employers) -> list[str]` — every employer in output must appear in `profile["experiences"]`
  - `check_project_existence(cv_text, known_projects) -> list[str]` — every project referenced must exist in `profile["projects"]`
  - `check_skill_provenance(cv_text, candidate_skills) -> list[str]` — every skill claimed must be in the candidate knowledge base or selected evidence
  - `run_all_validations(cv_text, profile, config) -> dict` — aggregate all checks; returns `{valid, missing_sections, grounding_violations, skill_violations}`

  > **Note:** the validator is **basic structural + grounding validation**, not a full hallucination guard. It catches invented employers, non-existent projects, and out-of-scope skills. It does not catch subtle factual errors in bullet text.

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): CV validation with section, grounding, and skill provenance checks"
  ```

---

### Task 15: Versioning & Application Tracker

**Files:**

- Create: `src/fitcv/tracker.py`
- Create: `tests/test_tracker.py`
- Create: `assets/bigquery/cv_versions.sql`
- Create: `assets/bigquery/application_tracker.sql`
- Create: `assets/bigquery/generated_cvs.sql`

- [ ] **Step 1: Define BigQuery tables**

  - `fitcv.cv_versions` — `version_id`, `job_url`, `enrichment_version`, `vector_rank`, `ai_score`, `final_score`, `evidence_ids[]`, `prompt_version`, `cv_markdown`, `gap_summary`, `fit_classification`, `generated_at`
  - `fitcv.application_tracker` — `job_url`, `version_id`, `status` (applied / not_applied / interview / rejected / no_response), `cv_version_used`, `notes`, `updated_at`

- [ ] **Step 2: Write failing tests**

  ```python
  # tests/test_tracker.py
  from fitcv.tracker import create_cv_version_record, update_application_status

  def test_create_cv_version_record():
      record = create_cv_version_record(
          job_url="https://linkedin.com/jobs/view/123",
          enrichment_version="v1",
          vector_rank=5,
          ai_score=0.85,
          final_score=0.78,
          evidence_ids=["e1", "e2"],
          prompt_version="v1",
          cv_markdown="# CV",
          gap_summary={"matched": ["SQL"]},
          fit_classification="strong",
      )
      assert record["job_url"] == "https://linkedin.com/jobs/view/123"
      assert "version_id" in record
      assert "generated_at" in record

  def test_update_application_status():
      record = update_application_status(job_url="https://linkedin.com/jobs/view/123", status="applied")
      assert record["status"] == "applied"
  ```

- [ ] **Step 3: Run test — expect FAIL**

- [ ] **Step 4: Implement `src/fitcv/tracker.py`**

  Functions:
  - `create_cv_version_record(**kwargs) -> dict` — build version record with UUID + timestamp
  - `store_cv_version(record, config) -> None` — insert into `fitcv.cv_versions` (`@pytest.mark.integration`)
  - `update_application_status(job_url, status, notes="") -> dict`
  - `store_application_status(record, config) -> None` (`@pytest.mark.integration`)

- [ ] **Step 5: Run test — expect PASS**

- [ ] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): versioning and application feedback tracker"
  ```

---

## Orchestration

### Task 16: Full Pipeline Orchestrator

**Files:**

- Create: `src/fitcv/pipeline.py`

- [ ] **Step 1: Implement `src/fitcv/pipeline.py`**

  Orchestrate the full flow:

  ```python
  def run_pipeline(jobs_path: str, config_path: str = ".env.yaml") -> dict:
      config = load_config(config_path)
      # Layer 1 — ingest + normalize + enrich
      raw_jobs = parse_jobs_file(jobs_path)
      normalized = normalize_batch(raw_jobs)
      load_to_bigquery(prepare_raw_rows(normalized), config)
      enriched = enrich_batch(normalized, config)
      load_structured_jobs(enriched, config)
      # Layer 2 — candidate profile
      profile = load_profile_yaml("data/candidate_profile.yaml")
      load_candidate_to_bigquery(profile, config)
      # Layer 3 — rule filter FIRST, then embed eligible jobs only, then vector shortlist
      filtered = apply_rule_filters(enriched, profile["preferences"])
      embed_and_store_jobs(filtered, config)          # embed rule-passing jobs only
      embed_and_store_candidate(profile, config)
      shortlist = run_vector_search(config, top_n=50)
      ai_scores = run_ai_scoring(config, top_n=50)   # cap at 50 per scope constraint
      ranked = rank_jobs(ai_scores, top_n=10)
      store_final_ranking(ranked, config)
      # Layer 4 — evidence, CV generation, validation, versioning
      results = []
      for job in ranked:
          evidence = retrieve_evidence(profile, job["required_skills"])
          gap = compute_gap(job["required_skills"], flatten_skills(profile), ...)
          fit = classify_fit(gap)
          if fit == "skip":
              continue
          cv = generate_cv(job, evidence, gap, profile, config)
          validation = run_all_validations(cv, profile, config)
          version = create_cv_version_record(
              job_url=job["job_url"], ...  # canonical business key
          )
          store_cv_version(version, config)
          results.append({"job_url": job["job_url"], "fit": fit, "cv": cv, "gap": gap})
      return {"total_jobs": len(raw_jobs), "ranked": len(ranked), "cvs_generated": len(results)}
  ```

  > **Ordering invariant:** rule filter **must** run before `embed_and_store_jobs` so only eligible jobs are embedded and searched. Embedding all jobs and filtering after is wasteful and means structurally excluded jobs compete in the vector shortlist.

- [ ] **Step 2: Commit**

  ```bash
  git add -A
  git commit -m "feat(fitcv): full pipeline orchestrator"
  ```

---

## Verification Plan

### Automated Tests

Run the full test suite:

```bash
cd JOB-PROJECT
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

Each task has its own test file. All tests should pass before moving to the next task.

### Integration Test (BigQuery)

After all unit tests pass, run the pipeline end-to-end with the sample fixture:

```bash
python -c "from fitcv.pipeline import run_pipeline; print(run_pipeline('data/sample_jobs.json'))"
```

Verify in BigQuery:

```sql
-- Check tables were populated
SELECT COUNT(*) FROM fitcv.raw_jobs;
SELECT COUNT(*) FROM fitcv.structured_jobs;
SELECT COUNT(*) FROM fitcv.final_ranking;
SELECT COUNT(*) FROM fitcv.cv_versions;
```

### Manual Verification

1. **Enrichment quality:** Inspect 3–5 rows in `fitcv.structured_jobs` — do extracted skills match the JD?
2. **Ranking sanity:** Check top-5 ranked jobs — do they make sense for your profile?
3. **CV output:** Read a generated CV — is it grounded in real evidence? No hallucinated employers or skills?
4. **Gap analysis:** Verify the matched/missing breakdown matches reality
