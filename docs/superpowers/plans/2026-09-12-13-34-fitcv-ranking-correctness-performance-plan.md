---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-ranking-correctness-performance
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - frontend/src/features/runs/runs-list.tsx
  - tests/
  - scripts/
---

# FitCV Ranking Correctness And Confirmed Overhead

## Goal

Make FitCV ranking truthful before optimizing it: operational scoring failures
must not become poor-fit scores, retrieval must rank by meaningful job/profile
signals, reuse must invalidate on changed inputs, and confirmed control-plane
overhead must leave pipeline execution without changing user-visible outcomes.

## Implementation Outcomes

### Truthful ranking state

The active ranking path distinguishes `valid`, `unscored`, and `invalid` AI
score results. A valid model-produced `0.0` remains a valid zero; parser,
provider, timeout, and validation failures carry `ai_score: null` plus a stable
failure code. Failed rows remain visible for retry or review and never qualify
as semantic fit evidence.

### Meaningful retrieval and safe reuse

The default shortlist uses deterministic canonical role, skill, domain, and
location signals rather than SHA-256 byte projections. Retrieval and embedding
contracts carry explicit strategy/version fingerprints. Unchanged job inputs do
not append duplicate embedding rows, while changed prompt, model, schema, or
stage inputs invalidate only affected reuse records.

### Evidence-backed ranking

AI ranking receives bounded explicit job requirements, responsibilities,
eligibility facts, candidate summary, and source-linked candidate evidence.
Ranking policy weights and fit gates remain unchanged until evaluation data
proves a safe adjustment.

### Measured execution overhead

Remote telemetry delivery no longer blocks `PipelineReporter.emit()`. Runs list
queries use SQL-side view/search/count/pagination and return list projections
without per-row detail expansion. Active-run polling prevents overlap and pauses
when the page is hidden.

## Explicit Non-Goals

- No async rewrite of the pipeline.
- No new embedding provider before deterministic retrieval has a measured recall gap.
- No adaptive `ai_score_top_n`, soft fit-gate policy, or two-pass explanation flow before benchmark evidence and an approved contract for deferred rows.
- No SQLite writer architecture change unless focused measurements prove contention after the list and telemetry changes.
- No ATS concurrency change in this plan; retain existing deadline and deduplication behavior until a representative scan benchmark proves need.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-executing-plans`, `skill-chief-of-staff`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve existing unrelated working-tree changes
- Commit policy: `no commits during execution`
- Preauthorized local actions: edits in task-listed paths, declared local tests and benchmark commands, read-only source inspection, and bounded DeepAgents execution for review or implementation tasks
- User-approval actions: push, merge, publication, external writes, destructive recovery, discard, cleanup of pre-existing files, and new dependency or provider installation
- Parallel ownership: none; `src/fitcv/pipeline.py` and ranking contracts span multiple outcomes and stay serialized
- Sequential fallback: one lead Codex executor runs Tasks 1–7 in order, with independent review after Task 7

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `11e11e6612391b5a0595bdee749da7fc38d0a833`
- Expected workspace: `main` with pre-existing modifications preserved; plan creation adds only this file before execution
- Next action: none — execution complete; accepted deviations recorded below
- Blockers: none
- Accepted governance exception: repository-wide contract validator still reports pre-existing legacy plan/spec errors; legacy artifacts remain untouched by instruction.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | Baseline tests and benchmark fixture execute | Accepted after independent proof: Codex lane `0ed36d64e8ad433aba27c5692792ddfb` delivered; 41 focused tests passed; fixture 4 profiles × 60 candidates with 48 calibration + 12 held-out each; ranking and Runs baseline artifacts passed exact CLI checks |
| Task 2 | `completed` | current | `codex` | Task 1 | Score failure cases remain unscored end to end | Accepted after Herdr lane `fitcv-task-2-score-validity` (`97ba7c969eed4ae98bcf04fb7edad312`) and independent proof: `787 passed, 1 skipped`; compileall and `git diff --check` passed; restored pre-existing deleted `data/candidate_profile.v2.sample.yaml`; no storage migration required |
| Task 3 | `completed` | current | `codex` | Task 1 | Retrieval probe and embedding reuse tests pass | Accepted after Herdr lane `fitcv-task-3-lexical-retrieval` (`608bef03e58c42c7964a234bf67039fa`) and independent proof: `309 passed, 2 skipped`; lexical benchmark Recall@50, AI top-N recall, and NDCG@15 all `1.0`; compileall and `git diff --check` passed; retained metadata helper in `src/fitcv/pipeline_stages/common.py` required for shortlist projection |
| Task 4 | `completed` | current | `codex` | Tasks 2–3 | Prompt invalidation and ranking-input tests pass | Accepted after Herdr lane `fitcv-task-4-enrichment-evidence` (`a6c6402f4f5e48ed85df25abce0b2e80`) and independent proof: `264 passed, 1 skipped`; compileall and `git diff --check` passed; prompt replacement, bounded evidence, source IDs, and provider/model reuse fingerprints verified |
| Task 5 | `completed` | current | `codex` | Tasks 2–4 | Backend boundary and side-effect proof passes | Accepted after independent proof: control-plane focused suite `761 passed`; worker/main regression suite `108 passed`; `compileall` and `git diff --check` passed; startup delivery-loop leak fixed before acceptance. Benchmark artifact generated at `.tmp/runs-list-after.json`; exact SQLite rows-read metric remains unavailable through stdlib tracing. |
| Task 6 | `completed` | current | `codex` | Task 5 | Browser-visible polling behavior and frontend checks pass | Accepted after Herdr UI lane evidence: focused frontend tests `36 passed`; a11y `3 passed`; build passed; backend Runs contract `239 passed`; Chrome proof passed visible polling, hidden pause, visibility resume, in-flight deduplication, terminal stop, stale-response suppression, and unmount cleanup. Full frontend suite retains one pre-existing `src/test/scans.test.ts:441` failure reproduced on clean base; typecheck retains unrelated pre-existing errors in `src/test/notice-layout.test.ts`. |
| Task 7 | `completed` | current | `codex` | Tasks 1–6 | Fresh full verification and independent review pass | Accepted after independent Herdr review returned a resolved finding list: telemetry drain, production Runs benchmark, lexical benchmark, clean-base frontend reproduction, ledger reconciliation, `git diff --check`, and focused/full evidence reviewed; adaptive scoring and other deferred work remain out of scope. |

## Task Breakdown

### Task 1: Lock baseline and ranking evaluation

**Purpose:** Establish reproducible correctness and performance baselines before changing ranking or runtime behavior.

**Task Function:** Evaluation harness and regression-test design.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded fixture and benchmark work.

**Specification Coverage:** Gold-set metrics, unchanged-output baseline, and acceptance thresholds for retrieval, ranking, cache reuse, and stage latency.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`.

