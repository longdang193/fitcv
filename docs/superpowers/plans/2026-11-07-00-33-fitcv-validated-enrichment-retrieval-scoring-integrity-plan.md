---
layer: change
artifact_type: plan
contract_version: "1"
status: completed
template_id: implementation-plan
name: fitcv-validated-enrichment-retrieval-scoring-integrity
targets:
  - src/fitcv/enrich.py
  - src/fitcv/candidate.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline_stage_runner.py
  - tests/test_enrich.py
  - tests/test_candidate.py
  - tests/test_vector_search.py
  - tests/test_evidence.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_scoring_input_integrity.py
  - docs/FitCV-pipeline.md
  - docs/pipeline.md
---

# FitCV Validated Enrichment, Retrieval, And Scoring Integrity Plan

## Goal

Preserve valid job requirements and attributable candidate evidence from
enrichment through compatibility scoring. Prevent relevant jobs from being
removed because canonical skill projections are incomplete, retrieval query
components are truncated or mis-ranked, selected evidence is lost during
handoff, or prompt-budget diagnostics describe a different payload from the
one received by the scorer.

This plan is based on the completed read-only reviews of the exact
implementation base `02d876afd88b4e4d9f40dfaa46891bb55d2548fd` (the parent
of the plan-only commit). All source and test evidence must be revalidated
against this SHA before implementation; the superseded review pin
`1b2e2e40b9ad0a2a23ea27702cb98bdede8fbafb` is not an implementation base.
The two model reviews were reconciled by tracing the shared pipeline:
enrichment normalization → rule filtering → candidate/job retrieval →
shortlist cutoff → evidence selection → scorer request budgeting →
compatibility score → final ranking.

The source-level root causes included here are validated by both review
evidence or by a direct, deterministic code path with a focused regression
contract. Runtime frequency still requires the verification work in this plan.

## Validated Review Scope

Included defects:

- The canonical-skill merge remains an invariant to preserve, but the prior
  review claim that `_build_skill_entities()` or the merge path currently
  drops raw skills is not accepted without a failing regression on the chosen
  implementation base.
- Broad non-skill substring markers remove technical skills containing
  `language` or `communication`.
- Candidate retrieval is bounded by profile traversal order and project-name
  order instead of relevance-aware coverage.
- Mixed vector and lexical retrieval competes on incompatible score scales.
- Neutral unknown relevance values can be treated as affirmative lexical rescue
  signals and displace stronger cutoff rows.
- Evidence selected through enriched `scoring_context` can lose that context
  before scoring, and channel caps can make rare required-skill evidence
  unrecoverable.
- Prompt budgeting can reduce selected evidence to zero while still producing
  the operative AI score.
- Candidate-summary overflow can be attributed to mandatory skills even when
  optional employment or language records caused the overflow.
- Persisted scorer visibility diagnostics can describe the unbounded source
  input instead of the final bounded prompt payload.
- Structured completeness can be inferred from partial signal rather than
  verified per mandatory requirement channel.

Deferred from this plan because the review evidence is conditional or requires
an explicit product-policy decision before implementation:

- Expanding the optional must-have filter to `tech_stack` and other channels;
  the filter is not enabled by default and requires a hard-filter policy
  decision.
- Supporting or ranking degraded-enrichment jobs after retrieval admission;
  the code mismatch is real, but choosing degraded scoring versus a provisional
  result lane requires a separate scoring-policy specification.
- Multi-skill qualifier binding, support-state promotion, education-status
  retention, and missing embedding signatures; each needs a focused contract
  decision or runtime reproduction before changing behavior.

## Review-Cycle Corrections

The first independent review of PR `#126` at head
`495da4afcb9650231363d0d554205babfad51db6` reproduced three additional defects
within this plan's scope. The plan is amended to include their root-cause fixes:

- Hybrid lexical filtering must distinguish component-specific neutral values
  from positive partial overlap. A skill overlap such as `0.25` is affirmative
  evidence even when title relevance is the neutral unknown value `0.5`.
