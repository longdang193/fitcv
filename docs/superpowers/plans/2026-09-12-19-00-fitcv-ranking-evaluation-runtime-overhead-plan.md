---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-ranking-evaluation-runtime-overhead
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/enrich.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv/llm_runtime.py
  - scripts/benchmark_ranking.py
  - scripts/benchmark_runs_endpoint.py
  - scripts/benchmark_llm_transport.py
  - tests/test_ai_score.py
  - tests/test_enrich.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline_outcome_fact.py
  - tests/test_pipeline.py
  - tests/test_evidence.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_ranking_evaluation.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_run_lifecycle.py
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
---

# Implementation Plan

## Goal

Restore one source of truth for ranking requests, evidence, routing, cache identity, and observations; make ranking evaluation truthful; then remove verified telemetry, Runs-list, and HTTP transport overhead without changing user-visible contracts or losing durable work.

Review evidence is anchored to commit `86f719d`; PR #42 is already present in current `main`. Implementation starts from current `main` at `75e34d10f2276996ae6471a2a926f51b30351e81` (`chore(governance): align agent rules and hook setup`), preserving the merged CV-warning outcome behavior and all unrelated working-tree changes. Reconfirm target symbols against this base before editing.

## Implementation Outcomes

### Canonical ranking and evidence contract

Ranking execution, fingerprinting, reuse, and observation consume the same rendered request, resolved `LlmRouting`, response contract, and generation settings. Each job receives job-relevant evidence selected from one projected profile evidence pool. Observation-enabled and observation-disabled paths produce identical model inputs.

### Trustworthy evaluation and checkpoint compatibility

The benchmark separates evaluator labels from retrieval inputs, evaluates against the complete eligible pool, keeps held-out records out of calibration, reports cutoffs honestly, and distinguishes replay from live provider execution. Legacy checkpoints missing `retrieval_strategy` fail closed instead of bypassing retrieval-contract validation.

### Bounded runtime and data access

Telemetry shutdown has an absolute delivery deadline, leaves unfinished records pending, and preserves stored rich metadata. `/runs` returns the required projection without per-row `get_run()` reads. Ranking HTTP calls reuse a process-owned client with explicit shutdown and bounded connection limits. All claimed performance improvements have before/after measurements with correctness checks.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-chief-of-staff`, `skill-verification-before-completion`
- Isolation: `isolated worktree per write lane`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect current source and reviewed commit, edit declared files with `apply_patch`, add focused tests, run declared local checks, and update this plan’s task ledger
- User-approval actions: commits, branch changes, merge, push, publication, destructive cleanup, reset, discard, or changes outside declared ownership
- Parallel ownership: none; ranking request and shared runtime paths force serialization
- Sequential fallback: execute Tasks 1–7 in listed order; stop and reconcile the plan if current `main` removed or renamed a declared owner
- Final review binding: review the exact base SHA and preserved worktree diff recorded under `Coordination State`; use `git diff --name-status` and `git diff --cached --name-status` before acceptance.

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `75e34d10f2276996ae6471a2a926f51b30351e81`
- Expected workspace: `main at base commit plus exact preserved dirty paths: M config/taxonomy/skill_synonyms.yaml; D data/dataset_indeed-jobs-scraper_2026-06-25_22-25-16-456.json; D data/dataset_indeed-jobs-scraper_2026-06-25_23-11-47-317.json; D data/product150-dataset_linkedin-jobs-scraper_2026-05-23_08-05-06-456.json; D data/product50-dataset_linkedin-jobs-scraper_2026-05-23_08-28-36-344.json; M docs/superpowers/plans/2026-08-30-fitcv-frontend-closure-verification-plan.md; M docs/superpowers/plans/2026-09-02-fitcv-residual-journey-verification-plan.md; M docs/superpowers/plans/2026-09-12-18-20-fitcv-cv-warning-outcomes-plan.md; ?? .tmp/; ?? data/ReverseTemplate.pdf; ?? data/sample_jobs-3.json; ?? docs/superpowers/plans/2026-09-12-19-00-fitcv-ranking-evaluation-runtime-overhead-plan.md; ?? fitcv-flow-preview.png; ?? frontend/test-results/; ?? node_modules/`
- Next action: `none; plan execution and fresh completion verification finished`
- Blockers: `none`
- Active lane: `none; completion verification finished`
- Lane branch: `codex/fitcv-ranking-task-1`
- Lane worktree: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1`
- Fresh completion verification: `1112 passed, 1 skipped`; ranking benchmark completed; `/runs` benchmark completed; transport validator `PASS`; `git diff --check` clean.
- Confirmed issue patched: stale transport failure could close newer same-identity client; `LlmTransportPool.discard()` now compares client identity and regression proof passes.
- Benchmark correction: transport harness now exercises one `responses` 404 fallback and derives retry count from `attempt_count`; current post-change and metadata self-check artifacts match current script hash.
- Benchmark parity: historical pre-change artifact remains preserved; current-baseline-mode and current-post-change artifacts use identical fallback workload, current script hash, retry count `1`, and correctness checksum.
- Preserved scope: root template/lifecycle validators still report pre-existing unrelated legacy plans/specs; current plan passes both validators in isolated scope. Legacy plans/specs remain unchanged.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | none | focused ranking/runtime tests plus request-equivalence probe | `DONE`; 173 passed, 1 skipped; independent review `PASS` |
| Task 2 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Task 1 | evidence-selection and ranking-input tests | `DONE`; 348 passed, 1 skipped; provider-failure, route-freeze, two-job selection probes passed; independent review `PASS` |
| Task 3 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Task 1 | legacy checkpoint rejection and current-checkpoint acceptance tests | `DONE`; 206 passed in impacted suite; independent review `PASS`; mixed row/policy mismatch fixed |
| Task 4 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Tasks 1–3 | benchmark tests plus replay output with honest denominators | `DONE`; 59 passed, 1 skipped; pre/post replay artifacts and metadata captured; p50 -0.34%, p95 -0.84%; independent review `PASS` |
| Task 5 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Task 4 | slow-delivery shutdown, lease, duplicate, and metadata tests | `DONE`; 772 passed; no-background/background 20-record slow probes bounded at 0.2s; independent review `PASS` |
| Task 6 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Task 5 | full `/runs` endpoint test and endpoint benchmark | `DONE`; 663 passed; query path read-only after initialization; page-20 checksum unchanged; 100/500 base rejection classified unsupported and post support classified as new workload; SQL 1463→3; p50 230.3956→5.2713 ms; p95 234.5111→5.7154 ms; independent review `PASS` |
| Task 7 | `completed` | `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-ranking-task-1` | `codex` | Task 1 | transport reuse, latency, retry, and worker-occupancy proof | `DONE`; 583 passed, 1 skipped focused suite; 1112 passed, 1 skipped acceptance suite; final independent validator `PASS`; stale-discard race reproduced then fixed; fresh reuse benchmark 1 connection/retry 1 and baseline 30 connections/retry 1 with matching checksum |

