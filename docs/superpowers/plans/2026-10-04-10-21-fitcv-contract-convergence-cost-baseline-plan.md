---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-contract-convergence-cost-baseline
targets:
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv/agentic_cv_generation.py
  - frontend/src/features/cv-review/
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx
  - frontend/src/features/job-evaluation/components/PipelineOutcome.tsx
  - scripts/render_acceptance_state.py
  - scripts/benchmark_cv_efficiency.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_acceptance_state.py
  - tests/test_benchmark_cv_efficiency.py
  - frontend/e2e/integration-flows.spec.ts
  - frontend/src/features/cv-review/final-artifact-evidence.test.ts
  - frontend/src/features/cv-review/cv-api.test.tsx
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - docs/superpowers/evidence/
---

# FitCV Contract Convergence Then Generation-Cost Baseline

## Verdict Review

The supplied verdict is correct. Merge `7bc1d1f6` establishes stable backend
acceptance for P0, P1-A, and P1-B within frozen scope. Remaining defects sit at
the product boundary:

- backend final-artifact proof is structured, while React still accepts a
  scalar interpretation and can reject valid native proof;
- persisted proof needs artifact-version and content-checksum identity binding;
- React renders uncertainty identifiers instead of backend questions and does
  not bind every action to one uncertainty;
- lifecycle and qualification evidence presentation collapses distinct backend
  states into passed/rejected output;
- `config/acceptance_state.yaml` is canonical, while generated
  `artifacts/acceptance_state.json` can drift;
- current telemetry cannot attribute proof reuse, avoided provider work, or
  avoided renders;
- `generation_format_defect` is the dominant recorded regeneration cause and is
  the only optimization subtype selected for this milestone.

The roadmap statement after this plan is:

> P0 is complete within frozen evaluation scope. P1-A/B backend acceptance is
> complete. One bounded frontend/backend convergence patch remains. Then one
> measured optimization targets repeated generation cost. P1-C and roadmap P2
> remain deferred.

## Goal

Finish frontend/backend final-CV contract convergence once, prove it through
one real browser flow and direct backend tests, then run one identical-workload
generation-efficiency experiment. Promote no candidate unless correctness gates
remain intact and total workload cost per accepted CV decreases.

## Preserved Behavior

- Keep backend P0-B and P0-C frozen-scope evidence unchanged.
- Keep current P0-A rejection and incumbent production default.
- Keep canonical review actions `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, and
  `OVERRIDE_BLOCK`.
- Keep stale cached rerender local; failed local rerender stays
  `review_required` without provider fallback.
- Keep idempotency, replay ownership, job-scoped uncertainty, and persisted
  resolution semantics from PR #82.
- Preserve all unrelated untracked workspace files. Do not stage, delete, or
  rewrite them.

## Explicit Exclusions

- No GraphRAG, larger retrieval pool, reranker, verifier model, new agent,
  vector store, online ESCO dependency, provider-routing layer, or monitoring
  service.
- No P1-C market-gap implementation in this milestone.
- No roadmap P2 retrieval work.
- No broad model/provider comparison. The experiment has one incumbent arm and
  one narrowly scoped `generation_format_defect` correction arm.
- No status promotion based on source inspection alone.

## Implementation Outcomes

1. One backend-owned, identity-bound final-CV evidence envelope feeds fresh,
   cached, regenerated, resolution-triggered, and review-finalized artifacts.
2. Canonical CV review JSON exposes backend uncertainty fields and final-artifact
   evidence without a second frontend interpretation.
3. React shows truthful lifecycle state, actionable uncertainty, and verified
   one-page/native-render proof from production-shaped payloads.
4. YAML acceptance state remains SSOT; generated JSON is regenerated and CI
   rejects drift.
5. One deterministic Playwright flow proves review resolution, refresh, status,
   evidence, and preview/download identity against current routes.
6. Trace and benchmark contracts measure total-workload cost, accepted-artifact
   cost, stage latency, retry categories, reuse, avoided work, and human effort.
7. One `generation_format_defect` optimization is measured on identical workload
   and runtime. Candidate is promoted only when hard gates pass and cost falls.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`; one lead executor owns ordered edits in current
  workspace.
- Executor: Codex lead.
- Isolation: current workspace. Existing untracked files are read-only context
  and remain untouched.