- Candidate-summary compaction must match language names and proficiency levels
  structurally, reserve matching records before optional-record removal, and
  mark `candidate_languages` incomplete if an originally present mandatory
  language record cannot remain visible.
- Raw-skill fallback must reject natural-language proficiency and interpersonal
  communication formulations while preserving allowlisted technical phrases
  such as `natural language processing` and `technical communication protocol`.

Focused regressions are required in `tests/test_vector_search.py`,
`tests/test_scoring_input_integrity.py`, and `tests/test_enrich.py` before the
next review cycle.

The final review cycle also validated two boundary cases: scalar skill overlap
`0.5` can be a genuine partial match rather than neutral unknown data, and a
candidate's language identity must remain visible for compatibility assessment
regardless of whether its recorded proficiency is above or below the job's
requested level. Retrieval now carries explicit skill-match signal metadata;
language compaction protects identity matches and retains the actual level.

## Implementation Outcomes

### Complete skill requirement contract

`required_skills_canonical` and `preferred_skills_canonical` remain complete
canonical projections of accepted raw skills. This is a preserved invariant;
change canonical construction only if the base-commit regression proves a
surviving information-loss path. Entity confidence and provenance remain
available without making the entity subset the completeness contract.
Known technical phrases survive soft-skill filtering, and enrichment quality
records distinguish partial structured signal from verified mandatory-channel
completeness.

### Retrieval preserves relevant candidates

Candidate query construction represents a bounded, relevance-aware cross-section
of skills and project evidence. Vector and lexical results use a shared fusion
contract, and neutral unknown values cannot qualify a row for affirmative
lexical rescue.

### Scoring receives attributable evidence

Evidence selection preserves both source text and enriched scoring context,
reserves recoverability for distinct required skills, and does not allow the
request budgeter to silently remove all selected attributable evidence while
still accepting an evidence-complete score. If no attributable evidence fits,
the scorer returns an explicit `evidence_limited` result and the ranking stage
does not treat it as a normal compatibility score.

### Diagnostics and regression proof are faithful

Candidate overflow is diagnosed by field ownership, scorer visibility metadata
is derived from the exact bounded payload, and focused tests prove the complete
admission-to-scoring path. Pipeline documentation records the preserved
contracts and the explicit deferred policy decisions.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `task-specific worktree from a clean implementation base`; preserve the current workspace's unrelated edits
- Commit policy: `no commits during execution`; branch disposition remains separately authorized after verification
- Preauthorized local actions: inspect and modify the listed source, test, fixture, and documentation files; run the listed local Python/pytest/compile/diff checks; use configured read-only repository inspection
- User-approval actions: push, merge, publication, destructive cleanup, changing ranking weights, enabling optional hard-filter policy, or choosing degraded-scoring policy
- Parallel ownership: `none`; `enrich.py`, `vector_search.py`, `evidence.py`, and `ai_score.py` share contracts and must be updated in dependency order
- Sequential fallback: execute Tasks 1–5 in order; do not begin a downstream task until the preceding task's focused tests pass

## Task Breakdown

### Task 1: Restore complete enrichment skill and quality contracts

**Purpose:**
- Ensure accepted raw technical skills survive entity normalization and canonical snapshot construction, and expose completeness only when mandatory requirement channels are verified.

**Task Function:**
- Reconcile the enrichment semantic snapshot and extraction-quality predicates without changing the raw-source contract.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded backend contract change with direct unit-test proof; no delegation required.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: task-local tests and final backend verification provide independent proof.

