---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
  - docs/api.md
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan F Reliability Hardening Failed Cancelled And Event Outbox

**Goal:** Harden runtime reliability while preserving current control-plane surfaces:

1. persist partial artifacts for `failed` and `cancelled` runs
2. add event outbox + retry + dead-letter flow for `pipeline_run_events`

## Scope

- add degraded but usable snapshot persistence for non-succeeded runs
- add durable event write workflow instead of best-effort-only event writes
- expose degraded persistence state in operator surfaces

## Non-Goals

- backend migration (BQ -> Postgres) in this plan
- replay-mode behavior changes

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Partial Snapshot Persistence On Failed/Cancelled
- [ ] Persist StageResult/stage-artifact partial snapshot on failure/cancel paths in `worker_job.py`.
- [ ] Include explicit degradation metadata (`snapshot_complete=false`, reason codes).
- [ ] Keep existing success-path snapshots unchanged.

## Task 2: Event Outbox + Retry + Dead-Letter
- [ ] Add outbox write path for reporter events.
- [ ] Add bounded retry policy and terminal dead-letter persistence.
- [ ] Ensure failed event writes are queryable and operator-visible.

## Task 3: Control Plane Visibility
- [ ] Add degraded snapshot/event-state indicators in run detail/export payloads.
- [ ] Keep current routes stable; only extend payloads.

## Task 4: Tests
- [ ] Add/extend tests for failed/cancelled snapshot persistence.
- [ ] Add tests for outbox retry and dead-letter fallback.
- [ ] Add tests for degraded-state visibility in app routes.

## Verification

```powershell
python -m pytest tests/test_fitcv_cp/test_worker_job.py
python -m pytest tests/test_fitcv_cp/test_app.py
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. Failed/cancelled runs retain usable partial artifacts.
2. Event writes are durable via outbox/retry/dead-letter path.
3. Degraded states are explicit to operators.
