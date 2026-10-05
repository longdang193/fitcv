---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-evidence-analytics-convergence
targets:
  - config/acceptance_state.yaml
  - config/evidence_registry.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx
  - frontend/src/features/run-detail/run-detail-page.tsx
  - frontend/src/features/cv-review/api.ts
  - frontend/src/features/cv-review/types.ts
  - docs/fitcv-new-frontend.integration.md
  - scripts/verify_fitcv_acceptance.py
  - scripts/run_fitcv_repair_experiment.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/render_acceptance_state.py
  - scripts/run_fitcv_review_e2e.ps1
  - scripts/seed_fitcv_review_e2e.py
  - scripts/fitcv_analytics.py
  - scripts/sql/fitcv_gold_views.sql
  - artifacts/acceptance_state.json
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_acceptance_state.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_fitcv_analytics.py
  - frontend/src/features/cv-review/cv-api.test.tsx
  - frontend/src/features/run-detail/run-detail-page.test.tsx
  - frontend/src/features/job-evaluation/components/FitEvidenceDrawer.test.tsx
  - frontend/e2e/integration-flows.spec.ts
  - frontend/e2e/runs.spec.ts
  - scripts/seed_fitcv_review_e2e.py
  - scripts/run_fitcv_review_e2e.ps1
  - docs/superpowers/evidence/
---

# FitCV P0/P1 Evidence & Analytics Convergence

## Goal

Review verdict is accepted with one correction to project status: PR #85 is
runtime-correctness convergence, not blanket P0/P1 completion. Preserve the
declared acceptance position while closing the remaining evidence and analytics
gaps:

- P0-A stays rejected; `local_first` stays production default.
- P0-B and P0-C stay passed only within declared frozen/reviewed scopes.
- P1-A and P1-B stay accepted within scope, but current-head evidence becomes
  mechanically freshness-checked.
- P1-C stays deferred.
- P2 stays deferred except the two targeted frontend contract fixes.

Deliver one traceable analytical path:

```text
operational SQLite/artifacts -> Bronze observations -> Silver facts -> Gold metrics
                                                -> JSON / Markdown / CI / BI / experiments
```

Keep Bronze/Silver/Gold off the request path. Keep operational SQLite
authoritative for queue ownership, review actions, resolutions, artifacts, and
application behavior. Do not introduce a warehouse, Parquet pipeline, DuckDB,
new provider routing, retriever, reranker, vector store, or P1-C work.

## Implementation Outcomes

### 1. Frontend/backend contract parity

Backend lifecycle owns displayed outcome. `review_required` never becomes
`Passed / Suitable` because `result_bucket` is `passed`; qualification text
never claims support without support evidence. Review capability is explicit and
does not depend on a persisted CV version. Browser proof covers review-required
with one unresolved uncertainty and zero CV versions through resolution and
regeneration.

### 2. Complete review concurrency contract

Actionable canonical review requests require `review_revision`. The revision is
part of idempotency identity. Stale submissions return typed conflict without
mutation or duplicate regeneration, and the frontend reloads the canonical
resource after stale/conflict responses. Two-tab behavior is regression-tested.

### 3. Current evidence cannot pass by accident

Each active evidence claim has source commit, declared-input fingerprint,
fixture/cohort identity, metric digest, and explicit `current`, `historical`, or
`superseded` status. Acceptance verification discovers referenced experiments
from `config/acceptance_state.yaml`; omitted CLI experiment arguments cannot
silently skip required checks. Evidence is current only when recorded source
and declared-input fingerprints match the current working tree. Matching
`HEAD` is not sufficient when staged or unstaged declared inputs differ;
otherwise the record becomes historical. Immutable provider-backed experiment
provenance is never relabeled current. Local report rebuilds may refresh only
from retained inputs whose provenance is complete.

### 4. One analytical source

Existing operational traces and reports project into small Bronze, Silver, and
Gold SQL/Python views. `gold_cv_effort` and `gold_acceptance_state` are first
deliverables. JSON evidence, Markdown, CI scorecards, and future BI consume the
same Gold projection. Metric grain, identity, joins, null semantics, cohort
semantics, and provenance are explicit; failed, missing, unknown, zero,
historical, and current remain distinct.

