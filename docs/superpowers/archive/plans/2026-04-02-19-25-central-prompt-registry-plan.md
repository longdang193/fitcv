---
feature_type: add
feature_name: prompt_management
status: completed
summary: "Implement a shared prompt registry and template layer for LLM-backed stages, starting with enrich and prompt provenance."
---

# Central Prompt Registry Implementation Plan

## Scope

Implement the prompt-management design defined in [2026-04-02-19-10-central-prompt-registry-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/superpowers/specs/2026-04-02-19-10-central-prompt-registry-spec.md).

This rollout introduces a shared prompt registry and template system for LLM-backed stages while keeping stage business logic, schemas, parsing, and validation inside the existing stage modules.

Phase 1 is intentionally narrow:

- introduce the prompt registry package
- migrate the `enrich` extraction prompt into the registry
- persist enrich prompt provenance into inspection surfaces
- add config-based prompt selection for the enrich path

This plan does not:

- migrate `ai_score` in phase 1
- migrate `cv_generation` in phase 1
- build a UI prompt editor
- centralize stage response schemas in phase 1
- store full rendered prompt bodies in BigQuery by default

## Source-of-Truth Alignment

Affected current-state docs:

- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/cv_system/cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/cv_system/cv_system.yaml)
- [docs/features/pipeline_performance/pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/pipeline_performance/pipeline_performance.yaml)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)

Affected history docs:

- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/history.md)
- [docs/features/cv_system/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/cv_system/history.md)
- [docs/features/pipeline_performance/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/pipeline_performance/history.md)

Affected code and tests:

- [src/fitcv/prompts](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/prompts)
- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/config.py)
- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [src/fitcv/ai_score.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/ai_score.py)
- [src/fitcv/cv_generator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/cv_generator.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_config.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)
- new prompt-registry tests as needed

Generated refresh required:

- [docs/generated/feature_overview.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/generated/feature_overview.md)
- [docs/generated/features_index.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/generated/features_index.yaml)

## Invariants

- Stage business logic remains in stage modules.
- Prompt text, prompt metadata, and prompt rendering move into the shared prompt layer.
- Prompt selection must be explicit and reproducible via stable IDs and versions.
- Inspection surfaces must be able to show which effective prompt definition a run used.
- Phase 1 must not change enrich extraction semantics except where prompt text parity is intentionally preserved.

## Implementation Tasks

### Task 1: Add the Prompt Registry Package and Core Data Model

Create the shared prompt package and the minimum registry/loader/renderer contract.

Primary files:

- [src/fitcv/prompts](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/prompts)
- [tests](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests)

Acceptance criteria:

- the repo has a dedicated `fitcv.prompts` package
- prompt definitions can be looked up by `prompt_id`
- prompt definitions expose metadata such as stage, template path, and version
- the rendering path validates required inputs before returning rendered text

### Task 2: Move the Enrich Extraction Prompt Into a Versioned Template

Extract the current enrich prompt body from `enrich.py` into the prompt registry without changing the enrich schema or post-processing contract.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- prompt template file under [src/fitcv/prompts/templates](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/prompts/templates)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)

Acceptance criteria:

- `enrich` no longer owns the large inline prompt body
- `enrich` renders its extraction prompt through the prompt registry
- existing structured-output and fallback behavior still works
- the enrich prompt remains behaviorally equivalent at rollout time

### Task 3: Add Config-Based Prompt Selection for Enrich

Add the prompt-selection config contract for the enrich path and validate it through the central config loader.

Primary files:

- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/config.py)
- supporting config files if needed
- [tests/test_config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_config.py)

Acceptance criteria:

- config can specify the effective prompt ID for enrich extraction
- missing or unknown prompt IDs fail validation clearly
- default config behavior remains backward compatible when no new prompt config is provided

### Task 4: Persist Enrich Prompt Provenance Into Inspection Surfaces

Record which effective enrich prompt definition was used and expose that in settings-used and stage-level inspection/debug outputs.

Primary files:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- any run-settings or stage-artifact persistence surfaces involved
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)

Acceptance criteria:

- run inspection can show enrich prompt ID and version
- the recorded provenance includes model name
- prompt provenance is tied to the effective prompt used, not just a static default

### Task 5: Add Registry and Render Tests

Cover the new prompt-management layer with focused tests so prompt lookup, rendering, and enrich integration do not drift silently.

Primary files:

- prompt-registry tests under [tests](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_config.py)

