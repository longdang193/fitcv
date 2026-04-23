---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T13:25:00+02:00
change_id: 2026-04-22-phase-6-lineage-evidence-hydration
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 6 lineage evidence hydration.
parent_workstream: none
targets:
  - docs/features/*/lineage.generated.yaml
  - docs/features/*/<feature_id>.yaml
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

# Phase 6 Lineage Evidence Hydration Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-13-10-phase-6-lineage-evidence-hydration-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to land the generator, validation, and repo-refresh work batch by batch.

**Goal:** Turn the Phase 5 evidence-oriented lineage schema into a more useful steady state by hydrating real evidence into `lineage.generated.yaml`, removing YAML alias noise, and validating evidence claims honestly.

**Architecture:** This phase keeps the Phase 5 schema intact and improves the quality of the generated evidence. The generator should first learn to produce deterministic alias-free YAML and derive evidence from real repo metadata surfaces. Only after that should the validator harden around path existence and completeness-status sanity.

**Key Invariants:**
- `feature.source.yaml` remains the human-owned semantic source.
- `<feature_id>.yaml` remains the generated assembled current-state contract.
- `lineage.generated.yaml` remains generated evidence output, not a manual source.
- File metadata and `@proves` remain inputs to lineage rather than semantic owners.
- Feature-level spec/plan evidence may be used conservatively as fallback context, but direct capability evidence should be preferred when available.

**Rollout / Revert:**  
- rollback_trigger: Evidence extraction creates noisy or misleading capability associations across many features, or validator hardening blocks normal regeneration without clear fixes.  
- rollback_method: Revert the Phase 6 generator and validator changes, rerun `scripts/sync_architecture_docs.py`, and return to the Phase 5 minimal-evidence lineage state.

---

## Doc Update Matrix

- Feature source: `none` unless a small curated evidence seed is needed
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

- `docs/superpowers/archive/specs/2026-04-22-13-10-phase-6-lineage-evidence-hydration-spec.md`
- `docs/superpowers/plans/2026-04-22-13-25-phase-6-lineage-evidence-hydration-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- optional small curated metadata seeds in `scripts/` or `tests/` if needed for direct-evidence coverage
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

### Task 1: Batch 1 Test And Generator Groundwork

**Files:**
- Modify: `scripts/sync_architecture_docs.py`
- Test: `tests/test_sync_architecture_docs.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add failing tests for alias-free YAML output in generated lineage files.
- [x] Step 2: Add failing tests for evidence hydration from direct file metadata and `@proves`.
- [x] Step 3: Add failing tests for conservative feature-level spec/plan fallback evidence.
- [x] Step 4: Run `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py` and confirm failure.
- [x] Step 5: Update the generator to dump YAML without aliases.
- [x] Step 6: Add metadata parsing for repo Python files and conservative evidence extraction for code/tests/specs/plans/configs/components.
- [x] Step 7: Define deterministic `completeness_status` rules based on actual evidence presence.
- [x] Step 8: Re-run the focused pytest command and confirm pass.

### Task 2: Batch 2 Validator Hardening

**Files:**
- Modify: `scripts/validate_adoption_shape.py`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add validator checks for alias-policy compliance on generated lineage outputs if the raw text still contains YAML anchors.
- [x] Step 2: Add validator checks that evidence paths referenced in lineage exist.
- [x] Step 3: Add validator checks that `complete` lineage claims require real direct evidence, especially `code` or `tests`.
- [x] Step 4: Keep validation conservative for `partial` and `missing_evidence` so the repo can hydrate iteratively without false precision.
- [x] Step 5: Re-run the focused pytest command and confirm pass.

### Task 3: Batch 3 Repo Evidence Refresh

**Files:**
- Modify if needed: small curated metadata seeds under `scripts/` or `tests/`
- Modify via regeneration: all managed `docs/features/*/<feature_id>.yaml`
- Modify via regeneration: all managed `docs/features/*/lineage.generated.yaml`
- Modify via regeneration: `docs/generated/*`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Decide whether the current repo metadata is sufficient for direct evidence hydration or whether a small curated seed is needed.
- [x] Step 2: If needed, add the minimum direct evidence seed rather than broad blanket metadata.
- [x] Step 3: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Step 4: Inspect representative lineage files for:
  alias-free YAML,
  real evidence buckets,
  and conservative completeness states.
- [x] Step 5: Confirm generated contracts and discovery remain coherent after the lineage refresh.
- [x] Step 6: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check` and confirm pass.

### Task 4: Batch 4 Governance Refresh And Final Verification

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `repo_config/adoption-mode.yaml`
- Modify: phase 6 spec/plan execution notes
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update governance wording so it distinguishes Phase 5 schema alignment from Phase 6 evidence hydration.
- [x] Step 2: Update `repo_config/adoption-mode.yaml` notes/divergences if the repo's remaining starter drift changed.
- [x] Step 3: Re-run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` and confirm pass.
- [x] Step 4: Run `git diff --check`.
- [x] Step 5: Mark the Phase 6 spec/plan with execution notes once the work is complete.

## Scope Notes

- Preferred initial implementation scope:
  alias-free lineage output, direct metadata-based evidence extraction, conservative feature-level spec/plan fallback, validator hardening
- Optional same-phase scope:
  small curated metadata seed additions if the current repo does not yet expose enough direct evidence
- Explicitly out of scope:
  starter partial-generated history migration

## Review Focus

When reviewing this plan during execution, pay special attention to:

- whether feature-level fallback evidence is being over-attributed to every capability
- whether direct evidence derivation is tied to explicit metadata rather than weak filename guesses
- whether completeness states are conservative enough to avoid false confidence
- whether alias-free YAML is enforced in a robust way rather than by brittle string rewriting

## Execution Notes

- Phase 6 landed on 2026-04-22 with passing focused tests and fresh sync/validation evidence.
- Generated lineage is now alias-free and hydrated with conservative feature-level spec/plan evidence plus direct metadata support when explicit capability links exist.
- No broad repo-wide direct capability seeding was added in this phase; live repo direct code/test evidence remains sparse until future metadata work expands it deliberately.
