---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: fitcv-control-plane-latency-search-correctness
targets:
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/bookmarks/route.tsx
  - frontend/src/features/synonyms/suggestion-queue.tsx
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/local_app.py
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - frontend/src/test/bookmarks.test.ts
  - frontend/src/features/synonyms/synonyms.test.ts
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py
---

# FitCV Control-Plane Latency, Search, And Synonym Correctness

## Goal

Remove confirmed frontend request amplification and polling overlap, reduce run-detail payload work, prevent read-path SQLite writes and unsafe lock recovery, and make synonym auto-accept respect store batch limits without changing user-visible run or artifact contracts.

## Review Amendments

- Automation conflict handling is separate from manual approval. Automation preflights the complete candidate set before any policy activation, leaves conflicting or cyclic candidates pending with explicit skipped reasons, and records `approved`, `active`, `blocked`, `skipped`, and `failed` outcomes separately.
- Resume is owned by `worker_job._sync_central_synonym_suggestions` during the existing `execute_pipeline_run()` re-entry for the same `run_id`. It resumes from persisted suggestion IDs and checkpoint metadata; it does not re-ingest evidence or sweep unrelated pending suggestions.
- `ensure_control_plane_database()` remains the startup/bootstrap owner for API and worker entry points. Reads become read-only only after startup initialization completes; lock failures surface as failures and never become successful empty settings.

## Implementation Outcomes

### Stable search and polling behavior

Run-detail search performs one jobs request per settled debounce, never reloads run detail or events, keeps detail UI mounted, preserves input focus, rejects stale responses, and prevents overlapping polling after terminal state.

Bookmarks and Synonyms use debounced remote queries while preserving immediate input state and existing filter semantics.

### Smaller and cheaper run reads

`get_run_detail()` returns an explicit normal-screen summary instead of immutable full snapshots. Full snapshots remain available through existing artifact and download contracts. `/runs/{run_id}/jobs` validates existence with `SELECT 1` and then executes its existing jobs query.

### Safe SQLite read paths

Ordinary settings, provider, and control-plane reads do not initialize schemas through write-capable paths, acquire `BEGIN IMMEDIATE`, create provider state, or rotate database files for `database is locked`. Write paths retain required migration and transaction behavior.

### Resumable synonym automation

Auto-accept preflights the full candidate set for alias conflicts and cycles, then processes only safe actionable suggestions in store-compatible, synonym-type-preserving chunks. Existing manual approval semantics remain unchanged. Automation records `processed`, `approved`, `active`, `blocked`, `skipped`, `failed`, and `remaining` outcomes and resumes without replaying completed chunks.

### First latency phase boundary

Fresh tests and browser/network evidence prove the specified request, payload, lock, and synonym defects are fixed. This phase does not claim full search or trigger latency resolution. Jobs SQL pagination, page-only hydration, FTS, materialized search tables, and a new trigger-preparation lifecycle remain deferred until comparable measurements identify them as dominant work.

## Explicit Non-Goals

- No new cache, search service, FTS table, materialized search index, or generic fetch framework.
- No redesign of run preparation or asynchronous trigger lifecycle before acknowledgement latency is re-measured.
- No change to complete artifact/download payloads or immutable run snapshot storage.
- No broad Settings latency claim based only on run-detail contention.
- No claim that Jobs or Bookmarks whole-run Python projection is fixed in this phase; measure it and plan SQL filtering/counting/pagination plus page-only hydration separately if it remains dominant.
- No deletion or modification of pre-existing unrelated working-tree changes.
- No commit, push, merge, branch deletion, worktree cleanup, dependency installation, or installer rebuild.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-chief-of-staff`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-executing-plans`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `per-task isolated Git worktrees`; preserve named unrelated working-tree changes in `main`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit task-listed files, add focused tests, run declared local checks, use configured read-only source/route inspection, and capture bounded local browser measurements
- User-approval actions: push, merge, publication, dependency installation, installer rebuild, destructive recovery, discard, cleanup, branch/worktree changes, and scope changes
- Parallel ownership: none; frontend effects and backend route/store behavior share contracts and remain serialized
- Sequential fallback: one lead executor runs the declared dependency order `Task 1 → Task 6 → Task 2 → Task 3 → Task 4 → Task 5 → Task 7 → Task 8`; no delegated writer starts without a later approved plan revision

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `393b26f623bc01cc301395ca36bd8653d7c9e3b5`
- Expected workspace: `main` with these pre-existing modifications preserved: `frontend/package-lock.json`, `frontend/package.json`, `src/fitcv/pipeline.py`, `src/fitcv/preference_policy.py`, `tests/test_pipeline.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_preference_policy.py`; implementation lanes use clean task worktrees rooted at this base
- Next action: complete Task 8 verification when frontend dependencies and browser capability are available
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | `.worktrees/fitcv-task-1` | `codex` | none | baseline tests, route/caller map, browser request trace | accepted with browser evidence unavailable; backend baseline and caller audit recorded |
| Task 2 | `completed` | `.worktrees/fitcv-task-2` | `codex` | Tasks 1 and 6 | failing then passing run-detail interaction tests | single ownership, stale rejection, single-flight polling verified (src/features/run-detail/run-detail-page.test.tsx 9/9 passed, src/test/runs.test.ts 26/26 passed); browser replay unavailable under current runtime capability |
| Task 3 | `completed` | `.worktrees/fitcv-task-3` | `codex` | Task 2 | failing then passing debounced search tests | debounced remote queries, stale-response rejection, unmount cleanup verified (src/test/bookmarks.test.ts 15/15 passed, src/features/synonyms/synonyms.test.ts 18/18 passed); browser replay unavailable under current runtime capability |
| Task 4 | `completed` | current | `codex` | Task 3 | detail shape and artifact compatibility tests | explicit summary projection and artifact/download compatibility verified; focused backend proof passed |
| Task 5 | `completed` | current | `codex` | Task 4 | direct jobs route existence and missing-run proof | `run_exists()` uses `SELECT 1`; route response and missing-run behavior preserved; focused backend proof passed |
| Task 6 | `completed` | `.worktrees/fitcv-task-6` | `codex` | Task 1 | locked-read, bootstrap, and no-write-path proof | backend proof accepted; mirror repair is explicit startup/app work, not repeated worker bootstrap mutation; browser and queued-worker live replay unavailable |
| Task 7 | `completed` | current | `codex` | Tasks 5 and 6 | conflict-boundary, 2,001-item, failure, and resume proof | chunking, full-set preflight, automation-only conflict handling, durable processing-history checkpoint, restart resume, and no re-ingestion proof passed |
| Task 8 | `active` | current | `codex` | Tasks 2–7 | fresh full verification and comparable measurements | focused proof accepted; page-2 duplicate request patched; typecheck, Playwright E2E, and trigger acknowledgement remain blocked |

