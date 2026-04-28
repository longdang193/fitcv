---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-settings-surface-alignment-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-operator-control-plane-settings-surface-alignment-spec.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
  - docs/usage.md
related_features:
  - settings_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Operator Control Plane Settings Surface Alignment Plan

**Feature Source:** `docs/features/settings_system/feature.source.yaml`  
**Feature Contract:** `docs/features/settings_system/settings_system.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-28-operator-control-plane-settings-surface-alignment-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Keep the Settings page faithful to real runtime ownership by tightening which controls are editable, how task-first groups present current versus draft state, and how the page explains fixed, advanced, and run-scoped settings truth.

**Architecture:** The center of gravity is the control-plane settings stack: `src/fitcv_cp/settings_schema.py` defines which keys are operator-tunable, `src/fitcv_cp/settings_store.py` supplies persisted defaults, and `src/fitcv_cp/app.py` plus `src/fitcv_cp/templates/settings.html` render grouped task-first surfaces and grouped-save behavior. The implementation should stay additive to the current task-first UI rather than replatforming it, with docs updated only to explain the resulting operator contract.

**Key Invariants:**
- the settings UI only exposes controls that are real schema-backed runtime-backed operator settings
- fixed runtime fields render as metadata, not fake editable controls
- task-first grouping remains the primary navigation model
- grouped validation remains atomic and preserves draft values on invalid submissions
- run-scoped `settings-used` exports remain the historical truth for what a run used

**Rollout / Revert:**  
- rollback_trigger: the Settings page starts implying editability for fixed fields, loses grouped-save validation behavior, or diverges from actual persisted and run-scoped settings truth  
- rollback_method: revert the bounded settings-page alignment patch set together so schema, app, template, tests, and docs return to the prior consistent surface

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Implement the settings-surface alignment spec across schema-backed settings metadata, task-first control-plane rendering, grouped-save behavior, and operator-facing documentation.  
Reasoning:

- the bounded thread already exists and now has an approved detailed spec
- the work is centered on one managed feature, `settings_system`
- the implementation touches a small cluster of control-plane files and tests, not a repo-wide redesign
- no separate implementation execution map is needed because this is one narrow spec rather than a multi-spec execution set

Invariants:

- editable controls remain limited to supported persistence keys and save paths
- metadata-only fields continue to communicate provenance without pretending to be mutable
- advanced disclosure remains available without crowding the default operator workflow
- current versus draft state remains legible at grouped-card scope

Dependencies:

- `docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-settings-surface-alignment-spec.md`
- `docs/features/settings_system/feature.source.yaml`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`

Affected stages:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `settings_system`
- `trigger_run_management`
- `inspection_debugging`

Primary lens: `mixed`

Affected docs:
  feature_source: `docs/features/settings_system/feature.source.yaml`
  feature_yaml: `docs/features/settings_system/settings_system.yaml`
  feature_lineage: `docs/features/settings_system/lineage.generated.yaml`
  feature_history: `docs/features/settings_system/history.md`
  stage_source: `none`
  stage_contract: `none`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `docs/configuration.md`
    - `docs/usage.md`
  operating_system_docs:
    - `none`
  readme: `none`
  generated:
    - `docs/generated/planning_lineage.yaml`

Generated refresh required: `yes`  
Capability IDs:

- `settings_system.task-first-settings-ui`
- `settings_system.advanced-settings-disclosure`
- `settings_system.metadata-only-fixed-controls`
- `settings_system.compact-cv-visibility-controls`
- `settings_system.grouped-form-validation`
- `settings_system.per-run-overrides`
- `settings_system.run-safety-settings`
- `settings_system.trigger-time-effective-settings-snapshot`
- `settings_system.settings-used-exports`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- grouped settings saves become partially persistent, fixed fields appear editable, or operator-facing settings truth drifts from runtime-backed keys and run-scoped exports

Rollback method:

- revert the settings-surface alignment patch as one bounded change so schema, rendering, validation, and docs stay in sync

Migration needed: `no`  
Risk level: `medium`

## Doc Update Matrix

- Feature source: `docs/features/settings_system/feature.source.yaml`
- Feature contract: `docs/features/settings_system/settings_system.yaml`
- Feature lineage: `docs/features/settings_system/lineage.generated.yaml`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `docs/features/settings_system/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/configuration.md`
  - `docs/usage.md`
