---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-closure-optimization
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - scripts/evaluate_p0b_source_job_relevance.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - scripts/build_p0b_support_oracle.py
  - scripts/validate_p0b_support_oracle.py
  - scripts/publish_public_corpus.py
  - scripts/render_acceptance_state.py
  - artifacts/acceptance_state.json
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0b_support_oracle.py
  - tests/test_p0b_holdout_review.py
  - tests/test_p0_public_corpus.py
  - tests/test_cv_render_acceptance.py
  - tests/fixtures/p0b/
  - data/fitcv-p0-corpus/p0b/
  - .github/workflows/repo-hooks.yml
  - docs/superpowers/evidence/
  - docs/pipeline.md
---

# FitCV P0/P1 Closure and Bounded Optimization

## Goal

Produce one reproducible P0/P1 acceptance path and remove only measured P0-B correctness or performance losses. P0-A remains rejected as a negative experiment; P0-C remains protected while its responsibility verifier closes mandatory constraints; P1-A remains maintenance-only; P1-B records bounded real-use measurements; P1-C and P2 remain deferred.

## Verdict Review

The verdict is accepted with these decisions:

- `6/143` relevance recall is not a valid P0-B promotion denominator. Relevance and candidate-evidence support remain separate metrics.
- Broad aliases remain candidate-generation aids only. Proof must verify complete action, object, tool/entity, duration, credential/field, level/domain, qualifier, and negation constraints.
- Pair truth is authoritative: unsupported assigned pairs are false positives; unknown rows remain unjudged until full-pool review resolves them.
- Selected-evidence review cannot prove valid evidence was absent from the rest of the projection. A bounded calibration full-pool support oracle is required before retrieval optimization.
- Calibration decomposition must classify each pair exactly once and match real pipeline stages.
- Clean-checkout CI failures are reproducibility defects. Private raw packets remain private; tests use committed sanitized fixtures or explicit public/external inputs.
- P1-A needs no new render architecture. P1-B has measurement plumbing only at `n=1`; collect normal-use telemetry without claiming efficiency improvement.
- P1-C implementation is explicitly deferred. P2, new embeddings, rerankers, LLM verifiers, graph RAG, new services, and larger global `top_k` are out of scope.

Repository-boundary assumption:

- Canonical repository is `longdang193/fitcv` on `origin`; deprecated `longdang193/fitcv-public` is not a publication target.
- Verify GitHub visibility and remote roles before closure. Do not change repository visibility, force-push, delete repositories, or repoint remotes without explicit user approval.
- One authoritative implementation repository remains source; sanitized corpus and `docs/superpowers` are tracked there. No second runtime or duplicate corpus is maintained.

Pre-execution publication reconciliation:

- Apply only the sanitized corpus tree from the prior canonical public snapshot to current `main`; do not merge unrelated public-branch history.
- Retain current implementation, tests, workflow, and `docs/superpowers` from `main`, adding the new plan as a tracked artifact.
- Commit and push this publication checkpoint to `origin/main` before Task 1. This checkpoint is repository preservation, not plan execution.
- Do not stage protected untracked local files, private CV/profile inputs, runtime state, or generated scratch files.

## Implementation Outcomes

### Trustworthy support proof

`src/fitcv/evidence.py` emits normalized requirement/evidence constraint facts. Only `verified_support` satisfying every mandatory constraint reaches `requirement_support`, `supported_requirement_ids`, `requirement_coverage`, and selection/recovery logic. Contradiction and missing mandatory constraints fail closed.

### Correct P0-B acceptance

The evaluator validates schema, IDs, source joins, review completeness, verdict vocabulary, qualifier vocabulary, accepted evidence references, unsupported assignments, and pair-level false positives. Relevance remains separate. Eligibility is false on validation error, pair false positive, unresolved required review, or failed frozen support thresholds.

### Full-pool calibration truth

A bounded oracle reviews candidate pairs proposed from the complete source-backed evidence projection. It records supported, unsupported, and unjudged states and enables stage metrics for pool availability, candidate generation, verification, qualification, selection, and assignment.

### Reproducible closure and bounded optimization

Clean checkout tests use committed sanitized fixtures or explicit corpus paths. Public publication binds source commit, sanitizer version, contract versions, and hashes. Acceptance status is machine-owned. Only the dominant measured loss is patched; cache/index work is conditional on measured benefit.

### P1 evidence boundary

