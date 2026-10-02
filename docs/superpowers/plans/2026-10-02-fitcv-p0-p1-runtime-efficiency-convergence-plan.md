---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-runtime-efficiency-convergence
targets:
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - scripts/render_acceptance_state.py
  - scripts/verify_fitcv_acceptance.py
  - scripts/benchmark_cv_efficiency.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv/cv_generator.py
  - src/fitcv/evidence.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - tests/
  - docs/pipeline.md
  - docs/superpowers/evidence/
---

# FitCV P0/P1 Closure And Runtime Efficiency Convergence

## Goal

Freeze P0 within measured scope, close P1-B measurement integrity with one canonical generation-trace identity, then reduce runtime waste through measured sequential changes. Preserve retrieval quality, requirement-support truth, compiler/render gates, artifact lineage, and deferred P1-C/P2 scope.

## Verdict Review

- P0-A: rejected experiment. Keep incumbent retrieval; make no production-improvement claim.
- P0-B: passed only for frozen oracle scope. Eight supportable requirements reach recall/selection coverage `1.0`; excluded requirements remain outside claim.
- P0-C: passed, including qualifier, entity/domain, degree-level, and Computer Science versus Political Science regressions.
- P1-A: maintenance-only. Existing compiler and one-page render gates remain contract.
- P1-B: functionally implemented. Historical runs remain measurement-incomplete, while fresh post-fix ordinary-run evidence proves complete `run_job_id` and `trace_id` attribution for accepted debug records, artifacts, and `cv_versions`.
- P1-C: deferred. P2: deferred.
- Historical effort totals are not next optimization baseline. Recompute from fresh ordinary runs after trace attribution is trustworthy.

## Implementation Outcomes

### Bounded P0/P1 status source

Acceptance state and generated reports distinguish implementation, acceptance, and measurement status. P0-B/P0-C claims remain bounded to frozen evidence; fresh P1-B measurement is complete for the post-contract workload, with final closure gated by Task 10; P1-C/P2 remain deferred.

### Canonical P1-B trace and effort contract

Every new CV generation receives one immutable `trace_id` at generation start. The ID travels through top-level traces, embedded debug records, accepted artifacts, review actions, CV-version metadata, and `accepted_cv_effort_v1`. New traces deduplicate by `trace_id`; legacy traces use strict scoped compatibility keys. Ambiguous or missing attribution is explicit and never reported as zero cost.

### Measured runtime convergence

A persisted normal-use baseline reports total workload cost and cost per accepted CV. Retry/regeneration waste, content-plan reuse, diagnostics, support verification, channel scoring, copying, and semantic alignment are optimized in that order. Each retained change proves measurable benefit on same workload without correctness, lineage, or render regression. Changes without benefit are rejected and recorded.

### No speculative architecture

