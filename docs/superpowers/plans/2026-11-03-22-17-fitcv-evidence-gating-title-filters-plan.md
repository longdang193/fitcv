---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: in_progress
name: fitcv-evidence-gating-title-filters
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/rule_filter.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/job_sources.py
  - src/fitcv_cp/scan_contracts.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - config/policy/cv_analysis.yaml
  - frontend/src/features/pipeline-settings/sections-def.ts
  - frontend/src/features/pipeline-settings/types.ts
  - frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx
  - frontend/src/features/scans/types.ts
  - frontend/src/features/scans/new-scan-dialog.tsx
  - frontend/src/features/scans/scan-detail.tsx
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_ranking_contract.py
  - tests/test_rule_filter.py
  - tests/test_pipeline.py
  - tests/test_job_sources.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - frontend/src/test/pipeline-settings.test.tsx
  - frontend/src/test/scans.test.ts
  - frontend/e2e/integration-flows.spec.ts
  - scripts/run_fitcv_review_e2e.ps1
  - docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV Evidence Gating and Job-Title Filters

## Goal

Correct the validated evidence-gating and persisted-ranking defects, add
deterministic job-title inclusion and exclusion filtering across acquisition
and pipeline paths, and preserve the existing `Loose`, `Full`, and `Strict`
settings contract while proving that the setting is visible and effective.

The implementation must distinguish capability evidence from professional
experience evidence. Projects may support students and entry-level candidates
when the requirement permits that interpretation; senior or explicitly
professional requirements must not be promoted by project evidence alone.

## Review Findings

The findings below were confirmed against the immutable revision
`ead991a950c2a3561511bc98d56e3c36e5212472` after both requested model reviews
completed. No code was changed during review.

1. **High — Loose routing is not seniority-aware.**
   `should_route_loose_experience_review()` and the Loose promotion path in
   `src/fitcv/agentic_cv_analysis.py` can promote project-backed evidence
   without checking candidate seniority, target seniority, or professional
   tenure.
2. **High — Full/Strict evidence gaps do not independently gate readiness.**
   `src/fitcv/evidence.py` computes evidence facts, but the final analysis path
   remains primarily gated by `fit_classification == "skip"`; a high baseline
   result can therefore survive an unresolved professional qualification gap.
3. **High — Title exclusion is unsupported.**
   The scan/request path carries one positive `keywords` list and OR-only
   matching. There is no canonical exclusion predicate shared by uploaded jobs,
   managed scans, and provider acquisition.
4. **Medium — Persisted fit labels are trusted without numeric consistency.**
   `resolve_ranked_job_fit()` accepts a valid persisted `baseline_fit_label`
   without checking that it matches `baseline_fit` and the active thresholds.
5. **Medium — Project-acceptance negation is incomplete.**
   `_project_acceptance_is_affirmed()` can interpret wording such as
   `academic projects are insufficient` as affirmative project acceptance.
6. **Validated non-defect — The compatibility formula is centralized and
   internally consistent.** The active policy is
   `1.0 * holistic_ai_fit + 0.0 * structured_fit`; missing or invalid AI scores
   do not fabricate a baseline. The plan adds boundary and consistency tests,
   but does not change the configured formula or weights.

The attached screenshot/comment about a missing strictness control is not
carried as a new implementation defect: the pinned revision already contains
the schema key, API projection, and UI select for
`cv_analysis.experience_evidence_mode` with `loose`, `full`, and `strict`
options. The existing control is retained and explicitly verified below.

## Plan-review follow-ups

The plan review also identified these justified scope corrections, which are
required before execution:

1. **High — Ranking-label authority is incomplete.** The plan must cover every
   raw-label consumer, not only `resolve_ranked_job_fit()`. Use one canonical
   score/label resolver and route analysis records, pipeline exports, decision
   chains, and checkpoint restoration through it.
2. **High — The active Managed Scan specification was omitted.** Update
   `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`,
   whose current `job_titles` contract is case-insensitive Unicode-substring
   OR matching, so the new include/exclude semantics are authoritative and
   persisted consistently.
