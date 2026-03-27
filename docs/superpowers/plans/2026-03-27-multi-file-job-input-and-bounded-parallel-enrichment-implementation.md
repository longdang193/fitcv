# Multi-File Job Input and Bounded Parallel Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-file jobs upload support for one logical run and speed up enrichment with bounded parallel execution while preserving one merged run snapshot and existing downstream pipeline behavior.

**Architecture:** Keep the current one-`jobs_path` pipeline contract by validating multiple uploaded JSON files, concatenating them into one canonical merged upload file, and storing that merged payload in `jobs_input_json`. Add conservative admin-managed settings for `enrichment_batch_size` and `enrichment_concurrency`, then refactor `enrich_batch()` to process pre-filtered jobs in bounded parallel batches while preserving deterministic output order for downstream storage and admin inspection. The existing cheap-first pipeline order already runs pre-enrichment global filters before `enrich_batch()`, so this plan preserves that placement rather than redesigning `pipeline.py`.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, BigQuery, concurrent.futures, pytest

---

## File Map

- **Modify:** `src/fitcv_cp/app.py`
  - multi-file upload handling and canonical merge snapshot creation
- **Modify:** `src/fitcv_cp/templates/runs_list.html`
  - upload control supports selecting multiple JSON files
- **Modify:** `src/fitcv_cp/settings_schema.py`
  - add admin-editable enrichment concurrency settings and validation
- **Modify:** `src/fitcv_cp/models.py`
  - update `jobs_input_json` field comment to match upload-mode merged snapshots
- **Modify:** `src/fitcv/enrich.py`
  - add bounded parallel batch enrichment while preserving deterministic result ordering
- **Check only:** `src/fitcv/pipeline.py`
  - confirm enrichment still runs only after pre-enrichment filtering; no code change expected unless a regression test needs a small helper adjustment
- **Modify:** `tests/test_fitcv_cp/test_app.py`
  - multi-file upload trigger tests
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`
  - new settings validation coverage
- **Modify:** `tests/test_enrich.py`
  - bounded parallel enrichment behavior and ordering tests
- **Modify:** `tests/test_pipeline.py`
  - regression coverage that cheap-first filtering still narrows the job set before enrichment

---

## Task 1: Add bounded enrichment settings to the admin config layer

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Test: `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 1: Write failing settings-schema tests**

Add tests for:
- `enrichment_batch_size` is registered
- `enrichment_concurrency` is registered
- both validate as positive integers
- zero or negative values are rejected
- both write to the expected config paths

Example:
```python
def test_enrichment_parallelism_keys_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "enrichment_batch_size" in keys
    assert "enrichment_concurrency" in keys
```

- [x] **Step 2: Run the targeted settings tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py
```

Expected:
- FAIL because the new keys do not exist yet

- [x] **Step 3: Add schema entries in `settings_schema.py`**

Add two `int` settings to the timing/throttling section:
```python
{
    "key": "enrichment_batch_size",
    "type": "int",
    "default": 10,
    "label": "Enrichment Batch Size",
    "description": "How many jobs to enrich in one bounded worker batch.",
    "group": "timing",
    "config_path": ["enrichment_batch_size"],
},
{
    "key": "enrichment_concurrency",
    "type": "int",
    "default": 1,
    "label": "Enrichment Concurrency",
    "description": "How many enrichment batches may run concurrently.",
    "group": "timing",
    "config_path": ["enrichment_concurrency"],
},
```

- [x] **Step 4: Keep validation simple and strict**

No new validator branch is needed if the existing `int >= 1` rule is reused.
Confirm the new keys fit that existing rule cleanly.

- [x] **Step 5: Re-run the targeted settings tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/test_fitcv_cp/test_settings_schema.py
git commit -m "feat(cp): add bounded enrichment settings"
```

---

## Task 2: Add multi-file upload support to the admin trigger flow

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/models.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1: Write failing app tests for multi-file upload mode**
- [x] **Step 2: Run the targeted app tests to verify failure**
- [x] **Step 3: Update the upload route signature for backward-compatible multi-file support**
- [x] **Step 4: Validate all uploaded files before merge**
- [x] **Step 5: Build the canonical merged upload**
- [x] **Step 6: Update the upload UI control**
- [x] **Step 7: Update the `PipelineRun` field comment**
- [x] **Step 8: Re-run the targeted app tests** — PASS (8 upload_trigger tests, 70 total CP tests)
- [x] **Step 9: Commit** — `ca70b9f feat(cp): support multi-file job uploads`

---

## Task 3: Refactor `enrich_batch()` for bounded parallel execution

**Files:**
- Modify: `src/fitcv/enrich.py`
- Test: `tests/test_enrich.py`

