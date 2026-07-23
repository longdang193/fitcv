---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: cv-runtime-job-concurrency-and-request-pacing
parent_spec: docs/superpowers/specs/2026-07-22-16-31-fitcv-packaged-local-complete-frontend-backend-integration-spec.md
targets:
  - config/runtime/pipeline.yaml
  - docs/fitcv-settings-ui-prototype.html
  - docs/configuration.md
  - docs/pipeline-settings-page-suggestions.md
  - src/fitcv/config.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/retry_settings.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - tests/test_config.py
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_retry_settings.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_pipeline_prototype.py
---

# CV Runtime Job Concurrency And Request Pacing Implementation Plan

## Goal

Replace stage-local batch and delay controls with one understandable scheduling contract: every pipeline item is one executor job, each stage exposes only its maximum simultaneous jobs, and all generative provider requests use one process-global minimum request-start interval enforced at the shared LLM execution boundary. Keep CV Analysis local and unpaced, buffer completed Enrichment results internally before persistence, and preserve deterministic output order, reuse, cancellation, heartbeat, checkpoints, and immutable run snapshots.

Prototype and maintained documentation must show the same contract before production UI work is considered complete. This plan does not add provider-specific pacing overrides, user-configurable persistence batching, new executor infrastructure, or parallel configuration owners.

## Implementation Outcomes

### One canonical runtime settings contract

`llm_runtime.request_start_interval_secs` becomes the only request-pacing setting, with default `0.0`, finite nonnegative values, and zero disabling pacing. `stage_runtime.enrich.concurrency`, `stage_runtime.ranking.concurrency`, `stage_runtime.cv_analysis.concurrency`, and `stage_runtime.cv_generation.concurrency` remain the only stage scheduling controls, keep defaults `8`, `4`, `4`, and `4`, require integers of at least `1`, and are labeled **Maximum Concurrent Jobs**. Removed stage `sleep_secs`, `batch_size`, and legacy top-level throughput aliases no longer affect new runs or appear in Settings, runtime summaries, prototype state, effective-setting snapshots, or maintained docs.

### Provider-keyed request-start pacing

`execute_llm_task` owns thread-safe request-start pacing immediately before adapter invocation. Within the packaged-local worker process, requests using the same provider connection share one monotonic-time bucket; requests using different providers do not block each other. Cross-process pacing is out of scope. Zero disables pacing. Routing, credential validation, parse, validation, retry backoff, local CV Analysis, and non-LLM work remain outside the pacing wait.

### One item per executor task

Ranking, CV Analysis, and CV Generation submit one item per `ThreadPoolExecutor` future and collect results by original index. Enrichment also submits one job per future, preserves per-job retry and runtime observations, and buffers completed rows for persistence without changing returned order or failure semantics.

### Preserved run behavior and evidence

Run-trigger snapshots freeze process-global pacing, four stage concurrency values, System `maximum_attempts`, and System `initial_backoff_seconds`. Existing reuse, cancellation polling, heartbeat events, checkpoint/replay behavior, worker-slot evidence, incremental artifact persistence, and historical settings-used exports remain deterministic and compatible with completed runs.

### Prototype, production UI, and docs agree

