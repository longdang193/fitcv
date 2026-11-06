---
layer: change
artifact_type: plan
contract_version: "1"
status: proposed
template_id: implementation-plan
name: fitcv-enrichment-retrieval-scoring-integrity
targets:
  - scripts/fetch_jobs.py
  - src/fitcv/contracts.py
  - src/fitcv/ingest.py
  - src/fitcv/enrich.py
  - src/fitcv/rule_filter.py
  - src/fitcv/vector_search.py
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/ranking_contract.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - config/policy/ranking.yaml
  - tests/fixtures/requirement_support_benchmark.json
  - tests/fixtures/retrieval_admission_fixture.json
  - tests/test_ingest.py
  - tests/test_enrich.py
  - tests/test_rule_filter.py
  - tests/test_vector_search.py
  - tests/test_candidate.py
  - tests/test_evidence.py
  - tests/test_ai_score.py
  - tests/test_scoring_input_integrity.py
  - tests/test_pipeline.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
---

# FitCV Enrichment, Retrieval, And Scoring Integrity Plan

## Goal

Make FitCV preserve the information content of substantive job descriptions and
the strongest attributable candidate evidence from ingestion through final
compatibility scoring. The implementation must prevent application/contact
boilerplate such as `Lebenslauf` or a telephone number from becoming verified
requirements, must not turn unknown extraction quality into a hard mismatch,
and must make every admitted job either source-backed and scoreable or
explicitly incomplete/unscored.

The two completed authenticated reviews and the supplied verdicts agree on the
validated code-level risks below. They do not prove which stage caused the
specific Indeed run for `1a32c5dae60fbb71`; the plan therefore requires a trace
before attributing that incident to the scraper, normalization, model, cache,
or post-processing stage.

Preserve these policies unless later labeled evidence authorizes a separate
change:

- `pipeline.vector_search_top_n == 50`.
- `pipeline.ai_score_top_n == 50`.
- `ai_score.RANKING_REQUEST_MAX_CHARS == 12_000`.
- `config/policy/ranking.yaml` remains `active_baseline_mode: holistic_ai_only`
  with holistic weight `1.0`.

## Implementation Outcomes

### Source-backed job description quality

`fetch_jobs.py` and ingestion expose one source-quality contract for complete,
partial, boilerplate-only, missing, and unknown descriptions. Character count
or non-empty text alone cannot satisfy completeness. Raw source provenance,
source checksum, and enough boundary information for diagnostics survive
normalization. Footer-only descriptions are retained for recovery but cannot
enter the normal successful-enrichment state.

### Trusted enrichment and requirement semantics

Required-skill values are validated as semantic entities and as raw values.
Contact, application, CV/resume, phone, email, URL, recruiter, and similar
boilerplate are rejected from verified skill projections and retained only as
classified rejected artifacts when useful for diagnosis. Sparse German
requirements, including one validated skill per bullet, are recoverable without
promoting preferred or advantageous terms to hard requirements.

Canonical entity mappings supplied with valid source evidence remain
authoritative; a raw-phrase semantic snapshot cannot erase them or replace
them with an empty projection. Requirement strength is preserved as typed
`required`, `preferred`, `advantage`, or `unspecified` data with source spans.
Language requirements remain typed objects. The enrichment validation policy
participates in the cache contract so previously accepted but now-invalid rows
are reprocessed while valid cache rows remain reusable.

### Recall-preserving admission and retrieval

Rule filtering uses a validated requirement projection plus trust state. A
missing or degraded requirement signal is not treated as a confirmed mismatch.
Jobs with usable raw title/role/description context remain eligible for
provisional retrieval and carry explicit admission, recovery, and cutoff
reasons. The existing hybrid RRF architecture remains the primary path. Any
mixed vector/lexical fallback uses rank or percentile normalization rather than
incomparable raw score scales. `50`/`50` cutoffs remain unchanged.

### Source-backed scorer inputs

The final scorer receives mandatory job facts, typed language requirements,
source-backed requirement IDs/spans, candidate fact IDs/values, and the
selected evidence actually visible in the rendered request. Mandatory
completeness is computed from that visible payload, not optimistic zero-filled
omission counters. If required facts are unknown, degraded, or cannot fit,
the result is explicit `needs_enrichment` or `unscored`, never a misleading
numeric compatibility score. Compact typed payloads and source snippets are
used to stay within `12_000` characters rather than raising the limit.

