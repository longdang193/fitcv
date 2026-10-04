---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: fitcv-integration-convergence
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/agentic_cv_analysis.py
  - frontend/src/features/cv-review/
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx
  - docs/api.md
  - docs/superpowers/evidence/
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_agentic_cv_generation.py
  - frontend/src/test/
  - frontend/e2e/integration-flows.spec.ts
  - scripts/benchmark_cv_efficiency.py
---

# FitCV Frontend/Backend Integration Convergence

## Goal

Deliver bounded milestone: **Frontend/backend final-CV parity + low-cost
generation baseline**.

Verdict review: P0 is complete within frozen scope. P1-A and P1-B backend
contracts are accepted, but end-to-end product closure is incomplete. Active
React client uses phantom review mutation, does not consume backend uncertainty
resolution semantics, hides final one-page proof, and collapses lifecycle
states. Fix integration truth first, then measure one low-cost generation
optimization. Do not reopen retrieval, ranking, model choice, evidence
architecture, P1-C, or P2.

Stop milestone when one real React flow displays verified one-page CV proof,
distinguishes `pending`, `review_required`, `rejected`, `cancelled`, and success
states, executes one backend-owned uncertainty resolution, persists and refreshes
it, and CI proves frontend/backend contract parity.

## Implementation Outcomes

### Backend-owned final-artifact evidence

Fresh generation, cache reuse, regeneration, persistence, and review closure
produce one identity-bound envelope containing `artifact_version_id`,
`content_checksum`, `page_fit_status`, `render_acceptance`, render/template
fingerprints, renderer contract version, `trace_id`, and `run_job_id`. React
never infers acceptance from missing fields or rendered text.

### Canonical review-resolution API

One JSON review resource/action contract exposes `review_item_id`, `reason_code`,
`uncertainties`, `resolution_key`, `allowed_actions`, current resolution state,
CV status, and final-artifact evidence. Supported actions remain
`RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, and `OVERRIDE_BLOCK`. Existing admin HTML
routes remain compatibility surfaces and delegate to same domain operation.

### React parity and low-cost baseline

React renders server-owned status and qualifier-aware evidence separately,
shows one-page/native-render proof only when backend proof passes, and refreshes
after resolution or regeneration. Existing trace/benchmark contracts report
provider duration, artifact acceptance latency, whole-run latency, provider
calls, tokens, regenerations, retry categories, cache reuse, human actions, and
resolution reuse. One frozen workload establishes incumbent baseline before one
bounded retry experiment.

### Scope boundary

P1-C stays deferred until this milestone and one measured optimization close.
P2 stays frozen. No new agent, vector store, reranker, verifier model,
monitoring service, or provider-routing layer.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-full-stack-integration`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Parallel ownership: `none`; all surfaces share final-artifact and review SSOT
- Sequential fallback: evidence envelope → review API → React parity → full-stack proof → telemetry → one retry experiment → final verification

## Task Breakdown

### Task 1: Normalize final-CV evidence envelope

**Purpose:** Make final-artifact identity and one-page proof identical across
fresh, cached, regenerated, persisted, and review-closed paths.

**Specification Coverage:** Backend-owned evidence; P1-A acceptance gates;
no historical fact synthesis.