## Task Breakdown

### Task 1: Canonical ranking request, route, fingerprint, and observation

**Purpose:**
- Make ranking cache identity describe the exact request executed by the provider.
- Align control-plane and runtime routing, including frozen local snapshots.
- Remove the observation callback’s compact-input drift.

**Task Function:**
- Resolve and freeze ranking route and execution settings once at stage entry. Pass that resolved contract into one canonical per-job request builder using existing `LlmTaskRequest` and `LlmRouting` values; fingerprinting and execution consume the same built request without adding a second configuration layer.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded shared-runtime change with moderate contract and cache risk; resolve lowest reliable profile before activation.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent validation of request equality, route provenance, and callback behavior.

**Specification Coverage:**
- Covers verified prompt drift between `build_ai_score_input_fingerprint()` and `_execute_ranking_runtime()`.
- Covers verified provider drift between `build_ai_score_contract_fingerprint()` and `resolve_llm_routing()` with runtime snapshots.
- Covers verified observation drift in `run_ai_scoring()`.
- Applies the same request/fingerprint rule to enrichment through `build_extraction_prompt`, `build_enrich_contract_fingerprint`, `_execute_enrich_runtime`, and `_enrich_one`; do not create a new cross-stage framework.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/ai_score.py:build_ai_score_contract_fingerprint`, `build_ai_score_input_fingerprint`, `build_ranking_job_input`, `_execute_ranking_runtime`, `score_job`, `run_ai_scoring`
- Inspect: `src/fitcv/runtime_routing.py:resolve_llm_routing`, `build_runtime_routing_snapshot`
- Inspect: `src/fitcv/llm_runtime.py:LlmTaskRequest`, `LlmRouting`, `execute_llm_task`
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`
- Inspect: `src/fitcv/enrich.py:build_extraction_prompt`, `build_enrich_contract_fingerprint`, `get_enrich_prompt_provenance`, `_execute_enrich_runtime`, `enrich_job`, `_enrich_one`
- Modify: `src/fitcv/ai_score.py` canonical builder and all ranking callers
- Modify: `src/fitcv/runtime_routing.py` route resolution and `src/fitcv/enrich.py` enrichment request/fingerprint/observation callers
- Verify: `tests/test_ai_score.py`, `tests/test_enrich.py`, `tests/test_llm_runtime.py`, `tests/test_runtime_routing.py`, `tests/test_ranking_contract.py`

