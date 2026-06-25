---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: template-ssot-patch
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-06-25-15-10-template-ssot-patch-spec.md
targets:
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/bookmarks.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/_synonym_overlay_upload_form.html
  - src/fitcv_cp/templates/_synonym_decision_ledger.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/usage.md
  - docs/api.md
  - docs/generated/planning_lineage.yaml
related_features:
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages: []
---

## Goal

Implement bounded template SSOT patch that fixes verified control-plane truth bugs and
improves design-governance on touched surfaces only.

## Key Deliverables

### Deliverable 1: Template truth defects are fixed at shared owners

Settings filtering, bookmarks archived rendering, and delete-archived confirmation/execute
parity are corrected through one owner per concern instead of local special cases.

### Deliverable 2: Touched UI surfaces gain stronger design-governance

Shared tokens, badge semantics, partials, and interactive state handling are restored to
single-owner patterns across touched templates.

### Deliverable 3: Regression proof and docs stay aligned

Focused tests, planning-lineage refresh, and operator docs confirm the patch without
expanding into full redesign work.

## Task/Wave Breakdown

### Task 1: Fix settings filtering contract

**Purpose:**
- replace split filter/search visibility logic with one combined owner

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec remains `proposed|active`
- current settings sections and danger-zone semantics are confirmed from live template

**Steps:**
- [x] Step 1: inventory current axis-filter, search-filter, and section-hide paths in `settings.html`.
- [x] Step 2: consolidate visibility computation so cards and sections derive from one combined rule set.
- [x] Step 3: keep danger-zone behavior explicit inside same owner instead of separate special-case pass.
- [x] Step 4: remove or shrink redundant visibility toggles left behind by old split logic.

**Verification:**
- [x] add/extend tests for axis-only, search-only, and combined filtering
- [x] rendered settings output keeps danger-zone visibility truthful under combined filters

**Exit Criteria:**
- settings filtering has one state owner
- no visible-section drift remains between search and axis filters

### Task 2: Fix archived data and delete-archived truth surfaces

**Purpose:**
- make archived bookmark rendering and delete-archived destructive preview truthful

**Files:**
- Inspect: `src/fitcv_cp/templates/bookmarks.html`
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- delete-archived route/store contract already exists in source
- archived bookmark data is already present in template context

**Steps:**
- [x] Step 1: render archived bookmarks in `view == 'all'` so empty-state and list contents use same data truth.
- [x] Step 2: choose one owner for delete-archived matched-count semantics: either server-count preview or explicit client-submitted eligible set validated server-side.
- [x] Step 3: align confirmation copy, request contract, and response feedback to that one owner.
- [x] Step 4: keep destructive behavior bounded to archived runs and preserve existing archived-view UX.

**Verification:**
- [x] add/extend tests for archived bookmarks visible in all-view combinations
- [x] add/extend tests for zero-match and matched delete-archived confirmation/response parity

**Exit Criteria:**
- archived bookmarks no longer disappear from all-view
- delete-archived preview count and executed scope share one contract

### Task 3: Restore shared tokens and semantic status styling

**Purpose:**
- improve design-governance by moving touched styling back to shared owners

**Files:**
- Inspect: `src/fitcv_cp/templates/base.html`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 and Task 2 fixes are scoped
- touched templates using missing vars/classes are identified

**Steps:**
- [x] Step 1: define missing shared vars/classes in `base.html` or stop exporting them from touched templates.
- [x] Step 2: add missing `badge-neutral` shared styling if backend can emit it.
- [x] Step 3: replace touched ad hoc local status-color rules with shared badge/token semantics where possible.
- [x] Step 4: remove duplicate local style blocks only when shared base owner fully covers touched usage.

**Verification:**
- [x] inspection confirms `base.html` owns shared vars/classes referenced by touched templates
- [x] rendered touched pages no longer depend on missing vars or extra local semantic color systems

**Exit Criteria:**
- shared token/class debt is reduced on touched surfaces
- touched status styling follows shared semantic owner

### Task 4: Extract drifted synonym fragments and clean tab state owner

**Purpose:**
- reduce duplicate UI markup and split interactive truth on touched surfaces

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/synonym_review.html`
- Inspect: `src/fitcv_cp/templates/_synonym_overlay_upload_form.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Modify: `src/fitcv_cp/templates/_synonym_overlay_upload_form.html`
- Modify: `src/fitcv_cp/templates/_synonym_decision_ledger.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- touched duplicate synonym blocks are confirmed live
- shared partial names/locations are stable enough for reuse

**Steps:**
- [x] Step 1: extract or reuse shared partial for synonym decision ledger where duplication already drifted.
- [x] Step 2: keep upload-form partial ownership single across `run_detail.html` and `synonym_review.html`.
- [x] Step 3: refactor run-detail tabs so semantic markup, active classes, and JS switching derive from one state owner.
- [x] Step 4: add basic roles/aria hooks and remove redundant inline/global state mutations where safe.

**Verification:**
- [x] inspection confirms shared synonym fragments are reused from one owner
- [x] tests/markup checks confirm tab controls render with role/aria hooks and stable active-state behavior

**Exit Criteria:**
- synonym UI duplication is reduced on touched surfaces
- run-detail tabs no longer split truth across multiple state models

### Task 5: Final docs, lineage, and regression closeout

**Purpose:**
- align docs and finish with targeted proof only

**Files:**
- Modify: `docs/usage.md`
- Modify: `docs/api.md`
- Modify: `docs/generated/planning_lineage.yaml`
- Verify: `docs/superpowers/specs/2026-06-25-15-10-template-ssot-patch-spec.md`
- Verify: `docs/superpowers/plans/2026-06-25-15-18-template-ssot-patch-plan.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: update operator/API docs only if user-visible wording or route contract changed.
- [x] Step 2: regenerate `docs/generated/planning_lineage.yaml`.
- [x] Step 3: run targeted control-plane tests for touched surfaces.
- [x] Step 4: run fast validator hook and fix any resulting planning/template drift.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or bookmarks or archived or run_detail or synonym"`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs and planning lineage are current
- focused tests and validator pass

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or bookmarks or archived or run_detail or synonym"`
- `python scripts/generate_planning_lineage.py`
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
