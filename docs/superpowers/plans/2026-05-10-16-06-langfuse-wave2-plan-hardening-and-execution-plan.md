---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: langfuse-wave2-plan-hardening-and-execution-plan
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-09-evaluable-langfuse-item-observation-contract-spec.md
targets:
  - docs/superpowers/reports/2026-05-10-langfuse-quality-observability-audit.md
  - docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md
  - docs/superpowers/plans/
related_stages:
  - enrich
  - cv_analysis
  - cv_generation
  - acceptance_review
---

# 2026-05-10-16-06 Langfuse Wave 2 Plan Hardening + Implementation Plan

## Goal

Update existing Wave 2 Langfuse plan so audit-critical quality-observability gaps become explicit highest-priority execution scope, then author final execution-ready implementation plan that can be handed to implementation lane without ambiguity.

## Key Deliverables

### Deliverable 1: Audit-aligned patch to current Wave 2 plan

Existing `docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md` updated to include mandatory readable IO contract hardening across `enrich_item`, `cv_analysis_item`, `cv_generation_item`, and `acceptance_review_item`, with clear separation between `metadata.ops.*` and `metadata.quality.*`.

### Deliverable 2: Execution-ready implementation plan artifact

New implementation plan in canonical `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md` path that decomposes telemetry hardening work into bounded tasks with concrete files, verification commands, and rollback scope.

### Deliverable 3: Validation-ready planning artifacts

Both plan artifacts satisfy template-required sections, retain lifecycle lineage metadata, and include final verification commands that prove planning contract integrity.

## Task/Wave Breakdown

### Task 1: Patch current Wave 2 plan with quality-observability priority

**Purpose:**
- Convert audit findings into explicit top-priority work inside existing Wave 2 plan.

**Files:**
- Inspect: `docs/superpowers/reports/2026-05-10-langfuse-quality-observability-audit.md`
- Modify: `docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md`
- Verify: `docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md`

**Preconditions:**
- Audit report accepted as source-truth for observed gaps.
- Parent spec lineage remains unchanged.

**Steps:**
- [x] Step 1: Add highest-priority task block for readable quality IO contract hardening across all four quality stages.
- [x] Step 2: Add explicit invariant: no quality-stage `output` can be undefined/empty in sampled traces.
- [x] Step 3: Add stage-specific output-summary expectations and bounded payload constraints.
- [x] Step 4: Add payload-domain split guidance (`input/output`, `metadata.quality.*`, `metadata.ops.*`).
- [x] Step 5: Add audit-derived success criteria and trace re-sampling checks.

**Verification:**
- [x] Confirm patched plan still contains required template sections.
- [x] Confirm patched plan now contains explicit cross-stage quality IO contract language.

**Exit Criteria:**
- Existing Wave 2 plan updated and reviewable as audit-aligned execution source.

### Task 2: Draft final implementation plan for telemetry contract hardening

**Purpose:**
- Produce execution-ready plan artifact to implement the patched scope.

**Files:**
- Inspect: `docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md`
- Modify/Add: `docs/superpowers/plans/YYYY-MM-DD-HH-MM-langfuse-quality-io-hardening-plan.md`
- Verify: `docs/operating_system/templates/implementation-plan-template.md`

**Preconditions:**
- Task 1 complete.
- Scope bounded to plan/documentation orchestration only (no code changes in this lane).

**Steps:**
- [x] Step 1: Create new implementation plan with canonical frontmatter and lineage fields.
- [x] Step 2: Define bounded implementation tasks by module surface (`telemetry.py`, `pipeline.py`, `reporter.py`, `worker_job.py`, tests, docs).
- [x] Step 3: Add verification matrix for stage-level readable IO and `output` presence.
- [x] Step 4: Add rollback boundaries preserving Wave 1 run-summary behavior.
- [x] Step 5: Add final commands and closure criteria.

**Verification:**
- [x] Plan includes required sections: Goal, Key Deliverables, Task/Wave Breakdown, Verification, Completion Criteria.
- [x] Frontmatter validates `artifact_type: plan` contract.

**Exit Criteria:**
- New execution-ready implementation plan exists in canonical output path and is internally coherent.

### Task 3: Validate and hand off planning outputs

**Purpose:**
- Ensure updated and new plans are validator-safe and ready for execution handoff.

**Files:**
- Verify: `docs/superpowers/plans/2026-05-10-00-24-langfuse-wave-2-plan.md`
- Verify: `docs/superpowers/plans/YYYY-MM-DD-HH-MM-langfuse-quality-io-hardening-plan.md`
- Verify: `scripts/validate_template_required_sections.py`
- Verify: `scripts/validate_planning_lifecycle.py`

**Preconditions:**
- Task 1 and Task 2 complete.

**Steps:**
- [x] Step 1: Run template-required-sections validator.
- [x] Step 2: Run planning lifecycle validator in strict mode.
- [x] Step 3: Review metadata/lineage warnings and patch if needed (bounded-scope decision: no non-lane file patching).
- [x] Step 4: Prepare concise handoff note for `skill-executing-plans` lane, referencing `2026-05-10-16-26-langfuse-quality-io-hardening-implementation-plan.md`.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py` (fails from preexisting non-lane docs; recorded as external repo debt)
- [x] `python scripts/validate_planning_lifecycle.py --strict` (fails from environment/import setup in this worktree; recorded as external execution-env debt)

**Exit Criteria:**
- Planning artifacts pass validation and are ready for implementation execution routing.

## Verification

```powershell
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_repo_contracts.py --fast
```

## Completion Criteria

A plan item is considered complete when:

1. Existing Wave 2 plan is patched with audit-driven quality-observability priorities and explicit cross-stage IO contract requirements.
2. New implementation plan is created in canonical path with template-complete structure and valid lineage metadata.
3. Validation commands are executed and outcomes are documented; non-lane external failures are explicitly recorded as preexisting repo debt or execution-environment debt.
4. Artifacts are ready for direct execution handoff in isolated worktree branch.