No new vector database, GraphRAG layer, reranker, LLM verifier, agent, routing service, global `top_k` expansion, or request-path ESCO dependency enters this plan.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`; current branch contains approved P0/P1 contract commits; preserve unrelated untracked scratch files
- Commit policy: `verified per-task checkpoint commits preauthorized`
- Preauthorized local actions: edits to listed source, tests, scripts, acceptance artifacts, and docs; read-only database inspection; local pytest, render, verifier, and benchmark commands; generation of task-owned reports
- User-approval actions: push, merge, publication, dependency/provider installation, destructive recovery, discard, cleanup of pre-existing files, and changes to repository visibility or remotes
- Parallel ownership: none; trace contracts and retrieval hot paths stay serialized
- Sequential fallback: complete Tasks 1–3 before any efficiency task; run one efficiency task at a time and retain only measured wins

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Base commit: `6a27b93aa8bed25c6d295d8e08eba06360efe5ea`
- Expected workspace: current branch with approved P0/P1 contract commits; existing unrelated untracked files remain untracked and untouched
- Next action: complete final closure verification and reconcile plan status
- Blockers: none; approved rejected/deferred runtime options have task-owned evidence

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | acceptance state and verifier tests | 11 focused tests passed; acceptance verifier passed |
| Task 2 | `completed` | current | `codex` | Task 1 | canonical trace propagation tests | 857 focused cross-boundary tests passed; trace ID assertions added |
| Task 3 | `completed` | current | `codex` | Task 2 | projection, ambiguity, and unmatched-attribution tests | 27 projection tests passed; unmatched metrics null; workload totals retained |
| Task 4 | `completed` | current | `codex` | Task 3 | fresh persisted baseline report | historical baseline incomplete; post-fix fresh run complete with 2 accepted artifacts, non-null `run_job_id`, and zero attribution gaps |
| Task 5 | `completed` | current | `codex` | Task 4 | failure-category and before/after efficiency proof | rejected runtime change; failure evidence recorded |
| Task 6 | `completed` | current | `codex` | Task 5 | content-plan reuse and correctness proof | existing fingerprinted reuse retained; tests passed |
| Task 7 | `completed` | current | `codex` | Task 6 | lazy diagnostics/support benchmark | duplicate support pass removed; tests passed |
| Task 8 | `completed` | current | `codex` | Task 7 | one-pass channel benchmark and parity tests | optimization rejected; parity evidence recorded |
| Task 9 | `completed` | current | `codex` | Task 8 | copy profile and semantic ablation decision | lexical-only rejected; copy refactor deferred |
| Task 10 | `completed` | current | `codex` | Tasks 1–9 | final verifier, full suite, render, and evidence | verified; final evidence recorded |

## Task Breakdown

### Task 1: Reconcile bounded acceptance status

**Purpose:**
- Make acceptance state, generated report, verifier output, and documentation agree on bounded P0/P1 status.

**Task Function:**
- Reconcile implementation, acceptance, and measurement dimensions without widening frozen evidence claims.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: status-only change with known files, low ambiguity, and no provider dependency.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: local verifier tests provide independent proof.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- P0-B remains accepted only for the frozen eight-requirement oracle scope.
- P0-C remains accepted with Computer Science versus Political Science regression coverage.
- P1-A is maintenance-only; P1-B is measurement-blocked until attribution is complete; P1-C and P2 remain deferred.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`, `scripts/render_acceptance_state.py:main`, `scripts/verify_fitcv_acceptance.py:build_acceptance_report`
- Modify: `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, `docs/pipeline.md`
- Verify: `tests/` acceptance-state and verifier tests

**Dependencies:**
- Verdict decisions in this plan are fixed inputs.
- PR #72 merge commit `a38812a64c8a6873798ff583812c5ebcc9b7f86b` is the implementation base.

**Authority:**
- Preauthorized local actions: edit acceptance state, generated acceptance artifact, documentation, and focused tests; run local verifier commands.
- Stop for: any change to P0 scope, P1-C/P2 disposition, repository base, or external publication.

**Steps:**
- [x] Step 1: Compare current acceptance state, generated artifact, verifier schema, and pipeline wording.
- [x] Step 2: Set explicit implementation, acceptance, and measurement fields for P0-B, P0-C, P1-A, P1-B, P1-C, and P2.
- [x] Step 3: Regenerate only owned acceptance output and update `docs/pipeline.md` to match the canonical state source.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_acceptance_state.py`
- Expected: focused acceptance tests pass and generated output contains no contradictory status.

**Exit Criteria:**
- One canonical status source exists, generated output matches it, and bounded claims are explicit.

### Task 2: Create and propagate canonical trace identity

**Purpose:**
- Give every new CV generation one immutable `trace_id` created before any traceable work starts.

**Task Function:**
- Thread one identity through generation, persistence, review, and accepted-effort records.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-file contract change with known call paths and high lineage risk; lead controller retains ownership.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: propagation tests cover each boundary.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- New generations receive one immutable identity at generation start.
- Identity reaches top-level traces, embedded debug records, accepted artifacts, HITL actions, CV-version metadata, and `accepted_cv_effort_v1`.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`, `src/fitcv_cp/worker_job.py:_build_cv_generation_debug_payload`, `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/app.py`, `src/fitcv/cv_generator.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_cv_generator.py`

**Dependencies:**
- Task 1 defines measurement-blocked P1-B status.
- Existing run and artifact schemas remain backward compatible.

**Authority:**
- Preauthorized local actions: edit listed trace, persistence, and generation code plus focused tests; run local unit and direct-boundary checks against temporary stores.
- Stop for: destructive schema migration, production data rewrite, external service access, or any identity field change outside listed records.

**Steps:**
- [x] Step 1: Locate generation entry and every construction path for top-level trace, embedded debug, accepted artifact, HITL, CV-version, and effort records.
- [x] Step 2: Generate `trace_id` once at generation start and pass it through existing payload/context objects rather than adding a new registry.
- [x] Step 3: Persist identity on every new record and preserve legacy records without inventing retroactive IDs.
- [x] Step 4: Add success, retry, rejection, and accepted-artifact tests that assert one ID survives all boundaries.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_cv_generator.py`
- Expected: one `trace_id` per generation; retries and accepted artifacts retain the same ID; unrelated generations never share it.
- [x] Direct temporary SQLite round trip through `src/fitcv_cp/sqlite_store.py`
- Expected: persisted trace, artifact, action, CV-version, and effort rows retain exact identity.

