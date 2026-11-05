---
layer: change
artifact_type: plan
contract_version: "1"
status: proposed
template_id: implementation-plan
name: fitcv-top50-admission-and-evidence-integrity
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/embeddings.py
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/ranking.py
  - src/fitcv/preference_policy.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - config/runtime/pipeline.yaml
  - config/policy/ranking.yaml
  - scripts/diagnose_ranking_loss.py
  - scripts/benchmark_ranking.py
  - tests/test_vector_search.py
  - tests/test_embeddings.py
  - tests/test_candidate.py
  - tests/test_evidence.py
  - tests/test_ai_score.py
  - tests/test_ranking.py
  - tests/test_preference_policy.py
  - tests/test_pipeline.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_ranking_evaluation.py
  - tests/fixtures/ranking_gold.json
  - tests/fixtures/retrieval_admission_fixture.json
---

# FitCV Top-50 Admission And Evidence Integrity Plan

## Goal

Keep the existing top-50 scoring cohort and 12,000-character scorer request
limit, while changing how eligible jobs compete for those 50 places and how
the request budget is allocated. Relevant jobs must not be excluded only
because their embedding is missing, their role family is not the primary target
role, or their evidence occurs later in the candidate profile. Jobs admitted to
scoring must retain truthful mandatory facts and the strongest source-linked
project evidence, or receive an explicit unscored result when the compact
mandatory core cannot fit.

This plan consolidates only source-confirmed findings from the reviews of
`longdang193/fitcv` at commit `05707b1ac5c33717035287ecf303d1dc3ab19f1f` and
the attached verdict based on merged commit `3607e46fb2d6c5ba1f84019012d08b4e45e49352`.
The exact historical RWE production rank remains unverified because the
original job pool, backend state, and cutoff artifacts are unavailable.

## Preserved Constraints And Non-Goals

- Keep `vector_search_top_n` at `50` and `ai_score_top_n` at `50`.
- Keep the scorer request limit at `12,000` characters.
- Keep the existing compatibility formula and `holistic_ai_only` policy.
- Do not disable eligibility or rule filters to improve recall.
- Do not treat user interest feedback as qualification evidence.
- Do not mix incomparable cosine and lexical scores directly.
- Do not promote optional job technologies to mandatory requirements.
- Preserve unrelated working-tree changes, including
  `config/job_sources/linkedin.json` and existing untracked workspace artifacts.

## Validated Findings

- Lexical fallback can fill only unused shortlist slots, so a relevant
  missing-embedding job cannot displace a weak vector hit when the vector cohort
  already contains 50 rows.
- Production shortlist execution can request vector retrieval even when
  configuration selects lexical retrieval; tested helper behavior does not
  prove the inline production path.
- A mixed vector/lexical shortlist can fail personalized ranking because
  preference resolution examines only the first row, while lexical rows lack a
  compatible embedding. The same mixed rows can fail checkpoint strategy
  validation.
- Embedding lookup selects the newest row before filtering by the effective
  embedding contract, allowing an incompatible newer row to hide an older
  compatible row.
- Candidate query construction is position-capped and can omit later role
  families and project evidence. Lexical retrieval computes role-family fit but
  does not include it in the shortlist score.
- Canonical candidate claims can default to supported without attributable
  evidence references. Legacy parent skills can also be attached to unrelated
  child evidence.
- Technology and multi-token evidence matching can accept partial or unordered
  matches that overstate support.
- More than eight mandatory skills can be rejected before the complete compact
  request is actually budgeted.
- Request budgeting can remove all selected evidence and still submit a request
  whose diagnostics report a complete mandatory core.
- Language levels, education, and certifications can be lost or removed under
  pressure even when they are job-specific mandatory facts.
- Effective embedding metadata is reconstructed from configuration instead of
  carried from the actual generator through cache, retrieval, diagnostics, and
  resume.
- Production admission manifests and scorer visibility diagnostics do not fully
  reconcile raw, selected, rendered, and omitted items, and aggregate persisted
  diagnostics are not bounded.
- The recorded benchmark fixture is invalid, so required performance and
  ranking-equivalence evidence is not available.
- Existing cross-stage acceptance starts after shortlist admission and does not
  prove the raw-to-rule-filter boundary for relevant jobs.

## Implementation Outcomes

