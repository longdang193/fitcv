---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-cross-functional-retrieval-and-ranking-recall
targets:
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline_stage_artifacts.py
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_candidate.py
  - tests/test_evidence.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
---

# FitCV Cross-Functional Retrieval And Ranking Recall Plan

## Goal

Prevent cross-functional AI-agent/LLM roles from being lost before or during
AI scoring when the candidate has relevant project technology evidence. The
plan targets the validated implementation gaps in `main` at
`29d79df0c7d5f16713ac08f4a5259c936ebdec48`:

- the default deterministic SHA-256 embedding is treated as a cosine-semantic
  vector instead of selecting the existing structured lexical fallback;
- shortlist job summaries omit structured responsibilities and `tech_stack`;
- legacy project adaptation removes `tech_stack` before canonical evidence is
  created;
- ranking input bounds skills by source order, sends only two caller-selected
  evidence items, and omits job `tech_stack` from the bounded requirements
  payload.

Preserve the current score formula, thresholds, baseline policy, shortlist
ordering contract, and Loose/Full/Strict evidence-mode semantics.

## Review Verdict

### Validated findings included

- `src/fitcv/embeddings.py:get_embedding_backend()` defaults to
  `sqlite_deterministic_local`, and `_deterministic_local_embedding()` derives
  vectors from SHA-256 bytes. `src/fitcv/vector_search.py:run_vector_search()`
  currently cosine-ranks valid vectors and only falls back for availability,
  validity, or contract failures. The source does not establish semantic
  meaning for the deterministic vector.
- `src/fitcv/embeddings.py:build_job_summary_text()` and
  `build_job_summary_signature_payload()` do not include structured job
  responsibilities or `tech_stack`, so those requirements cannot influence
  the shortlist embedding unless duplicated in another field.
- `src/fitcv/candidate.py:_adapt_legacy_parent()` removes project `tech_stack`
  before the v2 project evidence collection. The canonical project evidence
  path already knows how to carry project technology context, so the loss is in
  legacy adaptation rather than a need for a new evidence system.
- `src/fitcv/ai_score.py:build_ranking_job_input()` bounds candidate skills by
  list order, sends only two already-selected evidence items, and does not put
  job `tech_stack` into `job_requirements`. The pipeline does call
  `select_ranking_evidence()`, but its terms also omit job technology fields.
- Existing tests cover bounded payloads and individual retrieval/evidence
  behavior, but do not cover a synthetic profile with analytics distractors and
  agent/tool evidence through both shortlist and ranking stages.

### Excluded claims

- The exact Heidi Systems run outcome, rejection stage, numeric score, vector
  rank, selected snippets, and employer decision remain unproven without the
  original run artifacts. The implementation must expose enough diagnostics to
  distinguish below-shortlist, scorer-input, and scorer-output failures; it
  must not claim that the real vacancy was rejected by a particular stage.
- The in-memory profile rewrite is not a product fix. Do not alter candidate
  source data, reorder a user's skills manually, or add unsupported lead-
  scraping claims.
- Do not change numeric scoring weights, fit thresholds, baseline mode, or
  Loose/Full/Strict semantics. Do not add a new vector database, unbounded
  prompt input, adaptive top-N policy, or generic LLM reranker.

## Implementation Outcomes

### Semantic shortlist contract

A deterministic local embedding is never used as evidence of semantic
similarity. When the effective candidate-query backend is
`sqlite_deterministic_local`, `run_vector_search()` uses the existing
`_lexical_search_result()` path with a stable fallback reason
`non_semantic_embedding_backend`. A validated `sentence_transformers` result
continues to use cosine ranking. Effective backend, requested strategy,
effective strategy, fallback reason, and cutoff diagnostics remain available in
shortlist artifacts.

### Technology-preserving candidate and job projections

Bounded shortlist job summaries contain canonical/raw technology terms and
responsibility terms, and their signature/fingerprint changes when those terms
change. Legacy project `tech_stack` entries survive as stable canonical
`project_technology` evidence with source references. Project name and
technology context remain available to ranking evidence without relabeling
arbitrary technology strings as candidate skills.

### Requirement-aware bounded ranking input

