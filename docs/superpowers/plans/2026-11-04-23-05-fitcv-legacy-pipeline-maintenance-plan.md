---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-legacy-pipeline-maintenance
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv/enrich.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_ai_score.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_rule_filter.py
---

# FitCV Legacy Pipeline Maintenance Plan

## Goal

Create a separate, executable maintenance change for the legacy pipeline
failures observed after the retrieval/ranking work, while preserving the
completed retrieval/ranking contracts and refusing to classify an unproven
ranking regression as legacy maintenance.

The plan starts from `main` at
`6f170c1c6058c5bd184706934ff8918abb96fe57`, which contains this tracked plan
and has the same source/test content as its parent maintenance base
`c84c1ee79cafc7e62bf0cad8fbca0ec39a53f705`. The completed retrieval/ranking
plan remains unchanged. This plan first revalidates the failure inventory at
the execution revision and the earlier comparison revision
`14e2c55195e111c1b4ae5e72b6340cfe001948e7`, then repairs only failures proved
to belong to the maintenance scope.

## Validated Review Basis

- Both read-only model reviews agreed that the existing retrieval/ranking
  plan's `## Verification` → `### Execution Evidence` section does not name
  the seven deferred test node IDs or provide a standalone maintenance task.
- The current reported inventory contains ten exact tests: seven in
  `tests/test_pipeline.py`, one canonical SQLite projection test, one empty
  ranking-evidence test, and one screening persistence test.
- `tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`
  is adjacent to the ranking-input changes and must be baseline-classified
  before it can enter this plan.
- The canonical SQLite collection failure and the screening persistence
  failure are separate public-surface concerns and must not be repaired as one
  broad store rewrite.
- The existing plan records focused and deselected-suite evidence, not a
  successful unrestricted `python -m pytest -q` run. This plan requires fresh
  full-suite evidence with explicit pass, skip, xfail, xpass, and deselection
  counts; known pre-existing out-of-scope failures remain listed rather than
  being hidden behind a green-only acceptance claim.
- The empty-evidence test currently indexes `scoring_ranking_inputs` by the raw
  URL even though the production map uses `primary_job_identity_key()` and an
  identity-prefixed key. That lookup must be classified as a fixture contract
  issue before it is used as proof of a production regression.
- The actual scoring path still has separate empty-list fallbacks in
  `run_ai_scoring()` and `build_ranking_request()`. The ranking-stage mock test
  alone cannot prove that the submitted request and its fingerprint preserve an
  explicitly empty selected-evidence pool.

## Implementation Outcomes

### Complete failure classification

All ten exact test node IDs have a reproducible current-revision result and a
separate comparison-revision result. Each is classified as `legacy_confirmed`,
`retrieval_ranking_regression`, `current_unverified`, or `fixture_contract`
with observed output and a named owner. No current failure is described as a
historical baseline failure without its own evidence.

### Repaired legacy pipeline state and persistence

The proven legacy defects are repaired at their canonical owners: CV-generation
resume/export state, pre-enrichment filtering and screening persistence, and
canonical job enrichment projection across run and bookmark collections.
Production orchestration and public SQLite query surfaces retain their
existing status, identity, ordering, and idempotency contracts.

### Preserved retrieval/ranking behavior

Deterministic local retrieval remains lexical with its existing diagnostics;
validated semantic backends retain cosine retrieval; ranking remains bounded to
eight skills and two evidence items; explicit selected evidence remains
authoritative; score arithmetic, thresholds, shortlist ordering, and
Loose/Full/Strict semantics remain unchanged. The empty-evidence test is fixed
here only if baseline evidence proves it is legacy maintenance; a
current-only failure is returned to retrieval/ranking ownership instead.

### Fresh acceptance evidence

