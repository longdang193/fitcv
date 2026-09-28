---
layer: change
artifact_type: plan
status: blocked
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-residual-completion
targets:
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - data/fitcv-p0-corpus/p0a/ranking_source_backed.json
  - data/fitcv-p0-corpus/p0a/admission_report.json
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json
  - tests/fixtures/requirement_support_benchmark.json
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_ranking_evaluation.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/evidence/2026-09-28-fitcv-p0-p1-residual-closeout.md
---

# FitCV P0/P1 Residual Completion Plan

## Review Basis

Supplied verdict is strategically correct but stale against current `main`.

- P0-C runtime work is closed under `requirement-support-v5`; candidate answers
  already use `candidate_resolution` and existing qualifier assessment. Do not
  bump policy version without another semantic change.
- P1-A runtime work exists: `cv_content_plan_v1`, approved-evidence filtering,
  bounded section repair, and trace fields. Remaining gap is measurement.
- P1-B runtime pieces exist: resolution loading, profile/source scoping, worker
  refresh, debug replacement, and queue identity. One permanent end-to-end
  regression is still required.
- P0-B reports bind `fixture_sha256`, and current support validation reports
  `17/17`. Promotion remains blocked by broader reviewed boundary coverage.
- P0-A remains open. `scripts/benchmark_ranking.py` emits a deliberate
  multilingual `not_run`; `src/fitcv/embeddings.py` currently provides a
  deterministic local vector, not a multilingual semantic encoder.

## Goal

Close remaining P0 acceptance gates and produce honest P1 acceptance evidence.
Keep incumbent production defaults unchanged until measured evidence supports a
promotion decision. Leave P1-C, P2, GraphRAG, extra agents, and vector-database
infrastructure deferred.

## Implementation Outcomes

### P0-C evidence and cache correctness

- Candidate answers, profile evidence, and imported evidence retain one
  requirement-support contract.
- Cache reuse proves policy, qualifier-parser, projection, and source identity
  mismatches force fresh analysis under `requirement-support-v5`.

### P0-B reproducible evidence decision

- Reviewed boundary labels cover selection misses, compound requirements,
  aliases, duration, negation, production/context qualifiers, multiple evidence
  items, and unrelated skill text.
- Benchmark artifacts contain commit, script, policy, fixture, dataset, run,
  and pass/fail/not-applicable metadata generated from source files.

### P0-A bounded multilingual retrieval

- One local CPU-capable multilingual adapter uses the existing retrieval shape,
  SQLite storage, contract fingerprinting, and lexical fallback diagnostics.
- Incumbent, lexical, and multilingual arms run on the same mixed-language,
  reviewed, held-out corpus, or produce an explicit unavailable blocker.

### P1 lifecycle and measurement

- One permanent regression proves review answer → stored resolution → worker
  refresh → fresh analysis → fresh generation → debug replacement → queue close.
- Existing P1-A/P1-B traces produce a scorecard distinguishing measured,
  partial, `not_run`, and `not_applicable` metrics.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect and edit declared files, run declared local tests and offline benchmarks, write `.tmp/` reports, and write the residual evidence artifact
- User-approval actions: external provider/model download or authentication, production-default changes, push, merge, publication, destructive cleanup, and discard of unrelated workspace changes
- Parallel ownership: none; evidence IDs, fingerprints, benchmark fixtures, and lifecycle payloads require serialization
- Sequential fallback: execute Tasks 1–6 in order and stop at any required contract or data gate

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `f04761a0`
- Expected workspace: `main` with unrelated untracked `.tmp/` preserved
- Next action: Task 6, final acceptance reconciliation with explicit blockers
- Blockers: reviewed P0-B labels and approved multilingual model artifact are external acceptance inputs; missing inputs keep affected tasks explicitly blocked

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | lifecycle regression command | `826 passed`; focused lifecycle proof |
| Task 2 | `blocked` | current | `codex` | Task 1 | P0-B benchmark artifacts and comparison | reports complete; broader reviewed labels unavailable |
| Task 3 | `blocked` | current | `codex` | Task 2 | multilingual adapter and focused tests | `sentence_transformers`/`torch` unavailable; model not cached |
| Task 4 | `blocked` | current | `codex` | Task 3 | three-arm held-out ranking report | incumbent/lexical measured; multilingual `not_run` |
| Task 5 | `completed` | current | `codex` | Tasks 1–4 | P1 scorecard and focused generation tests | `230 passed`; offline/live metrics separated |
| Task 6 | `blocked` | current | `codex` | Tasks 1–5 | full suite, diff check, closeout evidence | residual closeout written; external blockers remain |

