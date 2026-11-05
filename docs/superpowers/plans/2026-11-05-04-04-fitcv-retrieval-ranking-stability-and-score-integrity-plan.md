---
layer: change
artifact_type: plan
contract_version: "1"
status: active
template_id: implementation-plan
name: fitcv-retrieval-ranking-stability-and-score-integrity
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - tests/test_ai_score.py
  - tests/test_candidate.py
  - tests/test_evidence.py
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_ranking.py
  - tests/test_ranking_contract.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_ranking_evaluation.py
  - scripts/benchmark_ranking.py
---

# FitCV Retrieval, Ranking Stability, And Score Integrity Plan

## Goal

Preserve a bounded ranking request while ensuring that the holistic AI scorer
receives the most job-relevant, source-linked candidate evidence available in
that request. Remove validated retrieval and embedding-contract defects that
can alter shortlist membership, distort evidence similarity, or fail final
ranking. Reduce repeated computation and SQLite work without changing the
existing compatibility formula, shortlist size, or ranking modes.

This plan is based on the completed read-only reviews of
`longdang193/fitcv` at commits `d669d89e3a6f90c437f8baa9517231591a6704cc`
and `223be9de4d65452942d6be8ffdd2733d28bc157f`, plus the plan review at
`1b006a817c33c53ddbf4cbf2bd4014e3f52298b2`. Attached verdict: **changes
required before implementation**. The reviews were static; production
incidence and performance gains remain unmeasured until the verification tasks
run.

## Validated Findings

- `build_ranking_job_input()` exposes only the first eight required skills and
  two selected evidence records; `build_ranking_request()` can then remove
  evidence, candidate facts, job requirements, and finally raw-slice the
  rendered prompt. A valid model response can therefore be based on incomplete
  or malformed scoring context.
- Scorer-side skill prioritization uses case-insensitive string equality while
  structured ranking resolves the configured semantic/synonym policy. A
  synonym-equivalent candidate skill can therefore be scored as absent or lose
  one of the eight visible slots even when structured ranking recognizes it.
- The 12,000-character request boundary is not a complete contract for every
  caller: scalar fields and custom prompt replacements can remain unbounded,
  list counts are not all bounded, and direct callers without `ranking_input`
  cannot provide the same canonical candidate-fact checksums. Overflow policy
  and the exact boundary between dynamic payload, rendered prompt, and custom
  template are therefore part of the defect surface.
- Job embedding retrieval chooses the newest row per URL before filtering by
  the current job input signature, so an `A -> B -> A` URL reuse sequence can
  retrieve the vector for `B` while the current job is `A`.
- CV semantic evidence alignment can apply cosine similarity to deterministic
  SHA-256 vectors when no semantic backend is active.
- Lexical retrieval rows omit normalized embeddings, while final ranking raises
  when a non-zero preference vector is active. The fallback can therefore fail
  the final ranking stage instead of completing baseline-only ranking.
- The orchestrator always requests vector retrieval even when configuration
  selects lexical retrieval, allowing cached semantic vectors to bypass the
  configured strategy.
- A deterministic fallback vector can be cached under the configured semantic
  contract because the evidence cache key is built before the actual backend is
  known.
- Legacy project-level skills are attached to every child project evidence
  item, allowing unrelated highlights to appear to prove the parent skill.
- The scope explosion is owned by `adapt_candidate_profile_to_v2()`, where
  parent skills and bullet skills are merged and then attached to every parent
  evidence ID; changing only `_adapt_legacy_parent()` cannot preserve
  bullet-to-bullet attribution. Parent-only support needs an explicit
  project-context representation rather than a false child evidence link.
- `flatten_rankable_skills()` is not wired through every ranking path: the AI
  projection, candidate query, lexical retrieval, and `pipeline.build_ranking_features()`
  can still disagree about which claims are rankable. Unsupported claims can
  therefore remain in shortlist diagnostics even when scorer input excludes
  them.
- Lexical technology overlap compares exact strings even when candidate
  technology evidence is prose, reducing recall for contained technologies.
- Evidence provenance is retained internally but mostly omitted from the scorer
  prompt; the same excerpt is computed and serialized twice.
- The complementary two-slot selector has no deterministic marginal-coverage,
  redundancy, excerpt, or tie-breaking contract, so implementations can still
  crowd out a scarce technology proof with duplicate generic skill evidence.
