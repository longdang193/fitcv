---
artifact_type: plan
template_id: implementation-plan
name: fitcv-p0-p1-efficiency-completion
contract_version: "1"
status: completed
layer: change
---

# FitCV P0/P1 Efficiency Completion

## Review Basis

- Source review: consolidated FitCV review after `fe093c73`.
- Repository baseline: `main` at `fe093c73`; tracked tree clean. Preserve untracked `.tmp/` and `.venv/`.
- Existing completed plans already cover cache identity, retrieval/evidence foundations, and most uncertainty backend work. This plan must not repeat them.
- Current cache identity contract and regressions live in `src/fitcv/embeddings.py`, `src/fitcv/vector_search.py`, `tests/test_embeddings.py`, and `tests/test_vector_search.py`. Cache rewrite is out of scope.
- Current evidence fragments live in `src/fitcv/evidence.py`; candidate resolution coverage still constructs one answer-wide fragment in `src/fitcv/agentic_cv_analysis.py`.
- `cv_content_plan_v1` already exists in `src/fitcv/agentic_cv_generation.py`; this plan tightens allocation and measurement rather than creating a second compiler.

## Goal

Complete residual P0/P1 acceptance work and reduce human effort per accepted CV without adding services, evaluators, retrieval layers, or duplicate workflow state.

## Implementation Outcomes

### Canonical evidence proof

Candidate answers, profile evidence, and imported evidence use the same support-fragment and qualifier contract. Skill-local qualifiers cannot transfer between skills. False transfer, valid support, and contradiction cases have permanent regression coverage.

### Product-path uncertainty closure

One existing review queue/action path proves generation → review item → candidate answer → persisted resolution → fresh analysis/generation → replacement artifact → review closure. Failed refresh keeps review open; replay is idempotent.

### Measured efficiency loop

Existing run/generation observability reports accepted-CV elapsed time, provider calls, token estimates or usage when available, regeneration count, review-question count, and human-action count. Missing live economics remain explicit `not_run` or `not_applicable`, never fabricated.

### Bounded CV content allocation

Existing `cv_content_plan_v1` deterministically ranks approved evidence, allocates section/page budgets, and limits repair retries. Tests prove fewer unnecessary regeneration calls without weakening grounding or required-section validation.

### Retrieval measurement readiness

P0-A benchmark tooling consumes reviewed relevance labels and reports `Recall@20`, `Precision@20`, `nDCG@10`, and `MRR`. P0-B exposes selected-pool versus full-pool diagnostic results. No multilingual promotion occurs without discriminative labels and measured gain.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-executing-plans`, `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: `edit scoped source/tests/docs, run declared local checks, inspect configured local artifacts, and preserve untracked .tmp/ and .venv/`
- User-approval actions: `push, merge, publication, external provider calls, human-label acquisition, destructive cleanup, or discard`
- Parallel ownership: `none; shared evidence, generation, worker, and run-artifact contracts require ordered edits`
- Sequential fallback: `complete Task 1, then Task 2, then Task 3, then Task 4; keep Task 5 blocked until reviewed benchmark labels exist`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `fe093c73`
- Expected workspace: `clean tracked tree; preserve untracked .tmp/ and .venv/`
- Next action: `supply reviewed job relevance corpus before running Task 5`
- Blockers: `reviewed 500–1000 job relevance corpus and live accepted-CV workload are external inputs; use not_run/not_applicable until supplied`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | focused evidence and analysis tests | `162 passed` |
| Task 2 | `completed` | current | `codex` | Task 1 | worker/API product-path and failure/idempotency tests | `6 passed; existing surfaces sufficient` |
| Task 3 | `completed` | current | `codex` | Task 2 | observability contract tests and no-live-workload handling | `125 passed` |
| Task 4 | `completed` | current | `codex` | Task 3 | generation/compiler budget and bounded-repair tests | `97 passed` |
| Task 5 | `blocked` | current | `codex` | reviewed labels and Task 3 | benchmark metrics plus selected/full-pool comparison | `86 passed, 2 skipped; reviewed corpus absent` |
| Final verification | `completed` | current | `codex` | Tasks 1–4; Task 5 blocked with evidence | full focused suite and plan reconciliation | `885 passed` |

