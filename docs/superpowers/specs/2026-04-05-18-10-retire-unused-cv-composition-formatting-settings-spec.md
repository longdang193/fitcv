---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Retire dormant CV composition formatting settings from the active pipeline and admin settings contract while keeping active section visibility and max-pages controls."
---

# Retire Unused CV Composition Formatting Settings

## Summary

Clean up the active CV settings contract so the admin UI and runtime config expose only composition controls that currently affect the pipeline.

Keep:

- section visibility toggles
- `cv.validation.max_pages` as a warning-only validation control

Retire from the active pipeline and admin settings contract:

- `cv_summary_style`
- `cv_education_detail`
- `cv_experience_bullet_style`
- `cv_skills_max_items`
- `cv_publications_detail`
- `cv_languages_detail`

These formatting/detail controls are currently accepted and validated by preset/config code, but they do not meaningfully change the live `cv_generation` runtime path.

## Problem

The current CV composition surface mixes two categories:

- active controls that change generation/validation behavior
- dormant formatting/detail controls that are validated config but not consumed at runtime

This creates misleading UI, unclear pipeline provenance, and false confidence that formatting knobs influence generated CVs when they do not.

## Current-State Findings

Active today:

- section visibility toggles under `cv.composition.<section>.enabled`
- `cv.validation.max_pages`

Dormant today:

- `summary.style`
- `education.detail`
- `experience.bullet_style`
- `skills.max_items`
- `publications.detail`
- `languages.detail`

The dormant fields are still:

- present in canonical CV config
- exposed in the admin settings UI
- validated by preset composition validation

But they are not currently used to branch generation, rendering, or validation behavior in the live pipeline.

## Goals

- make the active settings surface truthful
- reduce admin/UI noise
- simplify CV-generation provenance and debugging
- keep the door open to reintroduce a smaller, truly runtime-backed formatting subset later

## Non-Goals

- wiring the retired formatting settings into runtime behavior now
- deleting preset validation support for dormant fields in the same change
- changing warning-only `max_pages` behavior
- redesigning CV generation prompts or rendering structure

## Triage

Feature type: MODIFY
Summary: Remove unused CV composition formatting/detail settings from the active pipeline contract and admin UI while preserving active section visibility and warning-only max-pages validation.
Reasoning: This is a contract cleanup on existing CV-generation behavior; the runtime is not gaining new formatting behavior, only shedding misleading controls.
Invariants:
  - section visibility toggles remain active
  - `cv.validation.max_pages` remains active and warning-only
  - live `cv_generation` behavior must not change materially
  - dormant formatting/detail fields may remain internally tolerated by preset/config validation during the migration window
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

## Proposed Design

### 1. Active Contract

The active CV composition/runtime contract should expose only:

- `cv.composition.<section>.enabled`
- `cv.validation.max_pages`

These are the only composition/validation settings that currently affect the live pipeline in a user-visible way.

### 2. Retired From Active Pipeline Contract

The following fields should be removed from:

- canonical admin-editable settings schema
- active admin settings UI
- active CV feature capability wording
- active runtime settings/provenance expectations where they are described as live controls

Fields:

- `cv.composition.summary.style`
- `cv.composition.education.detail`
- `cv.composition.experience.bullet_style`
- `cv.composition.skills.max_items`
- `cv.composition.publications.detail`
- `cv.composition.languages.detail`

### 3. Internal Tolerance During Migration

To keep the cleanup low-risk, the dormant formatting/detail fields may remain:

- tolerated by config loading when present
- accepted by preset validation logic if older config still includes them

But they should no longer be presented as active pipeline controls.

This keeps the cleanup focused on contract honesty, not broad preset-schema redesign.

### 4. Runtime Behavior

No new runtime formatting behavior is introduced.

Expected active behavior after cleanup:

- section inclusion still follows `enabled`
- `max_pages` remains warning-only
- generation/render/validation behavior otherwise remains unchanged

## Why This Is The Optimized Solution

This is the smallest change that restores truthfulness between:

- settings UI
- config contract
- actual runtime behavior

It avoids:

- implementing half-defined formatting behaviors just to justify existing knobs
- preserving misleading settings that increase operator confusion
- deleting internal preset fields prematurely when we may want some of them later

## Future Reintroduction Strategy

If formatting controls are later wired into runtime behavior, reintroduce only the highest-value subset first:

1. `experience.bullet_style`
2. `summary.style`
3. `skills.max_items`

Any reintroduced control must have:

- explicit runtime ownership
- prompt/render/validation behavior
- tests proving it changes output semantics

## Acceptance Criteria

- the admin settings UI no longer shows the dormant composition formatting/detail controls
- active CV settings surface keeps only section visibility toggles plus `CV Maximum Pages`
- feature/stage docs no longer imply the retired formatting/detail controls are active runtime knobs
- `cv_generation` runtime behavior remains unchanged aside from cleaner contract/provenance
- `CV Maximum Pages` remains warning-only

## Risks

- some tests may still assume the removed controls exist in the settings page
- docs may still describe the broader composition model as if all formatting fields are active
- internal preset/config validation may still mention retired fields unless wording is carefully scoped to “tolerated but not active”

## Open Decision

This spec keeps dormant formatting/detail fields tolerated internally during the migration window.

A later cleanup may decide whether to:

- fully remove them from canonical `cv.yaml`
- or keep them as dormant preset-schema placeholders for future runtime wiring
