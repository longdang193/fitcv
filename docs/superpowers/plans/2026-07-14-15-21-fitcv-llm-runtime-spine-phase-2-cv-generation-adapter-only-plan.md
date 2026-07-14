---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-llm-runtime-spine-phase-2-cv-generation-adapter-only-implementation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/tracker.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - config/runtime/control_plane.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/cv_system/history.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/settings_system/history.md
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/trigger_run_management/trigger_run_management.yaml
  - docs/features/trigger_run_management/lineage.generated.yaml
  - docs/features/trigger_run_management/history.md
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/inspection_debugging/history.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline_status_registry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - settings_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# Implementation Plan: FitCV LLM runtime spine Phase 2 CV-generation adapter-only LangGraph

## Goal

Make `fitcv.agentic_cv_generation.generate_from_analysis` sole per-job
CV-generation business entrypoint. Phase 1 `CvAnalysisRecord` remains sole
input authority. LangGraph becomes private provider/orchestration adapter, not
second owner of prompt meaning, reuse, validation, repair, acceptance, status,
persistence semantics, or artifact shape.

Pipeline keeps scheduling, cancellation, reuse-candidate lookup, persistence,
reporting, observations, and stage boundaries. It stops owning built-in versus
agentic generation methods and stops reconstructing generation results.

## Key Deliverables

### Deliverable 1: complete canonical generation contract

`generate_from_analysis` handles analysis passthrough, exact reuse, fresh
writer execution, structured normalization, render, validation, bounded repair,
acceptance, review-required, validation failure, and generation failure.
`CvGenerationResult` contains complete identity, fingerprint, reuse, decision,
validation, repair, artifact, error, and provenance fields without pipeline
hydration.

### Deliverable 2: private adapter-only LangGraph runtime

Canonical repo code builds prompt/schema/routing requests and interprets adapter
responses. LangGraph owns provider setup, graph/tool sequencing, transport
retries, and trace capture only. Direct provider execution remains as supported contract-equivalent adapter for
built-in/offline routing. Phase 2 deletes duplicate semantics, not this transport.

### Deliverable 3: one pipeline generation path

Pipeline calls canonical generator once per ready analysis record, persists only
accepted or review-required results, and uses canonical persistence-failure
transition on storage error. Mode labels remain observational and do not select
semantic behavior or enter fingerprints.

### Deliverable 4: executable symmetry proof and synchronized docs

Focused contract, adapter parity, reuse, replay/resume, pipeline, worker, and
control-plane tests prove one result shape across all admissible cases. Stage,
feature, configuration, pipeline, and architecture docs change only where owner
wording or generated references become stale.

## Task/Wave Breakdown

### Task 1: Lock proof matrix with failing contract tests

**Purpose:**
- define canonical behavior before moving or deleting runtime branches

**Files:**
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/late_stage_contract.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_cv_generation_reason_mapping.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Phase 2 detailed spec has `status: active`
- Phase 1 canonical `CvAnalysisRecord` tests pass
- current generation-focused tests pass before new assertions are added
- reviewed spec and plan changes are committed or otherwise checkpointed before code edits begin

**Steps:**
- [x] Add direct `generate_from_analysis` fixtures for reranker block, fit-gate
      skip, analysis failure, valid fresh generation, review-required,
      validation failure, and generation failure.
- [x] Add canonical result-field assertions for identity, generation fingerprint
      components, reuse decision, validation snapshots, repair attempt, final
      artifacts, error/outcome separation, and normalized runtime provenance.
- [x] Add exact-reuse fixtures for valid, stale, incomplete, mismatched-contract,
      prompt-changed, policy-changed, route-changed, and validation-rejected
      candidates.
- [x] Add deterministic direct-versus-LangGraph adapter parity fixture that
      normalizes only allowed telemetry fields.
- [x] Add mode-toggle fixture proving `agentic_late_stage_enabled` and
      `late_stage_mode` do not change fingerprint or semantic output.
- [x] Add review-required fixtures proving canonical reason code and validation
      evidence fingerprint are emitted while accepted-version persistence is skipped.
- [x] Add persistence-transition fixture proving final artifacts survive
      `persistence_failed`.
- [x] Add replay/resume fixture proving canonical result needs no pipeline
      semantic hydration.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_status_registry.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] new assertions fail only where Phase 2 contract is not implemented

**Exit Criteria:**
- proof matrix is executable and distinguishes semantic invariants from allowed
  provider/trace differences

### Task 2: Complete canonical result, fingerprint, reuse, and status ownership

**Purpose:**
- make one generator entrypoint and one result builder express every outcome

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/late_stage_contract.py`
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/tracker.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_pipeline_status_registry.py`

