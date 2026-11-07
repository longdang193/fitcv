---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: proposed
name: fitcv-skill-evidence-integrity
targets:
  - src/fitcv/enrich.py
  - src/fitcv/candidate.py
  - src/fitcv/vector_search.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/evidence.py
  - tests/test_enrich.py
  - tests/test_vector_search.py
  - tests/test_ai_score.py
  - tests/test_scoring_input_integrity.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - docs/pipeline.md
---

# FitCV Skill and Evidence Integrity

## Goal

Restore end-to-end integrity for skill extraction, demonstrated-technology retrieval, compatibility-scoring inputs, evidence attribution, and reused CV-analysis records. The implementation must preserve valid requirement signals and supported candidate evidence from enrichment through retrieval, scoring, and analysis reuse without weakening the existing no-attributable-evidence scoring gate.

The plan is based on the publicly reachable review revision `6fdfcc92f3119766c213bf82105c8e709201bdc8` on `longdang193/fitcv` and the completed read-only reviews from `GPT-5.6-Sol` and `GPT-6`, both at `High` effort.

## Validated Scope

The following findings were independently confirmed against the pinned source and are in scope:

1. `_build_skill_entities()` rejects valid raw multiword skills after a structured entity exists, allowing an incomplete canonical requirement list to suppress the raw list downstream.
2. Sparse description recovery does not recognize common `Requirements:`, `Qualifications:`, or `Technical Skills:` headings.
3. `_profile_technology_inventory()` admits unsupported or `claimed_only` project technology into candidate query hints, lexical overlap, and fallback rescue.
4. `_profile_technology_inventory()` omits technologies demonstrated only in experience-bullet skills and supported top-level candidate skills.
5. Scorer bounding drops boolean `false` values and stringifies nested location evidence before the provider sees it.
6. Scorer diagnostics read the pre-budget `bounded_ranking_input` source rather than the final selected payload.
7. `build_evidence_used()` omits canonical evidence IDs and plural source attribution needed to join compact evidence to requirement coverage.
8. `_rebuild_reused_record()` does not preserve all fresh-analysis evidence classifications, uncertainty metadata, or candidate-profile identity needed for faithful reuse.

The following review observations are deliberately excluded from this implementation plan because they were classified as workload-dependent risks rather than validated deterministic defects: expanding the fixed `evidence_top_k` selection limit and replacing positional evidence prompt text with labeled serialization. They remain follow-up evaluation topics after the confirmed integrity fixes land.

## Implementation Outcomes

### Canonical requirement signals remain complete

Accepted raw skills are reconciled with validated structured entities without an arbitrary three-word cutoff, while verbose non-skill requirement sentences remain rejected. Common requirement headings recover bullet-list skills without leaking preferred-only text. The canonical requirement projection consumed by retrieval and scoring contains every accepted requirement.

### Retrieval uses demonstrated technology only

Technology hints and lexical overlap use the same support-state eligibility rule as rankable skills, include eligible experience-bullet technologies and supported top-level skills, and retain deterministic deduplication and hint bounds.

### The provider payload and diagnostics agree

The final ranking request preserves typed booleans and bounded nested location fields. `bounded_ranking_input`, visibility manifests, persisted diagnostics, and request fingerprints describe the same final model-visible payload, with raw and model-visible counts kept separate.

### Evidence identity survives compact views and reuse

`evidence_used` remains backward-compatible while retaining canonical IDs, kinds, parent attribution, and source references. Exact CV-analysis reuse preserves evidence summaries, uncertainty identifiers, and candidate-profile identity; legacy reusable records lacking those fields are recomputed rather than silently reconstructed with weaker metadata.

### Regression proof covers cross-stage handoffs

Focused tests cover enrichment, retrieval, scoring, evidence projection, and reuse. A cross-contract test proves that a requirement and its supporting evidence survive the `enrich -> vector_search -> pipeline_stage_runner -> ai_score -> agentic_cv_analysis` handoff.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `task-specific isolated worktree` based on reviewed commit `6fdfcc92f3119766c213bf82105c8e709201bdc8`; preserve the current checkout's unrelated edits and untracked files
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only the listed source, test, and documentation files; run the listed focused and broad verification commands in the isolated worktree
- User-approval actions: commit, push, merge, publication, destructive cleanup, or changes outside the listed files
- Parallel ownership: `none`; `src/fitcv/candidate.py`, `src/fitcv/enrich.py`, `src/fitcv/vector_search.py`, `src/fitcv/ai_score.py`, and `src/fitcv/agentic_cv_analysis.py` have shared contract consumers and are serialized
- Sequential fallback: execute Tasks 1 through 5 in order; stop at the first failed task-local proof before editing a dependent surface

