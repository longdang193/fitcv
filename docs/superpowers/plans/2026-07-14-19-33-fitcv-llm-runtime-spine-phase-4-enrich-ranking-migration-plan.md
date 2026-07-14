---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-implementation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-19-22-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-spec.md
targets:
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - config/runtime/control_plane.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/enrich.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/features/bounded_parallel_enrichment/feature.source.yaml
  - docs/features/bounded_parallel_enrichment/bounded_parallel_enrichment.yaml
  - docs/features/bounded_parallel_enrichment/lineage.generated.yaml
  - docs/features/bounded_parallel_enrichment/history.md
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/pipeline_performance/pipeline_performance.yaml
  - docs/features/pipeline_performance/lineage.generated.yaml
  - docs/features/pipeline_performance/history.md
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/cv_system/history.md
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/settings_system/history.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_provider_routing.py
related_features:
  - bounded_parallel_enrichment
  - pipeline_performance
  - cv_system
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_generation
---

# Implementation Plan: FitCV LLM runtime spine Phase 4 enrich and ranking migration

## Goal

Migrate `enrich_extraction` and `ranking_ai_score` onto the Phase 3 repo-native
runtime spine while preserving each stage's current semantic output and failure
policy:

`stage prompt -> LlmTaskRequest -> execute_llm_task -> stage parser -> structural validator -> existing stage output/failure policy`

Delete stage-local provider transport, routing, credential, payload, decoder, and
SDK-shaped shim ownership from `enrich.py` and `ai_score.py`. Make one proven
stage-neutral shared-runtime correction: empty adapter text reaches stage parsers.
Keep routing types and control-plane config unchanged, require routed model as
SSOT, and allow only operational failure message wording to normalize.

This plan is sequential. Enrich and ranking touch separate stage modules, but
both depend on the same test contract and final shared-runtime regression proof;
parallel execution would create avoidable fixture and closeout conflicts.

## Key Deliverables

### Deliverable 1: one runtime integration frame for enrich and ranking

`enrich.py` and `ai_score.py` each gain one private runtime helper using existing
`LlmTaskRequest`, `execute_llm_task`, stage parser, and structural validator
contracts. Public stage entrypoint signatures stay unchanged. Shared runtime
removes only its non-empty-response guard so permissive stage parsers own empty
response meaning.

### Deliverable 2: exact enrich semantics with normalized 429 retry

Enrichment preserves prompt, permissive structured-normalization/repair parsing,
merge, row shape, fingerprints, reuse, batching, ordering, callbacks,
persistence, fail-fast behavior, and exponential backoff. `_enrich_chunk`
retries only normalized adapter HTTP 429 failures after shared adapter fallback
is exhausted.

### Deliverable 3: exact ranking semantics with per-job isolation

Ranking preserves permissive score parsing, safe malformed-output defaults,
fit-label derivation, row shape, fingerprints, reuse, pacing, ordering,
persistence, and per-job runtime-exception skip records.

### Deliverable 4: local transport owners deleted

Both stage modules stop owning provider/model route resolution, credentials,
`httpx.Client`, wire endpoints, payloads, response decoding, `SimpleNamespace`
shims, and private client builders. Plain callable fake adapters replace
SDK-shaped transport tests.

### Deliverable 5: cross-stage symmetry proof and lifecycle closeout

Runtime, CV, pipeline, replay/resume, routing, enrich, and ranking tests prove
mechanics-only migration. Canonical docs and generated metadata describe one
runtime owner while leaving provenance/artifact convergence and legacy-label
removal to Phase 5.

## Task/Wave Breakdown

### Task 1: Freeze stage contracts with adapter-first tests