## Task Breakdown

### Task 1: Close P0-C candidate-answer proof boundary

**Task Function:**

Normalize `RESOLVE_WITH_ANSWER` into the existing evidence-fragment contract. Reuse `_build_support_fragments`, `_support_fragments`, and `_assess_requirement_support`; do not create a candidate-answer evaluator. Preserve `REQUIREMENT_SUPPORT_POLICY_VERSION`, evidence IDs, fingerprints, contradiction handling, empty-answer behavior, and fail-closed status semantics.

**Required Skills:**

- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**

- Modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Inspect or modify: `src/fitcv/agentic_cv_analysis.py:_append_resolution_evidence`
- Reuse or minimally adjust: `src/fitcv/evidence.py:_build_support_fragments`, `src/fitcv/evidence.py:_support_fragments`, `src/fitcv/evidence.py:_assess_requirement_support`
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_validator.py`

**Dependencies:**

- None. Existing cache fix remains unchanged.

**Authority:**

- Preauthorized local actions: `edit evidence/analysis code and focused tests; run direct boundary checks`
- Stop for: `new evaluator subsystem, metadata-derived proof, policy bypass, or any qualifier result not explainable by source-scoped fragments`

**Steps:**

- [x] Add failing matrix for `3 years production SQL` against `5 years production Python; SQL classroom exercises`, `4 years production SQL; Python classroom training`, `No SQL experience`, underspecified SQL, and empty answer.
- [x] Convert candidate answer to the same fragment shape used by profile evidence before qualifier assessment.
- [x] Keep only fragments attributed to target skill when qualified requirements are assessed.
- [x] Confirm resolution evidence appended for generation uses identical fragment data and does not donate unrelated qualifiers.
- [x] Retain `requirement-support-v5`; no policy fingerprint bump was needed.

**Verification:**

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py`
- Expected: false transfer is `relevant_unverified`; valid SQL answer is `verified`; explicit negation is `contradicted`; empty answer is `pending`.

**Exit Criteria:**

- Candidate answers and normal evidence reach `_assess_requirement_support` through one fragment contract with regression proof.

### Task 2: Prove P1-B uncertainty through existing product path

**Task Function:**

Exercise existing review queue, resolution action, worker refresh, analysis, generation, and queue-closure owners. Add only missing boundary coverage. Do not create a second review workflow or synchronous shortcut.

**Required Skills:**

- `skill-full-stack-integration`
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**

- Inspect: `src/fitcv_cp/app.py` review queue and requirement-resolution routes
- Inspect: `src/fitcv_cp/worker_job.py` resolution refresh path
- Inspect: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Inspect: `src/fitcv/agentic_cv_generation.py:generate_from_analysis`
- Verify or minimally extend: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:**

- Task 1 must pass so refreshed answers use corrected proof semantics.

**Authority:**

- Preauthorized local actions: `edit existing route/worker contract tests and small missing adapters; run API/client boundary checks`
- Stop for: `new route, new queue, direct database mutation outside existing store, successful closure before fresh validation, or unverified browser-only acceptance`

**Steps:**

- [x] Seed one review-required run with a qualified requirement gap and capture queue payload, resolution ID, profile scope, and source fingerprint.
- [x] Submit candidate answer through existing action route/API; assert persistence and idempotent replay behavior.
- [x] Run worker refresh; assert fresh analysis and generation consume resolution, replacement artifact is stored, and queue item closes only after successful validation.
- [x] Force analysis/refresh failure; assert old artifact remains recoverable and review item stays open with actionable failure state.
- [x] Existing API/worker tests cover displayed requirement, answer action, and terminal status; no browser-only proof substituted.

**Verification:**