3. **High — Seniority authority is underspecified.** Define precedence and
   conflict handling for explicit JD professional wording, normalized target
   seniority, `candidate.preferences.seniority_target`, and
   `profile.years_experience`; unknown or conflicting signals must not allow a
   Loose project-only promotion for senior/professional requirements.
4. **Medium — Provider prefilters may create false negatives.** Positive
   provider search terms must be treated as an optimization only: query each
   inclusion term and union/deduplicate results, or fetch broadly when safe
   recall cannot be demonstrated. Exclusions remain post-acquisition.
5. **Medium — Scan frontend/browser coverage was missing.** Include the
   existing `frontend/src/test/scans.test.ts` and
   `frontend/e2e/integration-flows.spec.ts` in the implementation and proof.
6. **Low — Execution dependency typo.** Final verification is Task 6, not
   Task 5.

## Implementation Outcomes

### Evidence-aware recommendation gating

Loose, Full, and Strict produce explicit capability and professional-evidence
verdicts. Loose can surface a project-backed stretch recommendation only when
the candidate/role context allows it; senior and explicitly professional
requirements remain unverified without professional evidence. Full and Strict
cannot silently present unresolved professional requirements as fully
qualified, while the numeric baseline fit remains separately available.

### Consistent ranking and filtering contracts

Persisted numeric baseline scores and labels are validated against one ranking
contract. The deterministic title predicate supports optional inclusion and
exclusion lists with OR semantics within each list and AND semantics between
the lists, using case-insensitive whole-word or phrase matching. Filter
decisions record the matched exclusion or missing inclusion reason.

### Settings, scan, and regression coverage

The existing strictness selector remains reachable through the pipeline
settings API and UI. Managed scans accept both title lists, provider-level
prefiltering remains an optimization rather than the source of truth, and
post-acquisition filtering applies identically to uploaded and scanned jobs.
Focused backend, API, frontend, and browser-level checks prove the contract.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-backend-verification`, `skill-full-stack-integration`, `skill-frontend-component-engineering`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit only the plan-named files, run focused tests/type checks/builds, inspect source and generated test artifacts, and preserve unrelated untracked files
- User-approval actions: push, merge, publication, destructive cleanup, deleting unrelated artifacts, or changing the reviewed base commit
- Parallel ownership: `none`; evidence, ranking, filter, settings, and scan contracts share runtime and artifact boundaries
- Sequential fallback: complete Tasks 1–2 before ranking hardening, complete Task 3 before scan/UI wiring, then run Task 6 final verification

## Task Breakdown

### Task 1: Make evidence gating seniority- and requirement-aware

**Purpose:**
- Prevent Loose project evidence from promoting senior or explicitly professional requirements, and make Full/Strict unresolved professional requirements visible to the final recommendation gate without changing the baseline score formula.

**Task Function:**
- Implement the shared evidence policy and reconcile analysis routing with the policy.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: high-impact backend behavior with existing source-of-truth helpers and bounded policy changes.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: task-local backend tests and final verification provide the required independent assertions.

**Specification Coverage:**
- Loose, Full, and Strict must distinguish capability evidence from professional evidence.
- Student/entry-level project evidence may support a requirement when appropriate.
- Senior and explicitly professional requirements require professional evidence unless the JD explicitly accepts project evidence.
- Baseline fit and evidence readiness remain separate outputs.
- Authority precedence is deterministic: explicit JD professional wording is
  strongest, normalized target seniority is next, candidate seniority
  preference is contextual, and profile tenure is supporting evidence rather
  than a selector. Unknown or conflicting signals are conservative for
  professional gating.
- Decision matrix: Loose may produce a project-backed stretch only for an
  entry-level/compatible context without an explicit professional requirement;
  Full may credit directly demonstrated capability while exposing unresolved
  professional evidence separately; Strict requires professional evidence for
  experience-classified requirements unless the JD explicitly accepts projects.
- The mode is never auto-selected from student/senior status; the existing
  run-level `cv_analysis.experience_evidence_mode` remains authoritative.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:experience_requirement_policy`, `src/fitcv/evidence.py:_strict_professional_evidence_required`, `src/fitcv/evidence.py:resolve_experience_evidence_mode`, `src/fitcv/rule_filter.py:_normalise_seniority`, `candidate.preferences.seniority_target`, `profile.years_experience`, `config/taxonomy/taxonomy.yaml`
