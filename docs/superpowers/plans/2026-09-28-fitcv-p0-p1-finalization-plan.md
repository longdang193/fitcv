---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-finalization
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - scripts/benchmark_requirement_support.py
  - scripts/benchmark_ranking.py
  - data/fitcv-p0-corpus
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_ranking_evaluation.py
  - tests/test_p0_public_corpus.py
  - docs/pipeline.md
  - docs/api.md
  - docs/observability.md
---

# FitCV P0 and P1 Finalization Plan

## Review Basis

The supplied consolidated verdict is directionally correct and source review
supports its main conclusion: architecture is sufficient, but integration
contracts remain incomplete. The earlier closeout plan is retained as history;
this plan starts from current `main` at `72c822b1` and does not assume checked
boxes are proof.

Current acceptance state:

- P0-C: source-boundary fixes exist, but candidate-answer and all caller paths
  require fresh end-to-end proof.
- P0-A: benchmark plumbing and fixture integrity exist; multilingual quality
  decision remains blocked until one approved backend and mixed-label evidence
  are available.
- P0-B: comparison tooling exists; prior `6/17` validation coverage was caused
  by fixture/harness defects, now corrected to `17/17`. No new reviewed labels
  were collected, so promotion-grade quality claims remain blocked.
- P1-A: content-plan filtering exists; writer-context reduction, repair impact,
  and one-page truthful output are not decision-grade.
- P1-B: storage and review actions exist; lifecycle proof from review through
  worker refresh and uncertainty identity reuse is incomplete.
- P1-C and P2 remain explicitly deferred.

## Goal

Finalize P0 and P1 by enforcing one fail-closed evidence contract across source
evidence and candidate answers, completing profile-scoped uncertainty review and
refresh, measuring P1-A value, and producing reproducible P0-A/P0-B decisions or
explicit provider/data blockers. Do not add agents, graphs, new evidence
models, retrieval layers, or speculative orchestration.

## Implementation Outcomes

### Evidence correctness

- Candidate answers enter the existing requirement-support contract as temporary,
  requirement-scoped evidence; unsupported, contradictory, ambiguous, and empty
  answers never become verified claims.
- `CONFIRM_OMIT` omits a claim and `OVERRIDE_BLOCK` permits workflow continuation
  without manufacturing factual support.
- Canonical profile evidence and candidate-answer evidence produce identical
  qualifier and verification semantics.

### Uncertainty lifecycle

- One uncertainty ID and profile/source identity survive analysis, generation,
  debug persistence, review queue, resolution storage, worker refresh, and fresh
  analysis.
- Review actions expose `pending`, `processing`, `resolved`, and `failed` states;
  `resolved` requires successful refreshed validation.
- Stale profile revision, stale source fingerprint, malformed storage rows, and
  duplicate actions fail closed and remain auditable.

### Measurement and decisions

- P1-A reports before/after evidence context, generation tokens, repairs, and
  factual-preservation checks before any page-budget optimizer is added.
- P0-A reports incumbent, lexical, and one approved multilingual arm on held-out
  mixed-label data, or records a precise `not_run` provider blocker.
- P0-B records mismatch classification, qualified support metrics, context and
  latency cost, and a bounded retain/promote decision without changing production
  defaults prematurely.
