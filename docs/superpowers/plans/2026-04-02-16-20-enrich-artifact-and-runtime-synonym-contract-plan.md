---
feature_type: modify
feature_name: none
status: completed
summary: "Implement full enrich-stage artifact visibility, durable synonym suggestion persistence, runtime synonym overlays, and one effective merged map shared across downstream stages."
---

# Enrich Artifact And Runtime Synonym Contract Implementation Plan

## Scope

Implement the design in [2026-04-02-16-05-enrich-artifact-and-runtime-synonym-contract-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/superpowers/specs/2026-04-02-16-05-enrich-artifact-and-runtime-synonym-contract-spec.md).

This rollout does:

- make enrich-stage sampled rows include all enrich fields present on sampled jobs
- persist `mapping_suggestions` for later review
- add a runtime synonym overlay layer on top of the base `skill_synonyms.yaml`
- propagate one effective merged synonym map across synonym-aware stages in a run
- expose enough runtime metadata to debug which synonym sources influenced a run

This rollout does not:

- auto-promote suggestions into the trusted base synonym YAML
- build a full admin editing UI for synonym review in phase 1
- redesign the canonical-skill ontology beyond the current synonym map model
- replace the base `config/skill_synonyms.yaml` file

## Source-of-Truth Alignment

Affected cross-cutting docs:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/rule_filter.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)

Affected code and config:

- [config/skill_synonyms.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/config/skill_synonyms.yaml)
- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/config.py)
- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [src/fitcv/rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/rule_filter.py)
- [src/fitcv/ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/ranking.py)
- [src/fitcv/gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/gap_analysis.py)
- [src/fitcv/validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/validator.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/models.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/run_detail.html)

Affected tests:

- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_rule_filter.py)
- [tests/test_ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_ranking.py)
- [tests/test_gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_gap_analysis.py)
- [tests/test_validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_validator.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_bq_store.py)

Generated refresh required:

- none

## Invariants

- Enrich-stage artifact rows must expose the full enrich output contract for sampled rows.
- Suggested mappings remain durable review artifacts and do not auto-update the trusted base map.
- The base synonym YAML remains the stable default layer.
- Runtime overlays can augment or override the base map for later stages.
- A single run uses one effective merged synonym map across synonym-aware stages.

## Implementation Tasks

### Task 1: Expand Enrich-Stage Sample Rows To Include All Enrich Fields

Update the stage-artifact sampler so enrich-stage `outputs_sample` rows include every enrich field present on the sampled row rather than a small legacy subset.

Primary files:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)

Acceptance criteria:

- enrich-stage sample rows show all enrich fields present on sampled jobs
- canonical companion fields appear when present
- `required_skill_entities` and `mapping_suggestions` are visible in enrich-stage sample rows
- stage artifact downloads remain bounded by row sample count rather than by aggressive field omission

### Task 2: Formalize Suggestion Record Shape And Persistence

Make `mapping_suggestions` a durable persisted artifact rather than a transient in-memory enrich detail.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/models.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- BigQuery assets or migration scripts as needed
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_bq_store.py)

Acceptance criteria:

- each suggestion follows the agreed shape with fields such as `must_have_skill`, `matches`, `confidence`, `alias`, and `canonical`
- run-scoped suggestions are persisted and reloadable
- stage artifacts can show the persisted suggestion content for sampled rows

### Task 3: Add Aggregate Suggestion Export For Review

Add a reviewable aggregate export that groups suggestions across runs so repeated aliases can be evaluated for promotion.

Primary files:

- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/run_detail.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- a run-level suggestion export is downloadable
- an aggregate suggestion export can summarize repeated alias-to-canonical candidates
- aggregate records include counts, confidence summaries, and conflict visibility

### Task 4: Add Runtime Synonym Overlay Loading In Config Resolution

Teach config loading to merge the trusted base synonym YAML with one or more explicit overlay sources.

Primary files:

- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/config.py)
- [config/skill_synonyms.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/config/skill_synonyms.yaml)
- overlay config assets or docs as needed
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_rule_filter.py)
- [tests/test_ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_ranking.py)

Acceptance criteria:

- runtime config can load a base map plus overlay map
- later layers override earlier entries on key collision
- absence of an overlay preserves current behavior

### Task 5: Propagate One Effective Synonym Map Across All Synonym-Aware Stages

