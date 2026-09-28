---
layer: change
artifact_type: plan
status: blocked
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-closeout
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_rag_impact.py
  - data/fitcv-p0-corpus
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_cv_generator.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_ranking_evaluation.py
  - tests/test_benchmark_requirement_support.py
  - docs/pipeline.md
  - docs/api.md
  - docs/observability.md
---

# FitCV P0 and P1 Closeout Plan

## Review Basis

The supplied verdict is accepted as the current assessment of main at
8d646c357cc3a54966d7cb380c0d96cf448176a2. It is well founded, with one scope
clarification: “complete P0 and P1” means finish runtime correctness and produce
measured decisions for P0-A/P0-B, finish P1-A/P1-B, and leave P1-C/P2 explicitly
deferred. P0-A/P0-B must not be promoted from synthetic or all-positive data.

Current source review confirms the verdict's integration-risk pattern:

- src/fitcv/evidence.py:project_candidate_evidence builds support_fragments twice,
  so later metadata-derived material can replace source-only proof.
- src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage treats a non-empty
  RESOLVE_WITH_ANSWER or OVERRIDE_BLOCK payload as verified without qualifier assessment.
- src/fitcv_cp/worker_job.py:_load_requirement_resolutions exits before its storage
  lookup, while lookup code is appended to _persist_resolution_reanalysis.
- build_requirement_uncertainty can emit empty profile identity fields that later
  setdefault calls cannot repair; generation contracts expose uncertainties but
  must be checked across all return paths.
- cv_content_plan_v1 exists, but writer input still needs an explicit
  approved-evidence projection and before/after token evidence.

No new evidence model, answer-validation subsystem, persistent cache service,
retrieval architecture, agent, GraphRAG path, or P1-C work enters this plan.

## Goal

Complete P0 and P1 with one coherent, fail-closed evidence contract; a working
user-to-storage-to-worker-to-refresh uncertainty lifecycle; a content compiler
that actually constrains writer context; and reproducible offline decisions for
retrieval and evidence-selection strategy.

## Implementation Outcomes

### P0 correctness and decisions

- P0-C proof uses source text fragments only, preserves skill-local qualifier
  attribution, fails closed on ambiguity, and advances
  REQUIREMENT_SUPPORT_POLICY_VERSION to requirement-support-v5.
- Candidate answers are assessed through the same requirement-support contract;
  contradictions and insufficient qualifiers never become verified evidence.
- OVERRIDE_BLOCK permits workflow continuation but never manufactures factual proof.
- P0-A produces a held-out multilingual ranking comparison across incumbent,
  lexical, and one multilingual encoder arm, or records the encoder as unavailable
  without changing production defaults.
- P0-B produces a production-versus-full-pool diagnostic comparison over reviewed
  boundary cases and records a bounded promotion or retention decision.

### P1 completion

- P1-B resolution loading, persistence, re-analysis, debug replacement, review
  identity, and queue refresh work end to end and remain profile/source scoped.
- Uncertainty identity survives analysis, generation, persistence, review, and
  refresh; changed profile revision or source fingerprint invalidates reuse.
- P1-A writer input contains only approved evidence from cv_content_plan_v1;
  full evidence remains available for diagnostics and validators. One bounded
  section repair preserves unaffected sections and revalidates the full CV.
- P1-A/P1-B scorecards report context reduction, repair outcomes, reuse, manual
  actions, latency, and accepted-CV economics.
- P1-C, P2, GraphRAG, advanced routing, and extra-agent work remain deferred.

## Execution Approach

- Mode: inline sequential
- Coordination: git-tracked
- Required skills: skill-systematic-debugging, skill-test-driven-development, skill-backend-verification, skill-full-stack-integration, skill-performance-optimization, skill-plan-document-reviewer, skill-verification-before-completion
- Isolation: current workspace; preserve unrelated files and worktrees
- Commit policy: verified per-task checkpoint commits preauthorized
- Preauthorized local actions: inspect declared source/tests/docs, edit declared paths, run declared local tests and offline benchmarks, write ignored benchmark reports, update this plan's task ledger, and create verified per-task checkpoint commits
- User-approval actions: push, merge, publication, destructive cleanup, discard, external provider access, and production-default changes
- Parallel ownership: none; P0-C, P1-B, and P1-A share fingerprints, evidence IDs, and payload contracts
- Sequential fallback: execute Tasks 1–6 in order; stop when a required contract or data gate fails

