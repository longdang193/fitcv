---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-closure-contract
targets:
  - scripts/evaluate_p0b_source_job_relevance.py
  - src/fitcv/evidence.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - scripts/verify_fitcv_acceptance.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_evidence.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_acceptance_verifier.py
  - .github/workflows/repo-hooks.yml
  - config/acceptance_state.yaml
---

# FitCV P0/P1 Closure Contract Plan

## Goal

Close P0-B, P0-C, and P1-B against current repository truth at commit
`6a27b93aa8bed25c6d295d8e08eba06360efe5ea`, then produce fresh acceptance
evidence. Keep P0-A rejected, P1-A maintenance-only, P1-C deferred, and P2
deferred. Do not add retrieval architecture, services, vector stores, LLM
verification, or new orchestration layers.

## Verdict Review

Verdict is accepted with one correction to status interpretation: `config/acceptance_state.yaml`
currently claims P0-B, P0-C, and P1-B passed, but the verdict reports a failed
Acceptance Verifier and three remaining contract defects. Treat those claims as
unproven until this plan's fresh checks pass. The verdict's closure order is
sound:

1. P0-C exact related-field regression.
2. P0-B unknown-evidence pair accounting.
3. P1-B canonical trace deduplication and `run_job_id` lineage.
4. Diagnosable, bounded Acceptance Verifier.
5. Fresh end-to-end measurement; optimization remains follow-up work.

## Implementation Outcomes

### Fail-closed P0-B assignment accounting

Every emitted requirement/evidence assignment is classified exactly once as
`oracle_evaluated`, `explicitly_excluded`, or `unexpected` before any set
intersection. A known requirement paired with unknown evidence remains visible
as an unsafe assignment. Runtime gates require zero unexpected assignments, zero
unsupported assignments, and assignment precision `1.0`; recall denominators
remain limited to supportable requirements.

### Strict P0-C degree semantics

Explicit degree-field alternatives are complete concepts. Exact or canonical
concept matches can verify support. `related field` permits candidate discovery
but does not verify ambiguous token overlap. Degree level remains separate from
degree field. `Computer Science or related field` with `Political Science` fails
verified support.

### Lossless, identity-safe P1-B measurement

Generation traces are normalized once before deduplication and enrichment.
Top-level traces are authoritative when present; embedded traces only fill
missing records. Accepted-artifact events and effort rows carry `run_job_id`.
`run_id` scopes a record but never identifies a job alone. Conflicting job
identities remain unmatched rather than falling back to a loose match. Failed,
regenerated, render-retried, and provider-attempt work contributing to an
accepted artifact remains counted. Zero-acceptance workloads retain cost totals.

### Diagnosable acceptance closure

Acceptance verification writes its JSON report and concise failure summary even
when it fails. CI always uploads the acceptance report and P0-B runtime report.
Acceptance Verifier runs only acceptance-specific checks not already covered by
Full Suite, while preserving all required gates. Reports identify current
implementation commit, evaluation freeze, priority status, failure reason, and
artifact paths.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect and edit listed source, tests, workflow, acceptance metadata, and evidence files; run declared local checks; preserve unrelated untracked files
- User-approval actions: commit, push, merge, publication, external writes, destructive recovery, dependency installation outside existing project setup, discard, cleanup, and production-default changes
- Parallel ownership: none; evaluator, evidence matcher, artifact projection, and verifier contracts are serially dependent
- Sequential fallback: execute Tasks 1–6 in order and stop at each exit gate

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `6a27b93aa8bed25c6d295d8e08eba06360efe5ea`
- Expected workspace: `main` at base commit with existing untracked scratch/runtime files preserved and excluded from this plan
- Next action: branch disposition after verified closure; commit, push, merge, and cleanup remain outside approved execution
- Blockers: acceptance state claims passed while verdict reports failed verifier; status updates wait for fresh proof

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | 125 focused tests passed; verifier passed | `.tmp/fitcv-acceptance-baseline.json`; 125 passed, 4 skipped; verifier exit 0 |
| Task 2 | `completed` | current | `codex` | Task 1 | P0-C hard-negative and positive tests | `src/fitcv/evidence.py`; `tests/test_evidence.py`; 122 passed |
| Task 3 | `completed` | current | `codex` | Task 1 | P0-B pair classification and runtime gates | `.tmp/p0b-contract-closure.json`; 22 passed, 4 skipped; runtime eligible |
| Task 4 | `completed` | current | `codex` | Tasks 2–3 | P1-B identity, dedupe, attempt-accounting tests | 815 passed; duplicate traces and same-run job IDs stay distinct |
| Task 5 | `completed` | current | `codex` | Tasks 2–4 | verifier report, stdout, and CI artifact proof | `.tmp/fitcv-acceptance-closure.json`; verifier exit 0; workflow upload `if: always()` |
| Task 6 | `completed` | current | `codex` | Task 5 | Full Suite, render acceptance, fresh closure evidence | closure evidence; 3015 passed; render 4 passed; verifier exit 0 |

