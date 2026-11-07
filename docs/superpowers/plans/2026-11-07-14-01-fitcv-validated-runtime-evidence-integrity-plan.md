---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: proposed
name: fitcv-validated-runtime-evidence-integrity
targets:
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/vector_search.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - tests/test_candidate.py
  - tests/test_evidence.py
  - tests/test_vector_search.py
  - tests/test_ai_score.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_agentic_cv_generation.py
  - tests/test_pipeline.py
  - docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md
---

# FitCV Validated Runtime Evidence Integrity

## Goal

Restore a single evidence-integrity policy from candidate-profile ingestion through runtime convergence, retrieval, evidence selection, CV gap analysis, and compatibility scoring. The implementation must prevent unsupported claims, negative prose, and non-rankable project material from becoming positive ranking evidence while preserving valid legacy and canonical-v2 evidence.

The review basis is the public, commit-pinned revision `4d15a0e6eb05064c65afa4b1fe60d9667c289f37` of `longdang193/fitcv`. The dedicated-profile TCP-CDP review completed for both requested models at `High`: GPT-5.6-Sol supplied the initial findings and GPT-6 supplied the exact pinned `Review Skill Evidence Ranking` response. Only findings confirmed against the pinned source are included below.

## Implementation Outcomes

### Support status survives every runtime projection

Legacy parent and bullet support states remain attached during v2 adaptation and runtime convergence. CV capability matching, evidence projection, retrieval, and scoring admit only evidence-backed rankable claims, while raw compatibility projections retain their documented legacy behavior.

### Canonical-v2 claims require admissible proof

Canonical-v2 validation rejects missing or unknown support states, dangling evidence references, and supported claims without at least one valid evidence reference. Runtime rankability uses an explicit admissible-status policy rather than treating missing or unknown values as supported.

### Retrieval and evidence polarity are truthful

Negated source prose cannot become affirmative evidence merely because structured skill or technology tags repeat the negated term. Non-rankable projects and project evidence are excluded from positive retrieval components, query text, and signatures; supported project evidence remains bounded and deterministic.

### Scoring receives bounded, attributable evidence

Nested source locators and provenance metadata are bounded independently from evidence text, and final scoring diagnostics describe the exact model-visible payload. Evidence required for compatibility scoring remains attributable and joinable to canonical evidence IDs.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`
- Isolation: `optional worktree from origin/main`; preserve the dirty canonical checkout and unrelated user changes
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit the named source, test, and specification files; create the focused regression tests; run the declared pytest commands; inspect Git history and the pinned commit
- User-approval actions: push, merge, publication, destructive cleanup, reset, discard, or changes outside the named targets
- Parallel ownership: `none`
- Sequential fallback: complete Tasks 1–5 in order because each later task consumes the shared support-status and evidence-projection contracts

## Task Breakdown

### Task 1: Preserve support status through legacy convergence and CV capability matching

**Purpose:**
- Keep legacy parent and bullet `support_status` semantics intact when `_adapt_legacy_parent` and `adapt_candidate_profile_to_v2` create evidence and derived claims, and stop CV gap analysis from counting claimed-only or unsupported skills as demonstrated capabilities.

**Task Function:**
- Trace and repair status propagation from legacy profile input through runtime convergence, evidence projection, candidate-skill extraction, requirement coverage, and generation review gating.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: bounded multi-module backend correctness work with known symbols and explicit regression paths; no delegated profile is required.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: task-local focused tests and direct boundary verification are sufficient.

**Specification Coverage:**
- Legacy compatibility remains supported without converting claimed-only or unsupported parent/bullet material into supported ranking evidence.
- CV generation review decisions use evidence-backed requirement coverage rather than the unrestricted declared-skill projection.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/candidate.py:_adapt_legacy_parent`, `adapt_candidate_profile_to_v2`, `converge_candidate_profile_for_runtime`, `flatten_rankable_skills`
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`
- Modify: `src/fitcv/candidate.py:_adapt_legacy_parent`, `adapt_candidate_profile_to_v2`
- Modify: `src/fitcv/agentic_cv_analysis.py:_candidate_skill_names`
- Modify: `src/fitcv/agentic_cv_generation.py:check_cv_acceptance_policy` and its requirement-coverage callers
- Verify: `tests/test_candidate.py`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_agentic_cv_generation.py`, `tests/test_pipeline.py`

**Dependencies:**
- Pinned-source evidence at `candidate.py:340-563`, `candidate.py:653-724`, `evidence.py:1374-1391`, and `agentic_cv_analysis.py:1292-1300`.
- Preserve existing `flatten_skills` compatibility callers unless the caller is explicitly a rankability or evidence-admission boundary.