**Specification Coverage:**
- Complete canonical skill projections.
- Preserve technical phrases containing non-skill marker words.
- Separate partial structured signal from mandatory-channel completeness.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/enrich.py:_is_allowed_skill_entity`, `_is_reusable_skill_alias`, `_build_skill_entities`, `_semantic_skill_values`, `_apply_job_semantic_snapshot`, `_repair_required_skill_signal`, `parse_extraction_response`, `merge_scraped_and_enriched`
- Verify: `tests/test_enrich.py`
- Preserve downstream readers in: `src/fitcv/rule_filter.py`, `src/fitcv/evidence.py`, `src/fitcv/vector_search.py`, `src/fitcv/ai_score.py`

**Dependencies:**
- Start from implementation base `02d876afd88b4e4d9f40dfaa46891bb55d2548fd` and record any source/test path that differs from the superseded review evidence.
- Preserve existing raw skill ordering, deduplication, synonym canonicalization, and entity provenance behavior unless a regression test proves the current behavior loses information.

**Authority:**
- Preauthorized local actions: edit `src/fitcv/enrich.py` and `tests/test_enrich.py`; run `uv run pytest -q tests/test_enrich.py` and `uv run python -m compileall -q src`
- Stop for: a required schema change, a new extraction-provider contract, or a change to ranking policy weights

**Steps:**
- [x] Step 1: First add/execute a base-commit regression for mixed raw/entity inputs such as `GCP`, `Python`, and `SQL`. If the base already preserves all accepted raw requirements, retain the regression as a guard and do not rewrite canonical construction.
- [x] Step 2: Add failing technical-collision tests for `Natural Language Processing`, `Large Language Models`, language modeling, and a technical communication protocol; retain existing soft-skill and natural-language requirement rejection tests.
- [x] Step 3: Only if Step 1 fails, change canonical construction to merge entity-derived values with canonicalized accepted raw values, retaining provenance for values without an explicit LLM entity.
- [x] Step 4: Replace unrestricted marker substring rejection with exact or boundary/context-aware non-skill matching.
- [x] Step 5: Make completeness metadata channel-specific so one extracted field cannot claim verified mandatory coverage; preserve unresolved raw description/source evidence for later stages.
- [x] Step 6: Run the focused suite and inspect the semantic snapshot fixtures for stable field names and deterministic ordering.

**Verification:**
- [ ] `uv run pytest -q tests/test_enrich.py`
- Expected: existing enrichment tests pass; mixed raw/entity and technical-collision regressions pass; partial structured signal is not reported as mandatory completeness.
- [ ] `uv run python -m compileall -q src`
- Expected: no syntax or import compilation failures.

**Exit Criteria:**
- Every accepted raw technical skill remains visible in canonical requirements, technical marker collisions are preserved, and enrichment quality metadata no longer overclaims completeness.

### Task 2: Make candidate retrieval coverage and cutoff fusion relevance-aware

**Purpose:**
- Prevent relevant jobs from being omitted before compatibility scoring because candidate query inputs are selected by source order or because vector and lexical fallback scores compete on incompatible scales.

**Task Function:**
- Repair bounded query construction and retrieval cutoff ordering while preserving configured top-N limits and existing cache contracts.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared retrieval behavior crosses candidate projection, vector search, and ranking neutral-score helpers; sequential ownership avoids conflicting cutoff changes.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: retrieval regression suite plus pipeline admission proof.

**Specification Coverage:**
- Preserve late demonstrated skills and project evidence within bounded candidate queries.
- Calibrate vector/lexical fallback before applying a common shortlist cutoff.
- Do not treat unknown neutral relevance as affirmative rescue evidence.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/candidate.py:flatten_rankable_skills`, `src/fitcv/vector_search.py:build_candidate_query_components`, `_lexical_search_result`, `_hybrid_search_result`, `run_vector_search`, and cache/fusion helpers
- Inspect and modify: `src/fitcv/ranking.py:compute_title_relevance`, `_preference_dimension_score`
- Verify: `tests/test_candidate.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`

**Dependencies:**
- Task 1 must pass so retrieval consumes complete canonical skill projections.
- Keep `pipeline.vector_search_top_n` and `pipeline.ai_score_top_n` unchanged unless a separate approved policy changes those limits.

**Authority:**
- Preauthorized local actions: edit the listed retrieval/ranking sources and focused tests; run `uv run pytest -q tests/test_candidate.py tests/test_vector_search.py tests/test_ranking.py`
- Stop for: changing top-N policy, changing embedding model/cache schema, or introducing a new external retrieval dependency

