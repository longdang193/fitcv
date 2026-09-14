---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-async-lifecycle-correctness
targets:
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - frontend/src/features/runs/api.ts
  - frontend/src/features/runs/runs-list.tsx
  - frontend/src/test/runs-list.test.tsx
  - frontend/src/features/scans/api.ts
  - frontend/src/features/scans/scan-detail.tsx
  - frontend/src/features/scans/scans-list.tsx
  - frontend/src/features/scans/route.tsx
  - frontend/src/test/scans.test.ts
  - frontend/src/features/candidate-profile/api.ts
  - frontend/src/features/candidate-profile/components/CatalogView.tsx
  - frontend/src/features/candidate-profile/components/DetailView.tsx
  - frontend/src/features/candidate-profile/components/ProcessingStep.tsx
  - frontend/src/features/candidate-profile/components/SourceDialog.tsx
  - frontend/src/test/candidate-profile.test.ts
  - frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx
  - frontend/src/test/pipeline-settings.test.tsx
  - frontend/src/features/synonyms/policy-editor.tsx
  - frontend/src/features/synonyms/synonyms.test.ts
  - frontend/e2e/async-lifecycle.spec.ts
---

# FitCV Async Lifecycle Correctness

## Goal

Remove stale async state writes and polling lifecycle races in the frontend.
The implementation must prevent false `Run not found` states, stop timers after
disposal, preserve current data during refresh, and protect unsaved editor
drafts without changing backend response contracts or disabling React
`StrictMode`.

## Review Disposition

The verdicts support one shared root cause: request, loading, cursor, and
polling ownership are split across unrelated refs and callbacks. Confirmed
scope:

- Run Detail stale `finally`, shared lifecycle invalidation, premature terminal
  finalization, and event-cursor exhaustion handling.
- Runs list callback writes that occur before coordinator request validation.
- Scan Detail unguarded loaders and timer re-arming after cleanup.
- Candidate Profile catalog/detail stale loaders and coupled draft/profile
  loads.
- Pipeline Settings and Synonym Policy responses overwriting editable drafts.
- Scans URL parsing retaining prior lifecycle/page when parameters are absent.

Deferred from this plan:

- Global cache, React Query, or a new generic fetch framework.
- Broad routing consolidation or hash-state rewrite.
- Backend contract changes, asynchronous `preparing` lifecycle, ETags, or
  `304` client behavior.
- Provider settings, New Run, and scan-picker effect changes until a focused
  reproduction proves the same user-visible race.
- Candidate Profile processing and source-dialog loaders are included after
  focused evidence confirmed mount-only guards allowed stale attempt/source
  responses to settle into a replacement view. Baseline, derived, confirmation,
  and synonym-detail loaders remain outside this pass pending separate
  reproductions.
- P0 incident labels; evidence supports high-priority correctness work, not
  universal P0 classification.

## Implementation Outcomes

### Resource-owned async state

Each independently loaded resource accepts state updates only from its current
request/session identity. Abort is used where API wrappers support it, but
correctness does not depend on cancellation being honored by the server.
`finally` blocks use the same ownership check as data and error writes.

### Correct polling and finalization

Polling owns its timer, in-flight request, cursor, and cleanup generation.
Cleanup prevents new work from being scheduled after awaited work returns.
Event pagination distinguishes “another page exists” from “cursor exhausted.”
Because the current backend has no continuation token after the final page, the
frontend retains the last valid request cursor and performs bounded final-page
rereads. This preserves live-event discovery without manufacturing cursors or
replaying the full history. Terminal status renders immediately; final
jobs/events refresh has separate state, bounded retry, and visible failure
handling.

### Safe retained-data and draft behavior

An accepted empty response counts as loaded. Refresh keeps accepted rows
mounted while exposing busy/error state separately. Saved server state, the
draft base snapshot/revision, and editable draft values remain separate;
accepted background reads cannot erase dirty edits or silently move their
optimistic-concurrency baseline.

### Regression proof