**Exit Criteria:**
- New records carry immutable `trace_id` end to end, with regression coverage for each required boundary.

### Task 3: Fix projection deduplication and unmatched attribution

**Purpose:**
- Stop duplicate workload rows and stop treating missing trace attribution as zero cost.

**Task Function:**
- Normalize new and legacy trace records into one projection with strict scoped fallback and explicit ambiguity.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: deterministic projection logic with known identity fields and focused regression scope.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: projection tests cover duplicate, legacy, unique, and ambiguous records.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- New records deduplicate by `trace_id`.
- Legacy keys are ordered as `run_id + run_job_id`, `run_id + generation_input_fingerprint`, then unique `run_id + job_url`.
- Ambiguous records remain unmatched.
- Missing attribution returns explicit status and `null` per-artifact metrics while workload totals remain visible.
- Required counters exist: `unmatched_trace_count`, `unattributed_accepted_artifact_count`, workload provider calls, and workload tokens.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`, `src/fitcv_cp/run_artifact_contracts.py:_TRACE_IDENTITY_FIELDS`, `src/fitcv_cp/app_run_support.py:_load_run_cv_generation_debug_payload`
- Modify: `src/fitcv_cp/app_run_support.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/run_artifact_contracts.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 2 persists canonical `trace_id` for new records.
- Existing PR #72 cross-run URL fallback remains preserved.

**Authority:**
- Preauthorized local actions: edit projection and storage-read code plus focused tests; run temporary-store and fixture-based projection checks.
- Stop for: retroactive data mutation, broad schema redesign, silent fallback widening, or treating ambiguous attribution as zero.

**Steps:**
- [x] Step 1: Replace partial identity deduplication with `trace_id` deduplication for new records.
- [x] Step 2: Implement ordered legacy compatibility keys scoped by `run_id`; accept `run_id + job_url` only when unique inside that run.
- [x] Step 3: Emit explicit attribution status and null per-artifact metrics for unmatched records while retaining aggregate workload totals.
- [x] Step 4: Add counters and projection tests for same-URL cross-run records, duplicate embedded/top-level records, ambiguous legacy rows, and missing trace rows.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py`
- Expected: duplicate rows collapse only when identity is proven; ambiguous and missing rows are counted, not priced at zero.
- [x] Fixture projection with two runs sharing one URL
- Expected: each run retains separate workload attribution.

**Exit Criteria:**
- P1-B attribution is measurement-ready for new records, legacy ambiguity is visible, and no projection path reports unknown cost as zero.

### Task 4: Produce fresh persisted normal-use workload baseline

**Purpose:**
- Replace historical effort totals with reproducible baseline data from ordinary persisted runs.

**Task Function:**
- Build one bounded benchmark/report path that reads stored workload facts and labels attribution quality.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: measurement task with existing persistence and no new runtime service.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: benchmark self-checks and persisted fixture tests.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- Baseline uses fresh ordinary persisted runs.
- Report includes total workload, cost per accepted CV, retries/regenerations, provider calls, tokens, elapsed time, render/compiler outcomes, and attribution counters.
- Missing or ambiguous attribution is excluded from per-artifact cost but never hidden from totals.

**Required Skills:**
- `skill-performance-optimization`
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app_run_support.py:build_accepted_cv_effort_projection`, `src/fitcv_cp/sqlite_store.py`, `scripts/verify_fitcv_acceptance.py:build_acceptance_report`
- Modify: `scripts/benchmark_cv_efficiency.py`, `tests/test_benchmark_cv_efficiency.py`, `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json`, `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md`
- Verify: persisted-run fixture and benchmark output schema

