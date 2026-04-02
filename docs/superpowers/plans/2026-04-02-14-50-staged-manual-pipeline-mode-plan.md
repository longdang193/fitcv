---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Implement a staged/manual pipeline mode with checkpointed stage progression, continue actions, and run-detail visibility while preserving the existing automatic run flow."
---

# Staged Manual Pipeline Mode Implementation Plan

## Scope

Implement the staged/manual pipeline mode defined in [2026-04-02-14-35-staged-manual-pipeline-mode-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/superpowers/specs/2026-04-02-14-35-staged-manual-pipeline-mode-spec.md).

This rollout introduces a debugging-oriented execution mode that pauses after each existing pipeline stage and allows explicit continuation from the next pending stage.

This plan does:

- preserve the existing `run_all` trigger path
- add a `manual_staged` run mode
- persist explicit stage checkpoint metadata
- let the worker/orchestrator run only a bounded stage suffix
- add run-detail visibility for manual checkpoint state
- add control-plane actions to continue a manual run to the next stage

This plan does not:

- replace the existing automatic pipeline mode
- support arbitrary stage jumping in phase 1
- support stage reruns in phase 1
- turn the UI into a generic workflow editor
- redesign the underlying pipeline stage order

## Source-of-Truth Alignment

Affected current-state docs:

- [docs/features/trigger_run_management/trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/trigger_run_management/trigger_run_management.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/rule_filter.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)

Affected history docs:

- [docs/features/trigger_run_management/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/trigger_run_management/history.md)
- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/history.md)

Affected code and tests:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/models.py)
- [src/fitcv_cp/worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/worker_job.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/run_detail.html)
- [src/fitcv_cp/templates/runs.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/runs.html)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_bq_store.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_worker_job.py)

Generated refresh required:

- none

## Invariants

- `run_all` remains the current default execution path.
- `manual_staged` uses the existing stage order and names.
- Completed stages persist checkpoint state that allows continuation from the next pending stage.
- Existing older runs without manual checkpoint metadata must continue to render safely.
- Phase 1 supports linear continuation only; rerun and arbitrary stage jumps stay out of scope.

## Implementation Tasks

### Task 1: Extend the Run Model With Manual Checkpoint Metadata

Add explicit run-mode and checkpoint fields to the control-plane run contract.

Primary files:

- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/models.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- BigQuery persistence assets or migrations as needed
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_bq_store.py)

Acceptance criteria:

- runs can store `run_mode`
- runs can store checkpoint metadata such as `next_stage`, `last_completed_stage`, and `checkpoint_status`
- older rows without the new fields remain readable

### Task 2: Refactor Pipeline Orchestration to Support Bounded Stage Execution

Make the pipeline able to run through a bounded stage range and stop after a stage when requested.

Primary files:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)

Acceptance criteria:

- orchestration can still run the full pipeline end to end
- orchestration can stop after a specified stage
- stage completion emits enough state to allow the next stage to resume later
- existing automatic runs keep their current behavior

### Task 3: Persist and Update Checkpoint State During Worker Execution

Teach the worker layer to persist checkpoint progress for manual runs and to resume from the next pending stage.

Primary files:

- [src/fitcv_cp/worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/worker_job.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/bq_store.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_worker_job.py)

Acceptance criteria:

- a manual run can stop in an explicit `awaiting_continue` state after a completed stage
- the worker can resume from the next pending stage instead of restarting from the beginning
- failures still record the failing stage clearly

### Task 4: Add Trigger-Time Selection for `run_all` vs `manual_staged`

Expose the new run mode in the trigger flow and persist it on created runs.

Primary files:

- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/runs.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/runs.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- admins can choose `Run All` or `Run Stage by Stage`
- the selected run mode is stored on the run record
- existing trigger modes for jobs/profile inputs continue to work unchanged

### Task 5: Add Run-Detail Continue Action and Manual Progress Indicators

Expose manual checkpoint state in the run detail UI and add a continue action for paused manual runs.

Primary files:

- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/run_detail.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- manual runs show run mode, checkpoint status, completed stages, and next stage
- paused manual runs expose a `Run Next Stage` control
- automatic runs remain visually simple and unchanged where possible

### Task 6: Reuse Existing Inspection Surfaces at Pause Points

Ensure manual mode works naturally with the current stage-artifact and run-detail inspection surfaces.

Primary files:

- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv_cp/templates/run_detail.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- paused runs can still inspect the stage outputs already produced
- stage-artifact downloads remain available and useful at manual checkpoints
- older non-manual runs continue to render safely

### Task 7: Update Docs and History for the New Execution Mode

Sync the feature and stage docs to reflect the new staged/manual execution path.

Primary files:

- [docs/features/trigger_run_management/trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/trigger_run_management/trigger_run_management.yaml)
- [docs/features/trigger_run_management/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/trigger_run_management/history.md)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/features/inspection_debugging/history.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/rule_filter.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)

Acceptance criteria:

- trigger/run docs explain both automatic and manual modes
- inspection docs explain checkpoint visibility and continue actions
- stage docs remain aligned to the same lifecycle and do not imply a second pipeline architecture

## Execution Order

1. Complete Task 1 first so the run/checkpoint contract is explicit before UI or worker changes.
2. Complete Task 2 next so the pipeline can run bounded stage ranges cleanly.
3. Complete Task 3 after orchestration is stage-bounded so worker resume behavior has a stable contract.
4. Complete Task 4 to expose the mode at trigger time.
5. Complete Tasks 5 and 6 together so the manual flow is visible and usable in the run detail UI.
6. Complete Task 7 last so the docs reflect implemented behavior rather than the draft design.

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "manual or staged or checkpoint or build_ranking_features"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py -k "run_mode or checkpoint or pipeline_runs"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "manual or staged or checkpoint"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py -k "run_detail or trigger or manual or staged"
```

Manual verification checklist:

- trigger one automatic run and confirm it still executes end to end without pausing
- trigger one manual run and confirm it stops after the first stage in an explicit checkpoint state
- inspect run detail and confirm next stage plus completed stages are visible
- continue the manual run and confirm it resumes from the next pending stage rather than restarting
- inspect stage artifacts after a paused stage and confirm the existing inspection surfaces still work

## Risks and Mitigations

### Resume Contract Risk

Risk:

- some stages may still rely on transient in-memory handoffs instead of persisted checkpoint-compatible state

Mitigation:

- start with strict linear continuation only
- define one explicit authoritative checkpoint contract before wiring UI actions
- add stage-focused tests for resume behavior

### Status Model Complexity Risk

Risk:

- adding checkpoint states may make run status behavior harder to reason about

Mitigation:

- keep phase-1 statuses minimal and explicit
- separate `awaiting_continue` from `failed` and `cancelled`
- document the run-state transitions clearly

### UI Confusion Risk

Risk:

- automatic and manual runs may be hard to distinguish if the run detail changes are too subtle

Mitigation:

- add explicit run mode and checkpoint status labels
- only show continue controls on paused manual runs
- preserve current automatic-run presentation wherever possible

## Done Definition

The work is complete when:

- admins can choose `run_all` or `manual_staged`
- manual runs can stop after a completed stage in an explicit checkpoint state
- manual runs can continue from the next pending stage
- automatic runs still work without adopting manual checkpoints
- run detail clearly surfaces manual progress and continue actions
- existing inspection surfaces remain useful at stage pause points
- targeted verification passes

## Task Status

Status: pending

- [ ] Task 1: Extend the run model with manual checkpoint metadata
- [ ] Task 2: Refactor pipeline orchestration to support bounded stage execution
- [ ] Task 3: Persist and update checkpoint state during worker execution
- [ ] Task 4: Add trigger-time selection for `run_all` vs `manual_staged`
- [ ] Task 5: Add run-detail continue action and manual progress indicators
- [ ] Task 6: Reuse existing inspection surfaces at pause points
- [ ] Task 7: Update docs and history for the new execution mode
- [ ] Run targeted verification
- [ ] Update plan status after implementation