- [x] **Step 1: Write failing enrichment tests for bounded parallelism**
- [x] **Step 2: Run the targeted enrichment tests to verify failure**
- [x] **Step 3: Extract `_enrich_chunk` helper** — added `threading.Lock` for global rate limiting (see Debug Log below)
- [x] **Step 4: Add chunking logic**
- [x] **Step 5: Run chunks with bounded concurrency** — `ThreadPoolExecutor(max_workers=concurrency)`
- [x] **Step 6: Flatten chunk results in original order**
- [x] **Step 7: Preserve existing failure semantics** — fail-fast via `future.result()` re-raise
- [x] **Step 8: Re-run the targeted enrichment tests** — PASS (9 enrich_batch tests)
- [x] **Step 9: Commit** — `3506b7a feat: add bounded parallel enrichment`

---

## Task 4: Wire new settings into runtime config without changing cheap-first pipeline placement

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_pipeline.py`

- [x] **Step 1: Make `enrich_batch()` read the new config keys with safe defaults**
- [x] **Step 2: Add one focused config-driven enrichment test**
- [x] **Step 3: Add one control-plane test that the new settings can enter effective config**
- [x] **Step 4: Add one pipeline regression test for pre-enrichment narrowing** — `test_run_pipeline_forwards_enrichment_parallelism_config_to_enrich_batch`
- [x] **Step 5: Run focused tests** — PASS
- [x] **Step 6: Commit** — `7093ffe test: add pipeline regression and enrichment parallelism tests`

---

## Task 5: Full verification

**Files:**
- No new product files

- [x] **Step 1: Run control-plane tests** — 70 passed
- [x] **Step 2: Run focused enrichment tests** — 83 passed (2 pre-existing failures unrelated to this feature)
- [x] **Step 3: Run broader non-integration suite** — 489 passed, 7 skipped
- [x] **Step 4: Manual admin verification** — multi-file upload confirmed working in browser; 429 issue discovered and fixed (see Debug Log)
- [x] **Step 5: Final commit** — `583addf` pushed to `origin/feat/admin-control-plane`

---

## Important Notes

- **Keep one logical run.** Multiple uploaded files must still produce one `run_id`, one merged `jobs_path`, and one run-detail view.
- **Validate before merge.** Do not write the merged snapshot until every uploaded file passes JSON-array validation.
- **Apply upload guardrails.** The first implementation should enforce reasonable file-count and total-size limits, even if the exact thresholds are implementation-defined.
- **Preserve deterministic order.** File order and row order must be preserved in the merged snapshot and in the final flattened enrichment result.
- **Do not add merge-time dedup.** Rely on existing downstream normalization/deduplication first.
- **BigQuery is storage only.** Parallelism belongs in `enrich.py` / worker-side orchestration, not in BigQuery.
- **Keep concurrency bounded.** `enrichment_batch_size` and `enrichment_concurrency` must stay conservative and validated as positive integers.
- **Default concurrency must stay conservative.** Use `enrichment_concurrency=1` by default; higher values are opt-in tuning and may require provider-specific rate-limit adjustments.
- **Per-thread sleep is not a global throttle.** `enrichment_sleep_secs` should not be documented or treated as a true global rate limiter once concurrency is greater than `1`.
- **Fail fast on non-recoverable chunk errors.** Parallel chunk execution must not silently downgrade failures that the sequential `enrich_batch()` path would have raised.
- **`jobs_input_json` is acceptable for current scope.** If merged upload snapshots become substantially larger later, revisit whether the run should store a lighter snapshot plus metadata instead of the full merged payload.

---

## Debug Log

### Bug: `429 RESOURCE_EXHAUSTED` on first multi-file run

**Date:** 2026-03-27  
**Commit fixed:** `149e7cb fix(enrich): add global rate-limit lock; default concurrency to 1`

**Symptom:**
First live multi-file run (19 jobs, 2 merged files) failed after 156 seconds with:
```
429 RESOURCE_EXHAUSTED — Resource exhausted. Please try again later.
```
Pipeline stage: `layer1b_pre_filter (19 pass) → pipeline_failed`

**Root cause:**
The initial `_enrich_chunk` implementation used `time.sleep(enrichment_sleep_secs)` as a per-thread rate limiter between jobs within each chunk. This is not a global rate limiter when `enrichment_concurrency > 1`. With two concurrent chunks, two threads could both call the Vertex AI API simultaneously, effectively doubling the API call rate and exhausting quota faster than expected.

Additionally, the `enrichment_concurrency` schema default was set to `2` (implementation error — plan spec required `1`).

**Fixes applied:**
1. **`src/fitcv_cp/settings_schema.py`** — corrected `enrichment_concurrency` default from `2` → `1`. Updated description to warn that higher values are provider-sensitive and per-thread sleep is not a global rate limiter.
2. **`src/fitcv/enrich.py`** — added module-level `_ENRICH_RATE_LOCK: threading.Lock`. In `_enrich_chunk`, every `enrich_job` call + the subsequent success-path sleep is now wrapped in `with _ENRICH_RATE_LOCK:`, serializing all API calls across all concurrent chunk threads globally.
3. **Hardcoded fallback default** in `enrich_batch()` corrected from `2` → `1`.
4. **3 retry test assertions** updated: the success-path sleep now fires inside the lock on each successful call, so `sleeps` lists each include one extra `sleep_secs` entry at the end.

**Verification:**
```
83 passed, 2 pre-existing failures (unrelated)
```
