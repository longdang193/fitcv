---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-final-artifact-integration-optimization
superseded_by: docs/superpowers/plans/2026-10-04-fitcv-p1ab-final-convergence-and-artifact-optimization-plan.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - scripts/render_acceptance_state.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - tests/test_pipeline.py
  - tests/test_cv_generator.py
  - tests/test_cv_render_acceptance.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_fitcv_cp/test_acceptance_verifier.py
  - tests/test_acceptance_state.py
  - docs/superpowers/evidence/
---

# FitCV Final-Artifact Integration Defects And First-Pass Optimization

## Goal

Close three narrow integration defects identified after PR #76, then improve
first-pass CV acceptance without reopening retrieval architecture:

1. cached reuse must preserve or freshly prove final-render acceptance;
2. overflow trimming must remove low-value claims before whole sections and must
   preserve verified requirement evidence;
3. trimmed content must be revalidated, and benchmark/report/verifier must share
   one complete page-fit measurement and outcome contract.

After those gates pass, run one current-contract incumbent/candidate experiment
and optimize the dominant deterministic retry cause. Defer P1-C and keep P2
frozen.

An accepted CV means exact persisted content has:

- required content and grounding validation;
- successful native render;
- page_count == 1 and page_fit_status == pass;
- render proof bound to exact content, template, render configuration, and
  renderer contract;
- complete lineage through trace_id and run_job_id.

## Verdict Review

Verdict is correct at merged PR #76 (cfeed507ed28a08c35df48cefaf7c87af0a2a467)
and current branch HEAD d7e7047e:

- P0 remains frozen and complete within documented scope.
- P1-A/P1-B remain blocked by integration and measurement defects, not by a
  need for another retrieval or orchestration architecture.
- Reuse validates cached content but reconstructs an accepted result without
  page_fit_status or render_acceptance; generic generation fingerprints do not
  prove final render identity.
- Overflow handling can discard whole optional sections, including unique
  project or required language evidence, instead of trimming marginal claims.
- Trimmed content can be rendered and accepted using validation performed on
  different content.
- Per-run page-fit data exists, but aggregate reporting does not expose the
  complete page-fit-success contract required by verifier.
- Historical pre-contract runs remain audit evidence but must not be presented
  as current P1 measurement evidence.
- Earlier same-workload experiment was not promotion evidence: incumbent and
  candidate each recorded 0 / 8 first-pass acceptance, while candidate final
  page-fit was 5 / 5. That cohort remains historical and rejected.
- Fresh provider-backed rerun now has two eligible ten-repeat cohorts with
  identical fixture, executable-input, model, and analysis identities. Candidate
  preserves 10 / 10 acceptance and one-page success while reducing end-to-end
  wall time.
- Root cause fixed: seeded-cohort stabilization incremented
  `configuration_revision` even when temperatures were already `0.0`, changing
  `enrich_contract_fingerprint` and forcing divergent upstream enrichment.
  Stabilization is now idempotent.

## Scope And Non-Goals

In scope:

- one final-artifact acceptance gate shared by fresh generation, cache reuse,
  bounded trim, HITL approval, persistence, and reporting;
- deterministic evidence-aware trim using existing cv_content_plan_v1 data;
- one post-trim validation/render cycle with hard one-cycle bound;
- aggregate page-fit coverage and success outcomes, current-contract cohort
  selection, and fail-closed verifier checks;
- defect-aware retry optimization after correctness closure;
- focused unit, integration, backend-boundary, and benchmark evidence.

Out of scope:

- P1-C gap aggregation or request-path product work;
- P2 feature work;
- GraphRAG, new agents, LLM verifiers, vector stores, rerankers, retrieval
  policy replacement, provider routing redesign, or broad refactoring;
- disabling cache reuse or globally suppressing retries;
- synthesizing missing lineage or page-fit facts into historical runs;
- committing credentials or copying local .env contents into tracked files.

## Implementation Outcomes

### Final-artifact contract

Every accepted path produces the same persisted fields:

~~~text
artifact_content_sha256
structured_content_fingerprint
cv_generation_input_fingerprint
template_sha256
render_config_fingerprint
renderer_contract_version
page_count
page_fit_status
render_acceptance
artifact_checksum
trace_id
run_job_id
~~~