**Dependencies:**
- Current-main symbol mapping must confirm the reviewed owners still exist or record their current replacements before code changes.
- Reuse existing `LlmTaskRequest`, `LlmRouting`, routing snapshots, prompt renderers, and provenance helpers.

**Authority:**
- Preauthorized local actions: inspect and edit only declared ranking/runtime files and focused tests; run focused pytest and one local request-equivalence probe
- Stop for: missing current-main owner, changed public request contract, new provider/auth behavior, or any required edit outside declared files

**Steps:**
- [x] Step 1: Compare current-main definitions and callers for `src/fitcv/ai_score.py`, `src/fitcv/runtime_routing.py`, `src/fitcv/llm_runtime.py`, and `src/fitcv/enrich.py` with commit `86f719d`; record any renamed owner in this plan before editing.
- [x] Step 2: At `execute_ranking_stage` entry, resolve and freeze ranking route plus execution settings from the stage runtime snapshot. Pass that immutable contract into each per-job request builder; do not resolve routing inside the candidate loop.
- [x] Step 3: Add one canonical ranking-request builder that renders rich job requirements and candidate evidence, carries response schema/temperature/timeout settings, and returns existing runtime request values plus canonical identity data.
- [x] Step 4: Make fingerprinting, fresh execution, reuse metadata, and observation callback consume that builder result; remove fallback reconstruction from compact `build_job_summary_text(job)` and retrieval `top_evidence` when rich ranking input exists.
- [x] Step 5: Include provider, base URL, wire API, model, configuration revision, prompt identity/customization, response contract, and generation settings in identity only when those values affect execution; preserve stable job identity fields.
- [x] Step 6: Apply identical request/fingerprint/route handling to enrichment, then add regression coverage for ranking and enrichment observations enabled/disabled, empty evidence, frozen local routing snapshots, changed providers, and identical request/fingerprint payloads. Exercise one success path and one provider failure path per stage.
- [x] Step 7: Mutate configuration between candidate requests and assert current stage keeps its initial route/settings; invoke a subsequent stage with changed configuration and assert it uses the new route/settings.

**Verification:**
- [x] `uv run pytest -q tests/test_ai_score.py tests/test_enrich.py tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_ranking_contract.py`
- Expected: all focused tests pass; assertions prove fingerprint prompt/route equals executed request and callback metadata preserves rich input.
- [x] Run a stubbed-provider probe with observations enabled and disabled.
- Expected: both modes send the same prompt, route, model, response contract, and generation settings; only observation delivery differs.
- [x] Run stage route-freeze regression with configuration mutation between candidates and a second stage invocation.
- Expected: all requests in first stage use initial route/settings; second stage uses changed route/settings.

**Exit Criteria:**
- One builder owns ranking request construction; no caller reconstructs prompt or provider identity independently.
- Focused tests prove cache identity cannot remain equal when executed provider or prompt changes.

### Task 2: Job-specific evidence selection and one-time profile projection

**Purpose:**
- Stop every job receiving the same first two profile evidence records.
- Project candidate evidence once per profile revision, then select bounded relevant evidence per job.

**Task Function:**
- Reuse existing deterministic evidence scoring and retrieval primitives to select job-specific evidence without invoking another model or the full CV-analysis workflow.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded data-selection change with deterministic tie-breaking and cache-contract impact.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent proof of per-job relevance, source-ID stability, and profile projection reuse.

**Specification Coverage:**
- Covers `project_candidate_evidence(profile)[:2]` order-dependent evidence bug.
- Covers repeated profile projection inside the production candidate loop.
- Preserves evidence source IDs, stable ordering, bounded output, and empty-evidence behavior.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`, `score_evidence_item`, `_EvidenceSelectionEngine`, `retrieve_evidence_bundle`
- Inspect: `src/fitcv/pipeline.py` ranking candidate loop around `ranking_inputs_by_url`
- Inspect: `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`
- Modify: `src/fitcv/evidence.py` only if a small existing selector needs a ranking-facing wrapper
- Modify: `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_runner.py` ranking input assembly
- Verify: `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_pipeline.py`

**Dependencies:**
- Task 1 canonical ranking input shape and evidence contract.
- Existing evidence scoring/retrieval behavior remains authoritative.

**Authority:**
- Preauthorized local actions: edit evidence/ranking-input owners and focused tests; run deterministic evidence and pipeline tests
- Stop for: evidence schema migration, nondeterministic ordering, model-dependent selection, or edits outside evidence/pipeline/ranking tests

**Steps:**
- [x] Step 1: Build one profile-level evidence pool per profile revision at ranking-stage setup.
- [x] Step 2: For each shortlisted job, use existing job-requirement matching and `score_evidence_item`/retrieval primitives to choose at most two records with deterministic score and evidence-ID tie-breaks.
- [x] Step 3: Preserve selected source IDs and rich text in `ranking_input`; do not store the same profile prefix as every job’s evidence.
- [x] Step 4: Remove duplicate projection work from both direct pipeline and stage-runner paths, keeping one owner for production ranking input assembly.
- [x] Step 5: Test two jobs with different requirements receiving different evidence, repeated runs producing identical selection, empty profile evidence producing valid empty input, and one profile projection call per revision.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_ai_score.py tests/test_pipeline.py`
- Expected: existing evidence contracts pass; new assertions show job-specific records and stable source IDs.
- [x] Run a two-job deterministic selection probe.
- Expected: differing job requirements yield differing selected evidence when matching records exist; no job receives unrelated first-record evidence.