### 1. Fixed-budget hybrid admission

Eligible jobs are retrieved through valid semantic and bounded lexical channels,
merged by rank position with deterministic deduplication, and admitted through
one top-50 cutoff. Explicit lexical configuration is honored in production,
mixed fallback is legal and resumable, and run-wide personalization becomes
baseline-only whenever an admitted row lacks a compatible embedding.

### 2. Role-complete, provenance-aware candidate representation

All declared role families and high-value project evidence can compete for
bounded query slots without depending on profile order. Demonstrated candidate
claims require attributable evidence under the canonical v2 policy, while
legacy inputs remain distinguishable rather than silently becoming supported.

### 3. Truthful 12,000-character scorer requests

The scorer first fits job-specific mandatory facts, then preserves attributable
selected evidence and its provenance, then spends remaining space on optional
context. Evidence support is calculated per requirement against the final
rendered excerpts. Existing evidence is never silently reduced to zero; genuine
compact-core overflow returns explicit `input_budget_exceeded` without a
provider call.

### 4. End-to-end diagnostics and acceptance proof

Production and resumed runs persist bounded admission and visibility manifests
that reconcile available, selected, rendered, omitted, and scored states.
Valid retrieval, evidence-visibility, full-pipeline, false-positive, cache,
checkpoint, and same-arm benchmark tests prove the preserved budgets and the
new behavior.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit the declared plan targets, add the declared regression fixtures and tests, run read-only source inspection, run declared local tests and benchmarks, and update this plan's task ledger
- User-approval actions: push, merge, external publication, destructive cleanup, deleting unrelated artifacts, or changing the preserved budget constraints
- Parallel ownership: none; `vector_search.py`, `ai_score.py`, and production pipeline orchestration require sequential integration
- Sequential fallback: execute Tasks 1–7 in dependency order in the current workspace

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-scoring-input-integrity`
- Base commit: `05707b1ac5c33717035287ecf303d1dc3ab19f1f`
- Expected workspace: preserve the existing modification to `config/job_sources/linkedin.json` and all unrelated untracked artifacts; do not reset or clean them
- Next action: complete Task 1 baseline inspection and add the bounded admission fixture
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current | `unresolved` | none | baseline diagnostic and fixture tests | pending |
| Task 2 | `pending` | current | `unresolved` | Task 1 | hybrid admission and strategy tests | pending |
| Task 3 | `pending` | current | `unresolved` | Task 1 | embedding contract and metadata tests | pending |
| Task 4 | `pending` | current | `unresolved` | Task 1 | role-query and provenance tests | pending |
| Task 5 | `pending` | current | `unresolved` | Tasks 1 and 4 | scorer budget and evidence-visibility tests | pending |
| Task 6 | `pending` | current | `unresolved` | Tasks 2–5 | production/resume diagnostics tests | pending |
| Task 7 | `pending` | current | `unresolved` | Tasks 2–6 | full pipeline, benchmark, and final suite | pending |

## Task Breakdown

### Task 1: Freeze the admission and scorer contracts

**Purpose:**
- Establish the fixed-budget invariants, diagnostic schema, and source-backed
  regression fixture that every later task must preserve.

**Task Function:**
- Convert the validated review findings into executable cross-stage fixtures and
  baseline measurements without changing production behavior.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: direct source inspection and bounded test design; no delegated
  implementation is required.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: task-local assertions and the final verification skill.

**Specification Coverage:**
- Preserve top-50 admission and the 12,000-character request limit.
- Distinguish confirmed source defects from unverified production incidence.
- Prove the raw-to-ranking transition counts required by the stated goal.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/runtime/pipeline.yaml:vector_search_top_n,ai_score_top_n`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`
- Inspect: `src/fitcv/ai_score.py:build_ranking_request`
- Modify: `tests/fixtures/retrieval_admission_fixture.json`
- Modify: `tests/test_ranking_evaluation.py:retrieval and scorer contract tests`
- Modify: `scripts/diagnose_ranking_loss.py:diagnostic output`
- Verify: `config/policy/ranking.yaml:active_baseline_mode`

**Dependencies:**
- Current source at base commit `05707b1ac5c33717035287ecf303d1dc3ab19f1f`.

**Authority:**
- Preauthorized local actions: read source/config, add the named fixture and tests, and run the named diagnostic script without changing production budgets
- Stop for: any request to change `top_n`, the 12,000-character limit, eligibility policy, or unrelated workspace files

**Steps:**
- [ ] Step 1: Record the current values of `vector_search_top_n`, `ai_score_top_n`, the request limit, and `active_baseline_mode` in the fixture assertions.
- [ ] Step 2: Add one source-backed relevant cross-functional job, one relevant missing-vector job, one weak vector hit, and grounded negative controls to `tests/fixtures/retrieval_admission_fixture.json`.
- [ ] Step 3: Extend `scripts/diagnose_ranking_loss.py` to emit raw, normalized, enriched, rule-filtered, retrieved, admitted, selected-for-scoring, scored, and ranked counts with bounded per-job samples.
- [ ] Step 4: Add contract assertions that the top-50 and 12,000-character budgets are unchanged.

**Verification:**
- [ ] `python -m pytest -q tests/test_ranking_evaluation.py`
- Expected: the fixture loads, budget invariants pass, and stage transition fields are present with bounded samples.

**Exit Criteria:**
- A deterministic fixture and diagnostic contract exist for all later retrieval and scorer tests without altering production behavior.

### Task 2: Implement one bounded hybrid shortlist executor

**Purpose:**
- Ensure valid semantic and lexical candidates compete for the same fixed top-50
  cohort and that configured retrieval strategy is honored in production and
  resume paths.

**Task Function:**
- Refactor retrieval admission and its orchestration around one effective
  strategy and an auditable rank-fusion envelope.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared production-path ownership and cross-stage integration risk.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused vector-search, pipeline, and checkpoint regressions.

**Specification Coverage:**
- Preserve top-50 scoring capacity.
- Let a strong lexical match displace a weak vector hit when the vector cohort is full.
- Honor explicit lexical configuration and permit supported mixed fallback.
- Keep cosine and lexical values separate; fuse rank positions only.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/vector_search.py:run_vector_search,_lexical_search_result,hybrid admission helpers`
- Inspect/modify: `src/fitcv/pipeline.py:run_pipeline,_validate_checkpoint_retrieval_strategy`
- Inspect/modify: `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage`
- Inspect/modify: `src/fitcv/pipeline_stage_context.py:_validate_checkpoint_retrieval_strategy`
- Inspect/modify: `src/fitcv/preference_policy.py:resolve_run_preference_policy`
- Inspect/modify: `src/fitcv/ranking.py:rank_jobs`
- Verify: `tests/test_vector_search.py`, `tests/test_pipeline.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_preference_policy.py`, `tests/test_ranking.py`