**Dependencies:**
- Task 3 must expose trustworthy attribution status and counters.
- No eligible persisted ordinary runs blocks optimization claims but not benchmark code tests.

**Authority:**
- Preauthorized local actions: add benchmark/report script, fixture tests, and task-owned evidence files; read local persisted data and run local benchmark commands.
- Stop for: provider billing claims from offline estimates, synthetic-only promotion claims, external database writes, or publishing incomplete baseline as accepted.

**Steps:**
- [x] Step 1: Define benchmark input as persisted ordinary runs with explicit run IDs and acceptance outcomes.
- [x] Step 2: Aggregate workload totals and per-accepted-CV metrics with attribution status and counter fields.
- [x] Step 3: Write JSON plus Markdown evidence containing workload identity, environment, run selection, exclusions, and baseline values.
- [x] Step 4: Mark baseline incomplete when no eligible persisted runs exist; do not substitute historical or synthetic totals.

**Verification:**
- [x] `python scripts/benchmark_cv_efficiency.py --help`
- Expected: command documents persisted-input and output options without requiring a new dependency.
- [x] `python -m pytest tests/test_benchmark_cv_efficiency.py`
- Expected: fixture tests prove totals, accepted-CV denominator, null attribution, and counter handling.

**Exit Criteria:**
- A reproducible baseline command and evidence format exist; baseline completeness is explicit.

### Task 5: Reduce failure and regeneration waste

**Purpose:**
- Remove avoidable retries and regeneration work before changing steady-state retrieval or generation behavior.

**Task Function:**
- Classify failed and regenerated attempts, then fix highest-volume local causes without weakening gates.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: sequential optimization with baseline-driven scope and direct failure evidence.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: before/after benchmark plus failure-path tests.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- Failure/regeneration waste is first runtime optimization target.
- Compiler, render, lineage, and requirement-support correctness remain unchanged.
- Changes without measured benefit are rejected and recorded.

**Required Skills:**
- `skill-performance-optimization`
- `skill-systematic-debugging`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`, `src/fitcv_cp/worker_job.py:_run_cancelled_event`, `src/fitcv_cp/app.py`, `scripts/benchmark_cv_efficiency.py`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_benchmark_cv_efficiency.py`, `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-failures.md`
- Verify: failure-category counts and same-workload before/after benchmark

**Dependencies:**
- Task 4 baseline is complete and has eligible persisted workload or an explicit blocked result.

**Authority:**
- Preauthorized local actions: edit failure and regeneration paths, focused tests, and task-owned evidence; run identical local workloads and configured render/compiler gates.
- Stop for: bypassing acceptance gates, changing retry semantics without evidence, external provider changes, or retaining a change without a measured win.

