---
layer: change
artifact_type: plan
contract_version: "1"
status: proposed
template_id: implementation-plan
name: fitcv-validated-scoring-input-and-retrieval-integrity
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv/evidence.py
  - src/fitcv/vector_search.py
  - src/fitcv/normalize.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/ranking.py
  - src/fitcv_cp/candidate_profile_service.py
  - tests/test_ai_score.py
  - tests/test_enrich.py
  - tests/test_evidence.py
  - tests/test_vector_search.py
  - tests/test_normalize.py
  - tests/test_ranking.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_artifacts.py
  - tests/test_fitcv_cp/test_candidate_profile_service.py
---

# FitCV Validated Scoring-Input And Retrieval-Integrity Plan

## Goal

Make the information entering FitCV's holistic compatibility scorer bounded,
truthful, auditable, and materially representative of the canonical candidate
and job evidence. Preserve the current ranking policy and budgets while fixing
lossy enrichment, retrieval, evidence-selection, prompt-construction, cache-
reuse, and diagnostic boundaries that can bias which jobs are scored or hide
material evidence from the score-producing component.

Review basis: `longdang193/fitcv` `main` at
`db1ca88a81aaaea6b7c07eead1c50f312edc90f3`, independently reviewed in one
authenticated context by `GPT-5.6-Sol/High` and `GPT-6/High`. Both reviews
completed with pinned-SHA evidence and no repository modifications. The
attached verdict was used as input, but only source-confirmed findings are
included below.

## Validated Findings

### Confirmed and included

- `config/policy/ranking.yaml` makes `holistic_ai_only` authoritative with
  `holistic_ai_fit: 1.0` and `structured_fit: 0.0`; omitted scorer input cannot
  be recovered by structured factors.
- `src/fitcv/ai_score.py` bounds candidate facts and job requirement channels
  by position, selects at most two evidence items, raw-slices the serialized
  job-requirement field, and can shed evidence, candidate facts, and job
  requirements until a request fits. The first raw slice is not fully reported
  by truncation diagnostics.
- Evidence diagnostics can count from an already-shortened projected pool, and
  reused-score diagnostics do not restore the final request's visibility or
  truncation record.
- `src/fitcv/enrich.py` can promote `tech_stack` or keywords into required
  skills when extracted requirements are empty or sparse. Language aggregation
  keeps the strongest level/type for one language, so a required B2 plus
  preferred C1 can become required C1.
- `src/fitcv_cp/candidate_profile_service.py` validates source references but
  does not require every substantive source block to be represented or
  explicitly dispositioned before downstream projection.
- `src/fitcv/pipeline_stage_runner.py` always passes the vector strategy even
  when configuration selects lexical retrieval. Retrieval and `ai_score_top_n`
  are irreversible admission gates for holistic scoring.
- `src/fitcv/vector_search.py` can switch an entire retrieval run to lexical
  fallback when any required job vector is missing, invalid, or incompatible;
  valid vector results are not preserved as a mixed shortlist.
- `src/fitcv/evidence.py` selects by bounded channel terms and marginal score,
  so later requirements, negation, qualifiers, and long decisive passages can
  lose selection or excerpt visibility. The scorer rendering duplicates the
  excerpt and omits useful evidence provenance such as kind, section, dates,
  and source references.
- `src/fitcv/normalize.py` deduplicates blank URLs together and near-duplicates
  without location, so a viable location variant can be discarded by input
  order.
- `src/fitcv/ranking.py` excludes rows without valid holistic scores from the
  final ranked set; the failure state exists internally but is not represented
  as an explicit unscored result in the ranked output.
- Score reuse is exact for the bounded scorer request, not proof that the
  complete canonical profile is unchanged. A complete-profile change outside
  the bounded representation can leave the prior score reusable.

### Explicitly excluded from this plan

- The attached stale-cache claim that a newer incompatible vector is selected
  before a compatible one is not confirmed at this revision; current lookup
  filters input signatures and embedding contracts.
- The attached claim that semantic canonicalization necessarily merges several
  atomic skills into one sentence is not confirmed; the semantic snapshot
  stores per-entity raw and canonical values. Keep atomic-skill regression
  coverage, but do not redesign canonicalization without a failing fixture.
