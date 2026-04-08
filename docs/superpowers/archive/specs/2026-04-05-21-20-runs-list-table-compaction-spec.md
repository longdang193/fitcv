---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Compact the runs-list table so bulk selection and per-run controls remain usable without pushing the actions column off-screen."
---

# Runs-List Table Compaction

## Summary

Compact the runs-list table so the new bulk-selection controls do not push the per-run actions column off the visible layout.

Keep both control models:

- bulk actions for list-scale operations
- per-run actions for precise one-off work

But reduce table width by:

- compressing the per-run action surface
- truncating long secondary fields
- prioritizing the most operationally important columns

## Triage

Feature type: MODIFY
Summary: Compact the runs-list table so the checkbox column, key run metadata, and both bulk and per-run actions remain visible and usable.
Reasoning: After adding bulk selection, the runs list became too wide for the current column set and text-button actions, causing the actions column to be obscured and reducing discoverability.
Invariants:
  - bulk actions remain available on the runs list
  - per-run actions remain available somewhere on the runs list
  - run detail remains the full-fidelity single-run control surface
  - no lifecycle action semantics change as part of this compaction
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

## Current Problem

The runs list currently tries to show all of the following at once:

- selection checkbox
- run id
- status
- mode
- triggered by
- jobs path
- created at
- duration
- actions

That was already tight before bulk selection.

After adding:

- a checkbox column
- a bulk action bar

the table width is now wide enough that the actions column can be pushed out of view on common desktop widths.

This makes the UI feel broken even though the actions still technically exist.

## Recommendation

Use a compact table design instead of removing functionality.

The best balance is:

- keep bulk actions visible as the primary multi-run control
- keep per-run actions, but compress them into a narrow overflow-style action trigger
- truncate long, secondary fields such as `jobs_path`
- preserve full data access through:
  - hover title/tooltips
  - run detail

Do not remove per-run actions entirely.

## Goals

- make the runs list readable at common desktop widths
- keep the actions surface discoverable
- preserve bulk-selection usability
- reduce the visual dominance of low-value repeated text
- keep full-fidelity run inspection in run detail

## Non-Goals

- redesign run detail
- remove bulk actions
- remove per-run actions
- change lifecycle action semantics
- add responsive mobile card layouts in this rollout

## Proposed UI Changes

### 1. Compact Per-Run Action Surface

Replace wide text-button actions in the table with a compact per-row action trigger.

Preferred form:

- a narrow `⋯` action button or icon button

Opening the trigger should reveal the actions currently available for that row, such as:

- `Run Next Stage`
- `Stop Run`
- `Repair Status`
- `Archive`
- `Unarchive`

Why:

- preserves per-run controls
- dramatically reduces column width
- avoids forcing the action column off-screen

### 2. Truncate Long Jobs Path Values

`jobs_path` is useful but often too wide for the list.

Use:

- single-line ellipsis truncation in the table
- full value on hover via `title`

This keeps the table readable while preserving access to the full path.

### 3. Prioritize Core Operational Columns

The runs list should prioritize:

- checkbox
- run id
- status
- mode
- created at
- duration
- actions

Other fields should be treated as secondary and compressed where possible.

`triggered_by` can remain if it still fits after compaction, but it should not force the action column off-screen.

### 4. Keep Row-Level Detail Access

Run ID already links to run detail.

That should remain the main full-detail path for:

- complete jobs path
- full lifecycle context
- rich per-run actions

This means the list can be optimized for operations instead of carrying every detail inline.

## UX Principles

- the list should optimize for scanability first
- the list should optimize for operations second
- full inspection belongs in run detail

That means:

- compact, repeatable cells in the list
- fewer long inline strings
- actions accessible but not text-heavy

## Acceptance Criteria

- the actions surface remains visible without horizontal clipping at common desktop widths
- bulk-selection checkboxes remain visible
- per-run actions remain available from the list
- long `jobs_path` values are truncated in-row but still inspectable
- no lifecycle action semantics change
- run detail continues to serve as the full-detail single-run surface