Exact field names must follow existing repository conventions. A cache hit is
reusable only when content validation passes and render proof matches all
render-relevant fingerprints. If proof is absent or mismatched, perform native
rerender only; do not call provider. Render failure, unknown page count, or
non-one-page result cannot produce accepted artifact.

### Evidence-aware bounded trim

Use existing cv_content_plan_v1 approved claims, supported requirements,
protected numbers/dates, and section mapping. Rank removable claims/items by
deterministic marginal requirement value, with stable tie-breakers. Preserve,
in order:

1. must-have requirement evidence;
2. unique support for verified requirement;
3. high-priority job requirement support;
4. quantified outcomes and protected numbers/dates;
5. core identity, work, and education data;
6. required language evidence.

Remove duplicate or already-covered claims, verbose wording, low-priority
optional evidence, and lowest-value bullets first. Whole-section removal is a
last fallback. One trim/rerender/revalidation cycle is maximum; failure or new
content-validation loss becomes review_required.

### Lossless page-fit measurement

Benchmark snapshots expose both measurement and outcome quality:

~~~text
coverage.page_fit:
  measured
  unavailable
  total
  complete

outcomes.page_fit:
  pass
  fail
  total
  rate

page_fit_success:
  pass
  fail
  total
  rate
  complete
~~~

page_fit_success remains compatibility projection if existing consumers need
it. Measurement completeness and success rate stay separate. Verifier requires
complete measurement and 100% success for current accepted-artifact cohort.
Contract-version tags select current runs; older runs remain historical.

### First-pass optimization

Keep hybrid retrieval and frozen P0 gates. Classify retries by existing failure
signals:

~~~text
provider/transient failure -> bounded provider retry
missing/shallow section -> targeted section repair
schema/heading defect -> deterministic repair
page overflow -> bounded trim/render/revalidate
same deterministic defect twice -> review_required
~~~

Target one full provider generation plus zero or one narrow correction, not two
full generations for every recoverable defect. Promote only on identical
incumbent/candidate workload, model, provider, settings, retrieval policy,
limits, and current reporting contract.

## Execution Approach

- Mode: inline sequential
- Coordination: git-tracked
- Required skills: skill-systematic-debugging, skill-test-driven-development, skill-backend-verification, skill-performance-optimization, skill-verification-before-completion, skill-plan-document-reviewer
- Isolation: task-specific isolated worktree from approved base; preserve current untracked .tmp/, .venv/, scratch files, and local data
- Commit policy: no commits during execution; lead creates final commit only after verification and user authorizes Git disposition
- Preauthorized local actions: inspect history, edit plan-listed source/tests/config/evidence, run declared checks, read local .env through existing configuration without printing or persisting secrets
- User-approval actions: provider/network publication, push, merge, dependency installation, credential changes, destructive cleanup, discard, and acceptance-status promotion
- Parallel ownership: none; final-artifact, trim, and reporting contracts share persisted fields and must be serialized
- Sequential fallback: execute Tasks 1–7 in order in one controller-owned worktree
- Optimization fixture: C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\linkedin-2026-10-02-22-52-15.json; read-only, SHA-256 before both runs, stop if changed
- Provider credentials: load FITCV_LLM_API_KEY from repository-local .env through existing runtime configuration. Never print, copy, commit, or include value in evidence. Missing key blocks only optimization experiment, not P1-A/P1-B correctness acceptance.

## Coordination State

This historical plan is complete and superseded by the canonical P1-A/B plan
listed in `superseded_by`. Its task ledger is reconciled against current proof;
newer evidence and remaining work belong to the successor plan.

- Coordination owner: single lead controller
- Coordination schema: 2
- Branch: historical task-specific branch; current execution continues on the successor plan
- Base: historical base `d7e7047e`; current proof is bound to successor-plan evidence
- Workspace ownership: historical task ledger closed; current checkout and unrelated untracked files remain untouched
- Next action: finish successor-plan review and Git disposition only after fresh verification
- Blockers: P1-C and P2 remain intentional deferrals; optimization promotion remains rejected

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | complete | historical worktree | lead | none | baseline plus failing regressions | successor-plan evidence |
| Task 2 | complete | historical worktree | lead | Task 1 | cache final-render boundary | successor-plan evidence |
| Task 3 | complete | historical worktree | lead | Task 1 | evidence-aware trim and post-trim validation | successor-plan evidence |
| Task 4 | complete | historical worktree | lead | Tasks 2–3 | fresh generation/cache/overflow acceptance matrix | successor-plan evidence |
| Task 5 | complete | historical worktree | lead | Task 1 | aggregate benchmark/verifier contract | successor-plan evidence |
| Task 6 | complete | historical worktree | lead | Tasks 4–5 | current-contract cohort and optimization experiment | R13; promotion rejected |
| Task 7 | complete | current worktree | lead | Task 6 | final verification and reconciliation | R13 plus fresh CAS regression; Git disposition belongs to successor plan |

