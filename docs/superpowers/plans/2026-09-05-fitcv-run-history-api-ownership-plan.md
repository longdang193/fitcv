---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: approved
layer: change
name: fitcv-run-history-api-ownership
parent_spec: docs/superpowers/specs/2026-09-05-fitcv-run-history-api-ownership-spec.md
targets:
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/worker_job.py
  - scripts/backfill_fitcv_run_history.py
  - docs/api.md
  - frontend/src/features/runs/api.ts
  - frontend/src/features/runs/types.ts
  - frontend/src/features/runs/route.tsx
  - frontend/src/features/runs/runs-list.tsx
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/run-detail/components/EventConsole.tsx
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - frontend/src/test/runs.test.ts
  - frontend/src/test/run-results-and-overview-parity.test.tsx
  - frontend/e2e/runs.spec.ts
---

# FitCV Run History API Ownership Implementation Plan

## Goal

Move Run History to one canonical personal-use persistence and transport
contract without losing legacy Runs, overwriting normalized truth, or widening
scope. Canonical owners are `pipeline_runs`, `run_inputs`,
`run_stage_executions`, `run_jobs`, `run_job_stage_results`, and
`process_events`. Legacy tables remain migration input and temporary read-only
compatibility sources only.

## Implementation Outcomes

### Canonical persistence and migration

SQLite owns Run identity, immutable input, stages, jobs, outcomes, and
chronology. A bounded, resumable backfill imports stable legacy Runs/events,
records fingerprints and dispositions, quarantines orphan events, preserves
malformed payloads as diagnostics, and is safe to rerun.

### Exact backend contract

Run list/detail/stages/jobs/events return approved envelopes, enums, nullability,
ordering, search fields, count scopes, page semantics, and exclusive opaque
cursor behavior. Errors use existing error-envelope machinery and canonical
reads fail closed instead of silently falling back to legacy truth.

### One frontend transport boundary

The Run API adapter maps nested page metadata once to existing internal types.
UI state preserves URL/filter behavior, resets stale pagination correctly, and
does not derive backend totals or lifecycle state.

### Rollout proof and recovery

Focused tests prove real SQLite state, direct HTTP boundaries, idempotency,
conflict handling, frontend transport, and browser flows. Rollout requires
backup, parity, zero unmigrated rows, and one release-cycle write evidence.

## Current Truth And Constraints

- Approved source: `docs/superpowers/specs/2026-09-05-fitcv-run-history-api-ownership-spec.md`, approved September 5, 2026.
- Current branch: `main`; planning base: `91ac68df202c9a035149520ee353b52fec7bf73b`.
- Current worktree has unrelated tracked and untracked changes. Preserve them; do not reset, stash, clean, commit, push, or edit them.
- Schema/store paths live mainly in `src/fitcv_cp/sqlite_store.py`; delegation lives in `src/fitcv_cp/store.py`; HTTP routes and envelope helpers live in `src/fitcv_cp/app.py`.
- Current routes still contain legacy fallback behavior, and `frontend/src/features/runs/api.ts` accepts multiple pagination shapes. These are cutover targets.
- No visual redesign, event retention change, legacy-table deletion, enterprise telemetry, multi-tenant abstraction, or calendar sunset belongs here.

## Ownership Matrix

| Surface | Sole owner | Responsibility | Forbidden |
| --- | --- | --- | --- |
| SQLite schema, canonical reads/writes, fingerprints, ledger, event journal | `src/fitcv_cp/sqlite_store.py` | Durable state and transactions | Canonical fallback to legacy tables |
| Store interface/delegation | `src/fitcv_cp/store.py` | Stable delegation and test injection | Second persistence implementation |
| HTTP routes and envelopes | `src/fitcv_cp/app.py` | Validation, projection, status mapping | Legacy queries after read cutover |
| Runtime write callers | `src/fitcv_cp/queue.py`, `reconciler.py`, `reporter.py`, `scan_worker.py`, `worker_job.py` | Canonical Run/event calls | Independent legacy writes |
| Backfill command | `scripts/backfill_fitcv_run_history.py` | Bounded invocation and progress | Schema or API ownership |
| API documentation | `docs/api.md` | Public contract and compatibility notes | Divergent behavior |
| Frontend transport | `frontend/src/features/runs/api.ts`, `types.ts` | One transport adapter | Guessing totals/cursors |
| Frontend state/UI | `frontend/src/features/runs/route.tsx`, `runs-list.tsx`, `frontend/src/features/run-detail/run-detail-page.tsx`, `components/EventConsole.tsx` | URL state and rendering | Lifecycle/count truth |
| Backend proof | `tests/test_fitcv_cp/test_sqlite_store.py`, `test_store.py`, `test_app.py`, `test_worker_job.py` | SQLite, route, failure, caller evidence | Mock-only persistence proof |
| Frontend proof | `frontend/src/test/runs.test.ts`, `run-results-and-overview-parity.test.tsx`, `frontend/e2e/runs.spec.ts` | Adapter/component/browser evidence | Replacing backend proof |

