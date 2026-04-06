---
feature_type: modify
feature_name: run_lifecycle_controls
status: draft
summary: "Add bulk run selection and batch lifecycle actions to the runs list without replacing existing per-run controls."
---

# Bulk Run Selection And Batch Lifecycle Actions

## Summary

Add checkbox-based run selection to the runs list and expose batch lifecycle actions for the selected set.

Keep the existing per-run actions for one-off use, but add a bulk action bar that appears when one or more runs are selected.

Initial bulk actions:

- `Cancel selected`
- `Archive selected`
- `Unarchive selected` only in contexts where archived runs are visible and selected

The design must be context-aware:

- selection respects the current tab/filter (`Active`, `All`, `Archived`)
- batch actions only apply to eligible runs
- ineligible runs are reported as skipped, not silently acted on

## Triage

Feature type: MODIFY
Summary: Add bulk run selection and multi-run lifecycle actions to the runs list while preserving existing single-run controls.
Reasoning: The underlying lifecycle capabilities already exist, but the runs-list UX only supports per-run execution, which becomes inefficient for operational cleanup at scale.
Invariants:
  - existing per-run actions remain available
  - batch actions must not weaken lifecycle eligibility rules
  - bulk cancel must only affect cancellable runs
  - archive and unarchive must continue to respect current run terminal-state rules
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

## Current Problem

The runs list already supports per-run lifecycle actions, but not batch operations.

This creates operational friction when:

- many queued or active runs need cancellation together
- many completed runs need archiving together
- operators need to clean up filtered sets instead of opening each run one by one

The current model is good for precision, but inefficient for scale.

## Recommendation

Use a hybrid control model:

- keep per-run actions for precise one-off work
- add bulk selection and batch actions for list-scale operations

Do not replace row-level actions with bulk-only controls.

This preserves the simplicity of the current UI while adding the operational tool the list is currently missing.

## Goals

- let operators select one or many runs from the runs list
- let operators execute lifecycle actions across the selected set
- keep action eligibility transparent before the action is confirmed
- preserve current single-run behavior and lifecycle rules
- keep the runs list usable even when nothing is selected

## Non-Goals

- redesign run detail
- add new lifecycle semantics beyond existing cancel/archive/unarchive rules
- introduce destructive deletion
- add batch resume/continue for staged runs in this rollout
- add cross-page persistent selection beyond the current filtered result set in phase 1

## Proposed UX

### 1. Selection Column

Add a leftmost checkbox column to the runs list.

Support:

- row checkbox
- header checkbox for `select visible`

When no runs are selected:

- the list behaves almost exactly as it does today
- no bulk toolbar is shown

### 2. Bulk Action Bar

Show a bulk action bar only when at least one run is selected.

The bar should display:

- selected count
- available batch actions
- clear selection affordance

Example content:

- `5 selected`
- `Cancel selected`
- `Archive selected`
- `Clear`

### 3. Context-Aware Action Availability

Batch actions should be shown or enabled based on the current selected set.

Examples:

- `Cancel selected`
  - enabled when at least one selected run is cancellable
- `Archive selected`
  - enabled when at least one selected run is archivable
- `Unarchive selected`
  - enabled when at least one selected run is currently archived and unarchivable state rules allow it

Runs that are not eligible for the chosen action remain selected, but are reported as skipped in the preview and result summary.

### 4. Confirmation Modal

Batch actions should open a confirmation modal before execution.

The modal should summarize:

- total selected
- how many are eligible
- how many will be skipped

Example:

- `12 selected`
- `4 queued/running runs will be cancelled`
- `8 terminal runs will be skipped`

This avoids misleading operators into thinking every selected row will be affected.

### 5. Result Feedback

After execution, show a compact result summary.

Example:

- `Cancelled 4 runs; skipped 8 ineligible runs`
- `Archived 15 runs`
- `Unarchived 3 runs; skipped 2 active runs`

## Lifecycle Rules

### Bulk Cancel

Eligible:

- queued runs
- running runs that already support cooperative cancellation

Ineligible:

- succeeded
- failed
- cancelled
- archived terminal runs if cancel is meaningless in that state
- any run the current lifecycle contract already treats as non-cancellable

### Bulk Archive

Eligible:

- terminal, non-archived runs

Ineligible:

- active or queued runs
- already archived runs

### Bulk Unarchive

Eligible:

- archived runs that the current lifecycle contract allows to be unarchived

Ineligible:

- non-archived runs
- any state currently blocked by lifecycle policy

## API Shape

Add explicit bulk lifecycle endpoints rather than simulating many single-run calls from the browser.

Recommended endpoints:

- `POST /admin/runs/bulk/cancel`
- `POST /admin/runs/bulk/archive`
- `POST /admin/runs/bulk/unarchive`

Request body shape:

```json
{
  "run_ids": ["run_a", "run_b", "run_c"]
}
```

Response shape:

```json
{
  "requested": 3,
  "processed": 2,
  "skipped": 1,
  "processed_run_ids": ["run_a", "run_b"],
  "skipped_items": [
    {
      "run_id": "run_c",
      "reason": "not_cancellable"
    }
  ]
}
```

Why batch endpoints are preferred:

- clearer server-side audit trail
- simpler UI flow
- easier eligibility reporting
- avoids partial hidden failure patterns from many client-issued per-run requests

## Audit And Event Semantics

Each successfully processed run must still emit its own lifecycle event so the existing audit model remains intact.

Optionally add one top-level bulk-operation event later, but this is not required for phase 1.

Per-run audit fidelity must remain the source of truth.

## Runs-List Interaction Rules

- row click still opens run detail
- checkbox click only affects selection
- selection should reset when a tab/filter change makes selected rows no longer visible in phase 1
- batch operations should operate on the current selected rows only

Phase 1 should avoid complex “select across every page of filtered results” semantics unless the server-side list model already supports it cleanly.

## Why This Is The Optimized Solution

This design is the best balance of usability and safety because it:

- solves the real operational pain on long run lists
- preserves simple one-off actions
- avoids overloading the default list view when nothing is selected
- keeps lifecycle eligibility rules centralized on the server
- gives operators explicit previews instead of surprising partial action behavior

## Acceptance Criteria

- runs list supports selecting one or multiple visible runs
- a bulk action bar appears only when selection is non-empty
- operators can batch cancel eligible selected runs
- operators can batch archive eligible selected runs
- operators can batch unarchive eligible selected runs when archived selections are present
- confirmation UX reports eligible and skipped counts before execution
- result feedback reports processed and skipped counts after execution
- existing per-run actions remain available
- per-run lifecycle eligibility rules remain authoritative
- per-run lifecycle audit events remain intact for batch-processed runs

## Rollout Notes

Phase 1:

- visible-row selection only
- bulk cancel/archive/unarchive
- confirmation modal
- server response summary

Possible later expansion:

- select all filtered results across pagination
- batch resume/continue for paused manual runs
- richer bulk-operation history or dedicated bulk-action audit grouping
