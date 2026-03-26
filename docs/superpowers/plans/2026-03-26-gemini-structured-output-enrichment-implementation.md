# Gemini Structured Output Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the text-prompt → json.loads() enrichment pipeline with Gemini's native `response_schema` structured output, eliminating malformed JSON failures at the source.

**Architecture:** Add an `EnrichmentOutput` Pydantic model, pass it as `response_schema` to `generate_content`, read `response.parsed` directly. Delete `parse_extraction_response`, `_coerce_field`, `_normalize_enum` and related constants. Keep `json_repair` as a `response.parsed is None` fallback.

**Tech Stack:** Python, Pydantic, google-genai SDK (`GenerateContentConfig`), pytest

**Spec:** `docs/superpowers/specs/2026-03-26-gemini-structured-output-enrichment-design.md`

---

### File Map

- **Modify:** `src/fitcv/enrich.py` — add `EnrichmentOutput`, update `enrich_job`, delete dead code
- **Modify:** `tests/test_enrich.py` — update mocks, add new tests, delete tests for removed functions

---

### Task 1: Add `EnrichmentOutput` Pydantic Model and Update `enrich_job`

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`

- [ ] **Step 1.1: Write failing test for structured output path**

Add to `tests/test_enrich.py`:

```python
from unittest.mock import MagicMock, patch
from fitcv.enrich import enrich_job, EnrichmentOutput