Shared files are edited sequentially. Later tasks may edit a prior owner file
only after its exit criteria pass and its tests remain green.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-executing-plans`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`, `skill-using-git-worktrees`
- Isolation: dedicated clean Git worktree for implementation; current workspace remains inspection-only
- Commit policy: no commits during this plan unless owner separately authorizes disposition
- Preauthorized local actions: inspect declared files, edit task-owned files in implementation worktree, run declared checks, back up selected local DB, run bounded backfill against selected local DB
- User approval required: push, merge, publication, destructive cleanup, row deletion, backup restore, live-data mutation, compatibility/table removal
- Parallel ownership: none; migration and contract phases have hard ordering dependencies
- Sequential fallback: stop on failed gate, preserve DB/evidence, reconcile plan/Git, resume only from last completed phase

## Coordination State

- Coordination owner: single lead controller
- Coordination schema: 2
- Branch: `main`; base `91ac68df202c9a035149520ee353b52fec7bf73b`
- Expected workspace: dirty current work preserved; clean named implementation worktree before edits
- Next action: create/reuse implementation worktree, then execute Task 1
- Blockers: none for plan drafting; implementation blocks on schema, ownership, parity, or workspace mismatch

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1: Schema/read-path audit | `pending` | implementation worktree | `codex` | none | inventory and baseline tests | pending |
| Task 2: Idempotent backfill/quarantine | `pending` | implementation worktree | `codex` | Task 1 | SQLite state and repeat-run parity | pending |
| Task 3: Canonical write/read cutover | `pending` | implementation worktree | `codex` | Task 2 | append/read and no-legacy-write proof | pending |
| Task 4: API envelopes/search/counts/cursors | `pending` | implementation worktree | `codex` | Task 3 | direct HTTP contract proof | pending |
| Task 5: Frontend adapter cleanup | `pending` | implementation worktree | `codex` | Task 4 | adapter/component/browser proof | pending |
| Task 6: Tests and final verification | `pending` | implementation worktree | `codex` | Tasks 2–5 | focused suites and build checks | pending |
| Task 7: Rollout/rollback gate | `pending` | implementation worktree plus selected DB | `codex` | Task 6 | backup, parity, stop record | pending |

## Task Breakdown

### Task 1: Schema/read-path audit

**Purpose:** Establish exact current schema, every Run/event reader and writer,
and the smallest migration delta before behavior changes.

**Task Function:** Reconcile approved ownership against source, tests, docs, and
runtime callers.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: source-first audit; no delegated lane needed

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: lead reviews exact file and symbol inventory

**Specification Coverage:** Canonical table ownership; event SSOT; explicit
unknown legacy fields; fail-closed schema incompatibility; no dual truth.

**Required Skills:** `skill-backend-verification`, `skill-using-git-worktrees`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py` schema setup, `_ensure_local_pipeline_runs_table`, `_ensure_process_event_tables`, `insert_run`, `create_run_bundle`, `query_runs`, `get_run_detail`, `query_run_jobs`, `get_process_events`, `append_process_event`, `append_event`, `get_events`
- Inspect: `src/fitcv_cp/store.py` `RunStore`, `ControlPlaneStore` Run/event delegation
- Inspect: `src/fitcv_cp/app.py` `_collection_response`, `_data_response`, `_validated_page`, Run routes, compatibility fallback branches, `append_event`, `get_process_events`
- Inspect: runtime callers in `src/fitcv_cp/queue.py`, `reconciler.py`, `reporter.py`, `scan_worker.py`, and `worker_job.py`
- Inspect: `docs/api.md`, `docs/architecture.md`, and focused tests in ownership matrix
- Modify: none; record findings in task evidence, not temp files

**Dependencies:** Approved spec and current repository truth. Do not infer
missing routes or tables without confirming source symbols.

**Authority:**
- Preauthorized local actions: read-only inspection and baseline tests in implementation worktree
- Stop for: missing canonical table, conflicting contract, unknown writer, dirty implementation worktree, or edit outside target ownership

**Steps:**
- [ ] Record branch/base/worktree identity and preserve unrelated changes.
- [ ] Inventory every legacy and canonical Run/event read/write path, including journal replay.
- [ ] Compare schema constraints, indexes, foreign keys, immutable triggers, and migration version with approved invariants.
- [ ] Define migration ledger/quarantine fields needed by Task 2 and exact route/store symbols for later tasks.
- [ ] Run baseline focused backend tests.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py -q`
- Expected: baseline result recorded; failures classified before implementation.