## Task Breakdown

### Task 1: Reproduce defects and freeze baseline

**Purpose:** Confirm each verdict finding against current source, trace shared
callers, and capture focused failing proof before behavior changes.

**Task Function:** systematic root-cause tracing and regression design.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: resolve through Planning Dispatch after approval; use lowest profile that can trace shared contracts and preserve evidence.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent contract and regression review after implementation.

**Specification Coverage:** All three narrow integration defects; frozen P0
behavior; no historical-data mutation.

**Required Skills:** skill-systematic-debugging, skill-test-driven-development, skill-backend-verification

**Files And Symbols:**
- Inspect: src/fitcv/agentic_cv_generation.py:_reusable_result_or_none, _finalize_generation_result, _build_result, generate_from_analysis, build_cv_content_plan, build_cv_generation_input_fingerprint.
- Inspect: src/fitcv/cv_generator.py:render_cv_markdown, render_cv_template and native render boundary exercised by tests/test_cv_render_acceptance.py.
- Inspect: src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact; src/fitcv_cp/worker_job.py:_build_cv_generation_debug_payload and accepted-artifact event construction.
- Inspect: src/fitcv_cp/run_artifact_contracts.py:accepted_cv_artifact_event_v1, collect_normalized_generation_traces, build_accepted_cv_effort_projection.
- Modify tests: tests/test_pipeline.py, tests/test_cv_render_acceptance.py, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_worker_job.py, tests/test_fitcv_cp/test_run_artifact_contracts.py.

**Dependencies:** Current branch HEAD d7e7047e and verdict attachment are authoritative.

**Authority:**
- Preauthorized local actions: inspect history/source, add focused failing tests, run read-only baseline commands.
- Stop for: unexpected tracked changes, missing native-render boundary, inability to reproduce defect, or any P0 gate change.

**Steps:**
- [x] Record git status, HEAD, focused test baseline, and active acceptance-state status.
- [x] Trace fresh generation, cache reuse, trim/overflow, HITL approval, persistence, and benchmark projection callers; identify one owner per shared field.
- [x] Add fixtures for reusable content with absent render proof; render-proof fingerprint mismatch; overflow preserving project/language evidence; trim that invalidates grounding; and aggregate page-fit pass/fail records.
- [x] Assert current behavior fails only new contract expectations while existing P0 regressions remain green.

**Verification:**
- [x] python -m pytest tests/test_pipeline.py tests/test_cv_render_acceptance.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_acceptance_state.py -q
- Expected: baseline output recorded; new tests identify three defects without editing historical evidence.

**Exit Criteria:** Root cause and shared callers are named, focused failing proof exists, and no unrelated tracked file changes occur.

### Task 2: Unify cached reuse with final-render acceptance

**Purpose:** Keep cache reuse cheap while ensuring accepted cache hits carry valid
final-render proof for exact persisted content.

**Task Function:** final-artifact contract implementation.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: contract-sensitive backend change with narrow source ownership.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent cache and persistence boundary review.

**Specification Coverage:** Cached reuse cannot bypass page-fit/render acceptance;
fingerprint mismatch rerenders locally and never calls provider.

**Required Skills:** skill-test-driven-development, skill-backend-verification

**Files And Symbols:**
- Modify: src/fitcv/agentic_cv_generation.py:_reusable_result_or_none, _finalize_generation_result, _build_result, generate_from_analysis.
- Add or modify adjacent helpers in src/fitcv/agentic_cv_generation.py for structured-content, template, render-config, renderer-contract, page-count, and checksum proof matching.
- Modify propagation: src/fitcv/pipeline.py trace fields; src/fitcv_cp/worker_job.py accepted-artifact event construction; src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact.
- Verify: tests/test_pipeline.py, tests/test_fitcv_cp/test_worker_job.py, tests/test_fitcv_cp/test_app.py, tests/test_cv_render_acceptance.py.

