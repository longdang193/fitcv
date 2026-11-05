---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-scoring-input-integrity-and-retrieval-recall
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/evidence.py
  - src/fitcv/candidate.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - tests/test_ai_score.py
  - tests/test_evidence.py
  - tests/test_candidate.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_artifacts.py
  - docs/superpowers/plans/2026-11-04-21-26-fitcv-cross-functional-retrieval-and-ranking-recall-plan.md
---

# FitCV Scoring-Input Integrity And Retrieval Recall Plan

## Goal

Make the bounded input received by FitCV's holistic AI scorer complete enough,
relevant enough, and truthful enough to preserve substantial candidate evidence
without increasing the existing eight-skill or two-evidence limits. Recover
cross-functional retrieval recall before scoring, make the two evidence slots
complementary, and persist enough bounded diagnostics to distinguish retrieval
loss from scorer-input loss.

Review basis: `longdang193/fitcv` `main` at
`1b006a817c33c53ddbf4cbf2bd4014e3f52298b2`, the attached verdict, and the
completed read-only browser review. The baseline policy in
`config/policy/ranking.yaml` assigns `holistic_ai_fit: 1.0` and
`structured_fit: 0.0`; personalization may change ordering but cannot recover
facts omitted from the AI request.

## Review Verdict

### Completed behavior to preserve

- Deterministic local hash embeddings route through lexical retrieval instead
  of being interpreted as semantic cosine vectors.
- Normal ranking limits the candidate projection to eight skills and two
  evidence items.
- Matching skills are moved ahead of unrelated skills, and job technology,
  responsibilities, title, family, and domain contribute to selection.
- Legacy project technology survives canonical evidence projection.
- Selected evidence includes bounded project and organization context.

### Validated findings included in this plan

- Candidate facts beyond skills, years of experience, and target role do not
  reach the holistic scorer. Canonical languages and employment chronology are
  omitted; education and certifications compete for the same two evidence
  slots; serialized evidence omits `kind` and `source_section`.
- Evidence selection is independently scored and takes the top two items, so
  two overlapping items can crowd out evidence covering a different required
  skill or technology.
- Evidence is selected before the final `text[:400]` and
  `scoring_context[:400]` truncation, so the statement that caused selection
  can disappear from the transmitted request.
- AI-input matching uses case-insensitive string equality while structured
  ranking uses the configured synonym policy. Required, technology, and
  preferred terms share one priority bucket, allowing preferred items to
  displace required items.
- Unsupported skill claims are included by ranking flatteners, and legacy
  parent or bullet skills are expanded to every evidence item under the parent,
  overstating which evidence demonstrates a skill.
- Lexical technology retrieval uses only the first eight profile-order hints
  and recognizes canonical technology evidence only when its title is exactly
  `Technology stack`; later or differently titled technology evidence can be
  lost before AI scoring.
- The final request boundary does not reapply the two-evidence limit and does
  not cap every list/scalar field or the total serialized request size.
- Invalid cached candidate vectors can be reused repeatedly and force lexical
  fallback without regeneration.
- Retrieval artifacts can report configured embedding metadata instead of the
  effective fallback contract, and ranking artifacts retain a fingerprint but
  not the bounded skills/evidence the scorer actually saw.
- The prior retrieval plan is marked completed while its declared focused test
  command remains unchecked; its verification record needs reconciliation.

### Excluded claims

- Do not claim the exact Heidi outcome, employer decision, numeric score, or
  rejection stage without original run artifacts.
- Do not change compatibility weights, thresholds, baseline mode, shortlist
  size, or Loose/Full/Strict semantics.
- Do not increase the eight-skill or two-evidence budgets, add an unbounded
  prompt, add a generic LLM reranker, or convert unsupported claims into
  supported claims.
- Do not add a new vector store or delete stored embeddings as a migration.

## Implementation Outcomes

### Versioned bounded scoring-input contract

`build_ranking_job_input()` and `build_ranking_request()` share one versioned
contract. It preserves eight candidate skills and two evidence items, applies
the configured semantic/synonym policy used by structured ranking before
deduplication, prioritization, and skill coverage, and fingerprints that policy
and revision. It then applies case-insensitive deduplication and per-value limits before slot allocation,
  enforces a `12_000`-character serialized request cap at the final boundary,
  caps ordinary term/scalar values at `160` characters and evidence text/context
  at `400` characters,
