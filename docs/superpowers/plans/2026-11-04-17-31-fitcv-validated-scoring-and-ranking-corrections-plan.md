---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
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
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/sqlite_store.py
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - frontend/src/features/pipeline-settings/sections-def.ts
  - tests/test_ai_score.py
  - tests/test_ranking_contract.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - frontend/src/test/pipeline-settings.test.tsx
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
mandatory professional-experience requirement in the supported requirement
universe that has no qualifying candidate evidence. CV-analysis reuse
invalidates when canonical ranking score/label data changes and rebuilds
authoritative labels from current job data instead of trusting stale stored
labels.

### Occurrence-safe ranking and persistence

Rows that reach ranking, reuse, result assembly, and SQLite export join by stable
occurrence identity (`run_job_id`, then an applicable run-scoped raw
fingerprint). URL is a legacy fallback only when no stable identity exists;
normalization and shortlist URL de-duplication remain unchanged in this scope.
Independent duplicate-URL scoring for the normal pipeline would require broader
normalization/vector-search and persistence changes and is explicitly deferred.

### Complete, reusable ranking inputs

The ranking request uses a bounded job-aware projection that includes seniority
bounds and deterministic compact skill/requirement coverage fields rather than
silently truncating by position. One immutable candidate evidence projection is
built per profile revision/run and reused across ranking and CV analysis while
job-specific annotations remain local. Direct call-count and request-shape tests
prove this; no unbounded runtime-quality claim is made without a real fixture.

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
- Do not change `build_raw_job_fingerprint` or CV-analysis lookup identity to
  make CV analysis globally URL-independent. Only the semantic AI-score
  fingerprint excludes URL; CV-analysis reuse remains keyed by its existing raw
  identity and is invalidated by authoritative baseline score/label changes.
- Do not claim or implement independent normal-pipeline scoring for duplicate
  URLs. The existing normalization and vector-search URL de-duplication are
  preserved; this plan only prevents later stable-identity joins from collapsing
  rows that already exist.

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
- [x] Add or reuse one type-safe finite-score predicate so booleans are invalid,
  numeric zero is valid, and parser/runtime/ranking behavior agrees.
- [x] Preserve the existing holistic-only policy and update settings copy/control
  state so users cannot infer that structured weights affect the active score.
- [x] Add regression assertions for boolean rejection, zero acceptance, policy
  invariance, and the UI contract.

**Verification:**
- [x] `python -m pytest -q tests/test_ai_score.py tests/test_ranking_contract.py -k "score or ranking"`
- Expected: boolean scores fail with the existing invalid-score contract; numeric
  zero remains valid; baseline policy tests pass.
- [x] `npm --prefix frontend test -- src/test/pipeline-settings.test.tsx`
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
  numeric `years_experience_min`/`years_experience_max` bounds and requirements
  with no candidate evidence or unsupported profile coverage.
- Preserve valid human policy actions: `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`,
  and `OVERRIDE_BLOCK` must continue to affect the final disposition according
  to their existing policy, while genuinely unsupported mandatory requirements
  remain blocking.
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
- [x] Thread `explicit_project_acceptance` through project-backed experience
  classification and the final Full/Strict gate without weakening unrelated
  professional-evidence rules.
- [x] Enumerate all mandatory experience-shaped requirements, including numeric
  experience bounds, and emit a professional gap when no qualifying candidate
  evidence exists.
- [x] Preserve valid human resolution and policy-action outcomes while blocking
  only genuinely unsupported mandatory requirements.
- [x] Add direct tests for accepted project evidence, unsupported mandatory
  requirements, and unchanged Loose/Full/Strict baseline score behavior.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py -k "experience or project or unsupported or strict or loose"`
- Expected: explicit accepted projects can reach the intended Full/Strict path;
  unsupported mandatory professional requirements block Full/Strict; existing
  Loose routing and evidence-policy tests pass.
- [x] Direct boundary fixture assertions for project-only and unsupported-skill
  candidates verify final disposition, `unverified_requirement_ids`, and no
  false `ready_for_generation` result.
- Expected: final records contain the blocking requirement IDs and preserve the
  configured baseline score.
- [x] Add direct numeric experience-bound coverage and valid human-resolution
  assertions around `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, and `OVERRIDE_BLOCK`.

