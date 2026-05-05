---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv/telemetry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv/test_telemetry.py
related_features:
  - none
related_stages:
  - cv_generation
---

# Telemetry Disabled Classification Surface Audit Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-04-provider-storage-agnostic-parity-implementation-execution-map.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` to implement task-by-task with bounded scope.

## Goal

Audit and normalize telemetry health classification across operator-facing surfaces so intentional OTEL disablement (`otel_disabled`) is not reported as actionable degradation.

## Key Deliverables

- Inventory of telemetry health classifiers in control-plane endpoints/templates used by run/operator views.
- Bounded patch for confirmed misclassification surfaces (`degraded` counting without reason filtering).
- Focused tests proving:
  - true degradations still show degraded,
  - `otel_disabled` is classified as disabled/neutral (not degraded),
  - existing artifact and UI contracts remain stable.

## Task Breakdown

### Task 1: Surface Inventory and Failure Pattern Confirmation

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv/telemetry.py`
- Inspect tests: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv/test_telemetry.py`

- [ ] Step 1: Enumerate all telemetry-health aggregation helpers and UI render points used in operator/run-detail surfaces.
- [ ] Step 2: Confirm where `status == degraded` is counted without guarding `degradation_reason == otel_disabled`.
- [ ] Step 3: Classify findings as `confirmed | likely | risk` with file/function references.

### Task 2: Apply Bounded Normalization Patch

**Files:**
- Modify: `src/fitcv_cp/app.py` (aggregator logic only)
- Modify: `src/fitcv/telemetry.py` (status normalization only, if required by confirmed finding)
- Modify: `src/fitcv_cp/templates/run_detail.html` (only if label semantics need parity)

- [ ] Step 1: Implement minimal classification guardrails for confirmed misclassification surfaces.
- [ ] Step 2: Preserve current behavior for true degraded reasons (dependency missing, endpoint missing, export failures).
- [ ] Step 3: Avoid unrelated refactors or schema changes.

### Task 3: Tests and Contract Verification

**Files:**
- Modify/Add tests: `tests/test_fitcv_cp/test_app.py`
- Modify/Add tests: `tests/test_fitcv/test_telemetry.py`

- [ ] Step 1: Add/adjust tests for `otel_disabled` semantics at helper and rendered-surface levels.
- [ ] Step 2: Re-run focused tests for telemetry + run-detail health.
- [ ] Step 3: Confirm no regressions in already patched provenance/export contract tests.

## Verification

```powershell
pytest -q tests/test_fitcv/test_telemetry.py
pytest -q tests/test_fitcv_cp/test_app.py -k "telemetry_export"
pytest -q tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv
```

Optional lane validation (if local app running on port 8000):
```powershell
# open /admin/runs/<run_id> where payload includes otel_disabled
# verify telemetry health badge/counters do not show degraded due only to otel_disabled
```

## Completion Criteria

A plan item is complete when:

1. confirmed misclassification surfaces are fixed with bounded edits,
2. `otel_disabled` no longer inflates degraded telemetry health in operator views,
3. true degraded telemetry reasons still appear degraded,
4. focused verification commands pass,
5. deferred `likely/risk` findings are explicitly logged without uncontrolled scope expansion.

## Wave/Lane Fit

This plan fits the same implementation-wave lane as the Phase-2 portability work (`2026-05-04-provider-storage-agnostic-parity-implementation-execution-map.md`), specifically the operator observability hardening slice after provider/provenance corrections. It is a follow-up containment patch, not a new roadmap branch.