## Task Breakdown

### Task 1: Add Permanent P1-B End-to-End Regression

**Purpose:** Prove one complete review-resolution-refresh lifecycle without
creating another resolution subsystem.

**Task Function:** Extend existing worker/control-plane regression coverage.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded backend lifecycle change with existing helpers and low implementation ambiguity.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused tests and direct state assertions are sufficient.

**Specification Coverage:** P1-B actionable uncertainty loop, identity scoping,
idempotency, stale invalidation, and queue closure.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:_load_requirement_resolutions`, `src/fitcv_cp/worker_job.py:_persist_resolution_reanalysis`, `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:** Existing profile/source-scoped resolution storage and current
`requirement-support-v5` candidate-answer semantics.

**Authority:**
- Preauthorized local actions: edit the two declared test files and run focused local tests
- Stop for: worker/storage contract changes outside declared files, external provider access, or destructive fixture cleanup

**Steps:**
- [x] Step 1: Seed `review_required` for `3 years production SQL` with profile ID, revision, projection fingerprint, and `review_item_id`.
- [x] Step 2: Save `RESOLVE_WITH_ANSWER` containing `4 years production SQL`; assert stored resolution identity and answer payload.
- [x] Step 3: Run existing worker regeneration; assert verified SQL coverage, fresh generation, preserved `review_item_id`, and queue closure after validation.
- [x] Step 4: Repeat action; assert idempotent storage and one bounded refresh.
- [ ] Step 5: Change revision/fingerprint; assert stale resolution is ignored. Cover `CONFIRM_OMIT`, `OVERRIDE_BLOCK`, contradiction, and malformed rows.

**Verification:**
- [x] `py -3.13 -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py` — `826 passed`
- Expected: one test trace proves storage row, worker load, fresh analysis, fresh generation, debug replacement, and queue state.

**Exit Criteria:** End-to-end lifecycle passes; stale, contradictory, duplicate,
and malformed paths fail closed without duplicate refresh.

### Task 2: Close P0-B Reviewed Evidence and Artifact Contract

**Purpose:** Make support benchmark claims reproducible and promotion-grade.

**Task Function:** Extend reviewed fixtures, manifests, benchmark metadata, and
comparison validation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: deterministic benchmark and data-contract work with existing arm registry.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing benchmark and public-corpus tests cover artifact integrity.

