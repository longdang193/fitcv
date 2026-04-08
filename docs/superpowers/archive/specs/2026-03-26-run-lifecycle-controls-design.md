# Run Lifecycle Controls — Design Spec

**Date:** 2026-03-26
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The admin control plane can currently trigger and inspect runs, but it lacks lifecycle controls once a run exists.

This creates two operational gaps:

- an admin cannot stop a queued or running run when the input is wrong
- an admin cannot reduce list clutter without deleting historical runs

As the run table grows, the lack of archive controls also makes the default runs view noisier and less useful for day-to-day operations.

---

## Goal

Add persisted run lifecycle controls for:

1. stopping active runs
2. archiving and unarchiving old runs

The design should preserve auditability, avoid destructive deletion in v1, and make the runs list more operationally useful by hiding archived runs by default.

---

## Non-Goals

- Permanent hard-delete of runs in v1
- Rewriting the pipeline execution engine from scratch
- Guaranteeing immediate termination in the middle of any in-flight external call
- Per-user archive visibility preferences

---

## Design

### Lifecycle Actions

Introduce two explicit admin actions:

1. `Stop Run`
2. `Archive Run`

Also add the inverse archive action:

3. `Unarchive Run`

These are persisted server-side lifecycle controls, not browser-only UI state.

---

### Stop Run

`Stop Run` is an operational control for runs that should no longer continue consuming time or cost.

Eligible statuses:

- `queued`
- `running`

Not eligible:

- `succeeded`
- `failed`
- `cancelled`

Recommended behavior:

- if a run is still `queued`, stopping it should prevent pipeline execution and transition it directly to `cancelled`
- if a run is already `running`, stopping it should set a persisted cancellation request and transition the run to `cancelling`
- once the pipeline reaches a safe checkpoint and stops further work, the final status becomes `cancelled`

Queued-stop behavior needs to account for queue timing:

- if the queued job is still claimable in the queue, stopping it should prevent execution and mark the run `cancelled`
- if the worker has already claimed the job but the run still appears `queued` briefly, the stop request should be treated as a normal cancellation request once execution starts

This is cooperative cancellation, not force-kill semantics.

The system should stop at explicit safe checkpoints controlled by the orchestrator rather than attempting unsafe interruption of arbitrary in-flight work.

Suggested safe-checkpoint model:

- before enrichment begins
- between enrichment batches
- before AI scoring begins
- between AI scoring batches
- before CV generation begins

If a run finishes naturally before the cancellation request is honored, the existing terminal outcome remains authoritative.

Cancellation checks are performed only at explicit stage boundaries and batch boundaries the orchestrator already controls.

---

### Archive Run

`Archive Run` is a history-management control for completed runs.

Eligible statuses:

- `succeeded`
- `failed`
- `cancelled`

Not eligible:

- `queued`
- `running`
- `cancelling`

Archiving should:

- persist archive state on the run record
- hide the run from the default runs list
- preserve run detail, events, inspection data, and audit history

`Archive Run` is not deletion.

Recommended persistence model:

- `archived_at TIMESTAMP NULLABLE`
- optional `archived_by STRING NULLABLE`

If `archived_at` is null, the run is active.
If `archived_at` is set, the run is archived.

`Unarchive Run` clears `archived_at` and returns the run to the default runs list.

Archived runs remain fully accessible in run-detail pages and APIs.
Archive only changes default list inclusion and lifecycle-action availability.

---

### Status Model

Extend the lifecycle model to support cancellation explicitly.

Recommended statuses:

- `queued`
- `running`
- `cancelling`
- `cancelled`
- `succeeded`
- `failed`

If introducing `cancelling` is too large for the first implementation, it may be acceptable to keep the stored status as `running` while separately recording `cancel_requested_at`, but the preferred design is to show cancellation-in-progress explicitly.

Recommended cancellation metadata:

- `cancel_requested_at TIMESTAMP NULLABLE`
- `cancel_requested_by STRING NULLABLE`

This makes cancellation auditable and helps the worker decide whether it should continue.

