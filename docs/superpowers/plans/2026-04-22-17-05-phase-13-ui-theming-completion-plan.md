---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T17:05:00+02:00
change_id: 2026-04-22-phase-13-ui-theming-completion
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 13 UI theming evidence work.
parent_workstream: none
targets:
  - docs/superpowers/archive/specs/2026-04-22-16-27-phase-13-ui-theming-completion-spec.md
  - docs/superpowers/plans/2026-04-22-17-05-phase-13-ui-theming-completion-plan.md
  - scripts/sync_architecture_docs.py
  - src/fitcv_cp/templates/base.html
  - tests/test_fitcv_cp/test_app.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
  - docs/features/ui_consistency_theming/ui_consistency_theming.yaml
  - docs/features/ui_consistency_theming/lineage.generated.yaml
related_features:
  - ui_consistency_theming
related_stages: []
---

# Phase 13 UI Theming Completion Implementation Plan

**Feature Source:** `docs/features/ui_consistency_theming/feature.source.yaml`  
**Feature Contract:** `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-16-27-phase-13-ui-theming-completion-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** completed

> **For agentic workers:** Execute this phase conservatively. Do not force Python ownership onto template-owned behavior; add only the smallest repo-local metadata support needed for truthful template lineage.

**Goal:** Complete the remaining `ui_consistency_theming` evidence gaps by making the shared base template a first-class code-evidence surface, adding direct proof tests for the six deferred theming capabilities, and extending enforcement only after regenerated lineage shows full direct coverage.

**Architecture:** The six deferred theming capabilities are materially implemented in `src/fitcv_cp/templates/base.html`, not in `src/fitcv_cp/app.py`. Existing tooling only harvested Python `@meta`, so Phase 13 adds bounded template metadata ingestion for leading Jinja/HTML architecture blocks, then uses direct tests in `tests/test_fitcv_cp/test_app.py` to prove theme bootstrap, design tokens, shared classes, attached inspection composition, and responsive wrapping.

**Key Invariants:**
- Do not hand-edit generated feature contracts or lineage files.
- Keep template ownership selective and limited to the shared base template that materially implements the capability.
- Use direct `@proves` coverage for every newly enforced theming capability.
- Do not claim app-level ownership for CSS/bootstrap behavior that only exists in `base.html`.

**Rollout / Revert:**  
- rollback_trigger: template metadata parsing proves too broad or regenerated lineage over-attributes template ownership  
- rollback_method: remove the template parser, remove `base.html` metadata and proof markers, regenerate architecture docs, and return to the Phase 12 baseline

## Doc Update Matrix

- Feature source: `docs/features/ui_consistency_theming/feature.source.yaml` unchanged
- Feature contract: `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- Feature lineage: `docs/features/ui_consistency_theming/lineage.generated.yaml`
- Stage source: none
- Stage contracts: none
- Feature history: unchanged
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`
- README: none
- Generated discovery: existing `docs/generated/*` outputs refreshed by the current repo generator

## Mapping Audit

| Capability | Code owner(s) | Proof test(s) | Confidence | Rationale |
| --- | --- | --- | --- | --- |
| `ui_consistency_theming.css-custom-properties-design-tokens` | `src/fitcv_cp/templates/base.html` | `test_base_template_defines_theme_tokens_and_shared_classes` | complete_candidate | Dark/light CSS custom properties live only in the shared base template. |
| `ui_consistency_theming.shared-component-classes` | `src/fitcv_cp/templates/base.html` | `test_base_template_defines_theme_tokens_and_shared_classes` | complete_candidate | Shared card, sub-card, inspection-card, and pane classes are defined centrally in the template stylesheet. |
| `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence` | `src/fitcv_cp/templates/base.html` | `test_base_template_bootstraps_saved_theme_before_styles` | complete_candidate | The saved-theme bootstrap script reads `localStorage` and applies `data-theme`. |
| `ui_consistency_theming.flash-free-theme-application` | `src/fitcv_cp/templates/base.html` | `test_base_template_bootstraps_saved_theme_before_styles` | complete_candidate | Flash prevention is implemented by running the theme bootstrap before the stylesheet block. |
| `ui_consistency_theming.attached-tab-inspection-card-pattern` | `src/fitcv_cp/templates/base.html` | `test_run_detail_inspection_area_wrapped_in_inspection_card`, `test_run_detail_tab_bar_uses_attached_modifier` | complete_candidate | The shared attached-tab/card shell is styled in `base.html` and directly asserted in rendered run-detail tests. |
| `ui_consistency_theming.responsive-wrapping` | `src/fitcv_cp/templates/base.html` | `test_base_template_uses_wrapping_rules_for_shared_layout_surfaces` | complete_candidate | Shared `.page-header` and `.section-actions` wrapping rules live in the shared template CSS. |

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-16-27-phase-13-ui-theming-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-17-05-phase-13-ui-theming-completion-plan.md`
- `scripts/sync_architecture_docs.py`
- `src/fitcv_cp/templates/base.html`
- `tests/test_fitcv_cp/test_app.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Generated outputs to refresh**

- `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- `docs/features/ui_consistency_theming/lineage.generated.yaml`
- `docs/generated/*`

### Task 1: Template Ownership Support

**Files:**
- Modify: `scripts/sync_architecture_docs.py`
- Modify: `src/fitcv_cp/templates/base.html`

- [x] Step 1: Add bounded template architecture parsing for leading Jinja/HTML metadata blocks.
- [x] Step 2: Add selective `base.html` ownership metadata for the six remaining theming capabilities.

### Task 2: Direct Proof Coverage

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] Step 1: Add `@proves` markers to the existing attached-tab and inspection-card structure tests.
- [x] Step 2: Add direct proof tests for theme bootstrap persistence and flash-free ordering.
- [x] Step 3: Add direct proof tests for design tokens, shared component classes, and responsive wrapping.

### Task 3: Enforcement And Regeneration

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Refresh: generated feature contracts, lineage, and `docs/generated/*`

- [x] Step 1: Extend the direct-evidence pilot to the six Phase 13 theming capabilities.
- [x] Step 2: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Step 3: Confirm regenerated lineage closes all `ui_consistency_theming` code/test gaps.

### Task 4: Operating-System Docs And Closeout

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `docs/superpowers/archive/specs/2026-04-22-16-27-phase-13-ui-theming-completion-spec.md`
- Modify: `docs/superpowers/plans/2026-04-22-17-05-phase-13-ui-theming-completion-plan.md`

- [x] Step 1: Document the repo-local template ownership rule in `feature-lifecycle.md`.
- [x] Step 2: Run focused pytest and architecture validation.
- [x] Step 3: Record exact before/after gap counts and mark the spec and plan completed.

## Execution Notes

Status: `completed`

Outcome:

- Added repo-local template ownership support so `base.html` can participate truthfully in lineage.
- Completed all six previously deferred `ui_consistency_theming` capabilities.
- `ui_consistency_theming` moved from `6/6` missing code/test evidence to `0/0`.
- Repo-wide missing direct evidence moved from `63/63` to `14/14`.

Verification:

- Focused pytest passed for the touched app and adoption-shape surfaces.
- `scripts/sync_architecture_docs.py --check` passed.
- `scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