**Exit Criteria:** Every reader/writer has one owner, schema delta is bounded,
and no unresolved behavior question remains inside approved scope.

### Task 2: Idempotent backfill and quarantine

**Purpose:** Import legacy Runs/events without duplicates, overwrites, silent
loss, or orphan promotion.

**Task Function:** Implement transactional source reconciliation and a bounded,
resumable operator command.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: migration correctness and direct SQLite proof require one owner

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: real SQLite assertions remain task-owned

**Specification Coverage:** Stable-ID source scope; SHA-256 fingerprints;
Run-bundle atomicity; event migration; equal/conflict dispositions; orphan
quarantine; malformed payload preservation; resumability.

**Required Skills:** `skill-executing-plans`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py` schema/version path, legacy source readers, Run/input/stage/job transformation, event migration, fingerprint/conflict helpers, migration-status queries
- Create/modify: `scripts/backfill_fitcv_run_history.py` with preflight, `--dry-run`, bounded batch, explicit DB selection, progress counts, nonzero failure exit, and rerun-safe source identity
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py` fixtures for complete/incomplete Runs, malformed JSON, orphan events, equal/conflicting fingerprints, duplicate source indices, and two-run idempotency
- Verify: `src/fitcv_cp/store.py` only if migration functions require existing delegation; add no second abstraction

**Dependencies:** Task 1 inventory; existing SQLite transaction/backup paths;
canonical constraints and event immutability.

**Authority:**
- Preauthorized local actions: edit listed files, create disposable DB fixtures, run backfill against disposable DB, inspect counts/fingerprints
- Stop for: foreign-key failure, schema mismatch, unstable source ID, unquarantinable malformed Run, unresolved canonical conflict, or source mutation

**Steps:**
- [ ] Add only required migration ledger/quarantine structures and indexes through existing schema/version handling.
- [ ] Compute exact Run/event fingerprints from source bytes and canonical JSON rules in spec.
- [ ] Transform valid/degraded Runs into canonical Run/input/six-stage/job rows; preserve unknown fields under compatibility metadata.
- [ ] Import events into `process_events`; record equal no-op, conflict, and orphan dispositions without changing legacy rows.
- [ ] Commit each Run bundle atomically; commit event migration independently; resume by source identity and fingerprint.
- [ ] Add CLI preflight, bounded batches, progress summary, and failure exit behavior.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: canonical counts, six stages, fingerprints, dispositions, quarantine records, and unchanged legacy rows match fixtures.
- [ ] `python scripts/backfill_fitcv_run_history.py --help`
- Expected: safe invocation and required DB/batch arguments are documented.
- [ ] Run command twice against one disposable DB, first `--dry-run`, then apply mode.
- Expected: second apply changes no canonical counts; changed fingerprint conflicts without overwrite.

**Exit Criteria:** Stable legacy Runs are reachable or durably degraded; every
event is equal/inserted/conflicted/quarantined; rerun is a no-op; source rows are
unchanged.

### Task 3: Canonical read-then-write cutover

**Purpose:** Prepare and verify one ordered canonical read-then-write cutover
without permanent dual-write or dual-read truth.

**Task Function:** Replace compatibility persistence paths with canonical
delegation while preserving explicitly retained historical adapters.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared write boundary spans backend callers and needs serialized review

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: Task 6 owns consolidated regression proof

**Specification Coverage:** Canonical write/read cutover; compatibility
`RunEvent` conversion; journal as canonical durability detail; no legacy
fallback after cutover; inspectable failed Run after queue failure.

