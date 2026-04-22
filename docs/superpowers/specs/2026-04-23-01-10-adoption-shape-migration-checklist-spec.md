---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - scripts/validate_adoption_shape.py
  - tools/docs/generate_architecture_metadata.py
  - scripts/sync_architecture_docs.py
  - docs/features/*/*.yaml
  - docs/stages/*.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - tests/test_validate_adoption_shape.py
  - tests/test_validate_repo_contracts.py
  - repo_config/adoption-mode.yaml
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
  - ranking
  - shortlist
  - cv_analysis
  - cv_generation
---

# Adoption-Shape Migration Checklist

## Summary

Convert the new starter-aligned validator findings into a focused migration
checklist that upgrades JOB-PROJECT's generated architecture surfaces to the
current `project-OS-starter` contract shape.

This is a generator-and-generated-output migration, not a product-behavior
phase. The validator is now close enough to starter to expose the remaining
schema drift truthfully; the next work is to make the generator and generated
artifacts satisfy that contract.

## Problem

JOB-PROJECT now runs a much stricter `scripts/validate_adoption_shape.py`
aligned to the latest local starter baseline. That validator no longer passes
because the repo's generated architecture artifacts still follow an older
contract.

Fresh validator evidence from April 23, 2026:

- `python scripts/validate_adoption_shape.py` exited non-zero with `215` errors
- `.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_validate_repo_config.py tests/test_validate_repo_contracts.py -q`
  failed with `8` failures caused by the same stricter contract
- `python scripts/validate_repo_contracts.py --fast` now fails because the
  adoption-shape gate correctly exposes generator drift

Current error buckets:

- `10` generated feature contracts are missing the full `refs` mapping
- `7` generated stage contracts still use the legacy nested wrapper and miss the
  new top-level fields
- `133` `architecture_dag.yaml` nodes are missing a non-empty `type`
- `30` `capability_lineage.yaml` feature summary fields are missing or wrong

So the repo is no longer blocked on validator drift. It is now blocked on
generator and generated-surface migration.

## Goals

- Upgrade the architecture generator to emit starter-aligned generated feature
  contracts.
- Upgrade generated stage contracts to the newer flat top-level schema.
- Upgrade generated discovery outputs so `architecture_dag.yaml` and
  `capability_lineage.yaml` satisfy the current validator contract.
- Update validation fixtures/tests so local sync and repo-contract tests reflect
  the new generator truth.
- Keep repo-local truths only where they are real:
  - `config/` remains the local runtime config root
  - underscore feature IDs remain intentional
  - the extra adoption-shape gate remains allowed on top of narrower starter
    repo-config validation

## Non-Goals

- Do not change product behavior, UI behavior, or pipeline execution logic.
- Do not rewrite feature/source semantics unless the generator requires small
  source-compatible additions.
- Do not manually hand-edit generated artifacts as a lasting fix; the generator
  must become the source of truth.
- Do not broaden validator rules past what the current starter validator
  already enforces.

## Migration Scope

### Batch A: Generated Feature Contract Shape

Patch the generator so every generated feature contract includes the full
starter-style `refs` mapping:

- `code`
- `tests`
- `specs`
- `plans`
- `docs`
- `configs`
- `components`

This batch currently affects:

- `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- `docs/features/bounded_parallel_enrichment/bounded_parallel_enrichment.yaml`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/multi_file_job_input/multi_file_job_input.yaml`
- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
- `docs/features/settings_system/settings_system.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`

### Batch B: Generated Stage Contract Shape

Patch stage-contract generation so each generated stage contract is emitted in
the current flat top-level contract shape, not the older nested wrapper form.

Each generated stage contract should carry explicit top-level fields such as:

- `stage_id`
- `name`
- `status`
- `purpose`
- `feature_refs`
- `capability_refs`
- `code_refs`
- `test_refs`
- `doc_refs`
- `config_refs`
- `component_refs`

This batch currently affects:

- `docs/stages/cv_analysis.yaml`
- `docs/stages/cv_generation.yaml`
- `docs/stages/enrich.yaml`
- `docs/stages/normalize.yaml`
- `docs/stages/ranking.yaml`
- `docs/stages/rule_filter.yaml`
- `docs/stages/shortlist.yaml`

### Batch C: Generated Discovery Schema

Patch aggregate discovery generation so the following files match the newer
starter contract:

- `docs/generated/architecture_dag.yaml`
  - every node needs a non-empty `type`
- `docs/generated/capability_lineage.yaml`
  - every feature summary needs:
    - `lineage_file`
    - integer `capability_count`
    - list `capabilities`

### Batch D: Fixture And Sync Convergence

Update local validation fixtures and sync expectations so temp repos built by:

- `tests/test_validate_adoption_shape.py`
- `tests/test_validate_repo_contracts.py`

generate the new contract shape and stop failing for repo-generator drift.

This batch also includes any minimal sync-flow updates in:

- `scripts/sync_architecture_docs.py`

if the generator change requires an extra refresh or check step.

## Target State

After this migration:

- `scripts/validate_adoption_shape.py` stays starter-close and passes against
  the real repo
- `scripts/validate_repo_contracts.py --fast` passes again
- generated feature contracts expose complete ref families even when some lists
  are empty
- generated stage contracts use the flat current schema
- generated discovery outputs expose canonical `node.type` and per-feature
  lineage summary fields
- validator fixtures encode the new schema so tests fail only on real regressions

## Acceptance Criteria

- `python scripts/validate_adoption_shape.py` passes
- `python scripts/validate_repo_contracts.py --fast` passes
- `python scripts/sync_architecture_docs.py` passes
- `python scripts/sync_architecture_docs.py --check` passes
- `.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_validate_repo_config.py tests/test_validate_repo_contracts.py -q` passes
- generated feature contracts no longer report missing `refs` keys
- generated stage contracts no longer report legacy nested-wrapper errors
- `docs/generated/architecture_dag.yaml` no longer reports missing node `type`
- `docs/generated/capability_lineage.yaml` no longer reports missing
  `lineage_file`, `capability_count`, or `capabilities`

## Risks

- The generator may currently derive less stage/discovery structure than the new
  contract expects, so some fields may need careful defaulting rather than blind
  backfill.
- If the migration patches generated files directly before patching the
  generator, the repo will drift again on the next sync run.
- Validation fixtures may conceal real gaps if they are updated too loosely
  instead of mirroring the actual generator output.
- The recorded starter baseline in `repo_config/adoption-mode.yaml` is still
  older than the currently reviewed local starter head, so baseline bookkeeping
  may need a follow-up once this migration lands cleanly.

## Suggested Next Step

Turn this spec into a focused implementation plan with four batches executed in
order:

1. feature contract generation
2. stage contract generation
3. generated discovery outputs
4. fixture and sync convergence