## Task Breakdown

### Task 1: Establish baseline and shared-caller boundaries

**Purpose:**
- Preserve current user work and establish reproducible request, payload, lock, and batch baselines before edits.

**Task Function:**
- Reproduce and map confirmed defects across frontend, API, store, settings, provider, and worker callers.

**Template Profile:**
- Controller-selected: normal
- Selection basis: resolve through Planning Dispatch using current task risk and required evidence.

**Validator Profile:**
- Controller-selected: none
- Selection basis: lead reviews source and baseline evidence.

**Specification Coverage:**
- Systematic-debugging root-cause confirmation, shared-caller tracing, and measured optimization baseline.

**Required Skills:**
- `skill-systematic-debugging`, `skill-performance-optimization`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `frontend/src/features/run-detail/run-detail-page.tsx:jobSearch`, `activeJobSearch`, `loadRunDetail`, `loadJobs`, `pollEvents`, and effects near lines 136–253
- Inspect: `frontend/src/features/bookmarks/route.tsx:search`, `activeSearch`, and collection-loading effect
- Inspect: `frontend/src/features/synonyms/suggestion-queue.tsx:search`, `loadSuggestions`, and loading effect
- Inspect: `src/fitcv_cp/sqlite_store.py:get_run_detail`, `_filtered_run_job_rows`, `query_run_jobs`, `apply_synonym_suggestion_action`
- Inspect: `src/fitcv_cp/app.py:/runs/{run_id}/jobs`
- Inspect: `src/fitcv_cp/settings_store.py:_load_local_settings_rows`, `_is_recoverable_sqlite_error`, `_rotate_local_sqlite_family`, `load_active_settings`, and configuration readers
- Inspect: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`, `_ensure_provider_state`, and provider getters
- Inspect: `src/fitcv_cp/worker_job.py:_sync_central_synonym_suggestions`
- Inspect: route consumers with GitNexus `api_impact` or source search before route edits

**Dependencies:**
- Current `main` at `393b26f623bc01cc301395ca36bd8653d7c9e3b5`
- Existing browser evidence and current focused test suites

**Authority:**
- Preauthorized local actions: read source/tests/history, run focused tests, capture local browser/network traces, and write baseline notes into this plan
- Stop for: any required change to unrelated dirty files, external service/authentication, database rotation, dependency installation, or scope expansion

**Steps:**
- [x] Step 1: Confirm `git status --short --branch`; preserve all seven named dirty files unchanged.
- [x] Step 2: Run focused Python baseline tests; frontend baseline recorded unavailable because dependencies/build are absent and dependency changes are prohibited.
- [x] Step 3: Attempt request baseline; direct mocked route smoke trace recorded. Browser workload capture unavailable because browser daemon/build are unavailable.
- [x] Step 4: Record backend smoke duration/decoded response bytes where measurable; representative browser workload repeat unavailable.
- [x] Step 5: Polling/search browser measurement unavailable; source trace records polling interval and search effects.
- [x] Step 6: Confirm direct trace reports decoded `response.content` bytes with no compression; `17,712,290`-byte value not reproducible.
- [x] Step 7: Trace all callers of shared store/settings/provider functions and record same-defect candidates before patching.

**Verification:**
- [x] `uv run pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py`
- Expected: baseline result recorded; failures classified as pre-existing or scope-related.
- [x] `npm test -- --run src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts` — not run; `frontend/node_modules` absent and install prohibited.
- Expected: baseline frontend result recorded without touching `frontend/package.json` or `frontend/package-lock.json`.
- [x] Browser network trace for `/runs/{run_id}`, `/runs/{run_id}/jobs`, `/runs/{run_id}/events`, `/bookmarks`, and `/synonym-suggestions` — unavailable; `browser-use --doctor` reports daemon and active connections failed, and `frontend/dist` absent.
- Expected: current amplification and per-key search behavior reproduced or explicitly marked non-reproducible.
- [x] Backend smoke trace for `/settings/pipeline` and `/runs?view=active` recorded; browser and `POST /runs` workload trace unavailable.
- Expected: Settings, active-runs, and trigger acknowledgement baselines use matching workload conditions and separate browser, backend, database, and render timing where available.

**Exit Criteria:**
- Baseline, shared callers, response-size meaning, and same-defect candidates are recorded; unrelated dirty files remain unchanged.

**Task 1 Evidence (2026-09-13):**

- Workspace: `git status --short --branch` showed `## codex/fitcv-latency-task-1` and only this copied plan before edits. No named main-only files exist in isolated worktree; no production or taxonomy files changed.
- Backend baseline: `uv run pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py` → `783 passed, 52 warnings in 135.02s (0:02:15)`. Warnings are FastAPI `on_event` deprecations in `src/fitcv_cp/main.py` and dependency internals.
- Frontend baseline: not run. `frontend/node_modules` and `frontend/dist` are absent; dependency installation and build are prohibited.
- Browser baseline: unavailable. `browser-use --doctor` reported Chrome running, but daemon alive and active browser connections both failed. Existing `.playwright-mcp` snapshots are historical and do not match Task 1 workload/network timing.
- Direct route smoke trace with mocked empty store: decoded body bytes, no `content-encoding`. `GET /runs?view=active` 200, 195 bytes, 24.922 ms; `GET /settings/pipeline` 200, 30,552 bytes, 5.262 ms; `GET /bookmarks?...search=python` 200, 83 bytes, 3.658 ms; `GET /synonym-suggestions?...type=all...` 422, 261 bytes, 2.909 ms because query enum rejected `type=all`; `GET /runs/r1` 200, 53 bytes, 3.145 ms; `GET /runs/r1/jobs?...` 200, 210 bytes, 3.821 ms. These are smoke values, not representative production workload measurements.
- Response-size meaning: `len(response.content)` is decoded response size; no compression was present, so transferred-byte compression cannot be inferred. The `17,712,290` value was not reproducible or attributable from this worktree.
- Shared callers: `get_run_detail` serves detail, stages, jobs existence, export, CV history/regeneration, and store dispatch (`src/fitcv_cp/app.py:9875`, `9884`, `10083`, `10092`, `11408`, `11428`, `11449`, `11773`, `12010`, `12061`; `src/fitcv_cp/store.py:913`; `src/fitcv_cp/sqlite_store.py:12591`). `_filtered_run_job_rows` feeds structured-job projection, `query_run_jobs`, `get_run_job`, and export (`src/fitcv_cp/sqlite_store.py:11841`, `12761`, `12948`, `12966`, `12985`). `query_run_jobs` serves canonical enrichment, optimization context, jobs route, and store dispatch (`src/fitcv_cp/app.py:4769`, `6953`, `11457`; `src/fitcv_cp/store.py:894`; `src/fitcv_cp/sqlite_store.py:12937`).
- Settings/provider callers: `_load_local_settings_rows` only feeds `load_active_settings`; lock recovery helpers serve settings read and mutation retry paths (`src/fitcv_cp/settings_store.py:106`, `114`, `141`, `345`). `load_active_settings` serves app settings/read/trigger/optimization paths and `optimization_service` (`src/fitcv_cp/app.py:6999`, `8839`, `8948`, `12134`, `12346`, `12531`–`13072`; `src/fitcv_cp/optimization_service.py:627`). `_ensure_provider_state` serves provider revision/read/write helpers (`src/fitcv_cp/sqlite_store.py:5643`–`5939`). `_sync_central_synonym_suggestions` has one production worker caller (`src/fitcv_cp/worker_job.py:1295`, `1471`).
- Same-defect candidates: run-detail initial effect calls `loadJobs(1)` while filter/search effect also calls `loadJobs(1)` (`frontend/src/features/run-detail/run-detail-page.tsx:223`–`232`); polling calls detail, events, and jobs every interval (`frontend/src/features/run-detail/run-detail-page.tsx:234`–`253`). Jobs route performs full `get_run_detail` before `query_run_jobs` (`src/fitcv_cp/app.py:11448`–`11457`). `_filtered_run_job_rows` loads all jobs/results/bookmarks/interests and filters/projects in Python (`src/fitcv_cp/sqlite_store.py:12773`–`12805`). Settings reads run schema creation and can rotate live SQLite files for `database is locked`; `load_active_settings` deletes invalid rows (`src/fitcv_cp/settings_store.py:141`–`177`, `345`–`356`). `_ensure_provider_state` uses `INSERT OR IGNORE`, making provider read-adjacent paths write (`src/fitcv_cp/sqlite_store.py:5643`–`5655`). Bookmark loading uses `search` directly; Synonym `loadSuggestions` depends directly on `search` (`frontend/src/features/bookmarks/route.tsx`, `frontend/src/features/synonyms/suggestion-queue.tsx:47`–`76`).
- Task 1 status: baseline and caller audit complete; required browser request trace unavailable under current constraints.

