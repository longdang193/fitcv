# Runs List Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide an easy way to refresh run statuses and allow direct uploading of `jobs.json` datasets through the UI.

**Architecture:** Introduce a new `POST /admin/upload-trigger` multipart form handler in `app.py` which saves attachments to `data/uploads/` and triggers a run. Update the `runs_list.html` form with a file input and a refresh button.

**Tech Stack:** Python, FastAPI (`UploadFile`, `Form`), JavaScript (Fetch API `FormData`)

---

## ✅ STATUS: COMPLETE — Deployed 2026-03-25, extended 2026-03-26

All checkboxes verified against production code. Originally implemented on 2026-03-25.
Extended on 2026-03-26 as part of Admin Run Inspection plan: `runs_list.html` was fully rewritten to expose `jobs_input_mode` (path/upload/paste) and `candidate_profile_mode` (default_config/upload/paste) tabs.

---

### Task 1: Backend Upload API

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1.1: Extract trigger logic**

  `_execute_trigger()` helper exists in `app.py`. Extended on 2026-03-26 to `_execute_trigger_with_inputs()`.

- [x] **Step 1.2: Build the Upload Route**

  `POST /admin/upload-trigger` implemented with `UploadFile`, `Form`, saves to `data/uploads/`.
  Extended on 2026-03-26 to support `jobs_input_mode` (path/upload/paste) and candidate profile overrides.

- [x] **Step 1.3: Write failing & passing tests**

  `test_admin_upload_trigger_success` passes. Updated on 2026-03-26 to use new form fields.

---

### Task 2: Frontend UI Integrations

**Files:**
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 2.1: Add UI elements**

  `runs_list.html` contains `⟳ Refresh Status` button and file input for jobs upload.
  Extended 2026-03-26: full tabbed trigger card with `📂 Path | ⬆ Upload | 📋 Paste JSON` for jobs and `⚙ Default Config | ⬆ Upload JSON | 📋 Paste JSON` for candidate profile.

- [x] **Step 2.2: Update JS `triggerRun` logic**

  JS posts `FormData` to `/admin/upload-trigger` with `jobs_input_mode` and `candidate_profile_mode`.

- [x] **Step 2.3: Verify rendering**

  `test_admin_runs_rendered_nav` asserts `id="jobs_file"` and `id="jobs_path"` present. `372 passed`.

---

## Debug Log

### 2026-03-25: `sample_data_engineer_jobs.json` enrichment investigation

- **Symptom:** Run against `data/sample_data_engineer_jobs.json` showed `Total Jobs = 10`, but event timeline reported `Ingested 10 jobs, enriched 1`.
- **Root cause:** `normalize_batch()` deduplicated raw scraper payloads before converting `jobUrl` → `job_url`. Exact dedup on the raw shape found all records had an empty `job_url`, so 9 were dropped.
- **Fix:** Updated `normalize_batch()` to normalize first, then deduplicate on the normalized shape.
- **Verification:** `tests/test_normalize.py` → `24 passed`. All 10 jobs now flow through enrichment.
