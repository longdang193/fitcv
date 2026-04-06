---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Let admins attach a run-scoped synonym overlay before trigger for both run modes, while preserving a staged enrich-checkpoint override before rule_filter."
invariants:
  - The trusted base synonym config remains unchanged by run-scoped uploads.
  - A run-scoped synonym overlay belongs to one run only unless separately promoted.
  - `run_all` must support run-scoped synonym overlays only at trigger time, not mid-run.
  - `manual_staged` keeps the enrich -> rule_filter checkpoint override capability.
  - Downstream synonym-aware stages in a run consume one effective merged synonym map at continuation time.
---

# Pre-Trigger And Staged Synonym Overlay UX

## Triage

Feature type: MODIFY  
Summary: Add a pre-trigger run-scoped synonym-overlay input for both execution modes, while keeping the staged enrich-checkpoint upload as a later run-specific override before `rule_filter`.  
Reasoning: This extends the existing trigger surface and staged synonym-overlay lifecycle inside the current run-management feature instead of creating a new feature area. The work changes how operators attach run-scoped synonym config and clarifies the lifecycle difference between `run_all` and `manual_staged`.  
Invariants:
- The base shared synonym YAML remains the trusted default and is never mutated by run-scoped uploads.
- A run-scoped synonym overlay is snapshotted onto the run and stays isolated from other runs.
- `run_all` can use a run-scoped synonym overlay only at trigger time because there is no pause point for mid-run injection.
- `manual_staged` may use both a trigger-time run overlay and a later enrich-checkpoint override before `rule_filter`.
- The effective merged synonym map for a run remains deterministic and inspectable.
Dependencies:
- run trigger form handling in the admin control plane
- persisted run input snapshots
- existing run-scoped synonym overlay loading/runtime merge behavior
- staged checkpoint continuation after `enrich`
Affected stages:
- normalize
- enrich
- rule_filter
- ranking
- cv_analysis
- cv_generation
Affected features:
- trigger_run_management
- inspection_debugging
Primary lens: mixed
Affected docs:
- feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
- feature_history: `docs/features/trigger_run_management/history.md`
- feature_docs:
  - `none`
- cross_cutting_docs:
  - `docs/FitCV-pipeline.md`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
- readme: `none`
- generated:
  - `none`
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Migration needed: no
Risk level: medium

## Problem

The current UX only supports a run-scoped synonym-overlay upload in one narrow situation:

- `manual_staged`
- paused after `enrich`
- before continuing into `rule_filter`

That solves one debugging workflow, but it leaves an obvious gap:

- `run_all` has no way to attach a run-specific synonym overlay before trigger

So today users have inconsistent options:

- `run_all`: must rely on global/default synonym config
- `manual_staged`: can inject a run-scoped overlay only after `enrich`

This is not the best operator model, because a synonym overlay is fundamentally a run input, just like:

- job input
- candidate profile

The current staged-only upload also creates UI confusion:

- the upload is mixed into the action row on run detail
- the capability looks like a one-off repair action instead of a real run-owned input
- the lifecycle difference between `run_all` and `manual_staged` is implicit rather than explained

## Goals

- Let users attach a run-scoped synonym overlay before triggering a run.
- Support that pre-trigger upload for both:
  - `run_all`
  - `manual_staged`
- Keep the staged enrich-checkpoint upload as a later override before `rule_filter`.
- Make the synonym overlay feel like a first-class run input, not a hidden side path.
- Preserve a deterministic and inspectable effective synonym map for downstream stages.

## Non-Goals

- In-browser synonym editing in this rollout.
- Mid-run synonym upload for `run_all`.
- Promotion of run-scoped overlays into the trusted base config.
- Arbitrary stage-specific overlay editing at every checkpoint.
- Paste-YAML mode in phase 1.

## Current-State Summary

The project already supports:

- pre-trigger run setup for jobs input and candidate profile
- staged checkpoint pausing after `enrich`
- run-scoped synonym overlay upload after `enrich` in `manual_staged`
- runtime merge of synonym overlays on top of the base config
- inspection of effective synonym-overlay status on run detail

What is missing is a complete and coherent lifecycle:

- no trigger-time synonym overlay input
- `run_all` cannot use a run-scoped synonym file at all
- run detail upload is over-exposed in the top action row
- the operator must infer when staged mid-run upload is available and why

## Proposed Design

## 1. Treat Synonym Overlay As A First-Class Run Input

The trigger page should add a third run-input block:

- `Synonym Overlay`

It should live beside:

- `Jobs Input`
- `Candidate Profile`

Phase 1 recommendation:

- `Default Config`
- `Upload YAML`

This input should be optional. If no file is uploaded, the run uses:

- base/default synonym config only

If a file is uploaded, the run receives a run-scoped synonym overlay snapshot at trigger time.

This makes the capability available for both execution modes:

- `Run All`
- `Stage by Stage`

## 2. Keep The Staged Enrich-Checkpoint Upload As A Later Override

`manual_staged` should retain the existing special upload point after:

- `last_completed_stage = enrich`
- `next_stage = rule_filter`
- `status = awaiting_continue`