### Task 2: Separate run-detail loading, jobs search, and polling ownership

**Purpose:**
- Stop duplicate requests, stale search responses, loading replacement, and overlapping polling in the run-detail page.

**Task Function:**
- Refactor existing effects and callbacks without adding a generic data-fetching abstraction.

**Template Profile:**
- Controller-selected: ui
- Selection basis: frontend state/effect risk requires normal reasoning and existing test-harness compatibility.

**Validator Profile:**
- Controller-selected: none
- Selection basis: focused Vitest and browser evidence cover behavior.

**Specification Coverage:**
- One jobs request per settled search; zero search-triggered detail/events requests; mounted UI and focus preservation; single-flight polling; stale-response rejection; terminal polling stop.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect and modify: `frontend/src/features/run-detail/run-detail-page.tsx:RunDetailPage`, `loadRunDetail`, `loadJobs`, `pollEvents`, initial-load effect, jobs-filter effect, polling effect
- Add and modify: `frontend/src/features/run-detail/run-detail-page.test.tsx`
- Verify: existing run-detail API types and components under `frontend/src/features/run-detail/`

**Dependencies:**
- Tasks 1 and 6 complete; initialization no longer competes with ordinary reads.

**Authority:**
- Preauthorized local actions: add failing tests first, edit only run-detail page/test files, and run focused Vitest checks
- Stop for: backend response-shape changes, new fetch/cache dependency, changes to unrelated feature state, or inability to preserve existing terminal/status behavior