**Files And Symbols:**
- Add `tests/fixtures/ranking_gold.json` with four profile-specific pools of 60 candidates each, reviewed graded relevance `0..3`, 48 calibration candidates and 12 held-out candidates per profile, covering direct matches, paraphrases, missing requirements, language/location conflicts, and clear mismatches.
- Add `tests/test_ranking_evaluation.py` with deterministic replay checks for Recall@50, Recall@`ai_score_top_n`, NDCG@15, false-rejection, valid-zero, and unscored-row behavior; keep live model-quality evaluation outside CI.
- Add `scripts/benchmark_ranking.py` with CLI arguments `--fixture`, `--mode {replayed,model}`, `--warmup-iterations`, `--measured-iterations`, and `--output`; report p50/p95 stage latency, LLM calls, retries, cache hits/misses, shortlist recall, and final-N ranking metrics without logging prompts or credentials.
- Add `scripts/benchmark_runs_list.py` with the same warm-up/measured iteration controls plus `--sizes` and `--output`; report SQL statements, rows read, endpoint p50/p95, and response item equality for synthetic Runs databases.
- Inspect `tests/test_ranking.py`, `tests/test_ai_score.py`, `tests/test_vector_search.py`, and `src/fitcv/pipeline_observability.py` for reusable helpers before adding any new helper.

**Dependencies:** None.

**Authority:**
- Preauthorized local actions: add listed fixture, evaluation test, and benchmark script; run declared local baseline commands; preserve all pre-existing changes.
- Stop for: missing canonical test fixture, inability to run the existing Python environment, or any request to change ranking policy before baseline capture.