**Dependencies:** Task 1 failing fixtures and current persisted field names.

**Authority:**
- Preauthorized local actions: edit final-artifact fields and focused tests.
- Stop for: any provider call on proof mismatch, acceptance of unknown/non-one-page render, or contract field duplication across owners.

**Steps:**
- [x] Define one render-proof payload with content SHA-256, template SHA-256, render-config fingerprint, renderer contract/version, page count, page-fit status, and artifact checksum.
- [x] Require content validation plus exact render-proof match before reuse. Treat absent, stale, or legacy proof as non-reusable proof, not accepted status.
- [x] On proof mismatch, rerender native content locally, preserve provider-call count, and feed resulting proof through same finalization path as fresh generation.
- [x] Make fresh generation, cached reuse, HITL approval, persistence, and accepted-artifact events emit identical final-artifact acceptance fields.
- [x] Preserve trace_id and run_job_id lineage through rerender and reuse; do not infer proof from job_url or generic generation fingerprint alone.

**Verification:** Focused tests cover matching proof reuse, missing proof, each fingerprint mismatch, native rerender without provider call, render failure, unknown page count, and page_count != 1.

**Exit Criteria:** Cache hits cannot create a special accepted path, and local rerender repairs stale proof without increasing provider calls.

### Task 3: Replace coarse overflow trim and revalidate exact trimmed content

**Purpose:** Preserve high-value verified evidence while enforcing one-page output
with one bounded trim/rerender/revalidation cycle.

**Task Function:** deterministic content reduction and validation integration.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: evidence-preservation logic with deterministic tie-breaking and backend proof.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent grounding and requirement-retention review.

**Specification Coverage:** cv_content_plan_v1 is trimming SSOT; post-trim validation uses exact persisted content and same grounding payload.

**Required Skills:** skill-systematic-debugging, skill-test-driven-development, skill-backend-verification

**Files And Symbols:**
- Modify: src/fitcv/agentic_cv_generation.py:build_cv_content_plan, _build_generation_ready_analysis, _run_repair_cycle, _generate_fresh_from_analysis and final-artifact flow from Task 2.
- Reuse or extend: src/fitcv/cv_generator.py:render_cv_markdown; existing evidence selection helpers in src/fitcv/evidence.py such as _trim_selected_project_entry, _trim_selected_experience_entry, and cv_content_plan_v1 claim metadata.
- Modify propagation: src/fitcv/pipeline.py trace output fields for trim_count, trimmed_claim_ids, trim_reason, post_trim_validation_status, and post_trim_missing_requirements.
- Verify: tests/test_cv_generator.py, tests/test_cv_render_acceptance.py, tests/test_pipeline_agentic_late_stage.py, tests/test_pipeline.py.

**Dependencies:** Task 1 fixtures; Task 2 final-render proof contract.

**Authority:**
- Preauthorized local actions: edit bounded trim and validation flow plus focused regressions.
- Stop for: new retrieval policy, LLM trim call, unbounded retry loop, loss of protected requirement evidence, or acceptance based on pre-trim validation.

**Steps:**
- [x] Build removable units from approved claims/items rather than deleting projects, languages, certifications, or publications wholesale.
- [x] Compute deterministic marginal requirement value from approved claim support, requirement priority, uniqueness, quantified outcomes, protected values, section identity, and stable claim ID tie-breakers.
- [x] Remove duplicate/low-value claims first; use whole-section removal only after claim-level candidates are exhausted and no protected evidence is removed.
- [x] Render exact trimmed structured content, rerun existing content and grounding validation against exact content, then rerun native render and page-count/checksum proof.
- [x] Permit at most one trim cycle. Persist trim diagnostics; route overflow, render failure, missing page count, or post-trim validation failure to review_required with no accepted artifact event.

**Verification:** Project-only technical evidence and required language evidence survive overflow trim when uniquely supporting verified requirements; duplicate/low-value claims are removed first; trim output is validated and rendered again.

**Exit Criteria:** Trimmed persisted content and validation/render proof always refer to same content, with bounded deterministic behavior and complete diagnostics.