The ranking request remains bounded at eight skills and two evidence items with
400-character evidence text, but fills the skill budget with stable
job-relevant candidate matches before remaining skills. `job_requirements`
contains bounded technology requirements. Each selected evidence item carries
bounded project identity and context fields so the model can distinguish
OpenAI-compatible API use, provider integration, and other technology claims
without treating them as interchangeable.

### Heidi-like regression and stage diagnostics

A synthetic cross-functional fixture proves shortlist and ranking separately:
the default deterministic backend selects through lexical overlap, and the
ranking payload selects agent/tool evidence over analytics distractors. The
shortlist artifact records the effective retrieval backend and fallback reason,
so a real run can be diagnosed without inferring a rejection stage.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `task-specific isolated worktree created from the reviewed main revision; preserve the current workspace and its unrelated untracked artifacts`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only declared source and test files, inspect existing contracts, create the isolated worktree, and run the declared local verification commands
- User-approval actions: `push`, `merge`, publication, destructive database cleanup, deleting or discarding unrelated artifacts, and changing score policy or retrieval defaults beyond this plan
- Parallel ownership: `none; contract changes and shared evidence projection require ordered edits`
- Sequential fallback: `job/query contract → deterministic-backend fallback → legacy technology evidence → ranking projection → pipeline diagnostics and integration proof`

## Task Breakdown

### Task 1: Extend and version structured shortlist inputs

**Purpose:**
- Make job responsibilities and technology requirements available to shortlist retrieval while preserving bounded, deterministic embedding inputs and invalidating stale summaries.

**Task Function:**
- Maintain the existing job-summary and candidate-query contracts with the smallest additive structured fields.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: bounded backend contract work with moderate cache-invalidation risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: task-local tests cover the contract directly.

**Specification Coverage:**
- Semantic shortlist contract; technology-preserving job projection.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/enrich.py` job technology extraction and canonical fields.
- Modify: `src/fitcv/embeddings.py:SHORTLIST_SUMMARY_SCHEMA_VERSION`, `build_job_summary_signature_payload()`, `build_job_summary_text()`, and embedding contract fingerprint inputs.
- Modify: `src/fitcv/vector_search.py:CANDIDATE_QUERY_SCHEMA_VERSION`, `build_candidate_query_components()`, `build_candidate_query_signature_record()`, and `build_candidate_query_text()`.
- Verify: `tests/test_embeddings.py`, `tests/test_vector_search.py`.

**Dependencies:**
- Reviewed `main` revision `29d79df0c7d5f16713ac08f4a5259c936ebdec48` and the existing embedding reuse contracts.

**Authority:**
- Preauthorized local actions: add bounded structured responsibility/technology fields, update the related schema versions/fingerprints, and add focused contract tests.
- Stop for: any change that requires deleting stored embeddings, changing the score policy, or making prompt input unbounded.

**Steps:**
- [ ] Step 1: Add stable, deduplicated, bounded `responsibilities` and `tech_stack`/`tech_stack_canonical` values to the job-summary signature payload and labelled summary text; retain current title, skill, location, seniority, and job-family fields.
- [ ] Step 2: Bump `SHORTLIST_SUMMARY_SCHEMA_VERSION` so stored job embeddings created from the old summary cannot be silently reused; keep regeneration through the existing `embed_and_store_jobs()` path.
- [ ] Step 3: Add bounded project technology hints to the candidate query components, signature payload, and query text using the existing deterministic ordering and the existing candidate-query budget; do not merge technology strings into the skill list.
- [ ] Step 4: Add tests proving that changing responsibilities or technology changes the summary/signature and that candidate query text/signature contains bounded project technology hints.

**Verification:**
- [ ] `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py -k "summary or signature or contract or query"`
- Expected: the new fields are present, bounded, deterministic, and alter the relevant fingerprint; old summary contracts are not accepted as current.

**Exit Criteria:**
- Job and candidate shortlist projections carry the new structured terms, cache identity reflects them, and focused tests pass without changing retrieval execution yet.

### Task 2: Route non-semantic embeddings to lexical retrieval

**Purpose:**
- Prevent SHA-derived deterministic vectors from being interpreted as semantic cosine similarity while retaining real sentence-transformer retrieval.

**Task Function:**
- Enforce effective-backend semantics at the shortlist boundary and preserve existing fallback behavior for unavailable structured data.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: backend boundary correction with direct success/failure proof.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing vector-search tests already exercise fallback diagnostics.

**Specification Coverage:**
- Semantic shortlist contract; effective backend diagnostics.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:generate_embedding_with_metadata()` and `build_embedding_backend_metadata()`.
- Modify: `src/fitcv/vector_search.py:run_vector_search()`, `_lexical_search_result()`, and shortlist diagnostics assembly.
- Verify: `tests/test_vector_search.py`, `tests/test_embeddings.py`.