Ensure the same merged map is used consistently across enrich and downstream stages in the same run.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [src/fitcv/rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/rule_filter.py)
- [src/fitcv/ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/ranking.py)
- [src/fitcv/gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/gap_analysis.py)
- [src/fitcv/validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/validator.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [tests/test_gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_gap_analysis.py)
- [tests/test_validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_validator.py)

Acceptance criteria:

- enrich, rule filter, ranking, gap analysis, and validator all consume the same effective map
- stage-to-stage synonym behavior is consistent within a run
- no stage falls back to an unmerged base-only map when an overlay is active

### Task 6: Expose Effective-Map Provenance In Run Inspection

Record and surface which synonym sources were used so debugging can explain why a particular mapping decision happened.

Primary files:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/models.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- a run can report whether base-only or base-plus-overlay synonym resolution was used
- run inspection can expose enough metadata to audit the effective map source
- exported artifacts are sufficient to explain which synonym layer influenced a result

### Task 7: Sync Cross-Cutting Docs And Stage Contracts

Update the pipeline and stage docs to reflect the new enrich visibility and runtime synonym lifecycle.

Primary files:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)

Acceptance criteria:

- enrich docs state that sampled enrich rows expose the full enrich contract
- downstream docs describe use of the effective merged synonym map
- docs distinguish base synonyms, overlay synonyms, and suggestion persistence clearly

## Execution Order

1. Complete Task 1 first so enrich-stage visibility matches the actual enrich contract.
2. Complete Task 2 next so suggestion persistence exists before aggregate exports or overlay governance depend on it.
3. Complete Task 3 after persistence so review exports have stable source data.
4. Complete Task 4 before broader propagation so the runtime overlay contract is explicit.
5. Complete Task 5 after config loading supports overlays.
6. Complete Task 6 once the effective map is stable and traceable.
7. Complete Task 7 last so docs reflect implemented behavior.

## Verification Plan

Targeted verification should cover:

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_pipeline.py -k "enrich_sample or stage_transition"
```

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_enrich.py -k "canonical or mapping"
```

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_rule_filter.py tests\test_ranking.py tests\test_gap_analysis.py tests\test_validator.py -k "skill or canonical or synonym"
```

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_fitcv_cp\test_bq_store.py tests\test_fitcv_cp\test_app.py -k "stage_artifact or mapping or synonym"
```

Manual verification checklist:

- trigger a run and confirm enrich-stage artifact samples show the full enrich field set for sampled rows
- confirm `required_skill_entities` and `mapping_suggestions` are visible in the enrich-stage artifact
- confirm run-scoped suggestion exports are downloadable after a run
- confirm an approved overlay file changes downstream matching behavior without editing the base YAML
- confirm enrich, rule filter, ranking, and later synonym-aware stages behave consistently under the same overlay

Verification completed in this implementation session:

- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_enrich.py' -k 'mapping_suggestions or canonical_skill_companions'`
- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_pipeline.py' -k 'enrich_sample_keeps_full_list_fields or enrich_sample_includes_canonical_fields'`
- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_fitcv_cp\test_bq_store.py' '.worktrees\Stage-by-stage-flow\tests\test_fitcv_cp\test_app.py' -k 'mapping_suggestions'`
- `python -m py_compile` over the touched Python modules
- repo-local direct overlay load check via `fitcv.config.load_config(...)`

Known verification caveat:

- the dedicated pytest run for `tests/test_config.py -k skill_synonym_overlay_paths` hit a Windows permission issue during pytest temp-dir cleanup, even though the overlay behavior itself was validated directly with a repo-local fixture

## Risks And Mitigations

### Artifact Size Risk

Full enrich rows increase sampled artifact payload size.

Mitigation:

- keep row sampling limits
- keep text truncation for very large strings
- avoid reducing field visibility unless a field is truly empty

### Overlay Drift Risk

Overlay files can make runtime behavior harder to reason about if provenance is hidden.

Mitigation:

- record effective-map provenance in run metadata or artifacts
- make overlay loading explicit and inspectable

### Map Pollution Risk

Persisted suggestions can encourage over-promotion of weak aliases.

Mitigation:

- keep suggestions separate from trusted base config
- make aggregate exports show confidence and conflicts
- keep manual review as the promotion boundary

## Task Status

- [x] Task 1: Expand enrich-stage sample rows to include all enrich fields
- [x] Task 2: Formalize suggestion record shape and persistence
- [x] Task 3: Add aggregate suggestion export for review
- [x] Task 4: Add runtime synonym overlay loading in config resolution
- [x] Task 5: Propagate one effective synonym map across all synonym-aware stages
- [x] Task 6: Expose effective-map provenance in run inspection
- [x] Task 7: Sync cross-cutting docs and stage contracts
