---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
---

# FitCV Evidence Reconciliation And Measured Optimization Plan

## Goal

Make P1-A and P1-B independently verifiable from committed, sanitized,
hash-bound evidence. Keep P0 decisions frozen, classify the first-pass
generation candidate as a completed rejected experiment, and establish one
measured path for reducing full-document regeneration and maximizing reuse.
Defer P1-C and keep P2 frozen.

## Review Findings

- PR #80 fixed local acceptance credential setup and regression coverage. It did
  not change production CV-generation behavior or close canonical P1 evidence.
- `config/acceptance_state.yaml` still reports `p1_a: blocked` and `p1_b: blocked`.
- The current cohort evidence is not yet admissible as canonical: it contains
  machine-local paths, a source commit that must be checked against current
  `main`, incomplete trace/cost/timing detail, and no committed replacement for
  the referenced `.tmp` efficiency report.
- The first-pass candidate has equal-denominator evidence of `0/4` versus
  `0/4`, equal provider calls and regenerations, and higher token use. Its
  classification is `experiment: complete`, `promotion: rejected`,
  `production default: unchanged`.
- P1-A/B closure and optimization are separate decisions. A rejected
  optimization experiment must not keep functional acceptance blocked.

## Implementation Outcomes

### 1. Canonical P1-A/B evidence bundle

Commit one sanitized current-contract cohort artifact and deterministic
manifest. It records source commit, fixture hash, frozen job identities, every
attempted outcome, final artifact identity, native one-page proof, provenance
status, trace attribution, provider calls, tokens, renders, stage timing, and
exclusions. It contains no API key, database path, user-home path, or local
`.tmp` reference.

### 2. Acceptance SSOT and verifier reconciliation

Make `config/acceptance_state.yaml` point only at committed current-contract
evidence for current P1-A/B status. Preserve historical evidence as immutable
audit material, but exclude it from current denominators. Separate
`implementation_status`, `acceptance_status`, `measurement_status`, and
optimization result status in the validated state.

### 3. Measured optimization path

Extend existing trace and benchmark reporting to expose regeneration causes,
reuse hits, proof reuse, provider calls avoided, renders avoided, tokens
avoided, human actions, resolution reuse, and stage p50/p95. Select one narrow
repair or reuse improvement using `frequency × extra calls × extra tokens ×
retry-failure probability`; do not start another broad prompt, retrieval, or
architecture redesign.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-backend-verification`, `skill-performance-optimization`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect repository state, edit listed files, generate sanitized evidence, run declared local tests and verifiers
- User-approval actions: live provider runs, secret use, push, PR creation, merge, destructive cleanup, and changes outside listed surfaces
- Parallel ownership: none
- Sequential fallback: complete evidence admissibility before changing SSOT; complete SSOT/verifier changes before optimization instrumentation; complete instrumentation before selecting an optimization

## Task Breakdown

### Task 1: Establish evidence admissibility and current baseline

**Purpose:**
- Decide whether existing October 3 evidence can be promoted or whether a same-workload rerun is required.

**Task Function:**
- Reconcile evidence identity, scope, and reproducibility without changing product behavior.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: direct evidence review; no delegation benefit.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller owns evidence admission.

**Specification Coverage:**
- Current-contract evidence only; historical 5/5 and unequal 10/9 experiments remain audit-only.
- P1-C remains deferred; P2 remains frozen.

**Required Skills:**
- `skill-systematic-debugging`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`
- Inspect: `docs/superpowers/evidence/2026-10-03-fitcv-current-cohort-b.json`
- Inspect: `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.json`
- Inspect: `scripts/benchmark_cv_efficiency.py:build_report` and `scripts/verify_fitcv_acceptance.py:verify_acceptance`
- Verify: `git rev-parse HEAD`, fixture SHA-256, source-commit ancestry, and all referenced paths

**Dependencies:**
- None.

**Authority:**
- Preauthorized local actions: read current evidence and run local validation commands.
- Stop for: missing source identity, non-ancestor source commit, unrecoverable fixture, secret exposure, or need for a new live cohort.

