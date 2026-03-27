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

- [ ] **Step 1: Write failing settings-schema tests**

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

- [ ] **Step 2: Run the targeted settings tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py
```

Expected:
- FAIL because the new keys do not exist yet

- [ ] **Step 3: Add schema entries in `settings_schema.py`**

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

- [ ] **Step 4: Keep validation simple and strict**

No new validator branch is needed if the existing `int >= 1` rule is reused.
Confirm the new keys fit that existing rule cleanly.

- [ ] **Step 5: Re-run the targeted settings tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py
```

Expected:
- PASS

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: Write failing app tests for multi-file upload mode**

Add tests for:
- upload mode accepts two JSON files and returns `201`
- uploaded files are validated individually before merge
- one invalid file rejects the whole request with `422`
- merged snapshot in `jobs_input_json` preserves file order and row order
- empty arrays are allowed per-file, but an all-empty merged upload is rejected

Example:
```python
def test_admin_upload_trigger_merges_multiple_job_files():
    ...
    assert resp.status_code == 201
```

- [ ] **Step 2: Run the targeted app tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "upload_trigger"
```

Expected:
- FAIL because the route only accepts one jobs file

- [ ] **Step 3: Update the upload route signature for backward-compatible multi-file support**

In `app.py`, update `upload_trigger()` to accept both legacy single-file submissions and new multi-file submissions.

One acceptable shape is:
```python
jobs_files: list[UploadFile] = File(default_factory=list)
jobs_file: UploadFile | None = File(None)
```

Compatibility rule:
- if `jobs_files` is empty and `jobs_file` is provided, treat it as a one-file list
- if both are empty in upload mode, reject the request

This preserves current clients while enabling the new UI.
The exact FastAPI `File(...)` signature can be adjusted if needed, but the internal normalization rule must remain the same.

- [ ] **Step 4: Validate all uploaded files before merge**

In upload mode:
- read each uploaded file
- decode as UTF-8
- parse JSON
- require top-level array
- track original filename for error reporting
- reject the entire request if any file fails

Use error messages that identify the failing file:
```python
raise HTTPException(status_code=422, detail=f"Invalid jobs JSON in {filename}: {exc}")
```

Also apply basic operational guardrails:
- enforce a reasonable maximum number of uploaded files per request
- enforce a reasonable maximum total upload size, or explicitly fail fast once a combined-size threshold is exceeded

The exact thresholds can remain implementation-defined, but the first version should not allow unbounded upload fan-in.

- [ ] **Step 5: Build the canonical merged upload**

After all files validate:
- concatenate arrays in submitted file order
- preserve row order within each file
- reject if merged result is empty
- serialize canonical merged JSON once
- write one merged file into `data/uploads/`
- set:
  - `actual_jobs_path` to the merged file path
  - `jobs_input_source = "upload"`
  - `jobs_input_json_snapshot` to the canonical merged JSON string

Suggested filename pattern:
```python
f"{uuid.uuid4().hex}_merged_jobs.json"
```

Keep storing the canonical merged payload in `jobs_input_json` for this first version.
That is acceptable for current expected run sizes, but if merged upload snapshots grow materially later, the system may need to evolve toward a lighter snapshot/reference model.

- [ ] **Step 6: Update the upload UI control**

In `runs_list.html`:
- add `multiple` to the jobs file input
- update the client-side JS to append all selected files to `FormData` under `jobs_files`

Example:
```javascript
for (const f of document.getElementById('jobs_file').files) {
  fd.append('jobs_files', f);
}
```

Do not remove single-file usability; selecting one file should still work naturally.

- [ ] **Step 7: Update the `PipelineRun` field comment**

In `models.py`, update the comment on `jobs_input_json` so it no longer says paste-only semantics.

Example:
```python
jobs_input_json: Optional[str] = None  # canonical JSON snapshot (paste/upload merged payload)
```

- [ ] **Step 8: Re-run the targeted app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "upload_trigger"
```

Expected:
- PASS

- [ ] **Step 9: Commit**

```bash
git add src/fitcv_cp/app.py src/fitcv_cp/templates/runs_list.html \
  src/fitcv_cp/models.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): support multi-file job uploads"
```

---

## Task 3: Refactor `enrich_batch()` for bounded parallel execution

**Files:**
- Modify: `src/fitcv/enrich.py`
- Test: `tests/test_enrich.py`

- [ ] **Step 1: Write failing enrichment tests for bounded parallelism**

Add tests for:
- batching respects `enrichment_batch_size`
- concurrency uses `enrichment_concurrency`
- result ordering remains deterministic and matches input order
- jobs are not dropped when batches complete out of order
- `enrichment_concurrency=1` still behaves like sequential bounded batching

Example:
```python
def test_enrich_batch_preserves_input_order_under_parallel_batches():
    jobs = [{"job_url": "u1"}, {"job_url": "u2"}, {"job_url": "u3"}]
    ...
    assert [row["job_url"] for row in result] == ["u1", "u2", "u3"]
```

