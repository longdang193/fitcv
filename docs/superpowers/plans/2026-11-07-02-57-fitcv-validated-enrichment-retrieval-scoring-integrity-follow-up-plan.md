---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-validated-enrichment-retrieval-scoring-integrity-follow-up
targets:
  - src/fitcv/enrich.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - tests/test_enrich.py
  - tests/test_vector_search.py
  - tests/test_ranking.py
  - tests/test_evidence.py
  - tests/test_ai_score.py
  - tests/test_scoring_input_integrity.py
  - tests/test_pipeline.py
  - docs/pipeline.md
  - docs/FitCV-pipeline.md
---

# FitCV Validated Enrichment, Retrieval, And Scoring Integrity Follow-Up Plan

## Goal

Preserve valid job requirements and attributable candidate evidence from
enrichment through compatibility scoring. The implementation must avoid scoring
jobs without selected evidence, prevent incompatible retrieval signals from
distorting admission, preserve multi-word skills and mandatory completeness,
retain evidence context through the scorer handoff, and make visibility
diagnostics describe the exact bounded payload that the scorer receives.

This plan consolidates only the nine code-path findings validated by the two
completed read-only reviews at source commit
`503b0ed3a94bc1438173b97fdbfd71fc54e5fcb4`. The reviews inspected source and
tests but did not execute the provider or measure production frequency, so
implementation must prove deterministic boundary behavior without claiming a
measured production rate.

The confirmed non-findings remain out of scope: no separate default must-have
hard-filter defect was established, no hidden shortlist cutoff beyond the
configured `ai_score_top_n` was found, and rare-skill reservation exists even
though evidence can still be lost during scorer-context projection or
budgeting.

## Implementation Outcomes

### Canonical enrichment completeness

Canonical skill projection unions accepted raw skills with validated entity
mappings, including valid multi-word values such as `Apache Spark`. Mandatory
channel completeness is tracked independently from any preferred or
responsibility signal, so partial enrichment cannot claim a complete mandatory
core.

### Recall-preserving retrieval

Candidate/project query components are ordered by demonstrated relevance and
evidence strength, hybrid vector/lexical fallback scores are fused on a common
scale, and lexical rescue distinguishes affirmative overlap from neutral
unknown title relevance. Existing shortlist limits remain unchanged.

### Source-backed scoring and truthful diagnostics

Selected evidence retains source text, scoring context, stable IDs, and source
references through request construction. A job with no attributable selected
evidence becomes explicitly `unscored` with `failure_code: evidence_limited`
and does not invoke normal compatibility scoring. Optional candidate facts do
not masquerade as mandatory-skill overflow, and persisted visibility fields are
derived from the final selected job, candidate, and evidence payload.

### Regression and boundary proof

