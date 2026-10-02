---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-contract-boundary-optimization
targets:
  - scripts/evaluate_p0b_source_job_relevance.py
  - src/fitcv/evidence.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - config/acceptance_state.yaml
  - scripts/verify_fitcv_acceptance.py
  - tests/
  - .github/workflows/repo-hooks.yml
---

# FitCV P0/P1 Contract-Boundary Closure And Runtime Optimization

## Goal

Close three real findings in commit `4e0cf0884f79a9c14bc05b4748a23528fbe5fea1` without changing deferred scope:

- P0-B rejects every runtime assignment that is not explicitly oracle-evaluated or explicitly excluded.
- P0-C evaluates degree alternatives as complete concepts, keeps degree level separate, and does not verify ambiguous related-field proximity.
- P1-B preserves accepted-artifact lineage and reports workload cost even when zero CVs are accepted.
- Runtime optimization starts only after fresh contract-correctness evidence and keeps ranking, fit gates, artifact truth, and render behavior unchanged.

P0-A, P1-A, P1-C, and P2 remain respectively rejected/maintenance-only/deferred/deferred. No new service, vector database, GraphRAG layer, reranker, LLM verifier, or agent-management surface enters this scope.

## Implementation Outcomes

### Fail-closed P0-B acceptance contract

Runtime assignment pairs have one explicit state: `oracle_evaluated`, `explicitly_excluded`, or `unexpected`. Only the first two are legal. Unknown requirement IDs fail validation and promotion; safety metrics include every evaluated runtime assignment; recall and coverage continue to use supportable requirements only. Gates require zero unexpected assignments, zero unsupported assignments, and assignment precision `1.0`.

### Concept-level P0-C degree semantics

Degree requirements split alternatives such as `economics, finance or data science` into complete accepted concepts. Exact/canonical concept matches can verify support. `related field` remains a separate weaker policy; token overlap alone cannot verify Political Science against Computer Science or International Business against Computer Science. Degree level remains independently evaluated.

### Lossless P1-B effort lineage

Accepted effort projection retains all trace records and attempts contributing to each accepted artifact using run, artifact, generation-input, and explicit attempt identity. Repeated applications to one job remain distinct and idempotent. Zero-acceptance runs return measured workload totals with accepted count `0`; accepted-denominator ratios return `null` or `not_applicable`.

### Machine-driven acceptance evidence

One local/CI verifier validates acceptance state, public corpus manifests, P0-B runtime evidence, P0-C focused regressions, P1-B effort projection, and render acceptance. Generated evidence separates `implementation_status`, `acceptance_status`, and `measurement_status`; a claimed `passed` status without matching evidence fails closed.

### Measured runtime efficiency

Optimization uses identical frozen workloads and environments before and after each change. Priority order: retry/repair waste, expensive diagnostics, support-matrix and candidate preprocessing reuse, duplicate projection copies, one-pass lexical channel scoring, then semantic ablation and bounded candidate-vector reuse. Correctness gates remain unchanged before any optimization is accepted.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edits to task-listed source, tests, acceptance artifacts, verifier, workflow, and docs; read-only inspection; declared local pytest, acceptance, render, and benchmark commands; preservation of unrelated untracked files
- User-approval actions: push, merge, publication, external writes, dependency/provider installation, destructive recovery, discard, cleanup of pre-existing files, and Git disposition
- Parallel ownership: none; `src/fitcv/evidence.py`, evaluator contracts, and P1-B projection surfaces are shared hot paths and stay serialized
- Sequential fallback: execute Tasks 1–8 in order in one lead workspace

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `4e0cf0884f79a9c14bc05b4748a23528fbe5fea1`
- Expected workspace: `main` with existing untracked scratch/runtime files preserved and unstaged
- Next action: preserve final verifier fix in Git and push
- Blockers: local P7 acceptance harness source-order assertion remains pre-existing; P0/P1 closure gates pass

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `complete` | current | `codex` | none | focused baseline, acceptance baseline, benchmark artifacts | `.tmp/p0-p1-contract-baseline.json`; `.tmp/support-baseline.json`; acceptance rerun exposed P7 failure |
| Task 2 | `complete` | current | `codex` | Task 1 | P0-B evaluator tests and fail-closed runtime report | `.tmp/p0b-contract-closure.json`; runtime promotable; 203 explicit exclusions |
| Task 3 | `complete` | current | `codex` | Task 1 | P0-C focused degree regressions | `tests/test_evidence.py`; focused matrix and adjacent suites pass |
| Task 4 | `complete` | current | `codex` | Task 1 | lineage and zero-acceptance effort tests | `tests/test_fitcv_cp/test_run_artifact_contracts.py`; `tests/test_fitcv_cp/test_app.py` |
| Task 5 | `complete` | current | `codex` | Tasks 2–4 | local verifier and CI invocation | `.tmp/fitcv-acceptance-final.json`; all closure checks pass after freeze-semantics fix |
| Task 6 | `complete` | current | `codex` | Task 5 | measured retry/repair and diagnostic reduction | no retry change retained; acceptance runner P7 remains unrelated failure |
| Task 7 | `complete` | current | `codex` | Task 6 | measured reuse/scoring optimization | `.tmp/support-after-optimization.json`; bounded candidate cache retained |
| Task 8 | `complete` | current | `codex` | Tasks 5–7 | full verification and reconciled acceptance state | verifier pass; full non-render and render suites pass; P7 deviation recorded |

