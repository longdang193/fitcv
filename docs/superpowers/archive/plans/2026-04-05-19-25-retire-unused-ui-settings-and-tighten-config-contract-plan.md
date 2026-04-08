---
feature_type: modify
feature_name: settings_system
status: completed
summary: "Remove metadata-only CV admin controls from the active settings surface and tighten remaining runtime reliance on legacy flat retrieval keys."
---

# Retire Unused UI Settings And Tighten Config Contract Plan

## Summary

Implement a narrow contract-honesty cleanup for the admin settings surface.

Keep active:

- prompt selection via `config/runtime/prompts.yaml` and the prompt registry
- preset-based template resolution
- canonical nested retrieval settings:
  - `pipeline.vector_search_top_n`
  - `pipeline.ai_score_top_n`

Remove from the active admin settings contract:

- `cv_prompt_version`
- `cv_template_path`

Tighten drift:

- update active runtime consumers to prefer canonical nested retrieval keys over legacy flat names
- preserve compatibility fallbacks in the config layer where useful during the migration window

## Scope

This plan covers:

- removing metadata-only CV settings from the admin schema and UI
- removing active-contract wording that implies those settings are operator-facing runtime controls
- tightening active retrieval/ranking runtime reads toward canonical nested config paths
- preserving low-risk compatibility for older config payloads where appropriate
- syncing feature, history, cross-cutting, and generated docs

This plan does not cover:

- redesigning prompt registry structure
- deleting all compatibility projection code
- changing prompt contents or switching prompt ownership
- changing shortlist, ranking, or CV-generation behavior beyond config-read cleanup
- removing provenance fields from stored run or CV records unless clearly safe

## Triage

Feature type: MODIFY
Summary: Remove unused CV admin controls from the active settings contract and reduce remaining flat-vs-nested config drift in runtime consumers.
Reasoning: The UI still exposes metadata-only or legacy-only controls while active runtime prompt/template selection and retrieval settings are now owned elsewhere.
Invariants:
  - active prompt selection for `enrich`, `ranking`, and `cv_generation` remains owned by the prompt registry and `config/runtime/prompts.yaml`
  - `cv_generation.structured_write` remains the sole active `cv_generation` runtime prompt contract
  - preset-based template resolution remains the active template path
  - retrieval, ranking, `cv_analysis`, and `cv_generation` behavior must not materially change
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

Primary code and config targets:

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/vector_search.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [pipeline.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/pipeline.yaml)

Primary tests:

- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)
- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_ai_score.py)
- [test_vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_vector_search.py)

## Invariants

- active prompt selection remains prompt-registry-owned
- `cv_prompt_version` is not reintroduced as a live runtime switch
- `cv_template_path` is not presented as an active admin-editable control
- shortlist and ranking continue to respect current effective top-N values
- compatibility tolerance for legacy config remains available where needed during migration

## Implementation Tasks

### Task 1: Remove Metadata-Only CV Controls From The Active Settings Schema

#### Goal

Stop presenting `cv_prompt_version` and `cv_template_path` as active operator-facing settings.

#### Code targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

#### Work

- remove `cv_prompt_version` from the active CV preset/settings schema
- remove `cv_template_path` from the active settings schema
- update grouped UI rendering and copy so CV settings no longer imply these are editable runtime controls
- preserve remaining active CV controls:
  - `cv_preset`
  - `cv_generation_model`
  - section visibility toggles
  - `cv_max_pages`

#### Output

- settings UI and schema expose only active CV operator controls

### Task 2: Preserve Runtime Compatibility While Reclassifying Those Fields

#### Goal

Keep older config and record compatibility intact without treating these fields as active control-plane knobs.

#### Code targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

#### Work

- keep prompt selection owned by `prompts.cv_generation.structured_write.prompt_id`
- keep `cv_prompt_version` only if needed for provenance or compatibility
- keep `cv_template_path` only as an internal fallback if still needed
- narrow comments and config-contract wording so those fields are clearly metadata/fallback, not operator-facing runtime controls

#### Output

- runtime remains backward-compatible while the active contract becomes clearer

### Task 3: Tighten Shortlist And Ranking Runtime Reads Toward Canonical Nested Keys

#### Goal

Reduce ongoing drift by making active consumers prefer the nested retrieval config the admin UI actually edits.

#### Code targets

- [vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/vector_search.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [pipeline.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/pipeline.yaml)
- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_ai_score.py)
- [test_vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_vector_search.py)

#### Work

- update `vector_search.py` to prefer `config["pipeline"]["vector_search_top_n"]` over `config["vector_top_n"]`
- update `ai_score.py` to prefer `config["pipeline"]["ai_score_top_n"]` over `config["rerank_top_n"]`
- retain flat-key fallback only as compatibility support if still needed
- decide whether legacy flat values in `pipeline.yaml` should remain temporarily or be documented as compatibility-only

#### Output

- active runtime consumers read the same canonical paths that the admin UI edits

### Task 4: Keep Provenance Accurate Without Misrepresenting Control Ownership

#### Goal

Ensure run records and debug surfaces still explain what happened without implying removed settings are active knobs.

#### Code targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)

#### Work

- keep prompt provenance driven by prompt definition/registry metadata
- ensure any retained `cv_prompt_version` values are clearly compatibility/provenance only
- avoid implying that removed settings are still part of the operator-facing runtime contract

#### Output

- provenance remains useful for debugging while the settings contract stays honest

### Task 5: Sync Feature, History, And Cross-Cutting Docs

#### Goal

Bring docs into alignment with the cleaned settings contract.

#### Doc targets

- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

#### Work

- document that active prompt control lives in `config/runtime/prompts.yaml`
- remove wording that implies `cv_prompt_version` or `cv_template_path` are live admin controls
- document canonical nested retrieval settings as the operator-facing contract
- refresh generated discovery after source-layer docs are updated

#### Output

- source-of-truth and discovery docs match the real settings/runtime contract

### Task 6: Verify The Contract Cleanup End-To-End

#### Goal

Prove the removed controls are absent and canonical nested settings still drive runtime behavior.

#### Verification targets

- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_ai_score.py)
- [test_vector_search.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_vector_search.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

#### Work

- add or update tests asserting `cv_prompt_version` and `cv_template_path` are absent from the active settings surface
- add or update tests showing canonical nested retrieval settings drive `vector_search.py` and `ai_score.py`
- keep compatibility-path tests where needed so old config still loads
- run a focused pytest slice plus `py_compile` for touched runtime modules

#### Output

- behavior and contract cleanup are verified before completion
