---
layer: change
artifact_type: plan
status: proposed
parent_workstream: none
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
parent_spec: docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md
targets:
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
---

# Agentic Shared Trace Wave 2 CV Analysis Trace Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-29-agentic-shared-trace-standard-implementation-execution-map.md`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Add a persisted `cv_analysis` trace surface that follows the shared agentic trace standard and is exportable through the same run-scoped artifact system already used for `agentic-live-trace.json`.

**Architecture:** The agentic CV analysis step already produces bounded stage-owned facts such as analysis input fingerprints, evidence-selection summaries, gap summaries, and terminal stage-owned statuses like `ready_for_generation` or `blocked_by_reranker_fit`. Wave 2 should wrap those facts in the shared trace vocabulary, persist the run-scoped summary through the existing worker snapshot path, and expose the trace as a first-class downloadable artifact and bundle member without reopening the settled `cv_generation` trace contract.

**Key Invariants:**
- the `cv_analysis` trace follows the same top-level and per-record vocabulary now used by the normalized `cv_generation` trace
- stage-owned `cv_analysis` outcomes remain authoritative and are not flattened into vague success or failure labels
- non-agentic or non-applicable runs resolve to explicit `not_applicable` truth
- the trace remains bounded and does not duplicate full evidence corpora or full stage artifacts
- this wave does not change synonym or proposal trace behavior yet

**Rollout / Revert:**  
- rollback_trigger: `cv_analysis` trace capture causes stage-truth drift, noisy duplicate payloads, or artifact/export instability  
- rollback_method: remove the `cv_analysis` trace artifact and leave existing `cv_analysis.json`, `stage-artifacts.json`, and `cv-debug.json` surfaces as the only analysis diagnostics until the trace can be reintroduced safely

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: add a persisted shared-standard trace artifact for agentic `cv_analysis` runs  
Reasoning: `cv_analysis` is the next highest-value agentic debugging seam after `cv_generation`, and the shared-standard reference implementation is now stable enough to extend  
Invariants:
  - `cv_analysis` stage-owned statuses remain authoritative
  - the trace captures bounded provenance, input, attempt, output, and degradation facts without becoming a duplicate stage artifact
  - bundle manifest, export links, and direct download routes stay aligned
Dependencies:
  - `docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md`
  - `docs/superpowers/execution_maps/2026-04-29-agentic-shared-trace-standard-implementation-execution-map.md`
  - `src/fitcv/agentic_cv_analysis.py`
  - `src/fitcv/pipeline.py`
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_app.py`
Affected stages:
  - `cv_analysis`
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
  - `inspection_debugging.cv-analysis-diagnostics`
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

- `src/fitcv/agentic_cv_analysis.py`
  - add bounded shared-standard per-record trace capture around agentic analysis decisions
- `src/fitcv/pipeline.py`
  - collect and summarize run-scoped `cv_analysis` trace payloads
- `src/fitcv_cp/worker_job.py`
  - persist the normalized run-scoped analysis trace through the existing snapshot path
- `src/fitcv_cp/app.py`
  - add the direct download route, run export inclusion, and manifest state handling
- `tests/test_pipeline.py`
  - lock the runtime and pipeline summary contract for `cv_analysis` trace capture
- `tests/test_fitcv_cp/test_worker_job.py`
  - lock persisted snapshot shape and `not_applicable` handling
- `tests/test_fitcv_cp/test_app.py`
  - lock direct download, run exports, and bundle manifest behavior
- `docs/observability.md`
  - document the new `cv_analysis` trace surface within the shared agentic trace model

### Create

- `none` unless a narrowly scoped test helper or trace-builder helper proves necessary

### Generated Refresh

- `docs/generated/planning_lineage.yaml`

## Task 1: Lock The CV Analysis Trace Contract In Tests

**Files:**
- Create: `none`
- Modify: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Test: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add failing tests for the shared top-level contract on the persisted `cv_analysis` trace payload.
- [ ] Step 2: Add failing tests for the shared per-record contract, including:
  - `trace_family`
  - `step_id`
  - `records`
  - stage-owned `status`
  - `runtime_provenance`
  - `input_summary`
  - `output_summary`
  - `error_summary`
- [ ] Step 3: Cover at least these runtime cases:
  - `ready_for_generation`
  - `blocked_by_reranker_fit`
  - bounded analysis failure
  - explicit `not_applicable` truth when the agentic path is off
- [ ] Step 4: Add failing app tests for:
  - `/admin/runs/{run_id}/cv-analysis-trace.json`
  - run export link visibility
  - `artifacts.zip` inclusion
  - manifest states for `present`, `not_applicable`, and bounded degradation
- [ ] Step 5: Run the focused failing suite before implementation changes.

## Task 2: Capture Shared-Standard CV Analysis Trace Records In Runtime Code

**Files:**
- Create: `none`
- Modify: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/pipeline.py`
- Test: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add the smallest bounded trace record builder inside `src/fitcv/agentic_cv_analysis.py`.
- [ ] Step 2: Capture shared-standard runtime facts for `cv_analysis`, such as:
  - actual runtime path when relevant
  - analysis input fingerprint
  - bounded evidence-selection facts
  - stage-owned outcome
  - bounded failure or degradation reason