## Task Breakdown

### Task 1: Establish closure baseline

**Purpose:**
- Capture current tracked state, commit, focused failures, and acceptance metadata before edits.

**Task Function:**
- Reconcile verdict claims with source, tests, workflow, and generated acceptance state.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: narrow repository inspection and bounded test execution; resolve through Planning Dispatch before activation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: baseline commands are direct evidence.

**Specification Coverage:**
- Verdict reconciliation; no source changes before reproducible baseline.

**Required Skills:**
- `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:_runtime_requirement_metrics`
- Inspect: `src/fitcv/evidence.py:_related_education_domain_match`, `_assess_responsibility_support`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:_lineage_matches`, `build_accepted_cv_effort_projection`
- Inspect: `scripts/verify_fitcv_acceptance.py:verify_acceptance`, `.github/workflows/repo-hooks.yml:acceptance-verifier`
- Verify: `config/acceptance_state.yaml`, current Git status, focused tests

**Dependencies:**
- Current workspace at base commit; preserve all existing untracked files.

**Authority:**
- Preauthorized local actions: read source/config/workflow and run declared baseline checks, writing only `.tmp` reports
- Stop for: tracked changes, base commit drift, missing dependencies, or any need to delete or rewrite existing fixtures

**Steps:**
- [x] Step 1: Record `git status --short --branch`, `git rev-parse HEAD`, and tracked `git diff --check`; list untracked files without modifying them.
- [x] Step 2: Run focused baseline: `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_acceptance_verifier.py`.
- [x] Step 3: Run `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-baseline.json`; retain report and stdout/stderr tails.
- [x] Step 4: Record which verdict blockers reproduce and which are already fixed at `6a27b93a`.

**Verification:**
- [x] `git rev-parse HEAD`
- [x] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-baseline.json`
- Expected: baseline identifies current blocker state; no tracked source, test, config, or workflow changes.

**Exit Criteria:**
- Base commit and preserved workspace are recorded; every remaining implementation task has a source-backed failing or missing proof target.

### Task 2: Close P0-C concept-level degree matching

**Purpose:**
- Prevent broad education-group overlap from verifying an unrelated degree field.

**Task Function:**
- Tighten requirement parsing and verified-support evaluation while preserving candidate discovery and existing positive alternatives.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: focused parser/matcher change with bounded regression surface; resolve before activation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused evidence tests directly exercise positive and negative contracts.

