---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: hitl-review-queue-identity-alignment
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-review-actions
parent_spec: docs/superpowers/specs/2026-05-20-09-21-hitl-review-queue-identity-alignment-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/review_queue.html
  - tests/
related_features:
  - admin_control_plane_core
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Implement identity-aligned HITL review queue behavior so all `review_required` CV rows are visible, count symmetry holds between worker pause state and UI queue state, and operator actions/closure operate on unified row identity.

## Key Deliverables

### Deliverable 1: Unified review identity and pending semantics in runtime code

`review_item_id` becomes canonical row identity across worker finalize logic, queue assembly, and action resolution; pending definition is shared and deterministic for both event count and queue count.

### Deliverable 2: Review UI and action flows handle missing `job_url` without row loss

Review queue renders rows even when URL is missing, supports identity-based action selection, and clearly marks URL-limited actions while preserving current operator workflow safety.

### Deliverable 3: Regression-proof verification coverage

Targeted tests prove:
- missing-URL rows remain visible and counted
- pause/queue pending parity
- identity-based action resolution
- legacy payload compatibility
- no premature closure when pending identities remain

## Task/Wave Breakdown

### Task 1: Establish canonical review identity + normalization helpers

**Purpose:**
- introduce shared identity contract and migration-safe payload normalization

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/`

**Preconditions:**
- parent spec approved for implementation
- current behavior confirmed: worker counts rows queue can drop

**Steps:**
- [ ] Step 1: add deterministic `review_item_id` builder/normalizer (stable tuple, collision-resistant hash).
- [ ] Step 2: ensure debug payload write path stamps `review_item_id` on each review-required record.
- [ ] Step 3: ensure read path derives missing IDs for legacy payloads before queue/action logic consumes rows.
- [ ] Step 4: define/centralize pending predicate helper keyed by `review_item_id`.

**Verification:**
- [ ] unit tests for deterministic ID generation and legacy-derivation fallback.
- [ ] unit tests for pending predicate behavior across terminal/non-terminal action states.

**Exit Criteria:**
- all review-required rows are identity-addressable in-memory even when `job_url` is empty.

### Task 2: Align worker finalize counter with queue semantics

**Purpose:**
- eliminate pause-count vs queue-count drift

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: refactor finalize-status review-required counting to rely on canonical review identity + pending semantics.
- [ ] Step 2: preserve existing reason-code aggregation while ensuring `remaining` derives from same row universe as queue.
- [ ] Step 3: add explicit diagnostic field for rows missing `job_url` (observability only; not exclusion condition).

**Verification:**
- [ ] integration test: synthetic run with mixed URL/missing-URL review rows returns pause `remaining == queue pending_count`.
- [ ] event payload assertions for `cv_review_required` include expected totals and parity.

**Exit Criteria:**
- no reproducible state where run pauses for N pending review rows while queue shows fewer due to selector mismatch.

### Task 3: Refactor review queue/action endpoints to identity-first selection

**Purpose:**
- make operator actions robust when `job_url` unavailable

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Modify: `src/fitcv_cp/templates/review_queue.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: update queue builder to never drop `review_required` rows solely for missing URL.
- [ ] Step 2: switch latest-action mapping and row lookup to `review_item_id` primary key, with legacy `job_url` fallback.
- [ ] Step 3: update single/batch review endpoints to accept and process `review_item_id`.
- [ ] Step 4: update templates/forms to post selected `review_item_id`; keep URL as display/secondary metadata.
- [ ] Step 5: gate URL-dependent actions (if any) with explicit UI state instead of row suppression.

**Verification:**
- [ ] endpoint tests for identity-only action on row without URL.
- [ ] batch-action tests for mixed selected rows, including already-terminal skip behavior.
- [ ] rendering test/assertion that pending rows without URL still appear.

**Exit Criteria:**
- operator can see and resolve every pending review row represented in debug payload.

### Task 4: Preserve closure correctness and backward compatibility

**Purpose:**
- prevent regression in run completion and historical run readability

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/`

**Preconditions:**
- Tasks 2 and 3 complete

**Steps:**
- [ ] Step 1: ensure closure gate (`awaiting_review` -> `succeeded`) checks terminal status by identity-set completeness.
- [ ] Step 2: ensure legacy runs with no persisted `review_item_id` remain actionable via derived IDs.
- [ ] Step 3: verify no accepted-CV acknowledgment logic still triggers correctly when applicable.

**Verification:**
- [ ] closure test with one pending identity blocks completion.
- [ ] closure test with all terminal identities allows completion path.
- [ ] legacy payload fixture test passes queue + action + closure flow.

**Exit Criteria:**
- closure state machine behavior unchanged except bug-class removal.

### Task 5: Final verification and evidence capture

**Purpose:**
- prove patch meets spec acceptance criteria and is safe to execute/merge

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-20-09-21-hitl-review-queue-identity-alignment-spec.md`
- Verify: `tests/`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: run targeted tests for HITL queue/count/action/closure paths.
- [ ] Step 2: run broader relevant test slice for `fitcv_cp` control-plane review flows.
- [ ] Step 3: collect evidence mapping each acceptance criterion to concrete test/proof output.

**Verification:**
- [ ] targeted test command succeeds.
- [ ] broader regression command succeeds (or explicit justified gaps documented).
- [ ] acceptance-criteria checklist marked complete with evidence references.

**Exit Criteria:**
- implementation ready for execution closeout with no open blocker on this bug class.

## Verification

- `pytest -q tests -k "hitl or cv_review or review_queue or awaiting_review"`
- `pytest -q tests/fitcv_cp`
- manual sanity check on run detail/review queue page for synthetic missing-URL fixture:
  - pending badge count
  - rendered row count
  - action controls state
  - closure gating behavior

## Completion Criteria

1. all Key Deliverables are satisfied and mapped to evidence
2. all plan tasks are terminal with verification outcomes recorded
3. implementation behavior satisfies parent spec acceptance criteria without introducing closure regressions
