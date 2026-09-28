---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-post-pr70-next-steps
targets:
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json
  - tests/fixtures/requirement_support_benchmark.json
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - docs/superpowers/evidence/2026-09-28-fitcv-post-pr70-next-steps.md
---

# FitCV Post-PR #70 Next Steps Plan

## Review Basis

The supplied review has correct direction but mixes current facts with stale
pre-PR #70 observations.

- P0-A is no longer an all-positive 50-job benchmark. Current source-backed
  corpus has 100 reviewed rows, 50 German, 50 English, 80 calibration, 20
  held-out, and relevance grades 1 and 3. Re-run remains required after cache
  correction; do not promote multilingual retrieval from equal-quality,
  slower results.
- P0-C candidate-answer evidence already uses `candidate_resolution` and
  `requirement-support-v5` qualifier assessment. No policy bump is planned.
- Embedding fallback cache identity defect remains valid. Requested
  `sentence_transformers` contract can be used to persist a deterministic
  fallback vector, so encoder recovery can reuse a vector produced by a
  different backend.
- P1-A compiler paths and scorecard fields exist. Live accepted-CV economics
  remain unavailable without an authorized provider/operator workload.
- P1-B storage, queue, and worker refresh paths exist. Existing residual plan
  still leaves stale-resolution, contradiction, omit, override, and malformed
  row regression coverage incomplete.
- P0-B promotion remains blocked by reviewed-boundary coverage and provenance;
  labels must come from an approved human review source, not model output.
- GraphRAG, extra agents, new embedding models, vector databases, and
  speculative orchestration remain out of scope.

## Plan Relationship

This plan is the sole execution ledger for post-PR #70 next steps. Earlier
completed or blocked plans remain historical evidence; do not execute their
overlapping tasks as a second workstream. Reconcile any accepted work here and
preserve prior plan status and evidence history.

## Goal

Close remaining trust and acceptance gaps after PR #70 without changing
production retrieval defaults or adding architecture. Make fallback vectors
cache-safe, prove the remaining uncertainty failure paths, rerun reproducible
benchmarks, and record honest promotion and live-economics blockers.

## Implementation Outcomes

### Cache-safe embedding contract

Embedding rows and candidate-query rows persist the contract of the backend
that produced the vector. A deterministic fallback never occupies a
`sentence_transformers` cache identity. Encoder recovery ignores prior fallback
rows and generates a fresh multilingual vector.

### Fail-closed uncertainty lifecycle

One permanent regression covers stale identity, contradiction, `CONFIRM_OMIT`,
`OVERRIDE_BLOCK`, duplicate action, malformed resolution, refresh failure, and
successful queue closure. Resolved state appears only after fresh validation.

### Reproducible acceptance evidence

P0-A reports compare incumbent, lexical, and multilingual arms on the current
 100-row mixed-language corpus with held-out metrics and backend diagnostics.
P0-B reports remain benchmark-only until approved reviewed labels expand
boundary coverage and exact fixture provenance passes.

### Explicit deferral

Accepted-CV economics remain `not_run` or `not_applicable` without authorized
live provider/operator data. P1-C, P2, GraphRAG, extra agents, and vector
database work receive no implementation task.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-verification-before-completion`, `skill-plan-document-reviewer`
- Isolation: `current workspace`
- Commit policy: `verified per-task checkpoint commits preauthorized; no push, merge, publication, or implementation-lane commits during execution`
- Preauthorized local actions: inspect and edit declared files, run declared Windows-native tests and offline benchmarks, write `.tmp/` reports, update the declared evidence artifact, and create one accepted task checkpoint commit containing task changes plus ledger state
- User-approval actions: external provider download or authentication, human-label collection, production-default changes, push, merge, publication, destructive cleanup, and discard of unrelated `.tmp/` or `.venv/` files
- Parallel ownership: none; embedding identity, lifecycle evidence, benchmark metadata, and final evidence share acceptance state
- Sequential fallback: Task 1 → Task 2 → Task 3 → Task 4; stop at first unresolved trust or provenance gate

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `ad4a9e11`
- Expected workspace: current `main`; preserve unrelated untracked `.tmp/` and `.venv/`
- Next action: preserve evidence; no further execution planned
- Blockers: approved human-reviewed P0-B boundary labels and authorized live accepted-CV workload are unavailable

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | fallback cache regression | `60 passed, 2 skipped` |
| Task 2 | `completed` | current | `codex` | Task 1 | uncertainty lifecycle regression | `832 passed` |
| Task 3 | `completed` | current | `codex` | Task 1 | three-arm P0-A reports and P0-B gate | P0-A unchanged; P0-B blocked |
| Task 4 | `completed` | current | `codex` | Tasks 1–3 | final tests, evidence, blockers | `2882 passed, 4 skipped`; diff clean |

## Task Breakdown

### Task 1: Separate Fallback Embedding Cache Identity

**Purpose:**
- Prevent deterministic fallback vectors from being stored or reused as
  multilingual vectors.

**Task Function:**
- Repair actual-backend identity propagation through embedding persistence and
  vector-search diagnostics.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: narrow backend contract change with direct cache and failure
  regression proof.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused embedding/vector-search tests assert persisted rows,
  contract fingerprints, and recovery behavior.

**Specification Coverage:**
- Supplied review section “Multilingual backend fallback issue”.
- Preserve deterministic fallback availability while separating its identity
  from `sentence_transformers`.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:build_embedding_contract_fingerprint`, `src/fitcv/embeddings.py:generate_embedding`, `src/fitcv/embeddings.py:embed_and_store_jobs`, `src/fitcv/vector_search.py:build_candidate_query_embedding_contract_fingerprint`, `src/fitcv/vector_search.py:run_vector_search`