## Coordination State

- Coordination owner: single lead controller
- Coordination schema: 2
- Branch: main
- Base commit: 8d646c357cc3a54966d7cb380c0d96cf448176a2
- Expected workspace: current main ahead of origin/main by verified checkpoint; preserved untracked .tmp benchmark reports and this active plan
- Next action: add promotion-grade reviewed P0-A/P0-B coverage before changing production retrieval defaults
- Blockers: P0-A multilingual backend unavailable and promotion-grade held-out fixture absent; P0-B fixture validation is `6/17`; runtime P0-C/P1-A/P1-B closeout is verified

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | completed | current | codex | none | canonical P0-C tests | `157 passed`; checkpoint `515426f8` |
| Task 2 | completed | current | codex | Task 1 | resolution lifecycle trace | `822 passed`; loader/persistence guards pass |
| Task 3 | completed | current | codex | Tasks 1–2 | writer-context and repair tests | `230 passed`; filtering metrics recorded |
| Task 4 | blocked | current | codex | Task 1 | held-out ranking report | measured DE/EN; multilingual backend unavailable; fixture hash now bound to every report |
| Task 5 | blocked | current | codex | Task 1 | qualified-support comparison | equal arms; reviewed coverage insufficient for promotion |
| Task 6 | completed | current | codex | Tasks 2–5 | final suites and scorecard | `2860 passed, 4 skipped`; diff-check clean; P0-A/P0-B promotion blockers recorded |

## Task Breakdown

### Task 1: Restore P0-C proof boundary and candidate-answer semantics

Purpose:
- Make requirement verification depend only on source fragments that belong to the
  requirement, then reuse that contract for candidate answers.

Task Function:
- Evidence-boundary repair and canonical-path regression proof.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: shared contract, high correctness risk, small write surface.

Validator Profile:
- Controller-selected: none
- Selection basis: focused canonical tests and static source inspection cover the bounded contract.

Specification Coverage:
- P0-C source-only proof, qualifier locality, v5 invalidation, candidate-answer
  assessment, and non-evidentiary operator override.

Required Skills:
- skill-systematic-debugging, skill-test-driven-development, skill-backend-verification

Files And Symbols:
- Inspect: src/fitcv/evidence.py:project_candidate_evidence, _build_support_fragments, _support_fragments, _assess_requirement_support, REQUIREMENT_SUPPORT_POLICY_VERSION
- Inspect: src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage, _append_resolution_evidence, _resolution_map
- Modify: src/fitcv/evidence.py, src/fitcv/agentic_cv_analysis.py
- Verify: tests/test_evidence.py, tests/test_agentic_cv_analysis.py, tests/test_validator.py, docs/api.md, docs/pipeline.md

Dependencies:
- Current source and existing requirement-support tests.
- No P1-B storage work may mask P0-C failures.

Authority:
- Preauthorized local actions: edit P0-C runtime/contracts/tests/docs, run focused backend checks, and create the verified Task 1 checkpoint commit.
- Stop for: new evidence model, semantic parser, answer-validation subsystem, production retrieval change, or any claim that metadata proves requirements.

Steps:
- [x] Step 1: Remove duplicate metadata-derived support_fragments construction in project_candidate_evidence; retain _build_support_fragments(text, skills) as the only proof source and keep title, role, company, domain, location, and scoring_context retrieval-only.
- [x] Step 2: Bump REQUIREMENT_SUPPORT_POLICY_VERSION to requirement-support-v5; update every reuse/fingerprint comparison and reject v2–v4 artifacts as stale.
- [x] Step 3: Convert RESOLVE_WITH_ANSWER text into a temporary requirement-scoped candidate_resolution fragment and run the existing qualifier assessment. Map full satisfaction to verified, contradiction to contradicted, insufficient qualifier to relevant_unverified, ambiguity to unverified, and empty answer to pending.
- [x] Step 4: Keep CONFIRM_OMIT as omission and change OVERRIDE_BLOCK to workflow continuation without verified support, approved claim, or writer evidence.
- [x] Step 5: Add canonical-path regressions through profile → project_candidate_evidence → retrieve_evidence_bundle → requirement_coverage for production SQL versus classroom SQL, including the inverse Python case so false positives and false negatives are covered.
- [x] Step 6: Add a small AST/source regression guard for duplicate literal support_fragments keys in the canonical projection and undefined locals in the worker module; use stdlib ast, not a new dependency.