**Authority:**
- Preauthorized local actions: change only the named status-propagation and CV matching symbols and add focused tests in the listed test files.
- Stop for: a required behavior change to the public candidate schema beyond the listed support-status and evidence-reference contract.

**Steps:**
- [ ] Step 1: Add fixtures for a legacy project and experience bullet marked `claimed_only` or `unsupported`, plus a supported sibling claim with distinct evidence IDs.
- [ ] Step 2: Preserve parent/bullet status during adaptation and prevent non-rankable parents or fragments from creating supported derived claims or rankable evidence links.
- [ ] Step 3: Change `_candidate_skill_names` and generation review gating to use rankable skills and authoritative requirement coverage without weakening legacy fallback behavior.
- [ ] Step 4: Add an end-to-end regression from legacy profile input through runtime convergence, evidence projection, evidence selection, CV gap analysis, and ranking/generation inputs.

**Verification:**
- [ ] `python -m pytest tests/test_candidate.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_agentic_cv_generation.py tests/test_pipeline.py -q`
- Expected: claimed-only and unsupported skills never appear as demonstrated CV capabilities or supported ranking evidence; supported claims still reach evidence selection and scoring.
- [ ] Direct assertion over the converged profile, projected evidence, `candidate_skills`, `requirement_coverage`, `do_not_claim`, and generated review flags.
- Expected: the final state is status-consistent and the unsupported-requirement review is not skipped merely because an unrestricted declared-skill list matched.

**Exit Criteria:**
- Legacy support states survive convergence, non-rankable claims are excluded from positive runtime evidence, and focused tests prove both supported and rejected paths.

### Task 2: Enforce canonical-v2 claim admission and explicit rankability

**Purpose:**
- Close the canonical-v2 contract gap that currently permits missing or unknown support statuses and supported claims with empty evidence references to enter retrieval and scorer inputs.

**Task Function:**
- Align validation, runtime convergence, rankability, and scorer-input construction around one explicit canonical-v2 admissibility rule while keeping legacy profiles separately compatible.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: contract-focused backend validation with low ambiguity and high correctness impact.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: validator behavior is fully expressible through deterministic unit and boundary tests.

**Specification Coverage:**
- `support_status` is an explicit enum for canonical-v2 derived claims.
- Supported claims have valid, nonempty, non-dangling `evidence_refs` before they are rankable.
- Unknown and missing statuses cannot default to positive ranking admission.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/candidate.py:validate_candidate_profile`, `converge_candidate_profile_for_runtime`, `_is_rankable_support_status`, `flatten_rankable_skills`
- Inspect: `src/fitcv/ai_score.py:build_ranking_job_input`
- Inspect: `src/fitcv/pipeline.py` rankable candidate-skill assembly and `src/fitcv/pipeline_stage_runner.py` scoring-input selection
- Modify: `src/fitcv/candidate.py` canonical-v2 validation and rankability helpers
- Modify: `src/fitcv/ai_score.py:build_ranking_job_input` only where admission must be enforced at the scorer boundary
- Verify: `tests/test_candidate.py`, `tests/test_ai_score.py`, `tests/test_pipeline.py`
- Reconcile if required: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`

**Dependencies:**
- Task 1 establishes the status-preserving runtime projection and must complete first.
- The canonical field registry already marks `support_status` as required; use that existing contract owner instead of introducing a second schema source.

**Authority:**
- Preauthorized local actions: update the canonical-v2 validator, shared admission predicate, scorer boundary, and their focused tests; update the named spec only if its maintained contract text is directly stale.
- Stop for: a request to change legacy profile acceptance or to introduce a second support-status registry.

**Steps:**
- [ ] Step 1: Define the canonical-v2 admissible statuses and the supported-claim evidence-reference invariant in the existing candidate contract owner.
- [ ] Step 2: Reject missing, unknown, empty, and dangling claim metadata with field-specific validation errors; preserve the separate legacy adaptation path.
- [ ] Step 3: Make `_is_rankable_support_status` use an explicit allowlist or validated enum result so unknown values cannot become supported by default.
- [ ] Step 4: Add validator and scorer-input regressions for missing status, unknown status, empty refs, dangling refs, supported-without-evidence, and valid supported evidence.

**Verification:**
- [ ] `python -m pytest tests/test_candidate.py tests/test_ai_score.py tests/test_pipeline.py -q`
- Expected: invalid canonical-v2 claims fail validation or are excluded before retrieval/scoring; valid supported claims with real refs remain visible.
- [ ] Direct assertion that an unrelated attributable evidence item cannot make a proof-less skill appear in `all_candidate_skills` or scorer payloads.

