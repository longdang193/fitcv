# CV Generation Debug Snapshots Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification after each task. Keep the existing final `results_export_json` export unchanged in purpose, and treat CV-generation debug snapshots as a separate admin-debug artifact.

**Goal:** Add a bounded run-scoped CV-generation debug snapshot so admins can inspect the immediate per-job generation path for ranked jobs without rerunning the pipeline.

**Architecture:** Capture per-ranked-job debug records during the live Layer 4 CV-generation path in `pipeline.py`, return them through the worker summary, persist them as a best-effort run-scoped JSON snapshot on `pipeline_runs`, and expose them through one admin-only download action on run detail.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Source spec:** `docs/superpowers/specs/2026-03-31-cv-generation-debug-snapshots-design.md`

**Affected feature contracts:**

- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`

**Supporting docs to update during implementation:**

- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/history.md`

---

## Task 1: Extend Run Persistence for Debug Snapshots

**Files:**

- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `assets/bigquery/pipeline_runs.sql`
- Add: `scripts/migrations/005_add_cv_generation_debug_json_to_pipeline_runs.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [ ] **Step 1.1: Add run model field**
  - Add nullable `cv_generation_debug_json` to the `PipelineRun` model
  - Keep it explicitly separate from `results_export_json`

- [ ] **Step 1.2: Add BigQuery schema support**
  - Add nullable `cv_generation_debug_json STRING` to `pipeline_runs`
  - Add a migration script for existing environments

- [ ] **Step 1.3: Add persistence helpers**
  - Add a dedicated `update_run_cv_generation_debug(...)` helper in `bq_store.py`
  - Extend `_row_to_run(...)` so run reads map the new field

- [ ] **Step 1.4: Add failing storage tests**
  - row-to-run mapping includes `cv_generation_debug_json`
  - update helper writes only the debug snapshot field
  - existing results-export logic remains unaffected

- [ ] **Step 1.5: Confirm tests pass**

---

## Task 2: Define and Capture the Live Debug Record Contract

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 2.1: Add debug-record builders**
  - Add small helpers in `pipeline.py` to build:
    - compact `evidence_used`
    - `repair_attempt`
    - error payloads
  - Keep the record contract aligned to the spec’s required keys and nullability

- [ ] **Step 2.2: Capture live stage-local artifacts only**
  - Capture fields from the live Layer 4 path at the moment they exist
  - Do not reconstruct `structured_cv_initial`, `validation_initial`, or final artifacts later from persisted outputs

- [ ] **Step 2.3: Record success-path debug state**
  - For successful jobs, capture:
    - `job_url`
    - `job_title`
    - `status=accepted`
    - `fit_classification`
    - `evidence_used`
    - `gap_summary`
    - `structured_cv_initial`
    - `validation_initial`
    - `repair_attempt`
    - `structured_cv_final`
    - `markdown_final`
    - `error=null`

- [ ] **Step 2.4: Record failure-path debug state**
  - For failed jobs, capture the last known stage-local artifact without recomputation
  - Support at least:
    - `generation_failed`
    - `validation_failed`
    - `persistence_failed`
  - Preserve `error.stage` and `error.message`

- [ ] **Step 2.5: Add failing pipeline tests**
  - accepted record contains all required keys
  - validation-failed record preserves initial structured/validation state and no final accepted artifact
  - persistence-failed record preserves final in-memory artifact and error payload
  - no-recomputation behavior is enforced by the runtime capture path

- [ ] **Step 2.6: Confirm tests pass**

---

## Task 3: Add Top-Level Snapshot Assembly and Boundedness Rules

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

- [ ] **Step 3.1: Assemble run-scoped snapshot payload**
  - Build a top-level payload with:
    - `run_id`
    - `status`
    - `debug_schema_version`
    - `created_at`
    - `ranked_jobs_total`
    - `debug_records_captured`
    - `snapshot_complete`
    - `debug_records`

- [ ] **Step 3.2: Make partial snapshot semantics explicit**
  - Ensure top-level counts distinguish:
    - jobs intended for debug capture
    - records actually captured
  - Support partial snapshots when the run path captured only some ranked-job records

- [ ] **Step 3.3: Add boundedness and truncation policy**
  - Implement bounded truncation in snapshot assembly
  - Preserve:
    - top-level run metadata
    - identifiers
    - statuses
    - compact evidence references
    - error stage/message
  - Trim low-priority large fields first, especially:
    - `markdown_final`
    - oversized nested text fields

- [ ] **Step 3.4: Keep persistence best-effort**
  - If debug snapshot assembly or persistence fails, do not fail the run
  - Warn and continue, matching current results-export resilience

- [ ] **Step 3.5: Add failing worker/pipeline tests**
  - top-level payload includes completeness fields
  - truncation preserves required identifiers/status/error fields
  - persistence failure for debug snapshot does not downgrade successful runs

- [ ] **Step 3.6: Confirm tests pass**

---

## Task 4: Persist and Download the Debug Snapshot

**Files:**

- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 4.1: Persist run-scoped debug snapshot**
  - After a successful pipeline run, persist `cv_generation_debug_json` using the dedicated helper
  - Keep the final `results_export_json` persistence path unchanged in purpose

- [ ] **Step 4.2: Add admin-only download endpoint**
  - Add `GET /admin/runs/{run_id}/cv-debug.json`
  - Return `application/json`
  - Use `Content-Disposition` attachment headers with a clear filename
  - Pretty-print the JSON for readability on download

- [ ] **Step 4.3: Add minimal run-detail action**
  - Add one download action on run detail when a debug snapshot exists
  - Keep UI scope download-first only; do not add a broad new inspection panel in v1

- [ ] **Step 4.4: Add failing app/template tests**
  - button appears only when debug snapshot exists
  - endpoint returns 404 or equivalent when snapshot is absent
  - endpoint returns pretty JSON with correct filename when snapshot exists

- [ ] **Step 4.5: Confirm tests pass**

---

## Task 5: Add Focused Regression Coverage for Real CV-Debug Cases

**Files:**

- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: fixture/test data only if needed

- [ ] **Step 5.1: Encode the motivating failure modes**
  - Add deterministic regression fixtures for cases where:
    - initial structured CV exists, validation fails
    - repair occurs before acceptance
    - persistence fails after final in-memory artifact exists

- [ ] **Step 5.2: Assert artifact completeness**
  - Verify required keys are always present with correct nullability
  - Verify failure-path records preserve last known stage-local data
  - Verify accepted records preserve both structured and markdown final artifacts

- [ ] **Step 5.3: Assert non-regression**
  - final run-results export remains separate
  - event timeline stays concise and is not overloaded with giant debug payloads
  - normal successful run status remains unchanged when debug snapshot persistence fails

- [ ] **Step 5.4: Confirm tests pass**

---

## Task 6: Update Feature Docs

**Files:**

- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/inspection_debugging/history.md`
- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/trigger_run_management/history.md`

- [ ] **Step 6.1: Update inspection/debugging feature contract**
  - Add run-scoped CV-generation debug snapshot capability
  - Link the new spec and implementation plan

- [ ] **Step 6.2: Update CV-system feature contract**
  - Record that live CV-generation artifacts can now be captured into a run-scoped debug snapshot
  - Keep this framed as a debugging surface, not the canonical storage contract

- [ ] **Step 6.3: Update trigger/run-management feature contract**
  - Record the new admin debug-download action on run detail
  - Keep it separate from the final results export action

- [ ] **Step 6.4: Record feature history**
  - Add history entries summarizing the new run-scoped debug snapshot and download action

---

## Execution Order

1. Complete Task 1 first so the persistence contract exists before any runtime capture code depends on it.
2. Complete Task 2 before worker persistence so the per-record contract is stable and testable.
3. Complete Task 3 once the record contract exists, so top-level bounded snapshot assembly is locked down.
4. Complete Task 4 after persistence semantics are stable.
5. Complete Task 5 before closing the work so the motivating CV-debug scenarios stay covered.
6. Complete Task 6 last so the feature docs reflect the implemented behavior.

---

## Verification Checklist

- [ ] `pipeline_runs` supports `cv_generation_debug_json`
- [ ] Per-job debug records are captured from the live Layer 4 path, not reconstructed later
- [ ] Top-level snapshot includes completeness fields for partial capture interpretation
- [ ] Truncation preserves identifiers, statuses, and error stage/message fields
- [ ] Debug snapshot persistence failure does not fail otherwise successful runs
- [ ] One admin-only download action exists for the snapshot
- [ ] Existing `results_export_json` behavior remains separate and intact

---

## Risks and Notes

### Snapshot Size Risk

The artifact contains structured CV and markdown content. Keep truncation logic explicit and deterministic so debug usefulness survives even when large text must be trimmed.

### Contract Drift Risk

This snapshot is a debugging convenience surface, not the system of record for all stage facts. Do not let future work silently depend on it as the canonical analytics model.

### UI Scope Risk

Do not expand this rollout into a full in-page debug browser. Keep v1 download-first so storage and contract semantics stabilize before broader UI work.