Runtime & Limits shows one shared **Minimum Request Start Interval (seconds)** setting followed by four stage rows whose managed form contains only **Maximum Concurrent Jobs**. Help text distinguishes request pacing from retry backoff and states that CV Analysis is local. Prototype self-checks, Settings schema tests, route tests, and maintained configuration docs prove the same UI intent.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-code-standards`, `skill-full-stack-integration`, `skill-central-config-layer`, `skill-frontend-component-engineering`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: optional worktree on a `codex/` branch before execution; preserve unrelated `docs/fitcv-preference-optimization-ui-prototype.html`
- Parallel ownership: none; `config.py`, `runtime_routing.py`, `llm_runtime.py`, `pipeline.py`, Settings schema, prototype, and shared runtime tests form one ordered contract
- Sequential fallback: settings contract, pacing boundary, per-item stage scheduling, Enrichment persistence buffering, UI/docs, then final cross-stack verification

## Task Breakdown

### Task 1: Replace timing schema and snapshots

**Purpose:**
- Establish one canonical pacing value and four stage concurrency values before changing execution behavior.

**Specification Coverage:**
- Remove Batch Size from Enrichment, Ranking, CV Analysis, and CV Generation.
- Remove all stage-local Delay controls, including CV Analysis.
- Keep one global per-request pacing control and one concurrency control per stage.
- Freeze selected values into each run's effective settings and settings-used artifact.

**Required Skills:**
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/config.py:get_stage_runtime_value`, `get_stage_runtime_batch_size`, `get_stage_runtime_concurrency`, `get_stage_runtime_sleep_secs`
- Modify: `config/runtime/pipeline.yaml` canonical runtime defaults
- Modify: `src/fitcv/config.py` runtime accessors, canonical pipeline keys, and legacy compatibility projection
- Modify: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`, `timing_canonical_runtime_throughput_keys`, `timing_compatibility_runtime_alias_keys`, `build_settings_page_spec`
- Modify: `src/fitcv_cp/app.py:_apply_trigger_runtime_envelope` and runtime payload projections that still read stage delays
- Modify: `src/fitcv_cp/worker_run_support.py:_build_settings_used_payload_dict`, `_materialize_stage_runtime_snapshot`
- Modify: `src/fitcv_cp/worker_job.py` removed runtime-helper imports
- Inspect: `src/fitcv_cp/settings_store.py:_decode_active_settings_rows`
- Verify: `tests/test_config.py`, `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Approved setting key is `llm_runtime.request_start_interval_secs`.
- Stage keys remain `stage_runtime.<stage>.concurrency` to preserve current snapshot structure.
- Request interval default is `0.0`; accepted values are finite floats greater than or equal to `0.0`.
- Concurrency defaults remain Enrichment `8`, Ranking `4`, CV Analysis `4`, and CV Generation `4`; accepted values are integers greater than or equal to `1`.
- Existing persisted historical runs remain readable; removed keys are ignored rather than migrated into new semantics.
- Stale active Settings rows for removed keys follow the existing schema-backed cleanup path in `_decode_active_settings_rows`; no compatibility alias translates old stage delays, batch sizes, or top-level Enrichment concurrency into current settings.

**Steps:**
- [x] Step 1: Add failing tests for request interval default `0.0`, finite nonnegative validation, concurrency defaults `8/4/4/4`, integer minimum `1`, Settings page grouping, nested config application, run-trigger snapshot retention, stale-row cleanup, and absence of stage batch/delay rows.
- [x] Step 2: Replace canonical YAML defaults with `llm_runtime.request_start_interval_secs: 0.0` and four `stage_runtime.<stage>.concurrency` values; delete `enrichment_sleep_secs`, `enrichment_batch_size`, `enrichment_concurrency`, `rerank_sleep_secs`, and stage `sleep_secs`/`batch_size` values.
- [x] Step 3: Add `get_llm_request_start_interval_secs`, retain `get_stage_runtime_concurrency`, delete active callers/exports of `get_stage_runtime_batch_size` and `get_stage_runtime_sleep_secs`, and remove retired top-level runtime keys from canonical config ownership.
- [x] Step 4: Replace twelve Timing schema rows and four compatibility alias rows with one global pacing row plus four concurrency rows; label every concurrency field **Maximum Concurrent Jobs** and describe it as maximum simultaneous item jobs.
- [x] Step 5: Update Runtime & Limits page spec and diagnostic rules so zero pacing is valid, concurrency validation remains positive, and no warning assumes stage delay or batching.
- [x] Step 6: Ensure trigger-time effective config and immutable settings-used output include `llm_runtime.request_start_interval_secs` and four stage concurrency values; stop materializing removed values in new `settings_used_v2` payloads while preserving old completed-run payloads verbatim when displayed.
- [x] Step 7: Remove retired helper imports and CV Analysis delay leakage from synonym recommendation runtime payloads; external synonym LLM requests receive pacing only through shared LLM routing, while builtin recommendations remain unpaced.

**Verification:**
- [x] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- Expected: new settings contract passes; no current-run schema, trigger snapshot, or settings-used assertion requires stage `batch_size` or `sleep_secs`.

**Exit Criteria:**
- New runs have one pacing value and four concurrency values as runtime SSOT; removed stage controls have no active Settings or snapshot owner.

### Task 2: Centralize provider request-start pacing

**Purpose:**
- Enforce shared pacing once at the actual generative provider-call boundary.

**Specification Coverage:**
- Pace actual generative provider requests at `execute_llm_task`.
- Same-provider requests share pacing; different providers remain independent.
- Retry backoff remains separate from request pacing.
- CV Analysis remains local and unpaced.