- [ ] Step 3: Keep `cv_analysis`-specific payloads stage-owned and compact; do not duplicate full evidence payloads or full stage-artifact bodies.
- [ ] Step 4: Thread the per-record trace into `src/fitcv/pipeline.py` and build a run-scoped summary that mirrors the shared top-level vocabulary already used by the normalized `cv_generation` trace.
- [ ] Step 5: Re-run the focused `tests/test_pipeline.py` coverage for the new trace contract.

## Task 3: Persist And Expose The Run-Scoped CV Analysis Trace

**Files:**
- Create: `none`
- Modify: `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Persist the run-scoped `cv_analysis` trace through the existing debug or snapshot family rather than introducing a second bespoke storage path.
- [ ] Step 2: Add the direct download route:
  - `/admin/runs/{run_id}/cv-analysis-trace.json`
- [ ] Step 3: Include the new artifact in run exports and `artifacts.zip`.
- [ ] Step 4: Extend manifest logic so applicability and degradation for the `cv_analysis` trace use the same state vocabulary as the `cv_generation` trace.
- [ ] Step 5: Re-run worker and app tests and confirm export behavior stays aligned.

## Task 4: Refresh Observability Docs And Run Final Focused Verification

**Files:**
- Create: `none`
- Modify: `docs/observability.md`
- Test: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/observability.md` to document `cv-analysis-trace.json` as the second shared-standard trace family surface.
- [ ] Step 2: Clarify when an operator should open `cv-analysis-trace.json` versus `agentic-live-trace.json`, `cv-debug.json`, and `cv_analysis.json`.
- [ ] Step 3: Refresh generated discovery:
  - `python scripts/generate_planning_lineage.py`
- [ ] Step 4: Run the final focused verification suite:
  - `python -m pytest tests/test_pipeline.py`
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py`
  - `python -m pytest tests/test_fitcv_cp/test_app.py`
- [ ] Step 5: If practical in the current environment, sanity-check one run detail page and verify the new analysis trace artifact is only shown when appropriate.

## Verification Notes

- Keep this wave scoped to `cv_analysis`; do not reopen the normalized `cv_generation` trace beyond tiny helper reuse if truly necessary.
- Preserve stage-owned `cv_analysis` outcome language such as `ready_for_generation` and `blocked_by_reranker_fit`.
- Prefer compact step-specific fields within the shared contract over a giant universal trace abstraction.
- Keep the operator-facing artifact name explicit and readable even if the shared payload family is generic.

## Suggested Verification Commands

```powershell
python -m pytest tests/test_pipeline.py
python -m pytest tests/test_fitcv_cp/test_worker_job.py
python -m pytest tests/test_fitcv_cp/test_app.py
python scripts/generate_planning_lineage.py
```

## Execution Readiness

This plan is intentionally centered on `cv_analysis` as the next shared-standard trace adoption wave, so the repo gains the second real implementation before synonym or proposal trace work begins.