- Inspect: `src/fitcv/agentic_cv_analysis.py:should_route_loose_experience_review`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `src/fitcv/agentic_cv_analysis.py:_experience_evidence_facts`
- Modify: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/pipeline.py` only where the final evidence/readiness artifact is assembled
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`

**Dependencies:**
- The existing `cv_analysis.experience_evidence_mode` setting and policy version remain the canonical mode contract.
- Preserve existing hard eligibility filters and the recorded run-level effective settings snapshot.

**Authority:**
- Preauthorized local actions: update the named evidence/analysis/pipeline symbols and their focused tests; run the backend test commands listed in this task.
- Stop for: a required change to persistence schema, a new mode beyond `loose`, `full`, or `strict`, or a behavior change that conflates numeric baseline fit with evidence readiness.

**Steps:**
- [x] Step 1: Define the seniority/requirement decision table in tests before changing routing: project-only entry-level, project-only senior, professional evidence, and explicit project acceptance.
- [x] Step 2: Make Loose promotion require an allowed project-equivalence context and refuse promotion when the role or requirement is senior/professional-only without professional evidence.
- [x] Step 3: Make Full/Strict return an explicit unresolved-professional verdict/readiness reason while preserving the baseline fit and evidence payload.
- [x] Step 4: Ensure the effective mode and evidence policy version remain present in the analysis artifact and run trace.

**Verification:**
- [x] `python -m pytest tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py -q`
- Expected: project-only senior cases do not promote; allowed entry-level/project cases can produce the documented Loose stretch; Full/Strict preserve a separate unresolved-professional verdict; existing hard filters remain unchanged.

**Exit Criteria:**
- Every mode has a tested, explicit decision for capability evidence, professional evidence, seniority, and project acceptance; no high baseline result is presented as fully qualified when a mandatory professional gap remains.

### Task 2: Harden project-acceptance parsing and qualification language

**Purpose:**
- Prevent negative or insufficient project language from being interpreted as affirmative project acceptance.

**Task Function:**
- Tighten natural-language qualifier parsing with bounded negation/insufficiency cases and regression fixtures.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: narrow parser correction with low implementation surface and high semantic risk.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: table-driven parser tests directly exercise affirmative and negative wording.

**Specification Coverage:**
- `academic projects are insufficient`, `projects do not count`, `without project experience`, and equivalent negated forms must not affirm project acceptance.
- Positive forms such as `academic projects accepted` remain affirmative.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_PROJECT_ACCEPTANCE_MARKERS`, `src/fitcv/evidence.py:_project_acceptance_is_affirmed`, `src/fitcv/evidence.py:experience_requirement_policy`
- Modify: `src/fitcv/evidence.py:_project_acceptance_is_affirmed`
- Verify: `tests/test_evidence.py`

**Dependencies:**
- Task 1 decision table defines how explicit project acceptance affects Loose/Full/Strict outcomes.

**Authority:**
- Preauthorized local actions: update the parser and its table-driven tests without changing unrelated qualifier extraction.
- Stop for: an ambiguous language rule that cannot be covered by deterministic tests; record the example for product clarification instead.

**Steps:**
- [x] Step 1: Add affirmative, negated, insufficient, and mixed-context examples for every existing project marker.
- [x] Step 2: Replace the broad local negation check with a bounded pattern that recognizes insufficiency/rejection wording without rejecting independent positive clauses.
- [x] Step 3: Re-run the evidence policy tests and confirm the resulting policy fields used by Task 1.

**Verification:**
- [x] `python -m pytest tests/test_evidence.py -q`
- Expected: positive acceptance is true; negative/insufficient acceptance is false; unrelated requirement parsing remains green.

**Exit Criteria:**
- The parser has regression coverage for the validated failure and no longer turns explicit project rejection into project acceptance.

### Task 3: Enforce numeric baseline and fit-label consistency

**Purpose:**
- Prevent persisted `baseline_fit_label` values from overriding a contradictory numeric score or active threshold policy.

**Task Function:**
- Reconcile persisted ranking rows against the canonical score-to-label function and preserve safe handling of missing/invalid scores.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: deterministic ranking-contract change with a small blast radius and clear boundary tests.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: numeric boundary and mismatch fixtures are sufficient.

**Specification Coverage:**
- `0.3999 → skip`, `0.4000 → stretch`, `0.6999 → stretch`, and `0.7000 → strong` remain threshold-consistent under the configured policy.
- Missing, non-numeric, non-finite, or out-of-range scores do not fabricate a fit label.
- A persisted label that disagrees with the numeric score is rejected, recomputed, or marked invalid according to one documented contract; it must not be trusted silently.
- Analysis records, decision chains, pipeline exports, and checkpoint payloads
  all use the same resolver; no raw persisted label remains authoritative.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/ranking_contract.py:build_baseline_result`, `src/fitcv/ranking_contract.py:_fit_label_from_thresholds`, `src/fitcv/ranking_contract.py:adapt_legacy_ranking_row`, `src/fitcv/agentic_cv_analysis.py:_authoritative_ranking_fit_label`, `src/fitcv/agentic_cv_analysis.py:build_decision_chain`, `src/fitcv/agentic_cv_analysis.py:build_cv_analysis_record`, `src/fitcv/pipeline.py:_authoritative_ranking_fit_label`, `src/fitcv/pipeline_stage_context.py:PipelineState.from_checkpoint_payload`
