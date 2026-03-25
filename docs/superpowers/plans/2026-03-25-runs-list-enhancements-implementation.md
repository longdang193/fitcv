# Runs List Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide an easy way to refresh run statuses and allow direct uploading of `jobs.json` datasets through the UI.

**Architecture:** Introduce a new `POST /admin/upload-trigger` multipart form handler in `app.py` which saves attachments to `data/uploads/` and triggers a run. Update the `runs_list.html` form with a file input and a refresh button.

**Tech Stack:** Python, FastAPI (`UploadFile`, `Form`), JavaScript (Fetch API `FormData`)

---

### Task 1: Backend Upload API

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 1.1: Extract trigger logic**
In `src/fitcv_cp/app.py`, extract the core body of `trigger_run` into a private helper function `_execute_trigger(jobs_path: str, config_path: str, triggered_by: str, config_overrides: dict, bq: Any, project: str, dataset: str, redis_url: str) -> dict`. Keep `app.post("/runs")` intact by unpacking the `TriggerRequest` and calling the helper.

- [ ] **Step 1.2: Build the Upload Route**
In `src/fitcv_cp/app.py`, add `@app.post("/admin/upload-trigger", status_code=201)`. Use `jobs_file: fastapi.UploadFile = fastapi.File(None)`, and `fastapi.Form` for other fields. Ensure a configured path like `data/uploads/` exists via pathlib. Generate a unique name for the file (e.g. `uuid4().hex + ".json"`), read it asynchronously, write it to disk, and pass its resulting absolute or relative path to `_execute_trigger()`. If no file is provided, use the fallback `jobs_path`. *Note: The architectural contract assumes the web app and worker share this filesystem layer for queued paths to remain readable.*

- [ ] **Step 1.3: Write failing & passing tests**
In `tests/test_fitcv_cp/test_app.py`, write `test_admin_upload_trigger_success` that uses `TestClient` to send multipart form data. **Crucially**, patch the `data/uploads/` destination directory to point to a Pytest `tmp_path` fixture to prevent leaking test artifacts into the workspace. Verify it returns 201 Created and asserts that the temporary file matches the payload. Run `/tmp/fitcv-test-env/bin/pytest tests/test_fitcv_cp/test_app.py -v`. Commit changes.

---

### Task 2: Frontend UI Integrations

**Files:**
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 2.1: Add UI elements**
In `runs_list.html`, add `<a href="/admin/runs" class="button" style="text-decoration:none;font-size:0.85rem">⟳ Refresh Status</a>` to the page header area. Inside the `.form-row`, retain the existing `jobs_path` text input as the manual fallback path, and place a new `<input type="file" id="jobs_file" accept=".json">` tightly adjacent to it.

- [ ] **Step 2.2: Update JS `triggerRun` logic**
In `scripts` block of `runs_list.html`, check if `#jobs_file` has files (`document.getElementById('jobs_file').files.length > 0`). If so, build a `FormData` object, append the file and the `config_path` value, and `fetch('/admin/upload-trigger', {method: 'POST', body: formData})`. If no file, retain the existing `fetch('/runs', {method: 'POST', body: JSON.stringify(...)})` behavior using the text of `#jobs_path`. 

- [ ] **Step 2.3: Verify rendering**
In `test_app.py`, update UI tests to ensure the `<input type="file">` and the new "Refresh" button text exist in the rendered HTML. Run full suite. Commit changes.

## Debug Log

### 2026-03-25: `sample_data_engineer_jobs.json` enrichment investigation

- Symptom observed:
  - A run against `data/sample_data_engineer_jobs.json` showed `Total Jobs = 10`, but the event timeline reported `Ingested 10 jobs, enriched 1`.

- Initial hypothesis checked:
  - The admin setting `enrichment_sleep_secs = 10` was reviewed.
  - Verified this setting only controls the delay between enrichment API calls.
  - It does not limit the number of jobs sent to enrichment.

- Data checks performed:
  - Confirmed `data/sample_data_engineer_jobs.json` contains 10 records.
  - Confirmed all 10 input records have distinct `jobUrl` values.

- Pipeline trace:
  - Verified `run_pipeline()` reports `len(enriched)` after `enrich_batch(normalized, config)`.
  - Therefore the `enriched 1` message implied the list had already been reduced before or during enrichment.

- Root cause found:
  - `normalize_batch()` in `src/fitcv/normalize.py` deduplicated raw scraper payloads before converting scraper keys like `jobUrl` to canonical keys like `job_url`.
  - Because exact dedupe looked for `job_url` on raw LinkedIn records, every raw row appeared to have an empty URL.
  - Exact deduplication therefore kept only the first record and dropped the remaining 9.

- Fix applied:
  - Updated `normalize_batch()` to normalize each record first, then run exact and near-duplicate deduplication on the normalized shape.

- Regression test added:
  - Added a unit test to `tests/test_normalize.py` covering raw scraper-style `jobUrl` keys before deduplication.

- Verification evidence:
  - `/tmp/fitcv-test-env/bin/python -m pytest tests/test_normalize.py -v` → `24 passed`
  - Direct check before fix:
    - `raw = 10`
    - `normalized = 1`
  - Direct check after fix:
    - `raw = 10`
    - `normalized = 10`

- Outcome:
  - The “only 1 job enriched” issue was caused by preprocessing/deduplication, not by the enrichment delay setting.
  - A new run against `data/sample_data_engineer_jobs.json` should now send all 10 normalized jobs into enrichment.