- Do not claim a production frequency, exact score change, employer decision,
  or specific candidate outcome from these static and synthetic findings.
- Do not change compatibility weights, thresholds, baseline mode, shortlist
  size, the eight-skill limit, the two-evidence limit, or Loose/Full/Strict
  semantics.
- Do not add a generic LLM reranker, new vector store, unbounded prompt, or
  destructive cache migration.
- User-facing presentation of unscored jobs is deferred if it requires a new
  API/export contract; this plan preserves explicit failure diagnostics and
  retry state without silently treating failure as incompatibility.

## Implementation Outcomes

### Fail-closed scorer-input contract

`build_ranking_job_input()` and `build_ranking_request()` share one versioned,
field-aware contract. Mandatory job requirements and critical candidate facts
survive bounded serialization; optional fields shed deterministically. JSON is
never character-sliced after serialization. If the mandatory core cannot fit,
scoring fails explicitly instead of producing an apparently valid score. The
final request records every omitted or truncated field and its reason.

### Truthful requirements and candidate source coverage

Required, preferred, technology-mentioned, and inferred requirement states stay
separate and retain source support. Language clauses retain their own level and
requirement type. Candidate baseline mapping reports every substantive source
block as represented, unresolved, or deliberately ignored with a reason; no
unaccounted factual block silently disappears before retrieval or scoring.

### Complementary, provenance-preserving evidence

The two-item evidence budget remains unchanged, but selection searches the full
available pool, prioritizes mandatory requirements and marginal coverage, keeps
negation/qualifiers with the selected span, and renders each excerpt once with
compact ID, kind, source section, dates/location, and source references.
Unsupported or merely inferred claims remain distinguishable from demonstrated
evidence.

### Stable retrieval and admission behavior

Configured retrieval strategy reaches the retrieval implementation. Missing or
invalid job vectors do not discard valid vector results for the whole batch;
fallback and regenerated rows merge under the existing shortlist budget with
effective-strategy diagnostics. Deduplication retains materially distinct
location/identity variants. Retrieval, shortlist, and AI-score admission
boundaries remain bounded and observable.

### Reusable visibility and failure diagnostics

Fresh and reused scores persist the same bounded visibility manifest: canonical
available IDs/counts, selected IDs/counts, rendered IDs/counts, model-visible
fields, omissions, truncation reasons, request fingerprint, and complete
canonical input checksums. Invalid/provider-failed scores retain explicit
failure/retry diagnostics and are never interpreted as a compatibility score.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve unrelated untracked artifacts
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared source/tests/docs, run declared
  local checks, and preserve unrelated workspace changes
- User-approval actions: commit, push, merge, destructive cache migration,
  deleting unrelated artifacts, or changing public/API/export contracts
- Parallel ownership: none; `ai_score.py`, `evidence.py`, retrieval, and
  diagnostics share contract versions and fingerprints
- Sequential fallback: execute Tasks 1–5 in order, then Task 6; do not split
  shared contract work into parallel writers

## Task Breakdown

### Task 1: Make the bounded scorer request fail closed

**Purpose:**
- Prevent request-size handling from deleting the core job/candidate evidence
  and still returning a normal holistic score.

**Task Function:**
- Implement the canonical scoring-input contract and its focused regression
  proof.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independently validate request shape, fail-closed behavior,
  and reuse fingerprints.

**Specification Coverage:**
- Fail-closed scorer-input contract; preserved `12_000` request cap;
  mandatory-core visibility; exact request diagnostics; unchanged score policy.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify `src/fitcv/ai_score.py:build_ranking_job_input`.
- Inspect/modify `src/fitcv/ai_score.py:build_ranking_request`.
- Inspect/modify `src/fitcv/ai_score.py:build_ranking_input_diagnostics`.
- Inspect/modify `src/fitcv/ai_score.py:build_ai_score_input_fingerprint` and
  the score-reuse path in `run_ai_scoring`.
- Verify `tests/test_ai_score.py`.

**Dependencies:**
- Review baseline at `db1ca88a81aaaea6b7c07eead1c50f312edc90f3`.
- Preserve the existing eight-skill, two-evidence, and 12,000-character
  budgets.