Verification:
- [x] uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py (`157 passed`)
- Expected: source-only proof passes; metadata-only or cross-skill text is not verified; qualified candidate answer verifies; contradiction and insufficient qualifier remain unverified/contradicted; v4 reuse is rejected.
- [x] Direct trace: canonical profile → projected fragments → selected/pool support → requirement coverage → uncertainty/claim decision.

Exit Criteria:
- P0-C is fail-closed and v5-scoped; no candidate answer or override can manufacture factual proof.

### Task 2: Repair P1-B resolution lifecycle and identity propagation

Purpose:
- Restore storage lookup and prove review answer → persisted resolution → worker
  reuse → re-analysis → refreshed debug/review state.

Task Function:
- Backend lifecycle repair with direct boundary and state-transition proof.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: shared worker/storage contract and high integration risk.

Validator Profile:
- Controller-selected: none
- Selection basis: end-to-end control-plane tests cover success, stale identity,
  idempotency, and failure paths.

Specification Coverage:
- P1-B actionable uncertainty, profile/source-scoped reuse, bounded re-analysis,
  queue refresh, review identity preservation, and fail-closed invalidation.

Required Skills:
- skill-systematic-debugging, skill-test-driven-development, skill-backend-verification, skill-full-stack-integration

Files And Symbols:
- Inspect: src/fitcv_cp/worker_job.py:_load_requirement_resolutions, _persist_resolution_reanalysis, worker run context and impacted-job regeneration entrypoint
- Inspect: src/fitcv/pipeline_contracts.py:build_requirement_uncertainty, UncertaintyDisposition, UncertaintyResolutionAction
- Inspect: src/fitcv/agentic_cv_analysis.py:_build_requirement_uncertainties, _build_requirement_coverage, resolution map
- Inspect: src/fitcv/agentic_cv_generation.py:CvGenerationResult, generate_from_analysis
- Modify: src/fitcv_cp/worker_job.py, src/fitcv/pipeline_contracts.py, src/fitcv/agentic_cv_analysis.py, src/fitcv/agentic_cv_generation.py, and only existing endpoint/template surfaces required to preserve the current review contract
- Verify: tests/test_fitcv_cp/test_worker_job.py, tests/test_fitcv_cp/test_app.py, tests/test_fitcv_cp/test_sqlite_store.py, tests/test_agentic_cv_analysis.py, tests/test_cv_generation_reason_mapping.py, docs/api.md, docs/pipeline.md

Dependencies:
- Task 1 candidate-resolution semantics and v5 fingerprint policy.
- Existing list_requirement_resolutions, review action endpoint, queue, and regeneration entrypoint.

Authority:
- Preauthorized local actions: edit existing P1-B runtime/storage/endpoint/tests/docs, run local control-plane tests, and create the verified Task 2 checkpoint commit.
- Stop for: new queue, new persistence service, unbounded re-analysis, cross-profile resolution reuse, destructive migration, or silently closing review without refreshed evidence.

Steps:
- [x] Step 1: Move all profile identity validation, projection fingerprint construction, list_requirement_resolutions lookup, exception handling, and list return into _load_requirement_resolutions(run, profile); guarantee list[...] on every path.
- [x] Step 2: Remove lookup code from _persist_resolution_reanalysis; keep that function limited to loading debug payload, replacing the affected job record, preserving review_item_id, persisting the payload, and returning without storage lookup.
- [x] Step 3: Pass candidate profile ID, revision, and source fingerprint directly into build_requirement_uncertainty; replace falsey identity fields instead of relying on setdefault.
- [x] Step 4: Ensure every CvGenerationResult and persisted debug record preserves uncertainties, resolution IDs/actions, coverage, content plan, and re-analysis metadata.
- [x] Step 5: Preserve one bounded impacted-job re-analysis, queue refresh, and idempotent repeated action behavior; changed revision, changed projection fingerprint, missing profile identity, and malformed storage rows fail closed.
- [x] Step 6: Add the full boundary test: review answer → save resolution → worker loads resolution → fresh analysis → fresh generation → debug record replacement → queue refresh; include contradiction, CONFIRM_OMIT, OVERRIDE_BLOCK, stale identity, and duplicate-action cases.

