---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-score-title-filter-export-optimization
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/ai_score.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - frontend/src/features/run-detail/run-detail-page.tsx
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - frontend/src/features/run-detail/run-detail-page.test.tsx
---

# Implementation Plan

## Goal

Correct the validated compatibility-score input contract, make Pipeline Results
title filtering and export surfaces use one authoritative selection, reduce full
export latency and memory/query overhead, and repair the ranking test fixture
without changing the already-correct title-filter semantics.

Review baseline: `longdang193/fitcv` `main` at
`fc309d795f75109fa73d8c2164a967591aa9c1e6`. The browser review completed for
both requested models and independently confirmed the export-parity,
full-export-resource, results-scan, and ranking-fixture findings. The score
input finding was independently confirmed by source inspection. The selected-job
export-banner observation was not independently confirmed and is intentionally
deferred.

## Implementation Outcomes

### Canonical score inputs

Every ranking job uses and fingerprints the same canonical `ranking_input`,
including jobs with no selected candidate evidence. Empty evidence remains a
valid value; it no longer causes a fallback to a different LLM input contract.
Regression coverage proves equal input/fingerprint behavior for empty and
non-empty evidence paths where the canonical fields are otherwise equal.

### Results and export parity

Pagination, counts, CSV export, and full ZIP export use the same stage, result
bucket, search, sort, inclusion-title, and exclusion-title selection. Inclusion
terms remain OR-within-inclusion, exclusion terms remain OR-within-exclusion,
exclusion takes precedence, and the two lists combine with AND semantics.
Selected job IDs and row ordering are provably identical across surfaces.

### Bounded export and stable results behavior

Full export avoids invalid page-size calls, N+1 CV lookups, and unbounded
in-memory JSONL/ZIP assembly. Results filtering performs title normalization and
matching at the earliest safe selection boundary, and polling/reconstruction is
optimized only where a measured baseline demonstrates a benefit without
weakening freshness or cancellation behavior.

### Reconciled proof

Backend boundary tests, focused frontend tests/typecheck, representative export
traces, and a before/after performance comparison cover success, empty-result,
invalid-filter, partial-CV, active-run, and large-export cases. The previously
known ranking-policy fixture failures are either fixed or recorded with an
explicit scope deviation.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only the plan-authorized source and test files, run declared local checks, and preserve all unrelated existing workspace changes
- User-approval actions: push, merge, publication, destructive cleanup, discard, or changes outside the listed targets
- Parallel ownership: `none`
- Sequential fallback: complete each task and its proof before starting the next task; do not parallelize shared selector, export, or fixture changes

## Task Breakdown

### Task 1: Restore the canonical ranking-input contract

**Purpose:**
- Ensure ranking scoring, reuse fingerprints, stored ranking inputs, labels, ordering, and top-N behavior all derive from the same canonical input for every shortlisted job.

**Task Function:**
- Trace and repair the ranking-input forwarding boundary.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded source/test change with a clear existing canonical builder; no delegation needed.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused regression tests and backend verification provide independent proof.

