---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Retire unused admin settings from the active pipeline contract and tighten remaining legacy config drift around CV prompt/version and legacy flat retrieval keys."
---

# Retire Unused UI Settings And Tighten Config Contract Spec

## Summary

The admin settings UI is much closer to the live runtime contract than before, but it still exposes at least one setting that does not act as a real runtime control and retains a few legacy compatibility surfaces that create drift:

- `cv_prompt_version` is exposed as if it changes CV generation behavior, but the active `cv_generation` prompt is now selected from the prompt registry via `config/runtime/prompts.yaml`
- `cv_template_path` remains in the settings schema as a legacy fallback even though preset/template resolution is the active path
- several runtime modules still read legacy flat config names like `vector_top_n` and `rerank_top_n` even though the control plane now owns canonical nested keys

This spec cleans up those mismatches so the admin settings surface more accurately reflects the live pipeline contract.

## Triage

Feature type: MODIFY  
Summary: Remove unused admin-editable controls from the active settings contract and reduce remaining config drift between the UI schema and runtime consumers.  
Reasoning: The current admin UI still presents at least one non-functional setting (`cv_prompt_version`) and the runtime continues to tolerate some legacy flat config keys that are no longer the canonical control surface.  
Invariants:
  - active prompt selection for `enrich`, `ranking`, and `cv_generation` continues to come from the prompt registry and `config/runtime/prompts.yaml`
  - `cv_generation` remains structured-prompt-first
  - `cv_template_path` may remain as an internal fallback during the migration window, but must not be presented as a live admin control
  - retrieval, ranking, `cv_analysis`, and `cv_generation` behavior must not materially change during this cleanup
Dependencies:
  - `settings_system`
  - `cv_system`
Affected stages:
  - shortlist
  - ranking
  - cv_generation
Affected features:
  - settings_system
  - cv_system
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/settings_system/settings_system.yaml`
  feature_history: `docs/features/settings_system/history.md`
  feature_docs:
    - `docs/features/cv_system/history.md`
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

## Source-Of-Truth Alignment

Affected current-state feature docs:

- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code targets:

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/vector_search.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)

Primary config targets:

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
- [pipeline.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/pipeline.yaml)
- [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/policy/cv.yaml)

## Problem

### 1. `cv_prompt_version` is not an active runtime control

The active `cv_generation` path uses the prompt registry and the configured `prompts.cv_generation.structured_write.prompt_id` to select the runtime prompt. The `cv.generation.prompt_version` field is still carried through config, settings, and persistence, but it does not control the prompt definition that is rendered.

Current effect:

- appears editable in the admin UI
- persists into run/config metadata
- does not actually switch the writer prompt

This makes it a misleading UI control.

### 2. `cv_template_path` remains in schema despite no longer being the active control surface

Preset-based template resolution is the active CV rendering contract. `cv_template_path` still exists as a legacy fallback in runtime code, but it is not part of the active preset-based admin UX.

This creates schema/runtime drift:

- schema implies it is a supported editable setting
- runtime treats it as fallback compatibility only

### 3. Runtime still reads some legacy flat retrieval keys directly

The config layer already normalizes between nested canonical settings and old flat names, but several modules still read legacy flat keys directly:

- `vector_search.py` reads `vector_top_n`
- `ai_score.py` reads `rerank_top_n`

This does not break behavior today, but it prolongs a split config contract:

- control plane edits canonical nested keys
- runtime consumers still tolerate and sometimes prefer flat names

## Goals

- remove unused or misleading admin-editable controls from the active pipeline contract
- ensure the settings UI exposes only knobs that affect live behavior
- preserve low-risk runtime compatibility during the migration window
- reduce flat-vs-nested config drift in active runtime consumers
- keep prompt provenance and runtime metadata accurate without presenting metadata-only values as operator controls

## Non-Goals

- redesign prompt registry structure
- remove all backward-compatibility projections in one pass
- change actual retrieval/ranking/CV behavior
- remove useful provenance fields from stored run or CV records if they still help debugging

## Proposed Design

### A. Retire `cv_prompt_version` from the active admin settings contract

`cv_prompt_version` should no longer appear as a live admin-editable setting.

Desired contract:

- active prompt selection is controlled by `config/runtime/prompts.yaml`
- prompt registry metadata remains authoritative for prompt definition and version
- if `cv.generation.prompt_version` is still retained temporarily, it is treated as internal metadata or compatibility-only, not as a control-plane knob

Preferred rollout:

1. remove `cv_prompt_version` from the admin schema and settings UI
2. stop presenting it as a supported operator control in docs
3. keep runtime tolerance for legacy config if needed during migration
4. derive prompt provenance from the prompt registry and selected prompt definition

### B. Retire `cv_template_path` from the active settings schema

`cv_template_path` should be removed from the active settings schema and UI-facing contract.

Desired contract:

- preset-driven template resolution is the active path
- any `cv_template_path` fallback remains internal and compatibility-only
- docs should describe preset/template ownership rather than raw template-path editing

### C. Tighten active runtime reads around canonical nested retrieval config

The active runtime should prefer canonical nested keys at point-of-use:

- `pipeline.vector_search_top_n`
- `pipeline.ai_score_top_n`

The config layer may continue to project flat legacy keys temporarily, but active consumers should stop depending on them directly.

Desired direction:

- `vector_search.py` prefers nested canonical path, with legacy fallback only if still necessary
- `ai_score.py` prefers nested canonical path, with legacy fallback only if still necessary
- docs describe nested keys as the only active operator-facing contract

## Expected Outcome

After this cleanup:

- the admin settings UI no longer exposes `cv_prompt_version`
- the admin settings schema no longer treats `cv_template_path` as a live editable control
- prompt selection truth is clearly owned by `config/runtime/prompts.yaml` plus the prompt registry
- retrieval/ranking runtime reads align better with the canonical nested settings contract
- remaining compatibility code is clearly internal rather than operator-facing

## Invariants

- `cv_generation.structured_write` remains the sole active runtime prompt contract for `cv_generation`
- section visibility toggles and warning-only `cv.validation.max_pages` remain active
- retrieval, ranking, `cv_analysis`, and `cv_generation` continue to honor current effective values after config normalization
- no run should fail because a legacy config still contains compatibility-only fields during the migration window

## Risks

### Low: stale tests and docs

Removing metadata-only settings from the schema/UI will require coordinated test and doc updates.

### Low: compatibility confusion if metadata survives in persistence

If `cv_prompt_version` remains in stored records temporarily but is removed from the UI, the docs must clearly explain that it is provenance/compatibility only.

### Medium: partial cleanup of flat legacy reads

If some runtime consumers are updated and others are not, the config contract can remain subtly inconsistent. The cleanup should be explicit about which active consumers are being migrated now.

## Acceptance Criteria

- `cv_prompt_version` is no longer exposed as an active admin-editable setting
- `cv_template_path` is no longer exposed as an active admin-editable setting
- active docs describe prompt ownership through the prompt registry and `config/runtime/prompts.yaml`
- `vector_search.py` and `ai_score.py` prefer canonical nested runtime settings instead of depending on flat legacy names
- compatibility fallbacks, if retained, are documented as internal migration support rather than operator-facing controls
- tests cover:
  - removed settings absence in UI/schema
  - prompt provenance still present and correct
  - canonical nested retrieval settings still drive runtime behavior

## Recommendation

Treat this as a contract-honesty cleanup, not a behavioral refactor.

The safest sequence is:

1. remove the misleading admin controls
2. keep compatibility in runtime/config loading where necessary
3. tighten point-of-use config reads toward canonical nested keys
4. update docs to match the real operator-facing contract

