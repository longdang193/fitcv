---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T00:32:00+02:00
change_id: 2026-04-22-option-b-phase-3-cleanup
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the Option B phase 3 cleanup.
parent_workstream: none
targets:
  - docs/features/
  - docs/generated/
  - docs/operating_system/
  - repo_config/
  - scripts/
  - tests/
  - .github/workflows/
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

# Option B Phase 3 Cleanup Implementation Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/archive/specs/2026-04-22-00-29-option-b-phase-3-cleanup-spec.md`
**Type:** modify
**Plan Layer:** operating_system
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Tighten the post-rollout Mode B layer by making feature/capability naming policy explicit, enriching generated lineage, normalizing managed capabilities to structured entries, and wiring architecture checks into standard CI enforcement.

**Architecture:** Phase 3 builds on the completed Phase 2 rollout instead of reopening it. The plan first locks policy and validation behavior in tests, then expands the sync/validator tooling, normalizes feature-source metadata to structured capabilities, refreshes generated outputs, and finally integrates the checks into CI and governance records.

**Key Invariants:**
- Underscore feature IDs remain the explicit accepted repo-local naming policy for this phase.
- Managed feature capabilities should use structured entries with `capability_id` and `name`.
- Generated contracts, lineage, and discovery remain script-owned outputs.
- Validation should catch stale architecture docs, invalid capability shape, and naming-policy drift.
- Phase 3 should reduce ambiguity and drift without forcing a second large migration.

**Rollout / Revert:**
- rollback_trigger: the new naming or capability validation causes widespread metadata churn without a stable compatibility path or the enriched lineage model becomes too noisy to review
- rollback_method: revert the Phase 3 policy, tooling, metadata normalization, and CI updates together so the repo returns to the verified Phase 2 baseline

---

## Doc Update Matrix

- Feature source: `docs/features/*/feature.source.yaml`
- Feature contract: `docs/features/*/<feature_id>.yaml`
- Feature lineage: `docs/features/*/lineage.generated.yaml`
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/repo-governance.md`, `docs/operating_system/publication-workflow.md`
- Repo config: `repo_config/adoption-mode.yaml`
- Scripts: `scripts/sync_architecture_docs.py`, `scripts/validate_adoption_shape.py`
- Tests: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- CI: `.github/workflows/repo-hooks.yml`
- Generated discovery: `docs/generated/feature_capabilities_index.yaml`, `docs/generated/feature_overview.md`, `docs/generated/features_index.yaml`, `docs/generated/feature_dependency_graph.yaml`, `docs/generated/features_by_status.yaml`

---

### Task 1: Add Failing Tests For Policy, Lineage, And Enforcement

**Files:**
- Modify: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Create: none
- Test: exact files above
- Docs: none

- [ ] Step 1: Expand sync tests so they assert richer lineage content and normalized capability indexing behavior.
- [ ] Step 2: Expand validator tests so they fail on invalid feature-id format, string-only capability entries, malformed capability IDs, and missing CI enforcement expectations where relevant.
- [ ] Step 3: Run `python -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py` and confirm failure before implementation.

### Task 2: Expand Sync And Validation Tooling

**Files:**
- Modify: `scripts/sync_architecture_docs.py`, `scripts/validate_adoption_shape.py`
- Create: none
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: feature lineage and generated discovery outputs

- [ ] Step 1: Add explicit naming-policy and capability-shape handling to the sync and validation layers.
- [ ] Step 2: Enrich `lineage.generated.yaml` with a stronger assembled traceability view.
- [ ] Step 3: Keep underscore feature IDs as the accepted policy for this repo and validate them consistently.
- [ ] Step 4: Re-run targeted tests until green.

### Task 3: Normalize Managed Feature Capability Metadata

**Files:**
- Modify: `docs/features/*/feature.source.yaml`
- Modify: generated feature contracts, lineage, and discovery under `docs/generated/`
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: exact feature source/generated files above

- [ ] Step 1: Convert string-only capability entries in managed feature sources into structured entries with stable `capability_id` plus `name`.
- [ ] Step 2: Preserve existing feature meaning while avoiding unnecessary rewrite churn.
- [ ] Step 3: Regenerate contracts, lineage, and discovery from the normalized sources.

### Task 4: Integrate Enforcement And Refresh Governance

**Files:**
- Modify: `.github/workflows/repo-hooks.yml`, `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/repo-governance.md`, `docs/operating_system/publication-workflow.md`, `repo_config/adoption-mode.yaml`
- Test: CI-path commands plus targeted pytest
- Docs: exact files above

- [ ] Step 1: Add architecture freshness and adoption-shape validation to the repo hook workflow.
- [ ] Step 2: Update governance docs to record the underscore-ID policy and structured capability expectation.
- [ ] Step 3: Refresh `repo_config/adoption-mode.yaml` so it records the reduced divergence set after Phase 3 cleanup.

### Task 5: Final Verification And Diff Review

**Files:**
- Modify: all Phase 3 touched files above
- Test: `tests/test_sync_architecture_docs.py`, `tests/test_validate_adoption_shape.py`
- Docs: all entries from the Doc Update Matrix

- [ ] Step 1: Run `python -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 3: Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Step 4: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 5: Review `.github/workflows/repo-hooks.yml` for the new architecture checks.
- [ ] Step 6: Run `git diff --check`.

