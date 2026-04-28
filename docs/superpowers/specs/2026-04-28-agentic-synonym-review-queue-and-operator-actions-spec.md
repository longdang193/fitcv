---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - docs/intent/workstreams/threads/workstream-agentic-synonym-management/03-agentic-synonym-review-queue-and-approval.md
  - docs/intent/workstreams/threads/workstream-operator-control-plane/04-operator-control-plane-agentic-review-actions.md
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/models.py
  - config/taxonomy/skill_synonyms.yaml
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# Agentic Synonym Review Queue And Operator Actions

## Summary

Define the shared operator review surface for synonym proposals so proposals can
be queued, inspected, approved, rejected, or turned into run-scoped overlays
through one bounded action model instead of separate ad hoc UI and workflow
surfaces.

This spec builds directly on the proposal-engine spec and the operator
control-plane truth spec. It treats review as an operator decision surface, not
as an implicit side effect of suggestion generation.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is the Wave 5 shared-surface spec in the approved first-wave authoring
  map
- it depends on a stable proposal object and stable operator truth vocabulary
- it merges the synonym-review thread and the operator-control-plane review
  actions thread into one bounded review surface

Invariants:

- proposals remain advisory until an operator action changes their state
- operator review actions must preserve proposal identity and rationale
- run-scoped overlay adoption is distinct from shared-default promotion
- review surfaces must stay truthful to runtime and proposal state, not just UI
  convenience

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-synonym-management/03-agentic-synonym-review-queue-and-approval.md`
- `docs/intent/workstreams/threads/workstream-operator-control-plane/04-operator-control-plane-agentic-review-actions.md`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/worker_job.py`
- `config/taxonomy/skill_synonyms.yaml`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec linkage from
`parent_thread`.

Plan needed: `no` until the first-wave detailed-spec set is reviewed and we are
ready to sequence implementation.

## Problem

The repo already has pieces of a review-adjacent workflow:

- run-scoped mapping suggestion snapshots
- aggregate mapping suggestion export
- run-scoped overlay upload for staged runs
- run detail surfaces that already expose overlay state

What it lacks is a single shared review surface that answers:

- which proposals are waiting for review?
- what exactly is being approved or rejected?
- what action changes proposal state?
- when does approval create a run-scoped overlay versus a later shared-default
  candidate?

## Goals

- define one bounded review queue surface for proposal objects
- define the operator actions that move proposals through review
- preserve proposal evidence and rationale during approval or rejection
- connect review decisions cleanly to run-scoped overlay creation

## Non-Goals

- no shared-default synonym-file mutation workflow in this spec
- no downstream impact preview yet
- no implementation details for background jobs beyond the action contract

## Proposed Contract

## 1. Review Queue Object Model

The review queue should consume the proposal object defined in:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`

Queue rows must preserve:

- `proposal_id`
- proposal summary fields
- confidence
- rationale summary
- conflict summary
- proposal scope
- current review status
- source run or artifact refs

Rule:

- the queue is a projection over proposal objects, not a second proposal schema

## 2. Review Status Contract

Every proposal in the queue should have one bounded review state.

Minimum states:

- `proposed_unreviewed`
- `in_review`
- `approved_for_run_overlay`
- `rejected`
- `deferred`

Optional later states may be added for broader lifecycle needs, but the first
wave should keep the queue narrow and operator-readable.

Rule:

- status describes review state, not confidence and not final shared-canonical
  governance

## 3. Operator Action Contract

The shared review surface should support bounded explicit actions.

Required actions:

- `start_review`
- `approve_for_run_overlay`
- `reject`
- `defer`

Each action should preserve:

- `proposal_id`
- acting operator identity when available
- action timestamp
- optional bounded note or reason

Rule:

- actions change proposal review state explicitly
- actions must never silently discard proposal evidence or rationale

## 4. Approval Contract

First-wave approval should target run-scoped overlay creation, not shared
default mutation.

Approval rules:

- approving a proposal creates or updates a run-scoped overlay candidate for the
  relevant run
- approval must preserve which proposal ids contributed to the overlay
- approval should be reversible at the review-state level before a later shared
  promotion workflow exists

This keeps the safety ladder intact:

- suggestion
- proposal
- operator approval
- run-scoped adoption

## 5. Rejection And Deferral Contract

Rejected and deferred proposals are both meaningful outcomes.

### `rejected`

Meaning:

- the operator decided this proposal should not be applied for the current
  review context

### `deferred`

Meaning:

- the proposal remains potentially useful, but the operator is not ready to act
  on it yet, often because ambiguity or missing evidence remains

Rule:

- both states should preserve the proposal object and bounded review notes
- neither state should mutate shared canonical synonym config

## 6. Run-Scoped Overlay Creation

Run-scoped overlay creation is the immediate product action supported by this
review surface.

Rules:

- overlay creation should use approved proposal mappings as source material
- overlays remain run-scoped and do not alter the shared default synonym file
- the run detail surface should make it clear when a run overlay came from
  reviewed proposals versus a raw upload path
- overlay provenance should remain inspectable

## 7. Review Surface Placement

The review queue may live within the operator control plane, but it should be
treated as its own bounded decision surface.

Operator-truth requirements:

- queue status must reflect real proposal review state
- action availability must reflect real state transitions
- queue copy may be human-friendly, but must preserve proposal meaning
- the queue should not pretend rejected, deferred, and approved states are the
  same class of outcome

## 8. Relationship To Existing Overlay Upload Flow

The current manual overlay upload flow remains valid, but it is a different
entry path.

Distinction:

- raw upload path = operator supplies overlay YAML directly
- review-queue path = operator approves proposal objects that generate overlay
  entries

Rule:

- both paths may produce a run-scoped overlay
- the review queue must preserve that its overlays came from approved proposals,
  not from opaque manual edits

## 9. Shared-Surface Traceability

The review surface should preserve enough traceability for later observability
and impact work.

Minimum traceability fields:

- proposal id
- source run id
- action history summary
- resulting overlay refs when applicable

This prepares the repo for later:

- proposal trace specs
- downstream impact preview specs
- shared-canonical promotion specs

## Acceptance Criteria

- a reviewer can inspect one queue row and understand what proposal is being
  reviewed, with what confidence and rationale
- operator actions move proposals through explicit review states
- approval cleanly creates run-scoped overlay outcomes without mutating shared
  canonical config
- rejected and deferred states remain inspectable and distinct

## Risks

- if queue rows become their own schema, proposal meaning will drift between the
  engine and the UI
- if approval jumps straight to shared-config mutation, the safety boundary of
  review-first synonym management will collapse
- if the queue does not preserve action history, later trace and impact work
  will have to reconstruct it from weak signals

## Next Artifact

This completes the first-wave detailed-spec sequence from the current
spec-authoring map.

The next orchestration artifact should be an implementation execution map for
the approved subset that is ready to build.
