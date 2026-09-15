---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
---

# Unified Date-Range Filters

## Goal

Add one consistent date-range filter to Runs, Scans, and Bookmarks:
`Today`, `24h`, `7D`, `30D`, and `All`. Default selection is `Today`.
Filtering must happen before pagination, survive navigation/reload through URL
state, preserve existing lifecycle/search filters, and avoid hiding older scans
from non-list consumers such as Run source selection.

## Implementation Outcomes

### Shared date-range contract

Runs, scans, and bookmarks expose one validated `date_range` contract with
server-side filtering and stable pagination. `Today` uses the browser's local
calendar boundary through an optional IANA `timezone`; rolling windows use the
 current instant. Endpoint missing or invalid values resolve to `today`; direct
 store callers may retain an explicit legacy `all` default for compatibility.
 Internal cross-list consumers explicitly request `all` when they need the
 complete set.

### Consistent list experience

All three list pages render the same accessible segmented control, default to
`Today`, reset pagination when the range changes, preserve the range in hash
URL state, and show an explicit empty-state path to `All`.

### Regression proof

Backend tests prove boundary inclusion, invalid/default values, combined
filters, and pre-pagination counts. Frontend tests prove query serialization,
URL persistence, default selection, page reset, stale-request safety, and
accessibility. Browser verification covers all three pages at desktop and
mobile widths.

## Execution Approach

- Mode: `subagent-ready`
- Coordination: `git-tracked`
- Required skills: `skill-chief-of-staff`, `skill-full-stack-integration`, `skill-backend-verification`, `skill-frontend-component-engineering`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect and edit plan-owned source/tests, run declared local checks, and use browser verification; preserve named pre-existing dirty files
- User-approval actions: push, merge, publication, destructive cleanup, discard, or changes outside declared ownership
- Parallel ownership: backend contract lane owns `src/fitcv_cp` and backend tests; frontend lane owns `frontend/src` and frontend tests; lead controller owns plan, integration, and acceptance
- Sequential fallback: complete and verify backend contract before frontend lane; run final integration proof after both lanes

## Coordination State

- Coordination owner: `single lead controller using CoS`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `3105a02b`
- Expected workspace: `main` with preserved unrelated changes in `config/taxonomy/skill_synonyms.yaml`, `frontend/package-lock.json`, `frontend/package.json`, `src/fitcv/pipeline.py`, `src/fitcv/preference_policy.py`, `tests/test_pipeline.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_preference_policy.py`, and untracked `frontend/test-results/`
- Next action: none; plan execution complete, awaiting explicit Git disposition; review budget exhausted without verdict because provider returned `503`
- Blockers: `none`; preserved dirty files are outside this plan. `npm run typecheck` still reports pre-existing unrelated test-global/Node-type errors; all date-range wiring errors are resolved.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1: Backend date-range contract | `completed` | current | `codex` | none | focused app/store tests | `715 passed`; compatibility fixture accepts new scan query contract; `git diff --check` passed |
| Task 2: Shared frontend filter | `completed` | current | `ui` | Task 1 | focused frontend tests | focused `95 passed`; full frontend `324 passed`; `npm run build` and `git diff --check` passed; deep-link reload regression fixed |
| Task 3: Integration and acceptance proof | `completed` | current | `codex` | Tasks 1–2 | full focused backend/frontend checks and browser flow | original DB `C:\Users\HOANG PHI LONG DANG\AppData\Local\FitCV\data\fitcv.sqlite3`; Runs `24h=2`, `7D=12`, `All=13`; Scans `All=2`; Bookmarks `All=27`; desktop and 390px mobile snapshots show filters, URL state, and settled loading |

## Task Breakdown

### Task 1: Backend date-range contract

**Purpose:**
- Add one validated date-range parameter to all three list endpoints and stores.
- Filter before pagination without changing existing status, lifecycle, stage, result, search, or sort behavior.

**Task Function:**
- Implement and verify a shared server-side date-window boundary for three resource types.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: ordinary multi-file backend contract with bounded SQLite and API changes; reliable without highest-cost profile.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent contract and boundary-test verification.