**Dependencies:**
- Task 1 complete so summary/query contracts and fingerprints are final.

**Authority:**
- Preauthorized local actions: branch on the effective embedding backend, route deterministic results to `_lexical_search_result()`, add diagnostics, and add mocked backend tests.
- Stop for: any attempt to silently treat a deterministic vector as semantic, bypass the existing lexical matcher, or remove contract/dimension validation.

**Steps:**
- [ ] Step 1: Read `candidate_query_record["embedding_backend_id"]` after `resolve_candidate_query_embedding()` and treat only `sentence_transformers` as semantic cosine input.
- [ ] Step 2: When the effective backend is `sqlite_deterministic_local` and `structured_jobs` is available, return `_lexical_search_result()` with `requested_strategy="vector_cosine_v1"` and `fallback_reason="non_semantic_embedding_backend"`; preserve `fallback_data_unavailable` when structured jobs are absent.
- [ ] Step 3: Keep valid sentence-transformer vectors on the current cosine path and preserve stale/missing/invalid vector fallback reasons.
- [ ] Step 4: Add `diagnostics["embedding_backend_id"]` from the effective candidate-query backend without changing the existing `backend_id` meaning for effective retrieval; assert requested/effective strategy and both backend fields in diagnostics.
- [ ] Step 5: Test both a deterministic backend with complete valid stored vectors and a mocked sentence-transformer backend; assert the former never emits vector-cosine production rows and the latter does.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_embeddings.py -k "vector_search or fallback or backend or embedding"`
- Expected: deterministic backend uses `lexical_v1` with `non_semantic_embedding_backend`; semantic backend uses `vector_cosine_v1`; existing missing/invalid/stale fallback tests remain green.

**Exit Criteria:**
- The shortlist path cannot produce semantic cosine rankings from deterministic hash vectors, and diagnostics identify both effective strategy and actual backend.

### Task 3: Preserve legacy project technology as evidence

**Purpose:**
- Stop the legacy profile adapter from deleting project technology facts before the canonical evidence projection is built.

**Task Function:**
- Extend the existing candidate v1-to-v2 adapter using the current evidence contract and stable source references.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: localized data-preservation change with identity and provenance risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: adapter and evidence projection tests provide direct proof.

**Specification Coverage:**
- Technology-preserving candidate projection; source provenance and evidence identity.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/candidate.py:CANDIDATE_PROFILE_V2_FIELD_REGISTRY` project schema and `_legacy_evidence()`.
- Modify: `src/fitcv/candidate.py:_adapt_legacy_parent()` for the `projects` section.
- Modify: `src/fitcv/evidence.py:_normalise_project_entry()`, `project_candidate_evidence()`, `select_ranking_evidence()`, and technology-term scoring inputs only where required by the preserved evidence.
- Verify: `tests/test_candidate.py`, `tests/test_evidence.py`.

**Dependencies:**
- Task 1 establishes the technology field names used by job and candidate projections.

**Authority:**
- Preauthorized local actions: preserve project technology as evidence, add stable `project_technology` evidence IDs/source references, include technology terms in ranking evidence scoring, and add focused tests.
- Stop for: changing the canonical project schema to add an unproven parent-level `tech_stack` field, relabeling all technology strings as skills, or weakening evidence provenance validation.

