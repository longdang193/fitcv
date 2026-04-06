---
feature_type: modify
feature_name: run_lifecycle_controls
status: draft
summary: "Broaden cancel eligibility so paused manual runs in `awaiting_continue` can be cancelled directly into the terminal `cancelled` state."
---

# Awaiting-Continue Cancel Eligibility Adjustment

## Summary

Broaden run-cancel eligibility so `awaiting_continue` runs are cancellable.

This keeps the lifecycle model simple:

- non-terminal runs can be cancelled
- terminal runs cannot be cancelled

For this rollout, that means:

- cancellable:
  - `queued`
  - `running`
  - `awaiting_continue`
- not cancellable:
  - `succeeded`
  - `failed`
  - `cancelled`

`awaiting_continue` should use a direct terminal-cancel path:

- no queue cancellation
- no cooperative `cancelling` intermediate state
- immediate transition to `cancelled`

## Triage

Feature type: MODIFY
Summary: Allow paused manual runs in `awaiting_continue` to be cancelled directly, while keeping terminal runs non-cancellable.
Reasoning: The current lifecycle model treats `awaiting_continue` as ineligible for cancel even though it represents unfinished work. This creates an inconsistent operator experience where a paused non-terminal run cannot be intentionally ended.
Invariants:
  - `queued` and `running` retain their current cancel semantics
  - `awaiting_continue` transitions directly to `cancelled`
  - `succeeded`, `failed`, and `cancelled` remain non-cancellable
  - single-run and bulk cancel use the same eligibility rules
  - each successful cancel still appends its lifecycle audit event
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
Risk level: low

## Current Problem

Today, cancel only applies to:

- `queued`
- `running`

This means a manual staged run that is paused in `awaiting_continue` cannot be ended intentionally, even though:

- it is not finished
- it still represents pending pipeline work
- the operator may have decided the run should not continue

Operationally, that is awkward because `awaiting_continue` is already a controlled pause point, so it is actually the safest state to cancel directly.

## Recommendation

Treat `awaiting_continue` as cancellable.

Use this rule:

- if the run still has unfinished work, it can be cancelled
- if the run is already terminal, it cannot

That produces a cleaner lifecycle model than the current “queued or running only” rule.

## Goals

- allow operators to cancel paused staged runs without resuming them first
- keep cancel behavior consistent between single-run and bulk actions
- preserve the current queue and cooperative-cancellation behavior for `queued` and `running`
- keep terminal-state rules simple and easy to explain

## Non-Goals

- adding a new lifecycle status
- changing archive eligibility
- changing continue/resume behavior
- changing the meaning of `cancelling`
- adding deletion or force-kill semantics

## Proposed Lifecycle Rules

### Cancel Eligibility

Eligible:

- `queued`
- `running`
- `awaiting_continue`

Not eligible:

- `succeeded`
- `failed`
- `cancelled`

This rollout does not broaden cancel to archived terminal runs or other already-finished states.

### Cancel Execution Paths

#### 1. Queued

Keep the current behavior:

- cancel from queue if still claimable
- otherwise mark directly `cancelled` if not yet claimed
- if already claimed, use the cooperative-cancel path

#### 2. Running

Keep the current behavior:

- transition to `cancelling`
- stop at the next safe checkpoint
- end as `cancelled` once the cancellation request is honored

#### 3. Awaiting Continue

Use a direct terminal-cancel path:

- set status to `cancelled`
- set `finished_at`
- append a lifecycle event explaining the run was cancelled while paused for manual continuation

No queue cancellation or `cancelling` transition is needed because there is no active worker progression at that point.

## Single-Run And Bulk Consistency

The single-run `Stop Run` action and the bulk `Cancel selected` action must share the same eligibility logic.

That means:

- both surfaces allow `awaiting_continue`
- both surfaces reject `succeeded`, `failed`, and `cancelled`
- both surfaces report non-eligible runs clearly

The user should never see different answers for the same run depending on which cancel surface they use.

## UI Expectations

### Runs List

`awaiting_continue` rows should now be considered cancellable for both:

- row-level action logic
- bulk cancel eligibility

The wording can stay `Stop Run` or `Cancel selected` as long as the behavior is consistent.

### Run Detail

Run detail should expose the cancel action for `awaiting_continue` just as it does for other cancellable states.

The operator should not need to resume the run before ending it.

## Audit Expectations

Successful cancellation of an `awaiting_continue` run must still append an explicit lifecycle event.

Recommended event message:

- `Run cancelled while awaiting manual continuation`

This keeps paused-run termination visible in the audit trail and makes it distinguishable from:

- queue cancellation
- cooperative mid-flight cancellation

## Acceptance Criteria

- single-run cancel accepts `awaiting_continue`
- bulk cancel accepts `awaiting_continue`
- cancelling `awaiting_continue` transitions directly to `cancelled`
- `queued` and `running` keep their existing cancel behavior
- `succeeded`, `failed`, and `cancelled` still return non-cancellable responses
- the event stream clearly records cancellation of paused manual runs