- `uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_agentic_cv_analysis.py`
- Expected: success, failure, stale-scope rejection, and idempotent replay are covered.

**Exit Criteria:**

- One real product-path acceptance test proves uncertainty lifecycle from review-required result through validated closure.

### Task 3: Add accepted-CV efficiency measurement to existing observability

**Task Function:**

Extend canonical generation/run trace payloads, not a new metrics service or table. Record fields needed to locate dominant cost: elapsed time, provider call count, token usage or deterministic estimate, regeneration count, review-question count, and human-action count. Preserve redaction and existing artifact contracts.

**Required Skills:**

- `skill-performance-optimization`
- `skill-backend-verification`

**Files And Symbols:**

- Inspect or modify: `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`, `_run_repair_cycle`, `_finalize_generation_result`, `generate_from_analysis`
- Inspect or modify: `src/fitcv_cp/run_artifact_contracts.py` run-attempt payload owner
- Inspect or modify: `src/fitcv_cp/worker_job.py` terminal run/result projection
- Verify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, generation tests covering `cv_generation_trace`

**Dependencies:**

- Task 2 defines review-question and human-action lifecycle events.

**Authority:**

- Preauthorized local actions: `extend existing trace/payload schemas, add deterministic unit tests, run local benchmark commands without live providers`
- Stop for: `new telemetry backend, secret/token content persistence, fabricated live economics, or schema duplication across run and generation layers`

**Steps:**

- [x] Locate one canonical accepted-CV trace owner and add versioned optional fields there.
- [x] Count provider calls and repair/regeneration attempts from existing attempt trace, not from log scraping.
- [x] Carry review-question count from existing analysis uncertainties; human actions remain `not_applicable` at generation boundary.
- [x] Emit `not_run` for live token/provider economics when provider usage is unavailable; retain deterministic input estimates.
- [x] Add backward-compatible trace assertions; existing provider evidence remains redacted.

**Verification:**

- Focused trace/artifact tests named above.
- `uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py`
- Expected: one accepted-CV payload exposes all KPI fields without secrets and old payloads still parse.

**Exit Criteria:**

- Efficiency bottleneck can be identified from stored run evidence; no live workload claim is made without live evidence.

### Task 4: Tighten existing `cv_content_plan_v1` for bounded allocation and repair

**Task Function:**

Use existing content-plan and approved-evidence mechanisms. Make section allocation deterministic from job relevance, evidence strength, business impact, and uniqueness; enforce page/section budgets before provider call; preserve required claims and grounding; cap repair to existing bounded paths. Avoid a separate compiler service.

**Required Skills:**

- `skill-performance-optimization`
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**

- Inspect or minimally modify: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `_run_repair_cycle`, `_determine_repair_targets`
- Inspect or minimally modify: `src/fitcv/cv_generator.py:_supporting_evidence_score`, content-plan prompt assembly, render/validation integration
- Verify: generation and validator tests covering content plan, grounding, required sections, and repair attempts

**Dependencies:**

- Task 3 must expose regeneration count and input-size evidence.

**Authority:**

- Preauthorized local actions: `edit existing content-plan allocation and bounded repair logic; add focused regression tests; run local generation benchmarks`
- Stop for: `new compiler service, unbounded retry, weaker grounding rule, page-layout dependency, or provider call added without measured need`

**Steps:**

- [x] Record baseline counts from current tests/fixture generation: input evidence count, repair attempts, required-section failures, and grounding violations.
- [x] Add deterministic tie-breaking and explicit section/page budget fields to existing `cv_content_plan_v1` only where absent.
- [x] Ensure approved evidence is ranked once and reused by prompt construction and validation; avoid duplicate scoring/retrieval passes.
- [x] Keep repair targets limited to existing repairable fields and stop after current retry cap.
- [x] Compare representative fixture behavior through focused generation and validation tests; no grounding regression observed.

**Verification:**

- `uv run pytest -q tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py`
- Expected: deterministic plan output, no unsupported claims, required sections preserved, and repair count non-increasing on representative fixtures.

