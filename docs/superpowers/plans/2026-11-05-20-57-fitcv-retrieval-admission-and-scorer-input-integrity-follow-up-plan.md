---
layer: change
artifact_type: plan
contract_version: "1"
status: proposed
template_id: implementation-plan
name: fitcv-retrieval-admission-and-scorer-input-integrity-follow-up
targets:
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv/vector_search.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_store.py
  - tests/test_vector_search.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/fixtures/retrieval_admission_fixture.json
---

# FitCV Retrieval Admission And Scorer Input Integrity Follow-Up Plan

## Goal

Prevent relevant jobs from disappearing before scoring, then ensure every job
admitted to scoring retains the mandatory candidate and job facts plus the
strongest source-linked project evidence needed for an honest compatibility
score.

Preserve the existing `vector_search_top_n` and `ai_score_top_n` values of 50,
the 12,000-character scorer request limit, the compatibility formula, and the
existing eligibility/rule-filter behavior. A job that cannot fit the mandatory
scorer core must receive an explicit `input_budget_exceeded` result rather than
an apparently valid score based on incomplete input.

Review basis: the completed `GPT-5.6-Sol` review of commit
`1805de35240d91af822ab2c5797e41da8b6ad7af` and source confirmation against the
same revision. The requested `GPT-6` review was blocked before submission
because `High` effort was not visibly confirmed; it contributes no findings.
Only the eight findings confirmed in source are included below.

## Implementation Outcomes

### Competitive, relevance-aware shortlist admission

The production path uses competitive hybrid retrieval so lexical-only and
missing-vector jobs can displace weak vector results before the fixed top-50
cutoff. Lexical scoring includes accepted role-family alignment, and vector
candidate-query project evidence is selected from the full profile by
relevance, coverage, and deterministic cross-project diversity rather than
profile order.

### Honest enrichment and scoring inputs

Malformed or materially blank enrichment cannot silently erase a job’s raw
requirements before retrieval. Scoring retains job-specific mandatory
education, certification, language, employment, and candidate-clause facts;
selected attributable evidence cannot be reduced to zero while still scoring.

### Bounded, durable observability

Checkpoint manifests contain bounded deterministic samples and aggregate counts,
while the durable admission ledger remains complete. Hybrid below-cutoff audit
sampling is populated from the configured bound and remains stable across
reruns and resume.

### Regression proof

Focused tests cover full-cutoff lexical admission, role-family scoring, late
project evidence, enrichment failure recovery, mandatory-fact preservation,
evidence-budget failure, bounded checkpoint manifests, complete ledger writes,
and deterministic hybrid audit samples. The full test suite remains green.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only the listed source/config/test/fixture files and run the declared local verification commands
- User-approval actions: push, merge, publication, destructive cleanup, changing unrelated working-tree files, or changing the preserved top-50/12,000-character constraints
- Parallel ownership: `none`; `src/fitcv/vector_search.py` is shared by retrieval-admission and query-selection outcomes and is serialized
- Sequential fallback: execute Tasks 1 through 5 in order; stop at the first failed task-local proof before changing downstream contracts

The existing unrelated working-tree changes in `config/job_sources/indeed.json`,
`config/job_sources/linkedin.json`, `config/job_sources/workingstudentjobs.json`,
`.tmp/`, `.venv/`, `data/`, `frontend/test-results/`, and root exploratory
artifacts remain untouched.

## Task Breakdown

### Task 1: Make full-cutoff admission competitive

**Purpose:**
- Make the shipped retrieval path admit relevant lexical-only and missing-vector jobs into the same fixed top-50 competition instead of using lexical rows only as spare-capacity fill.

**Task Function:**
- Update the retrieval strategy contract and prove production shortlist admission at the cutoff.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded source change with deterministic tests and no external dependency.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: task-local tests and final verification provide the required validation.

**Specification Coverage:**
- Preserve top-50 admission while allowing a strong lexical/missing-vector candidate to displace a weak vector candidate.
- Keep vector and lexical channels comparable through the existing hybrid reciprocal-rank mechanism rather than mixing raw cosine and lexical scores.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/runtime/pipeline.yaml:pipeline.retrieval_strategy`
- Inspect: `src/fitcv/config.py:DEFAULT_RETRIEVAL_STRATEGY`, `resolve_retrieval_strategy`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`, `_hybrid_search_result`, `_lexical_search_result`
- Modify: `config/runtime/pipeline.yaml`, `src/fitcv/config.py`, `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`, `tests/test_pipeline.py`, `tests/fixtures/retrieval_admission_fixture.json`