The ten targeted tests, their containing test files, the retrieval/ranking
guard suite, compilation, diff checks, and an unrestricted full pytest suite
provide fresh evidence. The evidence records collected, passed, failed,
skipped, xfailed, xpassed, and deselected counts and separates in-scope
failures from known pre-existing out-of-scope failures. No `xfail`, deselection,
broad exception swallowing, or weakened assertion is accepted as a repair.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-using-git-worktrees`, `skill-verification-before-completion`
- Isolation: current implementation workspace plus one temporary detached worktree for comparison-revision tests
- Commit policy: `no commits during execution`; publication or merge requires separate authorization after fresh verification
- Preauthorized local actions: before creating the comparison worktree, bind `EVIDENCE_DIR` to an absolute path in the implementation workspace at `<implementation-workspace>/.tmp/legacy-pipeline-maintenance/`; inspect and edit the declared source/test files, run declared local pytest/compile/diff commands, create and remove the task-owned detached comparison worktree, and write task-owned temporary evidence under `EVIDENCE_DIR`
- User-approval actions: push, merge, destructive recovery outside the task-owned temporary worktree, discard of unrelated changes, or scope expansion into retrieval/ranking behavior
- Parallel ownership: none; `pipeline.py` and `sqlite_store.py` are shared owners across maintenance clusters
- Sequential fallback: run Tasks 1 through 6 in order; do not begin a repair task until Task 1 records the relevant classification and a disposition/next action for every non-`legacy_confirmed` node

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-legacy-pipeline-maintenance`
- Base commit: `6f170c1c6058c5bd184706934ff8918abb96fe57`
- Expected workspace: feature branch based on the base commit; unrelated user changes remain untouched
- Next action: branch finishing and publication
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current + temporary detached baseline worktree | lead controller | none | current/baseline result for all ten node IDs | `$EVIDENCE_DIR/baseline-classification.md` |
| Task 2 | `completed` | current | lead controller | Task 1; each repair candidate classified `legacy_confirmed` | focused CV state/export tests and artifact assertions | task-local pytest output |
| Task 3 | `completed` | current | lead controller | Task 1; each repair candidate classified `legacy_confirmed` | direct rejection and SQLite round-trip proof | task-local pytest output |
| Task 4 | `completed` | current | lead controller | Task 1; canonical projection candidate classified `legacy_confirmed` | run and bookmark collection parity plus duplicate-occurrence isolation | task-local pytest output |
| Task 5 | `completed` | current | lead controller | Task 1; empty-evidence classification | explicit fixture disposition and request-level compatibility proof | `$EVIDENCE_DIR/ranking-empty-evidence-disposition.md` |
| Task 6 | `completed` | current | lead controller | Tasks 2–5 complete and every non-legacy node has an explicit disposition | targeted, guard-suite, and unrestricted full-suite proof | `$EVIDENCE_DIR/final-verification.md` |

## Execution Update

- Tasks 1–5 are complete. The paired classification, focused repairs, fixture
  disposition, and request-level empty-evidence regression are recorded in the
  task-owned evidence directory.
- A post-verification regression exposed an unsafe fallback in Task 4:
  run-scoped rows with a missing `run:` payload could hydrate from a shared
  `fp:` payload. `_identity_payload_for_job()` now permits only an unambiguous
  legacy URL fallback after a run-key miss; the duplicate-occurrence regression
  passes.
- Task 6 is complete. The first unrestricted run exposed three environment-only
  failures because `frontend/dist` had not been built. Running the canonical
  `frontend` build from `.github/workflows/repo-hooks.yml` resolved all three;
  the final unrestricted suite is `3520 passed, 10 skipped`. See
  `$EVIDENCE_DIR/final-verification.md`.

## Task Breakdown

### Task 1: Reproduce and classify the complete failure inventory

**Purpose:**
- Establish the current ten-test inventory and compare every test with the earlier revision before any repair is assigned.

**Task Function:**
- Regression classification and failure-boundary mapping.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: pending until the lead resolves the profile from the required debugging depth and repository evidence.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: the lead controller owns the paired revision comparison.

**Specification Coverage:**
- Complete failure inventory, explicit baseline classification, and no overclaim of the historical seven-failure result.

**Required Skills:**
- `skill-systematic-debugging`, `skill-using-git-worktrees`

**Files And Symbols:**
- Inspect: `tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_returns_export_results_sorted_and_statused`
- Inspect: `tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment`
- Inspect: `tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields`
- Inspect: `tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`
- Inspect: `tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows`
- Verify: `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stage_runner.py`, `src/fitcv/rule_filter.py`, `src/fitcv_cp/sqlite_store.py`, and `src/fitcv/ai_score.py`

**Dependencies:**
- Base commit `6f170c1c6058c5bd184706934ff8918abb96fe57` is checked out and clean. `EVIDENCE_DIR` is an absolute implementation-workspace path created before any detached worktree.

