---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-implementation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-20-40-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-spec.md
targets:
  - src/fitcv/llm_runtime.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - docs/stages/enrich.source.yaml
  - docs/stages/enrich.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
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
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/inspection_debugging/history.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/settings_system/history.md
  - docs/configuration.md
  - docs/api.md
  - docs/observability.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_llm_runtime.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
related_features:
  - bounded_parallel_enrichment
  - pipeline_performance
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# Implementation Plan: FitCV LLM runtime spine Phase 5 observability, parity, and closeout

## Goal

Close the five-phase LLM-runtime-spine remediation by projecting existing
`LlmRuntimeResult` truth through one persisted evidence shape, carrying it
through existing stage diagnostics, replacing late-stage mode-owned trace names
with stage-neutral names, preserving historical reads, and locking adapter
parity.

Do not change stage business semantics. Do not add a registry, service, event
bus, middleware layer, or replacement mode toggle. Reuse existing runtime
dataclasses, job callbacks, stage-artifact builders, debug payloads, control-plane
artifact registry, and documentation generators.

Execution is sequential. Each task deletes or reuses current owners needed by
the next task; parallel edits would conflict in pipeline, trace, and fixture
surfaces.

## Key Deliverables

### Deliverable 1: canonical runtime evidence

`llm_runtime.py` exposes one pure `LlmRuntimeResult` projection containing only
canonical status, provenance, and failure fields. Existing stage observations
wrap it with stable item and outer-invocation identity. Tests prove runtime
invariants, deterministic sampling, null handling, and secret exclusion.

### Deliverable 2: routed-stage evidence without business-row changes

Enrich, ranking, and CV generation emit one evidence block per actual runtime
call through existing callbacks/debug surfaces. Stage artifacts expose bounded
shared summaries. Reuse, replay, resume, and gated cases emit zero new calls.

### Deliverable 3: honest stage-neutral late-stage traces

CV analysis stops fabricating LLM provenance. CV-generation traces use
`cv_generation_trace`, `stage_execution_trace_*`, and
`cv-generation-trace.json`. Applicability follows stage reach and artifact
presence, not mode labels.

### Deliverable 4: one-way compatibility and dead-label deletion

Historical readers translate old persisted `agentic_live_trace` payloads.
Current pipeline, worker, mirror, bundle, API, settings, and UI writes omit
late-stage mode fields. The ignored `cv.agentic_late_stage.enabled` setting is
removed without a replacement toggle.

### Deliverable 5: parity and master closeout proof

Default, fake, direct, and LangGraph adapters match on adapter-invariant fields
where admissible. Full regression, typing, compile, generated-doc, lifecycle,
residue, and GitNexus change-scope checks pass before Phase 5 and master status
move to `completed`.

## Task/Wave Breakdown

### Task 1: freeze baseline, consumers, and blast radius

**Purpose:**
- establish exact current-write, historical-read, adapter, and test boundaries
  before changing shared symbols

**Files:**
- Inspect: `src/fitcv/llm_runtime.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_run_support.py`
- Inspect: `tests/test_llm_runtime.py`
- Inspect: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `docs/superpowers/specs/2026-07-14-20-40-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-spec.md`

**Preconditions:**
- Phase 4 spec and implementation plan are `completed`
- Phase 5 detailed spec is `active`
- working tree contains only Phase 5 planning artifacts before implementation

**Steps:**
- [x] Step 1: Run `./scripts/get_gitnexus_freshness.ps1`; refresh with
      `npx gitnexus analyze` when stale before high-trust impact work.
- [x] Step 2: Before editing each existing function, class, or method, run
      upstream impact analysis with `file_path` disambiguation. Cover runtime
      owners, stage adapters, callbacks, artifact builders, trace loaders,
      route handlers, worker/mirror projections, settings load/schema functions,
      and every helper deleted or renamed. Report HIGH or CRITICAL results
      before edits.
- [x] Step 3: Run API impact and route-map analysis before changing either trace
      download route. Record current middleware, consumers, and response shape.
- [x] Step 4: Record exact current matches for scoped legacy labels and classify
      each as current write, historical read, test fixture, or unrelated agentic
      feature.
- [x] Step 5: Run focused baseline tests for runtime, routed stages, late-stage
      traces, replay/resume, control-plane artifacts, and settings.
- [x] Step 6: Freeze historical fixture shapes for `agentic_live_trace`,
      `agentic_step_trace_*`, and `late_stage_mode` reads.
- [x] Step 7: Record unrestricted focused mypy output for every noisy Python
      module that will change; later verification permits no new diagnostic.

**Verification:**
- [x] GitNexus impact report covers every shared symbol before modification.
- [x] Baseline focused tests pass or any pre-existing failure is recorded without
      being folded into Phase 5.
