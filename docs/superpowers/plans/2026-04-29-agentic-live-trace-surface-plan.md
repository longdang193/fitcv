---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
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

# Persisted Run-Scoped Agentic Live Trace Surface Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Persist a bounded `agentic-live-trace.json` artifact for agentic CV generation runs and expose it through the existing run exports and bundle surfaces.

**Architecture:** The runtime capture should start where live-provider generation facts already exist, then flow through the pipeline summary into the worker’s run-scoped snapshot persistence path. The control plane should expose the trace as a first-class downloadable artifact and mark its presence or absence in the bundle manifest using the same truth vocabulary already used for other run artifacts.

**Key Invariants:**
- no raw chain-of-thought or unbounded provider transcripts are persisted
- non-agentic runs must resolve to explicit `not_applicable` trace truth
- direct download, artifact bundle contents, and manifest state must stay aligned
- trace records must describe actual runtime behavior, not merely configured defaults
- the first implementation should prefer existing persisted snapshot surfaces and avoid a new BigQuery schema change unless the existing surfaces prove too contorted

**Rollout / Revert:**  
- rollback_trigger: trace payload growth, route instability, or manifest drift breaks existing run artifact flows  
- rollback_method: remove the new artifact route and manifest entry, then keep existing `cv-debug.json` and `stage-artifacts.json` as the only late-stage diagnostics

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: add a persisted downloadable live-trace artifact for agentic CV generation runs  
Reasoning: the design is already settled by the spec, but implementation crosses runtime capture, worker persistence, control-plane export routes, and operator docs  
Invariants:
  - trace capture is bounded and redacted
  - late-stage non-agentic runs stay explicit instead of looking broken
  - operator download surfaces and bundle manifest expose the same artifact truth
Dependencies:
  - `docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md`
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
  - add bounded live-request and live-response trace facts near the existing live-provider generation path
- `src/fitcv/pipeline.py`
  - collect per-job live trace records into pipeline summary output and derive run-level trace status
- `src/fitcv_cp/worker_job.py`
  - serialize and persist the new run-scoped artifact payload alongside the existing debug and stage-artifact snapshots
- `src/fitcv_cp/app.py`
  - add the download route, export-link registration, bundle inclusion, and manifest state handling
- `src/fitcv_cp/templates/run_detail.html`
  - expose the artifact in the run exports card through existing export-link rendering
- `tests/test_pipeline_agentic_late_stage.py`
  - lock the runtime and summary contract
- `tests/test_fitcv_cp/test_worker_job.py`
  - lock persisted snapshot payload shape and non-agentic handling
- `tests/test_fitcv_cp/test_app.py`
  - lock direct download, run exports, and bundle manifest behavior
- `docs/observability.md`
  - document the new persisted trace surface and its debugging role

### Modify Only If A Dedicated Persistence Column Becomes Necessary

- `src/fitcv_cp/models.py`
- `src/fitcv_cp/bq_store.py`
- `tests/test_fitcv_cp/test_bq_store.py`

### Create

- `none` expected unless implementation requires a narrowly scoped helper test fixture

### Generated Refresh

- `docs/generated/planning_lineage.yaml`

## Task 1: Lock The Runtime Trace Contract In Tests

**Files:**
- Create: `none`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Test: `tests/test_pipeline_agentic_late_stage.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add failing tests that define the per-job bounded trace contract produced by the live-provider path.
- [ ] Step 2: Cover at least these cases:
  - accepted live-provider generation with bounded request and response facts
  - validation retry after missing sections
  - live-provider failure returning bounded error fields
  - non-agentic path returning explicit `not_applicable` truth
- [ ] Step 3: Run `python -m pytest tests/test_pipeline_agentic_late_stage.py`.
- [ ] Step 4: Confirm the new assertions fail for the right reason before code changes.
- [ ] Step 5: Commit after the runtime contract and tests pass.

## Task 2: Capture And Summarize The Live Trace In Runtime Code

**Files:**
- Create: `none`
- Modify: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/pipeline.py`
- Test: `tests/test_pipeline_agentic_late_stage.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add the smallest bounded trace primitives to `src/fitcv/agentic_cv_generation.py` where live-provider calls, retries, validation, and repair decisions already happen.
- [ ] Step 2: Ensure the runtime records actual provenance, request timing, retry context, bounded provider outcome, and validation/repair summary without persisting full prompt or response bodies.
- [ ] Step 3: Thread those per-job trace records through `src/fitcv/pipeline.py` into the late-stage summary so the worker can persist one run-scoped artifact.
- [ ] Step 4: Re-run `python -m pytest tests/test_pipeline_agentic_late_stage.py`.
- [ ] Step 5: Commit after the runtime trace contract passes cleanly.

## Task 3: Persist The Run-Scoped Artifact And Expose It Through The Control Plane

**Files:**
- Create: `none`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/run_detail.html`
- Test: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add failing worker-job tests for the persisted artifact payload, including explicit `not_applicable` handling for non-agentic runs.
- [ ] Step 2: Add failing app tests for:
  - `/admin/runs/{run_id}/agentic-live-trace.json`
  - run-detail export link visibility
  - `artifacts.zip` inclusion
  - manifest state for `present`, `not_applicable`, and bounded degradation
- [ ] Step 3: Run `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`.
- [ ] Step 4: Implement worker payload serialization and persistence in `src/fitcv_cp/worker_job.py`.
- [ ] Step 4a: Prefer deriving the downloadable artifact from the existing persisted run-scoped snapshot family first.
- [ ] Step 4b: If that path is too contorted or duplicates too much state, stop and explicitly add the smallest necessary `src/fitcv_cp/models.py` and `src/fitcv_cp/bq_store.py` changes plus `tests/test_fitcv_cp/test_bq_store.py` coverage in the same branch.
- [ ] Step 5: Implement artifact routing, export list inclusion, and manifest state wiring in `src/fitcv_cp/app.py`.
- [ ] Step 6: Keep template changes in `src/fitcv_cp/templates/run_detail.html` minimal by using the existing `run_export_links` rendering path.
- [ ] Step 7: Re-run `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py`.
- [ ] Step 8: Commit after the control-plane artifact surface is stable.

## Task 4: Refresh Operator Docs And Run End-To-End Verification

**Files:**
- Create: `none`
- Modify: `docs/observability.md`
- Test: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/observability.md` to explain when to use `agentic-live-trace.json`, how it differs from `cv-debug.json`, and how it appears in the run exports and artifact bundle.
- [ ] Step 2: Refresh generated discovery with the repo’s canonical planning-lineage path after the plan/spec source updates.
- [ ] Step 3: Run the focused verification suite:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py`
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py`
  - `python -m pytest tests/test_fitcv_cp/test_app.py`
- [ ] Step 4: If a local app server is already available, sanity-check one run detail page and confirm the artifact download appears only when appropriate.
- [ ] Step 5: Commit once tests and docs are aligned.

## Verification Notes

- Keep the first implementation narrow to `cv_generation`; do not silently expand scope to `cv_analysis` tracing in the same change.
- Prefer deriving the downloadable artifact from existing run-scoped persisted payloads instead of introducing a second storage mechanism.
- Treat `docs/generated/planning_lineage.yaml` as generated output only; do not edit it manually.

## Suggested Verification Commands

```powershell
python -m pytest tests/test_pipeline_agentic_late_stage.py
python -m pytest tests/test_fitcv_cp/test_worker_job.py
python -m pytest tests/test_fitcv_cp/test_app.py
```

## Execution Readiness

This plan is intentionally split into runtime, persistence, and operator-surface slices so a later execution pass can parallelize safely without blurring ownership boundaries.