### 5. Optimization-ready baseline

Failure categories and cost-weighted Pareto ranking identify the dominant source
of wasted work. Telemetry is added only when it has a named decision owner.
`local_first` remains unchanged until a future identical-cohort candidate meets
correctness, page-fit, first-pass, total-call, token, and human-effort gates.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-full-stack-integration`, `skill-backend-verification`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-verification-before-completion`, `skill-plan-document-reviewer`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared plan targets, run declared local tests/checks, update local evidence and plan ledger, and preserve existing untracked scratch files without cleanup
- User-approval actions: push, merge, publication, destructive recovery, credential/authentication changes, provider-backed experiment generation, and deletion or cleanup of untracked files
- Parallel ownership: `none`; frontend, backend, verifier, and reporting changes share contract and evidence semantics
- Sequential fallback: complete Tasks 1–3 before Tasks 4–6; complete Task 7 only after current proof passes; complete Task 8 last

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-evidence-scoped-backfill`
- Base commit: `94eaf089a07d5fe07c84755a84170f347a1b6d72`
- Expected workspace: `tracked files clean; preserve existing untracked scratch files`
- Next action: separately authorized Git disposition only; do not infer commit, push, PR, review, merge, or cleanup authorization from plan completion
- Blockers: `none`; current acceptance-state freshness and analytical-source drift are planned work, not execution blockers

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | `python -m pytest -q tests/test_acceptance_state.py`; render/drift proof | 8 passed; `artifacts/acceptance_state.json` regenerated |
| Task 2 | `completed` | current | `codex` | Task 1 | backend/frontend/browser proof | healthz, typecheck, focused tests, build, zero-version browser flow passed |
| Task 3 | `completed` | current | `codex` | Task 2 | race/idempotency tests and two-tab browser proof | 144 focused tests; frontend typecheck/tests/build; 2 browser tests passed; worker re-analysis preserves prior fit label and fails closed on missing classification |
| Task 4 | `completed` | current | `codex` | Task 1 | stale-input and referenced-experiment verifier tests | 26 verifier/state tests; acceptance verifier passed; declared-input check includes working tree |
| Task 5 | `completed` | current | `codex` | Task 1, Task 4 | Bronze/Silver/Gold projection tests | 4 analytics tests; deterministic read-only Gold effort and acceptance projections |
| Task 6 | `completed` | current | `codex` | Task 5 | identical metric outputs across consumers | 34 benchmark/analytics tests; Gold effort and material digest exposed in JSON/Markdown; refreshed current evidence r3 |
| Task 7 | `completed` | current | `codex` | Task 5, Task 6 | failure Pareto and promotion-gate proof | unavailable cost fields remain unavailable; non-identical/incomplete cohort rejected; production default unchanged |
| Task 8 | `completed` | current | `codex` | Tasks 2–7 | full suite, acceptance verifier, reconciliation | full matrix passed; R5 current-contract evidence; stale-input regression; Git disposition deferred |

## Task Breakdown

### Task 1: Freeze claim, evidence, and cohort identity

**Purpose:**
- Replace implicit “latest JSON wins” semantics with one explicit registry and
  a compatible acceptance-state contract.

**Task Function:**
- Define canonical evidence identity and status semantics before changing
  consumers.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: source-first contract ownership; no delegation needed.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: contract tests and final plan review cover validation.

**Specification Coverage:**
- Verdict sections 3, 4, and 10; one current artifact per analytical claim;
  acceptance, measurement, and optimization remain separate.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`, `scripts/render_acceptance_state.py:_validate_state`, `scripts/render_acceptance_state.py:render_acceptance_state`, `scripts/verify_fitcv_acceptance.py:_source_inputs_match_current`, `tests/test_acceptance_state.py`
- Modify: `config/acceptance_state.yaml`, new `config/evidence_registry.yaml`, `scripts/render_acceptance_state.py:_validate_state`, `scripts/render_acceptance_state.py:render_acceptance_state`, `artifacts/acceptance_state.json`, `tests/test_acceptance_state.py`
- Verify: `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json`, `docs/superpowers/evidence/2026-10-05-fitcv-p0-p1-evidence-analytics-convergence.md`

