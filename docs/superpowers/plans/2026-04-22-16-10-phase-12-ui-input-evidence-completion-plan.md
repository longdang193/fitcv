---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-04-22T16:10:00+02:00
change_id: 2026-04-22-phase-12-ui-input-evidence-completion
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 12 UI input evidence work.
parent_workstream: none
targets:
  - docs/features/multi_file_job_input/multi_file_job_input.yaml
  - docs/features/multi_file_job_input/lineage.generated.yaml
  - docs/features/ui_consistency_theming/ui_consistency_theming.yaml
  - docs/features/ui_consistency_theming/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/templates/base.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_models.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - multi_file_job_input
  - ui_consistency_theming
related_stages: []
---

# Phase 12 UI And Input Evidence Completion Implementation Plan

**Feature Source:** `docs/features/multi_file_job_input/feature.source.yaml`, `docs/features/ui_consistency_theming/feature.source.yaml`  
**Feature Contract:** `docs/features/multi_file_job_input/multi_file_job_input.yaml`, `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-16-02-phase-12-ui-input-evidence-completion-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task. Keep upload and theming ownership separated so app logic, persistence, and template tokens do not all claim the same behavior.

**Goal:** Complete the bounded Mode B evidence pass for `multi_file_job_input` and `ui_consistency_theming` by attaching direct code and test evidence to the upload-trigger, snapshot persistence, and shared base-template theming surfaces that already implement these behaviors.

**Architecture:** Upload parsing, validation, and canonical merge behavior live in `src/fitcv_cp/app.py`, while persisted jobs-input snapshots and run input contracts are owned by `src/fitcv_cp/bq_store.py` and `src/fitcv_cp/models.py`. Global design tokens, theme bootstrap, and shared UI component styles live in `src/fitcv_cp/templates/base.html`, with `app.py` contributing only the page structures that explicitly exercise headings, tab shells, action hierarchy, and responsive layouts.

**Key Invariants:**
- Do not edit generated feature contracts or lineage files manually.
- Add upload capabilities only to files that materially own upload parsing, validation, merge, or persistence.
- Add theming capabilities only to files that materially own theme/bootstrap/style tokens or explicit rendered structure.
- Only add `@proves` markers to tests that directly assert the named upload, snapshot, or UI/theming behavior.

**Rollout / Revert:**  
- rollback_trigger: weak or indirect UI/upload evidence mapping, or adoption-shape validation failure  
- rollback_method: remove Phase 12 metadata/proof markers/enforcement entries, rerun architecture sync, and return to the Phase 11 baseline

## Doc Update Matrix

- Feature source: `docs/features/multi_file_job_input/feature.source.yaml`, `docs/features/ui_consistency_theming/feature.source.yaml` unchanged unless audit reveals semantic drift
- Feature contract: `docs/features/multi_file_job_input/multi_file_job_input.yaml`, `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- Feature lineage: `docs/features/multi_file_job_input/lineage.generated.yaml`, `docs/features/ui_consistency_theming/lineage.generated.yaml`
- Stage source: none
- Stage contracts: none
- Feature history: `docs/features/multi_file_job_input/history.md`, `docs/features/ui_consistency_theming/history.md` unchanged unless narrative clarification becomes necessary
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`
- README: none
- Generated discovery: `docs/generated/*`

## Selected Mapping Audit

### Multi-File Job Input

| Capability | Code owner(s) | Proof test(s) | Confidence | Rationale |
| --- | --- | --- | --- | --- |
| `multi_file_job_input.multiple-file-inputs-in-trigger-form` | `src/fitcv_cp/app.py` | `test_admin_upload_trigger_merges_multiple_job_files`, `test_admin_upload_trigger_upload_mode_no_files_rejected` | complete_candidate | The app upload-trigger route owns multi-file form handling and upload-mode entry rules. |
| `multi_file_job_input.per-file-server-side-validation` | `src/fitcv_cp/app.py` | `test_admin_upload_trigger_one_invalid_file_rejects_entire_request`, `test_admin_upload_trigger_multi_file_non_array_rejected`, `test_admin_upload_trigger_all_empty_arrays_rejected` | complete_candidate | File-by-file validation happens in the upload-trigger request parser. |
| `multi_file_job_input.canonical-merge-preserving-order` | `src/fitcv_cp/app.py` | `test_admin_upload_trigger_merges_multiple_job_files`, `test_admin_upload_trigger_multi_file_preserves_order` | complete_candidate | Canonical merge and input-order preservation are implemented directly in app. |
| `multi_file_job_input.one-immutable-snapshot-stored-per-run` | `src/fitcv_cp/app.py`, `src/fitcv_cp/bq_store.py`, `src/fitcv_cp/models.py` | `test_admin_upload_trigger_merges_multiple_job_files`, `test_admin_upload_trigger_path_mode_stores_jobs_snapshot`, `test_insert_run_includes_input_metadata_params`, `test_row_to_run_maps_input_metadata_fields` | complete_candidate | App creates the snapshot, bq_store persists it, and models define the stored contract fields. |
| `multi_file_job_input.all-or-nothing-rejection-on-validation-failure` | `src/fitcv_cp/app.py` | `test_admin_upload_trigger_one_invalid_file_rejects_entire_request`, `test_admin_upload_trigger_all_empty_arrays_rejected` | complete_candidate | All-or-nothing rejection is endpoint-owned behavior in app. |

### UI Consistency & Theming

| Capability | Code owner(s) | Proof test(s) | Confidence | Rationale |
| --- | --- | --- | --- | --- |
| `ui_consistency_theming.css-custom-properties-design-tokens` | `src/fitcv_cp/templates/base.html` | none yet direct; use template metadata only unless a test explicitly checks token/bootstrap text | defer_candidate | Code ownership is clear, but the current tests do not directly assert token definitions as rendered behavior. |
| `ui_consistency_theming.shared-component-classes` | `src/fitcv_cp/templates/base.html` | `test_runs_list_renders_bulk_action_bar_hooks` only if explicit shared-class hooks are asserted; otherwise defer | defer_candidate | We need explicit class-level assertions, not just presence of content. |
| `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence` | `src/fitcv_cp/templates/base.html` | none yet direct | defer_candidate | The bootstrap code is obvious in `base.html`, but there is not yet a direct test for the toggle/persistence contract. |
| `ui_consistency_theming.flash-free-theme-application` | `src/fitcv_cp/templates/base.html` | none yet direct | defer_candidate | The anti-flash inline bootstrap is code-evident but not currently proven by tests. |
| `ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section` | `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/base.html` | `test_runs_list_renders_bulk_action_bar_hooks`, `test_settings_page_renders_task_first_sections` | complete_candidate | These tests directly assert the structured action layout and task-first section organization. |
| `ui_consistency_theming.human-readable-section-headings` | `src/fitcv_cp/app.py` | `test_settings_page_renders_task_first_sections`, `test_settings_page_renders_cv_preset_section`, `test_settings_page_renders_cv_composition_section` | complete_candidate | The rendered section titles and headings are assembled in app and asserted in tests. |
| `ui_consistency_theming.attached-tab-inspection-card-pattern` | `src/fitcv_cp/templates/base.html`, `src/fitcv_cp/app.py` | inspect existing run-detail tab tests for explicit attached-tab structure; otherwise defer | defer_candidate | The pattern exists in code, but we should only enforce it if a test asserts the shared structural pattern rather than feature-specific content. |
| `ui_consistency_theming.responsive-wrapping` | `src/fitcv_cp/templates/base.html`, `src/fitcv_cp/app.py` | `test_runs_list_shows_active_all_archived_filter_tabs` or related only if they assert wrapped/action-bar structure; otherwise defer | defer_candidate | Responsive behavior is likely code-evident but weakly test-proven right now. |

Deferred at plan start unless direct proof is discovered during execution:

- `ui_consistency_theming.css-custom-properties-design-tokens`
- `ui_consistency_theming.shared-component-classes`
- `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
- `ui_consistency_theming.flash-free-theme-application`
- `ui_consistency_theming.attached-tab-inspection-card-pattern`
- `ui_consistency_theming.responsive-wrapping`

Complete in this phase unless execution reveals weaker-than-expected proof:

- all `multi_file_job_input` capabilities
- `ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section`
- `ui_consistency_theming.human-readable-section-headings`

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-16-02-phase-12-ui-input-evidence-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-16-10-phase-12-ui-input-evidence-completion-plan.md`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/models.py`
- `src/fitcv_cp/templates/base.html`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_models.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Generated outputs to refresh**

- `docs/features/multi_file_job_input/multi_file_job_input.yaml`
- `docs/features/multi_file_job_input/lineage.generated.yaml`
- `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- `docs/features/ui_consistency_theming/lineage.generated.yaml`
- `docs/generated/*`

### Task 1: Upload And Theme Code Evidence

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/templates/base.html`
- Docs: `docs/operating_system/feature-lifecycle.md`

- [x] Step 1: Add missing `multi_file_job_input` capability metadata to `app.py`, and only the snapshot-contract capabilities to `bq_store.py` and `models.py`.
- [x] Step 2: Add `ui_consistency_theming` capability metadata only for the theming capabilities that have clear owner files and a realistic path to direct proof in this phase.
- [x] Step 3: Prefer `base.html` for theme/bootstrap/style ownership and keep `app.py` focused on rendered structural hierarchy and headings.
- [x] Step 4: Update `docs/operating_system/feature-lifecycle.md` to note the Phase 12 upload/UI evidence pass.

### Task 2: Upload And UI Proof Evidence

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_models.py`
- Docs: none

- [x] Step 1: Add `@proves` markers to direct multi-file upload tests covering multiple inputs, per-file validation, merge order, snapshot storage, and all-or-nothing rejection.
- [x] Step 2: Add `@proves` markers to BQ store and model tests covering persisted jobs-input snapshot fields.
- [x] Step 3: Add `@proves` markers only to the UI rendering tests that directly assert human-readable section headings and structured action hierarchy.
- [x] Step 4: Leave the currently under-proven theme-token/localStorage/attached-tab/responsive capabilities deferred unless a direct proof test is found during execution.

### Task 3: Enforcement And Regeneration

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Refresh: generated feature contracts, lineage, and `docs/generated/*`

- [x] Step 1: Add only the completed Phase 12 capabilities to `repo_config/adoption-mode.yaml`.
- [x] Step 2: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Step 3: Measure updated gap counts for `multi_file_job_input`, `ui_consistency_theming`, and repo-wide totals.

### Task 4: Verification And Closeout

**Files:**
- Modify: `docs/superpowers/archive/specs/2026-04-22-16-02-phase-12-ui-input-evidence-completion-spec.md`
- Modify: `docs/superpowers/plans/2026-04-22-16-10-phase-12-ui-input-evidence-completion-plan.md`

- [x] Step 1: Run focused pytest:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_validate_adoption_shape.py`
- [x] Step 2: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Step 3: Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Step 4: Run `git diff --check`.
- [x] Step 5: Mark the spec and plan completed with exact before/after gap counts, including any deliberate UI/theming deferrals that remain.

## Execution Notes

Status: `completed`

Outcome:

- Completed all selected `multi_file_job_input` evidence mappings.
- Completed the currently well-proven structural portion of
  `ui_consistency_theming`.
- `multi_file_job_input` moved from `5/5` missing code/test evidence to `0/0`.
- `ui_consistency_theming` moved from `8/8` missing code/test evidence to
  `6/6`, with the broader theme/bootstrap capabilities intentionally deferred.
- Repo-wide missing direct evidence moved from `70/70` to `63/63`.

Deferred:

- `ui_consistency_theming.css-custom-properties-design-tokens`
- `ui_consistency_theming.shared-component-classes`
- `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
- `ui_consistency_theming.flash-free-theme-application`
- `ui_consistency_theming.attached-tab-inspection-card-pattern`
- `ui_consistency_theming.responsive-wrapping`

Verification:

- Focused pytest passed: `279 passed`.
- `scripts/sync_architecture_docs.py --check` passed.
- `scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