Focused tests prove each defect before implementation and after the fix,
including direct scorer-boundary success/failure behavior and one integrated
pipeline fixture showing that an admitted job retains required facts and
strongest project evidence through scoring. Pipeline documentation records the
new invariants and the unchanged cutoff policy.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit the listed source, test, and documentation files; run the declared local tests, compile checks, and diff checks; preserve unrelated worktree changes
- User-approval actions: push, merge, pull-request publication, external-provider calls, destructive cleanup, or scope expansion beyond the listed targets
- Parallel ownership: `none`; `enrich.py`, `vector_search.py`, `ranking.py`, `evidence.py`, and `ai_score.py` share cross-stage contracts and must be changed serially
- Sequential fallback: complete Tasks 1–5 in order; stop at the first contract mismatch or unrelated failure and record it before continuing

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-enrichment-integrity-execution`
- Base commit: `9528c7b9a3e43975524df9366b0f9a6b623cf7d9`
- Expected workspace: `clean; preserve any newly discovered user changes outside this plan`
- Next action: `Task 1 — revalidate the review pin against the current source and add the failing regression contracts`
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current | `unresolved` | none | baseline focused tests and failing regression assertions | pending |
| Task 2 | `pending` | current | `unresolved` | Task 1 | enrichment-focused tests | pending |
| Task 3 | `pending` | current | `unresolved` | Task 1 | retrieval/ranking-focused tests | pending |
| Task 4 | `pending` | current | `unresolved` | Tasks 2–3 | evidence/scorer boundary tests | pending |
| Task 5 | `pending` | current | `unresolved` | Tasks 2–4 | integrated pipeline proof, docs, final checks | pending |

## Task Breakdown

### Task 1: Revalidate the review paths and establish failing contracts

**Purpose:**
- Confirm the current implementation still contains only the nine validated paths and create deterministic regression assertions before changing shared code.

**Task Function:**
- Source-first root-cause reproduction and regression-contract design.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: pending implementation task; resolve from reasoning depth, ambiguity, scope, risk, and cost before activation.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: the lead controller owns the baseline contract.

**Specification Coverage:**
- `skill-systematic-debugging` root-cause gate; all nine validated findings; no implementation based on unverified review prose.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/enrich.py:_build_skill_entities`, `src/fitcv/enrich.py:_apply_job_semantic_snapshot`, `src/fitcv/vector_search.py:build_candidate_query_components`, `src/fitcv/vector_search.py:_hybrid_search_result`, `src/fitcv/ranking.py:compute_title_relevance`, `src/fitcv/evidence.py:build_evidence_projection`, `src/fitcv/evidence.py:build_evidence_excerpt`, `src/fitcv/ai_score.py:build_ranking_request`, `src/fitcv/ai_score.py:build_ranking_input_diagnostics`, `src/fitcv/ai_score.py:run_ai_scoring`
- Verify: `tests/test_enrich.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py`, `tests/test_pipeline.py`

**Dependencies:**
- Current workspace is clean at base commit `9528c7b9a3e43975524df9366b0f9a6b623cf7d9`; the review source pin is `503b0ed3a94bc1438173b97fdbfd71fc54e5fcb4`.

**Authority:**
- Preauthorized local actions: inspect source/tests and add deterministic failing tests in the listed test files; run focused baseline commands
- Stop for: source no longer matches a finding, a required behavior needs a product-policy decision, an unrelated worktree change is discovered, or any external/publication action

**Steps:**
- [ ] Step 1: Compare the review-pinned symbols with the current branch and record any source drift before designing assertions.
- [ ] Step 2: Add failing tests for evidence-free scoring, mixed-score fallback, neutral title rescue, multi-word raw-skill recovery, relevance-aware query ordering, context preservation, optional-overflow ownership, mandatory-channel completeness, and final-payload diagnostics.
- [ ] Step 3: Run the focused suites and confirm each new assertion fails for the expected root-cause reason rather than a fixture or import error.

**Verification:**
- [ ] `uv run pytest -q tests/test_enrich.py tests/test_vector_search.py tests/test_ranking.py tests/test_evidence.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_pipeline.py`
- Expected: existing tests pass; every newly added regression assertion fails for the identified behavior before implementation.

**Exit Criteria:**
- Each validated finding has one failing deterministic assertion, one owning symbol, and no unresolved product-policy ambiguity.

### Task 2: Preserve canonical skills and mandatory enrichment completeness

**Purpose:**
- Prevent valid multi-word skills from disappearing and prevent partial preferred/responsibility extraction from suppressing the degraded mandatory-core state.

**Task Function:**
- Enrichment contract repair with canonical projection and channel-level completeness.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: source behavior is bounded but touches canonical projection and enrichment state; resolve before activation.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused tests provide the bounded validation.