and records omitted counts and truncation reasons. The fingerprint includes the
final bounded request, contract version, and complete canonical requirement and
candidate-fact checksums needed to prevent stale reuse.

### Factual and attributable candidate projection

The scorer receives a compact bounded candidate-facts object containing
language names and levels, employment chronology/duration derived from dates,
and bounded education/certification context. Each evidence item retains its
evidence kind, source section, parent identity, and source references in the
serialized request. Unsupported claims remain marked unsupported and are
excluded from rankable skill matching.

### Complementary evidence selection

The selector keeps the two-item budget but chooses the first strong item and
then chooses the item with the greatest marginal coverage of important job
requirements. Direct technology matches in grounded evidence text count as
technology support. Requirement-relevant sentences or spans are selected before
the 400-character evidence/context limits are applied, preserving negation,
scope, duration, and provenance.

### Retrieval recall and cache correctness

Lexical matching uses the complete stable, deduplicated, source-grounded
project-technology inventory internally while keeping candidate-query and
prompt serialization bounded. Semantic query construction remains bounded but
uses representative technology signals rather than only the earliest profile
entries. Cached candidate vectors are validated against the effective backend
contract before reuse; invalid entries are regenerated through the existing
embedding path.

### Diagnosable stage artifacts

Shortlist artifacts distinguish requested versus effective embedding metadata
and persist the production cutoff score. Ranking artifacts persist only bounded
per-job diagnostics: visible candidate-skill names, selected evidence IDs,
included/omitted requirement counts, truncation flags/reasons, and the existing
AI-input fingerprint.

## Execution Approach

- Mode: `inline sequential`.
- Coordination: `none`; one executor owns the ordered changes because the
  scoring-input contract, evidence selector, retrieval projection, and stage
  artifacts share fingerprints and must be versioned together.
- Isolation: current worktree; preserve the existing untracked `.tmp/` review
  artifacts and do not include them in commits.
- Commit policy: no checkpoint commits are required; commit only after focused
  and final verification succeeds.
- Shared-write control: `ai_score.py` owns the scoring-input contract;
  `evidence.py` owns evidence projection, selection, and excerpting;
  `vector_search.py` owns retrieval/cache behavior; pipeline artifact modules
  only consume bounded diagnostic projections.
- Required final proof: `skill-backend-verification` evidence at the scoring
  and retrieval boundaries plus `skill-verification-before-completion` before
  changing this plan's status from `proposed`.

### Task 1: Define the versioned bounded scoring-input contract

**Purpose:** Stop oversized or caller-supplied ranking inputs from bypassing
the advertised eight-skill/two-evidence limits and prevent stale score reuse.

**Task Function:** Backend contract implementation and focused regression proof.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Versioned bounded scoring-input contract; total
request bound; fingerprint integrity; preserved score policy.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- Modify `src/fitcv/ai_score.py:build_ranking_job_input()` to use stable
  semantic-policy-aware bounded terms, preserve required-before-technology-
  before-preferred priority, and emit omitted/truncation metadata. Required,
  technology, preferred, and candidate skill coverage must resolve through the
  same configured alias policy as `src/fitcv/ranking.py:resolve_semantic_value()`.
- Modify `src/fitcv/ai_score.py:build_ranking_request()` and
  `build_ai_score_input_fingerprint()` to reapply all count/character limits,
  enforce the `12_000`-character serialized request cap, and fingerprint the
  final bounded payload plus contract version, semantic-policy fingerprint, and
  complete canonical checksums.
- Add the shared contract constants/helpers in `src/fitcv/ai_score.py`; do not
  create a second prompt-building implementation.
- Define the overflow contract explicitly: the cap applies to the final
  structured request payload and rendered prompt; reserve the configured
  template/rubric budget first, then remove optional fields in deterministic
  order (`candidate_evidence` excerpts, candidate facts, preferred terms,
  responsibilities, descriptive metadata) while retaining title, required
  terms, semantic-policy metadata, and checksums. If the mandatory core still
  exceeds the cap, raise a bounded contract error rather than silently sending
  an oversized request. Every list has an explicit count bound, and direct
  `build_ranking_request()` callers must provide or receive the same canonical
  ranking-input contract; the legacy string-only path is compatibility-only and
  is validated as a bounded candidate summary.
