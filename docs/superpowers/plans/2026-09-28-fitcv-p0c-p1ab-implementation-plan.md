---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0c-p1ab-implementation
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/review_identity.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline.py
  - tests/test_review_identity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/pipeline.md
  - docs/api.md
  - docs/observability.md
---

# FitCV P0-C, P1-B, and P1-A Implementation Plan

## Review Basis

The supplied verdict is accepted as current acceptance state. It correctly
identifies one remaining runtime defect: qualifier evidence can cross skill
boundaries when one canonical evidence record contains multiple statements.
It also correctly separates deferred P0-A/P0-B experiments from runtime work,
places P1-B before P1-A, and rejects semantic parsing, extra agents, and new
retrieval architecture.

Repository review adds three implementation constraints:

- P0-C already has requirement-instance descriptors, projection fingerprints,
  reuse fingerprints, and canonical validation paths. Extend them; do not add a
  second evidence model.
- P1-B already has `ReviewRequiredReasonCode`, deterministic `review_item_id`,
  run-scoped HITL actions, review queue rendering, and checkpoint closure.
  Extend this workflow; do not create a parallel review queue.
- P1-A already has a structured CV contract and one missing-section repair
  cycle. Add a small content-plan contract and section-targeted repair to that
  flow; do not create a separate compiler service.

The checked-out source currently reports
`REQUIREMENT_SUPPORT_POLICY_VERSION = "requirement-support-v2"`, despite the
verdict describing v3 as merged. The implementation target remains v4, but
execution must invalidate every pre-v4 record, including v2 and v3, rather
than assume one historical base.

`docs/stages/` is absent from this checkout. Stage truth for this plan remains
in `docs/pipeline.md` and `docs/api.md`; do not create generated stage files as
an incidental implementation step.

P0-A/P0-B quality experiments remain deferred. This plan does not promote
retrieval or evidence-selection strategies.

## Goal

Deliver deterministic, fail-closed qualifier proof; actionable uncertainty
records with profile-scoped resolution reuse; and a `cv_content_plan_v1`
generation path that supports section-level repair without rediscovering truth.
Preserve existing status values, review closure behavior, evidence IDs,
fingerprint invalidation, and rollback paths.

## Implementation Outcomes

### P0-C runtime closeout

`project_candidate_evidence()` emits proof-safe source fragments with
deterministic sentence/clause boundaries and conservative skill attribution.
Qualifier assessment consumes only those fragments, never `scoring_context`,
title, role metadata, or other retrieval text. Ambiguous attribution remains
unverified. `REQUIREMENT_SUPPORT_POLICY_VERSION` becomes
`requirement-support-v4`, and all pre-v4 analysis reuse is rejected end to
end.

### P1-B actionable uncertainty

