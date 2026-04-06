---
feature_type: modify
feature_name: run_lifecycle_controls
status: completed
summary: "Broaden cancel eligibility so paused manual runs in `awaiting_continue` can be cancelled directly into the terminal `cancelled` state."
---

# Awaiting-Continue Cancel Eligibility Adjustment Plan

## Summary

Allow paused staged runs in `awaiting_continue` to be cancelled without resuming them first.

Keep the existing cancel behavior for:

- `queued`
- `running`

And keep terminal runs non-cancellable:

- `succeeded`
- `failed`
- `cancelled`

For `awaiting_continue`, use a direct terminal-cancel path that marks the run `cancelled`, sets `finished_at`, and appends an explicit lifecycle event.

## Scope

This plan covers:

- shared cancel-eligibility logic
- single-run cancel behavior for `awaiting_continue`
- bulk cancel behavior for `awaiting_continue`
- run-list and run-detail action visibility consistency
- focused lifecycle tests
- source-of-truth and generated doc updates

This plan does not cover:

- archive rule changes
- continue/resume behavior changes
- new lifecycle statuses
- force-kill semantics
- deletion semantics

## Triage

Feature type: MODIFY
Summary: Let paused manual runs in `awaiting_continue` be cancelled directly while keeping terminal runs non-cancellable.
Reasoning: `awaiting_continue` is a paused but unfinished state, so excluding it from cancel creates an inconsistent lifecycle model and unnecessary operator friction.
Invariants:
  - `queued` and `running` retain their current cancel behavior
  - `awaiting_continue` transitions directly to `cancelled`
  - `succeeded`, `failed`, and `cancelled` remain non-cancellable
  - single-run and bulk cancel share the same eligibility rules
  - paused-run cancellation still appends a clear lifecycle audit event
Dependencies:
  - `admin_control_plane_core`
  - `run_lifecycle_controls`
  - `trigger_run_management`
Affected stages:
  - none
Affected features:
  - `run_lifecycle_controls`
  - `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
  feature_history: `docs/features/run_lifecycle_controls/history.md`
  feature_docs:
    - `docs/features/trigger_run_management/history.md`
  cross_cutting_docs:
    - `docs/fitcv-control-plane-setup.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: low

## Source-Of-Truth Alignment

Current feature contracts:

- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)

Current history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)

Primary implementation targets:

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html) for action-state consistency if needed

Primary verification targets:

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

## Invariants

- `awaiting_continue` can be cancelled without resuming
- cancelling `awaiting_continue` does not pass through `cancelling`
- current queue and cooperative-cancellation paths remain unchanged for other active states
- bulk and single-run cancel surfaces stay aligned

## Implementation Tasks

### Task 1: Broaden Shared Cancel Eligibility

#### Goal

Make the shared cancel-eligibility helper treat `awaiting_continue` as cancellable.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)

#### Work

- update the shared cancellable-state helper
- ensure terminal-state exclusions remain explicit
- reuse that same helper for both single-run and bulk cancel flows

#### Output

- one authoritative eligibility rule for cancellable runs

### Task 2: Add Direct Cancel Path For Awaiting-Continue Runs

#### Goal

Support immediate cancellation of paused staged runs.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)

#### Work

- detect `awaiting_continue` inside the cancel endpoint
- mark the run directly `cancelled`
- set `finished_at`
- append a dedicated lifecycle event/message for paused-run cancellation

#### Output

- single-run cancel handles `awaiting_continue` cleanly and terminally

### Task 3: Extend Bulk Cancel To Handle Awaiting-Continue

#### Goal

Keep bulk cancel behavior aligned with single-run cancel.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)

#### Work

- allow `awaiting_continue` rows through bulk-cancel eligibility
- give them the same direct terminal-cancel handling
- keep batch response summaries unchanged in shape

#### Output

- bulk cancel and single-run cancel answer the same way for paused runs

### Task 4: Update Action Visibility In Run Surfaces

#### Goal

Make the UI reflect the broadened cancel rule.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html) if action-state rendering depends on explicit status checks there

#### Work

- show the cancel action for `awaiting_continue` where applicable
- keep wording consistent with the rest of the lifecycle UI
- ensure no terminal run newly shows a cancel action

#### Output

- operators can discover the new paused-run cancel capability from the UI

### Task 5: Add Focused Regression Coverage

#### Goal

Lock in the new lifecycle behavior with targeted tests.

#### Targets

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

#### Work

- add single-run cancel tests for `awaiting_continue`
- add bulk-cancel tests that include `awaiting_continue`
- keep negative tests for terminal runs
- verify runs-list rendering exposes cancel for paused runs where expected

#### Output

- lifecycle behavior is protected against future regression

### Task 6: Sync Docs And Discovery

#### Goal

Keep feature contracts and history aligned with the new lifecycle rule.

#### Targets

- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)
- generated discovery files if refreshed in the same pass

#### Work

- update lifecycle capability wording
- record the broadened cancel eligibility in feature history
- note the UI-discoverability change in run-management history

#### Output

- docs match the shipped lifecycle behavior

## Completion Notes

- Broadened cancel eligibility so `awaiting_continue` now shares the same cancellable contract as other non-terminal active runs
- Added a direct terminal-cancel path for paused manual runs while preserving queue and cooperative-cancellation behavior for `queued` and `running`
- Verified the change with focused lifecycle and UI slices in `test_app.py` plus a `py_compile` check on the updated backend module