- Required skills: `skill-full-stack-integration`,
  `skill-backend-verification`, `skill-test-driven-development`,
  `skill-performance-optimization`, `skill-verification-before-completion`.
- Shared-write rule: `run_artifact_contracts.py`, backend projection code, API
  types, and acceptance evidence are shared SSOT surfaces. Serialize all tasks.
- Commit policy: no commit, push, merge, or acceptance-status promotion is part
  of this plan. Those actions require separate authorization after fresh
  verification.
- Stop rule: stop and record a blocker when current source, tests, or persisted
  evidence contradict the contract fields named below. Do not invent a second
  schema to bypass the conflict.

## Task Breakdown

### Task 1: Build one identity-bound final-artifact envelope

**Purpose:** Replace scattered render-proof interpretation with one backend
schema that can prove artifact identity and native one-page acceptance.

**Task Function:** Backend contract owner.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcomes 1 and 6; P1-A final-artifact acceptance;
  preserved stale-rerender behavior.

**Required Skills:** `skill-backend-verification`,
  `skill-test-driven-development`.

**Files And Symbols:**
- Modify `src/fitcv_cp/run_artifact_contracts.py`: `accepted_cv_artifact_event_v1`,
  `build_accepted_cv_effort_projection`; add
  `build_final_cv_evidence_envelope` beside existing final-artifact helpers.
- Modify `src/fitcv_cp/worker_job.py`:
  `execute_pipeline_run`, `execute_cv_regenerate_once`, and
  `_build_cv_generation_debug_payload`.
- Modify `src/fitcv_cp/sqlite_store.py`: `_cv_projection`,
  `list_cv_versions`, `lookup_reusable_cv_versions`, and final-CV preview/download
  projections.
- Add focused coverage in
  `tests/test_fitcv_cp/test_run_artifact_contracts.py`,
  `tests/test_fitcv_cp/test_worker_job.py`, and
  `tests/test_fitcv_cp/test_sqlite_store.py`.

**Dependencies:** None.

**Authority:** May add one shared backend helper and update its direct callers.
May not change accepted P0/P1 evaluation fixtures or introduce a second final
artifact schema. Stop on any required database migration or external provider
change; record it instead of widening scope.

**Steps:**
1. Define envelope fields exactly as
   `contract_version`, `artifact_version_id`, `content_checksum`,
   `evidence_state`, `page_count`, `page_fit_status`, `render_status`,
   `artifact_checksum`, `render_proof`, `trace_id`, `run_job_id`, and
   `trim_count`.
2. Set `evidence_state=passed` only when artifact version identity and content
   checksum match stored CV version data, `page_count == 1`, page fit is pass,
   render status is pass, and artifact checksum is a valid SHA-256 value.
3. Return explicit failed or missing state for stale, incomplete, mismatched,
   multi-page, and failed-render proof. Never infer acceptance from markdown
   text or a stringified object.
4. Route fresh generation, cached reuse, regenerate-once,
   resolution-triggered regeneration, and review finalization through the same
   builder before persistence or API serialization.
5. Preserve compatibility fields only as projections of the envelope; do not
   let compatibility fields become new authorities.

**Verification:**
```powershell
python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py -k "final_artifact or render_acceptance or cv_version or regenerate"
```
Required cases: valid native proof; wrong `artifact_version_id`; wrong
`content_checksum`; `page_count=2`; non-pass render status; stale or incomplete
proof; cached rerender failure with zero provider fallback.

**Exit Criteria:** All producers and projections emit the same envelope fields;
identity mismatches cannot produce `evidence_state=passed`; focused backend tests
pass.

### Task 2: Close canonical review API and persistence parity

**Purpose:** Make one backend review resource/action contract authoritative for
uncertainty resolution, final-artifact evidence, persistence, replay, and
refresh.

**Task Function:** Backend/API integration.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcomes 1, 2, and 5; P1-B integration closure.