## Task Breakdown

### Task 1: Reconcile extracted skills and recover requirement headings

**Purpose:** Prevent valid mandatory skills from disappearing between raw enrichment, structured entities, canonical projections, retrieval, and scoring.

**Task Function:** backend implementation and regression testing

**Template Profile:** unresolved

**Specification Coverage:** Validated findings 1 and 2; outcomes “Canonical requirement signals remain complete” and “Regression proof covers cross-stage handoffs”.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- `src/fitcv/enrich.py`: `_DESCRIPTION_REQUIREMENT_MARKERS`, `_is_requirement_like_description_segment`, `_required_skill_candidates_from_description`, `_repair_required_skill_signal`, `_build_skill_entities`, `_semantic_skill_values`, and the canonical merge path used by `merge_scraped_and_enriched`.
- `tests/test_enrich.py`: `test_build_skill_entities_keeps_support_vector_machines`, `test_apply_structured_normalization_merges_raw_skills_missing_from_entities`, and new heading-recovery cases.
- `tests/test_scoring_input_integrity.py`: the `build_ranking_job_input` requirement-preservation cases.
- `docs/pipeline.md`: the existing enrichment contract at the Stage Responsibilities section.

**Dependencies:** none

**Authority:**
- Preauthorized local actions: add focused tests, edit the named enrichment symbols, update the enrichment contract wording in `docs/pipeline.md`, and run the Task 1 pytest command.
- Stop for: a proposed change that broadens accepted prose beyond `_is_allowed_skill_entity` and `_is_raw_skill_union_candidate`, changes preferred-skill semantics, or requires modifying an unlisted schema owner.

**Steps:**
1. Add a regression where `required_skills` contains one valid four-word skill absent from `required_skill_entities` alongside one structured entity. Assert that the skill survives `required_skill_entities`, `required_skills_canonical`, and `build_ranking_job_input`.
2. Add description fixtures for `Requirements:`, `Qualifications:`, and `Technical Skills:` followed by bullets, plus a preferred-only heading fixture. Assert required recovery and preferred-section isolation.
3. Remove only the arbitrary `len(raw_value.strip().split()) <= 3` union gate in `_build_skill_entities`; retain length bounds, canonical deduplication, `_is_raw_skill_union_candidate`, and `_is_allowed_skill_entity` filtering so verbose qualification sentences remain excluded.
4. Extend `_DESCRIPTION_REQUIREMENT_MARKERS` with anchored-heading-compatible English and German requirement headings, then verify `_required_skill_candidates_from_description` enters and exits bullet mode without treating preferred markers as mandatory.
5. Confirm `_semantic_skill_values` and the merge reconstruction consume the reconciled entity union rather than treating a non-empty but partial entity list as authoritative.
6. Run `uv run pytest tests/test_enrich.py tests/test_scoring_input_integrity.py -q`.

**Verification:**
- A four-word accepted skill appears in the canonical ranking input even when structured extraction returns only a partial entity list.
- `Requirements:` bullets recover into required skills, while `Preferred`/`Nice to have` bullets do not become mandatory.
- Existing `Support Vector Machines` and enrichment fallback tests remain green.

**Exit Criteria:** Task 1 tests pass, the canonical union is complete for accepted multiword skills, and no preferred-only or verbose sentence regression is introduced.

### Task 2: Unify demonstrated-technology eligibility and retrieval inventory

**Purpose:** Stop unsupported claims from influencing retrieval and add supported technologies that are currently present only in work experience or top-level candidate skills.

**Task Function:** retrieval implementation and regression testing

**Template Profile:** unresolved