P1-A keeps current render fixtures and shell consistency. P1-B preserves `accepted_cv_effort_v1` and adds missing durable normal-use fields only where existing event owners can supply them. No efficiency claim is made from `n=1`.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve protected untracked files and do not stage them
- Commit policy: one authorized pre-execution publication checkpoint; no implementation commits during execution
- Preauthorized local actions: inspect source/corpus, edit declared code/tests/fixtures/docs, add sanitized calibration fixtures, run declared checks, and update plan/evidence records
- User-approval actions: repository visibility/remotes, publication, push, merge, force-push, destructive recovery, dependency installation, production-default changes, P1-C/P2 work
- Parallel ownership: none; shared evidence semantics require serialized edits
- Sequential fallback: execute Tasks 1–10 in order and stop at each exit gate

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `e3af6b067bd841d1eeed9af6b9a170ce1b5d56b8`
- Expected workspace: `main` with protected untracked files preserved and unstaged
- Next action: `Pre-execution publication checkpoint, then Task 1 — reconcile repository boundary and acceptance SSOT`
- Blockers: `none`; external visibility/remotes require explicit approval if correction is needed

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current | `unresolved` | none | boundary probe and acceptance-state schema | pending |
| Task 2 | `pending` | current | `unresolved` | Task 1 | mandatory-constraint regressions | pending |
| Task 3 | `pending` | current | `unresolved` | Task 2 | evaluator fail-closed tests | pending |
| Task 4 | `pending` | current | `unresolved` | Task 3 | full-pool oracle fixture | pending |
| Task 5 | `pending` | current | `unresolved` | Task 4 | disjoint/exhaustive calibration | pending |
| Task 6 | `pending` | current | `unresolved` | Task 5 | clean-checkout CI | pending |
| Task 7 | `pending` | current | `unresolved` | Task 6 | one protected acceptance run | pending |
| Task 8 | `pending` | current | `unresolved` | Task 7 | P0/P1 bounded evidence | pending |
| Task 9 | `pending` | current | `unresolved` | Task 7 | measured optimization baseline | pending |
| Task 10 | `pending` | current | `unresolved` | Task 9 | final verification | pending |

## Task Breakdown

### Task 1: Reconcile repository boundary and acceptance SSOT

**Purpose:** Establish repository, remote, visibility, branch, and machine-owned acceptance sources before behavior changes.
**Task Function:** Boundary audit and acceptance-contract alignment.
**Template Profile:** `default` executor; lead controller owns acceptance-state edits.
**Specification Coverage:** Repository-boundary assumption, acceptance-state ownership, public-corpus separation.
**Required Skills:** `skill-systematic-debugging`, `skill-private-public-repo-governance`.
**Files And Symbols:** `artifacts/acceptance_state.json`, `scripts/render_acceptance_state.py`, `scripts/publish_public_corpus.py`, `docs/pipeline.md`, `.github/workflows/repo-hooks.yml`.
**Dependencies:** None.
**Authority:** Current Git state, source/tests, repository metadata, and acceptance-state schema; verdict is intent only.
**Steps:**
1. Record `git status --short --branch`, `git rev-parse HEAD`, remote URLs, and remote roles without changing remotes or visibility.
2. Confirm acceptance state is rendered from one canonical input and public corpus is output-only.
3. Define exact fields for source commit, contract versions, sanitizer version, hashes, P0/P1 status, and evidence paths.
4. Preserve protected untracked files; do not stage or publish private packets/raw CV artifacts.
**Verification:** Run acceptance-state renderer and schema/JSON validation; compare generated output against canonical input; run `git diff --check`.
**Exit Criteria:** Boundary facts and ownership are recorded; no unresolved remote/visibility correction is required; acceptance-state SSOT is reproducible.

### Task 2: Add mandatory-constraint responsibility verification

**Purpose:** Replace responsibility heuristics that can over-credit broad aliases with complete mandatory-constraint verification.
**Task Function:** Evidence normalization and fail-closed support proof.
**Template Profile:** `default` executor.
**Specification Coverage:** Trustworthy support proof; action/object/tool-entity, duration, credential/field, level/domain, qualifier, and negation constraints.
**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** `src/fitcv/evidence.py` (`_parse_requirement_qualifiers`, `_strip_requirement_qualifiers`, `normalise_evidence_item`, `build_evidence_projection`, support scoring/verification helpers); `tests/test_evidence.py`; `tests/test_agentic_cv_analysis.py` if analysis contract fields change.
**Dependencies:** Task 1.
**Authority:** Requirement descriptors and normalized evidence facts in source; existing tests define compatibility unless verdict changes acceptance.
**Steps:**
1. Normalize mandatory constraints into explicit comparable facts while preserving IDs and source references.
2. Separate candidate-generation aliases from proof terms.
3. Require every mandatory constraint to be present and non-contradictory before emitting `verified_support`.
4. Keep missing, contradictory, negated, and qualifier-mismatched evidence unsupported.
5. Reuse existing projection and scoring paths; do not add a second evidence model.
**Verification:** Add tests for complete support, missing object/tool, wrong duration, wrong credential/field, level/domain mismatch, qualifier mismatch, explicit negation, contradiction, and alias-only false support. Run `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`.
**Exit Criteria:** Only complete, non-contradictory support reaches downstream coverage and selection; regressions pass.