**Dependencies:**
- Current source and acceptance state at `94eaf089`; preserve P0-A rejection,
  P0-B/C pass, P1-A/B pass, P1-C/P2 deferred.

**Authority:**
- Preauthorized local actions: edit registry/state schema and focused tests; run state validation tests.
- Stop for: any attempt to change production default, broaden frozen scope, or mark historical evidence current without lineage proof.

**Steps:**
- [ ] Step 1: Define registry fields `evidence_id`, `claim`, `schema_version`, `source_commit`, `declared_input_fingerprint`, `fixture_sha256`, `cohort_id`, `cohort_type`, `material_metrics_sha256`, `status`, `superseded_by`, `generated_at`, and `last_refresh`.
- [ ] Step 2: Register current P0/P1 claims and existing experiment/current-contract artifacts; label R15 and any changed-input artifacts historical where proof fails.
- [ ] Step 3: Add state/registry validation for exactly one current record per claim, valid supersession, stable cohort types, and explicit null/unavailable semantics.
- [ ] Step 4: Regenerate `artifacts/acceptance_state.json` from canonical YAML and require the drift test to pass.

**Verification:**
- [ ] `python -m pytest -q tests/test_acceptance_state.py`
- Expected: duplicate-current, bad-supersession, missing-lineage, and invalid-status fixtures fail; current repository registry passes.

**Exit Criteria:**
- Registry and acceptance state have one authoritative current record per claim and no unsupported blanket P0/P1 completion statement.

### Task 2: Reconcile lifecycle and review reachability

**Purpose:**
- Make frontend output represent backend lifecycle and expose review capability
  even when no CV version is persisted.

**Task Function:**
- Close the final FE/BE contract gap with one vertical user-visible capability.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-cutting contract change requires one owner.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused backend, frontend, accessibility, and browser proof.

**Specification Coverage:**
- Verdict sections 1 and 13; lifecycle outranks filter bucket; review access is
  capability-driven; `/healthz` does not expose SQLite path.

**Required Skills:**
- `skill-full-stack-integration`, `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:_canonical_cv_review_resource`, `src/fitcv_cp/app.py:_build_enriched_tab_context`, `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx`, `frontend/src/features/run-detail/run-detail-page.tsx`
- Modify: `src/fitcv_cp/app.py`, `frontend/src/features/cv-review/types.ts`, `frontend/src/features/cv-review/api.ts`, `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.tsx`, `frontend/src/features/run-detail/run-detail-page.tsx`, `docs/fitcv-new-frontend.integration.md`, `tests/test_fitcv_cp/test_app.py`, `frontend/src/features/job-evaluation/components/FitEvidenceDrawer.test.tsx`, `frontend/src/features/run-detail/run-detail-page.test.tsx`, `frontend/e2e/integration-flows.spec.ts`, `frontend/e2e/runs.spec.ts`
- Verify: `GET /runs/{run_id}/jobs/{run_job_id}/cv-review`, `GET /healthz`, and review dialog flow.

**Dependencies:**
- Task 1 registry/state semantics; current route contracts remain canonical.

**Authority:**
- Preauthorized local actions: edit declared backend/frontend contract, sidecar, and focused tests; run isolated local browser flow.
- Stop for: route-shape drift, unsupported qualification claims, accessibility regression, or any change to operational review ownership.

