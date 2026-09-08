---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
created: 2026-09-08
name: scan-redis-decommission
promotion_gate: >-
  Keep status proposed until implementation and verification prove that local
  and packaged Scan execution works without Redis while server and Docker Scan
  execution remains RQ-backed. Do not expand this plan beyond that boundary.
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/main.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_queue.py
  - README.md
  - docs/configuration.md
verification_only:
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/local_app.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - tests/test_fitcv_cp/test_local_app.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_orchestrator.py
  - tests/test_fitcv_cp/test_local_dev_scripts.py
  - tests/conftest.py
  - docker-compose.yml
  - docker-compose.isolated.yml
  - start_worker.ps1
  - start_web.ps1
  - stop_fitcv.ps1
  - requirements.txt
  - pyproject.toml
  - uv.lock
  - docs/setup.md
  - docs/fitcv-control-plane-setup.md
  - docs/architecture.md
  - frontend/src/features/scans/types.ts
  - frontend/src/test/scans.test.ts
  - frontend/e2e/runs.spec.ts
preserved_files:
  - requirements.txt
  - pyproject.toml
  - docker-compose.yml
  - start_worker.ps1
  - uv.lock
---

# Goal

Make managed Scan execution Redis-free in local and packaged mode. Reuse the
existing local execution path and `LocalJobExecutor`. Preserve server and
Docker Scan RQ execution, non-Scan Redis/RQ behavior, Scan API contracts,
provider acquisition, immutable snapshots, cancellation, output integrity,
and Scan-to-Run input behavior.

## Implementation Outcomes

### Local and packaged Scan execution

- Local mode sets `FITCV_LOCAL_MODE=1`, enables inline execution, removes
  `REDIS_URL`, and dispatches Scan work through the existing
  `LocalJobExecutor`.
- `execute_scan` remains execution boundary. SQLite remains persistence and
  status source. Existing Scan row fields and queue identity projection stay
  compatible.
- Local and packaged Scan creation, Run Again, polling, cancellation,
  restart-safe existing local behavior, terminal output, and Scan-to-Run
  copying work with Redis absent or unreachable.

### Server and Docker preservation

- Server and Docker mode continue using existing `REDIS_URL`, RQ queue
  identity, Scan worker startup, and `enqueue_scan_with_job_id` behavior.
- Run orchestration, Candidate Profile stage work, CV regeneration, shared
  queue code, package dependencies, Docker services, and worker scripts remain
  unchanged.

### Documentation and proof

- Runtime docs describe local/packaged Scan as Redis-free and server/Docker
  Scan plus non-Scan work as Redis/RQ-backed.
- Tests prove both mode boundaries, no accidental Redis call from local Scan,
  unchanged server RQ dispatch, and unchanged API/status/output contracts.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `plan-bound-execution`
- Required skills: `skill-writing-plans`, `skill-chief-of-staff`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed target files, inspect verification-only files, and run declared local checks
- User-approval actions: push, merge, publication, destructive recovery, discard, cleanup, or edits outside listed targets
- Top-level MAIN lanes: local/server wiring (Task 1, app/main implementation and focused app/main/queue tests); Scan behavior and persistence proof (Task 2, Scan contract/worker/SQLite tests); runtime documentation (Task 3, README/configuration); final verification and acceptance (Task 4, declared checks and diff inspection only). Lane ownership is disjoint; task dependencies remain sequential.
- Review and integration: Codex-only lead-controller review, reconciliation, and final integration after lane outputs; no delegated review or merge ownership.
- Sequential fallback: complete tasks in order; stop on boundary or contract drift

## Repository Truth

- `src/fitcv_cp/local_app.py:LocalJobExecutor` uses one worker and owns local
  job serialization. `prepare_local_environment` sets local and inline mode
  and removes `REDIS_URL`.
- `src/fitcv_cp/main.py:build_app` detects local mode, activates local storage,
  uses `redis_url=None` locally, and uses configured/default Redis outside
  local mode.
- `src/fitcv_cp/queue.py:enqueue_scan_with_job_id` already selects inline Scan
  execution when `FITCV_CP_INLINE_EXECUTION` is enabled and otherwise enqueues
  `scan_worker.execute_scan` in RQ. Treat this shared module as read-only unless
  focused tests prove a local/server boundary defect.
- `src/fitcv_cp/local_app.py` assigns the existing local executor during
  packaged startup and shuts it down during process exit.