def test_enrich_job_uses_response_parsed():
    """enrich_job reads response.parsed when API returns structured output."""
    job = {
        "job_url": "https://example.com/job/1",
        "title": "Data Engineer",
        "description": "Build pipelines with Python and Spark.",
        "location": "Berlin",
        "experience_level": "",
        "contract_type": "",
        "sector": "",
    }
    config = {
        "gcp_project": "test-proj",
        "ai_score_model": "gemini-2.5-flash",
        "gemini_model": "gemini-2.5-flash",
        "location": "us-central1",
        "enrichment_version": "v1",
    }
    parsed_output = EnrichmentOutput(
        required_skills=["Python", "Spark"],
        preferred_skills=["dbt"],
        responsibilities=["Build ETL pipelines"],
        tech_stack=["Airflow"],
        keywords=["data engineering"],
        location_type="remote",
        seniority="mid",
        domain="fintech",
        job_family="data_engineering",
        years_experience_min=3,
        years_experience_max=None,
    )
    mock_response = MagicMock()
    mock_response.parsed = parsed_output

    with patch("fitcv.enrich._make_genai_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        result = enrich_job(job, config)

    assert result["required_skills"] == ["Python", "Spark"]
    assert result["location_type"] == "remote"
    assert result["seniority"] == "mid"
    assert result["domain"] == "fintech"
    assert result["job_family"] == "data_engineering"
    assert result["years_experience_min"] == 3
```

- [ ] **Step 1.2: Run to verify failure**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py::test_enrich_job_uses_response_parsed -v
```

Expected: `ImportError` or `AttributeError` — `EnrichmentOutput` doesn't exist yet.

- [ ] **Step 1.3: Add `EnrichmentOutput` model and update `enrich_job`**

In `src/fitcv/enrich.py`, after the imports section, add:

```python
from pydantic import BaseModel, Field as _Field

class EnrichmentOutput(BaseModel):
    """Structured output schema for Gemini enrichment extraction."""
    required_skills: list[str] = _Field(default_factory=list)
    preferred_skills: list[str] = _Field(default_factory=list)
    responsibilities: list[str] = _Field(default_factory=list)
    tech_stack: list[str] = _Field(default_factory=list)
    keywords: list[str] = _Field(default_factory=list)
    location_type: str | None = None
    seniority: str | None = None
    domain: str | None = None
    job_family: str | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
```

Replace the body of `enrich_job` with:

```python
def enrich_job(job: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini to extract structured fields from one normalized job.

    Uses response_schema structured output to guarantee valid JSON.
    Falls back to json_repair + text parsing if response.parsed is None.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    from google.genai import types as _genai_types  # type: ignore[import-untyped]

    model_name = str(config.get("gemini_model", "gemini-2.5-flash"))
    client = _make_genai_client(config)

    prompt = build_extraction_prompt(
        description=str(job.get("description", "")),
        scraped_metadata={
            "title": job.get("title", ""),
            "experienceLevel": job.get("experience_level", ""),
            "contractType": job.get("contract_type", ""),
            "sector": job.get("sector", ""),
            "location": job.get("location", ""),
        },
    )

    gen_config = _genai_types.GenerateContentConfig(response_schema=EnrichmentOutput)
    response = client.models.generate_content(
        model=model_name, contents=prompt, config=gen_config
    )

    # Primary path: structured output
    if response.parsed is not None:
        output: EnrichmentOutput = response.parsed
        parsed = output.model_dump()
        # Post-validate strict enums (schema enforcement can be imperfect on thinking models)
        parsed["location_type"] = _normalize_enum(
            parsed.get("location_type"), _get_valid_location_types(config)
        )
        parsed["seniority"] = _normalize_enum(
            parsed.get("seniority"), _get_valid_seniority_enrich(config)
        )
        return merge_scraped_and_enriched(job, parsed, config)

    # Fallback path: text + json_repair
    _log.warning(
        "Structured output unavailable for job %r — falling back to json_repair",
        job.get("title") or job.get("job_url"),
    )
    extraction = parse_extraction_response(str(response.text or ""))
    if extraction["errors"]:
        _log.warning(
            "Enrichment parse errors for job %r: %s",
            job.get("title") or job.get("job_url"),
            "; ".join(extraction["errors"]),
        )
    return merge_scraped_and_enriched(job, extraction["parsed"], config)
```

- [ ] **Step 1.4: Run test to verify pass**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py::test_enrich_job_uses_response_parsed -v
```

Expected: PASS.

---

### Task 2: Add Fallback Path Tests

**Files:**
- Modify: `tests/test_enrich.py`

- [ ] **Step 2.1: Write failing fallback tests**

Add to `tests/test_enrich.py`:

```python
def _minimal_job_and_config():
    job = {
        "job_url": "https://example.com/job/99",
        "title": "Analyst",
        "description": "Analyse data with SQL.",
        "location": "Remote",
        "experience_level": "",
        "contract_type": "",
        "sector": "",
    }
    config = {
        "gcp_project": "test-proj",
        "gemini_model": "gemini-2.5-flash",
        "ai_score_model": "gemini-2.5-flash",
        "location": "us-central1",
        "enrichment_version": "v1",
    }
    return job, config


def test_enrich_job_fallback_when_parsed_is_none(caplog):
    """Falls back to json_repair when response.parsed is None."""
    import logging
    job, config = _minimal_job_and_config()
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = '{"required_skills": ["SQL"] "preferred_skills": []}'  # missing comma

    with patch("fitcv.enrich._make_genai_client") as mock_client_factory, \
         caplog.at_level(logging.WARNING, logger="fitcv.enrich"):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response
        result = enrich_job(job, config)

    assert "falling back" in caplog.text.lower()
    # json_repair should fix the missing comma and extract required_skills
    assert isinstance(result["required_skills"], list)


def test_enrich_job_fallback_produces_empty_on_bad_text(caplog):
    """Returns empty enrichment (no crash) when both parsed and text are invalid."""
    import logging
    job, config = _minimal_job_and_config()
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "I cannot extract structured data from this input."

    with patch("fitcv.enrich._make_genai_client") as mock_client_factory, \
         caplog.at_level(logging.WARNING, logger="fitcv.enrich"):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response
        result = enrich_job(job, config)

    assert result["required_skills"] == []
    assert result["location_type"] is None
```

- [ ] **Step 2.2: Run to verify tests pass**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py::test_enrich_job_fallback_when_parsed_is_none tests/test_enrich.py::test_enrich_job_fallback_produces_empty_on_bad_text -v
```

Expected: PASS.

- [ ] **Step 2.3: Commit Task 1 + 2**

```bash
git add src/fitcv/enrich.py tests/test_enrich.py
git commit -m "feat(enrich): use Gemini response_schema structured output; keep json_repair fallback"
```

---

### Task 3: Delete Dead Code

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`

> **Note:** Only delete after Task 1 + 2 pass. The fallback path still uses `parse_extraction_response`, so do NOT delete it yet.

- [ ] **Step 3.1: Identify dead code**

The following are now only used by `parse_extraction_response` (the fallback) and `enrich_job` no longer calls them directly:

- `_EXTRACTION_SCHEMA` (text constant) — used only in `build_extraction_prompt`
- `_EXTRACTION_RESPONSE_JSON_SCHEMA` (dict constant) — no longer used anywhere → **delete**
- `_ARRAY_FIELDS`, `_SCALAR_FIELDS`, `_KNOWN_FIELDS` — used only by `_coerce_field` → **delete when `parse_extraction_response` is deleted**
- `_coerce_field`, `_normalize_enum` → **keep** (used by both `enrich_job` post-validation and `parse_extraction_response` fallback)

- [ ] **Step 3.2: Delete `_EXTRACTION_RESPONSE_JSON_SCHEMA`**

Remove the `_EXTRACTION_RESPONSE_JSON_SCHEMA` dict from `src/fitcv/enrich.py` (lines ~125–154). It is no longer referenced.

- [ ] **Step 3.3: Simplify prompt — remove JSON-format instruction**

In `build_extraction_prompt`, remove the line:
```
Return ONLY a valid JSON object matching this schema. No markdown, no explanation:
```
Structured output makes this instruction redundant. Keep the field definitions for context.

- [ ] **Step 3.4: Run full enrich test suite**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py -v
```

Expected: all pass.

- [ ] **Step 3.5: Delete tests for `_EXTRACTION_RESPONSE_JSON_SCHEMA`**

Search for any test that asserts the shape or content of `_EXTRACTION_RESPONSE_JSON_SCHEMA`:

```bash
grep -n "_EXTRACTION_RESPONSE_JSON_SCHEMA" tests/test_enrich.py
```

Delete those test functions.

- [ ] **Step 3.6: Run full test suite**

```bash
/tmp/fitcv-test-env/bin/pytest tests/ -q --tb=short
```

Expected: all pass, no regressions.

- [ ] **Step 3.7: Commit**

```bash
git add src/fitcv/enrich.py tests/test_enrich.py
git commit -m "refactor(enrich): remove dead JSON schema dict and redundant prompt instruction"
```

---

### Task 4: Full Verification

- [ ] **Step 4.1: Run full test suite**

```bash
/tmp/fitcv-test-env/bin/pytest tests/ -q --tb=short
```

Expected: all pass.

- [ ] **Step 4.2: Restart server and trigger a run**

```bash
cd /workspaces/fitcv
pkill -9 -f "rq worker|uvicorn" && bash start_admin_cp.sh
```

Trigger a run from http://localhost:8000/admin/runs with `sample_data_engineer_jobs.json`.

- [ ] **Step 4.3: Verify enriched jobs have no `—` from parse failures**

After the run completes, check the run detail page. All 10 jobs should have populated `required_skills`. Check the worker log:

```bash
tail -30 /workspaces/fitcv/rq_worker.log | grep -E "WARNING|ERROR|parse"
```

Expected: no `"falling back"` or `"parse errors"` warnings.

- [ ] **Step 4.4: Final commit if needed**

```bash
git add .
git commit -m "fix(enrich): resolve gemini structured output verification"
```