**Authority:**
- Preauthorized local actions: modify only the declared scorer symbols and
  focused tests; preserve parser, thresholds, and score status meanings.
- Stop for: a required API/export change, a weight/threshold change, or a
  request to discard unrelated workspace changes.

**Steps:**
- [ ] Step 1: Define a versioned structured projection with explicit mandatory
  and optional fields; keep complete canonical requirement/fact checksums
  outside the serialized prompt.
- [ ] Step 2: Apply per-field reductions before JSON serialization, preserve
  valid JSON, and fail with an explicit unsatisfied-budget status when the
  mandatory core cannot fit.
- [ ] Step 3: Record raw, selected, rendered, model-visible, omitted, and
  truncated field metadata in the request record and diagnostics.
- [ ] Step 4: Include the bounded request plus complete canonical input
  checksums in the reuse fingerprint; restore the exact visibility record on
  reuse.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py -k "ranking_job_input or ranking_request or diagnostics or fingerprint or reuse" --disable-warnings --maxfail=1`
- Expected: long job requirements remain valid JSON; mandatory requirements
  and critical candidate facts are present or scoring fails explicitly;
  diagnostics identify every dropped field; changed complete input invalidates
  reuse.
- [ ] Use the existing scoring stub seam to inspect the exact request passed to
  the scorer for an oversized JD, two evidence items, and late candidate facts.
- Expected: no raw character-sliced JSON and no normal score from an empty
  mandatory core.

**Exit Criteria:**
- Every ranking caller receives the same versioned bounded contract and no
  request can silently shed mandatory scoring context.

### Task 2: Preserve requirement semantics and candidate source coverage

**Purpose:**
- Stop enrichment from inventing hard requirements and stop baseline mapping
  from silently dropping substantive source blocks.

**Task Function:**
- Correct requirement-state aggregation and candidate-profile completeness
  validation with regression fixtures.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independently validate source support and level/type
  preservation.

**Specification Coverage:**
- Explicit versus inferred requirement states; per-clause language levels;
  atomic canonical skill identity; source-block completeness.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify `src/fitcv/enrich.py:_repair_required_skill_signal`.
- Inspect/modify `src/fitcv/enrich.py:_supplement_sparse_required_skills`.
- Inspect/modify `src/fitcv/enrich.py:_canonical_language_requirements`.
- Inspect/modify `src/fitcv_cp/candidate_profile_service.py:_validate_baseline_payload`.
- Inspect/modify `src/fitcv_cp/candidate_profile_service.py:build_baseline_review`.
- Verify `tests/test_enrich.py` and
  `tests/test_fitcv_cp/test_candidate_profile_service.py`.

**Dependencies:**
- Task 1 defines the scorer fields that consume requirement state and source
  coverage diagnostics.

**Authority:**
- Preauthorized local actions: modify only enrichment/profile-mapping symbols
  and their focused tests; retain source text and provenance.
- Stop for: a schema migration, deleting source evidence, or changing the
  meaning of an existing user-approved requirement type without a new spec.

**Steps:**
- [ ] Step 1: Preserve `explicit_required`, `preferred`, `technology_mentioned`,
  and `inferred` channels with source evidence; remove unconditional promotion
  of `tech_stack` and keywords to hard required skills.
- [ ] Step 2: Aggregate language facts without taking a stronger preferred
  level over a weaker required level; retain each source clause or an explicit
  per-clause relation so B2-required/C1-preferred cannot become C1-required.
- [ ] Step 3: Keep canonicalization atomic per extracted entity and preserve the
  original clause for qualifiers; add a regression for one clause containing
  Python and SQL.
- [ ] Step 4: Require every substantive source block to be represented,
  unresolved, or explicitly ignored with a reason; expose unresolved blocks as
  residual evidence rather than silently omitting them.

**Verification:**
- [ ] `python -m pytest -q tests/test_enrich.py tests/test_fitcv_cp/test_candidate_profile_service.py -k "required_skill or language or semantic_snapshot or source_block or baseline or mapping" --disable-warnings --maxfail=1`
- Expected: optional technology never becomes hard required without explicit
  source support; B2-required/C1-preferred remains separate; all substantive
  source blocks have a disposition; Python and SQL remain separate atomic
  values.
- [ ] Assert a malformed or incomplete mapping is rejected or returns an
  explicit unresolved-source diagnostic, not a silently shortened baseline.

**Exit Criteria:**
- Downstream retrieval and scoring consume requirement states and candidate
  facts whose provenance and completeness are explicit.

### Task 3: Make the two evidence slots complementary and attributable

**Purpose:**
- Preserve the existing two-item budget while preventing redundant, stale,
  unqualified, or provenance-free evidence from reaching the scorer.

**Task Function:**
- Implement requirement-aware evidence selection and one-pass scorer rendering.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independently validate marginal coverage, negation, and
  excerpt provenance.

**Specification Coverage:**
- Full-pool search before bounding; required-before-preferred priority;
  negation/qualifier preservation; single rendering; truthful support states.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify `src/fitcv/evidence.py:select_ranking_evidence`.
- Inspect/modify `src/fitcv/evidence.py:score_evidence_item_by_channel`.
- Inspect/modify `src/fitcv/evidence.py:build_evidence_excerpt`.
- Inspect/modify `src/fitcv/ai_score.py:build_ranking_job_input` and
  `evidence_text`.
- Inspect/modify `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`.
- Verify `tests/test_evidence.py` and `tests/test_ai_score.py`.

**Dependencies:**
- Task 2 provides explicit requirement states and candidate source coverage.
- Task 1 provides the bounded evidence/provenance fields and manifest.

**Authority:**
- Preauthorized local actions: modify evidence selection/rendering and focused
  tests; keep the two-item limit and existing evidence IDs.
- Stop for: increasing the evidence budget, inventing support, or changing
  Loose/Full/Strict semantics.

**Steps:**
- [ ] Step 1: Search all available requirement terms before applying the
  bounded channel representation; rank required terms ahead of preferred and
  contextual terms.
- [ ] Step 2: Select the first strong item, then select the item with the
  greatest marginal coverage of distinct important requirements; penalize
  redundant overlap.
- [ ] Step 3: Choose the relevant sentence/span before the 400-character bound
  and retain negation, qualifiers, duration, and scope with the match.
- [ ] Step 4: Render each item once with ID, kind, source section, dates/location,
  source references, and support state; do not label a merely valid evidence ID
  as demonstrated support without text-level reconciliation.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_ai_score.py -k "ranking_evidence or excerpt or negation or qualifier or provenance or evidence_text" --disable-warnings --maxfail=1`