- [x] Residue inventory excludes unrelated synonym/review/automation features.

**Exit Criteria:**
- every implementation edit has a known owner, consumer set, and proof target

### Task 2: add canonical runtime-evidence projection

**Purpose:**
- serialize existing runtime truth once without adding another runtime contract

**Files:**
- Modify: `src/fitcv/llm_runtime.py`
- Modify: `tests/test_llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`

**Preconditions:**
- Task 1 complete
- `LlmRuntimeResult`, `LlmRuntimeFailure`, and `LlmRuntimeProvenance` field sets
  remain Phase 3 authority

**Steps:**
- [x] Step 1: Add failing tests for successful evidence, each failure stage,
      null IDs, attempt count, and forbidden secret/provider-payload fields.
- [x] Step 2: Add one version constant and one pure
      `build_llm_runtime_evidence(result)` helper using existing dataclass fields
      and stdlib serialization.
- [x] Step 3: Keep validation details, adapter response, raw text, provider
      payload, route base URL, headers, and credentials outside persisted evidence.
- [x] Step 4: Keep invariant ownership in runtime construction/tests. Projector
      selects explicit safe fields only and never raises a second semantic
      validation error.
- [x] Step 5: Export only the helper needed by stage consumers; add no generic
      serializer registry or evidence class hierarchy.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py -q`
- [x] `python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py`
- [x] Secret sentinel values do not appear in serialized test output.

**Exit Criteria:**
- one tested helper owns every persisted per-call runtime evidence block

### Task 3: carry evidence through enrich and ranking

**Purpose:**
- reuse current batch callbacks and stage-artifact builders to expose runtime
  evidence without adding fields to enriched or ranked rows

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Task 2 complete
- public enrich/ranking row contracts, fingerprints, ordering, retry, and failure
  policies are frozen by Phase 4 tests

**Steps:**
- [x] Step 1: Add failing tests proving one success/failure evidence event per
      actual enrich or ranking call, zero events for reused rows, and unchanged
      business rows.
- [x] Step 2: Reuse `_execute_enrich_runtime` and `_execute_ranking_runtime` as
      result owners; add only the minimum private result-to-row seam needed to
      let batch code observe evidence while keeping `enrich_job` and `score_job`
      return contracts unchanged.
- [x] Step 3: Extend existing enrich job events with one observation per
      `execute_llm_task` result before outer 429 retry or terminal failure
      mapping; keep start/done timing events and retry policy unchanged.
- [x] Step 4: Add one optional ranking batch job-event callback matching the
      existing enrich event pattern; emit canonical evidence before ranking maps
      failures to current `runtime_exception` skip rows.
- [x] Step 5: Collect enrich/ranking observations in pipeline-local sidecar
      lists. Use existing stable job identity plus `input_index` and
      `invocation_index`; never store evidence in business rows or fingerprints.
- [x] Step 6: Add one shared private stage-artifact summary builder in
      `pipeline_stage_artifacts.py` and use it for both stages with existing
      truncation/sample bounds. Sort stable observation identity before
      truncation so concurrency cannot change sample contents.
- [x] Step 7: Pass summary inputs through `_build_stage_transition_artifacts`
      without changing stage participation, replay, resume, or persistence truth.

**Verification:**
- [x] `python -m pytest tests/test_enrich.py tests/test_ai_score.py -q`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] Exact output fixtures contain no new business-row keys.
- [x] Enrich 429 retries and ranking per-job isolation retain current call counts
      and ordering.

**Exit Criteria:**
- enrich and ranking artifacts use one runtime-summary shape while business
  outputs remain byte-for-byte compatible where fixtures require it

### Task 4: converge CV runtime evidence and stage traces

**Purpose:**
- use canonical evidence for CV-generation initial/repair calls and remove fake
  LLM provenance from CV analysis

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_observability.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Tasks 2 and 3 complete
- canonical `CvAnalysisRecord` and `CvGenerationResult` semantic fields remain
  Phase 1/2 authority

**Steps:**
- [x] Step 1: Add failing direct/LangGraph/fake fixtures proving canonical
      evidence for initial and repair invocations and zero evidence for gated,
      reused, replayed, or already-completed work.
- [x] Step 2: Replace direct `asdict(result.provenance)` projections in
      `cv_generator.py` and LangGraph writer code with
      `build_llm_runtime_evidence(result)`.
- [x] Step 3: Preserve ordered per-call evidence across initial generation and
      repair; do not overwrite initial evidence with final-attempt provenance.
- [x] Step 4: Delete `_normalize_runtime_provenance` and
      `_build_live_trace_runtime_provenance`; add prompt/template/schema details
      only as separate stage-trace metadata, not canonical runtime provenance.
- [x] Step 5: Remove `_build_runtime_provenance` and fallback synthetic provider
      fields from `agentic_cv_analysis.py` and pipeline historical analysis trace
      construction.
- [x] Step 6: Rename newly written trace schemas/family to
      `stage_execution_trace_record_v1`, `stage_execution_trace_run_v1`, and
      `stage_execution_trace`; keep stage-specific input/output/validation/repair
      summaries.
- [x] Step 7: Rename `_build_agentic_live_trace_summary` to
      `_build_cv_generation_trace_summary` with GitNexus-aware rename tooling,
      then emit `cv_generation_trace` and canonical runtime summaries.
- [x] Step 8: Update CV-analysis and CV-generation item observations/stage
      artifacts to project existing semantic records plus canonical runtime
      evidence only where a real call occurred.

**Verification:**
- [x] `python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] Direct/LangGraph/fake semantic outputs match after only the spec-approved
      operational fields are normalized.