- Modify: `src/fitcv/ranking_contract.py` plus every raw-label consumer (`src/fitcv/agentic_cv_analysis.py`, `src/fitcv/pipeline.py`, and `src/fitcv/pipeline_stage_context.py`) so one canonical score/label resolver governs analysis records, exports, and checkpoint restoration
- Verify: `tests/test_ranking_contract.py`, `tests/test_agentic_cv_analysis.py`, `config/policy/ranking.yaml`

**Dependencies:**
- Preserve the active configured formula and weights; this task hardens consistency rather than retuning ranking.
- Task 1 must keep evidence readiness separate from baseline fit labels.

**Authority:**
- Preauthorized local actions: update ranking normalization/fit resolution and focused tests; do not alter policy weights or threshold defaults.
- Stop for: a requirement to migrate stored ranking rows or change the active ranking policy; document that as a separate migration decision.

**Steps:**
- [x] Step 1: Add mismatch fixtures for valid numeric scores paired with each incorrect label.
- [x] Step 2: Centralize the choice to recompute or reject mismatched labels and apply it to legacy aliases as well as canonical fields.
- [x] Step 3: Add boundary, missing, invalid, and finite-range tests while retaining the checked-in `1.0/0.0` baseline behavior.

**Verification:**
- [x] `python -m pytest tests/test_ranking_contract.py tests/test_agentic_cv_analysis.py -q`
- Expected: score/label pairs are consistent, invalid inputs remain unclassified, and every threshold boundary passes.

**Exit Criteria:**
- No analysis path silently trusts a persisted fit label that contradicts the canonical numeric score and active policy.

### Task 4: Add canonical title inclusion/exclusion filtering

**Purpose:**
- Add one deterministic title predicate that supports optional inclusion and exclusion keywords for every job source.

**Task Function:**
- Extend the scan/request and rule-filter contracts while keeping provider matching as an optimization only.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-boundary backend change involving acquisition, canonicalization, pipeline filtering, and persisted run details.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: direct boundary tests cover provider, uploaded-job, and artifact behavior.