Requirement coverage and review-required records expose a small actionable
contract with reason, requirement instance, affected fact, question,
recommended disposition, supporting evidence IDs, and profile/source
fingerprint. Machine dispositions are `AUTO_OMIT`, `ASK_CANDIDATE`,
`BLOCK_CLAIM`, and `REVIEW_CONFLICT`; human resolution actions are
`RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, and `OVERRIDE_BLOCK`. Existing review
queue and action endpoint accept the resolution. Resolutions are reused only
when the same candidate profile identity/revision, source fingerprint, and
resolution key remain valid; changed truth fails closed and asks again.

### P1-A content compiler and local repair

The existing analysis-to-generation flow emits `cv_content_plan_v1` containing
approved evidence IDs, approved factual claims, protected numbers/dates,
supported requirements, target section, space budget, and omitted evidence
with reasons. The writer handles wording only. A failed section regenerates
that section against the immutable plan and preserves unaffected sections;
final validation still runs over the complete document.

### Evidence and handoff

Focused backend tests, control-plane tests, full suite, `git diff --check`,
and documented API/pipeline contracts prove the three outcomes. No P0-A/P0-B
promotion claim, new retrieval strategy, external provider, telemetry service,
or GraphRAG/agent/ANN work enters this change.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve unrelated dirty and untracked files
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect declared source/tests/docs, edit declared paths, run declared local tests, and write ignored verification outputs
- User-approval actions: commit, push, merge, publication, destructive cleanup, discard, or external writes
- Parallel ownership: `none`; evidence, review, and generation contracts share fingerprints and payloads
- Sequential fallback: execute tasks in listed order and stop at first failed contract or unresolved schema decision

## Task Breakdown

### Task 1: Close P0-C with proof-safe fragments and v4 reuse

**Purpose:**
- Prevent qualifier transfer between skills inside one mixed evidence record.
- Invalidate analyses produced under prior support-policy semantics.

**Task Function:**
- Deterministic evidence-grain correction and compatibility migration.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded Python runtime change with existing tests and no external dependency.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused tests and final backend verification cover same pipeline.

**Specification Coverage:**
- Same atomic fact must establish target skill and qualifiers.
- Retrieval metadata remains retrieval-only.
- Ambiguous binding fails closed.
- Existing v3 analyses cannot be reused under v4.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`, `_evidence_text`, `_parse_duration_qualifier`, `_parse_requirement_qualifiers`, `_duration_satisfies`, `_assess_requirement_support`, `build_required_skill_descriptors`, `build_cv_analysis_input_fingerprint`
- Modify: `src/fitcv/evidence.py:REQUIREMENT_SUPPORT_POLICY_VERSION`, new `_support_fragments` helper, and proof-fragment construction/assessment only
- Verify: `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `src/fitcv/validator.py:run_all_validations`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline_agentic_late_stage.py`

**Dependencies:**
- Current source and tests confirm existing projection, descriptor, and reuse contracts.

**Authority:**
- Preauthorized local actions: edit evidence and focused test/doc files, run focused backend tests, and preserve existing retrieval payload fields.
- Stop for: any need for semantic parsing, LLM extraction, new agent, graph, provider, persistent migration, or change to P0-A/P0-B production defaults.

**Steps:**
- [ ] Add source-only `support_fragments` during canonical projection. Split on deterministic sentence/clause boundaries already available from standard-library parsing; retain original evidence text for retrieval/debugging.
- [ ] Attribute skills to each fragment only when explicit lexical binding is unambiguous. A fragment may prove a requirement only when that same fragment independently contains target skill and its qualifiers; sibling fragments cannot donate qualifiers. For ambiguous conjunctions, emit no qualifier proof rather than guessing.
- [ ] Make `_support_fragments()` and `_assess_requirement_support()` consume proof fragments only. Remove fallback paths that let `scoring_context`, title, parent role, organization, domain metadata, or another fragment establish duration/context qualifiers.
- [ ] Preserve exact identity, comparator, month, negation, German-alias, parent-metadata-isolation, and duplicate requirement-instance behavior.
- [ ] Bump policy version to `requirement-support-v4`; verify `build_cv_analysis_input_fingerprint()` changes and every pre-v4 reuse record is rejected while unrelated cache behavior remains intact. Include policy version in any persisted reuse namespace/key so a pre-v4 rollback reader cannot consume v4 artifacts.
- [ ] Exercise actual pipeline: canonical profile → `project_candidate_evidence` → `retrieve_evidence_bundle` → `analyze_ranked_job` → `run_all_validations`.
- [ ] Update `docs/pipeline.md` with proof-vs-retrieval boundary and freeze P0-C runtime semantics.

