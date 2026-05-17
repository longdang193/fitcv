---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: run-detail-decision-first-layout-synonym-mode-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-17-20-25-run-detail-decision-first-layout-synonym-mode-spec.md
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_app.py
  - docs/usage.md
related_features:
  - run_lifecycle_controls
  - trigger_run_management
related_stages:
  - cv_generation
---

## Goal

Implement the run-detail decision-first layout contract with fixed section ordering, synonym-review conditional depth, artifacts ownership consolidation, and end-of-page advanced diagnostics while preserving route integrity and audit invariants.

## Key Deliverables

### Deliverable 1: Fixed run-detail layout and section-order implementation

Run detail renders in canonical order (`Header -> Overview -> Synonym Review -> Pipeline Results -> Event Timeline -> Artifacts -> Advanced & Diagnostics`) with static placement and no duplicate summary blocks.

### Deliverable 2: Synonym-review workflow state implementation

Synonym Review supports `hidden|summary|decision_active` rendering, exposes `AI-Assisted Review` and `Manual Review` only in `decision_active`, and preserves working workspace route behavior.

### Deliverable 3: Surface deduplication and artifacts ownership cutover

`Outputs` and `Run exports workspace` overlaps are removed from run detail, with export/download ownership moved to Artifacts-only surface.

### Deliverable 4: Advanced diagnostics simplification implementation

Advanced diagnostics moves to page end, collapsed by default, and removes dead/non-functional quick action buttons while preserving required read-only technical evidence.

### Deliverable 5: Non-regression verification and docs alignment

Tests and docs prove section order, state visibility, route integrity, no dead CTAs, and no reintroduction of duplicated surfaces.

## Task/Wave Breakdown

### Task 1: Implement fixed run-detail section shell and deduplicate overview

**Purpose:**
- enforce canonical section order and remove duplicated overview blocks

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- parent spec approved for implementation

**Steps:**
- [ ] Step 1: reorder run-detail sections to canonical static order
- [ ] Step 2: remove duplicate decision/overview block(s)
- [ ] Step 3: keep one authoritative `Run Overview` with core fields only

**Verification:**
- [ ] render assertion proves single overview block
- [ ] ordered-section assertion passes for canonical order markers

**Exit Criteria:**
- no duplicated overview summary and layout order stable across run states

### Task 2: Implement synonym-review state model and mode controls

**Purpose:**
- add predictable synonym workflow behavior without section movement

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: define backend-facing synonym section state (`hidden|summary|decision_active`)
- [ ] Step 2: render compact summary mode in normal states
- [ ] Step 3: render `Review Mode` with `AI-Assisted Review` and `Manual Review` in `decision_active`
- [ ] Step 4: ensure `Open Synonym Review Workspace` uses canonical route `/admin/runs/{run_id}/synonym-review`
- [ ] Step 5: add deterministic fallback message for unavailable workspace state

**Verification:**
- [ ] route render tests prove mode controls appear only in decision-active state
- [ ] canonical workspace route test passes

**Exit Criteria:**
- synonym section behavior is state-driven, stable, and route-safe

### Task 3: Consolidate artifacts ownership and remove overlaps

**Purpose:**
- eliminate output/export duplication and reduce operator ambiguity

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: remove `Outputs` and `Run exports workspace` from run-detail flow
- [ ] Step 2: keep Artifacts section as sole owner for download/export CTA and status
- [ ] Step 3: keep compatibility messaging for moved surfaces where needed

**Verification:**
- [ ] regression tests assert removed sections are absent
- [ ] artifacts section still exposes required ownership signals/CTA

**Exit Criteria:**
- no output/export overlap remains in run detail

### Task 4: Move/simplify advanced diagnostics

**Purpose:**
- preserve debug access while minimizing decision-path clutter

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 and Task 3 complete

**Steps:**
- [ ] Step 1: move advanced diagnostics section after Artifacts
- [ ] Step 2: default diagnostics section to collapsed state
- [ ] Step 3: remove quick buttons for `Synonym Fingerprints`, `Event Delivery`, `Telemetry`, `Trace Links`, `Replay Summary`, `Runtime Alignment`
- [ ] Step 4: preserve required read-only diagnostics rows and deep audit evidence

**Verification:**
- [ ] template checks assert diagnostics appears last and collapsed default
- [ ] tests assert removed buttons do not render

**Exit Criteria:**
- advanced diagnostics is accessible but does not disrupt main task flow

### Task 5: Invariance/equivalence test expansion and docs alignment

**Purpose:**
- lock behavior with non-regression coverage and operator docs updates

**Files:**
- Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `docs/usage.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: add section-order and duplication-absence regression tests
- [ ] Step 2: add synonym-state visibility tests for mode controls
- [ ] Step 3: add CTA validity tests for synonym workspace route and fallback behavior
- [ ] Step 4: update usage docs to reflect new layout order and ownership boundaries

**Verification:**
- [ ] all targeted tests pass with new layout/state expectations
- [ ] docs describe final operator flow without stale section references

**Exit Criteria:**
- implementation is guarded against drift and docs match shipped UX

## Verification

- `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -k run_detail -q`
- `python scripts/hooks/run_validator.py --fast`

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