Verification:
- [ ] uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py
- Expected: resolution lookup returns a list, re-analysis writes no undefined-local path, stale resolutions are not reused, review identity is preserved, and exactly one bounded refresh occurs.
- [ ] Direct boundary trace records storage row before/after, worker config before/after, analysis status, generation status, debug replacement, and queue state.

Exit Criteria:
- P1-B works across user, storage, worker, analysis, generation, persistence, and review surfaces without parallel workflow state.

### Task 3: Make P1-A content plan constrain writer context

Purpose:
- Finish the measurable part of P1-A without prematurely building a page
  optimizer.

Task Function:
- Content-plan integration, context reduction, and bounded section repair.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: existing contract is present; change should remain minimal.

Validator Profile:
- Controller-selected: none
- Selection basis: generation, validator, and pipeline tests prove preserved facts.

Specification Coverage:
- cv_content_plan_v1, approved evidence filtering, protected facts, one bounded
  section repair, full-document validation, and P1-A measurement.

Required Skills:
- skill-test-driven-development, skill-backend-verification, skill-performance-optimization

Files And Symbols:
- Inspect: src/fitcv/agentic_cv_generation.py:build_cv_content_plan, generate_from_analysis, repair trace/result assembly
- Inspect: src/fitcv/cv_generator.py:build_generation_prompt, structured response schema, generation input fingerprint
- Inspect: src/fitcv/pipeline.py generation persistence and validation handoff
- Modify: src/fitcv/agentic_cv_generation.py, src/fitcv/cv_generator.py, src/fitcv/pipeline.py, and existing observability/docs surfaces
- Verify: tests/test_cv_generator.py, tests/test_pipeline_agentic_late_stage.py, tests/test_pipeline.py, tests/test_cv_generation_reason_mapping.py, docs/pipeline.md, docs/observability.md

Dependencies:
- Task 1 verified evidence IDs and resolved-fact semantics.
- Task 2 verified uncertainty preservation and resolution identity.

Authority:
- Preauthorized local actions: edit existing generation/pipeline contracts, prompts, tests, and docs, write ignored benchmark reports, and create the verified Task 3 checkpoint commit.
- Stop for: a separate compiler service, persistent plan cache, full-document retry when section repair applies, or page-allocation heuristics unsupported by measurements.

Steps:
- [x] Step 1: Keep cv_content_plan_v1 deterministic and derive approved claims only from verified requirement coverage, approved evidence IDs, resolved facts, protected numbers/dates, enabled sections, and explicit omission reasons.
- [x] Step 2: Build a writer evidence payload by filtering analysis evidence to content_plan.approved_evidence_ids; retain full evidence only in diagnostics and validator input where required for audit.
- [x] Step 3: Include plan version and content fingerprint in generation input components and reuse decisions; stale plan, profile, source, or policy versions force fresh generation.
- [x] Step 4: Keep one bounded targeted repair. Replace only requested section keys, preserve unrelated sections, reject unknown section names, render the complete document, and run complete validation after merge.
- [x] Step 5: Persist before/after input token estimates, approved/omitted evidence counts, repair attempted/accepted, page-overflow rate, unsupported-claim violations, and full-regeneration count in existing trace fields.
- [x] Step 6: Add focused tests proving an unsupported evidence item never reaches writer input, protected facts survive repair, unrelated sections remain unchanged, and full validation still rejects unsupported claims.

Verification:
- [ ] uv run pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_cv_generation_reason_mapping.py
- Expected: writer sees only approved evidence; targeted repair preserves unaffected sections; final validation runs on the merged full CV; stale plan fingerprints miss reuse.
- [ ] Compare trace metrics before and after filtering on existing deterministic generation fixtures; record token reduction or truthful not_applicable when no approved evidence exists.

Exit Criteria:
- P1-A context reduction is real, measured, and compatible with existing generation, validation, persistence, and review statuses.

