# Gemini Structured Output for Job Enrichment — Design Spec

**Date:** 2026-03-26  
**Status:** Approved  
**Feature area:** `src/fitcv/enrich.py`

---

## Problem

The current enrichment pipeline calls `gemini-2.5-flash` with a free-text prompt and parses the response with `json.loads`. The thinking model produces malformed JSON (missing commas, truncated arrays) in ~40% of calls. The workaround (`json_repair`) silently guesses corrections that may corrupt extracted data.

## Goal

Replace the text-parse pipeline with Gemini's native **structured output** (`response_schema`). The API guarantees valid JSON matching the declared schema, eliminating parse failures at the source.

---

## Architecture

### Current flow

```
build_extraction_prompt()
  → client.models.generate_content(prompt)
  → response.text (raw string)
  → _strip_markdown_fences()
  → json.loads()  ← fails ~40% of calls
  → json_repair() ← silent corruption risk
  → _coerce_field() per key
  → merge_scraped_and_enriched()
```

### New flow

```
build_extraction_prompt()
  → client.models.generate_content(
        prompt,
        config=GenerateContentConfig(response_schema=EnrichmentOutput)
     )
  → response.parsed  ← guaranteed valid, typed Pydantic object
  → merge_scraped_and_enriched()
```

If `response.parsed` is `None` (API couldn't produce structured output), fall back to `response.text` + `json_repair` and emit a `WARNING`.

---

## Components

### `EnrichmentOutput` — new Pydantic model in `src/fitcv/enrich.py`

```python
from pydantic import BaseModel, Field

class EnrichmentOutput(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    location_type: str | None = None   # "remote" | "hybrid" | "onsite"
    seniority: str | None = None       # "junior" | "mid" | "senior" | "lead"
    domain: str | None = None
    job_family: str | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
```

The `location_type` and `seniority` fields are post-validated against their allowed enum sets after parsing (Gemini's enum enforcement via schema can be imperfect on thinking models).

### Changes to `enrich_job`

- Pass `config=GenerateContentConfig(response_schema=EnrichmentOutput)` to `generate_content`
- Read `response.parsed` (a typed `EnrichmentOutput`) instead of `response.text`
- Call `merge_scraped_and_enriched(job, output.model_dump(), config)` directly

### Deleted code

The following are no longer needed and will be removed:

| Symbol | Reason |
|---|---|
| `parse_extraction_response()` | API handles parsing |
| `_coerce_field()` | Pydantic handles coercion |
| `_normalize_enum()` | Replaced by post-validate step |
| `_ARRAY_FIELDS`, `_SCALAR_FIELDS`, `_KNOWN_FIELDS` | Replaced by Pydantic model |
| `_EXTRACTION_SCHEMA` (text) | Replaced by Pydantic model |
| `_EXTRACTION_RESPONSE_JSON_SCHEMA` (dict) | Replaced by Pydantic model |

### Fallback path (resilience)

```python
if response.parsed is None:
    logger.warning("Structured output unavailable for %r — falling back to json_repair", title)
    # existing json_repair path
```

`json_repair` stays in the codebase as a last-resort fallback, not the primary path.

---

## Prompt changes

The prompt no longer needs to end with `"Return ONLY a valid JSON object..."` since structure is enforced by the API. The instruction block simplifies to a plain field-definition section.

---

## What doesn't change

- `merge_scraped_and_enriched()` — interface unchanged
- `enrich_batch()` — retry logic unchanged
- `load_run_structured_jobs()` — unchanged
- All downstream pipeline code — unchanged
- `.env.yaml` model config — unchanged

---

## Error handling

| Scenario | Behaviour |
|---|---|
| `response.parsed` is valid | Primary path, no logging |
| `response.parsed` is `None` | WARNING log + json_repair fallback |
| json_repair fallback also fails | Return `{}`, WARNING log, empty enrichment row |
| `ResourceExhausted` 429 | Existing retry logic in `enrich_batch` handles it |

---

## Testing

### Unit tests (no API calls)

- `test_enrich_job_uses_response_parsed` — mock `client.models.generate_content` to return a mock with `.parsed = EnrichmentOutput(...)`, assert correct merge
- `test_enrich_job_fallback_when_parsed_is_none` — mock `.parsed = None`, assert fallback triggers and WARNING logged
- `test_enrich_job_fallback_produces_empty_on_total_failure` — mock `.parsed = None` and `response.text = "not json"`, assert empty enrichment and no crash
- `test_enrichment_output_rejects_invalid_location_type` — assert post-validation nullifies unknown enum values
- `test_enrichment_output_rejects_invalid_seniority` — same for seniority

### Existing tests to update

- Tests that mock `parse_extraction_response` → update to mock `response.parsed`
- Tests that assert `_coerce_field` behaviour → replace with `EnrichmentOutput` field assertions

### Tests to delete

- All tests for `parse_extraction_response`, `_coerce_field`, `_normalize_enum` (functions being deleted)

---

## Constraints

- `pydantic` is already a dependency (used in `fitcv_cp`); no new package needed
- `google-genai` SDK already installed; `GenerateContentConfig` is available
- Must remain compatible with Vertex AI credentials path (service account key)