Production browser tests cover StrictMode replay, out-of-order responses,
unmount and identity changes, polling cleanup, terminal refresh failure,
successful-empty responses, URL default parsing, independent catalog loads, and
draft preservation. Vitest remains for pure coordinator and route logic; it is
not treated as proof that React effects ran.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-frontend-component-engineering`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed frontend files, add focused frontend tests, run declared local checks, and inspect current source/tests
- User-approval actions: dependency installation, authentication, branch/worktree changes, cleanup, discard, commit, push, merge, publication, or scope expansion
- Parallel ownership: none; lifecycle changes share request and loading semantics
- Sequential fallback: `Task 1 → Task 2 → Task 3 → Task 4`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `2bd1024b0d67f24162d4b511a4f6a1b5df2a6768`
- Expected workspace: `main` with preserved unrelated dirty files in `config/taxonomy/skill_synonyms.yaml`, `frontend/package.json`, `frontend/package-lock.json`, `src/fitcv/pipeline.py`, `src/fitcv/preference_policy.py`, related pipeline tests, and `frontend/test-results/`
- Next action: preserve changes for review or explicitly authorize branch
  finishing.
- Blockers: none for implementation verification; Chromium installed locally
  and focused browser proof passed.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | Run Detail race and finalization tests | Vitest 12 passed; build passed; E2E 2 passed after local Chromium install; typecheck baseline unchanged |
| Task 2 | `completed` | current | `codex/high` | Task 1 | Scan lifecycle, cursor, and route tests | Herdr lane complete; Vitest 13 passed with 1 pre-existing `Full-time` label failure; E2E 4 passed; build passed; typecheck baseline-only failures |
| Task 3 | `completed` | current | `codex/normal` | Task 1 | Runs coordinator out-of-order and loading tests | Herdr lane complete; Vitest 12 passed; E2E 5 passed; build passed; typecheck baseline-only failures |
| Task 4 | `completed` | current | `codex/high` | Tasks 1–3 | Candidate/editor stale-response and draft tests | Herdr lane complete; focused Vitest 101 passed; E2E 9 passed; build passed; typecheck baseline-only failures |

## Task Breakdown

### Task 1: Repair Run Detail ownership and terminal refresh

**Purpose:**
- Prevent stale initial requests from clearing current loading state or
  producing false `Run not found` output.
- Keep detail, Jobs, Events, and polling ownership independent while retaining
  the existing mounted page and API contracts.

**Task Function:**
- Repair existing request lifecycle at production component boundaries.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared state ownership and StrictMode-sensitive async race.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: browser tests must execute production effects; Vitest covers
  only pure helpers and coordinator logic.

**Specification Coverage:**
- An old request cannot update data, error, loading, cursor, or finalization
  state after replacement, cleanup, or run identity change.
- “Run not found” requires an accepted authoritative detail outcome, not merely
  `run === null` after a stale request settles.
- Terminal status is accepted before final Jobs/Events refresh; refresh failure
  remains visible and retryable.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`,
  `skill-frontend-component-engineering`

**Files And Symbols:**
- Inspect: `frontend/src/features/run-detail/run-detail-page.tsx:loadRunDetail`,
  `pollEvents`, `drainEvents`, initial-load effect, polling effect.
- Modify: `frontend/src/features/run-detail/run-detail-page.tsx` and
  `frontend/src/features/runs/api.ts` only when signal propagation is missing.
- Verify: `frontend/src/features/run-detail/run-detail-page.test.tsx`.

**Dependencies:**
- Current `fetchRun`, Jobs, and Events response contracts.
- Existing Jobs request-ID pattern; do not introduce a generic
  `useLatestRequest()` abstraction unless repeated implementation proves it is
  smaller and clearer.

**Authority:**
- Preauthorized local actions: edit listed Run Detail/API files, add focused tests, and run the Task 1 test command
- Stop for: backend response-contract changes, new dependency, unrelated dirty-file conflict, or cache/routing scope expansion