- Effective embedding metadata is not fully owned by the candidate-query
  record/fallback diagnostic path; configured metadata can be reconstructed
  after generation and obscure the actual backend, model, dimension, or
  revision used for the vector.
- Bounded scorer-input diagnostics are not persisted end to end: the local
  `ranking_inputs_by_identity` map does not automatically reach pipeline state,
  ranking rows, or the persisted ranking-stage artifact. A fingerprint alone
  cannot show which skills, requirements, or evidence IDs the scorer saw.
- Sentence-transformer failure can repeat once per job in a batch, and lexical
  paths can perform embedding work that is not consumed.
- Embedding maintenance loads the full historical key inventory for each batch;
  candidate technology inventory construction repeats inside the job loop; full
  diagnostic traces can materialize requirement/evidence Cartesian products; and
  two smaller redundant computations remain in query construction and skill
  prioritization.

## Preserved Invariants And Non-Goals

- Keep `holistic_ai_fit: 1.0` and `structured_fit: 0.0` for baseline scoring.
- Keep the existing eight-skill and two-evidence request budgets. Improve their
  selection and compression; do not increase them or add an unbounded prompt.
- Preserve score parsing, thresholds, shortlist size, and Loose/Full/Strict
  semantics.
- Never present unsupported candidate claims as demonstrated evidence.
- Do not claim or reconstruct any particular Heidi outcome without original run
  artifacts.
- Do not add a new vector store, delete stored embeddings as a migration, or
  change unrelated frontend, packaging, or legacy pipeline behavior.

## Implementation Outcomes

### Bounded scorer contract remains complete and truthful

The final serialized request retains a mandatory core containing the job title,
all mandatory requirement coverage in compact form, technology requirements,
hard experience/language constraints, source-linked selected evidence, and the
complete scoring/output contract. Optional descriptive fields are shed first.
If the mandatory core cannot fit the 12,000-character serialized request
contract, scoring fails with an explicit bounded contract status instead of
submitting a partial prompt. The same configured semantic/synonym policy used
by structured ranking defines skill equivalence, the eight-slot priority order,
coverage checks, and the input-contract fingerprint. Dynamic fields, list
counts, rendered prompt text, and custom replacements have deterministic caps
and overflow behavior; direct legacy callers are either normalized into this
contract or explicitly rejected.

### Evidence remains job-relevant and attributable

The two evidence slots remain complementary and job-aware. Each transmitted
evidence record includes compact provenance and one bounded excerpt. Legacy
skills are linked only to attributable evidence, so selection and scoring cannot
promote unrelated project facts. Parent-only project support is represented
without attaching the claim to every child bullet. Slot selection uses a
deterministic priority hierarchy, marginal requirement coverage, redundancy
handling, and stable tie-breaking.

### Retrieval and semantic backends are contract-safe

Job vectors are selected by current input signature and effective backend
contract. Semantic evidence alignment never consumes deterministic hash vectors.
Fallback vectors are identified by their actual backend and cannot contaminate
semantic caches. Explicit lexical configuration is honored end to end.
Candidate-query records and lexical fallback diagnostics retain the effective
backend metadata returned by generation, not a reconstruction from configured
defaults.

### Fallbacks complete predictably

Lexical retrieval completes final ranking with an explicit zero-residual
baseline-only personalization state. Technology matching handles contained
terms with token boundaries and controlled multi-token matching. Backend
outages are batch-bounded rather than retried independently for every job.

### Low-risk performance improvements are measured

Unused embedding work, full-table scans, repeated technology inventory creation,
uncapped diagnostic pair materialization, duplicate query construction, and
repeated skill index lookup are reduced only where ordering, artifacts, and
score contracts remain identical. Before/after measurements use fixed fixtures
and report latency, SQLite activity, memory-related trace sizes, cache reuse,
and ranking equivalence.

### Scorer-input diagnostics are auditable