**Specification Coverage:**
- Validated findings 4 and 8: union accepted raw skills with validated entity mappings; compute mandatory completeness from mandatory channels only.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/enrich.py:_build_skill_entities`, `src/fitcv/enrich.py:_apply_job_semantic_snapshot`, `src/fitcv/enrich.py:_repair_required_skill_signal`
- Verify: `tests/test_enrich.py`

**Dependencies:**
- Task 1 failing tests and current source comparison complete.

**Authority:**
- Preauthorized local actions: modify only enrichment canonicalization/completeness code and its focused tests; run direct enrichment boundary tests and compile checks
- Stop for: changes to rule-filter policy, cache schema, provider contracts, or any need to reinterpret preferred/advantage semantics beyond the validated scope

**Steps:**
- [ ] Step 1: Project accepted raw skill values and validated entity canonical values as a deduplicated union, retaining raw-to-canonical provenance and rejecting only the existing invalid/interpersonal/proficiency patterns.
- [ ] Step 2: Compute `enrichment_completeness` and `mandatory_core_complete` from mandatory requirement channels; do not let `preferred_skills` or `responsibilities` alone clear `enrichment_degraded`.
- [ ] Step 3: Advance `ENRICH_SKILL_POSTPROCESSING_VERSION` to `canonical_skill_entities_v2` for the changed projection semantics, then verify the enrichment cache contract reprocesses affected rows while preserving reuse for unchanged valid rows.
- [ ] Step 4: Run direct enrichment calls with a valid multi-word raw skill and a preferred-only structured payload, asserting canonical output, provenance, degraded state, and stable unrelated fields.

**Verification:**
- [ ] `uv run pytest -q tests/test_enrich.py`
- Expected: `Apache Spark`-style raw skills remain in the canonical projection; partial mandatory extraction remains degraded; existing valid enrichment cases remain green.
- [ ] `uv run python -m compileall -q src/fitcv/enrich.py`
- Expected: no compilation failures.

**Exit Criteria:**
- Enrichment emits a complete canonical skill union when evidence supports it and never marks the mandatory core complete from non-mandatory signal alone.

### Task 3: Make candidate retrieval relevance-aware and score-scale safe

**Purpose:**
- Improve query coverage and cutoff recall without admitting lexical rescue rows solely because an unknown title relevance value is positive or mixing incomparable raw scores.

**Task Function:**
- Retrieval query composition, hybrid fallback fusion, and component-specific relevance-state repair.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: retrieval changes affect admission and ranking; resolve the lowest profile that can safely handle shared search contracts.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: deterministic retrieval fixtures cover the contract.

**Specification Coverage:**
- Validated findings 2, 3, and 5: common-scale hybrid fusion, affirmative lexical rescue, and evidence-ranked candidate/project query components.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/vector_search.py:build_candidate_query_components`, `src/fitcv/vector_search.py:_lexical_search_result`, `src/fitcv/vector_search.py:_has_affirmative_lexical_relevance`, `src/fitcv/vector_search.py:_hybrid_search_result`, `src/fitcv/vector_search.py:run_vector_search`, `src/fitcv/ranking.py:compute_title_relevance`
- Verify: `tests/test_vector_search.py`, `tests/test_ranking.py`

**Dependencies:**
- Task 1 failing retrieval assertions complete; preserve the configured shortlist and scoring cutoffs.

**Authority:**
- Preauthorized local actions: modify retrieval/ranking helpers and their focused tests; preserve existing result schema fields and run provider-free search boundary tests
- Stop for: changing `ai_score_top_n`, introducing a new hard filter, removing RRF behavior, or changing ranking policy weights

**Steps:**
- [ ] Step 1: Order candidate skill and project query slots using required relevance, evidence strength, distinctiveness, recency, and stable deterministic tie-breakers; diversify project slots instead of inheriting profile/alphabetical order.
- [ ] Step 2: Preserve per-channel vector and lexical ranks/scores, normalize each channel before fallback fusion, and use the normalized fused score for ordering and cutoff decisions.
- [ ] Step 3: Keep title relevance’s neutral unknown state distinct from affirmative overlap; make `_has_affirmative_lexical_relevance` inspect component-specific states so a skill/technology/description overlap can authorize rescue even when title relevance is unknown, while unknown-only rows cannot.
- [ ] Step 4: Assert cutoff behavior with mixed score scales, late high-value query components, neutral title values, affirmative skill overlap, and stable ties under input reordering.

**Verification:**
- [ ] `uv run pytest -q tests/test_vector_search.py tests/test_ranking.py`
- Expected: relevant late query components are present, mixed-channel ordering is scale-invariant, neutral-only rescue is rejected, affirmative non-title overlap is retained, and existing RRF/cutoff contracts remain green.