**Steps:**
- [x] Step 1: Group baseline waste by failure category, retry cause, regeneration trigger, and terminal outcome.
- [x] Step 2: Investigate highest-volume local causes; no safe runtime fix was proven, so existing retry semantics remain.
- [x] Step 3: Re-run identical persisted workload and compare total workload, accepted-CV denominator, failure count, regeneration count, and correctness gates.
- [x] Step 4: Record rejected optimization and measured reason in `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-failures.md`.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`
- Expected: failure and regeneration paths preserve terminal state, artifact lineage, and retry behavior.
- [x] `python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-live-workload/control_plane.sqlite3`
- Expected: baseline reports `incomplete` when persisted accepted-artifact attribution is absent; no optimization claim retained.

**Exit Criteria:**
- Highest-volume avoidable failure waste is fixed or explicitly shown non-actionable; no unmeasured optimization remains retained.

### Task 6: Reuse `cv_content_plan_v1` and unaffected sections

**Purpose:**
- Avoid rebuilding unaffected CV content during accepted regeneration while preserving evidence and lineage contracts.

**Task Function:**
- Reuse canonical content-plan sections only when inputs and policy signatures prove validity.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing content-plan contract and bounded regeneration path; no new cache service.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: section reuse, invalidation, and lineage tests.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- `cv_content_plan_v1` is reused for unaffected sections.
- Changed requirements, evidence, policy, or schema invalidate only affected sections.
- Reuse never crosses `trace_id`, candidate baseline, or input fingerprint boundaries.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:_persist_resolution_reanalysis`, `src/fitcv_cp/worker_job.py:_resolve_run_replay_context`, `src/fitcv/cv_generator.py`, `docs/pipeline.md`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv/cv_generator.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_cv_generator.py`, `docs/pipeline.md`
- Verify: content-plan reuse and invalidation tests

**Dependencies:**
- Task 5 establishes failure/regeneration baseline and retained behavior.
- Task 2 establishes identity boundary required for safe reuse.

**Authority:**
- Preauthorized local actions: edit existing regeneration/content-plan code, focused tests, and pipeline documentation; run local deterministic generation checks.
- Stop for: cross-run reuse, stale evidence reuse, changed acceptance policy bypass, or new cache/storage subsystem.

**Steps:**
- [x] Step 1: Identify content-plan sections and existing input/policy signatures.
- [x] Step 2: Retain existing exact-fingerprint reuse with `trace_id`-scoped lineage boundaries.
- [x] Step 3: Retain invalidation and artifact identity preservation; no new cache path added.
- [x] Step 4: Verify existing reuse and fresh-generation tests; no additional optimization retained without a same-scenario provider benchmark.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py`
- Expected: unchanged sections reuse; changed sections regenerate; output and lineage remain correct.
- [x] Same-scenario provider benchmark not retained; existing fingerprinted reuse tests passed and no unmeasured cache claim remains.
- Expected: generation work decreases or change is rejected and recorded.

**Exit Criteria:**
- Valid unaffected-section reuse is proven; stale or cross-run reuse is impossible in covered paths.

### Task 7: Make diagnostics lazy and compute support once

**Purpose:**
- Keep production generation path lean by deferring diagnostic-only work and preventing repeated support computation.

**Task Function:**
- Separate accepted production payload work from opt-in diagnostics while preserving diagnostic completeness when requested.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: known diagnostic payload construction and support-analysis entry points.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: production/diagnostic parity tests and call-count benchmark.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- Diagnostics are lazy.
- Support verification is computed once per required scope and reused by consumers.
- Diagnostic mode remains complete and production mode remains contract-equivalent.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:_build_results_export_payload`, `src/fitcv_cp/worker_job.py:_collect_late_stage_reuse_snapshots`, `src/fitcv/evidence.py:_annotate_requirement_support`, `scripts/benchmark_requirement_support.py`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv/evidence.py`, `scripts/benchmark_requirement_support.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`
- Verify: production and diagnostic payload tests plus support call-count benchmark

**Dependencies:**
- Task 6 preserves content-plan inputs used by support computation.
- Existing diagnostic output contracts remain source of truth.

**Authority:**
- Preauthorized local actions: edit diagnostic/support call paths and focused tests; run local production and diagnostic benchmark modes.
- Stop for: removing required diagnostics, changing support semantics, adding a second support matrix, or moving required checks after acceptance.

**Steps:**
- [x] Step 1: Identify duplicate support annotation in retrieval and selection.
- [x] Step 2: Compute canonical support once; channel pools preserve annotated fields for selection and recovery.
- [x] Step 3: Retain existing explicit late-stage diagnostic paths; no required diagnostic was removed.
- [x] Step 4: Add one-pass call-count regression and run production/diagnostic parity tests.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_benchmark_cv_efficiency.py`
- Expected: support call count is one per scope; diagnostic output remains complete; production path skips opt-in work.
- [x] `python scripts/benchmark_requirement_support.py --help`
- Expected: existing benchmark interface remains available without new provider dependency.

**Exit Criteria:**
- Diagnostic-only work is lazy and support computation has one canonical producer with parity proof.

### Task 8: Score retrieval channels in one traversal

**Purpose:**
- Remove repeated candidate scans without changing incumbent retrieval policy or frozen P0 claims.

**Task Function:**
- Combine existing channel scoring into one traversal and preserve deterministic ordering and channel rationale.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: local hot-path optimization with existing channel functions and deterministic tests.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: parity tests compare candidate IDs, scores, ordering, and support outcomes.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- One-pass retrieval channel scoring.
- Incumbent retrieval stays in production; no P0-A promotion claim.
- Frozen P0-B/P0-C support and disambiguation outcomes remain unchanged.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_score_channel_components`, `src/fitcv/evidence.py:_effective_channel_weights`, `src/fitcv/evidence.py:_select_channel_candidates`, `src/fitcv/evidence.py:_merge_channel_pools`
- Modify: `src/fitcv/evidence.py`, `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`, `docs/superpowers/evidence/2026-10-02-fitcv-retrieval-parity.md`
- Verify: frozen oracle and requirement-support benchmark outputs