**Exit Criteria:**
- Profile evidence projects once; selection is job-specific, bounded, deterministic, and source-preserving.
- Ranking request builder receives selected evidence through one canonical path.

### Task 3: Fail-closed legacy checkpoint retrieval validation

**Purpose:**
- Prevent legacy vector checkpoints without `retrieval_strategy` from bypassing retrieval-contract validation.

**Task Function:**
- Extend current checkpoint payload validation so missing retrieval strategy is treated as unknown/incompatible for vector-derived state, while current valid checkpoints continue to resume.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: narrow compatibility guard with migration and resume risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent legacy/current checkpoint matrix validation.

**Specification Coverage:**
- Covers the verified guard bypass where absent `retrieval_strategy` skips validation.
- Preserves valid current checkpoint resume and explicit incompatibility errors.
- Preserves PR #42 CV-warning outcome persistence without restoring the retired review gate.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/pipeline_contracts.py:PipelineState.from_checkpoint_payload` and checkpoint compatibility helpers
- Inspect: `src/fitcv/pipeline.py:_checkpoint_payload_from_state`, retrieval-strategy validation, resume entry points
- Inspect: `src/fitcv/pipeline_stage_context.py` retrieval contract fields
- Modify: current canonical checkpoint validator and payload producer only
- Verify: `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`

**Dependencies:**
- Task 1 only for shared plan ordering; no code dependency on ranking behavior.
- Existing checkpoint schema and current retrieval strategy names remain canonical.

**Authority:**
- Preauthorized local actions: edit checkpoint contract owners and focused resume tests; run checkpoint and resume parity tests
- Stop for: destructive checkpoint migration, automatic data rewrite, or inability to distinguish vector-derived state from non-vector state

**Steps:**
- [x] Step 1: Enumerate current checkpoint payload variants and identify which fields prove vector-derived state.
- [x] Step 2: Reject legacy vector checkpoints when `retrieval_strategy` is absent, with the existing compatibility error contract and actionable reason.
- [x] Step 3: Keep non-vector/empty-state compatibility behavior unchanged where retrieval strategy is not applicable.
- [x] Step 4: Add tests for missing, mismatched, and matching strategies plus wrapped checkpoint payloads and valid current resume.

**Verification:**
- [x] `uv run pytest -q tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py`
- Expected: missing vector strategy fails closed; matching current strategy resumes; unrelated checkpoint fields remain preserved.
- [x] `uv run pytest -q tests/test_cv_generation_reason_mapping.py tests/test_pipeline_outcome_fact.py`
- Expected: merged CV-warning outcomes remain explicit, persisted, and distinct from `review_required` behavior.

**Exit Criteria:**
- No legacy vector checkpoint can bypass strategy validation.
- No destructive migration runs automatically.

### Task 4: Repair benchmark inputs, metrics, and evaluation modes

**Purpose:**
- Replace perfect but invalid ranking claims with independent inputs, complete-pool denominators, held-out evaluation, and truthful execution modes.

**Task Function:**
- Refactor the benchmark and its tests while retaining the existing fixture as a smoke test, not optimization evidence.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: evaluation-contract change with statistical and operational interpretation risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent audit of labels, denominators, cutoffs, mode semantics, and cache measurement.

**Specification Coverage:**
- Removes relevance-label leakage from synthesized job text.
- Calculates retrieval recall and ranking metrics against the full eligible candidate pool.
- Defines NDCG@K against the ideal ordering from the full eligible pool; missing returned positions contribute zero gain.
- Removes fake `--mode model` semantics; deterministic replay remains the only supported benchmark mode, and live provider evaluation stays deferred.
- Separates production-cache reuse measurement from in-memory benchmark bookkeeping.
- Separates calibration and held-out records in reporting.

