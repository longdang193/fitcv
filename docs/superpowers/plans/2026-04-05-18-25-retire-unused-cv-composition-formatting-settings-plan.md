---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Remove dormant CV composition formatting/detail settings from the active pipeline contract and admin UI while keeping section visibility toggles and warning-only max-pages validation."
---

# Retire Unused CV Composition Formatting Settings Plan

## Summary

Implement a narrow contract-honesty cleanup for CV composition settings.

Keep active:

- section visibility toggles
- `cv.validation.max_pages`

Remove from the active pipeline contract and admin settings surface:

- `cv_summary_style`
- `cv_education_detail`
- `cv_experience_bullet_style`
- `cv_skills_max_items`
- `cv_publications_detail`
- `cv_languages_detail`

Preserve current runtime behavior:

- no new formatting behavior is added
- `CV Maximum Pages` remains warning-only

## Scope

This plan covers:

- removing dormant CV formatting/detail controls from the active admin settings schema and UI
- removing active-contract wording that implies those controls affect the live pipeline
- cleaning up runtime/config/provenance assumptions that treat those fields as active controls
- preserving internal tolerance for older config that may still contain those fields, if needed
- syncing feature, stage, history, and generated docs

This plan does not cover:

- wiring these formatting/detail fields into runtime behavior
- redesigning CV generation prompts or template rendering
- changing section visibility behavior
- making `max_pages` a hard validation failure
- deleting dormant preset-validation support unless it is clearly dead and low-risk

## Triage

Feature type: MODIFY
Summary: Retire dormant CV composition formatting/detail settings from the active pipeline contract and admin UI while preserving active visibility toggles and warning-only max-pages validation.
Reasoning: The current live pipeline consumes section visibility and max-pages, but not the exposed formatting/detail knobs; this work aligns the settings surface with actual behavior.
Invariants:
  - section visibility toggles remain active
  - `cv.validation.max_pages` remains active and warning-only
  - live `cv_generation` behavior must not materially change
  - migration stays low-risk by tolerating older config where helpful
Dependencies:
  - `cv_system`
  - `settings_system`
Affected stages:
  - cv_generation
Affected features:
  - cv_system
  - settings_system
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/cv_system/cv_system.yaml`
  feature_history: `docs/features/cv_system/history.md`
  feature_docs:
    - `docs/features/settings_system/history.md`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: low

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code and config targets:

- [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/policy/cv.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [cv_presets.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_presets.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)

Primary tests:

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

## Invariants

- section visibility toggles remain active in config and UI
- `CV Maximum Pages` remains present in config and UI
- page overflow remains warning-only
- active CV-generation behavior must stay materially unchanged
- retired formatting/detail controls must no longer be presented as live runtime knobs

## Implementation Tasks

### Task 1: Remove Dormant Formatting Controls From The Active Settings Schema

### Goal

Stop presenting formatting/detail controls that do not affect the live pipeline.

### Code targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

### Work

- remove schema entries for:
  - `cv_summary_style`
  - `cv_education_detail`
  - `cv_experience_bullet_style`
  - `cv_skills_max_items`
  - `cv_publications_detail`
  - `cv_languages_detail`
- keep visibility toggles and `cv_max_pages`
- update CV composition grouped UI expectations accordingly

### Output

- admin settings surface shows only active CV composition controls

### Task 2: Remove Active-Contract Assumptions For Retired Formatting Fields

### Goal

Make the runtime/config contract reflect that those formatting/detail fields are not active controls.

### Code targets

- [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/policy/cv.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- remove or narrow wording that implies the dormant formatting/detail fields are live runtime controls
- keep active composition ownership focused on section visibility
- preserve compatibility tolerance where needed for old config payloads
- ensure runtime provenance continues to reflect only active controls

### Output

- active runtime contract and config wording match actual live behavior

### Task 3: Keep Preset Validation Low-Risk During The Migration Window

### Goal

Avoid unnecessary preset-schema churn while the active pipeline contract is being cleaned up.

### Code targets

- [cv_presets.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_presets.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- decide whether dormant formatting/detail fields remain tolerated by preset validation
- if retained, document them as tolerated/internal rather than active settings
- avoid changing live generation behavior

### Output

- migration remains low-risk and explicit about what is active versus merely tolerated

### Task 4: Lock In The Remaining Active CV Controls

### Goal

Protect the actual active behavior that should remain after the cleanup.

### Code targets

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/validator.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Work

- keep section visibility behavior intact
- keep warning-only `max_pages` behavior intact
- add or update focused tests if needed to prove these are still the active controls

### Output

- active CV controls remain stable and explicit

### Task 5: Sync Feature, Stage, and Generated Docs

### Goal

Bring source-of-truth docs in line with the cleaned settings contract.

### Doc targets

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

### Work

- remove wording that presents retired formatting/detail knobs as active runtime controls
- describe the active CV composition surface accurately:
  - visibility toggles
  - warning-only max-pages validation
- keep wording compatible with the migration-window tolerance decision

### Output

- docs match the live pipeline contract

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_config.py .worktrees\e2e-0\tests\test_cv_generator.py .worktrees\e2e-0\tests\test_fitcv_cp\test_settings_schema.py .worktrees\e2e-0\tests\test_fitcv_cp\test_app.py -k "cv or settings or composition or max_pages"
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv\cv_generator.py .worktrees\e2e-0\src\fitcv\cv_presets.py .worktrees\e2e-0\src\fitcv_cp\settings_schema.py .worktrees\e2e-0\src\fitcv_cp\app.py
```

## Risks

- tests may still assume the dormant formatting controls are present in the settings UI
- feature docs may still describe the broader composition model too broadly
- reducing active config wording too aggressively could obscure that some legacy fields are still tolerated internally

## Rollout Order

1. remove dormant formatting controls from active admin settings schema/UI
2. clean up active-contract wording and runtime assumptions
3. keep preset validation low-risk during the migration window
4. lock in active controls with focused tests
5. sync docs and generated discovery

## Done Criteria

- the dormant formatting/detail controls no longer appear as active admin-editable CV settings
- section visibility toggles remain active
- `CV Maximum Pages` remains active and warning-only
- docs no longer imply the retired formatting/detail controls affect the live pipeline
- focused verification passes