**Steps:**
- [ ] Step 0: Run preflight from `frontend`: record `git rev-parse HEAD`,
  `git diff -- <all target files>`, `npm ls --depth=0`, the existing focused
  Vitest baseline, and a Playwright smoke launch. Confirm
  `frontend/vitest.config.ts` uses `environment: "node"`; use the existing
  Playwright setup and new `frontend/e2e/async-lifecycle.spec.ts` for effect-
  level proof. Record failures before edits and stop if a target file has
  unrelated changes.
- [ ] Step 0b: Create or extend `frontend/e2e/async-lifecycle.spec.ts` with
  intercepted responses for Run Detail, Scans, Runs, Candidate Profile,
  Settings, and Synonyms. Keep server data fixtures local to the test and
  prove production effects through the running app; do not replace these
  checks with static rendering.
- [ ] Step 1: Add a detail-request identity and accepted-response state; guard
  data, error, loading, and `finally` writes with the same identity. Preserve
  abort handling and StrictMode replay behavior.
- [ ] Step 2: Give Jobs, Events, and polling independent ownership. A polling
  cleanup generation must not invalidate an unrelated detail request or Jobs
  query; each owner must check identity after every awaited boundary.
- [ ] Step 3: Separate terminal run status from final-results refresh. Stop
  active polling once terminal status is accepted and render that status. Track
  Jobs and Events finalization independently; retry only the unfinished
  operation, at most once, and never restart already drained event pages.
  Expose final-refresh failure after the retry is exhausted.
- [ ] Step 4: Preserve the current backend cursor contract. Advance the event
  cursor only when `next_cursor` is non-null. When the final page returns
  `null`, retain the cursor used for that request and perform bounded
  final-page rereads on later polls; keep initial `null` for an empty stream.
  Do not construct cursors in the frontend. Document server continuation as a
  separate follow-up, not as part of this task.

**Verification:**
- [ ] `npm test -- --run src/features/run-detail/run-detail-page.test.tsx`
- [ ] `npm run test:e2e -- e2e/async-lifecycle.spec.ts`
- Expected: StrictMode abort replay cannot clear replacement loading; stale
  detail/Jobs/Events responses cannot mutate current state; terminal status is
  visible when final refresh fails; cleanup starts no new polling work; empty
  streams discover later events; multi-page Events responses drain once, then
  reread only the final page; terminal catch-up retries only unfinished work.

**Exit Criteria:**
- Run Detail has independent accepted-response ownership for detail, Jobs,
  Events, and polling, with focused production-component regression proof.

### Task 2: Repair Scan Detail polling, loaders, cursor, and URL defaults

**Purpose:**
- Prevent Scan Detail and Scans List responses and timers from updating or
  rescheduling after disposal or identity/query changes.
- Make Scans URL parsing total and deterministic.

**Task Function:**
- Harden independent resource loaders and polling session cleanup.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: timer/request lifecycle and route-default correctness.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused fake-timer and component tests cover the bounded
  behavior.

**Specification Coverage:**
- Scan detail, Events, Jobs, and JSON loaders reject stale success, error, and
  loading settlements.
- Scans List rejects stale rows, totals, errors, and loading settlements after
  lifecycle/page changes.