**Exit Criteria:**
- Retrieval admits relevant jobs based on calibrated evidence rather than source order, and no row is rescued or displaced solely by an unknown title baseline.

### Task 4: Preserve evidence context and enforce scorer input integrity

**Purpose:**
- Ensure the scorer receives attributable selected evidence and truthful mandatory facts, and explicitly records evidence-limited jobs instead of producing unsupported compatibility scores.

**Task Function:**
- Evidence projection and bounded scorer-request contract repair.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: highest-risk shared backend task; resolve based on scorer-boundary ambiguity and regression complexity.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct boundary assertions are owned by the lead controller.

**Specification Coverage:**
- Validated findings 1, 6, 7, and 9: evidence floor, source/context preservation, overflow ownership, and exact final-payload diagnostics.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/evidence.py:build_evidence_projection`, `src/fitcv/evidence.py:build_evidence_excerpt`, `src/fitcv/ai_score.py:build_ranking_request`, `src/fitcv/ai_score.py:build_ranking_input_diagnostics`, `src/fitcv/ai_score.py:run_ai_scoring`, `src/fitcv/ai_score.py:score_job`
- Verify: `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py`

**Dependencies:**
- Tasks 1–3 complete; enrichment and retrieval output contracts are stable.

**Authority:**
- Preauthorized local actions: modify evidence/scorer handoff code and focused tests; run direct scorer-boundary tests with the existing adapter seam and assert provider-call suppression where evidence is unavailable
- Stop for: changing the external LLM wire contract, changing `RANKING_REQUEST_MAX_CHARS` from `12_000`, or changing ranking policy weights

**Steps:**
- [ ] Step 1: Carry `text`, `scoring_context`, `source_refs`, and `evidence_id` as separate fields from `build_evidence_projection` through selection and `build_ranking_request`; use context for selection without replacing source text.
- [ ] Step 2: After final evidence selection and budget attempts, treat zero selected attributable evidence as an evidence-limited outcome: persist `score_status: unscored`, `failure_code: evidence_limited`, omission/visibility details, and skip normal provider scoring.
- [ ] Step 3: Compact optional employment/language records independently from mandatory candidate skills; make overflow diagnostics identify the actual omitted field owner and preserve required language records whenever they were present.
- [ ] Step 4: Build `bounded_ranking_input` and candidate/job/evidence counts from the selected payload used to render the final prompt, not from the unbounded source object; retain selected IDs and omission reasons.
- [ ] Step 5: Prove both direct success and failure boundaries: a supported job receives source-backed evidence and a zero-evidence job never reaches the normal scoring adapter.

**Verification:**
- [ ] `uv run pytest -q tests/test_evidence.py tests/test_ai_score.py tests/test_scoring_input_integrity.py`
- Expected: selected evidence retains source/context/provenance, evidence-free requests are unscored with `evidence_limited`, optional overflow is correctly attributed, and visibility diagnostics equal the final bounded payload.
- [ ] `uv run python -m compileall -q src/fitcv/evidence.py src/fitcv/ai_score.py`
- Expected: no compilation failures.

**Exit Criteria:**
- The scorer cannot emit a normal compatibility score without selected attributable evidence, and every persisted visibility field describes the exact prompt payload.

### Task 5: Prove integrated pipeline behavior and update maintained documentation

**Purpose:**
- Demonstrate that the repaired contracts compose across admission, retrieval, evidence selection, scoring, and final ranking, then document the durable invariants.

**Task Function:**
- Representative backend trace, cross-stage reconciliation, and documentation alignment.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: final integration task; resolve for cross-stage verification and documentation ownership.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final verification is performed by the lead controller through the declared commands.

**Specification Coverage:**
- Integrated proof for all nine findings; required backend boundary, failure, final-state, and trace evidence; maintained pipeline documentation.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`
- `skill-code-standards`