**Exit Criteria:**
- Full/Strict gating cannot be bypassed by accepted-project propagation gaps or
  by a mandatory professional requirement with no evidence candidate.

### Task 3: Make CV-analysis reuse authoritative and keep semantic scoring URL-independent

**Purpose:**
- Prevent stale fit labels/recommendations and keep the AI semantic score
  fingerprint independent of mutable URL text without changing CV-analysis raw
  identity.

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
- AI semantic score fingerprints exclude mutable occurrence URL while retaining
  occurrence identity separately.
- CV-analysis reuse continues to use the existing raw-job identity; only
  authoritative baseline score/label changes invalidate it in this scope.
- Reused records derive fit labels/recommendations from current job data, not
  stale stored `fit_classification`/`ranking_fit_label` values.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py` reuse fingerprint construction around the fit-label fields; `src/fitcv/agentic_cv_analysis.py:_build_analysis_input_components`, `src/fitcv/agentic_cv_analysis.py:_rebuild_reused_record`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`; `src/fitcv/ai_score.py:build_ai_score_input_fingerprint`
- Modify: the authoritative CV-analysis invalidation/rebuild path and the AI-score
  semantic fingerprint payload; retain `build_raw_job_fingerprint` and the
  existing CV-analysis lookup identity unchanged.
- Verify: `tests/test_agentic_cv_analysis.py`, `tests/test_ai_score.py`, `tests/test_evidence.py`

**Dependencies:**
- Task 1 establishes valid numeric score handling.
- Task 4 must later carry stable occurrence identity through ranking rows; this
  task must not use URL as a substitute for that identity.

**Authority:**
- Preauthorized local actions: modify only fingerprint/reuse code and focused tests; run deterministic reuse and fingerprint checks.
- Stop for: deleting historical reuse compatibility, changing unrelated CV-generation fingerprints, or introducing URL-based identity as a new contract.

**Steps:**
- [x] Include canonical `baseline_fit`/`baseline_fit_label` or their authoritative
  normalized equivalents in CV-analysis invalidation inputs.
- [x] Remove `job_url` only from semantic AI-score fingerprint payloads while
  keeping occurrence identity in result rows and joins.
- [x] Rebuild reused records with current job score/label resolution and add
  regressions for changed score and identical semantic score content. Do not add
  a CV-analysis URL-only reuse guarantee.

**Verification:**
- [x] `python -m pytest -q tests/test_agentic_cv_analysis.py tests/test_ai_score.py tests/test_evidence.py -k "reuse or fingerprint or label or score"`
- Expected: changed ranking score invalidates stale reuse and yields current
  label/recommendation; URL-only changes do not alter the semantic AI-score
  fingerprint; existing CV-analysis identity compatibility tests pass.

**Exit Criteria:**
- Reuse decisions are invalidated by authoritative ranking changes and never
  return stale ranking labels; semantic AI scoring is insensitive to URL-only
  payload changes without changing CV-analysis raw identity.

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
- Use the existing `job_identity_keys` helper as the single identity owner.
- Resolve keys in this order: `run_job_id`; applicable run-scoped raw
  fingerprint; URL only as a legacy fallback when no stable key exists. A stable
  key that is present but unmatched must not silently fall through to a URL alias.