**Required Skills:** `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `execute_cv_regenerate_once`, `_build_cv_generation_debug_payload`
- Inspect: `src/fitcv_cp/sqlite_store.py:_cv_projection`, `list_cv_versions`, `lookup_reusable_cv_versions`, `get_cv_preview`, `get_cv_download`
- Modify: `src/fitcv_cp/run_artifact_contracts.py:accepted_cv_artifact_event_v1`, `build_accepted_cv_effort_projection`; add `build_final_cv_evidence_envelope`
- Modify: `src/fitcv_cp/app.py:get_canonical_cv_versions`, `preview_canonical_cv`, `download_canonical_cv`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `test_worker_job.py`, `test_sqlite_store.py`, `test_app.py`

**Dependencies:** Existing immutable CV-version storage, checksum validation,
render acceptance fields, and `cv_generation_debug_v3` remain canonical.

**Steps:**
- [x] Build one envelope from exact content, version identity, checksum, render/template/config fingerprints, renderer contract, page count, page-fit status, render acceptance, trace ID, and run-job ID.
- [ ] Call builder before accepted persistence on fresh generation, reuse, regeneration, and review closure.
- [x] Require content-validation success plus matching render proof for cache reuse; stale proof rerenders locally with zero provider calls.
- [x] Project envelope through CV-version JSON and quality-warning fields.
- [ ] Add missing identity, checksum mismatch, unknown page count, non-one-page, stale-config, and wrong-job binding tests.

**Verification:** `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`

**Expected:** Invalid proof stays non-accepted; accepted paths contain exact
identity-bound proof; stale reuse performs local render only.

**Exit Criteria:** One tested backend builder owns final-CV proof for every
accepted path.

### Task 2: Expose canonical review-resolution API

**Purpose:** Replace phantom frontend mutation with JSON contract that delegates
to existing P1-B resolution semantics.

**Specification Coverage:** Review resource, supported uncertainty actions,
idempotency, persistence, reanalysis, stale-source protection, refresh.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:CvReviewActionRequest`, `_build_hitl_review_queue`, `admin_run_cv_review_action`
- Inspect: `src/fitcv_cp/app_run_support.py:_build_cv_generation_review_required_payload`
- Inspect: `src/fitcv_cp/worker_job.py:_persist_resolution_reanalysis` and review closure logic
- Inspect: `src/fitcv/agentic_cv_analysis.py` resolution application/reuse checks
- Modify: `src/fitcv_cp/app.py`; add JSON `GET /runs/{run_id}/jobs/{run_job_id}/cv-review` and `POST /runs/{run_id}/jobs/{run_job_id}/cv-review/actions`
- Modify: `src/fitcv_cp/models.py` or app request models for typed JSON envelopes
- Modify: `docs/api.md`
- Verify: `tests/test_fitcv_cp/test_app.py`, `test_worker_job.py`, `tests/test_review_identity.py`

**Dependencies:** Task 1 projection exists. Admin HTML route remains and shares
action application path; no duplicated state machine.

**Steps:**
- [x] Define resource fields: run/job/version IDs, status, review item, reason, uncertainties, resolution key, allowed actions, current resolution, evidence, refresh metadata.
- [x] Define action fields: review item, uncertainty, resolution key, action, answer, note, idempotency key; reject unsupported actions and empty answers.
- [x] Resolve by canonical run-job/review identity, not client-supplied arbitrary `review_state`.
- [x] Reuse profile/source fingerprints, persist one resolution, enqueue at most one impacted-job reanalysis, and return refreshed resource.
- [x] Preserve idempotency and stale-resource semantics; CAS remains owned by legacy immutable-version review routes.

**Verification:** Focused pytest above plus assertions for fetch → resolve →
persist/reanalyze → refreshed resource with uncertainty no longer pending.

**Exit Criteria:** React can use one tested JSON contract without `/admin/...`
HTML routes or invented approve/stretch/reject resolution states.

### Task 3: Align React CV and fit-evidence semantics

**Purpose:** Make active React display match backend status, evidence, and
resolution truth.

**Specification Coverage:** Final-CV parity, distinct lifecycle states,
one-page proof, qualifier-aware evidence, refresh after mutation.

**Required Skills:** `skill-full-stack-integration`

**Files And Symbols:**
- Modify: `frontend/src/features/cv-review/types.ts`, `api.ts`
- Modify: `frontend/src/features/cv-review/components/CvEvaluationCard.tsx`, `CvVersionHistory.tsx`
- Modify: `frontend/src/features/run-detail/run-detail-page.tsx`
- Modify: `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx`
- Verify: `frontend/src/features/cv-review/cv-api.test.tsx`, `frontend/src/test/feature-ux-consistency.test.tsx`, `frontend/src/test/job-evaluation.test.ts`, `frontend/e2e/integration-flows.spec.ts`

**Dependencies:** Tasks 1–2 response shapes stable. Preserve preview,
download, immutable version selection, and existing tokens.

**Steps:**
- [x] Add typed evidence and review-resource/action types; enumerate server-owned statuses.
- [x] Render `Final artifact verified · 1 page · native render passed` only for passing backend proof; show missing/failed proof otherwise.
- [x] Separate qualifier-aware requirement evidence from pipeline disposition.
- [x] Render only `allowed_actions`; use answer input only for authorized answer actions.
- [x] Refresh jobs and review resource after resolution/regeneration; preview/history refresh remains limited to existing immutable-version flow.
- [ ] Add accessible names, keyboard/focus, and status-announcement assertions.