But that upload should be reclassified as:

- a run-scoped synonym-overlay override

rather than:

- the only path to run-scoped synonym upload

So the staged model becomes:

1. optional pre-trigger synonym overlay
2. optional later override after `enrich`
3. continue into `rule_filter` using the updated effective run overlay

This preserves the valuable stage-by-stage debugging workflow while removing the `run_all` gap.

## 3. Define Clear Overlay Precedence

Recommended precedence order:

```text
effective_synonym_map =
  base/default synonym config
  + pre-trigger run-scoped overlay
  + staged enrich-checkpoint override (if uploaded)
```

Phase 1 implementation recommendation:

- staged enrich-checkpoint upload replaces the existing run-scoped uploaded overlay for the rest of the run

That keeps the model simple:

- one active run-scoped overlay at a time

The important invariant is:

- every downstream stage sees one deterministic effective synonym map

## 4. Scope Mid-Run Upload To Stage By Stage Only

The UI and runtime should explicitly separate what each execution mode can do.

### `run_all`

Allowed:

- pre-trigger synonym overlay upload

Not allowed:

- mid-run upload

Reason:

- there is no checkpoint pause where the operator can safely inject it

### `manual_staged`

Allowed:

- pre-trigger synonym overlay upload
- staged override after `enrich` and before `rule_filter`

This should be presented as an intentional extra debugging capability of staged mode, not as an inconsistency.

## 5. Move The Staged Upload Out Of The Top Action Row

The current run-detail action row is already crowded with:

- lifecycle controls
- refresh
- optional synonym upload

This is the wrong place for a first-class run input.

Instead, run detail should render a dedicated `Synonym Overlay` card when relevant.

### For any run with trigger-time overlay state

Show:

- current overlay status
- source:
  - default only
  - trigger-time uploaded YAML
  - staged override uploaded YAML
- filename
- entry count

### For staged paused runs at `enrich -> rule_filter`

Show:

- current overlay state
- file picker
- upload button
- explanation:
  - `This override applies to this run only before continuing into Rule Filter.`

This makes the lifecycle legible and removes the awkward file picker from the top action row.

## 6. Persist Trigger-Time Overlay As Part Of Run Input Snapshot

The pre-trigger synonym overlay should be snapshotted onto the run at creation time, similar in spirit to other run-owned inputs.

Illustrative shape:

```json
{
  "schema_version": "run_synonym_overlay_v2",
  "source": "trigger_upload",
  "filename": "skill_synonyms.yaml",
  "uploaded_at": "2026-04-05T23:20:00Z",
  "entries": {
    "powerbi": "power bi",
    "gcp": "google cloud"
  }
}
```

If a staged override is later uploaded, the active run-owned overlay should be updated with metadata indicating:

- source = `staged_override`
- uploaded_at
- filename

The precise persistence field can be finalized in implementation, but the run detail and continuation logic must both read from the same run-owned contract.

## 7. Keep Validation Rules The Same For Both Upload Moments

Trigger-time and staged uploads should use the same validator.

Minimum rules:

- YAML must match the project synonym-overlay contract
- keys and values must be non-empty strings
- accepted structure must match the current loader contract

Operator-facing failure messages must be explicit and local to the UI surface where the upload happened.

## 8. Make Mode Constraints Explicit In The UI

The trigger page should explain the behavior clearly.

Suggested copy:

- `Attach a run-scoped synonym overlay for this run.`
- `Available for both Run All and Stage by Stage.`
- `Stage by Stage runs can also replace the overlay later after Enrich and before Rule Filter.`

The staged run detail card should explain:

- `This upload replaces the current run-specific synonym overlay before continuing to Rule Filter.`

This avoids the current hidden product rule where users have to guess why staged mode can do more.

## UX Summary

### Trigger page

Add a `Synonym Overlay` block with:

- `Default Config`
- `Upload YAML`

### Run detail

Add a dedicated `Synonym Overlay` card.

For normal runs:

- display current source and status

For staged paused runs at `enrich -> rule_filter`:

- display current source and status
- allow replacement upload

### Remove

- top-row synonym file picker in run detail

## Operational Flow

### `Run All`

1. Upload jobs input / candidate profile / optional synonym overlay.
2. Trigger run.
3. Pipeline uses the run-scoped overlay from the start.

### `Stage by Stage`

1. Upload jobs input / candidate profile / optional synonym overlay.
2. Trigger staged run.
3. Run pauses after `enrich`.
4. Operator may upload a replacement synonym overlay.
5. Continue to `rule_filter`.

## Acceptance Criteria

- The trigger page supports an optional run-scoped synonym-overlay upload for both `run_all` and `manual_staged`.
- The uploaded trigger-time overlay is snapshotted onto the run.
- `manual_staged` still supports a later override upload after `enrich` and before `rule_filter`.
- `run_all` does not expose or support mid-run synonym upload.
- Run detail shows a dedicated `Synonym Overlay` card instead of placing upload controls in the top action row.
- Downstream synonym-aware stages use one deterministic effective synonym map for the run.
- The base shared synonym config remains unchanged by either trigger-time or staged uploads.
