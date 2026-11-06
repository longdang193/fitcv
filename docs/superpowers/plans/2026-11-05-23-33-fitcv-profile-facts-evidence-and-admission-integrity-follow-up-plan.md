---
layer: change
artifact_type: plan
contract_version: "1"
status: active
template_id: implementation-plan
name: fitcv-matching-accuracy-and-admission-integrity-follow-up
targets:
  - src/fitcv/candidate.py
  - src/fitcv/fit_factors.py
  - src/fitcv/ai_score.py
  - src/fitcv/evidence.py
  - src/fitcv/ranking.py
  - src/fitcv/prompts/templates/ranking_ai_score_v2.md
  - src/fitcv/enrich.py
  - src/fitcv/rule_filter.py
  - src/fitcv/job_sources.py
  - src/fitcv/ats_export.py
  - src/fitcv/personio_export.py
  - src/fitcv/vector_search.py
  - config/runtime/pipeline.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/scan_worker.py
  - tests/test_candidate.py
  - tests/test_fit_factors.py
  - tests/test_ai_score.py
  - tests/test_ranking.py
  - tests/test_ranking_contract.py
  - tests/test_evidence.py
  - tests/test_enrich.py
  - tests/test_rule_filter.py
  - tests/test_job_sources.py
  - tests/test_ats_export.py
  - tests/test_personio_export.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_pipeline_store.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_scoring_input_integrity.py
  - tests/fixtures/fitcv_scoring_input_integrity_profile.yaml
  - tests/fixtures/fitcv_scoring_input_integrity_job.json
---

# FitCV Matching Accuracy, Profile Facts, Evidence, And Admission Integrity Follow-Up Plan

## Goal

Correct the validated matching-accuracy defects that can reject a relevant job
before compatibility scoring, remove mandatory candidate facts from the scorer
prompt, present contradictory evidence about the same requirement, or make
retrieval and score-availability diagnostics describe a different population or
channel than the one actually used.

The implementation preserves pipeline.vector_search_top_n == 50,
pipeline.ai_score_top_n == 50, the 12,000-character ranking request limit,
and the current holistic_ai_only baseline until a labeled calibration cohort
justifies a policy change. Explicit user exclusions remain hard exclusions.

Review basis:

- Repository longdang193/fitcv, branch main, commit
  42da99f313e6248ab6723a0f5c887c5510e69d18.
- Completed sequential GPT-5.6-Sol / High and GPT-6 / High GitHub reviews.
- Published-plan review by GPT-5.6-Sol / High at commit
  e32a6b0142a9760f638fdb12522110cab3d30e8f identified five actionable gaps:
  missing pipeline-store ownership and migration proof, Gem-only acquisition
  coverage, incomplete v2 language-schema handling, an insufficient final-request
  acceptance probe, and an underspecified decimal experience-bound contract.
- Attached profile-level verdict supplied in the task context.
- The attached verdict directly reproduced: missing fit-context rejection,
  loss of ongoing education and language-level facts, and incorrect project
  evidence selection/skill contradiction.
- The follow-up verdicts supplied in the task context confirmed the correlated
  title/role-family penalty, candidate-denominated
  description overlap, bounded query-order bias, post-retrieval evidence gap,
  generic API-token limitation, and score-state sorting behavior; GPT-6 also
  identified the missing hybrid audit-sample propagation and conditional
  lexical-as-vector fallback path.
- Completed review artifacts are retained outside the repository.
- Final PR review at commit 74ce9c019a1eefc8a10f9637fd70ea334c76ef6f
  identified three remaining P2 gaps: neutral lexical skill defaults could
  qualify unrelated jobs for rescue, URL-only ranked rows could resolve to the
  first of two manifest identities sharing a URL, and malformed string values
  such as `"false"` could be coerced to native language `true`.

## Implementation Outcomes

### Authoritative scorer-visible candidate facts

Language levels and dimensions (level, native, read, write, speak), ongoing
education dates, degree/field identity, and other mandatory candidate facts
survive profile convergence, evidence projection, candidate bounding, and final
prompt rendering. mandatory_core_complete is true only when required fact IDs
and values are present in the actual model-visible payload.

### Requirement-faithful evidence and coverage

Evidence attribution distinguishes parent metadata, declared claims, related
matches, and source-excerpt proof. Requirement coverage and selected evidence
are derived from one post-selection assessment, so a requirement cannot appear
as both demonstrated and missing in the same scorer input. Partial skill entity
lists never erase canonical or raw requirements.

### Recall-preserving admission

Unknown or failed extraction is not treated as a confirmed candidate/job
mismatch. Jobs with usable raw descriptions or substantive mandatory facts reach
retrieval; explicit user exclusions still reject. Semantically nonblank
mandatory-only enrichment is retained, and unresolved enrichment remains an
explicit incomplete/manual-review state rather than a silently valid or silently
lost scoring input.

### Stable retrieval and truthful diagnostics

Candidate query construction is stable under profile ordering and includes
canonical nested project evidence. Provider acquisition, vector fallback, and
lexical rescue report their actual channel participation and cutoff decisions.
The durable admission ledger contains one truthful outcome for every eligible
job, while bounded checkpoint samples remain bounded.