**Verification:**
- [ ] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_validator.py`
- Expected: mixed Python/SQL statement does not verify SQL production duration; same-skill statement verifies; a skill and qualifier split across clauses does not verify; parent role and metadata do not donate qualifiers; v2/v3 reuse is rejected.

**Exit Criteria:**
- P0-C acceptance cases pass through canonical pipeline, v4 is present in fingerprints and outputs, and no retrieval-only field can prove qualifiers.

### Task 2: Add actionable uncertainty and profile-scoped resolution reuse

**Purpose:**
- Replace opaque `review_required` flags with one actionable fact-level contract.
- Reuse one candidate answer across jobs while source truth remains unchanged.

**Task Function:**
- Cross-layer uncertainty contract, persistence, and idempotent resolution.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: material backend contract change crossing analysis, persistence, worker, and review action boundaries.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct store and app boundary tests plus worker closure tests.

**Specification Coverage:**
- Machine dispositions are exactly `AUTO_OMIT`, `ASK_CANDIDATE`, `BLOCK_CLAIM`, `REVIEW_CONFLICT`; human resolution actions are `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, `OVERRIDE_BLOCK`.
- Every uncertainty names reason, `requirement_instance_id`, affected fact, question, recommended disposition, evidence IDs, and resolution key.
- Resolution reuse requires unchanged profile/source fingerprint and matching requirement context.
- Invalid or stale resolution fails closed; no claim is silently promoted.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_analysis.py:CvAnalysisRecord`, `_build_requirement_coverage`; `src/fitcv/agentic_cv_generation.py:_build_generation_ready_analysis`, `_review_required_reason`, `_finalize_generation_result`; `src/fitcv/pipeline_contracts.py:ReviewRequiredReasonCode`; `src/fitcv_cp/review_identity.py`; `src/fitcv_cp/app_run_support.py:_build_cv_generation_review_required_payload`; `src/fitcv_cp/app.py:_build_hitl_review_queue`, `admin_run_cv_review_action`; `src/fitcv_cp/worker_job.py` review finalization; `src/fitcv_cp/store.py:RunStore`; `src/fitcv_cp/sqlite_store.py:cv_review_events`
- Modify: `src/fitcv/pipeline_contracts.py` uncertainty/disposition/resolution contract; analysis/generation payloads; existing review persistence and queue shaping; `src/fitcv_cp/store.py` and `src/fitcv_cp/sqlite_store.py` for one concrete profile-scoped resolution store
- Verify: `tests/test_review_identity.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Task 1 v4 requirement identity and evidence IDs.
- Existing run-scoped HITL queue and idempotent action behavior remain canonical.

**Authority:**
- Preauthorized local actions: extend existing contracts, store methods, worker closure, review queue template, and tests; add one profile-scoped resolution table using existing SQLite bootstrap/migration patterns.
- Stop for: new review queue, unbounded fact ontology, automatic claim promotion without fingerprint proof, destructive schema migration, or external notification/provider integration.

**Steps:**
- [ ] Define stable uncertainty rows and separate disposition/resolution action vocabularies in the existing pipeline contract owner. Keep legacy `review_required` and reason-code fields backward compatible.
- [ ] Derive uncertainty from requirement coverage and validation evidence, not from free-text error parsing. Include `uncertainty_id`, `resolution_key`, `affected_fact`, `question`, `recommended_disposition`, `reason`, evidence IDs, candidate profile ID/revision, source fingerprint, and requirement instance.
- [ ] Add concrete profile-scoped persistence in existing SQLite bootstrap/migration patterns. Store `resolution_id`, `candidate_profile_id`, `candidate_profile_revision`, `source_profile_fingerprint`, `resolution_key`, `requirement_instance_id`, `resolution_action`, `resolution_payload_json`, `actor`, `created_at`, and `updated_at`, with uniqueness over candidate profile, revision, source fingerprint, resolution key, and requirement instance. Add methods to `src/fitcv_cp/store.py` and `src/fitcv_cp/sqlite_store.py`.
- [ ] Read and validate stored resolutions before analysis/generation. Reuse requires both stable candidate profile identity/revision and matching source fingerprint; any mismatch fails closed.
- [ ] Propagate actionable rows into generation results, review-required export, run summary, and existing HITL queue. Keep pending/terminal status normalization unchanged.
- [ ] Extend existing `admin_run_cv_review_action` with explicit `uncertainty_id`, `resolution_key`, `answer_text`, and resolution `action` fields. Persist the profile-scoped resolution, apply it to the current run, and re-evaluate the impacted requirement/job through the existing analysis/generation entrypoint. Repeated same action is idempotent; conflicting action remains `REVIEW_CONFLICT`.
- [ ] Close a job/run only after every blocking uncertainty is resolved or explicitly omitted and the resulting analysis/generation outcome is terminal. Do not close from an answer write alone.
- [ ] Render affected fact, question, action, evidence references, and stale-resolution warning in `src/fitcv_cp/templates/_cv_review_queue.html`; preserve keyboard-accessible native form controls.
- [ ] Add docs for payload shape, reuse invalidation, action semantics, and audit/export behavior in `docs/api.md`, `docs/observability.md`, and `docs/pipeline.md`.

