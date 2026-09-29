---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
distribution_tier: starter_kit
name: fitcv-remaining-findings
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/embeddings.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - scripts/benchmark_ranking.py
  - tests/test_vector_search.py
  - tests/test_embeddings.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0_public_corpus.py
  - docs/superpowers/evidence/2026-09-29-fitcv-remaining-findings.md
---

# FitCV Remaining Findings

## Goal

Close remaining implementation defects after `c17fa9e1`, then produce valid
product-flow and measurement evidence. Do not claim P0 promotion or efficiency
gains without discriminating labels, protected holdout, comparable workload,
and linked accepted-CV evidence. Reuse existing owners; add no new services,
schemas, retry systems, or benchmark infrastructure.

## Implementation Outcomes

### Reuse and freshness

Identical candidate-query embedding requests generate once, reuse on the second
call, and persist one row. Lookup and insertion use one canonical backend/model
contract while preserving existing sentence-transformer fallback/recovery
behavior. Corrected requirement-support semantics invalidate old reusable
analysis records and recompute coverage.

### Complete review journey

Uncertainties survive generation into the ordinary review queue. Operator can
enter an answer, persist resolution, trigger fresh analysis/generation, observe
replacement-artifact behavior, and close only after successful resolution.
Failed refresh keeps review pending. Replay stays idempotent.

### Requirement coverage and fit proof

`cv_content_plan_v1` prioritizes marginal coverage of uncovered verified
requirements before score/tie-break ordering. Unique SQL evidence cannot be
dropped for redundant Python claims. `page_count: 1` is metadata only until
existing renderer/validator evidence proves one-page output.

### Honest evaluation and efficiency

P0-A/P0-B evaluation rejects all-positive or order-destroying fixtures,
preserves incumbent default when evidence does not discriminate, and emits
reproducible reports with exact blockers. Accepted-CV effort links existing run
events to one accepted artifact; input/output token fields appear when already
available; unavailable live economics remain `not_run`.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-executing-plans`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve unrelated `.tmp/` and `.venv/`
- Commit policy: `no commits during execution`; Git disposition only after fresh verification and explicit user instruction
- Preauthorized local actions: source/history/test inspection, focused regression tests, edits to listed files, local SQLite/app/browser probes, configured test/benchmark commands, and `not_run` blocker evidence
- User-approval actions: human labels, acceptance thresholds, live provider calls, publication, push, merge, destructive cleanup, or out-of-scope edits
- Parallel ownership: none; shared cache, analysis, review, and trace paths require one sequential lead
- Sequential fallback: reproduce, trace shared callers, patch smallest owner, prove focused behavior, then run cross-component flow and final suite

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `c17fa9e1`
- Expected workspace: `main` clean except preserved untracked `.tmp/` and `.venv/`
- Next action: final verification and Git handoff
- Blockers: external human labels/thresholds and authorized live provider workload unavailable; P0 promotion and live economics remain blocked

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | cold/warm cache contract | 61 passed, 2 skipped; default fresh→reuse regression green |
| Task 2 | `completed` | current | `codex` | none | stale snapshot recomputation | 130 passed; v5 stale snapshot recomputation green |
| Task 3 | `completed` | current | `codex` | Task 2 | rendered review-to-closure flow | 630 passed; uncertainty propagation/UI answer/empty-answer guard green |
| Task 4 | `completed` | current | `codex` | Task 2 | unique requirement coverage and fit proof | 99 passed; marginal requirement-group selection and `page_fit_status=unverified` green |
| Task 5 | `completed` | current | `codex` | Tasks 1-4 | valid P0 report or `not_run` | 15 ranking tests; 45 evidence tests; source-backed P0-A now `not_run` on invalid all-positive/full-pool fixture; synthetic P0-B remains diagnostic |
| Task 6 | `completed` | current | `codex` | Tasks 3, 5 | accepted-CV effort linkage | 16 contract tests; app suite green; accepted artifact projection deduplicates replay and reports missing live denominator as `not_run` |
| Task 7 | `completed` | current | `codex` | Tasks 5-6 | measured bottleneck decision and final ledger | no authorized accepted-CV workload; no optimization applied; deferral recorded |

## Task Breakdown

### Task 1: Restore canonical embedding-cache reuse

**Purpose:** Make cache lookup and insertion agree on one effective embedding contract.

**Task Function:** Trace backend/model identity through lookup, generation, insertion, and vector-search callers; patch shared contract owner only.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded source tracing and deterministic SQLite behavior.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused tests and direct SQLite probe.

**Specification Coverage:** First identical request is fresh; second reuses; one row persists; backend/model change invalidates reuse.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/vector_search.py:build_candidate_query_embedding_contract_fingerprint`, `resolve_candidate_query_embedding`
- Inspect: `src/fitcv/embeddings.py:build_embedding_contract_fingerprint`, `build_embedding_backend_metadata`, `generate_embedding_with_metadata`
- Verify: `tests/test_vector_search.py`, `tests/test_embeddings.py`

