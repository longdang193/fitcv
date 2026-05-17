---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: settings-page-deprecated-surface-removal
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-17-14-38-settings-page-deprecated-surface-removal-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
related_features:
  - settings_system
  - admin_control_plane_core
related_stages:
  - cv_generation
  - cv_analysis
---

## Goal

Implement settings-page deprecated-surface removal so `/admin/settings` exposes canonical runtime authority only, with deprecated keys hidden and write-rejected across all settings save paths.

## Key Deliverables

### Deliverable 1: Deprecated-key visibility enforcement

Introduce settings key visibility contract (`active | metadata_only | hidden_deprecated`) and apply it consistently in context assembly and page render flow.

### Deliverable 2: Save-route protection for hidden deprecated keys

Ensure single-key, group, and section save endpoints reject hidden deprecated keys with deterministic 422 behavior, eliminating silent drift and false authority writes.

### Deliverable 3: Verified UI + docs alignment

Add regression tests and documentation updates proving deprecated surfaces are no longer operator-visible controls while compatibility internals remain non-authoritative.

## Task/Wave Breakdown

### Task 1: Key Inventory and Deprecation Classification

**Purpose:**
- create source-of-truth mapping of settings keys to UI visibility policy before code edits

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec approved for implementation
- current `/admin/settings` behavior understood

**Steps:**
- [x] Step 1: inventory keys used by `settings_page_sections`, group registries, and section registries.
- [x] Step 2: add explicit deprecation visibility metadata for each deprecated/compat key.
- [x] Step 3: expose helper accessors for hidden-deprecated key set to be consumed by app routes/context.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "settings and deprec" -q`

**Exit Criteria:**
- hidden-deprecated key set is explicit and available to app layer

### Task 2: Settings Context and Template Surface Cleanup

**Purpose:**
- remove deprecated controls from rendered settings task cards without breaking canonical rows

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: filter card/section/group entry build to exclude `hidden_deprecated` keys.
- [x] Step 2: preserve metadata-only explanatory rows for canonical-relevant keys.
- [x] Step 3: keep owner/source labels consistent with runtime truth notes and mode summary.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "admin_settings and (render or metadata_only or hidden)" -q`

**Exit Criteria:**
- `/admin/settings` render contains no deprecated-hidden control rows

### Task 3: Save Route Guardrails for Deprecated Keys

**Purpose:**
- block deprecated writes across all settings mutation seams

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 hidden-deprecated registry available

**Steps:**
- [x] Step 1: enforce 422 rejection in `/admin/settings/{key}` for hidden-deprecated keys.
- [x] Step 2: enforce group-save rejection if any hidden-deprecated key is in submitted group payload.
- [x] Step 3: enforce section-save rejection if any hidden-deprecated key is in submitted section payload.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "settings and (422 or deprecated or group or section)" -q`

**Exit Criteria:**
- no deprecated key can be saved via UI routes

### Task 4: Regression Tests and Documentation Sync

**Purpose:**
- prove behavior and keep operator docs truthful

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `docs/configuration.md`
- Verify: `docs/pipeline.md`

**Preconditions:**
- Tasks 2 and 3 complete

**Steps:**
- [x] Step 1: add/adjust tests asserting hidden deprecated keys absent from page HTML.
- [x] Step 2: add/adjust tests asserting write rejection contract for deprecated keys.
- [x] Step 3: update config docs: distinction between internal compatibility vs operator-visible authority.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- tests and docs align with new visibility/write policy

### Task 5: Final Validation and Handoff Pack Refresh

**Purpose:**
- finalize plan execution readiness evidence and downstream handoff integrity

**Files:**
- Modify: `docs/generated/planning_lineage.yaml`
- Modify: `docs/superpowers/execution_context_packs/ai-plane-unification-and-backend-symmetry-implementation/latest.md`
- Modify: `artifacts/execution_context_pack.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: regenerate planning lineage after plan/state updates.
- [x] Step 2: run fast validators and repo contracts validation.
- [x] Step 3: refresh canonical + mirror execution context pack with deprecated-surface patch evidence and residual risks.

**Verification:**
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- patch ready for execution with synchronized plan/context artifacts

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -q`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`
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

## Execution Progress Log

- 2026-05-17: Task 1 completed. Added explicit deprecation visibility contract in `settings_schema` via `ui_deprecation_state` and `hidden_deprecated_settings_keys()`; classified `cv_generation_model` as `hidden_deprecated`.
- 2026-05-17: Task 2 completed. Updated settings context-card assembly to filter hidden deprecated keys from render/surface key lists.
- 2026-05-17: Task 3 completed. Added save-route guardrails for hidden deprecated keys across `/settings/{key}`, `/admin/settings/{key}`, group save, and section save flows.
- 2026-05-17: Task 4 completed. Updated tests and docs; `docs/configuration.md` now documents `hidden-deprecated` semantics and operator-visible authority boundary.
- 2026-05-17: Verification completed. `pytest tests/test_fitcv_cp/test_app.py -q` passed (`388 passed`), validator and repo-contract fast checks passed.