**Purpose:**
- lock current enrich and ranking meaning before deleting local transport code

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/llm_runtime.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_llm_runtime.py`
- Modify: `tests/test_runtime_routing.py`

**Preconditions:**
- Phase 3 spec, plan, and master entry are `completed` at commit `0ee85f44`
- Baseline stage/runtime suite passes with `124 passed, 1 skipped`
- Run unrestricted focused mypy on `enrich.py` and `ai_score.py`; record current
  52-error baseline by error code and message before production edits
- GitNexus is currently unavailable; retry freshness before implementation and
  continue source-first if still unavailable
- Before editing existing symbols, run required upstream GitNexus impact where
  indexed; warn and stop for user review on HIGH or CRITICAL risk

**Steps:**
- [x] Classify existing enrich/ranking tests into semantic-contract tests and
      deleted transport-owner tests.
- [x] Add plain callable fake adapters returning `LlmAdapterResponse` or raising
      `LlmAdapterError`/provider exceptions that shared runtime normalizes; remove
      dependency on `SimpleNamespace.models.generate_content` scaffolding.
- [x] Freeze enrich request fields, prompt, structured normalization, repair
      fallback, empty and non-object default merge, coercion warnings, canonical
      skill/mapping fields, row shape, fingerprints, reuse, callbacks, ordering,
      batching, and persistence.
- [x] Add failing shared-runtime proof that empty `raw_text` reaches parser.
- [x] Add failing routing proof that missing control-plane model is
      `routing_invalid`; do not add config fallback to `LlmTaskRequest`.
- [x] Move local ranking 404 transport proof to a stage-neutral
      `tests/test_llm_runtime.py` JSON-object fallback test; shared `/responses`
      404 fallback may succeed, while a 404 failure returned after fallback
      exhaustion remains a stage failure.
- [x] Freeze enrich operational boundary: remaining adapter HTTP 429 retries with
      current attempts/backoff; every other remaining failure propagates.
- [x] Freeze retry callback behavior: `job_start` once per attempt and `job_done`
      once after success.
- [x] Freeze ranking request fields, prompt, permissive parser outputs, score
      clamping, label derivation, arrays, reasoning, parser status, row shape,
      fingerprints, reuse, pacing, ordering, batching, and persistence.
- [x] Freeze ranking failure output as current per-job `runtime_exception` skip
      record while sibling jobs still complete; permit normalized operational
      failure message wording only.
- [x] Add failing integration tests for private enrich/ranking runtime helpers and
      exact request fields without changing public stage signatures.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_enrich.py tests/test_ai_score.py -q`
      passes before new helper expectations are enabled.
- [x] New helper tests fail only because private helper seams do not exist or
      stage entrypoints still use local clients.
- [x] Fixture comparisons exclude no stage row field; runtime provenance remains
      in-memory and outside Phase 4 output contracts.

**Exit Criteria:**
- exact stage behavior and allowed operational convergence are executable before
  production transport deletion begins

### Task 2: Pass empty adapter text to stage parsers

**Purpose:**
- fix the one proven stage-neutral runtime contract gap without adding API surface

**Files:**
- Modify: `src/fitcv/llm_runtime.py`
- Modify: `tests/test_llm_runtime.py`
- Verify: `tests/test_cv_generator.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 1 empty-response test fails with `adapter_contract_error`
- Run GitNexus upstream impact before editing `execute_llm_task` and
  `_openai_compatible_adapter`; warn before proceeding on HIGH or CRITICAL risk

**Steps:**
- [x] Remove only the non-empty `raw_text` rejection from `execute_llm_task`.
- [x] Remove only the default adapter's empty-text rejection.
- [x] Keep adapter return-type validation, parser/validator sequencing, failure
      taxonomy, provenance, and every public runtime contract unchanged.
- [x] Confirm empty text reaches injected and default-adapter parser paths.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py -q`
- [x] Empty text can become enrich defaults or ranking `malformed_json` through
      stage parsers instead of adapter failure.
- [x] CV direct/LangGraph tests remain green.

**Exit Criteria:**
- shared runtime delegates empty response meaning to stage parsers with no new
  abstraction or contract field

### Task 3: Migrate enrich parse and result seam

**Purpose:**
- make enrichment consume shared runtime without changing parser or row meaning

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`
- Verify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`

**Preconditions:**
- Task 1 enrich helper tests fail at expected missing integration seam
- Task 2 empty-response runtime proof passes
- Run GitNexus upstream impact before editing `_build_openai_compat_client`,
  enrich-local `_make_genai_client`, `enrich_job`, `_enrich_chunk`, and
  `parse_extraction_response`; warn and stop on HIGH or CRITICAL risk
- Existing Phase 3 request, result, parser, validator, adapter, and failure
  contracts are sufficient; do not change shared runtime API in this task

**Steps:**
- [x] Import only required Phase 3 runtime contracts into `enrich.py`.
- [x] Add private `_execute_enrich_runtime(..., adapter=None)` using
      `routing_part="enrich_extraction"`, current prompt,
      `response_mode="json_object"`, and no instructions/schema fields.