**Authority:**
- Preauthorized local actions: create the named detached comparison worktree, run the exact ten-node pytest command at both revisions, inspect source/test history, correct a test-only fixture/identity mismatch when directly proven, and write the task-owned classification report.
- Stop for: any uncommitted unrelated change in the implementation workspace, a missing comparison commit, a test that cannot be reproduced at either revision, or evidence that requires changing retrieval/ranking scope.

**Steps:**
- [x] Step 1: Run the exact ten-node command at the execution revision and save the complete output to `$EVIDENCE_DIR/current-ten-tests.txt`.
- [x] Step 2: Create a temporary detached worktree at `14e2c55195e111c1b4ae5e72b6340cfe001948e7`, run the identical ten-node command there, and save output to `$EVIDENCE_DIR/baseline-ten-tests.txt` outside that worktree.
- [x] Step 3: For each node, record current result, baseline result, observed error, touched symbols between revisions, named owner, next action, and one disposition: `legacy_confirmed`, `retrieval_ranking_regression`, `current_unverified`, or `fixture_contract`. A `fixture_contract` result may authorize only the smallest test/fixture correction at the canonical identity or contract boundary, followed by a rerun at both revisions; it cannot authorize a production workaround.
- [x] Step 4: Write `$EVIDENCE_DIR/baseline-classification.md`, verify both captured output files exist, then remove only the task-owned detached worktree and leave unrelated workspace files untouched.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order tests/test_pipeline.py::test_run_pipeline_returns_export_results_sorted_and_statused tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows --disable-warnings --maxfail=0`
- Expected: the report contains all ten node IDs with separate current and baseline outcomes; no failure is labeled historical without a baseline result.

**Exit Criteria:**
- The classification report exists, names an owner and next action for every node, explicitly routes every non-`legacy_confirmed` result, and gates the empty-evidence ranking test on both identity correctness and actual request behavior.

### Task 2: Repair CV-generation resume and export state

**Purpose:**
- Restore the proven legacy CV-generation resume, debug-artifact, deterministic-order, and export-status contracts without changing scoring or shortlist behavior.

**Task Function:**
- State-machine repair at the production pipeline orchestration boundary.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Task 1 confirms the six CV state/export tests are `legacy_confirmed`.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused tests exercise the public pipeline result and artifact contract directly.

**Specification Coverage:**
- Resume from CV generation, structured CV export, accepted-CV debug output, reranker-blocked artifact preservation, deterministic completion ordering, and sorted/statused export results.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/pipeline.py::run_pipeline`
- Inspect/modify: `src/fitcv/pipeline.py::_build_export_results`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py::build_*_stage_block`
- Inspect: CV-generation checkpoint and export helpers called by `run_pipeline`
- Verify: the six CV state/export tests in `tests/test_pipeline.py` listed in Task 1

**Dependencies:**
- Task 1 classifies each candidate as `legacy_confirmed` and records its observed failure. Any `fixture_contract`, `current_unverified`, or other non-legacy result has an explicit no-code, test-only, or handoff disposition in the classification report and is excluded from production repair here.

**Authority:**
- Preauthorized local actions: edit only the pipeline state/export owners and their declared tests, add regression assertions for observed failure paths, and run focused backend tests.
- Stop for: a required change to scoring arithmetic, retrieval strategy, shortlist ordering, evidence-mode semantics, or an API/export schema outside the observed tests.

**Steps:**
- [x] Step 1: Trace the checkpoint payload from `run_pipeline()` through resume dispatch, CV-generation completion, debug records, and `_build_export_results()` for each failing test.
- [x] Step 2: Add or tighten regression assertions for terminal status, structured CV identity, accepted-CV debug payload, reranker-blocked artifacts, deterministic parallel order, and export row ordering/status.
- [x] Step 3: Make the smallest canonical pipeline change that restores those invariants; keep raw checkpoint data, stage artifacts, and public export fields backward-compatible.
- [x] Step 4: Re-run the six exact tests and inspect the resulting state/artifact payloads rather than relying only on aggregate status.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order tests/test_pipeline.py::test_run_pipeline_returns_export_results_sorted_and_statused`
- Expected: all six pass; exported results retain deterministic ordering and status, and resume preserves the expected CV/debug/artifact records.