**Specification Coverage:**
- OR within inclusion keywords; OR within exclusion keywords; AND between inclusion and exclusion conditions.
- Empty inclusion list means all titles are eligible unless excluded.
- Matching is case-insensitive whole-word or phrase matching, not raw substring matching (`AI` must not match `Retail` or `Trainee`).
- `Working Student – AI Analytics` is kept for inclusion `AI` and exclusion `duales`.
- `Duales Studium – AI Engineering` is excluded by `duales`.
- `Retail Analytics Intern` is excluded when inclusion is `AI`.
- `AI/ML Engineer` is kept.
- Run details identify the missing inclusion or matched exclusion reason.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/rule_filter.py:apply_rule_filters`, `src/fitcv/rule_filter.py:store_filter_results`, `src/fitcv/pipeline.py:enrich/rule-filter stage`
- Inspect: `src/fitcv/job_sources.py:ScannerRequest`, `src/fitcv/job_sources.py:build_scanner_request`, provider `_matches` helpers
- Inspect: `src/fitcv_cp/scan_contracts.py:ScanCreateRequest`, `src/fitcv_cp/scan_worker.py:execute_scan`, `src/fitcv_cp/sqlite_store.py:create_scan`
- Inspect and update: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md` so its `job_titles` contract no longer describes substring-OR-only behavior
- Modify: `src/fitcv/rule_filter.py`, `src/fitcv/pipeline.py`, `src/fitcv/job_sources.py`, `src/fitcv_cp/scan_contracts.py`, `src/fitcv_cp/scan_worker.py`, and only the persistence/projection functions required to retain the input and rejection reason
- Verify: `tests/test_rule_filter.py`, `tests/test_pipeline.py`, `tests/test_job_sources.py`, `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_scan_worker.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Define the canonical normalized list shape and predicate in `rule_filter.py` before wiring request or provider adapters.
- Keep existing positive `job_titles` compatibility for older scan inputs; map it once to the canonical inclusion field.
- Post-acquisition filtering is authoritative so uploaded jobs and providers behave identically.
- Preserve recall: a provider may use inclusion terms as a prefilter only when
  every canonical inclusion term is queried and results are unioned and
  deduplicated. Otherwise omit the positive prefilter and fetch broadly.
  Exclusion terms are never provider-only filters.

**Authority:**
- Preauthorized local actions: update the named request, filtering, acquisition, and artifact paths plus focused tests; preserve old scan-input compatibility.
- Stop for: a database migration requirement beyond JSON input/artifact compatibility, provider-specific semantics that cannot preserve the canonical predicate, or any request to apply raw substring matching.

**Steps:**
- [x] Step 1: Add normalized include/exclude fields to the scan contract and preserve legacy `job_titles` as an inclusion alias.
- [x] Step 2: Implement one casefolded whole-word/phrase matcher and a structured decision result containing `passed`, `reason_code`, and matched term.
- [x] Step 3: Apply the predicate at the deterministic post-acquisition rule-filter boundary; keep provider keyword filtering as a bounded prefetch optimization.
- [x] Step 4: Persist the input lists and title rejection details in scan/run artifacts so users can explain missing jobs.
- [x] Step 5: Add provider and uploaded-job parity tests for the four acceptance examples and empty-list behavior.

**Verification:**
- [x] `python -m pytest tests/test_rule_filter.py tests/test_pipeline.py tests/test_job_sources.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: inclusion/exclusion logic is identical across source paths, legacy positive title inputs still work, and rejection artifacts contain the matched reason.

**Exit Criteria:**
- One canonical predicate controls title filtering; no source path can bypass exclusion or apply a different substring interpretation.

### Task 5: Reconcile settings and scan UI/API surfaces

**Purpose:**
- Make the existing strictness control reliably discoverable and ensure the new title-filter contract is usable from the maintained scan surface without duplicating backend logic.

**Task Function:**
- Integrate the existing settings schema/API projection and the scan input controls with accessible, typed frontend state.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded full-stack contract work using existing select, textarea, save, reset, and scan-dialog patterns.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: existing frontend tests plus a focused browser flow verify the user-visible contract.

