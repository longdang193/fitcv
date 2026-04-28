---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
  - docs/usage.md
related_features:
  - settings_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Operator Control Plane Settings Surface Alignment

## Summary

Define the bounded contract for the FitCV Settings page so the operator-facing
settings UI stays aligned with real runtime ownership, current editable
capabilities, task-first ergonomics, and settings-used inspection surfaces
instead of becoming a partially truthful configuration mirror.

This spec treats the Settings page as an operator control surface layered on top
of the `settings_system` feature contract. It must reveal what operators can
actually tune, what is fixed by runtime contract, and how persisted defaults,
per-run overrides, and run-scoped exports relate to one another.

## Triage

Layer: `change`  
Feature type: `MODIFY`

Reasoning:

- the bounded thread already exists under the operator-control-plane workstream
- the `settings_system` feature contract already defines the relevant settings
  UI capabilities
- the thread has no current linked detailed spec or implementation plan yet
- the work is broader than one template patch because it spans UI truth,
  persisted setting behavior, grouped saves, and operator-facing explanations

Invariants:

- the settings UI must only expose real editable runtime-backed controls
- controls fixed by runtime contract must render as metadata, not fake edits
- task-first operator ergonomics must remain intact
- grouped save behavior must preserve validation atomicity
- settings-used exports remain the run-scoped truth for what a run actually used

Dependencies:

