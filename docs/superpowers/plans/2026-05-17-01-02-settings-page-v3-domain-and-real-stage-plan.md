---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: settings-page-v3-domain-and-real-stage
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-17-02-20-settings-page-v3-domain-and-real-stage-spec.md
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
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

Implement Settings page V3 so filter/navigation model is compact and unambiguous: one primary `Domain` axis, `Workflow Stage` aligned to real pipeline stages, and compact row guidance without backend contract regressions.

## Key Deliverables

### Deliverable 1: Domain-only primary axis and UI naming cleanup

Remove redundant `Intent Layer` selection surface from Settings UI and normalize labels/metadata so users operate through one primary grouping axis (`Domain`) without ambiguous dual controls.

### Deliverable 2: Real pipeline-stage filter wiring

Replace lifecycle-state stage chips with canonical runtime stage chips sourced from pipeline stage sequence, with deterministic key-to-stage mapping used by schema, app context, and template filtering.

### Deliverable 3: Compact guidance rendering and direct editing flow

Keep settings rows compact by moving long descriptive prose into help expanders/tooltips and preserve direct editing flow without reintroducing `Enable override` gating.

### Deliverable 4: Regression-safe rollout evidence

Update/extend Settings schema and template tests to prove discoverability parity, stage-filter correctness, and unchanged save/validation behavior.

## Task/Wave Breakdown

### Task 1: Normalize metadata contracts for V3 axis + real stages

**Purpose:**
- make schema/app context expose one primary domain taxonomy and stage metadata tied to runtime stage truth

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- V3 spec decisions approved in `docs/superpowers/specs/2026-05-17-02-20-settings-page-v3-domain-and-real-stage-spec.md`
- canonical stage source available via `PIPELINE_STAGE_SEQUENCE`

**Steps:**
- [ ] Step 1: audit existing workflow-stage constants and replace lifecycle-state mapping with runtime stage IDs (`normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, `cv_generation`)
- [ ] Step 2: keep each setting key mapped to exactly one domain and one-or-more runtime stages where applicable; keep invariants for metadata-only/runtime-used keys
- [ ] Step 3: maintain compatibility helpers only where needed while ensuring primary accessor semantics are `Domain` + real stage IDs

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- schema metadata and helper outputs expose real-stage filters and no orphan keys

### Task 2: Update Settings route context and filter payloads

**Purpose:**
- ensure server-rendered context emits V3-ready axis/filter data and summary stats

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: replace lifecycle-stage title map with real pipeline-stage titles and IDs in `settings_stage_filters`
- [ ] Step 2: remove redundant `settings_intent_layers` usage from active template context path (preserve temporary alias only if needed for safe migration)
- [ ] Step 3: ensure summary structures and row metadata still expose modified/error/override/effective-source signals used by UI

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`

**Exit Criteria:**
- route context reflects single primary domain axis and runtime-aligned stage filters without breaking render contracts

### Task 3: Redesign template filter rail and compact help surfaces

**Purpose:**
- apply V3 interaction model in Settings UI: remove redundant selector, keep compact scan, retain clear help and editing affordances

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: remove redundant `Intent Layer` chip group from page shell and keep single `Domain` filter rail
- [ ] Step 2: render stage chips from real pipeline stages; keep front-end filtering logic aligned with updated `data-workflow-stages`
- [ ] Step 3: keep long prose hidden behind compact help expanders/tooltips and preserve direct editing controls without override gate

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q -k "settings and (render or template or filter or override or error)"`

**Exit Criteria:**
- default Settings view is compact, filter model is unambiguous, and row guidance remains accessible on demand

### Task 4: Harden tests for V3 contracts and run regression slice

**Purpose:**
- lock V3 behavior with explicit assertions and prove no unintended contract regressions

**Files:**
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: add/adjust assertions for stage-filter IDs parity with runtime stage sequence and absence of redundant primary-axis controls
- [ ] Step 2: add/adjust template assertions for compact help behavior and direct-edit flow expectations
- [ ] Step 3: run full settings regression slice and fix any contract drift

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- tests encode V3 contracts and pass for schema + route + template surfaces

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- `python scripts/validate_planning_lifecycle.py --strict`

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