The bounded scorer-input projection—visible skill names, requirement IDs,
evidence IDs, input fingerprint, effective retrieval/backend metadata, and
truncation status—travels from ranking execution into pipeline state and the
persisted ranking-stage artifact without including raw descriptions or an
unbounded prompt.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve the untracked `.tmp/` review artifacts
- Commit policy: `no commits during execution`; commit only after final verification is fresh and the user explicitly requests publication
- Preauthorized local actions: source edits, test additions, local benchmark runs, static inspection, and configured repository verification commands
- User-approval actions: push, pull-request creation, external browser review, merge, destructive recovery, and deletion of the untracked `.tmp/` directory
- Parallel ownership: none; `ai_score.py`, `evidence.py`, `vector_search.py`, and shared pipeline contracts require ordered edits
- Sequential fallback: run Tasks 1 through 6 in order; do not start a later task until its focused proof is green or its deviation is recorded

## Task Breakdown

### Task 1: Make the serialized ranking request mandatory-core safe

**Purpose:**
- Prevent request budgeting from silently removing mandatory job, candidate, evidence, or scoring-contract data.

**Task Function:**
- Ranking-input contract implementation and prompt-boundary hardening.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after confirming the bounded backend scope and test surface.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused tests are run by the lead controller.

**Specification Coverage:**
- Bounded scorer contract remains complete and truthful; preserve the 12,000-character serialized request limit and eight-skill/two-evidence budgets.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`, `src/fitcv/ai_score.py:build_ranking_request`, `src/fitcv/ai_score.py:build_scoring_prompt`
- Inspect: `src/fitcv/ranking.py:compute_must_have_match`, `src/fitcv/semantic_snapshot.py:resolve_semantic_value`
- Modify: `src/fitcv/ai_score.py:build_ranking_job_input`, `src/fitcv/ai_score.py:build_ranking_request`, request-budget constants and truncation diagnostics
- Verify: `tests/test_ai_score.py`, `tests/test_ranking.py`, `tests/test_ranking_contract.py`

**Dependencies:**
- Pinned review evidence at `223be9de4d65452942d6be8ffdd2733d28bc157f`.
- Existing serialized-request and alias-priority tests in `tests/test_ai_score.py` remain the baseline.

**Authority:**
- Preauthorized local actions: edit the named scorer functions and their focused tests; run the declared local pytest commands.
- Stop for: any proposal to increase request budgets, alter score weights, alter score thresholds, or change shortlist/mode semantics.

**Steps:**
- [x] Step 1: Define the versioned mandatory scoring core and optional field order; apply the configured semantic/synonym resolver used by structured ranking to required, technology, preferred, and candidate skill equivalence while retaining the eight displayed slots.
- [x] Step 2: Define the 12,000-character boundary as the final serialized request and rendered prompt contract, reserve space for the scoring template/output instructions, cap every scalar and list field before serialization, and define deterministic field-removal precedence plus explicit overflow failure.
- [x] Step 3: Normalize every caller through the structured ranking-input contract, or mark the legacy direct `build_ranking_request()` path as unsupported when it cannot supply canonical candidate facts; include semantic-policy/version metadata in the contract fingerprint.
- [x] Step 4: Replace prefix and raw character slicing with field-aware reductions that preserve valid candidate JSON, complete scoring instructions, and source-linked evidence; keep serialized JSON escaping in the size calculation and emit bounded diagnostics naming removed optional fields without copying the prompt.
- [x] Step 5: Add regressions for synonym aliases, 12 required skills, duplicate/case variants, oversized escaped fields, oversized custom prompt text, direct-call behavior, and a legal maximum-size input; assert mandatory fields survive, JSON sections remain parseable, and `mandatory_prompt_tail` is never emitted.

**Verification:**
- [x] `python -m pytest -q tests/test_ai_score.py --disable-warnings --maxfail=1`
- Expected: all scorer-input tests pass; mandatory-core assertions prove the final serialized request is within 12,000 characters or returns the explicit bounded contract failure.

**Exit Criteria:**
- No valid scoring request silently submits a partial mandatory core or raw-sliced JSON.

### Task 2: Make bounded evidence selection attributable and complementary

**Purpose:**
- Ensure the two evidence slots cover distinct job requirements and retain enough provenance for the holistic scorer to interpret each fact correctly.

**Task Function:**
- Evidence projection, attribution, and coverage-aware selection correction.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after confirming the shared evidence schema and legacy compatibility constraints.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused evidence and scorer tests are run by the lead controller.

**Specification Coverage:**
- Evidence remains job-relevant and attributable; unsupported claims never become demonstrated evidence.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:select_ranking_evidence`, `src/fitcv/evidence.py:project_candidate_evidence`, `src/fitcv/evidence.py:build_evidence_excerpt`
- Inspect: `src/fitcv/evidence.py:score_evidence_item_by_channel`, `src/fitcv/evidence.py:_ranking_requirement_channels`, `src/fitcv/evidence.py:_term_is_present`
- Inspect: `src/fitcv/candidate.py:_adapt_legacy_parent`, `src/fitcv/candidate.py:adapt_candidate_profile_to_v2`, `src/fitcv/candidate.py:flatten_rankable_skills`
- Inspect: `src/fitcv/vector_search.py:build_candidate_query_components`, `src/fitcv/vector_search.py:_lexical_search_result`, `src/fitcv/pipeline.py:build_ranking_features`
- Modify: `src/fitcv/evidence.py:select_ranking_evidence`, `src/fitcv/evidence.py:project_candidate_evidence`, `src/fitcv/candidate.py:adapt_candidate_profile_to_v2`, `src/fitcv/candidate.py:flatten_rankable_skills`, `src/fitcv/ai_score.py:build_ranking_job_input`, and the named shortlist/ranking callers
- Verify: `tests/test_evidence.py`, `tests/test_candidate.py`, `tests/test_ai_score.py`, `tests/test_vector_search.py`, `tests/test_pipeline.py`

