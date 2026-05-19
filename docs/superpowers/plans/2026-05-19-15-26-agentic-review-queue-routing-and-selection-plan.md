---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: agentic-review-queue-routing-and-selection-implementation
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
parent_spec: docs/superpowers/specs/2026-05-19-15-18-agentic-review-queue-routing-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/_cv_review_queue.html
  - src/fitcv_cp/templates/review_queue.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# 2026-05-19-15-26 Agentic Review Queue Routing + Select-All Implementation Plan

## Goal
Implement threshold-based review-queue routing (`pending_count` limit `5`) and add Select-All/Clear-All controls while preserving existing review action semantics and audit behavior.

## Key Deliverables

### Deliverable 1: Routing behavior at threshold boundary
Run detail renders inline queue for `pending_count <= 5`, and renders summary + dedicated-queue navigation when `pending_count > 5`.

### Deliverable 2: Shared queue rendering surface
Queue row markup and batch-action control language are extracted into one shared template partial to keep inline and dedicated surfaces behaviorally symmetric.

### Deliverable 3: Bulk selection controls
Queue UI exposes `Select All` and `Clear All` controls that toggle visible selectable rows only and keep batch-action scope explicit.

### Deliverable 4: Regression-proof coverage
Test suite covers threshold routing, control visibility, wording updates, and selected-row batch behavior.

## Task/Wave Breakdown

### Task 1: Establish routing contract in server context

**Purpose:**
- produce deterministic render flags and navigation data for inline-vs-dedicated queue presentation.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Spec approved: `docs/superpowers/specs/2026-05-19-15-18-agentic-review-queue-routing-spec.md`
- Existing HITL queue builders remain source of queue truth (`_build_hitl_review_queue`, `_build_hitl_closure_summary`).

**Steps:**
- [x] Add review-queue display threshold constant (`5`) in run-detail rendering path.
- [x] Derive and pass template flags (example: `show_inline_review_queue`, `show_review_queue_cta`, `review_queue_threshold`).
- [x] Add dedicated GET route for review queue page using same queue payload builder and run identity context.
- [x] Keep existing POST endpoints (`/cv-review-action`, `/cv-review-batch-action`) unchanged.

**Verification:**
- [x] Route tests confirm boundary behavior at `pending_count=5` and `pending_count=6`.
- [x] Existing review action tests remain green.

**Exit Criteria:**
- Routing state is deterministic and computed once from queue payload.

### Task 2: Extract shared queue partial and wire both surfaces

**Purpose:**
- remove duplicated queue logic risk by consolidating queue UI into one reusable partial.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Modify: `src/fitcv_cp/templates/review_queue.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 flags and dedicated route available.
- Existing queue fields unchanged in template context (`hitl_review_queue`, `hitl_closure_summary`, `run`).

**Steps:**
- [x] Extract current queue card body into `_cv_review_queue.html` with context parameters for title/shell mode.
- [x] Update run-detail template:
  - inline include when `pending_count <= 5`
  - summary + CTA when `pending_count > 5`
- [x] Create dedicated page template `review_queue.html` that includes same partial and links back to run detail.
- [x] Apply wording updates in shared partial:
  - `Apply One Action to Selected Jobs`
  - `Apply to Selected Jobs`
  - `Review One by One`

**Verification:**
- [x] Template response assertions show updated text in both surfaces.
- [x] Queue row actions remain present and mapped to existing endpoints.

**Exit Criteria:**
- Single queue partial drives both inline and dedicated review experiences.

### Task 3: Add Select-All/Clear-All interaction

**Purpose:**
- reduce operator selection friction for batch actions without expanding action scope semantics.

**Files:**
- Inspect: `src/fitcv_cp/templates/_cv_review_queue.html`
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Modify: `src/fitcv_cp/templates/run_detail.html` (if shared JS placement required)
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Shared partial exists with stable checkbox selectors for queue rows.

**Steps:**
- [x] Add visible controls near batch action bar:
  - `Select All`
  - `Clear All`
- [x] Implement client-side toggle logic scoped to visible/selectable row checkboxes tied to batch form.
- [x] Keep controls no-op on submission state and do not mutate non-review checkboxes.
- [x] Add helper microcopy clarifying scope (`visible jobs`).

**Verification:**
- [x] UI test coverage for control presence.
- [x] Behavior check confirms selected checkbox count transitions for all/none states.
- [x] Batch endpoint tests verify only selected job URLs processed.

**Exit Criteria:**
- Bulk selection works predictably and remains selection-scoped.

### Task 4: Expand regression coverage and closeout validation

**Purpose:**
- lock behavior with focused tests and ensure no lifecycle or queue-action regressions.

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Verify: `src/fitcv_cp/templates/review_queue.html`

**Preconditions:**
- Tasks 1-3 complete.

**Steps:**
- [x] Add tests for run-detail threshold switch (`5` inline, `6` dedicated CTA).
- [x] Add tests for dedicated queue page render and back-link integrity.
- [x] Add/adjust copy assertions for normalized wording.
- [x] Run targeted test subset for review queue behavior.
- [x] Run fast repo validator for planning/doc contract integrity.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "review_queue or cv_review"` passes.
- [x] `python scripts/hooks/run_validator.py --fast` passes.

**Exit Criteria:**
- Contract-level and regression-level proof artifacts are green.

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k "review_queue or cv_review"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