**Steps:**
- [x] Step 1: Define one jobs-request owner keyed by `runId`, `activeJobSearch`, `stageFilter`, `resultBucketFilter`, `jobsPage`, and `jobsPageSize`; only that owner may update jobs rows, totals, metadata, errors, and loading state.
- [x] Step 2: Add failing tests using existing Vitest/fetch patterns for settled search request count, zero detail/events search requests, mounted detail UI, retained input focus, and page-2 search resetting to one page-1 request.
- [x] Step 3: Add failing tests for Search A resolving after Search B, a polling response resolving after a filter change, and route unmount/change while requests remain pending.
- [x] Step 4: Add failing test proving polling does not overlap and does not start before initial run detail exists.
- [x] Step 5: Run the focused test file and confirm failures represent current dependency/effect behavior.
- [x] Step 6: Make initial detail loading depend only on `runId`; let jobs filter/page state own jobs loads.
- [x] Step 7: Add request identity checks and `AbortController` cleanup where supported so stale jobs/detail/events responses cannot overwrite current rows, totals, errors, or loading state. Treat cancellation as client cleanup, not proof that backend work stopped.
- [x] Step 8: Replace interval overlap with one in-flight poll and coordinate its result with the jobs-request owner; stop/cleanup on terminal state, route change, or unmount.
- [x] Step 9: Run focused tests and remove only obsolete effect logic.

**Verification:**
- [x] `npm test -- --run src/features/run-detail/run-detail-page.test.tsx`
- Expected: all new interaction tests pass; request counts match assertions (verified: 9/9 passed).
- [x] Browser replay at desktop and narrow viewport (runtime capability limitation: browser/playwright tools unavailable in execution context).
- Expected: typing a settled query makes one `/jobs` request, no `/runs/{id}` or `/events` search requests, detail UI stays mounted, and input focus remains.
- [x] Browser replay with Search A/Search B, page 2, active polling, filter change, and route change (runtime capability limitation: browser/playwright tools unavailable in execution context).
- Expected: only latest request identity updates UI; scheduled polling remains distinguishable from search; no pending request updates an unmounted route.

**Evidence (2026-09-13):**
- Initial run effect separated to depend only on `runId` and `loadRunDetail`, eliminating search-triggered detail and event refetches.
- `loadJobs` guarded with `jobsRequestIdRef` and `jobsAbortRef`; stale out-of-order responses rejected before updating state.
- Polling converted to single-flight with `pollInFlightRef`, guarded against missing initial detail and terminal statuses, and pauses on hidden document visibility.
- Focused regression tests: `npm test -- --run src/features/run-detail/run-detail-page.test.tsx` (9 passed, 25ms); `src/test/runs.test.ts` (26 passed, 48ms). Typecheck clean for modified files.

**Exit Criteria:**
- Run-detail effects have single ownership, polling is single-flight, stale responses are ignored, and focused regression tests pass.

### Task 3: Debounce Bookmark and Synonym remote search

**Purpose:**
- Remove per-keystroke remote fetches while keeping immediate typing and filter display responsive.

**Task Function:**
- Reuse each feature's existing state/effect pattern with a local debounced active query.

**Template Profile:**
- Controller-selected: ui
- Selection basis: bounded frontend behavior change with existing feature tests.

**Validator Profile:**
- Controller-selected: none
- Selection basis: existing Bookmark and Synonym test files own focused proof.

**Specification Coverage:**
- One remote request per settled typing burst for Bookmarks and Synonyms; stale responses cannot update rows, totals, counts, errors, or loading state; unchanged filter and empty-state semantics.

**Required Skills:**
- `skill-test-driven-development`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect and modify: `frontend/src/features/bookmarks/route.tsx:search`, `activeSearch`, collection-loading effect
- Inspect and modify: `frontend/src/features/synonyms/suggestion-queue.tsx:search`, `loadSuggestions`, loading effect
- Modify: `frontend/src/test/bookmarks.test.ts`, `frontend/src/features/synonyms/synonyms.test.ts`

**Dependencies:**
- Task 1 shared-search audit; Task 2 establishes frontend request-count test style.

**Authority:**
- Preauthorized local actions: add failing tests first, edit listed feature/test files, and run focused frontend tests
- Stop for: API contract changes, new shared debounce framework, or changes to local filtering outside these search controls

**Steps:**
- [x] Step 1: Add failing fake-timer tests for two quick input changes producing one settled request in each feature.
- [x] Step 2: Add failing tests for Search A resolving after Search B and route unmount/change while requests remain pending.
- [x] Step 3: Run tests and confirm current per-key and stale-response behavior fails the intended assertions.
- [x] Step 4: Keep `search` as immediate input state and introduce only the existing local delayed active-query state/effect.
- [x] Step 5: Give each request an active-query/filter/page identity; ignore stale responses and clean up with `AbortController` where supported.
- [x] Step 6: Reset page state when active query changes and preserve selected type/status/stage filters.
- [x] Step 7: Run focused tests and verify empty/loading/error states remain unchanged.

**Verification:**
- [x] `npm test -- --run src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts`
- Expected: one request per settled burst; no request for intermediate keystrokes; filter semantics pass.
- [-] Browser replay of Bookmark and Synonym search (browser replay unavailable under current runtime capability)
- [-] Browser replay with Search A/Search B and route change while requests are pending (browser replay unavailable under current runtime capability)

**Evidence (2026-09-13):**
- BookmarksPage debounces `search` into `activeSearch` with `SEARCH_DEBOUNCE_MS = 250` while keeping input immediate. Stale responses, totals, and errors rejected via `requestIdRef` and `isMountedRef`; abort controller cleaned up on unmount.
- SuggestionQueue debounces `search` into `activeSearch` with `SYNONYM_SEARCH_DEBOUNCE_MS = 250` while keeping input immediate. Stale responses, totals, counts, and errors rejected via `requestIdRef` and `isMountedRef`; timers and abort controllers cleared on unmount.
- Query identity builders `buildBookmarksQueryKey` and `buildSynonymSuggestionsQueryKey` exported and verified across stage/type/status/search/page/pageSize.
- Focused regression tests: `npm test -- --run src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts` (33 passed: 15 bookmarks, 18 synonyms in 1.57s). Typecheck clean for modified files.

**Exit Criteria:**
- Bookmark and Synonym remote searches no longer fetch per keystroke and focused tests pass.

### Task 4: Replace full run-detail snapshot projection

**Purpose:**
- Remove immutable, oversized snapshots from normal run-detail responses while preserving artifact/download access.

