---
feature_type: modify
feature_name: trigger_run_management
status: completed
summary: "Compact the runs-list table so bulk selection and per-run controls remain visible without horizontal clipping."
---

# Runs-List Table Compaction Plan

## Summary

Compact the runs-list table so the checkbox column, key run metadata, and per-run action surface all remain visible after the recent bulk-selection rollout.

The implementation should:

- preserve bulk actions
- preserve per-run actions
- reduce table width
- move verbose row actions into a compact per-row action trigger
- truncate long `jobs_path` values without losing access to the full path

## Scope

This plan covers:

- runs-list column compaction
- per-row action menu/overflow trigger
- `jobs_path` truncation and full-value hover access
- focused UI rendering and contract tests
- source-of-truth and history doc updates

This plan does not cover:

- lifecycle behavior changes
- run-detail redesign
- mobile-specific alternative layouts
- server-side run list query changes

## Triage

Feature type: MODIFY
Summary: Compact the runs-list table so bulk selection and per-run actions remain visible and usable at common desktop widths.
Reasoning: The addition of bulk-selection controls widened an already-dense table, causing the actions column to clip off-screen and reducing usability.
Invariants:
  - bulk actions remain available
  - per-run actions remain available from the runs list
  - row-level lifecycle semantics do not change
  - long `jobs_path` values remain inspectable even if truncated in-row
Dependencies:
  - `trigger_run_management`
  - `run_lifecycle_controls`
Affected stages:
  - none
Affected features:
  - `trigger_run_management`
  - `run_lifecycle_controls`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history: `docs/features/trigger_run_management/history.md`
  feature_docs:
    - `docs/features/run_lifecycle_controls/history.md`
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

- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)

Current history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)

Primary implementation targets:

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py) only if template context needs light UI metadata
- shared control-plane styling if a small reusable action-menu style is needed

Primary verification targets:

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

## Invariants

- the runs list remains the main operational surface for bulk actions
- per-run actions still exist on the runs list, not only in run detail
- no row action becomes less authorized or more permissive
- the action column should stay visible at common desktop widths

## Implementation Tasks

### Task 1: Compact The Table Columns

#### Goal

Reduce the table width pressure without losing essential run-list information.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)

#### Work

- review the displayed columns for width pressure
- truncate or visually compress long secondary cells such as `jobs_path`
- ensure key operational columns stay visible:
  - checkbox
  - run id
  - status
  - mode
  - created at
  - duration
  - actions

#### Output

- a narrower, more scan-friendly runs table

### Task 2: Replace Wide Row Buttons With A Compact Action Trigger

#### Goal

Keep per-run controls available while sharply reducing action-column width.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)

#### Work

- replace wide inline text buttons with a compact action trigger such as `⋯`
- render the same available row actions inside a lightweight per-row menu/panel
- keep the current action availability logic unchanged

#### Output

- per-run actions remain accessible without dominating the table width

### Task 3: Preserve Full Secondary Data Access

#### Goal

Make sure compaction does not hide important information permanently.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)

#### Work

- add hover/title access for truncated `jobs_path`
- keep run-detail navigation obvious from the run id link
- ensure the compacted list still supports quick inspection

#### Output

- compressed rows with retained access to full values

### Task 4: Add Focused Rendering And Interaction Coverage

#### Goal

Lock in the compacted layout contract with low-cost tests.

#### Targets

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

#### Work

- add or update rendering tests for:
  - compact action trigger presence
  - retained bulk action bar hooks
  - truncated `jobs_path` rendering hook/title when appropriate
  - no regression to row-level action availability

#### Output

- runs-list compaction is protected by focused regression tests

### Task 5: Sync Docs And Discovery

#### Goal

Keep the current-state docs aligned with the compacted runs-list design.

#### Targets

- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md) if the list-level action discoverability note belongs there too

#### Work

- update the runs-list capability wording
- record the compaction rollout in feature history
- regenerate generated discovery docs if refreshed in the same pass

#### Output

- docs describe the compacted list behavior accurately

## Completion Notes

- Compacted the runs-list table with fixed-width priority columns and truncated `jobs_path` cells
- Replaced wide inline row buttons with a compact per-row `⋯` action trigger while preserving the same lifecycle actions
- Verified the runs-list rendering contract with a focused `test_app.py` slice covering bulk hooks, compact actions, and truncated path metadata
