---
layer: change
artifact_type: plan
contract_version: "1"
status: active
template_id: implementation-plan
name: fitcv-recommended-execution-sequence
targets:
  - scripts/fitcv_analytics.py
  - scripts/sql/fitcv_gold_views.sql
  - config/analytics_metrics.yaml
  - scripts/export_fitcv_analytics_source.py
  - scripts/produce_fitcv_p1b_measurement.py
  - scripts/compare_fitcv_optimization.py
  - scripts/refresh_fitcv_analytics.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - scripts/render_acceptance_state.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv/reuse.py
  - src/fitcv/reuse_law_engine.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - frontend/src/app/route-registry.ts
  - frontend/src/features/analytics-dashboard/
  - tests/test_fitcv_analytics.py
  - tests/test_export_fitcv_analytics_source.py
  - tests/test_refresh_fitcv_analytics.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_produce_fitcv_p1b_measurement.py
  - tests/test_compare_fitcv_optimization.py
  - tests/test_acceptance_state.py
  - frontend/src/test/analytics-dashboard.test.tsx
  - frontend/e2e/analytics-dashboard.spec.ts
  - scripts/run_fitcv_analytics_dashboard_e2e.ps1
  - docs/superpowers/evidence/
  - config/evidence_registry.yaml
---

# FitCV Recommended Execution Sequence

## Review Findings

The prior `2026-10-06-fitcv-next-pr-sequence-plan.md` is directionally useful
but stale.

- It duplicates PR numbers, branches, merge SHAs, and active states owned by
  GitHub. Those facts drift and must not be coordination truth.
- It omits the `gold_optimization_state` source fix. Canonical source is
  `optimization_result`, not `optimization_status` under `status_dimensions`.
- It treats four population defects as unrelated metric patches instead of one
  bounded correctness change with shared invariants.
- It does not make refresh idempotency and atomic publication separate gates.
- It names dashboard paths absent from current repository. This plan uses the
  existing route discovery/API surfaces and creates only the approved feature.

## Decision

Use this milestone sequence as canonical. A milestone may become one PR, but
this plan never records PR number, branch, merge SHA, or machine-observable
GitHub state. Every PR requires one independent `review-1` review before merge.

Before Task 1 activation, track this plan, reconcile the predecessor plan's
unfinished claims against current repository evidence, designate this plan as
sole ledger, and record exact branch/base/workspace facts in Coordination State.
No task starts while two plans claim active ownership.

FitCV needs complete source populations, trustworthy measurement, and less
repeated work; it does not need another analytics architecture.

## Goal

```text
population-correct Gold
  -> replayable refresh and atomic publish
  -> fresh reproducible P1-B baseline
  -> small P1-C dashboard
  -> content-addressed work reuse
  -> deterministic repair and bounded escalation
  -> measured promotion decision
```

## Implementation Outcomes

### Correct analytics populations

Failed attempts, canonical posting identity, complete requirement outcomes,
historical cohorts, structured dimensions, real coverage counts, and
`gold_optimization_state` all use authoritative source data. Incomplete coverage
cannot become a percentage.

### Replayable analytics operation

One command reads a consistent operational snapshot, exports a sanitized source
bundle, rebuilds Bronze → Silver → Gold, validates identity/digests, and
atomically publishes. Repeat inputs are idempotent; failed refresh preserves
last-known-good output.

### Current evidence and bounded dashboard

Fresh P1-B evidence is replayable and independently verifiable. P1-C exposes
only opportunity landscape, imported-corpus requirement demand, and candidate
evidence gaps with sample size, source mix, collection window, coverage,
candidate revision, and source-to-posting traceability.

### Measured optimization

Reuse is content-addressed with explicit invalidation. Deterministic local repair
precedes targeted generation; full regeneration is last resort. Promotion needs
paired measurement with no grounding or one-page regression.

## Non-goals

- Do not recover or infer unavailable R5/R6 evidence.
- Do not change provider routing, model selection, `local_first`, accepted
  artifact semantics, or CV-generation request contracts in early milestones.
