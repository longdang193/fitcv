---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: synonym-workspace-action-model-simplification
parent_thread: workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow
parent_spec: docs/superpowers/specs/2026-05-19-22-45-synonym-workspace-action-model-simplification-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_fitcv_cp/test_app.py
related_features:
  - admin_control_plane_core
related_stages:
  - enrich
---

## Goal

Implement Synonym Workspace action-model simplification so synonym review actions stay in one interactive surface, redundant controls are removed, and operator feedback is deterministic and workspace-local.

## Key Deliverables

### Deliverable 1

Unified redirect contract for synonym actions where workspace-origin actions return to `/admin/runs/{run_id}/synonym-review` (or stay on promote preview) with no forced run-detail jump for normal operator flow.

### Deliverable 2

Simplified workspace controls: one canonical decision lane, one explicit AI recommendation action, one promote lane, and one actor input source.

### Deliverable 3

Regression coverage and UI assertions that lock action destination, banner behavior, and control-surface invariants.

## Task/Wave Breakdown

### Task 1: Normalize synonym action redirects

**Purpose:**
- remove navigation drift by aligning all synonym action postbacks to workspace contract

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Parent spec approved:
  `docs/superpowers/specs/2026-05-19-22-45-synonym-workspace-action-model-simplification-spec.md`
- current route behavior captured from tests and source

**Steps:**
- [ ] Step 1: enumerate workspace-origin action handlers and current redirect destinations
- [ ] Step 2: update handlers to redirect to `/synonym-review` for:
  - triage refresh
  - AI fast-path execute
  - promote commit (success and conflict summary)
  - any remaining workspace-origin no-op guards
- [ ] Step 3: keep explicit preview route behavior intact (`promote-preview` page) while handling no-approved state via workspace banner

**Verification:**
- [ ] Add/adjust route tests asserting `Location` headers for all touched endpoints

**Exit Criteria:**
- no workspace action unexpectedly lands user on run detail

### Task 2: Simplify workspace action surface

**Purpose:**
- remove redundant decision pathways and pseudo-mode controls

**Files:**
- Inspect: `src/fitcv_cp/templates/synonym_review.html`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- current UI control inventory confirmed

**Steps:**
- [ ] Step 1: remove per-row instant Approve/Defer/Reject submit forms
- [ ] Step 2: retain canonical batch lane:
  - per-row select
  - single batch submit button
- [ ] Step 3: replace AI/Manual mode toggle semantics with explicit AI assist action behavior and copy that matches backend reality
- [ ] Step 4: deduplicate actor inputs to one shared actor source for workspace actions

**Verification:**
- [ ] Template-render tests for presence/absence of key controls
- [ ] Manual HTML assertion checks for removed duplicate button labels

**Exit Criteria:**
- one canonical mutation path exists for decision updates

### Task 3: Gate controls by rollout mode and normalize banners

**Purpose:**
- prevent invalid actions from being shown and centralize status messaging in workspace

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 and Task 2 complete
- mode fields available from `_synonym_management_mode(run)` context

**Steps:**
- [ ] Step 1: conditionally render workspace controls based on mode flags (`apply_to_run_enabled`, `promote_global_enabled`, triage toggles)
- [ ] Step 2: add explicit workspace-local info messages for disabled/empty/no-op states
- [ ] Step 3: remove or downgrade duplicate synonym action banners in run detail to summary-only role

**Verification:**
- [ ] Tests for control visibility matrix under different mode settings
- [ ] Tests for workspace info banner rendering on no-approved/no-op states

**Exit Criteria:**
- UI no longer advertises actions that backend rejects by design

### Task 4: Regression and contract verification sweep

**Purpose:**
- prove patch stability and preserve existing synonym transition semantics

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/synonym_review.html`, `src/fitcv_cp/templates/run_detail.html`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: expand targeted tests for redirects, banners, and action controls
- [ ] Step 2: rerun existing promote/apply/batch tests to ensure semantic parity
- [ ] Step 3: run repo fast validator hook and resolve any planning/doc drift

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and (promote or batch or fast_path or review)"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- tests and validator pass with no unexpected contract drift

## Verification

- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and (promote or batch or fast_path or review)"`
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