**Required Skills:** `skill-executing-plans`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py` `insert_run`, `create_run_bundle`, `append_process_event`, `append_event`, `get_process_events`, `get_events`, `query_runs`, `get_run_detail`, and legacy boundaries
- Modify: `src/fitcv_cp/store.py` `RunStore`/`ControlPlaneStore` delegation only where canonical methods require it
- Modify: `src/fitcv_cp/app.py` Run route reads, compatibility wrappers, lifecycle/action calls, and persistence error mapping
- Modify only for direct calls: `src/fitcv_cp/queue.py`, `src/fitcv_cp/reconciler.py`, `src/fitcv_cp/reporter.py`, `src/fitcv_cp/scan_worker.py`, `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_store.py`, `test_app.py`, `test_worker_job.py`

**Dependencies:** Task 2 successful representative backfill; canonical schema
and migration ledger available.

**Authority:**
- Preauthorized local actions: edit listed backend files, run direct boundary tests against disposable SQLite, inspect SQL writes/final state
- Stop for: new legacy write, route fallback after cutover, event append/read mismatch, false success after persistence/queue failure, or route change without consumer inventory

**Steps:**
- [ ] Convert compatibility `RunEvent` once to canonical `ProcessEvent` with pipeline identity and specified defaults.
- [ ] Require migration status to report zero unmigrated stable Runs and parity for Run IDs, event IDs, lifecycle/timestamp projections, counts, and list/detail/stages/jobs/events reachability before enabling canonical reads.
- [ ] Establish canonical-only reads: migrated legacy-only Runs appear once from canonical rows; an unmigrated legacy-only Run/detail returns `404 run_not_found`, never legacy data, and records durable migration diagnostics plus quarantine disposition; mixed Runs return canonical projections only, leave absent fields explicitly unknown/null, and record durable integrity diagnostics plus quarantine disposition.
- [ ] Read events only from `process_events`: unmigrated legacy-only events are omitted and durably quarantined; mixed event results contain canonical events only, with legacy-only/mismatched rows diagnosed and quarantined rather than merged.
- [ ] Enforce event-ID/fingerprint idempotency and durable integrity conflicts.
- [ ] Remove canonical route fallback reads; retain read-only compatibility adapters only where documented.
- [ ] After the read-cutover gate and direct canonical-only read tests pass, ensure queue, reconciler, reporter, scan worker, worker job, and lifecycle callers use canonical Run/event boundaries.
- [ ] Keep filesystem journal replay inside canonical event ownership and expose degradation through existing diagnostics.
- [ ] Add no-new-legacy-write assertions before API contract work.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- Expected: canonical callers pass; failures return retryable errors without false success.
- [ ] Direct HTTP tests against real SQLite cover migrated legacy-only, unmigrated legacy-only, and mixed Run/detail/stages/jobs/events after canonical read cutover.
- Expected: migrated legacy-only resources appear once from canonical rows; unmigrated legacy-only resources return `404 run_not_found` with durable diagnostics/quarantine; mixed resources contain canonical rows only, preserve unknown/null fields, expose durable diagnostics/quarantine, and never read or merge legacy rows.
- [ ] Append through compatibility and canonical callers, then read canonical events.
- Expected: stable order; equal duplicate no-op; mismatched duplicate preserves original and records conflict.

**Exit Criteria:** Read cutover passes zero-unmigrated/parity gate and direct
canonical-only tests; new Run/event writes use canonical stores only, canonical
routes never query legacy stores, and retained callers delegate once.

### Task 4: Exact API envelopes, search, counts, and cursors

**Purpose:** Freeze route behavior to approved contract and document one
backend-owned transport shape.

**Task Function:** Implement validation, projections, filtering, counting,
ordering, and response mapping at HTTP boundary.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: exact status/envelope requirements and backend proof dependency

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct route tests and final verification cover contract

**Specification Coverage:** Nested page envelopes; six-stage detail; search
normalization/fields; count invariants; cursor-only events; 400/404/409/422/503
errors; no legacy names in canonical payloads.

**Required Skills:** `skill-backend-verification`, `skill-full-stack-integration`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py` Run handlers, `_collection_response`, `_data_response`, `_validated_page`, projection builders, and error mapping
- Modify: `src/fitcv_cp/sqlite_store.py` filter/order/count/cursor helpers only where store support is required
- Modify: `docs/api.md` Run History, event, error, and compatibility sections
- Modify: `tests/test_fitcv_cp/test_app.py` direct HTTP cases; extend `test_sqlite_store.py` for independent SQL counts and stable ordering
- Verify: `frontend/src/features/runs/api.ts`, `frontend/src/features/run-detail/run-detail-page.tsx`, and `frontend/src/test/runs.test.ts`