- [x] Keep parser order exact: decode one JSON value, try
      `_apply_structured_normalization` for objects, then call
      `parse_extraction_response` on JSON decode failure or `_ValidationError`.
- [x] Return current `parsed`/`errors`/`raw_response` mapping; accept warnings,
      empty parsed data, and repaired output as successful runtime values.
- [x] Add minimal structural validation for extraction-result container types;
      do not move enrichment business validation into shared runtime.
- [x] Update `enrich_job` to preserve warning logging and call
      `merge_scraped_and_enriched` exactly once on runtime success.
- [x] Preserve public signatures and external row fields; do not emit runtime
      provenance.

**Verification:**
- [x] Valid, fallback, malformed, coercion, canonical-skill,
      mapping-suggestion, and merge fixtures pass through fake adapters.
- [x] Request capture proves exact routing part and `json_object` mode.
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_enrich.py -q`

**Exit Criteria:**
- enrich parsing and success mapping use shared runtime with exact existing output

### Task 4: Preserve enrich retry and delete local transport

**Purpose:**
- retain enrich batch policy while removing its provider transport owner

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`
- Verify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/openai_compat.py`

**Preconditions:**
- Task 3 enrich success-path tests pass
- Required GitNexus impact for `_enrich_chunk`, `_build_openai_compat_client`,
  and enrich-local `_make_genai_client` has been reviewed
- Shared adapter owns one bounded `/responses` 404 fallback and normalized HTTP
  failure status

**Steps:**
- [x] Add one small `EnrichRuntimeError` or equivalent stage-local seam carrying
      `LlmRuntimeFailure` and rendering `failure.message`.
- [x] Map enrich runtime failure through that seam without recreating `httpx`
      exceptions or provider branches.
- [x] Update `_enrich_chunk` to retry only adapter-stage
      `adapter_http_error` with `http_status == 429` below current retry limit.
- [x] Preserve rate-slot acquisition before every attempt and backoff formula
      `sleep_secs * (2 ** (attempts - 1))`.
- [x] Preserve fail-fast behavior for every non-429 failure after shared adapter
      fallback exhaustion.
- [x] Delete `_build_openai_compat_client`, enrich-local `_make_genai_client`,
      `SimpleNamespace`, local `httpx.Client`, route/credential resolution,
      endpoint/payload/decoder code, and imports used only by those paths.
- [x] Replace client-shim tests with fake-adapter 429, post-fallback non-429,
      timeout, malformed-output, and batch-order tests; keep HTTP 404 fallback
      transport proof in `tests/test_llm_runtime.py`.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_enrich.py -q`
- [x] 429 fixtures prove attempts, sleep sequence, per-job isolation, rate-slot
      calls, and deterministic output order.
- [x] Post-fallback non-429 failures, including HTTP 404, propagate with unchanged
      message and fail fast; shared JSON-object 404 fallback passes in
      `tests/test_llm_runtime.py`.
- [x] `rg -n "def _build_openai_compat_client|def _make_genai_client|SimpleNamespace|httpx\.Client|/responses|/chat/completions|resolve_model_routing_part|resolve_openai_compatible_api_key" src/fitcv/enrich.py`
      returns no active match.

**Exit Criteria:**
- enrich uses one runtime transport owner with unchanged parser, row, retry,
  fail-fast, batching, ordering, callback, reuse, and persistence semantics

### Task 5: Migrate ranking and delete local transport

