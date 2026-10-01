---
layer: change
artifact_type: plan
status: active
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
  - scripts/render_acceptance_state.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0b_support_oracle.py
  - tests/test_acceptance_state.py
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

- Publication checkpoint `525216b49afdca80ad15e3a6da57f1633cb9e7c0` is already on `origin/main`; do not repeat publication or merge unrelated public-branch history.
- Current `main` retains implementation, tests, workflow, sanitized corpus, and `docs/superpowers`; this plan is tracked there.
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
- Commit policy: no implementation commits before the final protected input freeze; create one local implementation checkpoint before protected evaluation, and push only with explicit approval
- Preauthorized local actions: inspect source/corpus, edit declared code/tests/fixtures/docs, add sanitized calibration fixtures, run declared checks, and update plan/evidence records
- User-approval actions: repository visibility/remotes, publication, push, merge, force-push, destructive recovery, dependency installation, production-default changes, P1-C/P2 work
- Parallel ownership: none; shared evidence semantics require serialized edits
- Sequential fallback: execute Tasks 1–10 in order and stop at each exit gate

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `525216b49afdca80ad15e3a6da57f1633cb9e7c0`
- Expected workspace: `main` with protected untracked files preserved and unstaged
- Next action: `Task 4 — obtain independent acceptance for draft oracle labels`
- Blockers: draft oracle is structurally complete and threshold is `1.0`, but `123` pairs remain `unjudged` and reviewer provenance is model-only; dependent Tasks 5–9 stay blocked for promotion claims

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `normal` | none | boundary probe and acceptance-state schema | `artifacts/acceptance_state.json`, `tests/test_acceptance_state.py`, `tests/test_p0_public_corpus.py` |
| Task 2 | `completed` | current | `normal` | Task 1 | mandatory-constraint regressions | `src/fitcv/evidence.py`, `tests/test_evidence.py`, `117 passed` |
| Task 3 | `completed` | current | `normal` | Task 2 | evaluator fail-closed tests | `scripts/evaluate_p0b_source_job_relevance.py`, `tests/test_p0b_source_job_relevance_evaluator.py`, `7 passed, 4 skipped` |
| Task 4 | `blocked` | current | `normal` | Task 3 | full-pool oracle fixture | draft oracle validated (`549/549`); blocked: human acceptance and independent reviewer provenance remain missing |
| Task 5 | `pending` | current | `normal` | Task 4 | disjoint/exhaustive calibration | pending |
| Task 6 | `pending` | current | `normal` | Task 5 | clean-checkout CI | pending |
| Task 7 | `pending` | current | `normal` | Task 5, Task 6 | measured optimization baseline | pending |
| Task 8 | `pending` | current | `normal` | Task 7 | one protected acceptance run | pending |
| Task 9 | `pending` | current | `normal` | Task 8 | P0/P1 bounded evidence and final verification | pending |

## Task Breakdown

### Task 1: Reconcile repository boundary and acceptance SSOT

**Purpose:** Establish repository, remote, visibility, branch, and machine-owned acceptance sources before behavior changes.
**Task Function:** Boundary audit and acceptance-contract alignment.
**Template Profile:** `normal` executor; lead controller owns acceptance-state edits.
**Specification Coverage:** Repository-boundary assumption, acceptance-state ownership, public-corpus separation.
**Required Skills:** `skill-systematic-debugging` plus repository-boundary checks defined in this plan; no unavailable governance skill is required.
**Files And Symbols:** `config/acceptance_state.yaml` (new canonical input), `scripts/render_acceptance_state.py` (new renderer), `tests/test_acceptance_state.py` (new schema/render tests), `artifacts/acceptance_state.json` (generated output), `docs/pipeline.md`, `.github/workflows/repo-hooks.yml`.
**Dependencies:** None.
**Authority:** Current Git state, source/tests, repository metadata, and acceptance-state schema; verdict is intent only.
**Steps:**
1. Record `git status --short --branch`, `git rev-parse HEAD`, remote URLs, and remote roles without changing remotes or visibility.
2. Create `config/acceptance_state.yaml` as the sole editable acceptance input; define schema fields for source commit, corpus manifest hashes, contract versions, sanitizer version, P0/P1 status, and evidence paths.
3. Create `scripts/render_acceptance_state.py` and `tests/test_acceptance_state.py`; renderer must reject unknown statuses, missing hashes, missing evidence paths, and duplicate ownership fields.
4. Render with `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json`.
5. Preserve protected untracked files; do not stage or publish private packets/raw CV artifacts.
**Verification:** Run `python -m pytest -q tests/test_acceptance_state.py`, rerun the exact renderer command, validate generated JSON, compare output hashes against canonical manifests, and run `git diff --check`.
**Exit Criteria:** Boundary facts and ownership are recorded; no unresolved remote/visibility correction is required; acceptance-state SSOT is reproducible.