**Dependencies:** Task 3 cutover; approved schemas/enums; existing `ApiError`
machinery.

**Authority:**
- Preauthorized local actions: edit listed route/store/docs/tests, run ASGI/HTTP tests, compare JSON to spec fixtures
- Stop for: unresolved envelope alias, page-length count, exposed/internal cursor, accepted invalid filter, legacy fallback, or undocumented field/status drift

**Steps:**
- [ ] Enforce `view`, `page`, `page_size`, `stage`, `result_bucket`, `limit`, search normalization, and cursor validation.
- [ ] Return exact list/detail/stages/jobs/events shapes, null fields, six ordinal stages, links, capabilities, and conflicts.
- [ ] Filter before pagination; Run tab counts use search ignoring view; job facets use search/stage ignoring result bucket.
- [ ] Order Runs deterministically, jobs by case-insensitive title then ID, events by `(recorded_at ASC, event_id ASC)`.
- [ ] Keep events cursor-only with exclusive opaque cursor and query-time `total_count`.
- [ ] Update `docs/api.md` from route/test truth and record compatibility exit criteria.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: exact envelopes, statuses, fields, order, counts, empty pages, invalid cursor, missing Run, schema incompatibility, and persistence failure cases pass.
- [ ] Compare endpoint counts with independent SQL counts across view/search/stage/result/page combinations.
- Expected: counts stay constant across pages and never fall back to visible array length.

**Exit Criteria:** Backend contract matches spec/docs and frontend can consume
one canonical response without aliases.

### Task 5: Frontend adapter cleanup

**Purpose:** Remove dual transport parsing and make UI state obey canonical page
and cursor metadata without visual redesign.

**Task Function:** Tighten adapter types and update Run list/detail/Console
consumers.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded transport cleanup using existing components

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused Vitest and Playwright proof

**Specification Coverage:** One adapter normalization; canonical query
parameters; required pagination metadata; URL state; prior-data refresh;
page/cursor reset; conflicts as diagnostics.

**Required Skills:** `skill-full-stack-integration`

**Files And Symbols:**
- Modify: `frontend/src/features/runs/api.ts` `PaginationEnvelope`, `fetchRuns`, `fetchRunJobs`, `fetchRunEvents`, and adapter validation
- Modify: `frontend/src/features/runs/types.ts` internal types and metadata nullability
- Modify: `frontend/src/features/runs/route.tsx`, `runs-list.tsx`, `frontend/src/features/run-detail/run-detail-page.tsx`, `frontend/src/features/run-detail/components/EventConsole.tsx`
- Modify: `frontend/src/test/runs.test.ts`, `run-results-and-overview-parity.test.tsx`; update `frontend/e2e/runs.spec.ts` only for canonical assertions
- Verify: backend contract remains owned by `src/fitcv_cp/app.py`; no generated client exists

**Dependencies:** Task 4 contract. No integration sidecar is needed because
approved spec is durable; remove any temporary `*.integration.md` mapping after
Task 6 evidence passes.

**Authority:**
- Preauthorized local actions: edit listed frontend files/tests, run frontend checks and browser flow against local API fixture
- Stop for: `data.length` totals, missing metadata treated as success, stale cursor across Runs, noncanonical default filters, or visual redesign request

**Steps:**
- [ ] Parse `payload.data`, nested `payload.page`, and `payload.meta` once; missing required metadata is contract error.
- [ ] Remove flat/legacy aliases and omit canonical default filters.
- [ ] Reset page on search/filter changes and clear cursor on Run ID changes.
- [ ] Preserve prior data during refresh; expose retryable errors and diagnostic conflicts without converting them to Run failure.
- [ ] Preserve keyboard/focus/status behavior; make no styling changes.

**Verification:**
- [ ] `npm run test -- src/test/runs.test.ts src/test/run-results-and-overview-parity.test.tsx`
- Expected: canonical query strings, nested mapping, metadata errors, filter resets, and cursor mapping pass.
- [ ] `npm run typecheck`
- Expected: no type errors from narrowed transport shapes.
- [ ] `npm run test:e2e -- e2e/runs.spec.ts`
- Expected: Run list/detail/jobs and Console incremental loading use canonical responses.

**Exit Criteria:** Frontend has one transport shape, correct page/count/cursor
state, and browser evidence supplements backend proof.