**Steps:**
- [ ] Step 1: Compare evidence source commit, fixture hash, run ID, contract versions, and accepted artifact IDs with current `main`.
- [ ] Step 2: Confirm current evidence excludes the two timed-out jobs and does not claim historical 169-job comparability.
- [ ] Step 3: Confirm all accepted artifacts have native final proof, one page, provenance attribution, and trace identity.
- [ ] Step 4: If identity or coverage fails, run one fixed current-contract cohort through the repaired local acceptance runner using `.env` without printing or persisting secrets in evidence.

**Verification:**
- [ ] `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-baseline.json`
- Expected: report identifies exact missing or stale evidence; no current claim is promoted from local `.tmp` data.

**Exit Criteria:**
- One admissible evidence source and one explicit rerun decision exist.

### Task 2: Produce committed sanitized cohort evidence

**Purpose:**
- Replace local-path-only closure claims with a reproducible committed artifact and digest.

**Task Function:**
- Export, sanitize, normalize, and hash current-contract evidence from the existing benchmark/reporting path.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: evidence schema and secret-boundary risk require direct ownership.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: deterministic artifact and schema tests are sufficient.

**Specification Coverage:**
- Every attempted outcome included; accepted, review-required, and failed outcomes are not dropped.
- P1-A gates: accepted count > 0, native proof coverage 100%, accepted one-page rate 100%, provenance loss 0, unresolved accepted overflow 0.
- P1-B gates: trace conflicts 0, unattributed accepted artifacts 0, provider/token/timing coverage complete.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `scripts/benchmark_cv_efficiency.py` report export and sanitization boundary.
- Add: `docs/superpowers/evidence/2026-10-03-fitcv-p1-ab-current-contract.json`
- Add: `docs/superpowers/evidence/2026-10-03-fitcv-p1-ab-current-contract.md`
- Add: `docs/superpowers/evidence/2026-10-03-fitcv-p1-ab-current-contract.sha256`
- Verify: `tests/test_benchmark_cv_efficiency.py` and focused evidence-schema tests

**Dependencies:**
- Task 1 complete.

**Authority:**
- Preauthorized local actions: create sanitized evidence and focused tests; use existing local report input.
- Stop for: any secret, absolute user path, unbound database path, missing outcome, or unsupported historical reconstruction.

**Steps:**
- [ ] Step 1: Export the selected run using the existing benchmark command and retain raw output only in disposable `.tmp` storage.
- [ ] Step 2: Normalize paths to repository-relative references or opaque digests; remove API keys, credentials, database locations, and machine-specific metadata.
- [ ] Step 3: Add source commit, fixture digest, report digest, schema version, and deterministic outcome records.
- [ ] Step 4: Verify JSON and Markdown describe identical counts and gates; write the SHA-256 manifest.

**Verification:**
- [ ] `python -m pytest tests/test_benchmark_cv_efficiency.py -q`
- Expected: deterministic export, complete outcomes, stable digest, and secret/path redaction tests pass.

**Exit Criteria:**
- CI can validate the committed artifact without provider credentials or local database access.

### Task 3: Reconcile state schema and acceptance verifier

**Purpose:**
- Make the verifier promote P1-A and P1-B independently from committed current evidence and stop treating rejected optimization as an acceptance blocker.

**Task Function:**
- Extend the existing acceptance-state contract and verifier; do not create a second status registry.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared SSOT and validator changes are tightly coupled.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: state-render and verifier regression tests cover the contract.

**Specification Coverage:**
- `implementation_status`, `acceptance_status`, `measurement_status`, and optimization result are distinct.
- `first_pass_experiment_no_observed_lift` moves from acceptance blockers to rejected optimization evidence.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `scripts/render_acceptance_state.py:_validate_state`, `render_acceptance_state`
- Modify: `scripts/verify_fitcv_acceptance.py:_run_runtime_efficiency_evidence_check`, `verify_acceptance`
- Modify: `config/acceptance_state.yaml`
- Verify: `tests/test_acceptance_state.py`, `tests/test_fitcv_cp/test_acceptance_verifier.py`

**Dependencies:**
- Task 2 complete.

**Authority:**
- Preauthorized local actions: modify state schema, verifier logic, and focused tests within listed files.
- Stop for: production CV-generation changes, status claims unsupported by committed evidence, or schema migration outside acceptance-state consumers.