**Required Skills:** `skill-full-stack-integration`,
  `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- Modify `src/fitcv_cp/app.py`: `_canonical_cv_review_resource`,
  `get_canonical_cv_review`, `apply_canonical_cv_review_action`,
  `get_canonical_cv_versions`, `preview_canonical_cv`, and
  `download_canonical_cv`.
- Use existing backend review storage and resolution functions in
  `src/fitcv_cp/app.py` and `src/fitcv_cp/sqlite_store.py`; preserve admin HTML
  routes as compatibility adapters to the same domain operation.
- Update `tests/test_fitcv_cp/test_app.py` and
  `tests/test_fitcv_cp/test_sqlite_store.py`.

**Dependencies:** Task 1.

**Authority:** May change response shape only through the canonical JSON route
and its typed consumers. May not remove admin compatibility routes, weaken
idempotency, bypass stale-source checks, or enqueue duplicate regeneration.

**Steps:**
1. Return `review_item_id`, `reason_code`, `uncertainties`,
   `resolution_key`, `allowed_actions`, `resolution_status`, `status`,
   `cv_version`, and the Task 1 final-artifact envelope from
   `GET /runs/{run_id}/jobs/{run_job_id}/cv-review`.
2. Ensure each uncertainty includes `uncertainty_id`, `affected_fact`,
   `question`, `recommended_disposition`, `resolution_key`, and current
   resolution state when present.
3. Require action identity to match the selected review item and uncertainty;
   keep resolution persistence before regeneration enqueue and preserve
   idempotent replay responses.
4. Return refreshed review resource and regeneration job identity after an
   action; never require React to reconstruct state from a redirect or admin
   HTML response.
5. Return the same envelope from version listing and final-CV preview/download
   metadata where current API consumers need proof identity.

**Verification:**
```powershell
python -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -k "canonical_cv or cv_review or hitl_review or requirement_resolution or idempotent_action or final_artifact"
```
Add direct success, stale identity, invalid uncertainty, replay, duplicate
enqueue, and persistence-failure tests. Verify action side effects and final
stored state, not only HTTP status.

**Exit Criteria:** One JSON resource/action contract serves React and admin
compatibility routes; backend tests prove identity, persistence, idempotency,
refresh, and no duplicate enqueue.

### Task 3: Make React render backend truth

**Purpose:** Remove scalar proof coercion, opaque uncertainty labels, and
lifecycle-state collapse from the active product flow.

**Task Function:** Frontend contract consumer.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcomes 2 and 3; P1-A/B product integration.

**Required Skills:** `skill-full-stack-integration`,
  `skill-test-driven-development`.

**Files And Symbols:**
- Modify `frontend/src/features/cv-review/types.ts` and `api.ts` to mirror the
  canonical API fields and action payload.
- Modify `frontend/src/features/cv-review/final-artifact-evidence.ts`:
  `hasVerifiedNativeOnePageRender` must inspect the structured
  `render_acceptance` object and identity-bound fields.
- Modify `frontend/src/features/run-detail/run-detail-page.tsx`:
  `getPendingCvReviewUncertainty`, `handleCvReviewAction`, review dialog
  rendering, and refresh handling.
- Modify `frontend/src/features/cv-review/components/CvEvaluationCard.tsx` and
  `CvVersionHistory.tsx` to display the same evidence and lifecycle mapping.
- Modify `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx`
  and `PipelineOutcome.tsx` so qualifier, pending, review-required, rejected,
  cancelled, failed, and success remain distinct.
- Update `frontend/src/features/cv-review/final-artifact-evidence.test.ts`,
  `cv-api.test.tsx`, and `frontend/src/features/run-detail/run-detail-page.test.tsx`.

**Dependencies:** Task 2.

**Authority:** May add one shared frontend status/evidence helper only when it
removes duplicate mappings. Do not add frontend fallback fields or infer backend
acceptance from rendered content. Preserve keyboard access, focus behavior,
semantic controls, supported themes, and reduced-motion behavior.

**Steps:**
1. Replace `String(renderAcceptance).toLowerCase()` logic with structured proof
   reads for `render_status`, `page_count`, `page_fit_status`, and checksum.
2. Display exactly `verified · 1 page · native render passed` only for a passed
   identity-bound envelope; display an explicit unavailable/unverified state for
   all other proof.
3. Render every unresolved uncertainty using `affected_fact`, `question`, and
   `recommended_disposition`; never use `resolution_key` as the primary copy.
4. Track selected `uncertainty_id` and `resolution_key` in action state. Submit
   the selected identity, then replace resource state with the server response
   and refetch when `refresh_required` is true.
5. Map statuses through one shared frontend mapping. Do not render every
   non-pass status as rejected.
6. Keep final-artifact evidence separate from qualification evidence and show
   both in the review dialog and version history.

**Verification:**
```powershell
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run frontend/src/features/cv-review/final-artifact-evidence.test.ts frontend/src/features/cv-review/cv-api.test.tsx frontend/src/features/run-detail/run-detail-page.test.tsx
```
Required fixture cases: production-shaped valid proof; wrong artifact version;
wrong content checksum; two pages; failed render; stale proof; multiple
uncertainties; selected uncertainty action; refresh after resolution; every
lifecycle status.

**Exit Criteria:** React displays backend proof and uncertainty copy without
fallback reinterpretation; focused tests and typecheck pass.

### Task 4: Reconcile generated acceptance state

**Purpose:** Keep acceptance state single-source and prevent YAML/JSON drift
from changing roadmap truth.

**Task Function:** Generated-artifact owner.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcome 4; preserved P0/P1 historical evidence and
explicit P1-C/P2 deferrals.

**Required Skills:** `skill-full-stack-integration`,
  `skill-test-driven-development`.

**Files And Symbols:**
- Canonical input: `config/acceptance_state.yaml`.
- Generator: `scripts/render_acceptance_state.py:render_acceptance_state`.
- Generated output: `artifacts/acceptance_state.json`.
- Tests: `tests/test_acceptance_state.py` and
  `tests/test_fitcv_cp/test_acceptance_verifier.py`.
- CI: `.github/workflows/repo-hooks.yml`.

**Dependencies:** Tasks 1–3.

**Authority:** Edit YAML first. Regenerate JSON through the existing script.
Do not hand-edit generated JSON or alter frozen corpus references. Keep
`p1_c: deferred` and `p2: deferred`; record product-integration closure in
current evidence, not by rewriting historical acceptance claims.

**Steps:**
1. Validate the intended post-convergence state in
   `config/acceptance_state.yaml`: P0-A rejected, P0-B/P0-C passed, backend
   P1-A/P1-B acceptance passed, P1-C deferred, and P2 deferred.
2. Regenerate `artifacts/acceptance_state.json` with
   `python scripts/render_acceptance_state.py config/acceptance_state.yaml artifacts/acceptance_state.json`.
3. Add a deterministic test that renders twice and compares canonical JSON
   bytes, then compares committed generated JSON with freshly rendered output.
4. Add the equality check to `.github/workflows/repo-hooks.yml` beside the
   existing acceptance verifier.
5. Record current product-integration and optimization boundaries in a new
   dated evidence markdown file without rewriting prior evidence files.

**Verification:**
```powershell
python -m pytest -q tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py
python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/fitcv-acceptance-report.json
git diff --check
```

**Exit Criteria:** Fresh generated JSON equals committed JSON byte-for-byte;
CI fails on drift; P1-C and P2 remain deferred.

### Task 5: Prove one real browser contract flow

**Purpose:** Prove end-to-end P1-A/B product integration against current route
contracts, not flattened synthetic frontend fixtures.

**Task Function:** Full-stack acceptance proof.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcomes 2, 3, and 5.

**Required Skills:** `skill-full-stack-integration`,
  `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- Extend `frontend/e2e/integration-flows.spec.ts` using the existing local API
  and deterministic fixture setup.