**Steps:**
- [x] Record `HEAD`, branch, status, Python version, dependency lock state, and benchmark environment in command output.
- [x] Define fixture labels as `relevant`, `borderline`, or `irrelevant` with expected shortlist and final-rank order; keep examples free of personal data.
- [x] Capture current `50 → 50 → 15` behavior, score failure behavior, enrichment reuse behavior, and Runs list query counts; record known baseline failures as expected failures instead of requiring new regression assertions to pass before fixes.
- [x] Separate deterministic replayed-score CI checks from opt-in model-quality runs; never use mocked scores as proof that prompt changes improve ranking quality.
- [x] Run five warm-up iterations, then 30 measured deterministic iterations for p95; define numeric noise tolerance as the larger of 10% relative or 20 ms absolute.
- [x] Set acceptance owners to the plan owner: zero false-fit labels from operational failures, no gold-set Recall@50 or NDCG@15 regression, and no unchanged-path p95 regression beyond the stated noise tolerance.

**Verification:**
- `python -m pytest tests/test_ai_score.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_vector_search.py tests/test_embeddings.py tests/test_enrich.py`
- `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --mode replayed --warmup-iterations 5 --measured-iterations 30 --output .tmp/ranking-baseline.json`
- `python scripts/benchmark_runs_list.py --sizes 100,1000,10000 --warmup-iterations 5 --measured-iterations 30 --output .tmp/runs-list-baseline.json`

**Exit Criteria:** Baseline artifact exists, metrics are recorded, fixture labels are reviewable, and later tasks can compare identical workload and environment.

### Task 2: Make score validity explicit end to end

**Purpose:** Prevent parser, provider, timeout, and validation failures from becoming semantic fit scores.

**Task Function:** Backend contract correction with regression proof.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: cross-surface correctness contract and failure semantics.

**Specification Coverage:** `valid | unscored | invalid` score state, valid zero preservation, failure reason propagation, ranking omission behavior, cache protection, and export/API truthfulness.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv/ai_score.py`: `parse_score_response`, `_execute_ranking_runtime`, `_ranking_result_to_row`, `run_ai_scoring`, compatibility `store_ai_scores`.
- `src/fitcv/ranking_contract.py`: `build_baseline_result` and fit-label derivation.
- `src/fitcv/ranking.py`: `rank_jobs` and missing-score ordering requirements.
- `src/fitcv/agentic_cv_analysis.py`: `resolve_ranked_job_fit` and analysis status mapping for unknown fit.
- `src/fitcv/pipeline_contracts.py`: canonical job outcome status and reason mappings.
- `src/fitcv/pipeline.py`: `_normalize_late_stage_reuse_snapshots`, `build_ranking_features`, ranking-stage assembly around `run_ai_scoring`.
- `src/fitcv/pipeline_stage_artifacts.py`: ranking artifact projections and persisted score fields.
- `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/app.py`: result/export/API projections that expose score or failure state.
- `frontend/src/lib/format.ts` and `frontend/src/features/runs/types.ts`: user-visible status labels/types when score status reaches existing run/result views.
- `tests/test_ai_score.py`, `tests/test_ranking_contract.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, and `tests/test_fitcv_cp/test_app.py`.

**Dependencies:** Task 1 baseline.

**Authority:**
- Preauthorized local actions: change canonical score/result contracts and listed consumers/tests; use existing JSON/SQLite compatibility paths; run focused backend tests.
- Stop for: a required storage migration that cannot preserve existing artifacts, an unknown consumer expecting numeric failure scores, or any change that treats retrieval position as fit qualification.

**Steps:**
- [x] Require explicit finite numeric `ai_score` for `valid`; preserve a model-produced `0.0`.
- [x] Return `ai_score: null`, `score_status: unscored` or `invalid`, and stable `failure_code` for malformed JSON, non-object payloads, missing/invalid score, provider failure, timeout, and validation failure.
- [x] Change runtime validation to reject parser defaults and missing required model fields instead of checking only parser-generated keys.
- [x] Make `build_baseline_result` represent unknown holistic fit without converting it into a valid poor-fit label; keep unscored rows in run diagnostics and retry/review output.
- [x] Define one downstream mapping: valid score, including zero, keeps existing ranking and fit gates; provider/timeout failure has absent fit score, visible failure, and recorded retry eligibility; invalid model output has absent fit score, visible validation failure, and no fit classification.
- [x] Make `rank_jobs` exclude unscored/invalid rows from scored ordering without deleting them; make `resolve_ranked_job_fit` return explicit unknown/skip state with reason `ranking_unavailable` rather than a poor-fit label.
- [x] Define mixed results as a completed partial ranking with `unscored_count` and `invalid_count`; define all-unusable scoring as ranking-stage `failed` with `reason_code=ranking_unavailable` and no fit classifications.
- [x] Map historical rows lacking `score_status`: finite numeric scores become `valid`, known parser/runtime failures become their explicit failure state, and ambiguous legacy rows become `unscored` and non-reusable.
- [x] Prevent unscored or invalid rows from ranking, fit-gating, or cache reuse; do not make `store_ai_scores` the canonical active-path fix, but keep its compatibility behavior explicit.
- [x] Update result projections and exports to expose `score_status` and `failure_code` without inventing a score.