**Required Skills:**
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/runtime_routing.py:LlmRouting`, `resolve_llm_routing`
- Modify: `src/fitcv/llm_runtime.py:execute_llm_task` and a module-private provider pacing helper/state
- Modify: `src/fitcv_cp/app.py:_apply_trigger_runtime_envelope`
- Verify: `tests/test_runtime_routing.py`, `tests/test_llm_runtime.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 defines the canonical pacing setting and run snapshot.
- Provider pacing key is existing canonical `route.provider`: provider IDs are unique and each provider owns at most one connection, so no second connection identity or provider-specific setting is introduced.
- Process-global means all stage threads inside the packaged-local worker process; distributed cross-process pacing is explicitly out of scope.

**Steps:**
- [x] Step 1: Add deterministic tests with injected monotonic clock/wait hooks proving zero-delay behavior, same-provider serialization, independent provider buckets, and no wait before routing/credential failures.
- [x] Step 2: Carry the frozen global interval through `resolve_llm_routing(..., runtime_config=config)` into `LlmRouting` without copying it into provider registry persistence.
- [x] Step 3: Add one thread-safe module-private map keyed by canonical provider connection identity and acquire a request-start slot immediately before `selected_adapter(...)`; first request starts immediately and later starts reserve monotonic slots at the configured interval.
- [x] Step 4: Keep adapter retry behavior and System `initial_backoff_seconds` separate; pacing applies to every adapter attempt only when that attempt crosses `execute_llm_task`.
- [x] Step 5: Keep pacing state private; focused tests clear the private map in fixture setup so state cannot leak between cases without adding a production test-only API.

**Verification:**
- [x] `py -3 -m pytest tests/test_runtime_routing.py tests/test_llm_runtime.py tests/test_fitcv_cp/test_app.py -q`
- Expected: request starts for one provider respect configured spacing; another provider can start independently; local/non-adapter failures do not consume slots.

**Exit Criteria:**
- One shared LLM boundary owns pacing, with no stage-specific rate limiter or submission sleep needed for generative requests.

### Task 3: Submit one Ranking and late-stage job per future

**Purpose:**
- Remove executor batching from Ranking, CV Analysis, and CV Generation while preserving order and lifecycle behavior.

