---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T01:35:00+02:00
change_id: 2026-04-22-phase-4-required-metadata-correction
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 4 required metadata correction.
parent_workstream: none
targets:
  - docs/features/*/feature.source.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/generated/feature_capabilities_index.yaml
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - scripts/**/*.py
  - tests/**/*.py
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

# Phase 4 Required Metadata Correction Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-01-20-required-metadata-correction-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Correct Mode B metadata semantics so curated capability IDs, file-level metadata, validation, and generated lineage stay evidence-backed rather than prose-derived.

**Architecture:** This phase is cross-cutting operating-system work over the repo's managed architecture metadata layer. The implementation should tighten the generator and validator first, then normalize noisy capability sources, then refresh governance and generated discovery so the repo has a stable steady-state metadata contract.

**Key Invariants:**
- `docs/features/*/feature.source.yaml` remains the human-owned semantic source.
- Generated contracts, lineage, and discovery remain script-owned outputs.
- File-level `@meta`, `capabilities`, and `@proves` metadata must only be added where the file materially participates in lineage or proof.
- Capability IDs must remain stable, feature-qualified identifiers rather than sentence-level change notes.

**Rollout / Revert:**  
- rollback_trigger: Validation or generation changes create widespread false positives or destructive metadata churn.  
- rollback_method: Revert the Phase 4 edits, restore prior feature-source capability IDs, and rerun `scripts/sync_architecture_docs.py` to regenerate the pre-change outputs.

---

## Doc Update Matrix

- Feature source: `docs/features/*/feature.source.yaml`
- Feature contract: `docs/features/*/<feature_id>.yaml`
- Feature lineage: `docs/features/*/lineage.generated.yaml`
- Stage source: `none`
- Stage contracts: `docs/stages/*.yaml`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`
- README: `none`
- Generated discovery:
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-01-20-required-metadata-correction-spec.md`
- `docs/superpowers/plans/2026-04-22-01-35-phase-4-required-metadata-correction-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- `docs/features/inspection_debugging/feature.source.yaml`
- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/operating_system/feature-lifecycle.md`
- `repo_config/adoption-mode.yaml`
- required behavioral Python files under `scripts/` and `tests/`

**Generated outputs to refresh**

- `docs/features/*/<feature_id>.yaml`
- `docs/features/*/lineage.generated.yaml`
- `docs/generated/*`

**Verification commands**

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

### Task 1: Batch 1 Inventory And Policy Lock

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `repo_config/adoption-mode.yaml`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Inventory current missing `@meta` coverage under `scripts/` and `tests/`.
- [ ] Step 2: Inventory the most prose-like capability IDs, starting with `inspection_debugging`, `trigger_run_management`, and `settings_system`.
- [ ] Step 3: Record the local steady-state policy for curated capability IDs and selective file-level metadata in `docs/operating_system/feature-lifecycle.md`.
- [ ] Step 4: Update `repo_config/adoption-mode.yaml` notes/divergences only if the policy wording needs to change.
- [ ] Step 5: Run targeted tests or checks only if policy text affects validators indirectly.

### Task 2: Batch 2 Generator And Validator Tightening

**Files:**
- Modify: `scripts/sync_architecture_docs.py`
- Modify: `scripts/validate_adoption_shape.py`
- Test: `tests/test_sync_architecture_docs.py`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Write failing tests for stricter capability handling and required Python metadata checks.
- [ ] Step 2: Run `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py` and confirm failure.
- [ ] Step 3: Tighten the generator so string-only capabilities are treated as legacy/transitional rather than canonical.
- [ ] Step 4: Tighten the validator to catch missing `@meta`, malformed capability IDs, and legacy string-only capability entries.
- [ ] Step 5: Re-run the targeted pytest command and confirm pass.

### Task 3: Batch 3 Metadata Normalization

**Files:**
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/features/trigger_run_management/feature.source.yaml`
- Modify: `docs/features/settings_system/feature.source.yaml`
- Modify: required behavioral Python files under `scripts/`
- Modify: required Python test files under `tests/`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Collapse the most prose-like capability IDs into smaller, stable capability IDs in the targeted feature sources.
- [ ] Step 2: Preserve change detail in `summary`, names, and existing refs instead of encoding it into IDs.
- [ ] Step 3: Add required top-of-file `@meta` blocks to behavioral Python scripts and test modules that currently lack them.
- [ ] Step 4: Add selective capability/proof metadata only where materially justified.
- [ ] Step 5: Run targeted pytest again to confirm the normalized metadata passes the stricter rules.
- [ ] Step 6: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py` to regenerate contracts, lineage, and discovery.

### Task 4: Batch 4 Governance Refresh And Final Verification

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `repo_config/adoption-mode.yaml`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Review the post-normalization state and refresh governance wording if execution changed the exact steady-state contract.
- [ ] Step 2: Re-run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [ ] Step 3: Re-run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [ ] Step 4: Run `git diff --check`.
- [ ] Step 5: Review the exact doc/code/generated outputs changed before closeout.