**Purpose:**
- make ranking consume shared runtime while preserving permissive scoring and
  per-job isolation

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `tests/test_ai_score.py`
- Verify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`

**Preconditions:**
- Task 1 ranking helper tests fail at expected missing integration seam
- Tasks 2-4 prove shared runtime can serve one migrated non-CV stage unchanged
- Run GitNexus upstream impact before editing ranking-local `_make_genai_client`,
  `score_job`, `run_ai_scoring`, and `parse_score_response`; warn and stop on
  HIGH or CRITICAL risk

**Steps:**
- [x] Import only required Phase 3 runtime contracts into `ai_score.py`.
- [x] Add private `_execute_ranking_runtime(..., adapter=None)` using
      `routing_part="ranking_ai_score"`, current prompt,
      `response_mode="json_object"`, and no instructions/schema fields.
- [x] Call `parse_score_response` with raw text and current config; keep malformed,
      non-object, and invalid-value fallback records as runtime successes.
- [x] Add minimal structural validation for normalized score-record keys/types;
      keep score, label, and parser policy stage-owned.
- [x] Update `score_job` to return current record and add `job_url` exactly once.
- [x] Map runtime failure to an exception rendering `failure.message` so current
      `_score_single` handling emits exact `runtime_exception` skip row.
- [x] Preserve public signatures, `top_n`, candidate summary, top-two evidence,
      thresholds, concurrency, submit pacing, sleep, ordering, fingerprints,
      reuse, and persistence.
- [x] Delete ranking-local `_make_genai_client`, `SimpleNamespace`, local
      `httpx.Client`, route/credential resolution, endpoint/payload/decoder code,
      and imports used only by those paths.
- [x] Replace client-shim tests with fake-adapter request, permissive parser,
      normalized failure, batch-isolation, and order tests.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_ai_score.py -q`
- [x] Valid, malformed, non-object, clamp, label, arrays, reasoning,
      parser-status, and job URL fixtures match exactly.
- [x] One adapter failure yields current skip row while sibling rows score in
      input order.
- [x] `rg -n "def _make_genai_client|SimpleNamespace|httpx\.Client|/responses|/chat/completions|resolve_model_routing_part|resolve_openai_compatible_api_key" src/fitcv/ai_score.py`
      returns no active match.

**Exit Criteria:**
- ranking uses one runtime transport owner with unchanged parser, row, failure
  isolation, batching, ordering, pacing, reuse, and persistence semantics

### Task 6: Prove cross-stage parity and bounded diff

**Purpose:**
- prove Phase 4 changed mechanics only and did not redesign shared runtime

**Files:**
- Verify: `src/fitcv/enrich.py`
- Verify: `src/fitcv/ai_score.py`
- Verify unchanged: `src/fitcv/llm_runtime.py`
- Verify unchanged: `src/fitcv/runtime_routing.py`
- Verify unchanged: `config/runtime/control_plane.yaml`
- Modify only when parity coverage is missing: `tests/test_pipeline.py`
- Modify only when parity coverage is missing: `tests/test_pipeline_stage_resume_parity.py`
- Verify: `tests/test_cv_generator.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_fitcv_cp/test_provider_routing.py`

**Preconditions:**
- Tasks 2-5 pass focused enrich and ranking suites
- No shared-runtime change exists unless a neutral failing test caused a prior
  spec amendment
- Unrestricted mypy baseline from Task 1 is available

**Steps:**
- [x] Compare frozen before/after enrich and ranking outputs exactly except
      normalized operational failure message wording.
- [x] Run CV direct/LangGraph suites to prove Phase 3 consumer unchanged.
- [x] Run pipeline and resume suites to prove entrypoints, replay, reuse,
      persistence, and deterministic ordering unchanged.
- [x] Run provider-routing tests to prove route/model/config SSOT unchanged.
- [x] Run unrestricted focused mypy again; confirm no new error code/message in
      modified runtime seams.
- [x] Inspect Git diff; production changes stay bounded to `enrich.py`,
      `ai_score.py`, and the two empty-text guards in `llm_runtime.py`.
- [x] Run transport and shared-runtime residue gates.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_enrich.py tests/test_ai_score.py -q`
- [x] `python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_provider_routing.py -q`
- [x] `python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py --follow-imports=skip --show-error-codes`
- [x] `python -m mypy src/fitcv/enrich.py src/fitcv/ai_score.py --follow-imports=skip --show-error-codes --disable-error-code=no-any-return --disable-error-code=list-item --disable-error-code=dict-item --disable-error-code=type-arg --disable-error-code=misc --disable-error-code=arg-type --disable-error-code=union-attr --disable-error-code=unused-ignore --disable-error-code=import-not-found`
- [x] `python -m compileall -q src/fitcv src/fitcv_cp`
- [x] Combined transport residue gate returns no active match.
- [x] `rg -n "enrich_extraction|ranking_ai_score" src/fitcv/llm_runtime.py`
      returns no active match.

**Exit Criteria:**
- enrich, ranking, and CV use one runtime spine; empty text reaches stage parsers,
  routed model stays control-plane-owned, and only operational failure wording may
  normalize

### Task 7: Synchronize docs and close Phase 4 lifecycle

**Purpose:**
- publish completed ownership accurately and hand off only Phase 5 scope

**Files:**
- Modify when stale: `docs/stages/enrich.source.yaml`
- Modify when stale: `docs/stages/ranking.source.yaml`
- Modify when stale: `docs/features/bounded_parallel_enrichment/feature.source.yaml`
- Modify when stale: `docs/features/pipeline_performance/feature.source.yaml`
- Modify when stale: `docs/features/cv_system/feature.source.yaml`
- Modify when stale: `docs/configuration.md`
- Modify when stale: `docs/pipeline.md`
- Modify when stale: `docs/architecture.md`
- Modify: `docs/superpowers/specs/2026-07-14-19-22-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-spec.md`
- Modify: `docs/superpowers/plans/2026-07-14-19-33-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-plan.md`
- Modify: `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- Generate: stage, feature, history, architecture, capability, and planning lineage
  outputs named in frontmatter