Hybrid retrieval propagates its configured below-cutoff audit sample, records
the effective retrieval strategy and channel provenance, and does not count a
lexical fallback as independent semantic evidence. Lexical-only rescue is
bounded, relevance-qualified, and records the rescued and displaced jobs.

Result contracts distinguish AI score availability from retrieval ordering:
an unscored job remains explicitly unscored and is never represented as a zero
compatibility score. UI copy is outside this plan because the exact label was
not verified in the scoped source; the source-confirmed backend score-state
contract is the required invariant.

### Regression and acceptance proof

A sanitized BI working-student fixture reproduces the attached verdict and
proves that enrollment, German B1, practical Power BI work, and SQL evidence
remain visible and correctly classified. Additional tests cover adjacent-title,
partial-enrichment, fallback, order-permutation, audit-sample, score-state,
cutoff, and over-budget cases.

## Execution Approach

- Mode: inline sequential
- Coordination: git-tracked
- Required skills: skill-plan-document-reviewer, skill-backend-verification, skill-test-driven-development, skill-code-standards, skill-verification-before-completion
- Isolation: task-specific isolated worktree from 42da99f313e6248ab6723a0f5c887c5510e69d18; preserve the current dirty workspace unchanged
- Commit policy: no commits during execution
- Preauthorized local actions: edit only the listed source, test, fixture, and prompt files; run the declared local verification commands; create the task worktree without changing the current checkout
- User-approval actions: push, merge, publication, changing score weights or final cutoff limits, provider/network calls, destructive cleanup, or editing unrelated working-tree files
- Parallel ownership: none; ai_score.py, evidence.py, and pipeline admission contracts are shared serialization points
- Sequential fallback: execute Tasks 1 through 7 in order and stop at the first failed task-local proof before changing downstream contracts

## Coordination State

- Coordination owner: single lead controller
- Coordination schema: 2
- Branch: main
- Base commit: 42da99f313e6248ab6723a0f5c887c5510e69d18
- Expected workspace: current checkout retains unrelated uncommitted source-config and exploratory artifacts; implementation runs in an isolated worktree
- Next action: restore the missing `frontend/dist` build prerequisite and rerun the full suite; implementation-scope checks are complete
- Blockers: full-suite verification is environment-blocked by the absent `frontend/dist` directory; no matching-pipeline failure is unresolved
- Execution worktree: C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-matching-accuracy\JOB-PROJECT
- Execution base: 07e2ec6c13b7c34ccdad91e6041a742461d698c4

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | complete | isolated worktree | Codex | none | candidate fact visibility and completeness tests | 158 focused tests; final-request probe; language/schema tests |
| Task 2 | complete | isolated worktree | Codex | Task 1 | evidence attribution and requirement-consistency tests | 130 evidence-focused tests; existing implementation satisfied contract |
| Task 3 | complete | isolated worktree | Codex | Task 1 | admission and enrichment recall tests | 55 focused tests; raw-description/mandatory-only/decimal coverage |
| Task 4 | complete | isolated worktree | Codex | Task 3 | source acquisition and cutoff recall tests | 588 provider/app tests; explicit acquisition_limit and description-aware filtering |
| Task 5 | complete | isolated worktree | Codex | Tasks 1-4 | query-order, audit-sample, effective-channel, fallback/rescue, and role/overlap tests | 30 retrieval-focused tests; deterministic technology/project hints; rescue evidence |
| Task 6 | complete | isolated worktree | Codex | Tasks 1-5 | complete admission ledger, score-state, and final-prompt manifest tests | additive SQLite migration and post-ranking round-trip test; focused suite green |
| Task 7 | pending | isolated worktree | Codex | Tasks 1-6 | end-to-end fixture, focused suite, full suite, compile, diff checks | focused suite, compile, and diff checks pass; full suite is blocked by absent `frontend/dist` |

## Validated Scope And Non-Goals

The plan includes only findings confirmed by source inspection, both completed
model reviews, or the attached direct reproduction:

- candidate language and education facts can be lost before the scorer while
  diagnostics still claim completeness;
- broad parent/claim references can cause metadata-derived skill support to win
  over stronger source excerpts;
- selected evidence and exact skill coverage can disagree in one prompt;
- missing_fit_context can reject a job when raw text and mandatory facts are
  useful but classification fields are absent;
- semantically blank enrichment ignores mandatory fact families;
- source acquisition and provider title/keyword caps can prevent retrieval from
  seeing relevant jobs;
- candidate query hints are profile-order-sensitive;
- vector fallback/rescue diagnostics can describe a semantic strategy when the
  admitted rows are lexical-only;
- configured hybrid shortlist audit sampling can be dropped before admission
  diagnostics, making below-cutoff jobs look unavailable;
- a conditional non-semantic embedding fallback can be fused as a second
  lexical channel unless effective channel provenance is explicit;
- lexical-only rescue can displace the last fused row without a recorded
  confidence policy;
- score-descending results place null AI scores after scored rows; the backend
  behavior is confirmed, but the exact UI label and Wabtec's historical score
  state are not established by the scoped source;