**Dependencies:**
- None. Establish the fixed-cutoff contract before changing downstream scorer inputs.

**Authority:**
- Preauthorized local actions: edit the listed retrieval/config/test files and run focused retrieval and pipeline tests.
- Stop for: any request to increase either top-50 budget, disable eligibility filters, mix incomparable channel scores, or alter unrelated source configuration.

**Steps:**
- [ ] Step 1: Add a failing production-path regression with 51 eligible jobs: 50 vector-backed rows including one weak vector result and one highly relevant lexical-only/missing-vector row.
- [ ] Step 2: Select `hybrid_rrf_v1` as the runtime and default retrieval strategy while retaining explicit support for `vector_cosine_v1` and `lexical_v1` callers.
- [ ] Step 3: Ensure the hybrid production cohort is fused and cut once at 50; below-cutoff audit rows must not consume admission capacity.
- [ ] Step 4: Update stale expectations that assert missing-vector jobs are never scored, and preserve diagnostics for requested/effective strategy and admission reason.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_pipeline.py -k "hybrid or missing_vector or retrieval_strategy or shortlist"`
- Expected: the lexical-only job enters the 50, the weak vector job is displaced, exactly 50 jobs reach scoring, and no audit-only row is admitted.

**Exit Criteria:**
- The default production path uses competitive hybrid admission, the fixed top-50 bound remains unchanged, and focused tests prove displacement and resume-stable strategy metadata.

### Task 2: Rank accepted role families and all project evidence

**Purpose:**
- Prevent retrieval query content and lexical relevance from being biased by primary-role or profile-input order.

**Task Function:**
- Refine deterministic query-feature selection and lexical component accounting without changing the scorer’s compatibility formula.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded deterministic ranking logic in an existing retrieval module.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused retrieval tests cover ranking, tie-breaking, and permutation invariance.

**Specification Coverage:**
- Accepted role families contribute to lexical retrieval.
- Project evidence selection uses relevance, coverage, and cross-project diversity, with stable tie-breaking.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/vector_search.py:build_candidate_query_components`, `_lexical_search_result`, `build_candidate_query_text`
- Inspect: `src/fitcv/preference_policy.py:compute_declared_preference_fit_details`
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`, `config/policy/ranking.yaml`

**Dependencies:**
- Task 1 complete, so query diagnostics and admission strategy use the finalized retrieval contract.

**Authority:**
- Preauthorized local actions: edit retrieval scoring/query helpers and their tests; reuse existing preference weights and normalization helpers.
- Stop for: changing the compatibility formula, adding nondeterministic ranking, or introducing a new persistence/configuration layer for query hints.

**Steps:**
- [ ] Step 1: Add a failing test showing an accepted non-primary role family must improve lexical relevance when other fields tie.
- [ ] Step 2: Include the existing computed `role_family` preference component in the lexical score and expose it in `retrieval_components`; retain deterministic documented weighting from the existing preference policy.
- [ ] Step 3: Build project passage candidates from every declared project, score coverage against accepted role families, skills, domains, and technologies, and select at most eight with a greedy project-diversity term and stable project/name/index tie-breaks.
- [ ] Step 4: Add tests where eight weak projects precede one strong late project and where project order is permuted; assert the selected bounded query content is relevant and order-invariant.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py -k "role_family or project_evidence or query_components or lexical"`
- Expected: role-family alignment appears in lexical components, the late strong project is selected, and equivalent project permutations produce the same bounded query payload and fingerprint.

**Exit Criteria:**
- Retrieval uses all accepted role families and a deterministic relevance/diversity selection of project evidence; no primary-role-only or input-order-only path remains.

### Task 3: Preserve retrieval signal after enrichment failure

**Purpose:**
- Stop malformed extraction from converting a distinctive job into an apparently successful empty structured row.

**Task Function:**
- Harden the enrichment validation boundary and provide a source-preserving fallback for retrieval.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: failure-path contract with existing retry and raw-description fields.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct enrichment and retrieval regressions cover both recovery and fallback behavior.