**Specification Coverage:**
- Ranking, CV Analysis, and CV Generation submit one job per executor task.
- Concurrency means maximum simultaneous jobs.
- CV Analysis has no delay and makes no generative provider call.
- Preserve deterministic order, reuse, cancellation, heartbeat, checkpoints, and historical evidence.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/ai_score.py:run_ai_scoring`
- Modify: `src/fitcv/agentic_cv_analysis.py:_cv_analysis_sleep_secs` and callers
- Modify: `src/fitcv/agentic_cv_generation.py:_cv_generation_sleep_secs` and callers
- Modify: `src/fitcv/pipeline.py` CV Analysis and CV Generation executor submission/collection blocks
- Verify: `tests/test_ai_score.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`

**Dependencies:**
- Task 2 provides provider pacing for Ranking and CV Generation.
- Existing effective-concurrency calculation remains `min(configured_concurrency, runnable_work_items)` and zero when no runnable work remains.

**Steps:**
- [x] Step 1: Replace batch-oriented tests with failing assertions that each runnable item produces one submitted future and configured concurrency bounds simultaneous item execution.
- [x] Step 2: Simplify Ranking to submit `_score_single(index, job)` per selected job, collect by original index, and delete batch construction and inter-submission sleep.
- [x] Step 3: Simplify CV Analysis to submit one analysis work item per future, remove `_cv_analysis_sleep_secs`, and preserve local deterministic embedding behavior and worker-slot metadata.
- [x] Step 4: Simplify CV Generation to submit one generation index per future, remove `_cv_generation_sleep_secs`, and preserve polling heartbeat, cancellation checks, attempt traces, reuse, checkpoint writes, and ordered finalization.
- [x] Step 5: Remove dead batch-size and stage-sleep imports/helpers only after all callers are gone.

**Verification:**
- [x] `py -3 -m pytest tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`
- Expected: one future per runnable Ranking/CV Analysis/CV Generation item; outputs and persisted artifacts remain in input order under out-of-order completion.

**Exit Criteria:**
- Three stages use per-item executor jobs, with concurrency as their only scheduling knob and no local pacing logic.

### Task 4: Submit individual Enrichment jobs and buffer persistence

**Purpose:**
- Convert Enrichment from chunk workers to per-job workers while avoiding one persistence transaction per completion.

**Specification Coverage:**
- Enrichment submits jobs individually.
- Completed Enrichment results are buffered for persistence.
- Internal persistence buffer is not user-configurable.
- Preserve per-job retry isolation, observations, order, incremental durability, cancellation, and heartbeat.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/enrich.py:_acquire_enrich_rate_slot`, `_enrich_chunk`, `enrich_batch`
- Modify: `src/fitcv/pipeline.py:_enrich_jobs_with_reuse`, `_run_enrich_call_with_polling`, `_enrich_runtime_projection`
- Modify: `src/fitcv_cp/app.py:_apply_trigger_runtime_envelope`
- Inspect: `src/fitcv_cp/retry_settings.py:load_retry_settings`, `SYSTEM_SETTINGS_DEFAULTS`
- Verify: `tests/test_enrich.py`, `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_retry_settings.py`, `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 2 replaces `_acquire_enrich_rate_slot` with shared provider pacing.
- Trigger-time runtime inputs freeze the canonical System settings resource, including revision; Enrichment reads `maximum_attempts` and `initial_backoff_seconds` from that snapshot rather than live Settings, `enrichment_max_retries`, or removed Enrichment delay.
- Persistence buffer threshold is internal constant `10` completed results; it is not added to configuration or UI.

**Steps:**
- [x] Step 1: Add failing tests proving one future per fresh job, bounded simultaneous execution in normal and `FITCV_ENRICH_DEBUG_HEARTBEAT` modes, out-of-order completion with input-order return, System-owned retry attempts/backoff, and persistence flushes at ten completed rows plus final remainder.
- [x] Step 2: Snapshot System settings in `_apply_trigger_runtime_envelope`, add the smallest config-side accessors for frozen `maximum_attempts` and `initial_backoff_seconds`, remove `enrichment_max_retries`, and replace `_enrich_chunk` with a single-job worker retaining job start/done events, runtime observations, existing retry eligibility, and normalized failure propagation.
- [x] Step 3: Submit each fresh job independently with `stage_runtime.enrich.concurrency`, collect completed rows into an index map, and reconstruct returned rows in original input order; use this same scheduler in normal and debug-heartbeat modes so diagnostics never change concurrency semantics.
- [x] Step 4: Buffer finalized completed rows inside `_enrich_jobs_with_reuse`; flush each ten-row buffer and the final remainder through existing `load_structured_jobs` and `load_run_structured_jobs` calls.
- [x] Step 5: On success, flush the final remainder. On the first non-recoverable worker failure or observed cancellation, flush only completed rows already delivered to the buffer, then propagate; results completing after failure processing stops are not persisted. Existing persistence callback failures remain warnings and do not replace the stage outcome.
- [x] Step 6: Remove `enrichment_max_retries`, `enrichment_batch_size`, `enrichment_sleep_secs`, `enrichment_concurrency`, `_acquire_enrich_rate_slot`, chunk callback naming, and runtime projection aliases after consumers are gone.

**Verification:**
- [x] `py -3 -m pytest tests/test_enrich.py tests/test_pipeline.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_worker_job.py -q`
- Expected: Enrichment runs one item per future, returns deterministic order, uses global provider pacing, and persists completed results in internal groups of ten plus remainder.

**Exit Criteria:**
- Enrichment has per-item execution and bounded persistence writes without exposing another user setting or changing artifact truth.

### Task 5: Align production UI, prototype, and maintained docs

**Purpose:**
- Make approved runtime behavior visible and understandable across production Settings, approved prototype, UI intent, and durable configuration docs.

**Specification Coverage:**
- Prototype adjustments are required.
- Runtime & Limits must expose one global pacing setting and four concurrency-only stage forms.
- CV Analysis must not imply an LLM/API delay.
- Retry backoff must be described as separate from request pacing.

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-frontend-component-engineering`
- `ui-ux-pro-max`

**Files And Symbols:**
- Modify: `docs/fitcv-settings-ui-prototype.html:runtime`, runtime transactions, stored-state normalizer, runtime summary formatter, prototype self-checks
- Modify: `src/fitcv_cp/settings_schema.py:build_settings_page_spec`
- Modify: `docs/configuration.md` runtime timing contracts
- Modify: `docs/pipeline-settings-page-suggestions.md` Runtime & Limits guidance
- Verify: `tests/test_fitcv_pipeline_prototype.py`, `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_local_routes.py`

