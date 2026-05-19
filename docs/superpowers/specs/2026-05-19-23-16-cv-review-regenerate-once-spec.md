---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cv-review-regenerate-once-job-execution
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-review-actions
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
related_features: []
related_stages:
  - cv_generation
---

## Goal

Define bounded, deterministic regeneration flow for `regenerate_once` CV review action so action triggers real regeneration execution, emits lifecycle events, updates per-row regeneration metadata, and preserves reviewer decision gate.

## Key Deliverables

### Deliverable 1: Regenerate-once execution contract

Define control-plane and worker contract for single-item regeneration keyed by `(run_id, job_url)` without replaying full run.

### Deliverable 2: Lifecycle observability contract

Define event schema and emission points for requested, started, succeeded/failed lifecycle states.

### Deliverable 3: Review-queue state contract

Define required debug-record updates (`last_regenerated_at`, regenerated draft fingerprint/hash, regenerated draft fields) while keeping row in `review_required` pending reviewer decision.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current route/queue/worker behavior and isolate missing execution handoff

**Steps:**
- [ ] confirm `admin_run_cv_review_action` and batch route only persist action/event
- [ ] confirm no existing queue API for bounded CV regenerate task
- [ ] confirm current debug payload row fields and queue rendering dependencies

**Verification:**
- [ ] evidence mapped to exact symbols/files and current blast radius noted

**Exit Criteria:**
- missing execution path and required extension points are explicit

### Wave 2: Decision closure

**Purpose:**
- lock final regeneration architecture and state transition semantics

**Steps:**
- [ ] decide dedicated queue worker path vs full run replay path
- [ ] decide event stage names/payload schema
- [ ] decide debug-record mutation rules and failure semantics

**Verification:**
- [ ] all non-trivial design branches have chosen path and rejected alternatives

**Exit Criteria:**
- design yields deterministic behavior with bounded code churn

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof obligations for behavior, telemetry, and invariants

**Steps:**
- [ ] define route-level tests for enqueue handoff and event emission
- [ ] define worker-level tests for started/succeeded/failed paths
- [ ] define queue-state tests to ensure item remains pending after regeneration

**Verification:**
- [ ] each acceptance criterion has concrete proof target and evidence artifact

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Use dedicated bounded regenerate worker task

- context: current action route records action only; full-run replay adds unnecessary risk/scope
- choice: add dedicated enqueue + worker function for single CV regenerate job
- alternatives considered:
  - reuse full `continue_run` replay path with checkpoint pruning
  - inline regeneration in request thread
- impact:
  - new bounded queue API in `src/fitcv_cp/queue.py`
  - new worker entrypoint in `src/fitcv_cp/worker_job.py`
  - action routes enqueue task instead of no-op logging

### Decision: Explicit lifecycle events

- context: current path emits only `cv_review_action`; no execution observability
- choice: emit `cv_regenerate_once_requested`, `cv_regenerate_once_started`, `cv_regenerate_once_succeeded|failed`
- alternatives considered:
  - reuse `cv_review_action` only with overloaded payload
- impact:
  - deterministic audit trail for operator and debugging workflows

### Decision: Preserve reviewer gate after regenerate

- context: reviewer must inspect regenerated draft before approval/rejection
- choice: keep row status effectively pending (`review_required` remains authoritative), do not auto-finalize
- alternatives considered:
  - auto-approve regenerated draft
  - close queue row on successful regenerate
- impact:
  - queue semantics unchanged for closure logic; only draft content and regeneration metadata change

### Decision: Update row-level regeneration metadata in debug payload

- context: operator needs proof of regeneration freshness
- choice: update target debug record with `last_regenerated_at`, `regenerated_draft_fingerprint`, and regenerated markdown fields
- alternatives considered:
  - event-only tracking without mutating debug row
- impact:
  - review UI and exports can surface regenerated freshness deterministically

## Invariants

- `approve_as_is` semantics unchanged; still only path that finalizes CV artifact.
- `regenerate_once` must enqueue exactly one bounded regeneration task per action invocation.
- Queue row for target `job_url` remains review-pending after successful regeneration.
- Existing queue rendering contract for non-regenerated rows remains backward-compatible.
- Failure in regeneration must not corrupt prior draft fields; failure must be observable via event.

## Acceptance Criteria

- Posting `regenerate_once` to single-action route enqueues bounded regeneration task and returns redirect success path.
- Posting `regenerate_once` via batch route enqueues one task per selected eligible row.
- Worker emits `started` then terminal (`succeeded` or `failed`) event for each enqueued task.
- Successful regeneration updates target debug record timestamp + fingerprint/hash + draft fields.
- Queue item remains pending reviewer terminal action after regeneration.
- No regression in `approve`, `approve_as_is`, `reject` action flows.

## Non-Goals

- No redesign of overall run-mode/checkpoint lifecycle.
- No conversion of regenerate-once into full pipeline replay.
- No automatic reviewer decisioning or auto-approval logic.
- No cross-run CV dedupe/orchestration redesign.

## Risks and Mitigations

- Risk: duplicate enqueue from repeated clicks.
  - mitigation: idempotency guard keyed by `(run_id, job_url, unresolved regeneration state)` or short-window dedupe in action log.
- Risk: debug payload race between worker and concurrent actions.
  - mitigation: read-modify-write with latest payload fetch and conflict-safe append/update strategy.
- Risk: blast radius via `_build_hitl_review_queue` regressions.
  - mitigation: avoid schema-breaking changes; add optional fields only.
- Risk: worker failure leaves ambiguous operator state.
  - mitigation: mandatory failed event with error payload, preserve prior draft for fallback review.

## Validation Plan

- proof target: single-action regenerate request triggers bounded enqueue
  - method: route unit/integration test with mocked queue adapter
  - evidence: test asserts enqueue called once with `(run_id, job_url)` and `cv_regenerate_once_requested` event emitted
- proof target: batch regenerate enqueues per eligible row only
  - method: route integration test with mixed eligible/ineligible rows
  - evidence: call-count and payload assertions + skipped/failed counters
- proof target: worker lifecycle event completeness
  - method: worker unit tests for happy path and exception path
  - evidence: ordered events `[started, succeeded]` or `[started, failed]` with required payload fields
- proof target: debug record mutation correctness
  - method: worker/state test on synthesized payload
  - evidence: target row fields updated (`last_regenerated_at`, fingerprint, markdown fields); non-target rows unchanged
- proof target: queue pending semantics preserved
  - method: queue builder test before/after regeneration update
  - evidence: item remains pending until terminal human action
- proof target: no regression for non-regenerate actions
  - method: regression tests for `approve`, `approve_as_is`, `reject`
  - evidence: existing behavior and status transitions unchanged

## Completion Criteria

1. all Key Deliverables satisfied by approved implementation and tests
2. all acceptance criteria verified with recorded evidence from test outputs
3. downstream implementation plan created and approved before code execution
4. no unresolved high-risk items remain in risks list without explicit owner/deferral