### Task 4: Prove all accepted-artifact paths converge

**Purpose:** Add integration proof across fresh generation, cache reuse, overflow repair,
irreducible overflow, HITL approval, persistence, and event emission.

**Task Function:** end-to-end acceptance contract verification.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: cross-module backend boundary and side-effect proof.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: acceptance-matrix review independent from implementation.

**Specification Coverage:** No accepted path bypasses final-artifact contract.

**Required Skills:** skill-test-driven-development, skill-backend-verification

**Files And Symbols:**
- Modify: tests/test_pipeline.py, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_worker_job.py, tests/test_cv_render_acceptance.py.
- Verify: src/fitcv/agentic_cv_generation.py:generate_from_analysis, src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact, src/fitcv_cp/worker_job.py, and accepted event schema in src/fitcv_cp/run_artifact_contracts.py.

**Dependencies:** Tasks 2 and 3.

**Authority:**
- Preauthorized local actions: add integration fixtures and run backend boundary tests.
- Stop for: accepted artifact event without one-page proof, persisted content differing from validated content, or missing final state evidence.

**Steps:**
- [x] Scenario A: valid fresh generation, one-page native render, accepted and persistable.
- [x] Scenario B: unchanged reusable artifact, zero provider calls, proof reused or local rerendered, accepted and persistable.
- [x] Scenario C: valid two-page content, evidence-aware trim, exact post-trim validation, one-page rerender, accepted.
- [x] Scenario D: irreducible overflow or post-trim requirement loss, review_required, no accepted event.
- [x] Assert persisted artifact, debug trace, HITL event, and normalized report carry matching content/checksum/page-fit fields.

**Verification:** Run focused integration suite from Tasks 2–3.
Expected: A–C converge on same accepted contract; D fails closed; provider calls remain bounded.

**Exit Criteria:** Backend boundary proof covers success, failure, final state, side effects, and idempotent reuse behavior.

### Task 5: Complete aggregate page-fit and current-contract verification

**Purpose:** Make benchmark, acceptance-state rendering, and verifier consume one
lossless page-fit contract and separate historical evidence from current gates.

**Task Function:** measurement-contract implementation and fail-closed verification.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: reporting contract change with generated-state reconciliation.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent benchmark-to-verifier contract validation.

**Specification Coverage:** Aggregate page_fit_success; explicit measurement/outcome separation; current-contract cohort; no invented historical facts.

**Required Skills:** skill-test-driven-development, skill-backend-verification, skill-performance-optimization

**Files And Symbols:**
- Modify: scripts/benchmark_cv_efficiency.py:_run_snapshot, build_baseline, report serialization, and compatibility projection.
- Modify: scripts/verify_fitcv_acceptance.py:verify_acceptance, _run_runtime_efficiency_evidence_check, and report gate construction.
- Modify canonical state: config/acceptance_state.yaml; regenerate artifacts/acceptance_state.json only through scripts/render_acceptance_state.py.
- Modify contracts: src/fitcv_cp/run_artifact_contracts.py:collect_normalized_generation_traces, build_accepted_cv_effort_projection only for page-fit/version fields; preserve one normalization owner.
- Verify: tests/test_benchmark_cv_efficiency.py, tests/test_fitcv_cp/test_acceptance_verifier.py, tests/test_acceptance_state.py, tests/test_fitcv_cp/test_run_artifact_contracts.py.

**Dependencies:** Task 4 accepted-artifact fields; historical evidence files and acceptance-state references.

**Authority:**
- Preauthorized local actions: edit benchmark/verifier contracts, tests, canonical YAML, and generated JSON.
- Stop for: synthesized historical attribution, incomplete aggregate contract accepted as measured, or stale generated JSON.

**Steps:**
- [x] Aggregate page-fit measurements into coverage.page_fit, outcomes.page_fit, and compatibility page_fit_success without dropping unavailable values.
- [x] Add final-artifact, trace, and efficiency contract versions to new persisted/report records; select current P1 evidence by version, not date guesswork.
- [x] Keep historical pre-contract reports for audit/trend context, label historical/superseded, and exclude from current P1 measurement eligibility.
- [x] Make verifier require complete page-fit measurement and 100% success for current accepted-artifact cohort; reject missing, partial, contradictory, or falsely measured status.
- [x] Run benchmark-to-verifier integration tests using clean pass, measured failure, unavailable measurement, conflict, unmatched artifact, and historical-only cohorts.