**Verification:**
- Direct parser checks for valid `0.0`, `{}`, missing `ai_score`, explicit `null`, malformed JSON, non-object JSON, NaN, and provider errors.
- Pipeline test with valid, unscored, and invalid rows proves valid zero remains rankable while failures remain visible and never receive `baseline_fit_label` from a fabricated score.
- Ranking and CV-analysis tests prove unknown fit never becomes `skip` solely through a missing-score fallback that looks like poor fit, and all-failed/mixed-result counters and statuses are stable.
- Cache test proves invalid/unscored rows cannot satisfy ranking reuse.
- `python -m pytest tests/test_ai_score.py tests/test_ranking_contract.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`

**Exit Criteria:** All failure paths carry explicit non-fit status, valid zero remains valid, active ranking and CV analysis no longer fabricate or silently lose failure state, all-failed/mixed-result behavior is explicit, and focused backend tests pass.

### Task 3: Replace hash retrieval and suppress duplicate embeddings

**Purpose:** Make shortlist ordering meaningful without adding a provider dependency, then make reuse content-addressed.

**Task Function:** Deterministic retrieval and cache/storage correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded retrieval and cache changes.

**Specification Coverage:** Retrieval correctness, stable tie-breaking, strategy versioning, cache invalidation, and unchanged-run write suppression.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv/embeddings.py`: `_deterministic_local_embedding`, `generate_embedding`, `build_embedding_contract_fingerprint`, `embed_and_store_jobs`.
- `src/fitcv/preference_policy.py`: saved-policy resolution and runtime compatibility checks.
- `src/fitcv/decision_feedback.py`: `DecisionEpisode`, `DecisionAlternative`, and `build_decision_feedback_source` embedding/shortlist contracts.
- `src/fitcv/vector_search.py`: `build_candidate_query_components`, `build_candidate_query_signature_record`, `build_candidate_query_embedding_contract_fingerprint`, `build_candidate_query_text`, shortlist ordering, and `store_shortlist`.
- `src/fitcv/pipeline.py`: shortlist stage consumers, checkpoint/resume validation, and retrieval diagnostics.
- `src/fitcv/ranking.py`: any personalized-ranking path that consumes embedding coordinates.
- `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_pipeline.py`, `tests/test_preference_policy.py`, `tests/test_decision_feedback.py`, `tests/test_pipeline_checkpoint_contract.py`, and `tests/test_pipeline_stage_resume_parity.py`.

**Dependencies:** Task 1 baseline; Task 2 score contract must remain independent of retrieval strategy.

**Authority:**
- Preauthorized local actions: replace default local retrieval internals with existing canonical skill/role/domain/location helpers; update fingerprints and listed tests; preserve output ordering determinism.
- Stop for: a real embedding provider or new dependency becoming necessary, a cache migration that would delete old rows, or a shortlist recall regression beyond Task 1 tolerance.

**Steps:**
- [x] Add one deterministic lexical retrieval strategy using canonical skill overlap, role-family/title relevance, domain hints, and location-type compatibility already available in `vector_search.py` and ranking helpers.
- [x] Use explicit `retrieval_strategy = lexical_v1`, `retrieval_score`, and stable job URL tie-breaking; never place lexical values in fields documented as cosine/vector similarity. Update diagnostics and consumers to use `retrieval_score`.
- [x] Keep old embedding rows unreadable by the new strategy through contract fingerprint versioning; do not delete historical rows.
- [x] Skip job/query vector generation and storage on the lexical shortlist path; retain embeddings only for consumers that still declare a compatible embedding contract.
- [x] Add a schema migration that keeps the newest row for each existing embedding key, creates a unique index on `(job_url, chunk_type, embedding_input_signature, embedding_contract_fingerprint)`, and uses atomic `INSERT ... ON CONFLICT DO NOTHING` for retained embedding consumers.
- [x] Keep candidate-query cache fingerprints aligned with the same strategy contract. On lexical runs, resolve baseline ranking with zero learned residual and expose `personalization_unavailable_reason=embedding_strategy_incompatible`; preserve historical policies and feedback for inspection.
- [x] On resume, validate checkpoint strategy, shortlist artifact strategy, and preference-policy fingerprint together; reject or mark stale incompatible snapshots instead of mixing hash coordinates with lexical results.

**Verification:**
- Retrieval probe ranks paraphrases and canonical skill matches above unrelated roles; same text ranks identically across runs.
- Test proves old hash vectors are not reused after strategy-version change.
- Test embeds an unchanged job twice and proves row count and LLM/provider work do not increase; changed job content creates one new contract row; concurrent duplicate writes converge to one row.
- Preference-policy and decision-feedback tests prove lexical runs preserve historical records, do not consume incompatible learned residuals, and emit honest `retrieval_score`/strategy metadata.
- Checkpoint/resume tests prove incompatible shortlist artifacts and saved policies are rejected or marked stale before ranking resumes.
- `python -m pytest tests/test_embeddings.py tests/test_vector_search.py tests/test_ranking.py tests/test_pipeline.py`
- `python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --mode replayed --warmup-iterations 5 --measured-iterations 30 --output .tmp/ranking-lexical.json`

**Exit Criteria:** Default shortlist passes retrieval recall tolerance, lexical runs do not generate unnecessary vectors, retained embedding writes are atomic and unique, incompatible personalization/checkpoint state cannot be reused, old vectors cannot contaminate new retrieval, and no new provider dependency exists.

### Task 4: Fix enrichment invalidation and enrich ranking evidence

**Purpose:** Ensure changed prompt content invalidates extraction reuse and give AI ranking enough bounded evidence without bloating retrieval summaries.

**Task Function:** Cache contract and ranking-input correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded prompt and ranking-input changes.

**Specification Coverage:** Prompt-content fingerprinting, provider/model identity, explicit job requirements and responsibilities, eligibility facts, bounded candidate evidence, and source IDs.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv/enrich.py`: `EnrichContractFingerprintPayload`, `get_enrich_prompt_provenance`, `build_enrich_contract_fingerprint`.
- `src/fitcv/ai_score.py`: `build_scoring_prompt` plus new bounded helper `build_ranking_job_input` beside it; keep retrieval text separate.
- `src/fitcv/evidence.py`: canonical `project_candidate_evidence` source projection and source references.
- `src/fitcv/pipeline.py`: ranking-stage prompt assembly and reuse fingerprints.
- `tests/test_enrich.py`, `tests/test_ai_score.py`, and `tests/test_pipeline.py`.