### Task 4: Complete P0-A multilingual retrieval decision experiment

Purpose:
- Turn P0-A from plumbing into a reproducible offline decision without changing
  production defaults during measurement.

Task Function:
- Held-out ranking experiment and promotion/retention decision.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: bounded offline benchmark; no runtime architecture change.

Validator Profile:
- Controller-selected: none
- Selection basis: existing benchmark and ranking evaluation tests cover metric correctness.

Specification Coverage:
- Relevant/borderline/irrelevant multilingual corpus, held-out Recall@N,
  Precision@N, nDCG, cold/warm p50/p95, fallback rate, and storage overhead.

Required Skills:
- skill-performance-optimization, skill-test-driven-development

Files And Symbols:
- Inspect: scripts/benchmark_ranking.py:_run_once, _split_metric_rows, main; tests/test_ranking_evaluation.py
- Modify: data/fitcv-p0-corpus/p0a/ranking_source_backed.json, its admission/hash manifest, and only benchmark tests/docs if fixture schema requires it
- Verify: scripts/benchmark_ranking.py, tests/test_ranking_evaluation.py, docs/pipeline.md, a checked-in decision report under docs/superpowers/evidence/

Dependencies:
- Task 1 must establish corrected evidence semantics before any downstream quality claim.
- Corpus must contain 100–300 reviewed jobs with relevant, borderline, and irrelevant labels and held-out splits; the current all-positive corpus cannot pass this gate.

Authority:
- Preauthorized local actions: add/review offline fixture labels, run deterministic ranking arms, write evidence reports, update benchmark tests/docs, and create the verified Task 4 checkpoint commit.
- Stop for: provider authentication, production default changes, permanent experiment flags, or a multilingual arm that reports not_run without recording that limitation.

Steps:
- [ ] Step 1: Expand or replace the P0-A source-backed fixture to 100–300 jobs across German and English with reviewed relevant, borderline, and irrelevant labels, calibration/held-out splits, and valid manifest hashes. **Blocked:** current source-backed fixture lacks promotion-grade mixed-label review coverage.
- [x] Step 2: Run incumbent and lexical arms with uv run python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --arm incumbent --warmup-iterations 5 --measured-iterations 30 --output .tmp/p0a-incumbent.json and the equivalent --arm lexical command.
- [x] Step 3: Run the multilingual arm with the same fixture and iteration counts; record not_run and backend-unavailable reason if no approved encoder is available.
- [x] Step 4: Report held-out Recall@N, Precision@N, nDCG, language split metrics, cold/warm p50/p95, fallback count, backend/storage overhead, correctness status, and `fixture_sha256` bound to report bytes.
- [x] Step 5: Choose incumbent retention or one production strategy only when held-out quality and operational thresholds are met; otherwise retain incumbent and record the missing evidence.

Verification:
- [x] uv run pytest -q tests/test_ranking_evaluation.py tests/test_p0_public_corpus.py
- [x] Run all three benchmark commands above and inspect JSON schema/status, including matching `fixture_sha256`.
- Expected: no all-positive shortcut, held-out metrics are present for measured arms, unavailable arms are explicit, and production defaults remain unchanged until a recorded decision passes.

Exit Criteria:
- P0-A has a reproducible decision report or an explicit data/provider blocker; no unsupported multilingual promotion claim remains.

### Task 5: Complete P0-B qualified-support comparison and simplification decision

Purpose:
- Determine whether production evidence selection loses qualified support and whether
  hash-derived semantic scoring earns its complexity.

Task Function:
- Full-pool diagnostic experiment and lexical-only comparison.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: existing benchmark arm registry and bounded fixture.

Validator Profile:
- Controller-selected: none
- Selection basis: support benchmark and comparison tests cover the output contract.

Specification Coverage:
- Boundary labels for selection misses, compound requirements, multiple evidence
  items, aliases, duration, negation, context, production/full-pool comparison,
  and lexical-only simplification.

Required Skills:
- skill-performance-optimization, skill-test-driven-development, skill-backend-verification