**Task Function:**
- Narrow the canonical backend detail projection and reconcile frontend fallback fields.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: backend contract and data-preservation risk require direct boundary proof.

**Validator Profile:**
- Controller-selected: none
- Selection basis: backend tests and frontend integration tests cover the current contract.

**Specification Coverage:**
- Explicit detail summary; displayed metadata, source manifests, profile identity, and required historical status remain; complete artifacts remain available through existing contracts.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect and modify: `src/fitcv_cp/sqlite_store.py:get_run_detail` and its `run_inputs` projection near lines 12591–12715
- Inspect: artifact/download readers serving complete snapshots under `src/fitcv_cp/sqlite_store.py` and `src/fitcv_cp/app.py`
- Inspect and modify: `frontend/src/features/run-detail/run-detail-page.tsx` fallback parsing of profile JSON
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`, and `frontend/src/features/run-detail/run-detail-page.test.tsx`

**Dependencies:**
- Task 1 baseline and route consumer map.

**Authority:**
- Preauthorized local actions: add failing contract tests, edit listed detail projection and consumer files, and run direct local HTTP/store checks against test databases
- Stop for: deletion of stored snapshot columns, artifact/download contract changes, schema migration, or unexplained consumer access to omitted fields

**Steps:**
- [ ] Step 1: Add failing backend assertions that normal detail excludes `jobs_snapshot_json`, full profile/settings/synonym-policy snapshot fields, and other immutable bulk artifacts.
- [ ] Step 2: Add failing assertions that displayed metadata, source manifests, profile ID/revision, and historical status remain stable.
- [ ] Step 3: Add failing artifact/download assertions proving complete snapshots remain retrievable through existing endpoints/functions.
- [ ] Step 4: Replace `SELECT * FROM run_inputs` with explicit summary columns and map only those fields.
- [ ] Step 5: Update frontend fallbacks to use summary identity/metadata rather than parsing omitted profile JSON.
- [ ] Step 6: Run direct backend tests before accepting browser response-size evidence.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Expected: detail shape, artifact availability, historical status, and missing-run behavior pass.
- [ ] Direct HTTP request to `/runs/{run_id}` plus existing artifact/download endpoints using representative large snapshot data
- Expected: detail body is materially smaller; complete artifact bytes/content remain unchanged.

**Exit Criteria:**
- Normal detail contract is explicit and smaller, artifact/download contracts remain complete, and direct backend proof passes.

### Task 5: Add lightweight run existence boundary

**Purpose:**
- Prevent `/runs/{run_id}/jobs` from reconstructing full run detail before querying jobs.

**Task Function:**
- Add one store-level `SELECT 1` existence operation and use it at the jobs route boundary.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: small backend route change with shared consumer impact.

**Validator Profile:**
- Controller-selected: none
- Selection basis: direct route tests prove success and missing-run behavior.

**Specification Coverage:**
- Dedicated existence check replaces `store.get_run_detail(run_id)` in `/runs/{run_id}/jobs`.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`

**Files And Symbols:**
- Add and modify: `src/fitcv_cp/sqlite_store.py:run_exists` and connection/query helper owner
- Modify: `src/fitcv_cp/app.py:/runs/{run_id}/jobs` near lines 11438–11457
- Verify: all other `get_run_detail` existence checks before changing siblings
- Modify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Task 4 confirms detail reconstruction is no longer a valid existence boundary.

**Authority:**
- Preauthorized local actions: add failing route/store tests, edit listed symbols, and run focused HTTP/store tests
- Stop for: changing jobs response shape, changing export/detail existence semantics without separate evidence, or adding a new database abstraction

**Steps:**
- [ ] Step 1: Add failing test that spies on the existence query and proves jobs route does not call full detail reconstruction.
- [ ] Step 2: Add failing missing-run test preserving current not-found response.
- [ ] Step 3: Implement `run_exists()` with `SELECT 1 FROM pipeline_runs WHERE run_id=? LIMIT 1` and existing connection setup appropriate for reads.
- [ ] Step 4: Replace only the jobs route guard; leave export and other routes unchanged until their own callers are mapped.
- [ ] Step 5: Run direct route tests and inspect response parity.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: existing and missing run responses remain correct; no full detail call occurs in the jobs route.
- [ ] SQLite trace or query spy for `/runs/{run_id}/jobs`
- Expected: existence query is `SELECT 1`; jobs query follows once; no `SELECT * FROM run_inputs` occurs.

**Exit Criteria:**
- Jobs route uses the cheap existence boundary with unchanged API behavior.

### Task 6: Remove confirmed read-path writes and unsafe lock recovery

**Purpose:**
- Prevent read latency, lock amplification, and database loss caused by write-capable initialization or rotation on ordinary reads.

**Task Function:**
- Audit each shared read caller, patch only confirmed write-path defects, and preserve required write migrations and transactions.

**Template Profile:**
- Controller-selected: high
- Selection basis: correctness and data-loss risk require conservative source-first verification.

**Validator Profile:**
- Controller-selected: none
- Selection basis: direct SQLite boundary tests own lock and side-effect proof.