**Dependencies:**
- Task 1 defines the final request boundary and mandatory evidence serialization contract.
- Existing project-fragment attribution tests must remain green.

**Authority:**
- Preauthorized local actions: edit canonical evidence projection/selection and legacy attribution plus their tests; run focused backend tests.
- Stop for: any increase to the two-evidence budget, removal of source references, or promotion of unsupported claims.

**Steps:**
- [x] Step 1: Define deterministic slot selection as a lexicographic priority: uncovered mandatory requirements, uncovered required technologies, distinct total requirement coverage, source quality, then stable evidence ID; select slot two by marginal gain over slot one and reject near-duplicates unless no uncovered requirement exists.
- [x] Step 2: Assemble the excerpt from the bounded source span with stable sentence ordering: prefer spans covering more mandatory terms, then technology terms, then dates/scope/provenance; tie-break by source position and evidence ID, and compute the excerpt once.
- [x] Step 3: Serialize `kind`, `source_section`, parent/source identity, relevant dates, source references, skills, and one excerpt in the bounded evidence record. Preserve the two-item budget and all valid attributable repeated bullet references.
- [x] Step 4: Fix attribution in `adapt_candidate_profile_to_v2()` where parent and bullet skills are merged: create exactly one source-backed parent-context evidence record using an existing legal evidence shape/kind, point parent-only skills only to that record, attach bullet claims only to their own evidence, and do not rely on `_adapt_legacy_parent()` alone. Add validation and a regression proving parent-only skills have zero child-highlight refs and no dangling refs.
- [x] Step 5: Wire `flatten_rankable_skills()` through `build_ranking_job_input`, `build_candidate_query_components`, `_lexical_search_result`, and `build_ranking_features`; document non-ranking callers that intentionally retain the broader inventory.
- [x] Step 6: Pass the same compiled semantic policy through `execute_ranking_stage()` into requirement-channel scoring, evidence selection, and excerpt prioritization; keep responsibilities/context lexical and bounded.
- [x] Step 7: Add mixed-project SQL/Python regressions, synonym-aware fixtures that assert equivalent evidence coverage and selected IDs, provenance-in-final-prompt assertions, duplicate-variant tests, and a test proving the excerpt is not duplicated under separate `text` and `scoring_context` fields.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_candidate.py tests/test_ai_score.py --disable-warnings --maxfail=1`
- Expected: unrelated child evidence has no inherited skill, complementary evidence is selected, provenance markers appear in the serialized prompt, and repeated attributable bullets retain all valid references.

**Exit Criteria:**
- Every transmitted evidence item is source-linked and attributable, and the two slots cover distinct high-value requirements when such coverage exists.

### Task 3: Bind embeddings to current content and actual backend contracts

**Purpose:**
- Prevent stale job vectors, deterministic hash vectors, and fallback vectors cached under semantic identities from changing retrieval or semantic evidence decisions.

**Task Function:**
- Embedding identity, cache-contract, and semantic-backend correctness.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after confirming SQLite and backend-failure scope.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct backend tests are run by the lead controller.

**Specification Coverage:**
- Retrieval and semantic backends are contract-safe; cache reuse remains effective without cross-version contamination.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:embed_and_store_jobs`, `src/fitcv/embeddings.py:generate_embedding_with_metadata`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`
- Inspect: `src/fitcv/vector_search.py:CandidateQueryEmbeddingRecord`, `src/fitcv/vector_search.py:_build_candidate_query_embedding_record`
- Inspect: `src/fitcv/evidence.py:_embed_text_cached`, `src/fitcv/evidence.py:_semantic_similarity`
- Modify: the named functions, `CandidateQueryEmbeddingRecord`, `_build_candidate_query_embedding_record`, and the SQLite selection/index path that owns job-embedding identity
- Verify: `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_evidence.py`, `tests/test_pipeline.py`

**Dependencies:**
- Task 1 does not block the database contract, but Task 3 must preserve existing retrieval diagnostics consumed by Task 4.
- Existing invalid-candidate-vector regeneration and stale-contract fallback tests are the baseline.

**Authority:**
- Preauthorized local actions: edit embedding metadata, cache keys, SQL selection, and focused tests; create or update only the existing SQLite indexes required by the canonical embedding contract.
- Stop for: destructive deletion of historical embeddings, a new vector-store dependency, or an embedding dimension/model change without a versioned contract and migration decision.

**Steps:**
- [x] Step 1: Select the current job embedding by URL, input signature, effective backend, model/revision, dimension, and contract fingerprint before applying newest-row ordering.
- [x] Step 2: Preserve stale-row diagnostics separately from the usable-vector query so stale-only cases still fall back with an explicit reason.
- [x] Step 3: Extend `CandidateQueryEmbeddingRecord` and `_build_candidate_query_embedding_record()` to carry the complete effective metadata returned by generation—backend, model, revision, dimension, preprocessing, fallback state, and contract fingerprint—through lexical fallback diagnostics instead of reconstructing configured defaults.
- [x] Step 4: Make `_embed_text_cached()` consume backend metadata and include actual backend, dimension, model, revision, and contract in candidate/job cache identity; never cache deterministic fallback as semantic.
- [x] Step 5: Gate `_semantic_similarity()` on a supported semantic backend and route unsupported backends to documented lexical-only behavior.
- [x] Step 6: Add A → B → A, stale-only, contract-change, fallback-then-recovery, dimension-mismatch, effective-metadata propagation, and deterministic-backend semantic-alignment regressions.

**Verification:**
- [x] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_evidence.py tests/test_pipeline.py --disable-warnings --maxfail=1`
- Expected: A → B → A selects A, stale-only rows fall back, fallback vectors are not reused as semantic vectors, and valid semantic backends retain semantic behavior.