- [x] CV-analysis fixtures contain no `fitcv_builtin`,
      `fitcv_agentic_cv_analysis_builtin`, or `mode_source` runtime provenance.
- [x] Initial plus repair cases retain two ordered evidence blocks.

**Exit Criteria:**
- CV stages use honest stage-neutral traces and the same runtime evidence owner as
  enrich/ranking

### Task 5: replace current mode labels and preserve historical reads

**Purpose:**
- make control-plane, worker, mirror, bundle, settings, and download surfaces
  write canonical stage truth while translating old stored payloads once

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_contracts.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_run_support.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `docs/api.md`
- Modify: `docs/observability.md`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`

**Preconditions:**
- Task 4 complete
- canonical current-write key is `cv_generation_trace`
- historical fixtures from Task 1 are frozen

**Steps:**
- [x] Step 1: Add failing tests for canonical artifact registry names, canonical
      route, mode-free applicability, historical old-key translation, and stale
      persisted setting pruning.
- [x] Step 2: Replace control-plane artifact
      `agentic-live-trace.json` with `cv-generation-trace.json`, label it “CV
      Generation Trace JSON”, and expose the canonical download route.
- [x] Step 3: Centralize one historical read helper that accepts
      `cv_generation_trace` first and otherwise exposes `agentic_live_trace`
      under the canonical key. Preserve nested historical schema/family values.
- [x] Step 4: Keep the old GET route as a thin read-only alias to the canonical
      loader and response builder. Remove old UI links and current artifact
      writes; add no second loader or payload semantics.
- [x] Step 5: Delete pipeline/control-plane/worker late-stage mode payload
      builders and remove `late_stage_mode`, `agentic_late_stage_enabled`,
      `agentic_status`, and `mode_source` from all current writes and bundle
      manifests.
- [x] Step 6: Change `_artifact_applicability_state` trace handling to stage
      reach plus canonical/historical trace presence; never consult a mode field.
- [x] Step 7: Rename current trigger payload
      `agentic_runtime_expectation` to `cv_generation_runtime_expectation` where
      it represents the canonical generation adapter expectation.
- [x] Step 8: Remove `cv.agentic_late_stage.enabled` from settings schema, IA,
      forms, labels, and active-setting tests; prove the existing loader prunes
      the stale row without adding a replacement toggle.
- [x] Step 9: Update worker terminal payloads and artifact mirror to write only
      canonical trace keys and filenames.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- [x] New-run fixtures contain no scoped mode-owned fields or filenames.
- [x] Historical fixtures remain downloadable from the canonical route.
- [x] Synonym/review/automation agentic settings and artifacts remain unchanged.

**Exit Criteria:**
- current writes are stage-neutral; compatibility is read-only and single-owner

### Task 6: lock parity, synchronize docs, and close master

**Purpose:**
- prove all admissible cases, update owning documentation, and close Phase 5
  without creating another remediation phase

**Files:**
- Modify: `tests/test_llm_runtime.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `docs/stages/enrich.source.yaml`
- Modify: `docs/stages/ranking.source.yaml`
- Modify: `docs/stages/cv_analysis.source.yaml`
- Modify: `docs/stages/cv_generation.source.yaml`
- Modify: `docs/features/bounded_parallel_enrichment/feature.source.yaml`
- Modify: `docs/features/pipeline_performance/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/features/settings_system/feature.source.yaml`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/architecture.md`
- Generate: `docs/stages/enrich.yaml`
- Generate: `docs/stages/ranking.yaml`
- Generate: `docs/stages/cv_analysis.yaml`
- Generate: `docs/stages/cv_generation.yaml`
- Generate: `docs/features/bounded_parallel_enrichment/bounded_parallel_enrichment.yaml`
- Generate: `docs/features/bounded_parallel_enrichment/lineage.generated.yaml`
- Generate: `docs/features/bounded_parallel_enrichment/history.md`
- Generate: `docs/features/pipeline_performance/pipeline_performance.yaml`
- Generate: `docs/features/pipeline_performance/lineage.generated.yaml`
- Generate: `docs/features/pipeline_performance/history.md`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/features/cv_system/history.md`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Generate: `docs/features/inspection_debugging/history.md`
- Generate: `docs/features/settings_system/settings_system.yaml`
- Generate: `docs/features/settings_system/lineage.generated.yaml`
- Generate: `docs/features/settings_system/history.md`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`
- Modify: `docs/superpowers/specs/2026-07-14-20-40-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-spec.md`
- Modify: `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- Modify: `docs/superpowers/plans/2026-07-14-20-54-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-plan.md`