- Cleanup prevents a completed in-flight poll from arming another timeout.
- Event cursor state distinguishes “last page” from “no cursor initialized.”
- `#/scans` restores `active`, page `1`, and no selected scan; omitted query
  parameters do not retain prior state.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`,
  `skill-frontend-component-engineering`

**Files And Symbols:**
- Inspect: `frontend/src/features/scans/scan-detail.tsx:loadScanData`,
  `loadJobs`, `loadJson`, polling effect; `frontend/src/features/scans/scans-list.tsx:loadScans`;
  `frontend/src/features/scans/route.tsx:parseHash`.
- Modify: `frontend/src/features/scans/scan-detail.tsx`,
  `frontend/src/features/scans/scans-list.tsx`,
  `frontend/src/features/scans/api.ts`, and `frontend/src/features/scans/route.tsx`.
- Verify: `frontend/src/test/scans.test.ts` and
  `frontend/e2e/async-lifecycle.spec.ts`.

**Dependencies:**
- Task 1 ownership rules and existing `apiClient` signal support.

**Authority:**
- Preauthorized local actions: edit listed Scans files, add focused tests, and run the Task 2 test command
- Stop for: backend scan contract changes, new polling abstraction, unrelated route rewrite, or destructive cleanup

**Steps:**
- [ ] Step 1: Add per-scan/detail and list-query loader/session identities and
  AbortSignal propagation for detail, Events, Jobs, JSON, and list reads. Guard
  every state write and `finally` settlement.
- [ ] Step 2: Replace timer re-arm-after-await behavior with a session-owned
  poll loop that checks disposal, identity, visibility, and terminal status
  before scheduling the next timeout.
- [ ] Step 3: Apply the same backend-compatible cursor rule as Task 1: advance
  only on a non-null next cursor, retain the last valid request cursor after
  final-page exhaustion, and reread only that bounded final page. Test an
  initially empty stream, new events after exhaustion, multiple pages, and
  terminal catch-up. Keep deduplication as a safety net, not as the primary
  correctness mechanism.
- [ ] Step 4: Make `parseHash` assign defaults on every parse, including hashes
  without `lifecycle` and `page`, then add direct route regression coverage.

**Verification:**
- [ ] `npm test -- --run src/test/scans.test.ts`
- [ ] `npm run test:e2e -- e2e/async-lifecycle.spec.ts`
- Expected: delayed old scan responses cannot replace current data; cleanup
  leaves no newly scheduled timer; terminal scans do not continue polling;
  exhausted Events discover later events without full-history replay; stale
  Scans List responses cannot replace a newer page; bare `#/scans` restores
  active/page 1.

**Exit Criteria:**
- Scan Detail and Scans route have deterministic ownership and cleanup proof.

### Task 3: Close Runs coordinator settlement gap

**Purpose:**
- Prevent Runs list callbacks from committing stale rows, totals, errors, or
  loading state before `RunsPollingCoordinator` validates request identity.

**Task Function:**
- Align callback state writes with coordinator request ownership.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: small shared coordinator change with out-of-order response risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing coordinator unit tests can deterministically resolve
  same-query and changed-query overlaps.

**Specification Coverage:**
- Callback state writes and loading settlement require both current query and
  current request generation.
- Coordinator setup and teardown survive StrictMode setup-cleanup-setup replay;
  the second setup owns a functioning coordinator and does not reuse destroyed
  state.
- A request finishing late cannot alter rows, totals, counts, error, or loading,
  even when its query key matches a newer request.
- Polling remains single-flight and stops when all visible runs are terminal.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `frontend/src/features/runs/runs-list.tsx:RunsPollingCoordinator.load`,
  `RunsListPage` callback, and `frontend/src/features/runs/api.ts:fetchRuns`.
- Modify: `frontend/src/features/runs/runs-list.tsx` and `fetchRuns` only if
  signal propagation is needed for the ownership contract.
- Verify: `frontend/src/test/runs-list.test.tsx`.

**Dependencies:**
- Task 1’s accepted-response rule; no dependency on a shared fetch framework.

**Authority:**
- Preauthorized local actions: edit listed Runs files, add focused tests, and run the Task 3 test command
- Stop for: API response changes, coordinator redesign beyond request ownership, or unrelated polling behavior changes

**Steps:**
- [ ] Step 1: Make the coordinator the single acceptance boundary. Keep the
  transport callback responsible for fetching and returning data; let the
  coordinator validate request ID and query identity before committing rows,
  totals, counts, errors, and loading state. Do not expose request IDs to
  several independent state-writing callbacks.
- [ ] Step 2: Make coordinator creation/setup and teardown explicit and safe
  under StrictMode setup-cleanup-setup replay. The second setup must create or
  retain a live coordinator, while cleanup must stop timers, settle ownership,
  and prevent late callbacks from committing.