**Dependencies:**
- Task 1 fixture and invariants.

**Authority:**
- Preauthorized local actions: edit the named retrieval/orchestration symbols and add focused tests while preserving the fixed budgets and eligibility filters
- Stop for: changing ranking formula semantics beyond rank fusion, increasing cohort size, disabling filters, or modifying unrelated pipeline stages

**Steps:**
- [ ] Step 1: Resolve `effective_strategy` once from configuration in the canonical shortlist executor and pass it to embedding generation, retrieval, diagnostics, persistence, and resume validation.
- [ ] Step 2: Retrieve bounded vector and lexical candidate lists, deduplicate by job URL, and merge by reciprocal rank with a fixed constant and deterministic URL tie-break; retain per-channel rank and score fields separately.
- [ ] Step 3: Apply the same `top_n=50` cutoff after fusion, allowing a lexical missing-vector job to displace a weak vector hit without increasing the scoring cohort.
- [ ] Step 4: Represent requested strategy, effective run strategy, and per-row retrieval origin separately; allow only the declared mixed-fallback envelope during checkpoint restore.
- [ ] Step 5: Define mixed personalization as run-wide baseline-only whenever any admitted row lacks a compatible embedding, and persist the resolution status instead of raising during final ranking.
- [ ] Step 6: Make `run_pipeline()` call the canonical shortlist executor or share the exact same strategy-resolution path so helper tests cover production behavior.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_preference_policy.py tests/test_ranking.py`
- Expected: a full-cutoff missing-vector relevant job can enter the top 50; explicit lexical mode consumes no semantic rows; mixed rows rank and resume without an exception; the cohort remains exactly 50 or fewer.

**Exit Criteria:**
- Production, helper, and resume paths share one bounded hybrid admission contract with deterministic mixed-row behavior.

### Task 3: Enforce effective embedding contracts end to end

**Purpose:**
- Prevent stale, incompatible, or deterministic fallback vectors from being
  selected or represented as valid semantic evidence.

**Task Function:**
- Correct embedding selection ordering, cache reuse validation, and metadata
  propagation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cache-contract correctness and bounded backend integration.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: cache and metadata regressions.

**Specification Coverage:**
- Select compatible vectors before newest-row ordering.
- Carry actual backend/model/revision/dimension/preprocessing metadata.
- Keep deterministic local fallback vectors out of semantic-only paths.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/vector_search.py:embedding lookup and candidate-query cache readers`
- Inspect/modify: `src/fitcv/embeddings.py:generate_embedding_with_metadata,embed_and_store_jobs`
- Inspect/modify: `src/fitcv/pipeline_store.py:embed_and_store_jobs`
- Inspect/modify: `src/fitcv/pipeline_stage_artifacts.py:shortlist and embedding diagnostics`
- Verify: `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_pipeline_stage_resume_parity.py`

