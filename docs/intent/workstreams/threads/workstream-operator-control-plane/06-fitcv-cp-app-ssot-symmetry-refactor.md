---
thread_id: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
status: proposed
---

# fitcv-cp-app-ssot-symmetry-refactor

## Goal

Refactor `src/fitcv_cp/app.py` control-plane surfaces to enforce SSOT, symmetry, and invariance for:

- run-store operations (ControlPlaneStore vs BigQuery store selection)
- orchestration operations and binding safety
- shared contract helpers (run-mode normalization, JSON decode/pretty/schema checks)

## Key Deliverables

### Deliverable 1: SSOT control-plane façades

- no shadow-import contradictions in `src/fitcv_cp/app.py`
- single run-store façade/selector used by all routes
- single orchestration façade used by all routes

### Deliverable 2: Invariants enforced by shared helpers + tests

- run-mode normalization/labeling has one SSOT helper + tests
- JSON decode/pretty/schema validation centralized + tests
- `_RUN_SUBMISSION_CACHE` bounded or removed with tests proving orchestration behavior

## Task/Wave Breakdown

### Wave 1: Boundary confirmation

**Purpose:**
- confirm exact slice this thread owns before downstream execution

**Checks:**
- [ ] confirm in-scope surfaces
- [ ] confirm out-of-scope surfaces
- [ ] identify required upstream dependencies
- [ ] identify explicit downstream handoff target

**Verification:**
- [ ] scope bounded to `fitcv_cp` control-plane layer and does not overlap unrelated pipeline internals

**Exit Criteria:**
- thread scope stable enough for spec/plan execution

### Wave 2: Handoff preparation

**Purpose:**
- prepare clean handoff to spec/plan execution

**Steps:**
- [ ] link downstream spec + plan artifacts
- [ ] record follow-up work intentionally deferred

**Verification:**
- [ ] downstream artifacts exist and validator accepts their lineage

**Exit Criteria:**
- thread ready for implementation execution

## Scope

- in scope:
  - `src/fitcv_cp/app.py` refactor R1–R5 (SSOT/symmetry/invariance)
  - shared helpers in `src/fitcv_cp/run_artifact_contracts.py` (or new `src/fitcv_cp/*` helper module if required)
  - minimal interface tightening in `src/fitcv_cp/store.py` / `src/fitcv_cp/orchestrator.py` only as needed
- out of scope:
  - BigQuery schema changes
  - route/API shape changes (unless required to resolve contradictions; then must be split)
  - refactor of `fitcv.pipeline` internals
- deferred:
  - broader contract consolidation for non-run-mode label dictionaries (timeline/stage labels) unless pulled in by R4

## Dependencies

- upstream:
  - none
- blockers:
  - none
- downstream handoff:
  - `docs/superpowers/specs/2026-05-24-10-02-fitcv-cp-app-ssot-symmetry-refactor-spec.md`
  - `docs/superpowers/plans/2026-05-24-10-05-fitcv-cp-app-ssot-symmetry-refactor-plan.md`

## Completion Criteria

1. thread deliverables satisfied (SSOT/symmetry/invariance refactor shipped)
2. downstream spec + plan marked completed/superseded appropriately
3. validation evidence exists (validator + tests + GitNexus detect-changes)

