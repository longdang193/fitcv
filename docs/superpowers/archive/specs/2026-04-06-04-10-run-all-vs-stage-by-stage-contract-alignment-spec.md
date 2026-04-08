---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Align Run All and Stage by Stage control-plane behavior so the two modes differ only where the product intentionally requires it."
invariants:
  - "Both execution modes must run the same stage algorithms and produce the same stage-owned artifacts for the same reached stages."
  - "Intentional mode differences must be explicit in the UI and backed by a documented product reason."
  - "Run All must not lag Stage by Stage in progress visibility, artifact availability, or post-failure diagnosability for stages it has already reached."
  - "Manual operator wait time must not be conflated with active pipeline runtime unless the contract explicitly says so."
---

# Run All vs Stage by Stage Contract Alignment

## Triage

Feature type: MODIFY  
Summary: Align control-plane semantics between `run_all` and `manual_staged` so the modes differ only in pause/continue affordances and staged-only override powers, not in progress visibility or diagnostic completeness.  
Reasoning: Existing behavior is an update to active run-orchestration and inspection features, not a new feature or a replacement system.  
Invariants:
- Both modes must share the same pipeline stage contracts.
- Stage-owned diagnostics must be available once a stage is reached, regardless of run mode.
- `manual_staged` may pause between stages; `run_all` may not.
- Run-scoped synonym overlay replacement after `enrich` remains staged-only unless explicitly broadened in a later spec.
Dependencies:
- `admin_control_plane_core`
- `trigger_run_management`
- `inspection_debugging`
- `run_lifecycle_controls`
Affected stages:
- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- `trigger_run_management`
- `inspection_debugging`
- `run_lifecycle_controls`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history: `docs/features/trigger_run_management/history.md`
  feature_docs:
    - `docs/features/inspection_debugging/history.md`
    - `docs/features/run_lifecycle_controls/history.md`
  cross_cutting_docs:
    - `docs/fitcv-control-plane-setup.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

`Run All` and `Stage by Stage` currently share the same pipeline implementation but drift in the control plane:

- `manual_staged` persists checkpoints after every stage boundary and therefore gains richer mid-run status, stage ownership, and artifact visibility.
- `run_all` skips those checkpoint snapshots and only persists the full stage-transition bundle on final success, so in-flight observability and some failure-time diagnostics are weaker.
- `manual_staged` is subject to timeout while waiting for human continuation, while `run_all` is only timed against active queue/runtime states.
- UI terminology varies across surfaces (`Run All`, `Automatic`, `Auto`, `Stage by Stage`, `Manual staged`, `Manual`), making the mode contract harder to understand.

This makes the two modes feel like different products instead of two execution strategies over one pipeline.

## Goals

- Make stage reachability, stage-owned artifacts, and stage summaries consistent between `run_all` and `manual_staged`.
- Keep the intentional product difference small and explicit:
  - `manual_staged` pauses after stage boundaries and supports continue.
  - `manual_staged` allows a late synonym-overlay replacement after `enrich` and before `rule_filter`.
- Make timeout semantics mode-aware and operator-comprehensible.
- Normalize terminology across trigger UI, runs list, run detail, and timeline.

## Non-Goals

- Change the core pipeline stage algorithms.
- Add mid-run continuation to `run_all`.
- Broaden staged-only post-`enrich` synonym overlay replacement to `run_all`.
- Redesign the entire run-detail page beyond terminology and mode-contract clarity.

## Current Drift Summary

### 1. Checkpoint and artifact persistence drift

`manual_staged` runs:
- start with explicit checkpoint metadata
- stop after each stage
- persist checkpoint payloads and stage-transition artifacts at each pause

`run_all` runs:
- start without checkpoint metadata
- execute straight through
- persist stage-transition artifacts only on final success

Impact:
- `run_all` has weaker in-flight diagnostics
- `run_all` failures can have less stage-owned context than staged pauses
- operators cannot compare the modes on equal diagnostic footing

### 2. Timeout semantics drift

`manual_staged` enters `awaiting_continue`, and the current max-runtime policy can cancel the run while it is waiting for operator input. `run_all` never enters that state.

Impact:
- the same admin setting effectively covers two different concepts:
  - active pipeline duration
  - human wait time between manual stages

### 3. Capability drift around synonym overlays

Both modes support trigger-time run-scoped overlay upload, but only `manual_staged` supports the late replacement window after `enrich`.

Impact:
- this is intentional product behavior, but today it is mixed into the broader mode drift instead of being presented as a clear, narrow exception

### 4. Terminology drift

The same mode appears as:
- `Run All`
- `Automatic`
- `Auto`

and:
- `Stage by Stage`
- `Manual staged`
- `Manual`

Impact:
- operators cannot quickly reason about whether two screens are describing the same mode

## Proposed Design

### A. Treat both modes as one stage contract with two execution policies

Document the execution modes as:

- `Run All`
  - continuous execution across the full stage sequence
  - no manual pause points
- `Stage by Stage`
  - same stage sequence
  - same stage logic
  - explicit pause after each configured stage boundary

This becomes the canonical contract language across UI and docs.

### B. Persist lightweight stage progress for `Run All`

`run_all` should persist stage-boundary progress snapshots as stages complete, even though it does not pause.

Required persisted facts after each reached stage:
- `last_completed_stage`
- `completed_stages`
- stage-boundary event row
- stage-owned artifact snapshot availability for all reached stages

This is not a manual checkpoint contract. It is a progress/diagnostic contract.

Result:
- `Run All` gains the same stage reachability visibility as `Stage by Stage`
- stage-owned downloads and run-detail diagnostics can rely on reached-stage semantics rather than pause semantics

### C. Separate checkpoint state from progress state

Split the concepts clearly:

- Progress state:
  - what stages have been completed
  - what stage was reached last
  - what artifacts exist
- Checkpoint state:
  - whether the run is paused for manual continuation
  - what the next resumable stage is
  - the serialized checkpoint payload

Rules:
- `manual_staged` has both progress state and checkpoint state.
- `run_all` has progress state only.

### D. Make timeout policy mode-aware

The admin-facing setting remains one visible concept unless and until a later product decision broadens it, but the implementation contract should distinguish:

- active runtime timeout
- manual wait timeout

Required behavior:
- queued/running/cancelling timeout remains a run-lifecycle safety guard for both modes
- `awaiting_continue` timeout is documented explicitly as a manual-wait policy that applies only to `Stage by Stage`

UI/helper copy must make this explicit so operators do not assume the same limit means the same thing in both modes.

### E. Keep the staged-only synonym override as the only intentional post-trigger capability difference

Maintain:
- trigger-time synonym overlay upload for both modes
- late post-`enrich` replacement for `Stage by Stage` only

Clarify this in the UI as a narrow exception:
- `Run All` uses the trigger-time overlay snapshot for the full run
- `Stage by Stage` may replace that snapshot before continuing from `enrich` to `rule_filter`

### F. Normalize terminology everywhere

Use the same labels everywhere:

- `Run All`
- `Stage by Stage`

Optional small metadata subtitle:
- `continuous`
- `manual pause between stages`

Do not mix these with `Auto`, `Automatic`, `Manual`, or `Manual staged` in operator-facing surfaces.

### G. Make run-detail controls mode-explicit

Run detail should communicate:

- this run’s execution mode
- whether it can currently continue
- whether it can currently replace the synonym overlay
- whether timeout is acting on runtime or on manual wait

The page should not rely on users inferring these differences from status alone.

## UX / Contract Changes

### Trigger page

- Keep both execution-mode options.
- Keep pre-trigger synonym overlay support for both modes.
- Add concise helper text:
  - `Run All runs continuously through all stages.`
  - `Stage by Stage pauses after each stage so you can inspect and continue.`

### Runs list

- Replace `Auto` / `Manual` labels with `Run All` / `Stage by Stage`.
- Keep `next: <stage>` only for paused staged runs.
- If future live progress chips are shown, they must reflect reached stages for both modes.

### Run detail

- Show execution mode with canonical product language.
- Distinguish:
  - `Paused for manual continuation`
  - `Running continuously`
- Keep late synonym replacement visible only on staged runs paused after `enrich`.
- Surface runtime-vs-manual-wait timeout semantics in helper copy or status detail.

### Timeline and artifacts

- Stage aggregate rows and stage-owned downloads should appear based on reached stages, not only pause checkpoints.
- `Run All` should gain the same aggregate stage progression visibility as staged runs, minus manual checkpoint rows.

## Data / Persistence Contract

### For `manual_staged`

Persist:
- progress state
- checkpoint state
- checkpoint payload
- stage-owned artifacts after each reached stage

### For `run_all`

Persist:
- progress state
- stage-owned artifacts after each reached stage

Do not persist:
- resumable checkpoint payloads
- staged-only checkpoint statuses

### Required invariant

If a stage is reached in either mode, then:
- its stage-owned artifact availability rules must evaluate the same way
- its stage summary should be representable in run detail and timeline

## Acceptance Criteria

- A `Run All` run that has completed `normalize`, `enrich`, or later stages exposes the same stage-owned downloads as a staged run that has reached the same stages, except for staged-only checkpoint artifacts.
- A `Run All` run that fails after reaching intermediate stages still preserves stage progress and stage-owned diagnostics for the reached stages.
- `Stage by Stage` remains the only mode with:
  - `continue`
  - `awaiting_continue`
  - post-`enrich` synonym overlay replacement
- Timeout behavior clearly distinguishes manual wait timeout from active runtime timeout.
- Runs list and run detail use one consistent mode vocabulary.

## Risks

- Adding progress snapshots to `Run All` may increase write frequency to the control-plane store.
- If progress-state and checkpoint-state are not separated cleanly, the system could accidentally imply resumability for `Run All`.
- Existing UI/tests may implicitly depend on current `Auto` / `Manual` strings.

## Rollout Notes

- Prefer additive progress-state persistence first.
- Update control-plane rendering to depend on reached-stage state rather than staged-only checkpoint state.
- Then normalize labels and helper copy.
- Keep staged-only override powers unchanged in the same rollout to avoid widening scope.

## Affected Source-of-Truth Docs

- [trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/trigger_run_management/trigger_run_management.yaml)
- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/inspection_debugging.yaml)
- [run_lifecycle_controls.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