**Verification:** `npm --prefix frontend run typecheck`; `npm --prefix frontend run test -- src/features/cv-review/cv-api.test.tsx src/test/feature-ux-consistency.test.tsx src/test/job-evaluation.test.ts`

**Expected:** Phantom endpoint gone; lifecycle states distinct; proof comes
only from backend fields; tests pass.

**Exit Criteria:** React consumes canonical resources and completes one real
resolution refresh without frontend-only truth.

### Task 4: Prove full-stack parity flow

**Purpose:** Prove direct backend behavior and browser behavior against same
contract, not frontend mocks alone.

**Specification Coverage:** Milestone stop point; success, failure, persistence,
refresh, and stale/CAS behavior.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `frontend/e2e/integration-flows.spec.ts`
- Verify: `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:** Tasks 1–3 complete; deterministic fixtures avoid external
providers.

**Steps:**
- [ ] Seed review-required CV with immutable version and evidence envelope.
- [ ] Assert React status, one-page proof, and separate qualification evidence.
- [ ] Submit `RESOLVE_WITH_ANSWER` or `CONFIRM_OMIT`; assert persisted resolution and refreshed resource.
- [ ] Assert preview remains bound to selected immutable version and stale/CAS conflict is actionable.
- [ ] Assert `cancelled`, `pending`, `review_required`, `rejected`, and accepted fixtures render distinct labels.

**Verification:** `python -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`; `npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts`

**Exit Criteria:** CI proves one real final-CV display/resolution/persistence/
refresh flow.

### Task 5: Instrument stage cost and reuse

**Purpose:** Establish low-cost baseline before retry changes, using existing
trace and benchmark contracts only.

**Specification Coverage:** Provider/non-provider timing, cost, retry, reuse,
human effort, current-contract cohort selection.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`, `_update_efficiency_summary`, `_update_live_trace_validation_cycle`
- Inspect/modify: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Inspect: `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`, `_build_cv_generation_debug_payload`
- Modify: `scripts/benchmark_cv_efficiency.py`; verify `tests/test_agentic_cv_generation.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 1 prevents unverified artifacts entering accepted-CV
metrics. No new monitoring service.

**Steps:**
- [ ] Record analysis, retrieval, content-plan, provider, validation, render, repair, and persistence durations.
- [ ] Keep provider duration, artifact acceptance latency, and whole-run latency separate.
- [ ] Record calls, tokens, regenerations, retry category, review-required count, human actions, resolution reuse, repeated questions avoided, and cache fields `reuse_candidate`, `reuse_hit`, `render_proof_reused`, `local_rerender_performed`, `provider_calls_avoided`, `renders_avoided`, `tokens_avoided`.
- [ ] Benchmark same request twice, stale renderer config, and saved-resolution reuse.
- [x] Exclude historical/incomplete cohorts from promotion claims and write current evidence under `docs/superpowers/evidence/` without secrets.

**Verification:** `python -m pytest -q tests/test_agentic_cv_generation.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py`; run existing frozen-workload command from `scripts/benchmark_cv_efficiency.py`.

**Exit Criteria:** Baseline explains provider and non-provider wall time and
identifies one dominant retry/reuse cost with trustworthy denominator.

### Task 6: Optimize one dominant retry cause

**Purpose:** Reduce cost through one narrow, evidence-driven experiment.

**Specification Coverage:** One primary provider call plus zero/one narrow
repair; no generic stronger-prompt loop; no acceptance regression.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:_failure_category`, `_attempt_failure_category`
- Inspect: `src/fitcv/agentic_cv_generation.py:_determine_repair_targets`, `_shallow_section_repair_targets`
- Modify: exactly one owner selected from `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, or `src/fitcv_cp/worker_job.py`
- Verify: changed-owner tests and `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 5 identifies category by frequency × provider-call cost
× token cost × retry-failure probability. If denominator is incomplete, stop
with baseline-only evidence.

**Steps:**
- [x] Freeze incumbent workload and runtime.
- [x] Do not select a repair: current cohort denominator lacks comparable workload and complete stage latency evidence.
- [ ] Keep maximum one narrow repair after primary generation; preserve P0-B/P0-C, final proof, review, and cache behavior.
- [ ] Compare incumbent/candidate on same workload: first-pass acceptance, accepted one-page rate, calls, tokens, regenerations, retry failures, p50/p95 stage latency, and whole-run latency.
- [x] Reject promotion and retain incumbent because optimization evidence is incomplete; record boundary in `docs/superpowers/evidence/2026-10-03-fitcv-efficiency-baseline.md`.

