---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: pipeline-results-bookmark-stars-and-cross-run-bookmarks-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-20-16-07-pipeline-results-bookmark-feature-spec.md
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
related_features: []
related_stages: []
---

## Goal

Implement bookmark stars in `Pipeline Results` generated-output rows and deliver dedicated bookmarks page that persists saved jobs across runs without regressing existing run-detail actions.

## Key Deliverables

### Deliverable 1: Run-detail bookmark star interaction

`Pipeline Results` rows render bookmark star controls with deterministic saved/unsaved state and row-local toggle behavior while preserving existing `Download Markdown` and job-link actions.

### Deliverable 2: Persistent bookmark store contract

Bookmark persistence supports idempotent save/remove by stable identity key, stores required snapshot fields, and survives restart/run boundaries.

### Deliverable 3: Dedicated bookmarks page and navigation

New page renders all saved jobs across runs with default newest-first ordering, remove action, and stable empty-state behavior.

### Deliverable 4: Regression and proof coverage

Automated tests cover row rendering/toggle endpoints, persistence semantics, and bookmarks page behavior with no regressions to existing run-detail output availability checks.

## Task/Wave Breakdown

### Task 1: Define bookmark persistence contract in settings store

**Purpose:**
- establish single persistence API used by run-detail action handlers and bookmarks page reader

**Files:**
- Inspect: `src/fitcv_cp/settings_store.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Verify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`

**Preconditions:**
- approved spec at `docs/superpowers/specs/2026-05-20-16-07-pipeline-results-bookmark-feature-spec.md`
- stable bookmark identity rule selected (`job_id` preferred + deterministic fallback)

**Steps:**
- [x] Step 1: add bookmark record schema/API (`upsert`, `delete`, `list`, `exists`) with idempotent semantics
- [x] Step 2: persist required snapshot fields (`title`, `company`, `location`, `url`, `run_id/source`, `saved_at`)
- [x] Step 3: add/update sqlite-backed tests for duplicate save, remove, and restart persistence behavior

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_store_sqlite.py -k bookmark`

**Exit Criteria:**
- persistence API is deterministic, idempotent, and fully test-covered for core CRUD behavior

### Task 2: Add run-detail bookmark star actions in Pipeline Results

**Purpose:**
- expose bookmark save/remove where user evaluates generated outputs

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete
- run-detail generated-output rows provide sufficient identity/context fields for toggle actions

**Steps:**
- [x] Step 1: add route handlers/endpoints for bookmark save/remove from run-detail rows
- [x] Step 2: render star control inside Pipeline Results row action cluster with saved/unsaved visual state
- [x] Step 3: keep legacy actions intact and add test assertions for star presence + unchanged download/link behavior

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Exit Criteria:**
- each generated-output row supports bookmark toggle with no regression to existing actions

### Task 3: Build dedicated bookmarks page and nav entry

**Purpose:**
- provide single cross-run surface listing all saved jobs

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/` (new bookmarks template + nav link updates)
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- bookmarks list API available from persistence layer

**Steps:**
- [x] Step 1: add bookmarks-page route backed by persistent bookmark list query (default sort `saved_at desc`)
- [x] Step 2: implement page rendering for list rows, remove action, source link, and empty state
- [x] Step 3: add navigation affordance to reach bookmarks page from existing admin/run surfaces

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k bookmark`

**Exit Criteria:**
- dedicated bookmarks page available, stable, and powered only by persisted bookmark records

### Task 4: End-to-end regression sweep and closeout evidence

**Purpose:**
- prove integrated behavior and ensure bounded change does not leak regressions

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Inspect: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Inspect: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: run targeted bookmark/store/run-detail/page test subset
- [x] Step 2: run broader FitCV control-plane regression subset touching run detail and settings store
- [x] Step 3: capture final validation results and residual risk notes for execution handoff/closeout

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_store_sqlite.py -k bookmark`
- [x] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "bookmark or pipeline results"`

**Exit Criteria:**
- all required tests pass and evidence is recorded for implementation completion gate

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest tests/test_fitcv_cp/test_settings_store_sqlite.py -k bookmark`
- `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
- `pytest tests/test_fitcv_cp/test_app.py -k "bookmark or pipeline results"`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