**Exit Criteria:**
- Every CV state/export test classified `legacy_confirmed` passes without changing retrieval, scoring, or evidence-mode contracts; non-legacy tests have a recorded disposition.

### Task 3: Repair pre-enrichment filtering and screening-result persistence

**Purpose:**
- Ensure pre-filtered jobs reach the correct terminal rejection state before enrichment and that screening results persist and round-trip through SQLite.

**Task Function:**
- Backend boundary and persistence repair for filtering side effects.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Task 1 confirms both filtering tests are `legacy_confirmed`.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct pipeline and SQLite tests cover success, rejection, and persisted state.

**Specification Coverage:**
- Pre-enrichment rejection behavior and run-scoped screening-result persistence, including public read-back and identity fields.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/pipeline.py::run_pipeline` inline pre-enrichment filtering path
- Inspect: `src/fitcv/pipeline_stage_runner.py::execute_enrich_stage`
- Inspect/modify: `src/fitcv/rule_filter.py::store_filter_results`
- Inspect/modify: effective later definitions of `src/fitcv_cp/sqlite_store.py::replace_filter_results` and `list_filter_results_for_run`
- Verify: `tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment`
- Verify: `tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows`

**Dependencies:**
- Task 1 classifies each filtering/persistence candidate as `legacy_confirmed` and identifies whether the production path uses inline filtering, `execute_enrich_stage()`, or both. Non-legacy results are dispositioned before this task starts.

**Authority:**
- Preauthorized local actions: trace effective runtime definitions, edit only filter orchestration/persistence owners and focused tests, and run disposable SQLite-backed backend tests.
- Stop for: any schema migration, data deletion, unrelated duplicate-definition cleanup, or change to filtering preference semantics not required by the two failing contracts.

**Steps:**
- [x] Step 1: Trace the actual `run_pipeline()` pre-filter path and compare it with `execute_enrich_stage()`; record which path owns the production side effect.
- [x] Step 2: Trace the runtime-effective SQLite definitions and the identity key used by `store_filter_results()` → `replace_filter_results()` → `list_filter_results_for_run()`.
- [x] Step 3: Add regression assertions for pre-enrichment non-invocation, terminal rejection reason/state, persisted passed/rejected rows, marks/reasons, and repeat-safe round-trip behavior.
- [x] Step 4: Apply the smallest fix at the canonical runtime owners and run both focused tests against a temporary SQLite database.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows`
- Expected: pre-filtered jobs are rejected before enrichment, and persisted screening rows are returned with the original identity, reasons, marks, and status.

**Exit Criteria:**
- Every filtering/persistence test classified `legacy_confirmed` passes with no blanket exception handling and no change to configured filtering semantics; non-legacy results have a recorded disposition.

### Task 4: Repair canonical enrichment projection across job collections

**Purpose:**
- Make canonical enrichment fields available consistently through both run-job and bookmark collection APIs when the enrichment row is identified by URL and the collection row has a `run_job_id`.

**Task Function:**
- Canonical identity and read-model projection repair.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Task 1 confirms the canonical SQLite test is `legacy_confirmed`.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: the focused test asserts both public collection surfaces.

**Specification Coverage:**
- Stable enrichment identity, run/bookmark projection parity, and preservation of canonical location, work mode, language, seniority, domain, and skills.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/enrich.py::load_run_structured_jobs`
- Inspect/modify: `src/fitcv_cp/sqlite_store.py::_identity_payload_for_job`
- Inspect/modify: `src/fitcv_cp/sqlite_store.py::_hydrate_run_job_ids`
- Inspect/modify: effective `src/fitcv_cp/sqlite_store.py::query_run_jobs`
- Inspect/modify: effective `src/fitcv_cp/sqlite_store.py::query_bookmarks`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields`

**Dependencies:**
- Task 1 classifies the canonical projection candidate as `legacy_confirmed` and identifies the failing identity path; a non-legacy classification is dispositioned before this task starts.

**Authority:**
- Preauthorized local actions: edit canonical enrichment identity/projection owners and the focused regression test, run disposable SQLite tests, and inspect both query payloads.
- Stop for: schema migration, changing public field names, weakening URL/run-job identity precedence, or modifying unrelated collection sorting/pagination.