### Task 2: Add mandatory-constraint responsibility verification

**Purpose:** Replace responsibility heuristics that can over-credit broad aliases with complete mandatory-constraint verification.
**Task Function:** Evidence normalization and fail-closed support proof.
**Template Profile:** `normal` executor.
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
**Template Profile:** `normal` executor.
**Specification Coverage:** Correct P0-B acceptance; pair truth authoritative; relevance separate from support.
**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** `scripts/evaluate_p0b_source_job_relevance.py` (public-input loader, pair validation, support-gate, and eligibility functions); `data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl`; `data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv`; `data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1_manifest.json`; `tests/test_p0b_source_job_relevance_evaluator.py`; `tests/test_p0b_holdout_review.py`; `docs/pipeline.md`.
**Dependencies:** Task 2.
**Authority:** Evaluator contract and committed review records; promotion never comes from headline relevance alone.
**Steps:**
1. Remove the public evaluator path's dependency on absent private fixture/packet/group-map defaults. Use only the committed sanitized projection, evidence-link review, review manifest, and oracle inputs; reject any private-path input.
2. Validate schema, stable IDs, source joins, verdict vocabulary, qualifier vocabulary, and accepted evidence references.
3. Treat every unsupported assigned pair as false positive, including pairs absent from selected evidence.
4. Keep unknown/unreviewed rows unresolved; eligibility fails closed when required review is incomplete.
5. Remove `6/143` relevance recall from promotion eligibility; report it only as diagnostic relevance.
6. Freeze support gates as `maximum_pair_false_positives=0`, `minimum_review_completeness=1.0`, and `minimum_oracle_coverage=1.0`; any additional support-recall threshold must be present in `config/acceptance_state.yaml`, or eligibility remains false.
7. Use exact final-run command: `python scripts/evaluate_p0b_source_job_relevance.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --output .tmp/p0b-final.json`.
**Verification:** Add tests for invalid schema, duplicate/missing IDs, stale source joins, invalid verdict/qualifier, dangling evidence, unsupported assignment, pair false positive, unknown row, missing threshold, private input, and relevance-only high score. Run evaluator unit tests and a failing-fixture matrix.
**Exit Criteria:** Any invalid, incomplete, or unsupported pair makes eligibility false; eligibility does not depend on `6/143` relevance recall.

### Task 4: Build bounded full-pool support oracle

**Purpose:** Measure whether valid support exists anywhere in complete source-backed projection before changing retrieval.
**Task Function:** Calibration oracle and sanitized fixture construction.
**Template Profile:** `normal` executor.
**Specification Coverage:** Full-pool calibration truth; candidate generation, verification, qualification, selection, and assignment stages.
**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** `scripts/build_p0b_support_oracle.py` (new), `scripts/validate_p0b_support_oracle.py` (new), `tests/test_p0b_support_oracle.py` (new), `tests/fixtures/p0b/`, `data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl` (new), `data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json` (new), `data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl`.
**Dependencies:** Task 3.
**Authority:** Independently adjudicated labels for a bounded calibration cohort; runtime matching in `src/fitcv/evidence.py` is compared against oracle truth, never used to create it.
**Steps:**
1. Define deterministic oracle schema with source commit, fixture version, bounded cohort ID, pair IDs, support state, adjudicator provenance, review timestamp, and source references.
2. Independently adjudicate every pair in bounded cohort over the complete source-backed projection; no candidate-generation or verifier result may supply oracle labels.
3. Record `supported`, `unsupported`, and `unjudged`; incomplete or truncated coverage remains `unjudged`, never `unsupported`.
4. Add only redacted/sanitized fixtures; exclude private packets, credentials, raw CVs, and personal data.
5. Validate output and reject duplicate pair IDs, missing source joins, missing provenance, incomplete coverage, or unsupported state vocabulary.
6. Produce `data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl` and its manifest with deterministic hashes and coverage counts.
**Verification:** Run `python scripts/build_p0b_support_oracle.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --labels tests/fixtures/p0b/support_oracle_labels.jsonl --output data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --manifest data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json`, then run `python scripts/validate_p0b_support_oracle.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --manifest data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json`; assert deterministic hash, complete bounded coverage, and stable counts.
**Exit Criteria:** Oracle distinguishes pool absence from retrieval loss, uses independent truth, and remains bounded, sanitized, and non-production.

### Task 5: Repair exhaustive and disjoint calibration accounting