- admission and scorer diagnostics can describe an incomplete or pre-budget
  population rather than the final model-visible input.

This plan does not change holistic_ai_fit/structured_fit weights, remove the
applicant-count policy, weaken explicit title/contract exclusions, increase the
final scored-job cutoff, or claim a live score improvement without a labeled
provider-backed evaluation. It does not assert that Wabtec actually missed the
cutoff, had a particular historical rank, used a specific embedding backend, or
had a null AI score. It does not treat role-family vocabulary divergence as an
active defect without an unresolved mapping signal, and it does not rename an
unverified UI label from the five-file review alone. Those decisions remain
follow-up calibration or surface-verification work.

## Task Breakdown

### Task 1: Preserve mandatory candidate facts through rendering

**Purpose:**
- Make the final ranking payload retain mandatory language and education facts, including values that are currently lost by legacy adaptation or tail trimming.

**Task Function:**
- Normalize and bound candidate facts without losing required identity, value, provenance, or enrollment semantics.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: source-contract change with high correctness impact and bounded file scope

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: independently verify final model-visible values and failure-path completeness

**Specification Coverage:**
- Authoritative scorer-visible candidate facts; mandatory_core_complete must reflect actual final values, not only field presence.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify src/fitcv/candidate.py:CANDIDATE_PROFILE_V2_FIELD_REGISTRY, adapt_candidate_profile_to_v2, validate_candidate_profile_v2, and converge_candidate_profile_for_runtime.
- Inspect and modify src/fitcv/fit_factors.py:_candidate_level and build_candidate_fit_context.
- Inspect and modify src/fitcv/ai_score.py:build_ranking_job_input, build_ranking_request, and the nested bound_candidate_summary contract.
- Verify tests/test_candidate.py, tests/test_fit_factors.py, and tests/test_ai_score.py.

**Dependencies:**
- None; current base commit and the attached sanitized BI reproduction are the inputs.

**Authority:**
- Preauthorized local actions: edit the listed candidate/factor/scorer files and their focused tests; run the declared Python test commands.
- Stop for: changing the 50-job/12,000-character limits, changing score weights, modifying unrelated working-tree files, or needing provider/network access.

**Steps:**
- [x] Step 1: Extend CANDIDATE_PROFILE_V2_FIELD_REGISTRY and adapt_candidate_profile_to_v2 so already-v2 and legacy profiles preserve complete language records, including level, native, read, write, speak, and source_refs; validate those fields in validate_candidate_profile_v2; make ranking language normalization call the existing _candidate_level resolver rather than reading only level.
- [x] Step 2: Add typed education matching for degree, field, and active enrollment dates; keep an ongoing relevant degree ahead of optional education records when the job has an education or enrollment requirement.
- [x] Step 3: Replace tail-only candidate trimming with required-fact reservation. Serialize mandatory candidate records first, then trim optional records and text while preserving required IDs, values, and source references.
- [x] Step 4: Compute mandatory_core_complete by reconciling required fact IDs and normalized values against the final model_visible candidate payload. Set omitted or value-mismatched requirements to explicit nonzero omission records before provider invocation.
- [x] Step 5: Add regression tests for the attached BI fixture and both profile shapes: legacy-to-v2 conversion and already-v2 validation must preserve the language dimensions; reversing education order must not remove the active master’s record; German B1 must retain its level; native/read/write/speak-only language entries must normalize consistently; and a bounded payload must never report complete after required-value loss.

**Verification:**
- [x] python -m pytest -q tests/test_candidate.py tests/test_fit_factors.py tests/test_ai_score.py -k "language or education or mandatory or candidate or budget"
- Expected: all focused tests pass; final rendered payload contains the required language level, enrollment dates, and fact IDs; omission diagnostics become nonzero when a required value is intentionally removed.
- [x] Exercise build_ranking_job_input() as the earlier-stage serialization check, then build the full build_ranking_request() and inspect its final rendered/model-visible candidate payload. Assert required IDs and normalized values against that final payload and assert the existing 12,000-character request-budget result.

**Exit Criteria:**
- Required candidate facts survive convergence and budgeting, and completeness diagnostics are value-aware and test-proven.

### Task 2: Make evidence attribution and requirement coverage consistent

**Purpose:**
- Prevent metadata-only or inherited references from being presented as direct proof and eliminate contradictory matched/missing requirement states.

**Task Function:**
- Build one requirement assessment from canonical job requirements and the selected source evidence.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: cross-module contract change with direct scoring-bias risk

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: verify attribution boundaries and prompt-level consistency with negative controls

**Specification Coverage:**
- Requirement-faithful evidence; each requirement receives one consistent status: demonstrated, declared, related, or no_evidence.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify src/fitcv/candidate.py:_adapt_legacy_parent and converge_candidate_profile_for_runtime.
- Inspect and modify src/fitcv/evidence.py:build_required_skill_descriptors, project_candidate_evidence, select_ranking_evidence, and score_evidence_item_by_channel.
- Inspect and modify src/fitcv/ai_score.py:build_ranking_job_input and build_ranking_request.
- Update src/fitcv/prompts/templates/ranking_ai_score_v2.md to consume the single assessment contract.
- Verify tests/test_candidate.py, tests/test_evidence.py, and tests/test_ai_score.py.