**Verification:**
- [x] python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json
- [x] Focused benchmark, verifier, state-render, and contract tests.
- Expected: clean current-contract report passes only with complete measurement and 100% success; incomplete or historical-only evidence remains blocked.

**Exit Criteria:** One reporting path supplies page-fit measurement and outcome status, and verifier decisions match report contents without historical synthesis.

### Task 6: Run current-contract cohort and optimize first-pass acceptance

**Purpose:** Measure and improve first-pass acceptance only after correctness and
reporting gates are closed.

**Task Function:** controlled performance experiment and defect-aware retry tuning.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: measured optimization with provider/runtime dependency and strict comparability.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent experiment evidence and promotion-gate review.

**Specification Coverage:** Improve first-pass acceptance; preserve frozen retrieval/P0 behavior; use repository .env credential; separate experiment blocker from P1 closure.

**Required Skills:** skill-performance-optimization, skill-backend-verification, skill-verification-before-completion

**Files And Symbols:**
- Modify only if measured defect requires it: src/fitcv/agentic_cv_generation.py:_run_repair_cycle, _build_fallback_retry_executor, _determine_repair_targets; trace fields in src/fitcv/pipeline.py.
- Verify: scripts/benchmark_cv_efficiency.py, existing generation tests, and current-contract evidence under docs/superpowers/evidence/.
- Use fixture: C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\linkedin-2026-10-02-22-52-15.json.

**Dependencies:** Tasks 4 and 5 pass; current-contract cohort eligible; FITCV_LLM_API_KEY available from local .env.

**Authority:**
- Preauthorized local actions: read key through existing config, run incumbent/candidate locally, add bounded retry tests, write evidence without secrets.
- Stop for: missing key, changed fixture/model/provider/settings, frozen P0 regression, reporting conflict, or need for a second full generation where narrow correction should suffice.

**Steps:**
- [x] Record fixture SHA-256, candidate profile, job order, model, provider, retrieval policy, temperature/settings, limits, code revision, and runtime environment for both arms.
- [x] Run incumbent and candidate through configured FitCV runtime using same .env-provided key and workload; do not create a new runner.
- [x] Classify every non-first-pass outcome into provider/transient, missing section, schema/heading, overflow, or repeated deterministic defect.
- [x] Apply smallest measured correction: bounded provider retry for transient errors, targeted section repair for missing sections, deterministic repair for schema/heading defects, trim/render/revalidate for overflow.
- [x] Compare first-pass acceptance, accepted artifacts, final page-fit success, provider calls per accepted CV, tokens per accepted CV, regenerations per accepted CV, failed retry rate, latency, trace conflicts, and attribution completeness.
- [x] Promote only if candidate improves first-pass acceptance or dominant retry metric without violating P0, grounding, final-artifact, page-fit, or reporting gates; otherwise retain incumbent and record rejection.

**Verification:**
- [x] Run exact benchmark command used by existing FitCV efficiency evidence with both arms and current contract versions.
- [x] Confirm .env key is absent from stdout, logs, JSON, Markdown, Git diff, and generated artifacts.
- Expected: comparable evidence with explicit experiment status; missing credentials blocks experiment only and does not alter P1 correctness status.

**Exit Criteria:** Optimization has reproducible current-contract evidence and either narrowly justified promotion or recorded rejection; no architecture expansion occurs.

**Historical result (2026-10-05; superseded by R13):** Fresh source-bound incumbent `local_first` and
candidate `provider_first` cohorts completed with 10 runs each under identical
`cold_first_then_frozen` upstream policy. Manifest, declared executable-input,
fixture, model, runtime, and provider provenance match. `provider_first` accepted
10 / 10 versus `local_first` 5 / 10, used fewer provider calls, tokens, and wall
time in this rerun. Candidate promotion remains deferred pending repeatable
comparable savings; production default remains `local_first`. Downstream provider
analysis identity is informational because provider output is stochastic.
Evidence:
`docs/superpowers/evidence/2026-10-05-fitcv-p1ab-provider-backed-convergence-r5.json`.
R5 is retained for audit history only; R13 is current decision evidence.

### Task 7: Final verification and reconciliation