**Dependencies:**
- Task 2 effective-strategy envelope.

**Authority:**
- Preauthorized local actions: edit embedding lookup, cache validation, metadata projection, and their named tests without changing provider credentials or external services
- Stop for: adding a new embedding provider, deleting historical cache rows, or changing persistent data outside the declared cache contract

**Steps:**
- [ ] Step 1: Filter by job identity, current input signature, and expected effective embedding contract before selecting the newest compatible row.
- [ ] Step 2: Treat a matching cache key with invalid dimensions, backend, model, revision, or contract as unusable and regenerate through the existing provider boundary when generation is enabled.
- [ ] Step 3: Persist the complete actual embedding metadata in candidate-query and job-vector records, distinguishing requested metadata from effective metadata after fallback or recovery.
- [ ] Step 4: Gate semantic retrieval and CV semantic evidence alignment on a compatible semantic backend; never apply cosine semantics to deterministic fallback vectors.
- [ ] Step 5: Add bounded diagnostics for stale and incompatible rows without allowing them to hide compatible rows or make artifacts unbounded.

**Verification:**
- [ ] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_pipeline_stage_resume_parity.py`
- Expected: older compatible rows win over newer incompatible rows; invalid rows regenerate or remain explicitly rejected; actual metadata survives cache, retrieval, and resume projections.

**Exit Criteria:**
- Every semantic row used by retrieval or evidence alignment is contract-compatible and carries its actual effective metadata.

### Task 4: Make candidate queries role-complete and claims attributable

**Purpose:**
- Prevent profile order and unsupported claims from biasing retrieval or scorer
  input toward the primary target role.

**Task Function:**
- Build bounded, role-specific query representations and enforce source-linked
  support semantics across legacy and canonical candidate projections.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: candidate schema and retrieval representation share one source of truth.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: candidate, query, and matching negative controls.

**Specification Coverage:**
- Include all accepted role families and high-value AI/project evidence.
- Select by coverage and diversity rather than YAML position.
- Prevent unsupported or parent-only claims from becoming demonstrated skills.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/vector_search.py:build_candidate_query_components,technology overlap and lexical matching helpers`
- Inspect/modify: `src/fitcv/candidate.py:legacy-to-v2 adaptation,flatten_rankable_skills,language projection`
- Inspect/modify: `src/fitcv/evidence.py:term matching and support-state helpers`
- Verify: `tests/test_candidate.py`, `tests/test_vector_search.py`, `tests/test_evidence.py`

**Dependencies:**
- Task 1 fixture and Task 2 retrieval channels.

**Authority:**
- Preauthorized local actions: edit candidate/query/matching projections and add named positive and negative tests while preserving legacy input compatibility
- Stop for: discarding valid legacy evidence, adding uncontrolled substring matching, or changing accepted role-family configuration