**Dependencies:**
- Task 1 complete; required candidate fact IDs and final-prompt visibility are available.

**Authority:**
- Preauthorized local actions: edit the listed evidence/scorer/prompt files and focused tests; add the requirement-status assertions needed for the contract.
- Stop for: adding a second parallel evidence contract, weakening credential evidence when a credential is explicitly required, changing score weights, or modifying unrelated files.

**Steps:**
- [x] Step 1: Preserve claim-to-parent attribution separately from excerpt-to-requirement proof. Parent metadata may aid retrieval, but it must not make an unrelated child excerpt demonstrated.
- [x] Step 2: Union required_skill_entities, canonical required skills, and raw required skills by canonical identity; retain qualifiers and source IDs from every representation.
- [x] Step 3: Make evidence scoring distinguish source-excerpt action/tool/outcome proof from metadata-only relevance. Keep metadata as related or retrieval coverage rather than demonstrated.
- [x] Step 4: After evidence selection, compute one per-requirement assessment and derive matched, missing, mandatory-fact statuses, and selected evidence IDs from that assessment. Do not render the same requirement as both demonstrated and missing.
- [x] Step 5: Use the second evidence slot for uncovered requirement coverage or a distinct strong project/professional proof item; preserve valid credential evidence when the requirement is credential-specific.
- [x] Step 6: Add negative tests: an AI-course metadata row cannot prove SQL without a source excerpt; a Power BI dashboard bullet is practical evidence; a project stack mention is weaker related evidence; incomplete entity rows do not erase canonical skills; and prompt fields agree with the assessment.

**Verification:**
- [x] python -m pytest -q tests/test_candidate.py tests/test_evidence.py tests/test_ai_score.py -k "reference or attribution or support or coverage or missing or evidence"
- Expected: all focused tests pass; no selected item is demonstrated solely from inherited metadata; missing and selected evidence statuses are mutually consistent.
- [x] Render the sanitized BI scorer prompt and inspect the final JSON fields for SQL and Power BI status, evidence IDs, and support basis.

**Exit Criteria:**
- Evidence selection, requirement coverage, and scorer prompt use one coherent requirement assessment with provenance-aware support states.

### Task 3: Separate extraction uncertainty from job eligibility

**Purpose:**
- Keep relevant jobs with usable source text or substantive mandatory facts in retrieval while preserving explicit exclusion behavior and truthful incomplete states.

**Task Function:**
- Change deterministic admission and enrichment blankness so missing classification is not treated as confirmed incompatibility.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: pre-score admission policy with direct recall impact

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: validate pass/mark/reject behavior across unknown, mismatch, fallback, and explicit exclusion cases

**Specification Coverage:**
- Recall-preserving admission; missing fit context and mandatory-only enrichment must not discard informative jobs before retrieval.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify src/fitcv/rule_filter.py:check_fit_context, check_freshness, apply_pre_enrichment_global_filters, and apply_rule_filters.
- Inspect and modify src/fitcv/enrich.py:EnrichmentOutput, _is_semantically_blank_enrichment_row, _coerce_field, and enrich_batch; define the accepted numeric representation for years_experience_min/max and preserve it through structured validation and persistence.
- Inspect and modify src/fitcv/pipeline.py:run_pipeline and src/fitcv/pipeline_stage_runner.py:execute_enrich_stage / execute_rule_filter_stage where incomplete status is persisted.
- Verify tests/test_rule_filter.py, tests/test_enrich.py, and tests/test_pipeline.py.

**Dependencies:**
- Task 1 complete; the scorer fact contract defines which job facts are substantive.

**Authority:**
- Preauthorized local actions: edit listed admission/enrichment/pipeline files and tests; add explicit diagnostic fields for unknown/extraction-failed states.
- Stop for: removing explicit user exclusions, changing applicant-count policy without a labeled cohort, changing final cutoff limits, or requiring live enrichment-provider calls in tests.

**Steps:**
- [x] Step 1: Route title outcomes through _get_selected_rule_filter_codes() so unselected title signals become marks; preserve hard behavior only when the signal is explicitly selected.
- [x] Step 2: Make freshness independently opt-in: a missing global_job_filters.max_age_days disables freshness rather than implying 30 days; persist the effective global filter settings.
- [x] Step 3: Treat absent location_type, seniority, role family, and domain as unknown/extraction warnings when raw description or substantive requirements exist. Reject only when no usable source text or substantive requirement remains, or when an explicit hard exclusion fails.
- [x] Step 4: Expand _is_semantically_blank_enrichment_row() to recognize qualifications, education, certifications, employment constraints, mandatory clauses, actual location, language requirements, and validated decimal experience bounds. Update EnrichmentOutput.years_experience_min/max and _coerce_field() together so a valid decimal such as 1.5 is not truncated to 1; preserve the same numeric value through structured validation, enrichment persistence, and scorer input.
- [x] Step 5: Preserve raw job text and mark mandatory_input_incomplete when recovery cannot produce a complete scorer contract; do not emit a normal valid score from incomplete mandatory input.
- [x] Step 6: Add tests for the attached missing-fit-context reproduction, mandatory-language/certification-only enrichment, explicit title exclusion, unconfigured freshness, raw-text fallback behavior, and a decimal experience-bound round trip such as 1.5 through coercion, EnrichmentOutput, persistence, and scorer input.

