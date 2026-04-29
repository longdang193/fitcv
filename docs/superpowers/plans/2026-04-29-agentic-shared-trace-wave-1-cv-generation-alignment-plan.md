---
layer: change
artifact_type: plan
status: proposed
parent_workstream: none
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
parent_spec: docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_generation
---

# Agentic Shared Trace Wave 1 CV Generation Alignment Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-29-agentic-shared-trace-standard-implementation-execution-map.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Normalize the existing `cv_generation` persisted trace surface so it becomes the reference implementation of the shared agentic trace standard without expanding scope into new trace families yet.

**Architecture:** The current `agentic-live-trace.json` flow already captures and persists valuable bounded runtime facts. Wave 1 should reshape that existing path into the shared trace vocabulary at the runtime payload, run-level summary, persisted snapshot, and export-manifest layers, while preserving the working operator download experience already in place.

**Key Invariants:**
- the existing `cv_generation` trace remains persisted, downloadable, and bundle-visible throughout the refactor
- shared top-level and per-record vocabulary is introduced without losing current bounded provenance, attempt, validation, repair, and error facts
- non-agentic runs still resolve to explicit `not_applicable` truth
- no raw chain-of-thought, full prompt bodies, or full provider response bodies are added
- this wave does not add `cv_analysis` or synonym trace capture yet

**Rollout / Revert:**  
- rollback_trigger: the renamed or normalized trace contract breaks direct downloads, bundle manifests, or existing operator debugging paths  
- rollback_method: revert to the current working `agentic-live-trace.json` contract and keep the broader shared-standard work as spec-only until the alignment can be redone safely

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: align the existing `cv_generation` trace payload and export semantics with the shared agentic trace standard  
Reasoning: the repo already has a working live trace surface, and the shared-standard spec now defines the canonical vocabulary that future trace families should inherit  
Invariants:
  - the current working trace remains operator-usable during and after the alignment
  - the shared standard is adopted through bounded refactoring, not a broad runtime rewrite
  - `manifest.json`, direct download route, and export list remain aligned
