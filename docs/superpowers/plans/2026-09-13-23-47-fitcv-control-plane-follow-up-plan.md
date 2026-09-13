---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-control-plane-follow-up
targets:
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/runs/api.ts
  - frontend/src/features/bookmarks/api.ts
  - frontend/src/features/synonyms/api.ts
  - frontend/src/features/bookmarks/route.tsx
  - frontend/src/features/synonyms/suggestion-queue.tsx
  - frontend/src/features/runs/route.tsx
  - frontend/src/features/runs/runs-list.tsx
  - frontend/src/components/table.tsx
  - frontend/src/components/states.tsx
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - frontend/src/test/runs.test.ts
  - frontend/src/test/bookmarks.test.ts
  - frontend/src/features/synonyms/synonyms.test.ts
  - frontend/src/test/pipeline-settings.test.tsx
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
---

# FitCV Control-Plane Follow-Up

## Goal

Fix request and polling correctness, remove write-capable SQLite initialization from ordinary reads, establish retained-data loading semantics, and reduce interactive Jobs query work without changing search, count, export, artifact, or run-state contracts.

Reviewed baseline: `11aa6134e4ea3097d46ea02a4b0718b5c1ca0117`. Local `main` is newer (`aa6c4a6e`) and dirty; execution must reconcile that base and preserve unrelated work.

## Implementation Outcomes

### Correct request ownership

Jobs state updates require current query identity and request generation. Old polling callbacks cannot overwrite newer searches or leave loading stuck. Abort signals reach API calls. Polling stays single-flight and performs final Jobs/Events refresh before terminal stop.

### Read-only control-plane reads

Bookmarks, synonym, scan, settings, and ordinary run reads do not run schema DDL, migrations, seeding, `BEGIN IMMEDIATE`, provider-state writes, or lock-recovery rotation. Startup and explicit write paths retain initialization ownership. Locked reads fail visibly.

### Retained-data loading

Initial load may replace empty content with a loader. Refresh keeps existing rows mounted, preserves focus/layout, and exposes busy/error state separately from row mutations. Successful empty data is not loading.

### Page-first Jobs hydration

Interactive Jobs selection, counts, ordering, and pagination happen before detailed projection. Selection may inspect narrow JSON/source fields to preserve current derived-field fallbacks; only requested IDs hydrate detailed objects. Search normalization, stage/bucket filters, totals, CV capabilities, and exports remain compatible. FTS, materialized indexes, and trigger lifecycle changes stay deferred.

### Explicit Bookmarks boundary

Task 3 removes read-path write-lock contention for Bookmarks. Whole-run Bookmarks projection optimization is measured and recorded as separate follow-up scope; this plan does not silently claim to fix it.

### Measurement-based deferral

Settings revalidation and `POST /runs` acknowledgement receive matched measurements. No ETag/`304` client change or asynchronous `preparing` lifecycle is added without separate evidence and approval.

## Explicit Non-Goals

