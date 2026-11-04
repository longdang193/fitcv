---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: proposed
name: fitcv-synonyms-approve-all-pipeline-results-title-filter
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv/rule_filter.py
  - frontend/src/features/synonyms/api.ts
  - frontend/src/features/synonyms/suggestion-queue.tsx
  - frontend/src/features/synonyms/synonyms.test.ts
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - frontend/src/features/runs/api.ts
  - frontend/src/features/runs/new-run-dialog.tsx
  - frontend/src/test/runs.test.ts
  - frontend/src/lib/filter-values.ts
  - frontend/src/features/scans/new-scan-dialog.tsx
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_rule_filter.py
  - docs/pipeline.md
---

# FitCV Synonym Approval and Pipeline-Results Title Filtering

## Goal

Add a safe, auditable `Approve All` action for pending Taxonomy & Synonyms
suggestions and add inclusion/exclusion job-title filtering to the existing
Pipeline Results view only. Preserve the run-trigger contract: title filters
entered in Pipeline Results must never be sent to `/runs`, change source
acquisition, or alter the jobs snapshot used by a run.

The plan also records the Synonyms table alignment decision. The current
implementation intentionally aligns the Actions header and action controls to
the right, while the shared `.data-table` default aligns ordinary columns to
the left. The supplied screenshot makes ordinary headers look visually
centered because of column widths, but the source CSS does not center them.
This is not a confirmed design-system defect; do not change alignment unless
fresh rendered evidence shows the header and its action cells disagree.

## Implementation Outcomes

### Approve all pending synonym pairs

Provide an accessible `Approve All` control that approves every pending
suggestion matching the active Type and Search filters, across all pages rather
than only the current page or selected rows. With default filters, this means
all pending suggestions. The operation is idempotent, revision-safe, bounded by
the server-side query, and reports processed, approved, blocked, and issue
counts without requiring the browser to fetch every ID.

### Pipeline Results title filters

Add optional include and exclude title filters to Pipeline Results. Terms are
normalized through the existing `fitcv.rule_filter.evaluate_title_filter`
contract: OR within each list, exclusion wins, and inclusion plus exclusion is
AND logic. Matching is case-insensitive whole-word/phrase matching, so `AI`
does not match `Retail` or `Trainee`. The same filters apply to pagination,
summary counts, CSV export, and full export.

### Alignment and run-trigger contract proof

Keep the current Actions-column right alignment unless browser-computed styles
prove a mismatch. Add regression proof for the alignment decision and for the
absence of title-filter fields in New Run submission. Scan title filters remain
Scan-owned; Pipeline Results filters are transient read-only query state.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-test-driven-development`, `skill-frontend-component-engineering`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only the named plan-approved files, run focused tests/typechecks, and perform local browser/accessibility inspection
- User-approval actions: push, merge, publication, destructive cleanup, or changes outside the named surfaces
- Parallel ownership: `none`
- Sequential fallback: implement and prove the backend contract before wiring the frontend; keep the run-trigger contract unchanged throughout

## Assumptions and Invariants

- `Approve All` means all `pending` suggestions matching the current Type and
  Search filters, not approved/declined rows and not only the current page.
- The backend owns the authoritative selection and count; the browser never
  expands the action into a client-side list of IDs.
- The approve-all request uses the existing required `Idempotency-Key` flow and
  carries the expected draft and active-bundle revisions for the selected
  cross-type snapshot. The revision values are part of the idempotency
  fingerprint, so a retry cannot replay a response for a different snapshot.
- A policy conflict commits deterministic blocked/skipped results and counts,
  preserving existing single/batch approval semantics. Revision conflicts,
  audit failures, and persistence failures roll back the complete operation.
  Existing single/batch approve behavior remains unchanged.
- If a duplicate idempotency key is currently reserved without a stored
  response, return `409 idempotency_in_progress`; never re-enter the mutation.
- Pipeline Results title filters are query-time display/export filters. They are
  not run settings, are not persisted into the run effective-settings snapshot,
  and do not affect source acquisition or pipeline stages.
- The existing title predicate in `src/fitcv/rule_filter.py` is the SSOT. Do not
  duplicate whole-word matching or AND/OR semantics in the results store.

## Task Breakdown

### Task 1: Add an atomic, idempotent Approve All backend contract

**Purpose:**
- Add one server-owned operation that selects and approves all matching pending synonym suggestions across types and pages.

**Task Function:**
- Extend the existing synonym action path with a transaction-safe, multi-type bulk operation while preserving single/batch action behavior.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded backend contract change with existing store, revision, and idempotency patterns to reuse.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: direct SQLite and API boundary tests provide independent contract proof.

**Specification Coverage:**
- Approve all pending synonym pairs at once.
- Respect active Type/Search filters, ignore pagination, and report auditable counts.
- Preserve idempotency, transaction rollback, and existing approval revision semantics.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:SynonymSuggestionActionRequest`, `_apply_synonym_action`, and synonym action routes
- Inspect: `src/fitcv_cp/store.py:apply_synonym_suggestion_action`, idempotency wrapper
- Inspect: `src/fitcv_cp/sqlite_store.py:query_synonym_suggestions`, `apply_synonym_suggestion_action`, `_record_synonym_processing_run`
- Modify: `src/fitcv_cp/app.py` with an approve-all request model and `POST /synonym-suggestions/actions/approve-all`
- Modify: `src/fitcv_cp/store.py` with the store protocol/delegating wrapper for the new operation
- Modify: `src/fitcv_cp/sqlite_store.py` with the authoritative pending selection and shared per-type approval transaction helper
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Reuse the existing synonym policy bundle activation, revision checks, processing-run audit, and idempotency reservation rather than creating a second policy mechanism.
- The operation must support more than the existing 1,000-ID single action limit because the server selects pending rows directly.

