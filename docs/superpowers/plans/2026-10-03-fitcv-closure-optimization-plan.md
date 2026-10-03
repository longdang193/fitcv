---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
---

# FitCV Closure And Optimization Plan

## Goal

Close P1-A and P1-B without reopening settled P0 decisions. Make final-artifact
provenance source-owned and fail closed on ambiguity. Make native render proof
one canonical identity used by generation, trimming, reuse, and review
finalization. Prove the result with one predefined current-contract cohort,
then optimize the measured dominant cost. Defer P1-C market-gap intelligence
and keep P2 frozen.

## Implementation Outcomes

### 1. Source-owned final-artifact provenance

`cv_content_plan_v1` and `render_item_provenance_v1` carry canonical source
identity for each approved claim. Exact or deterministic source mappings may
populate `evidence_ids` and `supported_requirement_ids`; ambiguous or
unmatched mappings are marked protected and contribute no verified support.
Trimming cannot delete uniquely supporting source evidence because of semantic
text overlap with another project.

### 2. Canonical render proof and bounded reuse

`render_cv_native_acceptance()` owns the complete static render identity and
dynamic render outcome. Callers do not overlay independently computed template
or configuration fingerprints. A valid cached proof reuses with zero provider
calls and zero renders; stale proof rerenders exactly once before bounded trim
or `review_required` handling.

### 3. Current-contract closure evidence

One frozen cohort records every ranked outcome under `fitcv.final_artifact.v1`,
`fitcv.trace.v1`, and `fitcv.efficiency.v1`. P1-A/B promotion requires accepted
artifacts with 100% native one-page proof, zero verified provenance loss, zero
unresolved accepted overflow, zero trace conflicts, zero unattributed accepted
artifacts, and complete cost/timing coverage. Historical `5/5` evidence remains
audit-only and cannot establish first-pass improvement.

### 4. Measured optimization path

Current traces produce one scorecard with regeneration causes, provider calls,
tokens, renders, reuse hits, resolution reuse, human actions, and stage p50/p95.
Optimization changes target the largest measured cost first, beginning with
zero-render/one-render reuse and then the dominant regeneration cause. No
retrieval, provider, model, vector-store, reranker, GraphRAG, or new-agent
change is introduced by this plan.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: `source and test edits, plan/evidence edits, local fixture runs, configured MCP reads, focused test/build/verification commands, and process-only loading of FITCV_LLM_API_KEY from repository .env`
- User-approval actions: `push, merge, publication, destructive cleanup, credential changes, external writes, and production/provider/model changes`
- Parallel ownership: `none; provenance and render-proof changes share final-artifact contracts`
- Sequential fallback: `complete provenance contract and tests, then render-proof contract and tests, then integration/cache proof, then cohort and optimization measurement`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Base commit: `53f95ad0e2f13777e723911521a17e8cac197670`
- Expected workspace: `existing untracked experiment/evidence artifacts preserved; no required tracked implementation edits yet`
- Next action: `closed; retain P1-C deferred and P2 frozen`
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 — Freeze contracts and reproduce defects | `completed` | current | `codex` | none | focused failing tests and defect traces | `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.md` |
| Task 2 — Implement canonical source provenance | `completed` | current | `codex` | Task 1 | provenance and adversarial ownership tests | `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.md` |
| Task 3 — Implement canonical render identity | `completed` | current | `codex` | Task 1 | render identity and caller contract tests | `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.md` |
| Task 4 — Close final-artifact reuse and trim paths | `completed` | current | `codex` | Tasks 2–3 | zero/one-render cache tests and backend boundary proof | `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.md` |
| Task 5 — Run current-contract acceptance cohort | `completed` | current | `codex` | Task 4 | frozen cohort scorecard and P1-A/B gate result | `docs/superpowers/evidence/2026-10-03-fitcv-current-cohort-b.json` |
| Task 6 — Optimize measured dominant cost | `completed` | current | `codex` | Task 5 | bounded cache optimization and lossless efficiency report | `docs/superpowers/evidence/2026-10-03-fitcv-closure-verification.json` |

## Task Breakdown

