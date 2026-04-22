---
layer: operating_system
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/features/*/feature.source.yaml
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/features/*/history.md
  - docs/generated/*
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - repo_config/adoption-mode.yaml
related_features:
  - admin_control_plane_core
  - bounded_parallel_enrichment
  - cv_system
  - inspection_debugging
  - multi_file_job_input
  - pipeline_performance
  - run_lifecycle_controls
  - settings_system
  - trigger_run_management
  - ui_consistency_theming
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 5 Evidence-Oriented Lineage Alignment Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-12-05-phase-5-evidence-oriented-lineage-alignment-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Align JOB-PROJECT's managed feature-folder contract to the newer starter target by shrinking `feature.source.yaml`, moving assembled contract facts into generated feature contracts, replacing the legacy lineage schema with the starter evidence-oriented schema, and tightening validation around that new target.

**Architecture:** This phase is a repo-wide contract migration over the managed metadata layer. The generator and validator must move first so the repo has a truthful target shape, then the feature sources and generated outputs can be migrated in a controlled batch, and only then should validation harden to reject the older JOB-PROJECT-style folder shape.

**Key Invariants:**
- `feature.source.yaml` stays the human-owned semantic source.
- `<feature_id>.yaml` stays generated assembled current-state contract output.
- `lineage.generated.yaml` stays generated feature-local evidence, not a refs summary.
- Generated discovery remains script-owned and is refreshed from the updated source/generator contract.
- The repo's underscore feature-ID policy remains unless this phase explicitly changes it.

**Rollout / Revert:**  
- rollback_trigger: Generator/validator changes produce invalid generated outputs across many features or break local tooling assumptions faster than compatibility bridges can absorb.  
- rollback_method: Revert Phase 5 changes, restore the Phase 4 feature-source and lineage shapes, rerun `scripts/sync_architecture_docs.py`, and revalidate the older repo-local contract.

---

## Doc Update Matrix

- Feature source: `docs/features/*/feature.source.yaml`
- Feature contract: `docs/features/*/<feature_id>.yaml`
- Feature lineage: `docs/features/*/lineage.generated.yaml`
- Stage source: `none`
- Stage contracts: `docs/stages/*.yaml`
- Feature history: `docs/features/*/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`
- README: `none`
- Generated discovery:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-12-05-phase-5-evidence-oriented-lineage-alignment-spec.md`
- `docs/superpowers/plans/2026-04-22-12-20-phase-5-evidence-oriented-lineage-alignment-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- all managed `docs/features/*/feature.source.yaml`
- all managed `docs/features/*/<feature_id>.yaml` via regeneration
- all managed `docs/features/*/lineage.generated.yaml` via regeneration
- selected or all `docs/features/*/history.md` depending on whether history migration is included in this phase
- `docs/operating_system/feature-lifecycle.md`
- `repo_config/adoption-mode.yaml`

**Generated outputs to refresh**

- all managed feature contracts
- all managed lineage files
- `docs/generated/*`

**Primary verification commands**

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

### Task 1: Batch 1 Generator And Validator Groundwork

**Files:**
- Modify: `scripts/sync_architecture_docs.py`
- Modify: `scripts/validate_adoption_shape.py`
- Test: `tests/test_sync_architecture_docs.py`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Write failing tests for the new starter-aligned feature source, generated contract, and evidence-oriented lineage shapes.
- [x] Step 2: Include explicit tests that reject the current legacy summary-style lineage keys such as `generated_contract`, `naming_policy`, `capability_shape`, `capability_ids`, `refs`, and `refs_by_type`.
- [x] Step 3: Run `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py` and confirm failure.
- [x] Step 4: Update the generator to support the new contract split:
  source stays semantic,
  generated contract carries assembled refs/freshness,
  lineage becomes evidence-oriented.
- [x] Step 5: Add temporary compatibility bridges only where needed so the migration can proceed in a controlled batch.
- [x] Step 6: Update the validator to understand both the migration bridge and the final target, but keep final hard-failure rules gated until feature sources are migrated.
- [x] Step 7: Re-run the focused pytest command and confirm pass.

### Task 2: Batch 2 Feature Source Migration

**Files:**
- Modify: all managed `docs/features/*/feature.source.yaml`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Inventory the current managed feature-source fields and group legacy fields that must be removed or relocated.
- [x] Step 2: Migrate feature sources to the smaller semantic shape:
  `feature_id`, `name`, `status`, `type`, `summary`, `invariants`, `domains`, `depends_on`, `capabilities`, `stage_participation`, `lineage_exceptions` when needed.
- [x] Step 3: Remove legacy source-only fields such as `owner`, `primary_stage`, `stages`, `refs`, and `keywords`.
- [x] Step 4: Normalize source capabilities from `name` / `summary` to the newer starter-aligned `statement` / `state` shape while preserving stable `capability_id`.
- [x] Step 5: Where stage meaning was previously encoded through `primary_stage` or `stages`, map the retained meaning into `stage_participation` or leave it derived elsewhere according to the new generator contract.
- [x] Step 6: Run the focused pytest command again if feature-source fixtures changed in the test suite.

### Task 3: Batch 3 Generated Contract And Lineage Refresh

**Files:**
- Modify via regeneration: all managed `docs/features/*/<feature_id>.yaml`
- Modify via regeneration: all managed `docs/features/*/lineage.generated.yaml`
- Modify via regeneration: `docs/generated/*`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py` after source migration.
- [x] Step 2: Inspect representative generated contracts to ensure they now act as assembled current-state contracts rather than mirrored source dumps.
- [x] Step 3: Inspect representative lineage files to ensure they now use the starter evidence-oriented top-level shape.
- [x] Step 4: Confirm generated discovery files remain coherent with the new source/contract split.
- [x] Step 5: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check` and confirm pass.

### Task 4: Batch 4 History Alignment

**Files:**
- Modify: selected or all `docs/features/*/history.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Decide whether history alignment will land in this phase or as a tightly scoped follow-up.
- [ ] Step 2: If included now, convert feature histories to the starter partial-generated shape:
  `# History`,
  generated block markers,
  `## Human Notes`.
