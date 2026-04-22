---
layer: operating_system
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/trigger_run_management/lineage.generated.yaml
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_queue.py
  - scripts/validate_adoption_shape.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - repo_config/adoption-mode.yaml
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 7 Direct Evidence Backfill Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to land the direct-evidence pilot batch by batch.

**Goal:** Land a bounded pilot of truthful direct code and test evidence for selected capabilities under `cv_system`, `inspection_debugging`, and `trigger_run_management`, then lock the pilot in with lightweight validation.

**Architecture:** This phase does not redesign the evidence schema. It adds explicit capability ownership to a small set of high-signal Python files, adds truthful `@proves` links to the tests that already verify those behaviors, and then regenerates lineage so the selected capabilities move from spec/plan-only context toward real code and proof evidence. A small pilot-enforcement hook in validation keeps these gains from drifting away later without forcing repo-wide direct evidence coverage.

**Key Invariants:**
- Direct evidence must come from explicit file metadata and truthful `@proves`, not filename inference.
- Pilot capability-to-file mappings must stay sparse and materially true.
- The rest of the repo may remain partially hydrated; Phase 7 only hardens the selected pilot capabilities.
- `feature.source.yaml` remains the semantic owner; generated contracts and lineage remain generated outputs.

**Rollout / Revert:**  
- rollback_trigger: Pilot metadata proves noisy, pilot enforcement blocks valid repo states, or regenerated lineage over-attributes capability ownership.  
- rollback_method: Revert the pilot metadata, validator, and governance changes; rerun `scripts/sync_architecture_docs.py`; return to the Phase 6 evidence state.

---

## Doc Update Matrix

- Feature source:
  - `docs/features/cv_system/feature.source.yaml` reviewed, expected unchanged unless small capability cleanup becomes necessary
  - `docs/features/inspection_debugging/feature.source.yaml` reviewed, expected unchanged unless small capability cleanup becomes necessary
  - `docs/features/trigger_run_management/feature.source.yaml` reviewed, expected unchanged unless small capability cleanup becomes necessary
