---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
  - docs/usage.md
related_features:
  - settings_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Operator Control Plane Agentic Settings Surface Plan

**Feature Source:** `docs/features/settings_system/feature.source.yaml`  
**Feature Contract:** `docs/features/settings_system/settings_system.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Add a bounded, truthful `Agentic` settings surface to `/admin/settings` for real operator-tunable future-run defaults, while keeping setup-only knobs, secrets, and run-history truth out of the live settings form.

**Architecture:** This work centers on the control-plane settings stack. `src/fitcv_cp/settings_schema.py` must become the source of truth for which agentic settings are editable, fixed metadata, or excluded, while `src/fitcv_cp/app.py` and `src/fitcv_cp/templates/settings.html` render those settings in a task-first `Agentic` section with the same grouped-save and truth-messaging rules used elsewhere. Managed feature/docs updates should explain how these defaults relate to run-scoped `settings-used.json` and observability surfaces rather than reproducing run inspection inside the settings page.

**Key Invariants:**
- only real schema-backed operator-tunable agentic defaults may appear in `/admin/settings`
- provider credentials, deployment glue, and hidden implementation-only settings stay out of the settings page
- agentic settings remain future-run defaults, not historical run truth
- `settings-used.json` and run-detail observability remain authoritative for what a specific run actually used or did
- deterministic acceptance and late-stage outcome contracts remain authoritative even when agentic defaults change

**Rollout / Revert:**  
- rollback_trigger: the new `Agentic` section exposes non-owned controls, blurs run-history truth, or drifts from runtime-backed settings behavior  
- rollback_method: revert the bounded agentic-settings patch together so schema, rendering, docs, and tests move back to the prior non-agentic settings surface in one slice

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Implement a bounded `Agentic` section in `/admin/settings` for real operator-tunable agentic defaults and align the schema, docs, and tests to that runtime ownership.  
Reasoning:

- the thread and detailed spec now exist and clearly bound this change
- the work primarily modifies the existing `settings_system` managed feature
- it also touches operator-facing explanation and run-truth relationship docs, but does not require a broader execution map
- the implementation should stay small and source-backed rather than speculative

Invariants:

- only supported operator-owned agentic settings are rendered
- metadata-only agentic fields remain explanatory, not persistable edits
- omitted setup-only fields remain absent from the UI and saved payloads
- truth messaging still points operators to run-scoped observation and `settings-used.json`

Dependencies:

- `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/settings_system/settings_system.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`

Affected stages:

- `cv_analysis`
- `cv_generation`

Affected features:

- `settings_system`
- `inspection_debugging`
- `trigger_run_management`

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
- `settings_system.grouped-form-validation`
- `settings_system.trigger-time-effective-settings-snapshot`
- `settings_system.settings-used-exports`
- `inspection_debugging.settings-used-export`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- the new settings section exposes non-runtime-owned agentic knobs, persists metadata-only agentic fields, or misstates historical run truth

Rollback method:

- revert the bounded schema, settings-page, and docs changes together so the prior settings surface is restored consistently

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

- `docs/features/settings_system/feature.source.yaml`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_app.py`
- `docs/configuration.md`
- `docs/usage.md`
- `docs/features/settings_system/history.md`
- `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`
- generated:
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/settings_system/lineage.generated.yaml`
  - `docs/generated/planning_lineage.yaml`

Tests to update:

- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_app.py`

Files to create:

- `docs/superpowers/plans/2026-04-28-operator-control-plane-agentic-settings-surface-plan.md`

## Task 1: Define The Bounded Agentic Settings Registry

**Files:**
- Create: `none`
- Modify:
  - `docs/features/settings_system/feature.source.yaml`
  - `src/fitcv_cp/settings_schema.py`
  - `src/fitcv_cp/settings_store.py`
- Test:
  - `tests/test_fitcv_cp/test_settings_schema.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing schema tests for:
  - the new agentic capability and section ownership
  - editable vs metadata-only vs excluded agentic setting classification
  - persistence-backed config paths for every editable agentic setting
  - omission of setup-only or deployment-only agentic knobs from the registry
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py -k "agentic or settings_section"`
- [ ] Step 3: Update `docs/features/settings_system/feature.source.yaml` to name the bounded operator-facing agentic settings capability.
- [ ] Step 4: Update `src/fitcv_cp/settings_schema.py` so:
  - the first supported agentic settings set is registered explicitly
  - the registry owns task section placement and mutability classification
  - non-owned agentic implementation glue remains excluded
- [ ] Step 5: Update `src/fitcv_cp/settings_store.py` only if the new registry needs bounded editable-setting loading behavior for the agentic slice.
- [ ] Step 6: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py -k "agentic or settings_section"`

## Task 2: Render The Agentic Section And Save Surface

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/settings.html`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing settings-page tests for:
  - a dedicated `Agentic` task section or explicitly agentic-labeled controls
  - grouped save behavior for the bounded agentic controls
  - absence of setup-only or metadata-only agentic fields from editable form inputs
  - truth messaging that points operators toward `settings-used.json` and run-detail observation
  - preservation of current-vs-draft feedback for agentic controls
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "agentic and settings"`
- [ ] Step 3: Update `src/fitcv_cp/app.py` so the settings view:
  - adds a bounded `Agentic` section or card group driven from schema-owned truth
  - keeps advanced agentic tuning behind disclosure when appropriate
  - persists only editable agentic settings
  - keeps metadata-only agentic fields explanatory but non-editable
- [ ] Step 4: Update `src/fitcv_cp/templates/settings.html` so the agentic surface fits the existing task-first layout and truth-copy patterns without becoming a run-inspection view.
- [ ] Step 5: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "agentic and settings"`

## Task 3: Refresh Cross-Cutting Docs And Managed Outputs

**Files:**
- Create: `none`
- Modify:
  - `docs/configuration.md`
  - `docs/usage.md`
  - `docs/features/settings_system/history.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_settings_schema.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/configuration.md` and `docs/usage.md` to explain how the agentic settings surface relates to future-run defaults, per-run overrides, and `settings-used.json`.
- [ ] Step 2: Add a concise changelog note in `docs/features/settings_system/history.md` for the new bounded agentic settings surface.
- [ ] Step 3: Link this plan from `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`.
- [ ] Step 4: Run the focused regression suite for this slice:
  - `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py`
- [ ] Step 5: Refresh generated discovery and managed metadata outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 6: Run repo contract validation:
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 7: Confirm the worktree contains the intended agentic-settings slice plus any unrelated pre-existing files.

## Shared-Surface Risks

- `src/fitcv_cp/settings_schema.py`
  - the biggest risk is inventing “agentic” settings with no stable runtime owner
- `src/fitcv_cp/app.py`
  - the page can easily drift into a run-inspection surface if it starts narrating observability rather than linking operators toward it
- `src/fitcv_cp/templates/settings.html`
  - agentic controls could crowd the page unless advanced and metadata-only rules are applied carefully
- `docs/features/settings_system/feature.source.yaml`
  - capability wording must stay bounded to real operator-owned defaults, not speculative roadmap language
