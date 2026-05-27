---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: FITCV run retry + crash-safe orchestration (SSOT/symmetry/invariance)
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_contracts.py
  - config/runtime/control_plane.yaml
  - docker-compose.yml
related_features: []
related_stages: []
---

# Detailed Spec: FITCV run retry + crash-safe orchestration (SSOT / symmetry / invariance)

## Goal

Define retry semantics for FITCV control-plane runs so worker crash and transient faults do **not** yield “mysteriously complete” runs.

Primary outcome: run lifecycle becomes **explicit, auditable, and retryable** under clear policy, while preserving SSOT, symmetry, and invariance across storage modes (sqlite / BigQuery) and across services (web / worker).

## Key Deliverables

### Deliverable 1: Retry policy contract (what retries, when, how many)

- Clear policy for when a run/job attempt is retried vs marked terminal failure.
- Explicit separation between:
  - *transient failures* (eligible for retry)
  - *permanent failures* (no retry; fail fast)
  - *operator-canceled* (no retry)

### Deliverable 2: SSOT attempt bookkeeping + run state machine

- Single SSOT record for attempts (count, timestamps, last error, next retry time, terminal cause).
- Run state transitions become symmetric and invariant regardless of storage backend.

### Deliverable 3: Crash-safe reconciliation (abandoned detection)

- Defined mechanism to detect "worker died mid-run" cases and resolve them deterministically:
  - either requeue attempt, or mark failed, depending on policy and limits.

### Deliverable 4: Validation evidence plan

- Concrete proof targets + expected evidence artifacts (logs/events/DB rows) that demonstrate retry works in real failure modes.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current behavior, boundaries, and constraints before proposing decisions

**Steps:**
- [ ] Confirm current enqueue + worker execution contract (`src/fitcv_cp/queue.py`, `src/fitcv_cp/worker_job.py`).
- [ ] Confirm run status persistence surfaces (sqlite SSOT vs BigQuery SSOT).
- [ ] Identify where “complete” is currently set, and under what conditions.
- [ ] Enumerate failure classes observed in live runs (timeouts, provider overload, container crash).

**Verification:**
- [ ] Current-state understanding explains observed symptom: "worker crash can look complete" and "no retry".

**Exit Criteria:**
- No retry design decision depends on unstated assumptions about RQ behavior.

### Wave 2: Decision closure

**Purpose:**
- resolve design choices and document why chosen shape preferred

**Steps:**
- [ ] Decide retry execution mechanism(s): RQ-native retry, reconciler, or hybrid.
- [ ] Decide SSOT schema: attempt fields, error classification, idempotency keys.
- [ ] Decide run/job state machine transitions and invariants.
- [ ] Decide operator controls (stop, requeue, override).

**Verification:**
- [ ] Each major design question has documented decision or explicit deferral.

**Exit Criteria:**
- Policy bounded: max attempts, backoff, terminal states, cancellation semantics.

### Wave 3: Validation and approval readiness

**Purpose:**
- prepare spec for implementation handoff by making proof expectations explicit

**Steps:**
- [ ] Define validation plan and evidence artifacts.
- [ ] Define minimal integration scenarios to prove crash retry.
- [ ] Define metrics to detect overload vs big input vs systemic regressions.

**Verification:**
- [ ] Validation proves intended behavior and invariant preservation.

**Exit Criteria:**
- Spec ready for implementation planning (`skill-writing-plans`).

## Design Decisions

### Decision: Use hybrid retry (RQ Retry + reconciler sweep)

- context: RQ retry covers *exceptions thrown by job function* but does not fully cover *worker process death* or *lost heartbeats* without additional reconciliation.
- choice: Implement **two-layer retry**:
  1) **RQ-native retry** for transient exceptions inside a running worker attempt.
  2) **Reconciler sweep** (periodic control-plane task) to detect "attempt started but no terminal event within SLA" and deterministically resolve (retry or fail).
- alternatives considered:
  - RQ Retry only
  - Reconciler only (no RQ retry)
- impact:
  - Requires attempt SSOT schema and heartbeat/lease semantics.
  - Produces symmetric behavior regardless of RQ nuances.

### Decision: SSOT owns truth; RQ job state becomes advisory

- context: RQ job status can be inconsistent across restarts; "finished" does not necessarily mean "business complete".
- choice: Treat run lifecycle as **SSOT-first**:
  - SSOT run record is authoritative for "pending/running/succeeded/failed/canceled".
  - RQ job id(s) are references for execution, not truth.
- alternatives considered:
  - Treat RQ as truth and derive SSOT
- impact:
  - Requires explicit terminalization logic and idempotency.

### Decision: Retry policy keyed by failure classification

- context: Not all failures should retry. Timeouts/429/connection resets often transient; schema violations often permanent.
- choice: Introduce normalized failure classes:
  - `transient` (retry)
  - `permanent` (no retry; fail fast)
  - `canceled` (no retry)
  - `unknown` (retry with conservative cap)
- alternatives considered:
  - Retry everything up to N
  - No classification (manual only)
- impact:
  - Requires consistent mapping from exceptions/HTTP errors into class.

### Decision: Idempotency via attempt tokens + derived artifacts

- context: Retrying must not duplicate side effects or corrupt artifacts.
- choice:
  - Each attempt has immutable `attempt_id`.
  - Artifacts written with attempt context; “latest successful attempt” becomes selected view.
  - Event emission includes attempt identity.
- alternatives considered:
  - Overwrite in place
- impact:
  - Requires clear read strategy: “selected attempt” vs “all attempts”.

## Acceptance Criteria

