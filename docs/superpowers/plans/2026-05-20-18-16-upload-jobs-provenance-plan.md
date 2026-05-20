---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: upload-jobs-provenance-labeling
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

## Goal

Make upload-mode jobs path display include merged-file provenance wording, so users see canonical merged path plus original uploaded filenames in one readable, invariant message.

## Key Deliverables

### Provenance contract for upload-mode jobs input

Run record includes enough metadata to render:
`data/uploads/<id>_merged_jobs.json (merged from: foo.json, bar.json, ...)`
without changing execution semantics of `jobs_path`.

### Symmetric UI rendering for jobs path

Run list/detail surfaces render same wording rule for upload mode, and preserve existing plain path display for non-upload modes.

### Regression coverage

Tests validate new wording, fallback behavior, and unchanged behavior for path/paste modes.

## Task/Wave Breakdown

### Task 1: Add upload provenance data contract

**Purpose:**
- Capture uploaded source filenames at trigger time in structured run metadata while keeping `run.jobs_path` canonical merged file path.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Upload merge path generation already stable in trigger handler.
- Backward compatibility needed for existing run rows.

**Steps:**
- [x] Step 1: Define/extend run metadata field for jobs provenance (source filenames + mode marker).
- [x] Step 2: Populate provenance in upload-mode trigger path where `effective_files` are known.
- [x] Step 3: Keep non-upload modes null/empty to avoid semantic drift.
- [x] Step 4: Persist/read field through store adapters with backward-compatible fallback.

**Verification:**
- [x] Unit test: upload trigger run row contains merged path and provenance filenames.
- [x] Unit test: path/paste triggers remain unchanged.

**Exit Criteria:**
- Metadata available at render layer for deterministic wording generation.

### Task 2: Render merged-from wording in run surfaces

**Purpose:**
- Show concise user-facing label:
`<merged_path> (merged from: <file1>, <file2>, ...)`
for upload-mode runs only.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.
- Existing truncation/tooltip behavior for long jobs path should remain usable.

**Steps:**
- [x] Step 1: Add formatter/helper that composes wording from merged path + provenance list.
- [x] Step 2: Use formatter in run detail and runs list view models.
- [x] Step 3: Ensure fallback to raw `jobs_path` when provenance unavailable.
- [x] Step 4: Keep output stable and symmetric across both pages.

**Verification:**
- [x] Template test: upload-mode rendered string matches exact wording pattern.
- [x] Template test: non-upload mode still shows raw path only.

**Exit Criteria:**
- Both pages show same invariant wording rule with no regressions.

### Task 3: Final validation and rollout safety

**Purpose:**
- Confirm functional correctness, formatting consistency, and no schema/runtime break.

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/bq_store.py`

**Preconditions:**
- Task 1 and Task 2 complete.

**Steps:**
- [x] Step 1: Run focused tests for trigger + run detail/list rendering.
- [x] Step 2: Run broader fitcv_cp test subset if needed for storage/model changes.
- [x] Step 3: Manual smoke-check one upload run in UI for final wording.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "upload or jobs_path or run_detail or runs_list"`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Tests pass, wording appears exactly as requested, no unrelated behavior drift found.

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k "upload or jobs_path or run_detail or runs_list"`
- `python scripts/hooks/run_validator.py --fast`
- Manual UI check on one upload run row and one run detail page.

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>