**Dependencies:**
- Task 7 establishes one canonical support result.
- No global `top_k` increase, reranker, vector DB, GraphRAG, or routing service is allowed.

**Authority:**
- Preauthorized local actions: edit existing evidence scoring functions, parity tests, and task-owned evidence; run frozen and representative local benchmarks.
- Stop for: changing retrieval policy, adding external retrieval infrastructure, weakening Computer Science versus Political Science separation, or retaining a non-parity result.

**Steps:**
- [x] Step 1: Capture current candidate IDs, scores, ordering, rationales, and support metrics on frozen fixtures.
- [x] Step 2: Evaluate one-pass folding; do not retain speculative rewrite without material measured gain.
- [x] Step 3: Confirm incumbent exact support and ordering outputs remain unchanged.
- [x] Step 4: Record rejected optimization in `docs/superpowers/evidence/2026-10-02-fitcv-retrieval-parity.md`.

**Verification:**
- [x] `python -m pytest tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- Expected: candidate IDs, ordering, support metrics, and disambiguation outcomes remain equal on frozen fixtures.
- [x] `python scripts/compare_requirement_support.py --help`
- Expected: comparison command remains usable for parity evidence.

**Exit Criteria:**
- One-pass scoring either proves lower workload with exact output parity or is rejected with evidence.

### Task 9: Profile deep copies and run semantic ablation

**Purpose:**
- Measure copy overhead and semantic alignment value before keeping further optimization changes.

**Task Function:**
- Profile existing copy boundaries and compare hybrid versus lexical scoring under the same workload and correctness gates.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded profiling and ablation, no architecture change.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: benchmark parity and semantic regression checks.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- Deep-copy profiling occurs after higher-value runtime changes.
- Hybrid-versus-lexical semantic ablation informs, but does not silently change, production policy.
- Quality, support, domain, degree, and disambiguation regressions remain blocked.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_support_fragments`, `src/fitcv/evidence.py:_select_budgeted_items`, `src/fitcv_cp/candidate_profile_service.py`, `src/fitcv/evidence.py:_hybrid_score`
- Modify: `scripts/benchmark_cv_efficiency.py`, `tests/test_benchmark_cv_efficiency.py`, `docs/superpowers/evidence/2026-10-02-fitcv-semantic-ablation.md`
- Verify: profiler output, allocation/copy counters, frozen oracle, and regression fixtures

**Dependencies:**
- Tasks 4–8 provide baseline and retained optimization results.
- Incumbent hybrid policy remains default unless an approved evidence review changes it.

**Authority:**
- Preauthorized local actions: add bounded profiling and ablation reporting to existing benchmark script and tests; run local profilers and frozen fixtures.
- Stop for: production policy change based only on synthetic timing, new semantic infrastructure, or unresolved quality regression.

**Steps:**
- [x] Step 1: Measure copy count, copied payload size, and elapsed time on the representative frozen workload.
- [x] Step 2: Run production/current-hash and lexical-only ablations with identical inputs, budgets, and correctness gates.
- [x] Step 3: Report quality deltas, semantic failures, workload deltas, and decision in `docs/superpowers/evidence/2026-10-02-fitcv-semantic-ablation.md`.
- [x] Step 4: Keep incumbent hybrid behavior; reject lexical-only and defer copy refactor.

**Verification:**
- [x] `python -m pytest tests/test_benchmark_cv_efficiency.py tests/test_evidence.py`
- Expected: profiling and ablation output is reproducible and frozen regressions remain absent.
- [x] Same-workload ablation comparison recorded; lexical-only rejected and incumbent retained.
- Expected: every retained change has paired correctness and runtime evidence.