**Dependencies:** Current source at `c17fa9e1`; no provider call required.

**Authority:**
- Preauthorized local actions: `reproduce deterministic SQLite behavior, add focused cache tests, and patch listed symbols`
- Stop for: `new cache storage, provider authentication, schema migration outside existing table, or production retrieval-policy change`

**Steps:**
- [x] Reproduce cold/warm calls; record configured ID, actual ID, contract fingerprints, row count, and reuse status.
- [x] Align lookup/insertion on same effective contract, including deterministic fallback identity; preserve sentence-transformer fallback/recovery behavior.
- [x] Add tests for fresh-to-reuse, one-row persistence, invalid JSON, and contract-change miss.
- [x] Run direct SQLite probe and focused tests.

**Verification:** `uv run pytest -q tests/test_vector_search.py tests/test_embeddings.py`

**Expected:** first call `fresh_query_embedding`; second `reused_cached_query_embedding`; one row; changed contract creates fresh row.

**Exit Criteria:** Cache reuse and invalidation are demonstrated without unrelated retrieval changes.

### Task 2: Invalidate stale requirement-support assessments

**Purpose:** Stop old support snapshots from bypassing corrected qualification logic.

**Task Function:** Trace fingerprint construction, reusable-record selection, and all `_reuse_rejection_reason` callers; version semantic identity at policy boundary.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared fingerprint/reuse path with correctness risk.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct and caller-visible analysis tests.

**Specification Coverage:** Known false-verified answer recomputes after policy correction; exact reuse requires same semantic version and input identity; absent policy version fails closed.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_analysis.py:_build_analysis_input_components`, `_reuse_rejection_reason`, `_rebuild_reused_record`, `analyze_ranked_job`
- Inspect: policy/fingerprint owners found by search for `REQUIREMENT_SUPPORT_POLICY_VERSION`, `requirement-support-v5`, and `build_cv_analysis_input_fingerprint`
- Verify: `tests/test_agentic_cv_analysis.py`, related pipeline tests

**Dependencies:** None; Task 1 independent.

**Authority:**
- Preauthorized local actions: `reproduce stale snapshot reuse, add regression tests, and version existing support-semantics identity`
- Stop for: `stale-record compatibility copy, historical-artifact deletion, or unrelated requirement-label changes`

**Steps:**
- [x] Reproduce v5 snapshot reuse with known incorrect qualification; trace shared callers before editing.
- [x] Bump `REQUIREMENT_SUPPORT_POLICY_VERSION` from `requirement-support-v5` to `requirement-support-v6`; compare reuse against that central constant and reject missing policy versions.
- [x] Test stale recomputation, current-version reuse, input mismatch, incomplete snapshot, and historical safety.
- [x] Run focused analysis/pipeline tests and record decision reasons.

**Verification:** `uv run pytest -q tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py`

**Expected:** stale or absent-version record has explicit rejection; SQL mismatch becomes `relevant_unverified`; valid v6 record still reuses.

**Exit Criteria:** Old assessments cannot remain reusable after support-semantics change.

### Task 3: Prove complete review-required product flow

**Purpose:** Close P1-B across payload, form, persistence, refresh, artifact replacement, failure retention, and replay.

**Task Function:** Complete one existing frontend-to-backend slice through review route, resolution store, regeneration queue, run events, and artifact projection.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-boundary behavior and idempotency risk.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused route tests plus local browser/probe evidence.

**Specification Coverage:** `generation → review item → candidate answer → persisted resolution → fresh analysis/generation → replacement artifact → review closure`; failed refresh stays pending; replay has no duplicate terminal effects.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_generation.py:_build_result`, `generate_from_analysis`
- Inspect/modify: `src/fitcv_cp/app_run_support.py:_build_cv_generation_review_required_payload`
- Inspect/modify: `src/fitcv_cp/templates/_cv_review_queue.html`
- Inspect: current `frontend/src/features` review surfaces; if no uncertainty-answer consumer exists, keep the server-rendered queue as canonical and do not create a parallel SPA flow.
- Inspect/modify: `src/fitcv_cp/app.py:admin_run_cv_review_action`, `_build_hitl_review_queue`, `_build_hitl_closure_summary`, `_finalize_review_draft_as_cv_artifact`
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, `tests/test_pipeline_agentic_late_stage.py`