**Verification:**
- [x] python -m pytest -q tests/test_rule_filter.py tests/test_enrich.py tests/test_pipeline.py -k "fit_context or title or freshness or blank or fallback or mandatory or extraction"
- Expected: the BI job with usable description passes to retrieval despite absent classification fields; explicit exclusions still reject; mandatory-only enrichment is nonblank; unknown freshness does not reject.
- [x] Directly inspect persisted filter and enrichment records and assert each rejected job has a confirmed reason rather than an extraction-unknown reason.

**Exit Criteria:**
- Admission preserves informative jobs, separates unknown from mismatch, and never presents incomplete enrichment as a complete scorer input.

### Task 4: Decouple source acquisition from final scoring admission

**Purpose:**
- Prevent provider ordering, title-only discovery, and a 50-job scanner cap from hiding relevant postings before FitCV retrieval and scoring.

**Task Function:**
- Add a bounded acquisition capacity distinct from the fixed final shortlist/scorer capacities.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: provider-boundary recall change with integration impact

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: verify provider request bounds, pagination, deduplication, and nonmatching-title description recall

**Specification Coverage:**
- Relevant jobs remain eligible for semantic matching after source acquisition; final scored-job budget remains 50.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify src/fitcv/job_sources.py:ScannerRequest, build_scanner_request, provider acquisition functions, and acquire_scanner_jobs.
- Inspect and modify src/fitcv/ats_export.py:_matches and the Greenhouse, Ashby, Lever, Gem, and Workday pre-detail acquisition paths; inspect and modify src/fitcv/personio_export.py title filtering and fallback detail loading.
- Inspect and modify callers in src/fitcv_cp/app.py and src/fitcv_cp/scan_worker.py so acquisition capacity is explicit and separate from pipeline scoring settings.
- Verify tests/test_job_sources.py, tests/test_ats_export.py, tests/test_personio_export.py, tests/test_fitcv_cp/test_scan_worker.py, tests/test_pipeline.py, and tests/test_ranking.py.

**Dependencies:**
- Task 3 complete; admission semantics distinguish discovery filtering from explicit user exclusions.

**Authority:**
- Preauthorized local actions: edit the listed source-acquisition callers and tests; add bounded request metadata and provider-cap diagnostics.
- Stop for: unbounded provider pagination, bypassing SSRF/provider safety checks, increasing final shortlist/scorer limits, or external provider calls during tests.

**Steps:**
- [x] Step 1: Add an explicit acquisition bound to ScannerRequest and its callers, defaulting to the existing validated upper bound of 200; retain max_jobs compatibility at the request boundary while making the distinction visible in diagnostics.
- [x] Step 2: Keep vector_search_top_n and ai_score_top_n at 50; use acquisition capacity only to provide a broader candidate pool for downstream retrieval.
- [x] Step 3: Remove title-only hard discovery filtering before detail retrieval across every keyword-constrained acquisition path: Greenhouse, Ashby, Lever, Gem, Workday, and Personio. Fetch bounded detail rows, then apply description-aware relevance downstream. Preserve provider safety and timeout bounds.
- [x] Step 4: Make Workday keyword behavior explicit: do not rely on provider searchText alone to establish relevance; either request the bounded broad feed or record the provider-query limitation and ensure the local detail path can recover description-relevant adjacent-title jobs.
- [x] Step 5: Record provider truncation, title-discard, keyword-query, and fetched-detail counts so recall losses are measurable.
- [x] Step 6: Add provider-specific tests proving a relevant description with an adjacent title survives acquisition for each affected path, the Workday query behavior is bounded and observable, deduplication remains stable, and the pipeline/ranking contract still admits at most 50 jobs for final scoring.

**Verification:**
- [x] python -m pytest -q tests/test_job_sources.py tests/test_ats_export.py tests/test_personio_export.py tests/test_fitcv_cp/test_scan_worker.py tests/test_pipeline.py tests/test_ranking.py
- Expected: bounded acquisition requests pass; provider safety tests remain green; nonmatching-title but description-relevant fixtures are returned for downstream filtering; final pipeline limits remain unchanged.
- [x] Assert the acquisition diagnostics distinguish fetched, provider_capped, title_discarded, and downstream_not_admitted counts.

**Exit Criteria:**
- Provider acquisition no longer silently acts as the final compatibility filter, and its bounded losses are observable.

### Task 5: Make candidate query construction and fallback behavior order-stable

**Purpose:**
- Remove profile-order bias from vector hints and make hybrid audit, lexical fallback, and rescue behavior truthful and relevance-qualified.

**Task Function:**
- Stabilize bounded query component selection, preserve configured below-cutoff audit rows, and reconcile diagnostics with actual channel provenance and ranks.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: deterministic retrieval change with measurable permutation invariants

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: verify profile permutations preserve required query coverage and fallback diagnostics

