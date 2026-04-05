---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Remove the three non-functional CV content-rule toggles from active config and admin settings while keeping max-pages validation warning-only."
---

# Remove Unused CV Content Rules From Pipeline Plan

## Summary

Implement a focused cleanup that removes the three dormant CV content-rule settings from the active pipeline contract and admin UI:

- `cv_emphasize_required_skills`
- `cv_align_jd_terminology`
- `cv_evidence_grounded_only`

Keep `cv.validation.max_pages` as the remaining active CV validation length control, and preserve its current warning-only behavior.

## Scope

This plan covers:

- removing the three unused content-rule keys from canonical CV policy config
- removing the three settings from the admin settings schema and UI grouping
- removing any lingering config compatibility/default-hydration assumptions for those keys
- keeping `cv.validation.max_pages` active and warning-only
- syncing docs so the source of truth no longer implies those toggles are meaningful runtime switches

This plan does not cover:

- changing `cv_generation` prompting behavior
- redesigning CV validation beyond this cleanup
- converting `max_pages` into a hard validation failure
- replacing page-based length control with a word-based policy

## Triage

Feature type: MODIFY
Summary: Remove three dormant CV content-rule toggles from the active pipeline and admin settings surface while preserving warning-only page-length validation.
Reasoning: The current pipeline does not meaningfully branch on these toggles; keeping them in config and UI creates drift and misleading controls.
Invariants:
  - `cv.validation.max_pages` remains active.
  - Page-over-limit remains a warning, not a hard failure.
  - Grounding and JD-alignment behavior that is currently baked into generation/validation must not regress.
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
Spec needed: no
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
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/validator.py)

Primary tests:

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_validator.py)

Generated refresh required:

- yes

## Invariants

- `cv.validation.max_pages` stays in canonical config and admin settings.
- Page length remains warning-only in validation.
- The three removed rules must no longer appear as active pipeline settings or active admin controls.
- Existing grounded/analysis-aware validation behavior stays intact.

## Implementation Tasks

### Task 1: Remove Dormant Content Rules From Canonical CV Policy Config

### Goal

Make canonical config reflect only CV-generation/validation settings that the active runtime actually uses.

### Code targets

- [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/policy/cv.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- remove `cv.content_rules.emphasize_required_skills`
- remove `cv.content_rules.align_jd_terminology`
- remove `cv.content_rules.evidence_grounded_only`
- stop defaulting or projecting those keys as canonical active config values
- keep `cv.validation.max_pages` intact

### Output

- canonical CV policy config no longer advertises the three dormant rules

### Task 2: Remove The Three Settings From The Admin Settings Surface

### Goal

Ensure the settings UI no longer presents non-functional controls as if they were meaningful runtime switches.

### Code targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

### Work

- remove the three schema entries from the CV settings registry
- remove the `Content Rules` grouped form section if it becomes empty
- keep the `Validation` section with `CV Maximum Pages`
- update grouped-form expectations and schema tests accordingly

### Output

- admin UI exposes only meaningful CV controls for the current runtime path

### Task 3: Clean Up Residual Compatibility and Runtime Assumptions

### Goal

Retire leftover config/runtime assumptions so the removed rules do not keep surfacing through compatibility glue.

### Code targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- any runtime metadata/export paths that include CV setting snapshots
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- stop exposing the three removed rules as effective runtime settings
- remove default-hydration expectations for those keys
- ensure settings snapshots remain accurate after the cleanup

### Output

- runtime metadata and exported settings no longer imply those rules are active switches

### Task 4: Lock In Warning-Only Max-Pages Validation

### Goal

Make the remaining length setting’s behavior explicit and protected by tests.

### Code targets

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/validator.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_validator.py)

### Work

- keep `check_length_constraints(...)` warning behavior unchanged
- add or update tests to assert over-budget CVs produce warnings rather than hard failure
- make the warning-only behavior clearer in validator comments or test names if needed

### Output

- `max_pages` remains the sole active user-facing CV validation limit and stays warning-only

### Task 5: Sync Feature, Stage, and History Docs

### Goal

Bring source-of-truth docs in line with the actual active CV-generation contract.

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

- remove wording that presents the three content rules as configurable runtime capabilities
- document `CV Maximum Pages` as the remaining active user-facing validation control
- keep wording aligned with warning-only length validation

### Output

- docs no longer imply those three dormant rules are meaningful settings

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_config.py .worktrees\e2e-0\tests\test_fitcv_cp\test_settings_schema.py .worktrees\e2e-0\tests\test_validator.py -k "cv or settings or max_pages or validation"
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv_cp\settings_schema.py .worktrees\e2e-0\src\fitcv\validator.py
```

If the admin settings page has template-level assertions, include that focused slice too.

## Risks

- old tests may still assume the presence of the `Content Rules` group
- doc capability lists may still mention the removed rules in multiple places
- compatibility cleanup may need to preserve flat-path fallback for unrelated CV settings while removing only the dormant keys

## Rollout Order

1. remove dormant rules from canonical config
2. remove the three controls from the admin settings schema/UI
3. clean up residual compatibility/runtime assumptions
4. lock in warning-only `max_pages` validation with tests
5. sync docs and generated discovery

## Done Criteria

- the three dormant content-rule settings no longer appear in active config, runtime settings snapshots, or admin UI
- `CV Maximum Pages` remains available as the only user-facing CV validation control
- over-budget CVs still produce validation warnings rather than hard failures
- source-of-truth docs describe the simplified CV settings surface accurately