### Task 6: Consolidated tests and verification

**Purpose:** Prove acceptance claims across durable backend state, direct HTTP
boundaries, runtime callers, frontend adapter, and browser flow.

**Task Function:** Run focused suites, add only missing regression assertions,
and reconcile each failure to its owning task.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final cross-surface validation needs one evidence owner

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: fresh commands provide required proof

**Specification Coverage:** Legacy reachability, canonical conflict precedence,
event SSOT, stable search/counts, frontend single shape, and failure behavior.

**Required Skills:** `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`

**Files And Symbols:**
- Modify only missing assertions in `tests/test_fitcv_cp/test_sqlite_store.py`, `test_store.py`, `test_app.py`, `test_worker_job.py`, `frontend/src/test/runs.test.ts`, `run-results-and-overview-parity.test.tsx`, and `frontend/e2e/runs.spec.ts`
- Verify all implementation files from Tasks 2–5 and `docs/api.md`

**Dependencies:** Tasks 2–5 complete; no unresolved prior-task failure.

**Authority:**
- Preauthorized local actions: run declared checks and edit only direct regression assertions
- Stop for: unmapped failure, live-provider dependency, or evidence that passes only through legacy fallback

**Steps:**
- [ ] Run direct backend boundary tests on real SQLite with foreign keys, unique IDs, immutable triggers, and journal replay where configured.
- [ ] Run migration twice and compare canonical IDs/counts/fingerprints.
- [ ] Run endpoint matrix for filters, search, counts, pages, cursors, empty pages, and specified errors.
- [ ] Run frontend adapter/component tests, typecheck, build, and browser Run/Console flow.
- [ ] Trace one Run from trigger/reservation through canonical rows, stage/job updates, append, list/detail/stages/jobs/events reads, cursor read, and terminal state.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- Expected: focused backend suite passes with durable state assertions.
- [ ] `npm run test -- src/test/runs.test.ts src/test/run-results-and-overview-parity.test.tsx`
- Expected: focused frontend suite passes.
- [ ] `npm run typecheck; npm run build`
- Expected: typecheck and production build pass.
- [ ] `npm run test:e2e -- e2e/runs.spec.ts`
- Expected: browser flow passes against canonical API.
- [ ] `python -m compileall -q src scripts; git diff --check`
- Expected: compile and whitespace checks pass.

**Exit Criteria:** Every acceptance test has fresh evidence, no test depends on
legacy fallback, and all deviations are recorded before rollout.

### Task 7: Rollout and rollback gate

**Purpose:** Promote canonical behavior only after backup, preflight, parity,
and stop criteria pass.

**Task Function:** Execute bounded local rollout and record go/no-go evidence.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: owner-controlled data migration and release decision

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: lead accepts Task 6 evidence and rollback record

**Specification Coverage:** Backup/fingerprint preflight; bounded backfill;
parity; read then write cutover; one-cycle monitoring; no split-truth rollback.