**Preconditions:**
- Task 6 verification passes
- Source docs, not generated contracts, own semantic wording changes
- Phase 5 stays limited to provenance/artifact convergence and legacy-label removal

**Steps:**
- [x] Update only stale source docs to state enrich, ranking, and CV share runtime
      mechanics while each stage keeps semantic output and failure policy.
- [x] Keep route ownership in `control_plane.yaml` plus `runtime_routing.py`; do
      not duplicate route tables in docs or stage code.
- [x] Record Phase 5 handoff for provenance projection, failure/artifact and
      observation/debug convergence, and legacy-label deletion.
- [x] Regenerate architecture metadata and planning lineage from canonical sources.
- [x] Mark Phase 4 spec, plan, and master entry `completed` only after all proof
      passes.
- [x] Run GitNexus `detect_changes` before commit when graph becomes available;
      if unavailable, record source/test/doc verification as authority.

**Verification:**
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] `python scripts/validate_repo_contracts.py --fast`
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `git diff --check`
- [x] Generated files match canonical sources; no generated semantic surface is
      hand-edited.

**Exit Criteria:**
- Phase 4 is implemented, verified, documented, lifecycle-complete, and ready for
  Phase 5 spec drafting without reopening enrich/ranking migration

## Verification

Run after all tasks:

```powershell
python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_enrich.py tests/test_ai_score.py -q
python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_fitcv_cp/test_provider_routing.py -q
python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py --follow-imports=skip --show-error-codes
python -m mypy src/fitcv/enrich.py src/fitcv/ai_score.py --follow-imports=skip --show-error-codes --disable-error-code=no-any-return --disable-error-code=list-item --disable-error-code=dict-item --disable-error-code=type-arg --disable-error-code=misc --disable-error-code=arg-type --disable-error-code=union-attr --disable-error-code=unused-ignore --disable-error-code=import-not-found
python -m compileall -q src/fitcv src/fitcv_cp
python tools/docs/generate_architecture_metadata.py --check
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
python scripts/hooks/run_validator.py --fast
git diff --check
```

Before/after typing evidence:

```powershell
python -m mypy src/fitcv/enrich.py src/fitcv/ai_score.py --follow-imports=skip --show-error-codes
```

Unrestricted command currently reports 52 existing errors. Phase 4 may remove
errors with deleted transport code but must add no new error code/message in
modified runtime seams.

Residue gates:

```powershell
rg -n "def _build_openai_compat_client|def _make_genai_client|SimpleNamespace|httpx\.Client|/responses|/chat/completions|resolve_model_routing_part|resolve_openai_compatible_api_key" src/fitcv/enrich.py src/fitcv/ai_score.py
rg -n "enrich_extraction|ranking_ai_score" src/fitcv/llm_runtime.py
```

Expected residue result: no active match. Routing-part names remain in
stage-built requests and `control_plane.yaml`, not shared-runtime branches.

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

This plan has no child plans. Enrich and ranking use Phase 3 runtime without
shared-runtime redesign; local transport owners are deleted; exact-output except normalized failure text,
retry/fail-fast, per-job isolation, CV, pipeline, resume, routing, residue,
typing, compile, docs, and lifecycle proof pass; Phase 4 entries are `completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-19-22-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-spec.md`
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `config/runtime/control_plane.yaml`
- `src/fitcv/llm_runtime.py`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/enrich.py`
- `src/fitcv/ai_score.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