**Authority:**
- Preauthorized local actions: update the named backend/store symbols and focused tests; run the backend commands listed below.
- Stop for: a required schema migration, a change to existing single/batch approve semantics, partial-commit behavior, or a need to expose private policy data in the response.

**Steps:**
- [ ] Step 1: Add a request shape carrying optional normalized `synonym_type` and `search` filters plus the expected draft and active-bundle revision values (or one server-issued snapshot token that resolves to them); reserve/replay the idempotency action using filters and revision preconditions in the fingerprint.
- [ ] Step 2: Select all pending rows server-side using the same Type/Search semantics as the queue, group by synonym type, and reuse the existing policy activation/validation logic rather than duplicating it.
- [ ] Step 3: Execute the multi-type operation in one write transaction; commit deterministic blocked/skipped counts for policy-cycle/alias conflicts, but roll back all status/policy changes for revision conflict, audit failure, or persistence error and return the existing machine-readable error shape.
- [ ] Step 4: Return processing-run metadata and counts for selected, approved, skipped/blocked, and issue rows; replay completed idempotent requests and return `409 idempotency_in_progress` for an in-flight duplicate without re-entering the mutation.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: matching pending rows across multiple types are approved in one operation; unrelated rows remain pending; current-page size and the 1,000-ID limit do not truncate selection; conflict and injected audit failures leave no partial state; the processing log is written once.
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -q -k "synonym or openapi"`
- Expected: the route requires `Idempotency-Key`, validates filters, returns the canonical envelope, forwards the store operation, and replays the same response for the same key/fingerprint.

**Exit Criteria:**
- The backend can approve all matching pending suggestions without client-side ID enumeration, with atomic rollback and persisted audit evidence.

### Task 2: Wire Approve All into the Synonyms queue and lock the alignment decision

**Purpose:**
- Make the new operation discoverable and safe in the React queue, and prove that the Actions-column alignment is intentional rather than an inconsistent header rule.

**Task Function:**
- Add queue-level bulk-action state, confirmation, feedback, and regression coverage while preserving selected-row actions.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: focused stateful UI change using existing Button, Notice, loading, error, and table patterns.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: component tests plus one rendered browser/computed-style check.

**Specification Coverage:**
- Add `Approve All` for all pending rows matching active queue filters, not just selected rows/current page.
- Keep `Approve Selected`, Decline, Reset, detail, pagination, and refresh behavior unchanged.
- Confirm current alignment: Actions header and action cell are right-aligned; ordinary headers/cells follow shared left alignment.

**Required Skills:**
- `skill-frontend-component-engineering`
- `skill-test-driven-development`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `frontend/src/features/synonyms/suggestion-queue.tsx:SuggestionQueue`, current batch toolbar, table header, and action cell
- Inspect: `frontend/src/styles/main.css:.data-table` and `frontend/src/components/table.tsx:DataTable`
- Modify: `frontend/src/features/synonyms/api.ts` with `approveAllSynonymSuggestions`
- Modify: `frontend/src/features/synonyms/suggestion-queue.tsx` with the visible pending count, confirmation, loading lock, success/error notice, and reload behavior
- Verify: `frontend/src/features/synonyms/synonyms.test.ts` and a browser accessibility/computed-style check on the queue table

**Dependencies:**
- Task 1 API and store contract complete.
- Keep the current explicit `textAlign: 'right'` on both the Actions `<th>` and action `<td>` unless the rendered check proves it is not applied.

**Authority:**
- Preauthorized local actions: update the named Synonyms API/component/test files and run focused frontend checks; perform local browser inspection.
- Stop for: a requirement to center ordinary table headers, a visual change that affects shared tables, or a new design token/component not justified by the existing design system.

**Steps:**
- [ ] Step 1: Add the API client call with filter payload, idempotency key, canonical envelope parsing, and no client-side expansion of pending IDs.
- [ ] Step 2: Show `Approve All` when the queue is in the pending view and the matching pending count is nonzero; confirm the exact count and active filters before submission.
- [ ] Step 3: Disable duplicate actions while active, surface the server summary/error, refresh counts/items, clear selection, and call `onQueueChanged` once after success.
- [ ] Step 4: Add tests for filtered/all-page approval, confirmation text, loading/error/success state, and unchanged selected-row actions. Assert the table's computed styles: ordinary headers use the shared left default; Actions header and action cell both use right alignment.

**Verification:**
- [ ] `npm --prefix frontend test -- --run src/features/synonyms/synonyms.test.ts`
- Expected: API request and queue behavior pass, including no request for an empty queue and no accidental current-page-only implementation.
- [ ] `npm --prefix frontend run typecheck`
- Expected: TypeScript passes with the new request/result types.
- [ ] Browser check on `#/synonyms`: keyboard focus reaches `Approve All`, confirmation is announced, the table remains usable at narrow width, and computed alignment matches the documented decision.

