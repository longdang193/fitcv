---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-23T17:03:52+02:00
change_id: 2026-04-23-double-entry-truth-cleanup-batch-b
verification:
  - python scripts/sync_architecture_docs.py --check
  - python scripts/validate_adoption_shape.py
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Reframed `docs/FitCV-pipeline.md` as an explainer and updated `docs/pipeline.md` to point at it as a non-authoritative mental-model doc.
parent_workstream: none
targets:
  - docs/pipeline.md
  - docs/FitCV-pipeline.md
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
  - pipeline_performance
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Double-Entry Truth Cleanup Batch B Implementation Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/specs/2026-04-23-double-entry-truth-cleanup-spec.md`
**Type:** modify
**Plan Layer:** change
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task.

**Goal:** Demote `docs/FitCV-pipeline.md` from a quasi-contract surface to a conceptual explainer that points readers back to canonical stage, feature, and generated architecture sources.

**Architecture:** `docs/pipeline.md` remains the short navigation layer for pipeline ownership. `docs/FitCV-pipeline.md` should help readers understand the end-to-end system and operator mental model without manually restating stage-by-stage active contract details already owned by `docs/stages/*.source.yaml`, `docs/stages/*.yaml`, and `docs/features/*/feature.source.yaml`.

**Key Invariants:**
- Do not change runtime code, stage sources, feature sources, or generated contracts in this batch.
- Keep the pipeline docs useful for humans while making their non-authoritative role explicit.
- Replace manual current-stage assertions with canonical references instead of deleting all narrative context.

**Rollout / Revert:**
- rollback_trigger: the rewritten docs become too abstract to guide readers or accidentally introduce contradictory contract claims
- rollback_method: restore the prior prose and re-run the doc validators

---

## Triage

Layer: change
Feature type: MODIFY
Summary: Rewrite the pipeline narrative docs so they explain the system without re-entering stage truth.
Reasoning: The current detailed narrative behaves like a second editable contract for stage responsibilities and current behavior.
Invariants:
- `docs/pipeline.md` stays short and navigational
- `docs/FitCV-pipeline.md` becomes explainer-only
- canonical stage and feature truth remains upstream
Dependencies:
- `docs/superpowers/specs/2026-04-23-double-entry-truth-cleanup-spec.md`
Affected stages:
- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- cv_system
- inspection_debugging
- trigger_run_management
- pipeline_performance
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs: none
- cross_cutting_docs: `docs/pipeline.md`, `docs/FitCV-pipeline.md`
- readme: none
- generated: none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
Risk level: low

## Doc Update Matrix

- Feature source: none
- Feature contract: none
- Feature lineage: none
- Stage source: none
- Stage contracts: none
- Feature history: none
- Feature-specific docs: none
- Cross-cutting docs: `docs/pipeline.md`, `docs/FitCV-pipeline.md`
- Operating-system docs: none
- README: none
- Generated discovery: none

## Task 1: Reframe `docs/FitCV-pipeline.md` As An Explainer

**Files:**
- Modify: `docs/FitCV-pipeline.md`

- [x] Step 1: Remove stage-by-stage current-contract wording and "important current behavior" assertions.
- [x] Step 2: Preserve useful operator mental models, execution overview, and artifact concepts.
- [x] Step 3: Add explicit references back to stage sources, feature sources, and generated architecture outputs as the canonical truth surfaces.

## Task 2: Keep `docs/pipeline.md` Explicit About Ownership

**Files:**
- Modify: `docs/pipeline.md`

- [x] Step 1: Keep the short ownership model intact.
- [x] Step 2: Update the reference text so `docs/FitCV-pipeline.md` is described as an explainer rather than a detailed contract.

## Task 3: Verify Doc-System Integrity

**Files:**
- Verify only

- [x] Step 1: Run `python scripts/sync_architecture_docs.py --check`.
- [x] Step 2: Run `python scripts/validate_adoption_shape.py`.
- [x] Step 3: Run `python scripts/validate_repo_contracts.py --fast`.
- [x] Step 4: Run `git diff --check`.

## Completion Checklist

- intent docs updated? no
- operating-system docs updated? no
- stage sources updated? no
- stage contracts updated? no
- feature sources updated? no
- contract updated? no
- feature lineage updated? no
- feature history updated? no
- other feature-specific docs updated? no
- cross-cutting docs updated? yes
- agent memory updated or explicitly not needed? not needed
- README updated? no
- generated docs refreshed? no