**Specification Coverage:**
- Pipeline Settings exposes `Match strictness` with exactly `Loose`, `Full`, and `Strict` and persists the existing canonical key `cv_analysis.experience_evidence_mode`.
- New Scan exposes separate inclusion and exclusion title inputs; both are shown in scan details.
- Accessible labels, save/reset/error flows, and API validation remain intact.
- Do not create a second strictness setting or a second title-matching implementation.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-frontend-component-engineering`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`, `src/fitcv_cp/settings_schema.py:pipeline_settings_projection`, `src/fitcv_cp/app.py:/settings/pipeline`
- Inspect: `frontend/src/features/pipeline-settings/sections-def.ts:PIPELINE_SECTIONS`, `frontend/src/features/pipeline-settings/types.ts:PipelineFieldDef`, `frontend/src/features/pipeline-settings/pipeline-settings-dialog.tsx` field renderer
- Modify: `frontend/src/features/pipeline-settings/*` only if verification finds a regression in the already-present selector
- Modify: `frontend/src/features/scans/types.ts`, `frontend/src/features/scans/new-scan-dialog.tsx`, `frontend/src/features/scans/scan-detail.tsx`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_app.py`, `frontend/src/test/pipeline-settings.test.tsx`, `frontend/src/test/scans.test.ts`, `frontend/e2e/integration-flows.spec.ts`

**Integration Proof:**
- Canonical contract owner: `src/fitcv_cp/settings_schema.py` for strictness and `src/fitcv_cp/scan_contracts.py` for scan title lists.
- Integration sidecar: `none`; the existing API payload and settings projection are the maintained contract.
- Browser flow: open Pipeline Settings, select each mode, save/reset, then create a scan with include/exclude title lists and inspect Scan Details.
- Sidecar removal condition: none; no temporary contract mapping or generated adapter is introduced.

**Dependencies:**
- Task 1 establishes the mode semantics.
- Task 4 establishes the canonical title-list names and API payload shape.
- The existing selector is present at the pinned revision; avoid editing it unless a fresh test demonstrates a real regression.

**Authority:**
- Preauthorized local actions: update typed UI/API consumers and focused tests for the named contracts; reuse existing controls and tokens.
- Stop for: a required redesign, new route, or incompatible payload migration; escalate rather than silently adding parallel settings.

**Steps:**
- [x] Step 1: Add/retain explicit frontend assertions that the settings page renders all three strictness options and round-trips the canonical key through GET/PATCH/reset.
- [x] Step 2: Add include/exclude title controls to the existing New Scan dialog and show the persisted values in Scan Details.
- [ ] Step 3: Verify disabled, loading, validation-error, save, reset, and keyboard-accessible states without changing unrelated visual design.
- [x] Step 4: Run the focused frontend tests and type checking.

**Verification:**
- [x] `npm --prefix frontend test -- --run src/test/pipeline-settings.test.tsx`
- [x] `npm --prefix frontend test -- --run src/test/scans.test.ts`
- [x] `npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts` (via `scripts/run_fitcv_review_e2e.ps1 -FullSuite`; 8 tests passed and cleanup exited cleanly)
- [x] `npm --prefix frontend run test:e2e -- integration-flows.spec.ts -g "review"` (via `scripts/run_fitcv_review_e2e.ps1`; 2 review tests passed)
- [x] `npm --prefix frontend run typecheck`
- Expected: the strictness selector is visible and editable; title lists serialize to the backend contract; no duplicate control or raw substring behavior is introduced.

**Exit Criteria:**
- A user can select the existing strictness mode and create a scan with both title lists, with values retained and explainable after execution.

### Task 6: Align documentation and run final verification

**Purpose:**
- Document the accepted semantics and produce fresh proof for the complete implementation without claiming the compatibility formula was changed.

**Task Function:**
- Reconcile maintained docs, run focused and broader checks, and record deviations or deferred decisions.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final verification and documentation reconciliation across already-implemented task surfaces.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: `skill-verification-before-completion` is the final acceptance gate.

**Specification Coverage:**
- Document mode semantics, separate baseline/evidence outputs, title filter truth table, reason persistence, and score-label consistency.
- Confirm the existing strictness setting rather than describing it as newly implemented.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-backend-verification`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect/modify: `docs/pipeline.md`, `docs/configuration.md` if those files are the maintained owners for the affected behavior
- Verify: all files changed by Tasks 1–5 and the reviewed commit SHA

**Dependencies:**
- Tasks 1–5 complete with task-local proof.
- No unrelated untracked files may be cleaned, reformatted, or included.