**Steps:**
- [ ] Step 1: Build one bounded query representation per declared accepted role family, selecting skills, domains, technologies, and project passages by relevance, coverage, and cross-project diversity rather than input order.
- [ ] Step 2: Include role-family alignment in lexical retrieval and combine it with title relevance without making the primary target role the sole title reference.
- [ ] Step 3: Add bounded matching between job responsibilities and project passages; redistribute technology weight when the job has no extracted technology stack instead of allowing an empty stack to erase project evidence.
- [ ] Step 4: Require valid attributable evidence references before a canonical v2 skill is treated as demonstrated; represent legacy parent-only support explicitly rather than attaching it to every child project.
- [ ] Step 5: Replace reverse token-subset and unordered partial-token matches with exact phrases, approved aliases, and controlled containment tied to an attributable source span.
- [ ] Step 6: Preserve language `read`, `write`, and `speak` levels while projecting a scorer-readable canonical level, without allowing preferred proficiency to overwrite required proficiency.

**Verification:**
- [ ] `python -m pytest -q tests/test_candidate.py tests/test_vector_search.py tests/test_evidence.py`
- Expected: later AI role families and projects appear in bounded query components; unsupported claims do not enter rankable skills; `Power BI` does not match `BI` or `Power`; genuine aliases and pytest evidence remain positive.

**Exit Criteria:**
- Retrieval and scorer projections use role-complete, source-attributable candidate facts with deterministic negative-match behavior.

### Task 5: Make the 12,000-character scorer request truthful

**Purpose:**
- Preserve job-specific mandatory facts and the strongest complementary evidence
  within the fixed request limit, or fail explicitly without provider scoring.

**Task Function:**
- Replace arbitrary field and evidence deletion with structured mandatory-core
  budgeting and final-render coverage accounting.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: high-risk scorer boundary where incomplete context changes the baseline score.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: provider-boundary stubs and exact serialized-request assertions.

**Specification Coverage:**
- Keep the 12,000-character limit.
- Fit required skills, qualifications, language levels, and applicable constraints first.
- Preserve attributable evidence when it exists.
- Distinguish demonstrated, related, claimed-only, and no-evidence states.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/ai_score.py:build_ranking_job_input,build_ranking_request,build_ranking_input_diagnostics`
- Inspect/modify: `src/fitcv/evidence.py:build_evidence_excerpt,requirement coverage and support-state selection`
- Inspect/modify: `src/fitcv/candidate.py:language and education projection`
- Verify: `tests/test_ai_score.py`, `tests/test_evidence.py`, `tests/test_candidate.py`

**Dependencies:**
- Task 4 canonical candidate facts and evidence support states.

**Authority:**
- Preauthorized local actions: edit scorer projections, request budgeting, evidence selection, and provider-boundary tests while preserving the 12,000-character cap and holistic scoring policy
- Stop for: provider calls in tests, silent fallback to partial mandatory context, changing the compatibility formula, or deleting source provenance to save space

**Steps:**
- [ ] Step 1: Derive a job-specific mandatory-fact list from extracted required clauses, required skills, qualifications, language requirements, education, employment constraints, and applicable dates or scope.
- [ ] Step 2: Represent all mandatory facts through compact canonical IDs, normalized values, matched/missing state, and source provenance; do not reject solely because more than eight named skills exist.
- [ ] Step 3: Allocate request space in this order: mandatory facts, compact requirement coverage, attributable selected evidence, provenance and support state, then optional candidate/job context.
- [ ] Step 4: Remove duplicate `text`/`scoring_context` payloads and compute one canonical excerpt per evidence item. Rank excerpt sentences by mandatory requirement coverage before preferred/context coverage.
- [ ] Step 5: Preserve selected evidence when attributable evidence exists. If the compact mandatory facts plus evidence cannot fit, return `input_budget_exceeded` and do not call the provider. Allow zero evidence only when no attributable evidence was selected or exists, and record that state explicitly.
- [ ] Step 6: Recompute requirement coverage from the final rendered excerpts, marking pytest as direct testing evidence while not inferring debugging or evaluation without separate proof.
- [ ] Step 7: Make diagnostics report final visible evidence IDs, omission reasons, support states, provenance, character usage, and the exact mandatory-core result.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_evidence.py tests/test_candidate.py`
- Expected: 9–12 concise mandatory requirements score within 12,000 characters; genuine overflow returns `input_budget_exceeded` before provider invocation; selected evidence is retained or explicitly rejected; coverage and visible IDs match the serialized request.

**Exit Criteria:**
- No valid scorer response is produced from silently emptied mandatory facts or selected source-linked evidence.