**Dependencies:**
- Tasks 1 through 4 define final setting names and behavior.
- Approved prototype remains source of truth for UI intent; production schema and page rendering must consume canonical settings rather than duplicate values.
- No active `*.integration.md` sidecar exists; update durable prototype tests and maintained docs directly.

**Steps:**
- [x] Step 1: Add failing prototype and route assertions for the shared pacing row, four concurrency-only managed dialogs/sections, labels, descriptions, defaults, summary text, and absence of Batch Size/stage Delay controls.
- [x] Step 2: Replace prototype `runtime(title, description, delay, batch, concurrency)` state with a shared pacing definition plus reusable concurrency-only stage definition; update transactions and normalizer without retaining duplicate legacy state.
- [x] Step 3: Render **Minimum Request Start Interval (seconds)** once above stage rows; describe same-provider pacing, independent providers, zero-disable behavior, and separation from retry backoff.
- [x] Step 4: Render each stage row as `<stage name> · <n> maximum concurrent jobs`; managed UI exposes one **Maximum Concurrent Jobs** number input and explains CV Analysis is local work.
- [x] Step 5: Update prototype validation and self-checks for nonnegative global pacing, positive integer concurrency, no removed controls, theme parity, keyboard operation, and narrow viewport behavior.
- [x] Step 6: Replace batching/pacing claims in maintained docs with per-item scheduling, provider-keyed request starts, internal Enrichment persistence buffering, and local CV Analysis semantics.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_pipeline_prototype.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_local_routes.py -q`
- Expected: prototype, production page contract, and docs expose one pacing setting and four symmetric concurrency controls with no stale batch/delay language.
- [x] Playwright MCP: open Runtime & Limits at desktop and narrow widths; inspect shared pacing and each stage Manage flow; keyboard-edit, save, reload, switch themes, and confirm removed fields never appear. Approved deferral: local `file://` inspection is blocked by Browser security policy.
- Expected: controls remain accessible, responsive, theme-correct, and consistent with existing Settings row/dialog components.

**Exit Criteria:**
- Approved prototype, production Settings contract, UI tests, and maintained docs describe exactly the implemented scheduling semantics.

### Task 6: Verify cross-stack behavior and reconcile plan

**Purpose:**
- Prove scheduling, pacing, persistence, UI, and historical artifacts remain coherent after cutover.

**Specification Coverage:**
- Preserve deterministic output order, reuse, cancellation, heartbeat, checkpoints, and historical run snapshots.
- Do not create parallel settings, provider registries, pacing layers, or user-facing persistence buffer controls.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all targets listed in frontmatter
- Modify: this plan only for checked tasks, deviations, blockers, substitutions, and final `status`
- Verify: focused runtime suites, control-plane suites, full test suite, repository validators, browser flow, and diff hygiene

**Dependencies:**
- Tasks 1 through 5 complete with focused proof.

**Steps:**
- [x] Step 1: Search maintained config, source, tests, prototype, and docs for active `stage_runtime.*.batch_size`, stage `sleep_secs`, `enrichment_max_retries`, `enrichment_batch_size`, `enrichment_sleep_secs`, `enrichment_concurrency`, `rerank_sleep_secs`, chunk scheduling, and stage submission sleeps; retain matches only inside explicit historical-artifact fixtures.
- [x] Step 2: Run focused tests covering config, routing, LLM pacing, four stages, pipeline reuse/lifecycle, worker snapshots, Settings routes/schema, and prototype.
- [x] Step 3: Run full tests and repository validators; compare failures only against a freshly captured baseline if unrelated failures exist.
- [x] Step 4: Run browser proof for Runtime & Limits and inspect console/network behavior; verify no request is generated by CV Analysis settings interactions and no removed control survives responsive/theme states. Approved deferral: automated inspection cannot access local `file://` content.
- [x] Step 5: Reconcile every task checkbox, record deviations, and invoke completion verification before changing plan status from `active` to `completed`.

**Verification:**
- [x] `py -3 -m pytest tests/test_config.py tests/test_runtime_routing.py tests/test_llm_runtime.py tests/test_enrich.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_pipeline_prototype.py -q`
- [x] `py -3 -m pytest tests -q`
- [x] `py -3 scripts/validate_planning_lifecycle.py`
- [x] `py -3 scripts/validate_template_required_sections.py`
- [x] `py -3 scripts/hooks/run_validator.py --fast`
- [x] `git diff --check`
- Expected: all required checks pass or match only documented unchanged baseline; no active duplicate timing owner remains.