**Required Skills:**
- `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `scripts/benchmark_ranking.py:_recall`, `_ndcg`, `_run_once`, `main`
- Inspect: `scripts/benchmark_runs_endpoint.py` and `scripts/benchmark_llm_transport.py` benchmark contracts when added
- Inspect: `tests/fixtures/ranking_gold.json` and `tests/test_ranking_evaluation.py`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`, `src/fitcv/ranking.py:rank_jobs`
- Modify: `scripts/benchmark_ranking.py`, fixture schema/data only where needed, and `tests/test_ranking_evaluation.py`
- Verify: benchmark JSON output and fixture smoke tests

**Dependencies:**
- Tasks 1–3 complete so benchmark inputs and reuse identity reflect current contracts.
- No provider credentials or external service access; live evaluation remains an explicit separate mode.

**Authority:**
- Preauthorized local actions: edit benchmark/fixture/test files, run deterministic replay and smoke checks, write local benchmark output under `.tmp/`
- Stop for: live provider authentication, external data publication, changing production cutoffs, or using invalid fixture scores as release evidence

**Steps:**
- [x] Step 1: Before modifying benchmark code, run current `scripts/benchmark_ranking.py` with `--warmup-iterations 1 --measured-iterations 5` and save `.tmp/benchmarks/ranking/pre-change.json` plus fixture hash, Python version, and dependency lock revision.
- [x] Step 2: Define fixture fields so job text, profile text, retrieval features, evaluator grade, and split are independent; keep `reviewed` and case labels as evaluator metadata.
- [x] Step 3: Compute shortlist recall over all eligible source rows, not only rows already returned by ranking; compute ranking recall/NDCG from the complete eligible pool with explicit `top_n`.
- [x] Step 4: Define NDCG@K from the full eligible pool, count absent returned positions as zero gain, and report `returned_count`, `eligible_count`, `scoring_failure_count`, and `coverage` separately. Never shrink denominators to successful or returned rows.
- [x] Step 5: Remove `--mode model`; deterministic replay consumes recorded scores, and unsupported live evaluation fails with an explicit CLI error rather than substituting baseline scores.
- [x] Step 6: Measure cache hits/misses through the same production reuse index or a clearly labeled replay adapter; report calibration and held-out metrics separately and emit sample counts/denominators.
- [x] Step 7: Add a label-permutation test proving evaluator-grade changes do not alter retrieval inputs or model requests. Keep the current fixture as a smoke test and prevent it from claiming live optimization validity.

**Verification:**
- [x] `uv run pytest -q tests/test_ranking_evaluation.py tests/test_ranking.py tests/test_vector_search.py`
- Expected: fixture shape and deterministic replay pass; tests fail if labels leak into inputs, denominators shrink to ranked rows, absent NDCG positions are dropped, or mode semantics fake model calls.
- [x] `uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --mode replayed --warmup-iterations 1 --measured-iterations 5 --output .tmp/benchmarks/ranking/post-change.json`
- Expected: output includes split-aware counts, full-pool denominators, honest NDCG@K, replay mode, and cache provenance; no claim treats `1.0` as live ranking evidence.
- [x] Compare pre/post ranking benchmark with identical fixture hash and workload; accept no p50/p95 regression greater than 10%, and claim an optimization only when the metric improves by at least 10% across five measured iterations.

**Exit Criteria:**
- Benchmark output can support comparison only when inputs, split, denominator, cutoff, score source, and cache source are explicit.
- Synthetic smoke fixture remains available but cannot justify tighter cutoffs or cheaper models.

### Task 5: Bound telemetry shutdown, lease ownership, and rich metadata delivery

**Purpose:**
- Prevent worker/app completion from blocking on serial slow HTTP drains.
- Prevent 30-second leases from expiring while claimed batches are still being sent.
- Preserve rich stored event metadata during retries.

**Task Function:**
- Set one delivery-owner model per deployment mode, claim work immediately before delivery or renew leases, and enforce an absolute shutdown deadline owned by the caller. Delivery remains at-least-once with stable event identity and duplicate-safe acknowledgement; exactly-once delivery is not promised.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: concurrent durable-delivery behavior with data-loss and duplicate-delivery risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: slow-service and lease-expiry validation independent of implementation.

**Specification Coverage:**
- Covers synchronous `final_drain=True` after thread join.
- Covers batch claims using default `limit=20` and `lease_seconds=30` against sequential five-second timeouts.
- Covers retry rebuilding generic events instead of stored rich contracts.