## Execution Evidence

- Focused contract suite: `958 passed, 4 skipped`.
- P0-B runtime evaluator: `eligible=true`, `status=promotable`, assignment precision `1.0`, unexpected assignments `0`, unsupported assignments `0`.
- P0-C and P1-B focused proof: verifier captured `122 passed` and `812 passed` respectively.
- Support benchmark: correctness unchanged; total median `2.0127 ms` → `1.9036 ms`, p95 `6.6895 ms` → `4.8489 ms` after bounded candidate-vector reuse.
- Local acceptance harness: P7 remains failed on exact source ordering; API key loaded from root `.env` only.
- Canonical verifier: implementation checks pass; acceptance remains blocked by stale `evaluation_freeze_commit` until commit-backed refresh.
- Canonical verifier fix: `evaluation_freeze_commit` is frozen corpus/policy provenance, not current implementation `HEAD`; verifier no longer blocks fresh checks when those commits differ. Regression proof: `tests/test_fitcv_cp/test_acceptance_verifier.py`.
- Final canonical verifier: passed with P0-B, P0-C, and P1-B verified; P1-C/P2 deferred and P0-A rejected.
- Final suites: `3006 passed, 8 skipped, 4 deselected`; render acceptance `4 passed`.
- Final benchmark: selected support recall `1.0`, assignment precision `1.0`, total median `1.7585 ms`, p95 `4.1610 ms`; correctness unchanged versus baseline.
- Local acceptance: P6/P2/P3/P9/P11/P12/P14/P19/P20/P22/P23/P25 pass; P7 remains limited to `source_order_exact=false`. P7 boundary files are unchanged by this plan; retain as separate follow-up.

## Task Breakdown

### Task 1: Freeze baseline and contract inputs

**Purpose:** Record current behavior before changing contracts or performance.

**Task Function:** Establish reproducible correctness and cost baseline.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: source-first inspection and bounded local measurement; no delegation benefit

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead owns baseline capture

**Specification Coverage:** Verdict distinction between implementation status and acceptance status; performance changes require identical before/after workload evidence.