**Exit Criteria:**

- Existing content plan produces bounded, deterministic writer input and measurable reduction or no regression in repair work.

### Task 5: Complete P0-A/P0-B measurement only with valid evidence

**Task Function:**

Add or reuse benchmark evaluators for real reviewed data. P0-A consumes 500–1000 jobs with human relevance labels and reports retrieval/ranking metrics separately. P0-B compares selected evidence pool with full-pool diagnostic without changing production selection policy. Keep lexical/incumbent default until measured quality gain exists.

**Required Skills:**

- `skill-performance-optimization`
- `skill-backend-verification`

**Files And Symbols:**

- Inspect/reuse: `scripts/benchmark_ranking.py`, `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`
- Inspect/reuse: `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, retrieval/vector-search tests
- Modify only if needed: benchmark schema/evaluator and existing evidence-selection trace owner

**Dependencies:**

- External reviewed relevance labels block P0-A completion.
- Task 3 provides efficiency fields for P0-B latency/effort comparison.

**Authority:**

- Preauthorized local actions: `add label-schema validation and deterministic benchmark reporting; run fixtures and supplied reviewed corpus`
- Stop for: `synthetic/model-generated labels, multilingual default promotion, new retrieval infrastructure, or production behavior change from benchmark-only evidence`

**Steps:**

- [ ] Define input schema for human labels: relevant, similar-but-wrong, irrelevant, job ID, query/profile ID, and label provenance.
- [ ] Report `Recall@20`, `Precision@20`, `nDCG@10`, and `MRR` with sample counts and missing-label failures.
- [ ] Keep benchmark status `not_run` when corpus or labels are absent; do not infer quality from all-retrieved fixtures.
- [ ] Compare selected evidence pool against full-pool diagnostic for recovered qualified requirements, false claims, review requests, and latency/input size.
- [ ] Leave lexical/incumbent production path unchanged unless accepted thresholds and reviewed evidence support promotion.

**Verification:**

- Existing benchmark and comparison tests.
- `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_vector_search.py`
- Expected: invalid/missing label data fails closed; valid reviewed data produces all four metrics; no production default changes without a recorded decision.

**Exit Criteria:**

- P0-A is either measured on reviewed data or explicitly blocked with `not_run`; P0-B has selected/full-pool evidence comparison without retrieval expansion.

## Verification

### Focused proof

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py`
- `uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_artifact_mirror.py`
- `uv run pytest -q tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_vector_search.py tests/test_embeddings.py`
- `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`

### Contract checks

- Confirm `fe093c73` cache identity tests remain green; no cache rewrite enters diff.
- Confirm `requirement-support-v5` and all fingerprint invalidation behavior remain consistent unless Task 1 proves a contract change.
- Confirm old run artifacts deserialize and new trace fields are optional/backward-compatible.
- Confirm failure paths retain review state and recoverable prior artifact.

### Efficiency proof

- Run representative local generation fixtures before and after Task 4.
- Record input character/token estimates, provider-call count when mocked, repair/regeneration count, validation failures, and review actions.
- Report live accepted-CV economics as `not_run` when no authorized workload/provider is available.

## Completion Criteria

- [x] P0-C candidate-answer proof boundary closed with false-transfer, valid, contradiction, underspecified, and empty-answer tests.
- [x] P1-B existing product path proves persisted resolution, fresh recomputation, successful closure, failure retention, and idempotent replay.
- [x] Accepted-CV efficiency fields live in one existing trace/artifact contract and remain backward-compatible.
- [x] `cv_content_plan_v1` allocates deterministically and keeps repair bounded without grounding regression.
- [x] P0-A benchmark is marked `not_run` with missing reviewed-corpus blocker; no synthetic labels used.
- [x] P0-B existing selected/full-pool comparison tests pass without changing production retrieval policy.
- [x] Focused verification passes; unrelated failures were not changed.
- [x] Plan ledger, evidence, deviations, and blockers reconcile before branch disposition.
