---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-operator-control-plane
map_type: implementation_execution
threads:
  - workstream-operator-control-plane.operator-control-plane-agentic-review-actions
  - workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
specs:
  - docs/superpowers/specs/2026-04-30-hitl-and-extended-agentic-cv-analysis-spec.md
---

# HITL + Extended Agentic CV Analysis Implementation Execution Map

## Scope

Ship a bounded human-in-the-loop gate and richer CV-analysis contract to improve
CV quality while preserving automation-first behavior.

## Waves

### Wave 1: Extend CV Analysis Contract

Primary files:

- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/pipeline.py`
- `tests/test_pipeline_agentic_late_stage.py`

Deliverables:

- requirement coverage + confidence hints + do-not-claim fields
- stage artifact compatibility updates

### Wave 2: Generation Consumption + Bounded Depth

Primary files:

- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv/cv_generator.py`
- `tests/test_pipeline_agentic_late_stage.py`

Deliverables:

- generation prompt/logic consumes new analysis fields
- bounded repair behavior for shallow outputs

### Wave 3: HITL Review Gate Runtime

Primary files:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- tests around run status transitions

Deliverables:

- review-required state transitions
- review action command handling (`approve`, `regenerate_once`, `reject`)

### Wave 4: Control Plane Surface

Primary files:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- review queue in run detail
- action endpoints/buttons
- timeline/event integration

### Wave 5: Observability + Docs

Primary files:

- `docs/observability.md`
- stage/debug artifact builders in app/worker as needed

Deliverables:

- clear operator workflow for HITL cases
- review audit fields visible in exports

## Dependency Order

Hard order:

1. Wave 1 before Wave 2
2. Wave 2 before Wave 3
3. Wave 3 before Wave 4
4. Wave 4 before Wave 5

Reason:

- UI/actions depend on runtime statuses and artifact shape; runtime logic depends
  on analysis/generation contracts first.

## Verification Path

```powershell
python -m pytest tests/test_pipeline_agentic_late_stage.py -k "analysis or generation or review"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or review"
python scripts/validate_repo_contracts.py --fast
```

## First Buildable Subset

Wave 1 + Wave 2 only:

- richer analysis contract
- generation consumption and depth behavior

This provides immediate quality gains even before HITL UI/actions land.
