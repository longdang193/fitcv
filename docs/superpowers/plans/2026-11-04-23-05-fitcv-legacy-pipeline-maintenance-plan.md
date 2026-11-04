---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-legacy-pipeline-maintenance
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv/enrich.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
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
`c84c1ee79cafc7e62bf0cad8fbca0ec39a53f705`. The completed retrieval/ranking
plan remains unchanged. This plan first revalidates the failure inventory at
both the current revision and the earlier comparison revision
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
  full-suite proof.

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
provide fresh evidence. No `xfail`, deselection, broad exception swallowing,
or weakened assertion is accepted as a repair.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-using-git-worktrees`, `skill-verification-before-completion`
- Isolation: current implementation workspace plus one temporary detached worktree for comparison-revision tests
- Commit policy: `no commits during execution`; publication or merge requires separate authorization after fresh verification
- Preauthorized local actions: inspect and edit the declared source/test files, run declared local pytest/compile/diff commands, create and remove the task-owned detached comparison worktree, and write task-owned temporary evidence under `.tmp/legacy-pipeline-maintenance/`
- User-approval actions: push, merge, destructive recovery outside the task-owned temporary worktree, discard of unrelated changes, or scope expansion into retrieval/ranking behavior
- Parallel ownership: none; `pipeline.py` and `sqlite_store.py` are shared owners across maintenance clusters
- Sequential fallback: run Tasks 1 through 6 in order; do not begin a repair task until Task 1 records the relevant classification

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-legacy-pipeline-maintenance`
- Base commit: `c84c1ee79cafc7e62bf0cad8fbca0ec39a53f705`
- Expected workspace: clean checkout at the base commit; unrelated user changes remain untouched
- Next action: Task 1, reproduce and classify all ten test node IDs
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current + temporary detached baseline worktree | `unresolved` | none | current/baseline result for all ten node IDs | `.tmp/legacy-pipeline-maintenance/baseline-classification.md` |
| Task 2 | `pending` | current | `unresolved` | Task 1; six CV state/export tests classified `legacy_confirmed` | focused CV state/export tests and artifact assertions | task-local pytest output |
| Task 3 | `pending` | current | `unresolved` | Task 1; pre-filter and screening tests classified `legacy_confirmed` | direct rejection and SQLite round-trip proof | task-local pytest output |
| Task 4 | `pending` | current | `unresolved` | Task 1; canonical projection test classified `legacy_confirmed` | run and bookmark collection parity | task-local pytest output |
| Task 5 | `pending` | current | `unresolved` | Task 1; empty-evidence classification | explicit disposition or narrowly scoped compatibility proof | `.tmp/legacy-pipeline-maintenance/ranking-empty-evidence-disposition.md` |
| Task 6 | `pending` | current | `unresolved` | Tasks 2–5 with Task 5 non-blocked | targeted, guard-suite, and unrestricted full-suite proof | `.tmp/legacy-pipeline-maintenance/final-verification.md` |

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
- Base commit `c84c1ee79cafc7e62bf0cad8fbca0ec39a53f705` is checked out and clean.

**Authority:**
- Preauthorized local actions: create the named detached comparison worktree, run the exact ten-node pytest command at both revisions, inspect source/test history, and write the task-owned classification report.
- Stop for: any uncommitted unrelated change in the implementation workspace, a missing comparison commit, a test that cannot be reproduced at either revision, or evidence that requires changing retrieval/ranking scope.

