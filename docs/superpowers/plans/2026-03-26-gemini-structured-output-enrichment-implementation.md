# Gemini Structured Output Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up `response_schema` structured output in `enrich_job` using a `EnrichmentOutput` Pydantic model, eliminating malformed JSON failures on the primary path. Keep `parse_extraction_response` + `json_repair` as a `response.parsed is None` fallback.

**Architecture:** Add `EnrichmentOutput` Pydantic model; add `_apply_structured_normalization()` helper to preserve existing field semantics; update `enrich_job` to use `GenerateContentConfig(response_schema=EnrichmentOutput)`; delete only `_EXTRACTION_RESPONSE_JSON_SCHEMA` (the raw dict it replaces); keep all other helpers.

**Tech Stack:** Python, Pydantic (add as direct dep), google-genai SDK (`GenerateContentConfig`), pytest

**Spec:** `docs/superpowers/specs/2026-03-26-gemini-structured-output-enrichment-design.md`

---

### File Map

- **Modify:** `src/fitcv/enrich.py` — add `EnrichmentOutput` model + `_apply_structured_normalization()`, update `enrich_job`, delete `_EXTRACTION_RESPONSE_JSON_SCHEMA`
- **Modify:** `pyproject.toml` — add `pydantic` as direct dependency
- **Modify:** `tests/test_enrich.py` — add new tests, update mocks, delete `_EXTRACTION_RESPONSE_JSON_SCHEMA` tests

---

### Task 1: Add `EnrichmentOutput` and `_apply_structured_normalization()`

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`

- [ ] **Step 1.1: Write failing test for `_apply_structured_normalization`**

Add to `tests/test_enrich.py`:

```python
from fitcv.enrich import EnrichmentOutput, _apply_structured_normalization

def test_apply_structured_normalization_lowercases_domain():
    output = EnrichmentOutput(domain="FinTech", job_family="Data_Engineering")
    result = _apply_structured_normalization(output, config=None)
    assert result["domain"] == "fintech"
    assert result["job_family"] == "data_engineering"

def test_apply_structured_normalization_rejects_invalid_location_type():
    output = EnrichmentOutput(location_type="office")  # not in valid set
    result = _apply_structured_normalization(output, config=None)
    assert result["location_type"] is None

def test_apply_structured_normalization_rejects_invalid_seniority():
    output = EnrichmentOutput(seniority="executive")  # not in valid set
    result = _apply_structured_normalization(output, config=None)
    assert result["seniority"] is None

def test_apply_structured_normalization_sanitizes_skill_lists():
    output = EnrichmentOutput(required_skills=["Python", None, "SQL"])
    result = _apply_structured_normalization(output, config=None)
    assert result["required_skills"] == ["Python", "SQL"]
```

- [ ] **Step 1.2: Run to verify failure**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py::test_apply_structured_normalization_lowercases_domain -v
```

Expected: `ImportError` — `EnrichmentOutput` doesn't exist yet.

- [ ] **Step 1.3: Add `EnrichmentOutput` and `_apply_structured_normalization` to `enrich.py`**

After the `_SCALAR_FIELDS` block, add:

```python
from pydantic import BaseModel as _BaseModel, Field as _Field

class EnrichmentOutput(_BaseModel):
    """Structured output schema for Gemini enrichment extraction.

    Used as response_schema in generate_content to guarantee valid JSON
    from the API. Post-processing via _apply_structured_normalization
    preserves existing stored-enrichment field semantics.
    """
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


def _apply_structured_normalization(
    output: EnrichmentOutput,
    config: dict | None,
) -> dict[str, Any]:
    """Convert EnrichmentOutput to a normalized dict preserving existing field semantics.

    Applies the same canonicalization as the text-path's _coerce_field:
    - enum fields (location_type, seniority): validated against valid sets, unknown → None
    - domain, job_family: lowercased and stripped
    - list fields: None values removed, coerced to str
    """
    return {
        "location_type": _normalize_enum(
            output.location_type, _get_valid_location_types(config)
        ),
        "seniority": _normalize_enum(
            output.seniority, _get_valid_seniority_enrich(config)
        ),
        "domain":    output.domain.lower().strip() if output.domain else None,
        "job_family": output.job_family.lower().strip() if output.job_family else None,
        "years_experience_min": output.years_experience_min,
        "years_experience_max": output.years_experience_max,
        "required_skills":  [str(s) for s in output.required_skills  if s is not None],
        "preferred_skills": [str(s) for s in output.preferred_skills if s is not None],
        "responsibilities": [str(s) for s in output.responsibilities if s is not None],
        "tech_stack":       [str(s) for s in output.tech_stack       if s is not None],
        "keywords":         [str(s) for s in output.keywords         if s is not None],
    }
```

