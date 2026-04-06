---
feature_type: modify
feature_name: trigger_run_management
status: completed
summary: "Convert the runs list into a selection-first surface, remove the row action column, fix table overlap, and add a configurable max-runtime guard for unfinished runs."
---

# Runs-List Selection-First Cleanup And Max-Runtime Guard Plan

## Summary

Implement a combined control-plane cleanup with two coordinated outcomes:

- simplify the runs list into a bulk-operations-first surface
- add a real max-runtime lifecycle guard so unfinished runs do not wait forever

The rollout should:

- remove the per-row action column from the runs table
- reduce visible columns to a cleaner operational set
- keep bulk actions in the list
- keep single-run actions on run detail
- add an admin-editable `run_lifecycle.max_runtime_minutes` setting
- enforce state-aware timeout handling with explicit audit events

## Scope

This plan covers:

- runs-list column cleanup and overlap reduction
- removal of list-level per-row actions
- run-detail retention of single-run lifecycle controls
- lifecycle timeout policy and enforcement wiring
- admin settings support for the max-runtime control
- focused UI/lifecycle/settings tests
- source-of-truth and generated doc updates

This plan does not cover:

- broader run-detail redesign
- deletion semantics
- mobile-specific alternative layouts
- generic worker watchdog redesign beyond this lifecycle timeout policy

## Triage

Feature type: MODIFY
Summary: Simplify the runs list into a selection-first operational surface and add a configurable max-runtime lifecycle guard.
Reasoning: The runs table is now visually overloaded after bulk-selection support, and the system still lacks a hard timeout policy for non-terminal runs.
Invariants:
  - bulk actions remain available from the runs list
  - single-run lifecycle actions remain available from run detail
  - terminal-state lifecycle rules remain server-owned
  - timeout enforcement appends explicit audit events
  - paused manual runs and active runs follow state-specific timeout outcomes
Dependencies:
  - `trigger_run_management`
  - `run_lifecycle_controls`
  - `settings_system`
  - `admin_control_plane_core`
Affected stages:
  - none
Affected features:
  - `trigger_run_management`
  - `run_lifecycle_controls`
  - `settings_system`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history: `docs/features/trigger_run_management/history.md`
  feature_docs:
    - `docs/features/run_lifecycle_controls/history.md`
    - `docs/features/settings_system/history.md`
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
Risk level: medium

## Source-Of-Truth Alignment

Current feature contracts:

- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)

Current history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)

Primary implementation targets:

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- lifecycle persistence helpers if timeout enforcement needs shared store access

Primary verification targets:

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

## Invariants

- the runs list stays useful for bulk operations
- row-level lifecycle permissions do not become more permissive
- timeout policy is explicit and auditable
- setting ownership lives in `settings_system`, not ad-hoc UI-only state

## Implementation Tasks

### Task 1: Convert The Runs List To A Selection-First Table

#### Goal

Remove the per-row action column and simplify the table to the core operational fields.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)

#### Work

- remove the row action column from the runs list
- remove lower-value visible columns that contribute to overlap, especially `triggered_by`
- keep a clean visible set such as:
  - checkbox
  - run id
  - status
  - mode
  - jobs path
  - created at
  - duration
- keep `jobs_path` truncated with hover/title access
- ensure column sizing prevents overlap at common desktop widths

#### Output

- a cleaner selection-first runs table with no clipped action surface

### Task 2: Preserve Single-Run Controls On Run Detail

#### Goal

Keep one-run lifecycle operations available even after removing them from the list.

#### Targets

- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py) only if detail context needs small adjustments

#### Work

- keep existing single-run lifecycle controls on run detail
- ensure all actions formerly discoverable from the list are still reachable from detail
- keep run-detail affordances clear for paused, active, archived, and terminal runs

#### Output

- the list becomes bulk-first while run detail remains the single-run action surface

### Task 3: Add The Max-Runtime Setting

#### Goal

Expose a real admin-editable maximum run duration control.

#### Targets

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- baseline config files in the canonical config room if a default is needed
- settings UI templates if a dedicated group/section is introduced

#### Work

- add `run_lifecycle.max_runtime_minutes`
- validate it as a positive integer
- place it in a control-plane/lifecycle settings section, not CV settings
- ensure active/default hydration follows current config ownership rules

#### Output

- a real lifecycle timeout setting visible in the admin UI

### Task 4: Implement State-Aware Timeout Enforcement

#### Goal

Enforce max runtime across non-terminal runs with state-specific terminal outcomes.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- lifecycle/store helpers used to load and update runs
- worker/control-plane orchestration touchpoints if periodic enforcement requires an existing polling path

#### Work

- define the timeout decision path for:
  - `queued`
  - `running`
  - `cancelling`
  - `awaiting_continue`
- apply the correct terminal outcome per spec:
  - queued -> `cancelled`
  - running/cancelling -> timeout failure by policy
  - awaiting_continue -> `cancelled`
- append explicit audit events with timeout-specific messages
- choose the best available time source per state

#### Output

- a real server-owned timeout lifecycle policy for unfinished runs

### Task 5: Surface Timeout Outcomes Clearly In The UI

#### Goal

Make timed-out runs understandable to operators.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)

#### Work

- ensure timed-out runs surface meaningful final status and error/timeline context
- avoid ambiguous “just failed” messaging where a timeout-specific explanation is available
- keep the list concise while preserving detail in run detail/timeline

#### Output

- operators can tell a timeout apart from an execution error or an admin cancel

### Task 6: Add Focused Regression Coverage

#### Goal

Protect both the list cleanup and the timeout policy with tests.

#### Targets

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- [test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_settings_schema.py)

#### Work

- add/update runs-list rendering tests for:
  - no row action column
  - no overlap-prone extra columns
  - retained bulk action bar hooks
  - truncated jobs path behavior
- add timeout-policy tests for the supported non-terminal states
- add settings-schema coverage for `run_lifecycle.max_runtime_minutes`

#### Output

- the combined cleanup is covered by focused UI/lifecycle/settings regression tests

### Task 7: Sync Docs And Discovery

#### Goal

Keep source-of-truth docs aligned with the new list contract and timeout behavior.

#### Targets

- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- related history files
- generated discovery files if refreshed in the same pass

#### Work

- update runs-list capability wording to reflect the selection-first model
- record the timeout guard in lifecycle and settings history
- refresh generated discovery docs if included in the rollout

#### Output

- docs match the shipped combined cleanup