- Reuse the production-shaped API fixture from Tasks 1–3; do not create a
  flattened `render_acceptance: "passed"` fixture.
- Add backend route assertions in `tests/test_fitcv_cp/test_app.py` when the
  browser flow exposes a missing direct boundary.

**Dependencies:** Tasks 1–4.

**Authority:** Use local deterministic fixtures and existing browser tooling.
Do not authenticate against external services, alter provider credentials, or
replace browser proof with source inspection.

**Steps:**
1. Open a run job in review-required state through the canonical run-detail
   route.
2. Assert question, affected fact, recommended disposition, uncertainty ID,
   and current status are visible.
3. Assert valid final-artifact proof displays verified one-page/native-render
   text and invalid proof does not.
4. Resolve one selected uncertainty through the canonical JSON action route.
5. Assert response refreshes the review resource, preserves action identity,
   shows regeneration state, and does not duplicate the action.
6. Assert preview/download remains bound to returned CV version identity.
7. Exercise pending, review-required, rejected, cancelled, and success
   presentation states in the same deterministic fixture matrix.

**Verification:**
```powershell
npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts
```
Capture browser output for the representative flow. Browser evidence does not
replace committed backend and frontend tests.

**Exit Criteria:** One browser flow proves proof display, uncertainty action,
refresh, lifecycle mapping, and version identity against real route contracts.