- Expected: a ninth required skill can influence selection; a negated skill is
  not affirmative support; two overlapping snippets lose to two complementary
  snippets; the selected decisive span survives rendering; each excerpt is
  serialized once with provenance.
- [ ] Inspect a stub scorer request and assert selected evidence IDs match the
  visibility manifest exactly.

**Exit Criteria:**
- The scorer receives no more than two evidence items, but those items maximize
  distinct supported requirement coverage and retain enough context to interpret
  them correctly.

### Task 4: Restore configured retrieval behavior and shortlist recall

**Purpose:**
- Ensure configured retrieval strategy, vector fallback, technology coverage,
  and posting identity determine shortlist membership predictably.

**Task Function:**
- Correct retrieval orchestration and normalization while preserving the
  existing shortlist budget.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independently validate effective strategy, fallback merge,
  and location-variant retention.

**Specification Coverage:**
- Configured strategy propagation; mixed valid/fallback retrieval; bounded
  query coverage; exact technology matching; location-safe deduplication;
  retrieval/admission diagnostics.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify `src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage`.
- Inspect/modify `src/fitcv/vector_search.py:build_candidate_query_components`.
- Inspect/modify `src/fitcv/vector_search.py:run_vector_search`.
- Inspect/modify `src/fitcv/vector_search.py` embedding lookup/fallback helpers.
- Inspect/modify `src/fitcv/normalize.py:normalize_batch_with_exclusions`.
- Verify `tests/test_vector_search.py` and `tests/test_normalize.py`.

**Dependencies:**
- Task 2 supplies source-grounded technology and requirement inventories.
- Task 3 defines the evidence terminology used in retrieval diagnostics.

**Authority:**
- Preauthorized local actions: modify retrieval/normalization symbols and
  focused tests; preserve shortlist and audit-sample sizes.