**Exit Criteria:**
- Retrieval and semantic evidence use only vectors whose content and backend contract match the current request.

### Task 4: Make retrieval strategy and lexical fallback failure-safe

**Purpose:**
- Honor explicit retrieval configuration and ensure lexical fallback completes ranking without fabricating embeddings or miscounting technology matches.

**Task Function:**
- Orchestrator strategy resolution, lexical matching, and personalized-ranking fallback.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after confirming pipeline-stage and ranking-policy boundaries.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: pipeline and ranking tests are run by the lead controller.

**Specification Coverage:**
- Fallbacks complete predictably; preserve baseline scoring and personalization semantics when embeddings are available.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage`, `src/fitcv/pipeline.py` shortlist orchestration
- Inspect: `src/fitcv/vector_search.py:_lexical_search_result`, `src/fitcv/vector_search.py:run_vector_search`
- Inspect: `src/fitcv/ranking.py:rank_jobs`
- Modify: effective strategy propagation, lexical technology matching, and baseline-only personalization handling
- Verify: `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_pipeline.py`

**Dependencies:**
- Task 3 defines effective backend diagnostics and compatible-vector behavior.
- Task 1 preserves the score contract that final ranking must continue to use.

**Authority:**
- Preauthorized local actions: edit strategy propagation, lexical matching, fallback ranking behavior, and focused tests.
- Stop for: changing personalized weights, baseline score formula, score thresholds, shortlist size, or mode semantics.

**Steps:**
- [x] Step 1: Resolve `retrieval_strategy` once at the shortlist boundary and pass the effective value to embedding generation, query construction, retrieval, and diagnostics.
- [x] Step 2: Ensure explicit lexical mode never generates or consumes semantic vectors and reports `embedding_generation_skipped` truthfully.
- [x] Step 3: When lexical rows lack embeddings, set an explicit baseline-only preference resolution with zero residual instead of raising; retain normal personalization for vector-backed rows.
- [x] Step 4: Match job technologies against candidate technology evidence using token boundaries and controlled multi-token matching; preserve false-positive protections for `R`, `C`, `C++`, `C#`, `Power BI`, and unrelated prose.
- [x] Step 5: Add tests for explicit lexical configuration with cached vectors, non-zero preferences plus lexical fallback, technology prose, and vector-backed personalization.

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py tests/test_ranking.py tests/test_pipeline.py --disable-warnings --maxfail=1`
- Expected: explicit lexical configuration remains lexical, lexical fallback completes with zero residual, vector-backed rows personalize, and technology matching improves without substring false positives.

**Exit Criteria:**
- Strategy selection is consistent across stages and no supported fallback path fails final ranking solely because embeddings are unavailable.

### Task 5: Remove validated repeated work and bound diagnostics

**Purpose:**
- Reduce latency, CPU, SQLite writes/reads, and memory pressure without changing shortlist ordering, ranking output, or diagnostic counts.

**Task Function:**
- Measured backend performance optimization with ordering-equivalence proof.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after confirming representative benchmark workloads and measurable targets.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark output and regression suite are reviewed by the lead controller.

**Specification Coverage:**
- Low-risk performance improvements are measured; no optimization is accepted without correctness equivalence.

**Required Skills:**
- `skill-performance-optimization`, `skill-backend-verification`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:embed_and_store_jobs`, `src/fitcv/embeddings.py:_ensure_sqlite_embedding_tables`
- Inspect: `src/fitcv/vector_search.py:_lexical_search_result`, `src/fitcv/vector_search.py:resolve_candidate_query_embedding`
- Inspect: `src/fitcv/evidence.py:build_evidence_projection` diagnostic trace construction
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`
- Inspect: `src/fitcv/ai_score.py:build_ranking_input_diagnostics`, `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`, `src/fitcv/pipeline_stage_artifacts.py:build_ranking_stage_block`, `src/fitcv/pipeline_stages/common.py:ranking_row_sample`
- Inspect: `src/fitcv/pipeline_stage_context.py:PipelineState`, `src/fitcv/pipeline_stage_context.py:payload_keys`, `src/fitcv/pipeline_stage_context.py:as_state_dict`
- Modify: only repeated-work paths proven by the baseline measurements; extend `scripts/benchmark_ranking.py` when an existing benchmark surface is insufficient
- Modify: `src/fitcv/ai_score.py:build_ranking_input_diagnostics`, `src/fitcv/pipeline_stage_context.py:PipelineState`, `payload_keys`, `as_state_dict`, checkpoint restoration, `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`, `src/fitcv/pipeline_stage_artifacts.py:build_ranking_stage_block`, and `src/fitcv/pipeline_stages/common.py:ranking_row_sample` for the bounded scorer-input diagnostic handoff
- Verify: `scripts/benchmark_ranking.py`, `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_pipeline.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_ranking_evaluation.py`

**Dependencies:**
- Tasks 1–4 must be green so performance comparisons are not measuring incorrect behavior.
- Baseline commands: run separate same-arm pairs for vector and lexical retrieval, using identical fixture, environment, warmups, and iterations; never compare `incumbent` against `lexical` as an optimization proof.

**Authority:**
- Preauthorized local actions: add deterministic benchmark cases, optimize named repeated-work paths, and run before/after measurements with fixed fixtures.
- Stop for: any optimization that changes ranking order, score artifacts, exact aggregate diagnostics, or cache contract semantics; record it as deferred instead.

**Steps:**
- [ ] Step 1: Capture baseline p50/p95 latency, cache reuse, fallback count, retrieval ordering, and ranking metrics with the existing benchmark fixture. **Deferred:** both benchmark arms returned `status: not_run` with `reason: invalid_evaluation_input` because the fixture violates existing evaluation constraints (`ndcg_top_n_must_not_exceed_ranking_top_n` and repeated `missing_source_group_id`).
- [x] Step 2: Avoid unused candidate/job embedding work on lexical paths and replace full historical embedding-key scans with current-batch contract queries while preserving conflict-safe writes.
- [x] Step 3: Probe sentence-transformer backend health once per batch after the first failure; use deterministic generation for remaining rows and retry the configured backend on the next invocation.
- [x] Step 4: Hoist candidate technology inventory and normalized sets outside the eligible-job loop; reuse candidate query components and precomputed skill positions.
- [x] Step 5: Bound detailed requirement/evidence pair samples while preserving exact counts and explicit truncation metadata.
- [x] Step 6: Add `build_ranking_input_diagnostics()` and carry its bounded projection—visible skill names, requirement IDs, evidence IDs, input fingerprint, backend/retrieval metadata, and truncation status—through `PipelineState`, `payload_keys()`, `as_state_dict()`, checkpoint restoration, ranking rows, and `build_ranking_stage_block()`; keep raw descriptions and full prompts out of diagnostics.
- [x] Step 7: Add a checkpoint round-trip regression proving the exact diagnostic projection survives resume and feeds the persisted ranking-stage artifact.
- [ ] Step 8: Extend the existing benchmark with bounded SQLite-operation and diagnostic-trace-size counters, then run same-arm before/after pairs: `incumbent` before vs optimized incumbent after, and `lexical` before vs optimized lexical after. **Blocked:** the current fixture cannot produce valid evaluation output, so latency, cache, ordering-equivalence, SQLite, and trace-size claims remain unvalidated.

**Verification:**
- [ ] `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm incumbent --warmup-iterations 1 --measured-iterations 5 --output .tmp/ranking-incumbent-before.json` — deferred; fixture rejected before measurement.
- [ ] `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm lexical --warmup-iterations 1 --measured-iterations 5 --output .tmp/ranking-lexical-before.json` — deferred; fixture rejected before measurement.
- [ ] Repeat both commands against the optimized implementation with `-after` outputs and compare only within the same arm — blocked by the same fixture validation errors.
- [x] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_ranking_evaluation.py --disable-warnings --maxfail=1`
- Expected: same-arm before/after ordering and score artifacts are identical; benchmark JSON reports latency, cache, fallback, retrieval, bounded SQLite-operation, and diagnostic-trace-size metrics; detailed samples are bounded while exact aggregate counts remain equal; checkpoint round-trip preserves scorer-input diagnostics.