**Required Skills:**
- `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/reporter.py:retry_pending_process_event_deliveries`, `ProcessEventDeliveryLoop.stop`, `_drain_once`, `deliver_process_event`
- Inspect: `src/fitcv_cp/sqlite_store.py:claim_process_event_deliveries`, `record_process_event_delivery`, stored rich-event serialization helpers
- Inspect: `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`, `src/fitcv_cp/worker_job.py:run_pipeline_job`, and shutdown callers in `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/reporter.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/worker_job.py`, and only required app shutdown callers
- Verify: `tests/test_fitcv_cp/test_reporter.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, and worker/app shutdown tests

**Dependencies:**
- Task 4 establishes measurement discipline; no ranking code dependency.
- Stored event schema and delivery statuses remain canonical; no destructive event deletion.

**Authority:**
- Preauthorized local actions: edit reporter/store delivery logic and focused backend tests; use stubbed slow HTTP services and temporary SQLite stores
- Stop for: event-schema migration, dropping pending records, external telemetry writes, or inability to identify one delivery owner per deployment mode

**Steps:**
- [x] Step 1: Define shutdown deadline input and delivery-owner behavior for worker and app modes; keep `emit()` non-blocking.
- [x] Step 2: Replace unbounded final drain behavior with deadline-aware draining. Define deadline as the maximum time the shutdown caller waits; stop new claims at deadline, bound joins and waits by remaining time, and do not pretend a bounded join cancels an in-flight synchronous request.
- [x] Step 3: Align claim lease with bounded delivery behavior by claiming smaller batches immediately before send, or renew each claim before expiry. Keep claim ownership checks on status updates.
- [x] Step 4: Make retry use stored rich contract/metadata fields from the persisted event record; do not reconstruct generic payloads when rich metadata exists.
- [x] Step 5: Add tests for worker release before slow delivery completes, expired leases, reclaim after expiry, stable event identity, duplicate-safe acknowledgement, at-least-once retry delivery, and rich metadata preservation.

**Verification:**
- [x] `uv run pytest -q tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_run_lifecycle.py`
- Expected: shutdown caller returns by its deadline; in-flight synchronous work may finish after caller return; unfinished records remain durable; expired claims become reclaimable; stable event IDs support duplicate-safe acknowledgement; stored rich metadata reaches sink.
- [x] Run a bounded slow-service probe with 20 records, five-second request timeout, and a shutdown deadline shorter than full serial drain.
- Expected: caller returns by deadline, records not sent remain durable with pending/lease state for recovery, and repeated delivery attempts remain at-least-once rather than exactly-once.

**Exit Criteria:**
- Shutdown latency has a hard upper bound owned by caller deadline.
- Lease duration and claim batch cannot silently permit concurrent reclaim during normal bounded delivery.
- Shutdown interruption causes no event deletion or false acknowledgement; delivery contract remains at-least-once.

### Task 6: Remove `/runs` per-row reads and benchmark endpoint boundary

**Purpose:**
- Make `/runs` consume one batched list projection without `store.get_run()` for every displayed row.
- Measure complete HTTP endpoint behavior, not only `query_runs()`.

**Task Function:**
- Extend canonical `query_runs()` projection with reconciliation/status fields needed by the list response, then render directly from that projection.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: endpoint/database boundary change with response-contract risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent endpoint response parity and query-count/performance validation.

**Specification Coverage:**
- Covers per-row `store.get_run()` calls in `get_runs_list()`.
- Covers `SELECT p.*` and compatibility JSON deserialization in list path.
- Covers benchmark omission of endpoint-level cost while retaining status reconciliation behavior.

**Required Skills:**
- `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:get_runs_list`, `_reconcile_orphaned_run`, `_run_to_dict`, `_collection_response`
- Inspect: `src/fitcv_cp/sqlite_store.py:query_runs`, `get_run`, `get_run_detail`, list projection SQL and row deserializers
- Inspect: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, frontend consumers in `frontend/src/features/runs/api.ts` and `frontend/src/features/runs/types.ts`
- Modify: `src/fitcv_cp/sqlite_store.py:query_runs`, `src/fitcv_cp/app.py:get_runs_list`, and focused backend tests
- Verify: endpoint response shape, query count, status reconciliation, pagination, search, and archived/all views

**Dependencies:**
- Existing frontend response contract remains unchanged.
- Reconciliation remains correct for orphaned, active, and archived runs.

**Authority:**
- Preauthorized local actions: edit Runs list projection/endpoint and backend tests; run local HTTP tests and repeatable endpoint benchmark
- Stop for: frontend contract change, schema migration, detail endpoint changes, or status behavior requiring a separate owner

**Steps:**
- [x] Step 1: Add `scripts/benchmark_runs_endpoint.py` as a local-only harness, then capture the current endpoint baseline before changing `query_runs()` or `get_runs_list()` with warmup `1`, measured iterations `5`, page sizes `20,100,500`, and output `.tmp/benchmarks/runs/pre-change.json`.
- [x] Step 2: Enumerate exact fields `get_runs_list()` and current consumers require; remove compatibility payload fields not used by list response while retaining fields required by `frontend/src/features/runs/types.ts`.
- [x] Step 3: Add batched SQL projection for display status, backend status, error summary, timestamps, counts, and reconciliation inputs; keep `get_run()` for detail paths only.
- [x] Step 4: Add one bounded reconciliation pass for eligible `QUEUED` and `RUNNING` rows. Use batched database inputs and queue lookups where supported, preserve existing `_reconcile_orphaned_queued_run`, `_reconcile_orphaned_running_run`, `update_run_status`, and `append_event` behavior, and use compare-and-set/row-revision protection so concurrent worker completion cannot be overwritten.
- [x] Step 5: Make `get_runs_list()` render the reconciled projection directly and preserve `_collection_response` metadata, pagination, search, view semantics, event emission, and coherent timestamps from one reconciliation time sample.
- [x] Step 6: Add endpoint tests that count store calls and assert zero per-row `get_run()` detail reads for normal list rows, plus queue-state transitions, reconciliation events, concurrent worker completion, and orphan parity.
- [x] Step 7: Benchmark complete endpoint request with representative page sizes and compare query count, latency, response bytes, and correctness checksum before/after without changing payload contract.

**Verification:**
- [x] `uv run pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Expected: response JSON remains contract-compatible; list path performs one batched projection plus bounded reconciliation lookups; queue-state behavior, event emission, timestamps, and pagination tests pass; concurrent completion is never overwritten.
- [x] `uv run python scripts/benchmark_runs_endpoint.py --runs 20,100,500 --warmup 1 --iterations 5 --output .tmp/benchmarks/runs/post-change.json`
- Expected: report full HTTP latency, DB query count, response bytes, and correctness checksum; endpoint benchmark includes serialization and reconciliation.
- [x] Compare pre/post endpoint benchmark with identical seed, database contents, page sizes, and five measured iterations; accept no p50/p95 regression greater than 10%, and claim an optimization only when p50 or p95 improves by at least 10% without checksum drift.