- Stop for: adding a new vector store, deleting cached embeddings, or changing
  public retrieval configuration names without an approved contract update.

**Steps:**
- [ ] Step 1: Resolve `config["retrieval_strategy"]` once and pass the resolved
  value through `execute_shortlist_stage`; record requested and effective
  strategy separately.
- [ ] Step 2: Preserve valid vector rows when only some job vectors are missing,
  invalid, or incompatible; regenerate affected rows through the existing path
  or merge lexical results under the same production top-N budget.
- [ ] Step 3: Keep candidate query serialization bounded but derive technology
  signals from the stable complete source-grounded inventory, not only the first
  profile-order entries. Distinguish exact tools from related platforms such as
  Azure versus Azure Functions.
- [ ] Step 4: Prevent blank URLs from being one exact identity and preserve
  location/employment/application variants in grouped near-duplicate records.
- [ ] Step 5: Record which jobs were eligible, retrieved, audited, admitted to
  AI scoring, and excluded at each boundary.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_normalize.py tests/test_pipeline.py -k "retrieval or vector or lexical or technology or cache or dedup or location or shortlist" --disable-warnings --maxfail=1`
- Expected: configured lexical mode invokes lexical retrieval; one bad vector
  does not discard valid vector rows; exact technology matching does not grant
  Azure credit for Azure Functions unless the configured taxonomy says so;
  location variants and blank-URL postings remain distinguishable.
- [ ] Run a fixed paired recall fixture and record shortlist recall@50 for
  vector-only, lexical-only, and merged behavior without changing production
  shortlist size.

**Exit Criteria:**
- Retrieval behavior matches configuration, fallback is per-row or explicitly
  merged, and no eligible job disappears solely because of an unrelated cache
  or deduplication row.

### Task 5: Persist visibility, reuse, and failure diagnostics

**Purpose:**
- Make it possible to distinguish retrieval loss, evidence-selection loss,
  prompt truncation, and invalid scoring without exposing raw prompts.

**Task Function:**
- Thread bounded diagnostics through stage artifacts and ranking reuse paths.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: independently validate fresh/reused parity and failure
  visibility.

**Specification Coverage:**
- Available/selected/rendered/model-visible evidence sets; request truncation;
  complete input checksums; explicit invalid/provider-failure state.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`,
  `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`.
- Inspect/modify `src/fitcv/pipeline_stage_artifacts.py:build_ranking_stage_block`.
- Inspect/modify `src/fitcv/pipeline_stages/common.py:ranking_row_sample`.
- Inspect/modify `src/fitcv/ranking.py:rank_jobs` only for preserving explicit
  failure/retry metadata; do not change ranked-score arithmetic.
- Verify `tests/test_pipeline.py`,
  `tests/test_pipeline_stage_artifacts.py`, and `tests/test_ranking.py`.

**Dependencies:**
- Tasks 1–4 define the manifest fields, fingerprints, and admission boundaries.

**Authority:**
- Preauthorized local actions: add bounded diagnostics and focused tests; do
  not expose raw prompts, descriptions, credentials, or unrelated artifacts.
- Stop for: changing API/export schemas or silently converting failed scores
  into ranked compatibility values.

**Steps:**
- [ ] Step 1: Persist one per-job projection containing canonical available
  counts/IDs, selected IDs, rendered IDs, model-visible fields, omissions,
  truncation reasons, effective retrieval strategy, and request fingerprint.
- [ ] Step 2: Persist the same visibility record for fresh and reused scores;
  never rebuild reuse diagnostics from a missing request record.
- [ ] Step 3: Keep invalid/provider-failed rows explicitly unscored with
  failure code and retry eligibility in stage diagnostics, even when the
  existing ranked list contains only valid scores.
