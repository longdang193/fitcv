---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-23T17:08:00+02:00
change_id: 2026-04-23-double-entry-truth-cleanup-batch-c
verification:
  - python scripts/sync_architecture_docs.py --check
  - python scripts/validate_adoption_shape.py
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Reduced generated-history placeholder noise by omitting empty capabilities, verification, and generic outcome sections while preserving real plan-derived signal.
parent_workstream: none
targets:
  - tools/docs/generate_architecture_metadata.py
  - tests/test_architecture_metadata_generation.py
  - docs/features/*/history.md
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
  - pipeline_performance
related_stages: []
---

# Double-Entry Truth Cleanup Batch C Implementation Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/specs/2026-04-23-double-entry-truth-cleanup-spec.md`
**Type:** modify
**Plan Layer:** change
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task.

**Goal:** Reduce low-signal generated history noise by suppressing generic placeholder sections when completed-plan metadata is empty or purely boilerplate.

**Architecture:** Generated history remains a derived layer from completed plan metadata. The generator should keep real signal such as dated chronology, source-plan links, non-empty capability lists, specific verification commands, and meaningful outcome summaries, while omitting filler text that makes the derived history feel manually double-entered.

**Key Invariants:**
- Do not hide real plan metadata that adds traceability.
- Keep generated history deterministic and source-derived.
- Regenerate history files through the canonical sync flow rather than hand-editing them.

**Rollout / Revert:**
- rollback_trigger: history output loses useful traceability or tests reveal omitted non-placeholder data
- rollback_method: restore the prior generator behavior and regenerate the architecture docs

---

## Triage

Layer: change
Feature type: MODIFY
Summary: Trim generic generated-history placeholder sections from the architecture-doc generator.
Reasoning: The history generator currently emits repetitive placeholder text that adds noise without adding truth.
Invariants:
- source-plan links remain present
- meaningful capabilities, verification, and outcome data remain present
- generated history stays purely derived
Dependencies:
- `docs/superpowers/specs/2026-04-23-double-entry-truth-cleanup-spec.md`
Affected stages:
- none
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
- feature_history: `docs/features/*/history.md`
- stage_source: none
- stage_contract: none
- feature_docs: none
- cross_cutting_docs: none
- readme: none
- generated:
  - `docs/features/*/history.md`
Generated refresh required: yes
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
- Feature history: `docs/features/*/history.md`
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: none
- README: none
- Generated discovery: none

## Task 1: Tighten History Rendering Rules

**Files:**
- Modify: `tools/docs/generate_architecture_metadata.py`

- [x] Step 1: Detect empty capability lists and omit the entire `Affected capabilities` section instead of rendering `none recorded`.
- [x] Step 2: Detect empty verification lists and omit the entire `Verification` section instead of rendering `none recorded`.
- [x] Step 3: Omit the `Outcome` section when no non-placeholder outcome summary exists.

## Task 2: Add Targeted Generator Coverage

**Files:**
- Modify: `tests/test_architecture_metadata_generation.py`

- [x] Step 1: Add a unit test proving that placeholder sections are suppressed when plan metadata is generic or empty.
- [x] Step 2: Preserve existing coverage that real capabilities, verification, and outcome summaries still render.

## Task 3: Regenerate And Verify

**Files:**
- Generated: `docs/features/*/history.md`

- [x] Step 1: Run `python scripts/sync_architecture_docs.py --check` and then `python scripts/sync_architecture_docs.py` if regeneration is required.
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
- feature history updated? yes, generated
- other feature-specific docs updated? no
- cross-cutting docs updated? no
- agent memory updated or explicitly not needed? not needed
- README updated? no
- generated docs refreshed? yes
