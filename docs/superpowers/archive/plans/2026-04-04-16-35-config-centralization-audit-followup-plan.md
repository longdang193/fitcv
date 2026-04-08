---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Centralize remaining shared prompts, policy knobs, defaults, and contract constants to reduce config drift across code, YAML, and admin surfaces."
---

# Config Centralization Audit Follow-Up Plan

## Summary

Implement the config-centralization follow-up in a staged, low-risk order:

- centralize remaining prompt ownership
- deduplicate baseline defaults between YAML and admin schema
- extract `cv_analysis` policy knobs into declarative config
- centralize schema/version constants and shared channel semantics

The goal is to reduce drift without replacing the current config system wholesale.

## Scope

This plan covers:

- prompt-registry expansion for `ranking` and `cv_generation`
- prompt-id config accessors and prompt provenance alignment
- deduplication of YAML defaults vs admin settings schema defaults
- extraction of `cv_analysis` evidence-selection policy into config
- one shared code-owned contract/version module
- one shared analysis-channel semantics contract
- doc and generated discovery sync

This plan does not cover:

- making every prompt admin-editable
- rewriting the whole config loader architecture
- declarative reimplementation of ranking or evidence-retrieval algorithms
- whole-project config file renaming unless needed for the chosen rollout

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/ranking.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code and config targets:

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [pipeline.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/pipeline.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/ranking.yaml)
- [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/cv.yaml)
- `config/cv_analysis.yaml` (new)
- `config/prompts.yaml` (new or expanded prompt-id owner)
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- `src/fitcv/prompts/templates/*.md`
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- `src/fitcv/contracts.py` or `src/fitcv/schema_versions.py` (new)

Primary tests:

- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_ai_score.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_evidence.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

Generated refresh required:

- yes

## Invariants

- Configuration stays separated by responsibility rather than collapsing into one catch-all file.
- YAML remains the source of baseline runtime and policy defaults.
- Prompt content lives in one prompt-registry path once migrated.
- Settings metadata remains admin-focused and must not become a competing default store.
- Stage-owned policy stays stage-owned even after moving values into config.
- Contract/version constants stay code-owned and importable without loading YAML.

## Implementation Tasks

### Task 1: Expand Prompt Registry Coverage

### Goal

Move remaining primary prompt text out of stage modules and into the shared prompt registry.

### Code targets

- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- `src/fitcv/prompts/templates/ranking_ai_score_v1.md`
- `src/fitcv/prompts/templates/cv_generation_write_v1.md`
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)

### Work

- add prompt ids for:
  - `ranking.ai_score.v1`
  - `cv_generation.write.v1`
- move long prompt prose from code into template files
- keep stage-specific data assembly in code
- add prompt-id accessors in config
- align prompt provenance so these stages expose prompt id/version/template path consistently

### Output

- registry-backed prompt ownership for `enrich`, `ranking`, and `cv_generation`

### Task 2: Deduplicate Settings Defaults Against YAML

### Goal

Make YAML the only source of baseline defaults while keeping admin metadata and validation in the settings schema.

### Code targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/settings.html)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

### Work

- add a config-backed default resolver for settings paths
- remove duplicated baseline defaults where the path is already required in YAML
- keep explicit metadata for:
  - type
  - label
  - description
  - options
  - validation
- preserve optional fallback defaults only where config keys are intentionally absent

### Output

- one baseline default source for runtime/admin settings

### Task 3: Extract `cv_analysis` Policy Into Dedicated Config

### Goal

Move stage-tuning policy from `evidence.py` constants into a stage-owned config slice.

### Code targets

- `config/cv_analysis.yaml`
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py) if any extracted keys should be admin-editable
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_evidence.py)

### Work

- create a dedicated `cv_analysis` policy block for:
  - channel selection weights
  - evidence-type quotas
  - selection bonuses / penalties
  - residual weighting factors
- load and validate the new config
- refactor evidence selection to consume policy from config
- keep local helper math and retrieval flow in code

### Output

- declarative `cv_analysis` policy with fewer tuning constants trapped in code

### Task 4: Centralize Contract and Schema Version Constants