**Specification Coverage:** Validated findings 3 and 4; outcome “Retrieval uses demonstrated technology only”.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- `src/fitcv/candidate.py`: the support-state filtering currently embedded in `flatten_rankable_skills`.
- `src/fitcv/vector_search.py`: `_profile_technology_inventory`, `_bounded_profile_technology_hints`, `_technology_overlap`, `_lexical_search_result`, `_has_affirmative_lexical_relevance`, and partial fallback assembly.
- `tests/test_vector_search.py`: `test_build_candidate_query_components_prioritize_demonstrated_skill_evidence`, `test_build_candidate_query_components_prioritize_supported_project_evidence`, deterministic technology-overlap tests, and new support-state/experience-only cases.

**Dependencies:** Task 1

**Authority:**
- Preauthorized local actions: extract or reuse one support-state predicate, edit the named retrieval symbols, update the named vector-search tests, and run the Task 2 pytest command.
- Stop for: a change that makes legacy profiles without support metadata ineligible, changes vector backend selection, or adds a second independent support-status policy.

**Steps:**
1. Add a failing test with a unique technology on a `claimed_only` project and assert it is absent from bounded query technology hints, contributes zero technology overlap, and cannot authorize lexical rescue. Add the supported-project counterpart and assert the existing positive behavior.
2. Add an experience-only technology fixture in an experience bullet and assert positive technology overlap and candidate-query inclusion when the hint budget allows.
3. Extract the existing rankable support-state rule from `flatten_rankable_skills` into one private shared helper in `src/fitcv/candidate.py`, preserving legacy/raw profiles' default-supported behavior. Reuse that helper from `_profile_technology_inventory` instead of duplicating status strings.
4. Extend `_profile_technology_inventory` to include eligible top-level skills and experience-bullet skills, and to filter project technology/evidence by the same support-state rule. Keep canonical case-insensitive deduplication and the existing eight-hint bound.
5. Verify `_lexical_search_result` and `_has_affirmative_lexical_relevance` receive only the filtered inventory, so unsupported technology cannot create an affirmative fallback signal.
6. Run `uv run pytest tests/test_vector_search.py -q`.

**Verification:**
- A `claimed_only` technology is absent from query hints and lexical overlap.
- A supported project technology and an experience-only supported technology both receive deterministic technology-overlap credit.
- Legacy profiles with no explicit support metadata retain prior eligibility.

**Exit Criteria:** Retrieval and fallback use one demonstrated-technology policy, all Task 2 tests pass, and no unsupported technology can change candidate query intent or rescue admission.

### Task 3: Preserve typed scorer inputs and align diagnostics with the final payload

**Purpose:** Ensure compatibility scoring receives the structured facts selected by the budgeter and that persisted diagnostics describe exactly what the provider received.

**Task Function:** scoring-contract implementation and regression testing

**Template Profile:** unresolved

**Specification Coverage:** Validated findings 5 and 6; outcomes “The provider payload and diagnostics agree” and “Regression proof covers cross-stage handoffs”.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- `src/fitcv/ai_score.py`: `bound_job_summary`, `bound_candidate_summary`, `build_ranking_request`, `build_ai_score_input_fingerprint`, and `build_ranking_input_diagnostics`.
- `tests/test_ai_score.py`: `test_ranking_input_diagnostics_are_bounded_and_track_the_final_request`, `test_ranking_input_does_not_reject_nine_mandatory_skills_before_budgeting`, and final-prompt preservation tests.
- `tests/test_scoring_input_integrity.py`: `test_final_scorer_request_retains_language_dimensions_and_ongoing_education` and evidence-limited scoring tests.
- `src/fitcv/pipeline_stage_runner.py`: the ranking-stage persistence path that stores `ranking_input_diagnostics_by_identity`.
- `docs/pipeline.md`: Ranking-V2 scorer visibility contract.

**Dependencies:** Tasks 1 and 2

**Authority:**
- Preauthorized local actions: add the named scorer regressions, edit the named request/diagnostic symbols, update the ranking visibility documentation, and run the Task 3 pytest command.
- Stop for: a change that calls the provider when selected attributable evidence is absent, changes ranking policy weights, or removes existing request-budget failure codes.