### Task 6: Unify admission, visibility, cache, and resume diagnostics

**Purpose:**
- Make every material loss explainable and keep fresh, reused, resumed, and
  persisted ranking rows diagnostically equivalent.

**Task Function:**
- Carry one bounded diagnostic contract from production stages through artifacts,
  cache reuse, checkpoint restoration, and final ranking.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-stage state parity and bounded artifact ownership.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: persisted artifact and checkpoint round-trip tests.

**Specification Coverage:**
- Persist retrieval ranks, cutoff, backend, fallback reason, and admission reason.
- Reconcile available → selected → rendered → scored evidence states.
- Bound per-job samples and aggregate artifact growth.
- Keep score reuse tied to visible evidence and input versions.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/pipeline.py:run_pipeline,ranking-stage diagnostics and reuse`
- Inspect/modify: `src/fitcv/pipeline_stage_runner.py:shortlist admission and evidence handoff`
- Inspect/modify: `src/fitcv/pipeline_stage_artifacts.py:artifact builders`
- Inspect/modify: `src/fitcv/pipeline_stage_context.py:checkpoint payload and validation`
- Inspect/modify: `src/fitcv/ai_score.py:request fingerprint and visibility manifest`
- Verify: `tests/test_pipeline.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_ai_score.py`

**Dependencies:**
- Tasks 2–5.

**Authority:**
- Preauthorized local actions: edit diagnostic projection, artifact bounds, cache fingerprints, and checkpoint parity tests within the named pipeline surfaces
- Stop for: unbounded artifact growth, deletion of existing audit facts, or changing unrelated stage contracts

**Steps:**
- [ ] Step 1: Make production and resumed shortlist paths emit one `shortlist_admission_manifest` with aggregate counts plus bounded per-job samples.
- [ ] Step 2: Persist per-job retrieval rank, cutoff, channel ranks, effective metadata, admission reason, and exclusion reason.
- [ ] Step 3: Persist scorer visibility as `available`, `selected`, `rendered`, `omitted`, and `scored`, with requirement IDs and source references for rendered evidence.
- [ ] Step 4: Include profile version, requirement fingerprint, effective retrieval metadata, and final visibility manifest in score reuse identity.
- [ ] Step 5: Ensure fresh, reused, resumed, ranking-row, and persisted-artifact diagnostics use the same canonical record rather than reconstructing fields from configuration.
- [ ] Step 6: Bound diagnostic maps and SQL lookup batches while retaining exact aggregate transition counts.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_ai_score.py`
- Expected: fresh and reused rows have equal visibility and retrieval metadata; mixed fallback checkpoints restore; artifact sizes and diagnostic samples remain bounded under large eligible pools.

**Exit Criteria:**
- A relevant job or material fact can be traced from raw input to final score or to an explicit, stage-specific omission reason.

### Task 7: Repair evaluation fixtures and prove the complete pipeline

**Purpose:**
- Establish fresh recall, precision, evidence-visibility, false-positive, and
  performance evidence before the plan can be marked complete.

**Task Function:**
- Run the bounded evaluation matrix and reconcile results with the plan's
  preserved constraints and completion criteria.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final cross-stage verification and measured performance proof.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: `skill-verification-before-completion` owns the final status decision.

**Specification Coverage:**
- Prove relevant-job recall without increasing top-50 capacity.
- Prove truthful scorer visibility under 12,000 characters.
- Prove negative controls, raw-to-ranking transitions, checkpoint parity, and
  matched benchmark results.

**Required Skills:**
- `skill-performance-optimization`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect/modify: `tests/fixtures/ranking_gold.json:validated evaluation records`
- Inspect/modify: `tests/fixtures/retrieval_admission_fixture.json:full-pipeline cases`
- Inspect/modify: `tests/test_ranking_evaluation.py:recall and precision assertions`
- Inspect/modify: `scripts/diagnose_ranking_loss.py:replay and manifest output`
- Inspect: `scripts/benchmark_ranking.py:benchmark_ranking`
- Verify: all files in the plan target list and recorded result artifacts under `.tmp/`

**Dependencies:**
- Tasks 2–6.

