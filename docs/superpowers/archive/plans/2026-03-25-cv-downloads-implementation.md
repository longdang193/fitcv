# CV Downloads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to seamlessly download generated cv markdown files directly from the pipeline run detail page.

**Architecture:** Introduce `run_id` to BigQuery's `cv_versions` table via a python migration snippet, update the pipeline tracking payload to log it, expose data access safely in `bq_store.py`, and deliver a new FastAPI route to fetch and serve the raw text as a downloaded attachment.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

---

## ✅ STATUS: COMPLETE — Deployed 2026-03-25

All steps verified. BQ migration confirmed applied (2026-03-26 live schema check: `cv_versions` contains `run_id` column).

---

### Task 1: Schema Updates & Pipeline Tracking

**Files:**
- Create: `scripts/migrations/001_add_run_id_to_cvs.py`
- Modify: `assets/bigquery/cv_versions.sql`
- Modify: `src/fitcv/tracker.py`
- Modify: `src/fitcv/pipeline.py`

- [x] **Step 1.1: Update canonical DDL file**
- [x] **Step 1.2: Write reproducible migration script** (`scripts/migrations/001_add_run_id_to_cvs.py`)
- [x] **Step 1.3: Run the migration**

  **Confirmed applied:** Live BQ schema check on 2026-03-26 shows `run_id` in `cv_versions` column list:
  `['version_id', 'job_url', ..., 'cv_markdown', 'fit_classification', 'generated_at', 'run_id']`

- [x] **Step 1.4: Update tracker.py** — `create_cv_version_record()` accepts and persists `run_id`
- [x] **Step 1.5: Update pipeline.py** — `run_pipeline()` accepts injected `run_id`; worker passes control-plane run ID
- [x] **Step 1.6: Commit**

---

### Task 2: Data Access Layer (bq_store.py)

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 2.1: Write failing store tests**
- [x] **Step 2.2: Implement `list_cvs_for_run`** — parameterized query by `run_id`
- [x] **Step 2.3: Implement `get_cv_markdown`** — parameterized query by `version_id`, returns `None` if missing
- [x] **Step 2.4: Ensure tests pass & Commit**

  `tests/test_fitcv_cp/test_bq_store.py` passes. Full suite: `372 passed`.

---

### Task 3: API Endpoints & UI Rendering

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`

- [x] **Step 3.1: Write failing API & UI tests** — tests for 200 + 404 download paths, CV list rendering
- [x] **Step 3.2: Build the FastAPI Route** — `GET /admin/cvs/{version_id}/download` returns `text/markdown` attachment
- [x] **Step 3.3: Fetch CVs in the Run Detail route** — `list_cvs_for_run` called; `cv_versions` in template context
- [x] **Step 3.4: Update the Run Detail Template** — download buttons rendered per CV with job link + fit badge
- [x] **Step 3.5: Run tests & Commit** — `372 passed, 7 deselected`

---

## Problems Debugged

### 2026-03-25: CV download buttons not appearing on run detail page

- **Symptom:** Run detail showed success banner with `cvs_generated > 0`, but no per-CV download buttons rendered.
- **Root cause:** Control-plane `run_id` and pipeline-internal `run_id` diverged. The worker called `run_pipeline()` without passing the admin run ID, so `cv_versions.run_id` was written with a fresh UUID. `list_cvs_for_run(admin_run_id)` returned an empty list.
- **Fix:** `run_pipeline()` now accepts optional injected `run_id`. Worker passes the control-plane ID. Regression tests enforce this.
- **Verification:** `tests/test_fitcv_cp/test_worker_job.py` + `tests/test_pipeline.py` pass.