- Do not add predictive trends, market-wide claims, or dashboard-side formulas.
- Do not query operational SQLite directly from frontend code.
- Do not edit generated evidence without rebuilding from canonical sources.
- Do not clean preserved untracked workspace artifacts.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`,
  `skill-test-driven-development`, `skill-full-stack-integration`,
  `skill-frontend-component-engineering`, `skill-performance-optimization`,
  `skill-verification-before-completion`, `skill-requesting-code-review`,
  `skill-reviewing-pull-requests`
- Isolation: fresh `codex/` branch from updated `origin/main` per mergeable
  milestone; preserve current untracked artifacts
- Commit policy: verified checkpoint commits; push and merge only after
  independent `review-1` review and green checks
- Preauthorized local actions: inspect source, edit declared files, add focused
  tests/evidence, run declared checks, commit local changes, update this ledger
- User-approval actions: push, PR creation/update, merge into `main`, destructive
  recovery, discard, cleanup, or out-of-scope edits
- Parallel ownership: none; milestones share analytics contracts
- Sequential fallback: stop at failed gate, record evidence, fix upstream
  contract, rerun proof, then continue

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-recommended-sequence`
- Base commit: `5cfb745d73111fb72fa5bbf053e8d40b76e52da6`
- Expected workspace: `tracked plans plus preserved untracked artifacts; no cleanup`
- Next action: `commit Task 0 checkpoint, then admit Task 1`
- Blockers: `none known; R5/R6 unavailable evidence stays unavailable`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 0. Supersession/admission | `completed` | current plan branch | `codex` | none | tracked plan, reconciled predecessor, exact Git facts | branch/base recorded; predecessor superseded |
| 1. Reporting correctness | `pending` | fresh branch | `unresolved` | 0 | focused analytics/export tests and verifier | pending |
| 2. Refresh/publish | `pending` | fresh branch | `unresolved` | 1 | replay, idempotency, failure preservation | pending |
| 3. Fresh P1-B baseline | `pending` | fresh branch | `unresolved` | 2 | paired manifests and independent verifier | pending |
| 4. P1-C dashboard MVP | `pending` | fresh branch | `unresolved` | 3 | API, frontend, browser, accessibility proof | pending |
| 5. Content-addressed reuse | `pending` | fresh branch | `unresolved` | 4 | hit/miss/invalidation and equivalence proof | pending |
| 6. Repair/escalation | `pending` | fresh branch | `unresolved` | 5 | ordered repair and fallback tests | pending |
| 7. Re-measure/promote | `pending` | fresh branch | `unresolved` | 5–6 | paired comparison and quality gate | pending |

## Task Breakdown

### Task 0: Supersede stale coordination state

**Purpose:** Establish one recoverable coordination source before implementation.

**Task Function:** Track this plan, reconcile predecessor claims, and admit the
next implementation branch from current `origin/main`.

**Template Profile:** Controller-selected: `<none (lead controller)>`; lifecycle
and handoff integrity.

**Validator Profile:** Controller-selected: `review-1`; independent plan and
admission review.

**Specification Coverage:** Git is workspace truth; this plan is sole ledger;
machine-observable PR state is derived from GitHub; preserved untracked files
remain untouched.

**Required Skills:** `skill-using-git-worktrees`,
`skill-verification-before-completion`

**Files And Symbols:**
- Track and update this plan's Coordination State and ledger.
- Inspect `docs/superpowers/plans/2026-10-06-fitcv-next-pr-sequence-plan.md` and
  reconcile its active claims using current Git/evidence; do not copy PR state.
- Verify `git branch --show-current`, `git rev-parse HEAD`,
  `git rev-parse origin/main`, and `git status --short`.

**Dependencies:** None.

**Authority:**
- Preauthorized local actions: track this plan, record exact branch/base facts,
  reconcile plan metadata, and create a local checkpoint commit.
- Stop for: ambiguous predecessor ownership, dirty tracked changes, required
  discard/cleanup, or base mutation.

**Steps:**
- [ ] Record exact branch, base commit, and preserved workspace condition from
  Git in Coordination State; never record guessed values.
- [ ] Reconcile predecessor tasks and mark its ledger historical only when
  repository evidence supports that transition; otherwise record blocker.
- [ ] Commit the tracked plan checkpoint before Task 1 admission.

**Verification:** `git status --short --branch`, `git diff --check`, and plan
frontmatter/ledger inspection. Expected: one active ledger, exact Git facts, no
discarded untracked artifacts.

**Exit Criteria:** Task 1 has an exact recoverable branch/base/workspace
checkpoint and no competing active plan ownership.

### Task 1: Correct reporting populations and Gold semantics