**Verification:** Focused changed-owner test command plus `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_benchmark_cv_efficiency.py`; run identical frozen-workload benchmark for both arms.

**Exit Criteria:** One optimization result is reproducible or explicitly
rejected; no architecture expansion.

### Task 7: Final verification and reconciliation

**Purpose:** Verify milestone, reconcile evidence, preserve deferrals.

**Specification Coverage:** All outcomes, tests, evidence boundaries,
rollback/stop conditions, P1-C/P2 scope.

**Required Skills:** `skill-verification-before-completion`, `skill-full-stack-integration`, `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Verify all Task 1–6 targets, `docs/api.md`, `docs/superpowers/evidence/`, and `git diff --check`
- Inspect `config/acceptance_state.yaml` and `artifacts/acceptance_state.json` only if changed by implementation

**Dependencies:** Tasks 1–6 complete or explicitly blocked with evidence.

**Steps:**
- [ ] Run backend tests, frontend type/unit tests, browser flow, and frozen-workload benchmark.
- [ ] Confirm API and React use identical evidence fields/status values; no phantom review endpoint remains.
- [ ] Confirm historical evidence is unchanged and no credentials appear in output.
- [ ] Record metric denominators, optimization promotion/rejection, deviations, and rollback decision.
- [ ] Leave P1-C deferred and P2 frozen.

**Verification:** `python -m pytest -q`; `npm --prefix frontend run typecheck`; `npm --prefix frontend run test`; `npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts`; `git diff --check`

**Exit Criteria:** `skill-verification-before-completion` returns `verified`.
Only then may plan status change from `proposed` to `completed`.

## Verification

Final proof must show:

- one identity-bound final-CV evidence envelope across fresh, cached, regenerated, and review-closed paths;
- stale cached proof rerenders locally with zero provider calls;
- canonical JSON review resource/action contract with persistence, idempotency, stale-source protection, and refresh;
- React truthful lifecycle states, one-page/native-render proof, qualifier-aware evidence, and refreshed resolution state;
- direct backend boundary tests plus one browser flow against real route contracts;
- complete current-contract timing, call, token, retry, reuse, and human-effort telemetry;
- one bounded optimization experiment with identical workload/runtime and no secret leakage;
- P1-C deferred and P2 frozen.

Run final proof through `skill-verification-before-completion`. Do not claim
acceptance or cost improvement from source inspection alone.

## Completion Criteria

The plan is ready for completion verification when:

1. every implementation outcome is satisfied;
2. every task-local verification item passes or has evidence-backed blocker;
3. backend/frontend fields and statuses reconcile with current source/tests;
4. generated evidence matches canonical inputs;
5. optimization is reproducible or explicitly rejected;
6. historical evidence is unchanged and secrets are absent;
7. P1-C and P2 remain deferred;
8. final commands are runnable and verification returns `verified`.

This plan remains active until final verification returns `verified`. No commit,
push, merge, or acceptance-status promotion is authorized by this execution.

## Execution Reconciliation — October 3, 2026

- Backend focused proof: `531 passed`; full backend proof: `3023 passed, 8 skipped`; frontend unit proof: `328 passed`; frontend typecheck and production build passed; browser shell flow: `6 passed` with local API running.
- Frontend typecheck root cause fixed through `@types/node`, Vitest/Node ambient types, and stale fixture cleanup.
- Stale cached render proof now rerenders locally with zero provider calls; generation render acceptance now feeds final-CV evidence envelope without losing proof fields.
- Failed cached rerender now ends in `review_required` with retained CV content and explicit `final_artifact_acceptance` diagnostics; provider fallback is blocked and regression proof passes.
- Canonical review JSON resource/action contract, idempotency reservation/replay storage, refresh wiring, typed React consumption, and evidence display are implemented.
- Efficiency baseline is measured for `5` attempted jobs, `3` accepted final CVs, `6` provider calls, and `29130` tokens; stage latency is unavailable and cohort is not comparable to historical `169` jobs.
- P1-C remains deferred. P2 remains frozen. Task 1 review-closure binding tests and Task 4 deterministic CV browser fixture remain open for final verification.