- [ ] **Step 2: Run the targeted enrichment tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_enrich.py -k "enrich_batch"
```

Expected:
- FAIL because `enrich_batch()` is currently purely sequential

- [ ] **Step 3: Extract a small helper to enrich one bounded batch**

In `enrich.py`, introduce a focused helper:
```python
def _enrich_chunk(chunk: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    ...
```

This helper should preserve the current retry/backoff behavior for each job in the chunk.

Do not duplicate retry logic across two code paths.

- [ ] **Step 4: Add chunking logic**

Split `normalized_jobs` into chunks using `enrichment_batch_size`.

Example:
```python
chunks = [
    normalized_jobs[i:i + batch_size]
    for i in range(0, len(normalized_jobs), batch_size)
]
```

- [ ] **Step 5: Run chunks with bounded concurrency**

Use `ThreadPoolExecutor(max_workers=enrichment_concurrency)` because enrichment is network-bound.

Recommended shape:
```python
with ThreadPoolExecutor(max_workers=concurrency) as ex:
    futures = [ex.submit(_enrich_chunk, chunk, config) for chunk in chunks]
```

Important rule:
- collect chunk results by original chunk index, not completion order

This preserves deterministic merged output ordering.
Bounded parallel enrichment still applies only to jobs that survive pre-enrichment global filtering; it must not expand enrichment back to the full normalized input set.

- [ ] **Step 6: Flatten chunk results in original order**

After all futures finish:
- assemble chunk results in original chunk order
- flatten to one enriched result list

Do not let downstream correctness depend on future-completion order.

- [ ] **Step 7: Preserve existing failure semantics**

Keep the current contract explicit:
- individual per-job retry handling stays intact
- catastrophic provider/config failures may still raise and fail the run
- if you introduce per-chunk exception handling, it must not silently swallow failures that the current function would raise
- if any chunk raises a non-recoverable exception that would previously have failed `enrich_batch()`, the parallel version must still fail the enrichment stage rather than silently degrading to partial success

If you decide to keep existing fail-fast semantics inside `enrich_batch()`, document that in a code comment.

- [ ] **Step 8: Re-run the targeted enrichment tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_enrich.py -k "enrich_batch"
```

Expected:
- PASS

- [ ] **Step 9: Commit**

```bash
git add src/fitcv/enrich.py tests/test_enrich.py
git commit -m "feat: add bounded parallel enrichment"
```

---

## Task 4: Wire new settings into runtime config without changing cheap-first pipeline placement

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Make `enrich_batch()` read the new config keys with safe defaults**

Read:
```python
batch_size = int(config.get("enrichment_batch_size", 10))
concurrency = int(config.get("enrichment_concurrency", 1))
```

These defaults must match the settings schema defaults.
Keep `enrichment_concurrency=1` as the default so the first rollout preserves the reliability characteristics of the old sequential enrichment path.

- [ ] **Step 2: Add one focused config-driven enrichment test**

Add a test proving a custom config is used:
```python
def test_enrich_batch_uses_configured_batch_size_and_concurrency():
    ...
```

- [ ] **Step 3: Add one control-plane test that the new settings can enter effective config**

In `test_fitcv_cp/test_app.py`, add a trigger test with mocked active settings:
- `enrichment_batch_size = 5`
- `enrichment_concurrency = 3`

Assert the stored `effective_settings_json` includes those values, just like other admin-managed settings do.

- [ ] **Step 4: Add one pipeline regression test for pre-enrichment narrowing**

In `tests/test_pipeline.py`, add a focused regression test showing:
- pre-enrichment global filters still narrow the candidate set first
- `enrich_batch()` receives only surviving normalized jobs
- the new enrichment settings do not change that execution order

Keep this test small by mocking:
- `parse_jobs_file`
- `prepare_raw_rows`
- `apply_pre_enrichment_global_filters`
- `enrich_batch`

- [ ] **Step 5: Run focused tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_enrich.py -k "enrich_batch" \
  tests/test_fitcv_cp/test_app.py -k "effective_settings or upload_trigger" \
  tests/test_pipeline.py -k "pre_enrichment or enrich_batch"
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add src/fitcv/enrich.py tests/test_enrich.py \
  tests/test_fitcv_cp/test_app.py tests/test_pipeline.py
git commit -m "feat: wire bounded enrichment settings into runtime config"
```

---

## Task 5: Full verification

**Files:**
- No new product files

- [ ] **Step 1: Run control-plane tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short tests/test_fitcv_cp
```

Expected:
- PASS

- [ ] **Step 2: Run focused enrichment tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short tests/test_enrich.py
```

Expected:
- PASS

- [ ] **Step 3: Run broader non-integration suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
```

Expected:
- PASS

- [ ] **Step 4: Manual admin verification**

Check in browser:
- upload one jobs JSON file and confirm the run still works
- upload multiple jobs JSON files and confirm one run is created
- inspect `Original Job Input` and confirm it shows one merged canonical snapshot
- confirm runs with larger inputs still populate one `Enriched Jobs` tab
- lower `enrichment_batch_size` / raise `enrichment_concurrency` in settings and confirm the run still completes

- [ ] **Step 5: Final commit**

```bash
git status --short
git add src/fitcv_cp/app.py src/fitcv_cp/templates/runs_list.html \
  src/fitcv_cp/settings_schema.py src/fitcv_cp/models.py \
  src/fitcv/enrich.py tests/test_fitcv_cp/test_app.py \
  tests/test_fitcv_cp/test_settings_schema.py tests/test_enrich.py \
  tests/test_pipeline.py
git commit -m "feat(cp): add multi-file job uploads and bounded parallel enrichment"
```

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
