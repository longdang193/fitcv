---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: fitcv-run-full-export-ssot
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - frontend/src/features/runs/api.ts
  - frontend/src/features/run-detail/run-detail-page.tsx
  - tests/test_fitcv_cp/test_app.py
  - frontend/src/test/runs.test.ts
---

# Goal

Preserve the existing 13-column Pipeline Results CSV contract while adding a
separate full-fidelity run export that includes raw source data and canonical
enrichment. Remove CSV header/row mapping drift by making one backend column
specification the sole CSV mapping source.

## Implementation Outcomes

### Stable CSV contract

`GET /runs/{run_id}/jobs/export.csv` keeps current filters, header order,
column names, formula escaping, and downstream-compatible output. Header and
row values come from one backend column specification.

### Full-fidelity export

Run detail UI exposes separate CSV and full-export actions. Full export reuses
the existing versioned JSONL and manifest payload shape, preserves nested raw
job data, and includes canonical enriched fields already persisted in run-job
rows.

### Regression proof

Backend tests prove CSV width/order/value stability and full-export response
contracts. Frontend tests prove both actions send the expected run filters and
download paths.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-full-stack-integration`, `skill-test-driven-development`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared source and test files, run declared local checks, inspect configured local runtime evidence
- User-approval actions: commit, push, merge, publication, external writes, destructive recovery, discard, cleanup, and changes outside declared paths
- Parallel ownership: `none; app.py and its backend tests are shared sequential surfaces`
- Sequential fallback: `Task 1`, then `Task 2`, then `Task 3`, then final verification

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `b9a518622976baeaddb6afc398a5347422ed9ad0`
- Expected workspace: `main` with existing unrelated user changes preserved in `.gitignore`, `.serena/project.yml`, `data/`, two existing plan files, `.tmp/`, `fitcv-flow-preview.png`, and `node_modules/`; this plan is the only new planning artifact
- Next action: `resolve frontend typecheck baseline and run target-runtime export check`
- Blockers: `full frontend typecheck fails in pre-existing test typing; target backend runtime at 127.0.0.1:53361 is unavailable`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | `python -m pytest tests/test_fitcv_cp/test_app.py -k jobs_export` | 1 passed |
| Task 2 | `completed` | current | `codex` | Task 1 | `python -m pytest tests/test_fitcv_cp/test_app.py -k enriched_filtered` | 2 passed |
| Task 3 | `completed` | current | `codex` | Task 2 | `npm --prefix frontend test -- src/test/runs.test.ts` | 26 passed; production build passed; full typecheck blocked by pre-existing test typing errors |

## Task Breakdown

### Task 1: Consolidate CSV field mapping

**Purpose:**
- Remove confirmed SSOT violation between hardcoded CSV header and row mapping.

**Task Function:**
- Backend export-contract refactor.

**Template Profile:**
- `unresolved` until execution dispatch selects profile from `agents/*.toml`.

**Validator Profile:**
- `unresolved`; select independent validator after implementation proof exists.

**Specification Coverage:**
- Preserve current CSV contract.
- Make header, source key, and formatter one canonical mapping.
- Keep existing filtering and formula escaping behavior.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:GET /runs/{run_id}/jobs/export.csv`
- Modify: `src/fitcv_cp/app.py:CSV export route and local export constants`
- Verify: `tests/test_fitcv_cp/test_app.py:test_jobs_export_uses_full_filtered_rows_and_escapes_formulas`

**Dependencies:**
- Existing CSV route and test contract remain authoritative.

**Authority:**
- Preauthorized local actions: modify only `src/fitcv_cp/app.py` and the focused CSV test in `tests/test_fitcv_cp/test_app.py`; run local backend tests.
- Stop for: changed route contract, required schema migration, external dependency, unrelated dirty-file conflict, or any path outside declared ownership.

**Steps:**
- [x] Define one ordered CSV column specification containing header label, source key, and formatter.
- [x] Generate both CSV fieldnames and row values from that specification.
- [x] Preserve current 13-column order, filter behavior, formula escaping, and missing-value handling.
- [x] Update focused test assertions only where they prove the canonical mapping behavior.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k jobs_export`
- Expected: export tests pass; response header has 13 columns; every emitted row has matching width and stable order.

**Exit Criteria:**
- CSV header and row construction have one source in `src/fitcv_cp/app.py`.
- Focused backend export tests pass without changing public CSV output.

### Task 2: Add full-fidelity run export boundary

**Purpose:**
- Expose raw source and canonical enriched run-job data without overloading the stable CSV contract.

**Task Function:**
- Backend full-export vertical slice.

**Template Profile:**
- `unresolved` until execution dispatch selects profile from `agents/*.toml`.

**Validator Profile:**
- `unresolved`; select independent validator after implementation proof exists.

**Specification Coverage:**
- Add separate full export action for the run-detail flow.
- Reuse existing versioned JSONL and manifest contracts.
- Preserve nested raw job data and persisted enrichment.
- Prove success, unknown-run failure, filtering, row count, ordering, and checksum behavior.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:download_run_enriched_filtered_zip`
- Inspect: `src/fitcv_cp/sqlite_store.py:_filtered_run_job_rows`
- Modify: `src/fitcv_cp/app.py:shared full-export builder and user-facing run export route`
- Verify: `tests/test_fitcv_cp/test_app.py:enriched filtered export and route contract tests`

**Dependencies:**
- Task 1 keeps current CSV behavior stable.
- Existing `rerun_input.v1`, `rerun_export_manifest.v1`, `jobs.filtered.jsonl`, and persisted run-job filtering remain canonical for full-export payload assembly.

**Authority:**
- Preauthorized local actions: modify only `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py` when shared row projection needs correction, and declared backend tests; run direct local HTTP boundary tests.
- Stop for: new persistence schema, migration, authorization-policy change, external storage, destructive data operation, or incompatible versioned export contract.

**Steps:**
- [x] Extract existing JSONL/manifest assembly into one reusable backend helper shared by the current admin route and new run-detail export route.
- [x] Add `GET /runs/{run_id}/jobs/export.full.zip` with run-detail filters `search`, `stage`, `result_bucket`, and `pipeline_outcome` mapped to existing filtered-row behavior.
- [x] Keep `jobs.filtered.jsonl` and manifest version fields explicit; include raw source data, pipeline state, and canonical enriched fields already present in filtered rows.
- [x] Add tests for HTTP 200 success, enriched payload, filters, and manifest row count while preserving existing ordering/checksum behavior.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "enriched_filtered or full_export"`
- Expected: route returns ZIP payload with versioned manifest and JSONL; filtered rows match requested filters; unknown run returns existing API error shape.

**Exit Criteria:**
- Full export has separate route and stable versioned payload.
- Existing admin export still works through the shared builder.
- Direct boundary tests cover success and failure paths.

### Task 3: Wire separate frontend export actions

**Purpose:**
- Let users choose stable CSV or full-fidelity export from run detail without duplicating backend schemas.

**Task Function:**
- Frontend/backend contract integration.

**Template Profile:**
- `unresolved` until execution dispatch selects profile from `agents/*.toml`.

**Validator Profile:**
- `unresolved`; select independent validator after frontend proof exists.

**Specification Coverage:**
- Keep existing `Export CSV` behavior.
- Add distinct `Export full data` action.
- Forward current run filters consistently.
- Preserve keyboard access, loading state, and failure handling.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `frontend/src/features/runs/api.ts:exportRunJobsCsv`
- Inspect: `frontend/src/features/run-detail/run-detail-page.tsx:Export action`
- Modify: `frontend/src/features/runs/api.ts:full-export download helper`
- Modify: `frontend/src/features/run-detail/run-detail-page.tsx:export controls`
- Verify: `frontend/src/test/runs.test.ts:download action tests`

**Dependencies:**
- Task 2 route and filter contract complete.
- Backend route name and query parameters remain unchanged during frontend work.

**Authority:**
- Preauthorized local actions: modify only `frontend/src/features/runs/api.ts`, `frontend/src/features/run-detail/run-detail-page.tsx`, and focused frontend tests; run frontend typecheck and tests.
- Stop for: backend contract mismatch, visual redesign request, browser permission blocker that prevents required evidence, or changes outside declared frontend files.

**Steps:**
- [x] Add `exportRunJobsFull` using the same run ID and active filters as `exportRunJobsCsv`.
- [x] Replace the single export control with two accessible actions: `Export CSV` and `Export full data`.
- [x] Keep current action progress and error behavior shared between both downloads.
- [x] Add focused tests for URL, query parameters, filenames, and action invocation.

**Verification:**
- [x] `npm --prefix frontend test -- src/test/runs.test.ts` — 26 passed
- [ ] `npm --prefix frontend run typecheck` — blocked by existing `@types/node`/test-global errors and stale `RunJobItem` fixture typing
- [x] `npm --prefix frontend run build` — passed
- Expected: focused tests and production build pass; both actions use current filters and distinct download paths.

**Exit Criteria:**
- User can select CSV or full data export from run detail.
- Frontend owns no export field list; backend remains contract owner.
- Focused frontend tests and typecheck pass.

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py -k "jobs_export or enriched_filtered or full_export"`
- `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -k "run_job or export"`
- `npm --prefix frontend test -- src/test/runs.test.ts`
- `npm --prefix frontend run typecheck`
- Direct runtime check against run `77d7af8a-e2b3-4244-a815-3c5f804d21d8`: CSV preserves 13-column header; full export returns versioned manifest and JSONL with filtered enriched rows.
- `git diff --check`
- `git status --short --branch`; confirm unrelated existing changes remain untouched.

## Completion Criteria

The plan is ready for completion verification when:

1. CSV header and row mapping use one backend specification.
2. Existing CSV output remains backward compatible.
3. Full export returns raw source and canonical enriched data through a separate versioned payload.
4. Backend success, failure, filtering, ordering, row-count, and checksum proof passes.
5. Frontend exposes both export actions with focused tests and typecheck passing.
6. Final runtime check confirms both downloads for the target run.
7. No unrelated user changes are staged, reverted, or reformatted.