**Steps:**
- [x] Step 1: Trace how `load_run_structured_jobs()` stores enrichment when the incoming row lacks `run_job_id`, then trace `_identity_payload_for_job()` and both collection query surfaces.
- [x] Step 2: Define the preserved identity rule in the regression test: use `run_job_id` when the enrichment payload is run-scoped, retain the existing URL fallback for legacy rows, and never let a missing primary-key match erase available canonical fields.
- [x] Step 3: Implement the smallest shared projection fix so `query_run_jobs()` and `query_bookmarks()` consume the same canonical enrichment payload.
- [x] Step 4: Verify the expected fields and identity through both public query results, including the bookmark path.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields`
- Expected: both collection items expose the exact expected canonical fields and the same `run_job_id`.

**Exit Criteria:**
- The canonical projection test passes when classified `legacy_confirmed`, and the shared identity rule is covered without a schema change; otherwise the classification report records the follow-up owner and this task makes no production change.

### Task 5: Classify and disposition the empty-evidence ranking contract

**Purpose:**
- Prevent an unproven ranking regression from being hidden inside legacy maintenance while preserving the explicit empty selected-evidence contract.

**Task Function:**
- Cross-plan regression gate and narrow compatibility disposition.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Task 1 determines whether the failure is baseline-confirmed or current-only.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: the exact test and paired-revision comparison are the required proof.

**Specification Coverage:**
- Explicit selected evidence remains authoritative, including an explicitly empty selected evidence pool; retrieval/ranking behavior is not silently changed.

**Required Skills:**
- `skill-systematic-debugging`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stage_runner.py::execute_ranking_stage`
- Inspect: `src/fitcv/ai_score.py::build_ranking_job_input`
- Inspect: `src/fitcv/ai_score.py::run_ai_scoring`
- Inspect: `src/fitcv/ai_score.py::build_ranking_request`
- Verify: `tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`
- Add or update the request-level regression in `tests/test_ai_score.py`

**Dependencies:**
- Task 1 paired-revision result for the empty-evidence test.

**Authority:**
- Preauthorized local actions: run the paired-revision test, correct the test lookup to the canonical identity key when the raw-URL lookup is directly proven to be a fixture contract mismatch, inspect the fingerprint and actual scoring request payloads, and write the disposition report. Modify `src/fitcv/ai_score.py` or `tests/test_ai_score.py` only when the paired evidence classifies the behavior as `legacy_confirmed`.
- Stop for: a current-only failure, a change that repopulates explicit empty evidence, or any request to alter retrieval/ranking contracts within this legacy plan.

