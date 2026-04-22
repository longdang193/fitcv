---
layer: change
artifact_type: plan
status: active
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/project-adoption-migration-guide.md
  - docs/features/*/feature.source.yaml
  - docs/generated/
  - repo_config/adoption-mode.yaml
  - repo_config/publication-config.json
  - README.md
  - docs/pipeline.md
  - docs/usage.md
related_features: []
related_stages: []
---

# Architecture Metadata Cleanup Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-19-05-architecture-metadata-cleanup-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** active

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Align the repo's metadata toolchain and current docs to the newer starter-style Mode B contract by adding truthful function-level capability support, requiring explicit stage participation, normalizing generated contract strings, and replacing the older generated discovery suite with the new canonical generated folder outputs.

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Upgrade the metadata generator, validator, source files, and generated discovery surfaces so the repo follows the newer Mode B cleanup guidance from `project-OS-starter`.  
Reasoning: The repo already has managed feature folders and evidence-oriented lineage, but it still carries structural drift in capability ownership granularity, stage participation handling, generated string formatting, and generated discovery outputs.  
Invariants:

- `feature.source.yaml` stays the human-owned semantic source.
- generated contracts and lineage remain generator-owned.
- file-level `@meta` remains valid ownership metadata.
- function-level `@capability` is additive and selective, not a blanket replacement for file-level metadata.
- explicit `stage_participation` becomes required in feature sources, but `[]` remains valid for intentionally stage-agnostic features.
- `docs/generated/architecture_dag.yaml` and `docs/generated/capability_lineage.yaml` become the only canonical generated discovery targets.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-19-05-architecture-metadata-cleanup-spec.md`
- `..\project-OS-starter\docs\operating_system\project-adoption-migration-guide.md`
- `..\project-OS-starter\docs\operating_system\feature-lifecycle.md`
- `..\project-OS-starter\docs\architecture_templates\python-capability.py.template`

Affected stages:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `admin_control_plane_core`
- `bounded_parallel_enrichment`
- `multi_file_job_input`
- `pipeline_performance`
- `run_lifecycle_controls`
- `settings_system`
- `ui_consistency_theming`

Primary lens: `cross-cutting`

Affected docs:

- feature_source:
  - `docs/features/*/feature.source.yaml`
- feature_yaml:
  - `docs/features/*/<feature_id>.yaml`
- feature_lineage:
  - `docs/features/*/lineage.generated.yaml`
- feature_history: `none`
- stage_source:
  - `docs/stages/*.source.yaml`
- stage_contract:
  - `docs/stages/*.yaml`
- feature_docs: `none`
- cross_cutting_docs:
  - `README.md`
  - `docs/pipeline.md`
  - `docs/usage.md`
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- readme: `README.md`
- generated:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`

Generated refresh required: `yes`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `no`  
Plan needed: `yes`

## File Map

Files to create:

- `docs/superpowers/plans/2026-04-22-20-20-architecture-metadata-cleanup-plan.md`
- `docs/operating_system/project-adoption-migration-guide.md`

Files to modify:

- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- `docs/operating_system/feature-lifecycle.md`
- `docs/features/admin_control_plane_core/feature.source.yaml`
- `docs/features/bounded_parallel_enrichment/feature.source.yaml`
- `docs/features/multi_file_job_input/feature.source.yaml`
- `docs/features/pipeline_performance/feature.source.yaml`
- `docs/features/run_lifecycle_controls/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/ui_consistency_theming/feature.source.yaml`
- `repo_config/adoption-mode.yaml`
- `repo_config/publication-config.json`
- `README.md`
- `docs/pipeline.md`
- `docs/usage.md`

Generated outputs to refresh:

- `docs/features/*/<feature_id>.yaml`
- `docs/features/*/lineage.generated.yaml`
- `docs/stages/*.yaml`
- `docs/generated/architecture_dag.yaml`
- `docs/generated/capability_lineage.yaml`

Files to delete through generator-backed cleanup:

- `docs/generated/features_index.yaml`
- `docs/generated/feature_dependency_graph.yaml`
- `docs/generated/feature_capabilities_index.yaml`
- `docs/generated/feature_overview.md`
- `docs/generated/features_by_status.yaml`
- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`

## Batch 1: Generator And Validator Upgrade

1. Add generator support for function-level Python `@capability <feature_id.capability-slug>` markers using bounded docstring parsing.
2. Keep file-level `@meta capabilities:` support intact.
3. Prefer files containing function-level `@capability` markers as direct code evidence before falling back to broader file-level ownership metadata.
4. Add validator checks that:
   - unknown `@capability` IDs fail validation
   - malformed `@capability` markers fail validation
   - file-level `@meta` remains required where already required
5. Replace the older generated discovery suite with:
   - `docs/generated/architecture_dag.yaml`
   - `docs/generated/capability_lineage.yaml`
6. Update the generator so write mode removes the superseded generated discovery files and check mode reports them as stale drift when present.
7. Add or update generator and validator tests for:
   - valid function-level capability ownership
   - unknown `@capability`
   - new generated discovery files
   - stale legacy generated outputs

## Batch 2: Source And Contract Cleanup

1. Normalize generated `summary`, capability `statement`, and invariant `statement` text before YAML emission:
   - trim trailing whitespace
   - trim trailing blank lines
   - collapse single-paragraph generated strings into clean scalar output where YAML allows
2. Make `stage_participation` required in `feature.source.yaml`.
3. Add validator checks that:
   - the key must exist
   - every `stage_id` exists in `docs/stages/*.source.yaml`
   - every listed `capability_id` belongs to the owning feature
4. Backfill explicit `stage_participation` into the currently missing feature sources:
   - use meaningful stage mappings for stage-aware features
   - use explicit `[]` only for intentionally stage-agnostic repo surfaces
5. Add focused tests for:
   - missing `stage_participation`
   - invalid stage references
   - invalid capability references
   - normalized generated string formatting

## Batch 3: Docs, Repo Config, And Final Sync

1. Add a repo-local `docs/operating_system/project-adoption-migration-guide.md` that records the current starter-aligned Mode B contract for this repo, especially:
   - evidence-oriented lineage
   - selective function-level `@capability`
   - explicit `stage_participation`
   - canonical generated discovery under `docs/generated/`
2. Update `docs/operating_system/feature-lifecycle.md` to match the cleanup decisions.
3. Update current repo-facing navigation/config surfaces to the new generated outputs:
   - `README.md`
   - `docs/pipeline.md`
   - `docs/usage.md`
   - `repo_config/publication-config.json`
   - `repo_config/adoption-mode.yaml`
4. Refresh generated outputs from source.
5. Run the full validation suite and fix any remaining drift before closeout.

## Verification

Run after implementation:

```powershell
python scripts/sync_architecture_docs.py
python scripts/sync_architecture_docs.py --check
python scripts/validate_adoption_shape.py
.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py
git diff --check
```

## Completion Checklist

- intent docs updated? `not needed`
- operating-system docs updated? `yes`
- stage sources updated? `no`
- stage contracts updated? `yes, regenerated`
- feature sources updated? `yes`
- contract updated? `yes, regenerated`
- feature lineage updated? `yes, regenerated`
- feature history updated? `not needed`
- other feature-specific docs updated? `not needed`
- cross-cutting docs updated? `yes`
- agent memory updated or explicitly not needed? `not needed unless execution reveals a reusable invariant`
- README updated? `yes`
- generated docs refreshed? `yes`