- Modify: `src/fitcv/embeddings.py`, `src/fitcv/vector_search.py`, `tests/test_embeddings.py`, `tests/test_vector_search.py`
- Verify: SQLite `job_embeddings` and `candidate_query_embeddings` rows created by isolated test state

**Dependencies:**
- Current `embedding_contract_fingerprint` fields and SQLite schema remain the
  persistence owner.
- Do not add a cache service, provider, model, or new storage table.

**Authority:**
- Preauthorized local actions: edit declared embedding/vector-search files and focused tests; run isolated local SQLite tests
- Stop for: schema replacement, external model download, production default change, or unrelated workspace cleanup

**Steps:**
- [x] Step 1: Add failing regression for encoder unavailable → fallback row written → encoder restored → fresh multilingual vector generated; assert fallback and real-vector contracts differ.
- [x] Step 2: Propagate actual vector backend metadata into job and candidate-query cache keys without changing lexical fallback behavior.
- [x] Step 3: Mark fallback diagnostics with deterministic backend identity and retain requested/effective strategy distinction.
- [x] Step 4: Assert incompatible fallback rows are ignored, compatible real rows are reused, vector dimensions remain valid, and `embedding_failure_policy: raise` still fails closed.

**Verification:**
- [x] `py -3.13 -m pytest -q tests/test_embeddings.py tests/test_vector_search.py`
- Expected: fallback recovery regression passes; no fallback row matches the multilingual contract; existing lexical and raise-policy tests remain green.

**Exit Criteria:**
- Cache identity represents vector producer, recovery never reuses fallback as multilingual, and focused backend tests pass.

### Task 2: Finish P1-B Uncertainty Failure-Path Regression

**Purpose:**
- Prove existing review-resolution storage and worker refresh behavior across
  every remaining fail-closed branch.

**Task Function:**
- Extend current control-plane lifecycle regression; change runtime code only
  where the new regression exposes a real contract defect.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing worker and SQLite owners are known; proof gap is
  bounded.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct persistence, worker, analysis, and queue assertions
  cover the boundary.

**Specification Coverage:**
- Supplied review section “P1-B: uncertainty workflow”.
- Preserve profile/source/revision scoping, idempotency, and queue closure only
  after successful fresh validation.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:_load_requirement_resolutions`, `src/fitcv_cp/worker_job.py:_persist_resolution_reanalysis`, `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`, `src/fitcv_cp/app.py:admin_run_cv_review_action`, `src/fitcv_cp/sqlite_store.py:requirement_resolutions`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`; modify runtime owners only when a focused failing test proves defect
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_cv_generation_reason_mapping.py`

**Dependencies:**
- Task 1 complete.
- Current `requirement-support-v5` candidate-answer semantics remain unchanged.

**Authority:**
- Preauthorized local actions: edit declared lifecycle tests and bounded runtime owners, run SQLite/API/worker checks, and write local test evidence
- Stop for: schema replacement, implicit auto-approval, external provider access, or state marked resolved before refreshed validation

**Steps:**
- [x] Step 1: Seed one `review_required` item with profile ID, revision, source/projection fingerprint, uncertainty ID, and `review_item_id`.
- [x] Step 2: Cover `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, and `OVERRIDE_BLOCK`; assert stored resolution identity, claim omission/continuation semantics, and no fabricated support.
- [x] Step 3: Change revision or source fingerprint; assert stale resolution is ignored. Add contradiction and malformed-row cases; assert fail-closed status.
- [x] Step 4: Repeat action; assert idempotent storage and one bounded refresh. Force refresh failure; assert queue remains open and state is not `resolved`.
- [x] Step 5: Complete successful refresh; assert fresh analysis, fresh generation, debug replacement, preserved uncertainty identity, and queue closure.