**Steps:**
- [ ] Step 1: Add validated references for the current-contract evidence bundle and its digest.
- [ ] Step 2: Add a validated optimization result object with `experiment: complete`, `promotion: rejected`, and `production_default: unchanged`.
- [ ] Step 3: Make P1-A and P1-B checks consume only current-contract evidence and report independent failures.
- [ ] Step 4: Preserve `p1_c: deferred` and `p2: deferred`; keep P0 statuses unchanged.
- [ ] Step 5: Add failing tests for stale evidence, missing digest, dropped outcomes, rejected optimization, and independent P1-A/P1-B promotion.

**Verification:**
- [ ] `python -m pytest tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py -q`
- Expected: stale/local evidence blocks; committed complete evidence promotes only satisfied dimensions; rejected optimization does not block P1-A/B.

**Exit Criteria:**
- One verifier command produces a deterministic report whose current status matches `config/acceptance_state.yaml`.

### Task 4: Update canonical closure documentation

**Purpose:**
- Align human-readable closure evidence with the validated SSOT without rewriting historical records.

**Task Function:**
- Update current closure documentation and preserve immutable audit history.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: documentation follows validated state and committed artifact.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: verifier and reference checks provide proof.

**Specification Coverage:**
- Current roadmap reads `P0 finished → P1-A/B closed → P1-C remaining → P2 frozen` only after gates pass.
- First-pass candidate remains rejected and is not presented as a production default.

**Required Skills:**
- `skill-code-standards`

**Files And Symbols:**
- Modify: `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.md`
- Modify: `config/acceptance_state.yaml:evidence_paths` and current status fields
- Verify: all historical evidence files remain unchanged and referenced only as audit evidence

**Dependencies:**
- Task 3 complete.

**Authority:**
- Preauthorized local actions: update current closure documentation and references only.
- Stop for: deletion or rewriting of historical evidence, unsupported promotion language, or new product claims.

**Steps:**
- [ ] Step 1: Replace stale October 2 current-status references with the committed October 3 bundle.
- [ ] Step 2: State P1-A and P1-B independently, including exact gates and residual limits.
- [ ] Step 3: Record optimization rejection, unchanged production default, P1-C deferral, and P2 freeze.

**Verification:**
- [ ] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output .tmp/acceptance-state-rendered.json`
- Expected: all evidence references resolve and rendered state is deterministic.

**Exit Criteria:**
- Documentation, SSOT, and verifier report agree without local-only references.

### Task 5: Complete reuse and stage-timing scorecard

**Purpose:**
- Measure the next optimization target through existing trace infrastructure instead of another redesign.

**Task Function:**
- Fill missing stage, reuse, cost, and human-work coverage in the existing scorecard.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve after Task 4 based on measured missing fields and scope.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent verification profile selected after instrumentation scope is known.

**Specification Coverage:**
- Valid cached artifact: 0 provider calls and 0 renders.
- Stale proof: 0 provider calls and exactly 1 render.
- Report generation duration, artifact acceptance latency, whole-run wall time, reuse hits, proof reuse, avoided work, human actions, and resolution reuse separately.

**Required Skills:**
- `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify only measured gaps in `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`, `_update_efficiency_summary`
- Inspect/modify only measured gaps in `src/fitcv_cp/app_run_support.py:load_cv_generation_trace_payload`
- Modify: `scripts/benchmark_cv_efficiency.py` aggregation and scorecard output
- Verify: `tests/test_benchmark_cv_efficiency.py` and existing reuse/final-artifact tests

**Dependencies:**
- Task 4 complete.

**Authority:**
- Preauthorized local actions: add trace fields and scorecard aggregation for existing events; run bounded local benchmarks.
- Stop for: new monitoring service, provider prompt changes, retrieval redesign, global `top_k` expansion, or missing before/after workload equivalence.

**Steps:**
- [ ] Step 1: Map each missing scorecard field to an existing trace event or final-artifact contract field.
- [ ] Step 2: Add only fields that preserve current trace contracts and redact secrets.
- [ ] Step 3: Add regression proof for cache-hit and stale-proof call/render counts.
- [ ] Step 4: Run one fixed-size baseline and record p50/p95 plus coverage.

**Verification:**
- [ ] `python -m pytest tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_run_artifact_contracts.py -q`
- Expected: scorecard reports complete coverage or explicitly marks unavailable fields; reuse contracts remain unchanged.