**Dependencies:** Tasks 2–3.

**Authority:**
- Preauthorized local actions: update listed fingerprints, prompt projections, and regression tests; preserve prompt registry ownership and bounded input sizes.
- Stop for: prompt behavior requiring a new product decision, source IDs unavailable in canonical candidate evidence, or token growth that exceeds the Task 1 benchmark envelope.

**Steps:**
- [x] Add `effective_prompt_sha256` to the enrichment contract payload. Hash canonical default template content plus replacement text, then retain resolved prompt ID, version, template path, provider/model, response schema, and post-processing versions.
- [x] Add a regression test that changes only replacement text and proves the enrichment fingerprint changes; retain existing prompt-version and schema-version tests.
- [x] Build ranking input from explicit requirements, responsibilities, language/location facts, candidate summary, and at most two source-linked candidate evidence items returned by `project_candidate_evidence`; do not add a second evidence owner in `vector_search.py`.
- [x] Keep `build_candidate_query_text` and retrieval summaries compact; do not reuse a retrieval-only projection as full ranking evidence.
- [x] Include ranking-input content and resolved provider/model identity in ranking reuse fingerprints.

**Verification:**
- `python -m pytest tests/test_enrich.py tests/test_ai_score.py tests/test_pipeline.py`
- Assert prompt replacement changes enrichment fingerprint while unrelated candidate-independent extraction remains reusable.
- Assert ranking prompt includes required bounded fields and source IDs, excludes unbounded CV text, and invalidates reuse when evidence or prompt content changes.