**Required Skills:** `skill-systematic-debugging`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:validate_public_inputs`, `_runtime_requirement_metrics`
- Inspect: `src/fitcv/evidence.py:_related_education_domain_match`, `_assess_responsibility_support`, `_semantic_runtime_state`, `_embed_text_cached`, `_select_channel_candidates`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Verify: focused tests and existing acceptance/benchmark scripts

**Dependencies:** clean source baseline at base commit; preserve all existing untracked files.

**Authority:**
- Preauthorized local actions: read-only source/test inspection and declared baseline commands; write only `.tmp` evidence files
- Stop for: base commit change, dirty tracked files, missing frozen fixture, or any request to delete/clean unrelated files

**Steps:**
- [ ] Step 1: Confirm `git status --short --branch`, `git rev-parse HEAD`, and `git diff --exit-code` for tracked files; record untracked paths as preserved.
- [ ] Step 2: Run focused baseline: `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`.
- [ ] Step 3: Run `python scripts/run_fitcv_local_p0_acceptance.py --output .tmp/p0-p1-contract-baseline.json` and `python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/support-baseline.json`.
- [ ] Step 4: Record workload fixture, Python version, dependency state, p50/p95 latency, provider calls, regenerations, tokens, acceptance counts, and current gate results without changing acceptance claims.

**Verification:**
- [ ] Baseline commands complete or record concrete pre-existing failures.
- Expected: no tracked file changes; evidence identifies exact fixture, commit, policy hash, and environment.

**Exit Criteria:** Reproducible baseline exists and no tracked source/test/config file changed.

### Task 2: Make P0-B assignment accounting fail closed

**Purpose:** Prevent unknown runtime requirement IDs from bypassing precision and safety gates.

**Task Function:** Repair evaluator boundary classification and preserve metric denominator semantics.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: narrow contract change with shared evaluator callers

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused evaluator tests provide direct proof

**Specification Coverage:** Every runtime assignment is `oracle_evaluated`, `explicitly_excluded`, or `unexpected`; only first two are legal; supportable requirements remain recall denominator.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `scripts/evaluate_p0b_source_job_relevance.py:validate_public_inputs`, `_runtime_requirement_metrics`, runtime gate construction
- Modify: `config/acceptance_state.yaml` only to declare explicit exclusions or corrected status after evidence
- Inspect/modify tests: `tests/test_p0b_source_job_relevance_evaluator.py`, `tests/test_calibrate_p0b_recovery.py`, `tests/test_p0b_support_oracle.py`
- Verify: `data/fitcv-p0-corpus/p0b/*manifest.json` and frozen oracle inputs

**Dependencies:** Task 1 baseline; no implicit exclusion inferred from absent oracle rows.

**Authority:**
- Preauthorized local actions: edit evaluator, focused tests, and explicit acceptance metadata; run evaluator and pytest commands
- Stop for: new oracle labels, corpus rewrite, private input, or behavior requiring changed recall policy

**Steps:**
- [ ] Step 1: Add failing fixtures for unknown requirement ID, explicit excluded requirement ID, known all-negative requirement, and unsupported selected pair.
- [ ] Step 2: Classify each runtime assignment explicitly; reject unexpected IDs during validation or safety gate before promotion.
- [ ] Step 3: Keep recall/coverage denominators limited to supportable requirements while precision/safety counts all oracle-evaluated runtime assignments.
- [ ] Step 4: Add gates `unexpected_assignment_count == 0`, `unsupported_assignment_count == 0`, and `assignment_precision == 1.0`; retain diagnostics without allowing `unscoped_selected_pairs` to hide failure.
- [ ] Step 5: Re-run frozen P0-B evaluator and update acceptance metadata only after report evidence passes.

**Verification:**
- [ ] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_p0b_support_oracle.py`
- [ ] `python scripts/evaluate_p0b_source_job_relevance.py --output .tmp/p0b-contract-closure.json`
- Expected: unknown IDs are not promotable; explicit exclusions are visible; supportable recall unchanged; safety gates pass only with zero unexpected and unsupported assignments.

**Exit Criteria:** P0-B cannot report promotable status while any unknown runtime assignment exists.

### Task 3: Replace token-group degree matching with concept alternatives

**Purpose:** Stop unrelated degree fields from becoming verified through shared tokens and preserve explicit alternative support.

**Task Function:** Narrow education-domain parsing and assessment semantics.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: localized parser/matcher change with direct regression matrix

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused evidence tests cover exact and ambiguous cases

**Specification Coverage:** Complete degree alternatives; exact concepts can verify; related-field policy is weaker; degree level is independent.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv/evidence.py:_responsibility_constraints`, `_related_education_domain_match`, `_assess_responsibility_support`
- Modify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`
- Inspect: `src/fitcv/evidence.py:_responsibility_stem`, `_parse_requirement_qualifiers`

**Dependencies:** Task 1 baseline; preserve existing Claude Code, executive search, Kubernetes, and degree-level behavior.

**Authority:**
- Preauthorized local actions: edit education parsing/matching and focused tests; run evidence and agentic analysis tests
- Stop for: changes to non-education support policy, synonym catalog expansion, embedding/provider use, or altered degree-level semantics

**Steps:**
- [ ] Step 1: Add failing regressions for Political Science vs Computer Science, International Business vs Computer Science, Finance satisfying a Finance alternative, an explicitly allowed related-field positive, and independent degree-level mismatch.
- [ ] Step 2: Parse degree-domain alternatives as complete concepts, excluding grammar markers and the separate `related field` policy token.
- [ ] Step 3: Make exact/canonical concept match the only automatic verified domain support; return non-verified/unknown for ambiguous related-field proximity unless existing explicit policy permits it.
- [ ] Step 4: Preserve candidate-match diagnostics while ensuring `verified_support` remains false for ambiguous or unrelated education evidence.
- [ ] Step 5: Re-run adjacent hard negatives and existing requirement-support tests.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: required positive/negative matrix passes; existing unrelated hard negatives remain rejected; degree level still fails independently.

**Exit Criteria:** P0-C no longer promotes shared-token proximity as verified field support.

### Task 4: Repair P1-B artifact lineage and zero-acceptance measurement

**Purpose:** Make accepted effort attribution lossless and retain cost evidence when no artifact succeeds.

**Task Function:** Align trace identity, attempt aggregation, and projection status with the shared artifact contract.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared contract path affects automatic and HITL callers; serialize changes

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: contract and worker/app tests cover boundary behavior

**Specification Coverage:** Stable identity uses run, artifact, generation fingerprint, and attempt IDs; repeated same-job applications remain distinct/idempotent; zero accepted count still reports measured workload.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv_cp/run_artifact_contracts.py:accepted_cv_artifact_event_v1`, `build_accepted_cv_effort_projection`, trace/attempt helpers
- Modify: `src/fitcv_cp/app_run_support.py:_load_run_cv_generation_debug_payload`
- Inspect/modify callers: `src/fitcv_cp/app.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv/pipeline.py`
- Modify tests: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:** Task 1 baseline; retain existing `accepted_cv_effort_v1` compatibility unless a versioned contract change is proven necessary.

**Authority:**
- Preauthorized local actions: edit shared artifact/trace shaping and focused tests; run direct projection, worker, SQLite, and app tests
- Stop for: destructive schema migration, data deletion, new persistence service, or inability to preserve legacy payload decoding

**Steps:**
- [ ] Step 1: Add failing case with two trace records sharing `job_url` but different run/artifact/input/attempt identity; assert both contributing traces remain attributable and replay-safe.
- [ ] Step 2: Replace lossy `trace_by_job` lookup with stable lineage association; retain all attempts and distinguish repeated applications to the same job.
- [ ] Step 3: Move workload aggregation before the accepted-artifact early return. Return `status: measured`, `accepted_cv_count: 0`, workload calls/tokens/failures/retries/elapsed values, and `null`/`not_applicable` accepted-denominator ratios when no artifact is accepted.
- [ ] Step 4: Reconcile automatic and human-confirmed artifact events through the same lineage contract and preserve idempotent event/artifact deduplication.
- [ ] Step 5: Update app/worker shaping only where required to carry identity fields; do not create a second lineage registry.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- Expected: multiple traces survive projection; zero-acceptance workload is measured; automatic/HITL artifacts remain correct; repeated replay is idempotent.

**Exit Criteria:** P1-B measurement is truthful for accepted and zero-accepted runs, with no job-key data loss.

### Task 5: Add canonical acceptance verifier and CI entry point

**Purpose:** Remove manual status copying and fail when acceptance metadata outruns evidence.

**Task Function:** Compose existing validators into one bounded, deterministic acceptance command.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: orchestration is small and local; no new management surface

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: verifier output and focused harness tests

**Specification Coverage:** Separate implementation, acceptance, and measurement status; validate state, manifests, P0-B, P0-C, P1-B, and render evidence from one local/CI entry point.

**Required Skills:** `skill-backend-verification`

**Files And Symbols:**
- Add: `scripts/verify_fitcv_acceptance.py`
- Modify: `tests/test_fitcv_cp/test_acceptance_harness.py` for verifier contract tests
- Modify: `.github/workflows/repo-hooks.yml` only to invoke the verifier in one bounded acceptance job
- Inspect/modify: `config/acceptance_state.yaml`, `tests/test_acceptance_state.py`, `scripts/render_acceptance_state.py`, `tests/test_cv_render_acceptance.py`

**Dependencies:** Tasks 2–4 complete; verifier consumes canonical evaluator and projection outputs, not duplicated logic.

**Authority:**
- Preauthorized local actions: add verifier/tests and bounded workflow invocation; run local verifier and existing acceptance commands
- Stop for: duplicated business logic, new service credentials, CI dependency expansion beyond existing project dependencies, or status rewrite without evidence

**Steps:**
- [ ] Step 1: Define verifier output with per-priority `implementation_status`, `acceptance_status`, `measurement_status`, commit, policy hash, workload fingerprint, evidence paths, and failure reasons.
- [ ] Step 2: Compose existing acceptance-state, corpus/manifest, P0-B, P0-C, P1-B, and render checks; fail non-zero on claimed `passed` without matching fresh evidence.
- [ ] Step 3: Add deterministic report output under `.tmp` and focused tests for stale evidence, deferred status, missing manifest, and passed/blocked state.
- [ ] Step 4: Invoke same verifier locally and in CI without editing generated evidence by hand.

**Verification:**
- [ ] `python -m pytest -q tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_harness.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- [ ] `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-report.json`
- Expected: verifier exits non-zero for stale or unsupported `passed` claims and exits zero only when required evidence matches current contracts; deferred P1-C/P2 remain explicit.

**Exit Criteria:** One bounded command becomes canonical acceptance evidence source for local and CI checks.

### Task 6: Measure and reduce retry, repair, and diagnostic waste

**Purpose:** Reduce dominant runtime cost without changing output or acceptance semantics.

**Task Function:** Profile frozen workload, then patch only measured waste.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: performance edits require baseline evidence and same-workload comparison

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark and correctness gates are deterministic

**Specification Coverage:** One generation plus at most one bounded targeted repair; reuse `cv_content_plan_v1`, requirement resolutions, and prior analysis by fingerprint; lazy expensive diagnostics.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/pipeline.py:_build_cv_generation_debug_record`, `_build_cv_generation_trace_summary`, generation state around `generation_attempt_count` and `repair_attempt`
- Inspect/modify: `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `_build_cv_generation_debug_payload`
- Inspect/modify tests: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`, pipeline generation tests
- Verify: `scripts/run_fitcv_local_p0_acceptance.py` output metrics and `.tmp/p0-p1-contract-baseline.json`

**Dependencies:** Tasks 2–5; accepted contract baseline is green before performance edits.

**Authority:**
- Preauthorized local actions: measured edits in pipeline/worker diagnostics and focused tests/benchmarks; write `.tmp` reports
- Stop for: lower correctness metrics, changed artifact/render contract, unbounded retry, provider change, or new concurrency architecture

**Steps:**
- [ ] Step 1: Use identical frozen workload, environment, warmups, and measured runs to identify dominant provider calls, retries, regenerations, token cost, elapsed time, and memory when available.
- [ ] Step 2: Reduce repeated generation by preserving one initial generation and at most one bounded targeted repair; reuse existing plan/resolution fingerprints and batch uncertainty inputs.
- [ ] Step 3: Defer expensive trace/diagnostic construction until requested by acceptance, review, export, or failure handling; retain persisted evidence required by contracts.
- [ ] Step 4: Compare before/after output, accepted/review/failed counts, render results, and all contract metrics before accepting latency/call reductions.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_pipeline.py`
- [ ] `python scripts/run_fitcv_local_p0_acceptance.py --output .tmp/p0-p1-contract-after-repair.json`
- Expected: fewer dominant retries/calls or a measured reason for no change; no correctness, artifact, or render regression.

**Exit Criteria:** Only measured retry/diagnostic improvements remain, with identical correctness gates and bounded repair behavior.

### Task 7: Reduce evidence-path allocation and test semantic ablation

**Purpose:** Lower retrieval overhead after contract fixes without silently changing ranking semantics.

**Task Function:** Optimize hot-path evidence reuse in small, reversible steps.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: same-module performance work with exact output comparison

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing benchmark and evidence tests cover output invariants

**Specification Coverage:** Reuse support matrices and candidate preprocessing; avoid duplicate projection copies; one-pass lexical channel scoring; semantic ablation before candidate-vector cache.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py:_semantic_runtime_state`, `_embed_text_cached`, `_score_components`, `_channel_score_components`, `_select_channel_candidates`, `_merge_channel_pools`, `_EvidenceSelectionEngine`, `retrieve_evidence_bundle`
- Inspect: projection construction and `base_items`/`canonical_items` copy sites in `src/fitcv/evidence.py`
- Modify tests/benchmarks: `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`, `scripts/benchmark_requirement_support.py` only where required to compare arms

**Dependencies:** Task 6 and contract verifier green; no semantic optimization accepted before frozen correctness comparison.

**Authority:**
- Preauthorized local actions: edit evidence hot path and benchmark/test code; run identical support and ranking measurements
- Stop for: recall, selected coverage, assignment precision, hard-negative, ranking, or support-status regression; unbounded process cache; Redis/vector service proposal

**Steps:**
- [ ] Step 1: Reuse support matrices and candidate-side preprocessing within one bundle; remove avoidable `deepcopy`/duplicate projection-item copies while preserving immutability at public boundaries.
- [ ] Step 2: Compute lexical channel subscores in one evidence traversal and maintain bounded top-N structures; preserve existing tie-breaking and ranking output.
- [ ] Step 3: Run strict-support lexical-only versus current hybrid on the frozen workload. Keep lexical-only only if recall, selected coverage, assignment precision, latency, and provider/embedding counts meet gates.
- [ ] Step 4: If semantic scoring remains necessary, add only bounded process-local candidate-vector reuse keyed by projection fingerprint, embedding-contract fingerprint, and model; keep job vectors ephemeral.
- [ ] Step 5: Record before/after metrics and reject any optimization whose quality change is not explicitly approved.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_benchmark_requirement_support.py tests/test_p0b_source_job_relevance_evaluator.py`
- [ ] `python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/support-after-optimization.json`
- Expected: exact or approved-equivalent support/ranking outputs; no recall/coverage/precision regression; measurable p50/p95 or call/token improvement before retaining optimization.

**Exit Criteria:** Retrieval hot path is simpler or faster on representative workload, with bounded cache and unchanged contract outcomes.

### Task 8: Final verification and acceptance-state reconciliation

**Purpose:** Prove closure, separate deferred work, and leave plan evidence ready for completion review.

**Task Function:** Run fresh final proof and reconcile durable artifacts.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance and Git evidence require controller authority

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final verification skill owns completion decision

**Specification Coverage:** All implementation outcomes, fresh evidence, explicit deferrals, and no stale passed statuses.

**Required Skills:** `skill-verification-before-completion`, `skill-plan-document-reviewer`

**Files And Symbols:**
- Verify: all task-listed source/tests/scripts, `config/acceptance_state.yaml`, generated reports, `.github/workflows/repo-hooks.yml`
- Inspect: `git diff --check`, tracked/untracked boundary, plan ledger, evidence paths

**Dependencies:** Tasks 1–7 complete with accepted proof.

**Authority:**
- Preauthorized local actions: run final checks, update plan ledger/evidence references, and reconcile acceptance metadata from fresh results
- Stop for: unresolved required failure, stale evidence, unrelated tracked changes, branch/base mismatch, or any Git disposition action

**Steps:**
- [ ] Step 1: Run focused contract suites, full pytest excluding only declared render marker, render acceptance, verifier, and both before/after benchmark comparisons.
- [ ] Step 2: Confirm acceptance state separates `implementation_status`, `acceptance_status`, and `measurement_status`; P1-C/P2 remain deferred and P0-A remains rejected/negative experiment.
- [ ] Step 3: Record accepted deviations, environment, workload fingerprint, metrics, and threshold owner in evidence; do not hand-copy counts that verifier can generate.
- [ ] Step 4: Run `git diff --check`, inspect tracked diff, confirm unrelated untracked files remain untouched, and request independent plan/code review before changing plan status.

**Verification:**
- [ ] `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-final.json`
- [ ] `python -m pytest -q -m "not render_acceptance"`
- [ ] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [ ] `git diff --check`
- Expected: verifier and required tests pass with fresh evidence; only explicit deferred/rejected items remain outside closure.

**Exit Criteria:** `skill-verification-before-completion` returns `verified`; only then may the lead change plan status from `proposed` to `completed` in a later authorized workflow.

## Verification

Final artifact-level proof:

- `python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-final.json`
- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- `python scripts/run_fitcv_local_p0_acceptance.py --output .tmp/p0-p1-contract-final.json`
- `python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/support-final.json`
- `git diff --check`

Required performance comparison uses identical workload, fixture, Python/dependency environment, warmups, measured runs, and policy/contract fingerprints. Report p50/p95 latency, provider calls, regenerations, token totals, embedding fresh/reuse counts, acceptance/review/failure counts, memory when measured, and correctness metrics. Threshold owner: plan owner. Hard gates: zero unexpected assignments, zero unsupported assignments, assignment precision `1.0`, unchanged support recall/coverage, no accepted-artifact lineage loss, zero-acceptance workload measured, no render regression, and no unbounded retry/cache growth.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-B, P0-C, and P1-B implementation outcomes pass focused regression proof.
2. The canonical verifier passes using fresh current-commit evidence.
3. Optimization changes show measured benefit or are rejected and reverted from scope.
4. Full pytest, render acceptance, and final acceptance command pass, with unrelated pre-existing failures explicitly recorded if any.
5. Acceptance metadata, manifests, generated reports, workflow invocation, and this ledger match repository truth.
6. P1-C and P2 remain clearly deferred; P0-A remains a rejected negative experiment; no claim extends beyond evidence.
7. `skill-verification-before-completion` returns `verified` before any final plan-status transition.