**Steps:**
- [ ] Step 1: Run the exact ten-node command at the current revision and save the complete output to `.tmp/legacy-pipeline-maintenance/current-ten-tests.txt`.
- [ ] Step 2: Create `.tmp/legacy-pipeline-baseline` as a detached worktree at `14e2c55195e111c1b4ae5e72b6340cfe001948e7`, run the identical ten-node command there, and save output to `.tmp/legacy-pipeline-maintenance/baseline-ten-tests.txt`.
- [ ] Step 3: For each node, record current result, baseline result, observed error, touched symbols between revisions, and one disposition: `legacy_confirmed`, `retrieval_ranking_regression`, `current_unverified`, or `fixture_contract`.
- [ ] Step 4: Write `.tmp/legacy-pipeline-maintenance/baseline-classification.md`, remove only the task-owned detached worktree, and leave unrelated workspace files untouched.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order tests/test_pipeline.py::test_run_pipeline_returns_export_results_sorted_and_statused tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows --disable-warnings --maxfail=0`
- Expected: the report contains all ten node IDs with separate current and baseline outcomes; no failure is labeled historical without a baseline result.

**Exit Criteria:**
- The classification report exists, names an owner and next task for every node, and explicitly gates the empty-evidence ranking test.

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
- Task 1 classifies all six tests as `legacy_confirmed` and records their observed failures.

**Authority:**
- Preauthorized local actions: edit only the pipeline state/export owners and their declared tests, add regression assertions for observed failure paths, and run focused backend tests.
- Stop for: a required change to scoring arithmetic, retrieval strategy, shortlist ordering, evidence-mode semantics, or an API/export schema outside the observed tests.

**Steps:**
- [ ] Step 1: Trace the checkpoint payload from `run_pipeline()` through resume dispatch, CV-generation completion, debug records, and `_build_export_results()` for each failing test.
- [ ] Step 2: Add or tighten regression assertions for terminal status, structured CV identity, accepted-CV debug payload, reranker-blocked artifacts, deterministic parallel order, and export row ordering/status.
- [ ] Step 3: Make the smallest canonical pipeline change that restores those invariants; keep raw checkpoint data, stage artifacts, and public export fields backward-compatible.
- [ ] Step 4: Re-run the six exact tests and inspect the resulting state/artifact payloads rather than relying only on aggregate status.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_recomputes_shortlist_debug_state tests/test_pipeline.py::test_run_pipeline_resume_from_cv_generation_preserves_reranker_blocked_final_artifacts tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order tests/test_pipeline.py::test_run_pipeline_returns_export_results_sorted_and_statused`
- Expected: all six pass; exported results retain deterministic ordering and status, and resume preserves the expected CV/debug/artifact records.

**Exit Criteria:**
- The six legacy CV state/export tests pass without changing retrieval, scoring, or evidence-mode contracts.

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
- Task 1 classifies both tests as `legacy_confirmed` and identifies whether the production path uses inline filtering, `execute_enrich_stage()`, or both.

**Authority:**
- Preauthorized local actions: trace effective runtime definitions, edit only filter orchestration/persistence owners and focused tests, and run disposable SQLite-backed backend tests.
- Stop for: any schema migration, data deletion, unrelated duplicate-definition cleanup, or change to filtering preference semantics not required by the two failing contracts.

**Steps:**
- [ ] Step 1: Trace the actual `run_pipeline()` pre-filter path and compare it with `execute_enrich_stage()`; record which path owns the production side effect.
- [ ] Step 2: Trace the runtime-effective SQLite definitions and the identity key used by `store_filter_results()` → `replace_filter_results()` → `list_filter_results_for_run()`.
- [ ] Step 3: Add regression assertions for pre-enrichment non-invocation, terminal rejection reason/state, persisted passed/rejected rows, marks/reasons, and repeat-safe round-trip behavior.
- [ ] Step 4: Apply the smallest fix at the canonical runtime owners and run both focused tests against a temporary SQLite database.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_blocks_pre_filtered_jobs_before_enrichment tests/test_rule_filter.py::test_store_filter_results_persists_sqlite_rows`
- Expected: pre-filtered jobs are rejected before enrichment, and persisted screening rows are returned with the original identity, reasons, marks, and status.

**Exit Criteria:**
- Both filtering/persistence tests pass with no blanket exception handling and no change to configured filtering semantics.

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
- Task 1 classifies the canonical projection test as `legacy_confirmed` and identifies the failing identity path.

**Authority:**
- Preauthorized local actions: edit canonical enrichment identity/projection owners and the focused regression test, run disposable SQLite tests, and inspect both query payloads.
- Stop for: schema migration, changing public field names, weakening URL/run-job identity precedence, or modifying unrelated collection sorting/pagination.

**Steps:**
- [ ] Step 1: Trace how `load_run_structured_jobs()` stores enrichment when the incoming row lacks `run_job_id`, then trace `_identity_payload_for_job()` and both collection query surfaces.
- [ ] Step 2: Define the preserved identity rule in the regression test: use `run_job_id` when the enrichment payload is run-scoped, retain the existing URL fallback for legacy rows, and never let a missing primary-key match erase available canonical fields.
- [ ] Step 3: Implement the smallest shared projection fix so `query_run_jobs()` and `query_bookmarks()` consume the same canonical enrichment payload.
- [ ] Step 4: Verify the expected fields and identity through both public query results, including the bookmark path.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py::test_job_collections_project_canonical_enrichment_fields`
- Expected: both collection items expose the exact expected canonical fields and the same `run_job_id`.

**Exit Criteria:**
- The canonical projection test passes and the shared identity rule is covered without a schema change.

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
- Verify: `tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`

**Dependencies:**
- Task 1 paired-revision result for the empty-evidence test.

