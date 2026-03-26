# Gemini Structured Output Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up `response_schema` structured output in `enrich_job` using a `EnrichmentOutput` Pydantic model, eliminating malformed JSON failures on the primary path. Keep `parse_extraction_response` + `json_repair` as a `response.parsed is None` fallback.

**Architecture:** Add `EnrichmentOutput` Pydantic model; add `_apply_structured_normalization()` helper to preserve existing field semantics; update `enrich_job` to use `GenerateContentConfig(response_mime_type="application/json", response_schema=EnrichmentOutput)`; delete only `_EXTRACTION_RESPONSE_JSON_SCHEMA` (the raw dict it replaces); keep all other helpers.

**Tech Stack:** Python, Pydantic (add as direct dep), google-genai SDK (`GenerateContentConfig`), pytest

**Spec:** `docs/superpowers/specs/2026-03-26-gemini-structured-output-enrichment-design.md`

**Status: ✅ COMPLETE — 121/121 tests pass, committed, server running**

---

### File Map

- **Modify:** `src/fitcv/enrich.py` ✅
- **Modify:** `pyproject.toml` ✅
- **Modify:** `tests/test_enrich.py` ✅

---

### Task 1: Add `EnrichmentOutput` and `_apply_structured_normalization()` ✅

- [x] **Step 1.1:** Write failing normalization tests
- [x] **Step 1.2:** Run to verify failure
- [x] **Step 1.3:** Add `EnrichmentOutput` model and `_apply_structured_normalization()` to `enrich.py`
- [x] **Step 1.4:** Run normalization tests (4 pass)

---

### Task 2: Wire `response_schema` into `enrich_job` ✅

- [x] **Step 2.1:** Write failing test for primary path
- [x] **Step 2.2:** Run to verify failure
- [x] **Step 2.3:** Update `enrich_job` to use `GenerateContentConfig(response_mime_type="application/json", response_schema=EnrichmentOutput)`; read `response.parsed` primary / fallback to `json_repair`
- [x] **Step 2.4:** Write fallback path tests (2 pass)
- [x] **Step 2.5:** All 3 new path tests pass
- [x] **Step 2.6:** Commit

---

### Task 3: Delete `_EXTRACTION_RESPONSE_JSON_SCHEMA` and add `pydantic` dep ✅

- [x] **Step 3.1:** Delete `_EXTRACTION_RESPONSE_JSON_SCHEMA` from `enrich.py`
- [x] **Step 3.2:** Grep confirms no remaining references
- [x] **Step 3.3:** Delete tests asserting on the old dict constant
- [x] **Step 3.4:** Add `pydantic>=2.0` to `pyproject.toml`
- [x] **Step 3.5:** Full enrich test suite passes (38 tests)
- [x] **Step 3.6:** Commit: `feat(enrich): wire Gemini response_schema structured output`

---

### Task 4: Full Verification ✅

- [x] **Step 4.1:** 121/121 tests pass (all suites)
- [x] **Step 4.2:** Server restarted successfully
- [x] **Step 4.3:** Live run triggered
- [x] **Step 4.4:** Fix applied: `response_mime_type=application/json` required alongside `response_schema` on Vertex AI — committed as `fix(enrich): add response_mime_type=application/json to GenerateContentConfig`

---

### Problems Encountered

| Problem | Fix |
|---|---|
| `400 INVALID_ARGUMENT: Response_schema with response mime type 'text/plain' is unsupported` | Added `response_mime_type="application/json"` to `GenerateContentConfig` — Vertex AI requires both fields |
| Legacy tests asserting old dict schema (`response_json_schema`, `response_mime_type` dict keys) | Updated to assert `GenerateContentConfig` called with `response_schema=EnrichmentOutput` |
| `list[str]` field rejects `None` at Pydantic construction time | Removed invalid test; Pydantic enforces type at construction, making runtime `None`-filtering redundant |
