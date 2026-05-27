---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: Implement FITCV run retry + crash-safe orchestration
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-05-27-15-24-fitcv-run-retry-orchestration-spec.md
targets:
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/control_plane_store.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv/enrich.py
  - src/fitcv/pipeline.py
  - config/runtime/control_plane.yaml
  - docker-compose.yml
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Implementation Plan: FITCV run retry + crash-safe orchestration

## Goal

Implement SSOT-first retry for FITCV control-plane runs, so worker crash and transient provider faults result in deterministic outcomes:

- retry within bounded policy when eligible
- terminal failure with explicit failure class when not eligible
- no "mysteriously complete" runs

## Key Deliverables

### Deliverable 1: SSOT attempt bookkeeping + run state machine

- Run SSOT includes attempt counters, selected attempt, and terminal failure class.
- Attempt SSOT exists (run_id, attempt_id, lease fields, status, error classification, retry metadata).
- sqlite-mode and BigQuery-mode produce identical semantics (symmetry/invariance).

### Deliverable 2: Retry execution (RQ retry + reconciler)

- Transient in-attempt failures retry automatically via RQ `Retry` within configured cap/backoff.
- Worker-crash / abandoned attempts retried (or failed terminally) via reconciler sweep based on SSOT leases.

### Deliverable 3: Operator controls + UI visibility

- Operator can:
  - cancel run (stops future retries)
  - trigger retry-now when policy allows
  - disable/enable auto-retry via config
- Run detail shows attempt history and clear terminal reasons.

### Deliverable 4: Test + evidence pack

- Unit tests cover classification + SSOT transitions.
- Integration test covers worker crash retry (kill worker or simulate lease expiry).
- `python scripts/hooks/run_validator.py --fast` passes.

## Task/Wave Breakdown

### Task 1: Define SSOT schema for attempts (sqlite + BigQuery symmetry)

**Purpose:**
- Add attempt record as SSOT-first truth source for retry bookkeeping.

**Files:**
- Inspect: `src/fitcv_cp/control_plane_store.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `src/fitcv_cp/control_plane_store.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Spec reviewed: `docs/superpowers/specs/2026-05-27-15-24-fitcv-run-retry-orchestration-spec.md`

**Steps:**
- [ ] Define attempt record shape (run_id, attempt_id, job_id, lease fields, status, error classification, error summary/details, retry metadata).
- [ ] Implement store-level CRUD for attempt records in sqlite store.
- [ ] Implement store-level CRUD for attempt records in BigQuery store (or define compatible mapping layer).
- [ ] Ensure run summary fields derivable from attempts without duplicating truth.

**Verification:**
- [ ] Add unit tests proving attempt lifecycle persistence + readback in both store modes.

**Exit Criteria:**
- Both stores expose same attempt semantics (no backend-only fields required for correctness).

### Task 2: Centralize failure classification helper (SSOT/symmetry/invariance)

**Purpose:**
- Make retry eligibility decision invariant across call sites.

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (only if shared error JSON schema needed)
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete (attempt records exist).

**Steps:**
- [ ] Implement a single helper that maps exceptions/HTTP errors to `transient|permanent|canceled|unknown` + stable `error_summary`.
- [ ] Ensure mapping covers observed class: httpx read timeout, 429/503, connection reset.
- [ ] Enforce size cap for error_details payload.

**Verification:**
- [ ] Add unit tests with representative exception objects / synthetic errors.

**Exit Criteria:**
- Worker uses exactly one classification path (no duplicated retry rules).

### Task 3: Implement worker attempt lease + terminalization (no “mysterious complete”)

**Purpose:**
- Ensure every run attempt ends in explicit SSOT terminal state or becomes `abandoned` via lease expiry.

**Files:**
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 attempt SSOT exists.
- Task 2 classification helper exists.

**Steps:**
- [ ] Enqueue path creates attempt record and sets run status to `queued`/`running` consistently.
- [ ] Worker starts attempt by acquiring lease in SSOT (compare-and-set).
- [ ] Worker periodically renews lease while running (or updates lease at key boundaries).
- [ ] Worker writes attempt terminal state on success/failure/cancel, with classification and summary.