**Dependencies:** Task 2 supplies fresh analysis behavior.

**Authority:**
- Preauthorized local actions: `preserve uncertainties, add native answer input, extend route/queue tests, and run local app/browser probes`
- Stop for: `new UI/API framework, new resolution store, auto-close after failed refresh, or browser-only proof`

**Steps:**
- [x] Reproduce missing `uncertainties` in `_build_result` and missing answer control in rendered queue.
- [x] Preserve uncertainty payload and add semantic answer input with safe action-specific validation.
- [x] Test answer submission, resolution identity, fresh regeneration, replacement artifact, closure, refresh failure retention, and replay idempotency.
- [x] Run local browser/probe against rendered HTML and POST, then reconcile with backend assertions.

**Verification:** `uv run pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_pipeline_agentic_late_stage.py`

**Expected:** uncertainty and answer field render; one resolution row; one regeneration per idempotency key; fresh replacement; closure only after success.

**Exit Criteria:** Ordinary review UI proves complete journey; direct test-only form data is insufficient.

### Task 4: Preserve marginal requirement coverage and verify rendered fit

**Purpose:** Stop score-first allocation from dropping unique requirements and separate budget metadata from actual page proof.

**Task Function:** Use deterministic marginal-coverage selection and existing renderer/validator evidence; add no layout engine.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded allocation and rendering proof.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused compiler/validator tests and fixture render check.

**Specification Coverage:** Uncovered verified requirements outrank redundant claims; `page_count: 1` alone is not proof.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `_run_repair_cycle`, `_determine_repair_targets`
- Inspect: `src/fitcv/cv_generator.py` render/validation integration
- Verify: `tests/test_cv_generation_reason_mapping.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_evidence.py`, existing renderer/validator tests

**Dependencies:** Task 2 supplies fresh coverage; Task 3 is not required for local compiler work.

**Authority:**
- Preauthorized local actions: `add deterministic selection tests and patch existing content-plan/render-validation paths`
- Stop for: `new compiler service, unbounded repair, weaker grounding, or claim-count-as-page-proof`

**Steps:**
- [x] Reproduce six Python plus one SQL fixture; record selected/omitted evidence and coverage.
- [x] Select by maximum uncovered requirement contribution, then score, skill count, and evidence ID.
- [x] Add unique SQL retention regression and redundant-claim omission proof.
- [x] Run existing renderer/validator path; expose rendered fit separately from `space_budget.page_count`.
- [x] No canonical rendered-page measurement exists; leave page-fit status unverified and add no layout infrastructure.
- [x] Confirm repair count and grounding do not regress.

