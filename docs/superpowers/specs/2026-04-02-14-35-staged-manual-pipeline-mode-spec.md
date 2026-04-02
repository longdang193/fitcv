---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Add a staged/manual pipeline mode so admins can run, inspect, and resume FitCV one stage at a time while preserving the existing one-click full pipeline flow."
invariants:
  - The current full end-to-end pipeline trigger must remain available for normal runs.
  - Stage-by-stage execution must reuse the existing stage boundaries instead of inventing a second pipeline lifecycle.
  - Completed stages must persist enough state to allow later stages to resume without defaulting to full recomputation.
  - Manual mode must improve debugging visibility without weakening existing run inspection and auditability.
---

# Staged Manual Pipeline Mode

## Affected Source Contracts

- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/stages/enrich.yaml`
- `docs/stages/rule_filter.yaml`
- `docs/stages/ranking.yaml`
- `docs/FitCV-pipeline.md`

## Problem

The current pipeline trigger assumes one execution pattern:

- trigger once
- run every stage automatically
- inspect only after the full run has progressed or failed

That is efficient for routine runs, but it is painful when the team is debugging stage-local issues such as:

- enrichment schema drift
- rule-filter policy mistakes
- shortlist/ranking contract drift
- CV-generation or validation regressions

Today, even though stage artifacts exist, the operational flow is still all-or-nothing. A single trigger pushes the run through all stages in sequence, which creates several debugging problems:

- the team learns about problems too late
- later-stage failures can hide earlier-stage contract issues
- reruns often repeat expensive upstream work even when only one stage needs investigation
- it is hard to stop after a stage, inspect the outputs, and continue only when the stage looks correct

The result is that debugging uses post hoc inspection rather than explicit stage checkpoints.

## Goals

- Add a manual pipeline mode that lets an admin execute the pipeline stage by stage.
- Let admins stop after a stage, inspect outputs, and explicitly continue.
- Support resuming from completed checkpoints rather than rerunning earlier stages by default.
- Preserve the existing automatic one-click full pipeline mode.
- Make the run model and inspection surfaces clearly show whether a run is automatic or staged/manual.

## Non-Goals

- Replacing the existing automatic pipeline mode.
- Redesigning the stage order or stage ownership model.
- Making every internal helper function independently runnable from the UI.
- Turning the admin UI into a general-purpose workflow engine.
- Solving every migration or schema problem in this rollout.

## Current-State Summary

The current runtime model is effectively:

1. `normalize`
2. `enrich`
3. `rule_filter`
4. `shortlist`
5. `ranking`
6. `cv_generation`

The control plane can inspect stage-local artifacts after the fact, but the execution contract still assumes one continuous orchestration path.

This means the project already has:

- named stages
- run-scoped artifacts
- stage-aware inspection
- run statuses

What it lacks is:

- a trigger mode that intentionally pauses between stages
- persisted stage checkpoint state as a first-class execution concept
- an admin action model for `continue from this stage`

## Proposed Design

## 1. Introduce Two Run Modes

The control plane should support two explicit execution modes:

- `run_all`
- `manual_staged`

### `run_all`

This is the existing behavior:

- trigger once
- run end-to-end automatically unless cancelled or failed

### `manual_staged`

This is the new debugging-oriented behavior:

- trigger a run in manual mode
- execute one stage or one stage group at a time
- stop in a checkpointed state after each completed stage
- allow the admin to inspect artifacts before continuing

The key principle is:

- automatic mode optimizes for throughput
- manual mode optimizes for debuggability

## 2. Use Existing Stage Boundaries as the Manual Checkpoints

Manual mode should not invent a new lifecycle. It should use the existing stage model directly.

Recommended checkpoint sequence:

1. `normalize`
2. `enrich`
3. `rule_filter`
4. `shortlist`
5. `ranking`
6. `cv_generation`

These are the same stages already reflected in stage contracts and run inspection.

This preserves one architectural model for:

- execution
- artifacts
- debugging
- documentation

## 3. Add Explicit Stage Checkpoint State

The run system should treat stage completion as a persisted checkpoint, not just a transient log event.

Recommended state concepts:

- `next_stage`
- `completed_stages`
- `last_completed_stage`
- `checkpoint_status`

Illustrative examples:

```json
{
  "run_mode": "manual_staged",
  "completed_stages": ["normalize", "enrich"],
  "last_completed_stage": "enrich",
  "next_stage": "rule_filter",
  "checkpoint_status": "awaiting_continue"
}
```

```json
{
  "run_mode": "run_all",
  "completed_stages": ["normalize", "enrich", "rule_filter"],
  "last_completed_stage": "rule_filter",
  "next_stage": "shortlist",
  "checkpoint_status": "running"
}
```

The exact persistence shape can be finalized during implementation, but the contract needs a first-class checkpoint model.

## 4. Resume From the Last Completed Checkpoint

Manual mode should allow an admin to continue from the next pending stage without repeating prior completed stages by default.

That means the runtime should be able to:

- load or reconstruct the required inputs for the next stage from prior stage outputs
- detect that earlier stages already completed for this run
- continue from the stored checkpoint

Examples:

- after `enrich`, continue to `rule_filter`
- after `ranking`, continue to `cv_generation`

The default behavior in manual mode should be:

- continue from the next pending stage

Optional later extension:

- rerun a completed stage intentionally

That rerun behavior is useful, but it should be a separate explicit control rather than part of the first rollout.

## 5. Keep Automatic Mode Intact

The current one-click automatic path should remain the default operational mode.

This is important because:

- most routine runs should still be fast
- staged mode is primarily for debugging, validation, and controlled rollout work
- existing users should not be forced into more clicks for normal work

So the admin trigger should clearly expose:

- `Run All`
- `Run Stage by Stage`

The staged/manual mode is additive, not a replacement.

## 6. Extend Run Statuses for Manual Flow

The existing run status model should be extended to distinguish:

- currently running
- paused at a stage checkpoint
- ready to continue
- failed at a stage
- completed

Illustrative statuses:

- `queued`
- `running`
- `awaiting_continue`
- `completed`
- `failed`
- `cancelled`

The exact status names can vary, but the important behavior is:

- manual mode needs a non-error paused state
- the UI must distinguish that state from failure or cancellation

## 7. Add Stage-Level Admin Actions

The run detail view should expose stage-aware actions when a run is in manual mode.

Recommended actions:

- `Run Next Stage`
- `Run Through Ranking`
- `Run Through CV Generation`
- `Rerun Current Stage` (optional, not phase 1)

Phase 1 recommendation:

- keep actions simple
- support `Run Next Stage`
- optionally support `Run Remaining Stages`

This gives the team explicit control without overcomplicating the UI in the first rollout.

## 8. Surface Stage Checkpoint State in the Run Detail UI

The admin run detail page should make manual progression obvious.

Recommended additions:

- run mode label: `Automatic` or `Manual staged`
- current checkpoint status
- completed stages list
- next stage label
- continue button when paused

This should pair naturally with the existing event timeline and stage-artifact downloads.

The UI should answer:

- which stage has completed?
- where is the run paused?
- what can I inspect now?
- what happens if I continue?

## 9. Reuse Existing Stage Artifacts as Inspection Gates

Manual mode becomes more valuable if each pause point naturally pairs with the current inspection surfaces.

Examples:

- after `enrich`: inspect enriched rows and mapping suggestions
- after `rule_filter`: inspect pass/reject reasons
- after `shortlist`: inspect raw shortlist vs scoring shortlist
- after `ranking`: inspect feature values, fit labels, ranked outputs
- after `cv_generation`: inspect CV debug records and final outputs

This means the feature should reuse existing artifact and run-detail surfaces rather than introducing a parallel debug viewer.

## 10. Execution Model Recommendation

The implementation should move from:

- one orchestration function that always runs everything

toward:

- a stage-aware execution model that can run a bounded suffix of the pipeline

Recommended mental model:

- one runtime contract per stage
- one orchestrator that can:
  - run all stages
  - run from `stage_a` to `stage_b`
  - stop after a stage and persist checkpoint state

This does not require exposing every internal helper directly.

It does require making stage entry and exit data explicit enough that the orchestrator can resume cleanly.

## Data Flow

### Automatic Mode

1. Trigger run with `run_mode = run_all`
2. Pipeline executes through all stages in sequence
3. Existing success/failure behavior remains

### Manual Mode

1. Trigger run with `run_mode = manual_staged`
2. Execute through the first stage
3. Persist checkpoint state and stage artifacts
4. Mark run as awaiting continuation
5. Admin inspects outputs
6. Admin clicks continue
7. Runtime resumes from the next pending stage
8. Repeat until completion

## Recommended Phase 1 Shape

To keep rollout risk low, phase 1 should support:

- `run_all` and `manual_staged`
- pause after every existing stage
- `Run Next Stage`
- persisted checkpoint state
- run detail indicators for manual progression

Phase 1 should not require:

- arbitrary stage jumping
- parallel stage branches
- editing stage outputs in the UI
- rerun-any-stage controls

## Risks

- The orchestrator may currently assume in-memory continuity between stages.
- Some stages may not yet have clean resume contracts from persisted artifacts alone.
- Manual mode may complicate run statuses and admin actions if the state model is underspecified.
- The UI could become confusing if automatic and manual runs are not clearly distinguished.

## Mitigations

- Start with a strict linear manual flow using the existing stage order.
- Persist explicit checkpoint metadata rather than inferring it from logs alone.
- Reuse existing stage artifacts and run detail surfaces.
- Keep `Run All` untouched for normal production use.
- Add compatibility behavior so older runs without checkpoint metadata still render safely.

## Acceptance Criteria

- Admins can trigger a run in `manual_staged` mode.
- A manual run can complete one stage and stop in an explicit checkpoint state.
- The run detail UI shows completed stages, next stage, and checkpoint status.
- Admins can continue a manual run from the next pending stage.
- Existing automatic runs still work without adopting manual checkpoints.
- Existing inspection surfaces remain usable and become more valuable at stage pause points.
- The stage-aware design reuses the existing pipeline stage model rather than introducing a second lifecycle.

## Open Questions

- Should `normalize` and pre-enrichment global filtering pause as separate checkpoints, or should they remain one practical entry stage?
- Should phase 1 support only `Run Next Stage`, or also `Run Remaining Stages` from a paused manual run?
- Which persisted data should be treated as the authoritative resume source for each stage: in-memory handoff snapshots, BigQuery tables, or run-scoped artifact snapshots?
- Should stage reruns be part of the initial design, or deferred until checkpoint continuation is stable?