**Authority:**
- Preauthorized local actions: update only maintained documentation for the implemented behavior and run final verification commands; preserve unrelated worktree state.
- Stop for: any failed required check, stale generated surface, unexpected diff, or evidence that the implementation diverged from the validated findings.

**Steps:**
- [x] Step 1: Document the mode decision table and title-filter examples, including the distinction between baseline fit and evidence readiness.
- [x] Step 2: Run focused backend/frontend checks, then the repository-required broader checks for touched surfaces.
- [x] Step 3: Inspect `git diff --check`, changed-file scope, and test output; record blockers rather than weakening acceptance criteria.

**Verification:**
- [x] `python -m pytest tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_ranking_contract.py tests/test_rule_filter.py tests/test_pipeline.py tests/test_job_sources.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- [x] `npm --prefix frontend test -- --run src/test/pipeline-settings.test.tsx`
- [x] `npm --prefix frontend test -- --run src/test/scans.test.ts`
- [x] `npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts` (via `scripts/run_fitcv_review_e2e.ps1 -FullSuite`; 8 tests passed and cleanup exited cleanly)
- [x] `npm --prefix frontend run test:e2e -- integration-flows.spec.ts -g "review"` (via `scripts/run_fitcv_review_e2e.ps1`; 2 review tests passed and cleanup exited cleanly)
- [x] `npm --prefix frontend run typecheck`
- [x] `npm --prefix frontend run build`
- [x] `git diff --check`
- [x] `git status --short`
- Expected: all required checks pass; only plan-authorized files are changed; unrelated untracked artifacts remain untouched.

**Exit Criteria:**
- Documentation, backend contracts, persisted artifacts, frontend controls, and tests agree; `skill-verification-before-completion` can return `verified` without unresolved required work.

## Execution Evidence

Executed on `main` after the amended plan publication:

- Backend: `1341 passed, 1 skipped` for the required focused suite.
- Frontend unit: pipeline settings `27 passed`; scan feature `18 passed`.
- Frontend typecheck: passed.
- Frontend production build: passed; Vite emitted only the existing chunk-size warning.
- `git diff --check`: passed.
- Browser E2E: `scripts/run_fitcv_review_e2e.ps1 -FullSuite` seeded the disposable
  fixture, generated `FITCV_E2E_MANIFEST`, started the owned backend at
  `127.0.0.1:8000`, and passed the full `integration-flows.spec.ts` suite:
  `8 passed` in `16.7s`. Cleanup retries transient SQLite WAL/SHM locks; the
  run completed with exit code `0` and removed the fixture.

## Verification

Final artifact-level verification must prove:

- The existing settings API and UI expose exactly `loose`, `full`, and `strict`, default omissions to `full`, reject unknown values, and preserve the run-level effective setting.
- Loose cannot promote a senior/professional-only requirement from project evidence alone; allowed entry-level/project cases remain usable.
- Full and Strict preserve baseline fit separately but expose/gate unresolved mandatory professional evidence.
- Negated project-acceptance wording is never treated as affirmative.
- Baseline numeric scores, labels, thresholds, missing scores, and persisted legacy aliases remain consistent.
- Title inclusion/exclusion uses OR-within and AND-between semantics, whole-word/phrase matching, and identical post-acquisition behavior for providers and uploaded jobs.
- Scan/run details retain filter inputs and explain title rejections.
- The four title acceptance examples pass exactly as specified.
- Fresh backend, frontend, typecheck, build, and diff-hygiene commands pass.

## Completion Criteria

The plan is ready for completion verification when:

1. Tasks 1–6 have complete task-local proof and no unrecorded deviations.
2. The existing strictness selector has been verified rather than duplicated.
3. Every validated review finding is either fixed and tested or explicitly recorded as blocked with its source evidence.
4. The active compatibility formula remains unchanged unless a separately approved ranking-policy decision is recorded.
5. Code, settings schema, scan contracts, persisted artifacts, frontend consumers, tests, and documentation are reconciled.
6. `skill-verification-before-completion` runs fresh final verification and returns `verified` before any implementation branch is finished or published.