### Task 6: Complete generation and reuse telemetry

**Purpose:** Make repeated-generation cost measurable before changing the
expensive path.

**Task Function:** Runtime measurement contract.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcomes 6 and 7; P1-A/B measurement boundary.

**Required Skills:** `skill-performance-optimization`,
  `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- Modify `src/fitcv/agentic_cv_generation.py`:
  `_empty_cv_generation_trace`, `_update_efficiency_summary`, and the
  generation attempt loop around `generate_from_analysis`.
- Modify `src/fitcv_cp/run_artifact_contracts.py`:
  `_normalize_trace_record`, `collect_normalized_generation_traces`, and
  `build_accepted_cv_effort_projection`.
- Modify `src/fitcv_cp/worker_job.py`:
  `_build_cv_generation_debug_payload` and persisted trace/debug payload fields.
- Modify `scripts/benchmark_cv_efficiency.py` and
  `tests/test_benchmark_cv_efficiency.py`.
- Write evidence to a new dated file in `docs/superpowers/evidence/`.

**Dependencies:** Tasks 1–5.

**Authority:** Add fields to existing trace/efficiency contracts; do not add a
new telemetry service. Preserve null/unavailable semantics when data is absent.
Do not claim avoided work unless source and candidate paths can be attributed to
the same job and artifact identity.

**Steps:**
1. Persist provider duration, artifact-acceptance latency, whole-run latency,
   provider calls, token totals, regeneration count, retry category, render
   failures, validation failures, stage samples, and terminal status.
2. Persist `reuse_hit_count`, `proof_reuse_count`, `provider_calls_avoided`,
   `renders_avoided`, `tokens_avoided`, `human_action_count`, and
   `reused_resolution_count` with explicit coverage status.
3. Ensure `generation_format_defect` is reported as a category with subcategory
   values from `_generation_format_defect_category`, not as an unexplained retry
   total.
4. Keep accepted-artifact and total-workload denominators separate. Include all
   attempted jobs, including failed and cancelled jobs with measurable work.
5. Add tests for complete coverage, missing coverage, attribution mismatch, and
   no false avoided-work claim.

**Verification:**
```powershell
python -m pytest -q tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_run_artifact_contracts.py
python scripts/benchmark_cv_efficiency.py --limit 100 --output-json docs/superpowers/evidence/2026-10-04-fitcv-generation-efficiency-baseline.json --output-markdown docs/superpowers/evidence/2026-10-04-fitcv-generation-efficiency-baseline.md
```

**Exit Criteria:** Benchmark reports complete or explicitly unavailable fields,
all attempted-job denominators, retry categories, reuse, human effort, and
stage latency without secret leakage.

### Task 7: Run one narrow generation-format correction experiment

**Purpose:** Reduce expensive repeated generation by replacing one known
deterministic format-defect retry with local correction where correctness
permits.

**Task Function:** Measured performance optimization.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** Outcome 7; expensive repeated-generation path;
incumbent preservation.

**Required Skills:** `skill-performance-optimization`,
  `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- Modify `src/fitcv/agentic_cv_generation.py`:
  `_generation_format_defect_category`, the attempt loop around
  `repair_retry`, and validation/render handoff.
- Modify `src/fitcv_cp/worker_job.py` only where persisted attempt type and
  retry category need the candidate result.
- Extend `tests/test_agentic_cv_generation.py` and
  `tests/test_fitcv_cp/test_worker_job.py`.
- Use `scripts/benchmark_cv_efficiency.py` for both experiment arms.
- Write incumbent/candidate evidence to a new dated JSON and Markdown pair in
  `docs/superpowers/evidence/`.

**Dependencies:** Task 6.

**Authority:** Candidate may correct only deterministic format defects with a
bounded local operation: missing mandatory section or other deterministic
format defect. Do not alter grounding, unsupported-claim, page-overflow,
provider-failure, or render-failure semantics. One local correction is the
maximum; failed correction ends in existing review/failure behavior and never
silently falls back to an unbounded provider loop.

**Steps:**
1. Freeze workload IDs, candidate profile revision, provider/model, generation
   config, ordering, run limit, acceptance rules, and source commit before both
   arms.