**Purpose:** Fix four reproduced population defects and the optimization-state
source without changing generation/provider behavior.

**Task Function:** Reconcile operational rows with authoritative Silver/Gold
grains and semantic metrics.

**Template Profile:** Controller-selected: `<none (lead controller)>`; source
contract work has high data-integrity impact.

**Validator Profile:** Controller-selected: `review-1`; independent correctness
review before merge.

**Specification Coverage:** Attempts exist independently of artifacts; posting
identity differs from processing identity; requirement outcomes include
`unevaluated`; historical cohorts stay separate; `optimization_result` is the
canonical optimization source; dimensions and coverage counts stay explicit.

**Required Skills:** `skill-backend-verification`,
  `skill-test-driven-development`, `impeccable`

**Files And Symbols:**
- Modify `scripts/export_fitcv_analytics_source.py`: `collect_source`,
  `_debug_records`, `export_bundle`; fix processing/posting identity,
  evaluation-state completeness, and attempt extraction at its source owner.
- Modify `scripts/fitcv_analytics.py`: `build_silver_*`, `build_gold_*`,
  `build_gold_optimization_state`,
  `build_gold_semantic_metric`.
- Modify `scripts/sql/fitcv_gold_views.sql` and `config/analytics_metrics.yaml`.
- Verify `tests/test_export_fitcv_analytics_source.py`,
  `tests/test_fitcv_analytics.py`, `tests/test_acceptance_state.py`, and
  `tests/fixtures/analytics_semantic_contract.json`.

**Dependencies:** Updated `origin/main`; no R5/R6 recovery.

**Authority:**
- Preauthorized local actions: edit declared analytics/export/config/test files
  and run focused backend checks.
- Stop for: provider/generation behavior changes, unrelated schema migration,
  missing source evidence, or destructive data mutation.

**Steps:**
- [ ] Map each defect to source row, grain, denominator, and regression.
- [ ] Export attempts independently from `cv_versions`; derive canonical
  posting identity; preserve cohorts; retain `unevaluated` outcomes.
- [ ] Correct optimization source and expose structured dimensions/coverage.
- [ ] Add failure, duplicate-processing, incomplete-evaluation, repeated-cohort,
  and unavailable-coverage fixtures.
- [ ] Rebuild twice and compare material digests.

**Verification:**
- [ ] `python -m pytest -q tests/test_export_fitcv_analytics_source.py`
- [ ] `python -m pytest -q tests/test_fitcv_analytics.py tests/test_acceptance_state.py`
- [ ] `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/task1-acceptance-report.json`
- Expected: failed work remains counted, duplicate processing does not duplicate
  postings, cohorts remain distinct, and incomplete coverage is unavailable.

**Exit Criteria:** Four invariants and source/export regressions pass; no
provider routing or CV-generation behavior changes.

### Task 2: Build idempotent refresh and atomic publication

**Purpose:** Replace repeated manual export/rebuild steps with one safe command.

**Task Function:** Orchestrate readonly snapshot, sanitized export, rebuild,
validation, and atomic publish.

**Template Profile:** Controller-selected: `<none (lead controller)>`; bounded
backend orchestration with data-loss risk.

**Validator Profile:** Controller-selected: `review-1`; idempotency and failure
isolation review.

**Specification Coverage:** Consistent readonly snapshot, secret-free bundle,
source/metric/contract fingerprints, atomic publish after validation, prior
output preserved on failure.

**Required Skills:** `skill-backend-verification`,
`skill-test-driven-development`

**Files And Symbols:**
- Use, but do not redesign, `scripts/export_fitcv_analytics_source.py:export_bundle`.
- Modify `scripts/fitcv_analytics.py`: `rebuild_analytics_bundle`,
  `write_analytics_sqlite`.
- Add `scripts/refresh_fitcv_analytics.py` and
  `tests/test_refresh_fitcv_analytics.py`.
- Verify `src/fitcv_cp/sqlite_store.py:open_readonly_snapshot`.

**Dependencies:** Tasks 0–1 complete.

**Authority:**
- Preauthorized local actions: add refresh command, focused tests, disposable
  output, and local validation.
- Stop for: operational DB mutation, non-atomic publish, secret export, or
  shared runtime/database cleanup.

**Steps:**
- [ ] Define input/output manifest and digest contract.
- [ ] Build in a task temp directory; validate schema and material digests;
  publish with atomic `os.replace`.