- P1-C/P2 deferrals and all unresolved P0-A/P0-B gates remain explicit.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `verified per-task checkpoint commits preauthorized`
- Preauthorized local actions: `edit declared files, run declared tests and offline benchmarks, update evidence and plan state, create local checkpoint commits`
- User-approval actions: `push, merge, publication, external provider or credential changes, destructive cleanup, and promotion of a blocked benchmark`
- Parallel ownership: `none; shared contracts and sequential evidence require one lead controller`
- Sequential fallback: `Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `72c822b1`
- Expected workspace: `clean tracked state; preserve unrelated .tmp/`
- Next action: `run final verification and reconcile acceptance evidence`
- Blockers: `approved multilingual backend and promotion-grade P0-B review coverage may remain unavailable`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | mismatch classification report and focused benchmark tests | 17/17 validation cases pass; no new labels collected |
| Task 2 | `completed` | current | `codex` | Task 1 | candidate-answer proof boundary tests | answer skill-mismatch regression passes; 159 focused tests pass |
| Task 3 | `completed` | current | `codex` | Task 2 | review-to-refresh lifecycle trace | control-plane/runtime suite passes: 789 tests |
| Task 4 | `completed` | current | `codex` | Task 2 | writer-context and repair measurement | writer filtering/repair suite passes: 223 tests |
| Task 5 | `completed` | current | `codex` | Tasks 1–4 | P0-A/P0-B decision reports or explicit blockers | P0-A measured/blocked; P0-B measured with production retained |
| Task 6 | `completed` | current | `codex` | Tasks 2–5 | fresh final verification and acceptance record | 2865 passed, 4 skipped; diff clean; blockers retained explicitly |

## Task Breakdown

### Task 1: Classify P0-B validation mismatches before collecting labels

**Purpose:**
- Explain every failed validation scenario before expanding the fixture or
  changing promotion claims.

**Task Function:**
- Diagnostic classification of benchmark failures and fixture assumptions.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `source-first diagnosis; shared benchmark contract; low write risk`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `benchmark tests, fixture inspection, and report review`

**Specification Coverage:**
- Distinguish runtime bug, stale expectation, invalid benchmark assumption, and
  genuine recall gap for all 11 non-passing scenarios.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:run_benchmark`, arm registry, validation report assembly
- Inspect: `tests/fixtures/requirement_support_benchmark.json`
- Inspect: `src/fitcv/evidence.py:retrieve_evidence_bundle`, qualifier assessment, final selection
- Modify: `tests/test_benchmark_requirement_support.py`, comparison evidence, and fixture only when classification proves expectation drift
- Verify: `scripts/compare_rag_impact.py`, `docs/pipeline.md`

**Dependencies:**
- Current source, fixture, and existing `.tmp` benchmark outputs.
- No new labels until each mismatch receives one classification and owner.

**Authority:**
- Preauthorized local actions: `inspect source and benchmark artifacts, add diagnostic tests/docs, update stale expectations when proven, and create a local checkpoint commit`
- Stop for: `production retrieval changes, unbounded fixture expansion, external providers, or unresolved classification ambiguity`

**Steps:**
- [x] Step 1: Re-run the focused comparison with fixed fixture bytes and record all 17 scenario outcomes.
- [x] Step 2: Map each failure to runtime bug, stale expectation, invalid assumption, or genuine recall gap with file/symbol evidence.
- [x] Step 3: Add regression coverage for corrected semantics and update only proven-stale expectations.
- [x] Step 4: Publish mismatch counts and residual data gaps; leave labels blocked where evidence is insufficient.

**Verification:**
- [x] `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_rag_impact.py` — 25 passed
- [x] `uv run python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/p0b-production-finalization.json` — 17/17 validation cases pass
- Expected: all 17 scenarios are classified; no unexplained failure is treated as a label gap.

**Exit Criteria:**
- Every mismatch has classification, evidence, and disposition; fixture changes are minimal and justified.

### Task 2: Close P0-C candidate-answer proof boundary

**Purpose:**
- Make candidate answers another input to the canonical requirement-support
  contract instead of an implicit verification shortcut.

**Task Function:**
- Root-cause repair and regression proof for evidence and answer integration.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `high correctness risk; shared evidence contract; bounded files`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `canonical-path tests and direct boundary inspection`

