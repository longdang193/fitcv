# Gemini Structured Output for Job Enrichment — Design Spec

**Date:** 2026-03-26  
**Status:** Revised after review  
**Feature area:** `src/fitcv/enrich.py`

---

## Problem

The current enrichment pipeline calls `gemini-2.5-flash` with a free-text prompt and parses the response with `json.loads`. `_EXTRACTION_RESPONSE_JSON_SCHEMA` is already defined in `enrich.py` but has never been wired up to the API call. The thinking model produces malformed JSON (missing commas) in ~40% of calls. `json_repair` is a workaround that silently guesses corrections and may corrupt data.

## Goal

Wire up Gemini's native **structured output** (`response_schema`) using a Pydantic model instead of the existing raw dict. The API guarantees valid JSON matching the declared schema, eliminating parse failures on the primary path. A text + `json_repair` fallback is retained for resilience.

---

## Architecture

### Current flow

```
build_extraction_prompt()
  → client.models.generate_content(prompt)   # no schema — raw text response
  → response.text (raw string)
  → _strip_markdown_fences()
  → json.loads()  ← fails ~40% of calls
  → json_repair() ← silent corruption risk
  → _coerce_field() per key                  # lowercasing, enum validation, int coercion
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
  → _apply_structured_normalization()        # preserve existing field semantics
  → merge_scraped_and_enriched()

  # Fallback (response.parsed is None only):
  → response.text + json_repair
  → _coerce_field() per key (unchanged)
  → merge_scraped_and_enriched()
```

---

## Components

### `EnrichmentOutput` — new Pydantic model

Replaces `_EXTRACTION_RESPONSE_JSON_SCHEMA` (the raw dict). Everything else in `enrich.py` is preserved.

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

### Normalization after `response.parsed`

`_coerce_field` / `_normalize_enum` are **kept** and applied after `response.parsed`. This preserves the existing stored enrichment semantics: enum canonicalization, lowercasing, list sanitization, integer coercion.

```python
def _apply_structured_normalization(
    output: EnrichmentOutput, config: dict | None
) -> dict[str, Any]:
    """Convert EnrichmentOutput to a normalized dict matching existing semantics."""
    return {
        "location_type": _normalize_enum(output.location_type, _get_valid_location_types(config)),
        "seniority":     _normalize_enum(output.seniority, _get_valid_seniority_enrich(config)),
        "domain":        output.domain.lower().strip() if output.domain else None,
        "job_family":    output.job_family.lower().strip() if output.job_family else None,
        "years_experience_min": output.years_experience_min,
        "years_experience_max": output.years_experience_max,
        "required_skills":  [str(s) for s in output.required_skills if s],
        "preferred_skills": [str(s) for s in output.preferred_skills if s],
        "responsibilities": [str(s) for s in output.responsibilities if s],
        "tech_stack":       [str(s) for s in output.tech_stack if s],
        "keywords":         [str(s) for s in output.keywords if s],
    }
```

### What is deleted

Only `_EXTRACTION_RESPONSE_JSON_SCHEMA` (the raw dict constant, now superseded by `EnrichmentOutput`). Nothing else.

| Symbol | Action | Reason |
|---|---|---|
| `_EXTRACTION_RESPONSE_JSON_SCHEMA` | **Delete** | Replaced by `EnrichmentOutput` |
| `parse_extraction_response()` | **Keep** | Used by fallback path |
| `_coerce_field()`, `_normalize_enum()` | **Keep** | Used by both primary and fallback normalization |
| `_ARRAY_FIELDS`, `_SCALAR_FIELDS`, `_KNOWN_FIELDS` | **Keep** | Used by `_coerce_field` in fallback |
| `_EXTRACTION_SCHEMA` (text) | **Keep** | Still in prompt for field guidance |

### Prompt

The `"Return ONLY a valid JSON object…"` instruction is **kept**. The fallback still reads `response.text`, and this prompt guidance improves text shape when structured output fails.

### Fallback path

When `response.parsed is None`:
1. Log `WARNING`
2. Run `parse_extraction_response(response.text)` + `json_repair` (existing path, unchanged)
3. Log any parse errors
4. Call `merge_scraped_and_enriched` with the fallback parsed dict

---

## Error handling

| Scenario | Behaviour |
|---|---|
| `response.parsed` is valid | Primary path — normalization applied, no log |
| `response.parsed` is `None` | WARNING + fallback via `parse_extraction_response` |
| Fallback parse also fails | Return empty enrichment, WARNING logged, no crash |
| 429 ResourceExhausted | Existing retry logic in `enrich_batch` — unchanged |

---

## Testing

### New unit tests

- `test_enrich_job_uses_response_parsed` — mock `response.parsed = EnrichmentOutput(...)`, assert normalization applied
- `test_enrich_job_fallback_when_parsed_is_none` — mock `response.parsed = None`, assert fallback triggers + WARNING
- `test_enrich_job_fallback_empty_on_bad_text` — mock `response.parsed = None`, `response.text = "not json"`, assert empty + no crash
- `test_apply_structured_normalization_lowercases_domain` — assert `"FinTech"` → `"fintech"`
- `test_apply_structured_normalization_rejects_invalid_location_type` — assert unknown value → `None`

### Tests to update

Tests that mock `parse_extraction_response` return values may need updating to reflect the new primary path. Fallback tests should still exercise `parse_extraction_response`.

### Tests to delete

Any test that directly asserts the shape or content of `_EXTRACTION_RESPONSE_JSON_SCHEMA`.

---

## Dependencies

`pydantic` is currently available transitively via `fastapi` (used in `fitcv_cp`). Since this change introduces a direct Pydantic dependency in `fitcv` (not just `fitcv_cp`), `pydantic` should be added as a direct dependency in `pyproject.toml` to make the coupling explicit and prevent breakage if the transitive path changes.