**Exit Criteria:**
- Fresh evidence proves approved runtime and prototype contract end to end, and plan accurately records implementation state.

## Execution Notes

- 2026-07-23 focused cross-stack verification passed: `1163 passed, 2 skipped`.
- 2026-07-23 full suite ran: `50 failed, 2274 passed, 4 skipped`. Failures match unchanged baseline areas: existing `pipeline_stage_runner` deferred-cleanup imports are present at `HEAD`, inverse-optimization tests cannot run because optional `cvxpy` is not installed, and planning/repository validators report pre-existing legacy planning metadata drift outside this plan's targets.
- Pytest exits also emit the existing Windows temp cleanup warning for `C:\tmp\pytest-of-HOANG PHI LONG DANG\pytest-current`; focused tests still exit successfully.
- Static stale-contract audit found retired runtime names only in explicit cleanup/pruning code and compatibility tests; no active current-run timing owner remains.
- `git diff --check` passes with line-ending conversion warnings only.
- Browser proof was blocked: the prototype was opened manually in the in-app browser, but Browser security policy rejects inspection of local `file://` content. No alternate browser surface or local-HTTP workaround was used; automated desktop/narrow, theme, keyboard/focus, save/reload, console, network, and overflow checks were not run.
- 2026-07-23 user explicitly approved deferring automated browser proof; static prototype assertions and route/schema tests remain required evidence for this plan.
- `validate_template_required_sections.py` reports this completed plan because the canonical implementation-plan template hard-codes `status: proposed`; the same unchanged validator rejects existing active/completed plans repo-wide. This known deprecated CI baseline is outside current scope.

## Verification

- `py -3 -m pytest tests/test_config.py tests/test_runtime_routing.py tests/test_llm_runtime.py tests/test_enrich.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_pipeline_prototype.py -q`
- `py -3 -m pytest tests -q`
- `py -3 scripts/validate_planning_lifecycle.py`
- `py -3 scripts/validate_template_required_sections.py`
- `py -3 scripts/hooks/run_validator.py --fast`
- `git diff --check`
- Playwright MCP verifies Runtime & Limits desktop/narrow, keyboard/focus, save/reload, light/dark, and absence of removed controls.
- Chrome DevTools MCP verifies no uncaught console errors, unexpected failed requests, layout overflow, or duplicate runtime-setting payloads.

## Completion Criteria

The plan is ready for completion verification when:

1. `llm_runtime.request_start_interval_secs` is the only current-run request-pacing setting, defaults to `0.0`, accepts finite nonnegative values, and is frozen into run effective settings;
2. `stage_runtime.enrich.concurrency`, `stage_runtime.ranking.concurrency`, `stage_runtime.cv_analysis.concurrency`, and `stage_runtime.cv_generation.concurrency` are the only stage scheduling controls, retain defaults `8/4/4/4`, and accept integers of at least `1`;
3. same-provider generative request starts inside the packaged-local worker process share one thread-safe pacing bucket, different providers remain independent, zero disables pacing, and cross-process pacing is not claimed;
4. System `maximum_attempts` and `initial_backoff_seconds` drive Enrichment retries and remain distinct from request pacing; no `enrichment_max_retries` owner remains;
5. CV Analysis remains local, uses no LLM/API pacing, and exposes no Delay or Batch Size control;
6. Ranking, CV Analysis, CV Generation, and Enrichment submit one runnable item per executor future and preserve configured concurrency caps;
7. all four stages preserve deterministic output order, reuse, cancellation, heartbeat, checkpoint/replay, worker-slot evidence, and historical run snapshots;
8. Enrichment buffers ten completed finalized rows per persistence flush, flushes the final or pre-failure remainder, never persists later completions after failure processing stops, and exposes no user setting;
9. approved prototype and production Runtime & Limits show one shared pacing control and four symmetric **Maximum Concurrent Jobs** controls with accessible validation and responsive/theme behavior;
10. maintained docs and tests contain no active claim that current work items are batches or that stages own request delays;
11. focused tests, full tests, planning validators, repository validator, browser evidence, and diff hygiene pass or match only documented unrelated baseline;
12. no second provider registry, pacing subsystem, executor abstraction, retry owner, or persistence-buffer configuration is introduced;
13. every task, deviation, blocker, substitution, and deferral is reconciled against approved scope and current repository truth.

The plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification;
2. confirms completion criteria against repository evidence;
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation;
4. returns `verified` and updates plan status.

A checked box records progress; it is not proof by itself.