- Operating-system docs: `none`
- README: `none`
- Generated discovery:
  - `docs/generated/planning_lineage.yaml`

## File Structure First

Files to modify:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `docs/configuration.md`
- `docs/usage.md`
- `docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md`
- generated:
  - `docs/generated/planning_lineage.yaml`
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/settings_system/lineage.generated.yaml`

Tests to update:

- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_settings_store.py`

Files to create:

- `docs/superpowers/plans/2026-04-28-operator-control-plane-settings-surface-alignment-plan.md`

## Task 1: Tighten The Settings Truth Registry

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/settings_schema.py`
  - `src/fitcv_cp/settings_store.py`
- Test:
  - `tests/test_fitcv_cp/test_settings_schema.py`
  - `tests/test_fitcv_cp/test_settings_store.py`
- Docs:
  - `docs/features/settings_system/feature.source.yaml` only if capability wording needs small truth-alignment updates

- [ ] Step 1: Add failing schema and store tests for:
  - editable versus fixed field classification
  - persistence-key coverage for each rendered editable setting
  - baseline-default hydration still surfacing current values for non-overridden fields
  - exclusion of retired or implementation-only fields from the UI registry
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py`
- [ ] Step 3: Update `src/fitcv_cp/settings_schema.py` so task-first groups and field metadata explicitly encode:
  - editable controls
  - metadata-only controls
  - advanced-disclosure controls
  - group ownership needed for grouped validation and save behavior
- [ ] Step 4: Update `src/fitcv_cp/settings_store.py` only as needed so persisted defaults, baseline fallbacks, and fixed-field metadata remain consistent with the schema-backed registry.
- [ ] Step 5: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py`
- [ ] Step 6: Commit the settings-registry truth alignment change.

## Task 2: Align Task-First Rendering, Draft Feedback, And Grouped Saves

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/settings.html`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing control-plane tests for:
  - current versus draft feedback within grouped cards
  - dirty-state summaries such as no-changes versus unsaved-edits feedback
  - fixed runtime fields rendering as metadata instead of editable inputs
  - advanced settings disclosure staying collapsed but discoverable
  - group-atomic validation preserving draft values on invalid submission
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or config or validation"`
- [ ] Step 3: Update `src/fitcv_cp/app.py` so the settings route and save handlers:
  - derive editable versus fixed surfaces from schema-backed truth
  - preserve current-value visibility even when a value comes from baseline fallback
  - produce grouped dirty-state summaries and validation feedback
  - keep save boundaries aligned with operator-facing task groups
- [ ] Step 4: Update `src/fitcv_cp/templates/settings.html` so the page:
  - remains task-first
  - uses metadata-only presentation for fixed controls
  - keeps advanced fields behind explicit disclosure
  - preserves compact CV visibility controls where that dense surface is already the preferred operator contract
- [ ] Step 5: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or config or validation"`
- [ ] Step 6: Commit the task-first rendering and grouped-save alignment change.

## Task 3: Refresh Operator Docs And Managed Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/configuration.md`
  - `docs/usage.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_settings_schema.py`
  - `tests/test_fitcv_cp/test_settings_store.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/configuration.md` and `docs/usage.md` to explain:
  - that the Settings page edits future-run defaults
  - that per-run overrides are captured at trigger time
  - that run-scoped `settings-used` exports remain the historical source of truth
  - which settings classes are fixed metadata versus editable operator controls
- [ ] Step 2: Link this plan from the owning thread in `docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md`.
- [ ] Step 3: Run the focused regression suite for this slice:
  - `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py`
- [ ] Step 4: Refresh generated discovery and managed metadata outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 5: Run repo contract validation:
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 6: Confirm the worktree only contains intended settings-surface planning and any unrelated pre-existing files.
- [ ] Step 7: Commit the plan-linked docs and generated-output refresh.

## Shared-Surface Risks

- `src/fitcv_cp/settings_schema.py`
  - field metadata can quietly become a second undocumented contract if editable, fixed, and advanced-state rules are implied rather than encoded
- `src/fitcv_cp/app.py`
  - grouped-save logic can drift from task-first operator groupings if validation and save ownership are not derived from the same group registry
- `src/fitcv_cp/templates/settings.html`
  - convenience rendering can make fixed runtime fields look editable unless metadata-only presentation is deliberate
- `docs/configuration.md` and `docs/usage.md`
  - operator docs can overstate what the live settings page controls unless they point back to future-run defaults and run-scoped truth