### Task 3: Make P0-B evaluation fail closed on pair truth

**Purpose:** Prevent unsupported assigned pairs, incomplete review, and validation errors from passing promotion eligibility.
**Task Function:** Acceptance evaluator hardening.
**Template Profile:** `default` executor.
**Specification Coverage:** Correct P0-B acceptance; pair truth authoritative; relevance separate from support.
**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** `scripts/evaluate_p0b_source_job_relevance.py` (schema/ID/source-join/review/verdict/eligibility functions); `tests/test_p0b_source_job_relevance_evaluator.py`; `tests/test_p0b_holdout_review.py`; `docs/pipeline.md`.
**Dependencies:** Task 2.
**Authority:** Evaluator contract and committed review records; promotion never comes from headline relevance alone.
**Steps:**
1. Validate schema, stable IDs, source joins, verdict vocabulary, qualifier vocabulary, and accepted evidence references.
2. Treat every unsupported assigned pair as false positive, including pairs absent from selected evidence.
3. Keep unknown/unreviewed rows unresolved; eligibility fails closed when required review is incomplete.
4. Remove `6/143` relevance recall from promotion eligibility; report it only as diagnostic relevance.
5. Freeze support thresholds and pair-level acceptance fields in evaluator output.
**Verification:** Add tests for invalid schema, duplicate/missing IDs, stale source joins, invalid verdict/qualifier, dangling evidence, unsupported assignment, pair false positive, unknown row, and relevance-only high score. Run evaluator unit tests and a failing-fixture matrix.
**Exit Criteria:** Any invalid, incomplete, or unsupported pair makes eligibility false; eligibility does not depend on `6/143` relevance recall.

### Task 4: Build bounded full-pool support oracle

**Purpose:** Measure whether valid support exists anywhere in complete source-backed projection before changing retrieval.
**Task Function:** Calibration oracle and sanitized fixture construction.
**Template Profile:** `default` executor.
**Specification Coverage:** Full-pool calibration truth; candidate generation, verification, qualification, selection, and assignment stages.
**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** `scripts/build_p0b_support_oracle.py`, `scripts/validate_p0b_support_oracle.py`, `tests/test_p0b_support_oracle.py`, `tests/fixtures/p0b/`, `data/fitcv-p0-corpus/p0b/`.
**Dependencies:** Task 3.
**Authority:** `src/fitcv/evidence.py` projection and normalized constraint facts; oracle is bounded diagnostic code, not production runtime.
**Steps:**
1. Define deterministic oracle schema with source commit, fixture version, pool bounds, pair IDs, and support state.
2. Enumerate complete source-backed evidence projection for each calibration pair within explicit bounds.
3. Record `supported`, `unsupported`, and `unjudged` with reason codes and source references.
4. Add only redacted/sanitized fixtures; exclude private packets, credentials, raw CVs, and personal data.
5. Validate output and reject duplicate pair IDs, missing source joins, or unsupported state vocabulary.
**Verification:** Run build then validate commands on committed fixtures; assert deterministic hash and stable counts; test empty, duplicate, missing, and unjudged cases.
**Exit Criteria:** Oracle distinguishes pool absence from retrieval loss and remains bounded, sanitized, and non-production.

### Task 5: Repair exhaustive and disjoint calibration accounting