**Exit Criteria:**
- Canonical-v2 validation and runtime admission agree, with no missing/unknown/default-supported escape path and no regression to legacy compatibility.

### Task 3: Separate evidence polarity from structured tags

**Purpose:**
- Prevent negated source prose from becoming affirmative evidence when a structured `skills` or `tech_stack` tag repeats the same term.

**Task Function:**
- Repair evidence search text and polarity evaluation so source text, scoring context, and structured metadata are evaluated as distinct channels with explicit provenance.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: narrow deterministic evidence-scoring change with clear positive and negative examples.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused polarity regressions cover the material success and failure paths.

**Specification Coverage:**
- Negative source evidence remains unsupported unless a separately validated positive claim-to-evidence link exists.
- Positive source prose with a matching skill tag continues to score as supported.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_evidence_search_text`, `score_evidence_item_by_channel`, `_is_negated_term`
- Modify: `src/fitcv/evidence.py` polarity and channel-scoring helpers
- Verify: `tests/test_evidence.py` existing polarity regressions around lines 2770-2779 and new structured-tag cases

**Dependencies:**
- Task 1 and Task 2 define the support-state and evidence-link semantics consumed by evidence scoring.
- Keep the existing qualifier and negation vocabulary as the single polarity source.

**Authority:**
- Preauthorized local actions: adjust evidence-channel construction and polarity evaluation in the named symbols and add focused evidence tests.
- Stop for: a proposed change that treats structured tags as independent proof without a validated canonical evidence reference.

**Steps:**
- [ ] Step 1: Reproduce `text="No Python experience was required for the role."` with `skills=["Python"]` and capture the current positive coverage.
- [ ] Step 2: Separate source/scoring prose used for polarity from structured tags used only as metadata or bounded search hints.
- [ ] Step 3: Preserve positive prose behavior and require an independently validated positive linkage before tags can add support.
- [ ] Step 4: Add negative, positive, mixed-channel, and multi-occurrence regressions.

**Verification:**
- [ ] `python -m pytest tests/test_evidence.py -q`
- Expected: the negated Python example remains unsupported; affirmative Python prose remains supported; structured tags do not override negative prose.

**Exit Criteria:**
- Evidence polarity is deterministic, provenance-aware, and covered by both negative and positive regression tests.

### Task 4: Filter negative and non-rankable technology/project material from retrieval

**Purpose:**
- Stop claimed-only, rejected, unsupported, and negated project technology from contributing positive technology overlap, lexical fallback admission, vector query text, or candidate-query signatures.

**Task Function:**
- Harden the technology inventory and project evidence-hint harvest while preserving supported project evidence, stable ordering, and existing query bounds.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: bounded retrieval-policy correction with deterministic query-component outputs.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: component-level and retrieval-level tests provide direct proof.

**Specification Coverage:**
- Positive retrieval uses only admissible, affirmative technology evidence.
- Excluded project text remains available for audit but is absent from positive embedding components, rendered query text, and signatures.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/vector_search.py:_profile_technology_inventory`, `_technology_overlap`, `_has_affirmative_lexical_relevance`, `build_candidate_query_components`, `build_candidate_query_signature_record`
- Modify: `src/fitcv/vector_search.py` technology admission and project-evidence-hint harvesting
- Verify: `tests/test_vector_search.py` query-component tests around lines 116-187 and retrieval/fallback tests

**Dependencies:**
- Tasks 1–3 establish support-state and polarity semantics.
- Existing bounded counts and deterministic ordering remain unchanged unless a test demonstrates that the current bound hides supported evidence.

**Authority:**
- Preauthorized local actions: modify only the named retrieval helpers and add deterministic vector-search regressions.
- Stop for: changing embedding models, retrieval cutoffs, or score calibration outside the support/polarity admission defect.

**Steps:**
- [ ] Step 1: Add a claimed-only project with `name`, `business_value`, and highlights that would otherwise enter `project_evidence_hints`.
- [ ] Step 2: Add a supported project with `text="No Kubernetes experience"` and verify current technology overlap and lexical admission.
- [ ] Step 3: Apply the shared rankability and polarity gates before technology inventory and project-hint harvesting.
- [ ] Step 4: Assert excluded values are absent from components, rendered query text, and signature while supported affirmative values remain present and ordered.

