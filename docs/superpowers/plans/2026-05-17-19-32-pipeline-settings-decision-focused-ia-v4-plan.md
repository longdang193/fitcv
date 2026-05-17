---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: pipeline-settings-decision-focused-ia-v4-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-17-19-22-pipeline-settings-decision-focused-ia-v4-spec.md
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
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement decision-first Pipeline Settings UX with SSOT decision-state classification, MECE primary groups, domain-filter secondary navigation, and progressive disclosure controls while preserving existing backend settings and validation contracts.

## Key Deliverables

### Deliverable 1: Canonical decision-state classifier and metadata contract

Settings schema and app view-model expose deterministic decision statuses, reason codes, precedence ordering, and domain labels from one canonical source.

### Deliverable 2: Decision-first UI layout with dual-layer IA

Settings page renders primary urgency tabs (`Needs Review`, `Recommended`, `Configured`, `Advanced`, `All`), overview readiness panel, top CTAs, and secondary domain filters without duplicating status logic.

### Deliverable 3: Progressive-disclosure and safety-action behavior

Hidden defaults/unused toggles, advanced detail expansion, and recommendation bulk-apply safety gates are implemented with explicit exclusion reasons and no backend behavior regression.

### Deliverable 4: Regression-proof verification coverage

Automated tests validate classifier determinism, MECE partitioning, cross-surface equivalence, domain-filter invariance, and persistence/validation parity.

## Task/Wave Breakdown

### Task 1: Implement SSOT classifier contract in settings schema

**Purpose:**
- define canonical decision-state and reason-code mapping so all UI surfaces derive from one invariant model

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- approved spec `2026-05-17-19-22-pipeline-settings-decision-focused-ia-v4-spec.md`
- existing settings key inventory and metadata fields are available

**Steps:**
- [x] Step 1: Add/extend per-setting metadata model to include `decision_status`, canonical `reason_codes`, `advanced`, `unused`, `recommended_delta`, and domain label fields.
- [x] Step 2: Implement deterministic precedence and tie-break ordering (`blocking > warning > recommendation > configured > hidden overlays`).
- [x] Step 3: Add helper accessors that return status buckets and counters without template-side reclassification.
- [x] Step 4: Ensure hidden-default/unused behavior is represented as visibility flags, not alternative status values.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- classifier output is deterministic, exhaustive, and single-source for all settings keys

### Task 2: Build app-layer view model for dual-layer IA

**Purpose:**
- provide renderer-ready data for primary decision tabs, secondary domain filters, and overview metrics

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: Construct primary tab groups from classifier status only (`Needs Review`, `Recommended`, `Configured`, `Advanced`, `All`).
- [x] Step 2: Build secondary domain filter index (`Domain & Taxonomy`, `Extraction Rules`, `Synonym Review`, `Output & Artifacts`) scoped within each tab.
- [x] Step 3: Compute overview readiness summary counts and next-action hints from same classifier snapshot.
- [x] Step 4: Add stable sorting for `Needs Review` priority order and consistent badge/action metadata payload.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`

**Exit Criteria:**
- app context exposes consistent tab/filter/counter model with no duplicate or conflicting status calculations

### Task 3: Redesign settings template to decision-first interaction model

**Purpose:**
- render new IA surface and remove mixed-axis top-level navigation

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: Add overview header panel with readiness summary and top CTAs (`Review Required Settings`, `Accept Recommended Settings`, `Run Pipeline`).
- [x] Step 2: Render primary decision tabs and ensure each setting card appears in one primary bucket only.
- [x] Step 3: Add secondary domain filters inside tab content and helper copy clarifying axis semantics.
- [x] Step 4: Apply symmetric card layout, badge language, and action labels across tabs.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k "settings and (tabs or overview or filters)"`

**Exit Criteria:**
- UI shows urgency-first flow, domain-scoped filtering, and consistent card/action semantics

### Task 4: Implement progressive disclosure and safety gating behaviors

**Purpose:**
- hide low-value details by default while preserving explicit operator control and safe bulk actions

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Step 1: Add toggle controls and state wiring for `Show Defaults` and `Show Unused`.
- [x] Step 2: Implement advanced detail expansion policy and tooltip boundary (short explanation only).
- [x] Step 3: Add `Accept Recommended Settings` preview/safety behavior showing included and excluded items with reasons.
- [x] Step 4: Keep high-risk/low-confidence items out of recommendation bulk-apply path.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k "recommended or advanced or defaults or unused"`

**Exit Criteria:**
- disclosure controls and bulk-action safety behavior match spec without hiding critical review items

### Task 5: Add MECE and equivalence regression test suite

**Purpose:**
- enforce invariance, equivalence, and non-overlap guarantees at test level

**Files:**
- Inspect: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: Add fixture-based tests proving deterministic classifier output for repeated identical inputs.
- [x] Step 2: Add MECE partition tests to assert unique primary-bucket membership per setting ID.
- [x] Step 3: Add cross-surface equivalence tests for overview counts vs tab contents vs classifier payload.
- [x] Step 4: Add domain-filter invariance tests to assert filter changes visibility only, not decision status.
- [x] Step 5: Add CTA gating tests for blocking/warning/ready scenarios.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- automated tests fail on any classifier drift, overlap regression, or cross-surface mismatch

### Task 6: End-to-end validation and plan handoff readiness

**Purpose:**
- produce final implementation confidence and clean handoff to execution workflow

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `tests/test_fitcv_cp/test_settings_schema.py`
- Inspect: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Step 1: Run targeted test suite and confirm no existing settings save/validation regression.
- [x] Step 2: Run repo fast validator and confirm planning/doc contracts remain valid.
- [x] Step 3: Record any residual risks or follow-up items for execution phase.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- plan is execution-ready with explicit proof path and no unresolved contract ambiguity

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -q`
- `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- `python scripts/validate_planning_lifecycle.py`
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