**Exit Criteria:**
- Every accepted optimization has measured evidence and preserves correctness; unmeasured or behavior-changing ideas are explicitly deferred.

### Task 6: Prove the cross-stage contract and reconcile the plan

**Purpose:**
- Demonstrate that retrieval, evidence projection, scorer serialization, and final ranking work together and leave auditable diagnostics.

**Task Function:**
- Final backend integration verification and plan reconciliation.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: lead controller resolves the lowest reliable profile after all implementation tasks are complete.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final verification is controlled by `skill-verification-before-completion`.

**Specification Coverage:**
- All implementation outcomes, preserved invariants, and validated findings in this plan.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage`, `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`, `src/fitcv/pipeline.py` shortlist/ranking orchestration
- Inspect: `src/fitcv/pipeline_stage_context.py:PipelineState`, `src/fitcv/pipeline_stage_artifacts.py:build_ranking_stage_block`
- Verify: `tests/test_embeddings.py`, `tests/test_ai_score.py`, `tests/test_candidate.py`, `tests/test_evidence.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_pipeline.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_ranking_evaluation.py`
- Update only if execution discovers a documented deviation: this plan file's verification record and task states

**Dependencies:**
- Tasks 1–5 complete with focused proof.

**Authority:**
- Preauthorized local actions: run full local verification, inspect generated diagnostics, and reconcile this plan with observed results.
- Stop for: any unrelated failure, missing external credential, or required behavior not covered by the approved scope; record the exact blocker instead of changing unrelated code.

**Steps:**
- [x] Step 1: Run the focused affected suite and inspect the final serialized request, evidence IDs, effective retrieval strategy, backend metadata, preference resolution, and ranking artifacts for one synthetic profile/job matrix.
- [x] Step 2: Add or run one cross-stage integration regression in `tests/test_pipeline.py` proving that the same synthetic job survives shortlist retrieval, receives the selected bounded evidence in `execute_ranking_stage()`, reaches `build_ranking_request()`, and persists the scorer-input diagnostic projection in the ranking-stage artifact.
- [x] Step 3: Run the full non-render suite and compile checks; compare failures with the pre-change baseline.
- [x] Step 4: Run `git diff --check` and inspect `git status --short`; preserve the task-owned `.tmp/` review artifacts and unrelated user changes.
- [x] Step 5: Reconcile every task's verification result, deviation, and deferred optimization in this plan before requesting final completion verification.

**Verification:**
- [x] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_ranking_evaluation.py --disable-warnings --maxfail=1`
- [x] `python -m pytest -q -m "not render_acceptance"`
- [x] `python -m compileall -q src/fitcv tests`
- [x] `git diff --check`
- [x] `git status --short`
- Expected: focused and full suites pass or have individually documented pre-existing failures; compilation and diff checks pass; the cross-stage regression proves the same bounded request, evidence selection, backend metadata, and persisted diagnostic contract used by the tests.