**Specification Coverage:**
- Parse errors plus materially blank extraction are explicit enrichment failures.
- Retrieval retains raw description signal after exhausted recovery rather than silently scoring an empty extraction.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/enrich.py:parse_extraction_response`, `_enrich_result_to_row`, `_is_semantically_blank_enrichment_row`, `_enrich_one`
- Inspect: `src/fitcv/vector_search.py:build_job_summary_text`, `_lexical_search_result`
- Modify: `src/fitcv/enrich.py`, `src/fitcv/vector_search.py`
- Verify: `tests/test_enrich.py`, `tests/test_vector_search.py`

**Dependencies:**
- Task 1 complete; the fallback must feed the same competitive retrieval path rather than bypass admission policy.

**Authority:**
- Preauthorized local actions: edit enrichment validation/fallback code and focused tests; reuse `description_cleaned`, existing retry policy, and existing enrichment diagnostics.
- Stop for: dropping raw descriptions, treating an empty structured row as a successful cache entry, or changing LLM provider/retry policy outside the malformed-extraction case.

**Steps:**
- [ ] Step 1: Add a failing test for a generic-title job whose raw description contains a unique required technology and whose extraction response is unparseable or materially blank.
- [ ] Step 2: Make `_enrich_result_to_row` reject parser errors plus material blankness through the existing retry/error boundary instead of logging and merging an empty extraction as success.
- [ ] Step 3: After retries are exhausted, retain an explicit enrichment-failure diagnostic and route `description_cleaned` through a deterministic raw-description retrieval fallback; do not write the row as a normal fully enriched cache hit.
- [ ] Step 4: Update the old empty-success assertion and add cache/reuse tests proving failed enrichment cannot become a reusable semantically blank row.

**Verification:**
- [ ] `python -m pytest -q tests/test_enrich.py tests/test_vector_search.py -k "malformed or blank or fallback or description or reuse"`
- Expected: recovery is attempted, the unique raw-description requirement remains searchable when recovery is exhausted, and semantically blank rows are not treated as successful reusable enrichment.

**Exit Criteria:**
- A malformed enrichment response cannot erase the job’s distinguishing retrieval signal or silently enter the normal enriched-cache path.

### Task 4: Protect mandatory scorer facts and selected evidence

**Purpose:**
- Ensure the scorer sees the facts and evidence required to make an honest compatibility decision, or receives an explicit unscored outcome.

**Task Function:**
- Reconcile job-specific mandatory fact selection with request-budget reduction and evidence visibility diagnostics.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: material backend contract with explicit failure semantics and direct provider-boundary proof.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused unit tests plus a provider-call suppression assertion.

**Specification Coverage:**
- Job-specific education, certification, language, employment, and mandatory-clause facts survive bounded candidate rendering.
- Selected attributable evidence never falls from non-empty to zero while a score is still submitted.
- `mandatory_core_complete` and omission diagnostics reflect actual rendered input.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`, `build_ranking_request`, `RankingInputBudgetExceeded`
- Inspect: `src/fitcv/evidence.py:_select_final_evidence`, `_assess_requirement_support`
- Modify: `src/fitcv/ai_score.py`
- Verify: `tests/test_ai_score.py`, `tests/test_evidence.py`

**Dependencies:**
- Tasks 1–3 complete so the scorer receives the final admitted/enriched job contract.

**Authority:**
- Preauthorized local actions: edit ranking-input projection, budget reduction, visibility manifests, and focused tests; preserve the 12,000-character limit.
- Stop for: increasing the request limit, changing score weights, submitting a request with omitted mandatory facts, or making provider calls in a budget-failure test.

**Steps:**
- [ ] Step 1: Add failing tests with the matching education and certification records in position five, then add budget pressure that would remove them under the current first-four/pop-and-drop behavior.
- [ ] Step 2: Add deterministic job-specific mandatory-fact selection before optional bounding. Retain candidate records that can satisfy education, certification, language, employment, or mandatory-clause requirements; trim only unrelated optional records.
- [ ] Step 3: Track actual omission counts in `contract_metadata["mandatory_omissions"]` and compute `mandatory_core_complete` from the rendered payload rather than zero-initialized counters.
- [ ] Step 4: Change evidence reduction in `build_ranking_request` to stop at one selected evidence item when attributable evidence exists. If the mandatory core plus one evidence item cannot fit, raise `RankingInputBudgetExceeded` with `failure_code == "input_budget_exceeded"` before provider invocation.
- [ ] Step 5: Preserve the empty-evidence scoring path only when no attributable evidence was selected or exists, and assert the visibility manifest distinguishes that case from budget omission.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_evidence.py -k "mandatory or education or certification or evidence or budget or visibility"`
- Expected: required facts remain model-visible, selected evidence count never becomes zero under budget reduction, genuine empty evidence remains scoreable, and budget failure suppresses the provider call.

**Exit Criteria:**
- Every scored request either contains its job-specific mandatory facts and at least one selected attributable evidence item when one exists, or returns an explicit `input_budget_exceeded` result with truthful diagnostics.

### Task 5: Bound admission artifacts and restore audit visibility

**Purpose:**
- Keep checkpoint artifacts bounded while preserving the complete durable admission ledger and deterministic below-cutoff audit evidence.

**Task Function:**
- Separate bounded checkpoint observability from complete persistence and validate restart parity.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-stage state contract with focused round-trip proof.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: checkpoint and pipeline tests cover persisted state and side effects.

**Specification Coverage:**
- Complete admission rows remain in the durable ledger.
- Checkpoint manifests contain only configured bounded samples and aggregate counts.
- Hybrid audit samples honor `shortlist_audit_sample_n` and remain deterministic across rerun/resume.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline.py:run_pipeline`, `_sample_rows`, `_build_shortlist_quality_metrics`
- Inspect: `src/fitcv/pipeline_store.py:persist_shortlist_admission_ledger`
- Inspect: `src/fitcv/vector_search.py:_lexical_search_result`, `_hybrid_search_result`
- Modify: `src/fitcv/pipeline.py`, `src/fitcv/vector_search.py`
- Verify: `tests/test_pipeline.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_vector_search.py`