**Authority:**
- Preauthorized local actions: repair the named evaluation fixture, run the declared local evaluations and benchmarks, and record immutable result paths in this plan
- Stop for: weakening fixture validation, changing budgets to make a benchmark pass, claiming production incidence without run artifacts, or publishing results externally

**Steps:**
- [ ] Step 1: Repair `tests/fixtures/ranking_gold.json` so `ndcg_top_n_must_not_exceed_ranking_top_n` and missing `source_group_id` validation errors are resolved without removing required labels or provenance.
- [ ] Step 2: Run `python scripts/diagnose_ranking_loss.py --fixture tests/fixtures/retrieval_admission_fixture.json --output .tmp/diagnose-ranking-loss.json` and verify raw-to-ranking counts reconcile.
- [ ] Step 3: Run matched benchmark arms with identical fixture and iteration settings: `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm incumbent --warmup-iterations 2 --measured-iterations 5 --output .tmp/benchmark/incumbent.json` and `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm lexical --warmup-iterations 2 --measured-iterations 5 --output .tmp/benchmark/lexical.json`.
- [ ] Step 4: Compare recall@50, precision@50, requirement-to-evidence recall, scorer evidence visibility, false-negative rate, score stability under profile reordering, cost per evaluated relevant job, latency, SQLite activity, cache reuse, trace size, and ranking equivalence.
- [ ] Step 5: Run the full focused cross-stage suite, compilation, full suite, and diff checks only after the fixture and production-path regressions pass.
- [ ] Step 6: Record deviations, unavailable production artifacts, benchmark result hashes, and exact command output in the plan before requesting completion verification.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_embeddings.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking.py tests/test_preference_policy.py tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_ranking_evaluation.py`
- Expected: all focused tests pass, including full-cutoff hybrid admission, mixed ranking/resume, mandatory-fact budgeting, evidence visibility, provenance, negative matching, and raw-to-ranking diagnostics.
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp tests`
- Expected: compilation succeeds.
- [ ] `python -m pytest -q`
- Expected: the full suite passes or exact pre-existing failures are recorded without claiming completion.
- [ ] `git diff --check`
- Expected: no whitespace errors.

**Exit Criteria:**
- Recall and precision are measured on the held-out fixture, the exact serialized request proves mandatory-fact and evidence visibility, matched benchmark arms are valid, and `skill-verification-before-completion` returns `verified`.

## Verification

Final artifact-level verification consists of:

- `python scripts/diagnose_ranking_loss.py --fixture tests/fixtures/retrieval_admission_fixture.json --output .tmp/diagnose-ranking-loss.json`
- The two matched `scripts/benchmark_ranking.py` commands in Task 7.
- The focused cross-stage pytest command in Task 7.
- `python -m compileall -q src/fitcv src/fitcv_cp tests`
- `python -m pytest -q`
- `git diff --check`
- `skill-verification-before-completion` confirming fresh evidence, no unresolved required task, no stale status, and no unrecorded scope deviation.

The final evidence must show that `vector_search_top_n` and `ai_score_top_n`
remain `50`, the scorer request limit remains `12,000`, mixed fallback does not
raise or fail checkpoint restore, relevant missing-vector jobs can compete for a
full cutoff, and every scored mandatory claim is either visible and attributable
or represented by an explicit unscored reason.

## Completion Criteria

The plan is ready for completion verification when:

1. all validated P1 and P2 defects in this plan have an owning implementation
   task and passing focused regression proof;
2. production and resumed shortlist paths use the same effective-strategy and
   hybrid-admission contract;
3. semantic vectors are selected and reused only when their actual effective
   contract is compatible;
4. canonical candidate claims, role-family query content, language levels, and
   evidence support states remain source-grounded;
5. the final scorer request preserves the compact mandatory core and selected
   source-linked evidence within 12,000 characters, or returns explicit
   `input_budget_exceeded` before provider invocation;
6. diagnostics reconcile available, selected, rendered, omitted, scored, and
   ranked states with bounded artifacts and stable cache identities;
7. the full raw-to-ranking fixture, negative controls, checkpoint tests, and
   valid same-arm benchmark evidence pass without increasing the top-50 cohort;
8. exact deviations and unavailable production artifacts are recorded; and
9. `skill-verification-before-completion` returns `verified` before status is
   changed from `proposed` to `completed`.

The plan must not be marked `completed` from checked boxes alone.