- [ ] Prove identical replay is idempotent and mismatched inputs reject before
  publish.
- [ ] Inject failures at snapshot/export/rebuild/validation/publish boundaries.

**Verification:**
- [ ] `python -m pytest -q tests/test_export_fitcv_analytics_source.py tests/test_refresh_fitcv_analytics.py tests/test_fitcv_analytics.py`
- [ ] Run same fixture twice and compare published digests.
- [ ] Confirm failed rebuild leaves prior published output unchanged.

**Exit Criteria:** One command produces repeatable valid output and never leaves
partial publication.

### Task 3: Produce fresh reproducible P1-B measurement

**Purpose:** Establish current evidence before optimization claims.

**Task Function:** Capture, benchmark, rebuild, and independently verify paired
baseline evidence.

**Template Profile:** Controller-selected: `<none (lead controller)>`; strict
identity and evidence task.

**Validator Profile:** Controller-selected: `review-1`; independent evidence
freshness and pairing review.

**Specification Coverage:** Manifest, sanitized replay input, run IDs, source
commit, candidate revision, provider/model, contract/metric versions, hashes,
and material digest are retained. Failed work remains in numerators. R5/R6 is
not inferred. Successful measurement updates canonical acceptance/evidence
sources, not only generated reports.

**Required Skills:** `skill-backend-verification`,
`skill-verification-before-completion`

**Files And Symbols:**
- Verify `scripts/benchmark_cv_efficiency.py`: `main`, `_load_run_manifest`,
  `_apply_manifest_measurement_gate`, `material_report_digest`.
- Verify `scripts/verify_fitcv_acceptance.py`: `verify_acceptance`,
  `_run_experiment_report_check`, `_run_registry_evidence_check`.
- Verify `tests/test_benchmark_cv_efficiency.py` and
  `tests/test_acceptance_state.py`; add generated evidence only under
  `docs/superpowers/evidence/`.
- Add `scripts/produce_fitcv_p1b_measurement.py` and a focused test. It accepts
  `--database`, `--output-root`, `--arm`, `--variant`, `--repeat-count`,
  `--max-provider-calls`, and `--source-commit`, persists ten unique run IDs per
  arm, and records database, fixture, candidate, provider/model, and input
  fingerprints. It must execute the real configured provider-backed workload,
  not mocked observations, and fail before the declared provider-call budget.
- Add `scripts/compare_fitcv_optimization.py` and
  `tests/test_compare_fitcv_optimization.py` to compare explicit
  `variant=baseline|optimized` packages while preserving the existing
  opposite-arm acceptance verifier.
- Modify only after successful proof: `config/acceptance_state.yaml`,
  `config/evidence_registry.yaml`, and canonical evidence sources required by
  `scripts/render_acceptance_state.py`; regenerate
  `docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-canonical.json` and
  `docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-canonical.md`.

**Dependencies:** Task 2 complete and retained replayable inputs exist.

**Authority:**
- Preauthorized local actions: add producer/comparison code and tests, run real
  provider-backed workloads within the declared call budget, edit canonical
  YAML/registry sources after proof, render derived evidence, and run verifier.
- Stop for: missing retained identity, fabricated run IDs, secret-bearing
  evidence, or incomplete peer arm.

**Steps:**
- [ ] Run the bounded producer twice, once per opposite arm, with
  `--variant baseline --repeat-count 10 --max-provider-calls <declared-budget>`
  and the matching optimized/peer commands, one retained database per arm,
  identical fixture/input identity, explicit source commit, and a named
  provider/model environment.
- [ ] Run benchmark and refresh analytics from the generated package.
- [ ] Verify source/candidate/provider identity, coverage, accepted artifacts,
  render proof, and digest.