**Steps:**
- [ ] Step 1: Add explicit review capability fields to the run-job projection or canonical review resource, including availability and pending count; keep operational SQLite as source of truth.
- [ ] Step 2: Make drawer status resolve lifecycle first (`review_required`, `failed`, `rejected`, `passed`) and remove bucket-only qualification fallback text.
- [ ] Step 3: Render CV Review from capability, not CV-version count; verify keyboard focus, dialog labeling, status announcement, disabled resolved controls, and reduced-motion-safe behavior.
- [ ] Step 4: Remove database path from generic `/healthz`; retain diagnostics in existing admin surface if already available.
- [ ] Step 5: Add an isolated seed mode that creates `review_required` with one unresolved uncertainty and zero CV versions; make the runner select that scenario explicitly and assert review visibility before any artifact exists.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_app.py`
- [ ] `npm --prefix frontend run typecheck`
- [ ] `npm --prefix frontend run test -- --run frontend/src/features/job-evaluation/components/FitEvidenceDrawer.test.tsx frontend/src/features/run-detail/run-detail-page.test.tsx`
- [ ] `powershell -File scripts/run_fitcv_review_e2e.ps1`
- Expected: review-required + one unresolved uncertainty + zero CV versions shows Review CV evidence before artifact creation, opens dialog, persists resolution, regenerates; lifecycle labels remain truthful; health response contains no DB path. Browser proof names keyboard/focus, dialog labeling, status announcement, responsive viewport, supported theme, and reduced-motion assertions.

**Exit Criteria:**
- Backend and frontend expose one matching review-capability/lifecycle contract with committed browser and accessibility proof.

### Task 3: Close review revision and stale-resource behavior

**Purpose:**
- Finish canonical review concurrency from request validation through stale UI recovery.

**Task Function:**
- Harden first-writer-wins, idempotency, and refresh behavior without duplicate side effects.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared route, store, and client semantics require sequential ownership.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct boundary and browser race tests provide independent proof.

**Specification Coverage:**
- Verdict section 2; required `review_revision`, revision-bound request identity,
  typed stale conflict, automatic canonical refresh, no duplicate regeneration.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:CanonicalCvReviewActionRequest`, `src/fitcv_cp/app.py:apply_canonical_cv_review_action`, `src/fitcv_cp/app.py:_request_fingerprint`, `src/fitcv_cp/app.py:resolve_review_queue_item`, `src/fitcv_cp/templates/_cv_review_queue.html`, `frontend/src/features/run-detail/run-detail-page.tsx:handleCvReviewAction`
- Modify: `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/templates/_cv_review_queue.html`, `frontend/src/features/cv-review/types.ts`, `frontend/src/features/cv-review/api.ts`, `frontend/src/features/run-detail/run-detail-page.tsx`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `frontend/src/features/cv-review/cv-api.test.tsx`, `frontend/src/features/run-detail/run-detail-page.test.tsx`, `frontend/e2e/integration-flows.spec.ts`
- Verify: canonical review action route and idempotent action store.

**Dependencies:**
- Task 2 canonical review capability and current `review_revision` calculation.

**Authority:**
- Preauthorized local actions: edit review request validation, fingerprint, store transaction, client refresh, and focused tests.
- Stop for: persisted state mutation on stale input, duplicate enqueue, revision omission from idempotency identity, or changed winner semantics.

**Steps:**
- [ ] Step 1: Require non-empty `review_revision` for actionable requests; reject missing/stale revisions before mutation.
- [ ] Step 2: Include run, run-job, review item, review revision, uncertainty, resolution key, action, and answer in request fingerprint/idempotency identity.
- [ ] Step 3: Make stale/conflict client handling refetch canonical resource and replace dialog state; preserve answer clearing when uncertainty changes.
- [ ] Step 4: Add two-tab race proof: Tab A reads R1, Tab B resolves, Tab A submits R1, response is 409, refresh shows winner, regeneration occurs once.
- [ ] Step 5: Render the canonical revision into `_cv_review_queue.html`, post it unchanged from the admin form, and test successful submission, stale-form rejection, and replay idempotency. Never substitute latest revision at submission.
- [ ] Step 6: Add an isolated two-tab browser scenario to `scripts/run_fitcv_review_e2e.ps1`/`frontend/e2e/integration-flows.spec.ts`; assert persisted winner after refresh and exactly one regeneration side effect.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- [ ] `npm --prefix frontend run test -- --run frontend/src/features/cv-review/cv-api.test.tsx frontend/src/features/run-detail/run-detail-page.test.tsx`
- [ ] `powershell -File scripts/run_fitcv_review_e2e.ps1`
- Expected: missing/stale revision fails closed; admin and React callers submit captured revision; competing tabs preserve first writer and one side effect; stale UI refreshes canonical state.

