---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: pipeline-results-and-bookmarks-company-display-format-alignment
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-20-16-07-pipeline-results-bookmark-feature-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/bookmarks.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
related_features: []
related_stages: []
---

## Goal

Implement a single SSOT job-label display contract so both Pipeline Results and Bookmarked Jobs render `Job Title (Company, Location)` with deterministic fallbacks and no template-level string drift.

## Key Deliverables

### Deliverable 1: Shared display-label contract in app layer

One canonical helper in `src/fitcv_cp/app.py` produces display strings for title/company/location with strict fallback behavior. Both run-detail and bookmarks paths consume it.

### Deliverable 2: Symmetric UI rendering across Pipeline Results and Bookmarks

Pipeline Results and Bookmarked Jobs use same primary-line format and no ad-hoc concatenation in templates. Missing-company and missing-location states remain readable and separator-safe.

### Deliverable 3: Regression coverage for formatting and fallback semantics

Tests verify the exact format and fallback behavior for both pages, including missing location and missing company/title cases.

## Task/Wave Breakdown

### Task 1: Define SSOT formatter and mapping surfaces

**Purpose:**
- centralize display-format behavior in one helper path

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- existing bookmark routes and run-detail mapping logic available
- agreed canonical format: `Job Title (Company, Location)` or `Job Title (Company)` when location missing

**Steps:**
- [ ] Step 1: add helper for canonical primary-line label with fallback matrix
- [ ] Step 2: wire run-detail `cv_versions` mapping through helper
- [ ] Step 3: wire bookmarks view-model mapping through same helper

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "bookmark and format"`

**Exit Criteria:**
- app-layer helper is single source for primary-line text in both surfaces

### Task 2: Update templates for symmetry-only rendering

**Purpose:**
- keep templates presentation-focused and free of logic duplication

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: render helper-produced label in Pipeline Results row link text
- [ ] Step 2: render helper-produced label in Bookmarks primary link text
- [ ] Step 3: ensure no inline `title/company/location` concatenation remains in templates

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Exit Criteria:**
- templates use upstream prepared values only and preserve action-button layout

### Task 3: Fallback and edge-case proof

**Purpose:**
- lock behavior for missing fields and avoid UX regressions

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-2 complete

**Steps:**
- [ ] Step 1: add/adjust tests for full format (`title+company+location`)
- [ ] Step 2: add tests for missing location (`title+company`)
- [ ] Step 3: add tests for missing company/title fallback behavior

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "bookmark and (company or location or format)"`

**Exit Criteria:**
- all fallback contracts are explicit and test-proven

### Task 4: Final bounded verification and handoff

**Purpose:**
- confirm implementation is stable and bounded to intended surfaces

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/bookmarks.html`
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Inspect: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: run targeted pytest subset for bookmark/display surfaces
- [ ] Step 2: run fast contract validator
- [ ] Step 3: capture residual risks and handoff notes

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k bookmark`
- [ ] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- requested display contract is validated and ready for execution handoff

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k bookmark`
- `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