**Verification:** `uv run pytest -q tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py`

**Expected:** unique requirement retained when budget permits; unsupported claims absent; page-fit verified only from rendered validation.

**Exit Criteria:** Content plan preserves marginal coverage and reports honest rendered-fit state.

### Task 5: Build valid P0-A/P0-B evaluation evidence

**Purpose:** Replace invalid all-positive/order-destroying benchmark assumptions with discriminating, reproducible evaluation.

**Task Function:** Harden existing benchmark/comparison validators and reports; do not promote production retrieval from benchmark output alone.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: measurement validity and evidence governance.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: existing benchmark/comparison tests and report hashes.

**Specification Coverage:** Human-reviewed label classes, preserved order, mixed candidate pools with `top_n < pool_size`, source-group-protected holdout, pre-registered thresholds, `not_run` for insufficient evidence, incumbent may remain default.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `scripts/benchmark_ranking.py:_run_once`, metric assembly, fixture validation, output schema
- Inspect/reuse: `scripts/compare_requirement_support.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`, `tests/test_p0_public_corpus.py`
- Verify: existing P0 evidence and new evidence ledger

**Dependencies:** Tasks 1-4; human labels and thresholds remain external prerequisites.

**Authority:**
- Preauthorized local actions: `validate inputs, preserve retrieval order, add deterministic reports/tests, and record supplied hashes`
- Stop for: `synthetic labels, production promotion, fabricated human approval, or unapproved live provider calls`

**Steps:**
- [x] Fail closed for all-positive labels, missing classes, non-discriminating full-pool retrieval, and metrics after order loss.
- [x] Require mixed relevant/borderline/irrelevant pools, `top_n < pool_size`, and source-group separation before producing promotion-grade retrieval evidence.
- [x] Preserve ranked order through `Recall@N`, `Precision@N`, `nDCG@N`, and `MRR`; report split counts.
- [x] Compare path validated; source-backed holdout and pre-registered thresholds remain an explicit blocker.
- [x] Evaluate P0-B with existing reviewed rows only as diagnostic; synthetic cases remain non-promotion evidence.
- [x] Emit exact `not_run` blocker when labels, thresholds, or holdout are absent; retain incumbent when candidate does not discriminate.

**Verification:** `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py`; run smoke/admitted reviewed fixture and inspect JSON/hash output.

**Expected:** invalid fixture cannot produce promotion evidence; valid fixture produces reproducible report or explicit `not_run`.

**Exit Criteria:** P0 status is evidence-backed or explicitly blocked, never inferred from invalid synthetic retrieval.

### Task 6: Measure accepted-CV effort from existing run events

**Purpose:** Extend generation-stage trace into honest end-to-end effort per accepted CV.

**Task Function:** Link existing run events, review actions, regeneration jobs, and accepted artifact identity into one backward-compatible projection.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing event/artifact ownership; no telemetry system.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: worker, artifact, and app tests cover stored contract.