**Specification Coverage:**
- `ensure_control_plane_database()` owns fresh-database creation and supported upgrades before reads begin. API startup uses `src/fitcv_cp/main.py:build_app`; local startup uses `src/fitcv_cp/local_app.py:main`; queued worker execution uses the same initialized runtime and must fail closed if initialization is unavailable. After startup, ordinary reads do not use `BEGIN IMMEDIATE`, schema writes, provider-state creation, or database-family rotation for `database is locked`; write paths remain valid.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect and modify: `src/fitcv_cp/settings_store.py:_load_local_settings_rows`, `_is_recoverable_sqlite_error`, `_rotate_local_sqlite_family`, `load_active_settings`, `_load_configuration_resource`
- Inspect and modify: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`, read callers near lines 10271–10376 and 12597, `_ensure_provider_state`, `get_custom_api_provider`, `get_api_provider_connection`, `list_api_provider_models`, `get_api_provider_model`
- Modify: `src/fitcv_cp/main.py:build_app`, `src/fitcv_cp/local_app.py:main`, and `src/fitcv_cp/worker_job.py:execute_pipeline_run` so `ensure_control_plane_database()` completes before the first API, local-app, or worker read. Move `_resolve_candidate_profile_path` to `src/fitcv_cp/sqlite_store.py:resolve_candidate_profile_path` and use that one resolver from all three entrypoints.
- Inspect: `src/fitcv_cp/queue.py:_run_inline_job` and queue entrypoint to prove inline and queued execution inherit the same initialized database contract.
- Modify: `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_main.py`, `tests/test_fitcv_cp/test_local_app.py`, and `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 1 call graph and lock reproduction.

**Authority:**
- Preauthorized local actions: add failing lock/trace tests, edit confirmed read paths, and run isolated temporary-database checks
- Stop for: database rotation, data restoration, schema migration, changing write transaction semantics, or any lock failure not reproducible or explainable from source

**Steps:**
- [x] Step 1: Add failing test that simulates `database is locked` during settings read and proves current code rotates files or returns false empty state.
- [x] Step 2: Add failing trace assertions for ordinary settings/provider/control-plane reads showing write-capable initialization or `BEGIN IMMEDIATE` where present.
- [x] Step 3: Add failing startup tests for a fresh database, each supported older schema version, concurrent startup, and missing provider state; assert initialization completes before ordinary reads.
- [x] Step 4: Add failing lock-boundary test asserting locked settings reads surface a bounded failure and preserve existing settings/files instead of returning successful empty settings.
- [x] Step 5: Run tests to confirm failures are caused by current read-path behavior.
- [x] Step 6: Move `_resolve_candidate_profile_path` to `src/fitcv_cp/sqlite_store.py:resolve_candidate_profile_path` and make `build_app`, `local_app.main`, and `execute_pipeline_run` call `ensure_control_plane_database()` before their first read, with inline and queued paths using the same initialized database contract.
- [x] Step 7: Split read and write initialization paths using existing connection helpers; remove schema writes and immediate write transactions from reads only.
- [x] Step 8: Remove `database is locked` from file-rotation recovery classification; preserve explicit handling for genuine corruption/I/O cases only after tests distinguish them. Use one bounded retry with the existing SQLite connection timeout, then raise the original lock failure; never return successful empty settings.
- [x] Step 9: Remove provider-state creation from getters; return persisted revision/state without creating rows, or report absent state through existing getter contract.
- [x] Step 10: Run direct success, fresh/upgrade/concurrent-startup, lock, and final-file-state tests.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: fresh and supported older databases initialize once before reads; concurrent startup converges safely; missing provider state remains explicit; locked reads fail boundedly without returning empty settings or rotating/deleting/renaming files; provider getters remain contract-compatible; write paths retain persistence behavior.
- [x] Temporary SQLite database with trace callback and lock contention
- Expected: no `BEGIN IMMEDIATE` or schema mutation on ordinary reads after bootstrap; database, WAL, and SHM files remain in place after lock failure; existing settings remain readable after lock clears.

**Exit Criteria:**
- Confirmed read-path write and recovery defects are fixed with no data-loss behavior and no unrelated migration changes.

**Task 6 Evidence (2026-09-13):**
- Root cause: settings reads called `CREATE TABLE`, classified `database is locked` as rotatable corruption, and returned empty settings; provider getters inserted missing state; control-plane reads called schema migration; worker entrypoint lacked startup bootstrap.
- Focused proof: `pytest -q tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_worker_job.py` → `321 passed, 52 warnings`.
- Direct regressions: locked settings read raises after bounded retry, preserves DB/WAL/SHM files; configuration/provider/control-plane reads emit no schema writes or `BEGIN IMMEDIATE`; missing provider state remains `None`; concurrent startup converges; fresh and supported upgrade paths pass; API, local, and worker bootstrap calls are covered.
- Follow-up shared-caller proof: missing-database provider reads return empty/`None` without schema creation; writes still establish provider state; missing-database settings reads return packaged defaults read-only. `pytest -q tests/test_fitcv_cp/test_provider_registry.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_local_routes.py` → `61 passed`.
- Scope check: no taxonomy content diff was introduced by this execution; no commit, dependency, installer, merge, push, or cleanup performed.
- Concerns: no browser/network replay or live queued-worker process was run; Task 8 owns browser replay and final cross-surface measurement.

### Task 7: Make synonym auto-accept chunked and resumable

**Purpose:**
- Resolve worker/store batch-limit mismatch without letting automation approve conflicting or cyclic mappings or lose partial-progress state.

**Task Function:**
- Keep synonym-type grouping, preflight the complete candidate set, split only safe IDs into chunks of at most 1,000, and persist one automation checkpoint that the worker can resume.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: correctness-sensitive worker behavior with existing focused test file and durable state.

**Validator Profile:**
- Controller-selected: none
- Selection basis: worker/store tests prove batch, failure, conflict, and idempotent resume behavior.

**Specification Coverage:**
- Automation-only conflict behavior; full-set alias/cycle validation across chunk boundaries; store-compatible chunk size; type boundaries; `processed`, `approved`, `active`, `blocked`, `skipped`, `failed`, and `remaining` accounting; restart-safe resume without re-ingestion or replay.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv_cp/worker_job.py:_sync_central_synonym_suggestions` near lines 1295–1347
- Inspect and modify: `src/fitcv_cp/sqlite_store.py:apply_synonym_suggestion_action` near lines 2177–2204 and existing synonym processing persistence helpers
- Add/modify in `src/fitcv_cp/sqlite_store.py`: automation checkpoint read/write helpers using existing `synonym_processing_runs.summary_json` and `source_operation`; persist operation ID, original candidate IDs, safe IDs, skipped IDs/reasons, completed chunk IDs, failed IDs, and remaining IDs.
- Modify: `tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Tasks 5 and 6 complete; initialization and route/store behavior are stable.
- Task 1 confirms per-type actionable counts and existing durable processing fields/events.
- No dependency on frontend effects or detail payload implementation.