**Specification Coverage:**
- Candidate answers must preserve skill-local qualifiers, contradiction,
  ambiguity, and empty-answer semantics used by normal evidence.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py:project_candidate_evidence`, `_build_support_fragments`, `_assess_requirement_support`
- Inspect/modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`, `_append_resolution_evidence`, `_resolution_map`
- Inspect: `src/fitcv/pipeline_contracts.py:REQUIREMENT_SUPPORT_POLICY_VERSION`, `build_requirement_uncertainty`
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_validator.py`, `docs/api.md`, `docs/pipeline.md`

**Dependencies:**
- Task 1 classification must not identify an unresolved benchmark defect in the
  shared qualifier contract.

**Authority:**
- Preauthorized local actions: `edit evidence and analysis contracts, add focused regression tests/docs, run direct boundary checks, and create a local checkpoint commit`
- Stop for: `new evaluator subsystem, metadata-derived proof, production retrieval redesign, or any verified claim without source-scoped evidence`

**Steps:**
- [x] Step 1: Write failing tests for the answer matrix: exact SQL, Python-for-SQL mismatch, classroom SQL, contradiction, underspecified SQL, and empty answer.
- [x] Step 2: Route `RESOLVE_WITH_ANSWER` through a temporary requirement-scoped fragment and existing qualifier assessment.
- [x] Step 3: Keep `CONFIRM_OMIT` non-evidentiary and `OVERRIDE_BLOCK` workflow-only; reject falsey or stale resolution identity.
- [x] Step 4: Trace profile evidence and candidate-answer evidence through projection, retrieval, coverage, uncertainty, and generation.
- [x] Step 5: Bump policy/fingerprint invalidation only if source contract changes; reject stale artifacts safely.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py` — 159 passed
- [x] Direct trace proves both input paths produce identical verification semantics.
- Expected: only qualified, requirement-scoped answers become verified; all other cases remain unverified, contradicted, pending, or omitted.

**Exit Criteria:**
- Candidate-answer proof bypass is closed with failing-first regression proof and no metadata donation path.

### Task 3: Complete P1-B uncertainty and review lifecycle

**Purpose:**
- Make review actions asynchronous, profile-scoped, idempotent, and truthful
  across storage, worker refresh, and queue state.

**Task Function:**
- Control-plane lifecycle repair and end-to-end boundary verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `cross-layer state contract; persistence and refresh risk`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `sqlite, API, worker, analysis, generation, and queue tests`

**Specification Coverage:**
- One uncertainty ID survives analysis → generation → debug record → review
  queue → resolution → worker → fresh analysis; terminal `resolved` requires
  successful validation.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv_cp/worker_job.py:_load_requirement_resolutions`, `_persist_resolution_reanalysis`
- Inspect/modify: `src/fitcv_cp/app.py:admin_run_cv_review_action`, batch review action, queue refresh
- Inspect/modify: `src/fitcv_cp/sqlite_store.py:requirement_resolutions` persistence/list/upsert helpers
- Inspect/modify: `src/fitcv/pipeline_contracts.py:build_requirement_uncertainty`
- Inspect: `src/fitcv/agentic_cv_analysis.py:build_cv_analysis_record`, generation result contracts
- Verify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_cv_generation_reason_mapping.py`

**Dependencies:**
- Task 2 must establish final answer-verification semantics before refresh can
  classify a resolution as resolved.

**Authority:**
- Preauthorized local actions: `edit declared control-plane and lifecycle paths, add direct boundary tests, run SQLite/API/worker checks, and create a local checkpoint commit`
- Stop for: `schema replacement, destructive migration, external notifications, implicit auto-approval, or state marked resolved before refreshed validation`

**Steps:**
- [x] Step 1: Add failing lifecycle tests for `pending`, `processing`, `resolved`, and `failed` action states.
- [x] Step 2: Repair resolution loading, persistence, identity replacement, and malformed-row handling; guarantee list return and profile/source scoping.
- [x] Step 3: Persist review action before refresh, run one bounded impacted-job re-analysis, and update queue state only from refresh result.
- [x] Step 4: Preserve uncertainty ID, resolution ID/action, coverage, content plan, and debug metadata on every return path.
- [x] Step 5: Prove contradiction, `CONFIRM_OMIT`, `OVERRIDE_BLOCK`, stale identity, duplicate action, and failed refresh behavior.

**Verification:**
- [x] `uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py` — 789 passed
- [x] Direct trace records storage before/after, worker load, analysis status, generation status, debug replacement, and queue state.
- Expected: `uncertainty_id_before == uncertainty_id_after_refresh`; resolved state appears only after successful re-analysis.

**Exit Criteria:**
- Review-to-refresh lifecycle is idempotent, auditable, profile/source scoped, and fail-closed.

### Task 4: Prove P1-A compiler value and constrain writer context

**Purpose:**
- Measure whether approved-evidence compilation reduces context and repairs while
  preserving truthful output before adding any optimizer.