**Specification Coverage:** Timing starts at run/generation admission and ends at accepted artifact; attempts, regeneration, review questions, human actions, final status, and input/output tokens when available share run/item identity; missing live economics are `not_run`.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`, `_update_efficiency_summary`, `_finalize_generation_result`
- Inspect/modify: `src/fitcv_cp/app.py:admin_run_cv_review_action`, `_build_hitl_review_queue`, `_build_hitl_review_audit_payload`
- Inspect/modify: `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/worker_job.py` existing trace/run-event projection
- Verify: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, app review tests

**Dependencies:** Task 3 supplies review semantics; Task 5 supplies comparable workload boundary.

**Authority:**
- Preauthorized local actions: `extend optional efficiency payload, link existing events/artifacts, add backward-compatible tests, and run local probes`
- Stop for: `new telemetry backend, secret persistence, fabricated live costs, or duplicate event schema`

**Steps:**
- [x] Map accepted-artifact fields from existing debug records and review actions; live admission-to-closure sample remains unavailable.
- [x] Add optional end-to-end fields while retaining generation-stage fields and old-payload parsing; include stored token usage only when provider evidence supplies it.
- [x] Test accepted-artifact projection and replay deduplication; unavailable live paths remain `not_run`.
- [x] Emit explicit denominator and `not_run` when no authorized live workload exists.

**Verification:** `uv run pytest -q tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_app.py`

**Expected:** one accepted CV maps to one effort record; human actions count only from stored events; old payloads parse.

**Exit Criteria:** Workflow savings claim uses total accepted-CV effort or remains `not_run`.

### Task 7: Optimize only measured bottleneck and close evidence ledger

**Purpose:** Apply one bounded optimization only when Tasks 5-6 identify a bottleneck; otherwise defer speculative work.

**Task Function:** Compare before/after on same representative workload while preserving grounding, review correctness, and artifact integrity.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: measurement-gated performance change.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final verification owns acceptance.

**Specification Coverage:** Largest measured bottleneck only; separate implemented, product-verified, measured-benefit, promoted/default, and deferred statuses; P1-C/P2 deferred.

**Required Skills:** `skill-performance-optimization`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect/modify: only measured bottleneck owner from Tasks 1-6
- Verify/write: `docs/superpowers/evidence/2026-09-29-fitcv-remaining-findings.md`

**Dependencies:** Tasks 1-6 complete with accepted evidence.

**Authority:**
- Preauthorized local actions: `make one measured local optimization, rerun comparable workload, update evidence ledger, and record deferrals`
- Stop for: `no measured bottleneck, weaker grounding/review, new subsystem, threshold disagreement, or unrelated failure`

**Steps:**
- [x] No complete accepted-CV workload exists; record absence and skip speculative optimization.
- [x] No optimization applied because no dominant end-to-end bottleneck is measured.
- [x] Existing synthetic timings retained as diagnostic only; no before/after promotion claim made.
- [x] Record implemented, product-verified, measured-benefit, promoted/default, and deferred statuses in evidence ledger.

**Verification:** Run all focused suites from Tasks 1-6, configured full suite, `git diff --check`, and evidence review.

**Expected:** no optimization without comparable proof; no required blocker hidden as success.

**Exit Criteria:** Findings are closed or explicitly blocked with evidence; plan can move to completion verification.

## Verification

- `python -m pytest -q tests/test_vector_search.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py tests/test_fitcv_cp/test_run_artifact_contracts.py` — 243 passed, 1 skipped.
- `python -m pytest -q tests/test_fitcv_cp/test_app.py` — passed; Windows SQLite temp cleanup emitted pre-existing `WinError 32` after completion.
- `python -m pytest -q` — 2907 passed, 4 skipped, 52 warnings.
- Local review-flow and cache SQLite probes recorded by Tasks 1-3; current accepted-CV live workload remains unavailable.
- `git diff --check` passes; plan ledger, evidence, and code/tests/docs reconcile with `main` at `c17fa9e1`.

## Completion Criteria

1. Cache cold/warm reuse and invalidation pass focused tests and direct probe.
2. Stale support snapshots fail closed and corrected analysis runs.
3. Ordinary review UI proves answer entry, persistence, refresh, replacement artifact, failure retention, closure, and replay idempotency.
4. Content plan preserves marginal requirement coverage and reports rendered fit only from validation evidence.
5. P0-A/P0-B report is valid or explicit `not_run`; no promotion inferred from invalid fixtures.
6. Accepted-CV effort links existing events/artifacts or remains `not_run` without live evidence.
7. Any optimization has comparable before/after proof with no grounding/review regression.
8. Evidence ledger separates implemented, product-verified, measured-benefit, promoted/default, and deferred status; P1-C/P2 deferrals are explicit.
9. Fresh final verification passes `skill-verification-before-completion`.

Plan execution complete; Git disposition remains separate and requires explicit user authorization.