**Steps:**
- [ ] Step 1: In `_adapt_legacy_parent()`, retain project `tech_stack` values long enough to convert each non-empty value into a canonical evidence entry with kind `project_technology`, deterministic index-based identity, and the uploaded document source reference.
- [ ] Step 2: Keep project highlights and business-value evidence behavior unchanged; leave technology out of `flatten_skills()` unless an existing explicit skill claim already contains it.
- [ ] Step 3: Ensure projected project evidence exposes bounded parent title, organization/context, and technology text through the existing `scoring_context`/support-fragment fields.
- [ ] Step 4: Extend `select_ranking_evidence()` job terms with bounded raw/canonical job technology values, using the same bounded-term helper as the ranking projection, so a project technology evidence item can outrank an analytics-only distractor when it covers the requirement.
- [ ] Step 5: Add adapter tests for preservation, stable IDs, and source references; add selector tests for a technology-matching project versus an analytics distractor.

**Verification:**
- [ ] `python -m pytest -q tests/test_candidate.py tests/test_evidence.py -k "legacy or project or technology or ranking_evidence or provenance"`
- Expected: legacy project technology survives canonicalization, retains source identity, and is selected only when job terms support it.

**Exit Criteria:**
- No legacy project technology is silently discarded, and the existing evidence selector can use it without broadening the skill taxonomy.

### Task 4: Make bounded ranking input requirement-aware

**Purpose:**
- Keep the AI scorer’s prompt bounded while preventing source-order truncation from hiding candidate skills, job tools, or project identity.

**Task Function:**
- Update the ranking projection contract and its caller-owned evidence selection without changing scoring arithmetic or provider behavior.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: bounded prompt-contract change with cross-module evidence dependencies.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: ranking payload tests and pipeline-stage integration tests cover the behavior.

**Specification Coverage:**
- Requirement-aware bounded ranking input; project/tool evidence visibility.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage()` and `select_ranking_evidence()` call site.
- Modify: `src/fitcv/ai_score.py:build_ranking_job_input()`.
- Modify: `src/fitcv/evidence.py:select_ranking_evidence()` only for the job-technology terms established in Task 3.
- Verify: `tests/test_ai_score.py`, `tests/test_pipeline.py`, `tests/test_evidence.py`.

**Dependencies:**
- Tasks 1 and 3 complete; the job/candidate technology fields and preserved project evidence are available.

**Authority:**
- Preauthorized local actions: add bounded job technology requirements, prioritize matched skills within the existing eight-item budget, and add bounded evidence context fields while preserving the two-item/400-character caps.
- Stop for: changing numeric score computation, adding full raw job descriptions, increasing the evidence count, or changing provider prompts outside the structured ranking payload.

**Steps:**
- [ ] Step 1: Add bounded `technology_requirements` to the serialized `job_requirements` using canonical values first and raw values as the existing fallback.
- [ ] Step 2: Build `candidate.skills` from the complete flattened list by placing stable exact/case-insensitive matches against required, preferred, and technology terms first, then fill remaining slots in original order; keep `skill_coverage` counts computed from the complete lists.
- [ ] Step 3: Serialize selected evidence with `parent_title` and `organization` capped at 160 characters, `scoring_context` capped at 400 characters, and `skills` capped at eight values in addition to the existing ID, kind, title, and text fields. Keep at most two items and retain the existing 400-character text cap.
- [ ] Step 4: Preserve `pipeline_stage_runner.py`’s selected evidence injection and verify it passes the job-aware pool into `build_ranking_job_input()` rather than rebuilding an unfiltered profile projection.
- [ ] Step 5: Add tests with more than eight conventional skills, later agent/tool matches, an analytics distractor, and project evidence naming the project and provider integration; assert the bounded payload contains the relevant matches and remains within limits.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_evidence.py tests/test_pipeline.py -k "ranking_job_input or skill_coverage or ranking_evidence or execute_ranking_stage or project"`
- Expected: relevant candidate skills and technology evidence survive bounded serialization, evidence count remains two, text/context limits remain enforced, and existing ranking identity/reuse tests remain green.

**Exit Criteria:**
- The scorer receives a small, deterministic, job-aware payload that includes relevant agent/tool evidence without changing score arithmetic or mode semantics.

### Task 5: Persist stage diagnostics and prove the cross-functional path

**Purpose:**
- Make the real run diagnosable and prove the full shortlist-to-ranking behavior with one synthetic cross-functional fixture.