## Task 1: Freeze contracts and reproduce defects

**Purpose:**
- Establish source-first baseline for both reported defects and prevent scope drift into P1-C or P2.

**Task Function:**
- Reproduce final-artifact provenance misattribution and stale-cache render-proof mismatch with production-shaped fixtures.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Existing workspace and bounded defect reproduction; no delegation needed.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Lead controller owns initial reproduction.`

**Specification Coverage:**
- Evidence ownership must not derive from semantic overlap when canonical source identity is available.
- A render proof must not change identity after rendering.
- Existing P0 behavior, current contracts, and historical evidence disposition remain unchanged.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_finalize_selected_item`, `_select_final_evidence`, `_recover_verified_supporters`
- Inspect: `src/fitcv/pipeline.py:cv_content_plan construction`
- Inspect: `src/fitcv/cv_generator.py:build_render_proof_identity`, `render_cv_native_acceptance`, `render_proof_matches`
- Inspect: `src/fitcv/agentic_cv_generation.py:_render_acceptance_matches_final_content`, `_reusable_result_or_none`, `_apply_final_artifact_contract`
- Verify: `tests/test_cv_render_acceptance.py`, `tests/test_cv_generator.py`, provenance and final-artifact tests discovered during reproduction

**Dependencies:**
- Verdict in `C:\Users\HOANG PHI LONG DANG\.codex\attachments\b35e18a9-43ac-4bea-bf29-e491fa617f95\Pasted text.txt`.

**Authority:**
- Preauthorized local actions: `read source/tests, add failing focused tests, create disposable fixtures, run focused tests`
- Stop for: `new product behavior, production/provider/model changes, destructive cleanup, or unresolved contract ambiguity`

**Steps:**
- [x] Step 1: Trace all callers and writers of provenance sidecars and render-proof identity.
- [x] Step 2: Add a failing confusable-project test where shared skill wording maps evidence to the wrong project.
- [x] Step 3: Add a failing stale-proof test showing independent identity recomputation causes an unnecessary rerender.
- [x] Step 4: Record exact failing output and affected shared callers before implementation.

**Verification:**
- [x] Focused provenance and render tests fail for the reported defects, not due to fixture or import errors.
- Expected: `RED` failures identify wrong source ownership and duplicate/stale render identity behavior.

**Exit Criteria:**
- Both defects reproduce deterministically; affected symbols and tests are recorded; no unrelated scope is added.

## Task 2: Implement canonical source provenance

**Purpose:**
- Carry host-known source identity from selected evidence through content planning and reconciliation.

**Task Function:**
- Replace speculative text-overlap ownership with deterministic identity mapping and fail-closed ambiguity handling.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Shared evidence contract requires direct source/test control.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Focused regression suite and final backend verification cover the bounded change.`

**Specification Coverage:**
- Add `claim_id`, `evidence_id`, `source_section`, `source_ref`, `canonical_source_id`, `canonical_source_label`, `supports_requirements`, and `target_section` to host-side content-plan data where available.
- Preserve the LLM boundary: provenance IDs remain host-managed and are not provider-controlled.
- Use `attribution_status` values `exact`, `resolved`, `ambiguous`, and `unmatched`.
- Only `exact` and `resolved` mappings populate verified evidence/support IDs; ambiguous/unmatched items become protected with empty verified support.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv/evidence.py:_annotate_requirement_support`, `_requirement_support_map`, `_finalize_selected_item`, `_select_final_evidence`, `_recover_verified_supporters`
- Modify: `src/fitcv/pipeline.py:cv_content_plan construction and serialization`
- Modify: `src/fitcv/agentic_cv_generation.py:render-item provenance reconciliation and trim protection`
- Verify: `tests/test_agentic_cv_analysis.py`, existing evidence-selection tests, new adversarial project/source fixtures

**Dependencies:**
- Task 1 reproduction and failing tests.

**Authority:**
- Preauthorized local actions: `modify provenance/content-plan/trim code and focused tests within listed surfaces; run local backend boundary tests`
- Stop for: `schema migration, provider prompt changes, retrieval changes, or any ambiguous ownership rule not resolved by source identity`