- Return stable occurrence identity from AI score rows.
- Preserve distinct rows that already exist through ranking/result/export paths;
  do not change upstream normalization/vector-search URL de-duplication or
  introduce a broad schema migration.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stages/common.py:job_identity_keys`, `src/fitcv/ai_score.py:_ranking_result_to_row`, `src/fitcv/ai_score.py:run_ai_scoring`; ranking blocks in `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_runner.py`; URL-keyed result/export maps in `src/fitcv_cp/sqlite_store.py`; `src/fitcv/enrich.py` and `src/fitcv/ai_score.py` URL-keyed persistence boundaries
- Modify: the existing identity helper if needed to expose stable precedence; score-row identity propagation; ranking reconciliation; SQLite structured/export indexing only at validated joins. Do not change the URL-keyed schema or upstream de-duplication in this task.
- Verify: `tests/test_pipeline.py`, `tests/test_ai_score.py`, `tests/test_fitcv_cp/test_sqlite_store.py:test_query_and_export_preserve_duplicate_url_occurrences`

**Dependencies:**
- Task 3 keeps semantic fingerprints separate from occurrence identity.
- Existing `run_job_id` occurrence rows and duplicate-URL preservation test are
  authoritative persistence primitives; do not introduce a broad schema rewrite.

**Authority:**
- Preauthorized local actions: modify declared ranking/result/export joins and focused backend tests; run direct duplicate-occurrence pipeline and SQLite export checks.
- Stop for: new database migrations, destructive data rewrites, URL-only identity contracts, or changes outside declared ranking/persistence surfaces.

**Steps:**
- [x] Extend/use `job_identity_keys` as the one occurrence-key helper with
  explicit stable-key-first ordering and run-scoping; add tests proving a
  present-but-unmatched stable key does not fall through to a URL alias.
- [x] Carry the key through ranking input maps, fresh/reused score maps, score
  rows, final ranking rows, and structured/export hydration.
- [x] Add a regression for distinct stable identities sharing a URL; assert later
  score/result/export joins do not collapse them. Record upstream URL de-duplication
  as an explicit deferred boundary rather than asserting normal-pipeline duplicate
  scoring.

**Verification:**
- [x] `python -m pytest -q tests/test_ai_score.py tests/test_pipeline.py tests/test_fitcv_cp/test_sqlite_store.py -k "duplicate or occurrence or ranking or query_and_export"`
- Expected: rows with distinct stable identities retain their identities through
  ranking, query, and export; existing pagination/filter tests pass. No test may
  claim that upstream duplicate-URL occurrences are independently scored.
- [x] Direct inspection of score-row and export payloads confirms stable identity
  is present before any URL fallback is used.

**Exit Criteria:**
- No production ranking or result/export join collapses rows by URL when stable
  occurrence identity is available; upstream URL de-duplication remains outside
  this plan.

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
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`; `src/fitcv/evidence.py:build_evidence_projection` and `build_profile_evidence_pool`; `src/fitcv/pipeline.py` ranking orchestration; `src/fitcv/agentic_cv_analysis.py:_experience_evidence_facts` and `analyze_ranked_job`
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
- [x] Add a deterministic unit fixture around the actual projection construction
  path that records projection-call count and ranking-input shape. Do not use the
  broad `tests/test_benchmark_cv_efficiency.py -k "projection or ranking or evidence"`
  selector as proof unless it matches the targeted tests.
- [x] Add seniority bounds and deterministic compact coverage fields while
  retaining bounded lists and stable serialization.
- [x] Construct one immutable projection per profile revision/run, pass it to
  ranking and CV analysis, and instrument/assert that repeated per-job builds
  are removed.
- [x] If a real fixture/gold corpus and predeclared threshold exist, run the
  benchmark and record them; otherwise record that runtime/quality benchmarking
  is deferred and rely on deterministic call-count/shape tests.

**Verification:**
- [x] `python -m pytest -q tests/test_ai_score.py tests/test_evidence.py tests/test_pipeline.py -k "ranking_input or projection or evidence"`
- Expected: inputs include both experience bounds and deterministic coverage
  fields; existing size bounds and evidence semantics remain valid.
- [x] Run the targeted projection-call-count and ranking-input-shape tests by
  node/keyword; do not rely on unrelated benchmark names.
- Expected: one projection per profile revision/run is observed and inputs
  contain the required fields. Runtime/quality claims require a real fixture and
  predeclared threshold; otherwise explicitly record the benchmark deferral.

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
- Stage docs are not targets in this repository snapshot; preserve stage/artifact
  behavior and run `python tools/docs/generate_architecture_metadata.py --check`
  when architecture metadata is affected.

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
- [x] Extract or select one shared ranking execution owner and route both current
  entry paths through it without duplicating request/reuse/reconciliation logic.
- [x] Preserve state keys, event names, cancellation checks, score counts, and
  final ranking artifacts; add parity tests for inline and stage-runner paths.
