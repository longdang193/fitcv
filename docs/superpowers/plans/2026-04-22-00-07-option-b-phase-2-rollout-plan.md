---
layer: operating_system
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/features/
  - docs/stages/
  - docs/generated/
  - docs/intent/
  - docs/
  - repo_config/
  - scripts/
  - tests/
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

# Option B Phase 2 Rollout Implementation Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/archive/specs/2026-04-21-23-54-option-b-phase-2-rollout-spec.md`
**Type:** modify
**Plan Layer:** operating_system
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Turn the Phase 1 Option B pilot into a repo-wide Mode B rollout by migrating all remaining managed feature and stage docs to the source/generated shape, adding repo-wide validation, and filling the missing root/intent doc surfaces.

**Architecture:** The rollout extends the pilot tooling instead of replacing it. We first harden tests and validation so repo-wide migration lands against an explicit contract, then migrate the remaining feature and stage sources, regenerate discovery, add the missing explanatory docs, and finally refresh governance/adoption records so the repo truthfully reports its new Mode B state.

**Key Invariants:**
- `docs/features/*/feature.source.yaml` is the human-owned semantic source for every managed feature after rollout.
- `docs/stages/*.source.yaml` is the human-owned semantic source for every managed stage after rollout.
- Generated contracts, lineage, and discovery remain script-owned outputs refreshed from source files.
- Validation must catch stale generated outputs and missing required Mode B surfaces.
- Shared-surface divergence from the starter baseline remains explicit in `repo_config/adoption-mode.yaml`.

**Rollout / Revert:**
- rollback_trigger: repo-wide sync or validation cannot reproduce current architecture docs truthfully enough to review feature/stage ownership changes with confidence
- rollback_method: revert the new source files, validator, root/intent docs, and sync-script expansion together so the repo returns to the Phase 1 pilot baseline instead of a mixed incomplete state

---

## Doc Update Matrix

- Feature source: `docs/features/*/feature.source.yaml`
- Feature contract: `docs/features/*/<feature_id>.yaml`
- Feature lineage: `docs/features/*/lineage.generated.yaml`
- Feature history: `docs/features/*/history.md`
- Stage source: `docs/stages/*.source.yaml`
- Stage contract: `docs/stages/*.yaml`
- Operating-system docs: `docs/operating_system/repo-governance.md`, `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/stage-lifecycle.md`, `docs/operating_system/publication-workflow.md`
- Root docs: `docs/setup.md`, `docs/configuration.md`, `docs/usage.md`, `docs/pipeline.md`, `docs/architecture.md`
- Intent docs: `docs/intent/README.md`, `docs/intent/project-charter.md`, `docs/intent/stakeholders.md`, `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md`
- Repo config: `repo_config/adoption-mode.yaml`
- Scripts: `scripts/sync_architecture_docs.py`, `scripts/validate_adoption_shape.py`
- Tests: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Generated discovery: `docs/generated/features_index.yaml`, `docs/generated/feature_dependency_graph.yaml`, `docs/generated/feature_capabilities_index.yaml`, `docs/generated/features_by_status.yaml`, `docs/generated/stages_index.yaml`, `docs/generated/stage_overview.md`

---

### Task 1: Add Failing Repo-Wide Sync And Validation Tests

**Files:**
- Create: `tests/test_validate_adoption_shape.py`
- Modify: `tests/test_sync_architecture_docs.py`
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: none

- [ ] Step 1: Expand architecture-sync tests from pilot-only expectations to repo-wide feature/stage discovery and generated output coverage.
- [ ] Step 2: Add failing tests for the adoption-shape validator covering missing source files, missing required docs, and stale generated outputs.
- [ ] Step 3: Run `python -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py` and confirm failure for the expected gaps.

### Task 2: Expand Architecture Sync Tooling To Repo-Wide Scope

**Files:**
- Create: none
- Modify: `scripts/sync_architecture_docs.py`
- Test: `tests/test_sync_architecture_docs.py`
- Docs: all generated feature/stage contracts and `docs/generated/*`

- [ ] Step 1: Generalize the current pilot sync script so it assembles contracts, lineage, and discovery for every managed feature/stage source file.
- [ ] Step 2: Regenerate and own all listed discovery surfaces under `docs/generated/`.
- [ ] Step 3: Keep `--check` deterministic and suitable for CI-style stale-file detection.
- [ ] Step 4: Re-run `python -m pytest tests/test_sync_architecture_docs.py` until green.

### Task 3: Migrate Remaining Managed Feature Sources

**Files:**
- Create: `docs/features/*/feature.source.yaml` for all remaining managed features
- Modify: `docs/features/*/<feature_id>.yaml`, `docs/features/*/lineage.generated.yaml`
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: feature source/generated files listed in the Doc Update Matrix

- [ ] Step 1: Promote each remaining managed feature contract into `feature.source.yaml`, preserving semantic ownership while dropping generated freshness concerns.
- [ ] Step 2: Normalize capabilities toward structured feature-qualified entries where practical without forcing a full naming migration.
- [ ] Step 3: Run the sync script to regenerate feature contracts and lineage for every migrated feature.
- [ ] Step 4: Review for duplicate truth between generated contracts and nearby prose docs, keeping explanation but not competing contract content.

### Task 4: Migrate Remaining Managed Stage Sources

**Files:**
- Create: `docs/stages/normalize.source.yaml`, `docs/stages/enrich.source.yaml`, `docs/stages/rule_filter.source.yaml`, `docs/stages/shortlist.source.yaml`, `docs/stages/ranking.source.yaml`, `docs/stages/cv_generation.source.yaml`
- Modify: `docs/stages/*.yaml`
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: stage source/generated files listed in the Doc Update Matrix

- [ ] Step 1: Promote each remaining stage contract into a stage source file using the `cv_analysis` source schema as the template.
- [ ] Step 2: Regenerate stage contracts from source and ensure cross-links to features remain truthful.
- [ ] Step 3: Re-run the sync script and confirm stage discovery surfaces reflect the full managed set.

### Task 5: Add Validator And Required Root/Intent Docs

**Files:**
- Create: `scripts/validate_adoption_shape.py`, all missing root docs under `docs/`, all files under `docs/intent/`
- Modify: `repo_config/adoption-mode.yaml`, `docs/operating_system/repo-governance.md`, `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/stage-lifecycle.md`, `docs/operating_system/publication-workflow.md`
- Test: `tests/test_validate_adoption_shape.py`
- Docs: exact files above

- [ ] Step 1: Implement the adoption-shape validator so it checks required Mode B surfaces and stale generated outputs.
- [ ] Step 2: Add the missing root and intent docs as concise source-like explanatory layers.
- [ ] Step 3: Update governance/lifecycle docs to describe repo-wide Mode B reality rather than pilot-only guidance.
- [ ] Step 4: Refresh `repo_config/adoption-mode.yaml` to record the new alignment state and any remaining intentional divergences.

### Task 6: Final Verification And Diff Review

**Files:**
- Create: none
- Modify: all rollout-touched files above
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: all entries from the Doc Update Matrix

- [ ] Step 1: Run `python -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 3: Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Step 4: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 5: Run `git diff --check`.
- [ ] Step 6: Review generated outputs and verify there is no remaining competing truth for managed feature/stage contracts.