**Steps:**
- [x] Step 1: Build canonical source identity from existing candidate profile IDs, source refs, project names, employers, and language identities.
- [x] Step 2: Reconcile generated items against canonical identity before semantic fallback; mark non-unique matches ambiguous.
- [x] Step 3: Remove speculative evidence/support assignment from ambiguous and unmatched items.
- [x] Step 4: Ensure trim/recovery protects ambiguous items and returns `review_required` when one-page fit cannot be proven safely.
- [x] Step 5: Keep output schema backward-compatible except for additive provenance fields and explicit status values.

**Verification:**
- [x] Confusable production/classroom Python projects map only production evidence to production source.
- [x] SQL/tool-sharing projects, renamed projects, language mentions, and unresolved mappings fail closed.
- [x] Selected evidence and requirement support remain unchanged for existing exact mappings.
- Expected: focused suite passes; no unsupported verified support is assigned; unique support cannot be trimmed away.

**Exit Criteria:**
- Provenance ownership is source-owned, ambiguity is safe, and all Task 1 regressions pass.

## Task 3: Implement canonical render identity

**Purpose:**
- Make one render-proof identity definition authoritative across native rendering, cache reuse, trim, and review finalization.

**Task Function:**
- Consolidate static render identity and prevent caller overlays from invalidating completed render proof.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Single final-artifact path with high contract coupling; keep sequential.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Focused render-contract tests plus backend finalization proof.`

**Specification Coverage:**
- Canonical proof includes `final_artifact_contract_version`, `content_sha256`, `artifact_content_sha256`, `template_sha256`, `render_config_fingerprint`, `renderer_contract_version`, `render_status`, `page_count`, `page_fit_status`, and `artifact_checksum`.
- Static identity derives from one builder used by acceptance and proof matching; dynamic fields come only from the renderer outcome.
- Callers do not rebuild or overlay template/config identity after rendering.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv/cv_generator.py:build_render_proof_identity`, `_render_config_fingerprint`, `_template_sha256`, `render_cv_native_acceptance`, `render_proof_matches`, `final_artifact_acceptance_passes`
- Modify: `src/fitcv/agentic_cv_generation.py:_render_acceptance_matches_final_content`, `_apply_final_artifact_contract`, `_reusable_result_or_none`
- Modify: `src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact`
- Verify: `tests/test_cv_render_acceptance.py`, `tests/test_cv_generator.py`, final-artifact integration tests

**Dependencies:**
- Task 1 reproduction; Task 2 is not required for isolated render identity but must be complete before final integration.

**Authority:**
- Preauthorized local actions: `modify render-proof helpers/callers and focused tests within listed surfaces; run native renderer checks`
- Stop for: `template redesign, renderer replacement, dependency installation, or unrelated layout changes`

**Steps:**
- [x] Step 1: Define one canonical static identity builder and make existing helpers delegate to it or delete duplicate logic.
- [x] Step 2: Return complete authoritative proof from `render_cv_native_acceptance()`.
- [x] Step 3: Remove post-render identity overlays and update proof matching to compare canonical fields.
- [x] Step 4: Preserve `review_required` behavior for failed or unverified render outcomes.

**Verification:**
- [x] Same content/template/config produces identical proof identity through fresh render, cache validation, and review finalization.
- [x] Changed content or stale template/config invalidates proof deterministically.
- Expected: focused render tests pass with no duplicate identity drift.

**Exit Criteria:**
- One canonical render identity owns all proof fields and all callers consume it without recomputation drift.

## Task 4: Close final-artifact reuse and trim paths

**Purpose:**
- Prove correctness and cost behavior at the backend boundary for accepted, stale, changed, and failed artifacts.