**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`, `skill-using-git-worktrees`

**Files And Symbols:**
- Modify: none by default; implementation changes must already be complete
- Run: `scripts/backfill_fitcv_run_history.py` against explicitly selected local DB and existing backup path
- Verify: migration ledger, canonical/legacy counts, route reachability, conflicts, write audit, and release evidence

**Dependencies:** Task 6 all-green; owner-approved DB target and backup
location; zero unresolved schema/data-integrity findings.

**Authority:**
- Preauthorized local actions: backup, preflight, bounded backfill, selected personal-environment cutover, evidence capture
- Stop for: backup failure, schema incompatibility, unmigrated Run, parity mismatch, new legacy write, missing event, cursor/count mismatch, persistence degradation, or endpoint error increase

**Steps:**
- [ ] Capture backup and source fingerprint before migration.
- [ ] Preflight schema version, foreign keys, event immutability, unique IDs, and ledger.
- [ ] Run bounded backfill; stop on integrity/schema failure instead of guessing.
- [ ] Compare Run IDs, event IDs, lifecycle/timestamp projections, counts, and list/detail/stages/jobs/events reachability.
- [ ] Read cutover gate: migration status reports zero unmigrated stable Runs; parity matches for Run IDs, event IDs, lifecycle/timestamp projections, counts, and list/detail/stages/jobs/events reachability; direct canonical-only tests pass for migrated legacy-only, unmigrated legacy-only, and mixed Run/detail/event cases. Any nonzero unmigrated count, parity mismatch, diagnostic/quarantine write failure, or test failure is a no-go; do not enable canonical reads.
- [ ] Enable canonical reads only after read cutover gate evidence is recorded; verify route reads remain canonical-only and monitor read canaries.
- [ ] Write cutover gate: after read canaries pass, no new legacy writes appear, canonical append/read idempotency passes, and direct queue/lifecycle failure tests preserve durable state. Any legacy write, event mismatch, false success, persistence error, or route error increase is a no-go; do not enable canonical writes.
- [ ] Enable canonical writes only after write cutover gate evidence is recorded. This is one fixed read-then-write sequence; no runtime feature-flag split or dual-read/write truth.
- [ ] Observe one release cycle for missing Runs, count mismatches, conflicts, cursor failures, persistence degradation, and route errors.

**Verification:**
- [ ] `python scripts/backfill_fitcv_run_history.py --help`
- Expected: command remains bounded and explicit.
- [ ] Run migration-status and parity queries against selected DB.
- Expected: zero unmigrated stable Runs; every event disposition is queryable; canonical rows win conflicts; no new legacy writes.
- [ ] Execute read-cutover gate, record evidence, enable reads, then execute write-cutover gate before enabling writes.
- Expected: failed read gate stops before read activation; failed read canary stops before write activation; failed write gate leaves writes disabled; successful gate evidence records exact status, parity, diagnostics/quarantine, and canary results.

**Rollback Path:**

1. Stop rollout on backup failure, schema incompatibility, any unmigrated stable Run, parity mismatch, failed diagnostic/quarantine write, legacy-only/mixed canonical-only test failure, missing event, new legacy write, cursor/count mismatch, persistence degradation, false success after queue/persistence failure, or endpoint error increase; preserve DB, backup, source fingerprint, logs, and evidence.
2. If the read-cutover gate fails, do not activate canonical reads; retain current compatibility reads only for rows not canonicalized and retain canonical backfill rows.
3. If read canaries or the write-cutover gate fails, keep canonical reads active only when their gate remains valid, disable canonical writes, and stop further rollout; do not re-enable legacy writes or switch canonical reads to legacy tables.
4. After write cutover, do not switch to legacy tables. Roll back application code to a canonical-compatible version or disable only affected operation while retaining normalized reads/writes.
5. Restore data only with owner approval from pre-migration backup; never delete rows as ad hoc rollback.
6. Preserve ledger, conflict, degraded, and quarantine records. Legacy cleanup is never rollback.

**Exit Criteria:** Owner has backup, parity, fresh tests, zero-unmigrated
evidence, one-cycle write/read evidence, stop action, and canonical-compatible
rollback path.

## Dependencies

- Task 1 precedes all schema, migration, route, and caller changes.
- Task 2 depends on Task 1 and must pass before read/write cutover.
- Task 3 depends on representative backfill and owns canonical boundaries before route contract work.
- Task 4 depends on Task 3 and is backend contract authority for frontend work.
- Task 5 depends on Task 4; frontend evidence cannot accept backend behavior.
- Task 6 depends on Tasks 2–5 and must pass before rollout.
- Task 7 depends on Task 6 and owner-approved backup/database target.
- No task adds provider, telemetry, tenant model, calendar policy, or new UI design.

## Acceptance Criteria

- Legacy-only complete/incomplete Runs appear once in canonical list/detail; six stages exist; unknowns remain explicit; second backfill changes no counts.
- Existing canonical Run/event rows win same-ID conflicts; changed fingerprints create durable conflict evidence without overwrite.
- Compatibility and canonical appends converge on `process_events`; equal duplicate is no-op; mismatch records conflict; `local_pipeline_run_events` is not read or newly written after cutover.
- Search uses approved public fields with NFKC, trim, case-fold, substring semantics; counts apply correct scopes and stay stable across pages.
- Runs/jobs use nested `data`/`page`/`meta`; stages return six ordinal resources; events use cursor-only metadata, exclusive stable ordering, and invalid-cursor `422 validation_failed`.
- Errors preserve stable codes, retryability, actions, and final durable state for missing Run, invalid input, conflicts, schema incompatibility, persistence failure, and queue failure.
- Frontend makes canonical requests, maps once, never derives totals from visible data, resets page/cursors correctly, and preserves loading/error/accessibility states.
- Fresh backend, frontend, typecheck/build, compile, template, diff, and browser evidence passes; no scope overclaim occurs.
