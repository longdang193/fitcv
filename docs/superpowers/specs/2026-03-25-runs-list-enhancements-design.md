# Runs List Enhancements — Design Specification

## Problem
Currently, the pipeline runs list only provides a static view of jobs and lacks a refresh mechanism. Furthermore, the UI string-based trigger requires jobs to be pre-existing on the server filesystem, preventing users from uploading ad-hoc `jobs.json` files for evaluation.

## Goals
1. Add a low-friction refresh mechanism to `/admin/runs` to quickly check status changes.
2. Enable file uploading of arbitrary JSON job lists through the `/admin/runs` web interface so users can test new requirements without terminal access.

## Architecture

**1. Auto-Refresh Button:**
- A simple HTML `<a href="/admin/runs" class="button">⟳ Refresh List</a>` added to the top of `runs_list.html`. Avoids heavy JS polling frameworks while solving the immediate UX pain point elegantly.

**2. Custom JSON Uploads:**
- **Storage Contract (Shared Filesystem):** For now, the application contract explicitly assumes the web application and the queue worker share the same writable disk/filesystem (as they currently do for reading `data/sample_jobs.json`). Uploaded files will be written to `data/uploads/`.
- **UI Modifications:** The form in `runs_list.html` will retain the existing manual text input (`#jobs_path`) as a fallback, and place a new `<input type="file" id="jobs_file" accept=".json">` next to it.
- **Trigger Logic:** The JS function `triggerRun()` will dynamically switch between JSON payloads and `FormData`:
  - If a file is selected in the file input, it performs a `fetch` with `FormData` to a new `POST /admin/upload-trigger` endpoint.
  - If no file is selected, it falls back to the existing `POST /runs` JSON payload using the string value in the manual text input, preserving the current behavior.
- **Backend (`app.py`):**
  - `POST /runs` logic will be extracted into a helper `_execute_trigger(...)`.
  - A new endpoint `POST /admin/upload-trigger` will be created using `File()` and `Form()`.
  - The script will save uploaded files to a persistent `data/uploads/` directory, generating a unique filepath with `uuid4()`, and pass that path into `_execute_trigger()`.

## Verification Plan
Automated tests will be added to `test_app.py` ensuring the upload endpoint correctly persists the file and calls the trigger helper. The tests will patch the upload directory to a temporary path (e.g., via Pytest's `tmp_path`) to prevent polluting the `data/uploads/` directory with test artifacts. UI tests will confirm the refresh button and file input render correctly alongside the manual path fallback.