- [x] Preserve current stage/artifact behavior and run
  `python tools/docs/generate_architecture_metadata.py --check` if the final
  architecture metadata is affected; do not invent absent `docs/stages` files.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_fitcv_cp/test_sqlite_store.py -k "ranking or stage or reuse or duplicate"`
- Expected: both ranking entry paths produce equivalent score identity,
  reuse/fresh counts, ranking rows, and preserved stage artifacts.
- [x] Run `python tools/docs/generate_architecture_metadata.py --check` when
  applicable; otherwise record that no stage-doc update was required because
  those files are absent in this repository snapshot.

**Exit Criteria:**
- Inline and stage-runner ranking share one implementation owner, pass parity
  tests, and preserve documented stage/artifact truth.

## Verification

## Post-Review Corrections

The final review validated the following additional corrections, now included
in the implementation and regression coverage:

- `replace_filter_results()` accepts an unambiguous legacy URL-only row, while
  ambiguous URL-only rows still fail safely.
- Numeric professional-experience descriptors use candidate years, qualifying
  professional evidence, and human-resolution answers; numeric bounds do not
  require a canonical skill.
- Ranking reconciliation joins shortlist, AI, and result rows by stable
  occurrence identity first, with a guarded unique-URL fallback only for
  legacy rows.
- Run-scoped structured persistence stores stable rows under `run:<run_job_id>`
  or `fp:<raw_job_fingerprint>` while retaining the real `job_url` in payloads;
  legacy rows retain URL keys. This preserves duplicate URL occurrences without
  a broad database schema migration.
- Stable-identity misses do not inherit unrelated stable or ambiguous legacy
  URL payloads.
- Ranking skill coverage is computed from complete requirement and candidate
  skill lists before prompt fields are bounded to eight entries.
- One candidate evidence projection is built after profile loading and reused
  by ranking and all CV-analysis calls in the same run.

- [x] Focused post-review regressions pass for ranking identity, score input
  coverage, numeric experience gates/resolutions, filter persistence, and
  duplicate structured occurrences.
- [x] Final filtered backend verification passes: `213 passed, 1 skipped,
  335 deselected`.
- [x] Frontend settings verification passes: `28 passed`.
- [x] `git diff --check` passes.

Run fresh final verification from the preserved current workspace:

- `python -m pytest -q tests/test_ai_score.py tests/test_ranking_contract.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_fitcv_cp/test_sqlite_store.py -k "score or ranking or experience or project or unsupported or reuse or fingerprint or duplicate_url or occurrence or query_and_export or stage" --disable-warnings --maxfail=1`
- `npm --prefix frontend test -- src/test/pipeline-settings.test.tsx`
- `git diff --check`
- Inspect `git diff --stat` and `git status --short`; confirm only declared
  files changed and all pre-existing untracked artifacts remain untouched.
- Apply `skill-verification-before-completion` before changing this plan’s
  status from `proposed`.

**Fresh Evidence:**

- Backend focused verification: `213 passed, 1 skipped, 335 deselected`.
- Frontend settings verification: `28 passed`.
- Architecture metadata: synchronized, then `Architecture docs are up to date.`
- `git diff --check`: passed with the repository’s configured `cr-at-eol`
  whitespace policy; pre-existing untracked artifacts remain untouched.

## Completion Criteria

The plan is ready for completion verification when:

1. the active baseline remains holistic-only and boolean score inputs are
   rejected without breaking numeric zero
2. explicit project acceptance and unsupported mandatory professional
   requirements produce the intended Full/Strict dispositions
3. CV-analysis reuse invalidates on canonical ranking changes and semantic AI
   score fingerprints ignore URL-only changes without changing raw CV identity
4. rows with stable occurrence identity retain distinct score and export joins;
   upstream normal-pipeline URL de-duplication remains explicitly deferred
5. ranking inputs include experience bounds and compact coverage fields while
   candidate evidence projection is built once per run/profile revision
6. inline and stage-runner ranking share one owner with preserved stage and
   artifact truth
7. all task-local and final verification commands pass, or any blocker/deviation
   is recorded explicitly without claiming completion
8. no deferred, unvalidated audit recommendation is implemented as part of this
   plan