- [ ] Step 4: Add an additive artifact assertion that a below-cutoff job,
  invalid-score job, and scored job are distinguishable.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_stage_artifacts.py tests/test_ranking.py -k "diagnostic or visibility or truncation or reuse or score_status or retry or ranking" --disable-warnings --maxfail=1`
- Expected: fresh and reused rows carry equivalent visibility manifests;
  omitted evidence is nonzero when the selector shortens the pool; failed
  scoring remains explicit and does not receive a compatibility rank.

**Exit Criteria:**
- A future run can identify where material evidence disappeared without reading
  a raw model prompt or inferring from the final score alone.

### Task 6: Execute cross-stage backend proof and reconcile the plan

**Purpose:**
- Prove the corrected contracts together and record any real deviation before
  implementation handoff.

**Task Function:**
- Final backend verification and plan reconciliation.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: resolve from reasoning depth, ambiguity, scope, risk, and
  cost before execution.

**Validator Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: final independent acceptance against the task contracts.

**Specification Coverage:**
- All implementation outcomes; pinned-review evidence; backend boundary proof;
  no unvalidated finding promoted into scope.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify changed files from Tasks 1–5.
- Verify this plan's task checkboxes and recorded deviations.
- Do not modify unrelated existing plans or untracked artifacts.

**Dependencies:**
- Tasks 1–5 complete with focused tests passing.

**Authority:**
- Preauthorized local actions: run declared verification, inspect diffs, and
  update this plan's evidence/checklists.
- Stop for: any required failure, scope deviation, external publication, or
  destructive cleanup.

**Steps:**
- [ ] Step 1: Run focused scorer, enrichment, evidence, retrieval, normalization,
  candidate-profile, pipeline, artifact, and ranking suites.
- [ ] Step 2: Run compile, whitespace, and full-suite checks; compare failures
  with the pre-change baseline without fixing unrelated failures.
- [ ] Step 3: Verify the direct scoring boundary with a stub provider and the
  representative retrieval trace; capture request/manifest assertions.
- [ ] Step 4: Apply `skill-verification-before-completion`; leave this plan
  `proposed` unless that verification returns `verified`.

**Verification:**
- [ ] `python -m pytest -q tests/test_ai_score.py tests/test_enrich.py tests/test_evidence.py tests/test_vector_search.py tests/test_normalize.py tests/test_ranking.py tests/test_pipeline.py tests/test_pipeline_stage_artifacts.py tests/test_fitcv_cp/test_candidate_profile_service.py --disable-warnings --maxfail=1`
- Expected: focused cross-stage suite passes with no new failures in the
  changed contracts.
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp tests`
- Expected: compilation succeeds.
- [ ] `python -m pytest -q`
- Expected: full suite passes, or pre-existing failures are recorded with exact
  command output and are not misrepresented as plan success.
- [ ] `git diff --check`
- Expected: no whitespace errors.
- [ ] `git status --short`
- Expected: only declared source/test/doc changes are present; unrelated
  untracked workspace artifacts remain untouched.

**Exit Criteria:**
- Every validated finding in scope has an implementation task and regression
  proof; all required verification is fresh; deviations and deferred claims
  are recorded; completion status remains governed by
  `skill-verification-before-completion`.

## Verification

Final artifact-level proof consists of:

- the focused cross-stage pytest command in Task 6;
- `python -m compileall -q src/fitcv src/fitcv_cp tests`;
- `python -m pytest -q` with any pre-existing failures recorded explicitly;
- `git diff --check`;
- a direct stub-provider assertion showing the exact model-visible request and
  visibility manifest;
- a fixed paired shortlist fixture reporting recall@50 without changing the
  production shortlist budget;
- `skill-verification-before-completion` returning `verified` before this plan
  can become `completed`.

## Completion Criteria

The plan is ready for completion verification when:

1. Mandatory scorer context is preserved or scoring fails explicitly; no valid
   JSON request is produced from a silently emptied core.
2. Requirement type, language level, candidate source coverage, and evidence
   support state are source-grounded and auditable.
3. Two evidence items remain bounded but complementary, contextual, and
   provenance-preserving.
4. Configured retrieval strategy is honored; mixed fallback does not discard
   valid rows; location and blank-URL identities remain distinct.
5. Fresh and reused scores expose the same bounded visibility manifest and
   complete canonical input checksums.
6. Retrieval/admission and scoring failures remain distinguishable from a low
   compatibility score.
7. All task-local and final verification commands pass, or exact blockers and
   deviations are recorded without claiming completion.
8. No excluded or merely hypothesized finding is implemented without a new
   approved specification.