**Purpose:** Make stage-loss metrics sum correctly and classify each pair exactly once.
**Task Function:** Calibration comparison and loss decomposition.
**Template Profile:** `default` executor.
**Specification Coverage:** Calibration decomposition matches real pipeline stages.
**Required Skills:** `skill-test-driven-development`, `skill-performance-optimization`.
**Files And Symbols:** `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, `tests/test_p0b_support_oracle.py`.
**Dependencies:** Task 4.
**Authority:** Oracle pair states, evaluator outputs, and actual stage boundaries; no inferred denominator from selected evidence.
**Steps:**
1. Define one partition over pair IDs: pool unavailable, candidate-generation miss, verification failure, qualification failure, selection loss, assignment loss, supported-through-pipeline, and unjudged.
2. Enforce disjointness and exhaustiveness with assertions/validation errors.
3. Keep denominators explicit per stage and separate relevance diagnostics from support metrics.
4. Compare baseline and current pipeline using identical pair identity and oracle bounds.
5. Emit loss counts, rates, confidence notes, and dominant-loss label for Task 9.
**Verification:** Add conservation, disjointness, duplicate, unknown, and stage-boundary regression tests; run focused benchmark/compare tests and deterministic fixture comparison.
**Exit Criteria:** Every judged pair is classified once, totals reconcile, and output identifies dominant measured loss without false precision.

### Task 6: Repair clean-checkout CI fixtures

**Purpose:** Make acceptance tests pass from clean checkout without private local files.
**Task Function:** Reproducibility and fixture ownership.
**Template Profile:** `default` executor.
**Specification Coverage:** Reproducible closure; sanitized public corpus and explicit external-input boundaries.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.
**Files And Symbols:** `.github/workflows/repo-hooks.yml`, `tests/test_p0_public_corpus.py`, `tests/test_cv_render_acceptance.py`, `tests/fixtures/p0b/`, `data/fitcv-p0-corpus/p0b/`, `scripts/publish_public_corpus.py`, `docs/pipeline.md`.
**Dependencies:** Task 5.
**Authority:** CI workflow, committed fixtures, and source-controlled sanitizer/output contracts.
**Steps:**
1. Identify tests assuming ignored/private paths or local generated artifacts.
2. Replace hidden local dependencies with committed sanitized fixtures or explicit skip/error for absent external inputs.
3. Keep render acceptance marked and runnable with declared dependencies; do not weaken assertions.
4. Bind public corpus output to source commit, sanitizer version, contract versions, and hashes.
5. Verify no private packet or raw artifact is reachable through public publication tests.
**Verification:** Run clean-checkout-equivalent focused suite locally, CI-equivalent non-render and render commands, tracked-file inspection, and publication-manifest checks.
**Exit Criteria:** Focused CI checks pass from clean checkout using only declared inputs; private data remains excluded.

### Task 7: Run one protected corrected P0-B acceptance evaluation

**Purpose:** Produce one auditable P0-B result after correctness and calibration fixes without tuning against repeated holdout feedback.
**Task Function:** Frozen acceptance execution.
**Template Profile:** `default` executor.
**Specification Coverage:** Correct P0-B acceptance and holdout protection.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.
**Files And Symbols:** `scripts/evaluate_p0b_source_job_relevance.py`, `scripts/build_p0b_support_oracle.py`, `scripts/validate_p0b_support_oracle.py`, `artifacts/acceptance_state.json`, `docs/superpowers/evidence/`.
**Dependencies:** Task 6.
**Authority:** Frozen protected evaluation inputs, evaluator output, and machine-owned acceptance state.
**Steps:**
1. Freeze commit, fixture, config, thresholds, and oracle version before execution.
2. Run one corrected P0-B evaluation and record command, environment, hashes, counts, and eligibility.
3. Do not alter production defaults or tune on protected holdout results.
4. Render acceptance state and write evidence record with pass/fail and unresolved rows.
**Verification:** Re-run validators against saved artifacts; compare hashes; confirm no private files entered output; inspect `git diff --check`.
**Exit Criteria:** One reproducible protected result exists; eligibility is determined by pair-level support truth and frozen thresholds.

### Task 8: Close P0 and bounded P1 evidence

**Purpose:** Reconcile final acceptance claims without overstating rejected or deferred work.
**Task Function:** Evidence ledger and status closure.
**Template Profile:** `default` executor.
**Specification Coverage:** P0/P1 status boundaries; P0-A rejected, P0-C protected, P1-A maintenance-only, P1-B `n=1`, P1-C deferred.
**Required Skills:** `skill-verification-before-completion`.
**Files And Symbols:** `artifacts/acceptance_state.json`, `scripts/render_acceptance_state.py`, `docs/superpowers/evidence/`, `docs/pipeline.md`, P1-B event owners in `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/worker_job.py`, and `src/fitcv_cp/app.py`.
**Dependencies:** Task 7.
**Authority:** Protected run evidence, source/tests, and acceptance-state renderer.
**Steps:**
1. Record P0-A as rejected negative experiment; do not relabel it as P0-B failure.
2. Record P0-B only from corrected evaluator output and frozen thresholds.
3. Record P0-C as protected until mandatory-constraint verification and pair truth pass.
4. Keep P1-A maintenance-only and P1-B measurement-only at `n=1`; add only missing durable normal-use fields owned by existing event contracts.
5. Mark P1-C and P2 deferred with no implementation claims.
**Verification:** Validate acceptance-state schema, evidence links, status consistency, and unsupported claims; run focused P1 artifact-contract tests.
**Exit Criteria:** Machine-owned state and evidence agree; every P0/P1 item has explicit status, proof, owner, and next condition.

### Task 9: Optimize only the measured dominant loss

**Purpose:** Improve P0-B only where Task 5 proves material loss, without speculative architecture.
**Task Function:** Measured performance/correctness optimization.
**Template Profile:** `default` executor.
**Specification Coverage:** Bounded optimization; no larger global `top_k`, new embeddings, rerankers, LLM verifiers, graph, service, or datastore.
**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** Only owner files identified by Task 5; expected candidates are `src/fitcv/evidence.py`, `scripts/benchmark_requirement_support.py`, and focused tests.
**Dependencies:** Task 7; Task 5 output selects one loss only.
**Authority:** Measured baseline and dominant-loss output; no optimization from intuition alone.
**Steps:**
1. Capture baseline metric, representative workload, environment, and threshold before editing.
2. Patch one smallest owner-level cause of dominant loss.
3. Preserve mandatory-constraint proof, negation, qualifiers, pair identity, and deterministic output.
4. Re-run calibration and protected acceptance checks; revert if correctness regresses or gain is immaterial.
**Verification:** Compare baseline/after metrics on same workload; run focused regressions and conservation checks; require no P0-B eligibility regression.
**Exit Criteria:** Optimization has measured benefit and no correctness/acceptance regression, or no change ships when benefit is not demonstrated.

### Task 10: Add conditional cache/index optimization only if measured

**Purpose:** Avoid speculative retrieval infrastructure while retaining a bounded path if repeated evidence proves a hot lookup cost.
**Task Function:** Optional performance hardening.
**Template Profile:** `default` executor.
**Specification Coverage:** Conditional cache/inverted-index optimization; P1-C and P2 remain deferred.
**Required Skills:** `skill-performance-optimization`, `skill-verification-before-completion`.
**Files And Symbols:** Same measured owner files as Task 9; no new service or datastore.
**Dependencies:** Task 9.
**Authority:** Fresh benchmark traces and Task 5 loss/latency evidence.
**Steps:**
1. Skip if Task 9 shows no repeated lookup bottleneck or material latency loss.
2. If required, use smallest in-process/native structure at existing owner boundary with explicit invalidation and deterministic behavior.
3. Keep cache/index out of acceptance truth and public corpus identity.
4. Measure memory, cold path, warm path, invalidation, and correctness before/after.
**Verification:** Run cold/warm benchmark, invalidation test, deterministic-output test, full focused suite, and clean-checkout CI commands.
**Exit Criteria:** Cache/index exists only when measured benefit clears recorded threshold; otherwise task is recorded as skipped with evidence.

## Verification

Run in order after implementation:

1. `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_p0b_holdout_review.py tests/test_p0b_support_oracle.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py tests/test_cv_render_acceptance.py`.
2. Run committed oracle build/validate commands on `tests/fixtures/p0b/` and `data/fitcv-p0-corpus/p0b/`; assert stable hashes and conservation totals.
3. Run CI-equivalent commands from clean checkout or clean exported tree, including non-render and render acceptance paths.
4. Run protected P0-B evaluator once with frozen inputs; preserve output hashes and command provenance.
5. Run `python scripts/render_acceptance_state.py` and validate `artifacts/acceptance_state.json` against its schema.
6. Run `git diff --check`, inspect `git status --short`, and confirm protected untracked files remain unmodified and unstaged.
7. Use `skill-verification-before-completion` to reconcile plan ledger, evidence paths, acceptance state, and completion claims. No final status is `completed` without fresh passing evidence.

## Completion Criteria

- Mandatory constraints are represented and verified fail closed; aliases do not prove support alone.
- P0-B eligibility fails on pair false positives, unresolved required review, invalid records, or failed frozen support thresholds.
- `6/143` relevance recall is diagnostic only and cannot promote P0-B.
- Full-pool oracle output is bounded, sanitized, deterministic, and distinguishes pool absence from retrieval loss.
- Calibration categories are exhaustive and disjoint over judged pairs and match actual pipeline stages.
- Clean-checkout CI passes without private local packets or ignored generated artifacts.
- One protected corrected P0-B run is reproducible from committed inputs and linked evidence.
- P0-A remains rejected; P0-C closes only on verified support; P1-A remains maintenance-only; P1-B remains measurement-only at `n=1`; P1-C and P2 remain deferred.
- Only measured optimization ships. No speculative embeddings, reranker, LLM verifier, graph, service, datastore, or global `top_k` expansion appears.
- Acceptance state, evidence records, tests, docs, fixtures, and generated public corpus outputs agree with one canonical source each.
