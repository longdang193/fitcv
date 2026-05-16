---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: settings-two-axis-ia-redesign-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-17-00-20-settings-two-axis-ia-redesign-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Implement two-axis Settings information architecture (intent layers + workflow-stage filtering) with explicit setting-card contracts and guarded edit behavior, while preserving existing backend settings semantics.

## Key Deliverables

### Deliverable 1: Two-axis settings navigation and filtering in admin UI

Settings page exposes intent-layer navigation and stage/state filter controls that can locate all existing settings keys without overlap or orphan keys.

### Deliverable 2: Setting-card clarity contract and badges

Each surfaced setting shows canonical clarity fields (`What`, `Effect`, `Applies when`, `Dependencies`, `Default source`, `Observed in`) and badges (`Layer`, `Stage(s)`, `Runtime-used`, `Metadata-only`, `Risk`).

### Deliverable 3: Layered edit policy with invariant-preserving guardrails

Low-risk layer edits remain lightweight; advanced/high-risk edits pass pre-save guardrail checks that align with existing backend validations.

### Deliverable 4: Regression-safe verification coverage

Automated tests and targeted checks prove unchanged payload/validation behavior and improved applicability clarity for known ambiguity scenarios.

## Task/Wave Breakdown

### Task 1: Build canonical settings mapping contract

**Purpose:**
- create single mapping source for each key’s intent layer, stage applicability, runtime/metadata status, and risk label

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- spec `2026-05-17-00-20-settings-two-axis-ia-redesign-spec.md` approved for implementation
- current schema keys inventory available

**Steps:**
- [x] Step 1: Add explicit per-key metadata model for layer/stage/risk/applies-when contract (without changing existing key names or config paths).
- [x] Step 2: Add helper accessors for UI layer filtering and stage filtering.
- [x] Step 3: Add/extend schema tests to assert full-key coverage and no unmapped key.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- every settings key has deterministic two-axis mapping and clarity metadata

### Task 2: Implement backend view-model support for two-axis UI

**Purpose:**
- provide template-ready grouped data and card contract fields from CP app layer

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: Build intent-layer collections and stage-filter collections from schema mapping.
- [x] Step 2: Attach setting-card contract fields and badges to rendered settings entries.
- [x] Step 3: Add/update app tests for grouped payload shape and key discoverability via both axes.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- backend provides complete two-axis data model with no missing keys

### Task 3: Redesign settings template for two-axis interaction

**Purpose:**
- implement UI navigation/filter layout and card-level clarity surface

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: Add primary intent-layer navigation sections (`General`, `Workflow Controls`, `Advanced Tuning`, `Governance/Metadata`).
- [x] Step 2: Add secondary stage filter controls and render filtered card sets.
- [x] Step 3: Render card contract fields and badges; preserve existing save endpoints/payload structure.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`

**Exit Criteria:**
- UI exposes both axes and setting-card clarity contract without breaking existing forms

### Task 4: Add layered guardrail UX and preserve backend invariants

**Purpose:**
- differentiate low-risk and high-risk edit flows while keeping backend validation as source of truth

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Step 1: Define layer-based save behavior flags (inline vs guarded confirmation path) using existing endpoints.
- [x] Step 2: Add pre-submit guardrail checks/messages for known invariant classes (weight sums, threshold ordering, dependent constraints).
- [x] Step 3: Keep backend validation error handling canonical; UI guardrails must mirror, not replace.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k "settings or validation"`

**Exit Criteria:**
- high-risk edits receive clear preflight warnings; backend validation behavior remains unchanged

### Task 5: Scenario regression and contract verification

**Purpose:**
- prove ambiguity reduction and no behavior regressions across known settings confusion scenarios

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: Add scenario tests for visibility intent vs eligibility messaging (including Certifications case semantics).
- [x] Step 2: Verify metadata-only keys are visibly marked and separated from runtime-used keys.
- [x] Step 3: Verify all keys are reachable through at least one intent layer and one valid filter state.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- tests demonstrate both clarity improvements and preserved runtime contract behavior

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -q`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_checkpoint_packs.py`
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