**Exit Criteria:**
- `/runs` no longer performs N+1 canonical reads for displayed rows.
- Required status/reconciliation fields come from one canonical list projection.
- Performance result uses identical workload and environment before/after.

### Task 7: Reuse ranking HTTP clients with bounded lifecycle

**Purpose:**
- Remove fresh `httpx.Client` construction from every ranking invocation without widening concurrency or changing auth/timeout semantics.

**Task Function:**
- Add the smallest ranking-scoped, process-owned transport lifetime around the existing OpenAI-compatible adapter, with bounded retained client identities and connection limits and explicit shutdown; keep route-specific timeout and headers request-specific.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: transport-lifecycle change with concurrency, retry, and shutdown risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent connection reuse and failure-path validation.

**Specification Coverage:**
- Covers fresh `httpx.Client` creation in `_openai_compatible_adapter()`.
- Measures connection creation, request latency, retries, and worker occupancy before increasing concurrency.
- Starts with ranking only; extending other stages requires separate measured scope.

**Required Skills:**
- `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Inspect: `src/fitcv/llm_runtime.py:_openai_compatible_adapter`, `execute_llm_task`, `LlmRouting`, timeout and retry handling
- Inspect: `src/fitcv/ai_score.py:run_ai_scoring` concurrency and runtime lifecycle
- Inspect: `src/fitcv_cp/main.py:build_app`, `start_process_event_delivery_loop`, `stop_process_event_delivery_loop`
- Inspect: `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `execute_cv_regenerate_once`
- Inspect: `tests/test_llm_runtime.py`, ranking runtime tests, and existing reset/shutdown fixtures
- Modify: `src/fitcv/llm_runtime.py` transport lifecycle, `src/fitcv/ai_score.py` ranking scope integration, `src/fitcv_cp/main.py` app lifecycle integration, and `src/fitcv_cp/worker_job.py` worker lifecycle integration
- Verify: focused runtime tests and a local keep-alive HTTP server that counts accepted TCP connections

**Dependencies:**
- Task 1 canonical route/request contract.
- Task 5 shutdown deadline rules if transport shutdown shares process lifecycle; do not couple unrelated telemetry state.

**Authority:**
- Preauthorized local actions: edit ranking transport lifecycle and focused tests; run local stub-server latency/retry/occupancy benchmark
- Stop for: new dependency, global client shared across unrelated credentials, changed auth semantics, unbounded connection pool, or external network calls