**Steps:**
1. Add a final-payload test with `native: false` and nested `actual_location` fields. Assert the serialized candidate/job JSON retains the boolean and structured location fields instead of stringifying or dropping them.
2. Add a small recursive JSON-safe bounding helper in `ai_score.py` that preserves booleans, numbers, lists, and selected nested objects while bounding leaf strings and filtering only `None` or genuinely empty strings.
3. Update `bound_candidate_summary` and `bound_job_summary` to use the helper, preserving mandatory skill ordering and existing total request limits.
4. Change `build_ranking_request` so `bounded_ranking_input` is assembled from `selected_job`, `selected_candidate`, and `selected_evidence`, not the pre-budget `source`. Preserve the existing key for compatibility with `build_ai_score_input_fingerprint` and current consumers.
5. Update `build_ranking_input_diagnostics` to derive visible skills, counts, evidence IDs, omission counts, and visibility manifests from that final bounded payload. Add separate raw and model-visible counts rather than overloading `candidate_skill_count`.
6. Keep the evidence-limited gate unchanged: no selected attributable evidence still produces `evidence_limited` without a provider call; budget trimming remains distinguishable from missing evidence.
7. Update the ranking-stage diagnostic assertions and `docs/pipeline.md` to state that raw input and model-visible payload are separate and that visibility diagnostics describe the final request.
8. Run `uv run pytest tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_pipeline.py -q`.

**Verification:**
- `native: false` remains a JSON boolean and `actual_location` remains structured in the final request.
- Diagnostics' visible skill/evidence IDs match the serialized request exactly after forced budget trimming.
- The no-attributable-evidence path remains non-provider-calling and non-retryable.

**Exit Criteria:** The scorer request, fingerprint, visibility manifest, and diagnostics have one final-payload source of truth, and all Task 3 tests pass.

### Task 4: Preserve evidence attribution and exact CV-analysis reuse metadata

**Purpose:** Make compact evidence views joinable to requirement coverage and make reused analysis records equivalent to fresh records for evidence and uncertainty metadata.

**Task Function:** analysis-contract implementation and regression testing

**Template Profile:** unresolved

**Specification Coverage:** Validated findings 7 and 8; outcome “Evidence identity survives compact views and reuse”.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- `src/fitcv/agentic_cv_analysis.py`: `build_evidence_used`, `build_cv_analysis_record`, `_REUSABLE_RECORD_REQUIRED_FIELDS`, `_reuse_rejection_reason`, and `_rebuild_reused_record`.
- `tests/test_agentic_cv_analysis.py`: `_complete_reusable_record`, `test_analyze_ranked_job_rebuilds_complete_exact_reuse_without_analysis`, `test_analyze_ranked_job_preserves_mode_on_exact_reuse`, and new evidence/reuse-equivalence tests.
- `tests/test_pipeline.py`: `test_run_pipeline_returns_debug_record_for_accepted_cv` and `test_run_pipeline_cv_analysis_persists_evidence_selection_provenance`.
- `tests/test_pipeline_agentic_late_stage.py`: late-stage fixtures that persist `evidence_used` and exact reuse records.

**Dependencies:** Task 3

**Authority:**
- Preauthorized local actions: add canonical evidence and reuse-equivalence regressions, edit the named analysis symbols, update exact-shape pipeline fixtures, and run the Task 4 pytest command.
- Stop for: a breaking removal or rename of legacy `evidence_type`, `source_ref`, or `name` fields, or a reuse path that accepts a record without the newly required evidence metadata.

**Steps:**
1. Add a canonical evidence fixture containing `evidence_id`, `kind`, `parent_title`, `source_refs`, `text`, and `scoring_context`. Assert `build_evidence_used` retains stable identity, canonical kind with legacy fallback, parent attribution, bounded source references, matched channels, and selection reasons.
2. Keep the legacy fields in `evidence_used` additively so existing consumers remain compatible; update exact expected records in the named pipeline tests.
3. Add `experience_evidence_summary` and `uncertainties` to `_REUSABLE_RECORD_REQUIRED_FIELDS`, so older reusable records fail closed into recomputation rather than incomplete reconstruction.
4. Persist `candidate_profile_id` and `candidate_profile_revision` in the analysis record and forward them, together with the saved experience summary and uncertainties, through `_rebuild_reused_record` into `build_cv_analysis_record`.
5. Extend `_complete_reusable_record` with the new fields and add a fresh-versus-reused test containing an unresolved professional-experience requirement. Assert equality of evidence classifications, supporting IDs, uncertainty IDs, candidate-profile identity, and requirement coverage, excluding only intentional reuse metadata.
6. Run `uv run pytest tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`.