**Authority:**
- Preauthorized local actions: run the paired-revision test, inspect the fingerprint and scoring request payloads, and write the disposition report.
- Stop for: a current-only failure, a change that repopulates explicit empty evidence, or any request to alter retrieval/ranking contracts within this legacy plan.

**Steps:**
- [ ] Step 1: Run the exact test at `14e2c55195e111c1b4ae5e72b6340cfe001948e7` and `c84c1ee79cafc7e62bf0cad8fbca0ec39a53f705` under identical conditions.
- [ ] Step 2: Inspect both the scoring fingerprint input and actual scoring request to confirm whether an explicit empty `_projected_evidence_pool` remains empty.
- [ ] Step 3: If the test is current-only, write `.tmp/legacy-pipeline-maintenance/ranking-empty-evidence-disposition.md` as `retrieval_ranking_regression`, stop this plan before completion, and route the failure back to retrieval/ranking ownership.
- [ ] Step 4: If the test reproduces at both revisions, make only the smallest legacy compatibility fix at the proven boundary and add the exact regression assertion; if it passes at both revisions, record the report as a stale/unreproduced failure with no code change.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline_agentic_late_stage.py::test_execute_ranking_stage_preserves_empty_evidence_ranking_input`
- Expected: the test passes without profile-evidence fallback when the selected pool is explicitly empty; a current-only failure cannot be closed by this plan.

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
- Verify: all declared source/test targets and `.tmp/legacy-pipeline-maintenance/baseline-classification.md`

**Dependencies:**
- Tasks 2–5 complete with Task 5 closed as no-code, repaired baseline-confirmed maintenance, or stale/unreproduced; a current-only ranking regression blocks this plan and must be handed back to retrieval/ranking ownership before Task 6 can start.

**Authority:**
- Preauthorized local actions: run the declared verification commands, inspect failures, and write the task-owned final evidence report.
- Stop for: any unresolved required failure, unrecorded scope deviation, dirty unrelated file, or failed full-suite check.

**Steps:**
- [ ] Step 1: Run the ten exact node IDs with `--maxfail=0` and confirm every in-scope node passes.
- [ ] Step 2: Run the containing files `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, and `tests/test_rule_filter.py` without deselection.
- [ ] Step 3: Run the retrieval/ranking guard suite covering `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_candidate.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, and `tests/test_ranking_contract.py`.
- [ ] Step 4: Run compilation, `git diff --check`, and unrestricted `python -m pytest -q`; record every result in `.tmp/legacy-pipeline-maintenance/final-verification.md`.
- [ ] Step 5: Run `skill-verification-before-completion`; only that verified result may authorize changing this plan from `proposed` to `completed`.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_rule_filter.py`
- [ ] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking_contract.py`
- [ ] `python -m compileall -q src/fitcv tests`
- [ ] `python -m pytest -q`
- [ ] `git diff --check`
- Expected: all required tests pass, the retrieval/ranking guard suite remains green, compilation and diff checks pass, and the unrestricted suite has no failures.

**Exit Criteria:**
- Fresh evidence proves the maintenance outcomes, no current-only ranking regression is hidden, no unrelated files changed, and the plan is ready for verification handoff.

## Verification

- `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_rule_filter.py`
- `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking_contract.py`
- `python -m compileall -q src/fitcv tests`
- `python -m pytest -q`
- `git diff --check`
- Inspect `git status --short --branch` and `.tmp/legacy-pipeline-maintenance/final-verification.md`.

## Completion Criteria

The plan is ready for completion verification when:

1. All ten exact failures have paired-revision classification evidence and no failure is mislabeled as historical without reproduction.
2. The six CV state/export failures, pre-filter failure, screening persistence failure, and canonical SQLite projection failure are repaired at their canonical owners with focused regression proof.
3. The empty-evidence ranking test has a paired-revision disposition; a current-only regression is explicitly routed back to retrieval/ranking ownership rather than closed here.
4. The retrieval/ranking guard suite remains green with deterministic-backend lexical fallback, bounded ranking input, evidence provenance, score arithmetic, thresholds, shortlist ordering, and Loose/Full/Strict semantics unchanged.
5. The containing test files and unrestricted `python -m pytest -q` pass without xfail, deselection, broad exception swallowing, or weakened assertions.
6. Compilation, `git diff --check`, workspace status, task evidence, and plan ledger reconcile with the declared targets.
7. `skill-verification-before-completion` returns `verified`; only then may the lead update plan status to `completed`.

This plan does not claim the original Heidi outcome, does not change candidate
profile source data, and does not authorize push, merge, schema migration, or
retrieval/ranking redesign.