#### Recommended Transition Rules

Stop action:

- `queued` -> `cancelled` when execution can still be prevented
- `running` -> `cancelling`
- `cancelling` -> `409 Conflict`
- terminal states -> `409 Conflict`

Completion after cancellation request:

- `cancelling` -> `cancelled` when a safe checkpoint is reached before natural completion
- `cancelling` -> `succeeded` if the run completes successfully before the request is honored
- `cancelling` -> `failed` if the run fails before the request is honored

---

### Runs List Behavior

The runs list should hide archived runs by default.

Recommended filters:

1. `Active`
2. `All`
3. `Archived`

Definitions:

- `Active`: non-archived runs only
- `All`: archived and non-archived runs
- `Archived`: archived runs only

The default view should be `Active`.

This keeps the main operational list focused without removing historical data.

The UI should label this filter clearly enough that admins understand it means non-archived runs, not only currently executing runs.

---

### Run Detail Actions

Run detail should expose lifecycle actions in the page header or metadata action area.

Action rules:

- show `Stop Run` for `queued` and `running`
- show disabled or informational state for `cancelling`
- show `Archive Run` for `succeeded`, `failed`, and `cancelled` when not archived
- show `Unarchive Run` for archived runs

The action area should clearly communicate why an action is unavailable when the run is not eligible.

`cancelling` is not archive-eligible because it is still operationally active.

Examples:

- `Cannot archive a running run`
- `Run is already cancelled`

---

### Audit and Safety Model

Lifecycle controls must preserve operational traceability.

Stopping or archiving a run should not remove:

- pipeline events
- structured jobs
- filter results
- snapshot inspection data

Archive is purely a control-plane visibility and state flag.
It does not delete or mutate pipeline-produced artifacts.

Recommended audit fields:

- `cancel_requested_at`
- `cancel_requested_by`
- `archived_at`
- `archived_by`

This keeps lifecycle actions explainable in run detail and future admin reporting.

Lifecycle actions should also append explicit audit events to the run event stream.

Recommended lifecycle events:

- `cancel_requested`
- `run_cancelled`
- `run_archived`
- `run_unarchived`

---

### Error Handling

The system should reject invalid lifecycle actions with clear server-side rules.

Lifecycle endpoints are not silently idempotent.
Repeated invalid actions should return conflict rather than pretending to succeed.

Examples:

- stopping a `succeeded` run returns `409 Conflict`
- archiving a `running` run returns `409 Conflict`
- unarchiving a non-archived run returns `409 Conflict`
- unknown run id returns `404`

The UI should surface a short error message and preserve the current page state.

---

### Initial Scope

Implement in v1:

- persisted stop/cancel request model
- persisted archive/unarchive model
- runs list filters for `Active`, `All`, `Archived`
- run detail lifecycle action buttons

Do not implement in v1:

- hard delete
- bulk archive
- automated retention policy

Retention rules can be added later on top of the same archive model.

---

## Acceptance Criteria

- [ ] Admin can request stop for `queued` and `running` runs
- [ ] Queued runs can transition to `cancelled` without starting pipeline work
- [ ] Running runs support cooperative cancellation at safe checkpoints
- [ ] Cancellation is checked only at explicit orchestrator-controlled checkpoints
- [ ] Cancellation is persisted and auditable
- [ ] The lifecycle model supports `cancelled`, and preferably `cancelling`
- [ ] Admin can archive terminal runs without deleting their history
- [ ] Archive state is persisted on the run record
- [ ] Archived runs are hidden from the default runs list
- [ ] Runs list supports `Active`, `All`, and `Archived` filters
- [ ] Admin can unarchive an archived run
- [ ] Run detail exposes the correct lifecycle action for the run’s current state
- [ ] Invalid lifecycle actions return clear server-side errors
- [ ] Lifecycle actions append corresponding audit events to the run event stream
- [ ] Archived runs remain accessible through run detail and API views
- [ ] Archive state does not delete or mutate pipeline-produced artifacts
- [ ] Run events, inspection data, and audit history remain available after archive or cancellation
