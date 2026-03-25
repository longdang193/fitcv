# CV Downloads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to seamlessly download generated cv markdown files directly from the pipeline run detail page.

**Architecture:** Introduce `run_id` to BigQuery's `cv_versions` table via a python migration snippet, update the pipeline tracking payload to log it, expose data access safely in `bq_store.py`, and deliver a new FastAPI route to fetch and serve the raw text as a downloaded attachment.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

## Status

- Overall status: implemented in code, with one follow-up verification gap.
- Functional status:
  - `cv_versions.run_id` support exists in the canonical DDL and tracker payload.
  - The migration script exists at `scripts/migrations/001_add_run_id_to_cvs.py`.
  - `bq_store.py` exposes `list_cvs_for_run()` and `get_cv_markdown()`.
  - `app.py` exposes `GET /admin/cvs/{version_id}/download` and passes `cv_versions` into the run detail template.
  - `run_detail.html` renders download links when matching CV rows are returned.
  - The worker now passes the control-plane `run_id` into `run_pipeline()`, and `run_pipeline()` uses that supplied ID as the canonical run ID for summary and CV persistence.
- Verification status:
  - Verified: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_pipeline.py -v`
  - Verified: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_worker_job.py -v`
  - Not fully verified in this environment: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_app.py -v` appears to hang at the first test and needs separate investigation.

---

### Task 1: Schema Updates & Pipeline Tracking

**Files:**
- Create: `scripts/migrations/001_add_run_id_to_cvs.py`
- Modify: `assets/bigquery/cv_versions.sql`
- Modify: `src/fitcv/tracker.py`
- Modify: `src/fitcv/pipeline.py`

- [x] **Step 1.1: Update canonical DDL file**
Add `run_id STRING OPTIONS(description="Logical FK to pipeline_runs")` directly below the `version_id` column in `assets/bigquery/cv_versions.sql`.

- [x] **Step 1.2: Write reproducible migration script**
Create `scripts/migrations/001_add_run_id_to_cvs.py` that utilizes `google.cloud.bigquery.Client` to execute the DDL: `ALTER TABLE {project}.{dataset}.cv_versions ADD COLUMN IF NOT EXISTS run_id STRING;` and prints a success message.

- [ ] **Step 1.3: Run the migration**
Execute the migration script against the currently configured database to safely alter the schema.

- [x] **Step 1.4: Update tracker.py**
Add `run_id: str` to the arguments of `create_cv_version_record()` and map it to `"run_id": str(run_id)` in the returned dictionary.

- [x] **Step 1.5: Update pipeline.py**
Update the call to `create_cv_version_record` around line 265 to pass `run_id=run_id`. Also update `run_pipeline()` to accept an injected `run_id`, and update the worker to pass the control-plane run ID into the pipeline so `pipeline_runs`, event logs, and `cv_versions` share the same canonical identifier.

- [ ] **Step 1.6: Commit**
Commit schema updates, migrations, and pipeline tracking integration.

---

### Task 2: Data Access Layer (bq_store.py)

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 2.1: Write failing store tests**
In `test_bq_store.py`, write `test_list_cvs_for_run` and `test_get_cv_markdown`. Mock `bq.query` and assert queries use parameterized inputs. Ensure `get_cv_markdown` correctly handles empty query results (returning `None`).

- [x] **Step 2.2: Implement `list_cvs_for_run`**
In `bq_store.py`, implement `list_cvs_for_run(run_id, bq_client, project, dataset)`. Execute a parameterized query: `SELECT version_id, job_url, fit_classification, generated_at FROM {table} WHERE run_id = @run_id ORDER BY generated_at DESC`. Return a list of dicts.

- [x] **Step 2.3: Implement `get_cv_markdown`**
In `bq_store.py`, implement `get_cv_markdown(version_id, bq_client, project, dataset)`. Execute a parameterized query: `SELECT cv_markdown FROM {table} WHERE version_id = @version_id LIMIT 1`. Return the string if found, otherwise `None`.

- [ ] **Step 2.4: Ensure tests pass & Commit**
Store tests exist. Final commit status remains open in this plan log.

---

### Task 3: API Endpoints & UI Rendering

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`

- [x] **Step 3.1: Write failing API & UI tests**
In `test_app.py`, write tests for `GET /admin/cvs/{id}/download` covering both the 200 path (verify `Content-Disposition`) and the 404 path. Next, update `test_admin_run_detail_success_banner` to mock `list_cvs_for_run` returning mock data, and assert the UI renders the download link (`href="/admin/cvs/.../download"`). Add a test `test_admin_run_detail_empty_cvs` for when 0 CVs exist but the status is succeeded.

- [x] **Step 3.2: Build the FastAPI Route**
In `src/fitcv_cp/app.py`, add `GET /admin/cvs/{version_id}/download`. Call `bq_store.get_cv_markdown`. If none, raise `HTTPException(404)`. If found, return `Response(content=md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="cv_{version_id}.md"'})`.

- [x] **Step 3.3: Fetch CVs in the Run Detail route**
In `src/fitcv_cp/app.py` inside `get_run_detail`, call `bq_store.list_cvs_for_run(run_id)` and pass the result `cv_versions=fetched_list` to the `TemplateResponse` context.

- [x] **Step 3.4: Update the Run Detail Template**
In `run_detail.html`, below the Pipeline Results text, loop through `cv_versions` to render the job link, fit badge, and download anchor. Handle the case where `cv_versions` is empty.

- [ ] **Step 3.5: Run tests & Commit**
Partial verification complete:
- Passed: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_pipeline.py -v`
- Passed: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_worker_job.py -v`
- Needs follow-up: `/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_app.py -v` hangs in this environment.

## Problems Debugged

- Symptom observed:
  - The run detail page showed the success banner with `cvs_generated > 0`, but no per-CV download buttons rendered below it.
- Initial hypothesis checked:
  - BigQuery query caching on `list_cvs_for_run()` and `get_cv_markdown()` was investigated and disabled via `use_query_cache=False`.
- Root cause found:
  - The control-plane run ID and the pipeline-internal run ID diverged.
  - `pipeline_runs` and the event timeline used the admin/control-plane run ID.
  - `cv_versions.run_id` was being written with a separate pipeline-generated run ID.
  - The UI queried `cv_versions` by the admin run ID, so `list_cvs_for_run()` returned an empty list even when a CV row existed.
- Evidence used:
  - The run detail page showed different run IDs in the header and the pipeline start/timeline messages.
  - The route and template logic already rendered download buttons when `cv_versions` was non-empty, which ruled out the template as the primary issue.
  - The worker called `run_pipeline()` without passing the control-plane run ID, and `run_pipeline()` always generated a fresh UUID internally.
- Fix applied:
  - `run_pipeline()` now accepts an optional injected `run_id`.
  - The worker now passes the control-plane `run_id` into `run_pipeline()`.
  - Regression tests were added to enforce that the supplied run ID is used for both the pipeline summary and `create_cv_version_record()`.