Acceptance criteria:

- prompt lookup by ID is covered by tests
- template rendering with required variables is covered by tests
- enrich integration still produces prompt text through the registry path
- config validation for prompt IDs is covered by tests

### Task 6: Sync Docs and History for the New Prompt Layer

Update the affected docs so the new prompt-management contract is discoverable and accurately scoped.

Primary files:

- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/history.md)
- [docs/features/cv_system/cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/cv_system/cv_system.yaml)
- [docs/features/cv_system/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/cv_system/history.md)
- [docs/features/pipeline_performance/pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/pipeline_performance/pipeline_performance.yaml)
- [docs/features/pipeline_performance/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/pipeline_performance/history.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)

Acceptance criteria:

- docs explain that prompt text is centrally managed while schemas remain stage-local
- enrich-stage docs mention prompt provenance visibility
- cross-cutting pipeline docs mention the prompt registry as shared infrastructure

### Task 7: Define Phase 2 and Phase 3 Follow-On Slices Without Implementing Them

Record the next migration steps for `ai_score` and `cv_generation` so phase 1 does not become a one-off enrich-only special case.

Primary files:

- this plan
- affected history docs if needed

Acceptance criteria:

- phase 2 target is explicitly `ranking.ai_score`
- phase 3 target is explicitly `cv_generation`
- rollout sequencing and non-goals remain clear after phase 1 lands

## Execution Order

1. Complete Task 1 first so the registry contract exists before stage migration starts.
2. Complete Task 2 next so `enrich` becomes the first real consumer.
3. Complete Task 3 after the registry is live so config selection validates against a real registry.
4. Complete Tasks 4 and 5 together so provenance and tests land with the new path.
5. Complete Task 6 after behavior is implemented.
6. Complete Task 7 last as documented follow-on scope.

## Verification Plan

Planned targeted verification after implementation:

```powershell
python -m pytest -q tests\test_config.py -k "prompt"
```

```powershell
python -m pytest -q tests\test_enrich.py -k "prompt or extraction"
```

```powershell
python -m pytest -q tests\test_pipeline.py -k "prompt or settings_used or enrich"
```

```powershell
python -m py_compile src\fitcv\config.py src\fitcv\enrich.py src\fitcv\pipeline.py src\fitcv\prompts\registry.py src\fitcv\prompts\loader.py src\fitcv\prompts\renderer.py
```

Manual verification checklist:

- trigger an enrich run and confirm the stage still produces valid structured output
- inspect settings-used or stage-artifact outputs and confirm prompt ID/version/model provenance is present
- change the enrich prompt ID in config to a valid alternate definition and confirm the new prompt path is selected
- set an invalid prompt ID and confirm config validation fails clearly

## Risks and Mitigations

### Prompt Parity Risk

Risk:

- moving prompt text out of `enrich.py` could accidentally change behavior during the migration

Mitigation:

- move the current prompt text with minimal semantic change first
- keep the enrich schema and parsing path unchanged in phase 1
- compare old and new rendered content in focused tests where practical

### Over-Centralization Risk

Risk:

- the prompt layer could become a dumping ground for stage logic instead of a clean template/metadata layer

Mitigation:

- keep schemas, parsing, and post-processing in stage modules
- centralize only prompt text, metadata, selection, and rendering

### Partial Migration Drift Risk

Risk:

- phase 1 may leave `ai_score` and `cv_generation` on older inline prompt paths for a while

Mitigation:

- keep the registry naming and config contract stage-generic from day one
- explicitly document phase 2 and phase 3 migration slices

## Done Definition

The phase-1 work is complete when:

- the repo has a shared prompt registry package
- `enrich` uses the registry instead of a large inline prompt body
- enrich prompt selection is config-driven and validated
- enrich prompt provenance is visible in run inspection surfaces
- targeted tests for registry/config/enrich integration pass
- docs describe the new prompt-management contract clearly

## Task Status

Status: completed

- [x] Task 1: Add the prompt registry package and core data model
- [x] Task 2: Move the enrich extraction prompt into a versioned template
- [x] Task 3: Add config-based prompt selection for enrich
- [x] Task 4: Persist enrich prompt provenance into inspection surfaces
- [x] Task 5: Add registry and render tests
- [x] Task 6: Sync docs and history for the new prompt layer
- [x] Task 7: Define phase 2 and phase 3 follow-on slices without implementing them
- [x] Run targeted verification
- [x] Update plan status after implementation