- [ ] Step 3: Preserve useful existing manual notes under `## Human Notes` rather than keeping version-ledger structure as the primary contract.
- [x] Step 4: If history migration is deferred, document that deferral explicitly in the plan execution notes and keep the spec target unchanged.

### Task 5: Batch 5 Validation Hardening And Governance Refresh

**Files:**
- Modify: `scripts/validate_adoption_shape.py`
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `repo_config/adoption-mode.yaml`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Remove transitional compatibility logic once the migrated feature-folder contract is live.
- [x] Step 2: Harden validation so the new starter-aligned source, contract, and lineage shapes are the only accepted managed-mode target.
- [x] Step 3: Update `docs/operating_system/feature-lifecycle.md` to describe the new source/contract/lineage split honestly.
- [x] Step 4: Update `repo_config/adoption-mode.yaml` notes and any divergence records if the repo's remaining starter drift changed.
- [x] Step 5: Re-run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` and confirm pass.
- [x] Step 6: Run `git diff --check`.

## Scope Notes

- Preferred initial implementation scope:
  generator, validator, feature source migration, generated contract migration, lineage migration
- Optional same-phase scope:
  `history.md` alignment
- If history migration meaningfully slows contract alignment, split it into a small follow-up plan after the source/contract/lineage migration lands.

## Review Focus

When reviewing this plan before execution, pay special attention to:

- whether the starter evidence-oriented lineage schema is described precisely enough for implementation
- whether the feature-source field removals are too aggressive for current repo usage
- whether generated discovery files need explicit schema adjustments once source capabilities move to `statement` / `state`
- whether history migration should stay in Phase 5 or be split out

## Execution Notes

- Batch 1 through Batch 3 landed on 2026-04-22 with passing focused tests and fresh sync/validation evidence.
- Batch 4 history alignment was intentionally deferred because the repo generator does not yet own the starter partial-generated history block.
- Batch 5 hardening landed in the same execution pass, including stricter generator behavior for structured capabilities and updated governance/adoption notes.