- [ ] Step 3: Add abort propagation only where it reduces work without being
  required for correctness; stale-response guards remain authoritative.
- [ ] Step 4: Preserve visibility pause/resume, single-flight, and terminal
  stop behavior.

**Verification:**
- [ ] `npm test -- --run src/test/runs-list.test.tsx`
- [ ] `npm run test:e2e -- e2e/async-lifecycle.spec.ts`
- Expected: two same-query requests resolving out of order leave newer data;
  changed-query and destroyed-coordinator responses cannot settle current
  state; StrictMode setup-cleanup-setup leaves one live coordinator; polling
  pause/resume and terminal stop remain green.

**Exit Criteria:**
- Coordinator and callback share one request-generation acceptance rule.

### Task 4: Protect Candidate Profile loads and editor drafts

**Purpose:**
- Stop Candidate Profile catalog/detail, Pipeline Settings, and Synonym Policy
  loaders from accepting stale responses or overwriting user edits.
- Decouple independent Candidate Profile resources so page changes do not reload
  unchanged creation attempts or let one failure hide another successful load.

**Task Function:**
- Separate resource ownership from editable draft state with the smallest
  existing-component changes.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: multiple related frontend loaders with direct user-data loss
  risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing Candidate Profile, Pipeline Settings, and Synonyms
  test suites provide focused regression locations.

**Specification Coverage:**
- Catalog attempts and profile pagination have independent request identities,
  loading, and error state. Changing page/tab does not refetch attempts unless
  explicitly requested.
- Candidate Profile detail accepts only the current `profileId` request.
- Settings and synonym policy keep latest server state, the draft base snapshot
  and original revision, and editable draft values separate. While dirty, a
  valid late read cannot erase edits or silently advance the draft's save
  baseline. Conflict/reload requires explicit resolution.
- Synonym drafts are keyed by policy type; switching types while dirty cannot
  carry one policy's text or revision into another.
