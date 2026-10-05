---
layer: change
artifact_type: plan
contract_version: "1"
status: active
template_id: implementation-plan
name: fitcv-p1ab-final-convergence-and-artifact-optimization
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/review_identity.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/worker_job.py
  - frontend/src/features/cv-review/api.ts
  - frontend/src/features/cv-review/types.ts
  - frontend/src/features/cv-review/final-artifact-evidence.ts
  - frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/bookmarks/route.tsx
  - frontend/src/test/job-evaluation.test.ts
  - frontend/src/features/cv-review/*.test.ts
  - frontend/e2e/integration-flows.spec.ts
  - scripts/benchmark_cv_efficiency.py
  - scripts/run_fitcv_repair_experiment.py
  - scripts/seed_fitcv_review_e2e.py
  - scripts/verify_fitcv_acceptance.py
  - tests/fixtures/fitcv-p1ab-repair-experiment.json
  - scripts/evaluate_requirement_support_live.py
  - docs/superpowers/plans/2026-10-03-fitcv-integration-convergence-plan.md
  - docs/superpowers/plans/2026-10-03-fitcv-final-artifact-integration-optimization-plan.md
  - docs/superpowers/evidence/
  - tests/test_agentic_cv_generation.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_benchmark_cv_efficiency.py
---

# FitCV P1-A/B Final Convergence And Final-Artifact Optimization

## Goal

Close P1-A and P1-B end to end without reopening accepted P0 scope, retrieval,
ranking, model selection, P1-C, or P2. Complete the remaining work represented
by `2026-10-03-fitcv-integration-convergence-plan.md` and
`2026-10-03-fitcv-final-artifact-integration-optimization-plan.md`:

1. make deterministic repair evidence authorization fail closed and symmetric;
2. make uncertainty actionability authoritative per uncertainty in backend and UI;
3. make evidence drawer and lifecycle presentation truthful and accessible;
4. prove one real frontend/backend review flow against current route contracts;
5. reconcile final-artifact identity/page-fit proof across all committed paths;
6. instrument missing stage, repair-savings, cache-reuse, and resolution-reuse data;
7. run one identical-workload incumbent/candidate experiment and promote only on
   correctness-preserving total-workload savings.

Canonical boundary:

> P0 is complete within frozen scope. P1-A/B acceptance contracts are passed,
> but end-to-end product convergence needs one final bounded correctness patch.
> P1-C starts only after this plan and one comparable optimization experiment
> close. P2 remains frozen.

## Implementation Outcomes

### Evidence-scoped deterministic repair

Fresh generation, retry, and local section repair distinguish legacy-unavailable
selection from explicit non-empty and explicit-empty selection. All repaired
skills, experience, projects, education, languages, and certifications consume
one host-built eligible repair projection. Plain-string skills cannot bypass
selection. Unsupported generic experience prose is never synthesized. Explicit
empty selection cannot widen profile access; local repair becomes unavailable and
existing bounded provider/review-required behavior remains intact.

### Per-uncertainty review contract

Every uncertainty carries authoritative `is_actionable`, `allowed_actions`, and
resolution state. The server verifies review-item ownership, uncertainty
ownership, pending state, requested-action eligibility, and resource revision
before mutation. Resolved uncertainties are read-only. Stale or non-pending
requests return the existing typed conflict/error contract without duplicate
side effects.

### Frontend/backend parity

React consumes one backend-owned status/outcome union and final-artifact evidence
envelope. `FitEvidenceDrawer` presents requirement coverage independently from
review lifecycle and never infers qualification success from missing evidence.
Pending, review-required, rejected, cancelled, and successful states have
truthful labels, focus behavior, status announcements, and keyboard-accessible
controls. Resolution refreshes the canonical resource and preserves answer
clearing when the selected uncertainty changes.

### Measured optimization baseline

The current trace records stage timing for queue wait, analysis, retrieval,
content planning, provider, validation, local repair, rendering, and persistence,
plus validation-failure causes. It records local-repair attempts/outcomes,
provider retries avoided, tokens/latency avoided, proof/cache/render/resolution
reuse, questions, actions, questions avoided, and review time. One generated
scorecard reports correctness, product parity, efficiency, and human effort.
The incumbent remains default unless an identical-workload candidate reduces
provider calls, tokens, and latency without grounding, artifact, review, or
one-page regressions.

### Scope and non-goals

P1-C remains deferred until the closure gate and one measured optimization pass.
P2 remains frozen. No new agent, database, vector store, reranker, verifier
model, provider-routing layer, or generic closure document.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-full-stack-integration`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`, `skill-plan-document-reviewer`
- Isolation: `current workspace`; preserve unrelated untracked files
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect source/history/evidence, edit declared plan/code/test/docs files, run declared local tests/build/browser/benchmark commands, and write generated evidence under `docs/superpowers/evidence/`
- User-approval actions: commit, push, PR creation/update, merge, branch deletion, destructive cleanup, secret/authentication changes, and acceptance-state promotion
- Parallel ownership: `none`; repair authorization, review state, UI lifecycle, and telemetry share contract truth
- Sequential fallback: baseline/reconciliation → repair authorization → review actionability → frontend parity → browser E2E → telemetry/scorecard → identical-workload experiment → final verification

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-evidence-scoped-backfill`
- Base commit: `1b86a119`
- Expected workspace: clean tracked checkout with unrelated disposable untracked files
  preserved; plan ledger distinguishes committed HEAD behavior from historical
  working-tree behavior
- Next action: rerun Task 7 against current HEAD, then complete Task 8 final
  verification and reconciliation before any production-default change
- Blockers: R13 is historical and fails current-head identity gates; current
  paired-cohort evidence is missing; production-default change remains pending
  independent final review

**Latest plan review:** 2026-10-04, independent `review-1` returned `needs
changes`. Findings: contradictory ledger/admission state, missing explicit
`INCUMBENT_ARM`/`CANDIDATE_ARM` mapping, ambient scorecard inputs, unchecked
PowerShell native exit codes, and ambiguous Task 7 unavailable-versus-negative
closure. These plan defects are patched below; a second bounded review must
return `implementation-ready` before Task 7 or Task 8 closes.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | baseline/reconciliation commands and committed-execution review | `1b86a119`, fresh git history/diff evidence; verification command reconciled |
| Task 2 | `completed` | current | `codex` | Task 1 | committed-incumbent/default proof plus focused backend regression tests | `tests/test_agentic_cv_generation.py`: 11 passed; incumbent/default proof recorded above |
| Task 3 | `completed` | current | `codex` | Task 2 | complete-resource precondition, shared HTML/API action, idempotency, stale-state, enqueue-intent, and race tests | app/store/artifact boundary: 752 passed; pipeline+job CAS and HTML delegation verified |
| Task 4 | `completed` | current | `codex` | Task 3 | drawer lifecycle matrix, accessibility assertions, and frontend proof | typecheck passed; frontend: 337 passed; production build passed with existing chunk warning |
| Task 5 | `completed` | current | `codex` | Task 4 | deterministic browser flow through owned bootstrap/server/DB | `powershell -ExecutionPolicy Bypass -File scripts/run_fitcv_review_e2e.ps1`: 1 passed; build passed; owned identity checks passed |
| Task 6 | `completed` | current | `codex` | Task 5 | telemetry schema tests and generated scorecard | `62 passed`; `docs/superpowers/evidence/2026-10-04-fitcv-current-scorecard.{json,md}`; explicit manifest-bound input; unavailable metrics preserved |
| Task 7 | `active` | current | `codex` | Task 6 | current-head identical-workload incumbent/candidate benchmark | R3 is historical source `7f351da`; rerun must bind source commit and declared-input fingerprint to current HEAD |
| Task 8 | `active` | current | `codex` | Task 7 | full verification and plan reconciliation | backend/frontend/owned-browser checks passed; candidate promotion rejected; fresh CI and final review remain |

## Activation Gate

- Plan-document review must return `implementation-ready` before activation.
- Lead controller changes `status: proposed` to `status: active` and records the
  next dependency-ready task before Task 1 starts.
- Task ledger is sole durable workflow state. A blocker keeps plan `active` or
  `blocked`; it does not satisfy completion unless separately approved as a
  deferral outside mandatory scope.

## Resume Gate

- This plan is already `active` and Task 1 already ran before the current review
  cycle; the new review cannot retroactively authorize that historical activation.
- Record the historical admission as `not evidenced` and preserve its committed
  execution facts. Do not claim Task 1 was admitted by the 2026-10-04 review.
- The 2026-10-04 review cycle did not authorize resume: two independent
  `review-1` audits returned `needs changes`. The prior HEAD and diff hash remain
  historical evidence only. After a fresh `implementation-ready` review, record
  current HEAD, working-tree diff hash, complete declared executable-input
  fingerprint, and dependency-ready next action here before Task 2 executes.
  Historical Task 1 admission remains `not evidenced` and is not retroactively
  changed.
- Fresh resume review passed on 2026-10-04 through one independent `review-1`
  audit. Current HEAD is `1b86a1199f692488b366567959f8a4364c0f91db`;
  working-tree diff hash is `0a4da0d0042321f13bb87bdb41c1693533c3912e50708d13a2fa5636c792a91b`;
  current declared-input hash is
  `a6de685fa34cfa105a57ab691e3212eac7d65dc9d3b331c5672e976e673ecf1b`;
  dependency-ready next action was Task 2. Historical Task 1 admission remains
  `not evidenced`.

- Reconciliation update on 2026-10-04: Task 2–5 execution evidence is now
  accepted from current working-tree tests and the owned browser run. The
  historical admission remains `not evidenced`; it is not reused as current
  admission proof.

- Final verification update on 2026-10-04: local backend suite passed with
  `3137 passed, 8 skipped`; frontend typecheck, `337` frontend tests, and
  production build passed; owned browser E2E passed; `git diff --check` and
  evidence secret scan passed; PR #85 CI passed all required checks. Task 7
  still has no eligible identical ten-repeat incumbent/candidate provider
  cohorts, so Task 8 remains blocked and no acceptance-state promotion is
  authorized.

## Task Breakdown

### Task 1: Reconcile verdict with committed executions and freeze baseline

**Purpose:** Prevent already-completed work from being reimplemented and establish
exact remaining scope.

**Files and symbols:**
- Inspect `git log`, `git show`, and `git diff origin/main...HEAD`.
- Inspect committed changes in `src/fitcv/agentic_cv_generation.py`,
  `src/fitcv_cp/run_artifact_contracts.py`, `src/fitcv_cp/worker_job.py`,
  `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, and frontend CV-review files.
- Reconcile `docs/superpowers/evidence/2026-10-04-fitcv-contract-convergence.md`,
  `docs/superpowers/evidence/2026-10-04-fitcv-generation-efficiency-baseline.md`,
  `docs/superpowers/evidence/2026-10-04-fitcv-generation-format-defect-experiment.json`,
  and predecessor plans, including
  `docs/superpowers/plans/2026-10-04-10-21-fitcv-contract-convergence-cost-baseline-plan.md`.
- Map executed outcomes to commits `c5fcec78`, `3303f810`, `93498433`,
  `2cf42479`, and `1b86a119`; preserve historical evidence as immutable.

**Task Function:** repository reconciliation and acceptance-boundary audit.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: source-first coordination; no implementation ambiguity.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent plan/ledger consistency review.

**Specification Coverage:** committed-execution reconciliation, P0 freeze, and
remaining P1-A/B scope.

**Required Skills:** `skill-plan-document-reviewer`, `skill-verification-before-completion`

**Dependencies:** clean plan admission; unrelated untracked files preserved.

**Steps:**
- [x] Confirm PR #84/committed fixes: sibling-claim leakage, filter-before-limit,
  retry evidence scope, artifact identity, persistence binding, and React proof checks.
- [x] Record exact gaps only: explicit-empty selection, plain-string skill bypass,
  generic prose, per-uncertainty actionability, drawer lifecycle, real review E2E,
  missing telemetry, and non-comparable optimization cohort.
- [x] Treat historical evidence as immutable audit records. Do not overwrite
  rejected P0-A or rejected generic first-pass experiment conclusions.
- [x] Preserve the production default without asserting its repair order here;
  Task 2 must identify the exact committed `HEAD` arm before experiment labels
  or promotion decisions are assigned.

**Authority:**
- Preauthorized local actions: read history, plans, evidence, source, and tests; update this plan's reconciliation notes only.
- Stop for: any request to change accepted P0 scope, rewrite historical evidence, or discard unrelated workspace files.

**Verification:**
- [x] `git status --short`; `git log --oneline --decorate -12`; `git diff --check`.
- Expected: committed execution map is reproducible and unrelated untracked files remain untouched.

**Exit criteria:** remaining work is mapped to Tasks 2–8; no duplicate implementation lane remains.

**Evidence:** HEAD `1b86a119` contains the scoped-repair commits; historical plans and evidence remain unmodified.

### Task 2: Close P1-A repair authorization at the source

**Purpose:** Remove evidence-scope widening from deterministic repair.

**Task Function:** backend correctness patch with focused regression proof.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded source/test change; no delegated implementation required.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent authorization and fallback review.

**Specification Coverage:** explicit selection states, authorized repair projection,
plain-string skill parity, generic-prose removal, and bounded fallback.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Dependencies:** Task 1 complete; current PR #84 evidence-scope commits retained.

**Files and symbols:**
- Modify `src/fitcv/agentic_cv_generation.py:_backfill_required_sections_from_profile`,
  `_run_repair_cycle`, and the generation call path in `_generate_fresh_from_analysis`.
- Add one canonical selection/projection helper in the same module only if existing
  analysis payload helpers cannot own it; do not add a second profile SSOT.
- Add one bounded internal repair-arm selector at the generation call boundary:
  name arms by observed order, not by assumption. Reconcile the exact `HEAD`
  behavior first. The production default must remain the committed incumbent;
  expose the alternate arm only through explicit experiment configuration until
  Task 7 promotion. Reuse existing generation config plumbing; do not add a new
  service or registry.
- Extend `tests/test_agentic_cv_generation.py` and relevant analysis/requirement
  support tests for both arms.

**Steps:**
- [x] Represent `LEGACY_UNAVAILABLE`, `EXPLICIT_NONEMPTY_SELECTION`, and
  `EXPLICIT_EMPTY_SELECTION` explicitly; never infer authorization from set
  truthiness.
- [x] Build one host-owned eligible repair projection from profile SSOT plus
  selection state before section repair. Include canonical evidence identity for
  dict and plain-string skills and preserve nested evidence parent semantics.
- [x] Make all repairable sections consume projection only. Plain-string skills
  such as `Python` or `Kubernetes` are eligible only when their canonical evidence
  is authorized.
- [x] Remove generic synthesized experience bullets such as
  `Delivered cross-functional work aligned with business goals.`
- [x] With explicit empty selection, return no local repair content and preserve
  bounded provider repair, `review_required`, or validation failure behavior.
- [x] Preserve legacy compatibility only when selection is genuinely unavailable.
- [x] Prove which arm is the committed incumbent by comparing `HEAD` and the
  working tree, add a default-behavior regression test, and restore any accidental
  default change before continuing. Candidate-only behavior stays explicit.
- [x] Keep the committed incumbent as production default until Task 7 promotion;
  candidate tests explicitly select the alternate arm and prove no arm ambiguity.

**Required regression proof:**
- absent selection keeps legacy compatibility behavior;
- explicit non-empty selection excludes sibling/unauthorized skill and experience;
- explicit empty selection repairs no profile content;
- plain-string and dict skills obey identical filtering;
- generic prose never appears;
- retry path preserves selection state.

**Authority:**
- Preauthorized local actions: edit generation code and focused tests; run backend unit tests.
- Stop for: any fallback that widens evidence beyond analysis selection or any schema change that lacks a compatibility test.

**Verification:**
- [x] `git show HEAD:src/fitcv/agentic_cv_generation.py`, the working-tree diff,
  and a default-arm regression test establish incumbent order; rerun the focused
  suites after correction. Focused suite: 11 passed.
- Expected: selection-state, projection, generic-prose, and retry-scope regressions pass.

**Exit criteria:** P1-A repair is fail-closed, symmetric, provider fallback remains
bounded, and the committed incumbent arm is recorded as `INCUMBENT_ARM` for Task 7.

### Task 3: Make P1-B uncertainty actionability authoritative

**Purpose:** Prevent actions against resolved or wrong uncertainties and preserve
idempotent review state.

**Task Function:** backend API/state contract hardening with atomic persistence proof.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: route/persistence ownership is local and explicit.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent API race/idempotency review.

**Specification Coverage:** per-uncertainty actionability, ownership, stale-source
protection, atomic resolution, refresh, and compatibility-route delegation.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`

**Dependencies:** Task 2 complete; canonical CV-review route remains source of truth.

**Files and symbols:**
- Modify `src/fitcv/pipeline_contracts.py:build_requirement_uncertainty`,
  `UncertaintyDisposition`, and `UncertaintyResolutionAction` only as needed.
- Modify `src/fitcv_cp/app.py:CanonicalCvReviewActionRequest`,
  `_canonical_cv_review_resource`, `_build_hitl_review_queue`,
  `apply_canonical_cv_review_action`, and compatibility HTML resolution branch
  `admin_run_cv_review_action`.
- Modify `frontend/src/features/cv-review/types.ts` request/resource types for the
  returned revision token and per-uncertainty fields.
- Modify authoritative requirement-resolution persistence
  `src/fitcv_cp/sqlite_store.py:save_requirement_resolution`; do not use
  candidate-profile authoring models or `_candidate_profile_review_resource_in_transaction`.
- Keep `src/fitcv_cp/review_identity.py:normalize_review_resolution_status` only
  for shared status normalization.
- Extend `tests/test_fitcv_cp/test_app.py`, `test_sqlite_store.py`, and contract tests.

**Steps:**
- [x] Add per-uncertainty `is_actionable`, `allowed_actions`, and authoritative
  resolution state to the canonical JSON resource.
- [x] On action, verify review-item identity, uncertainty ownership, pending state,
  allowed action, and resource revision before side effects.
- [x] Move complete canonical-resource validation into the authoritative
  requirement-resolution transaction. The store boundary must compare a
  transaction-bound resource token derived from review status, CV version, and
  uncertainty state while holding the write transaction, reject stale requests
  before mutation, and persist resolution plus durable enqueue intent together.
  Route-level prechecks remain advisory only; run-job CAS alone is insufficient.
- [x] Prove two different idempotency keys cannot replace one another's answer or
  enqueue duplicate regeneration, separately force a canonical resource revision
  change between route validation and persistence, and force enqueue failure to
  prove loser state and transaction rollback remain unchanged.
- [x] Return the existing typed stale/conflict response for stale or non-pending
  actions; do not enqueue duplicate work or mutate terminal state.
- [x] Keep answer payload scoped to the selected uncertainty and revision; React
  selection clearing and focus behavior are owned by Task 4.
- [x] Route HTML compatibility actions through the same guarded domain operation;
  add HTML-path stale, resolved, actionability, idempotency, and enqueue-intent
  tests. Separate direct persistence/enqueue logic is not acceptable.

**Required regression proof:** resolved uncertainty has no enabled actions;
wrong-uncertainty action is rejected; stale revision is rejected; duplicate action
replays safely; two competing actions yield exactly one winner and preserve its
answer; loser causes no replacement or duplicate enqueue; pending action persists
and refreshes canonical state. Use a controlled concurrent test/barrier or an
equivalent deterministic seam to force the revision-change window; do not treat
uniqueness-only first-writer-wins as proof of resource-precondition atomicity.

**Authority:**
- Preauthorized local actions: edit review contract/domain/persistence code and focused tests; run backend boundary tests.
- Stop for: any action path that mutates state before ownership, pending-state, or revision validation.

**Verification:**
- [x] Rerun `python -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_run_artifact_contracts.py` after the transaction-boundary change, plus the controlled revision-window race test. Result: 752 passed.
- Expected: per-uncertainty actionability, atomic resource precondition, stale
  revision, idempotent replay, and refresh tests pass.

**Exit criteria:** server is source of truth for action eligibility and terminal state.

### Task 4: Finish React lifecycle and evidence-drawer parity

**Purpose:** Render backend truth without inferred qualification or misleading
lifecycle state.

**Task Function:** frontend contract and accessibility implementation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing React surface; focused change with direct tests.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent lifecycle/accessibility review.

**Specification Coverage:** status union, evidence drawer semantics, focus,
announcements, keyboard access, proof display, and refresh behavior.

**Required Skills:** `skill-full-stack-integration`, `skill-test-driven-development`

**Dependencies:** Task 3 canonical resource/action fields complete.

**Files and symbols:**
- Modify `frontend/src/features/cv-review/types.ts`, `api.ts`, and
  `final-artifact-evidence.ts` to use one status/outcome union and canonical
  evidence fields.
- Modify `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx`.
- Modify review state/action wiring in
  `frontend/src/features/run-detail/run-detail-page.tsx` and
  `frontend/src/features/bookmarks/route.tsx`.
- Extend `frontend/src/test/job-evaluation.test.ts`,
  `frontend/src/features/cv-review/cv-api.test.tsx`, and
  `frontend/src/features/cv-review/final-artifact-evidence.test.ts`.

**Steps:**
- [x] Map `pending`, `review_required`, `rejected`, `cancelled`, and success
  independently in `FitEvidenceDrawer`; never display cancelled/pending as
  rejected and never collapse missing evidence into rejection.
- [x] Present requirement coverage separately from review status and remove copy
  that infers qualification success from absent/partial evidence. Add explicit
  tests for missing reasons/evidence and partial coverage.
- [x] Disable action controls for resolved uncertainties using backend
  `is_actionable`/`allowed_actions`; show read-only resolution state.
- [x] Preserve keyboard access, focus return, accessible names, status/live-region
  announcements, contrast, responsive layout, reduced-motion behavior, and theme
  support, with drawer-specific assertions rather than aggregate test counts.
- [x] Show one-page/native-render proof only when verified backend proof passes;
  add stale-cache, post-trim, and rejected-finalization cases to the proof matrix.

**Authority:**
- Preauthorized local actions: edit declared React/API/type/test files and run frontend unit/type checks.
- Stop for: any UI state inferred from text, missing backend field, or accessibility regression in affected controls.

**Verification:**
- [x] Add and run drawer-specific lifecycle/accessibility tests in
  `frontend/src/test/job-evaluation.test.ts` plus existing review tests, then run
  `npm --prefix frontend run typecheck` and `npm --prefix frontend run test -- --run`.
  The earlier 334-test result and build result remain historical only.
- [x] Rerun `npm --prefix frontend run build`; existing chunk-size warning is
  acceptable only if no new warning or behavior regression appears.
- Expected: status union, evidence-drawer lifecycle, focus, announcement, and
  proof-display assertions pass for every declared state.

**Exit criteria:** UI state, evidence qualifiers, actions, and proof match canonical API.

### Task 5: Prove one real deterministic review browser flow

**Purpose:** Close frontend/backend integration proof with actual route contracts.

**Task Function:** deterministic full-stack browser verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: browser capability is local and test-owned.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent route/fixture and accessibility review.

**Specification Coverage:** review-required display, answer submission, persisted
resolution, refresh, read-only resolved state, lifecycle labels, and one-page proof.

**Required Skills:** `skill-full-stack-integration`, `skill-verification-before-completion`

**Dependencies:** Tasks 3–4 complete; production frontend build and isolated backend
fixture available.

**Files and symbols:**
- Extend `frontend/e2e/integration-flows.spec.ts` using existing test harness and
  backend-shaped fixtures/routes; do not create a fake mutation contract.
- Add test-only credential-resolver injection at
  `src/fitcv/llm_runtime.py:execute_llm_task`, defaulting to existing credential
  resolution in production. The owned E2E server must pass an explicit fixture
  resolver and custom adapter so routing validation receives a fixture key without
  calling `resolve_llm_api_key`; add a focused negative test proving credential
  lookup and outbound transport are never invoked. Keep this seam unavailable to
  normal production startup.
- Add `scripts/seed_fitcv_review_e2e.py` as disposable SQLite seed owner; seed
  one review-required job, one final-artifact envelope, and one pending uncertainty
  with deterministic IDs. Persist the fixture profile/settings and a bounded
  regeneration outcome. Name and use a test-only runtime seam that bypasses
  credential resolution before adapter selection (for example, explicit
  `execute_llm_task(..., adapter=...)` injection at the owned server entrypoint);
  remove API-key environment values, install the deterministic adapter before
  app creation, deny outbound traffic, and prove no credential lookup/provider
  request occurs. Never rely on adapter injection after routing validation and
  never use route mocks.
  Emit a manifest containing the absolute database path, seeded IDs, expected
  regeneration terminal state, and cleanup ownership.
- Add `scripts/run_fitcv_review_e2e.ps1` as the setup/bootstrap owner. It must
  start only the owned server process, capture secret-safe effective diagnostics
  (PID, resolved database path, `FITCV_LOCAL_MODE`, inline-execution state), and
  refuse a port/database identity mismatch before browser mutation.
- Add `scripts/serve_fitcv_review_e2e.py` as the test-owned server launcher. It
  must install a deterministic provider adapter inside the server process before
  app creation, accept the seed manifest, reject unexpected provider requests and
  outbound provider access, and expose its effective fixture/identity diagnostics
  to the bootstrap owner. Keep routes, worker, validation, rendering, and
  persistence real.
- Reuse existing review API routes in `frontend/src/features/cv-review/api.ts`
  and canonical handlers in `src/fitcv_cp/app.py`; keep review GET/POST unmocked.
- Build frontend before browser run: `npm --prefix frontend run build`.
- Create a unique fresh path with `$e2eRoot = Join-Path $env:TEMP ("fitcv-p1ab-e2e-" + [guid]::NewGuid().ToString("N"))`; first assert the directory and database path do not exist, then create the directory. Set process-scoped
  `$env:FITCV_LOCAL_MODE = "0"`, `$env:FITCV_CP_INLINE_EXECUTION = "1"`, and
  `$env:FITCV_CP_SQLITE_PATH = Join-Path $e2eRoot "control-plane.sqlite3"`.
- Run `python scripts/seed_fitcv_review_e2e.py --database "$env:FITCV_CP_SQLITE_PATH"`
  before startup; assert the database was absent before seed and seed reports the
  same absolute database path.
- Start `python scripts/serve_fitcv_review_e2e.py --manifest <seed-manifest>`
  with only those process-scoped settings; the launcher starts Uvicorn after
  installing the provider fixture. Wait for
  `Invoke-WebRequest http://127.0.0.1:8000/healthz` and verify the owned
  process diagnostics show non-local mode plus the seeded database identity
  before browser mutation.
- After answer submission, poll the returned regeneration job through the owned
  worker/status boundary until the manifest's expected terminal state is reached;
  only then refresh the canonical review resource and assert persistence. Stop
  the owned server before cleanup, and fail on timeout or unexpected terminal
  state. Run with provider credentials absent and assert the persisted answer and
  expected artifact terminal state.
- Stop the owned server first, then remove the disposable directory; never touch
  personal-local storage or an existing user database.

**Flow:**
- [x] Load a review-required job with backend-owned final-artifact evidence and one
  pending uncertainty.
- [x] Assert status, reason, requirement coverage, evidence drawer contents, and
  one-page proof.
- [x] Select uncertainty, answer it, submit the allowed action, observe persisted
  response, refresh, and assert resolved read-only state.
- [x] Assert pending and cancelled labels are not rejected; assert focus/status
  announcement and no duplicate action.

**Authority:**
- Preauthorized local actions: edit browser test, declared seed helper, and setup files; build/start/stop the owned local server; run isolated browser flow.
- Stop for: route stubbing that bypasses canonical backend behavior, local-mode activation, database identity mismatch, or missing real request/response evidence.

**Verification:**
- [x] Run the owned bootstrap, not plain Playwright alone:
  `powershell -File scripts/run_fitcv_review_e2e.ps1`; the script must build the
  frontend, create/refuse-stale disposable paths, seed the manifest, start the
  owned server, verify PID/database/mode identity, invoke the browser flow, poll
  regeneration to terminal state, stop the owned server, and clean up in a
  finally path. The browser test itself remains unmocked.
- Expected: unmocked review flow persists answer, refreshes, locks resolved uncertainty, and passes lifecycle/accessibility assertions against isolated DB.

**Exit criteria:** one deterministic browser proof covers current backend route, persistence, refresh, lifecycle, and accessibility-critical interaction.

### Task 6: Complete trace telemetry and generated current scorecard

**Purpose:** Make optimization decisions from deployed behavior, not source
inspection or incomparable samples.

**Task Function:** runtime measurement and scorecard generation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing trace and benchmark owners; no new telemetry service.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent metric/denominator review.

**Specification Coverage:** stage timing, failure attribution, local-repair savings,
cache/render/proof reuse, resolution reuse, and generated current scorecard.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Dependencies:** Task 5 complete; current trace contract remains backward-compatible.

**Files and symbols:**
- Modify trace construction and efficiency aggregation in
  `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`,
  `_update_live_trace_validation_cycle`, and `_update_efficiency_summary`.
- Modify generation/persistence timing owners in
  `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/run_artifact_contracts.py`, and
  `src/fitcv_cp/sqlite_store.py`; retrieval timing owner is
  `src/fitcv/agentic_cv_analysis.py` and queue timing owner is the worker enqueue/
  start boundary, not generation aggregate timing.
- Modify `scripts/benchmark_cv_efficiency.py` and
  `scripts/evaluate_requirement_support_live.py`.
- Add `tests/fixtures/fitcv-p1ab-repair-experiment.json` as frozen canonical workload input and validate its hash before either arm runs.
- Add `scripts/run_fitcv_repair_experiment.py` as bounded producer for isolated
  incumbent/candidate runs; accept explicit fixture, arm, repeat count, and SQLite
  path, plus a credential-free `--preflight-fixture` mode that validates cohort
  shape before any provider-backed run. Load local credentials through existing
  config/.env handling without emitting secrets. Before either arm runs, compute
  a complete declared-input fingerprint over producer, bootstrap, server,
  benchmark, verifier, fixture, and canonical source files. Output manifest must
  contain that fingerprint plus all repeat run IDs, fixture hash, source commit,
  working-tree diff hash, arm, repeat count, and database path; missing or changed
  input hashes reject aggregation.
- Extend `scripts/benchmark_cv_efficiency.py` with `--run-manifest` so aggregation
  consumes every manifest run ID and rejects incomplete or duplicate cohorts.
- Extend `scripts/verify_fitcv_acceptance.py` with experiment-report arguments so
  eligibility checks bind to generated arm reports without mutating tracked
  `config/acceptance_state.yaml`.
- Add telemetry/scorecard tests in `tests/test_benchmark_cv_efficiency.py` and
  focused backend tests.
- Generate one current scorecard under `docs/superpowers/evidence/`; keep prior
  reports immutable.

**Steps:**
- [x] Define one canonical trace schema and map each metric to its owner and
  denominator before editing: queue wait at worker boundaries; analysis and
  retrieval in `src/fitcv/agentic_cv_analysis.py`; content planning/provider/
  validation/local repair in generation; render/persistence in artifact/store
  boundaries. Each field records value plus measured/unavailable state.
- [x] Persist `queue_wait_ms`, `analysis_ms`, `retrieval_ms`,
  `content_planning_ms`, `provider_ms`, `validation_ms`, `local_repair_ms`,
  `render_ms`, and `persistence_ms` with explicit unavailable semantics.
- [x] Persist validation failure causes, including missing sections, unsupported
  claims, page-fit failures, grounding failures, and final-artifact failures.
- [x] Persist `local_repair_attempted`, `local_repair_succeeded`,
  `local_repair_failed`, `provider_retry_avoided`, `tokens_avoided`, and
  `provider_latency_avoided`.
- [x] Persist proof reuse, provider calls avoided, renders avoided, tokens avoided,
  questions shown, human actions, resolution reuse, questions avoided, and review
  time using valid denominators.
- [x] Produce one generated scorecard with sections `CORRECTNESS`, `PRODUCT PARITY`,
  `EFFICIENCY`, and `HUMAN EFFORT`.
- [x] Mark metrics unavailable rather than zero when source traces cannot prove them.
- [x] Require verifier-backed current-contract, coverage, diversity, attribution,
  and conflict-free eligibility before treating scorecard values as comparable;
  values with missing stage ownership or denominator remain `unavailable`, never
  zero.

**Authority:**
- Preauthorized local actions: edit trace/benchmark/evidence code and tests; generate scorecard evidence without credentials in files or output.
- Stop for: fabricated denominators, hidden unavailable metrics, or API-key exposure.

**Verification:**
- [x] Focused telemetry tests; `python scripts/benchmark_cv_efficiency.py --help`; `python scripts/benchmark_cv_efficiency.py --run-manifest .tmp/fitcv-task6-scorecard-manifest.json --database .tmp/fitcv-candidate-clone-20261004.sqlite3 --output-json docs/superpowers/evidence/2026-10-04-fitcv-current-scorecard.json --output-markdown docs/superpowers/evidence/2026-10-04-fitcv-current-scorecard.md`; `git diff --check`.
- Expected: unavailable metrics stay unavailable, denominators are explicit, and scorecard has four required sections.

**Exit criteria:** current scorecard can explain correctness, parity, cost, latency, reuse, and human effort from persisted trace facts.

### Task 7: Run one identical-workload optimization experiment

**Purpose:** Test enabled deterministic repair against incumbent provider retry
without repeating the rejected or incomparable experiments.

**Task Function:** controlled performance experiment and promotion decision.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded local benchmark; no external delegation required.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent correctness and cost-gate review.

**Specification Coverage:** identical workload, arm isolation, correctness gates,
provider/token/latency savings, and incumbent retention.

**Required Skills:** `skill-performance-optimization`, `skill-verification-before-completion`

**Dependencies:** Task 6 scorecard and producer complete; production default is
unchanged, and incumbent/candidate labels come from Task 2's verified mapping.

**Files and symbols:**
- Use current generation path in `src/fitcv/agentic_cv_generation.py`.
- Record `INCUMBENT_ARM=local_first` and `CANDIDATE_ARM=provider_first` from
  `src/fitcv/agentic_cv_generation.py`; reject missing, invalid, or identical
  arm selectors before any provider call. Production default remains
  `local_first`.
- Use `scripts/run_fitcv_repair_experiment.py` to produce isolated runs with the
  exact `INCUMBENT_ARM` and `CANDIDATE_ARM` mapping emitted by Task 2, frozen
  fixture fingerprint, repeat count `10`, and separate SQLite files. Do not infer
  that `provider_first` is incumbent; the mapping must bind to verified `HEAD`
  behavior and the candidate is the opposite explicit arm.
- Use the exact fresh paths emitted by each producer manifest for
  `scripts/benchmark_cv_efficiency.py --database <manifest.database_path>
  --run-manifest <manifest.path> --output-json <role-scorecard.json>
  --output-markdown <role-scorecard.md>`; never substitute a fixed temp path.
- Use the corresponding role-bound scorecards with
  `scripts/verify_fitcv_acceptance.py --experiment-json <role-scorecard.json>
  --experiment-markdown <role-scorecard.md> --output <role-eligibility.json>`;
  checks bind to generated fixture/source hashes, coverage, diversity, attribution,
  and conflict-free evidence without changing tracked acceptance state.
- Write only new dated evidence under `docs/superpowers/evidence/`.
- Do not alter `config/acceptance_state.yaml` or `artifacts/acceptance_state.json`
  unless an explicitly authorized acceptance-state update is separately approved.
- Before paid/provider-backed execution, run the credential-free fixture preflight
  and freeze an eligible cohort containing at least two distinct job types and
  complete coverage for every required evidence category. This preflight validates
  shape only; post-run verifier eligibility consumes generated scorecards and
  remains a separate gate. Missing credentials or an ineligible cohort is
  `unavailable/rejected`, not a completed comparable experiment. Only an
  eligible, comparable negative result may close Task 7 without promotion.

**Protocol:**
- [x] Freeze one representative workload fingerprint, runtime/config/model,
  fixture hash, source commit, working-tree diff hash, complete declared-input
  fingerprint, acceptance rubric, and repeat count before either arm executes.
  Persist the same executable-input fingerprint in both manifests and require
  equality before aggregation; Task 8 only revalidates this pre-run identity.
- [x] Refuse pre-existing arm databases, cache directories, or manifests; create
  unique per-run/per-arm paths and record cache/reuse policy in each manifest.
- [x] Run the producer twice using the recorded mapping, for example
  `--arm $env:FITCV_INCUMBENT_ARM` and `--arm $env:FITCV_CANDIDATE_ARM`; write
  role-bound manifests/databases only after fresh-path checks pass. The exact
  commands and resolved arm values must be recorded in evidence.
- [x] Verify both manifests contain exactly 10 unique run IDs, at least two job
  types, complete coverage, and identical fixture/model/runtime/executable-input
  fingerprints.
  Compare normalized configuration fingerprints with only the declared repair-arm
  selector excluded; assert exact incumbent/candidate arm values separately and
  reject every other config difference.
- [x] Run incumbent and candidate on identical job/profile/analysis inputs with
  isolated repeats and no secret values in output.
- [x] Compare first-pass acceptance, final acceptance, grounding defects,
  unsupported claims, one-page native proof, review outcomes, provider calls,
  tokens, stage p50/p95, total wall-clock, local-repair success, and retry avoidance.
- [x] Require candidate non-regression on correctness and lower total workload
  calls/tokens/latency before promotion.
- [x] If cohort is missing, non-comparable, or any hard gate fails, reject
  promotion and retain incumbent. Record diagnostic result; do not claim savings.

**Authority:**
- Preauthorized local actions: run bounded local benchmark and write dated evidence with secret-safe redaction.
- Stop for: non-identical workload, missing denominator, acceptance regression, grounding leakage, or unavailable API credentials.

**Verification:**
- [x] Run `python scripts/run_fitcv_repair_experiment.py --fixture
  tests/fixtures/fitcv-p1ab-repair-experiment.json --preflight-fixture`; expected:
  no provider request, at least two job types, complete required-category coverage,
  and a frozen fixture hash before either arm starts.
- [x] `python scripts/run_fitcv_repair_experiment.py --help`; after preflight
  passes, run both fixture-bound producer commands using the recorded
  `INCUMBENT_ARM`/`CANDIDATE_ARM` mapping.
- [x] Run both manifest-bound `scripts/benchmark_cv_efficiency.py` commands from `Files and symbols`; each scorecard contains all ten unique repeat run IDs.
- [x] Run both experiment-bound `scripts/verify_fitcv_acceptance.py` commands from `Files and symbols`; both report `PASSED` and bind to generated fixture/source hashes without changing tracked acceptance state.
- [ ] Re-run after current-head code settles; compare evidence hashes and generated scorecards; fingerprints must match and no secrets may appear. R13 is historical only and cannot close this gate.

**Exit criteria:** candidate promoted only with measured total-workload improvement; otherwise explicit rejection with incumbent retained.

**Historical result (2026-10-04; superseded):** current-source rerun completed with two eligible,
identical ten-repeat provider-backed cohorts. `provider_first` produced 8
accepted CVs versus 7 for `local_first`, used 13 versus 16 provider calls,
59,567 versus 73,246 tokens, and 430,759.423 versus 447,843.781 ms wall time.
Candidate and incumbent acceptance verifiers both passed. Independent Task 8
review was still required; this result is historical and does not establish the
current optimization decision.

**Historical result (2026-10-05; superseded by R5):** fresh source-bound cohorts completed after
verifier hardening. `provider_first` accepted 10/10 versus `local_first` 5/10,
used 10 versus 15 provider calls, 47,367 versus 64,801 tokens, and
233,251.089 versus 268,544.321 ms wall time. Both acceptance verifiers passed.
The result was positive for the candidate, but it is not the final optimization
decision because the later R5 rerun used the completed declared-input inventory.
Evidence: `docs/superpowers/evidence/2026-10-05-fitcv-p1ab-provider-backed-convergence-r2.md`.

**Historical decision evidence (2026-10-05, R13):** comparable seeded cohorts
completed on source `2564e20`; this record does not certify later branch heads.
Both arms accepted 10/10, used 15 provider calls,
and had 5 regenerations. `provider_first` used 70,367 versus 70,282 tokens,
194,170 versus 216,303 generation ms, and 285,228.900 versus 308,266.482
end-to-end wall ms. Promotion is rejected because token cost increased;
`local_first` remains default. Evidence:
`docs/superpowers/evidence/2026-10-05-fitcv-p1ab-provider-backed-convergence-r13.md`.
R12 remains historical and is superseded because it predates the final caller-bound
regression patch.

### Task 8: Final verification and plan reconciliation

**Purpose:** Prove closure and retire duplicate workflow truth.

**Task Function:** final acceptance verification and durable plan reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final authority remains with lead controller.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent final readiness review.

**Specification Coverage:** all P1-A/B closure gates, final-artifact proof,
optimization decision, evidence immutability, and P1-C/P2 deferral.

**Required Skills:** `skill-verification-before-completion`, `skill-plan-document-reviewer`

**Dependencies:** Tasks 2–7 complete; no unresolved mandatory task.

**Files and symbols:**
- Run final checks across all Task 2–7 targets.
- Reconcile `docs/superpowers/plans/2026-10-03-fitcv-integration-convergence-plan.md`
  `docs/superpowers/plans/2026-10-03-fitcv-final-artifact-integration-optimization-plan.md`,
  and `docs/superpowers/plans/2026-10-04-10-21-fitcv-contract-convergence-cost-baseline-plan.md`
  against actual proof. Map each plan to commits and remaining proof; do not delete
  historical evidence.
- Update only the canonical current scorecard and plan reconciliation notes.

**Steps:**
- [x] Run backend full suite and focused boundary tests.
- [x] Run frontend typecheck, unit suite, production build, and browser E2E.
- [x] Run `git diff --check`, secret scan appropriate to repository, and inspect
  generated evidence for credentials/raw profile leakage.
- [x] Confirm every P1-A/B criterion, final-artifact identity, one-page proof,
  persistence identity, review actionability, browser parity, and telemetry gate.
- [x] Mark P1-C deferred and P2 frozen. Do not promote accepted-state files without
  separate authorization.
- [x] Revalidate the fresh `implementation-ready` resume record captured before
  Task 2, including current HEAD, working-tree diff hash, complete declared
  executable-input fingerprint, and dependency-ready next action. Record prior
  Task 1 admission as `not evidenced`; do not use this review as retroactive
  admission proof.

Resume reconciliation (2026-10-05): historical review head `2564e20` had clean
tracked state before final evidence-only updates; historical declared-input fingerprint is
`7813b2336ffa847549e42eb1b1566a541454ae492ac621151e8211c81237ac99`; the
record is not current-head freshness proof. Prior Task 1 admission remains
`not evidenced`.

- R3 is latest historical paired evidence: both arms accept 5/10; `provider_first`
  uses more tokens and wall time, so promotion remains rejected. R3 source
  `7f351da` is not current-head proof. Task 8 remains active pending current-head
  evidence and final review. Production default remains `local_first`.

**Authority:**
- Preauthorized local actions: run declared verification and reconcile plan/evidence text.
- Stop for: any failed hard gate, stale evidence, unresolved plan contradiction, or missing proof.

**Verification:**
- [x] Run each command with immediate exit-code propagation; do not chain
  unchecked native commands:
  `python -m pytest -q`; if nonzero stop. Then `npm --prefix frontend run typecheck`; if nonzero stop. Then `npm --prefix frontend run test -- --run`; if nonzero stop. Then `npm --prefix frontend run build`; if nonzero stop. Then `powershell -File scripts/run_fitcv_review_e2e.ps1`; if nonzero stop. Finally `git diff --check`.
- Expected: mandatory backend/frontend/browser proof passes, generated evidence is secret-safe, and no task remains pending or blocked. Fresh local proof: backend `3180 passed, 8 skipped`; frontend `typecheck`, `337 tests`, build, and browser E2E passed.

**Exit criteria:** every mandatory task is `completed` with fresh proof; a blocker
keeps plan `active` or `blocked` and cannot close the plan; no acceptance claim is
made on source inspection alone.

## Verification

Final proof must establish:

- [x] explicit selection presence semantics and fail-closed empty selection; expected: absent, non-empty, and empty states are distinct in focused tests.
- [x] one authorized repair projection for every profile-backed repair section; expected: no sibling or plain-string leakage.
- [x] no unsupported generic repair prose; expected: forbidden fallback text absent from outputs/tests.
- [x] per-uncertainty server-side actionability, stale-source protection, atomic conflict handling, and idempotency; expected: competing requests cannot replace the winner.
- [x] truthful React lifecycle and evidence-drawer behavior with accessibility proof; expected: pending/cancelled are not rejected and resolved controls are read-only.
- [x] one browser flow against current backend routes with persisted refresh; expected: isolated non-local backend and disposable DB only.
- [x] identity-bound final-artifact proof across fresh, cached, regenerated, persisted, and review-closed paths.
- [x] complete timing, failure-cause, savings, cache, render, proof, and resolution-reuse telemetry with explicit unavailable semantics.
- [ ] one identical-workload experiment with current-source paired cohorts;
  fixture, source, config, runtime, and all repeat IDs must match across arms;
  rerun after the final race fix must decide promotion or rejection.
- [x] immutable historical evidence, no secret leakage, P1-C deferred, and P2 frozen.

Run `skill-verification-before-completion` for final status. Source inspection,
unit tests alone, or browser evidence alone cannot close this plan.

## Rollback And Stop Conditions

- Keep the verified `INCUMBENT_ARM` behavior as production default until Task 7
  hard gates pass. Promotion eligibility does not authorize changing the default;
  any default change requires separate explicit approval.
- If repair authorization cannot be proven, disable local repair for that case and
  route to bounded provider repair or `review_required`; never widen evidence.
- If review action validation fails, leave persisted state unchanged and return the
  typed conflict/error contract.
- If frontend/backend fields diverge, stop browser acceptance and repair the
  canonical contract owner first.
- If timing or savings denominators are incomplete, report `unavailable`, reject
  optimization promotion, and retain the verified `INCUMBENT_ARM` behavior.
- If secret leakage, identity mismatch, stale proof, non-one-page artifact, or
  grounding regression appears, stop and preserve last known accepted behavior.

## Completion Criteria

1. Tasks 1–8 are `completed` with task-local proof; any blocker leaves the plan
   `active` or `blocked` and requires explicit approved deferral before scope changes.
2. P1-A/B backend and frontend contracts reconcile with source, tests, and current API.
3. Every committed execution claimed as complete has fresh supporting evidence.
4. Final-artifact identity/page-fit proof is consistent across all accepted paths.
5. Optimization result is reproducible or explicitly rejected; no unsupported savings claim exists.
6. One generated scorecard replaces repeated current-state closure documents; historical evidence remains immutable.
7. P1-C remains explicitly deferred until this plan and one comparable experiment close.
8. P2 remains frozen.
9. For historical work, preserve Task 1 admission as `not evidenced`; fresh
   resume evidence must be recorded before Task 2. Plan status changes
   `proposed` → `active` before new execution, then `active` → `completed` only
   after final verification returns `verified`.

This plan does not authorize commit, push, PR creation, merge, or acceptance-state
promotion. Those require explicit user approval after fresh verification.