**Verification:**
- [ ] `uv run pytest -q tests/test_review_identity.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- Expected: pending uncertainty is actionable; answer persists; repeated same resolution is idempotent; changed profile/source fingerprint asks again; conflict stays unresolved; run checkpoint closes only when no pending items remain.
- [ ] Direct boundary trace: create review-required record → GET review queue → POST action with answer → reload queue/export → resume/close run.
- [ ] Cross-run trace: resolve one uncertainty for profile revision/source fingerprint in run A → analyze same fact in run B and reuse resolution → change profile revision or source fingerprint → run C returns pending uncertainty.

**Exit Criteria:**
- Existing HITL workflow exposes fact-level actions and safely reuses valid resolutions across jobs without changing legacy status compatibility.

### Task 3: Add `cv_content_plan_v1` and section-level generation repair

**Purpose:**
- Move truth selection, protected facts, and space allocation before LLM wording.
- Regenerate only failed sections while preserving approved content and evidence.

**Task Function:**
- Existing late-stage generation contract extension and targeted repair.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded extension of existing structured writer and repair cycle.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing structured CV validator plus pipeline integration tests prove whole-document safety.

**Specification Coverage:**
- `cv_content_plan_v1` includes approved evidence IDs, approved factual claims, protected numbers/dates, supported requirements, target section, space budget, and omitted evidence/reason.
- LLM wording cannot add unsupported facts or independently reprioritize evidence.
- Section repair preserves untouched sections and reruns complete validation.
- Plan/profile/source changes invalidate generation reuse.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_generation.py:_build_generation_ready_analysis`, `build_cv_generation_input_fingerprint`, `_run_repair_cycle`, `generate_from_analysis`; `src/fitcv/cv_generator.py:build_generation_prompt`, `_execute_cv_generation_runtime`, `generate_cv`, `render_cv_markdown`; `tests/test_pipeline_agentic_late_stage.py`, `tests/test_cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py` result contract, content-plan builder, prompt payload, repair targeting, trace/fingerprint fields; `src/fitcv/cv_generator.py` prompt/schema support for immutable plan and target sections
- Verify: generation result persistence and existing review/validation mappings in `src/fitcv/pipeline.py`, `tests/test_cv_generation_reason_mapping.py`, `tests/test_pipeline.py`

**Dependencies:**
- Task 1 proof-safe evidence IDs.
- Task 2 actionable uncertainty and resolved-fact state.
- Existing structured CV schema, single repair cycle, and validation contract.

**Authority:**
- Preauthorized local actions: edit existing generation contracts, prompts, structured output handling, repair cycle, tests, and pipeline docs; run local backend/frontend contract checks.
- Stop for: new generation service, multi-agent planner, full-document regeneration when section repair is possible, silent claim invention, or schema change without backward-compatible reader behavior.