**Preconditions:**
- Tasks 1 through 5 complete
- no stage semantic or business-row change remains unexplained

**Steps:**
- [x] Step 1: Complete parity matrices for shared runtime default/fake, enrich
      default/fake, ranking default/fake, and CV-generation direct/LangGraph/fake
      adapters.
- [x] Step 2: Normalize only approved operational fields and assert exact runtime
      taxonomy, parsed value, stage status, validation, repair, reuse, and
      artifact equality.
- [x] Step 3: Add zero-call proof for reranker block, fit-gate skip, exact reuse,
      replay, and resume; assert no duplicate evidence.
- [x] Step 4: Add exact residue tests for scoped legacy builders, output keys,
      schemas, filenames, UI labels, and settings while excluding unrelated
      agentic features.
- [x] Step 5: Update human-owned stage and feature source docs plus cross-cutting
      docs to describe one runtime evidence owner, stage-neutral traces, and
      adapter-only LangGraph.
- [x] Step 6: Run architecture metadata and planning-lineage generators; never
      hand-edit generated stage, feature, history, or discovery files.
- [x] Step 7: Run full regression, focused mypy, compile, lifecycle, repo
      contracts, hook validator, residue, and diff checks.
- [x] Step 8: Run `gitnexus_detect_changes()` and inspect affected flows before
      commit; investigate any unexpected stage-semantic or unrelated feature
      impact.
- [x] Step 9: After every gate passes, mark this plan and Phase 5 spec
      `completed`, mark master Phase 5 entry `completed`, mark master spec
      `completed`, regenerate planning lineage, and rerun lifecycle validation.

**Verification:**
- [x] Full command set in top-level Verification passes from clean process state.
- [x] All five master child specs/plans are terminal.
- [x] Generated files contain only generator-produced changes.
- [x] GitNexus change scope matches runtime evidence, traces, settings cleanup,
      tests, and managed docs only.

**Exit Criteria:**
- Phase 5 and master are completed with no hidden sixth phase or remaining
  current-write semantic-mode owner

## Verification

```powershell
python -m pytest tests/test_llm_runtime.py tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q
python -m pytest -q
python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py src/fitcv/pipeline_stage_artifacts.py --follow-imports=skip --show-error-codes
python -m mypy src/fitcv/enrich.py src/fitcv/ai_score.py --follow-imports=skip --show-error-codes --disable-error-code=no-any-return --disable-error-code=list-item --disable-error-code=dict-item --disable-error-code=type-arg --disable-error-code=misc --disable-error-code=arg-type --disable-error-code=union-attr --disable-error-code=unused-ignore --disable-error-code=import-not-found
python -m compileall -q src tests
python tools/docs/generate_architecture_metadata.py
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
python scripts/hooks/run_validator.py --fast
git diff --check
```

```powershell
rg -n "late_stage_mode|agentic_late_stage_enabled|agentic_runtime_expectation|agentic_live_trace|agentic-live-trace|agentic_step_trace" src/fitcv src/fitcv_cp tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py
rg -n "cv\.agentic_late_stage\.enabled|Agentic Late Stage Enabled|non-agentic path" src/fitcv src/fitcv_cp docs/configuration.md docs/pipeline.md tests/test_fitcv_cp
rg -n "def _normalize_runtime_provenance|route_part" src/fitcv/cv_generator.py src/fitcv/agentic_cv_generation.py src/fitcv/agentic_cv_analysis.py
```

Expected residue:

- scoped legacy literals remain only in one bounded historical read helper and
  its fixtures
- no current writer, semantic branch, artifact registry row, UI label, or
  settings-schema entry remains
- no stage-local canonical provenance normalizer remains
- unrelated agentic synonym/review/automation surfaces remain present

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

This plan is `completed`. All tasks, proof commands, residue gates, generated-doc refreshes, audit evidence, full regression (`1931 passed, 3 skipped`), focused Phase 5 regression (`1111 passed, 1 skipped`), GitNexus change-scope review, and lifecycle status updates pass.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-20-40-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-spec.md`
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `src/fitcv/llm_runtime.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/pipeline_stage_artifacts.py`
- `src/fitcv_cp/app.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