**Steps:**
- [x] Step 1: Add a vector-path regression where a decisive skill appears after the current bounded skill prefix and must still reach the candidate query.
- [x] Step 2: Add a project-hint regression proving a relevant later project is not excluded solely by alphabetical project-name order.
- [x] Step 3: Define and test deterministic precedence for bounded selection: mandatory/required skills first, then demonstrated support, distinctiveness, recency, target-role alignment, and project evidence; allocate slots per category, define missing-date ordering, and use stable lexical/ID tie-breaks.
- [x] Step 4: Add a partial-embedding regression with vector and lexical candidates whose raw scores are on different scales; assert the cutoff uses calibrated or rank-fused ordering.
- [x] Step 5: Add a regression using the real neutral `0.5` title relevance value; assert a neutral lexical row cannot qualify as affirmative rescue or evict a stronger cutoff row.
- [x] Step 6: Preserve retrieval diagnostics showing which skills/projects were selected and why, so future recall regressions can be traced without inferring from final ranks.

**Verification:**
- [ ] `uv run pytest -q tests/test_candidate.py tests/test_vector_search.py tests/test_ranking.py`
- Expected: existing retrieval behavior remains stable except for validated false-negative cases; late-skill, late-project, score-fusion, and neutral-rescue regressions pass.
- [ ] `uv run pytest -q tests/test_pipeline.py -k "shortlist or ranking or retrieval"`
- Expected: the representative pipeline path admits the expected job set at the configured cutoff.

**Exit Criteria:**
- Bounded candidate queries retain representative relevant signals, mixed retrieval uses a common ordering contract, and neutral values cannot promote unsupported rescue rows.

### Task 3: Preserve selected evidence and rare-skill recoverability

**Purpose:**
- Ensure evidence selected for compatibility scoring retains the enriched facts that caused selection and that channel truncation cannot permanently remove the only proof of a distinct required skill.

**Task Function:**
- Keep retrieval/search context and scorer-visible context distinct, preserve the handoff into `build_ranking_job_input`, and enforce required-skill coverage before final evidence truncation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: evidence ownership is centralized in `evidence.py`; the change can be proven with deterministic item-level tests.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused evidence tests and scorer handoff assertions.

**Specification Coverage:**
- Preserve source text and `scoring_context` through ranking evidence selection.
- Reserve or recover evidence per distinct required skill before channel caps make it unreachable.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/evidence.py:project_candidate_evidence`, `select_ranking_evidence`, `retrieve_evidence_bundle`, `build_evidence_excerpt`, `_select_channel_candidates`, `_merge_channel_pools`, `_recover_verified_supporters`; `src/fitcv/agentic_cv_analysis.py` for the CV-analysis handoff; `src/fitcv/ai_score.py:build_ranking_job_input` for scorer-visible context.
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_ai_score.py`

**Dependencies:**
- Task 1 must pass so required-skill descriptors use complete canonical requirements.
- Preserve existing evidence IDs, source references, attribution metadata, and selection quotas.

**Authority:**
- Preauthorized local actions: edit `src/fitcv/evidence.py` and focused evidence/scorer tests; run `uv run pytest -q tests/test_evidence.py tests/test_ai_score.py`
- Stop for: changing evidence-source ranking policy without a fixture proving the new order, or deleting source attribution fields

**Steps:**
- [x] Step 1: Add a regression where an item is selected because `scoring_context` contains the decisive technology, while `text` is generic; assert both remain available to the scorer.
- [x] Step 2: Add a saturated-channel regression where the only proof for a rare required skill ranks below broad matches; assert the rare supporter survives or is recovered from the complete annotated pool.
- [x] Step 3: Trace `retrieve_evidence_bundle -> agentic_cv_analysis -> select_ranking_evidence -> build_ranking_job_input`; separate scorer excerpt from retrieval search text so context used to select an item is not discarded at either handoff.
- [x] Step 4: Reserve one candidate or recovery path per distinct required skill before final channel truncation, while keeping the global evidence budget bounded.
- [x] Step 5: Assert selected evidence retains stable IDs, source references, support diagnostics, and matched-term rationale.