### Qualifier-aware evidence and stable candidate retrieval

Evidence selection distinguishes lexical relevance from verified professional,
duration, education, production, and source-provenance support. Strongest
supporters for mandatory requirements are reserved before diversity trimming;
budget trimming removes the lowest marginal requirement coverage rather than
blindly removing the tail. Candidate query construction uses a stable
stratified budget across supported explicit skills, experience, projects, and
technology evidence. Unsupported, unverified, and claimed-only evidence stays
excluded from verified matching.

### Truthful persistence, UI, and measurement

Persisted admission and shortlist records distinguish source quality, retrieval
strategy, recovery/rescue, cutoff, score state, and scorer visibility. The UI
does not label `tech_stack` or generic `keywords` as verified required skills;
it exposes category and provenance/source fields. The end-to-end benchmark
measures relevant-job recall, fact visibility, evidence coverage, score-state
truthfulness, prompt-budget failures, query-order stability, and fallback
scale invariance before any score-weight or cutoff policy change.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-systematic-debugging`, `skill-backend-verification`, `skill-test-driven-development`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: task-specific clean worktree anchored at `origin/main`; preserve the current dirty checkout unchanged
- Commit policy: `no commits during execution`; a later approved execution may use lead-owned checkpoint commits after proof acceptance
- Preauthorized local actions: inspect declared source/tests/fixtures, edit declared plan-task paths in the isolated worktree, add regression fixtures/tests, run declared local checks, and record diagnostics without external writes
- User-approval actions: commit, push, merge, publication, live external Indeed retrieval, destructive recovery, reset, cleanup, or changes outside the declared task write sets
- Parallel ownership: none; enrichment contracts, admission, scorer contracts, persistence, and benchmarks share fields and must be serialized
- Sequential fallback: execute Tasks 1–8 in dependency order in one lead-controlled worktree; do not activate a later task until the prior task-local proof and contract changes are reconciled

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `eab9931d11c2bdb6c6674eddacc7a7bd5ebf74c6`
- Expected workspace: current checkout contains unrelated tracked edits in `config/job_sources/*.json` and unrelated untracked data, scripts, virtual-environment, frontend, and review artifacts; do not reset, clean, or edit them
- Next action: create a clean implementation worktree from `origin/main`, then execute Task 1
- Blockers: exact production cause for job `1a32c5dae60fbb71` is unavailable until its captured source/run artifacts are supplied; implementation proceeds with sanitized fixtures and records that limitation

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | isolated | `unresolved` | none | incident trace and fixtures | pending |
| Task 2 | `pending` | isolated | `unresolved` | Task 1 | source-quality regressions | pending |
| Task 3 | `pending` | isolated | `unresolved` | Task 2 | enrichment semantic/provenance regressions | pending |
| Task 4 | `pending` | isolated | `unresolved` | Task 3 | admission/retrieval recall regressions | pending |
| Task 5 | `pending` | isolated | `unresolved` | Task 3 | scorer visibility and budget regressions | pending |
| Task 6 | `pending` | isolated | `unresolved` | Task 3, Task 5 | evidence/query stability regressions | pending |
| Task 7 | `pending` | isolated | `unresolved` | Task 4, Task 5, Task 6 | persistence/UI contract regressions | pending |
| Task 8 | `pending` | isolated | `unresolved` | Task 1–7 | full benchmark and verification suite | pending |

### Task 1: Freeze the incident trace and regression contract

**Purpose:**
- Establish a reproducible, sanitized end-to-end case without claiming the exact live Indeed cause is known.

**Task Function:**
- Incident-contract and baseline-fixture construction

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: requires source-first diagnosis, fixture design, and cross-stage contract mapping; resolve through Planning Dispatch before activation

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: the lead controller owns the initial trace contract; a later validation task checks the complete suite

**Specification Coverage:**
- Compare the six snapshots for job `1a32c5dae60fbb71`: raw Apify/source record, normalized job, exact enrichment request and model response, persisted enriched row/cache metadata, filter/admission record, shortlist-admission record, and final scorer input/visibility manifest.
- Keep source, model, cache, post-processing, and admission causes explicitly distinguishable until evidence selects one.

**Required Skills:**
- `skill-systematic-debugging`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/fetch_jobs.py::_description_status`
- Inspect: `src/fitcv/ingest.py::_indeed_description_text`, `_normalize_indeed_job`, `_normalize_linkedin_job`
- Inspect: `src/fitcv/enrich.py::build_enrich_request`, `merge_scraped_and_enriched`
- Inspect: `src/fitcv/pipeline.py::run_pipeline`, `_materialize_scoring_shortlist`
- Inspect: `src/fitcv/ai_score.py::build_ranking_job_input`, `build_ranking_request`
- Modify: `tests/fixtures/requirement_support_benchmark.json`, `tests/fixtures/retrieval_admission_fixture.json`, and the smallest focused test files needed to encode the sanitized case
- Verify: `tests/test_pipeline.py`, `tests/test_enrich.py`, `tests/test_ai_score.py`

**Dependencies:**
- None; use reviewed commit `eab9931d11c2bdb6c6674eddacc7a7bd5ebf74c6` as the source baseline.

**Authority:**
- Preauthorized local actions: read the pinned baseline, add sanitized fixtures/tests, and record unavailable production artifacts without contacting external services
- Stop for: any request to use live Indeed data, mutate the dirty checkout, infer the incident cause without the six-snapshot trace, or broaden fixture scope beyond enrichment/matching integrity

**Steps:**
- [ ] Step 1: Map the six snapshots to existing pipeline fields and diagnostics; record which production artifacts are unavailable rather than fabricating them.
- [ ] Step 2: Add a full German Indeed-like fixture containing one-skill-per-bullet requirements, education, responsibilities, preferred technologies, and an application/contact footer.
- [ ] Step 3: Add a footer-only fixture containing `Lebenslauf` and telephone/contact text, plus a candidate profile with attributable Power BI/Python/analytics/AI project evidence.
- [ ] Step 4: Define baseline assertions for source quality, enrichment state, admission outcome, shortlist membership, final prompt visibility, and valid/unscored score state.

**Verification:**
- [ ] Run the focused fixture tests created in this task with `python -m pytest -q tests/test_enrich.py tests/test_pipeline.py tests/test_ai_score.py`.
- Expected: the fixtures execute through the existing boundaries; the baseline documents the current failures without attributing the live incident to a particular stage.

**Exit Criteria:**
- The sanitized fixtures and six-snapshot trace contract exist, and every later task can assert a concrete invariant against the same job/candidate case.

### Task 2: Enforce source-description quality at fetch and ingest

**Purpose:**
- Stop non-empty or length-only application/contact fragments from entering normal successful enrichment.

**Task Function:**
- Canonical source-quality contract implementation

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: backend contract change spanning source adapters and normalization; resolve after Task 1 confirms fixture boundaries

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused ingestion tests provide the first validation gate

**Specification Coverage:**
- Replace `_description_status()` length-only completeness and Indeed/LinkedIn non-empty completeness with one substantive quality classification.
- Preserve source provenance, checksum, and sufficient text boundary data for later source-span diagnostics.
- Retain incomplete jobs for recovery/provisional paths; do not silently discard them.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `scripts/fetch_jobs.py::_description_status`
- Inspect/modify: `src/fitcv/ingest.py::_indeed_description_text`, `_normalize_indeed_job`, `_normalize_linkedin_job`
- Inspect/modify: `src/fitcv/contracts.py` for the canonical normalized-job quality fields
- Verify: `tests/test_ingest.py`, `tests/fixtures/requirement_support_benchmark.json`

**Dependencies:**
- Task 1 fixtures and snapshot field mapping complete.

**Authority:**
- Preauthorized local actions: edit source-quality fields and focused ingestion tests in the declared paths, run local unit tests, and preserve raw job text for recovery
- Stop for: changing source-provider authentication, adding live network fetches, changing retrieval/scoring cutoffs, or editing unrelated source adapters

**Steps:**
- [ ] Step 1: Define the canonical `description_quality` values and source-quality payload, including source field, checksum, substantive-section signals, application/contact-tail signals, and unknown state.
- [ ] Step 2: Make fetch and ingest use the same semantic quality evaluator; keep original/raw and normalized text available for provenance and source spans.
- [ ] Step 3: Mark footer-only, contact-only, missing, and unknown records as recovery-needed rather than complete; keep full descriptions with application tails eligible for normal extraction.
- [ ] Step 4: Add fixture coverage for full German text, footer-only text, short partial text, and non-English/provider-shaped payloads.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_ingest.py`.
- Expected: the footer-only fixture is not `complete`; the full fixture retains substantive requirement/responsibility evidence; raw text and quality metadata survive normalization.
- [ ] Run `python -m compileall -q src/fitcv scripts`.
- Expected: no compile or import errors in changed backend/source modules.

**Exit Criteria:**
- No path in fetch or ingest can classify a contact/application-only description as complete solely because it is non-empty or at least 80 characters long.

### Task 3: Make enrichment semantic, source-grounded, and cache-revalidatable

**Purpose:**
- Prevent plausible-looking garbage from satisfying enrichment completeness and preserve valid canonical requirements through repair and semantic projection.

**Task Function:**
- Enrichment contract and provenance normalization

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: highest-risk shared semantic contract; requires compatibility with existing cache and fallback behavior

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: enrichment regression suite and source-span round trips are the task gate

**Specification Coverage:**
- Validate raw required-skill values as well as skill entities; reject contact/application/CV boilerplate and preserve rejection diagnostics.
- Repair one validated candidate per bullet and common German headings while using aggregate source support; do not promote optional/preferred terms to hard requirements.
- Preserve `required`, `preferred`, `advantage`, and `unspecified` strength with source spans and typed language requirements.
- Make explicit valid entity mappings authoritative over raw alias snapshots; empty or partial projections cannot erase valid canonical entities.
- Make display fallbacks category/provenance-aware and version the validation policy in the enrichment cache fingerprint.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/enrich.py::_is_allowed_skill_entity`, `_is_semantically_blank_enrichment_row`
- Inspect/modify: `src/fitcv/enrich.py::_required_skill_candidates_from_description`, `_repair_required_skill_signal`
- Inspect/modify: `src/fitcv/enrich.py::_semantic_skill_values`, `_apply_job_semantic_snapshot`, `merge_scraped_and_enriched`
- Inspect/modify: `src/fitcv/enrich.py::derive_required_skills_display`, `_canonical_language_requirements`
- Inspect/modify: `src/fitcv/contracts.py` for requirement strength, source-span, rejected-artifact, and cache-policy fields
- Verify: `tests/test_enrich.py`, `tests/test_ingest.py`, `tests/test_scoring_input_integrity.py`

**Dependencies:**
- Task 2 source-quality fields and Task 1 fixtures are available.

**Authority:**
- Preauthorized local actions: change enrichment normalization, validation, fallback state, cache fingerprint inputs, and focused tests in the declared paths
- Stop for: deleting stored enrichment data, changing provider/model credentials, silently discarding rejected artifacts, or changing mandatory/optional semantics without a source-span regression

**Steps:**
- [ ] Step 1: Add a reusable raw-skill classifier shared by completeness, canonicalization, display, and downstream trust-state projection.
- [ ] Step 2: Change semantic-blank and completeness checks to require source-backed validated content; classify invalid non-empty extraction as degraded/recovery-needed.
- [ ] Step 3: Update sparse repair to preserve requirement sentence/bullet boundaries, accept one validated candidate per requirement unit, recognize `Anforderungen`, `Profil`, and `Kenntnisse`, and retain source spans.
- [ ] Step 4: Implement requirement-strength records and typed language requirements without converting preferred/advantageous terms into hard required skills.
- [ ] Step 5: Make explicit entity mappings authoritative in `_apply_job_semantic_snapshot`; add a cache validation-policy version to the effective enrichment contract fingerprint and reprocess only rows that fail the new validation.
- [ ] Step 6: Make `derive_required_skills_display()` expose the actual source category and never present `tech_stack` or `keywords` as verified required skills.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_enrich.py tests/test_ingest.py`.
- Expected: `Lebenslauf`, phone numbers, emails, URLs, and application instructions never become verified skills; one-skill-per-bullet German requirements are recovered; valid canonical entities survive an empty/partial raw snapshot; cache rows failing the new policy are reprocessed.
- [ ] Run `python -m pytest -q tests/test_scoring_input_integrity.py`.
- Expected: requirement strength, source spans, and typed language records survive the enrichment-to-scoring contract.

**Exit Criteria:**
- The full German fixture produces source-grounded requirements/responsibilities and the footer-only fixture produces explicit degraded/recovery state, never normal successful enrichment from contact/application text.

### Task 4: Make admission and retrieval trust-state aware

**Purpose:**
- Prevent unknown or degraded job facts from becoming hard mismatches while preserving relevant jobs for provisional retrieval and recording why each job was admitted or cut off.

**Task Function:**
- Recall-preserving admission and retrieval integration

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: cross-module backend behavior with fixed top-N compatibility constraints

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: rule-filter, vector-search, and pipeline fixture tests are the task gate

**Specification Coverage:**
- `check_must_have_skills()` and `apply_rule_filters()` distinguish confirmed mismatch from missing/degraded requirement data; only explicit exclusions remain hard rejects.
- Source-quality-degraded jobs with usable title/role/raw description context enter provisional retrieval or recovery state.
- Preserve hybrid RRF and current `50` retrieval/scoring pools; normalize mixed fallback channels by rank/percentile or reuse RRF.
- Persist explicit stage reasons for admission, rescue, below-cutoff, and rejection; do not silently omit relevant jobs.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/rule_filter.py::check_must_have_skills`, `apply_rule_filters`
- Inspect/modify: `src/fitcv/vector_search.py::run_vector_search`, `_hybrid_search_result`, `build_candidate_query_components`
- Inspect/modify: `src/fitcv/pipeline.py::_materialize_scoring_shortlist`, shortlist/admission orchestration
- Inspect/modify: `src/fitcv/pipeline_stage_runner.py`, `src/fitcv/pipeline_stage_context.py` for stage diagnostics/contracts
- Verify: `tests/test_rule_filter.py`, `tests/test_vector_search.py`, `tests/test_pipeline.py`, `tests/fixtures/retrieval_admission_fixture.json`

**Dependencies:**
- Task 3 trust-state and validated requirement projection are complete.

**Authority:**
- Preauthorized local actions: edit admission/retrieval behavior and diagnostics in the declared backend paths and add deterministic regression tests
- Stop for: changing `vector_search_top_n`, `ai_score_top_n`, embedding providers, user exclusion semantics, or retrieval strategy policy outside fallback scale correction

**Steps:**
- [ ] Step 1: Define the shared validated requirement projection consumed by rule filtering, lexical retrieval, vector-query hints, and structured scoring.
- [ ] Step 2: Convert degraded/unknown skill completeness from hard mismatch to explicit mark/provisional state; preserve raw-description fit context.
- [ ] Step 3: Add source-quality-aware provisional retrieval using validated title/role/raw description context, while retaining current hybrid RRF and neutral-rescue protections.
- [ ] Step 4: Replace incomparable raw vector/lexical fallback sorting with rank/percentile normalization or RRF and retain channel/rank provenance.
- [ ] Step 5: Ensure `_materialize_scoring_shortlist()` attaches the full passed job and explicit admission/cutoff metadata rather than replacing job facts with retrieval stubs.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_rule_filter.py tests/test_vector_search.py tests/test_pipeline.py`.
- Expected: degraded required skills are retained as unknown/provisional, relevant raw-context jobs reach retrieval, rank-51 rescue behavior remains covered, fallback order is invariant to harmless score rescaling, and each fixture job has a truthful admission/cutoff reason.

**Exit Criteria:**
- A relevant job is not silently filtered because missing/degraded enrichment is treated as a confirmed mismatch, and all retained jobs carry enough source/context metadata for the scorer or explicit recovery state.

### Task 5: Make scorer input source-backed, typed, and budget-safe

**Purpose:**
- Ensure jobs admitted to scoring retain mandatory facts or become explicitly unscored, rather than receiving a numeric score from an optimistic or lossy prompt contract.

**Task Function:**
- Final scorer-input contract and budget enforcement

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: high-risk prompt-boundary work with direct impact on compatibility scores and failure-state semantics

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: rendered-request and visibility-manifest assertions are the task gate

**Specification Coverage:**
- Derive mandatory completeness from source-backed requirement IDs/spans and the actual rendered prompt; do not initialize omission channels optimistically.
- Serialize language requirements as typed JSON objects with level, type, and provenance.
- Preserve source requirement spans/snippets when structured enrichment is degraded.
- Compact typed mandatory facts/evidence to remain within `RANKING_REQUEST_MAX_CHARS == 12_000`; use explicit `needs_enrichment`/`unscored` for non-fitting or unknown mandatory input.
- Do not change holistic weighting or top-N policy.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/ai_score.py::build_ranking_job_input`, `build_ranking_request`, `mandatory_clause_records`
- Inspect/modify: `src/fitcv/enrich.py::_canonical_language_requirements`
- Inspect/modify: `src/fitcv/ranking_contract.py` for explicit valid/unscored/failed/needs-enrichment states
- Verify: `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py`, `config/policy/ranking.yaml`

**Dependencies:**
- Task 3 typed requirement/provenance state and Task 4 admission trust state are complete.

**Authority:**
- Preauthorized local actions: edit scorer-input serialization, visibility diagnostics, explicit failure-state mapping, and focused tests in the declared paths
- Stop for: raising the 12,000-character limit, dropping mandatory source facts to obtain a numeric score, changing holistic score weighting, or changing provider request policy

**Steps:**
- [ ] Step 1: Build a mandatory-fact manifest from source-backed requirement records and candidate fact IDs, then intersect it with the actual rendered payload.
- [ ] Step 2: Replace stringification of language dictionaries with typed JSON values and preserve level/type/provenance through `mandatory_clause_records()`.
- [ ] Step 3: Make degraded job requirements force source-span visibility or explicit `needs_enrichment`; make budget overflow explicit `unscored` with retryable diagnostics.
- [ ] Step 4: Compact repeated fields and evidence by coverage/value while retaining source snippets and prompt hash/visibility manifest.
- [ ] Step 5: Add tests for bogus-but-nonempty extraction, omitted mandatory requirements, typed German C1 language constraints, and near-budget source-span retention.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_ai_score.py tests/test_scoring_input_integrity.py`.
- Expected: every admitted fixture either has all required fact IDs/values visible in the final request or has explicit `needs_enrichment`/`unscored`; language is typed JSON; no numeric score is emitted for unknown mandatory input; the 12,000-character limit remains unchanged.

**Exit Criteria:**
- `mandatory_core_complete` is truthful against the rendered request, and scorer failures are distinguishable from genuine low compatibility scores.

### Task 6: Make evidence selection and candidate query construction qualifier-aware

**Purpose:**
- Keep the strongest attributable project/professional evidence visible and remove order-dependent candidate retrieval bias without admitting unsupported claims.

**Task Function:**
- Evidence attribution and stable query-budget design

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: cross-boundary evidence selection and retrieval-query behavior; depends on the scorer visibility contract

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: evidence coverage and permutation-stability regressions are the task gate

**Specification Coverage:**
- Separate lexical term coverage from verified professional/duration/education/production support and preserve source provenance.
- Reserve strongest verified supporters for mandatory requirements, then optimize diversity and marginal requirement coverage.
- Trim by marginal coverage under the scorer budget rather than by list position.
- Replace first-N skill truncation with a stratified supported-evidence budget across explicit skills, experience, projects, and technology context; exclude unsupported/unverified claims.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py::score_evidence_item_by_channel`, `select_ranking_evidence`, `project_candidate_evidence`
- Inspect/modify: `src/fitcv/candidate.py::flatten_rankable_skills`
- Inspect/modify: `src/fitcv/vector_search.py::build_candidate_query_components`
- Verify: `tests/test_evidence.py`, `tests/test_candidate.py`, `tests/test_vector_search.py`, `tests/test_scoring_input_integrity.py`

**Dependencies:**
- Task 3 provenance and Task 5 scorer visibility/budget contracts are complete.

**Authority:**
- Preauthorized local actions: edit evidence scoring/selection and candidate query construction in the declared paths and add deterministic evidence/retrieval tests
- Stop for: treating project evidence as professional experience without provenance, including unsupported/claimed-only claims, changing score weights, or increasing evidence/request caps without benchmark proof

**Steps:**
- [ ] Step 1: Annotate evidence items with requirement support type, source excerpt, qualifier coverage, and provenance strength.
- [ ] Step 2: Reserve mandatory requirement supporters and choose remaining evidence by marginal requirement coverage plus controlled diversity.
- [ ] Step 3: Make request-budget trimming use the same marginal-coverage calculation and emit before/after evidence IDs and omission reasons.
- [ ] Step 4: Build a stable stratified candidate query from canonical supported evidence; preserve late project technology via a separate searchable context channel without elevating it to verified skill status.
- [ ] Step 5: Add profile-permutation, late-project, qualifier, and budget-pressure regressions.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_evidence.py tests/test_candidate.py tests/test_vector_search.py tests/test_scoring_input_integrity.py`.
- Expected: a late high-value Power BI/Python/AI project remains visible when it supports a mandatory/preferred requirement; equivalent profile orderings produce equivalent query coverage; lexical overlap alone does not establish professional qualification.

**Exit Criteria:**
- The scorer sees the strongest attributable support for mandatory requirements whenever it exists within budget, and query construction is stable under harmless profile ordering changes.

### Task 7: Persist and expose provenance, admission, and score-state truthfully

**Purpose:**
- Ensure downstream storage and UI do not hide recovery jobs, mix retrieval populations, or label fallback categories as verified requirements.

**Task Function:**
- Cross-layer contract integration and observability

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: backend persistence and frontend/API consumer reconciliation after canonical contracts stabilize

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct store/API tests plus a representative rendered/UI contract check

**Specification Coverage:**
- Persist strategy-independent shortlist/admission rows or explicitly document and test any vector-only table contract; no contradiction between admission counts and scored jobs.
- Preserve source quality, enrichment trust state, admission reason, retrieval strategy/ranks, scorer visibility manifest, score state, and failure code.
- UI/API required-skills views expose required, preferred, advantage, technology, keyword, application, and contact categories separately with source labels.
- Normalized score state distinguishes valid, unscored, failed, unavailable, and needs-enrichment outcomes.

**Required Skills:**
- `skill-full-stack-integration`, `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/pipeline_stage_runner.py`, `src/fitcv/pipeline_stage_artifacts.py`, `src/fitcv/pipeline_stage_context.py`
- Inspect/modify: `src/fitcv/ranking_contract.py`
- Inspect/modify: `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/app.py`
- Verify: `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Tasks 4–6 define the admission, visibility, evidence, and score-state fields consumed here.

**Authority:**
- Preauthorized local actions: update declared persistence/API/UI consumers and their contract tests to expose canonical provenance and score state
- Stop for: destructive schema migration, deleting legacy rows, changing external API authentication, or adding a second conflicting source of truth

**Steps:**
- [ ] Step 1: Reconcile stage artifacts/checkpoint payloads with the canonical admission and scorer contracts; preserve resume parity.
- [ ] Step 2: Persist one truthful admission/shortlist record per eligible job with strategy, channel/rank, cutoff/rescue reason, source quality, and score state.
- [ ] Step 3: Update `derive_required_skills_display()` consumers and UI/API payloads to render category/provenance distinctions without fallback mislabeling.
- [ ] Step 4: Verify store round trips, checkpoint resume, score-state normalization, and rendered consumer behavior.

**Verification:**
- [ ] Run `python -m pytest -q tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`.
- Expected: persisted and rendered records preserve admission, provenance, visibility, retrieval strategy, and explicit score state with no contradiction between hybrid/lexical admissions and scored jobs.

**Exit Criteria:**
- Operators and users can distinguish verified requirements from fallback categories and can see why a job was admitted, rescued, cut off, unscored, or failed.

### Task 8: Run the end-to-end benchmark and reconcile the plan

**Purpose:**
- Prove the consolidated behavior on the sanitized Indeed case and a labeled edge-case cohort before any future tuning of scoring policy.

**Task Function:**
- Final integration verification and evidence reconciliation

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: requires fresh cross-stage evidence, benchmark interpretation, and completion-gate judgment

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: assign independently through Planning Dispatch; validator must inspect fresh outputs, not checked boxes

**Specification Coverage:**
- Validate source quality, requirement strength, enrichment trust, canonical preservation, admission recall, retrieval fusion, evidence coverage, final prompt visibility, score-state truth, and cache revalidation together.
- Measure the documented `18 valid` / `32 budget_exceeded` scorer-cohort evidence as a baseline only; do not claim it was independently rerun unless the benchmark reproduces it.
- Keep `50`/`50`, `12_000`, and `holistic_ai_only` unchanged until labeled calibration justifies a separate approved policy change.

**Required Skills:**
- `skill-verification-before-completion`, `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect/modify only when benchmark contracts require it: `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`
- Verify: `tests/fixtures/requirement_support_benchmark.json`, `tests/fixtures/retrieval_admission_fixture.json`, all focused test files from Tasks 1–7, `config/policy/ranking.yaml`

**Dependencies:**
- Tasks 1–7 complete with accepted task-local proof.

**Authority:**
- Preauthorized local actions: run fresh local benchmarks/tests, reconcile declared plan evidence, and record deviations or pre-existing failures
- Stop for: changing production policy based only on one fixture, marking the plan completed without `skill-verification-before-completion`, committing/pushing, or hiding failed/budget-exceeded outcomes

**Steps:**
- [ ] Step 1: Run the sanitized full-JD and footer-only fixtures through normalized job, enrichment, admission, retrieval, shortlist, evidence, and scorer-request boundaries.
- [ ] Step 2: Measure relevant-job recall@50, mandatory fact IDs/values visible in the final prompt, source-excerpt support, query permutation stability, fallback scale invariance, cache revalidation, admission reasons, and score-state truthfulness.
- [ ] Step 3: Compare benchmark output with the documented scorer-budget baseline; require admitted fixtures to receive a valid score or an explicit retryable `needs_enrichment`/`unscored` result.
- [ ] Step 4: Run focused tests, compile checks, full tests, and diff validation; record unrelated pre-existing failures without modifying unrelated workspace files.
- [ ] Step 5: Reconcile every validated finding to an owning task and update plan evidence only after fresh verification.

**Verification:**
- [ ] `python -m pytest -q tests/test_ingest.py tests/test_enrich.py tests/test_rule_filter.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- Expected: focused cross-stage regressions pass and the sanitized Indeed case preserves real requirements, rejects footer skills, retains relevant jobs, and exposes truthful scoring state.
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp scripts tests`
- Expected: no compile errors.
- [ ] `python -m pytest -q`
- Expected: the full suite passes; any unrelated environment/pre-existing failures are recorded with exact test names and are not silently treated as success.
- [ ] `git diff --check`
- Expected: no whitespace errors in the implementation worktree.

**Exit Criteria:**
- Fresh evidence proves the final acceptance invariants, all plan deviations are recorded, and `skill-verification-before-completion` returns `verified` before any later status change from `proposed` to `completed`.

## Verification

Final artifact-level verification after all implementation tasks:

- `python -m pytest -q tests/test_ingest.py tests/test_enrich.py tests/test_rule_filter.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- `python -m compileall -q src/fitcv src/fitcv_cp scripts tests`
- `python -m pytest -q`
- `git diff --check`

Final proof must show:

- Footer/application/contact text never becomes a verified technical skill.
- Full descriptions preserve requirement/responsibility content and required/preferred/advantage strength.
- Valid canonical entity mappings are not erased by raw semantic snapshots.
- Invalid enrichment remains explicit recovery/degraded state and cache policy changes revalidate only affected rows.
- Unknown/degraded job facts do not become confirmed mismatches or silent pre-scoring drops.
- Hybrid RRF remains in place; mixed fallback is scale-invariant; `50`/`50` cutoffs are unchanged.
- Every admitted job has source-backed mandatory facts visible to the scorer or an explicit `needs_enrichment`/`unscored` outcome.
- Typed language requirements retain level, type, and provenance in the rendered request.
- Strongest attributable project/professional evidence remains visible when it supports a mandatory requirement.
- Candidate query coverage is stable under harmless profile ordering changes and excludes unsupported claims.
- Admission, shortlist, cutoff, rescue, visibility, and score-state records are truthful and resume-stable.
- `RANKING_REQUEST_MAX_CHARS == 12_000` and `holistic_ai_only` remain unchanged until separate labeled calibration approval.
- The exact live Indeed cause remains explicitly unresolved unless the six-snapshot trace supplies evidence.

## Completion Criteria

The plan is ready for completion verification when:

1. every validated finding from the completed reviews and supplied verdicts has one owning task and one focused regression assertion;
2. source quality, enrichment, requirement strength, canonical entities, admission, retrieval, evidence, scorer visibility, persistence, and UI use one reconciled provenance-aware contract;
3. relevant jobs are not silently removed because unknown or degraded extraction is treated as mismatch;
4. jobs admitted to scoring retain source-backed mandatory facts and strongest attributable evidence or become explicitly unscored;
5. the sanitized Indeed case and labeled edge-case cohort pass under unchanged `50`/`50`/`12_000` and `holistic_ai_only` policies;
6. cache reuse, checkpoint resume, retrieval fallback, score states, and UI/API projections remain truthful;
7. focused tests, compile checks, full tests, and `git diff --check` are fresh and reconciled; and
8. `skill-verification-before-completion` returns `verified` before this plan status changes from `proposed` to `completed`.

The plan must not be marked `completed` from checked boxes alone.