**Specification Coverage:**
- Stable retrieval; canonical project evidence and role families participate without list-order bias; below-cutoff and fallback outcomes identify the actual retrieval channel.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify config/runtime/pipeline.yaml:shortlist_audit_sample_n and retrieval strategy defaults.
- Inspect and modify src/fitcv/ranking.py:compute_title_relevance, compute_must_have_match, and role-family scoring helpers.
- Inspect and modify src/fitcv/vector_search.py:_profile_technology_inventory, _bounded_profile_technology_hints, _description_overlap, build_candidate_query_components, _lexical_search_result, _hybrid_search_result, and run_vector_search.
- Verify tests/test_vector_search.py, tests/test_ranking.py, tests/test_ranking_contract.py, and add permutation/fallback fixtures under tests/fixtures/fitcv_scoring_input_integrity_job.json.

**Dependencies:**
- Task 4 complete; the retrieval input pool is broader and acquisition diagnostics exist.

**Authority:**
- Preauthorized local actions: edit the listed vector-search functions and tests; add deterministic diagnostic fields for fallback and rescue decisions.
- Stop for: changing final top-50 admission policy, changing embedding providers, weakening lexical relevance requirements, or using live embeddings in tests.

**Steps:**
- [x] Step 1: Select role-family, skill, technology, and project-evidence hints by deterministic relevance, coverage, and cross-project diversity; apply stable lexical tie-breaking after coverage quotas rather than raw profile order.
- [x] Step 2: Use canonical nested evidence and raw occurrence counts before deduplication; preserve technology frequency information while keeping the final bounded query deterministic.
- [x] Step 3: Ensure profile list permutations produce the same query coverage set and stable candidate-query fingerprint; retain the current full-eligible-population hybrid ranking before the fixed top-50 fusion cutoff.
- [x] Step 4: Pass pipeline.shortlist_audit_sample_n explicitly into _hybrid_search_result and derive below-cutoff audit rows from the fused population so configured audit rows are not lost between lexical retrieval and admission diagnostics.
- [x] Step 5: Propagate effective strategy and channel provenance. When a non-semantic embedding backend returns lexical fallback rows, do not fuse those rows as an independent semantic channel; report lexical-only or degraded-hybrid behavior explicitly.
- [x] Step 6: Require affirmative lexical relevance and a bounded confidence policy for lexical-only rescue; persist both rescued and displaced job IDs with vector, lexical, fused, and rescue evidence.
- [x] Step 7: Keep required-skill matching and synonym expansion conservative: add only reviewed phrase-level or evidence-backed relationships, preserve exact/related match types, and do not make bare API, AI, software, or framework universal matches.
- [x] Step 8: Add tests for the attached 60-job fallback probe, missing-vector fallback, non-semantic backend fallback, audit-sample propagation, partial-vector rescue, description-overlap breadth, cross-functional role alignment, capability aliases, and project-order permutations.

**Verification:**
- [x] python -m pytest -q tests/test_vector_search.py tests/test_ranking.py tests/test_ranking_contract.py -k "query or fallback or rescue or hybrid or order or permutation or audit or overlap or role or capability"
- Expected: audit rows honor the configured count; fallback diagnostics name the effective channel; lexical fallback is not double-counted as semantic retrieval; rescue decisions include a relevance reason and displaced ID; query fingerprints and required hint coverage are invariant under profile ordering; broad candidate inventories do not reduce unchanged job-side coverage.

**Exit Criteria:**
- Retrieval is order-stable and every fallback/rescue diagnostic describes the actual admitted channels.

### Task 6: Make admission and scorer diagnostics authoritative

**Purpose:**
- Ensure every eligible job has one truthful admission outcome, every scorer diagnostic reflects the exact request and evidence visible to the model, and score availability cannot be mistaken for compatibility quality.

**Task Function:**
- Unify production/stage admission accounting and persist final-input manifests from the rendered request.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: cross-stage observability and resume-integrity change

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: verify complete ledger cardinality, truthful cutoff reasons, checkpoint boundedness, and prompt-manifest equality

**Specification Coverage:**
- Evidence visibility and below-cutoff decisions remain auditable without claiming omitted facts were present; valid, unscored, failed, and unavailable score states remain distinct.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-code-standards

**Files And Symbols:**
- Inspect and modify src/fitcv/ai_score.py:build_ranking_request and build_ranking_input_diagnostics.
- Inspect and modify src/fitcv/pipeline.py:_materialize_scoring_shortlist and run_pipeline.
- Inspect and modify src/fitcv/pipeline_stage_runner.py:execute_shortlist_stage and execute_ranking_stage.
- Inspect and modify src/fitcv/pipeline_store.py:persist_shortlist_admission_ledger and its existing SQLite schema/row serialization; extend the current ledger additively rather than creating a second admission store, update final score-state fields after ranking, and preserve migration compatibility for existing databases.
- Inspect src/fitcv_cp/sqlite_store.py:query_run_jobs and _score_state_for_job and src/fitcv_cp/app.py:_sort_enriched_rows; modify only the existing score-state/result contract needed to propagate score_status and failure_code, preserving score_desc ordering semantics unless a labeled product decision changes it.
- Verify tests/test_ai_score.py, tests/test_pipeline.py, tests/test_pipeline_store.py, tests/test_pipeline_stage_resume_parity.py, tests/test_pipeline_checkpoint_contract.py, tests/test_fitcv_cp/test_app.py, and tests/test_fitcv_cp/test_sqlite_store.py.