- `src/fitcv_cp/app.py:create_app` currently binds `app.state.enqueue_scan`
  through `enqueue_scan_with_job_id`; preserve this callback contract and make
  only the smallest wiring change needed to keep local Scan off Redis.
- `src/fitcv_cp/scan_worker.py:execute_scan` remains Scan execution boundary.
  Keep the existing execution boundaries and do not duplicate local execution
  state.

## Boundary Rules

| Area | Local/packaged mode | Server/Docker mode |
| --- | --- | --- |
| Managed Scan dispatch | Existing inline path and `LocalJobExecutor` | Existing RQ path and worker |
| Redis requirement | None for Scan | Existing `REDIS_URL` requirement |
| Scan persistence | Existing SQLite store | Existing SQLite store |
| Non-Scan work | Preserve current behavior | Preserve current Redis/RQ behavior |
| Queue infrastructure | Verify only | Preserve unchanged |

No task may remove, rename, or repurpose shared queue functions, RQ job IDs,
worker startup, package dependencies, Docker services, or non-Scan Redis/RQ
paths. Any broader retirement needs separate approval and separate plan.

## Task Breakdown

### Task 1: Lock local/server Scan boundary

**Purpose:**
- Make mode selection explicit without duplicating local execution logic.

**Task Function:**
- Reconcile app startup and Scan callback wiring with existing local mode.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: narrow wiring change with existing implementation and tests.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller runs focused boundary checks.

**Specification Coverage:**
- Local/packaged Scan is Redis-free; server/Docker Scan remains RQ-backed.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/main.py:build_app`, `src/fitcv_cp/local_app.py:prepare_local_environment`
- Inspect: `src/fitcv_cp/queue.py:enqueue_scan_with_job_id`
- Modify: `src/fitcv_cp/app.py:create_app` and/or `src/fitcv_cp/main.py:build_app` only when required by focused proof
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_main.py`, `tests/test_fitcv_cp/test_queue.py`

**Dependencies:**
- Repository truth above and existing local-mode tests.

**Authority:**
- Preauthorized local actions: edit only listed target wiring and its focused tests; run local boundary checks
- Stop for: any required change to `queue.py`, `scan_worker.py`, SQLite schema, Docker/server topology, or non-Scan queue behavior

**Steps:**
- [ ] Step 1: Confirm local startup removes `REDIS_URL` and enables inline mode before app creation.
- [ ] Step 2: Keep local Scan dispatch on existing inline `enqueue_scan_with_job_id` behavior and `LocalJobExecutor`; keep non-local dispatch on existing RQ behavior.
- [ ] Step 3: Add only focused assertions needed to prevent local Redis access and server RQ regression.

**Verification:**
- [ ] Run focused app, main, and queue tests with local mode and server mode.
- Expected: local Scan uses `LocalJobExecutor` without Redis calls; server Scan still creates existing RQ job path.

**Exit Criteria:**
- Mode boundary is represented by existing configuration and one shared callback without duplicating local execution state.

### Task 2: Preserve Scan behavior and existing persistence

**Purpose:**
- Prove Redis removal changes transport only, not Scan behavior.

**Task Function:**
- Execute focused contract and failure-path regression checks.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing tests cover declared Scan behavior; no new framework needed.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct test evidence is sufficient.

**Specification Coverage:**
- Preserve API envelopes, statuses, cancellation, provider boundary, immutable
  output, terminal state handling, and Scan-to-Run ordering.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/scan_worker.py:execute_scan`, `src/fitcv_cp/sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_scan_worker.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 complete.

**Authority:**
- Preauthorized local actions: update focused Scan regression tests under listed targets and run them
- Stop for: API/status/output contract change, SQLite schema change, provider behavior change, or new recovery subsystem

**Steps:**
- [ ] Step 1: Cover Scan creation and Run Again with Redis unset and unreachable.
- [ ] Step 2: Cover queued/running/cancelling/failed/succeeded/cancelled behavior through existing local execution path.
- [ ] Step 3: Confirm one terminal output, immutable snapshot use, cancellation behavior, and existing Scan-to-Run source ordering.

**Verification:**
- [ ] Run focused Scan contract, worker, SQLite, and app tests.
- Expected: existing response shapes and lifecycle behavior remain unchanged.

**Exit Criteria:**
- Focused tests show transport split without Scan contract or persistence drift.

### Task 3: Align runtime documentation

**Purpose:**
- State supported Redis boundaries without expanding scope.

**Task Function:**
- Update only truthful local/server runtime statements.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: copy-level documentation change with direct source evidence.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: source and runtime checks validate claims.

