---
feature_type: modify
feature_name: settings_system
status: completed
summary: "Reorganize config files into responsibility-based subfolders under config/ while preserving compatibility during the migration window."
---

# Config Folder Reorganization Plan

## Summary

Implement the config-folder reorganization in a compatibility-first order:

- create the new `config/` subfolder structure
- move or copy the current YAML files into their new responsibility-based homes
- update the config loader to prefer the new paths
- preserve old-path fallback during the migration window
- refresh docs and generated discovery

The goal is to improve discoverability without changing runtime behavior.

## Scope

This plan covers:

- introducing `config/runtime/`, `config/policy/`, and `config/taxonomy/`
- relocating the existing config YAML files into those subfolders
- updating the loader to prefer the new layout
- preserving compatibility with the old flat layout temporarily
- updating docs to reflect the new config room structure

This plan does not cover:

- changing prompt text ownership
- moving `templates/cv_template.md`
- renaming config keys unless required for compatibility
- making additional settings admin-editable

## Source-of-Truth Alignment

Affected feature YAML:

- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code targets:

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)

Primary config targets:

- `config/runtime/pipeline.yaml`
- `config/runtime/prompts.yaml`
- `config/policy/ranking.yaml`
- `config/policy/cv_analysis.yaml`
- `config/policy/cv.yaml`
- `config/taxonomy/taxonomy.yaml`
- `config/taxonomy/skill_synonyms.yaml`
- `config/env.yaml`

Primary tests:

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

Generated refresh required:

- yes

## Invariants

- `config/` remains the single top-level home for configurable YAML assets
- responsibility-based subfolders are the new canonical layout
- prompt text remains under `src/fitcv/prompts/templates/`
- CV rendering template remains under `templates/`
- loader compatibility must preserve runtime behavior during migration
- old flat paths may exist temporarily only as fallback compatibility

## Implementation Tasks

### Task 1: Create The New Config Subfolder Layout

### Goal

Introduce the target directory structure without changing semantics.

### Targets

- `config/runtime/`
- `config/policy/`
- `config/taxonomy/`

### Work

- create the new subfolders
- place the current YAML files into their new target paths
- keep file contents unchanged initially where possible

### Output

- the new responsibility-based config room exists on disk

### Task 2: Relocate Existing Config Files

### Goal

Move the current flat config files into the right responsibility subfolders.

### Mapping

- `config/pipeline.yaml` → `config/runtime/pipeline.yaml`
- `config/prompts.yaml` → `config/runtime/prompts.yaml`
- `config/ranking.yaml` → `config/policy/ranking.yaml`
- `config/cv_analysis.yaml` → `config/policy/cv_analysis.yaml`
- `config/cv.yaml` → `config/policy/cv.yaml`
- `config/taxonomy.yaml` → `config/taxonomy/taxonomy.yaml`
- `config/skill_synonyms.yaml` → `config/taxonomy/skill_synonyms.yaml`
- `.env.yaml` stays supported, while canonical source-of-truth becomes `config/env.yaml`

### Work

- copy or move these files into the new locations
- decide whether `.env.yaml` is retained as runtime entrypoint with `config/env.yaml` as canonical, or whether loader treats both symmetrically during migration

### Output

- all current config files are represented in the new structure

### Task 3: Update Config Loader To Prefer The New Layout

### Goal

Teach the loader the canonical new folder structure while preserving runtime compatibility.

### Targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)

### Work

- update policy/runtime file discovery to load:
  - `config/runtime/pipeline.yaml`
  - `config/runtime/prompts.yaml`
  - `config/policy/ranking.yaml`
  - `config/policy/cv_analysis.yaml`
  - `config/policy/cv.yaml`
  - `config/taxonomy/taxonomy.yaml`
  - `config/taxonomy/skill_synonyms.yaml`
- keep temporary fallback loading from old flat paths if new paths are missing
- keep current key normalization and compatibility projections intact

### Output

- runtime prefers the new config structure with safe fallback support

### Task 4: Keep Admin Settings And Default Hydration Working

### Goal

Ensure settings-default hydration still resolves correctly after config files move.

### Targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

### Work

- verify settings schema still hydrates defaults from loaded config
- adjust any tests or loader assumptions tied to old flat paths
- preserve admin behavior and displayed defaults

### Output

- UI settings continue to reflect the correct baseline config after the folder move

### Task 5: Add Focused Compatibility Coverage

### Goal

Protect the layout migration with tests around path discovery and fallback behavior.

### Targets

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

### Cases

- loader resolves the new subfolder paths correctly
- loader still works during migration when only old flat paths exist
- settings defaults still hydrate from the loaded config
- prompt ids and policy config still resolve unchanged after file moves

### Output

- confidence that the folder move is structural, not behavioral

### Task 6: Update Docs And Discovery

### Goal

Make the new config-room structure discoverable in source-of-truth docs.

### Targets

- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
- generated docs under `docs/generated/`

### Work

- document the new responsibility-based config structure
- document that prompt text and output templates remain outside config
- update discovery docs so contributors can find the right config room quickly

### Output

- docs match the new layout

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .worktrees\e2e-0\.pytest_tmp .worktrees\e2e-0\tests\test_config.py .worktrees\e2e-0\tests\test_fitcv_cp\test_settings_schema.py
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv_cp\settings_schema.py
```

If loader path rules change significantly, run a broader config-using slice too.

## Risks

- old-path fallback may hide incomplete migration if left in place too long
- scripts or docs outside the loader may still point at the flat paths
- environment-path handling for `.env.yaml` vs `config/env.yaml` needs a clear canonical rule
- generated docs can drift if not refreshed

## Rollout Order

1. create new config subfolders
2. relocate files
3. update loader to prefer new paths with fallback
4. verify settings hydration and tests
5. sync docs and generated discovery
6. later remove fallback compatibility once the new layout is stable

## Done Criteria

- the repo has the new responsibility-based config subfolder structure
- the loader prefers the new layout
- compatibility fallback preserves runtime behavior during migration
- settings UI/default hydration still works
- docs clearly explain where runtime, policy, and taxonomy settings live
- focused verification passes for config loading and settings default hydration