**Exit Criteria:**
- A user can approve the intended pending scope once, see the result, and understand alignment/action feedback without changing shared table layout rules.

### Task 3: Add Pipeline Results-only title include/exclude filters

**Purpose:**
- Let users filter an existing run's Pipeline Results by job title without changing what the run processed or how a new run is triggered.

**Task Function:**
- Extend the existing run-jobs query/export path and results toolbar with transient title-filter state using the canonical title predicate.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-layer change with a narrow API contract and existing pagination/export architecture.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: backend predicate tests, route tests, API serialization tests, and run-detail component tests cover the contract boundaries.

**Specification Coverage:**
- Include terms match any supplied inclusion term; exclude terms reject any matching title; both lists use AND logic between inclusion and exclusion.
- Use case-insensitive whole-word/phrase matching and do not match `AI` inside `Retail` or `Trainee`.
- Apply filters to Pipeline Results pagination, counts, CSV export, and full export.
- Do not add title-filter controls or fields to New Run, `/runs`, `TriggerRequest`, `triggerRun`, scan acquisition, or run snapshots.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-backend-verification`
- `skill-test-driven-development`
- `skill-frontend-component-engineering`

**Files And Symbols:**
- Inspect: `src/fitcv/rule_filter.py:evaluate_title_filter`, `normalize_title_keywords`, `_title_keyword_pattern`
- Inspect: `src/fitcv_cp/sqlite_store.py:_select_run_job_ids`, `_filtered_run_job_rows`, `query_run_jobs`, `iter_run_jobs_for_export`
- Inspect: `src/fitcv_cp/app.py:get_run_jobs`, `export_canonical_run_jobs`, `export_full_run_jobs`
- Inspect: `frontend/src/features/run-detail/run-detail-page.tsx:buildRunJobsQueryKey`, `loadJobs`, Pipeline Results toolbar, export handlers
- Inspect: `frontend/src/features/runs/api.ts:fetchRunJobs`, `exportRunJobsCsv`, `exportRunJobsFull`, `triggerRun`
- Modify: `src/fitcv_cp/sqlite_store.py` to accept title include/exclude lists and call `evaluate_title_filter` before result-bucket totals/filtering
- Modify: `src/fitcv_cp/app.py` to expose repeated `job_title_include` and `job_title_exclude` query parameters on jobs and export routes and include active filters in response/export metadata
- Modify: `frontend/src/features/runs/api.ts` and `frontend/src/features/run-detail/run-detail-page.tsx` to serialize transient filter lists, include them in query identity, reload page 1 on changes, and pass them to exports
- Add/modify: a Pipeline Results-local helper (for example `frontend/src/features/run-detail/title-filters.ts`) for comma/newline-separated terms; do not modify `frontend/src/features/scans/new-scan-dialog.tsx` or its existing newline-only acquisition parser
- Verify: `tests/test_rule_filter.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`, `frontend/src/test/runs.test.ts`, `frontend/src/features/run-detail/run-detail-page.test.tsx`, and a New Run submission regression test

**Dependencies:**
- Reuse `evaluate_title_filter` as the backend SSOT; do not reimplement substring/word-boundary semantics in SQLite or TypeScript.
- Preserve the existing generic `search` filter and stage/result-bucket semantics.
- Keep Scan acquisition parsing and payload semantics unchanged; Pipeline Results owns a separate display/export-time parser and filter state.

**Authority:**
- Preauthorized local actions: update the named query/export/UI/parser files and focused tests; run backend/frontend verification and local browser flow.
- Stop for: any request to persist result filters into a run, pass them through `/runs`, change scan acquisition semantics, or duplicate the canonical title predicate.

**Steps:**
- [ ] Step 1: Add repeated-list query parameters and store arguments for `job_title_include`/`job_title_exclude`; normalize empty/duplicate terms and evaluate the title against the canonical predicate before totals and result-bucket filtering.
- [ ] Step 2: Extend both export routes and the enriched full-export builder so active title filters produce the same row set and are recorded in export metadata.
- [ ] Step 3: Add two accessible Pipeline Results controls (include and exclude, one term per line or comma-separated), parse them through the Pipeline Results-local helper, and include normalized values in `buildRunJobsQueryKey` and all fetch/export calls.
- [ ] Step 4: Keep New Run unchanged; add a focused assertion that its submitted FormData contains only existing run-trigger fields and never `job_title_include`/`job_title_exclude`.
- [ ] Step 5: Add acceptance cases: `Working Student – AI Analytics` kept; `Duales Studium – AI Engineering` excluded; `Retail Analytics Intern` excluded when `AI` is included; `AI/ML Engineer` kept; empty include admits all non-excluded titles.

**Verification:**
- [ ] `python -m pytest tests/test_rule_filter.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q`
- Expected: canonical matching, AND behavior, pagination/count/export parity, invalid query handling, and unchanged `/runs` trigger contract pass.
- [ ] `npm --prefix frontend test -- --run src/test/runs.test.ts src/features/run-detail/run-detail-page.test.tsx`
- Expected: query serialization, query-key identity, export serialization, UI reset/page behavior, and trigger FormData regression pass.
- [ ] `npm --prefix frontend run typecheck`
- Expected: frontend/backend parameter types remain aligned.
- [ ] Browser flow on an existing run's Pipeline Results: set include `AI` and exclude `duales`, verify only expected rows/counts remain, change stage/page, export CSV/full data, and confirm New Run has no title-filter controls or payload fields.

**Exit Criteria:**
- Pipeline Results and its exports use the same title-filter contract, while new-run acquisition and run snapshots remain byte-for-byte contract-compatible for the existing fields.

## Verification

- `python -m pytest tests/test_rule_filter.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q`
- `npm --prefix frontend test -- --run src/features/synonyms/synonyms.test.ts src/test/runs.test.ts src/features/run-detail/run-detail-page.test.tsx`
- `npm --prefix frontend run typecheck`
- Browser/accessibility check of Synonyms and Pipeline Results, including computed alignment, keyboard access, narrow viewport, loading/error/empty states, and export parity.
- Inspect the final diff to confirm no title-filter field was added to `frontend/src/features/runs/new-run-dialog.tsx`, `frontend/src/features/runs/api.ts:triggerRun`, `src/fitcv_cp/app.py:TriggerRequest`, or run effective-settings persistence.

## Completion Criteria

The plan is ready for completion verification when:

1. `Approve All` approves the server-selected pending scope atomically and idempotently, with audit/count evidence and focused regression tests.
2. Synonyms alignment is either unchanged with computed-style proof or changed only with a documented design-system requirement and focused visual regression proof.
3. Pipeline Results include/exclude title filters pass the canonical acceptance matrix and stay consistent across pagination, summary counts, and both exports.
4. New Run submission remains free of Pipeline Results title-filter fields and existing Scan title filtering remains intact.
5. All task-local checks and final verification commands pass, with unrelated worktree changes preserved and no generated/private artifacts added.

