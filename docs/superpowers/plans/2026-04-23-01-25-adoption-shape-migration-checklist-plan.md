---
layer: operating_system
artifact_type: plan
status: active
parent_workstream: none
targets:
  - tools/docs/generate_architecture_metadata.py
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_architecture_metadata_generation.py
  - tests/test_validate_adoption_shape.py
  - tests/test_validate_repo_contracts.py
  - docs/features/*/*.yaml
  - docs/stages/*.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
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

# Adoption-Shape Migration Checklist Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-04-23-01-10-adoption-shape-migration-checklist-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** active

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Upgrade JOB-PROJECT's architecture generator and generated outputs in four bounded batches so the starter-aligned adoption-shape validator passes truthfully.

**Architecture:** The validator is already close to the latest local starter baseline, so the remaining work is generator migration rather than validator negotiation. The generator in `tools/docs/generate_architecture_metadata.py` must become the single source of truth for the newer feature-contract, stage-contract, and generated-discovery schemas, with tests and sync surfaces updated only after the emitted shapes are correct.

**Key Invariants:**
- `scripts/validate_adoption_shape.py` stays starter-close and should not be weakened to make old outputs pass.
- Generated files must be fixed through generator changes, not durable manual edits.
- Repo-local truths remain intact: `config/` stays the runtime config root and underscore feature IDs remain intentional.
- Each batch should reduce one drift bucket without hiding the remaining ones.

**Rollout / Revert:**  
- rollback_trigger: Generator changes cause broader schema regressions outside the intended batch scope.  
- rollback_method: Revert the batch-local generator and test changes, then rerun the prior validation commands to restore the previous baseline.  

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Patch the architecture generator and its fixtures so the current starter-aligned validator can pass without relaxing any of the new generated-contract checks.  
Reasoning: The validator now exposes truthful generator drift across feature contracts, stage contracts, and generated discovery. The right fix is to migrate the generator in bounded batches.  
Invariants:

- The validator remains stricter than the current generator until each batch lands.
- Batch A only addresses generated feature-contract `refs` shape.
- Stage and discovery migrations remain separate batches so failures stay attributable.
- Sync and repo-contract checks should only be widened after their underlying generator batch is complete.

Dependencies:

- `docs/superpowers/specs/2026-04-23-01-10-adoption-shape-migration-checklist-spec.md`
- latest local `project-OS-starter` validator baseline already reviewed on April 23, 2026
- current generator: `tools/docs/generate_architecture_metadata.py`

Affected stages:

- `normalize`
- `enrich`
- `rule_filter`
- `ranking`
- `shortlist`
- `cv_analysis`
- `cv_generation`

Affected features:

- none

Primary lens: `cross-cutting`

Affected docs:

- feature_source: `none`
- feature_yaml: `docs/features/*/<feature_id>.yaml`
- feature_lineage: `docs/features/*/lineage.generated.yaml`
- feature_history: `docs/features/*/history.md`
- stage_source: `docs/stages/*.source.yaml`
- stage_contract: `docs/stages/*.yaml`
- feature_docs: `none`
- cross_cutting_docs: `none`
- readme: `none`
- generated:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`

Generated refresh required: `yes`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `no`  
Plan needed: `yes`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `docs/features/*/<feature_id>.yaml`
- Feature lineage: `docs/features/*/lineage.generated.yaml`
- Stage source: `docs/stages/*.source.yaml`
- Stage contracts: `docs/stages/*.yaml`
- Feature history: `docs/features/*/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `none`
- README: `none`
- Generated discovery:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`

## File Map

Files to modify:

- `tools/docs/generate_architecture_metadata.py`
- `tests/test_architecture_metadata_generation.py`
- `tests/test_validate_adoption_shape.py`
- `tests/test_validate_repo_contracts.py`
- `scripts/sync_architecture_docs.py` if a batch requires sync-step adjustment

Files to regenerate:

- `docs/features/*/<feature_id>.yaml`
- `docs/features/*/lineage.generated.yaml`
- `docs/features/*/history.md` if timeline rendering changes
- `docs/stages/*.yaml`
- `docs/generated/architecture_dag.yaml`
- `docs/generated/capability_lineage.yaml`

## Task 1: Batch A - Generated Feature Contract Refs

**Files:**
- Modify: `tools/docs/generate_architecture_metadata.py`
- Test: `tests/test_architecture_metadata_generation.py`
- Docs: `docs/features/*/<feature_id>.yaml`

- [ ] Step 1: Patch feature-contract ref generation so every generated feature contract emits `refs.code`, `refs.tests`, `refs.specs`, `refs.plans`, `refs.docs`, `refs.configs`, and `refs.components`.
- [ ] Step 2: Aggregate those refs truthfully from capability-linked evidence, feature-linked spec/plan docs, and feature history/doc ownership.
- [ ] Step 3: Add or update generator tests to assert the new `refs` shape directly.
- [ ] Step 4: Run the generator and refresh generated feature contracts.
- [ ] Step 5: Re-run focused checks and confirm the old “feature contract refs missing required keys” bucket disappears while stage/discovery errors remain for later batches.

## Task 2: Batch B - Generated Stage Contract Shape

**Files:**
- Modify: `tools/docs/generate_architecture_metadata.py`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: `docs/stages/*.yaml`

- [ ] Step 1: Patch stage-contract generation to emit the flat top-level schema.
- [ ] Step 2: Keep `stage_id`, `name`, `status`, `purpose`, and all ref-family keys explicit.
- [ ] Step 3: Update stage-shape fixtures/tests to match the new generator output.
- [ ] Step 4: Regenerate stage contracts and verify the legacy nested-wrapper errors disappear.

## Task 3: Batch C - Generated Discovery Schema

**Files:**
- Modify: `tools/docs/generate_architecture_metadata.py`
- Test: `tests/test_validate_adoption_shape.py`
- Docs:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`

- [ ] Step 1: Patch `architecture_dag.yaml` generation so every node includes a non-empty `type`.
- [ ] Step 2: Patch `capability_lineage.yaml` generation so every feature summary includes `lineage_file`, integer `capability_count`, and list `capabilities`.
- [ ] Step 3: Update tests to assert the new discovery shape directly.
- [ ] Step 4: Regenerate discovery files and verify the discovery-schema errors disappear.

## Task 4: Batch D - Fixture And Sync Convergence

**Files:**
- Modify: `tests/test_validate_adoption_shape.py`
- Modify: `tests/test_validate_repo_contracts.py`
- Modify: `scripts/sync_architecture_docs.py` if required

- [ ] Step 1: Update temp-repo fixtures so sync-generated outputs match the migrated contract.
- [ ] Step 2: Keep fixtures as close as possible to real generator output instead of hand-shaped exceptions.
- [ ] Step 3: Adjust sync or repo-contract test expectations only where the migrated generator changes the truthful output contract.

## Task 5: Verification

- [ ] Step 1: Run Batch A-focused generator tests.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 3: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 4: Run `python scripts/validate_repo_contracts.py --fast`.
- [ ] Step 5: Run `.venv\Scripts\python.exe -m pytest tests/test_architecture_metadata_generation.py tests/test_validate_adoption_shape.py tests/test_validate_repo_contracts.py tests/test_validate_repo_config.py -q`.
- [ ] Step 6: Run `git diff --check`.

## Execution Note

This session will execute only **Batch A** after saving the plan. Batches B-D
remain intentionally deferred until Batch A verification is recorded and the
remaining validator error buckets are re-counted.