**Specification Coverage:**
- Validated High finding: `src/fitcv/pipeline.py:3715-3730` conditionally forwards `ranking_input` only when `candidate_evidence` is non-empty, while `src/fitcv/ai_score.py:139-144` and `src/fitcv/ai_score.py:455-460` support the canonical contract.
- Preserve `config/policy/ranking.yaml:13-20` and `src/fitcv/ranking_contract.py:424-432` as the score-policy and canonical-input owners.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline.py` ranking AI-score loop around `build_ranking_job_input()` and `build_ai_score_input_fingerprint()`.
- Modify: `src/fitcv/pipeline.py` ranking-input map, fingerprint call, and scoring call payload construction.
- Verify: `src/fitcv/ai_score.py`, `src/fitcv/ranking_contract.py`, `tests/test_pipeline_agentic_late_stage.py`, and adjacent ranking tests.

**Dependencies:**
- Review baseline at `fc309d795f75109fa73d8c2164a967591aa9c1e6`.
- Do not alter the checked-in ranking weights or fit-label thresholds.

**Authority:**
- Preauthorized local actions: inspect and edit the listed ranking source/tests and run focused Python tests.
- Stop for: any required schema/policy change, unrelated workspace cleanup, or a change to score semantics beyond input-contract unification.

**Steps:**
- [ ] Step 1: Add a failing regression that exercises a shortlisted job with empty selected evidence and asserts the stored/scored payload still contains the canonical `ranking_input`.
- [ ] Step 2: Make the pipeline always pass/store the canonical `ranking_input`; keep `candidate_evidence` empty when no evidence is selected rather than selecting a legacy payload.
- [ ] Step 3: Assert that reuse fingerprints and ranking-input records are stable across equivalent empty-evidence and non-empty-evidence cases, and that invalid/missing numeric AI scores still follow the existing policy.

**Verification:**
- [ ] `python -m pytest tests/test_pipeline_agentic_late_stage.py -q`
- Expected: the new empty-evidence regression passes and existing ranking-stage tests remain green.
- [ ] Inspect the resulting fingerprint and payload assertions for one canonical input path.
- Expected: no conditional fallback to a generic `candidate_summary` remains at the ranking boundary.

**Exit Criteria:**
- Every ranking job reaches the scorer and reuse index through the same canonical input shape, with focused regression proof.

### Task 2: Make Pipeline Results selection authoritative across all surfaces

**Purpose:**
- Eliminate the full-ZIP divergence from pagination and CSV so title filters and all other result filters have one observable meaning.

**Task Function:**
- Consolidate selector ownership and reconcile hydrated rows with selected IDs.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared backend contract with direct existing selector and export callers.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: cross-surface ID-set tests and direct boundary tests.

**Specification Coverage:**
- Validated High finding: `src/fitcv_cp/sqlite_store.py:13728-13890` owns canonical selection, while `iter_run_jobs_for_export()` currently uses the legacy enriched path and `src/fitcv_cp/app.py:12232-12259` routes full ZIP through `_build_enriched_filtered_export_zip()`.
- Preserve `src/fitcv/rule_filter.py:108-146`: OR within each keyword list, exclusion precedence, and AND between inclusion and exclusion conditions.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:_select_run_job_ids`, `_hydrate_run_job_ids`, `query_run_jobs`, `iter_run_jobs_for_export`.
- Inspect: `src/fitcv_cp/app.py:export_canonical_run_jobs`, `export_full_run_jobs`, and `_build_enriched_filtered_export_zip`.
- Modify: the selector/export boundary in `src/fitcv_cp/sqlite_store.py` and `src/fitcv_cp/app.py`; add or update backend and frontend contract tests.
- Verify: `frontend/src/features/run-detail/run-detail-page.tsx` request construction and `frontend/src/features/run-detail/run-detail-page.test.tsx` filter/export behavior.

**Dependencies:**
- Task 1 is independent in behavior but must be complete before final cross-surface verification.
- Keep the public query parameters and title matching contract backward-compatible.

**Authority:**
- Preauthorized local actions: edit the listed selector/export source and focused tests, including shared helper extraction only when it removes duplicate selection logic.
- Stop for: API shape changes, database migrations, or changing Pipeline Results filtering into run-trigger filtering.

**Steps:**
- [ ] Step 1: Add a fixture run containing passed, rejected, skipped, excluded-title, non-included-title, and searchable jobs; assert the canonical selected-ID set for each filter combination.
- [ ] Step 2: Route pagination/counts, CSV, and full ZIP through the same selected IDs and ordering; retain enriched fields as a projection/hydration concern after selection.
- [ ] Step 3: Add acceptance cases for inclusion `AI`, exclusion `duales`, both together, empty filters, stage/result/search combinations, and invalid sort/filter values.
- [ ] Step 4: Add frontend request assertions proving the filter is sent for Pipeline Results and is not added to run-trigger requests.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: CSV rows, paginated IDs, and ZIP manifest IDs match for identical filters; invalid values return the existing validation response.
- [ ] `cd frontend; npm test -- --run src/features/run-detail/run-detail-page.test.tsx`
- Expected: UI filter state and export requests preserve inclusion/exclusion semantics without affecting run creation.

**Exit Criteria:**
- One selector determines every Pipeline Results surface, and cross-surface tests prove identical selected IDs and ordering.

### Task 3: Bound full-export queries, CV access, and memory

**Purpose:**
- Reduce export latency and operational overhead while preserving complete enriched output and clear failure behavior.

**Task Function:**
- Replace invalid/unbounded export access with bounded batch projection and streaming or spooled archive assembly.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded resource correction using existing batch helpers.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: query-count, batch-size, memory, and failure-path tests.