**Task Function:**
- Integrate provenance and render-proof contracts through generation, trim, reuse, persistence, and review actions.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Crosses generation, persistence, and review finalization; controller retains authority.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Backend boundary tests cover final state and side effects.`

**Specification Coverage:**
- Valid cached proof: `0` provider calls, `0` renders, accepted.
- Stale cached proof: `0` provider calls, exactly `1` render, accepted only with one-page proof.
- Changed content: old proof rejected, exactly `1` render before bounded trim/review.
- Failed rerender: exactly `1` render, then `review_required`; never approve unverified overflow.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Modify: `src/fitcv/agentic_cv_generation.py:_reusable_result_or_none`, `_apply_final_artifact_contract`, trim/retry orchestration
- Modify: `src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact` and review closure callers
- Verify: final-artifact, cache, review-queue, persistence, trace, and efficiency tests

**Dependencies:**
- Tasks 2 and 3 complete.

**Authority:**
- Preauthorized local actions: `modify final-artifact integration and tests; run local backend boundary checks with disposable state`
- Stop for: `production data mutation, external provider writes, schema migration, or unresolved trace/attribution contract conflict`

**Steps:**
- [x] Step 1: Add red tests for valid cache, stale proof, changed content, failed rerender, and protected ambiguous trim items.
- [x] Step 2: Wire canonical provenance and render proof through accepted/review-required/persistence paths.
- [x] Step 3: Assert provider-call and native-render counters at the boundary, not only helper-level mocks.
- [x] Step 4: Verify idempotent reuse and review actions do not create duplicate artifacts or contradictory trace records.

**Verification:**
- [x] Focused integration suite passes.
- [x] Direct boundary tests prove accepted final state, rejected overflow state, persisted proof, trace attribution, and idempotency.
- Expected: no accepted artifact lacks verified one-page render proof or source attribution.

**Exit Criteria:**
- Final-artifact path satisfies correctness and zero/one-render reuse contracts with regression proof.

## Task 5: Run current-contract acceptance cohort

**Purpose:**
- Produce fresh, attributable evidence for P1-A/B promotion after implementation closure.

**Task Function:**
- Freeze and execute one predefined cohort; report every outcome without outcome-based exclusion.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Evidence and acceptance authority remain with lead controller.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Final verification reads source, database, artifacts, and scorecard directly.`

**Specification Coverage:**
- Freeze fixture/selected jobs, candidate profile, config, provider/model, contract versions, run limits, and acceptance criteria before running.
- Load `FITCV_LLM_API_KEY` from repository `.env` into process environment only; never print or persist it.
- Include accepted, review-required, validation-failed, provider-failed, cancelled-with-work, retries, trace conflicts, unattributed artifacts, calls, tokens, renders, and timing coverage.
- Historical rejected experiments remain audit evidence only.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py` and current local experiment runner/evidence format
- Verify: `docs/superpowers/evidence/2026-10-03-fitcv-first-pass-experiment.json`, current cohort evidence, run SQLite compatibility/debug payloads, final artifact records
- Add/update: `docs/superpowers/evidence/<date>-fitcv-p1-closure-cohort.json`, `.md`

**Dependencies:**
- Task 4 complete and tracked implementation state clean enough for cohort execution.

**Authority:**
- Preauthorized local actions: `run frozen disposable local cohort, read local evidence, write evidence artifacts, and use process-only repository .env credentials`
- Stop for: `provider/config changes, secret exposure, outcome exclusion, production data mutation, or non-comparable fixture substitution without explicit record`

**Steps:**
- [x] Step 1: Freeze inputs and hashes in the evidence manifest.
- [x] Step 2: Run one fixed-size current-contract cohort with all outcomes retained.
- [x] Step 3: Extract canonical trace, artifact, provenance, efficiency, and timing metrics from one lossless reporting path.
- [x] Step 4: Evaluate P1-A/B gates; promote only if every gate passes.
- [x] Step 5: Record blockers and keep P1-C deferred if any gate fails.

**Verification:**
- [x] Accepted count is greater than zero.
- [x] Accepted one-page success and native proof coverage are `100%`.
- [x] Verified source-provenance loss and unresolved accepted overflow are `0`.
- [x] Trace conflicts and unattributed accepted artifacts are `0`.
- [x] Cost, token, render, and timing coverage is `100%` for current contracts.
- Expected: promotion decision follows recorded gates, not historical `5/5` evidence or excluded outcomes.

**Exit Criteria:**
- One current-contract cohort yields an auditable P1-A/B promotion or a precise blocker list.

## Task 6: Optimize measured dominant cost

**Purpose:**
- Improve first-pass acceptance and efficiency only after correctness gates are trustworthy.

**Task Function:**
- Rank measured regeneration and reuse costs, implement one narrow optimization, and prove no correctness regression.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: `Optimization requires controlled before/after evidence and no speculative architecture.`

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `Independent fresh cohort and regression suite provide verification.`

**Specification Coverage:**
- Score regeneration causes by provider calls, tokens, renders, latency, and accepted-CV impact.
- Optimize the largest measured cause first; prefer valid cached reuse (`0/0`) and stale-proof reuse (`0/1`) before local micro-optimizations.
- Reuse stable human resolutions only when requirement identity, evidence fingerprint, and job semantics are unchanged.
- Report generation duration, artifact acceptance latency, and batch wall time separately.
- Add stage p50/p95 for analysis, retrieval, content planning, provider generation, validation, render, repair, and persistence.

**Required Skills:**
- `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `scripts/benchmark_cv_efficiency.py` and canonical efficiency extraction/reporting path
- Modify only if measurement selects them: `src/fitcv/agentic_cv_generation.py:_reusable_result_or_none` and resolution reuse path
- Verify: current-contract trace/efficiency tests and before/after cohort evidence