**Specification Coverage:**
- Local/packaged Scan needs no Redis; server/Docker Scan and non-Scan paths
  retain Redis/RQ.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/main.py:build_app`, `src/fitcv_cp/local_app.py:prepare_local_environment`
- Modify: `README.md`, `docs/configuration.md`
- Verify: `docker-compose.yml`, `start_worker.ps1`, `start_web.ps1`, `docs/setup.md`, `docs/fitcv-control-plane-setup.md`

**Dependencies:**
- Tasks 1–2 complete.

**Authority:**
- Preauthorized local actions: edit only `README.md` and `docs/configuration.md` and run documentation-aligned checks
- Stop for: package, Docker, worker-script, setup, architecture, frontend, or global dependency/config edits

**Steps:**
- [ ] Step 1: Document local/packaged Scan Redis-free startup and existing local environment variables.
- [ ] Step 2: Document server/Docker Scan RQ and non-Scan Redis/RQ preservation.
- [ ] Step 3: Remove only contradictory Scan-specific wording.

**Verification:**
- [ ] Inspect all remaining Redis references in touched docs.
- Expected: each reference describes preserved server/Docker or non-Scan support.

**Exit Criteria:**
- Runtime docs match mode-specific behavior and preserved operational dependencies.

### Task 4: Fresh final verification

**Purpose:**
- Prove approved Option 1 and detect scope drift.

**Task Function:**
- Run focused regression, boundary, and diff checks.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance requires one sequential evidence pass.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: no independent validator assigned for this bounded plan.

**Specification Coverage:**
- Local/packaged Scan is Redis-free; server/Docker and non-Scan Redis/RQ remain intact.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify: all `targets`, `verification_only`, and `preserved_files`

**Dependencies:**
- Tasks 1–3 complete.

**Authority:**
- Preauthorized local actions: run declared tests, boundary probes, `git diff --check`, and inspect changed paths
- Stop for: failed no-Redis proof, failed server RQ proof, changed API contract, changed preserved path, or any out-of-scope diff

**Steps:**
- [ ] Step 1: Run focused backend tests.
- [ ] Step 2: Run direct local boundary probe with `REDIS_URL` unset and Redis unavailable; guard Redis connection construction.
- [ ] Step 3: Run direct server/Docker-mode dispatch regression with configured Redis boundary and inspect unchanged non-Scan queue paths.
- [ ] Step 4: Run `git diff --check` and verify only approved target files changed.

**Verification:**
- [ ] `py -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [ ] `py -m pytest tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_orchestrator.py -q`
- [ ] `git diff --check`
- Expected: focused tests pass; local Scan makes no Redis/RQ call; server/Docker Scan and non-Scan queue behavior remain RQ-backed; only approved targets change.

**Exit Criteria:**
- Fresh evidence supports every Implementation Outcome. Plan remains `status: proposed` until separately promoted by its owner.

## Verification

- Local/packaged direct probe: build app with `FITCV_LOCAL_MODE=1`, `FITCV_CP_INLINE_EXECUTION=1`, `REDIS_URL` unset, Redis connection constructor guarded to fail; create Scan, Run Again, dispatch, poll, cancel, and inspect terminal output.
- Server/Docker regression: verify `FITCV_LOCAL_MODE` disabled routes Scan through existing RQ enqueue and preserves `REDIS_URL`, worker, queue identity, and non-Scan paths.
- Focused pytest commands in Task 4.
- `git diff --check` and changed-path inspection.

## Completion Criteria

1. Local and packaged managed Scan execution succeeds without `REDIS_URL` or a reachable Redis server.
2. Local Scan uses existing inline execution and `LocalJobExecutor` without duplicating local execution state.
3. Server and Docker Scan execution remains RQ-backed with existing queue identity and worker behavior.
4. Non-Scan Run, Candidate Profile, CV regeneration, shared queue code, dependencies, Docker services, and worker startup remain unchanged.
5. Scan API, persistence, cancellation, output, and Scan-to-Run contract checks pass.
6. Documentation states mode-specific Redis requirements and preserves server/Docker and non-Scan support.
7. Fresh verification passes and only listed target files are changed.
8. Status remains `proposed` until plan owner records separate promotion approval.

## Completion Record

- **Date:** 2026-09-08
- **Decision:** Approved Option 1 only.
- **Plan state:** `proposed`.
- **Scope:** Local/packaged Scan transport only; server/Docker Scan and all non-Scan Redis/RQ paths preserved.
- **Deferred:** Any broader Redis/RQ or topology change requires separate approval and plan.
