---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: synonym-promote-review-page-and-queue-symmetry
parent_thread: workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow
parent_spec: docs/superpowers/specs/2026-05-20-11-33-synonym-review-queue-symmetry-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/templates/_cv_review_queue.html
  - tests/
---

## Goal

Implement symmetric selection behavior between Agentic Review Queue and Synonym Review, plus dedicated `Review Promote to Global` workbench page that explicitly separates promotable, already-global, and blocked rows.

## Key Deliverables

### Deliverable 1

Synonym Review supports explicit row selection contract (checkboxes, select-all/clear-all, selected count, batch apply to selected ids) across actionable states including deferred rows.

### Deliverable 2

Dedicated promote review route/page exists and renders grouped sections:
- Ready to Promote
- Already Global (No Change)
- Blocked/Conflict
with deterministic status handling and explicit commit scope.

### Deliverable 3

Server-side batch and promote handlers enforce explicit selected-id scope, valid transition rules, and clear operator-facing errors for empty/invalid selections.

### Deliverable 4

Targeted tests and regression checks verify queue symmetry, state transitions (`deferred -> pending` reopen path), and promote grouping/commit behavior.

## Task/Wave Breakdown

### Task 1: Introduce synonym selectable-row interaction model

**Purpose:**
- Align synonym queue UX contract with Agentic queue primitives.

**Files:**
- Inspect: `src/fitcv_cp/templates/_cv_review_queue.html`
- Inspect: `src/fitcv_cp/templates/synonym_review.html`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Verify: `src/fitcv_cp/templates/synonym_review.html`

**Preconditions:**
- Parent spec remains approved/proposed baseline.
- Existing synonym management mode gates unchanged.

**Steps:**
- [x] Add row-level checkbox controls for actionable synonym rows (`pending`, `deferred`, and any explicitly reversible states).
- [x] Add top controls: Select All, Clear All, Selected count, and helper text aligned with Agentic queue phrasing.
- [x] Keep row-level quick action controls where valid, without hiding rows from batch selection.
- [x] Update client-side JS to maintain selected counts and scoped actions.

**Verification:**
- [x] UI inspection confirms checkbox model present and usable on deferred rows.
- [x] No regression in existing actor sync and AI prefill UX.

**Exit Criteria:**
- Synonym queue uses explicit selected-row interaction semantics equivalent to Agentic queue.

### Task 2: Refactor synonym batch action contract to explicit selected ids

**Purpose:**
- Enforce deterministic, explicit server-side selection scope for synonym decisions.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/app.py`

**Preconditions:**
- Task 1 form shape finalized (`proposal_id[]` + batch action).

**Steps:**
- [x] Update `admin_run_synonym_proposals_batch_action` parsing to require explicit `proposal_id[]` selected set.
- [x] Add explicit `batch_action` contract supporting `approve`, `defer`, `reject`, `reopen_pending`.
- [x] Enforce allowed transitions in `_apply_synonym_proposal_action_in_run` path and return clear 422 details for invalid transitions or empty selection.
- [x] Preserve event/audit history semantics for each applied row.

**Verification:**
- [x] Endpoint-level tests verify only selected rows mutate.
- [x] Empty selection and invalid transition cases return deterministic errors.

**Exit Criteria:**
- Batch action logic cannot silently apply to non-selected rows.

### Task 3: Add dedicated Review Promote to Global page and route

**Purpose:**
- Provide dedicated promote workbench with explicit grouped review states and commit scope.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_promote_preview.html` (or split into new dedicated template if preferred)
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates/synonym_promote_preview.html`

**Preconditions:**
- `_build_promote_global_preview` remains canonical diff calculator.

**Steps:**
- [x] Add route `GET /admin/runs/{run_id}/synonym-proposals/promote-review` (or equivalent) as dedicated promote workbench entrypoint.
- [x] Extend preview view-model to provide grouped buckets (`ready`, `already_global`, `blocked`) from existing `diff_type/reason/status` semantics.
- [x] Render grouped sections with counts and selection enabled only for promotable rows.
- [x] Ensure commit endpoint consumes explicit selected ids from workbench and returns deterministic post-commit summary.
- [x] Link synonym review page button to dedicated promote workbench route.

**Verification:**
- [x] Manual/browser verification confirms grouped sections and selection constraints.
- [x] Promote commit rejects empty selected set and conflict-selected set as specified.

**Exit Criteria:**
- Dedicated promote workbench exists and removes no-op ambiguity.

### Task 4: Add and run targeted regression tests

**Purpose:**
- Lock behavior for symmetry and promote-workbench flows.

**Files:**
- Inspect: `tests/`
- Modify: `tests/` (relevant control-plane route/template/handler tests)
- Verify: `tests/`

**Preconditions:**
- Tasks 1-3 implemented.

**Steps:**
- [x] Add tests for synonym selection model rendering and actionable state coverage.
- [x] Add tests for batch action selected-scope enforcement and `reopen_pending` transition.
- [x] Add tests for promote workbench grouping membership and counts.
- [x] Add tests for promote commit deterministic failures/success summary.

**Verification:**
- [x] Run targeted pytest subset for modified handlers/templates.
- [x] Run broader regression slice if shared helpers changed.

**Exit Criteria:**
- Tests prove invariants from parent spec and prevent regressions.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest -q tests -k "synonym and (promote or review or batch)"`
- `pytest -q tests -k "cv_review_batch_action or synonym_proposals_batch_action"`
- Manual UI validation on Synonym Review and Promote Workbench for run with mixed approved/deferred/conflict rows.

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. parent spec invariants are preserved and verification evidence is attached to plan execution closeout



