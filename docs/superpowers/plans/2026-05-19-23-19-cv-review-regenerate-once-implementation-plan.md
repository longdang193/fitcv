---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cv-review-regenerate-once-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-review-actions
parent_spec: docs/superpowers/specs/2026-05-19-23-16-cv-review-regenerate-once-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages:
  - cv_generation
---

## Goal

Implement bounded `regenerate_once` execution flow for CV review queue so operator action enqueues real single-item regeneration job, worker performs regeneration with lifecycle telemetry, and review queue remains pending for human decision.

## Key Deliverables

### Deliverable 1: Control-plane enqueue behavior for regenerate_once

Single-item and batch review routes enqueue dedicated regeneration jobs for eligible review-required rows, record request state, and emit explicit `cv_regenerate_once_requested` events.

### Deliverable 2: Dedicated queue + worker execution path

New queue API and worker entrypoint execute bounded `(run_id, job_url)` regeneration flow with `started` and terminal (`succeeded`/`failed`) lifecycle events and deterministic error handling.

### Deliverable 3: Debug-record mutation and queue-state preservation

Successful regeneration updates target debug record fields (`last_regenerated_at`, regenerated fingerprint/hash, regenerated markdown fields) while preserving `review_required` pending semantics and avoiding regressions for `approve`, `approve_as_is`, and `reject`.

## Task/Wave Breakdown

### Task 1: Add bounded regenerate queue contract

**Purpose:**
- introduce explicit enqueue API for CV regenerate-once jobs without changing full run queue semantics

**Files:**
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv_cp/orchestrator.py`
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`

**Preconditions:**
- current queue behavior for run submission remains baseline truth
- spec decision fixed on dedicated bounded worker path

**Steps:**
- [ ] Step 1: define queue function for regenerate-once enqueue with stable signature `(run_id, job_url, actor, note, redis_url)`.
- [ ] Step 2: wire inline and RQ modes to execute bounded worker function (parallel to existing run enqueue patterns).
- [ ] Step 3: preserve backward compatibility of existing run enqueue APIs.
- [ ] Step 4: add/extend queue tests for job creation payload and inline status behavior.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_queue.py -k regenerate_once`

**Exit Criteria:**
- dedicated queue API exists and passes targeted queue tests

### Task 2: Implement worker regenerate-once execution pipeline

**Purpose:**
- execute bounded regeneration for one review-required row and emit lifecycle terminal state

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- current debug payload schema and review-required row shape confirmed

**Steps:**
- [ ] Step 1: add worker entrypoint for regenerate-once job with `cv_regenerate_once_started` event emission.
- [ ] Step 2: load run + debug payload, resolve target record by `job_url`, and guard on `status=review_required`.
- [ ] Step 3: run bounded regeneration logic for target row, update row markdown fields + regeneration metadata (`last_regenerated_at`, fingerprint/hash).
- [ ] Step 4: emit success/failure terminal event with structured payload and preserve prior draft on failure.
- [ ] Step 5: add worker tests for happy path, missing target row, and regeneration failure paths.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_worker_job.py -k "regenerate_once or cv_regenerate_once"`

**Exit Criteria:**
- worker path emits started+terminal events and mutates only target row on success

### Task 3: Integrate regenerate enqueue into CV review action routes

**Purpose:**
- convert `regenerate_once` from action-log no-op into real job trigger for both single and batch handlers

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 and Task 2 complete
- action semantics for non-regenerate paths must remain unchanged

**Steps:**
- [ ] Step 1: in single-action route, enqueue regenerate job for `regenerate_once` and append `cv_regenerate_once_requested` event with queue job metadata.
- [ ] Step 2: in batch route, enqueue per eligible row, track applied/skipped/failed enqueue counts, and emit aggregate requested event summary.
- [ ] Step 3: persist action entries with regeneration request metadata while preserving existing `hitl_review_actions` compatibility.
- [ ] Step 4: ensure queue closure logic still depends on terminal human review statuses, not regeneration success.
- [ ] Step 5: add/extend app tests for single and batch regenerate enqueue behavior plus non-regression on `approve`, `approve_as_is`, `reject`.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "cv_review_action or review_batch or regenerate_once"`

**Exit Criteria:**
- route calls enqueue for regenerate_once and preserves existing non-regenerate behavior

### Task 4: Preserve review queue semantics with optional regeneration metadata

**Purpose:**
- expose regeneration freshness data without destabilizing high-blast-radius queue builder behavior

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- GitNexus impact risk acknowledged: `_build_hitl_review_queue` is CRITICAL blast radius
- any queue-shape change must be additive and backward-compatible

**Steps:**
- [ ] Step 1: keep `_build_hitl_review_queue` status resolution contract unchanged.
- [ ] Step 2: add only optional/pass-through regeneration metadata fields needed by operator surfaces and exports.
- [ ] Step 3: validate pending semantics remain true until terminal human action.
- [ ] Step 4: add regression assertions for queue item pending flags before/after regeneration success.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "review_queue or hitl_review"`

**Exit Criteria:**
- queue semantics unchanged, optional regeneration metadata available

### Task 5: End-to-end verification and contract guards

**Purpose:**
- prove acceptance criteria and guard against regressions across queue, worker, and route layers

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Inspect: `tests/test_fitcv_cp/test_queue.py`
- Inspect: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `docs/superpowers/specs/2026-05-19-23-16-cv-review-regenerate-once-spec.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: run targeted tests for queue, worker, and app regenerate paths.
- [ ] Step 2: run broader control-plane subset touching review and run-detail surfaces.
- [ ] Step 3: reconcile failing assertions with spec acceptance criteria and patch gaps.
- [ ] Step 4: capture concise evidence summary mapped to spec validation targets.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "regenerate_once or cv_review or review_queue"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- acceptance criteria evidenced by passing tests and validator checks

## Verification

- `pytest tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "regenerate_once or cv_review or review_queue"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied by merged code and tests
2. regenerate-once request, started, succeeded/failed lifecycle evidence is present and verifiable
3. review queue pending semantics preserved until terminal human action
4. validator and targeted test suite pass with no regressions in existing review actions