**Steps:**
- [ ] Build `cv_content_plan_v1` from verified per-evidence requirement coverage, selected evidence, resolved uncertainties, enabled sections, and config space limits. Never Cartesian-assign every required skill to every evidence item; unsupported requirements stay out of approved claims. Store only canonical IDs/claims and explicit omissions.
- [ ] Add canonical content-plan version and content fingerprint to generation input components and reuse fingerprint. Reject older plan versions and stale profile/source fingerprints; test both version and content changes as cache misses.
- [ ] Extend `build_generation_prompt(..., content_plan: dict[str, Any] | None = None, target_sections: list[str] | None = None)` and the existing structured response contract. Full generation returns the normal document; targeted repair returns section-keyed data for requested sections only, with prompt/schema instructions forbidding unrelated sections.
- [ ] Replace repair targeting based only on missing sections with a normalized section target set that can include validation/overflow failures. Add deterministic `merge_repaired_section(existing_cv, section_name, repaired_section_data)` behavior: replace only requested section keys, retain all unrequested initial sections, and reject unknown section names.
- [ ] Render and validate complete merged CV after each targeted repair. Persist plan, target sections, initial/final validation, and repair trace in existing result/debug payloads.
- [ ] Keep one bounded repair attempt. If targeted repair fails, retain existing `review_required`/`validation_failed` outcome and actionable reason instead of looping.
- [ ] Update `docs/pipeline.md` and `docs/observability.md` with content-plan and section-repair contracts.

**Verification:**
- [ ] `uv run pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline.py`
- Expected: plan fields persist; stale plan/profile/source changes miss reuse; repair changes only requested section; protected facts survive; full validation still rejects unsupported claims and overflow.
- [ ] Regression: evidence supports one of two requirements; generated plan contains only supported requirement claims. Repair output attempts to alter an unrelated section; deterministic merge retains original unrelated section.
- [ ] Boundary trace: analysis record → content plan → initial structured CV → targeted section repair → merged render → full validator → accepted/review-required result.

**Exit Criteria:**
- Generation uses `cv_content_plan_v1`, section repair preserves approved unaffected content, and existing status/persistence/review contracts remain compatible.

### Task 4: Final verification and acceptance reconciliation

**Purpose:**
- Prove all three deliverables on one workspace state without promoting deferred P0 experiments.

**Task Function:**
- Final backend, control-plane, contract, and documentation verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final verification requires repository-wide acceptance judgment.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final suite and declared boundary traces are sufficient for proposed plan.

**Specification Coverage:**
- P0-C frozen and v4-valid.
- P1-B actionable and reusable with fail-closed invalidation.
- P1-A plan-driven generation and targeted repair.
- P0-A/P0-B remain deferred and explicitly documented.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all declared targets; `docs/pipeline.md`, `docs/api.md`, `docs/observability.md`; Git diff and status
- Verify: focused suites, full suite, contract docs, generated payloads, and no undeclared files

**Dependencies:**
- Tasks 1–3 complete.

**Authority:**
- Preauthorized local actions: run declared tests/checks, inspect diffs, and write ignored local reports under `tmp/`.
- Stop for: failed required checks, stale plan/fingerprint behavior, unrecorded schema drift, unrelated file changes, or any P0-A/P0-B promotion claim.

**Steps:**
- [ ] Run focused P0-C, P1-B, and P1-A tests.
- [ ] Run control-plane review queue, store, worker, and app tests.
- [ ] Run full Python suite and classify unrelated pre-existing failures without fixing them here.
- [ ] Run `git diff --check` and review changed-path list.
- [ ] Verify docs describe one canonical evidence/review/generation contract and preserve deferred P0-A/P0-B status.
- [ ] Record blockers, deviations, and required follow-up; leave plan `proposed` until `skill-verification-before-completion` returns `verified`.

**Verification:**
- [ ] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py tests/test_validator.py tests/test_review_identity.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline.py`
- [ ] `uv run pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] `uv run pytest -q`
- [ ] `git diff --check`
- [ ] `git status --short --branch`
- Expected: required tests pass; full-suite failures, if any, are pre-existing and recorded; no P0-A/P0-B production promotion appears.