Files And Symbols:
- Inspect: src/fitcv/evidence.py:retrieve_evidence_bundle, channel-pool merge, qualifier annotation, final selector
- Inspect: scripts/benchmark_requirement_support.py arm registry and report schema
- Inspect: existing comparison script/tests and data/fitcv-p0-corpus/p0b/*
- Modify: scripts/benchmark_requirement_support.py, comparison tests/docs, and reviewed P0-B labels/manifests only when needed to satisfy coverage gates
- Verify: tests/test_evidence.py, tests/test_benchmark_requirement_support.py, existing comparison tests, docs/pipeline.md

Dependencies:
- Task 1 corrected support semantics.
- Reviewed P0-B evidence must cover selection-boundary misses, compound requirements,
  multiple support items, canonical aliases, duration, negation, and context.

Authority:
- Preauthorized local actions: extend deterministic benchmark arms, add reviewed labels, run comparisons, write evidence reports, and create the verified Task 5 checkpoint commit.
- Stop for: direct-support recovery paths, unbounded candidate expansion, LLM/reranker use, or production rollout before qualified-support comparison.

Steps:
- [ ] Step 1: Add or validate reviewed P0-B labels and manifest hashes for the listed boundary cases; record coverage counts and any unavailable category. **Blocked:** current fixture validation passes `6/17`; broader reviewed labels remain required.
- [x] Step 2: Measure production, full_pool_diagnostic, and lexical_only arms with the same corrected qualifier contract, final top_k, warm/cold conditions, and candidate profile/job fixture.
- [x] Step 3: Report qualified requirement recall, qualified evidence-pair recall, retrieval-to-selection loss, pool/selected context size, p50/p95 latency, duplicates, and validation outcomes.
- [x] Step 4: Promote full_pool_diagnostic or lexical_only only when qualified support is non-decreasing, quality gains meet the recorded threshold, latency/context stay within budget, and validator outcomes remain compatible. **Retained production; promotion gate not met.**
- [x] Step 5: If semantic scoring does not earn its cost, remove only after report approval: hash embeddings, semantic weights, cache/settings knobs, and dependent diagnostics/fingerprints. Keep rollback evidence. **No deletion: fixture does not earn simplification decision.**

Verification:
- [x] uv run pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_rag_impact.py
- [x] uv run python scripts/benchmark_requirement_support.py --arm production --runs 50 --warmups 5 --output .tmp/p0b-production.json
- [x] uv run python scripts/benchmark_requirement_support.py --arm full_pool_diagnostic --runs 50 --warmups 5 --output .tmp/p0b-full-pool.json
- [x] uv run python scripts/benchmark_requirement_support.py --arm lexical_only --runs 50 --warmups 5 --output .tmp/p0b-lexical-only.json
- [x] Preserve JSON outputs under .tmp/ and write one comparison report.
- Expected: selected support never borrows qualifiers across evidence; comparison distinguishes measured, blocked, and not_applicable arms; no production change occurs without threshold evidence.

Exit Criteria:
- P0-B has a reviewed comparison decision, with incumbent retained when evidence is insufficient and unnecessary semantic complexity removed only when measured safe.

### Task 6: Build accepted-CV scorecard and complete verification

Purpose:
- Reconcile runtime, experiment, and operational evidence into one acceptance state.

Task Function:
- Final cross-surface verification and acceptance reconciliation.

Template Profile:
- Controller-selected: none (lead controller)
- Selection basis: repository-wide acceptance judgment.

Validator Profile:
- Controller-selected: none
- Selection basis: fresh focused, control-plane, benchmark, and full-suite evidence.

Specification Coverage:
- P0/P1 completion, deferred-scope honesty, backend boundary proof, and fresh verification.

Required Skills:
- skill-backend-verification, skill-performance-optimization, skill-verification-before-completion

Files And Symbols:
- Inspect: all changed files, existing run/debug artifacts, benchmark reports, docs
- Modify: docs/pipeline.md, docs/api.md, docs/observability.md, this plan's ledger and evidence sections
- Verify: repository-wide tests, benchmark reports, Git state, and no stale hashes

Dependencies:
- Tasks 1–5 complete or explicitly recorded as blocked/not applicable with evidence.

Authority:
- Preauthorized local actions: run final local checks, update docs and plan evidence, reconcile declared scope, and create the verified Task 6 checkpoint commit.
- Stop for: failed required checks, stale plan status, unrecorded scope deviation, production-default mutation, or unrelated workspace cleanup.

Steps:
- [x] Step 1: Build scorecard with median/p95 time per accepted truthful CV, provider calls, input/output tokens, repair attempts, full/section regenerations, manual actions, resolution reuse, questions avoided, and accepted-CV rate; unavailable live/provider fields are recorded as `not_run` or `not_applicable`.
- [x] Step 2: Run focused runtime suites, control-plane suites, ranking/support benchmark tests, full suite, git diff --check, and manifest/hash integrity tests.
- [x] Step 3: Record P0-A/P0-B measured decisions, P1-A/P1-B metrics, blockers, rollback path, and explicit P1-C/P2 deferrals in docs and plan evidence.
- [x] Step 4: Keep plan status active because promotion-grade P0-A/P0-B proof is still blocked; do not claim completed acceptance until those data gates clear.

Verification:
- [x] uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_validator.py tests/test_cv_generation_reason_mapping.py
- [x] uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py
- [x] uv run pytest -q tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_p0_public_corpus.py
- [x] uv run pytest -q — `2860 passed, 4 skipped, 52 warnings`
- [x] git diff --check
- [x] git status --short --branch
- Expected: required suites pass; full-suite failures are fixed or recorded with root cause; no stale hashes, unsupported claim, false verification, broken resolution lifecycle, or unmeasured promotion remains.

Exit Criteria:
- Fresh evidence supports every claimed P0/P1 outcome; deferred work remains explicit; no unresolved required task, failed required check, stale status, or unrecorded deviation remains.

## Verification

- uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_validator.py tests/test_cv_generation_reason_mapping.py
- uv run pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py
- uv run pytest -q tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_p0_public_corpus.py
- uv run pytest -q
- git diff --check
- git status --short --branch
- P0-A/P0-B decision reports, P1-A/P1-B scorecard, and direct lifecycle traces are stored in declared evidence/docs surfaces.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-C proof is source-only, deterministic, skill-local, fail-closed, and v5-scoped.
2. Candidate answers are assessed through the same qualifier contract; overrides do not create proof.
3. P1-B resolution lookup and persistence are separated; full lifecycle and stale-identity invalidation pass.
4. Uncertainty identity survives analysis, generation, storage, re-analysis, and review refresh.
5. P1-A writer receives approved evidence only; one bounded section repair preserves unaffected sections and full validation runs.
6. P0-A has a held-out multilingual decision report or an explicit unavailable/data blocker.
7. P0-B has reviewed boundary labels and a reproducible production/full-pool/lexical-only decision.
8. Accepted-CV economics and P1-A/P1-B metrics are recorded from fresh evidence.
9. P1-C, P2, GraphRAG, advanced routing, and extra agents remain explicitly deferred.
10. skill-verification-before-completion returns verified before status changes to completed.

## Rollback

No destructive migration is required. If P0-C fails, keep v5 artifacts isolated
and disable reuse of new results until the contract is corrected. If P1-B fails,
retain existing run-scoped actions but disable resolution reuse and preserve
pending review. If P1-A fails, retain full evidence in diagnostics and revert
writer filtering/targeted repair while keeping full-document validation. P0-A
and P0-B experiments never modify production defaults without recorded threshold
approval. Preserve benchmark reports and failing test output for diagnosis.

## Evidence

Plan created 2026-09-28 from verdict review and source inspection on main at
8d646c357cc3a54966d7cb380c0d96cf448176a. Initial source baseline was clean. Existing
completed plan docs/superpowers/plans/2026-09-28-fitcv-p0c-p1ab-implementation-plan.md
contains historical execution claims but is not treated as current source truth
when current code contradicts it.
Three independent reviews accepted the concrete test-path, benchmark-arm, and checkpoint-lifecycle fixes. The review suggestion to defer P0-A/P0-B decision work was rejected because the supplied verdict explicitly requires those offline experiments and labels before closeout.
The follow-up stale-report defect was traced to `scripts/benchmark_ranking.py` recording fixture paths without byte hashes; both measured and `not_run` report branches now emit `fixture_sha256`, with focused regression proof. Remaining plan progress is blocked until promotion-grade reviewed P0-A/P0-B labels and an approved multilingual backend exist; no labels or provider results were fabricated.
