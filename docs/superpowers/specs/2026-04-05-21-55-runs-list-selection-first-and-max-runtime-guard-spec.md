---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Convert the runs list into a selection-first operational surface, remove the per-row action column, fix column overlap, and add a configurable max-runtime guard for unfinished runs."
---

# Runs-List Selection-First Cleanup And Max-Runtime Guard

## Summary

This cleanup combines three related improvements:

1. make the runs list selection-first by removing the per-row action column
2. simplify the table layout so text no longer overlaps between columns
3. add a real max-runtime lifecycle guard so non-terminal runs do not wait forever

The core idea is:

- the runs list should optimize for scanability and bulk operations
- run detail should remain the full single-run control surface
- runtime protection against zombie or forgotten runs should be enforced in lifecycle behavior, not left to manual cleanup

## Triage

Feature type: MODIFY
Summary: Simplify the runs list into a bulk-operations-first surface and add a configurable max-runtime policy for unfinished runs.
Reasoning: The runs table has become too dense after bulk-selection support, causing overlap and clipping, while the system still lacks a hard guard against indefinitely waiting or long-running runs.
Invariants:
  - bulk actions remain available on the runs list
  - single-run lifecycle actions remain available from run detail
  - run lifecycle semantics stay server-owned
  - terminal runs remain non-runnable and non-cancellable under current rules
  - max-runtime enforcement must append explicit audit events
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

## Current Problems

### 1. The runs list is visually over-dense

The current table now tries to carry:

- selection checkbox
- run id
- status
- mode
- triggered by
- jobs path
- created at
- duration
- per-row actions

This causes:

- clipped action controls
- overlapping or crowded header/body text
- low scanability
- unclear visual hierarchy

### 2. The list is trying to serve two interaction models equally

The runs list now supports bulk selection, which is the right model for operational cleanup.

But it also still tries to carry a full per-row action surface inline.

That creates tension:

- bulk actions need space
- row actions need space
- metadata columns need space

The result is a table that is trying to do too much in one horizontal strip.

### 3. Runs can wait forever

Today the system has cancellation and repair flows, but no broad max-runtime policy for unfinished runs.

That leaves room for:

- long-running zombie runs
- paused runs forgotten in `awaiting_continue`
- operational clutter and indefinite cost/risk

## Recommendation

Use a selection-first runs list and move single-run actions fully to run detail.

At the same time, add a real lifecycle timeout policy.

This yields a cleaner split:

- runs list:
  - scan
  - select
  - bulk act
- run detail:
  - inspect
  - act on one run
- lifecycle guard:
  - prevent non-terminal runs from living forever

## Goals

- remove the action column from the runs list
- eliminate visual overlap and clipping in the runs table
- preserve efficient bulk run management
- keep full single-run control on run detail
- add a configurable maximum runtime policy
- make timed-out runs explicit and auditable

## Non-Goals

- redesign run detail more broadly
- add deletion semantics
- add mobile-specific card layouts in this rollout
- redesign all pipeline status semantics
- change bulk action meanings beyond their current server-owned rules

## Proposed Runs-List Design

### 1. Remove The Per-Row Action Column

The runs list should no longer carry row-level lifecycle buttons or menus.

Why:

- the list already has a strong bulk interaction model
- inline per-row actions are the main width offender
- single-run controls are better expressed on run detail

Operationally, this keeps the list clear:

- select one run
- select many runs
- act from the bulk action bar

For one-off work, the operator can click through to run detail.

### 2. Simplify Visible Columns

Recommended visible columns:

- checkbox
- run id
- status
- mode
- jobs path
- created at
- duration

Recommended removal from the list:

- `Triggered By`
- per-row `Actions`

Rationale:

- `Triggered By` is lower-value operationally than the other columns
- it belongs in run detail or hover-level metadata
- removing it creates space without hurting bulk operations

### 3. Fix Text Overlap By Reducing Width Pressure

The overlap should be solved structurally, not cosmetically.

Preferred fixes:

- fewer visible columns
- one flexible `jobs_path` column
- ellipsis truncation for long path values
- wrap-friendly `created_at` rendering if needed
- stable narrow columns for status/mode/duration

Avoid trying to save the current layout only with tiny font or tighter spacing.

That would reduce readability without solving the fundamental crowding problem.

## Single-Run Control Model

Single-run lifecycle actions should remain on run detail.

That includes:

- run next stage
- stop run
- repair status
- archive
- unarchive

The list should become:

- bulk-first
- navigation-first

Run detail remains:

- inspection-first
- single-run action surface

## Proposed Max-Runtime Policy

### 1. Add A Configurable Runtime Guard

Introduce a new admin-editable setting:

- `run_lifecycle.max_runtime_minutes`

This should live in the settings system as a real runtime control, not as metadata.

It should apply to non-terminal runs.

### 2. Enforcement Scope

The guard should apply to:

- `queued`
- `running`
- `cancelling`
- `awaiting_continue`

But the handling should differ by state.

### 3. State-Specific Timeout Handling

#### Queued

If a queued run exceeds the configured max runtime window since creation:

- transition to terminal `cancelled`
- append a timeout event

#### Running

If a running run exceeds the configured max runtime window since start:

- request cancellation or mark terminal failure by policy

Recommended choice:

- transition to terminal `failed`
- reason: `max_runtime_exceeded`

Why failure instead of cancellation:

- a timeout is system-enforced, not an intentional operator cancel
- this makes the cause clearer in history and reporting

#### Cancelling

If a cancelling run exceeds the max runtime window or a dedicated stale-cancelling timeout:

- transition to terminal `failed`
- reason: `max_runtime_exceeded` or `stale_cancelling_timeout`

#### Awaiting Continue

If a paused manual run sits in `awaiting_continue` beyond the configured limit:

- transition to terminal `cancelled`
- append a timeout/expiry event such as:
  - `Paused manual run expired before continuation`

Recommended reasoning:

- the run was waiting for an explicit human continuation and that never happened
- `cancelled` is a better operator-facing outcome than `failed`

## Timing Source

Use the most appropriate reference timestamp by state:

- queued:
  - `created_at`
- running / cancelling:
  - prefer `started_at`, fallback to `created_at`
- awaiting_continue:
  - prefer the timestamp of the pause checkpoint if available
  - otherwise fallback to `finished_at` if it represents checkpoint completion
  - otherwise fallback to `created_at`

If pause-specific timestamping is not already persisted, this rollout may initially use the best available persisted timestamp and document that limitation.

## Audit And Visibility

Timeout enforcement must append explicit lifecycle events.

Examples:

- `Run timed out while queued`
- `Run exceeded max runtime while running`
- `Paused manual run expired before continuation`

These must be visible in:

- pipeline run events
- run detail timeline

Timed-out outcomes should be distinguishable from:

- admin-requested cancel
- pipeline failure due to normal execution error

## Settings Surface

This combined cleanup should add one real lifecycle guard setting in the admin UI:

- `Maximum Run Duration (Minutes)`

This setting belongs in the lifecycle/control-plane area, not CV settings.

It should be documented as:

- a timeout for non-terminal runs
- warning-free and enforcement-backed

This is different from the existing CV max-pages setting, which is warning-only.

## Acceptance Criteria

- the runs list no longer shows a per-row actions column
- the runs table no longer exhibits overlapping column text at common desktop widths
- bulk selection and bulk actions remain available
- run detail retains full single-run lifecycle controls
- a configurable `run_lifecycle.max_runtime_minutes` setting exists
- timed-out non-terminal runs transition to explicit terminal outcomes by policy
- timeout events are appended and visible in audit/timeline surfaces