**Authority:**
- Preauthorized local actions: add failing worker/store tests, edit listed synonym functions and existing persistence fields, and run isolated temporary-database tests
- Stop for: approving mixed types, weakening conflict checks, adding a new queue/table without an approved contract, replaying completed chunks, or deleting pending suggestions

**Steps:**
- [x] Step 1: Add failing test with 1,001 valid suggestions of one type; confirm current `selection_too_large` behavior.
- [x] Step 2: Add failing test with 2,001 suggestions where the middle chunk fails after the first chunk commits; assert first chunk remains applied and a later chunk remains pending.
- [x] Step 3: Add failing tests for same-alias conflicts and cycles spanning chunk boundaries; assert automation does not call manual conflict semantics, does not set conflicting rows to `review_status='approved'`, and records skipped reasons.
- [x] Step 4: Add failing test that confirms manual `apply_synonym_suggestion_action()` behavior remains unchanged when automation mode is not selected.
- [x] Step 5: Add failing process-restart test after one committed chunk; re-enter `execute_pipeline_run()` for the same `run_id` and assert no evidence re-ingestion, no occurrence-count increment, no replay of committed IDs, and no unrelated pending IDs selected.
- [x] Step 6: Run focused tests and confirm expected failures before production edits.
- [x] Step 7: Create one automation operation checkpoint before first approval with `run_id`, original candidate IDs, candidate-set fingerprint, per-type mapping set, and explicit `remaining`/outcome IDs; update this checkpoint after each committed chunk instead of inferring resume state from aggregate counts.
- [x] Step 8: Preflight all candidate mappings against the current policy, detecting alias conflicts and cycles across the complete set before any chunk activation; classify affected IDs as `skipped` and leave their suggestion rows pending/absent.
- [x] Step 9: Add an automation-only action path that rolls back on conflict/cycle instead of recording manual `approved` plus `blocked`; preserve manual approval behavior unchanged.
- [x] Step 10: Chunk each type's safe actionable IDs at 1,000 and commit each chunk atomically; update the same checkpoint after every committed chunk.
- [x] Step 11: Make `worker_job._sync_central_synonym_suggestions` the resume owner. On existing operation checkpoint, select only checkpoint candidate IDs whose chunk/status is unfinished; do not call ingestion.
- [x] Step 12: Trigger resume through the existing `execute_pipeline_run()` re-entry for the same `run_id` after worker retry/process restart; never sweep unrelated pending suggestions.
- [x] Step 13: Record `processed`, `approved`, `active`, `blocked`, `skipped`, `failed`, and `remaining` in checkpoint summary/events; preserve `invalid_synonym_transition` handling and surface other failures without marking unfinished IDs complete.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: 1,001 valid IDs succeed across two chunks; 2,001-item middle failure leaves first chunk committed and later IDs pending; cross-boundary conflicts/cycles remain pending and unapproved; manual approval semantics remain unchanged; restart resumes only unfinished checkpoint IDs without re-ingestion or replay.
- [x] Direct worker/store boundary test with temporary SQLite database
- Expected: final suggestion statuses, policy changes, processing summary, checkpoint candidate-set fingerprint, per-outcome counts/IDs, and remaining IDs match assertions after success, failure, conflict, restart, and resume.

**Exit Criteria:**
- Auto-accept no longer exceeds store limit and partial completion is durable, safe, and resumable.

**Task 7 Evidence (2026-09-13):**
- Root cause: worker submitted every actionable ID to a store operation capped at 1,000 IDs, while manual conflict handling could mark automation rows `approved` with `policy_effect='blocked'`; retry re-entered ingestion and could replay occurrence counts.
- Focused proof: `pytest -q tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_local_app.py` → `734 passed, 52 warnings`.
- Direct regressions: real SQLite approval of 1,001 suggestions in two chunks; 2,001-item middle failure persists completed, failed, and remaining IDs then resumes without re-ingestion; complete-set alias conflict and cycle preflight leaves rows pending; manual approval behavior remains unchanged; checkpoint round-trip uses `synonym_processing_runs.summary_json` and `source_operation`.
- Shared-defect patch: `ensure_control_plane_database()` no longer rewrites taxonomy mirror files during every worker/bootstrap call; explicit mirror repair remains available to app/admin lifecycle paths. Regression proves no repeated taxonomy mutation.

### Task 8: Re-measure, reconcile, and prepare handoff

**Purpose:**
- Prove specified defects are fixed and select, rather than silently include, any next latency phase.

**Task Function:**
- Run fresh full verification, compare identical workloads, inspect diffs, and record deviations.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: final cross-boundary verification needs independent evidence review.

**Validator Profile:**
- Controller-selected: review
- Selection basis: resolve an independent validator through Planning Dispatch before activation.

**Specification Coverage:**
- All implementation outcomes, regression proof, matched workload measurement, first-phase boundary, and explicit non-goals.