**Purpose:** Make stage-loss metrics sum correctly and classify each pair exactly once.
**Task Function:** Calibration comparison and loss decomposition.
**Template Profile:** `normal` executor.
**Specification Coverage:** Calibration decomposition matches real pipeline stages.
**Required Skills:** `skill-test-driven-development`, `skill-performance-optimization`.
**Files And Symbols:** `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `src/fitcv/evidence.py`, `scripts/evaluate_p0b_source_job_relevance.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, `tests/test_p0b_support_oracle.py`, `data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl`.
**Dependencies:** Task 4.
**Authority:** Oracle pair states, evaluator outputs, and actual stage boundaries; no inferred denominator from selected evidence.
**Steps:**
1. Define observable pair-set inputs and precedence for each category: pool unavailable, candidate-generation miss, verification failure, qualification failure, selection loss, assignment loss, supported-through-pipeline, and unjudged.
2. Use existing qualification maps and evaluator assignments; add bounded stage trace fields only where current code lacks an observable boundary.
3. Never infer an unobserved stage; classify it as `unjudged` with a reason code.
4. Enforce disjointness and exhaustiveness with assertions/validation errors.
5. Keep denominators explicit per stage and separate relevance diagnostics from support metrics.
6. Compare baseline and current pipeline using identical pair identity and oracle bounds; emit loss counts, rates, confidence notes, and dominant-loss label for Task 7.
**Verification:** Add conservation, disjointness, duplicate, unknown, missing-stage, and stage-boundary regression tests; run focused benchmark/compare tests and deterministic fixture comparison.
**Exit Criteria:** Every judged pair is classified once, totals reconcile, and output identifies dominant measured loss without false precision.

### Task 6: Repair clean-checkout CI fixtures

**Purpose:** Make acceptance tests pass from clean checkout without private local files.
**Task Function:** Reproducibility and fixture ownership.
**Template Profile:** `normal` executor.
**Specification Coverage:** Reproducible closure; sanitized public corpus and explicit external-input boundaries.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.
**Files And Symbols:** `.github/workflows/repo-hooks.yml`, `tests/test_p0_public_corpus.py`, `tests/test_cv_render_acceptance.py`, `tests/fixtures/p0b/`, `data/fitcv-p0-corpus/p0b/`, `data/fitcv-p0-corpus/p0b/*_manifest.json`, `docs/pipeline.md`.
**Dependencies:** Task 5.
**Authority:** CI workflow, committed fixtures, and source-controlled sanitizer/output contracts.
**Steps:**
1. Identify tests assuming ignored/private paths or local generated artifacts.
2. Replace hidden local dependencies with committed sanitized fixtures or explicit skip/error for absent external inputs.
3. Keep render acceptance marked and runnable with declared dependencies; do not weaken assertions.
4. Validate existing public corpus manifests bind source commit, sanitizer version, contract versions, and hashes; do not add a second publisher or corpus mirror.
5. Verify no private packet or raw artifact is reachable through public publication tests.
**Verification:** Run clean-checkout-equivalent focused suite locally, CI-equivalent non-render and render commands, tracked-file inspection, and publication-manifest checks.
**Exit Criteria:** Focused CI checks pass from clean checkout using only declared inputs; private data remains excluded.

### Task 7: Optimize only the measured dominant loss

**Purpose:** Improve P0-B only where Task 5 proves material loss, without speculative architecture.
**Task Function:** Measured performance/correctness optimization.
**Template Profile:** `normal` executor.
**Specification Coverage:** Bounded optimization; no larger global `top_k`, new embeddings, rerankers, LLM verifiers, graph, service, or datastore.
**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`.
**Files And Symbols:** Only owner files identified by Task 5; expected candidates are `src/fitcv/evidence.py`, `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, and focused tests.
**Dependencies:** Task 5 and Task 6.
**Authority:** Measured baseline and dominant-loss output; no optimization from intuition alone.
**Steps:**
1. Capture baseline metric, representative workload, environment, and threshold before editing.
2. Patch one smallest owner-level cause of dominant loss; fold any measured cache/index need into this same task.
3. Preserve mandatory-constraint proof, negation, qualifiers, pair identity, and deterministic output.
4. Re-run calibration only; do not inspect or rerun protected holdout results during optimization.
5. Skip the change when benefit is not demonstrated or correctness regresses.
**Verification:** Compare baseline/after metrics on same calibration workload; run focused regressions and conservation checks; require no support-gate regression.
**Exit Criteria:** Optimization has measured benefit and no correctness regression, or no optimization ships with skip evidence.

### Task 8: Run one final protected corrected P0-B acceptance evaluation