- Extend `tests/test_ai_score.py` for oversized scalar/list values, more than
  two supplied evidence items, duplicate/case-variant skills, omitted
  requirement checksums, truncation flags, and stable fingerprints.

**Dependencies:** None.

**Authority:** Preauthorized changes are bounded serialization, contract
versioning, fingerprint fields, and tests. Stop for any score-weight,
threshold, evidence-mode, or provider-route change.

**Steps:**
1. Define the contract version and exact per-field plus total serialized-size
   limits alongside the existing evidence limits.
2. Normalize and casefold terms before deduplication and slot allocation, while
   retaining the first original display spelling.
3. Apply the same bounded projection in both the normal pipeline path and the
   direct `build_ranking_request()` boundary.
4. Include complete canonical requirement and candidate-fact checksums without
   serializing the complete unbounded facts into the prompt.
5. Return explicit omitted counts and truncation reasons in the bounded
   diagnostic projection.

**Verification:**
- `python -m pytest -q tests/test_ai_score.py -k "ranking_job_input or ranking_request or fingerprint or bounded" --disable-warnings --maxfail=1`
- Assert the final serialized request is at most `12_000` characters, contains
  at most eight candidate skills and two evidence items, and changes its
  fingerprint when an omitted canonical requirement or candidate fact changes.

**Exit Criteria:** Every caller receives the same bounded contract, malformed
or oversized direct inputs cannot bypass it, and score arithmetic remains
unchanged.

### Task 2: Preserve factual candidate context and truthful skill attribution

**Purpose:** Prevent languages, employment chronology, education, certification,
unsupported claims, and inherited legacy links from distorting the scorer's
view of demonstrated experience.

**Task Function:** Canonical profile projection and attribution correction.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Candidate factual summary; evidence provenance;
unsupported-claim handling; legacy adaptation correctness.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- Modify `src/fitcv/ai_score.py:build_ranking_job_input()` to emit bounded
  language name/level, employment date/duration, education, certification, and
  evidence-type context.
- Add `src/fitcv/candidate.py:flatten_rankable_skills()` and migrate every
  ranking/retrieval caller: `ai_score.build_ranking_job_input()`,
  `vector_search.build_candidate_query_components()`,
  `vector_search._lexical_search_result()`, and
  `pipeline.build_ranking_features()`. Leave `flatten_skills()` unchanged for
  non-ranking compatibility callers and enumerate those callers in tests.
- Modify both `src/fitcv/candidate.py:_adapt_legacy_parent()` and
  `adapt_candidate_profile_to_v2()`. Return a scope map for parent claims,
  explicit legacy evidence, and each bullet/highlight, then attach parent-level
  skills only to parent-level evidence (or a bounded parent-context marker) and
  bullet skills only to their own evidence. Project-level skills remain
  supported project context and must not be linked to unrelated child bullets.
- Modify `src/fitcv/evidence.py:project_candidate_evidence()` and the AI-score
  evidence serializer to preserve `kind`, `source_section`, parent identity,
  and source references.
- Extend `tests/test_candidate.py`, `tests/test_ai_score.py`, and
  `tests/test_evidence.py` with unsupported claims, parent/bullet scope,
  language changes, employment-date changes, and evidence provenance cases.

**Dependencies:** Task 1 defines the bounded output shape and fingerprint
fields.

**Authority:** Preserve the candidate schema and source references. Do not
silently delete unsupported claims or invent experience duration when dates are
missing or contradictory; represent unavailable duration explicitly.

**Steps:**
1. Derive chronology only from valid start/end/current fields, with explicit
   `unknown` or `ongoing` states for missing or present dates.
2. Include languages and factual education/certification context in the compact
   candidate projection before evidence-slot selection.
3. Keep unsupported claims available for audit but exclude them from rankable
   skill sets and matched-skill coverage across all four migrated callers.
4. Preserve legacy claim scope through `adapt_candidate_profile_to_v2()` and
   evidence projection; retain provenance labels in the final prompt payload.

**Verification:**
- `python -m pytest -q tests/test_candidate.py tests/test_ai_score.py tests/test_evidence.py -k "language or duration or unsupported or legacy or provenance or ranking" --disable-warnings --maxfail=1`
- Change only language proficiency or employment dates in a fixture and assert
  the candidate projection and AI-input fingerprint change.