**Dependencies:**
- Tasks 1 through 5 complete; final candidate/evidence/retrieval contracts are settled.

**Authority:**
- Preauthorized local actions: edit the listed pipeline/scorer contracts and tests; add bounded manifest fields and deterministic fingerprints.
- Stop for: adding a second admission ledger, making unbounded checkpoint payloads, or changing final scoring limits/weights.

**Steps:**
- [x] Step 1: Use one admission implementation for production and stage paths. Persist one compact outcome for every eligible job with channel participation, rank, cutoff, rejection, or scoring reason.
- [x] Step 2: Distinguish not_returned_in_raw_hits, after_fused_cutoff, scoring_cutoff, input_budget_exceeded, provider_failed, and explicit filter rejection; do not label a below-cutoff competitor as never retrieved.
- [x] Step 3: Initialize diagnostics with request_built false and request_within_budget null; replace them after every scoring attempt with the final request result, including failures.
- [x] Step 4: Persist separate pre-budget, selected, rendered, and model-visible evidence IDs, mandatory omission reasons, field checksums, and the final prompt hash.
- [x] Step 5: Keep checkpoint samples bounded while the durable admission ledger remains complete; round-trip the same manifest through resume and assert stable fingerprints.
- [x] Step 6: Preserve and expose score_status/failure_code alongside ai_score so unscored or failed rows are explicit and never coerced to numeric zero; keep retrieval relevance and AI compatibility as separate fields where the existing result contract supports both.
- [x] Step 7: Add direct persistence tests for the extended pipeline_store ledger, including additive schema migration and post-ranking updates. Force two-to-one evidence reduction, mandatory-budget refusal, below-cutoff ledger rows, unscored/failed score states, resume, and production/stage parity. Do not assert a Wabtec historical score or cutoff without a recorded run artifact.

**Verification:**
- [x] python -m pytest -q tests/test_ai_score.py tests/test_pipeline.py tests/test_pipeline_store.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -k "diagnostic or budget or ledger or cutoff or manifest or resume or parity or score or unscored or migration"
- Expected: model-visible diagnostics equal the rendered request; budget failures are explicit; every eligible job has one truthful outcome; checkpoint samples are bounded and resume-stable; null/failed scores remain distinguishable from valid zero scores.

**Exit Criteria:**
- Persisted artifacts cannot claim facts, evidence, channel ranks, or completeness that the scorer did not actually receive.

### Task 7: Add the end-to-end acceptance cohort and complete verification

**Purpose:**
- Prove the fixes together on the attached BI case and a small labeled cohort without changing production score weights or invoking external providers.

**Task Function:**
- Build deterministic integration regressions and run final backend verification.

**Template Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: final cross-stage validation with broad test surface

**Validator Profile:**
- Controller-selected: unresolved while task is pending
- Selection basis: independent final verification and plan reconciliation

**Specification Coverage:**
- All implementation outcomes and acceptance metrics in this plan.

**Required Skills:**
- skill-backend-verification, skill-test-driven-development, skill-verification-before-completion

**Files And Symbols:**
- Add tests/test_scoring_input_integrity.py.
- Keep the sanitized acceptance cases embedded in the focused test module; no
  separate fixture files are needed for the bounded assertions.
- Verify all focused test files from Tasks 1-6 and the full repository suite.

**Dependencies:**
- Tasks 1 through 6 complete.

**Authority:**
- Preauthorized local actions: add sanitized fixtures/tests and run all declared verification commands in the isolated worktree.
- Stop for: missing test dependencies, any unrelated test failure being fixed in scope, provider/network access, or any required behavior not covered by an exact assertion.

**Steps:**
- [x] Step 1: Encode the sanitized scorer-visible language, education, requirement, and raw-description admission cases in tests/test_scoring_input_integrity.py.
- [x] Step 2: Assert language dimensions and ongoing education remain visible in the final request and admitted jobs retain a diagnostic mark instead of being rejected for missing classification.
- [x] Step 3: Cover adjacent-title, fallback, order-stability, audit-sample, lexical-rescue, score-state, migration, and over-budget behavior in the focused suites owned by Tasks 1-6.
- [x] Step 4: Keep deterministic assertions separate for final-prompt visibility, acquisition/admission behavior, retrieval diagnostics, and ledger score-state persistence.
- [x] Step 5: Run focused tests, compile checks, the full suite, and diff validation; record any pre-existing failures without modifying unrelated code.

