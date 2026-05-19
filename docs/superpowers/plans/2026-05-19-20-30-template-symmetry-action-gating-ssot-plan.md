---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: template-symmetry-action-gating-ssot-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
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
- GitNexus freshness verified up-to-date (`npx gitnexus status` on 2026-05-19)

**Steps:**
- [x] Step 1: map all pending/resolved state labels to rendered controls in review templates.
- [x] Step 2: map all decision-mode controls to element types, classes, and active-state behavior across pages.
- [x] Step 3: freeze canonical target contract table (state -> affordance, mode -> style/state).

**Verification:**
- [x] source-backed violation matrix includes exact file and line anchors for each drift point.

**Exit Criteria:**
- implementation tasks can execute without unresolved UI contract ambiguity.

**Task 1 Evidence (2026-05-19):**

Violation matrix (source-first):

| Drift point | Evidence |
|---|---|
| Resolved rows still expose action controls in CV review queue | `src/fitcv_cp/templates/_cv_review_queue.html:52` marks resolved state, but row action forms still render unconditionally at `:72-88`; row select checkbox also always rendered at `:44`. |
| Decision-mode controls differ by element type and no explicit shared state contract on run detail | `src/fitcv_cp/templates/run_detail.html:190` AI control is `<button>` inside POST form; `:192` manual control is `<a>` link; both use `btn-secondary` only, no `decision-toggle` marker or `data-active`. |
| Run detail manual CTA is duplicated | `src/fitcv_cp/templates/run_detail.html:192` (`Manual Decide + Promote`) and `:195` (`Open Synonym Workspace`) both route to same workspace URL. |
| Workspace decision toggles lack active-state attributes and deterministic mode marker | `src/fitcv_cp/templates/synonym_review.html:33-34` two mode buttons have only `btn-secondary`; JS handlers at `:183-188` change recommendations/status text but never set `data-active` on controls. |
| Existing active-style selector too broad for explicit decision-toggle contract | `src/fitcv_cp/templates/base.html:300` applies active style to any `.btn-secondary[data-active="true"]`; no scoped decision-control class contract. |

Canonical contract table locked:

| Contract dimension | Canonical target |
|---|---|
| CV review row actionability | `item.pending == true`: show select checkbox + per-row action forms. `item.pending == false`: hide per-row action forms and selection checkbox; keep status, action metadata, preview. |
| Decision controls (run detail + synonym workspace) | Both AI/manual controls carry `decision-toggle` class and explicit `data-active` (`"true"` active, `"false"` inactive). |
| Decision control behavior | Mode transitions update both controls deterministically; machine-observable state required for tests. |
| Run detail manual entry path | Exactly one manual-entry CTA to `/admin/runs/{{ run.run_id }}/synonym-review`; no duplicate secondary CTA. |

### Task 2: Enforce resolved-row action gating symmetry in review queue

**Purpose:**
- align rendered affordance with queue state truth (SSOT)

**Files:**
- Modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: gate per-row action forms/buttons behind `item.pending`.
- [x] Step 2: add resolved-row locked presentation (status note) and preserve non-action metadata.
- [x] Step 3: ensure selection controls remain scoped to pending rows only.

**Verification:**
- [x] resolved rows render no per-row decision forms/buttons.
- [x] pending rows retain actionable controls.

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
- [x] Step 1: introduce scoped decision-toggle class contract (`decision-toggle`) with active/inactive/disabled states.
- [x] Step 2: apply contract to run detail and synonym workspace decision controls.
- [x] Step 3: update synonym workspace JS to set `data-active` deterministically for AI/manual mode transitions.

**Verification:**
- [x] both pages render equivalent controls with same class + state attributes.
- [x] active mode state is machine-observable (`data-active=true`).

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
- [x] Step 1: collapse duplicate manual CTAs into one canonical manual-entry control.
- [x] Step 2: keep copy aligned with workflow intent and no hidden secondary path.
- [x] Step 3: ensure link target and semantics remain unchanged.

**Verification:**
- [x] run detail renders exactly one manual-entry synonym workspace control.

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
- [x] Step 1: add render tests for resolved-row non-actionability and pending-row actionability.
- [x] Step 2: add parity tests for decision-toggle class/state presence in run detail + workspace.
- [x] Step 3: add test for single manual-entry CTA in run detail.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "resolved_rows_render_locked_non_actionable_state or synonym_decision_toggle_contract_is_symmetric_across_pages or single_manual_entry_synonym_workspace_cta"`
- [x] DROPPED (scope-approved): `pytest -q tests/test_fitcv_cp/test_app.py -k "review_queue or synonym or decision_toggle or manual_entry"` (pre-existing out-of-scope synonym baseline failures; user approved scoped verification for this lane on 2026-05-19; follow-up required in separate synonym baseline reconciliation thread)

Task 5 verification note (2026-05-19):
- targeted regression tests added in this task pass:
  - `test_admin_review_queue_resolved_rows_render_locked_non_actionable_state`
  - `test_synonym_decision_toggle_contract_is_symmetric_across_pages`
  - `test_run_detail_renders_single_manual_entry_synonym_workspace_cta`
- broad keyword bundle currently fails on pre-existing synonym-route/UI tests already red before this patch scope; keep open until separate synonym baseline reconciliation.
- decision record: user approved scoped verification acceptance for this lane on 2026-05-19; legacy synonym baseline failures remain follow-up work, not closure blocker for this patch scope.

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