- Feature contract:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
- Feature lineage:
  - `docs/features/cv_system/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
  - `docs/features/trigger_run_management/lineage.generated.yaml`
- Stage source: `none`
- Stage contracts: `docs/stages/*.yaml`
- Feature history:
  - `docs/features/cv_system/history.md` reviewed, expected unchanged
  - `docs/features/inspection_debugging/history.md` reviewed, expected unchanged
  - `docs/features/trigger_run_management/history.md` reviewed, expected unchanged
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs:
  - `docs/operating_system/feature-lifecycle.md`
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

- `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`
- `docs/superpowers/plans/2026-04-22-12-09-phase-7-direct-evidence-backfill-plan.md`
- `src/fitcv/cv_generator.py`
- `src/fitcv/validator.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/queue.py`
- `tests/test_cv_generator.py`
- `tests/test_validator.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_queue.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_validate_adoption_shape.py`
- `docs/operating_system/feature-lifecycle.md`
- `repo_config/adoption-mode.yaml`

**Files expected to be reviewed but not manually changed**

- `docs/features/cv_system/feature.source.yaml`
- `docs/features/inspection_debugging/feature.source.yaml`
- `docs/features/trigger_run_management/feature.source.yaml`
- `scripts/sync_architecture_docs.py`
- `tests/test_sync_architecture_docs.py`

**Generated outputs to refresh**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/lineage.generated.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/lineage.generated.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/lineage.generated.yaml`
- `docs/generated/*`
- `docs/stages/*.yaml`

**Pilot capability set**

- `cv_system.structured-cv-generation`
- `cv_system.analysis-grounded-validation`
- `inspection_debugging.run-detail-inspection-tabs`
- `inspection_debugging.run-progress-and-checkpoints`
- `inspection_debugging.stage-artifact-downloads`
- `trigger_run_management.execution-mode-selection`
- `trigger_run_management.manual-checkpoints-and-continue`

**Primary implementation/proof mappings**

- `src/fitcv/cv_generator.py` ↔ `cv_system.structured-cv-generation`
- `tests/test_cv_generator.py` ↔ `cv_system.structured-cv-generation`
- `src/fitcv/validator.py` ↔ `cv_system.analysis-grounded-validation`
- `tests/test_validator.py` ↔ `cv_system.analysis-grounded-validation`
- `src/fitcv_cp/app.py` ↔
  - `inspection_debugging.run-detail-inspection-tabs`
  - `inspection_debugging.run-progress-and-checkpoints`
  - `inspection_debugging.stage-artifact-downloads`
  - `trigger_run_management.execution-mode-selection`
  - `trigger_run_management.manual-checkpoints-and-continue`
- `src/fitcv_cp/queue.py` ↔ `trigger_run_management.manual-checkpoints-and-continue`
- `tests/test_fitcv_cp/test_app.py` ↔
  - `inspection_debugging.run-detail-inspection-tabs`
  - `inspection_debugging.run-progress-and-checkpoints`
  - `inspection_debugging.stage-artifact-downloads`
  - `trigger_run_management.execution-mode-selection`
  - `trigger_run_management.manual-checkpoints-and-continue`
- `tests/test_fitcv_cp/test_queue.py` ↔ `trigger_run_management.manual-checkpoints-and-continue`

**Primary verification commands**

- `.\.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_cv_generator.py tests/test_validator.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_queue.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

### Task 1: Pilot Metadata Mapping And Plan/Spec Anchors

**Files:**
- Modify: `docs/superpowers/plans/2026-04-22-12-09-phase-7-direct-evidence-backfill-plan.md`
- Modify: `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Confirm the selected pilot capability set and concrete file mappings before touching code.
- [x] Step 2: Keep the plan aligned to those pilot mappings and adjust only if implementation review proves one mapping weak.
- [x] Step 3: Leave the feature source files unchanged unless execution reveals a small capability-boundary cleanup is genuinely needed.

### Task 2: Seed Direct Code Ownership Metadata

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/queue.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Replace the existing top module docstrings in the pilot source files with valid `@meta` blocks.
- [x] Step 2: Add only the pilot capability IDs each file materially implements.
- [x] Step 3: Keep ownership sparse:
  - `cv_generator.py` should only claim `cv_system.structured-cv-generation`
  - `validator.py` should only claim `cv_system.analysis-grounded-validation`
  - `app.py` should claim the selected run-detail and trigger capabilities
  - `queue.py` should only claim `trigger_run_management.manual-checkpoints-and-continue`
- [x] Step 4: Re-read the edited files and confirm the metadata remains valid YAML for the Phase 6 parser.

### Task 3: Seed Truthful Test Proof Metadata

**Files:**
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_validator.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_queue.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add `@proves cv_system.structured-cv-generation` only to the CV generator tests that actually verify structured generation behavior.
- [x] Step 2: Add `@proves cv_system.analysis-grounded-validation` only to validator tests that verify grounding and validation behavior.
- [x] Step 3: Add `@proves inspection_debugging.run-detail-inspection-tabs` to the tab-shell tests that verify the three-tab inspection interface.
- [x] Step 4: Add `@proves inspection_debugging.run-progress-and-checkpoints` to the run-detail tests that verify shared progress and checkpoint controls.
- [x] Step 5: Add `@proves inspection_debugging.stage-artifact-downloads` to the run-detail tests that verify stage-owned artifact download visibility.
- [x] Step 6: Add `@proves trigger_run_management.execution-mode-selection` to the trigger test that persists `manual_staged` mode.
- [x] Step 7: Add `@proves trigger_run_management.manual-checkpoints-and-continue` to the continue-route and queue tests that actually verify requeue/cancel behavior.
- [x] Step 8: Avoid umbrella proof tags on unrelated tests just to raise counts.

### Task 4: Pilot Enforcement Hook

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Modify: `scripts/validate_adoption_shape.py`
- Modify: `tests/test_validate_adoption_shape.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add a small pilot declaration to `repo_config/adoption-mode.yaml` listing the selected pilot capabilities and their minimum direct-evidence requirements.
- [x] Step 2: Update `scripts/validate_adoption_shape.py` to read that declaration and enforce only those pilot requirements.
- [x] Step 3: Keep the enforcement narrow:
  - pilot capabilities that require direct code evidence must fail if `code` is empty
  - pilot capabilities that require direct test proof must fail if `tests` is empty
  - non-pilot capabilities must continue to use the broader Phase 6 conservative rules
- [x] Step 4: Add focused validator tests covering a passing pilot repo and a failing pilot-evidence case.
- [x] Step 5: Run `.\.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py` and confirm pass.

### Task 5: Regenerate, Review, And Governance Refresh

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `repo_config/adoption-mode.yaml`
- Modify: `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`
- Modify: `docs/superpowers/plans/2026-04-22-12-09-phase-7-direct-evidence-backfill-plan.md`
- Modify via regeneration: selected pilot feature contracts and lineage files
- Modify via regeneration: `docs/generated/*`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update governance wording so it documents the Phase 7 pilot rule: sparse direct-evidence seeding for selected capabilities, not blanket tagging.
- [x] Step 2: Update adoption-mode notes/divergences to capture the new pilot-enforcement layer and any remaining intentional evidence gaps.
- [x] Step 3: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Step 4: Inspect the regenerated pilot lineage files and confirm the selected capabilities now contain direct `code` evidence and, where targeted, direct `tests` evidence.
- [x] Step 5: Run `.\.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_cv_generator.py tests/test_validator.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_queue.py`.
- [x] Step 6: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Step 7: Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Step 8: Run `git diff --check`.
- [x] Step 9: Mark the Phase 7 spec and this plan completed with execution notes once verification is fresh.

## Scope Notes

- Preferred implementation scope:
  direct source metadata, truthful proof markers, pilot-specific validation, governance wording, regeneration
- Optional same-phase scope:
  very small capability-statement cleanup in the three pilot feature sources if a mapping proves genuinely ambiguous
- Explicitly out of scope:
  repo-wide direct evidence seeding

## Review Focus

When reviewing this plan during execution, pay special attention to:

- whether `app.py` is being tagged too broadly
- whether any `@proves` marker overstates what the test actually verifies
- whether the pilot validation hook stays pilot-only and does not become a repo-wide coverage gate
- whether the regenerated lineage shows meaningful pilot evidence improvements without metadata spray

## Execution Notes

- Phase 7 landed on 2026-04-22.
- Direct ownership metadata was added to `src/fitcv/cv_generator.py`,
  `src/fitcv/validator.py`, `src/fitcv_cp/app.py`, and `src/fitcv_cp/queue.py`.
- Truthful `@proves` links were added to the selected pilot tests in
  `tests/test_cv_generator.py`, `tests/test_validator.py`,
  `tests/test_fitcv_cp/test_app.py`, and `tests/test_fitcv_cp/test_queue.py`.
- `repo_config/adoption-mode.yaml` now declares the pilot capability
  requirements, and `scripts/validate_adoption_shape.py` enforces them with a
  focused test fixture in `tests/test_validate_adoption_shape.py`.
- Regenerated lineage now shows direct code/test evidence for:
  - `cv_system.structured-cv-generation`
  - `cv_system.analysis-grounded-validation`
  - `inspection_debugging.run-detail-inspection-tabs`
  - `inspection_debugging.run-progress-and-checkpoints`
  - `inspection_debugging.stage-artifact-downloads`
  - `trigger_run_management.execution-mode-selection`
  - `trigger_run_management.manual-checkpoints-and-continue`
- Repo-wide gap counts moved from `missing_code_evidence=232` /
  `missing_test_evidence=230` to `218` / `218`.