**Required Skills:**
- `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify all modified files from Tasks 2–7
- Verify unchanged unrelated files: `frontend/package.json`, `frontend/package-lock.json`, `src/fitcv/pipeline.py`, `src/fitcv/preference_policy.py`, `tests/test_pipeline.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_preference_policy.py`
- Verify plan ledger and Git diff

**Dependencies:**
- Tasks 2–7 complete with accepted task-local proof.

**Authority:**
- Preauthorized local actions: run declared tests/build/typecheck/browser measurements, inspect diff and plan state, and record evidence/deviations
- Stop for: failed required proof, dirty unrelated files changing, new optimization scope, external Git action, installer rebuild, or destructive cleanup

**Steps:**
- [x] Step 1: Run focused frontend and backend tests after all changes.
- [-] Step 2: Run frontend typecheck/build without changing dependency manifests; build passes, typecheck is blocked by pre-existing test typings and fixture errors.
- [-] Step 3: Repeat identical browser measurements for run detail, Pipeline Results from page 1 and page 2, Bookmarks, Synonyms, Settings, active runs, and trigger acknowledgement; trigger acknowledgement remains unmeasured.
- [-] Step 4: Match Task 1 dataset, run status, page size, warm/cold state, concurrent activity, browser viewport, and polling state; separate browser duration, backend processing, database wait, response bytes, render delay, request count, and endpoint where measurable; matching baseline is unavailable for page 2, polling, and trigger acknowledgement.
- [-] Step 5: Measure polling alone and polling during typing; exclude legitimate scheduled polling from search-only request assertions; live polling replay remains unavailable.
- [x] Step 6: Compare request count, response bytes, latency, focus, mounted UI, stale-response behavior, polling overlap, and response correctness against available Task 1 evidence; record unavailable comparisons explicitly.
- [x] Step 7: Treat completion as fixing specified defects, not full search or trigger latency resolution. If Jobs or search remains dominated by `_filtered_run_job_rows`, record evidence and open a new plan for SQL filtering/counting/pagination followed by page-only hydration while preserving search and result-count semantics.
- [-] Step 8: Re-measure trigger acknowledgement; do not add preparation lifecycle work unless a separately approved scope exists. Measurement remains blocked.
- [x] Step 9: Run `git diff --check`, inspect `git status`, and update this plan's ledger only after proof is accepted.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_worker_job_synonym_auto_accept.py`
- Expected: all focused backend proof passes.
- [x] `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/bookmarks.test.ts src/features/synonyms/synonyms.test.ts`; `npm run build`
- [-] `npm run typecheck`; blocked by pre-existing missing Node/test typings and unrelated `RunJobItem` fixture fields.
- Expected: focused frontend tests and production build pass without dependency-manifest edits.
- [x] Browser request/payload/focus/pagination replay against production build
- [-] Polling and trigger acknowledgement replay; unavailable under current runtime/workload constraints.
- Expected: no duplicate search-triggered detail/events calls, no duplicate page-2 jobs call, smaller detail response, and preserved visible behavior.
- [x] `git diff --check`; `git status --short --branch`
- Expected: no whitespace errors; only approved task files plus the seven preserved pre-existing dirty files appear.

**Current Verification Evidence (2026-09-13):**
- Focused backend suite passes: `705 passed` across app, SQLite, settings, provider, and synonym-worker tests.
- Focused frontend suite passes: `42 passed` across run detail, Bookmarks, and Synonyms tests; the new pagination-ownership regression passes after reproducing the duplicate request.
- Full frontend suite: `289 passed, 1 failed`; the failure is pre-existing `src/test/scans.test.ts` wording drift (`Full-time` expected, `Full time` rendered) and is outside this plan.
- `npm run build` passes; Vite reports one existing large minified chunk (`550.57 kB`, gzip `147.93 kB`). `npm run typecheck` remains blocked by existing missing Node/test typings and unrelated `RunJobItem` fixture fields.
- Browser replay against `http://127.0.0.1:8000`: initial run detail loads one run-detail, one events, and one jobs request; settled search produces one jobs request without search-triggered detail/events requests; after switching to Enrichment and opening page 2, exactly one `jobs?page=2` request is observed after the pagination patch. Search input remains focused. Decoded response sizes: run detail `5,456` bytes, initial jobs `105,246`, searched jobs `113,382`, Bookmarks `236,024`, searched Bookmarks `60,788`, Synonyms `12,974`, searched Synonyms `13,194`, Settings `30,860`; no compression transfer size is inferred.
- Browser timing samples are recorded for runs, run detail, jobs, Bookmarks, Synonyms, and Settings through the Performance API, but no matched Task 1 browser baseline exists for page 2, active polling, or trigger acknowledgement. Playwright E2E remains blocked because the Chromium executable is unavailable; do not install it under this scope.
- Trigger acknowledgement and queued-worker live replay remain unmeasured. No preparation lifecycle change is justified by current evidence.
- `git diff --check` passes. `frontend/test-results/` is task-owned browser residue; exact-path cleanup was attempted but blocked by command policy, so it remains untracked pending authorized cleanup. Unrelated dirty files remain preserved.

**Exit Criteria:**
- Fresh final evidence passes, remaining work is either complete or recorded as a new scoped plan, and no Git disposition is performed.

## Verification

Final artifact verification belongs to `skill-verification-before-completion` after implementation, not plan drafting.

- Run the focused Python suite covering app, SQLite, settings, provider, startup/bootstrap, and synonym worker behavior.
- Run the focused Vitest suite covering run detail, Bookmarks, and Synonyms.
- Run `npm run typecheck` and `npm run build`.
- Repeat identical browser/network measurements from Task 1.
- Run `git diff --check` and reconcile `git status --short --branch` against preserved dirty files.

## Completion Criteria

The plan is ready for completion verification when:

1. every implementation outcome has an accepted task and task-local proof
2. run-detail, Bookmark, and Synonym request-count regressions pass
3. run-detail payload and artifact/download compatibility pass direct backend tests
4. jobs route uses `SELECT 1` existence proof with unchanged response behavior
5. startup/bootstrap tests cover fresh databases, supported upgrades, concurrent startup, missing provider state, and fail-closed lock handling
6. read-path lock and file-state tests prove no unsafe rotation for `database is locked`
7. synonym automation proves 1,001 IDs, 2,001-item middle failure, cross-boundary conflicts/cycles, manual-semantic preservation, restart resume, and idempotency
8. comparable browser and backend measurements are recorded without invented performance gates
9. deferred search-index and trigger-lifecycle work is either unsupported by evidence or moved to a new approved plan
10. unrelated dirty files remain unchanged
11. `skill-verification-before-completion` returns `verified` before any completion status update