**Task Function:**
- Connect existing retrieval diagnostics to stage artifacts and add representative backend boundary tests.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: cross-stage verification with artifact and failure-path requirements.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independent validation is useful because this task checks persisted diagnostics and end-to-end stage boundaries.

**Specification Coverage:**
- Heidi-like regression and stage diagnostics; backend verification evidence.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage()` state fields and `src/fitcv/pipeline_stage_artifacts.py:build_shortlist_stage_block()`.
- Modify: `src/fitcv/pipeline_stage_artifacts.py:build_shortlist_stage_block()` to persist selected retrieval diagnostics (`requested_strategy`, `effective_strategy`, `backend_id`/actual backend, `fallback_reason`, eligible/scored/production totals, and cutoff rank).
- Verify: `tests/test_pipeline.py`, `tests/test_vector_search.py`, and the existing stage-artifact assertions.

**Dependencies:**
- Tasks 1–4 complete; all contracts and direct behavior are stable.

**Authority:**
- Preauthorized local actions: add diagnostic fields to the existing shortlist stage artifact, add a synthetic fixture, mock only external LLM transport, and run backend verification commands.
- Stop for: changing stage ordering, adding a new artifact store, modifying external provider behavior, or claiming the real Heidi run outcome without its artifacts.

**Steps:**
- [ ] Step 1: Add a bounded `retrieval_diagnostics` object to the shortlist stage `decision_summary` from the existing `shortlist_diagnostics`; do not duplicate the entire raw diagnostics payload.
- [ ] Step 2: Add a synthetic profile with analytics distractors plus agent orchestration/provider evidence and structured jobs representing equivalent cross-functional requirements; run shortlist with deterministic embeddings and assert lexical retrieval keeps the matching job in the production shortlist.
- [ ] Step 3: Run the ranking stage with the same profile and mock only the external LLM response; assert the ranking input contains the job technology requirements and selected agent/tool evidence, while the score parser and score arithmetic remain unchanged.
- [ ] Step 4: Assert stage artifacts distinguish a job absent from raw shortlist rows from a job present in ranking inputs with an invalid/provider-failed score using existing `vector_rank`, `shortlist_outcome`, `score_status`, and persisted retrieval diagnostics.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_embeddings.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py tests/test_ranking_contract.py --disable-warnings --maxfail=1`
- [ ] `git diff --check`
- Expected: focused backend suite passes; the synthetic fixture proves both shortlist and ranking paths; diagnostics persist the effective retrieval decision; no score-policy or mode-semantic regression appears.

**Exit Criteria:**
- The implementation has direct backend success/failure proof, a representative cross-stage trace, and enough persisted evidence to diagnose a future Heidi-like run without guessing its failure stage.

## Verification

- `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py tests/test_ranking_contract.py --disable-warnings --maxfail=1`
- `python -m pytest -q`
- `git diff --check`
- Inspect `git diff --stat` and `git status --short`; confirm only the declared source/test files changed and all pre-existing unrelated untracked artifacts remain untouched.
- Run `skill-verification-before-completion` before changing this plan’s status from `proposed`.

## Completion Criteria

The plan is ready for completion verification when:

1. Deterministic local vectors never drive semantic cosine shortlist ranking, and lexical fallback diagnostics identify the actual backend and reason.
2. Job summary and candidate query fingerprints include bounded responsibility and technology inputs, and stale summaries are invalidated by versioned contracts.
3. Legacy project technology survives canonicalization as stable evidence with source references; no arbitrary technology string becomes a skill claim.
4. Bounded ranking input includes job technology requirements, relevance-first candidate skills, and project identity/context while retaining eight-skill, two-evidence, and text-size limits.
5. A synthetic cross-functional profile proves shortlist survival and ranking evidence selection independently, including the deterministic fallback path.
6. Shortlist stage artifacts persist effective retrieval strategy, backend, fallback reason, and cutoff data sufficient to distinguish retrieval loss from ranking loss.
7. Score arithmetic, thresholds, baseline policy, and Loose/Full/Strict semantics remain unchanged.
8. No claim is made about the actual Heidi outcome without original run artifacts, and no unrelated dirty files are modified.