**Verification:**
- [x] `py -3.13 -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py`
- Expected: lifecycle passes for success and all failure paths; duplicate actions do not duplicate refresh; resolved state follows validation only.

**Exit Criteria:**
- One permanent regression proves review answer → stored resolution → worker refresh → fresh analysis/generation → debug replacement → queue close, with every stale or invalid branch fail-closed.

### Task 3: Reproduce Retrieval Evidence and Hold P0-B Promotion Gate

**Purpose:**
- Re-run current P0-A evidence after Task 1 and record the exact production
  decision without promoting a slower or equal-quality backend.

**Task Function:**
- Deterministic benchmark execution and evidence reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing benchmark scripts and admitted corpus provide the
  required offline boundary.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark metadata, fixture hashes, and focused benchmark
  tests provide reproducibility.

**Specification Coverage:**
- Supplied review sections “P0-A benchmark does not measure retrieval quality”
  and “Required benchmark design”.
- Current corpus already supplies mixed language, labels, calibration, and
  held-out rows; do not replace it with synthetic all-positive data.

**Required Skills:**
- `skill-performance-optimization`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/benchmark_ranking.py`, `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`, `data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json`
- Modify: `docs/superpowers/evidence/2026-09-28-fitcv-post-pr70-next-steps.md`; modify P0-B data and benchmark files only after approved reviewed labels arrive
- Verify: `tests/test_ranking_evaluation.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, `tests/test_p0_public_corpus.py`

**Dependencies:**
- Task 1 complete for cache-safe multilingual measurements.
- P0-B label expansion requires approved human review and source provenance;
  model-generated labels do not satisfy this task.

**Authority:**
- Preauthorized local actions: run offline benchmarks, compare generated reports, inspect hashes, and write evidence with explicit blocked status
- Stop for: missing label authority, stale fixture hash, external data access, production retrieval promotion, or benchmark result mutation to force green status

**Steps:**
- [x] Step 1: Run incumbent, lexical, and multilingual arms against `data/fitcv-p0-corpus/p0a/ranking_source_backed.json` with 5 warmups and 50 measured iterations; retain exact backend, model, revision, dimension, fallback, latency, Recall@K, Precision@K, and nDCG@K.
- [x] Step 2: Compare calibration and held-out results; retain incumbent production defaults unless multilingual quality improves without unacceptable latency or fallback risk.
- [x] Step 3: Re-run P0-B production, full-pool diagnostic, and lexical-only reports with exact fixture and script hashes. Keep `promotion_blocked` while the manifest records only three approved seed pairs and broader boundary coverage remains absent.
- [ ] Step 4: When approved reviewed labels exist, add only source-backed cases for selection misses, compound requirements, aliases, duration, negation, production/context qualifiers, multiple evidence items, and unrelated skill text; recompute manifest hash and rerun comparisons.