**Exit Criteria:** Default-template or replacement-text edits cannot reuse stale extraction; ranking receives explicit bounded evidence from the canonical projection; cache dependencies remain stage-specific; focused tests pass.

### Task 5: Remove confirmed backend/control-plane overhead

**Purpose:** Keep remote telemetry and Runs list work off critical pipeline execution while preserving durable local truth and API behavior.

**Task Function:** Backend performance correction with direct boundary and side-effect proof.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: backend persistence, query, and performance boundaries.

**Specification Coverage:** Durable telemetry persistence, bounded remote delivery, SQL-side Runs filtering/counts/pagination, list projection, and unchanged API response semantics.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`, `skill-full-stack-integration`.

**Files And Symbols:**
- `src/fitcv_cp/reporter.py`: `PipelineReporter.emit`, `retry_pending_process_event_deliveries`, and `deliver_process_event`.
- `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/main.py`: existing outside-pipeline drain points.
- `src/fitcv_cp/sqlite_store.py`: `query_runs`, `_normalized_run_from_row`, `get_run_detail`, schema/write/backfill helpers for normalized search projection and delivery claims.
- `src/fitcv_cp/app.py`: `/runs` list handler and `/runs/{run_id}` detail handler.
- `tests/test_fitcv_cp/test_reporter.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_main.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, and `tests/test_fitcv_cp/test_app.py`.

**Dependencies:** Tasks 2–4.

**Authority:**
- Preauthorized local actions: change listed backend/reporting/query code, add normalized search projection and delivery-claim fields through the existing SQLite schema initialization path, and run direct local boundary tests with mocked remote failures.
- Stop for: data-loss risk in event persistence, API response-shape drift without a consumer decision, destructive schema migration, or measured correctness mismatch in search normalization.

**Steps:**
- [x] Remove pending-delivery retry and direct remote delivery from `PipelineReporter.emit`; keep `append_event` durable and mark Langfuse delivery pending.
- [x] Make `fitcv_cp.main` own local-controller delivery and `fitcv_cp.worker_job` own server-worker delivery: each starts one bounded background drain loop after process readiness, stops it on process shutdown, and performs a final bounded drain after terminal run persistence without waiting on remote HTTP during startup or pipeline execution.
- [x] Add atomic delivery claims/leases in the existing SQLite delivery table, with bounded batch size, retry backoff, next-attempt time, lease expiry, and one active claim per `(event_id, sink)` so multiple workers cannot deliver the same event concurrently.
- [x] Prove terminal events drain without another run or process restart; prove remote failure does not delay app startup, pipeline start, or pipeline completion.
- [x] Change `query_runs` to apply view, normalized search, counts, ordering, `LIMIT`, and `OFFSET` in SQL. Populate persisted normalized search projection through the same Python NFKC/casefold helper used by current search behavior, with backfill and update paths for existing and new rows.
- [x] Escape literal `%` and `_` in search parameters; test Unicode normalization, substring semantics, active/archived/all counts, and stable ordering. Accept that exact counts and substring searches may scan records; promise bounded returned pages, not page-sized total work.
- [x] Preserve lifecycle reconciliation by keeping `_reconcile_orphaned_run` in the `/runs` list handler before lightweight projection, or transfer it to one identified store owner and remove the duplicate. Add abandoned-worker consistency tests for list/detail status.
- [x] Return the list projection needed by `/runs` directly from `query_runs`; remove per-item `get_run_detail` calls from the list handler while keeping `/runs/{run_id}` detail expansion unchanged.
- [x] Capture identical before/after workload metrics at 100, 1,000, and 10,000 synthetic runs: SQL statements, rows read, endpoint p50/p95, and response item equality.