- [ ] **Step 1.4: Run normalization tests**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py -k "structured_normalization" -v
```

Expected: 4 tests PASS.

---

### Task 2: Wire `response_schema` into `enrich_job` and add path tests

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`

- [ ] **Step 2.1: Write failing test for primary path**

Add to `tests/test_enrich.py`:

```python
from unittest.mock import MagicMock, patch
from fitcv.enrich import enrich_job, EnrichmentOutput

def _job_fixture():
    return {
        "job_url": "https://example.com/job/1",
        "title": "Data Engineer",
        "description": "Build pipelines with Python and Spark.",
        "location": "Berlin",
        "experience_level": "",
        "contract_type": "",
        "sector": "",
    }

def _config_fixture():
    return {
        "gcp_project": "test-proj",
        "gemini_model": "gemini-2.5-flash",
        "ai_score_model": "gemini-2.5-flash",
        "location": "us-central1",
        "enrichment_version": "v1",
    }

def test_enrich_job_uses_response_parsed():
    """Primary path: response.parsed is used and normalization applied."""
    mock_response = MagicMock()
    mock_response.parsed = EnrichmentOutput(
        required_skills=["Python", "Spark"],
        location_type="remote",
        seniority="mid",
        domain="FinTech",   # should be lowercased by normalization
        job_family="data_engineering",
    )

    with patch("fitcv.enrich._make_genai_client") as mk:
        mk.return_value.models.generate_content.return_value = mock_response
        result = enrich_job(_job_fixture(), _config_fixture())

    assert result["required_skills"] == ["Python", "Spark"]
    assert result["location_type"] == "remote"
    assert result["seniority"] == "mid"
    assert result["domain"] == "fintech"   # normalized to lowercase
    assert result["job_family"] == "data_engineering"
```

