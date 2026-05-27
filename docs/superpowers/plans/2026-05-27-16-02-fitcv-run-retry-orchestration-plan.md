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
  - src/fitcv_cp/store.py
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

### Task 0: Restore green baseline (prerequisite)

**Purpose:**
- Ensure `tests/test_fitcv_cp/` baseline is green before introducing retry changes, so regressions are attributable.

**Files:**
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/templates/_icons.html`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- None.

**Steps:**
- [x] Fix `ControlPlaneStore` wrapper to tolerate injected store functions returning `None` by using `_call_dict` and returning `{}`.
- [x] Add unicode star fallback marker in bookmark icons so UI tests can assert expected symbol presence.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp`

**Exit Criteria:**
- `tests/test_fitcv_cp/` passes.

### Task 1: Define SSOT schema for attempts (sqlite + BigQuery symmetry)

**Purpose:**
- Add attempt record as SSOT-first truth source for retry bookkeeping.

**Files:**
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Spec reviewed: `docs/superpowers/specs/2026-05-27-15-24-fitcv-run-retry-orchestration-spec.md`

**Steps:**
- [x] Define attempt record shape (run_id, attempt_id, job_id, lease fields, status, error classification, error summary/details, retry metadata).
- [x] Implement attempt SSOT as event-sourced `run_attempt.v1` events inside `pipeline_run_events` (sqlite+BQ parity; no schema migration).
- [x] Expose attempt read surface via `RunStore.list_run_attempt_payloads()` (single semantics across backends).
- [x] Ensure run terminal states stay symmetric with attempt SSOT (no “succeeded” without succeeded attempt; no retry when cancelled).

**Verification:**
- [x] Add unit tests proving attempt lifecycle persistence + readback in both store modes.

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
- [x] Implement a single helper that maps exceptions/HTTP errors to `transient|permanent|canceled|unknown` + stable `error_summary`.
- [x] Ensure mapping covers observed class: httpx read timeout, 429/503, connection reset.
- [x] Enforce size cap for error_details payload.

**Verification:**
- [x] Add unit tests with representative exception objects / synthetic errors.

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
- [x] Enqueue path sets run status `queued` and persists orchestration binding consistently (attempt SSOT starts in worker).
- [x] Worker starts attempt by emitting SSOT attempt-start event with lease window (`run_attempt.v1`).
- [x] Worker periodically renews lease while running (or updates lease at key boundaries).
- [x] Worker writes attempt terminal state on success/failure/cancel, with classification and summary.

**Verification:**
- [x] Unit tests for abandoned-attempt reconciliation invariants (cap enforcement, cancel blocks retry).
- [x] Unit test for terminalization ordering: success attempt event persisted before run marked `succeeded`.

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
- [x] Add RQ `Retry` config at enqueue time based on policy (`enabled`, `max_attempts`, `backoff_seconds`).
- [x] Ensure each retry attempt creates a new SSOT `attempt_id` and does not overwrite prior attempt.
- [x] Ensure canceled runs do not retry (stop condition).

**Verification:**
- [x] Unit tests: transient exception triggers retry schedule; permanent exception does not.

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
- [x] Implement reconciler function: scan SSOT for expired leases, mark attempt `abandoned`.
- [x] If retry eligible and under cap: enqueue new attempt and mark run `queued`.
- [x] If not eligible or over cap: terminalize run as `failed` with `failure_class=abandoned`.
- [x] Decide scheduling mechanism:
  - web-side background tick, or
  - dedicated lightweight container/service.

**Verification:**
- [x] Integration-style test: simulate lease expiry and assert new attempt enqueue or terminal failure.

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
- [x] Add operator action endpoints: cancel, retry-now.
- [x] Ensure cancel is SSOT terminal and blocks future retries.
- [x] Display attempt list in run detail (attempt_id, started/finished, status, error summary, classification).

**Verification:**
- [x] Tests for cancel stops retry.
- [x] Tests for retry-now respects policy caps.

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
- [x] Add retry config keys under a single namespace (no duplicated toggles).
- [x] Ensure docker runtime SSOT mount provides same config to web+worker.

**Verification:**
- [x] Unit evidence: retry disabled does not wire RQ retry (`tests/test_fitcv_cp/test_queue.py`).
- [x] Unit evidence: retry enabled wires bounded RQ retry (`tests/test_fitcv_cp/test_queue.py`) + cap enforcement in reconciler (`tests/test_fitcv_cp/test_reconciler.py`).

**Exit Criteria:**
- Retry policy adjustable without code edits.

## Verification

- [x] `python -m pytest -q tests/test_fitcv_cp` (PASS 2026-05-27)
- [x] `python scripts/hooks/run_validator.py --fast` (PASS 2026-05-27)

## Completion Criteria

1. All Key Deliverables satisfied.
2. At least one integration proof exists for crash recovery (abandoned -> retry or fail).
3. Retry policy bounded and visible in SSOT.
4. sqlite and BigQuery modes behave equivalently for retry.

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`