- Accepted empty results count as loaded; refresh does not blank retained rows.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`,
  `skill-frontend-component-engineering`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `CatalogView:loadData`, `DetailView:loadDetail`,
  `PipelineSettingsDialog:loadSettings`, `PolicyEditor:loadPolicy`.
- Modify: `frontend/src/features/candidate-profile/components/CatalogView.tsx`,
  `DetailView.tsx`, `frontend/src/features/candidate-profile/api.ts`,
  `frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx`,
  `frontend/src/features/synonyms/policy-editor.tsx`, and only the API wrappers
  needed for signal propagation.
- Verify: `frontend/src/test/candidate-profile.test.ts`,
  `frontend/src/test/pipeline-settings.test.tsx`, and
  `frontend/src/features/synonyms/synonyms.test.ts`.

**Dependencies:**
- Tasks 1–3 establish the accepted-response and retained-data rules.
- Existing saved/draft state in Pipeline Settings and Synonym Policy is the
  canonical state model; do not add a global editor store.

**Authority:**
- Preauthorized local actions: edit listed Candidate Profile/settings/synonym files, add focused tests, and run the Task 4 test command
- Stop for: new global cache/store, backend contract changes, unrelated editor redesign, or dirty-file conflict

**Steps:**
- [ ] Step 1: Split Catalog attempts and profile-page requests. Give each
  resource its own request identity, abort path, loading/error state, and
  accepted-empty handling. Retain profiles when attempts fail and vice versa.
- [ ] Step 2: Guard Candidate Profile detail success/error/loading settlement
  by `profileId` request identity and preserve existing action behavior.
- [ ] Step 3: Add request ownership to settings and synonym loads. Keep latest
  server state separate from the draft's base snapshot, base revision, and
  editable values. While dirty, do not advance the base snapshot/revision from
  a background read; expose an explicit conflict/reload decision. Advance the
  base only after explicit discard/reload or successful save. Never infer
  dirtiness from row count.
- [ ] Step 4: Bind synonym draft state to policy type. Switching types while
  dirty must retain a per-type draft or require explicit discard; a response for
  an old type cannot populate the current editor.
- [ ] Step 5: Keep populated content mounted during refresh and expose a
  compact busy/error state through existing components. Do not create a shared
  loading abstraction until at least two touched components need identical
  behavior.
- [ ] Step 6: Add rapid-switch, delayed-response, successful-empty, remote
  untouched-field change, save-conflict, post-save late-read, dirty type-switch,
  and draft-preservation tests against production components through the
  Playwright harness. Keep pure transformation tests in Vitest.

**Verification:**
- [ ] `npm test -- --run src/test/candidate-profile.test.ts src/test/pipeline-settings.test.tsx src/features/synonyms/synonyms.test.ts`
- [ ] `npm run test:e2e -- e2e/async-lifecycle.spec.ts`
- Expected: Candidate Profile page switches do not duplicate unrelated draft
  loads; late responses cannot replace current rows or errors; empty accepted
  results leave loading; settings/synonym edits survive late reads; remote
  changes to untouched fields preserve the original draft revision and surface
  conflict; save conflicts and post-save reads settle correctly; dirty synonym
  type switches preserve type ownership; refresh preserves populated content.

**Exit Criteria:**
- Candidate Profile and editor loaders have independent request ownership and
  draft-safe settlement with regression coverage.

## Verification

Run after all tasks, without staging or modifying unrelated dirty files:

- `npm test -- --run src/features/run-detail/run-detail-page.test.tsx src/test/runs-list.test.tsx src/test/scans.test.ts src/test/candidate-profile.test.ts src/test/pipeline-settings.test.tsx src/features/synonyms/synonyms.test.ts`
- `npm run test:e2e -- e2e/async-lifecycle.spec.ts`
- `npm run build`
- `npm run typecheck` for changed-file diagnostics; record existing unrelated
  failures separately rather than widening scope to legacy tests or plans.
- Browser smoke flow with the configured browser capability: open Runs, switch
  rapidly between run IDs/searches, open Scans and leave a running scan,
  revisit Candidate Profile, switch profile pages/tabs, and edit Settings and
  Synonyms while delayed reads resolve. Confirm no document reload, no false
  not-found state, no post-cleanup polling request, retained rows during
  refresh, and preserved drafts.

The full repository gate is not completion proof for this plan when it fails on
pre-existing legacy specs/plans. Use focused tests, build output, changed-file
diagnostics, and browser evidence instead.

Final evidence:

- Focused Vitest: 138 passed, 1 pre-existing Scans label assertion failed
  (`Full-time` vs rendered `Full time`); Candidate/editor lane: 101 passed.
- Playwright `e2e/async-lifecycle.spec.ts`: 9 passed.
- `npm run build`: passed with existing chunk-size warning.
- `npm run typecheck`: pre-existing Node/test typing and `RunJobItem` fixture
  diagnostics only; no new changed-file diagnostics.
- Full repository gate skipped per approved instruction because failures are in
  pre-existing legacy specs/plans.
- Unrelated dirty files remain untouched; no commit, push, branch change, or
  cleanup performed.

## Completion Criteria

The plan is ready for completion verification when:

1. Run Detail, Runs, Scan Detail, Candidate Profile, Pipeline Settings, and
   Synonym Policy accept state only from current request/session owners.
2. No cleanup path schedules new polling work after awaited work returns.
3. Event cursor exhaustion, terminal finalization, successful-empty loading, and
   retained-data behavior have focused regression proof.
4. Dirty editor drafts preserve their original base snapshot/revision until
   explicit resolution or successful save; late reads and type switches cannot
   cross-contaminate drafts.
5. URL parsing restores deterministic Scans defaults, and Scans List stale-page
   responses are rejected.
6. Vitest pure-logic checks and Playwright production-effect tests pass; build
   passes; typecheck findings are reconciled against the
   pre-change baseline.
7. Unrelated dirty files remain untouched and all deviations or deferrals are
   recorded before any branch-finishing action.