### Goal

Move scattered contract/schema literals into one code-owned module.

### Code targets

- `src/fitcv/contracts.py` or `src/fitcv/schema_versions.py`
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [enrich.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/enrich.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/embeddings.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)

### Work

- define one module for:
  - schema versions
  - contract versions
  - shared artifact schema ids
  - maybe shared channel ids if reused
- refactor modules to import from the new source
- keep these constants code-owned, not YAML-owned

### Output

- one discoverable source for runtime contract/version identifiers

### Task 5: Centralize Shared Accessors and Channel Semantics

### Goal

Reduce repeated key traversal, fallback model names, and duplicated channel meaning.

### Code targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [enrich.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/enrich.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/embeddings.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)

### Work

- add shared accessors such as:
  - `get_gemini_model`
  - `get_embedding_model`
  - `get_ranking_prompt_id`
  - `get_cv_generation_prompt_id`
- add one shared analysis-channel contract for:
  - channel ids
  - display labels
  - intended usage
- refactor `cv_analysis` and `cv_generation` to use the shared channel contract

### Output

- less repeated fallback logic
- less semantic drift between retrieval and writing

### Task 6: Add Focused Regression Coverage

### Goal

Protect the centralization refactor with narrow tests around defaults, prompts, and policy loading.

### Test targets

- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_ai_score.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_evidence.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

### Cases

- prompt ids resolve correctly for `ranking` and `cv_generation`
- prompt provenance remains stable after prompt extraction
- settings defaults resolve from loaded config instead of duplicated schema literals
- `cv_analysis` policy values load from config and preserve existing behavior
- contract/version constants are imported from the new shared module
- shared channel semantics remain aligned between evidence selection and CV writing

### Task 7: Sync Feature, Stage, and Generated Docs

### Goal

Update source-of-truth docs to match the new centralization contract.

### Doc targets

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/settings_system/settings_system.yaml`
- `docs/features/settings_system/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/stages/ranking.yaml`
- `docs/stages/cv_analysis.yaml`
- `docs/stages/cv_generation.yaml`
- `docs/FitCV-pipeline.md`
- `docs/generated/feature_overview.md`
- `docs/generated/features_index.yaml`
- `docs/generated/feature_capabilities_index.yaml`

### Work

- document expanded prompt registry ownership
- document config-backed admin defaults
- document new `cv_analysis` policy config slice
- document centralized contract/version ownership
- document shared analysis-channel semantics if they become part of stage/feature contracts

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_ai_score.py .worktrees\e2e-0\tests\test_cv_generator.py .worktrees\e2e-0\tests\test_evidence.py .worktrees\e2e-0\tests\test_fitcv_cp\test_settings_schema.py
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_pipeline.py .worktrees\e2e-0\tests\test_fitcv_cp\test_app.py -k "prompt or settings or cv_analysis"
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv\ai_score.py .worktrees\e2e-0\src\fitcv\cv_generator.py .worktrees\e2e-0\src\fitcv\evidence.py .worktrees\e2e-0\src\fitcv\pipeline.py .worktrees\e2e-0\src\fitcv_cp\settings_schema.py
```

If new prompt templates or config files are added, include focused tests for those loaders too.

## Risks

- prompt extraction may alter wording-sensitive behavior if migrated too aggressively
- removing duplicated defaults may expose hidden assumptions in the admin UI or tests
- moving `cv_analysis` policy into config can create noisy config if too many low-level knobs are exposed
- centralizing channel semantics may require careful compatibility handling for existing artifacts

## Rollout Order

1. prompt registry expansion
2. settings default deduplication
3. `cv_analysis` policy extraction
4. shared contract/version module
5. shared accessors and channel semantics
6. docs and generated sync

## Done Criteria

- `enrich`, `ranking`, and `cv_generation` share one prompt-registry path for primary prompt content
- admin settings no longer duplicate baseline defaults already owned by config YAML
- `cv_analysis` stage-policy knobs intended for tuning are config-backed
- shared model/prompt accessors exist and are used by stage modules
- schema/version constants are centralized in one code-owned module
- retrieval and generation share one analysis-channel contract