**Purpose:** Verify cross-task behavior, reconcile generated surfaces, and leave
P1-C/P2 explicitly deferred.

**Task Function:** final acceptance and evidence reconciliation.

**Template Profile:**
- Controller-selected: unresolved
- Selection basis: fresh full-scope verification and change-control review.

**Validator Profile:**
- Controller-selected: unresolved
- Selection basis: independent final verification.

**Specification Coverage:** All implementation outcomes, regression proof, benchmark integrity, and explicit deferrals.

**Required Skills:** skill-verification-before-completion, skill-backend-verification, skill-performance-optimization

**Files And Symbols:**
- Verify all Task 1–6 targets, generated acceptance state, current evidence pair, and plan-owned docs.
- Inspect: config/acceptance_state.yaml, artifacts/acceptance_state.json, docs/superpowers/evidence/, git diff --check.

**Dependencies:** Tasks 1–6 complete or explicitly blocked with evidence.

**Authority:**
- Preauthorized local actions: run fresh verification, reconcile generated outputs, record blockers and deferrals.
- Stop for: unresolved required failure, stale generated output, unrecorded scope change, leaked secret, or false acceptance claim.

**Steps:**
- [x] Run focused regression suites, backend boundary checks, benchmark-to-verifier checks, and full applicable test command.
- [x] Rebuild generated acceptance state from canonical YAML and verify deterministic output.
- [x] Run git diff --check, inspect tracked diff, and confirm unrelated untracked files remain untouched.
- [x] Confirm P1-A/P1-B status follows current-contract evidence, optimization status is separate, P1-C is deferred, and P2 remains frozen.
- [x] Record final evidence paths, commands, metric definitions, deviations, and rollback/stop conditions.

**Verification:**
- [x] python -m pytest -q
- [x] python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json
- [x] git diff --check
- Expected: fresh tests pass, generated state deterministic, diff whitespace-clean, and no required contract remains unverified.

**Exit Criteria:** skill-verification-before-completion returns verified; only then may plan status move from proposed to completed.

**Historical verification (2026-10-05; superseded by R4):** Full backend suite passes `3161 passed,
8 skipped`; focused verifier tests pass; both fresh current-source
experiment-bound acceptance verifier runs pass; paired manifests bind to source
`ef66aa04` with equal declared-input and cohort-setup identities; this evidence
predates the completed declared-input inventory and is superseded by R5.

**Final verification (2026-10-05):** R13 is historical decision evidence,
bound to source `2564e20`, not proof for current branch head. It binds both
manifests to identical declared-input/cohort identities;
`local_first` remains default because `provider_first` ties correctness and
provider calls while increasing token cost. R5 is superseded and retained only
for audit history. Evidence:
`docs/superpowers/evidence/2026-10-05-fitcv-p1ab-provider-backed-convergence-r13.json`.
Fresh CAS regression proof belongs to current source and rejects review actions
when pipeline revision advances after resource snapshot.

## Verification

Final artifact-level proof must show:

- fresh, cached, trimmed, and HITL-approved paths converge on one accepted
  final-artifact contract;
- stale cached proof rerenders locally without provider call;
- trim preserves unique verified requirements and exact post-trim validation;
- irreducible overflow or broken grounding fails closed;
- aggregate page-fit coverage and success are complete and verifier-consistent;
- current-contract evidence is separated from historical evidence;
- incumbent/candidate experiment uses identical workload/runtime and local .env
  credential without secret leakage;
- frozen P0 gates remain unchanged; P1-C and P2 remain deferred.

Run final proof through skill-verification-before-completion. Do not promote
acceptance state from source inspection alone.

## Completion Criteria

Plan execution is complete only when:

1. all required implementation outcomes are satisfied;
2. all task-local verification passes or an evidence-backed blocker is recorded;
3. generated acceptance state and evidence outputs match canonical inputs;
4. no historical record was rewritten to invent missing lineage or page-fit facts;
5. optimization result is reproducible or explicitly rejected;
6. P1-C and P2 remain deferred;
7. deviations, rollback decisions, and final commands are recorded;
8. skill-verification-before-completion returns verified.

This plan is completed as historical scope and superseded by the canonical
successor plan. No historical evidence is rewritten; current implementation,
review, commit, push, merge, and acceptance decisions belong to the successor.