**Exit Criteria:**
- Copy and semantic costs are measured; no speculative semantic architecture or unapproved policy change remains.

### Task 10: Complete closure verification and evidence

**Purpose:**
- Produce final closure evidence for P0/P1 status and runtime convergence, without changing plan status before verification succeeds.

**Task Function:**
- Reconcile all task outputs, rerun final checks, and record deviations, blockers, and deferred scope.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final integration and acceptance gate owned by lead controller.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: `skill-verification-before-completion` owns fresh final verification.
- Select independently from the executor profile; no profile-rank relationship is required.

**Specification Coverage:**
- P0/P1 status is bounded and reproducible.
- P1-B closes only when accepted artifacts have complete trace attribution and fresh workload evidence.
- Runtime changes are retained only when measured on identical workloads and correctness remains unchanged.
- P1-C and P2 remain deferred.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: all files listed in this plan, `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, `docs/pipeline.md`
- Modify: `docs/superpowers/evidence/2026-10-02-fitcv-p0-p1-runtime-efficiency-convergence.md`, plan ledger and evidence references only when supported by fresh results
- Verify: repository test suite, acceptance verifier, render/compiler gates, benchmark reports, and clean tracked diff

**Dependencies:**
- Tasks 1–9 complete or carry explicit blocked/rejected evidence.
- No unresolved required task, stale acceptance state, or unrecorded scope deviation remains.

**Authority:**
- Preauthorized local actions: run final local verification, update task evidence and final report, and reconcile plan ledger with Git evidence.
- Stop for: failed required checks, missing fresh evidence, new scope, external publication, push, merge, or cleanup of unrelated files.

**Steps:**
- [x] Step 1: Run focused tests, full relevant suite, acceptance verifier, render/compiler gates, and benchmark comparisons.
- [x] Step 2: Review plan once with `skill-plan-document-reviewer`; fix path, symbol, dependency, authority, or proof inconsistencies.
- [x] Step 3: Write final evidence report with retained, rejected, blocked, and deferred changes.
- [x] Step 4: Invoke `skill-verification-before-completion`; fresh attributed workload and final checks return `verified`.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp tests/test_cv_generator.py tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_acceptance_state.py`
- Expected: relevant suite passes with no new failures.
- [x] `python scripts/verify_fitcv_acceptance.py`
- Expected: verifier reports bounded P0-B/P0-C acceptance, P1-B attribution status, and deferred P1-C/P2 without contradictory fields.
- [x] `git diff --check`
- Expected: no whitespace errors.

**Exit Criteria:**
- Fresh final evidence proves every retained outcome, every blocker is explicit, deferred scope stays deferred, and verification authority returns `verified`.

## Verification

- [x] `python -m pytest tests/test_fitcv_cp tests/test_cv_generator.py tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_acceptance_state.py`
- Expected: relevant tests pass.
- [x] `python scripts/verify_fitcv_acceptance.py`
- Expected: acceptance report matches bounded verdict and generated acceptance state.
- [x] `python scripts/benchmark_cv_efficiency.py --help`
- Expected: persisted baseline and candidate comparison interfaces are available.
- [x] `git diff --check`
- Expected: no whitespace errors.
- [x] Manual red-flag scan of plan text, task paths, symbols, dependencies, authority lines, and evidence names against repository state.
- Expected: no unresolved path, symbol, ownership, or verification mismatch.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-B, P0-C, P1-A, P1-B, P1-C, and P2 status dimensions match canonical acceptance state and verdict scope.
2. Every new generation has one immutable `trace_id` across required records.
3. Projection deduplication uses canonical identity, legacy fallbacks remain run-scoped, and ambiguous attribution is explicit.
4. Fresh persisted workload evidence reports totals, accepted-CV denominator, provider calls, tokens, elapsed time, retries, regenerations, and attribution counters.
5. Runtime optimizations are sequential, same-workload measured, correctness-preserving, and rejected when they fail to improve the owned metric.
6. No new vector DB, GraphRAG, reranker, LLM verifier, agent, routing service, global `top_k` expansion, or request-path ESCO dependency is added.
7. Every task-local proof and final verification command is runnable and recorded.
8. `skill-verification-before-completion` returns `verified` before plan status changes to `completed`.