2. Run incumbent behavior and record all attempted jobs, not only accepted CVs.
3. Run candidate behavior with one local deterministic correction before any
   provider retry for the selected defect subtypes.
4. Compare accepted one-page CVs, first-pass acceptance, provider calls, calls
   per accepted CV, tokens per accepted CV, regeneration count, retry success
   and failure, validation/render failures, p50/p95 stage latency, end-to-end
   latency, human actions, and resolution reuse.
5. Verify hard gates: P0-B, P0-C, one-page native proof, review integrity,
   identity-bound persistence, no duplicate action, and no secret leakage.
6. Promote candidate only when total-workload cost per accepted CV is lower and
   every hard gate is unchanged. Otherwise reject candidate and retain incumbent
   production behavior.

**Verification:** Run the same benchmark command and compare material metric
digests from both arms. Run focused generation tests plus the full changed-owner
backend and frontend suites. Do not use accepted-only metrics as the promotion
decision.

**Exit Criteria:** Experiment produces reproducible incumbent/candidate evidence
with a written promotion or rejection decision. No second optimization subtype
is opened in this milestone.

### Task 8: Final verification and handoff boundary

**Purpose:** Reconcile contract convergence, measurement, deferrals, and current
working-tree safety.

**Task Function:** Completion verification.

**Template Profile:** unresolved; lead resolves through Planning Dispatch before
activation.

**Executor:** Codex lead.

**Specification Coverage:** All outcomes, preserved behavior, exclusions, and
completion criteria.

**Required Skills:** `skill-verification-before-completion`,
  `skill-full-stack-integration`, `skill-backend-verification`,
  `skill-performance-optimization`.

**Files And Symbols:**
- Verify all Task 1–7 files and new dated evidence files.
- Verify `config/acceptance_state.yaml` is canonical and
  `artifacts/acceptance_state.json` is generated output.
- Verify unrelated untracked files remain unchanged.

**Dependencies:** Tasks 1–7.

**Authority:** May fix only verification defects in files owned by this plan.
May not commit, push, merge, delete untracked files, or promote P1-C/P2.

**Steps:**
1. Run focused backend tests, full changed-owner backend tests, frontend
   typecheck/unit tests, browser flow, acceptance verifier, and benchmark.
2. Confirm every frontend field and status maps to current backend contract;
   search for scalar `render_acceptance` coercion and phantom review routes.
3. Confirm all final-artifact proof paths use identity-bound envelope and stale
   cached rerender remains local.
4. Confirm generated acceptance JSON equals fresh YAML rendering and historical
   evidence files are unchanged.
5. Record experiment denominator, material metrics, promotion/rejection,
   deviations, and rollback decision in evidence.
6. Confirm P1-C and P2 remain deferred and current untracked workspace files
   remain un-staged.

**Verification:**
```powershell
python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts
python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/fitcv-acceptance-report.json
git diff --check
git status --short --branch
```

**Exit Criteria:** `skill-verification-before-completion` returns `verified`;
all required proofs pass or have an evidence-backed blocker; plan may then be
marked completed. P1-C remains the next separate scope.

## Final Acceptance Matrix

| Area | Required proof |
|---|---|
| Final-CV evidence | One envelope across fresh, cached, regenerated, and review-closed paths; stale identity rejected |
| Backend review | Direct route tests prove success, invalid identity, stale source, replay, persistence, and no duplicate enqueue |
| React proof | Production-shaped structured render proof shows verified one-page state only when backend accepts it |
| Uncertainty UI | Question, affected fact, disposition, selected uncertainty ID, action response, and refresh are visible and bound |
| Lifecycle UI | Pending, running, review-required, rejected, cancelled, failed, and success remain distinct |
| Generated state | YAML is SSOT; committed JSON equals fresh render; CI rejects drift |
| Browser proof | One deterministic flow covers review, resolution, refresh, proof, and version identity |
| Cost baseline | All attempted jobs, accepted-artifact cost, total-workload cost, calls, tokens, retries, latency, reuse, and human effort measured |
| Optimization | One format-defect candidate only; hard gates preserved; cost reduction or incumbent retained |
| Scope | P1-C and roadmap P2 remain deferred |

## Completion Boundary

This plan ends after one contract-convergence patch and one measured
generation-efficiency experiment. Do not reopen accepted backend architecture or
start P1-C inside this plan. Any follow-on P1-C work requires a new approved
scope and plan.