**Exit Criteria:**
- One scorecard identifies the dominant regeneration/rework cause with comparable workload evidence.

### Task 6: Implement one bounded regeneration optimization

**Purpose:**
- Reduce measured waste without reopening P1-A/B architecture.

**Task Function:**
- Apply the smallest repair or reuse change for the highest-ranked failure category.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: choose after Task 5 frequency and cost ranking.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: select independently for backend and performance proof.

**Specification Coverage:**
- Prefer section-level regeneration, deterministic local repair, provenance-aware trim/rerender, or `review_required` stop over another equivalent full-document generation.
- Preserve final-artifact gates, trace attribution, and production default unless a bounded measured result passes all gates.

**Required Skills:**
- `skill-performance-optimization`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify only the selected owner in `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, or `src/fitcv/reuse.py` after Task 5 identifies it.
- Verify corresponding focused tests and `scripts/benchmark_cv_efficiency.py` output.

**Dependencies:**
- Task 5 complete.

**Authority:**
- Preauthorized local actions: implement one measured optimization and its focused regression proof.
- Stop for: second independent optimization, changed acceptance gates, lost provenance, non-one-page accepted artifact, or unequal comparison workload.

**Steps:**
- [ ] Step 1: Rank failure categories by frequency, extra calls, extra tokens, and retry-failure probability.
- [ ] Step 2: Select one repair/reuse change with a named baseline and target metric.
- [ ] Step 3: Add failing regression proof before implementation.
- [ ] Step 4: Implement the smallest change; rerun equal-workload incumbent/candidate comparison.
- [ ] Step 5: Reject promotion unless first-pass, total calls/tokens, latency, manual work, and all correctness gates improve or meet the approved target.

**Verification:**
- [ ] `python -m pytest -q`
- [ ] Fixed-size comparable cohort and generated scorecard with source/fixture hashes.
- Expected: no correctness regression; optimization decision is `promoted` only with measured improvement, otherwise `rejected` with production default unchanged.

**Exit Criteria:**
- One optimization decision is recorded with reproducible evidence; no speculative redesign remains in scope.

## Verification

- `python -m pytest tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_run_artifact_contracts.py -q`
- `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output .tmp/acceptance-state-rendered.json`
- `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-report.json`
- `python -m pytest -q`
- `git diff --check`
- Verify committed evidence has no secrets, absolute user paths, local database paths, or `.tmp` dependencies.

## Completion Criteria

The plan is complete only when:

1. P1-A and P1-B status comes from committed current-contract evidence and the verifier passes independently for each dimension.
2. Historical evidence remains immutable and does not affect current denominators.
3. The first-pass candidate is recorded as a completed rejected experiment with production default unchanged.
4. P1-C remains deferred and P2 remains frozen.
5. Reuse and stage timing coverage is present or explicitly unavailable in one scorecard.
6. Any regeneration optimization has equal-workload before/after proof and preserves final-artifact, provenance, trace, and one-page gates.
7. `skill-verification-before-completion` returns `verified` before any branch publication or merge action.

## Execution Record

- Completed October 3, 2026 on `codex/fitcv-p0-p1-closure-contract`.
- Root cause patched in disposable cohort setup: credential was stored under
  `openai_compatible` before a generated custom provider ID existed; local
  runtime correctly looked up the routed custom ID. The runner now registers
  credential after provider creation. Regression proof covers custom-provider
  credential resolution through the local boundary.
- Current fixed-size cohort: source commit `11732c6a72e6e816a19c0fc0e5efdae2fbd103e0`,
  fixture SHA-256 `74843e9fd3655d3c3a8f96a60fd98da3a6a78d6144b40289c8d83dcb17c8ceb5`,
  two runs (`b81204c1-8e5a-43c0-81f1-8263205d6ff0`,
  `70629b36-c725-4243-bfba-55845c9d319b`), 23 attempted outcomes, 13
  accepted final artifacts, 13/13 native one-page, and 0/23 first-pass
  acceptance. P1-B measurement is now `measured`; optimization promotion
  remains rejected and production default unchanged.
- Verification: `3097 passed, 8 skipped`; acceptance verifier passed; state
  render passed; evidence redaction, digest, and `git diff --check` passed.