**Task Function:**
- Content-plan integration and bounded measurement.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `existing compiler; measurement-first scope; no new optimizer`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `writer, pipeline, repair, and render contract tests`

**Specification Coverage:**
- Writer receives only approved evidence from `cv_content_plan_v1`; diagnostics
  retain full evidence; one bounded section repair revalidates the full CV.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, `src/fitcv/pipeline.py`
- Inspect: content-plan builder and generation result contracts
- Verify: `tests/test_cv_generator.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_cv_generation_reason_mapping.py`, `docs/observability.md`

**Dependencies:**
- Tasks 2–3 must provide trustworthy coverage and stable uncertainty state.

**Authority:**
- Preauthorized local actions: `edit writer input and metrics only, add bounded regression tests, run token/repair measurements, and create a local checkpoint commit`
- Stop for: `new page optimizer before baseline measurement, loss of audit evidence, unsupported claim suppression, or visual redesign outside content correctness`

**Steps:**
- [x] Step 1: Add failing test proving writer input is limited to `content_plan.approved_evidence_ids` while diagnostics retain full evidence.
- [x] Step 2: Verify approved claims, protected numbers/dates, omission reasons, enabled sections, and uncertainty notes survive compilation.
- [x] Step 3: Add one bounded section repair path and full-CV revalidation without regenerating unaffected sections.
- [x] Step 4: Measure before/after evidence tokens, generation tokens, repair count, factual validation, and rendered page count.
- [x] Step 5: Add a simple budget only if measurements show need; use fixed limits, not a speculative optimizer.

**Verification:**
- [x] `uv run pytest -q tests/test_cv_generator.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generation_reason_mapping.py` — 223 passed
- [x] Scorecard contains before/after context, tokens, repairs, preserved claims, and page count.
- Expected: less or equal writer context, no factual regression, and bounded repair behavior is observable.

**Exit Criteria:**
- P1-A has measured value or a recorded no-benefit result; no page-budget complexity is added without evidence.

### Task 5: Run P0-A/P0-B decision experiments without promotion shortcuts

**Purpose:**
- Convert ready benchmark plumbing into explicit decisions while preserving blocked
  states where provider or reviewed-data gates remain unavailable.

**Task Function:**
- Offline retrieval/evidence experiment and acceptance decision.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `measurement and data-governance risk; production defaults protected`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `manifest/hash checks, benchmark schema tests, and report inspection`

**Specification Coverage:**
- P0-A compares incumbent, lexical, and one approved multilingual encoder on
  mixed-label held-out data; P0-B compares production, full-pool diagnostic, and
  lexical-only arms after Task 1 classification.