1. Worker crash case becomes explicit: run ends in `failed` with `failure_class=abandoned` (or retried) rather than appearing "complete".
2. Transient provider overload case retries automatically up to configured limits and either succeeds or fails with explicit terminal reason.
3. SSOT shows attempt count and timeline for any run.
4. Behavior identical across sqlite SSOT and BigQuery SSOT (symmetry/invariance).
5. Operator can disable automatic retry via config without code changes.

## Non-Goals

- Designing LLM prompt optimization or chunking strategy.
- Guaranteeing provider SLA; retries mitigate but do not eliminate overload.
- Cross-run dedupe policies (this spec focuses on retry and lifecycle correctness).
- Changing enrichment semantics (only orchestration + bookkeeping).

## Design Details

### State machine (run-level)

Run status SSOT-owned and must be one of:

- `queued` (run accepted; no attempt started)
- `running` (attempt currently leased to worker)
- `succeeded` (terminal success)
- `failed` (terminal failure)
- `canceled` (terminal operator cancel)

Derived/aux fields (SSOT):

- `attempt_count`
- `max_attempts`
- `current_attempt_id` (nullable)
- `last_error` (structured)
- `failure_class` (nullable, set only on terminal)
- `next_retry_at` (nullable)

### Attempt schema (job-level)

Each attempt record must contain:

- identity:
  - `run_id`
  - `job_id`
  - `attempt_id` (UUID)
- lease:
  - `leased_by_worker_id`
  - `lease_started_at`
  - `lease_expires_at`
- outcome:
  - `status` (`running|succeeded|failed|canceled|abandoned`)
  - `finished_at` (nullable)
  - `error_classification` (`transient|permanent|canceled|unknown`)
  - `error_summary` (short, stable string)
  - `error_details_json` (optional, size-capped)
- retry:
  - `retry_eligible` (bool)
  - `retry_after_seconds` (int)

SSOT placement principle:

- Attempt records live in same SSOT store as run records (sqlite or BigQuery).
- Web and worker both read same SSOT path (symmetry) and produce same row shape (invariance).

### Retry execution

#### 1) RQ Retry (in-attempt transient errors)

- When attempt throws transient-classified error, allow RQ re-run job function.
- Backoff schedule and max retries configurable.
- Each RQ retry increments *attempt_count* in SSOT and creates new `attempt_id`.

#### 2) Reconciler sweep (crash/abandon)

- Periodic task scans SSOT for `running` attempts where `lease_expires_at < now` and no terminal record.
- For each:
  - mark attempt `abandoned`
  - if `attempt_count < max_attempts` and not canceled:
    - enqueue new attempt
  - else:
    - terminalize run as `failed` with failure_class `abandoned`

### Failure classification mapping

Canonical mapping (invariance):

- HTTP 429, 503, connection reset, read timeout => `transient`
- input/schema validation failure, deterministic parsing errors => `permanent`
- operator cancel => `canceled`
- unknown exceptions => `unknown` (treat as transient but cap retries lower)

Classification must be done once in shared helper, not re-implemented per call site (symmetry).

### Operator controls

Config keys (SSOT):

- `fitcv_cp.retry.enabled` (bool)
- `fitcv_cp.retry.max_attempts` (int)
- `fitcv_cp.retry.backoff_seconds` (list[int] or base+multiplier)
- `fitcv_cp.retry.lease_seconds` (int)
- `fitcv_cp.retry.reconciler_interval_seconds` (int)

Constraint: config resolved from same runtime SSOT for web+worker.

## Invariants

- SSOT: Exactly one authoritative run lifecycle record per `run_id`.
- Symmetry: sqlite and BigQuery stores expose same semantic fields for run + attempt.
- Invariance: run state machine does not depend on storage backend or service role.
- Idempotency: Retrying does not duplicate terminal artifacts; selection of "winning attempt" deterministic.
- Cancellation: If operator marks run canceled, no future retry enqueue occurs.
- Boundedness: Retry loops always bounded by `max_attempts`.

## Risks and Mitigations

- Risk: Reconciler races with active worker and double-enqueues.
  - Mitigation: lease/compare-and-set updates in SSOT; worker renews lease; reconciler only acts on expired leases.

- Risk: Attempt metadata grows without bound.
  - Mitigation: cap error_details size; optionally retain only last K attempts (policy explicit).

- Risk: Misclassification retries permanent failures and wastes capacity.
  - Mitigation: start conservative; log classification; allow operator override / quick config tweak.

- Risk: RQ retry semantics differ across versions.
  - Mitigation: SSOT-first design; treat RQ as advisory; reconciler enforces truth.

## Validation Plan

- proof target: Worker crash does not yield "complete" run
  - method: integration run + kill worker container mid-attempt
  - evidence: SSOT shows attempt `abandoned` + either retry attempt starts or run terminalizes `failed` with `failure_class=abandoned`

- proof target: Transient overload retries and eventually succeeds or fails deterministically
  - method: throttle provider / inject 429/timeout fault; run pipeline
  - evidence: attempt timeline shows retries with backoff; terminal state matches policy

- proof target: Symmetry across sqlite and BigQuery SSOT
  - method: run same scenario twice, once per store mode
  - evidence: same state transitions + same UI-visible counters/attempts

- proof target: Cancellation stops retries
  - method: cancel run while queued or running
  - evidence: no further enqueue; reconciler skips canceled runs; SSOT terminal `canceled`

- proof target: Boundedness of retries
  - method: force persistent transient failure, `max_attempts=2`
  - evidence: after 2 attempts, run terminal `failed` with explicit reason

## Completion Criteria

1. All Key Deliverables satisfied.
2. Spec has no unresolved core decisions needed for plan.
3. Validation Plan includes at least one crash test and one overload test with explicit evidence artifacts.
4. Implementation can proceed without inventing policy not stated here.

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
