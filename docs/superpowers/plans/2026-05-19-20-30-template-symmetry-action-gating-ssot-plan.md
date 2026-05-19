---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: template-symmetry-action-gating-ssot-plan
parent_workstream: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-19-20-28-template-symmetry-action-gating-ssot-spec.md
targets:
  - src/fitcv_cp/templates/_cv_review_queue.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - settings_system
  - inspection_debugging
related_stages:
  - cv_generation
  - enrich
---

## Goal

Implement template-level symmetry/SSOT fixes so rendered actionability always matches state truth, and equivalent decision controls share one visual/state contract across run detail and synonym workspace.

## Key Deliverables

### Deliverable 1: Resolved review rows are truly non-actionable

`_cv_review_queue.html` renders per-row decision controls only for pending items, while resolved items show locked metadata-only presentation.

### Deliverable 2: Cross-page decision toggle symmetry

`AI-Assisted Decide + Promote` and `Manual Decide + Promote` controls use one contract (`decision-toggle` class + `data-active` state semantics) in both run detail and synonym workspace.

### Deliverable 3: Manual-entry control de-duplication on run detail

Run detail exposes a single manual-entry path to synonym workspace; duplicate CTA drift is removed.

### Deliverable 4: Regression-proof tests

`tests/test_fitcv_cp/test_app.py` covers action-gating truthfulness and cross-page decision-control parity so drift re-fails quickly.

## Task/Wave Breakdown

### Task 1: Build source-first violation matrix and final patch map

**Purpose:**
- lock exact before/after template contracts and avoid accidental UI regressions

**Files:**
- Inspect: `src/fitcv_cp/templates/_cv_review_queue.html`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/synonym_review.html`
- Inspect: `src/fitcv_cp/templates/base.html`
- Inspect: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec approved
- GitNexus freshness is stale; use advisory-only and source-first truth

**Steps:**
- [ ] Step 1: map all pending/resolved state labels to rendered controls in review templates.
- [ ] Step 2: map all decision-mode controls to element types, classes, and active-state behavior across pages.
- [ ] Step 3: freeze canonical target contract table (state -> affordance, mode -> style/state).

**Verification:**
- [ ] source-backed violation matrix includes exact file and line anchors for each drift point.

**Exit Criteria:**
- implementation tasks can execute without unresolved UI contract ambiguity.

### Task 2: Enforce resolved-row action gating symmetry in review queue

**Purpose:**
- align rendered affordance with queue state truth (SSOT)

**Files:**
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: gate per-row action forms/buttons behind `item.pending`.
- [ ] Step 2: add resolved-row locked presentation (status note) and preserve non-action metadata.
- [ ] Step 3: ensure selection controls remain scoped to pending rows only.

**Verification:**
- [ ] resolved rows render no per-row decision forms/buttons.
- [ ] pending rows retain actionable controls.

**Exit Criteria:**
- no state/action mismatch remains in review queue rendering.

### Task 3: Normalize decision-toggle style/state contract across pages

**Purpose:**
- remove visual and behavior drift for equivalent decision controls

**Files:**
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: introduce scoped decision-toggle class contract (`decision-toggle`) with active/inactive/disabled states.
- [ ] Step 2: apply contract to run detail and synonym workspace decision controls.
- [ ] Step 3: update synonym workspace JS to set `data-active` deterministically for AI/manual mode transitions.

**Verification:**
- [ ] both pages render equivalent controls with same class + state attributes.
- [ ] active mode state is machine-observable (`data-active=true`).

**Exit Criteria:**
- cross-page decision controls are visually and behaviorally symmetric.

### Task 4: Remove manual-entry CTA duplication on run detail

**Purpose:**
- eliminate overlapping manual controls that cause workflow ambiguity

**Files:**
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: collapse duplicate manual CTAs into one canonical manual-entry control.
- [ ] Step 2: keep copy aligned with workflow intent and no hidden secondary path.
- [ ] Step 3: ensure link target and semantics remain unchanged.

**Verification:**
- [ ] run detail renders exactly one manual-entry synonym workspace control.

**Exit Criteria:**
- no duplicate manual-decision affordance remains.

### Task 5: Add regression tests and run final verification suite

**Purpose:**
- make symmetry/SSOT constraints executable and enforceable

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Verify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `src/fitcv_cp/templates/synonym_review.html`

**Preconditions:**
- Tasks 2-4 complete

**Steps:**
- [ ] Step 1: add render tests for resolved-row non-actionability and pending-row actionability.
- [ ] Step 2: add parity tests for decision-toggle class/state presence in run detail + workspace.
- [ ] Step 3: add test for single manual-entry CTA in run detail.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py -k "review_queue or synonym or decision_toggle or manual_entry"`

**Exit Criteria:**
- regression tests fail on any reintroduced symmetry/SSOT drift.

## Verification

- `pytest -q tests/test_fitcv_cp/test_app.py -k "review_queue or synonym or decision_toggle or manual_entry"`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