- No Redux, React Query, generic fetch framework, global TTL cache, FTS5, or search service.
- No immutable snapshot, artifact/download, export, or run-lifecycle contract changes.
- No bounded-export rewrite; current export execution remains unchanged while matching parity is protected.
- No whole-run Bookmarks projection optimization beyond read-only connection behavior; defer it to a measured follow-up.
- No dependency installation, branch change, commit, push, merge, cleanup, or unrelated dirty-file edits.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`; use clean worktree only after explicit base reconciliation
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit task-listed files, add focused tests, run declared local checks, capture bounded local measurements
- User-approval actions: dependency installation, authentication, external writes, branch/worktree changes, destructive recovery, cleanup, commits, push, merge, publication, scope changes
- Parallel ownership: none; execute serially because frontend/backend contracts overlap
- Sequential fallback: `Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `aa6c4a6e044086e2edfab9d80a77fa212ea93d58`
- Expected workspace: current dirty workspace preserved
- Next action: optional branch-finishing review; no commit, merge, push, cleanup, or publication authorized by this plan
- Residual evidence gaps: repository contract validation fails only on pre-existing legacy artifacts; skip those artifacts without modifying them. Browser daemon and active browser connection unavailable on 2026-09-13; browser accessibility and interaction evidence remain unavailable. Typecheck remains blocked by existing Node/test typings and unrelated `RunJobItem` fixtures. Matched Settings reopen, concurrent Settings, and `POST /runs` acknowledgement measurements remain unavailable. Fresh Herdr panes `default/w31:p1` through `default/w3A:p1` were created for this plan; legacy lanes remain untouched.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `complete` | current | `codex` | none | base/status audit and baseline | accepted: Herdr `fitcv-control-plane-task-1`, dispatch `72f54361882749d8b34adc2fa658e344`; HEAD `aa6c4a6e`; Python 699 passed; frontend 70 passed; runtime baselines captured; no source changes |
| Task 2 | `complete` | current | `codex` | Task 1 | race, abort, polling, terminal-refresh tests | accepted: Herdr `fitcv-control-plane-task-2`, dispatch `681a0bad6388493ebf448e2c9d458246`; focused frontend suite 70/70; `git diff --check` passed; typecheck remains blocked by existing Node/test typings and unrelated `RunJobItem` fixtures |
| Task 3 | `complete` | current | `codex` | Task 1 | SQLite trace and lock-failure tests | accepted: Herdr `fitcv-control-plane-task-3`, dispatch `dfb07e732b2247e386404f68cbc3bad4`; backend suite 728 passed; trace/lock checks 4 passed; `git diff --check` clean |
| Task 4 | `complete` | current | `codex` | Task 2 | retained-data loading and focus/accessibility tests | accepted: Herdr `fitcv-control-plane-task-4`, dispatch `fb2aac9ea6484d9da62a55de5e4580cd`; frontend suite 97 passed; build passed; `git diff --check` passed; typecheck blocked by existing unrelated test typings/errors |
| Task 5 | `complete` | current | `codex` | Task 3 | Jobs parity and hydration-bound tests | accepted: Herdr `fitcv-control-plane-task-5`, dispatch `741708c880764cb8beba50a7a4cc27b3`; focused 4 passed; declared backend suite 731 passed, 52 warnings; page workload 25 candidates/10 selected/10 hydrated; no app changes |
| Task 6 | `complete` | current | `codex` | Tasks 2–5 | final integration and matched measurements | accepted: fresh frontend 97/97; backend 731 passed, 52 warnings; build passed; `git diff --check` passed; typecheck blocked by pre-existing Node/test typings and unrelated `RunJobItem` fixtures; page hydration regression 1 passed; bookmark projection/search regression 1 passed; browser daemon unavailable; Settings/`POST /runs` matched measurements unavailable; no performance-improvement claim |

## Task Breakdown

### Task 1: Reconcile base and establish baseline

**Purpose:** Preserve user work and separate reviewed commit behavior from later local edits.

**Task Function:** Map callers, tests, runtime capability, and workload evidence for each confirmed defect.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded source and evidence mapping.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller owns reconciliation.

**Specification Coverage:** Review verdict correction; source-first evidence; dirty-work preservation.

**Required Skills:** `skill-systematic-debugging`, `skill-performance-optimization`

**Files And Symbols:** Inspect `run-detail-page.tsx:loadJobs` and polling; `runs/api.ts:fetchRunJobs`, `fetchRun`, `fetchRunEvents`; `pipeline-settings-dialog.tsx` settings load; `app.py` run creation path; `sqlite_store.py:_ensure_control_plane_schema`, `query_bookmarks`, `query_synonym_suggestions`, `_scan_store_connection`, `_filtered_run_job_rows`, `query_run_jobs`; related tests.

**Dependencies:** Reviewed commit `11aa613`; local branch may contain newer and uncommitted code.

**Authority:**
- Preauthorized local actions: read-only Git/source/test inspection and declared baseline commands.
- Stop for: reset, discard, dependency installation, authentication, or scope expansion.

**Steps:**
- [x] Record `git status --short --branch`, `git log -5 --oneline`, `git diff --name-status`, reviewed commit, and local divergence.
- [x] Mark partial fixes in dirty files as unaccepted until tests prove them; later accepted only where task evidence covers them.
- [x] Run available focused Python and frontend tests without installing dependencies.
- [x] Attempt controlled overlap/polling and representative Jobs traces; DB time, JSON decodes, hydrated rows, and controlled overlap replay were unavailable, so no matched performance claim is made.
- [x] Attempt one representative `/bookmarks` workload; only projection/search regression was reproducible, so whole-run projection remains measured follow-up scope.
- [x] Attempt Settings reopen and `POST /runs` acknowledgement baselines; safe repeat was unavailable without mutation/control setup, so both remain unresolved follow-ups.
- [x] Record unavailable browser evidence: `browser-use --doctor` found Chrome running but daemon unavailable and zero active connections.