**Steps:**
- [x] Step 1: Confirm route/base URL/auth key boundaries; client reuse must not cross incompatible base URLs, credentials, or proxy settings.
- [x] Step 2: Create clients inside owning worker/app processes, keep them open while ranking requests use them, and close them at owner shutdown. Key reuse only by safe transport identity; bound retained client identities and `httpx.Limits`, apply route timeout per request/client policy, and add explicit close/reset hooks for tests and shutdown.
- [x] Step 3: Preserve responses/chat fallback behavior, status handling, retry counts, and provider failure mapping.
- [x] Step 4: Add tests proving repeated ranking calls reuse connections, changed routes do not share unsafe clients, failures close/recover cleanly, owner shutdown closes clients, and retained client identities stay within the declared bound.
- [x] Step 5: Add `scripts/benchmark_llm_transport.py`, capture the current baseline before changing adapter/lifecycle paths with warmup `1`, measured iterations `5`, and output `.tmp/benchmarks/transport/pre-change.json`.
- [x] Step 6: Benchmark cold/warm request latency, accepted TCP connections on a local keep-alive server, retries, and worker occupancy using identical stub-server workload; do not increase ranking concurrency in this task.

**Verification:**
- [x] `uv run pytest -q tests/test_llm_runtime.py tests/test_ai_score.py tests/test_runtime_routing.py`
- Expected: request payloads and failure semantics remain unchanged; accepted TCP connection count drops for repeated compatible ranking calls; reset hooks isolate tests; app and worker shutdown close owned clients.
- [x] `uv run python scripts/benchmark_llm_transport.py --warmup 1 --iterations 5 --output .tmp/benchmarks/transport/post-change.json`
- Expected: report accepted TCP connections, p50/p95 latency, retries, worker occupancy, retained client identities, and correctness checksum; no cross-route credential leakage.
- [x] Compare pre/post transport benchmark with identical route, request count, keep-alive server, and five measured iterations; accept no p50/p95 regression greater than 10%, and claim an optimization only when accepted TCP connections or p95 improves by at least 10% without checksum drift.

**Exit Criteria:**
- Compatible ranking requests reuse owned transports; incompatible routes remain isolated.
- Explicit shutdown/reset exists and passes tests.
- No concurrency increase or cross-stage client framework added without a separate measured plan.

## Deferred Scope

- Adaptive candidate reduction and lexical-margin skipping.
- Shorter ranking outputs or a second explanation call; evaluate only after Task 4 produces trustworthy results.
- Broad stage-runner ownership consolidation and vector-era naming cleanup.
- Response slimming and `review_required` lifecycle retirement. PR #42 CV-warning outcome persistence already landed; retain its explicit failures, evidence-aware warnings, manual checkpoints, and historical recovery while this plan avoids changing that contract.

## Verification

- `uv run pytest -q tests/test_ai_score.py tests/test_enrich.py tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_ranking_contract.py tests/test_evidence.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_stage_resume_parity.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_outcome_fact.py tests/test_pipeline.py tests/test_ranking_evaluation.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- `uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --mode replayed --warmup-iterations 1 --measured-iterations 5 --output .tmp/benchmarks/ranking/final.json`
- Run `scripts/benchmark_runs_endpoint.py` and `scripts/benchmark_llm_transport.py` with warmup `1`, measured iterations `5`, identical workload/environment, correctness checksum, latency, query/connection counts, retained-client counts, and response-size reporting.
- Accept no p50/p95 regression greater than 10%; claim optimization only with at least 10% improvement and unchanged correctness checksum.
- Run `python "$HOME/.agents/project-os/scripts/validate_template_required_sections.py" --repo-root .`.
- Run `python "$HOME/.agents/project-os/scripts/validate_planning_lifecycle.py" --repo-root .`.
- Run `git diff --check`.

## Completion Criteria

The plan is ready for completion verification when:

1. Tasks 1–7 have accepted task-local proof and no unresolved required blocker.
2. Ranking execution, fingerprint, reuse, route, observation, and evidence paths share one canonical contract.
3. Legacy vector checkpoint validation fails closed without destructive migration.
4. Benchmark output proves independent inputs, complete-pool denominators, held-out separation, truthful mode, and cache provenance.
5. Telemetry shutdown, lease, and rich-metadata behavior pass slow-service and retry tests with stable event identity, duplicate-safe acknowledgement, and at-least-once delivery; exactly-once delivery is not claimed.
6. `/runs` response contract and reconciliation behavior pass with no per-row list reads.
7. Ranking transport reuse passes isolation, failure, shutdown, and measured performance checks.
8. Deferred scope remains unchanged unless separately approved and planned.
9. Plan deviations, substitutions, blockers, and preserved dirty files are recorded in coordination state.
10. `skill-verification-before-completion` returns `verified` before plan status changes from `proposed` to `completed`.