- Assert a bullet evidence item does not inherit unrelated parent skills and an
  unsupported claim is not counted as a matched demonstrated skill.

**Exit Criteria:** The scorer receives bounded factual context and truthful
evidence attribution without changing the source profile's supported/unsupported
status or scoring policy.

### Task 3: Make evidence selection complementary and excerpt-aware

**Purpose:** Keep two evidence slots while preventing redundant snippets and
prefix truncation from hiding the requirement match that justified selection.

**Task Function:** Evidence ranking, marginal coverage, and bounded excerpting.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Complementary evidence; direct technology support;
requirement-relevant excerpts; two-item bound.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- Modify `src/fitcv/evidence.py:select_ranking_evidence()` to select the first
  high-value item, then maximize marginal coverage of required skills,
  technology, responsibilities, and other bounded requirement channels while
  penalizing near-duplicate coverage.
- Make the algorithm deterministic in the plan and implementation: channel
  weights are required skills `5`, technology `4`, responsibilities `3`,
  title/family/domain `1`; required channels outrank preferred channels; the
  second item maximizes uncovered weighted-channel gain minus a token-set
  Jaccard duplicate penalty of `2 * overlap`; score ties break by original
  pool order then `evidence_id`. Excerpts select matching sentences first,
  preserve negation/date/duration/provenance spans, and use original order then
  evidence ID as tie-breakers.
- Add `src/fitcv/evidence.py:score_evidence_item_by_channel()` and call it from
  `select_ranking_evidence()` so direct grounded technology text is scored
  separately from structured skill links and heterogeneous-term denominator
  dilution cannot erase scarce technology matches; keep
  `score_evidence_item()` as the compatibility wrapper for existing callers.
- Add `src/fitcv/evidence.py` helper for requirement-relevant sentence/span
  extraction before applying the existing 400-character text/context limits.
- Keep `src/fitcv/ai_score.py:build_ranking_job_input()` as the final two-item
  boundary and include excerpt/truncation metadata in its bounded projection.
- Extend `tests/test_evidence.py` and `tests/test_ai_score.py` with SQL/Python,
  skill/technology, duplicate-prefix, late-match, negation, duration, and
  provenance fixtures.

**Dependencies:** Task 1 contract; Task 2 factual and attribution projection.

**Authority:** Keep the limit at two items and keep final compatibility scoring
weights unchanged. Do not use an external reranker or an unbounded evidence
window.

**Steps:**
1. Build normalized requirement channels from required skills, technology,
   responsibilities, title/family, and domain.
2. Select one strongest item deterministically, then choose the item with the
   greatest new important-channel coverage; use evidence ID as the final tie
   breaker.
3. Extract or compose bounded excerpts from the source text so relevant terms
   after character 400 remain visible while preserving negation, dates, scope,
   and source labels.
4. Serialize both selected evidence records with kind/source/parent metadata and
   explicit truncation flags.

**Verification:**
- `python -m pytest -q tests/test_evidence.py tests/test_ai_score.py -k "select_ranking_evidence or score_evidence_item or evidence or excerpt" --disable-warnings --maxfail=1`
- Assert two SQL items cannot occupy both slots when a distinct Python or
  technology item adds uncovered required-channel support.
- Assert a late requirement term survives the bounded excerpt and that negative
  statements are not converted into positive support.

**Exit Criteria:** The scorer receives at most two deterministic, complementary
evidence items whose transmitted excerpts still contain the supported claim.

### Task 4: Recover shortlist recall and repair candidate-vector reuse

**Purpose:** Prevent later project technology or malformed cached vectors from
removing a relevant job before AI scoring.

**Task Function:** Retrieval contract and cache-boundary correction.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Full local lexical technology recall; bounded
semantic query; cache validation; effective backend metadata.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- Modify `src/fitcv/vector_search.py:_bounded_profile_technology_hints()` and
  `build_candidate_query_components()` to derive technology from explicit,
  source-grounded project fields/evidence rather than only the exact display
  title `Technology stack`; keep semantic query serialization bounded and
  representative.
- Modify `src/fitcv/vector_search.py:_lexical_search_result()` to compare job
  technology against the complete stable deduplicated local inventory without
  expanding the serialized prompt/query.