- [ ] **Step 2.2: Run to verify failure**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py::test_enrich_job_uses_response_parsed -v
```

Expected: FAIL — `enrich_job` doesn't yet pass `response_schema`.

- [ ] **Step 2.3: Update `enrich_job` to pass `response_schema` and read `response.parsed`**

Replace the body of `enrich_job` in `src/fitcv/enrich.py`:

```python
def enrich_job(job: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini to extract structured fields from one normalized job.

    Primary path: uses response_schema structured output (EnrichmentOutput).
    Fallback: response.text + json_repair when response.parsed is None.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    from google.genai import types as _genai_types  # type: ignore[import-untyped]

    model_name = str(config.get("gemini_model", "gemini-2.5-flash"))
    client = _make_genai_client(config)
    title_for_log = job.get("title") or job.get("job_url")

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

    # ── Primary path: structured output ──────────────────────────────────────
    if response.parsed is not None:
        parsed = _apply_structured_normalization(response.parsed, config)
        return merge_scraped_and_enriched(job, parsed, config)

    # ── Fallback: text + json_repair ─────────────────────────────────────────
    _log.warning("Structured output unavailable for %r — falling back to json_repair", title_for_log)
    extraction = parse_extraction_response(str(response.text or ""))
    if extraction["errors"]:
        _log.warning(
            "Enrichment parse errors for job %r: %s",
            title_for_log,
            "; ".join(extraction["errors"]),
        )
    return merge_scraped_and_enriched(job, extraction["parsed"], config)
```

- [ ] **Step 2.4: Write fallback path tests**

Add to `tests/test_enrich.py`:

```python
def test_enrich_job_fallback_when_parsed_is_none(caplog):
    """Falls back to parse_extraction_response when response.parsed is None."""
    import logging
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = '{"required_skills": ["SQL"] "preferred_skills": []}'  # missing comma

    with patch("fitcv.enrich._make_genai_client") as mk, \
         caplog.at_level(logging.WARNING, logger="fitcv.enrich"):
        mk.return_value.models.generate_content.return_value = mock_response
        result = enrich_job(_job_fixture(), _config_fixture())

    assert "falling back" in caplog.text.lower()
    assert isinstance(result["required_skills"], list)


def test_enrich_job_fallback_empty_on_bad_text(caplog):
    """Returns empty enrichment (no crash) when parsed=None and text is not JSON."""
    import logging
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "I cannot extract structured data from this input."

    with patch("fitcv.enrich._make_genai_client") as mk, \
         caplog.at_level(logging.WARNING, logger="fitcv.enrich"):
        mk.return_value.models.generate_content.return_value = mock_response
        result = enrich_job(_job_fixture(), _config_fixture())

    assert result["required_skills"] == []
    assert result["location_type"] is None
```

- [ ] **Step 2.5: Run all new tests**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py -k "enrich_job_uses_response_parsed or enrich_job_fallback" -v
```

Expected: all 3 PASS.

---

### Task 3: Delete `_EXTRACTION_RESPONSE_JSON_SCHEMA` and add `pydantic` as direct dep

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_enrich.py`

- [ ] **Step 3.1: Delete `_EXTRACTION_RESPONSE_JSON_SCHEMA` from `enrich.py`**

Remove the `_EXTRACTION_RESPONSE_JSON_SCHEMA: dict[str, Any] = {...}` block (lines ~125–154). It is fully replaced by `EnrichmentOutput`.

- [ ] **Step 3.2: Grep for any remaining references**

```bash
grep -n "_EXTRACTION_RESPONSE_JSON_SCHEMA" src/fitcv/enrich.py tests/test_enrich.py
```

Expected: no output. If any found, remove those references.

- [ ] **Step 3.3: Delete tests that assert `_EXTRACTION_RESPONSE_JSON_SCHEMA`**

```bash
grep -n "_EXTRACTION_RESPONSE_JSON_SCHEMA" tests/test_enrich.py
```

Delete any test functions that assert on this constant.

- [ ] **Step 3.4: Add `pydantic` as direct dependency in `pyproject.toml`**

In `[project]` → `dependencies`, add:

```toml
[project]
dependencies = [
    "pydantic>=2.0",
]
```

(If there is no `dependencies` key yet, add one.)

- [ ] **Step 3.5: Run full enrich test suite**

```bash
/tmp/fitcv-test-env/bin/pytest tests/test_enrich.py -v --tb=short
```

Expected: all pass.

- [ ] **Step 3.6: Commit**

```bash
git add src/fitcv/enrich.py tests/test_enrich.py pyproject.toml
git commit -m "feat(enrich): wire Gemini response_schema structured output; keep json_repair fallback"
```

---

### Task 4: Full Verification

- [ ] **Step 4.1: Run full test suite**

```bash
/tmp/fitcv-test-env/bin/pytest tests/ -q --tb=short
```

Expected: all pass, no regressions.

- [ ] **Step 4.2: Restart server and trigger a run**

```bash
cd /workspaces/fitcv
pkill -9 -f "rq worker|uvicorn" && bash start_admin_cp.sh
```

Trigger a run from http://localhost:8000/admin/runs.

- [ ] **Step 4.3: Check worker log for fallback warnings**

```bash
tail -50 /workspaces/fitcv/rq_worker.log | grep -E "WARNING|falling back|parse error"
```

Expected: no `"falling back"` lines. If any appear, note which job title triggered it — this is now a tracked anomaly rather than a silent failure.

- [ ] **Step 4.4: Verify enriched fields on run detail page**

All jobs should show populated `required_skills`. `domain` and `job_family` should appear lowercased. `location_type` and `seniority` should only contain `remote/hybrid/onsite` and `junior/mid/senior/lead` (or `—` if unrecognized).

- [ ] **Step 4.5: Commit final state**

```bash
git add .
git commit -m "fix(enrich): verify gemini structured output end-to-end"
```