**Specification Coverage:**
- Five values only: `today`, `24h`, `7d`, `30d`, `all`.
- Default `today`; invalid values fail closed to `today`.
- `Today` uses requested IANA timezone, with UTC fallback; rolling windows use current UTC instant.
- Runs use `created_at`; scans use `created_at`; bookmarks use `bookmarked_at`.
- `all` remains available for complete-set consumers.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:get_runs_list`, `src/fitcv_cp/app.py:get_scans`, `src/fitcv_cp/app.py:get_bookmarks`
- Inspect: `src/fitcv_cp/sqlite_store.py:list_runs`, `src/fitcv_cp/sqlite_store.py:query_scans`, `src/fitcv_cp/sqlite_store.py:query_bookmarks`
- Modify: `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, and the shared date-window helper location selected by existing ownership
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_store.py`

**Dependencies:**
- Existing timestamp parsing and SQLite connection helpers remain canonical.
- No schema migration unless source inspection proves a required timestamp is absent.

**Authority:**
- Preauthorized local actions: edit only backend date-range code/tests named above and run focused backend checks.
- Stop for: schema migration, API response-shape change beyond query parameters, unrelated dirty-file edits, or timezone behavior that requires a new product decision.

**Steps:**
- [x] Step 1: Define a typed/validated date-range vocabulary and boundary helper using existing timestamp/UTC utilities.
- [x] Step 2: Add `date_range` and optional `timezone` to `/runs`, `/scans`, and `/bookmarks`; pass them through store queries before slicing pages.
- [x] Step 3: Expose `all` through the backend contract; Task 2 updates non-list scan consumers to request `date_range=all` explicitly.
- [x] Step 4: Add boundary, default, invalid, combined-filter, and pre-pagination tests.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -k 'date_range or runs or scans or bookmarks'` — `715 passed`.
- Expected: new date-range tests pass; existing selected list/store tests remain green; old rows are excluded only when range is not `all`.

**Exit Criteria:**
- All three endpoints accept the same range vocabulary, return correctly paginated filtered data, preserve legacy direct store callers, and leave frontend `all` caller updates to Task 2.

### Task 2: Shared frontend filter

**Purpose:**
- Render one reusable segmented control and connect it to Runs, Scans, and Bookmarks.

**Task Function:**
- Integrate shared URL-backed date-range state into three existing list controllers without duplicating filter semantics.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve through CoS; UI state and async list ownership require frontend-capable profile.

**Validator Profile:**
- Controller-selected: `ui`
- Selection basis: independent responsive, keyboard, focus, and visual-state validation.

**Specification Coverage:**
- Labels match `Today | 24h | 7D | 30D | All`.
- `Today` is selected when URL state is absent or invalid.
- Changing range resets page to `1`, cancels/replaces stale list requests, and updates hash state.
- Detail navigation/back preserves range; empty filtered lists offer `All`.

**Required Skills:**
- `skill-frontend-component-engineering`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Add/modify: `frontend/src/components/DateRangeFilter.tsx` and shared styles in `frontend/src/styles/main.css` only if existing tokens cannot express the control.
- Modify: `frontend/src/features/runs/api.ts`, `frontend/src/features/runs/route.tsx`, `frontend/src/features/runs/runs-list.tsx`
- Modify: `frontend/src/features/scans/api.ts`, `frontend/src/features/scans/route.tsx`, `frontend/src/features/scans/scans-list.tsx`, `frontend/src/features/scans/run-source-selection.tsx`
- Modify: `frontend/src/features/bookmarks/api.ts`, `frontend/src/features/bookmarks/route.tsx`
- Verify: `frontend/src/test/runs.test.ts`, `frontend/src/test/runs-list.test.tsx`, `frontend/src/test/scans.test.ts`, `frontend/src/test/bookmarks.test.ts`, plus a focused component test for `DateRangeFilter`

**Dependencies:**
- Task 1 query parameter contract is fixed and backend tests pass.
- Existing route hash parsers remain source of truth for page/detail state.

**Authority:**
- Preauthorized local actions: edit only shared filter, three list/API/route surfaces, non-list `all` caller, and focused frontend tests/styles named above.
- Stop for: new routing architecture, client-side filtering after pagination, cache layer, broad visual redesign, or edits to unrelated dirty files.