**Verification:**
- Reporter boundary test mocks a 5-second Langfuse timeout and proves `emit()` persists locally without waiting for HTTP; separate drain test proves delivery still occurs outside emission.
- Delivery lifecycle test proves terminal events arrive without another run or restart, startup/pipeline completion do not wait on remote failure, and concurrent drainers honor claims/leases.
- SQLite tests prove filtered counts and page contents match pre-change behavior, including NFKC/casefold search, active/archived/all views, and stable ordering.
- SQLite tests cover literal `%` and `_`, normalized search backfill/update, and abandoned-worker reconciliation consistency.
- App tests prove `/runs` performs no per-row detail expansion and `/runs/{run_id}` still returns full detail.
- `python -m pytest tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- `python scripts/benchmark_runs_list.py --sizes 100,1000,10000 --warmup-iterations 5 --measured-iterations 30 --output .tmp/runs-list-after.json`

**Exit Criteria:** Local event truth survives remote failure, terminal events drain without a later run/restart, delivery claims prevent concurrent duplicates, `emit()` has no remote wait, Runs list preserves reconciliation and performs bounded paginated work without N+1 detail reads, and API rows match baseline.

### Task 6: Make active-run polling bounded and visibility-aware

**Purpose:** Prevent overlapping or hidden-tab polling while retaining prompt updates for active runs.

**Task Function:** Frontend state and browser verification.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: frontend lifecycle and browser behavior.

**Specification Coverage:** One in-flight request, visible-tab polling, cleanup on unmount, resume on visibility change, and unchanged terminal-run behavior.

**Required Skills:** `skill-full-stack-integration`, `skill-test-driven-development`.

**Files And Symbols:**
- `frontend/src/features/runs/runs-list.tsx`: `loadRuns`, active-run polling `useEffect`, request identity, and lifecycle state.
- `frontend/src/features/runs/api.ts`: existing Runs list request contract; no new endpoint.
- Add `frontend/src/test/runs-list.test.tsx` using existing frontend test setup; do not add test infrastructure.
- `tests/test_fitcv_cp/test_app.py`: list response contract used by the frontend.

**Dependencies:** Task 5.

**Authority:**
- Preauthorized local actions: update the existing Runs list polling effect and focused frontend tests; use browser snapshots and network inspection against the existing local app.
- Stop for: a required API contract change, inability to prove request cancellation/overlap behavior, or any regression in manual refresh/search/pagination.

**Steps:**
- [x] Track one in-flight `loadRuns` request and skip a timer tick while it remains pending.
- [x] Assign each load request a query identity derived from `view`, `activeSearch`, `page`, and `pageSize`; deduplicate polling only for the same identity, supersede or abort requests after filter/page changes, ignore obsolete responses, and ignore state updates after unmount.
- [x] Start polling only when at least one run is non-terminal and `document.visibilityState === "visible"`.
- [x] Stop polling on hidden state, resume on `visibilitychange` when active runs remain, and clear timers/listeners on unmount.
- [x] Keep existing one-second cadence for visible active runs unless Task 1 measurements show a lower cadence meets update expectations; do not add a new polling library.
- [x] Scope this task to Runs-list polling; leave run-detail polling unchanged and deferred.

**Verification:**
- Frontend checks from `frontend/`: `npm run typecheck`, `npm run test`, `npm run test:a11y`, and `npm run build`.
- Browser proof: visible active run polls, hidden tab sends no new requests, delayed response does not create overlap, visibility restore resumes one request, terminal runs stop polling.
- Browser proof: changing search/view/page during delayed polling leaves only newest query state visible; unmount prevents late response updates.
- Backend contract proof: `python -m pytest tests/test_fitcv_cp/test_app.py`.

**Exit Criteria:** Runs-list polling has request identity, one in-flight request per query, obsolete responses cannot overwrite newer state, polling pauses while hidden, resumes correctly, stops for terminal runs, run-detail polling remains unchanged, and frontend checks pass without API changes.

### Task 7: Final integration, review, and deferred-work gate

**Purpose:** Reconcile all outcomes against source, tests, benchmark deltas, and the approved non-goals before any future adaptive-ranking work.

**Task Function:** Independent verification and acceptance review.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent final evidence challenge.

**Specification Coverage:** Cross-task correctness, performance evidence, regression proof, scope control, and deferred adaptive-scoring decision.

**Required Skills:** `skill-plan-document-reviewer`, `skill-verification-before-completion`, `skill-performance-optimization`.

**Files And Symbols:** All files changed by Tasks 1–6; this plan; `README.md` or feature documentation only when user-visible contracts changed.

**Dependencies:** Tasks 1–6.

**Authority:**
- Preauthorized local actions: run fresh validation, inspect diff and benchmark artifacts, dispatch one independent read-only review, and update this plan's coordination ledger.
- Stop for: failed acceptance evidence, unreviewed schema/API drift, benchmark workload mismatch, unbounded scope growth, or any request to start adaptive scoring without a separate approved contract.

**Steps:**
- [x] Run focused tests nearest each changed surface, then the full Python and frontend validation commands listed below.
- [x] Compare baseline and after metrics using identical fixture, iteration count, environment, and database workload.
- [x] Run `git diff --check`, inspect changed files, and confirm unrelated dirty files remain untouched.
- [x] Dispatch independent review through Herdr review lane; first review returned FAIL and findings were patched before re-review.
- [x] Record accepted deviations and deferred work in this plan; do not mark completion from tool exit alone.

**Verification:**
- `python "$HOME/.agents/project-os/scripts/validate_template_required_sections.py" --repo-root .`
- `python "$HOME/.agents/project-os/scripts/validate_planning_lifecycle.py" --repo-root .`
- `python -m pytest`
- From `frontend/`: `npm run typecheck`, `npm run test`, `npm run test:a11y`, and `npm run build`.
- `git diff --check`
- Independent review returns `PASS` or a resolved finding list with path:line evidence.

**Exit Criteria:** All implementation outcomes have fresh evidence, performance claims use identical workloads, no deferred item is presented as shipped, and final verification returns `verified` before plan status changes to `completed`.

## Accepted Deviations

- Repository-wide Python collection remains blocked by missing `scripts/filter_langfuse_export.py`; the excluded run also retains unrelated agentic-fit, ATS-opener, and scan-fixture/provider failures.
- Frontend full-suite failure at `frontend/src/test/scans.test.ts:441` is pre-existing; clean-base commit `11e11e6612391b5a0595bdee749da7fc38d0a833` reproduces `Full-time` versus `Full time`. Frontend typecheck retains unrelated existing errors.
- Windows temp SQLite cleanup emits `PermissionError` after passing control-plane assertions.
- Stdlib SQLite tracing cannot expose exact rows-read counts; benchmark records `rows_read: null` and retains SQL statement, response equality, progress, and p50/p95 evidence.
- Legacy plan/spec validator failures remain covered by approved governance exception; legacy artifacts stay untouched.

## Verification

### Correctness

- `python -m pytest tests/test_ai_score.py tests/test_ranking_contract.py tests/test_ranking.py tests/test_embeddings.py tests/test_vector_search.py tests/test_enrich.py tests/test_pipeline.py`
- `python -m pytest tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- `python -m pytest`

