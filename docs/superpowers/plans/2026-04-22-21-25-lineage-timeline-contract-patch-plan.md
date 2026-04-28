---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T21:25:00+02:00
change_id: 2026-04-22-lineage-timeline-contract-patch
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the lineage timeline contract patch.
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/project-adoption-migration-guide.md
  - docs/features/*/lineage.generated.yaml
related_features: []
related_stages: []
---

# Lineage Timeline Contract Patch Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-21-10-lineage-timeline-contract-patch-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Replace the repo's legacy `{kind, path}` lineage timeline contract with a starter-aligned richer completed-change timeline shape, while staying migration-safe by emitting `timeline: []` when completed-plan metadata is not truthfully available.

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Patch local lineage generation and validation so the `timeline` field uses the newer completed-change record contract instead of the older spec/plan ref list.  
Reasoning: The repo already uses evidence-oriented lineage at the top level, but the timeline section still comes from an older generator contract. The patch is bounded to timeline generation, timeline validation, focused tests, and operating-system guidance.  
Invariants:

- `lineage.generated.yaml` remains generated-only.
- no fake timestamps, change IDs, verification lists, or outcomes may be synthesized from filenames.
- `timeline: []` is valid when completed-plan metadata does not exist yet.
- legacy `{kind, path}` timeline entries must no longer be emitted or accepted.
- this phase does not require repo-wide historical plan backfill.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-21-10-lineage-timeline-contract-patch-spec.md`
- latest local starter guidance and reference implementation
- current repo-local generator, validator, and timeline fixtures

Affected stages:

- none

Affected features:

- none

Primary lens: `cross-cutting`

Affected docs:

- feature_source: `none`
- feature_yaml: `none`
- feature_lineage: `docs/features/*/lineage.generated.yaml`
- feature_history: `none`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- readme: `none`
- generated:
  - `docs/features/*/lineage.generated.yaml`

Generated refresh required: `yes`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `no`  
Plan needed: `yes`

## File Map

Files to modify:

- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/project-adoption-migration-guide.md`

Generated outputs to refresh:

- `docs/features/*/lineage.generated.yaml`

## Task 1: Patch Timeline Generation

**Files:**
- Modify: `scripts/sync_architecture_docs.py`

- [ ] Step 1: Add a small local completed-plan metadata parser for markdown plan artifacts.
- [ ] Step 2: Require a truthful minimum source shape before generating a rich timeline record:
  - `status: completed`
  - `completed_at`
  - `change_id`
  - `verification`
  - `outcome.summary`
  - optional `affects.capabilities`
- [ ] Step 3: Build `timeline` entries only from plans that meet that minimum shape.
- [ ] Step 4: Emit `timeline: []` when no valid completed-plan metadata exists for the feature.
- [ ] Step 5: Remove the legacy `{kind, path}` timeline fallback entirely.

## Task 2: Strengthen Timeline Validation

**Files:**
- Modify: `scripts/validate_adoption_shape.py`

- [ ] Step 1: Keep `timeline` required and list-shaped.
- [ ] Step 2: Reject legacy timeline entries containing the old `kind` / `path` shape.
- [ ] Step 3: When timeline entries exist, require the richer keys:
  - `completed_at`
  - `source_plan`
  - `change_id`
  - `summary`
  - `capabilities`
  - `verification`
  - `outcome`
- [ ] Step 4: Allow `timeline: []` as valid migration-safe output.

## Task 3: Add Regression Coverage

**Files:**
- Modify: `tests/test_sync_architecture_docs.py`
- Modify: `tests/test_validate_adoption_shape.py`

- [ ] Step 1: Update the happy-path fixture plan metadata so generator tests assert one richer timeline entry.
- [ ] Step 2: Add a generator test showing `timeline: []` when the plan lacks valid completed metadata.
- [ ] Step 3: Add a validator failure for legacy `{kind, path}` timeline entries.
- [ ] Step 4: Add a validator pass case for empty timeline lists.

## Task 4: Update Repo Guidance

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `docs/operating_system/project-adoption-migration-guide.md`

- [ ] Step 1: State that the old `{kind, path}` timeline shape is retired.
- [ ] Step 2: State that the current local target is rich completed-change records.
- [ ] Step 3: Clarify that empty timeline lists are acceptable during migration when completed-plan metadata is not yet available.

## Task 5: Refresh And Verify

**Files:**
- Regenerate: `docs/features/*/lineage.generated.yaml`

- [ ] Step 1: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Step 3: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 4: Run `.venv\\Scripts\\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`.
- [ ] Step 5: Run `git diff --check`.

## Completion Checklist

- intent docs updated? `not needed`
- operating-system docs updated? `yes`
- stage sources updated? `not needed`
- stage contracts updated? `not needed`
- feature sources updated? `not needed`
- contract updated? `not needed`
- feature lineage updated? `yes, regenerated`
- feature history updated? `not needed`
- other feature-specific docs updated? `not needed`
- cross-cutting docs updated? `yes`
- agent memory updated or explicitly not needed? `not needed`
- README updated? `not needed`
- generated docs refreshed? `yes`