- `docs/intent/workstreams/threads/workstream-operator-control-plane/03-operator-control-plane-settings-surface-alignment.md`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/settings_system/settings_system.yaml`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`
- `src/fitcv_cp/settings_schema.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread linkage from
`parent_thread`.

Plan needed: `yes` after this spec is approved.

## Problem

The Settings page already implements several strong ideas:

- task-first sectioning instead of schema-first dumping
- advanced disclosure for expert tuning
- grouped form saves
- metadata-only treatment for some fixed controls
- current-versus-draft feedback
- compact CV composition controls

But this surface is still vulnerable to drift in a few ways:

- new runtime capabilities can exist in code or config before the Settings page
  explains or exposes them well
- some controls may appear editable even when runtime ownership says they are
  fixed
- the relationship between baseline YAML, persisted settings, per-run
  overrides, and settings-used exports is not obvious from the UI alone
- agentic and late-stage settings can become discoverable only through code or
  tests rather than the operator surface

This thread exists to keep the Settings page truthful, scoped, and ergonomic as
the runtime evolves.

## Goals

- define what the Settings page must present as editable, fixed, or out of
  scope
- keep the UI aligned with `settings_system` capability ownership
- make task-based operator grouping stable and understandable
- preserve grouped validation and non-partial save behavior
- improve clarity around effective runtime settings versus future-default
  settings

## Non-Goals

- no redesign of the full control-plane visual system here
- no invention of a new configuration backend
- no replacement of the `settings_system` feature contract
- no attempt to expose every config file field as a UI control

## Current Surface In Scope

The current Settings page already includes:

- task sections such as selection, CV output, and run safety
- grouped cards such as retrieval settings and global job filters
- advanced disclosure blocks for expert tuning
- grouped save endpoints
- compact CV visibility/composition controls
- metadata-only handling for fixed single-option fields

The spec should refine and stabilize this shape rather than discarding it.

## Proposed Contract

## 1. Settings Truth Hierarchy

The Settings page should communicate runtime ownership in this order:

1. baseline checked-in configuration and runtime contract
2. persisted active settings defaults
3. per-run overrides captured at trigger time
4. run-scoped `settings-used` exports for historical truth

Rules:

- the Settings page edits future-run defaults, not past runs
- run-scoped truth belongs to `settings-used.json`, not the live settings form
- the UI must not imply that changing a default mutates historical run behavior

## 2. Editable vs Fixed Surface Rules

A settings field should appear as an editable control only when all of the
following are true:

- the runtime actually reads it as an operator-tunable setting
- the control maps to a real schema-backed persistence key
- the save path and validation path already exist

A field should render as metadata-only when:

- runtime contract fixes it to one supported value
- it remains relevant for explanation or provenance
- exposing it as editable would mislead operators

A field should stay out of the Settings page entirely when:

- it is retired compatibility baggage
- it is implementation-only glue
- it belongs to setup or deployment rather than operator tuning

## 3. Task-First Grouping Contract

The Settings page should remain task-first rather than schema-first.

Stable grouping goals:

- selection and early narrowing controls together
- ranking and fit-calibration controls together
- CV analysis tuning together
- CV output and validation together
- run-safety and pacing controls together
- expert-only tuning behind advanced disclosure

The grouping should optimize for:

- "what am I trying to improve?"
- "what stage or workflow does this affect?"
- "what can I safely ignore most of the time?"

## 4. Current vs Draft Feedback Contract

Every editable grouped surface should clearly distinguish:

- current effective persisted default
- operator draft value in the form
- whether anything is dirty

Requirements:

- dirty rows must remain identifiable before save
- grouped save summaries should surface `No changes`, `1 unsaved edit`, or
  equivalent bounded feedback
- current values should not disappear just because a field uses a baseline
  default instead of an explicit persisted override

## 5. Grouped Save And Validation Contract

Grouped save behavior is part of the Settings page contract, not just a backend
implementation detail.

Rules:

- validation is group-atomic
- partial saves are not allowed on invalid grouped submissions
- invalid submissions should preserve draft values in the returned page
- save actions should stay aligned with human-readable task/card boundaries

This is especially important for:

- retrieval settings
- CV output groups
- timing and runtime safety controls
- fit-calibration groups

## 6. Advanced Disclosure Contract

Expert-only tuning should remain available without crowding the default
operator workflow.

Requirements:

- advanced tuning blocks remain discoverable but collapsed behind disclosure
- disclosure labels should describe why the group is advanced
- moving a field into advanced disclosure must not hide whether it is still
  active and supported

The goal is not secrecy; it is operator focus.

## 7. CV Output Surface Contract

The CV output section is one of the densest operator-facing settings areas and
must stay especially truthful.

Requirements:

- editable controls remain limited to live CV generation and visibility fields
- retired formatting/detail controls stay absent
- fixed template/prompt/runtime fields stay metadata-only when appropriate
- the compact visibility matrix remains the preferred surface for section
  visibility toggles
- validation settings such as max pages remain clearly scoped as validation,
  not composition

## 8. Agentic And Late-Stage Settings Contract

The Settings page should better reflect the modern repo shape where late-stage
agentic behavior matters operationally.

This does not mean exposing every internal toggle. It means the Settings page
should make the active tunable seams discoverable and truthful for:

- retrieval breadth and downstream cost tradeoffs
- ranking and fit-calibration behavior
- `cv_analysis` semantic-alignment controls
- CV generation model and output constraints
- run pacing and timeout behavior

When agentic seams are active but fixed by contract, the UI should explain that
they are runtime-owned rather than pretending they are absent.

## 9. Relationship To Run-Scoped Observation

The Settings page must connect cleanly to inspection surfaces without becoming
an observability page itself.

Requirements:

- the UI should make it clear that `settings-used.json` is the historical
  source for a completed run
- operator-facing copy should distinguish between:
  - future default settings
  - per-run overrides
  - historical effective settings snapshots

Cross-links to root docs such as `docs/configuration.md`, `docs/usage.md`, or
`docs/observability.md` are allowed when they reduce confusion.

## 10. Thread-Owned Completion Criteria

This thread should be considered aligned when:

- every visible editable control maps to a real schema-backed runtime setting
- every fixed single-option field that still matters is rendered as metadata
- retired or unsupported fields are absent
- task-first grouping and advanced disclosure remain coherent
- grouped validation and draft preservation behavior are still true
- the page explains the relationship between defaults, overrides, and
  settings-used history more clearly than it does today

## Affected Runtime Surfaces

- `GET /admin/settings`
- `POST /admin/settings/{key}`
- `POST /admin/settings/group/{group_name}`
- `POST /admin/settings/section/{section_name}`
- `GET /settings`
- `POST /settings/{key}`

## Affected Capability IDs

- `settings_system.task-first-settings-ui`
- `settings_system.advanced-settings-disclosure`
- `settings_system.metadata-only-fixed-controls`
- `settings_system.compact-cv-visibility-controls`
- `settings_system.grouped-form-validation`
- `settings_system.per-run-overrides`
- `settings_system.run-safety-settings`
- `settings_system.cv-analysis-alignment-settings`
- `settings_system.cv-generation-settings`
- `settings_system.settings-used-exports`

## Validation Expectations

Implementation derived from this spec should prove:

- the settings page still renders stable task-first sections
- advanced groups remain disclosed correctly
- metadata-only fixed controls are not editable
- grouped save failures do not partially persist
- current-versus-draft rendering remains truthful
- removed and retired controls stay absent
- documentation and settings-page explanation stay aligned with current repo
  runtime shape

## Rollout / Revert

- rollback_trigger: the Settings page implies operator control over fields that
  runtime ignores, or hides active tunable seams behind inaccurate metadata or
  missing sections
- rollback_method: revert the settings-surface alignment patch as one bounded
  UI/schema/docs change so task grouping, grouped save behavior, and truth copy
  return to the previously known contract together
