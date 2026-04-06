---
feature_type: modify
feature_name: run_lifecycle_controls
status: completed
summary: "Add bulk run selection and batch lifecycle actions to the runs list while preserving existing single-run controls."
---

# Bulk Run Selection And Batch Lifecycle Actions Plan

## Summary

Implement checkbox-based run selection on the runs list and add server-backed batch lifecycle actions for:

- cancel
- archive
- unarchive

Keep the current per-run actions intact.

This rollout should make long-run-list cleanup efficient without changing the underlying lifecycle rules that already govern single-run actions.

## Scope

This plan covers:

- visible-row multi-select on the runs list
- a conditional bulk action bar
- batch lifecycle endpoints
- confirmation and result summary UX
- per-run eligibility reporting inside bulk results
- source-of-truth and generated doc updates

This plan does not cover:

- deleting runs
- batch continue/resume for paused manual runs
- cross-page “select all filtered results” semantics
- run-detail redesign

## Triage

Feature type: MODIFY
Summary: Add bulk run selection and batch lifecycle actions to the runs list while preserving single-run controls and server-owned lifecycle rules.
Reasoning: The lifecycle system already supports cancel/archive/unarchive, but list-scale operations remain inefficient because the UI only exposes one-run-at-a-time controls.
Invariants:
  - existing per-run actions remain visible and functional
  - bulk cancel only affects runs that are already cancellable under current rules
  - bulk archive and unarchive continue to respect current terminal/archive eligibility rules
  - each processed run still emits its normal lifecycle audit event
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
Risk level: medium

## Source-Of-Truth Alignment

Current feature contracts:

- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)

Current history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)

Primary implementation targets:

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [bq_store.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/bq_store.py)
- [models.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/models.py)
- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html) for consistency-only checks if needed

Primary verification targets:

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

## Invariants

- bulk actions never bypass current lifecycle eligibility rules
- single-run endpoints remain supported
- batch APIs return explicit processed/skipped summaries
- per-run lifecycle audit events remain intact
- list usability when nothing is selected remains close to the current experience

## Implementation Tasks

### Task 1: Add Shared Bulk Lifecycle Eligibility Helpers

#### Goal

Centralize lifecycle eligibility checks so single-run and bulk-run behavior stay aligned.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)

#### Work

- extract or add helpers for:
  - cancellable runs
  - archivable runs
  - unarchivable runs
- make the new helpers reusable by both existing single-run endpoints and new batch endpoints where practical

#### Output

- one authoritative eligibility path for lifecycle actions

### Task 2: Add Batch Lifecycle Endpoints

#### Goal

Provide explicit server endpoints for bulk cancel, archive, and unarchive.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [bq_store.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/bq_store.py)

#### Work

- add:
  - `POST /admin/runs/bulk/cancel`
  - `POST /admin/runs/bulk/archive`
  - `POST /admin/runs/bulk/unarchive`
- accept a JSON body with `run_ids`
- load run rows and apply eligibility checks per run
- process eligible runs using the existing lifecycle primitives:
  - cancel via queue/cooperative cancellation path
  - archive via archive helper
  - unarchive via unarchive helper
- return structured summaries:
  - requested
  - processed
  - skipped
  - processed_run_ids
  - skipped_items with reasons

#### Output

- explicit server-backed batch lifecycle APIs

### Task 3: Keep Audit And Event Behavior Correct

#### Goal

Preserve the current per-run audit trail for batch-processed runs.

#### Targets

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)

#### Work

- ensure each successfully processed run still appends its normal lifecycle event
- do not replace per-run audit events with one aggregate-only bulk event
- optionally add small response metadata if useful, but keep audit truth per run

#### Output

- batch actions remain auditable at the individual run level

### Task 4: Add Runs-List Multi-Selection UX

#### Goal

Make the runs list support selecting one or many visible runs and invoking bulk actions.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py) if template context needs light extensions

#### Work

- add a checkbox column to the runs list
- add a header checkbox for `select visible`
- add a conditional bulk action bar that appears only when one or more rows are selected
- keep row-level actions visible
- preserve row click/navigation behavior while preventing checkbox clicks from triggering row navigation

#### Output

- operators can select visible runs and stage a bulk action

### Task 5: Add Confirmation And Result Feedback UX

#### Goal

Make bulk action outcomes predictable and safe.

#### Targets

- [runs_list.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/runs_list.html)

#### Work

- add a confirmation modal for bulk lifecycle actions
- show:
  - selected count
  - eligible count
  - skipped count preview when possible
- after action completion, show a compact result message summarizing processed and skipped counts
- ensure ineligible runs are reported explicitly rather than silently ignored

#### Output

- bulk actions feel safe and explain partial eligibility clearly

### Task 6: Add Focused Tests For Bulk Actions And Selection Behavior

#### Goal

Lock in the new contract with server and UI-adjacent tests.

#### Targets

- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

#### Work

- add endpoint tests for:
  - bulk cancel with all eligible runs
  - bulk cancel with mixed eligible/ineligible runs
  - bulk archive with terminal runs
  - bulk unarchive with archived runs
  - empty or malformed request handling
- add UI-rendering tests for:
  - checkbox column presence
  - bulk action bar presence/structure hooks
  - no regression to existing per-run action rendering

#### Output

- the bulk-action contract is covered by focused regression tests

## Completion Notes

- Added shared lifecycle eligibility helpers and batch cancel/archive/unarchive endpoints in the admin control plane
- Added visible-row selection checkboxes and a conditional bulk action bar on the runs list while preserving row-level actions
- Verified the new contract with the focused `test_app.py` bulk/runs-list slice and a `py_compile` check on the updated backend module

### Task 7: Sync Feature And Generated Docs

#### Goal

Reflect the new runs-list batch lifecycle capability in the source-of-truth docs.

#### Targets

- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/history.md)
- [fitcv-control-plane-setup.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/fitcv-control-plane-setup.md)
- generated discovery files under `docs/generated/`

#### Work

- update lifecycle capabilities to mention batch cancel/archive/unarchive
- update run-management history to mention runs-list bulk selection and actions
- refresh generated discovery after source docs are updated

#### Output

- docs describe the runs-list lifecycle UX as it actually works

## Verification

Run at minimum:

- focused `test_app.py` slice for bulk lifecycle endpoints and runs-list rendering
- `py_compile` for touched control-plane Python modules

If template behavior is substantial, also do one manual browser sanity pass on:

- `Active` tab
- `Archived` tab
- mixed selection behavior

## Exit Criteria

- runs list supports visible-row multi-selection
- batch cancel, archive, and unarchive endpoints exist and respect current eligibility rules
- selection triggers a bulk action bar only when non-empty
- confirmation and result feedback summarize processed vs skipped runs
- existing per-run lifecycle actions still work
- per-run lifecycle audit events still exist after batch actions
- feature docs and history are updated