- [ ] Rebuild twice and compare material digests.
- [ ] Classify failure/work categories without changing routing.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py`
- [ ] Run verifier with explicit `--experiment-json`, `--experiment-markdown`,
  and `--experiment-peer-json`; plain invocation cannot promote R7.
- [ ] Render acceptance state from canonical YAML/registry sources and verify
  the measured transition; preserve historical evidence and keep production
  routing unchanged.
- [ ] Verify exact output paths, registry references, source commit, input
  fingerprints, and material digests for both arms.

**Exit Criteria:** Mark P1-B `measured` only after independent rebuild and
verifier success; otherwise retain explicit blocker evidence.

### Task 4: Deliver small P1-C dashboard MVP

**Purpose:** Expose trusted semantic projections without duplicating KPI logic.

**Task Function:** Add readonly API and accessible frontend views for three
decision surfaces.

**Template Profile:** Controller-selected: `<none (lead controller)>`; bounded
full-stack contract work.

**Validator Profile:** Controller-selected: `review-1`; API/UI/accessibility
review.

**Specification Coverage:** Opportunity landscape, imported-corpus requirement
demand, and candidate evidence gaps. Show sample size, source mix, collection
window, coverage, candidate revision, and source-posting traceability. Never
claim market-wide demand or unsupported candidate inability.

**Required Skills:** `skill-full-stack-integration`,
`skill-frontend-component-engineering`, `skill-backend-verification`,
`skill-test-driven-development`

**Files And Symbols:**
- Add readonly handlers `GET /analytics/semantic-metrics` and
  `GET /analytics/trace/{posting_id}` in `src/fitcv_cp/app.py`; add response
  contracts in `src/fitcv_cp/models.py`, backed by
  `config/analytics_metrics.yaml:published_artifact.path` and helper
  `_published_analytics_database`. Missing path, digest mismatch, or stale
  source commit returns explicit unavailable response; no operational DB
  fallback is allowed.
- Add `frontend/src/features/analytics-dashboard/route.tsx`, API/types, and
  views; modify `frontend/src/app/route-registry.ts` only if needed.
- Add `frontend/src/test/analytics-dashboard.test.tsx` and
  `frontend/e2e/analytics-dashboard.spec.ts`.
- Add exact API boundary coverage in
  `tests/test_fitcv_cp/test_analytics_routes.py`.
- Verify `frontend/src/lib/api-client.ts` and existing feature patterns.
- Add temporary mapping `docs/superpowers/analytics-dashboard.integration.md`
  for route → Gold projection → UI fields; remove it after contract and browser
  proof are committed.
- Add `scripts/run_fitcv_analytics_dashboard_e2e.ps1` to create disposable
  analytics fixtures, start the task-owned server, poll `/healthz`, assert
  published-artifact identity, run browser checks, and stop/remove only its
  exact temp directory.

**Dependencies:** Tasks 1–3 complete.

**Authority:**
- Preauthorized local actions: add declared API/frontend files, focused tests,
  browser checks, and accessibility assertions.
- Stop for: direct operational queries, dashboard formulas, market claims, or
  design-system expansion.

**Steps:**
- [ ] Define response envelope with coverage and unavailable reasons.
- [ ] Add bounded readonly handlers with source/collection/revision metadata.
- [ ] Add route-discovered feature with loading/error/empty/unavailable states,
  keyboard access, responsive layout, and supported themes.
- [ ] Add auditable source-posting drill-down.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp`
- [ ] API boundary tests cover both endpoints, unavailable coverage, empty
  result, and source-posting traceability.
- [ ] `npm --prefix frontend run typecheck`
- [ ] `npm --prefix frontend test -- --run`
- [ ] `pwsh -File scripts/run_fitcv_analytics_dashboard_e2e.ps1`
- [ ] Browser proof covers desktop/mobile viewport, supported theme, keyboard
  navigation, focus, contrast, loading/error/empty/unavailable states.
- [ ] Remove `docs/superpowers/analytics-dashboard.integration.md` only after
  canonical API/types/tests own every mapping.

**Exit Criteria:** Dashboard is contract-tested, accessible, auditable, and
consumes semantic projections only.

### Task 5: Optimize work reuse with content-addressed identities

**Purpose:** Remove repeated extraction, support, generation, and render work
after a measured baseline exists.

**Task Function:** Extend existing reuse identity/gate machinery with stage keys
and affected-unit invalidation.

**Template Profile:** Controller-selected: `<none (lead controller)>`; measured
runtime optimization with high regression risk.

**Validator Profile:** Controller-selected: `review-1`; invalidation and output
equivalence review.

**Specification Coverage:** Keys include source, semantic settings, policy/model
contract, candidate revision, and stage. Exact matches reuse; changed inputs
invalidate only affected units; no cross-candidate or stale reuse.