**Exit Criteria:**
- `skill-verification-before-completion` returns `verified`; all required tasks and proof items are reconciled; no unresolved required defect or unrecorded scope deviation remains.

## Verification

Final artifact-level verification, after Tasks 1–6:

- `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_ranking_evaluation.py --disable-warnings --maxfail=1`
- `python -m pytest -q -m "not render_acceptance"`
- `python -m compileall -q src/fitcv tests`
- `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm incumbent --warmup-iterations 1 --measured-iterations 5 --output .tmp/ranking-incumbent-final.json`
- `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --arm lexical --warmup-iterations 1 --measured-iterations 5 --output .tmp/ranking-lexical-final.json`
- `git diff --check`
- `git status --short`

The final verification report must state the exact focused-test counts, full-suite
result, benchmark p50/p95 and cache metrics, ordering-equivalence result, any
pre-existing failures, and any deferred optimization with its reason.

## Execution Verification And Deviations

- Focused affected suite: `512 passed, 4 skipped` after review regressions for punctuation-sensitive technology matching, newest-per-URL retrieval without a supplied signature, mid-batch semantic fallback recomputation, chunked SQLite cache lookup, and deterministic-cache reuse.
- Full non-render suite: `3537 passed, 10 skipped, 6 deselected`.
- Compilation: `python -m compileall -q src/fitcv tests` passed.
- Diff/status checks: `git diff --check` passed; `git status --short` contains only
  the expected source, test, plan, and task-owned untracked `.tmp/` artifacts.
