---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
related_features:
  - trigger_run_management
  - inspection_debugging
  - cv_system
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Operator Control Plane Run Detail Truth

## Summary

Define the truth contract for runs list, run detail, stage progress, timeline,
artifact downloads, and lifecycle actions so the operator control plane reports
runtime state faithfully instead of smoothing away meaningful stage-owned
outcomes.

This spec depends on the semantic-spine stage-authority contract and the
deterministic truth outcome contract. It treats the control plane as a
presentation surface that must reveal runtime truth clearly, not a layer that
gets to rename it for convenience.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is a Wave 3 detailed spec from the approved first-wave authoring map
- it is bounded to operator truth surfaces rather than general UI polish
- it depends on stable stage and deterministic outcome vocabulary

Invariants:

- run detail is the operator ground-truth surface
- operator-facing labels are derived views of runtime truth
- lifecycle controls may change run progression, but not completed stage meaning
- artifact availability must match real run state, not optimistic UI assumptions

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md`
- `src/fitcv_cp/app.py`
- `src/fitcv/pipeline.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread linkage from
`parent_thread`.

Plan needed: `no` until the Wave 3 spec trio is complete and approved.

## Problem

The control plane already does a lot of good work:

- exposes runs list and run detail
- renders stage quality metrics and run health
- summarizes timeline events
- links stage artifact downloads
- exposes artifact bundles and settings-used exports
- supports cancellation, continue, archive, and repair actions

But run-detail truth is currently distributed across:

- pipeline statuses
- stage artifact summaries
- event messages
- operator-facing labels and badge classes
- artifact availability rules

Without a bounded truth contract, the control plane risks becoming easier to
read but less trustworthy.

## Goals

- define what the run detail page must treat as source truth
- separate derived operator labels from stage-owned runtime meaning
- keep stage progress, artifact availability, and lifecycle controls aligned
- prevent "friendly" UI copy from hiding meaningful blocked, skipped, or failed
  states

## Non-Goals

- no visual redesign of the control plane here
- no new review queue surface in this spec
- no implementation of new lifecycle controls beyond truth requirements

## Proposed Contract

## 1. Truth Hierarchy

The control plane should read runtime truth in this order:

1. run status and checkpoint fields
2. stage-owned artifact payloads and decision summaries
3. deterministic outcome mapping
4. derived operator labels and badges

Rule:

- the UI may summarize downstream, but it must not invert this hierarchy

## 2. Runs List Truth

The runs list should answer a small number of truthful questions:

- what lifecycle state is the run in?
- which stage has been reached or completed?
- is the run active, paused, terminal, archived, or stale?
- are late-stage outcomes healthy, blocked, skipped, or failing unusually?

Must stay true:

- list-level summaries may be compact
- compactness must not replace or contradict run-detail truth

## 3. Run Detail Truth

Run detail is the operator’s inspection source of truth.

It must reveal:

- run mode and checkpoint state
- stage sequence progress
- stage quality metrics
- timeline events
- artifact availability tied to real stage reachability
- job outcome surfaces derived from deterministic outcome rules

Run detail should prefer explicit truth over convenience copy for:

- blocked-by-reranker cases
- skipped-fit-gate cases
- validation failures versus generation failures
- stage-not-reached versus artifact-missing cases

## 4. Timeline Contract

Timeline entries are summaries of real events, not the event source itself.

Rules:

- timeline stage labels derive from actual event stage ids
- timeline messages may summarize artifact output counts
- a timeline row should link to stage artifacts only when that stage artifact is
  actually available
- timeline copy must not suggest a stage succeeded when the underlying stage
  truth is blocked, skipped, or failed

## 5. Outcome Display Contract

Operator-facing labels such as:

- `CV created`
- `Ranked, blocked by reranker fit`
- `Skipped after CV analysis`
- `Ranked, CV failed`

are allowed, but they are derived display labels.

Requirements:

- each display label maps to a deterministic outcome family
- each display label preserves access to the more precise stage-owned subreason
- badge severity must not erase the difference between blocked, skipped, and
  rejected outcomes

## 6. Stage Progress And Artifact Availability

Stage progress and artifact downloads must stay aligned.

Rules:

- a stage artifact is downloadable only when the run has actually reached that
  stage and the artifact exists
- "not reached" is different from "reached but missing artifact"
- the control plane should not imply stage success just because a later artifact
  bundle exists
- checkpoint state should reflect stage-owned completion, not approximate UI
  progress

## 7. Lifecycle Action Truth

Lifecycle actions include:

- cancel
- continue
- archive
- unarchive
- stale-cancellation repair

Rules:

- actions may change lifecycle state forward
- actions do not rewrite completed stage truth
- continue resumes from canonical next-stage state only
- archive and unarchive affect visibility state, not semantic run outcome
- repair actions should explicitly communicate why a stale state is being fixed

## 8. Run Health And Quality Metrics

Run health rows and stage quality metrics are summary surfaces layered on top of
stage artifacts.

Requirements:

- severity and helper labels must derive from actual metric families
- stage health summaries should remain stage-scoped, not generic dashboard
  sentiment
- negative and positive metrics must remain distinguishable

The control plane may simplify the reading experience, but it should not hide
the stage that owns the signal.

## 9. Relationship To Observability Event Contract

The control plane should consume:

- bounded event records
- stage artifact summaries
- deterministic outcome mapping

It should not:

- become the place where event semantics are invented
- reconstruct missing event meaning from badge text alone

Coordination rule:

- event contract defines bounded machine-observable facts
- run detail truth defines how those facts and artifacts are presented to an
  operator without distortion

## Acceptance Criteria

- a reviewer can distinguish blocked, skipped, rejected, and accepted run
  outcomes from the control plane without reading raw code
- stage artifact download availability matches real run state
- timeline rows summarize real events without overstating success
- lifecycle controls preserve already-completed stage truth

## Risks

- if display labels become the primary contract, operators will lose precise
  runtime understanding
- if artifact availability logic is too optimistic, the UI will promise data
  that does not exist
- if timeline summaries flatten stage-owned differences, the control plane will
  become friendly but unreliable

## Next Artifact

The parallel Wave 3 companions are:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`

After the Wave 3 trio is approved, the next sequential spec should be:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