### Frontend and boundary

- From `frontend/`: `npm run typecheck`
- From `frontend/`: `npm run test`
- From `frontend/`: `npm run test:a11y`
- From `frontend/`: `npm run build`
- Browser network and visibility proof for `frontend/src/features/runs/runs-list.tsx`.

### Performance

- Baseline and after runs use `tests/fixtures/ranking_gold.json`, identical `--warmup-iterations 5`, identical `--measured-iterations 30`, identical Python/runtime environment, and synthetic Runs databases at 100, 1,000, and 10,000 rows.
- Metrics: shortlist Recall@50, Recall@`ai_score_top_n`, NDCG@15, false-rejection rate, valid-zero preservation, unscored-row count, cache hit/miss rate, LLM calls, SQL statements, rows read, and p50/p95 latency.
- Threshold owner: plan owner. Hard thresholds: zero operational failures labeled as valid fit; zero duplicate embedding inserts for unchanged signatures; zero remote HTTP wait inside `PipelineReporter.emit`; zero per-row detail queries in `/runs`; zero overlapping visible-tab polling requests.
- Quality threshold: no gold-set Recall@50 or NDCG@15 regression from baseline without an explicit approved decision.
- Performance target: reduce measured Runs list SQL rows read and list endpoint p95 at 1,000 and 10,000 runs; report numeric before/after deltas instead of claiming improvement from source inspection.

## Completion Criteria

- Score failure semantics pass parser, runtime, ranking, cache, export, and API tests.
- Valid zero scores remain valid and rankable.
- Retrieval uses `lexical_v1` or an explicitly approved successor with benchmark evidence; SHA-256 byte projections no longer drive shortlist ordering.
- Prompt replacement changes enrichment reuse fingerprint.
- Ranking input contains bounded explicit requirements and source-linked candidate evidence.
- Telemetry remains durably recorded while remote delivery runs outside pipeline emission.
- Runs list uses SQL-side pagination and list projection without detail N+1 expansion.
- Runs polling pauses when hidden and prevents overlap.
- Full verification and independent review return fresh passing evidence.
- Adaptive scoring, two-pass explanations, ATS concurrency, and provider/client architecture remain deferred until a separate approved plan passes benchmark gates.