**Exit Criteria:**
- Review action contract is revision-bound, idempotent, atomic, and user-visible stale recovery is proven.

### Task 4: Enforce evidence freshness and acceptance-state discovery

**Purpose:**
- Prevent stale current-contract or experiment evidence from passing because CLI
  parameters were omitted or declared inputs changed.

**Task Function:**
- Make evidence freshness a hard, source-owned CI invariant.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: verifier and acceptance-state ownership must remain singular.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: adversarial stale-input fixtures and acceptance-state tests.

**Specification Coverage:**
- Pasted verdict sections 3 and 4; source and declared-input fingerprints must
  match the working tree; acceptance state owns referenced experiment paths.

**Required Skills:**
- `skill-backend-verification`, `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/verify_fitcv_acceptance.py:_source_inputs_match_current`, `scripts/verify_fitcv_acceptance.py:_run_current_contract_evidence_check`, `scripts/verify_fitcv_acceptance.py:main`, `scripts/run_fitcv_repair_experiment.py:DECLARED_INPUTS`, `scripts/run_fitcv_repair_experiment.py:main`, `config/acceptance_state.yaml`
- Modify: `scripts/verify_fitcv_acceptance.py`, `scripts/run_fitcv_repair_experiment.py`, `config/acceptance_state.yaml`, `tests/test_fitcv_cp/test_acceptance_verifier.py`, `tests/test_benchmark_cv_efficiency.py`
- Verify: acceptance verifier with current and mutated temporary evidence fixtures.

**Dependencies:**
- Task 1 registry and explicit evidence statuses.

**Authority:**
- Preauthorized local actions: edit verifier/state references and add isolated stale-evidence fixtures/tests.
- Stop for: green verification with missing referenced experiment, undeclared input change, mismatched metric digest, or secret-bearing evidence.

**Steps:**
- [ ] Step 1: Make verifier load current-contract and experiment paths from `config/acceptance_state.yaml`/registry instead of requiring optional `--experiment-*` arguments for required checks.
- [ ] Step 2: Generalize declared-input freshness to every active claim; mark source-changed records historical automatically and expose reason codes.
- [ ] Step 3: Validate fixture hash, analysis-input identity, cohort identity, material metric digest, source commit, and registry status together.
- [ ] Step 4: Add negative tests for omitted experiment args, changed declared input, missing referenced path, stale digest, and source-commit mismatch.
- [ ] Step 5: Separate offline analytical rebuild from provider-backed experiment generation. Use `python scripts/benchmark_cv_efficiency.py --run-manifest <retained-manifest> --output-json <out.json> --output-markdown <out.md>` only when retained manifest/database inputs are complete. Use `python scripts/run_fitcv_repair_experiment.py --arm <arm> --database <db> --manifest <manifest> --produce-real` only after explicit provider/auth approval; otherwise record completion as blocked, never current.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_benchmark_cv_efficiency.py`
- [ ] `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-report.json`
- Expected: current evidence passes only with complete lineage; stale or missing referenced evidence fails or is historical; report names exact reason.

**Exit Criteria:**
- CI cannot declare active P1-A/P1-B evidence current without source/input/fixture/cohort/digest proof.

### Task 5: Build off-path Bronze, Silver, and Gold projections

**Purpose:**
- Establish a rebuildable analytical layer over existing SQLite and artifacts,
  without adding an operational platform.

**Task Function:**
- Normalize existing trace, artifact, review, experiment, and acceptance facts at explicit grains.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: data model crosses existing store and reporting contracts.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: projection fixtures and denominator/join tests.

**Specification Coverage:**
- Verdict sections 5–8; Bronze provenance; Silver identity/deduplication/validity;
  Gold `gold_cv_effort` and `gold_acceptance_state`; failed work included in totals.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:iter_run_jobs_for_export`, `src/fitcv_cp/sqlite_store.py:list_cv_versions`, `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`, `scripts/benchmark_cv_efficiency.py:collect_normalized_generation_traces`, `scripts/benchmark_cv_efficiency.py:build_baseline`, `scripts/benchmark_cv_efficiency.py:material_report_metrics`
