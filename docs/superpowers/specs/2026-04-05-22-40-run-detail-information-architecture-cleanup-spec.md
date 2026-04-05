---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Simplify the run-detail page by reducing visual competition, consolidating exports, compacting metrics, and keeping the most useful run outcome information visible."
---

# Run-Detail Information Architecture Cleanup

## Summary

The current run-detail page exposes too many equal-priority surfaces at once:

- lifecycle buttons
- multiple download buttons
- run metadata
- stage quality metrics
- late-stage reuse metrics
- pipeline results
- enriched jobs inspection
- event timeline

The result is a page that technically contains useful information but is hard to scan. Important user-facing outcomes such as `Pipeline Outcome` inside the enriched jobs table are pushed off-screen, metrics consume too much vertical space, and exports are fragmented across the page with redundant or overly run-specific placement.

This cleanup should make the page easier to operate by:

- clarifying hierarchy
- collapsing redundant export surfaces
- reducing table width pressure
- compacting metrics into a smaller health summary
- keeping run detail as the best place for single-run inspection and lifecycle operations

## Problem Statement

Current pain points:

- the top action row contains too many buttons with similar visual weight
- several download actions are redundant or misplaced
- `Stage Quality Metrics` and `Late-Stage Reuse` are too tall relative to their value
- the enriched jobs table shows too many wide columns, pushing `Pipeline Outcome` off-screen
- timeline stage downloads and top-level downloads compete for the same conceptual space
- the page lacks a clear distinction between:
  - run actions
  - run summary
  - run health
  - run outputs
  - run inspection
  - run exports

## Goals

- make the primary outcome of the run obvious within the first screen
- keep single-run lifecycle actions accessible without crowding the page
- make exports discoverable without spreading buttons everywhere
- keep `Pipeline Outcome` visible in the enriched jobs inspection surface
- preserve all current debugging capability while reducing noise

## Non-Goals

- changing lifecycle semantics
- changing artifact payloads
- redesigning the whole admin visual system
- changing run results or timeline data contracts

## Triage

Feature type: MODIFY  
Summary: Simplify run-detail layout, consolidate exports, and reduce width/height pressure across metrics and inspection surfaces.  
Reasoning: This is an existing admin control-plane feature whose current behavior is acceptable but whose UX has accumulated too many parallel surfaces.  
Invariants:
  - run detail remains the single-run lifecycle surface
  - existing artifact endpoints remain available
  - timeline stage-download links remain available
  - enriched jobs inspection remains present
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
    - none
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

Current contracts:

- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)

Primary implementation targets:

- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

## Proposed Design

### 1. Reframe The Page Into Clear Sections

The page should be ordered as:

1. page header
2. run actions + compact export access
3. run summary card
4. pipeline results / failure banner
5. compact run health card
6. inspection tabs
7. event timeline
8. secondary run-level export affordance if still needed

This order keeps the most important information higher:

- what happened
- what can I do now
- what outputs were produced
- how healthy was the run

### 2. Replace The Top Download Button Pile With A Compact Export Surface

Current top-level downloads are too fragmented.

The page should replace the button pile with a single compact `Exports` surface.

Recommended contents:

- Results JSON
- CV Debug JSON
- Settings Used JSON
- Mapping Suggestions JSON
- Stage Artifacts JSON

`Aggregate Mapping Suggestions JSON` should not live on an individual run detail page.
It belongs on a broader runs/admin surface because it is not run-specific.

### 3. Compact Metrics Into One `Run Health` Card

`Stage Quality Metrics` and `Late-Stage Reuse` should become one smaller `Run Health` block.

Instead of long stacked rows, the card should use compact metric chips or tiles.

Each metric should show only:

- short label
- percent
- numerator / denominator

Long hints should be:

- hidden behind tooltip/title text, or
- moved into a collapsible `Details` section

This reduces vertical bloat while preserving the meaning of the metrics.

### 4. Simplify The Enriched Jobs Table

The enriched jobs table currently uses too many columns.

To keep `Pipeline Outcome` visible, lower-value job metadata should be merged.

Recommended visible columns:

- Job
- Fit Context
- Required Skills
- Filter
- Pipeline Outcome

`Fit Context` should stack:

- location type
- seniority
- job family
- domain

This gives the same information with much less horizontal pressure.

### 5. Separate Run-Level Exports From Timeline Stage Downloads

There are currently overlapping artifact affordances.

The page should use this distinction:

- top export surface = run-level artifacts
- timeline row links = stage-specific artifacts

This keeps both capabilities while reducing duplication.

### 6. Tighten The Metadata Card

The run metadata card should remain dense but easier to scan.

Recommended grouping:

- identity
  - status
  - run mode
  - run id
- source
  - jobs path
  - jobs source
  - config
  - profile source
- timing
  - created
  - started
  - finished
  - duration
- progress
  - last completed
  - next stage
  - completed stages
  - total jobs / passed filter / ranked

This reduces the feeling that all metadata fields have equal importance.

## Information Architecture Rules

- run actions stay near the top
- export actions are grouped, not scattered
- metrics are summary-first, not essay-first
- outcomes stay visible without horizontal overflow
- stage-specific downloads belong in the timeline, not duplicated elsewhere

## UX Constraints

- no functionality should be removed without a replacement surface
- single-run lifecycle actions must remain obvious
- compacting must not hide success/failure outcomes
- run detail must remain useful for debugging failed and partial runs, not only succeeded runs

## Expected Outcome

After the cleanup:

- the run detail page reads from outcome to diagnosis instead of from buttons to noise
- the top of the page becomes smaller and easier to act on
- `Pipeline Outcome` remains visible in the enriched jobs table
- metrics become compact enough to scan quickly
- exports become grouped and understandable instead of repetitive

## Implementation Notes

This should be done as a UI restructuring change, not a data-contract rewrite.

Preferred strategy:

- keep existing route and data payloads where possible
- reshape presentation first
- only add minimal context in `app.py` if the template needs grouped export metadata or a precomputed health summary structure

## Acceptance Criteria

- top-level run detail actions no longer show a pile of parallel download buttons
- run detail exposes one grouped run-level export surface
- `Stage Quality Metrics` and `Late-Stage Reuse` no longer render as two large stacked cards
- enriched jobs inspection keeps `Pipeline Outcome` visible without horizontal clipping on normal desktop widths
- timeline still exposes stage-specific artifact downloads
- single-run lifecycle actions remain available on run detail