**Specification Coverage:**
- P0-C strict degree field and degree-level semantics; `Computer Science` versus `Political Science` hard negative.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py:_responsibility_constraints`
- Inspect/modify: `src/fitcv/evidence.py:_related_education_domain_match`
- Inspect/modify: `src/fitcv/evidence.py:_assess_responsibility_support`
- Verify/modify: `tests/test_evidence.py:test_degree_domain_alternatives_match_complete_concepts_only`, related responsibility-support tests

**Dependencies:**
- Task 1 baseline; do not change candidate-discovery ranking or non-education responsibility rules.

**Authority:**
- Preauthorized local actions: edit evidence matcher and focused tests; run declared evidence and analysis tests
- Stop for: new external field ontology, changed degree policy, fixture rewrite, or behavior outside degree-field verification

**Steps:**
- [x] Step 1: Add or strengthen failing cases for `Computer Science or related field` with `Political Science`, `International Business`, and an exact accepted alternative.
- [x] Step 2: Represent explicit alternatives as complete concepts; retain `related field` as discovery-only unless an explicit approved relation proves support.
- [x] Step 3: Keep degree-level matching independent; verify Bachelor/Master mismatches separately from field matching.
- [x] Step 4: Preserve candidate-match behavior where only verification must fail.
- [x] Step 5: Run focused evidence and analysis tests; inspect changed diff for no broad group-overlap fallback.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: exact/canonical alternatives pass; `Political Science` and unrelated fields fail `verified_support`; degree-level mismatch fails; candidate discovery remains available where intended.

**Exit Criteria:**
- P0-C hard-negative is green, positive alternatives remain green, and no ambiguous related-field match can promote verified support.

### Task 3: Close P0-B pair-based assignment accounting

**Purpose:**
- Keep known-requirement/unknown-evidence assignments in safety accounting.

**Task Function:**
- Repair runtime assignment classification before oracle intersection and preserve denominator semantics.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: evaluator contract change with direct fixture coverage; resolve before activation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: evaluator tests and frozen runtime report are direct proof.

**Specification Coverage:**
- P0-B pair classification; zero unexpected and unsupported assignments; precision `1.0` gate.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `scripts/evaluate_p0b_source_job_relevance.py:_runtime_requirement_metrics`
- Inspect/modify: `scripts/evaluate_p0b_source_job_relevance.py:validate_public_inputs` and runtime gate construction
- Verify/modify: `tests/test_p0b_source_job_relevance_evaluator.py` runtime metric and validation tests
- Verify: `data/fitcv-p0-corpus/p0b/*manifest.json`, oracle, projection, and review inputs

**Dependencies:**
- Task 1 baseline; P0-C may run first but does not change P0-B inputs.

**Authority:**
- Preauthorized local actions: edit evaluator/tests and run frozen P0-B commands, writing sanitized `.tmp` reports
- Stop for: new oracle labels, changed exclusion policy, private corpus data, or any recall-denominator change

**Steps:**
- [x] Step 1: Add regression for known requirement plus unknown evidence; assert pair remains unexpected or unsupported and cannot disappear through `selected_pairs` intersection.
- [x] Step 2: Classify each runtime pair exactly once as `oracle_evaluated`, `explicitly_excluded`, or `unexpected` before intersection.
- [x] Step 3: Distinguish supported and unsupported oracle-evaluated pairs; keep recall/coverage over supportable requirements only.
- [x] Step 4: Require `unexpected_assignment_count == 0`, `unsupported_assignment_count == 0`, and `assignment_precision == 1.0` for promotion.
- [x] Step 5: Run frozen evaluator and reconcile runtime report with acceptance-state thresholds.

**Verification:**
- [x] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_p0b_support_oracle.py`
- [x] `python scripts/evaluate_p0b_source_job_relevance.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --output .tmp/p0b-contract-closure.json`
- Expected: known requirement/unknown evidence fails safety; explicit exclusions remain visible and allowed; frozen qualifying input reports zero unexpected and unsupported assignments only if evidence supports it.

**Exit Criteria:**
- P0-B cannot become promotable while any emitted assignment has unknown evidence, unknown requirement, unsupported oracle state, or missing pair classification.

### Task 4: Normalize P1-B trace identity and lineage

**Purpose:**
- Stop duplicate or cross-job trace matching from distorting accepted-CV effort.

**Task Function:**
- Add one canonical trace normalization boundary, strengthen identity precedence, and carry `run_job_id` through accepted-artifact and projection contracts.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: shared artifact contract with multiple callers and identity risk; resolve before activation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: contract tests cover dedupe, collision, replay, and attempt accounting.

**Specification Coverage:**
- P1-B canonical trace dedupe; `run_job_id` lineage; `run_id` cannot identify a job alone; lossless accepted-attempt accounting.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv_cp/run_artifact_contracts.py:accepted_cv_artifact_event_v1`
- Inspect/modify: `src/fitcv_cp/run_artifact_contracts.py:_lineage_value`, `_lineage_matches`
- Inspect/modify: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Inspect/modify: `src/fitcv_cp/app_run_support.py:_load_run_cv_generation_debug_payload`
- Inspect/modify: `src/fitcv_cp/app.py` accepted-artifact event construction
- Inspect/modify: `src/fitcv_cp/worker_job.py` automatic accepted-artifact event construction
- Verify/modify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`

**Dependencies:**
- Tasks 2–3 complete; preserve `accepted_cv_effort_v1` schema compatibility unless a versioned contract change is required and explicitly documented.

**Authority:**
- Preauthorized local actions: edit listed artifact callers and contract tests; run projection, worker, app, and SQLite-focused checks
- Stop for: destructive migration, unversioned persisted-schema break, ambiguous identity policy, or changes to unrelated run-history behavior

**Steps:**
- [x] Step 1: Define canonical trace normalization that extracts stable lineage and source precedence before hashing or enrichment.
- [x] Step 2: Deduplicate top-level and embedded traces using normalized identity/content; embedded copies fill missing records only.
- [x] Step 3: Add `run_job_id` to accepted-artifact events, projection records, and all automatic/HITL event call sites where available.
- [x] Step 4: Make lineage matching require strongest available identity: `run_job_id`, artifact/version identity, generation fingerprint, and attempt identity; use `run_id` only as scope.
- [x] Step 5: Preserve conflicts as unmatched results; remove loose `run_id`-only fallback and prevent cross-job matching within one run.
- [x] Step 6: Confirm failed attempts, regenerations, render retries, provider calls, and zero-acceptance workload totals remain counted once.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: duplicate top-level/embedded traces produce one workload; same `run_id` with different `run_job_id` stays distinct; replay is idempotent; accepted rows include all contributing attempts; zero accepted artifacts retain workload totals.

**Exit Criteria:**
- P1-B effort projection has deterministic, lossless, job-specific lineage and no double-counting from dual trace sources.

### Task 5: Make Acceptance Verifier diagnosable and bounded

**Purpose:**
- Preserve failure artifacts and remove redundant test execution without weakening acceptance gates.

**Task Function:**
- Separate acceptance-specific runtime probes from Full Suite checks and make failure output/artifact upload unconditional.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: workflow and verifier contract change with direct CI evidence; resolve before activation.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: verifier tests and workflow inspection provide bounded proof.

**Specification Coverage:**
- Acceptance report survives failure; stdout names failing priority/gate; CI uploads `.tmp/fitcv-acceptance-report.json` and P0-B runtime report with `if: always()`.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `scripts/verify_fitcv_acceptance.py:verify_acceptance`, `main`, `_run_check`, `_run_runtime_check`
- Inspect/modify: `.github/workflows/repo-hooks.yml:acceptance-verifier`
- Verify/modify: `tests/test_fitcv_cp/test_acceptance_verifier.py`
- Verify: Full Suite job remains owner of broad P0-B/P0-C/P1-B regression suites

**Dependencies:**
- Tasks 2–4 complete; acceptance-specific commands must reflect final contract tests and runtime report paths.

**Authority:**
- Preauthorized local actions: edit verifier, workflow, and verifier tests; run local verifier and YAML/source inspections
- Stop for: weakening a gate, hiding a failed check, uploading private data, or changing unrelated CI jobs

**Steps:**
- [x] Step 1: Ensure report write occurs after captured check results even when a check fails.
- [x] Step 2: Add compact stdout summary listing failed priority, failed gate/reason, report path, runtime report path, and current commit.
- [x] Step 3: Keep verifier bounded to state validation, acceptance-specific probes, and runtime P0-B evaluation; do not duplicate Full Suite without a contract reason.
- [x] Step 4: Add workflow upload step after verifier with `if: always()` for both reports; preserve failure exit status.
- [x] Step 5: Add tests for failed checks, summary output data, deferred/rejected statuses, and CI missing-artifact warning behavior.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-closure.json`
- [x] Inspect `.github/workflows/repo-hooks.yml` for unconditional artifact upload and unchanged non-zero failure behavior.
- Expected: failed verifier exits `1` but leaves readable reports and concise diagnostics; passing verifier exits `0`; CI uploads reports on both outcomes.

**Exit Criteria:**
- Acceptance Verifier failure is actionable from job output and retained artifacts without rerunning broad suites unnecessarily.

### Task 6: Produce fresh closure evidence and reconcile status

**Purpose:**
- Prove P0/P1 closure from one current commit and update maintained acceptance evidence only after all gates pass.

**Task Function:**
- Run focused, full, render, and acceptance checks; record measured P1-B workload facts and explicit deferrals.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: final verification and evidence reconciliation; resolve before activation.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent completion verification is required by plan contract.

**Specification Coverage:**
- Fresh reproducible closure; no unsupported performance claim; P1-C and P2 remain deferred.

**Required Skills:**
- `skill-verification-before-completion`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `config/acceptance_state.yaml` statuses and evidence paths, only after proof passes
- Write: `docs/superpowers/evidence/2026-10-02-fitcv-p0-p1-contract-closure.md`
- Verify: `.tmp/fitcv-acceptance-closure.json`, `.tmp/p0b-contract-closure.json`, `accepted_cv_effort_v1` output, render artifacts

**Dependencies:**
- Tasks 2–5 complete; no acceptance-state promotion before fresh runtime and verifier evidence.

**Authority:**
- Preauthorized local actions: run declared local checks and write sanitized evidence/status files; preserve historical evidence files
- Stop for: private-data publication, failed required gate, stale commit/hash, render failure, or any claim that requires optimization evidence not measured here

**Steps:**
- [x] Step 1: Run focused closure tests for P0-B, P0-C, P1-B, and verifier.
- [x] Step 2: Run `python -m pytest -q -m "not render_acceptance"`.
- [x] Step 3: Run `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance` when native render tools are available; otherwise record blocked render proof and do not claim full closure.
- [x] Step 4: Run Acceptance Verifier and P0-B runtime evaluation from the known-HEAD implementation worktree; inspect reports, hashes, gates, and status.
- [x] Step 5: Record fresh `accepted_cv_effort_v1` workload totals, accepted denominator, attempts, provider calls, failures, regenerations, render retries, tokens, elapsed p50/p95, review questions, human actions, and reused resolutions. Do not infer optimization from one sample.
- [x] Step 6: Update `config/acceptance_state.yaml` and write closure evidence only if all required gates pass; retain P0-A rejected, P1-A maintenance-only, P1-C deferred, and P2 deferred.

**Verification:**
- [x] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python -m pytest -q -m "not render_acceptance"`
- [x] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [x] `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-closure.json`
- [x] `git diff --check`
- Expected: all required checks pass on one implementation commit; reports are readable and current; P0/P1 status matches evidence; no unrelated tracked changes appear.

**Exit Criteria:**
- `skill-verification-before-completion` returns `verified`; P0-B, P0-C, P1-A, and P1-B claims are current and source-backed; P1-C/P2 deferrals are explicit; no commit, push, merge, or cleanup occurs under this plan.

## Verification

- `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-closure.json`
- `git diff --check`
- Inspect current acceptance report, P0-B runtime report, P1-B `accepted_cv_effort_v1` projection, workflow artifact definitions, and sanitized closure evidence.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-C rejects `Computer Science or related field` plus `Political Science` as verified support while preserving exact accepted alternatives.
2. P0-B classifies every emitted assignment pair before intersection; unknown evidence cannot disappear from safety accounting.
3. P0-B promotion requires zero unexpected assignments, zero unsupported assignments, and assignment precision `1.0`.
4. P1-B normalizes top-level and embedded traces before dedupe and uses embedded traces only to fill missing records.
5. `run_job_id` flows through accepted-artifact events and effort projection; `run_id` alone cannot match distinct jobs.
6. Accepted-artifact effort includes all contributing attempts and zero-acceptance workload cost without double-counting replayed inputs.
7. Acceptance Verifier retains reports and concise failure diagnostics on failure, and CI uploads reports with `if: always()`.
8. Full Suite, focused checks, Acceptance Verifier, and Render Acceptance provide fresh evidence from one known-HEAD implementation worktree; commit remains outside approved execution.
9. P1-C and P2 remain explicit deferrals; no new architecture enters scope.
10. `skill-verification-before-completion` returns `verified` before plan status changes from `proposed`.

P1-C implementation remains out of scope. Add it only after protected normal-use data shows a repeatable evidence-gap pattern that offline aggregation can address without entering the request hot path.