**Performance Contract:**
- Baseline: current incumbent arm and `docs/superpowers/evidence/2026-09-28-fitcv-p0-p1-closeout.md` residual measurements.
- Workload: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`, 100 reviewed rows, 2 profile arms, 5 warmups, 50 measured iterations, Windows-native `py -3.13`, local CPU, pinned multilingual model revision when available.
- Primary metrics: held-out Recall@12, Precision@12, and nDCG@12. Secondary metrics: latency p50/p95, fallback count, and backend contract identity.
- Threshold owner: no latency promotion threshold is authorized by this plan; product acceptance owner must approve any threshold in a separate decision before production default change.
- Regression proof: three-arm reports, fixture/script hashes, focused benchmark tests, and unchanged incumbent default.

**Verification:**
- [x] `py -3.13 scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --arm incumbent --warmup-iterations 5 --measured-iterations 50 --output .tmp/post-pr70-p0a-incumbent.json`
- [x] Repeat command with `--arm lexical` and `--arm multilingual`, changing only `--output`.
- [x] `py -3.13 scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/post-pr70-p0b-production.json`
- [x] Repeat P0-B command with `--arm full_pool_diagnostic` and `--arm lexical_only`, changing only `--output`.
- [x] `py -3.13 scripts/compare_requirement_support.py --inputs .tmp/post-pr70-p0b-production.json,.tmp/post-pr70-p0b-full-pool.json,.tmp/post-pr70-p0b-lexical-only.json --output .tmp/post-pr70-p0b-comparison.json`
- Expected: reports contain exact hashes and split metrics; P0-A decision is reproducible; P0-B remains blocked unless approved coverage and provenance pass.

**Exit Criteria:**
- Current P0-A result is decision-grade and evidence-backed; P0-B promotion status matches reviewed coverage, with no production default change.

### Task 4: Final Evidence, Economics Boundary, and Deferral Reconciliation

**Purpose:**
- Publish one post-PR #70 acceptance record that separates measured offline
  value from unavailable live economics and records rollback/deferral rules.

**Task Function:**
- Final plan/evidence reconciliation after producer tasks.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final artifact must reconcile code, reports, tests, blockers,
  and deferred scope.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final commands and evidence inspection cover acceptance state.

**Specification Coverage:**
- Supplied review sections “Measure accepted CV economics” and “Avoid these
  next”.
- Record elapsed time, provider calls, token data, regeneration, manual review,
  and accepted truthful CV denominator only when live evidence exists.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/llm_runtime.py`, `src/fitcv_cp/app.py`, `docs/observability.md`, `.tmp/post-pr70-p0a-*.json`, `.tmp/post-pr70-p0b-*.json`
- Modify: `docs/superpowers/evidence/2026-09-28-fitcv-post-pr70-next-steps.md`
- Verify: repository tests, report hashes, Git state, and exact blocker wording

**Dependencies:**
- Tasks 1–3 complete or explicitly blocked with source evidence.
- No live provider/operator workload is authorized in this plan.

**Authority:**
- Preauthorized local actions: run final local checks, inspect generated reports, and write the declared evidence artifact
- Stop for: stale report hashes, failed required tests, unrecorded scope deviation, external data egress, or unrelated workspace cleanup

**Steps:**
- [x] Step 1: Record current commit, fixture hashes, embedding contract fields, benchmark commands, test results, and production decision.
- [x] Step 2: Record P0-C as closed under current tests, P0-B as promotion-blocked when coverage remains insufficient, and P1-B lifecycle result.
- [x] Step 3: Record P1-A/P1-B economics as measured, partial, `not_run`, or `not_applicable` from existing traces; do not invent accepted-CV denominator or provider cost.
- [x] Step 4: Record rollback: disable multilingual strategy, retain incumbent retrieval, preserve P0-C/P1-A/P1-B runtime paths, and discard only generated `.tmp/` reports after evidence retention decision.
- [x] Step 5: Run final verification and keep plan status proposed until `skill-verification-before-completion` returns `verified`.

**Verification:**
- [x] `py -3.13 -m pytest -q`
- [x] `git diff --check`
- [x] `git status --short --branch`
- Expected: full suite passes; evidence maps every claim to a report or test; unrelated `.tmp/` and `.venv/` remain preserved; no production promotion is implied.

**Exit Criteria:**
- One evidence artifact reconciles all implementation outcomes, blockers, rollback, and deferrals. Live economics remain explicitly unavailable until separately approved.

## Verification

- `py -3.13 -m pytest -q` → `2882 passed, 4 skipped`
- `py -3.13 -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py` → passed
- `git diff --check` → passed
- `git status --short --branch` → expected source/test/evidence/plan changes; unrelated `.tmp/` and `.venv/` preserved
- Inspect `docs/superpowers/evidence/2026-09-28-fitcv-post-pr70-next-steps.md` against generated `.tmp/post-pr70-*.json` reports and exact fixture bytes.

## Completion Criteria

The plan is ready for completion verification when:

1. fallback and real embedding contracts cannot collide, and recovery ignores fallback rows
2. uncertainty lifecycle regression passes for success and all listed fail-closed paths
3. P0-A reports reproduce current mixed-language held-out metrics and retain incumbent defaults unless an approved decision says otherwise
4. P0-B promotion status matches approved reviewed coverage and exact provenance
5. accepted-CV economics are backed by live evidence or explicitly marked unavailable
6. P1-C, P2, GraphRAG, extra agents, and vector-database work remain deferred
7. rollback and unrelated workspace preservation are recorded
8. `skill-verification-before-completion` returns `verified` before plan status changes to `completed`