**Specification Coverage:** P0-B boundary labels, qualified support metrics,
fixture provenance, and retain/promote decision.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:run_benchmark`, `scripts/compare_requirement_support.py`, `tests/fixtures/requirement_support_benchmark.json`
- Modify: `data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl`, `data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json`, `tests/fixtures/requirement_support_benchmark.json`, `scripts/benchmark_requirement_support.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, and `tests/test_p0_public_corpus.py`
- Verify: `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, `tests/test_p0_public_corpus.py`

**Dependencies:** Task 1 complete; labels must be human-reviewed or explicitly
recorded as unavailable. Do not infer labels from model output.

**Authority:**
- Preauthorized local actions: edit reviewed fixtures/manifests, extend benchmark metadata, run offline benchmark commands, and write `.tmp/` reports
- Stop for: missing review authority, external data access, production behavior changes, or stale fixture provenance

**Steps:**
- [ ] Step 1: Add reviewed cases for selection misses, compound requirements, aliases, duration, negation, production/context qualifiers, multiple evidence items, and unrelated skill text.
- [ ] Step 2: Recompute P0-B manifest SHA-256 from exact fixture bytes and reject stale hashes in tests.
- [x] Step 3: Add `commit_sha`, benchmark script hash, policy version, fixture hash, dataset size, arm, run counts, and pass/fail/skipped/not-applicable counts to generated reports.
- [x] Step 4: Generate production, full-pool, and lexical-only outputs and one machine-readable comparison artifact.
- [x] Step 5: Retain production behavior; make no semantic deletion or promotion without reviewed held-out evidence.

**Verification:**
- [x] `py -3.13 -m pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py` — `98 passed`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/p0b-production-residual.json`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm full_pool_diagnostic --runs 50 --warmups 5 --output .tmp/p0b-full-pool-residual.json`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm lexical_only --runs 50 --warmups 5 --output .tmp/p0b-lexical-only-residual.json`
- Expected: reports reproduce from metadata; support never borrows qualifiers across evidence; no promotion claim uses fixture assumptions.

**Exit Criteria:** Reviewed boundary coverage and machine-generated artifacts
support a bounded retain/promote decision.

### Task 3: Implement One Bounded Multilingual Retrieval Adapter

**Purpose:** Replace the benchmark-only multilingual stub with one bounded local
semantic backend while preserving retrieval contracts.

**Task Function:** Extend existing embedding and vector-search adapters.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: one narrow backend integration; no new orchestration or storage service.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused adapter, cache, fallback, and contract tests are sufficient.