- Modify: new `scripts/fitcv_analytics.py`, new `scripts/sql/fitcv_gold_views.sql`, `src/fitcv_cp/sqlite_store.py` only where read projections are missing, `tests/test_fitcv_analytics.py`, `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: isolated disposable SQLite database and fixture artifacts.

**Dependencies:**
- Tasks 1 and 4; operational schemas and evidence lineage are canonical.

**Authority:**
- Preauthorized local actions: add read-only analytical projections, SQL views, fixtures, and tests; no request-path writes.
- Stop for: join multiplication, accepted-only denominators, unknown-to-zero coercion, historical/current conflation, or new database service dependency.

**Steps:**
- [ ] Step 1: Define Bronze observations for run, job, provider attempt, generation attempt, review event, artifact event, and experiment with source ID, timestamp, schema, commit, input fingerprint, and ingestion time.
- [ ] Step 2: Define Silver entities for run, job, requirement, requirement evidence, generation attempt, CV artifact, review action, resolution, and experiment run; enforce identity and validity.
- [ ] Step 3: Build `gold_cv_effort` at grain `one accepted final artifact identity per run_job_id + artifact_version_id`; aggregate provider/generation/review one-to-many sources by `run_job_id` before joining. Reuse `build_accepted_cv_effort_projection` accepted-artifact predicate and `collect_normalized_generation_traces` trace identity; include all cohort attempts in total-work denominators and return null/unavailable when accepted count is zero.
- [ ] Step 4: Build `gold_acceptance_state` from registry/state, preserving implementation, acceptance, measurement, optimization, current/historical, and deferred dimensions.
- [ ] Step 5: Define primary keys, allowed joins, metric owner, cohort boundary, and null rules in SQL comments/tests; preserve `failed != missing`, `unknown != 0`, `review_required != rejected`, and `historical != current`.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_analytics.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: one-to-many sources aggregate before joins; repeated rebuilds are deterministic; failed attempts remain in total-work metrics; no operational write occurs.

**Exit Criteria:**
- Read-only projections produce deterministic `gold_cv_effort` and `gold_acceptance_state` from existing authoritative data.

### Task 6: Converge JSON, Markdown, CI, and future BI on Gold

**Purpose:**
- Remove parallel metric implementations and make cohort identity explicit in every report.

**Task Function:**
- Route existing evidence/report consumers through Gold projections while preserving output compatibility.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: report consumers must converge after Gold semantics are proven.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: cross-consumer equality tests and generated artifact inspection.

**Specification Coverage:**
- Verdict sections 9 and 10; one Gold metric contract feeds JSON, Markdown, CI,
  dashboard/BI exports, experiment comparison, and acceptance measurement.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:build_baseline`, `scripts/benchmark_cv_efficiency.py:material_report_digest`, `scripts/verify_fitcv_acceptance.py`, `scripts/render_acceptance_state.py`
- Modify: `scripts/benchmark_cv_efficiency.py`, `scripts/verify_fitcv_acceptance.py`, `scripts/render_acceptance_state.py`, `scripts/fitcv_analytics.py`, `tests/test_benchmark_cv_efficiency.py`, `tests/test_acceptance_state.py`, `config/evidence_registry.yaml`
- Verify: generated JSON, Markdown, acceptance report, registry, and Gold projection.

**Dependencies:**
- Task 5 deterministic Gold projections; Task 4 freshness gate.

**Authority:**
- Preauthorized local actions: refactor report adapters and add equality/lineage tests; preserve public output fields unless contract migration is explicitly recorded.
- Stop for: divergent metric values, missing cohort metadata, changed historical results without supersession, or duplicated metric calculation that bypasses Gold.