**Preconditions:**
- Task 1 proof-matrix tests exist
- Phase 1 `CvAnalysisRecord` field and status contract is unchanged

**Steps:**
- [x] Expand canonical result-status type to cover analysis passthrough plus
      `accepted`, `review_required`, `validation_failed`,
      `generation_failed`, and `persistence_failed` from one status owner.
- [x] Complete `CvGenerationResult` identity, fingerprint, reuse, validation,
      repair, final-artifact, review-reason, validation-evidence, error, and provenance fields.
- [x] Collapse `_build_result` and `_build_generation_result_payload` to one
      canonical builder; delete the redundant wrapper unless a distinct contract
      need exists.
- [x] Move `_build_cv_generation_input_fingerprint` from pipeline into canonical
      generation module as an exported pure helper and bump schema version.
- [x] Remove mutable job URL, mode labels, run data, and trace settings from
      semantic fingerprint; include current analysis, prompt/template, enabled
      sections, validation/acceptance policy, route contract, and schema version.
- [x] Add optional `reusable_record` input. Validate fingerprint, contract,
      reusable status, completeness, and current validation before rebinding.
- [x] Make rejected reuse fall through to fresh generation in same invocation.
- [x] Make non-ready analysis records use same result builder with no runtime,
      validation, repair, or generated artifacts.
- [x] Add canonical persistence-failure transition preserving final artifacts and
      prior validation while setting persistence-stage error.
- [x] Normalize runtime provenance to required route, adapter, provider, model,
      and wire fields without credentials.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_status_registry.py -q`
- [x] `python -m pytest tests/test_cv_generation_reason_mapping.py -q`
- [x] direct generator fixtures pass without importing pipeline builders

**Exit Criteria:**
- generator returns complete canonical records for every proof-matrix status and
  pipeline owns no missing-field hydration requirement

### Task 3: Put LangGraph behind one private writer seam

**Purpose:**
- preserve runtime orchestration while removing graph-owned business meaning

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify if needed: `src/fitcv/cv_generator.py`
- Modify if needed: `src/fitcv/runtime_routing.py`
- Modify only if routed truth changes: `config/runtime/control_plane.yaml`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify if prompt/schema proof changes: `tests/test_cv_generator.py`

**Preconditions:**
- Task 2 owns canonical request/result, fingerprint, statuses, and reuse
- existing prompt, schema, normalization, render, and routing helpers are reused

**Steps:**
- [x] Build canonical prompt, response schema, resolved routing snapshot, attempt
      kind, and repair targets before adapter invocation.
- [x] Introduce one private callable writer seam in existing generation module;
      add no public interface, factory, registry, service, or base class.
- [x] Make LangGraph adapter consume resolved request and return raw response,
      provenance, optional trace, and transport telemetry only.
- [x] Move response parsing, structured normalization, markdown rendering,
      validation, repair decision, repair limit, acceptance/review decision,
      statuses, and result assembly outside LangGraph-specific branch.
- [x] Reuse same adapter call for initial and repair attempts; semantic repair
      targets remain canonical inputs.
- [x] Retain direct writer as supported built-in/offline adapter; make it consume
      same request and return same response as LangGraph.
- [x] Keep LangGraph environment variables as transport compatibility values and
      assert they cannot override routed semantic truth.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py -q`
- [x] `python -m pytest tests/test_cv_generator.py -q`
- [x] deterministic adapter parity differs only in adapter/provider/trace/latency
      fields allowed by spec

**Exit Criteria:**
- replacing LangGraph changes runtime mechanics only; canonical result semantics
  remain unchanged

### Task 4: Collapse pipeline onto canonical generator and persistence transition

