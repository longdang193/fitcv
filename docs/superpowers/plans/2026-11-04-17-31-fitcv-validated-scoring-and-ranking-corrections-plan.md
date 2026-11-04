---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: proposed
layer: change
distribution_tier: starter_kit
name: fitcv-validated-scoring-and-ranking-corrections
targets:
  - config/policy/ranking.yaml
  - src/fitcv/ai_score.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/sqlite_store.py
  - frontend/src/features/pipeline-settings/sections-def.ts
  - tests/test_ai_score.py
  - tests/test_ranking_contract.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - frontend/src/test/pipeline-settings.test.tsx
  - docs/stages/*.source.yaml
  - docs/stages/*.yaml
---

# FitCV Validated Scoring And Ranking Corrections

## Goal

Implement only the scoring, evidence-gating, reuse, occurrence-identity, and
ranking-path corrections validated against the current `main` branch and direct
reproductions. Preserve the configured numeric baseline and the invariant that
Loose, Full, and Strict change evidence/disposition behavior rather than the
baseline score itself.

## Implementation Outcomes

### Canonical baseline contract

The ranking policy and settings UI agree that the active baseline is
`holistic_ai_only` with `holistic_ai_fit: 1.0` and `structured_fit: 0.0`.
Structured-factor controls no longer imply that they change the active baseline.
Score parsing rejects booleans while accepting valid numeric zero, using one
consistent finite-score rule.

### Correct evidence and reuse decisions

Full and Strict analysis honors explicit project acceptance and blocks every
mandatory professional-experience requirement that has no supported candidate
evidence. CV-analysis reuse invalidates when canonical ranking score/label data
changes and rebuilds authoritative labels from current job data instead of
trusting stale stored labels.

### Occurrence-safe ranking and persistence

Ranking, reuse, result assembly, and SQLite export join by stable occurrence
identity (`run_job_id` or the existing raw identity/fingerprint), not URL alone.
Duplicate URL occurrences retain distinct score rows and exports, with a narrow
legacy URL fallback only when no stable identity is available.

### Complete, reusable ranking inputs

The ranking request uses a bounded job-aware projection that includes seniority
bounds and deterministic compact skill/requirement coverage fields rather than
silently truncating by position. One immutable candidate evidence projection is
built per profile revision/run and reused across ranking and CV analysis while
job-specific annotations remain local.

### One ranking execution owner

Inline and stage-runner ranking flows share one request-preparation, reuse,
scoring, reconciliation, and ranking implementation. Stage/artifact truth and
existing reporting behavior remain intact, with focused regression coverage for
both entry paths.

## Scope Boundaries

- Keep the current ranking arithmetic, fit thresholds, and Loose/Full/Strict
  baseline-score invariants.
- Do not activate mixed AI/structured baseline weights; that requires offline
  label-migration evidence and product approval not present in the audits.
- Do not implement adaptive AI pool sizing or reranking reduction without
  benchmark/recall evidence.
- Do not redesign provider admission, retry classification, RQ compatibility,
  artifact retention, or broad SQLite/index architecture; those findings were
  not sufficiently validated for this plan.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared source, configuration, documentation, and test files; run declared local checks; inspect current repository and configured local runtime evidence
- User-approval actions: commit, push, merge, publication, external writes, destructive recovery, discard, cleanup, and changes outside declared ownership
- Parallel ownership: `none; ranking and persistence surfaces share occurrence and contract invariants`
- Sequential fallback: `Task 1`, then `Task 2`, then `Task 3`, then `Task 4`, then `Task 5`, then `Task 6`, then final verification

## Task Breakdown

### Task 1: Align baseline contract, score validation, and settings semantics

**Purpose:**
- Remove the validated mismatch between the canonical holistic-only policy,
  score parser behavior, and the editable structured-factor UI.

**Task Function:**
- Baseline contract correction across parser, policy enforcement, and settings
  presentation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded, source-defined contract change with low ambiguity;
  correctness is established by existing policy and parser tests.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused unit and frontend tests are sufficient for this
  bounded task.

**Specification Coverage:**
- Preserve `config/policy/ranking.yaml` active mode and weights.
- Reject boolean `ai_score` values without rejecting numeric `0`.
- Make structured-factor settings diagnostic/read-only or otherwise explicit
  that they do not affect the active holistic-only baseline.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `config/policy/ranking.yaml`, `src/fitcv/ranking_contract.py:is_finite_score`, `src/fitcv/ai_score.py:parse_score_response`, `src/fitcv/ai_score.py:build_ranking_request`
- Modify: `src/fitcv/ai_score.py:parse_score_response` and the smallest shared numeric-score validation surface; `frontend/src/features/pipeline-settings/sections-def.ts` structured-factor definitions
- Verify: `tests/test_ai_score.py`, `tests/test_ranking_contract.py`, `frontend/src/test/pipeline-settings.test.tsx`

**Dependencies:**
- Current policy and enforcement in `config/policy/ranking.yaml` and
  `src/fitcv/ranking_contract.py` remain authoritative.

**Authority:**
- Preauthorized local actions: modify only the declared parser, contract/UI, and focused test surfaces; run focused Python and frontend tests.
- Stop for: any proposal to change active baseline weights, fit thresholds, public settings schema, or files outside declared ownership.

**Steps:**
- [ ] Add or reuse one type-safe finite-score predicate so booleans are invalid,
  numeric zero is valid, and parser/runtime/ranking behavior agrees.
- [ ] Preserve the existing holistic-only policy and update settings copy/control
  state so users cannot infer that structured weights affect the active score.
- [ ] Add regression assertions for boolean rejection, zero acceptance, policy
  invariance, and the UI contract.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_ranking_contract.py -k "score or ranking"`
- Expected: boolean scores fail with the existing invalid-score contract; numeric
  zero remains valid; baseline policy tests pass.
- [ ] `npm --prefix frontend test -- src/test/pipeline-settings.test.tsx`
- Expected: settings tests prove holistic-only semantics and no misleading
  editable structured baseline controls.

**Exit Criteria:**
- Parser, ranking contract, policy, and settings UI expose one consistent
  holistic-only baseline contract with focused regression proof.

### Task 2: Correct project acceptance and unsupported mandatory requirements

**Purpose:**
- Make final Full/Strict disposition honor explicit project acceptance and
  prevent unsupported mandatory professional requirements from passing.

**Task Function:**
- Evidence-gate boundary correction with direct disposition proof.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: material backend behavior with direct reproducible failure
  paths and clear existing evidence-policy owners.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: task-local backend boundary tests cover success and blocking
  paths, including the existing lower-level policy tests.

**Specification Coverage:**
- Explicit project acceptance must be honored consistently from evidence
  qualification through `analyze_ranked_job` final gating.
- Every mandatory experience-shaped requirement must be evaluated, including
  requirements with no candidate evidence or unsupported profile coverage.
- Loose routing behavior and baseline numeric score remain unchanged.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:build_evidence_projection` and strict evidence qualification; `src/fitcv/agentic_cv_analysis.py:_experience_evidence_facts`, `src/fitcv/agentic_cv_analysis.py:build_experience_evidence_summary`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`
- Modify: `src/fitcv/agentic_cv_analysis.py:build_experience_evidence_summary` and final Full/Strict gate integration; adjust `src/fitcv/evidence.py` only if the shared policy boundary requires it
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:**
- Task 1 score contract must remain unchanged while disposition logic is fixed.
- Existing explicit-project lower-level test at
  `tests/test_evidence.py:test_strict_experience_policy_allows_explicit_project_acceptance`
  is the policy baseline.

**Authority:**
- Preauthorized local actions: modify evidence-summary/gate logic and focused backend tests; run direct Full/Strict/Loose boundary tests and the focused pytest subset.
- Stop for: changes to baseline score arithmetic, unrelated evidence categories, schema migrations, or external dependency behavior.

**Steps:**
- [ ] Thread `explicit_project_acceptance` through project-backed experience
  classification and the final Full/Strict gate without weakening unrelated
  professional-evidence rules.
- [ ] Enumerate all mandatory experience-shaped requirements and emit a
  professional gap when no qualifying candidate evidence exists.
- [ ] Add direct tests for accepted project evidence, unsupported mandatory
  requirements, and unchanged Loose/Full/Strict baseline score behavior.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py -k "experience or project or unsupported or strict or loose"`
- Expected: explicit accepted projects can reach the intended Full/Strict path;
  unsupported mandatory professional requirements block Full/Strict; existing
  Loose routing and evidence-policy tests pass.
- [ ] Direct boundary fixture assertions for project-only and unsupported-skill
  candidates verify final disposition, `unverified_requirement_ids`, and no
  false `ready_for_generation` result.
- Expected: final records contain the blocking requirement IDs and preserve the
  configured baseline score.

**Exit Criteria:**
- Full/Strict gating cannot be bypassed by accepted-project propagation gaps or
  by a mandatory professional requirement with no evidence candidate.

### Task 3: Make CV-analysis reuse authoritative and URL-independent

**Purpose:**
- Prevent stale fit labels/recommendations and unnecessary invalidation when a
  semantically identical job changes only its occurrence URL.

**Task Function:**
- Reuse-fingerprint and record-rebuild correction.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded state/fingerprint correction with existing focused
  reuse tests and direct stale-reuse reproduction.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: deterministic fingerprint and reuse regression tests provide
  direct proof.

**Specification Coverage:**
- Fingerprints include canonical baseline score/label inputs that affect
  authoritative ranking decisions.
- Semantic score fingerprints exclude mutable occurrence URL while retaining
  occurrence identity separately.
- Reused records derive fit labels/recommendations from current job data, not
  stale stored `fit_classification`/`ranking_fit_label` values.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py` reuse fingerprint construction around the fit-label fields; `src/fitcv/agentic_cv_analysis.py:_build_analysis_input_components`, `src/fitcv/agentic_cv_analysis.py:_rebuild_reused_record`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`; `src/fitcv/ai_score.py:build_ai_score_input_fingerprint`
- Modify: the canonical CV-analysis and AI-score fingerprint payloads and reuse rebuild path; retain raw identity outside semantic score payloads
- Verify: `tests/test_agentic_cv_analysis.py`, `tests/test_ai_score.py`, `tests/test_evidence.py`

**Dependencies:**
- Task 1 establishes valid numeric score handling.
- Task 4 must later carry stable occurrence identity through ranking rows; this
  task must not use URL as a substitute for that identity.

**Authority:**
- Preauthorized local actions: modify only fingerprint/reuse code and focused tests; run deterministic reuse and fingerprint checks.
- Stop for: deleting historical reuse compatibility, changing unrelated CV-generation fingerprints, or introducing URL-based identity as a new contract.

**Steps:**
- [ ] Include canonical `baseline_fit`/`baseline_fit_label` or their authoritative
  normalized equivalents in CV-analysis invalidation inputs.
- [ ] Remove `job_url` from semantic AI-score fingerprint payloads while keeping
  occurrence identity in result rows and joins.
- [ ] Rebuild reused records with current job score/label resolution and add
  regressions for changed score, changed URL, and identical semantic content.

**Verification:**
- [ ] `python -m pytest -q tests/test_agentic_cv_analysis.py tests/test_ai_score.py tests/test_evidence.py -k "reuse or fingerprint or label or score"`
- Expected: changed ranking score invalidates stale reuse and yields current
  label/recommendation; URL-only changes do not alter the semantic score
  fingerprint; existing reuse compatibility tests pass.

**Exit Criteria:**
- Reuse decisions are invalidated by authoritative ranking changes, insensitive
  to mutable URL-only changes, and never return stale ranking labels.

### Task 4: Propagate occurrence identity through ranking and SQLite results

**Purpose:**
- Eliminate URL-keyed score collapse for duplicate job occurrences across fresh
  scoring, reuse, result assembly, structured results, and export.

**Task Function:**
- Occurrence-identity contract propagation and persistence regression.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-module backend contract work with a direct duplicate-URL
  failure reproduction and existing occurrence rows.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: end-to-end pipeline/result/export tests cover the affected
  joins and final persisted state.

**Specification Coverage:**
- Use `run_job_id` or existing raw fingerprint as the primary occurrence key.
- Return stable occurrence identity from AI score rows.
- Use URL only as narrow legacy fallback when no stable identity exists.
- Preserve duplicate occurrences and distinct scores in result and export paths.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:_ranking_result_to_row`, `src/fitcv/ai_score.py:run_ai_scoring`; ranking blocks in `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_runner.py`; URL-keyed result/export maps in `src/fitcv_cp/sqlite_store.py`
- Modify: score-row identity propagation; `src/fitcv/pipeline.py` ranking reconciliation; `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`; SQLite structured/export indexing at the validated URL-keyed sites
- Verify: `tests/test_pipeline.py`, `tests/test_ai_score.py`, `tests/test_fitcv_cp/test_sqlite_store.py:test_query_and_export_preserve_duplicate_url_occurrences`

**Dependencies:**
- Task 3 keeps semantic fingerprints separate from occurrence identity.
- Existing `run_job_id` occurrence rows and duplicate-URL preservation test are
  authoritative persistence primitives; do not introduce a broad schema rewrite.

**Authority:**
- Preauthorized local actions: modify declared ranking/result/export joins and focused backend tests; run direct duplicate-occurrence pipeline and SQLite export checks.
- Stop for: new database migrations, destructive data rewrites, URL-only identity contracts, or changes outside declared ranking/persistence surfaces.

**Steps:**
- [ ] Define one occurrence-key helper with stable-key-first ordering and a
  documented legacy URL fallback.
- [ ] Carry the key through ranking input maps, fresh/reused score maps, score
  rows, final ranking rows, and structured/export hydration.
- [ ] Add a regression with two same-URL occurrences and different scores or
  ranking inputs; assert both scores, rows, and exported records remain distinct.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_pipeline.py tests/test_fitcv_cp/test_sqlite_store.py -k "duplicate or occurrence or ranking or query_and_export"`
- Expected: duplicate URLs retain independent scores and `run_job_id` values
  through final ranking, query, and export; existing pagination/filter tests pass.
- [ ] Direct inspection of score-row and export payloads confirms stable identity
  is present before any URL fallback is used.

**Exit Criteria:**
- No production ranking or result/export join collapses distinct occurrences by
  URL when stable occurrence identity is available.

### Task 5: Complete ranking input projection and reuse one evidence pool

**Purpose:**
- Make ranking requests job-aware and avoid rebuilding the same candidate
  evidence projection once per job.

**Task Function:**
- Bounded ranking-input and evidence-projection optimization with quality guard.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: deterministic projection change plus measured call-count and
  request-shape proof; no speculative model or pool-size redesign.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused input-shape tests and instrumentation provide the
  required correctness/performance evidence.

**Specification Coverage:**
- Preserve bounded prompt size while including `years_experience_min` and
  `years_experience_max` and compact deterministic matched/missing skill or ratio
  fields.
- Build one immutable candidate evidence projection per profile revision/run and
  pass it to ranking and CV analysis.
- Keep job-specific selection and annotations local to each job.

**Required Skills:**
- `skill-performance-optimization`
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`; `src/fitcv/evidence.py:build_evidence_projection`; `src/fitcv/pipeline.py:build_profile_evidence_pool` and ranking orchestration; `src/fitcv/agentic_cv_analysis.py:_experience_evidence_facts` and `analyze_ranked_job`
- Modify: bounded job-aware ranking projection; run-level immutable projection plumbing in `src/fitcv/pipeline.py` and `src/fitcv/agentic_cv_analysis.py`; only local job annotations may remain mutable
- Verify: `tests/test_ai_score.py`, `tests/test_evidence.py`, `tests/test_pipeline.py`, and the relevant benchmark tests under `tests/test_benchmark_cv_efficiency.py`

**Dependencies:**
- Task 4 supplies stable occurrence identity for per-job annotations.
- Candidate evidence policy and current bounded prompt-size limits remain
  authoritative.

**Authority:**
- Preauthorized local actions: modify declared ranking/evidence projection code and focused benchmark/unit tests; run before/after local measurements on the declared representative workload.
- Stop for: adaptive pool-size/reranking changes, unbounded prompt growth, evidence-policy changes, or a measured regression beyond the agreed local threshold.

**Steps:**
- [ ] Capture a baseline on the current benchmark fixture for projection-call
  count, ranking-input shape, and relevant runtime output.
- [ ] Add seniority bounds and deterministic compact coverage fields while
  retaining bounded lists and stable serialization.
- [ ] Construct one immutable projection per profile revision/run, pass it to
  ranking and CV analysis, and instrument/assert that repeated per-job builds
  are removed.
- [ ] Re-run the representative benchmark and record call-count/runtime and
  request-shape evidence in the implementation handoff.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_evidence.py tests/test_pipeline.py -k "ranking_input or projection or evidence"`
- Expected: inputs include both experience bounds and deterministic coverage
  fields; existing size bounds and evidence semantics remain valid.
- [ ] `python -m pytest -q tests/test_benchmark_cv_efficiency.py -k "projection or ranking or evidence"`
- Expected: one projection per profile revision/run is observed; runtime is no
  worse than the captured baseline within normal test noise, and no quality
  regression is introduced. The lead controller owns the local threshold and
  records the measured values.

**Exit Criteria:**
- Ranking sees the required job-aware fields and the candidate evidence
  projection is built once per run/profile revision with fresh proof.

### Task 6: Converge duplicate ranking execution paths and reconcile stage artifacts

**Purpose:**
- Remove the validated production duplication between the inline pipeline and
  parallel stage runner without changing stage/artifact truth.

**Task Function:**
- Ranking orchestration convergence and stage-contract reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final integration task after occurrence, reuse, and input
  contracts are stable; requires careful state/reporting preservation.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: both entry paths and stage artifact tests provide direct proof.

**Specification Coverage:**
- One owner prepares ranking requests, resolves reuse, runs fresh scoring,
  reconciles rows, and produces ranking inputs.
- `run_pipeline` and `execute_ranking_stage` preserve current state keys,
  reporter events, cancellation behavior, and artifact schemas.
- Update `docs/stages/*.source.yaml` and regenerated stage docs only if the
  converged implementation changes documented stage/artifact behavior.

**Required Skills:**
- `skill-backend-verification`
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline.py` inline ranking block around the AI-scoring and
  ranking stages; `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`;
  relevant stage source/generated docs
- Modify: the two ranking entry paths and the smallest shared owner/helper in an
  existing owning module; update stage source and generated docs only when
  required by actual contract changes
- Verify: `tests/test_pipeline.py`, ranking/stage artifact tests, and relevant
  docs-generation or stage validation commands already used by the repository

**Dependencies:**
- Tasks 1–5 complete; shared score, evidence, fingerprint, occurrence, and
  projection contracts are authoritative.
- No parallel edits are allowed because both ranking paths share state and
  artifact semantics.

**Authority:**
- Preauthorized local actions: modify only the declared ranking orchestration, stage documentation when contract changes require it, and focused tests; run local pipeline/stage verification.
- Stop for: stage/artifact schema changes not justified by the implementation, new parallel ownership, unrelated refactors, or any external/runtime write.

**Steps:**
- [ ] Extract or select one shared ranking execution owner and route both current
  entry paths through it without duplicating request/reuse/reconciliation logic.
- [ ] Preserve state keys, event names, cancellation checks, score counts, and
  final ranking artifacts; add parity tests for inline and stage-runner paths.
- [ ] Reconcile stage source/generated docs if and only if the final contract
  changed, then run the repository’s stage validation/generation check.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_fitcv_cp/test_sqlite_store.py -k "ranking or stage or reuse or duplicate"`
- Expected: both ranking entry paths produce equivalent score identity,
  reuse/fresh counts, ranking rows, and preserved stage artifacts.
- [ ] Run the repository’s existing stage documentation validation/generation
  command if Task 6 changes `docs/stages`; otherwise record that no stage-doc
  update was required.

**Exit Criteria:**
- Inline and stage-runner ranking share one implementation owner, pass parity
  tests, and preserve documented stage/artifact truth.

## Verification

Run fresh final verification from the preserved current workspace:

- `python -m pytest -q tests/test_ai_score.py tests/test_ranking_contract.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_fitcv_cp/test_sqlite_store.py -k "score or ranking or experience or project or unsupported or reuse or fingerprint or duplicate_url or occurrence or query_and_export or stage" --disable-warnings --maxfail=1`
- `npm --prefix frontend test -- src/test/pipeline-settings.test.tsx`
- `git diff --check`
- Inspect `git diff --stat` and `git status --short`; confirm only declared
  files changed and all pre-existing untracked artifacts remain untouched.
- Apply `skill-verification-before-completion` before changing this plan’s
  status from `proposed`.

## Completion Criteria

The plan is ready for completion verification when:

1. the active baseline remains holistic-only and boolean score inputs are
   rejected without breaking numeric zero
2. explicit project acceptance and unsupported mandatory professional
   requirements produce the intended Full/Strict dispositions
3. CV-analysis reuse invalidates on canonical ranking changes and semantic score
   fingerprints ignore URL-only changes
4. duplicate URL occurrences retain independent score and export rows keyed by
   stable occurrence identity
5. ranking inputs include experience bounds and compact coverage fields while
   candidate evidence projection is built once per run/profile revision
6. inline and stage-runner ranking share one owner with preserved stage and
   artifact truth
7. all task-local and final verification commands pass, or any blocker/deviation
   is recorded explicitly without claiming completion
8. no deferred, unvalidated audit recommendation is implemented as part of this
   plan