**Files And Symbols:**
- Inspect and verify: `src/fitcv/pipeline_stage_runner.py:execute_rule_filter_stage`, `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage`, `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`, `src/fitcv/ranking.py:rank_jobs`
- Modify tests: `tests/test_pipeline.py`, `tests/test_scoring_input_integrity.py`
- Modify documentation: `docs/pipeline.md`, `docs/FitCV-pipeline.md`

**Dependencies:**
- Tasks 2–4 complete with focused suites passing.

**Authority:**
- Preauthorized local actions: add one deterministic integrated fixture, update the two named pipeline documents, and run final local verification without provider calls or publication
- Stop for: a failing unrelated suite, a changed stage artifact/schema requiring migration, or any request to commit, push, open, review, or merge a pull request

**Steps:**
- [ ] Step 1: Add a deterministic job/candidate fixture containing a multi-word required skill, late project evidence, neutral title relevance, rich scoring context, optional candidate records, and a bounded request.
- [ ] Step 2: Trace the fixture through rule filtering, hybrid retrieval, shortlist materialization, evidence selection, scorer request construction, score-state normalization, and final ranking.
- [ ] Step 3: Assert that the admitted job retains required facts, selected evidence IDs, source references, evidence context, omission reasons, and final score state; assert that an evidence-limited variant is visible but not normally scored.
- [ ] Step 4: Document canonical skill-union, mandatory-channel completeness, calibrated retrieval, neutral-rescue, evidence-preservation, evidence-floor, and exact-diagnostics invariants without changing the existing shortlist/scoring policy values.

**Verification:**
- [ ] `uv run pytest -q tests/test_pipeline.py tests/test_scoring_input_integrity.py`
- Expected: the integrated fixture proves no planned information-loss path remains and score-state/visibility artifacts agree.
- [ ] `uv run python -m compileall -q src`
- Expected: no compilation failures.
- [ ] `git diff --check`
- Expected: no whitespace errors.

**Exit Criteria:**
- Integrated deterministic evidence proves the nine validated defects are fixed without changing unrelated admission policy, and documentation matches the implemented contracts.

## Verification

Final artifact-level verification after Tasks 1–5:

- `uv run pytest -q tests/test_enrich.py tests/test_vector_search.py tests/test_ranking.py tests/test_evidence.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_pipeline.py`
- `uv run pytest -q`
- `uv run python -m compileall -q src`
- `git diff --check`
- Inspect the integrated fixture’s final ranking request, visibility manifest, selected evidence IDs, source references, omission reasons, and score state; confirm they describe one identical bounded payload.
- Confirm `RANKING_REQUEST_MAX_CHARS == 12_000`, existing shortlist/scoring cutoffs remain unchanged, and no provider call occurs for `evidence_limited` rows.
- Confirm no unrelated current-workspace files are modified.

For backend verification, the direct boundaries are `build_ranking_request`,
`run_ai_scoring`, and the pipeline stage runner. Success and important failure
paths, final score/visibility state, and provider-call suppression are asserted
with deterministic fixtures. External LLM dependency and schema-driven API
proof are not applicable to these local contracts; no live provider call is
required. The integrated fixture is the representative operation trace.

## Completion Criteria

The plan is ready for completion verification when:

1. every validated finding has one owning source symbol, one owning task, one focused regression assertion, and one acceptance invariant;
2. canonical skill union and mandatory-channel completeness are proven;
3. retrieval query coverage, calibrated fallback fusion, and neutral rescue behavior are proven at the unchanged cutoff;
4. selected evidence retains source text, scoring context, IDs, and source references through the scorer boundary;
5. evidence-free jobs are explicitly `unscored` with `evidence_limited` and do not invoke normal compatibility scoring;
6. optional overflow and visibility diagnostics describe the exact final payload rather than source input;
7. the integrated pipeline fixture proves admitted jobs retain required facts and strongest attributable project evidence;
8. focused tests, the full suite, compile checks, and `git diff --check` are fresh and reconciled; and
9. `skill-verification-before-completion` returns `verified` before this plan status changes from `proposed` to `completed`.

No code, publication, commit, push, pull request, review, or merge is part of
this plan-writing step.