**Dependencies:**
- Task 5 produces complete current-contract baseline.

**Authority:**
- Preauthorized local actions: `add measurement/reporting fields, implement one bounded optimization selected by baseline evidence, and run before/after disposable cohorts`
- Stop for: `retrieval/provider/model changes, new infrastructure, unmeasured optimization, or any P1-A/B gate regression`

**Steps:**
- [x] Step 1: Generate one scorecard from canonical trace and artifact records.
- [x] Step 2: Select one dominant cost with explicit baseline metric and target threshold.
- [x] Step 3: Add a failing regression for the selected optimization contract.
- [x] Step 4: Implement the smallest change; rerun focused tests and current-contract cohort.
- [x] Step 5: Accept optimization only if correctness gates remain green and measured cost improves.

**Verification:**
- [x] Before/after evidence covers calls, tokens, renders, retries, latency, first-pass rate, accepted one-page rate, provenance loss, trace conflicts, and attribution.
- [x] No accepted artifact loses source evidence or page proof.
- Expected: optimization promotion is evidence-backed; otherwise revert optimization scope and retain closure fixes.

**Exit Criteria:**
- One measured optimization is accepted or explicitly rejected with evidence; no speculative optimization remains in scope.

## Verification

Use focused tests first, then full repository checks:

- `python -m pytest tests/test_cv_render_acceptance.py tests/test_cv_generator.py tests/test_agentic_cv_analysis.py`
- Relevant final-artifact, provenance, cache, review-queue, trace, and efficiency tests discovered in Tasks 1–4.
- Full configured test suite after integration changes.
- Frozen current-contract cohort command and evidence extraction from Task 5.
- Before/after optimization cohort and scorecard from Task 6.

Final review must confirm source code/tests are authoritative, generated docs or
stage surfaces are synchronized when touched, no secrets appear in output, and
P1-C/P2 remain deferred.

## Completion Criteria

The plan is ready for completion verification when:

1. provenance ownership is canonical and fail-closed;
2. render proof has one identity owner;
3. valid/stale/changed/failed cache paths have zero/one-render regression proof;
4. final-artifact backend boundaries prove accepted, review-required, rejected,
   persistence, trace, and idempotency behavior;
5. one frozen current-contract cohort records every outcome and evaluates P1-A/B
   gates without historical or outcome-based exclusions;
6. optimization has a measured baseline, one bounded change, and before/after
   evidence, or is explicitly rejected;
7. all required tests and final verification pass;
8. P1-C market-gap intelligence and P2 remain explicitly deferred;
9. no unresolved required task, failed required check, stale status, or
   unrecorded scope deviation remains.

The plan may be marked `completed` only after
`skill-verification-before-completion` returns `verified` against repository
evidence.