**Steps:**
- [ ] Step 1: Add `source_commit`, `declared_input_fingerprint`, `cohort_id`, `cohort_type`, `metric_schema_version`, `generated_at`, and `last_refresh` to report envelopes.
- [ ] Step 2: Make `material_report_metrics`/digest consume canonical Gold records rather than re-aggregating raw one-to-many inputs.
- [ ] Step 3: Generate Markdown and CI scorecard from the same JSON/Gold payload; retain stable compatibility fields and explicit unavailable values.
- [ ] Step 4: Add tests asserting JSON, Markdown summary, CI scorecard, and registry point to same evidence ID and material digest; preserve existing public metric fields unless an explicit migration is recorded.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py`
- Expected: all report consumers agree on metric values, cohort, lineage, and digest; historical reports remain immutable and explicitly labeled.

**Exit Criteria:**
- Exactly one current analytical answer exists for each metric claim, and every consumer derives from the same Gold contract.

### Task 7: Produce failure Pareto and future optimization gate

**Purpose:**
- Shift post-convergence engineering toward lower total work per accepted verified
  one-page CV without changing production routing prematurely.

**Task Function:**
- Categorize failure workload, attach decision-owned telemetry, and make future paired experiments mechanically admissible.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: optimization is deferred until measurement and reporting are converged.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: metric/gate tests and baseline reproducibility.

**Specification Coverage:**
- Verdict sections 11 and 12; failure categories, cost-weighted Pareto ranking,
  decision-owner telemetry, and unchanged `local_first` default.

**Required Skills:**
- `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:build_baseline`, `scripts/benchmark_cv_efficiency.py:material_report_metrics`, `scripts/run_fitcv_repair_experiment.py:build_manifest`, `scripts/run_fitcv_repair_experiment.py:capture_input_identity`
- Modify: `scripts/benchmark_cv_efficiency.py`, `scripts/run_fitcv_repair_experiment.py`, `tests/test_benchmark_cv_efficiency.py`, `config/acceptance_state.yaml`
- Verify: generated baseline/Pareto JSON and Markdown; no production-default mutation.

**Dependencies:**
- Tasks 5 and 6; current `local_first` acceptance and report lineage are stable.

**Authority:**
- Preauthorized local actions: add failure categories, decision-owned telemetry fields, Pareto output, and future experiment admission checks.
- Stop for: provider-order promotion, unpaired cohort comparison, missing failed-work denominators, unavailable human-effort measures presented as zero, or request-path behavior changes.

**Steps:**
- [ ] Step 1: Normalize failure categories: grounding/unsupported claim, requirement coverage, format/schema, section sufficiency, length/page-fit, provider format defect, local repair failure, render failure, and review-required uncertainty.
- [ ] Step 2: Rank categories by frequency × provider-call cost × token cost × latency × deterministic-repair likelihood; expose missing inputs as unavailable.
- [ ] Step 3: Add only decision-owned telemetry needed for review cost, avoided provider work, resolution reuse, and repair failure category; document each decision owner.
- [ ] Step 4: Gate any future paired experiment on identical source/config/fixture/cohort/runtime/repeat identity and correctness/page-fit/first-pass/total-call/token/human-effort checks.
- [ ] Step 5: Generate Pareto from `gold_cv_effort` and normalized trace failure causes; optimization engineering owns the decision, missing-value order is `unavailable` before `null` before numeric zero, and no category with unavailable cost inputs is ranked as zero-cost.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_cv_efficiency.py`
- [ ] `python scripts/benchmark_cv_efficiency.py --run-manifest <retained-manifest> --output-json .tmp/gold-cv-effort.json --output-markdown .tmp/gold-cv-effort.md`
- [ ] Run against a disposable retained manifest/database and inspect `gold_cv_effort`; do not call provider generation in this task.
- Expected: Pareto ranking is reproducible, failed work is included, unavailable is not zero, and `local_first` remains unchanged.

**Exit Criteria:**
- Dominant failure workload and admissible future optimization gate are documented; no optimization candidate is promoted by this plan.

### Task 8: Reconcile committed executions and close evidence

**Purpose:**
- Prove all claimed executions against current source and leave one durable
  completion record without declaring unsupported scope.

**Task Function:**
- Run fresh final verification, reconcile plan/state/evidence, and identify any blocker.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance and plan ledger require controller authority.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `skill-verification-before-completion` owns final proof.

**Specification Coverage:**
- Verdict closure criterion; every active claim traces Gold → Silver → Bronze →
  operational artifact and code/input fingerprint.