**Steps:**
- [x] Step 1: Run the exact test at `14e2c55195e111c1b4ae5e72b6340cfe001948e7` and `6f170c1c6058c5bd184706934ff8918abb96fe57` under identical conditions.
- [x] Step 2: First verify the test's lookup uses `primary_job_identity_key()`; if the raw URL lookup causes the failure, classify it as `fixture_contract`, correct only the test lookup, rerun both revisions, and do not infer a production defect from the original KeyError.
- [x] Step 3: Exercise the actual no-network scoring boundary with `candidate_evidence=[]` and nonempty legacy `top_evidence`; inspect `run_ai_scoring()` and `build_ranking_request()` so both the fingerprint input and submitted prompt remain empty rather than falling back through an `or` expression.
- [x] Step 4: If the behavior is current-only, write `$EVIDENCE_DIR/ranking-empty-evidence-disposition.md` as `retrieval_ranking_regression`, stop this plan before completion, and route the failure back to retrieval/ranking ownership.
- [x] Step 5: If the behavior reproduces at both revisions, make only the smallest legacy compatibility fix at the proven boundary and add the request-level regression assertion; if it passes at both revisions, record the report as a stale/unreproduced failure with no production code change.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`
- [x] `python -m pytest -q tests/test_ai_score.py`
- Expected: the canonical-identity test and request-level regression prove that an explicitly empty selected pool is preserved through fingerprinting and prompt construction; a current-only failure cannot be closed by this plan.

**Exit Criteria:**
- A paired-revision disposition exists. The task is either closed with no code change, repaired as baseline-confirmed maintenance, or explicitly blocked for retrieval/ranking remediation.

### Task 6: Run final backend and regression verification

**Purpose:**
- Prove the repaired maintenance scope and guard the completed retrieval/ranking behavior before the plan can be handed off for completion verification.

**Task Function:**
- Final integration verification and evidence reconciliation.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Tasks 2–5 complete.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final verification is owned by the lead controller through `skill-verification-before-completion`.

**Specification Coverage:**
- All required targeted failures, containing-file behavior, retrieval/ranking guard contracts, compilation, diff hygiene, and unrestricted full-suite acceptance.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify: all declared source/test targets and `$EVIDENCE_DIR/baseline-classification.md`

**Dependencies:**
- Tasks 2–5 complete, every node has a recorded no-code, fixture-fix, repair, or handoff disposition, and Task 5 is closed as no-code, repaired baseline-confirmed maintenance, or stale/unreproduced. A current-only ranking regression blocks this plan and must be handed back to retrieval/ranking ownership before Task 6 can start.

**Authority:**
- Preauthorized local actions: run the declared verification commands, inspect failures, and write the task-owned final evidence report.
- Stop for: any unresolved in-scope failure, unrecorded scope deviation, dirty unrelated file, or unexpected full-suite failure. Known pre-existing out-of-scope failures must be recorded with their baseline evidence and keep the plan active rather than being masked or declared complete.

**Steps:**
- [x] Step 1: Run the ten exact node IDs with `--maxfail=0` and confirm every in-scope node passes.
- [x] Step 2: Run the containing files `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, and `tests/test_rule_filter.py` without deselection.
- [x] Step 3: Run the retrieval/ranking guard suite covering `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_candidate.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, and `tests/test_ranking_contract.py`.
- [x] Step 4: Run `python -m compileall -q src tests`, `git diff --check`, and unrestricted `python -m pytest -q -ra`; record collected, passed, failed, skipped, xfailed, xpassed, deselected, effective pytest options, and every failure disposition in `$EVIDENCE_DIR/final-verification.md`.
- [x] Step 5: Run `skill-verification-before-completion`; result `verified` is recorded in `$EVIDENCE_DIR/final-verification.md`.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_rule_filter.py`
- [x] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking_contract.py`
- [x] `python -m compileall -q src tests`
- [x] `python -m pytest -q -ra` after `frontend` build (`3520 passed, 10 skipped`)
- [x] `git diff --check`
- Expected: all required in-scope tests pass, the retrieval/ranking guard suite remains green, compilation and diff checks pass, and the unrestricted suite has no unexpected in-scope failures. Any known pre-existing out-of-scope failures are explicitly listed with baseline evidence and prevent a `completed` status until separately accepted or handed off.

**Exit Criteria:**
- Fresh evidence proves the maintenance outcomes, no current-only ranking regression is hidden, no unrelated files changed, and all full-suite non-passing categories are explicitly accounted for before verification handoff.

## Verification

- `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_rule_filter.py`
- `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking_contract.py`
- `python -m compileall -q src tests`
- `python -m pytest -q -ra`
- `git diff --check`
- Inspect `git status --short --branch` and `$EVIDENCE_DIR/final-verification.md`.

## Completion Criteria

The plan is ready for completion verification when:

1. All ten exact failures have paired-revision classification evidence and no failure is mislabeled as historical without reproduction.
2. Every node classified `legacy_confirmed` is repaired at its canonical owner with focused regression proof; `fixture_contract`, `current_unverified`, and other non-legacy outcomes have explicit dispositions and named follow-up owners.
3. The empty-evidence ranking test has a paired-revision disposition; a current-only regression is explicitly routed back to retrieval/ranking ownership rather than closed here.
4. The retrieval/ranking guard suite remains green with deterministic-backend lexical fallback, bounded ranking input, evidence provenance, score arithmetic, thresholds, shortlist ordering, and Loose/Full/Strict semantics unchanged.
5. The containing test files and unrestricted `python -m pytest -q -ra` produce explicit outcome counts without xfail, deselection, broad exception swallowing, or weakened assertions; known pre-existing out-of-scope failures remain recorded and keep the plan active.
6. Compilation, `git diff --check`, workspace status, task evidence, and plan ledger reconcile with the declared targets.
7. `skill-verification-before-completion` returns `verified`; only then may the lead update plan status to `completed`.

This plan does not claim the original Heidi outcome, does not change candidate
profile source data, and does not authorize push, merge, schema migration, or
retrieval/ranking redesign.