**Required Skills:**
- `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `scripts/benchmark_ranking.py`, `scripts/benchmark_requirement_support.py`, `scripts/compare_rag_impact.py`
- Inspect/modify: `data/fitcv-p0-corpus/p0a/*`, `data/fitcv-p0-corpus/p0b/*` only when reviewed evidence or manifest rules justify it
- Verify: `tests/test_ranking_evaluation.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_p0_public_corpus.py`, `docs/pipeline.md`

**Dependencies:**
- Task 1 classification complete; Tasks 2–4 provide corrected semantics and
  comparable metrics.
- Approved multilingual backend and promotion-grade reviewed labels may remain
  unavailable; record `not_run` with exact reason instead of substituting an
  unapproved provider or fabricated labels.

**Authority:**
- Preauthorized local actions: `run offline benchmarks, update report schemas/docs/manifests for measured facts, add justified fixture labels, and create a local checkpoint commit`
- Stop for: `credential/provider setup, production default changes, unreviewed labels, benchmark promotion on synthetic/all-positive data, or semantic-layer deletion before comparison proof`

**Steps:**
- [x] Step 1: Verify fixture bytes, split counts, label distribution, and report `fixture_sha256` binding.
- [x] Step 2: Run P0-A incumbent and lexical arms; run multilingual arm only with an approved backend, otherwise emit schema-valid `not_run`.
- [x] Step 3: Run P0-B production, full-pool diagnostic, and lexical-only arms over only classified scenarios and approved reviewed evidence.
- [x] Step 4: Report Recall@10/20, Precision@10, nDCG, qualified support recall, retrieval-to-selection loss, context size, cold/warm latency, provider calls, and validation outcomes.
- [x] Step 5: Retain production defaults unless explicit thresholds pass; do not delete semantic scoring or add profile-artifact reuse without measured benefit.

**Verification:**
- [x] `uv run pytest -q tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_p0_public_corpus.py` — 41 ranking/public-corpus tests plus 25 P0-B tests
- [x] Run benchmark commands with outputs under `.tmp/`; inspect `measured`, `blocked`, `not_run`, and `not_applicable` status semantics.
- Expected: reproducible reports or precise blockers; no unsupported promotion claim.

**Exit Criteria:**
- P0-A/P0-B each have a bounded decision or explicit evidence/provider blocker with production behavior unchanged.

### Task 6: Build accepted-CV scorecard and close plan

**Purpose:**
- Produce fresh final proof, reconcile docs and evidence, and state exactly what is
  complete, blocked, or deferred.

**Task Function:**
- Final verification and acceptance record.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `cross-surface acceptance and stale-status risk`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `skill-verification-before-completion` evidence requirements

**Specification Coverage:**
- Accepted-CV scorecard covers runtime, token/cost, repairs, manual actions,
  uncertainty reuse, and truthful acceptance rate; P1-C/P2 remain deferred.

**Required Skills:**
- `skill-verification-before-completion`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `docs/pipeline.md`, `docs/api.md`, `docs/observability.md`, `docs/superpowers/evidence/*`, this plan
- Verify: all task-local files and generated/manifest outputs

**Dependencies:**
- Tasks 1–5 complete or carry explicit, evidence-backed blockers.

**Authority:**
- Preauthorized local actions: `run fresh final suites, write scorecard/evidence/plan status, reconcile docs, and create the final local checkpoint commit`
- Stop for: `claiming P0/P1 complete with unresolved required correctness, suppressing blockers, pushing or merging without user approval, or unrelated cleanup`

**Steps:**
- [x] Step 1: Record accepted-CV metrics: median/p95 latency, retrieval/generation/validation time, tokens, provider calls, repair count, manual actions, resolution reuse, and accepted truthful CV rate.
- [x] Step 2: Run focused suites, full suite, manifest/hash checks, and `git diff --check` from a clean tracked baseline.
- [x] Step 3: Update evidence and plan ledger with exact commands, results, blockers, rollback path, and deferred scope.
- [x] Step 4: Mark plan `completed` only if completion criteria are met; otherwise keep `blocked` with one concrete next action.

**Verification:**
- [x] `uv run pytest -q` — `2865 passed, 4 skipped, 52 warnings`
- [x] `git diff --check` — clean
- [x] `git status --short --branch` — tracked changes limited to declared files; preserve unrelated `.tmp/`
- Expected: fresh proof is green or failures are recorded with owner, blocker, and next action; no stale completion claim remains.

**Exit Criteria:**
- P0-C/P1-A/P1-B correctness is proven; P0-A/P0-B decisions are measured or explicitly blocked; P1-C/P2 are documented as deferred.

## Verification

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py`
- `uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_cv_generation_reason_mapping.py`
- `uv run pytest -q tests/test_cv_generator.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- `uv run pytest -q tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_p0_public_corpus.py`
- `uv run pytest -q`
- `git diff --check`
- Fresh scorecard and evidence report with all unavailable arms explicitly classified.

## Completion Criteria

The plan is ready for completion verification when:

1. candidate answers and canonical evidence share one tested, fail-closed
   requirement-support contract
2. uncertainty identity and action state survive the full review-to-refresh path
3. P1-A writer context and repair behavior have before/after evidence
4. every P0-B validation mismatch has a recorded classification
5. P0-A/P0-B have reproducible decisions or precise provider/data blockers
6. docs, tests, manifests, reports, and plan ledger match repository truth
7. P1-C/P2 deferrals are explicit and no production default changed without
   accepted evidence

The plan may be marked `completed` only after fresh verification confirms all
required correctness tasks and records any permitted P0-A/P0-B blockers. A
blocked benchmark is not a failed engineering closeout when its blocker is
explicit, reproducible, and production promotion remains disabled.