**Purpose:** Produce one auditable P0-B result after all behavior changes, without tuning against protected results.
**Task Function:** Frozen acceptance execution.
**Template Profile:** `normal` executor.
**Specification Coverage:** Correct P0-B acceptance and holdout protection.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.
**Files And Symbols:** `scripts/evaluate_p0b_source_job_relevance.py`, `scripts/build_p0b_support_oracle.py`, `scripts/validate_p0b_support_oracle.py`, `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, `docs/superpowers/evidence/`.
**Dependencies:** Task 7.
**Authority:** Explicitly admitted sanitized inputs, independently adjudicated oracle, approved threshold fields, evaluator output, and machine-owned acceptance state.
**Steps:**
1. Confirm admitted inputs exist and validate projection, evidence-link review, review manifest, independent oracle, policy, and oracle manifest hashes. If any input or approved threshold is missing, record blocked status and stop.
2. Create one local implementation checkpoint commit and freeze commit, fixture, config, thresholds, and oracle version; do not push as part of this task.
3. Run the exact evaluator command from Task 3 once and record command, environment, hashes, counts, and eligibility.
4. Do not alter production defaults or tune on protected results.
5. Render acceptance state and write evidence record with pass/fail or blocked status and unresolved rows.
**Verification:** Validate saved evaluator, oracle, manifest, and acceptance-state artifacts; compare hashes; confirm no private files entered output; inspect `git diff --check`. Do not rerun protected evaluation after this task.
**Exit Criteria:** One reproducible protected result exists, or an explicit blocked record names missing admitted inputs/thresholds; no later behavior change is allowed without a new approved evaluation.

### Task 9: Close P0 and bounded P1 evidence

**Purpose:** Reconcile final acceptance claims without overstating rejected or deferred work.
**Task Function:** Evidence ledger and status closure.
**Template Profile:** `normal` executor.
**Specification Coverage:** P0/P1 status boundaries; P0-A rejected, P0-C protected, P1-A maintenance-only, P1-B `n=1`, P1-C deferred.
**Required Skills:** `skill-verification-before-completion`.
**Files And Symbols:** `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, `tests/test_acceptance_state.py`, `docs/superpowers/evidence/`, `docs/pipeline.md`, P1-B event owners in `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/worker_job.py`, and `src/fitcv_cp/app.py`.
**Dependencies:** Task 8.
**Authority:** Saved protected-run evidence, source/tests, and acceptance-state schema.
**Steps:**
1. Record P0-A as rejected negative experiment; do not relabel it as P0-B failure.
2. Record P0-B only from the single corrected evaluator output and frozen thresholds, or preserve blocked status with its reason.
3. Record P0-C as protected until mandatory-constraint verification and pair truth pass.
4. Keep P1-A maintenance-only and P1-B measurement-only at `n=1`; add only missing durable normal-use fields owned by existing event contracts.
5. Mark P1-C and P2 deferred with no implementation claims.
**Verification:** Validate acceptance-state schema, evidence links, status consistency, and unsupported claims; run focused P1 artifact-contract tests and final repository checks.
**Exit Criteria:** Machine-owned state and evidence agree; every P0/P1 item has explicit status, proof, owner, and next condition.

## Verification

Run in order after implementation:

1. `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_p0b_holdout_review.py tests/test_p0b_support_oracle.py tests/test_acceptance_state.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py tests/test_cv_render_acceptance.py`.
2. Run the exact oracle build/validate commands from Task 4; assert independent-label provenance, complete bounded coverage, stable hashes, and conservation totals.
3. Run CI-equivalent commands from clean checkout or clean exported tree, including non-render and render acceptance paths.
4. Validate saved Task 8 evaluator, oracle, manifest, evidence, and acceptance-state artifacts; do not rerun protected evaluation.
5. Run `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json` and validate `artifacts/acceptance_state.json` against its schema.
6. Run `git diff --check`, inspect `git status --short`, and confirm protected untracked files remain unmodified and unstaged.
7. Use `skill-verification-before-completion` to reconcile plan ledger, evidence paths, acceptance state, and completion claims. No final status is `completed` without fresh passing evidence.

## Completion Criteria

- Mandatory constraints are represented and verified fail closed; aliases do not prove support alone.
- P0-B eligibility fails on pair false positives, unresolved required review, invalid records, or failed frozen support thresholds.
- `6/143` relevance recall is diagnostic only and cannot promote P0-B.
- Full-pool oracle output is bounded, sanitized, deterministic, and distinguishes pool absence from retrieval loss.
- Calibration categories are exhaustive and disjoint over judged pairs and match actual pipeline stages.
- Clean-checkout CI passes without private local packets or ignored generated artifacts.
- One final protected corrected P0-B run is reproducible from admitted sanitized inputs, independent oracle labels, frozen thresholds, and linked evidence; if admission remains incomplete, blocked status is explicit and promotion is false.
- No protected result is rerun after Task 8 or used to tune later behavior; any later behavior change invalidates closure.
- P0-A remains rejected; P0-C closes only on verified support; P1-A remains maintenance-only; P1-B remains measurement-only at `n=1`; P1-C and P2 remain deferred.
- Only measured optimization ships. No speculative embeddings, reranker, LLM verifier, graph, service, datastore, or global `top_k` expansion appears.
- Acceptance state, evidence records, tests, docs, fixtures, and generated public corpus outputs agree with one canonical source each.