- Modify `src/fitcv/vector_search.py:CandidateQueryEmbeddingRecord`,
  `_build_candidate_query_embedding_record()`, and
  `resolve_candidate_query_embedding()` to
  validate cached vectors with `_validated_vector()` against the effective
  backend dimension and regenerate invalid, zero-norm, non-finite, or
  wrong-dimension entries through `generate_embedding_with_metadata()`.
- Modify lexical diagnostics to persist requested and effective backend/model/
  dimension/revision/preprocessing/contract metadata separately, carrying the
  effective metadata record through lexical fallback, including
  `production_cutoff_retrieval_score`.
- Extend `tests/test_vector_search.py` and `tests/test_embeddings.py` with
  ninth-technology recall, non-`Technology stack` evidence, malformed cache,
  zero-norm cache, wrong-dimension cache, semantic-fallback metadata, and
  cutoff-score cases.

**Dependencies:** Task 2 rankable technology/source projection; Task 1 contract
versioning for candidate-query fingerprints.

**Authority:** Keep shortlist output bounded by the existing `vector_search_top_n`
and candidate-query limits. Do not delete historical embeddings or treat
deterministic vectors as semantic.

**Verification:**
- `python -m pytest -q tests/test_vector_search.py tests/test_embeddings.py -k "lexical or technology or cache or fallback or cutoff or contract" --disable-warnings --maxfail=1`
- Use a fixture with eight distractor technologies followed by OpenAI/agent
  technology and assert the matching job remains in the production shortlist.
- Reuse malformed cache rows and assert the backend regenerates the vector and
  records the effective contract rather than repeating lexical fallback.

**Exit Criteria:** Later relevant technology can influence lexical retrieval,
semantic query construction remains bounded, and cached-vector failures are
self-healing and diagnosable.

### Task 5: Persist bounded scorer-input diagnostics

**Purpose:** Make future runs distinguish retrieval loss, scorer-input evidence
loss, invalid/provider-failed scoring, and low model scores without storing raw
prompts.

**Task Function:** Pipeline integration and artifact contract.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Per-job bounded diagnostics; stage-level provenance;
retrieval-to-ranking traceability.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- Modify `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage()` to retain
  a bounded diagnostic projection beside `ranking_inputs_by_identity`, including
  visible skill names, selected evidence IDs, requirement counts, omitted counts,
  truncation flags/reasons, and AI-input fingerprint.
- Change the runner return/state contract so this projection is passed through
  `build_ranking_stage_block()`; do not leave it as a local variable. The
  canonical handoff is `state["ranking_input_diagnostics_by_identity"]` plus the
  returned projection mapping, and the artifact owns it under an additive
  `scorer_input_diagnostics` field.
- Modify `src/fitcv/pipeline_stage_artifacts.py:build_ranking_stage_block()` to
  include the projection in bounded input/output samples and stage decision
  metadata.
- Modify `src/fitcv/pipeline_stages/common.py:ranking_row_sample()` to expose
  only the bounded diagnostic fields; never expose raw candidate/job prompt text.
- Extend `tests/test_pipeline.py` and
  `tests/test_pipeline_stage_artifacts.py` for below-cutoff, selected-but-
  invalid-score, reused-score, and empty-evidence cases.

**Dependencies:** Tasks 1–4 define the projection fields and fingerprints.

**Authority:** Preserve existing artifact schemas unless additive diagnostic
  fields are required; do not change score status meanings or export schemas.

**Steps:**
1. Add one canonical per-job diagnostic projection in the ranking stage runner.
2. Pass it through existing stage-block builders and sample builders.
3. Keep identifiers, counts, flags, and hashes bounded; omit raw descriptions,
   full prompts, and credentials.
4. Assert the artifact distinguishes a job missing from raw shortlist rows from
   a job reaching scoring with invalid/provider-failed output.

**Verification:**
- `python -m pytest -q tests/test_pipeline.py tests/test_pipeline_stage_artifacts.py -k "ranking or shortlist or diagnostic or score_status" --disable-warnings --maxfail=1`
- Assert the persisted artifact contains selected evidence IDs and visible
  skill names for a scored job, while an absent shortlist job has no scorer-input
  projection.