**Verification:**
- [ ] `uv run pytest -q tests/test_evidence.py tests/test_ai_score.py`
- Expected: context-preservation and rare-skill recovery regressions pass without changing evidence attribution or ID stability.
- [ ] Inspect scorer-input fixtures and assert the selected evidence contains the technology terms that caused its selection.

**Exit Criteria:**
- Selected evidence is both attributable and semantically complete enough for scoring, and rare required-skill proof remains recoverable after channel pooling.

### Task 4: Enforce scorer budget ownership and exact visibility diagnostics

**Purpose:**
- Prevent successful scoring requests from silently losing all selected evidence, misclassifying optional candidate overflow as mandatory-skill overflow, or recording diagnostics that do not describe the actual bounded prompt.

**Task Function:**
- Make request budgeting preserve mandatory facts and attributable evidence, then derive all visibility metadata from the final rendered payload.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded scorer-input contract with direct serialization and prompt assertions; no external dependency required.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused scorer tests plus pipeline boundary verification.

**Specification Coverage:**
- Do not reduce selected project evidence to zero while treating the score as evidence-complete.
- Attribute candidate overflow to the field that caused it and compact optional fields before rejecting a mandatory subset.
- Persist diagnostics derived from the exact bounded job/candidate/evidence payload.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-code-standards`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/ai_score.py:build_ranking_request`, `build_ranking_input_diagnostics`, `build_ranking_job_input`, `prioritize_records`, and candidate-summary budget helpers
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage` for the evidence-to-score boundary
- Verify and add: `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py` (this file is absent at the implementation base and must be created by this task)

**Dependencies:**
- Task 3 must pass so the budgeter receives distinguishable source text, scoring context, and evidence attribution.
- Preserve `RANKING_REQUEST_MAX_CHARS == 12_000` and existing mandatory-fact ordering unless a test proves the current order drops a required fact.

**Authority:**
- Preauthorized local actions: edit `src/fitcv/ai_score.py`, `src/fitcv/pipeline_stage_runner.py` only when required by the handoff contract, and the named tests; run the focused scorer suite
- Stop for: changing the LLM provider, request budget, holistic ranking weights, or degraded-enrichment policy

**Steps:**
- [x] Step 1: Adopt one explicit contract: when no attributable evidence fits, return `score_status="unscored"`, `score_state="evidence_limited"`, `failure_code="evidence_limited"`, `evidence_limited=true`, and no normal compatibility score; `execute_ranking_stage` preserves that state and existing ranking normalization excludes it from ordinary compatibility ordering. Add a boundary regression for the zero-evidence case.
- [x] Step 2: Add a long-employment/language-history regression with one mandatory candidate skill; assert optional fields are compacted, records matching mandatory requirements are retained, and mandatory-skill overflow is raised only when the mandatory subset itself exceeds its budget.
- [x] Step 3: Build `bounded_ranking_input` from the exact selected job, selected candidate, and final evidence representations used for prompt rendering; do not couple completeness diagnostics to `enrichment_degraded` unless a separate policy is approved.
- [x] Step 4: Derive visible skill counts, evidence counts, omission reasons, and mandatory-core diagnostics from the bounded payload rather than the original source input; preserve the existing `enrichment_degraded` semantics unchanged.
- [x] Step 5: Add assertions that serialized prompt content and persisted visibility diagnostics agree field-for-field on the final bounded payload.

**Verification:**
- [ ] `uv run pytest -q tests/test_ai_score.py tests/test_scoring_input_integrity.py`
- Expected: evidence-floor, field-owned overflow, and exact-diagnostics regressions pass; existing request-budget tests remain green.
- [ ] `uv run pytest -q tests/test_pipeline.py -k "ranking or score"`
- Expected: representative ranking-stage execution preserves final score-state and visibility metadata.

**Exit Criteria:**
- A successful scorer request cannot silently omit all selected attributable evidence, overflow diagnostics identify the responsible field, and persisted visibility equals the actual prompt payload.

### Task 5: Prove the integrated admission-to-scoring contract and align documentation

**Purpose:**
- Demonstrate that the corrected contracts work together at the pipeline boundaries and document the invariants so future changes do not reintroduce information loss.

**Task Function:**
- Run representative backend traces, reconcile cross-stage artifacts, and update maintained pipeline documentation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final integration and verification task; requires source/test reconciliation rather than new implementation design.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: final verification command set and artifact inspection.

**Specification Coverage:**
- Preserve facts from enrichment through rule filtering, retrieval, evidence selection, prompt construction, scoring, and ranking.
- Record explicit non-goals and deferred policy decisions.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`
- `skill-code-standards`