**Required Skills:**
- `skill-verification-before-completion`, `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: all Task 1–7 targets, `config/acceptance_state.yaml`, `config/evidence_registry.yaml`, existing evidence artifacts, and `git log --stat`
- Modify: this plan, `config/acceptance_state.yaml`, `config/evidence_registry.yaml`, generated evidence only when produced by verified commands
- Verify: full backend/frontend/browser/acceptance/report matrix.

**Dependencies:**
- Tasks 1–7 completed; no stale or missing required evidence.

**Authority:**
- Preauthorized local actions: run final verification and reconcile plan/state/evidence text with fresh outputs.
- Stop for: any failed hard gate, stale current claim, unexplained committed execution, secret leakage, or required work that remains blocked.

**Steps:**
- [x] Step 1: Run focused backend/frontend tests, typecheck, frontend tests/build, browser flow, analytics tests, acceptance verifier, and `git diff --check` with immediate failure propagation.
- [x] Step 2: Verify every committed execution cited by acceptance state has current-head or declared-input proof; refresh stale R3/R4 current-contract records to R5 and retain historical records.
- [x] Step 3: Run `skill-verification-before-completion`; evidence is verified for current dirty workspace, with declared-input freshness guard and no unresolved required blocker.
- [x] Step 4: Leave Git disposition, push, PR, review, and merge for separately authorized workflow.

**Verification:**
- [x] `python -m pytest -q` — `3204 passed, 8 skipped`
- [x] `npm --prefix frontend run typecheck` — passed
- [x] `npm --prefix frontend run test -- --run` — `337 passed`
- [x] `npm --prefix frontend run build` — passed
- [x] `powershell -File scripts/run_fitcv_review_e2e.ps1` — repeated `3/3`, each `2 passed`
- [x] `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-report.json` — `PASSED`, P0-B/P0-C/P1-A/P1-B passed
- [x] `git diff --check` — passed
- Expected: all mandatory checks pass; every current claim has lineage; P1-C/P2 remain deferred; no unsupported optimization promotion exists.

**Exit Criteria:**
- Plan can move from `proposed` to `active` only after approval, and from `active` to `completed` only after fresh verification returns `verified`.

## Verification

Final artifact verification must establish:

- [x] lifecycle-first frontend labels and evidence-safe qualification text;
- [x] review capability independent of CV-version existence;
- [x] required revision, idempotent request identity, atomic stale rejection, and two-tab refresh;
- [x] health response excludes filesystem/database path;
- [x] registry has one current record per claim and explicit historical/superseded records;
- [x] acceptance verifier discovers referenced experiments and rejects stale declared inputs;
- [x] deterministic Bronze/Silver/Gold rebuild with `gold_cv_effort` and `gold_acceptance_state`;
- [x] JSON, Markdown, CI, and registry share Gold values and material digest;
- [x] failure Pareto and future promotion gate include failed work and unavailable semantics;
- [x] `local_first` remains production default; P1-C and P2 remain deferred;
- [x] no new operational analytics platform or request-path dependency exists.

Run `skill-verification-before-completion` before changing plan status.
Source inspection, unit tests alone, browser evidence alone, or historical
reports alone cannot close this plan.

## Completion Criteria

The plan is ready for completion verification when:

1. Tasks 1–8 have task-local proof and no unresolved required blocker.
2. Frontend lifecycle/review capability matches backend canonical state.
3. Review concurrency is revision-bound, atomic, idempotent, and browser-proven.
4. Current acceptance evidence is freshness-checked from declared inputs and registry paths.
5. Every active claim and KPI traces deterministically from Gold to exact operational artifact and source/input fingerprint.
6. Exactly one current analytical answer exists per claim/metric; historical evidence is immutable and labeled.
7. Failure Pareto identifies next expensive work without changing production routing.
8. P1-C remains deferred and P2 remains frozen except targeted UI fixes.
9. All committed executions cited by state/evidence are reconciled against current source.
10. `skill-verification-before-completion` returns `verified`; only then may plan status become `completed`.

This plan does not authorize commit, push, PR creation, merge, acceptance-state
promotion, external API use, or cleanup of existing untracked scratch files.