**Verification:**
- [ ] `python -m pytest tests/test_vector_search.py -q`
- Expected: non-rankable and negated values do not produce technology overlap or affirmative lexical relevance; supported affirmative values remain in bounded components and signatures.
- [ ] Direct comparison of query component payload, rendered query text, and query signature for excluded versus supported inputs.

**Exit Criteria:**
- Retrieval admission and candidate-query construction share the same support/polarity policy without score-scale or bound regressions.

### Task 5: Bound provenance independently and make scorer visibility truthful

**Purpose:**
- Ensure oversized nested source locators cannot crowd out valid evidence text, and ensure persisted visibility diagnostics describe the exact bounded payload sent to the compatibility scorer.

**Task Function:**
- Harden ranking-input serialization and diagnostics at the request boundary while preserving attributable evidence IDs, stable locator identifiers, and the existing evidence safety gate.

**Template Profile:**
- Controller-selected: `<none (lead controller)>`
- Selection basis: request-boundary correctness with explicit size, attribution, and failure-state assertions.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: direct request construction tests and backend boundary tests are sufficient.

**Specification Coverage:**
- Provenance metadata has its own bounded budget and schema validation.
- The final model-visible payload is the source of visibility counts and omission diagnostics.
- At least one attributable evidence item remains required for scoring; budget failure is explicit when the mandatory contract cannot fit.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:_bounded_source_refs`, `build_ranking_job_input`, request-budget attempt construction, and `build_ranking_input_diagnostics`
- Inspect: `src/fitcv/candidate.py:validate_candidate_profile` source-reference locator validation
- Inspect: `src/fitcv/pipeline_stage_runner.py` evidence selection and visibility handoff
- Modify: `src/fitcv/ai_score.py` provenance bounding, final-payload diagnostics, and explicit budget failure metadata
- Modify if required: `src/fitcv/candidate.py` locator schema/size validation
- Verify: `tests/test_ai_score.py`, `tests/test_candidate.py`, `tests/test_pipeline.py`

**Dependencies:**
- Tasks 1–4 establish which evidence is admissible before serialization.
- Preserve canonical evidence IDs, `kind`, parent attribution, and stable document/block locator fields while trimming optional metadata.

**Authority:**
- Preauthorized local actions: change only ranking-input serialization/diagnostics, locator validation, and the listed regression tests.
- Stop for: any relaxation of the selected-attributable-evidence gate or any change that silently substitutes raw pre-budget input for the final model payload.

**Steps:**
- [ ] Step 1: Reproduce a short attributable evidence item with an oversized additional locator string and record the current `budget_exceeded` result.
- [ ] Step 2: Restrict locator fields to the canonical kinds and bound nested scalar values plus serialized provenance size independently from evidence text.
- [ ] Step 3: Build `model_visible_ranking_input` from the selected final job, candidate, and evidence values and derive visibility counters from it; retain raw input under a distinct provenance field.
- [ ] Step 4: Add regressions for trimmed locators, preserved IDs, visible evidence counts, omission diagnostics, and explicit mandatory-contract failure.

**Verification:**
- [ ] `python -m pytest tests/test_ai_score.py tests/test_candidate.py tests/test_pipeline.py -q`
- Expected: short relevant evidence still reaches the scorer despite oversized optional locator data; diagnostics match serialized prompt content exactly; unsupported/no-attribution cases remain blocked.

**Exit Criteria:**
- Provenance cannot exhaust the request budget invisibly, and persisted scoring diagnostics are faithful to the final model-visible payload.

## Verification

- `python -m pytest tests/test_candidate.py tests/test_evidence.py tests/test_vector_search.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_agentic_cv_generation.py tests/test_pipeline.py -q`
- `python -m pytest -q`
- Inspect the final diff with `git diff --check` and confirm only the named source, test, and directly affected specification files changed.
- Run a representative backend trace covering legacy and canonical-v2 profile input, runtime convergence, evidence projection/selection, vector shortlist construction, scorer request serialization, CV requirement coverage, and final ranking/generation disposition.

## Completion Criteria

The plan is ready for completion verification when:

1. legacy and canonical-v2 support states are preserved and enforced at every ranking/evidence boundary
2. negated prose and non-rankable project material cannot create positive retrieval or scoring evidence
3. candidate query components and signatures contain supported affirmative evidence only, within existing bounds
4. scorer requests retain attributable evidence and bounded provenance, and diagnostics describe the exact model-visible payload
5. focused regressions and the full repository test suite pass with fresh output
6. any maintained specification changes are reconciled with the implemented contract and no unrelated workspace changes are included
7. deviations, blocked checks, and deferred findings are recorded before handoff to `skill-executing-plans`