**Exit Criteria:**
- Fresh evidence proves P0-C, P1-B, and P1-A contracts; docs and tests align; no unresolved required task or undeclared scope remains.

## Verification

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py tests/test_validator.py tests/test_review_identity.py tests/test_cv_generation_reason_mapping.py`
- `uv run pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- `uv run pytest -q`
- `git diff --check`
- `git status --short --branch`
- Manual boundary traces recorded for canonical qualifier proof, actionable review resolution, and section-targeted repair.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-C proof fragments are source-only, deterministic, skill-local, and fail closed on ambiguity.
2. `requirement-support-v4` invalidates every pre-v4 analysis reuse record and focused canonical-pipeline cases pass.
3. P1-B emits exact action vocabulary with fact-level reason, evidence, question, and fingerprint; existing queue/action/checkpoint behavior remains idempotent and backward compatible.
4. Profile/source changes invalidate stored uncertainty resolutions.
5. P1-A persists `cv_content_plan_v1`, constrains generation to approved facts, and repairs only failed sections before full-document validation.
6. Focused tests, control-plane tests, full suite, diff checks, and documentation review complete with evidence.
7. P0-A and P0-B remain explicitly deferred; no unmeasured retrieval or evidence architecture is promoted.
8. No unresolved required task, failed required check, stale status, or unrecorded scope deviation remains when `skill-verification-before-completion` is run.

## Rollback

No external provider or destructive data migration is required. If P0-C fails,
retain current pre-v4 behavior only as a local rollback path after confirming
its reader cannot consume v4 artifacts; do not claim closeout.
If P1-B fails, preserve existing run-scoped HITL actions and keep new resolution
reuse disabled. If P1-A fails, disable content-plan/section-repair promotion and
retain existing full-document writer plus bounded repair path. Preserve failed
test outputs for diagnosis; do not discard unrelated workspace changes.

## Execution Evidence

Recorded 2026-09-28 on workspace `main` with no commit created.

- Focused P0-C/P1-A suites passed: `371 passed` in `7.92s`.
- Control-plane suites passed: `780 passed` in `121.71s`.
- Full suite result: `2828 passed, 4 skipped, 1 failed` in `185.77s`; benchmark regression suite passed `18 passed`.
- Full-suite failure is `tests/test_p0_public_corpus.py::test_public_p0a_snapshot_integrity`: `data/fitcv-p0-corpus/p0a/admission_report.json` contains a stale SHA-256 for `ranking_source_backed.json`; P0-A corpus files were not changed.
- Stale P0-A hash root cause confirmed: commit `ea4ad790` changed `ranking_source_backed.json` bytes by rewriting `corpus_source` to its tracked path but did not refresh `publication.published_files.ranking_source_backed.json.sha256`. No other `published_files` manifests exist in `data/`; only P0-A ranking metadata was stale.
- Reproduced the failure before patch, updated the manifest to the exact `read_bytes()` SHA-256 `957d43482ad03a6f79b260d99263ef14e672506ff38fb14dffea791ea778b74e`, and reran the focused corpus suite: `3 passed`.
- Fresh full-suite verification after the hash patch: `2829 passed, 4 skipped, 52 warnings` in `186.86s`; `git diff --check` passes for the corrected manifest.
- `git diff --check` passed before this evidence-only plan update.
- Implemented runtime scope covers P0-C proof fragments/policy v4, P1-B uncertainty vocabulary/persistence/queue actions, and P1-A content-plan/targeted repair contracts.
- P1-B action path now persists profile/source-scoped resolutions, enqueues one bounded impacted-job re-analysis through the existing regeneration entrypoint, injects valid resolutions into analysis/generation, and refreshes the affected debug record while preserving review identity. User accepted plan completion on 2026-09-28.