**Verification:**
- [x] `git status --short --branch`
- [x] `uv run --no-sync --offline pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py`
- [x] `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs.test.ts src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts`

**Exit Criteria:** Baseline, divergence, preserved files, commands, and blockers recorded.

**Accepted Evidence (2026-09-13):** `main` at `aa6c4a6e044086e2edfab9d80a77fa212ea93d58`; reviewed commit `11aa6134e4ea3097d46ea02a4b0718b5c1ca0117` is one commit behind and `origin/main` matches `HEAD`. Existing dirty/staged/untracked files, including `frontend/test-results/`, were preserved. Focused Python tests passed: 699 in 124.84s. Focused frontend tests passed: 70 in 2.85s. GET-only runtime probe `1857a749-4d23-4764-b11f-29f0996741c9` recorded `/runs` 3107.1ms/10247B, Jobs 116.4ms/112522B, Bookmarks 1168.4ms/237069B, Events 329.1ms/71584B, Settings 26.6ms/30860B, and system settings 12.5ms/617B averages over three requests. DB time, JSON decodes, hydrated rows, controlled overlap replay, POST `/runs`, cold/concurrent Settings, and browser accessibility evidence remain unavailable. Confirmed defects remain unaccepted until later task proof.

### Task 2: Correct request ownership, cancellation, and polling

**Purpose:** Prevent stale Jobs updates and stuck loading across search, filters, pagination, unmount, and polling.

**Task Function:** Repair the existing async lifecycle at API and component boundaries; do not add a fetching framework.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: asynchronous lifecycle correctness.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independent race and interaction proof.