**Purpose:**
- delete second generation method and leave orchestration only

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify if projection signatures change: `src/fitcv/pipeline_observability.py`
- Modify if projection signatures change: `src/fitcv/pipeline_stage_artifacts.py`
- Modify if projection signatures change: `src/fitcv/pipeline_stages/common.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Tasks 2-3 pass direct generator and adapter parity tests
- canonical generator accepts optional reuse candidate and emits complete result

**Steps:**
- [x] Delete pipeline-local `_build_cv_generation_input_fingerprint`.
- [x] Delete `_run_non_agentic_cv_generation` and
      `_run_agentic_cv_generation`.
- [x] Delete non-agentic-only routing preflight and decision-critical branches on
      `agentic_late_stage_enabled` or `late_stage_mode`.
- [x] Keep batch scheduling, configured/effective concurrency, cancellation,
      canonical fingerprint-helper calls, candidate lookup, accepted-only
      persistence, reporter emission, observations, and stage
      boundaries.
- [x] Build batch lookup keys with canonical exported fingerprint helper, then
      pass canonical analysis record plus optional located reuse candidate to
      `generate_from_analysis`; consume returned record directly.
- [x] Persist only `accepted` canonical results; keep `review_required` artifacts
      observable but outside accepted-version storage.
- [x] On storage failure, use canonical persistence-failure transition; delete
      pipeline-local status/result construction.
- [x] Remove pipeline and stage-runner imports used only for generation parsing,
      validation, repair, acceptance, or semantic result assembly.
- [x] Make debug records, events, and stage artifacts projections of complete
      `CvGenerationResult` plus run context.
- [x] Add residue assertions for deleted helpers, local fingerprint owner, mode
      semantic branches, and local status hydration.

**Verification:**
- [x] `rg -n "_build_cv_generation_input_fingerprint|_run_non_agentic_cv_generation|_run_agentic_cv_generation|agentic_late_stage_enabled|late_stage_mode|run_all_validations|evaluate_cv_acceptance_policy" src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py`
- [x] residue command returns no active semantic-owner matches
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] `python -m pytest tests/test_pipeline.py -q`

**Exit Criteria:**
- pipeline has one CV-generation call path and cannot select or reconstruct second
  generation method

### Task 5: Verify projections and synchronize owned documentation

**Purpose:**
- prove one result contract across runtime consumers and refresh only affected docs

**Files:**
- Verify/modify: `src/fitcv_cp/worker_job.py`
- Verify/modify: `src/fitcv_cp/worker_run_support.py`
- Verify/modify: `src/fitcv_cp/app.py`
- Modify if stale: `docs/stages/cv_generation.source.yaml`
- Generated if source changed: `docs/stages/cv_generation.yaml`
- Modify if capability ownership changes: `docs/features/cv_system/feature.source.yaml`
- Modify if capability ownership changes: `docs/features/settings_system/feature.source.yaml`
- Modify if capability ownership changes: `docs/features/trigger_run_management/feature.source.yaml`
- Modify if capability ownership changes: `docs/features/inspection_debugging/feature.source.yaml`
- Generated from changed feature sources: corresponding feature YAML, lineage,
  and generated history blocks
- Modify if stale: `docs/configuration.md`
- Modify if stale: `docs/pipeline.md`
- Modify if stale: `docs/architecture.md`
- Generated if metadata changes: `docs/generated/architecture_dag.yaml`
- Generated if metadata changes: `docs/generated/capability_lineage.yaml`
- Generated after plan/spec lifecycle change: `docs/generated/planning_lineage.yaml`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 pass focused generator and pipeline tests

**Steps:**
- [x] Update worker/control-plane fixtures to canonical result shape; add no
      production compatibility hydration.
- [x] Verify stage timelines, reason mapping, reuse metrics, review counts,
      persistence failures, and pipeline outcomes consume canonical fields.
- [x] Verify replay and resume use same result contract as fresh execution.
- [x] Inspect stage, feature, configuration, pipeline, and architecture docs; edit
      only wording that still names built-in/agentic path or LangGraph as semantic
      owner.
- [x] If stage or feature source changes, run architecture metadata generator and
      include generated outputs; never edit generated YAML directly.
- [x] Regenerate planning lineage after plan creation and lifecycle changes.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "cv_generation or late_stage or pipeline_outcome" -q`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- direct, pipeline, worker, control-plane, replay, and resume paths consume one
  canonical generation result; owned docs and generated surfaces are synchronized

## Verification

Run after all tasks:

```powershell
python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_status_registry.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_pipeline.py -q
python -m pytest tests/test_fitcv_cp/test_worker_job.py -q
python -m pytest tests/test_fitcv_cp/test_app.py -k "cv_generation or late_stage or pipeline_outcome" -q
rg -n "def _build_cv_generation_input_fingerprint|_run_non_agentic_cv_generation|_run_agentic_cv_generation|if agentic_late_stage_enabled|if not agentic_late_stage_enabled" src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
python -m compileall -q src/fitcv src/fitcv_cp
git diff --check
```

Expected residue result: no active semantic-owner matches. Compatibility payload
labels may remain only when tests prove they are observational and cannot select
runtime meaning or change fingerprints.

Use focused mypy only for touched canonical modules if repo-wide mypy remains
blocked by unrelated existing errors:

```powershell
python -m mypy src/fitcv/agentic_cv_generation.py src/fitcv/runtime_routing.py src/fitcv/late_stage_contract.py
```

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

This plan has no child plans. Complete it only when focused and full pipeline
verification pass, residue is empty, canonical docs are synchronized, generated
metadata checks pass, and Phase 2 spec can move to `status: completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md`
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/stages/cv_generation.source.yaml`
- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv/late_stage_contract.py`
- `src/fitcv/runtime_routing.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
