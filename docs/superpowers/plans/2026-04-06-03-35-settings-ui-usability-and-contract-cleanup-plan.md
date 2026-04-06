---
feature_type: modify
feature_name: settings_system
status: completed
summary: "Rework the admin settings UI into a task-first, basic-vs-advanced surface while reclassifying single-option pseudo-choice controls as metadata and preserving the canonical settings contract."
---

# Settings UI Usability And Contract Cleanup Plan

## Scope

This plan executes the cleanup defined in:

- [2026-04-06-03-20-settings-ui-usability-and-contract-cleanup-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/superpowers/specs/2026-04-06-03-20-settings-ui-usability-and-contract-cleanup-spec.md)

Primary source-of-truth docs:

- [settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/settings_system.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/history.md)

Primary implementation targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)

## Invariants

- No currently live runtime control may silently disappear from the effective settings contract.
- Canonical nested settings in `settings_schema.py` remain the active admin-editable source of truth.
- Settings persistence, grouped validation, and grouped-save semantics must remain intact.
- Settings edits continue to apply only to future runs.
- Single-option pseudo-choice controls may be reclassified as metadata, but their underlying runtime values must remain visible.

## Task 1: Reclassify single-option pseudo-choice controls

Convert low-value pseudo-choice controls from editable widgets into runtime metadata surfaces.

Targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)
- [test_settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- identify schema entries that currently expose only one valid option
- keep those values in the contract, but render them as read-only metadata instead of normal editable controls
- apply this immediately to:
  - `cv_preset`
  - `cv_analysis.semantic_alignment.model`
- add explicit helper copy that explains why the value is fixed today

Acceptance:

- the admin page no longer implies these fields are meaningful operator choices
- the current value remains visible on the page
- grouped save behavior is not disrupted by the metadata treatment

## Task 2: Reorganize the page into task-first groups

Replace the current flat registry-like organization with operator-task groupings.

Targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- reorganize the visible UI into:
  - `Selection`
  - `Ranking`
  - `CV Output`
  - `Run Safety`
  - `Advanced`
- keep backend grouping and validation ownership aligned with current grouped-save boundaries where that reduces migration risk
- if display grouping diverges from save grouping, make the mapping explicit in the template/controller code

Acceptance:

- the settings page reads like an operator workflow rather than a raw schema dump
- all existing editable settings remain discoverable
- section-level save actions still map cleanly to backend validation and persistence

## Task 3: Add Basic vs Advanced disclosure

Reduce first-load cognitive overhead by hiding expert-only tuning until intentionally expanded.

Targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- define the default-visible, high-signal setting surface
- move advanced tuning behind explicit expandable sections
- advanced candidates include:
  - semantic alignment tuning
  - timing and throttling controls
  - low-frequency expert knobs such as `channel_pool_size`
- keep defaults visible and readable without requiring expansion for the most common workflows

Acceptance:

- the first screen exposes the small set of settings most operators are likely to tune
- advanced controls remain available without being removed from the contract
- expanded advanced sections preserve validation and save behavior

## Task 4: Improve current-vs-draft visibility and dirty-state feedback

Make it obvious which values are currently effective and which edits are unsaved.

Targets:

- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- give the effective value column an explicit `Current:` treatment
- visually mark dirty rows where the draft differs from the effective setting
- surface section-level unsaved state
- add a clearer section reset/save affordance when a section is dirty

Acceptance:

- operators can quickly distinguish current values from editable draft values
- dirty rows and dirty sections are visible without scanning the whole form
- reset and save affordances remain consistent across sections

## Task 5: Upgrade helper copy and control semantics

Make descriptions more decision-oriented and reduce misleading operator expectations.

Targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)

Changes:

- rewrite high-signal descriptions to explain tradeoffs, not just implementation detail
- add warning-style helper copy for controls that are easy to over-interpret, especially:
  - `enrichment_concurrency`
- keep helper copy concise and operational

Acceptance:

- descriptions help operators understand impact on latency, recall, safety, or cost
- the page is more honest about what controls do and do not strongly influence

## Task 6: Compact the CV Output surface

Make the CV configuration area denser and easier to scan while preserving the remaining meaningful controls.

Targets:

- [settings.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/templates/settings.html)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- rework the CV section into a tighter visibility-focused layout
- keep:
  - `cv_generation_model`
  - section visibility toggles
  - `cv_max_pages`
- render section visibility in a denser matrix or table-like presentation instead of long repeated cards where appropriate
- ensure the compact layout still works on smaller widths

Acceptance:

- CV settings remain easy to understand
- the composition area consumes less vertical space
- no retired CV controls reappear

## Task 7: Preserve grouped validation and save semantics

Ensure the UX cleanup does not accidentally break the current grouped form contract.

Targets:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [test_settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- verify display grouping vs save grouping intentionally
- keep validation rules unchanged for:
  - ranking weight sums
  - threshold ordering
  - semantic lexical/semantic weight sums
- make sure metadata-only controls do not create dead form state or false dirty-state signals

Acceptance:

- existing section/group POST routes still work
- validation failures remain correctly scoped and understandable
- the cleanup stays presentation-first rather than mutating runtime semantics

## Task 8: Verification and regression coverage

Add focused coverage for the redesigned contract and UI behavior.

Suggested coverage:

- metadata-only single-option fields render as non-editable
- default-visible vs advanced sections render correctly
- dirty-state and current-value markers appear as expected
- grouped save routes remain intact
- CV composition surface still exposes only the live toggles and max-pages setting

Targets:

- [test_settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_settings_schema.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Verification commands:

- focused `pytest` slices for settings schema and settings page rendering/controller behavior
- `py_compile` for touched Python files

## Task 9: Sync feature docs and history

Update the source-of-truth docs after the UI contract cleanup lands.

Targets:

- [settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/settings_system.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/history.md)

Doc outcomes:

- clarify that no active runtime settings were removed in this cleanup
- note that single-option pseudo-choice controls are now rendered as metadata rather than editable dropdowns
- describe the task-first, basic-vs-advanced organization
- note any denser CV Output surface changes if they materially alter operator flow

## Rollout Notes

- do the metadata reclassification and grouping cleanup before deeper visual polish so the contract becomes honest early
- keep save-route and validation ownership conservative during the first pass
- treat presets for common operating modes as a later follow-up, not part of this cleanup unless implementation proves very cheap

## Completion Criteria

- the settings page is easier to scan and grouped around operator tasks
- pseudo-choice single-option controls no longer appear as ordinary editable decisions
- basic vs advanced disclosure reduces first-load complexity
- current-vs-draft state is clearer
- grouped validation and save semantics still work
- focused tests and `py_compile` pass
