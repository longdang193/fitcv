# Admin CV Downloads — Design Specification

## Current Status

- Status: implemented in code, with one post-implementation bug fixed and one remaining verification gap.
- Implemented components:
  - `cv_versions.run_id` support in DDL, tracker payload, and pipeline persistence
  - migration script at `scripts/migrations/001_add_run_id_to_cvs.py`
  - control-plane data access in `bq_store.py`
  - download endpoint in `app.py`
  - run detail rendering of `cv_versions` download links in `run_detail.html`
- Post-implementation fix:
  - The first implementation wrote `cv_versions.run_id` using a pipeline-generated UUID instead of the control-plane run ID.
  - This prevented the run detail page from finding its own generated CV rows.
  - The pipeline now accepts an injected `run_id`, and the worker passes the control-plane run ID through.
- Verification status:
  - Verified: pipeline and worker regression suites
  - Needs follow-up: `tests/test_fitcv_cp/test_app.py` hangs in this environment and has not been freshly confirmed end-to-end here.

## Problem

Currently, the pipeline generates CVs and persists them successfully to the `cv_versions` BigQuery table. However, the Admin UI has no way to view or download these CVs. Additionally, `cv_versions` does not track which `run_id` generated the CV, making it impossible to render a reliable list of outputs on a specific Run Detail page. 

## Goals

- Establish a logical foreign-key relationship between `cv_versions` and `pipeline_runs`. (Note: BigQuery does not strictly enforce physical foreign keys; this operates as a documented logical join key).
- Serve the generated markdown CVs directly from the web app as file downloads.
- Keep the user experience contextual by listing a run's generated CVs directly on its Run Detail page.

## Architecture & Data Changes

1. **BigQuery Schema**:
   - The `cv_versions` table will be updated to include a new `run_id` column (STRING) that acts as a logical foreign key to `pipeline_runs.run_id`.
   - We will write a reproducible Python script `scripts/migrations/001_add_run_id.py` using `google-cloud-bigquery` to execute the `ALTER TABLE` DDL, avoiding manual CLI commands.

2. **Backend Tracker Integration**:
   - `create_cv_version_record()` in `src/fitcv/tracker.py` will be updated to accept `run_id`.
   - The main loop in `src/fitcv/pipeline.py` will start passing its local `run_id` down into the tracker.

3. **Control Plane Data Access (`bq_store.py`)**:
   - We will maintain separation of concerns by adding two new data-access functions to `src/fitcv_cp/bq_store.py`:
     - `list_cvs_for_run(run_id, ...)`: Fetches CV metadata for the list view.
     - `get_cv_markdown(version_id, ...)`: Fetches the raw string content for downloads.

4. **Web API & Routing (`app.py`)**:
   - The `GET /admin/runs/{run_id}` endpoint will call `list_cvs_for_run()` and pass the list to the template.
   - We will introduce a new lightweight endpoint `GET /admin/cvs/{version_id}/download` that calls `get_cv_markdown()`. If not found, it raises a 404. If found, it returns the content as an HTTP attachment.

5. **UI Updates (`run_detail.html`)**:
   - Inside the successful run banner (or just below it), we will iterate over the fetched CVs and display a list.
   - Each item will show the Job URL, the fit classification badge, and a `<a href="/admin/cvs/{version_id}/download"> Download ` button.

## Sequence Flow

1. User clicks "Download" on `/admin/runs/abc-123`
2. Browser sends `GET /admin/cvs/xyz-987/download`
3. FASTAPI backend hands off to `bq_store.get_cv_markdown('xyz-987')`
4. `bq_store` executes `SELECT cv_markdown FROM cv_versions WHERE version_id = @id`
5. FASTAPI responds with `Content-Type: text/markdown` and `Content-Disposition: attachment; filename="cv_xyz-987.md"`

## Test Strategy

- `bq_store.py` tests will mock `bq.query` to ensure the correct sql parameter passing.
- `app.py` tests will assert that the download endpoint correctly handles the `200 OK` path with valid content-disposition headers, and the `404 Not Found` path.
- `app.py` template tests will mock `list_cvs_for_run` to assert that the run detail page renders a list of CV download buttons, handles empty lists gracefully, and correctly formats job links.

## Debug Log

- User-visible symptom:
  - The run detail page showed `cvs_generated > 0` in the success banner, but no "Download Markdown" buttons appeared.
- What was investigated:
  - The `cv_versions` table contents for recent runs
  - server logs and rendered `run_detail.html`
  - `list_cvs_for_run()` behavior in `bq_store.py`
  - query caching behavior in BigQuery
- Intermediate finding:
  - Query caching was a plausible source of stale reads and was disabled for CV lookup queries with `use_query_cache=False`.
- Root cause:
  - The admin control plane and the pipeline were using different run IDs for the same logical run.
  - The page URL, `pipeline_runs`, and event timeline used the control-plane run ID.
  - `cv_versions.run_id` was populated from a separate UUID generated inside `run_pipeline()`.
  - Because the UI queried `cv_versions` by the control-plane run ID, it received an empty list and rendered no buttons.
- Corrective action:
  - `run_pipeline()` now accepts an externally supplied `run_id`.
  - The worker injects the control-plane run ID into `run_pipeline()`.
  - New regression tests lock down that the supplied run ID is used for both the pipeline summary and CV persistence.