**Specification Coverage:**
- Validated Medium finding: `src/fitcv_cp/app.py:5017-5053` calls `query_run_jobs(page_size=10_000)` even though `src/fitcv_cp/sqlite_store.py:14044-14057` accepts only `10`, `20`, or `50`, then suppresses the failure.
- Validated Medium finding: `src/fitcv_cp/app.py:5271-5314` performs per-job CV access while `src/fitcv_cp/sqlite_store.py:14275-14335` already contains batch projection primitives; full ZIP assembly currently buffers JSONL and archive content in memory around `src/fitcv_cp/app.py:16274-16383`.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:_build_enriched_tab_context`, `_build_enriched_filtered_export_zip`, and full-export route.
- Inspect: `src/fitcv_cp/sqlite_store.py:query_run_jobs`, `iter_run_jobs_for_export`, `_batch_cv_projections`, and `list_cvs_for_run`.
- Modify: bounded selection/hydration and export assembly in the listed files; add tests in `tests/test_fitcv_cp/test_app.py` and `tests/test_fitcv_cp/test_sqlite_store.py`.

**Dependencies:**
- Task 2 must define the selected-ID contract before export batching is changed.
- Reuse existing SQLite batch helpers and standard-library `zipfile`; do not add a dependency.

**Authority:**
- Preauthorized local actions: edit export and store code/tests, add bounded instrumentation in tests, and run local performance probes.
- Stop for: changing archive format or retention policy, adding a service/queue, or suppressing unexpected exceptions.

**Steps:**
- [ ] Step 1: Remove the invalid `10_000` page-size dependency; consume canonical selected IDs or a bounded iterator that cannot exceed the supported page-size contract.
- [ ] Step 2: Batch CV metadata by job ID using the existing projection path, preserving missing-CV behavior and output ordering.
- [ ] Step 3: Stream or spool JSONL and ZIP entries in bounded batches; ensure temporary resources are closed on success, empty exports, cancellation, and exception paths.
- [ ] Step 4: Narrow exception handling so expected empty/missing metadata cases remain compatible while unexpected database/export failures are observable and testable.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: full export succeeds for empty, partial-CV, and large fixtures without invalid page-size calls; archive contents and manifests remain complete.
- [ ] Add a test-level query counter and bounded-batch assertion.
- Expected: CV access is batch-based rather than one SQLite query per job, and peak in-memory payload is bounded by the chosen batch size.

**Exit Criteria:**
- Full ZIP export has no invalid page-size call, no per-job CV query loop, and no unbounded full-run JSONL/ZIP buffer, with preserved output and failure semantics.

### Task 4: Optimize Pipeline Results scanning and refresh only after measurement

**Purpose:**
- Reduce repeated run reconstruction and late title filtering without trading away freshness, cancellation, or result correctness.

**Task Function:**
- Measure, then optimize the results-selection and active-run refresh path.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: performance work requires local measurement before selecting an implementation.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: before/after representative trace and correctness regression.

**Specification Coverage:**
- Validated Medium finding: `src/fitcv_cp/sqlite_store.py:13745-13778`, `13817-13874`, `13906-13927`, and `14060-14076` reconstruct and scan the run before page slicing; `frontend/src/features/run-detail/run-detail-page.tsx:583-628` polls active runs every 2.5 seconds.
- Title matching must occur at the earliest safe boundary after normalized terms are computed once; no speculative cache is required without measured benefit.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-performance-optimization`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:_select_run_job_ids`, `_hydrate_run_job_ids`, `_filtered_run_job_rows`, `query_run_jobs`.
- Inspect: `frontend/src/features/run-detail/run-detail-page.tsx` polling/effect logic around lines `583-628`.
- Modify only after baseline: title normalization/early selection, duplicate hydration removal, and revision-aware refresh or caching if the trace proves it is safe.
- Verify: backend selection tests and `frontend/src/features/run-detail/run-detail-page.test.tsx` active-run refresh tests.

**Dependencies:**
- Task 2’s canonical selector must be stable.
- Record workload, environment, baseline latency, query count, memory, and freshness behavior before editing.

**Authority:**
- Preauthorized local actions: run bounded local benchmarks, edit the listed results/polling surfaces, and add focused regression tests.
- Stop for: changing polling cadence or cache invalidation without measured evidence, stale-result risk, or a required API contract change.

**Steps:**
- [ ] Step 1: Capture a representative small, medium, and large run trace with and without title/search/result filters, recording selection time, hydration time, query count, memory, and response freshness.
- [ ] Step 2: Normalize filter terms once and apply title predicates before expensive decoding/projection where the existing data model permits.
- [ ] Step 3: Remove duplicate full-run selection/hydration work; only add revision-aware refresh/caching if it keeps active-run updates and cancellation correct.
- [ ] Step 4: Re-run the same workloads and retain the comparison with the tests.

**Verification:**
- [ ] Run the repository’s focused backend/frontend tests plus the bounded benchmark command established in Step 1.
- Expected: filtered and unfiltered results are unchanged; active runs still refresh within the documented behavior; measured query/latency/memory metrics improve or the plan records why no optimization was safe.

**Exit Criteria:**
- A measured, correctness-preserving optimization is implemented, or the task records a verified no-change decision with baseline evidence rather than speculative complexity.

### Task 5: Repair the ranking-policy test fixture

**Purpose:**
- Remove the known fixture defect that masks ranking regressions and causes the five full-suite failures involving fit-label thresholds.

**Task Function:**
- Centralize a valid ranking-policy test configuration with explicit overrides.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: small test-only correction with a direct source of truth.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused and full-suite test output.

**Specification Coverage:**
- Validated Low finding: `tests/test_pipeline_agentic_late_stage.py:688-697` `_minimal_config` omits the required `fit_label_thresholds`, while `src/fitcv/ranking_contract.py:69-95` requires `strong` and `stretch`.
- Preserve production policy values from `config/policy/ranking.yaml:39-44`; test overrides must be explicit and valid.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `tests/test_pipeline_agentic_late_stage.py:_minimal_config`, related fixtures, and `src/fitcv/ranking_contract.py:_fit_label_from_thresholds`.
- Modify: the shared test fixture and only directly affected assertions.
- Verify: all tests named by the prior five threshold failures and the full Python suite.

**Dependencies:**
- Task 1’s ranking-input regression may reuse this fixture; keep fixture changes compatible with both.

**Authority:**
- Preauthorized local actions: edit the named test fixture/assertions and run focused/full Python tests.
- Stop for: changing production ranking thresholds or weakening threshold validation.

**Steps:**
- [ ] Step 1: Derive `_minimal_config` from one validated ranking-policy fixture and override only test-specific values.
- [ ] Step 2: Add an explicit threshold assertion so future fixture drift fails at setup rather than deep in unrelated tests.
- [ ] Step 3: Re-run the previously failing threshold cases and confirm no unrelated failures are hidden.

**Verification:**
- [ ] `python -m pytest tests/test_pipeline_agentic_late_stage.py -q`
- Expected: the five known threshold-related failures are resolved without changing production policy behavior.
- [ ] `python -m pytest -q`
- Expected: the full Python suite passes, or any unrelated pre-existing failure is recorded with exact output and scope.

**Exit Criteria:**
- Ranking tests construct a valid policy through one explicit fixture owner and the known threshold failures are resolved or accurately documented.

### Task 6: Reconcile cross-stack proof and final acceptance

**Purpose:**
- Confirm the implementation is complete at backend boundaries, frontend consumers, export artifacts, and representative runtime behavior.

**Task Function:**
- Execute final verification and reconcile source, tests, docs, and any deviations.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance requires one lead controller to reconcile all evidence.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: fresh commands and source/test reconciliation are sufficient for this plan.

**Specification Coverage:**
- Verify the score-input contract, Pipeline Results filter semantics, export parity, resource bounds, active-run freshness, and ranking fixture correctness.
- Explicitly keep the unconfirmed selected-job export-banner observation deferred unless fresh evidence validates it.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Verify all targets in this plan plus the generated/maintained documentation affected by the final implementation.
- Inspect `git diff`, test output, benchmark output, and API/UI request traces; do not include unrelated workspace files.

**Dependencies:**
- Tasks 1–5 complete with task-local proof.

**Authority:**
- Preauthorized local actions: run final local verification, inspect diffs, and update this plan’s evidence/status if execution is authorized later.
- Stop for: any required publication, branch cleanup, destructive workspace operation, or unresolved scope deviation.

**Steps:**
- [ ] Step 1: Run focused backend tests, focused frontend tests/typecheck, export parity tests, and the representative performance trace.
- [ ] Step 2: Run the full Python suite and frontend build/typecheck/test commands.
- [ ] Step 3: Confirm no unrelated modified/untracked files were changed and record exact failures, deviations, or deferred checks.

**Verification:**
- [ ] `python -m pytest -q`
- [ ] `cd frontend; npm test -- --run; npm run typecheck; npm run build`
- Expected: required checks pass; any environment-blocked check has its exact blocker and owner recorded rather than being marked green.

**Exit Criteria:**
- Fresh evidence supports every required outcome, no validated finding is omitted, no unverified observation is promoted, and the plan is ready for execution or explicit approval.

## Verification

- `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- `cd frontend; npm test -- --run; npm run typecheck; npm run build`
- `python -m pytest -q`
- Re-run the recorded representative export/results performance workload and compare latency, query count, peak memory, and freshness against its baseline.
- Review `git diff --check` and confirm only plan-authorized files changed during execution.

## Completion Criteria

The plan is ready for completion verification when:

1. canonical ranking input is used for every score and reuse decision
2. pagination, CSV, and full ZIP expose identical Pipeline Results selection for identical filters
3. full export uses bounded, batch CV access and bounded archive assembly with observable failures
4. results latency/polling changes are measured and correctness-preserving, or a documented no-change decision is recorded
5. the ranking fixture supplies valid fit-label thresholds and the known failures are resolved or explicitly scoped
6. focused backend/frontend proof and final suite/build evidence are recorded
7. unrelated existing workspace changes remain untouched
8. deferred observations remain clearly marked as unverified

The plan may be marked `completed` only after `skill-verification-before-completion` runs fresh final verification, confirms these criteria against repository evidence, and returns `verified`.