**Exit Criteria:** A future run can identify whether evidence disappeared during
retrieval, bounded selection, prompt construction, or scoring without reading a
raw prompt.

### Task 6: Reconcile verification records and complete cross-stage proof

**Purpose:** Close the prior plan's unchecked verification gate and prove the
combined retrieval, evidence, scoring-input, cache, and artifact contracts.

**Task Function:** Final backend verification and plan reconciliation.

**Template Profile:** `unresolved while task is pending`.

**Specification Coverage:** Attached verdict; prior-plan verification integrity;
cross-stage regression proof.

**Required Skills:** `skill-backend-verification`,
`skill-verification-before-completion`.

**Files And Symbols:**
- Update `docs/superpowers/plans/2026-11-04-21-26-fitcv-cross-functional-retrieval-and-ranking-recall-plan.md`
  only after the exact declared focused command is run; either check it with
  its real result or record the exact superseding command and deviation.
- Add or update the synthetic cross-functional fixture in
  `tests/test_vector_search.py`, `tests/test_evidence.py`, and
  `tests/test_ai_score.py`, plus one pipeline integration case spanning
  `execute_ranking_stage()` → `build_ranking_request()` → persisted ranking
  artifact. The same profile must prove shortlist survival, complementary
  evidence, bounded prompt transmission, language and chronology visibility,
  truthful skill attribution, and diagnostic persistence in one trace.

**Dependencies:** Tasks 1–5.

**Authority:** Do not mark either plan `completed` until
`skill-verification-before-completion` returns verified evidence. Record known
pre-existing pipeline failures separately instead of changing unrelated tests.

**Verification:**
- The originally declared command included `tests/test_pipeline_stage_artifacts.py`,
  which is not present in this repository. The superseding command below covers
  every existing affected test module, including the stage-artifact assertions
  in `tests/test_pipeline.py`:
  `python -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py --disable-warnings --maxfail=1`
- `python -m pytest -q`
- `python -m compileall -q src/fitcv tests`
- `git diff --check`
- `git status --short`
- Compare any broader-suite failures with the pre-change baseline and record
  only failures reproduced outside this plan's changed contracts.

**Exit Criteria:** Focused backend proof is fresh and green, the synthetic
cross-stage trace shows the relevant job survives retrieval and reaches the
scorer with complementary bounded evidence, diagnostics expose the exact
bounded projection, and plan verification records match executed commands.

## Final Constraints

1. Preserve `holistic_ai_fit: 1.0`, structured-factor zero weight, score parser,
   thresholds, shortlist size, and Loose/Full/Strict semantics.
2. Preserve the eight-skill and two-evidence limits; improve selection quality
   rather than increasing slots.
3. Keep retrieval query/prompt input bounded and source-grounded; internal
   lexical comparison may inspect the complete deduplicated technology inventory
   without serializing it.
4. Keep unsupported claims auditable but never present them as demonstrated
   evidence.
5. Do not claim the actual Heidi result without original run artifacts.

## Verification Record

- Focused affected-suite superseding command passed: `425 passed, 4 skipped`.
- Full regression command `python -m pytest -q` passed: `3534 passed, 10 skipped`.
- `python -m compileall -q src/fitcv tests` passed.
- `git diff --check` passed.
- The declared `tests/test_pipeline_stage_artifacts.py` target does not exist;
  stage-artifact coverage is implemented and verified in `tests/test_pipeline.py`.
- Review-only `.tmp/` artifacts remain untracked and were not modified or added
  to the implementation change.

## Final Review Corrections

The PR review identified six justified edge cases and the implementation now
covers each one without changing the scorer weights, thresholds, shortlist
size, or eight-skill/two-evidence budgets:

- Candidate summaries use field-aware trimming that retains skills and
  languages, and request-size enforcement measures the escaped serialized
  payload rather than only the rendered prompt.
- Requirement coverage uses token boundaries and controlled multi-token
  overlap, preventing substring matches such as `R`/`reports`, `Power BI`/power
  transmission, and `C++`/`C#`.
- Required priority is monotonic across required, technology, and preferred
  channels, and candidate aliases are deduplicated by the configured semantic
  policy before the eight-skill limit.
- Repeated legacy bullet skills retain every attributable bullet evidence ID.
- Regression tests cover all four behaviors above plus the bounded serialized
  request and repeated-bullet attribution cases.
