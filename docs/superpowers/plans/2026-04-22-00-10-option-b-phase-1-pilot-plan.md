---
layer: operating_system
artifact_type: plan
status: proposed
parent_workstream: none
targets:
  - docs/features/cv_system/
  - docs/stages/
  - docs/generated/
  - scripts/
  - tests/
related_features:
  - cv_system
related_stages:
  - cv_analysis
---

# Option B Phase 1 Pilot Implementation Plan

**Feature Source:** `docs/features/cv_system/feature.source.yaml`
**Feature Contract:** `docs/features/cv_system/cv_system.yaml`
**Spec:** `docs/superpowers/archive/specs/2026-04-21-23-50-option-b-migration-spec.md`
**Type:** modify
**Plan Layer:** operating_system
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Establish the first truthful Option B source/generated pilot by introducing `cv_system` and `cv_analysis` source files plus a minimal architecture sync/check script that regenerates the pilot outputs and discovery.

**Architecture:** This pilot adds a small source-owned lifecycle layer for one feature and one stage, then introduces a narrow sync script that derives generated outputs from those new sources. The pilot intentionally limits scope to `cv_system`, `cv_analysis`, and the generated discovery files they directly affect so the repo can prove the source/generated model before broader rollout.

**Key Invariants:**
- `docs/features/cv_system/feature.source.yaml` becomes the human-owned semantic source for the pilot feature.
- `docs/stages/cv_analysis.source.yaml` becomes the human-owned semantic source for the pilot stage.
- Generated contracts and discovery remain outputs and are refreshed by script rather than hand-maintained as truth.
- The pilot must not break existing adapter/publication workflows.

**Rollout / Revert:**
- rollback_trigger: pilot output shape proves too lossy or the sync/check script cannot reproduce existing contract content closely enough for review
- rollback_method: remove the pilot source files and script changes, keep the pre-pilot generated docs as current truth, and revise the migration design before retrying

---

## Doc Update Matrix

- Feature source: `docs/features/cv_system/feature.source.yaml`
- Feature contract: `docs/features/cv_system/cv_system.yaml`
- Feature lineage: `docs/features/cv_system/lineage.generated.yaml`
- Stage source: `docs/stages/cv_analysis.source.yaml`
- Stage contracts: `docs/stages/cv_analysis.yaml`
- Feature history: `docs/features/cv_system/history.md` | none
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/stage-lifecycle.md`
- README: none
- Generated discovery: `docs/generated/features_index.yaml`, `docs/generated/stages_index.yaml`, `docs/generated/stage_overview.md`

---

### Task 1: Add Failing Tests For The Pilot Sync Contract

**Files:**
- Create: `tests/test_sync_architecture_docs.py`
- Modify: none
- Test: `tests/test_sync_architecture_docs.py`
- Docs: none

- [ ] Step 1: Write failing tests that define the pilot sync/check behavior for `cv_system` and `cv_analysis`.
- [ ] Step 2: Run `python -m pytest tests/test_sync_architecture_docs.py` and confirm failure.
- [ ] Step 3: Cover at least:
  - source files are required for the pilot
  - generated pilot outputs are written from source
  - generated discovery is refreshed from the pilot outputs
  - source files are not overwritten
- [ ] Step 4: Commit only after the tests fail for the expected reason.

### Task 2: Create Pilot Source Files

**Files:**
- Create: `docs/features/cv_system/feature.source.yaml`, `docs/stages/cv_analysis.source.yaml`
- Modify: none
- Test: `tests/test_sync_architecture_docs.py`
- Docs: exact source files above

- [ ] Step 1: Draft the minimal truthful feature source for `cv_system` from the current contract.
- [ ] Step 2: Draft the minimal truthful stage source for `cv_analysis` from the current contract.
- [ ] Step 3: Keep source content focused on semantic ownership, not generated freshness fields.
- [ ] Step 4: Re-run the failing tests and keep them red until the sync/check script exists.

### Task 3: Implement Minimal Architecture Sync/Check Script

**Files:**
- Create: `scripts/sync_architecture_docs.py`
- Modify: none
- Test: `tests/test_sync_architecture_docs.py`
- Docs: `docs/features/cv_system/cv_system.yaml`, `docs/features/cv_system/lineage.generated.yaml`, `docs/stages/cv_analysis.yaml`, generated discovery files

- [ ] Step 1: Implement the smallest script that can read the pilot source files and write the pilot outputs.
- [ ] Step 2: Regenerate:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/cv_system/lineage.generated.yaml`
  - `docs/stages/cv_analysis.yaml`
  - `docs/generated/features_index.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`
- [ ] Step 3: Run `python -m pytest tests/test_sync_architecture_docs.py` and confirm green.
- [ ] Step 4: Re-run the sync script directly and confirm idempotent output.

### Task 4: Align Lifecycle Docs To The Pilot Reality

**Files:**
- Create: none
- Modify: `docs/operating_system/feature-lifecycle.md`, `docs/operating_system/stage-lifecycle.md`
- Test: `tests/test_sync_architecture_docs.py`
- Docs: exact files above

- [ ] Step 1: Update the lifecycle docs so they describe the pilot source/generated split truthfully.
- [ ] Step 2: Make sure the docs name the new sync script as the pilot refresh path.
- [ ] Step 3: Avoid claiming full repo-wide Mode B completion; describe this as the pilot path.

### Task 5: Final Verification And Diff Review

**Files:**
- Create: none
- Modify: all pilot-touched files above
- Test: `tests/test_sync_architecture_docs.py`
- Docs: all entries from the Doc Update Matrix

- [ ] Step 1: Run `python -m pytest tests/test_sync_architecture_docs.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 3: Run `git diff --check`.
- [ ] Step 4: Review the generated outputs and confirm that:
  - humans now edit only the pilot source files
  - generated contracts/discovery are script-owned outputs
  - no stale pilot truth remains in parallel files