**Dependencies:**
- Tasks 1–4 complete so admission rows, evidence diagnostics, and effective strategy metadata are final.

**Authority:**
- Preauthorized local actions: edit checkpoint manifest shaping, audit-count propagation, and tests; retain the complete SQL ledger contract.
- Stop for: deleting or truncating durable ledger rows, changing checkpoint schema without a compatibility test, or adding a second persistence owner.

**Steps:**
- [ ] Step 1: Add a failing 10,000-row pipeline/checkpoint test asserting manifest samples stay within `shortlist_audit_sample_n` while the durable ledger contains all rows.
- [ ] Step 2: Extract bounded deterministic admitted/below-cutoff/error samples and aggregate counts from the full `admission_rows` population before assigning `shortlist_admission_manifest` to checkpoint state.
- [ ] Step 3: Pass the configured `shortlist_audit_sample_n` explicitly into the hybrid result builder or publish it in lexical diagnostics, then emit fused below-cutoff audit rows without allowing them into admission.
- [ ] Step 4: Round-trip the checkpoint and resume the same run; assert counts, samples, effective strategy, and sample fingerprint are unchanged.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py tests/test_vector_search.py -k "manifest or ledger or checkpoint or resume or audit"`
- Expected: checkpoint row arrays remain bounded, SQL ledger cardinality is complete, hybrid audit samples equal the configured bound, and rerun/resume identities are stable.

**Exit Criteria:**
- Checkpoints remain bounded and restart-safe, the durable ledger remains complete, and below-cutoff hybrid evidence is visible and deterministic.

## Verification

Final artifact-level verification after all tasks:

- `python -m pytest -q tests/test_vector_search.py tests/test_enrich.py tests/test_ai_score.py tests/test_evidence.py tests/test_pipeline.py tests/test_pipeline_checkpoint_contract.py`
- `python -m compileall -q src/fitcv tests`
- `python -m pytest -q`
- `git diff --check`

The final evidence must show that:

- `vector_search_top_n == 50` and `ai_score_top_n == 50` remain unchanged;
- the scorer request limit remains `12,000` characters;
- a strong lexical-only/missing-vector job can displace a weak vector job at a full cutoff;
- role-family and late project evidence affect retrieval deterministically;
- malformed enrichment preserves raw retrieval signal and does not become a normal blank cache hit;
- mandatory scorer facts and selected evidence are visible or produce explicit `input_budget_exceeded` before provider invocation;
- the complete admission ledger is durable while checkpoint manifests and audit samples stay bounded; and
- rerun/checkpoint resume produces the same effective strategy, samples, fingerprints, and score-input diagnostics.

## Completion Criteria

The plan is ready for completion verification when:

1. all eight source-validated findings have an owning task and focused regression proof;
2. the production and resumed retrieval paths use one competitive fixed-cutoff admission contract;
3. accepted role families and project evidence selection are source-grounded, bounded, and order-stable;
4. malformed enrichment cannot erase raw job requirements before retrieval;
5. every scored request retains job-specific mandatory facts and non-empty selected evidence when attributable evidence exists, or returns explicit `input_budget_exceeded`;
6. checkpoint manifests are bounded and the durable admission ledger remains complete;
7. all focused tests, checkpoint tests, and the full suite pass with no unrelated working-tree changes; and
8. `skill-verification-before-completion` returns `verified` before this plan changes from `proposed` to `completed`.

The plan must not be marked `completed` from checked boxes alone.