**Steps:**
- [x] Step 1: Add shared `DateRange` type, labels, parser, default, and accessible segmented-control component.
- [x] Step 2: Add `date_range` and timezone serialization to the three API helpers.
- [x] Step 3: Thread range through each list query key, loader, URL parser/updater, page-reset path, and empty state.
- [x] Step 4: Pass `all` from Run source selection so older active scans remain selectable.
- [x] Step 5: Add focused tests for defaults, query strings, URL persistence, page reset, stale request ownership, keyboard access, and mobile-safe markup.

**Verification:**
- [x] `npm exec vitest run src/test/runs.test.ts src/test/runs-list.test.tsx src/test/scans.test.ts src/test/bookmarks.test.ts src/components/DateRangeFilter.test.tsx` — `95 passed`.
- Expected: all range/query/state tests pass; list requests include the selected range; source selection requests `all`.

**Exit Criteria:**
- Runs, Scans, and Bookmarks show identical filter behavior and no list path silently falls back to client-side filtering or loses URL state.

### Task 3: Integration and acceptance proof

**Purpose:**
- Reconcile backend/frontend changes under CoS and prove user-visible behavior across supported viewports.

**Task Function:**
- Execute final integration checks, inspect changed-surface impact, and capture acceptance evidence.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: Codex lead retains acceptance and browser authority.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent final evidence review after implementation.

**Specification Coverage:**
- All five filters work on all three list pages with Today default.
- Existing search/status/stage/lifecycle filters remain composable.
- Pagination totals reflect filtered rows.
- Browser behavior matches committed tests.

**Required Skills:**
- `skill-chief-of-staff`
- `skill-verification-before-completion`
- `skill-requesting-code-review`

**Files And Symbols:**
- Inspect: all Task 1–2 changed files and `docs/fitcv-new-frontend.integration.md`
- Modify: no product source by default; update integration note only if it is the canonical contract-to-UI sidecar and remove temporary notes after acceptance.
- Verify: backend and frontend commands from Tasks 1–2, frontend build, and browser flow.

**Dependencies:**
- Tasks 1–2 complete with accepted lane evidence.
- Review budget remains at most two evaluation turns; unresolved findings block acceptance until patched or explicitly deferred.

**Authority:**
- Preauthorized local actions: run final checks, inspect browser output, and update plan evidence/status without changing product scope.
- Stop for: failed required proof, unexpected worktree mutation, contract mismatch, or any requested push/merge/publication.

**Steps:**
- [x] Step 1: Reconcile lane Git facts and run focused backend/frontend checks plus frontend build.
- [x] Step 2: Browser-test Runs, Scans, and Bookmarks at desktop and mobile widths; verify default Today, each range, All recovery, pagination, and back navigation.
- [x] Step 3: Record evidence and final acceptance decision in this plan; leave Git disposition for explicit user approval.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py` — `715 passed`.
- [x] `npm exec vitest run src/test/runs.test.ts src/test/runs-list.test.tsx src/test/scans.test.ts src/test/bookmarks.test.ts src/components/DateRangeFilter.test.tsx` — `95 passed`.
- [x] `npm run build` — passed; Vite emitted existing chunk-size warning only.
- Expected: focused suites and build pass; browser shows server-filtered counts and stable URL state on all three pages.

**Exit Criteria:**
- CoS accepts fresh proof, all plan tasks have recorded evidence, no unrelated dirty file changed, and the plan is ready for explicit Git disposition.

## Verification

- [x] Backend contract tests pass for all three endpoints and store methods.
- [x] Frontend focused tests pass for API serialization, URL state, page reset, async ownership, accessibility, and non-list `all` behavior.
- [x] `npm run build` passes.
- [x] Browser flow passes at desktop and mobile widths with `Today` default and all five choices.
- [x] `git diff --check` passes and preserved unrelated files remain unchanged.
- [x] Plan ledger records accepted evidence; full repository and legacy plan/spec gates intentionally skipped.

## Completion Criteria

- Runs, Scans, and Bookmarks share the same five-option date filter and `Today` default.
- Backend filters before pagination using resource-appropriate timestamps.
- URL state, empty-state recovery, keyboard behavior, and responsive layout are verified.
- Existing scan source selection still sees all eligible scans.
- CoS review and final verification evidence are recorded; no push or merge occurs without explicit approval.