**Verification:**
- [x] python -m pytest -q tests/test_scoring_input_integrity.py tests/test_candidate.py tests/test_fit_factors.py tests/test_ai_score.py tests/test_evidence.py tests/test_enrich.py tests/test_rule_filter.py tests/test_job_sources.py tests/test_fitcv_cp/test_scan_worker.py tests/test_vector_search.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py
- Expected: all focused tests pass, including the BI reproduction and all cross-stage invariants.
- [x] python -m compileall -q src/fitcv src/fitcv_cp tests
- Expected: no compile errors.
- [ ] python -m pytest -q
- Expected: the full suite passes; unrelated pre-existing failures are listed with their exact test names if the environment cannot run them.
- [x] git diff --check
- Expected: no whitespace errors.

**Exit Criteria:**
- The complete focused and full verification evidence proves the attached defects are fixed without changing the preserved final limits or score policy.

## Verification

Final artifact-level verification after all tasks:

- python -m pytest -q tests/test_scoring_input_integrity.py tests/test_candidate.py tests/test_fit_factors.py tests/test_ai_score.py tests/test_evidence.py tests/test_enrich.py tests/test_rule_filter.py tests/test_job_sources.py tests/test_fitcv_cp/test_scan_worker.py tests/test_vector_search.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py
- python -m compileall -q src/fitcv src/fitcv_cp tests
- python -m pytest -q
- git diff --check

### Execution Evidence

- Focused suite: `1509 passed, 3 skipped in 132.83s (0:02:12)` after the first PR review fixes.
- Compile check: `python -m compileall -q src/fitcv src/fitcv_cp tests` passed.
- Diff check: `git diff --check` passed.
- Full suite after final-review fixes: `3607 passed, 10 skipped, 3 failed in 260.81s (0:04:20)`.
- The three failures are environmental and outside the matching-pipeline scope:
  `tests/test_fitcv_cp/test_frontend_host.py::test_app_spa_entry_and_deep_links`
  and `tests/test_fitcv_cp/test_frontend_host.py::test_csrf_cookie_issuance_and_unsafe_request_guard`
  receive `503` from `/app` because `frontend/dist` is absent;
  `tests/test_fitcv_local_packaging.py::test_pyinstaller_datas_sources_exist`
  independently reports the same missing `frontend/dist` path.
- Because the full suite is not green, the plan remains `active`; no unrelated
  frontend build or packaging changes were made.
- First PR review findings were fixed before the next review cycle: stable
  run/fingerprint identity resolution for colliding URLs, end-to-end language
  dimension projection, bounded Workday detail fetches, and affirmative lexical
  rescue gating with neutral/missing-score negative tests.
- Final PR review findings were fixed without changing the final shortlist or
  scorer limits: lexical rows now carry an explicit required-skill intersection
  flag and neutral `compute_must_have_match()` defaults cannot qualify rescue;
  ledger updates resolve stable identities separately from unique URL fallback
  and skip ambiguous URL-only rows; candidate validation rejects non-boolean
  language `native` values and ranking projection serializes only real booleans.
- Post-fix focused suite: `1511 passed, 3 skipped in 133.21s (0:02:13)`.

Final proof must show:

- the BI job reaches retrieval when classification fields are absent but raw text and substantive requirements exist;
- language level/dimensions and active education enrollment remain in the final scorer payload;
- mandatory_core_complete reflects required IDs and values after bounding;
- selected evidence has source-excerpt attribution and requirement status is not contradictory;
- partial structured requirement entities do not erase canonical/raw requirements;
- provider acquisition is bounded separately from the final 50-job scorer budget;
- query fingerprints and required hint coverage are stable under profile permutations;
- fallback/rescue diagnostics match actual vector and lexical ranks, including
  non-semantic embedding fallback and lexical-only rescue provenance;
- configured hybrid shortlist audit samples are populated and distinguish
  after_fused_cutoff from unavailable jobs;
- current full-eligible-population hybrid retrieval is preserved before the
  fixed top-50 fusion cutoff;
- every eligible job has one truthful admission outcome and below-cutoff jobs retain channel/cutoff evidence;
- valid zero, unscored, failed, and unavailable score states remain distinct in
  result contracts and are not interpreted as equivalent compatibility values;
- model-visible diagnostics equal the rendered request, including evidence IDs, omission reasons, and prompt hash;
- checkpoint samples remain bounded while the durable ledger remains complete and resume-stable;
- no score-weight or final-cutoff change was introduced by this plan.
- neutral lexical defaults, ambiguous URL-only ledger rows, and malformed
  language-native values have dedicated regression coverage.

## Completion Criteria

The plan is ready for completion verification when:

1. every validated finding has an owning task and a focused regression assertion;
2. candidate facts, job requirements, selected evidence, and scorer diagnostics use one consistent provenance-aware contract;
3. admission distinguishes explicit mismatch from missing or failed extraction;
4. relevant jobs are not silently removed by source caps or title-only discovery before downstream matching;
5. provider fallback, hybrid audit, vector rescue, cutoff, score-state, and scorer-budget outcomes are truthful and auditable;
6. the sanitized BI case and the labeled edge-case cohort pass under the unchanged 50-job and 12,000-character constraints, including broad-profile, cross-functional, and non-semantic-backend cases;
7. focused tests, full tests, compile checks, and git diff --check are fresh and reconciled; and
8. skill-verification-before-completion returns verified before this plan changes from proposed to completed.

The plan must not be marked completed from checked boxes alone.