**Required Skills:** `skill-backend-verification`,
`skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Modify `src/fitcv/reuse_law_engine.py`: `build_identity`, `evaluate_gate`,
  `emit_provenance`.
- Modify `src/fitcv/reuse.py`: `resolve_reuse_stage_policy`,
  `build_reuse_decision`.
- Integrate narrowly with `src/fitcv/agentic_cv_analysis.py` and
  `src/fitcv/agentic_cv_generation.py`; verify existing persisted stage-artifact
  storage. Reuse metadata is owned by
  `src/fitcv_cp/run_artifact_mirror.py:persist_terminal_run_artifact_mirror`
  in existing `stage_transition_artifacts_json`; do not add a second cache root.
- Add focused assertions in `tests/test_agentic_cv_analysis.py`,
  `tests/test_agentic_cv_generation.py`, and a reuse-specific test module only
  if existing coverage cannot own the cases.

**Dependencies:** Tasks 3–4 complete; no optimization before baseline.

**Authority:**
- Preauthorized local actions: edit declared reuse/generation surfaces and run
  bounded benchmark/regression checks.
- Stop for: routing changes, accepted-artifact changes, unbounded cache growth,
  or missing invalidation proof.

**Steps:**
- [ ] Map current fingerprints to extraction, support, generation, and render.
- [ ] Extend `build_identity` with optional stage-input and candidate-revision
  fingerprints; preserve old callers and reject missing required identity
  instead of hashing arbitrary ignored payload.
- [ ] Define bounded persisted stage-artifact lifetime and affected units:
  extraction, requirement support, generation section/bullet, and render. Keep
  metadata-only reuse records in terminal-run mirrors, apply existing
  `pipeline_stage_artifacts.py` truncation limits, and never persist a global
  binary cache.
- [ ] Add exact-match reuse and affected-unit invalidation.
- [ ] Emit hit/miss/invalidation/rejection provenance.
- [ ] Prove output equivalence and reduced repeated work.

**Verification:**
- [ ] `python -m pytest -q tests/test_agentic_cv_analysis.py tests/test_agentic_cv_generation.py tests/test_pipeline_stage_resume_parity.py`
- [ ] Representative benchmark uses identical input with reuse disabled and
  enabled, and asserts hit/miss/invalidation provenance plus output equivalence.

**Exit Criteria:** Reuse is bounded, observable, invalidation-safe, and improves
measured repeated work without quality regression.

### Task 6: Make deterministic repair the default

**Purpose:** Reduce expensive regeneration while preserving global validation.

**Task Function:** Route failures through local repair, targeted generation,
review, and last-resort full regeneration.

**Template Profile:** Controller-selected: `<none (lead controller)>`; runtime
policy change with quality risk.

**Validator Profile:** Controller-selected: `review-1`; fallback ordering review.

**Specification Coverage:** Deterministic defect → local repair; isolated
semantic defect → targeted generation; uncertainty → review; full regeneration
last; final artifact/render validation remains global.

**Required Skills:** `skill-backend-verification`,
`skill-test-driven-development`

**Files And Symbols:**
- Modify `src/fitcv/agentic_cv_generation.py:_run_repair_cycle`,
  `_build_fallback_retry_executor`, and retry/provenance helpers.
- Integrate `src/fitcv/agentic_cv_analysis.py` and `src/fitcv/reuse.py` only as
  needed for bounded policy decisions.
- Verify generation, render acceptance, and stage-artifact tests.

**Dependencies:** Tasks 3 and 5 complete.

**Authority:**
- Preauthorized local actions: edit declared repair policy and add regression
  tests.
- Stop for: weakened global validation, silent fallback, routing changes, or
  full regeneration as default.

**Steps:**
- [ ] Classify failures into deterministic, isolated semantic, uncertainty, and
  global inconsistency.
- [ ] Implement a decision table: deterministic local repair once; targeted
  generation for one isolated section/bullet once; review for uncertainty;
  full regeneration only after those paths fail, at most once per run.
- [ ] Set numeric retry caps: one local repair, one targeted generation, and one
  full regeneration. Uncertainty emits `review_required` as terminal until an
  explicit resume action; emit repair, escalation, review, resume, and final-
  rejection outcomes.
- [ ] Keep global validation after every repair.
- [ ] Test each branch, retry cap, and final rejection.

**Verification:**
- [ ] `python -m pytest -q tests/test_agentic_cv_generation.py tests/test_cv_render_acceptance.py`
- [ ] Representative trace proves ordered local repair → targeted generation →
  full regeneration fallback and global validation after each path.

**Exit Criteria:** Escalation is deterministic, bounded, observable, and safe.

### Task 7: Re-measure and make promotion decision

**Purpose:** Produce an advisory promotion decision only when paired evidence
proves improvement; production defaults and acceptance policy remain unchanged.

**Task Function:** Compare pre/post packages and record promote, hold, or revert.

**Template Profile:** Controller-selected: `<none (lead controller)>`; final
evidence and release gate.

**Validator Profile:** Controller-selected: `review-1`; independent promotion
review.

**Specification Coverage:** Pareto by failure category, frequency, provider
calls, tokens, elapsed time, and human actions; no grounding, artifact, or
one-page regression; improvement targets accepted-CV cost, p95, or human effort.
Promotion threshold owner is the lead controller; minimum gate is no regression
in grounding, verified-one-page, or accepted-artifact correctness plus a
declared improvement in one target metric versus the same-input baseline.

**Required Skills:** `skill-verification-before-completion`,
`skill-backend-verification`

**Files And Symbols:**
- Use `scripts/produce_fitcv_p1b_measurement.py` with explicit
  `--variant baseline|optimized`, `--arm local_first|provider_first`,
  `--repeat-count 10`, and bounded `--max-provider-calls`.
- Add `scripts/compare_fitcv_optimization.py:main` and
  `tests/test_compare_fitcv_optimization.py`; it owns variant-aware comparison,
  threshold enforcement, and quality-regression rejection.
- Verify `scripts/benchmark_cv_efficiency.py`,
  `scripts/verify_fitcv_acceptance.py`, `tests/test_benchmark_cv_efficiency.py`,
  `tests/test_produce_fitcv_p1b_measurement.py`, and canonical outputs under
  `docs/superpowers/evidence/`.

**Dependencies:** Tasks 5–6 complete.

**Authority:**
- Preauthorized local actions: run comparison benchmarks, verification, and
  update durable evidence/plan state.
- Stop for: incomplete paired evidence, quality regression, unbounded cost
  increase, or unsupported promotion claim.

**Steps:**
- [ ] Produce real provider-backed baseline and optimized packages with the
  same fixture/candidate/provider/model/environment, ten runs per arm, retained
  manifests, and explicit variant identity.
- [ ] Rebuild and independently verify both packages.
- [ ] Compare accepted-CV cost, p95, calls, tokens, regeneration, human effort,
  grounding, and one-page correctness.
- [ ] Run `python scripts/compare_fitcv_optimization.py --baseline <baseline-package> --optimized <optimized-package> --min-relative-improvement <lead-controller-threshold> --output docs/superpowers/evidence/2026-10-06-fitcv-optimization-comparison.json`.
- [ ] Record promote, hold, or revert with evidence.

**Verification:** Full applicable test suites, explicit experiment JSON/Markdown/
peer JSON verifier arguments for each opposite-arm package, comparison-script
tests, `git diff --check`, and
`skill-verification-before-completion` returning `verified`.

**Exit Criteria:** Final decision is evidence-bound; no unsupported optimization
claim remains.

## Verification

After all admitted tasks finish:

- `python -m pytest -q`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend test -- --run`
- `npm --prefix frontend run test:e2e`
- `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --experiment-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.json --experiment-markdown docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.md --experiment-peer-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-peer.json --output .tmp/final-acceptance-report.json`
- `git diff --check`
- `skill-verification-before-completion` with fresh outputs and evidence paths

Final proof must confirm unavailable coverage stays unavailable, refresh is
atomic/idempotent, dashboard uses semantic projections, reuse/repair preserve
grounding and one-page correctness, and R5/R6 evidence is never inferred.

## Completion Criteria

1. Tasks 1–7 have complete local proof and durable evidence.
2. Every mergeable milestone received independent `review-1` review before
   merge; findings are addressed or recorded as blockers.
3. This plan contains no stale PR/branch/merge registry.
4. Code, SQL, config, tests, frontend contracts, evidence, and docs agree with
   current repository truth.
5. P1-B is marked measured only with fresh replayable proof; otherwise its
   blocker remains explicit.
6. P2, predictive trends, and unapproved provider/generation optimization stay
   deferred.
7. `skill-verification-before-completion` returns `verified`.

Plan is `active` before Task 0 writes or commits coordination state. Change to
`completed` only after final verification.