**Specification Coverage:** Query identity, generation, real abort propagation, single-flight polling, terminal refresh.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-full-stack-integration`

**Files And Symbols:** Modify `run-detail-page.tsx:loadJobs`, search effect, polling effect, cleanup, terminal finalization; `runs/api.ts:fetchRun`, `fetchRunJobs`, `fetchRunEvents`; `bookmarks/api.ts:fetchBookmarks` and `bookmarks/route.tsx` call site; `synonyms/api.ts:fetchSynonymSuggestions` and `synonyms/suggestion-queue.tsx` call site. Verify mounted production component tests and related frontend tests.

**Dependencies:** Task 1; `frontend/src/lib/api-client.ts` already accepts `RequestOptions.signal`.

**Authority:**
- Preauthorized local actions: edit listed frontend files, add focused tests, run declared frontend checks.
- Stop for: response-contract changes, new dependency, manifest edits, or authentication.

**Steps:**
- [x] Add mounted-component tests invoking the production `RunDetailPage` controller for stale searches, polling races, refresh ownership, abort resolution, and unmount/run changes.
- [x] Thread `AbortSignal` through API wrappers into `apiClient.get`.
- [x] Key Jobs requests by `runId`, active search, stage, bucket, page, and page size; validate identity before every state write.
- [x] Invalidate polling generation on cleanup but keep in-flight ownership until promise settlement.
- [x] On terminal status, run one guarded finalization cycle: refresh current-query Jobs, drain Events cursors until no `next_cursor` remains, then stop polling. Failed final refresh retains rows, settles loading, and exposes refresh error.
- [x] Define initial-load, refresh, stale, and aborted-request behavior; stale or aborted replacements are ignored.
- [x] Preserve immediate input, 250 ms debounce, mounted detail UI, and scheduled/search-trigger separation.

**Verification:** `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs.test.ts src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts`; expected mounted production behavior proves stale responses cannot update state, abort reaches mocked `fetch`, background/foreground ownership settles correctly, polling never overlaps, terminal finalization runs once, failed finalization remains visible, and an events backlog larger than one page is drained.

**Exit Criteria:** Focused tests prove race, abort, cleanup, single-flight, and terminal-refresh behavior.

**Accepted Evidence (2026-09-13):** Updated `run-detail-page.tsx`, runs/bookmarks/synonyms API wrappers, and bookmark/synonym callers. Query identity, request generation, mount guards, AbortSignal propagation, single-flight polling, cursor-drained Events, and guarded terminal Jobs/Events refresh are present. Focused frontend suite passed: 4 files, 70 tests. `npm run typecheck` still reports pre-existing missing `__dirname`/`expect` globals in `src/test/notice-layout.test.ts` plus unrelated `RunJobItem` fixture errors; no new Task 2 source error remained. No unrelated files were changed by lane.

### Task 3: Make ordinary SQLite reads read-only

**Purpose:** Remove schema and lock-recovery side effects from ordinary reads without weakening startup or writes.

**Task Function:** Separate explicit initialization ownership from read connection setup and preserve visible failures.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: transaction and failure-path risk.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: direct boundary and concurrent lock validation.

**Specification Coverage:** No `BEGIN IMMEDIATE` on reads; startup owner; no fabricated empty data.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:** Modify `sqlite_store.py:_ensure_control_plane_schema`, `query_bookmarks`, `query_synonym_suggestions`, `_scan_store_connection`, read helpers; `settings_store.py` read/lock handling. Inspect bootstrap in `main.py`, `local_app.py`, `worker_job.py`. Verify SQLite/app/settings tests.

**Dependencies:** Task 1 caller map.

**Authority:**
- Preauthorized local actions: edit listed backend files, add direct boundary tests, run focused Python checks.
- Stop for: unrelated schema migration, database deletion/rotation, or lock-policy redesign.

**Steps:**
- [x] Add SQL trace tests asserting ordinary reads perform no DDL, migration, seeding, `BEGIN IMMEDIATE`, or provider-state write.
- [x] Keep one canonical schema/migration owner at startup and required write boundaries.
- [x] Propagate locked-read failures as non-success API results; never return empty settings/collections.
- [x] Add temporary-DB concurrent writer/read tests and verify final state.
- [x] Verify successful settings/provider payloads remain unchanged after startup initialization.

**Verification:** `uv run --no-sync --offline pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_local_app.py`; expected read traces have no write transaction and locked reads fail visibly.

**Exit Criteria:** Direct trace and concurrent tests prove read-only behavior and explicit initialization ownership.

**Accepted Evidence:** `sqlite_store.py` and `settings_store.py` now use read-only SQLite URI connections for ordinary reads, keep explicit write/schema ownership, remove read-time tracked-company writes, and propagate locked-read failures without rotation or fabricated empty payloads. Added SQL trace and visible lock regression tests. Declared backend suite passed: 728 tests, 52 warnings, 124.28s. Targeted trace/lock checks passed: 4 tests, 1.33s. No DB rotation, cleanup, or unrelated file changes.

### Task 4: Add retained-data loading semantics

**Purpose:** Keep valid content mounted during refresh and separate collection fetch state from row mutation state.

**Task Function:** Add the smallest shared `DataTable` busy presentation and apply existing page state owners; no generic fetch abstraction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: cross-screen interaction consistency.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: focus, keyboard, status, and state-transition proof.

**Specification Coverage:** Initial load, refresh, empty/error distinction, retained rows, independent mutation state.

**Required Skills:** `skill-test-driven-development`

**Files And Symbols:** Modify `components/table.tsx:DataTable`, `components/states.tsx` only if needed, `features/runs/route.tsx`, `features/runs/runs-list.tsx`, Run Detail, Bookmarks, and Synonyms page owners. Verify `run-detail-page.test.tsx`, related collection tests, and `pipeline-settings.test.tsx` only for unchanged Settings behavior.

**Dependencies:** Task 2; existing `DataTable` and `LoadingState`.

**Authority:**
- Preauthorized local actions: edit listed frontend files and tests; add one small shared type only when duplication is demonstrated.
- Stop for: Redux/React Query, global cache, new endpoint, redesign, or ETag/`304` changes.

**Steps:**
- [x] Add tests for first load, retained refresh, successful empty, refresh error with retained rows, and mutation during refresh.
- [x] Add busy/refresh presentation without unmounting rows; preserve focus, pagination, `aria-busy`, and keyboard access through available tests.
- [x] Separate `hasData`, fetch status, query identity, fetch error, and mutation status across listed pages.
- [x] Do not implement Settings revalidation in this task; record Settings reuse as unresolved follow-up after Task 6 measurements.

**Verification:** `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs.test.ts src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts src/test/pipeline-settings.test.tsx`; expected rows remain mounted and empty/error/mutation states stay distinct, including Run Detail loading transitions.

**Exit Criteria:** Shared retained-data behavior works across listed pages without a generic fetch framework.

**Accepted Evidence:** Added retained-row busy presentation and `aria-busy` behavior without unmounting valid rows; kept initial loading distinct for Runs, Bookmarks, Run Detail Jobs, and Synonyms; separated fetch errors from mutation state; preserved pagination and keyboard regions. Added focused retained-row regression. Declared frontend suite passed: 97 tests. Frontend build passed. Typecheck remains blocked by existing missing Node/test typings and unrelated feature test errors.

### Task 5: Refactor interactive Jobs to page-first hydration

**Purpose:** Stop detailed whole-run projection for interactive page requests while preserving canonical semantics.

**Task Function:** Split candidate selection/counting from page hydration in SQLite and prove parity.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: query correctness and measured performance risk.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: parity and workload validation.

**Specification Coverage:** SQL filter/count/order/page where semantics permit; derived-field-preserving selection; page-only hydration; search/stage/bucket/count/export parity; one-snapshot consistency.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:** Modify `sqlite_store.py:_filtered_run_job_rows`, `query_run_jobs`, supporting loaders, and `get_run_job` only as required. Inspect `app.py:get_run_jobs`, export callers, optimization callers, and store dispatch. Verify store/app/optimization tests plus representative Jobs workload instrumentation.

**Dependencies:** Task 3; Task 1 semantic fixtures and workload.

**Authority:**
- Preauthorized local actions: edit listed store/app files, add parity/instrumentation tests, run matched local workload.
- Stop for: FTS, materialized index, schema migration, response-shape change, bounded-export rewrite, Bookmarks projection rewrite, or arbitrary millisecond target.

**Steps:**
- [x] Add parity coverage for stage modes, result buckets, Unicode search, ordering ties, totals, skipped rows, CV capabilities, bookmarks/interests, and page boundaries.
- [x] Write and preserve the selection field map across base rows, `job_fields`, structured fallbacks, skills, stage results, and buckets.
- [x] Preserve Unicode substring behavior with normalized/casefolded matching; use SQL for narrow base-row retrieval and deterministic ordering, then lightweight fallback matching where required.
- [x] Run candidate selection, counts, deterministic page-ID slicing, and page hydration through one read transaction/connection so totals and rows share one database snapshot.
- [x] Hydrate selected page IDs plus required supporting rows; preserve export execution and materialization behavior without bounded export iteration.
- [x] Keep `get_run_job` single-item and non-materializing for unrelated jobs.
- [x] Do not optimize Bookmarks projection here; Task 6 records it as separate measured follow-up scope.
- [x] Measure available workload evidence: 25 candidates, 10 selected IDs, 10 detail rows, zero non-page hydration; detailed wall/DB/response/JSON instrumentation remains unavailable and no fixed latency promise is made.

**Verification:** `uv run --no-sync --offline pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_optimization_service.py`; expected parity passes, one-snapshot behavior is proven, and matched workload reduces detailed non-page work.

**Exit Criteria:** Page-first behavior is structurally and behaviorally proven; remaining bottleneck becomes separate measured scope.

**Accepted Evidence:** `query_run_jobs` now selects/counts/deterministically slices IDs before hydrating only requested page IDs inside one read transaction; `get_run_job` remains single-item and export path remains unchanged. Added page hydration regression proving page 2 hydrates exactly selected IDs. Focused checks passed: 4. Declared backend suite passed: 731 tests, 52 warnings, 132.16s. Page workload measured 25 candidates, 10 selected IDs, 10 detail rows, zero non-page hydration. No browser or detailed wall/DB/response/JSON instrumentation evidence available; no fixed latency claim made.

### Task 6: Final integration and deferral record

**Purpose:** Verify cross-layer acceptance and avoid overstating Settings or trigger improvements.

**Task Function:** Run fresh final checks, browser proof when available, and matched measurements.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: integration and acceptance verification.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independent final verification.

**Specification Coverage:** Updated verdict acceptance and measurement-based deferral.

**Required Skills:** `skill-full-stack-integration`, `skill-performance-optimization`, `skill-verification-before-completion`

**Files And Symbols:** Verify all Task 2–5 targets, `frontend/src/lib/api-client.ts`, Settings dialog, and run creation path.

**Dependencies:** Tasks 2–5 complete with task-local proof.

**Authority:**
- Preauthorized local actions: run declared checks, capture local evidence, update plan ledger.
- Stop for: dependency installation, authentication, external writes, commit, merge, cleanup, or deferred lifecycle implementation.

**Steps:**
- [x] Run focused tests, typecheck, build, and `git diff --check` when dependencies already exist; use non-syncing offline Python commands and record blocked checks otherwise.
- [x] Attempt browser replay for typing, pagination, polling, terminal transition, Bookmarks search, and Synonyms search; blocked because `browser-use --doctor` reports daemon unavailable and zero active connections.
- [x] Verify focus, mounted content, request counts, stale rejection, loading settlement, terminal refresh, and accessibility status through available tests; browser accessibility status remains unavailable.
- [x] Repeat matched Jobs workload and record correctness plus non-page hydration count through fresh page-first regression: 25 candidates, page 2 selected 10 IDs, 10 detail rows, zero non-page hydration.
- [x] Repeat available matched `/bookmarks` regression: search/projection test passed; whole-run endpoint timing/projection instrumentation unavailable, so no optimization verdict or claim.
- [x] Reconcile matched Settings reopen and `POST /runs` acknowledgement workloads from Task 1; safe repeat was unavailable without mutation/control setup, so record as unresolved follow-ups and do not implement Settings reuse or trigger preparation in this plan.

**Verification:** `uv run --no-sync --offline pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py`; `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs.test.ts src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts src/test/pipeline-settings.test.tsx`; `npm run typecheck`; `npm run build`; `git diff --check`.

**Exit Criteria:** Fresh proof, blockers, deviations, deferred Settings/trigger work, and preserved unrelated changes are recorded; plan is ready for verification skill.

**Accepted Evidence (2026-09-13):** Fresh declared backend suite passed: 731 tests, 52 warnings in 149.20s. Fresh declared frontend suite passed: 97 tests in 2.19s. `npm run build` passed in 3.65s with existing chunk-size warning; `git diff --check` passed with existing LF/CRLF warnings. `npm run typecheck` remains blocked by existing missing Node/test typings and unrelated `RunJobItem` fixture errors. Fresh page-first Jobs regression passed: 25 candidates, page 2 selected 10 IDs, 10 hydrated detail rows, zero non-page hydration. Fresh Bookmark projection/search regression passed. Cross-layer inspection confirms frontend API signal threading for run detail, Bookmarks, and polling plus backend `/runs/{run_id}/jobs` dispatch to `query_run_jobs`; no response-contract change observed. `browser-use --doctor` found Chrome running but daemon unavailable and zero active connections, so no browser interaction, focus, keyboard, or accessibility evidence. Task 1's production GET-only baseline remains the only timing baseline; no matched current wall/DB/response/JSON workload was safely reproducible, so no performance improvement is claimed. Settings reuse, concurrent Settings behavior, and `POST /runs` acknowledgement remain deferred and unproven. No source, test, dependency, branch, worktree, commit, or cleanup changes made by Task 6.

## Verification Result

`verified` on current dirty workspace. `main` remains at `aa6c4a6e044086e2edfab9d80a77fa212ea93d58`; reviewed baseline `11aa6134e4ea3097d46ea02a4b0718b5c1ca0117` remains one commit behind and `origin/main` matches `HEAD`. Fresh lead checks passed: backend suite 731 tests/52 warnings; frontend suite 97 tests; production build; `git diff --check`. `npm run typecheck` exited 2 only on existing Node/test typings and unrelated `RunJobItem` fixture errors. Browser doctor exited 1 because daemon and active connections were unavailable. Existing staged, unstaged, and untracked unrelated changes remain preserved; no dependency, branch, worktree, commit, push, merge, cleanup, or publication action occurred.

## Verification

- `uv run --no-sync --offline pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_local_app.py`
- `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs.test.ts src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts src/test/pipeline-settings.test.tsx`
- `npm run typecheck`
- `npm run build`
- `git diff --check`
- Browser request/focus/accessibility replay when capability exists; exact blocker otherwise.
- Matched Jobs workload report with parity and non-page hydration count.

## Completion Criteria

1. Tasks 1–6 contain fresh evidence and no unchecked required proof.
2. Request, polling, abort, read-lock, loading, and Jobs hydration criteria pass.
3. Backend tests cover direct success/failure boundaries, final state, and concurrent reads/writes.
4. Frontend tests cover stale responses, aborts, retained refresh, focus, empty/error states, and mutation independence.
5. Settings reuse and trigger preparation remain unresolved follow-ups; this plan only records matched measurements.
6. Unrelated dirty files remain unchanged; no unapproved dependency, Git, cleanup, or publication action occurred.
7. Verification result is `verified`; plan status is `completed`.