Dependencies:
  - `docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md`
  - `docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md`
  - `docs/superpowers/execution_maps/2026-04-29-agentic-shared-trace-standard-implementation-execution-map.md`
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_app.py`
Affected stages:
  - `cv_generation`
Affected features:
  - `inspection_debugging`
  - `trigger_run_management`
  - `cv_system`
Primary lens: `mixed`
Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage: `none`
  feature_history: `none`
  stage_source: `none`
  stage_contract: `none`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `docs/observability.md`
  readme: `none`
  generated:
    - `docs/generated/planning_lineage.yaml`
Generated refresh required: `yes`
Capability IDs:
  - `inspection_debugging.run-owned-artifact-exports`
  - `inspection_debugging.cv-generation-diagnostics`
  - `trigger_run_management.run-owned-artifact-exports`
Invariant IDs:
  - `none`
Spec needed: `no` (already exists)
Plan needed: `yes`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `docs/observability.md`
- Operating-system docs: `none`
- README: `none`
- Generated discovery: `docs/generated/planning_lineage.yaml`

## Implementation File Map

### Modify

- `src/fitcv/agentic_cv_generation.py`
  - align per-job runtime trace records with the shared per-record vocabulary
- `src/fitcv/pipeline.py`
  - align run-level trace summary shape and shared top-level field names
- `src/fitcv_cp/worker_job.py`
  - persist the normalized run-scoped trace payload without creating a second storage path
- `src/fitcv_cp/app.py`
  - keep direct download, export list, and manifest semantics aligned with the normalized contract
- `tests/test_pipeline_agentic_late_stage.py`
  - lock the shared-vocabulary runtime contract
- `tests/test_fitcv_cp/test_worker_job.py`
  - lock persisted snapshot shape
- `tests/test_fitcv_cp/test_app.py`
  - lock export-route and manifest behavior
- `docs/observability.md`
  - explain the trace as the first shared-standard reference implementation

### Create

- `none`

### Generated Refresh

- `docs/generated/planning_lineage.yaml`

## Task 1: Lock The Shared-Standard Vocabulary In Tests

**Files:**
- Create: `none`
- Modify: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Test: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add failing assertions for the shared top-level contract on the persisted `cv_generation` trace payload.
- [ ] Step 2: Add failing assertions for the shared per-record contract, including:
  - `trace_family`
  - `step_id`
  - `records`
  - shared `runtime_provenance`
  - shared `attempts`
  - shared `input_summary`, `output_summary`, `validation_summary`, `repair_summary`, and `error_summary`
- [ ] Step 3: Preserve explicit checks for `not_applicable`, `completed`, and `degraded` state handling in app and bundle tests.
- [ ] Step 4: Run:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py`
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`
- [ ] Step 5: Confirm the new assertions fail for the right contract reasons before implementation changes.

## Task 2: Align Runtime Trace Builders To The Shared Record Contract

**Files:**
- Create: `none`
- Modify: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/pipeline.py`
- Test: `tests/test_pipeline_agentic_late_stage.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `src/fitcv/agentic_cv_generation.py` so the current per-job trace payload is expressed using the shared per-record vocabulary rather than a one-off `cv_generation`-only shape.
- [ ] Step 2: Preserve all useful bounded facts already captured today, but remap them into the shared fields instead of duplicating old and new field sets unless a short transition shim is truly needed.
- [ ] Step 3: Update `src/fitcv/pipeline.py` so the run-level trace summary exposes the shared top-level contract:
  - `trace_family`
  - `step_id`
  - `trace_status`
  - `trace_summary`
  - `records`
  - `degradation`
  - `artifact_refs`
- [ ] Step 4: Keep the artifact filename `agentic-live-trace.json` for this wave unless a rename is necessary for compatibility, but make the payload itself the shared-standard reference.
- [ ] Step 5: Re-run `python -m pytest tests/test_pipeline_agentic_late_stage.py`.

## Task 3: Keep Persistence, Export Routes, And Manifest Semantics Aligned

**Files:**
- Create: `none`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `src/fitcv_cp/worker_job.py` to persist the normalized shared-standard payload through the existing snapshot family instead of adding a second trace storage mechanism.
- [ ] Step 2: Update `src/fitcv_cp/app.py` so the direct download route still returns `agentic-live-trace.json`, but now serves the normalized contract consistently.
- [ ] Step 3: Ensure the run export list and `artifacts.zip` manifest keep these semantics aligned:
  - artifact filename remains stable
  - manifest state remains `present`, `not_applicable`, `missing`, or `degraded`
  - degraded reasons stay compact and operator-readable
- [ ] Step 4: Re-run `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`.
- [ ] Step 5: Confirm no template change is needed unless the export grouping or label truly drifts from the current shared export surface.

## Task 4: Refresh Observability Docs And Run Final Focused Verification

**Files:**
- Create: `none`
- Modify: `docs/observability.md`
- Test: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/observability.md` so `agentic-live-trace.json` is described as the first shared-standard trace family implementation rather than a special isolated artifact.
- [ ] Step 2: Clarify which parts of the contract are shared across future agentic traces and which remain `cv_generation`-specific for now.
- [ ] Step 3: Refresh generated discovery:
  - `python scripts/generate_planning_lineage.py`
- [ ] Step 4: Run the final focused verification suite:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py`
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py`
  - `python -m pytest tests/test_fitcv_cp/test_app.py`
- [ ] Step 5: If practical in the current environment, sanity-check one run detail export path and verify the artifact still downloads cleanly under the existing filename.

## Verification Notes

- Keep this wave narrowly scoped to contract alignment for the existing `cv_generation` trace.
- Do not add `cv_analysis` trace capture in the same branch, even if helper reuse is tempting.
- Prefer small shared helper refactors over a giant universal trace abstraction in this first wave.
- Preserve backwards operator usability even if a short internal compatibility shim is needed during the transition.

## Suggested Verification Commands

```powershell
python -m pytest tests/test_pipeline_agentic_late_stage.py
python -m pytest tests/test_fitcv_cp/test_worker_job.py
python -m pytest tests/test_fitcv_cp/test_app.py
python scripts/generate_planning_lineage.py
```

## Execution Readiness

This plan is intentionally bounded to the existing `cv_generation` trace so the
repo gets one stable shared-standard reference implementation before `cv_analysis`
and synonym trace adoption begin.