**Verification:**
- Every `supporting_evidence_id` in requirement coverage can be resolved through the compact evidence view or the full evidence payload without guessing legacy fields.
- Exact reuse preserves `experience_evidence_summary`, uncertainty identifiers, and candidate-profile identity.
- Legacy reusable records missing the new fields are recomputed and do not silently return a degraded reused record.

**Exit Criteria:** Task 4 tests pass and evidence identity/reuse metadata are preserved across fresh, reused, and late-stage pipeline records.

### Task 5: Run cross-stage proof and reconcile maintained documentation

**Purpose:** Prove the four corrected contracts together and leave the maintained pipeline documentation aligned with the implementation.

**Task Function:** integration verification and documentation reconciliation

**Template Profile:** unresolved

**Specification Coverage:** All validated findings and all implementation outcomes.

**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- `tests/test_enrich.py`, `tests/test_vector_search.py`, `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`, and `tests/test_pipeline_agentic_late_stage.py`.
- `docs/pipeline.md`: Stage Responsibilities, Candidate Evidence Projection, and Ranking-V2 Fixed Baseline sections.

**Dependencies:** Tasks 1, 2, 3, and 4

**Authority:**
- Preauthorized local actions: add one deterministic cross-contract fixture/assertion, reconcile the named documentation sections with final field names and semantics, and run the final verification commands.
- Stop for: any failing focused test, a changed public field contract not represented in the plan, or evidence that the reviewed base revision cannot be reproduced in the isolated worktree.

**Steps:**
1. Add or extend one deterministic fixture that contains a multiword job requirement, an experience-only supported technology, a rejected/claimed-only technology, typed language/location facts, canonical evidence IDs, and reusable uncertainty metadata. Assert the data at each handoff: `enrich`, `vector_search`, `pipeline_stage_runner`, `ai_score`, and `agentic_cv_analysis`.
2. Update `docs/pipeline.md` to document the demonstrated-technology eligibility rule, raw-versus-model-visible scorer diagnostics, canonical compact evidence identity, and reuse fail-closed behavior.
3. Run the complete focused suite:
   `uv run pytest tests/test_enrich.py tests/test_vector_search.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_agentic_cv_analysis.py tests/test_evidence.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`
4. Run repository-level syntax proof:
   `uv run python -m compileall src/fitcv`
5. Review the diff against the reviewed base commit and confirm no files outside the plan targets changed and no unrelated current-worktree edits were copied into the implementation branch.

**Verification:**
- The cross-contract fixture proves requirement retention, supported-technology retrieval, scorer visibility, evidence attribution, and reuse equivalence in one trace.
- The focused suite and `compileall` command pass from a clean isolated worktree.
- Documentation states the implemented contracts without promising the excluded workload-dependent risks.

**Exit Criteria:** All validated findings have code and regression coverage, the complete focused suite passes, documentation is reconciled, and the final diff contains only plan-scoped changes.

## Verification

Task-local verification is required after each task; the dependent task does not start after a failed task-local command. Final verification requires all of the following from the isolated worktree based on `6fdfcc92f3119766c213bf82105c8e709201bdc8`:

1. `uv run pytest tests/test_enrich.py tests/test_vector_search.py tests/test_ai_score.py tests/test_scoring_input_integrity.py tests/test_agentic_cv_analysis.py tests/test_evidence.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`
2. `uv run python -m compileall src/fitcv`
3. A diff review confirming the final scorer request and diagnostics share the same selected payload, the no-evidence gate remains intact, and no unsupported technology enters retrieval.
4. A fresh-versus-reused analysis comparison confirming equal evidence classifications, supporting IDs, uncertainty IDs, and candidate-profile identity.

No provider calls, browser checks, publication, or destructive cleanup are required for this implementation plan. Backend proof is supplied by deterministic boundary tests, failure-path assertions, final persisted-record assertions, and fresh automated output.

## Completion Criteria

- All eight validated findings are addressed by Tasks 1 through 4.
- The two workload-dependent review risks remain explicitly out of implementation scope and are not presented as fixed defects.
- Focused and final verification commands pass from the isolated reviewed-base worktree.
- Existing legacy fields and the no-attributable-evidence scoring gate remain compatible.
- `docs/pipeline.md` accurately describes the resulting contracts.
- No unrelated dirty-checkout changes are included.