**Specification Coverage:** P0-A multilingual implementation, cache identity,
fallback diagnostics, and unchanged production defaults.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:build_embedding_contract_fingerprint`, `src/fitcv/embeddings.py:generate_embedding`, `src/fitcv/vector_search.py:run_vector_search`, `scripts/benchmark_ranking.py:main`
- Modify: `src/fitcv/embeddings.py`, `src/fitcv/vector_search.py`, `scripts/benchmark_ranking.py`, `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_ranking_evaluation.py`
- Verify: existing SQLite embedding tables and retrieval diagnostics

**Dependencies:** Task 2 fixture contract. Use
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; pin its model
revision before coding. If approval or local loading is unavailable, retain the
explicit `not_run` blocker and do not claim implementation completion.

**Authority:**
- Preauthorized local actions: edit declared adapter/benchmark/test files, run local tests, and write offline reports
- Stop for: model download/authentication, new dependency approval, production-default changes, or vector-database infrastructure

**Steps:**
- [ ] Step 1: Add lazy optional backend loading and explicit unavailable diagnostics; leave incumbent and lexical defaults unchanged.
- [ ] Step 2: Extend embedding contract fingerprint with backend ID, model revision, preprocessing version, and dimension.
- [ ] Step 3: Reuse SQLite embedding storage; invalidate cache when job-content hash, model revision, preprocessing version, or dimension changes.
- [ ] Step 4: Route the benchmark `multilingual` arm through the adapter and preserve lexical fallback diagnostics.
- [ ] Step 5: Add bilingual, cache-reuse, invalidation, unavailable-backend, and fallback tests.

**Verification:**
- [ ] `uv run pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_ranking_evaluation.py`
- Expected: adapter preserves result shape, cache identity, fallback behavior, and production default strategy.

**Exit Criteria:** Multilingual backend is measured or remains explicitly
`not_run` with a precise provider/data blocker.

### Task 4: Produce P0-A Promotion Evidence

**Purpose:** Evaluate incumbent, lexical, and multilingual retrieval on reviewed
German/English held-out data.

**Task Function:** Expand corpus admission and run three-arm ranking benchmark.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded offline evaluation with existing ranking harness.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: ranking and public-corpus tests validate metrics and hashes.

**Specification Coverage:** P0-A reviewed corpus, language split metrics,
quality/cost metrics, and no-premature-promotion rule.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_ranking.py:_run_once`, `scripts/benchmark_ranking.py:_split_metric_rows`, `tests/test_ranking_evaluation.py`
- Modify: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`, `data/fitcv-p0-corpus/p0a/admission_report.json`, and ranking benchmark tests only when schema requires it
- Verify: generated `.tmp/p0a-*.json` reports and public corpus hash checks

**Dependencies:** Task 3 adapter result and reviewed corpus input. If reviewed
100–300-job mixed-label corpus is unavailable, record the data blocker and do
not fabricate labels.

**Authority:**
- Preauthorized local actions: edit reviewed offline fixtures, recompute manifests, run deterministic ranking benchmarks, and write evidence reports
- Stop for: provider authentication, unreviewed labels, production strategy changes, or unsupported quality claims

**Steps:**
- [ ] Step 1: Admit 100–300 reviewed German and English jobs with relevant, borderline, and irrelevant labels plus calibration/held-out splits.
- [ ] Step 2: Recompute every published-file SHA-256 in `admission_report.json`.
- [ ] Step 3: Run incumbent, lexical, and multilingual arms with identical fixture, warmup, and measured iteration counts.
- [ ] Step 4: Record Recall@12, Precision@12, nDCG@12, language-split quality, cold/warm p50/p95, fallback count, embedding time, memory, and index size.
- [ ] Step 5: Retain incumbent unless approved thresholds show a safer multilingual promotion; do not change production defaults in this plan.

**Verification:**
- [ ] `uv run pytest -q tests/test_ranking_evaluation.py tests/test_p0_public_corpus.py`
- [ ] `uv run python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --arm incumbent --warmup-iterations 5 --measured-iterations 30 --output .tmp/p0a-incumbent-residual.json`
- [ ] `uv run python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --arm lexical --warmup-iterations 5 --measured-iterations 30 --output .tmp/p0a-lexical-residual.json`
- [ ] `uv run python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --arm multilingual --warmup-iterations 5 --measured-iterations 30 --output .tmp/p0a-multilingual-residual.json`
- Expected: all reports share fixture hash, schema, run counts, and split definitions; unavailable arms state exact reasons.

**Exit Criteria:** P0-A has a measured decision report or explicit data/provider
blocker. No unsupported multilingual quality claim remains.

### Task 5: Reconcile P1 Measurement Without Expanding Runtime Scope

**Purpose:** Turn existing P1-A/P1-B trace fields into an honest scorecard.

**Task Function:** Aggregate existing generation, repair, resolution, and queue
observations without adding telemetry architecture.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing trace payloads and focused runtime tests already own the data.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused generation and pipeline tests prove approved-evidence filtering and bounded repair.

**Specification Coverage:** P1-A context reduction and repair, P1-B resolution
reuse and manual actions, and truthful unavailable-metric handling.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `src/fitcv/agentic_cv_generation.py:merge_repaired_section`, `src/fitcv/agentic_cv_analysis.py:_build_cv_analysis_trace_record`, `src/fitcv_cp/worker_job.py:_build_cv_generation_debug_payload`
- Modify: only missing scorecard aggregation and its tests; do not change `cv_content_plan_v1` or add a telemetry subsystem
- Verify: `tests/test_cv_generator.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_pipeline.py`, `tests/test_cv_generation_reason_mapping.py`

**Dependencies:** Tasks 1–4 runtime and benchmark results.

**Authority:**
- Preauthorized local actions: edit declared scorecard/test files, run focused local tests, and record `not_run` or `not_applicable` metrics
- Stop for: live provider access, new telemetry infrastructure, page-budget optimization, or unrelated generation behavior changes

**Steps:**
- [x] Step 1: Report approved/full evidence items, characters, and estimated tokens.
- [x] Step 2: Report generation latency, provider calls, input/output tokens, retries, full/section repairs, and factual-preservation results.
- [x] Step 3: Report review actions, resolution reuse, questions avoided, and accepted-CV rate when live data exists; otherwise record exact unavailable status.
- [x] Step 4: Keep primary KPI as time and human actions per accepted truthful CV.

**Verification:**
- [ ] `uv run pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_cv_generation_reason_mapping.py`
- Expected: scorecard distinguishes measured, partial, `not_run`, and `not_applicable` without changing runtime contracts.

**Exit Criteria:** P1 scorecard is reproducible from existing traces and clearly
separates offline proof from unavailable live/provider evidence.

### Task 6: Final Acceptance Reconciliation

**Purpose:** Reconcile implementation, benchmark, test, blocker, rollback, and
deferred-scope evidence into one closeout artifact.

**Task Function:** Final verification and evidence publication inside repository.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: repository-wide acceptance judgment after all producer tasks.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final commands and evidence artifact provide fresh proof.

**Specification Coverage:** P0/P1 completion status, honest blockers, rollback,
and explicit P1-C/P2 deferral.

**Required Skills:** `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/superpowers/evidence/2026-09-28-fitcv-p0-p1-closeout.md`, `docs/superpowers/plans/2026-09-28-fitcv-p0-p1-finalization-plan.md`, `.tmp/p0a-incumbent-residual.json`, `.tmp/p0a-lexical-residual.json`, `.tmp/p0a-multilingual-residual.json`, `.tmp/p0b-production-residual.json`, `.tmp/p0b-full-pool-residual.json`, and `.tmp/p0b-lexical-only-residual.json`
- Modify: `docs/superpowers/evidence/2026-09-28-fitcv-p0-p1-residual-closeout.md`
- Verify: repository test suite, hashes, Git state, and plan status

**Dependencies:** Tasks 1–5 complete or explicitly recorded as blocked with
source evidence.

**Authority:**
- Preauthorized local actions: run final local checks and write the residual evidence artifact
- Stop for: failed required checks, stale hashes, unrecorded scope deviation, production-default mutation, or unrelated workspace cleanup

**Steps:**
- [x] Step 1: Record current commit, fixture hashes, policy version, exact commands, results, blockers, and rollback path.
- [x] Step 2: Record P1-C/P2/GraphRAG/extra-agent/vector-database deferrals.
- [x] Step 3: Run final verification; retain blocked status because required external acceptance inputs remain unresolved.

**Verification:**
- [x] `py -3.13 -m pytest -q` — `2869 passed, 4 skipped, 52 warnings`
- [x] `git diff --check` — clean
- [x] `git status --short --branch` — inspected; `.tmp/` and `.venv/` preserved
- Expected: required tests pass; every measured claim maps to an artifact; blockers and unavailable metrics remain explicit.

**Exit Criteria:** Final evidence supports every claimed P0/P1 outcome, no
required task is silently skipped, and no production promotion is implied.

## Verification

Final artifact-level verification only:

- `uv run pytest -q`
- `git diff --check`
- `git status --short --branch`
- Inspect `docs/superpowers/evidence/2026-09-28-fitcv-p0-p1-residual-closeout.md` against generated benchmark JSON and exact fixture bytes.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-C cache and candidate-answer regressions pass under `requirement-support-v5`.
2. P0-B reviewed boundary evidence and artifact metadata reproduce from source fixtures.
3. P0-A has measured multilingual evidence or a precise data/provider blocker.
4. P1-B has one permanent end-to-end lifecycle regression.
5. P1-A/P1-B scorecard separates measured, partial, `not_run`, and `not_applicable` metrics.
6. No production default, external provider, or deferred feature changes without separate approval.
7. `skill-verification-before-completion` returns `verified` before plan status changes to `completed`.

## Rollback

Disable multilingual strategy and retain incumbent retrieval. Keep existing
P0-C/P1-A/P1-B runtime paths unchanged. If benchmark metadata or reviewed
fixtures fail, restore prior fixture bytes from Git and discard only residual
`.tmp/` reports; do not weaken validation to make reports green.