**Files And Symbols:**
- Inspect and verify: `src/fitcv/pipeline_stage_runner.py:execute_rule_filter_stage`, `execute_shortlist_stage`, `execute_ranking_stage`
- Verify: `tests/test_pipeline.py`, `tests/test_vector_search.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_ranking.py`
- Modify documentation: `docs/FitCV-pipeline.md`, `docs/pipeline.md`

**Dependencies:**
- Tasks 1–4 complete with focused suites passing.
- Preserve unrelated current worktree changes and do not regenerate unrelated artifacts.

**Authority:**
- Preauthorized local actions: run the integrated local test and compile/diff checks; update the two named pipeline documents; inspect generated outputs without publishing
- Stop for: a failing unrelated suite, a changed stage contract requiring migration, or any request to publish/commit/push

**Steps:**
- [x] Step 1: Add or update a deterministic fixture covering a job with mixed canonical/raw skills, a late candidate/project signal, rich scoring context, and a bounded scorer request.
- [x] Step 2: Trace the fixture through rule filtering, vector/lexical retrieval, shortlist materialization, evidence selection, ranking-input construction, and final score-state normalization.
- [x] Step 3: Assert the required skills that caused admission remain present in the scorer-visible job payload and the strongest selected evidence remains attributable.
- [x] Step 4: Document the canonical-skill completeness invariant, retrieval fusion/neutral-baseline invariant, evidence-preservation invariant, and exact-diagnostics invariant.
- [x] Step 5: Record the deferred degraded-enrichment and optional-hard-filter policy decisions as explicit follow-up scope rather than silently changing them.

**Verification:**
- [ ] `uv run pytest -q tests/test_enrich.py tests/test_candidate.py tests/test_rule_filter.py tests/test_vector_search.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_pipeline.py tests/test_scoring_input_integrity.py`
- Expected: all focused pipeline integrity suites pass.
- [ ] `uv run python -m compileall -q src`
- Expected: no compilation failures.
- [ ] `git diff --check`
- Expected: no whitespace errors.
- [ ] Inspect the final diff and confirm no unrelated current-workspace files were modified.

**Exit Criteria:**
- The integrated fixture proves no validated information-loss path remains in the planned scope, documentation matches the implementation, and final verification is fresh and reproducible.

## Verification

- `uv run pytest -q tests/test_enrich.py tests/test_candidate.py tests/test_rule_filter.py tests/test_vector_search.py tests/test_evidence.py tests/test_ai_score.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_pipeline.py tests/test_scoring_input_integrity.py`
- `uv run python -m compileall -q src`
- `git diff --check`
- Inspect the final scorer visibility manifest and ranking score-state for the integrated fixture; confirm selected skills, evidence IDs, source references, omission reasons, and final bounded payload agree.
- Confirm the current worktree's pre-existing changes remain outside the implementation diff.

## Completion Criteria

The plan is ready for completion verification when:

1. Tasks 1–5 are implemented in order and each task-local regression suite is green.
2. Complete canonical skill projections and technical collision cases are proven.
3. Retrieval query coverage, score fusion, and neutral rescue behavior are proven at the configured shortlist cutoff.
4. Selected evidence and rare required-skill supporters remain available to the scorer.
5. Scorer budgeting, overflow ownership, and visibility diagnostics describe the exact final prompt payload.
6. The integrated pipeline fixture proves admitted jobs retain the required facts and strongest attributable evidence through final scoring.
7. Documentation and tests are reconciled with the changed contracts, and no deferred policy decision is implemented implicitly.
8. Fresh verification output is recorded before any commit, push, merge, or branch-finishing action.