- Cross-stage proof: the regression confirms that selected bounded evidence reaches
  scorer input and that ranking diagnostics persist through the stage artifact and
  checkpoint path.
- Benchmark deviation: both executed benchmark commands returned
  `status: not_run` and `reason: invalid_evaluation_input`; no p50/p95 latency,
  cache-reuse, ordering-equivalence, SQLite-activity, or trace-size claim is made.
  The fixture must be corrected in a separate task before Task 5 benchmark
  acceptance can be completed.
- Scope boundary: unrelated frontend, packaging, and legacy pipeline failures were
  not changed by this plan and remain outside its acceptance criteria.

## Completion Criteria

The plan is ready for completion verification when:

1. The mandatory scorer core remains complete and bounded, with no raw prompt
   slicing or malformed candidate JSON submission.
2. Two evidence slots are complementary, source-linked, and skill-attributable.
3. Job embeddings, semantic evidence vectors, and fallback caches are bound to
   actual content/backend contracts.
4. Explicit lexical strategy is honored and lexical fallback completes ranking
   with explicit baseline-only personalization semantics.
5. Technology matching passes boundary/false-positive tests.
6. Accepted optimizations have before/after measurements and unchanged ordering,
   score artifacts, and aggregate diagnostic counts.
7. All focused and full verification commands are fresh, runnable, and
   reconciled with repository truth.
8. `skill-verification-before-completion` returns `verified` before the plan
   status changes from `proposed` to `completed`.

This plan does not authorize push, pull-request creation, browser review, merge,
or deletion of preserved `.tmp/` artifacts.