**Verification:**
- [ ] Unit tests for lease acquisition invariants (no double-lease).
- [ ] Unit test for terminalization: success and failure write SSOT correctly.

**Exit Criteria:**
- Run cannot become terminal `succeeded` unless a `succeeded` attempt exists.

### Task 4: Wire RQ-native retry for transient in-attempt failures

**Purpose:**
- Use RQ to rerun the job function for transient failures without waiting for reconciler.

**Files:**
- Inspect: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 2 classification helper exists.

**Steps:**
- [ ] Add RQ `Retry` config at enqueue time based on policy (`enabled`, `max_attempts`, `backoff_seconds`).
- [ ] Ensure each retry attempt creates a new SSOT `attempt_id` and does not overwrite prior attempt.
- [ ] Ensure canceled runs do not retry (stop condition).

**Verification:**
- [ ] Unit tests: transient exception triggers retry schedule; permanent exception does not.

**Exit Criteria:**
- Retry bounded by `max_attempts` and visible in SSOT attempt timeline.

### Task 5: Implement reconciler sweep for abandoned/crash recovery

**Purpose:**
- Detect lease-expired running attempts and resolve deterministically (retry or fail).

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/app.py` (or new module under `src/fitcv_cp/`)
- Modify: `docker-compose.yml` (only if new service/cron needed)
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 3 lease semantics exist.

**Steps:**
- [ ] Implement reconciler function: scan SSOT for expired leases, mark attempt `abandoned`.
- [ ] If retry eligible and under cap: enqueue new attempt.
- [ ] If not eligible or over cap: terminalize run as `failed` with `failure_class=abandoned`.
- [ ] Decide scheduling mechanism:
  - web-side background tick, or
  - dedicated lightweight container/service.

**Verification:**
- [ ] Integration-style test: simulate lease expiry and assert new attempt enqueue or terminal failure.

**Exit Criteria:**
- Worker crash no longer leaves run ambiguous.

### Task 6: Operator actions + UI/run detail visibility

**Purpose:**
- Provide explicit operator control and make retry state observable.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: any templates/static UI surfaces under `src/fitcv_cp/` as needed
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 attempt store exists.

**Steps:**
- [ ] Add operator action endpoints: cancel, retry-now.
- [ ] Ensure cancel is SSOT terminal and blocks future retries.
- [ ] Display attempt list in run detail (attempt_id, started/finished, status, error summary, classification).

**Verification:**
- [ ] Tests for cancel stops retry.
- [ ] Tests for retry-now respects policy caps.

**Exit Criteria:**
- Operator can see and control retry state without reading raw worker logs.

### Task 7: Config SSOT integration + docs

**Purpose:**
- Make retry behavior adjustable via runtime config, shared by web/worker.

**Files:**
- Inspect: `config/runtime/control_plane.yaml`
- Modify: `config/runtime/control_plane.yaml`
- Inspect/Modify (if needed): config loader surfaces used by `src/fitcv_cp/app.py` + `src/fitcv_cp/worker_job.py`

**Preconditions:**
- Tasks 1–6 identify required config keys.

**Steps:**
- [ ] Add retry config keys under a single namespace (no duplicated toggles).
- [ ] Ensure docker runtime SSOT mount provides same config to web+worker.

**Verification:**
- [ ] Run with retry disabled: transient failures do not retry.
- [ ] Run with retry enabled + small cap: retries occur, then terminalize.

**Exit Criteria:**
- Retry policy adjustable without code edits.

## Verification

- [ ] `python -m pytest -q` (or repo test command subset covering `tests/test_fitcv_cp/`)
- [ ] `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. All Key Deliverables satisfied.
2. At least one integration proof exists for crash recovery (abandoned -> retry or fail).
3. Retry policy bounded and visible in SSOT.
4. sqlite and BigQuery modes behave equivalently for retry.

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
