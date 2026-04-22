---
layer: change
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_app.py
  - repo_config/adoption-mode.yaml
  - docs/superpowers/archive/specs/2026-04-22-18-10-phase-14-inspection-diagnostics-completion-spec.md
  - docs/superpowers/plans/2026-04-22-18-20-phase-14-inspection-diagnostics-completion-plan.md
related_features:
  - inspection_debugging
related_stages: []
---

# Phase 14 Inspection Diagnostics Completion Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Close the last two `inspection_debugging` evidence gaps by backfilling
direct app ownership and direct proof tests for CV-analysis and CV-generation
run-health diagnostics.  
Reasoning: After Phase 13, only two `inspection_debugging` capabilities remain
without direct code/test evidence, and both are already rendered by the
run-detail diagnostics surface in `src/fitcv_cp/app.py`.  
Invariants:

- The phase is evidence-oriented only; it does not redesign run-detail behavior.
- `src/fitcv_cp/app.py` remains the truthful owner for the diagnostic rows.
- `@proves` markers must attach only to tests that directly assert the named
  CV-analysis or CV-generation diagnostics.
- Adoption enforcement expands only after direct code and direct test evidence
  both exist.

## Current Gap Snapshot

As of the post-Phase-13 checkpoint:

| Feature | Missing code | Missing tests |
| --- | ---: | ---: |
| `inspection_debugging` | 2 | 2 |
| Repo-wide total | 14 | 14 |

Residual capabilities for this phase:

- `inspection_debugging.cv-analysis-diagnostics`
- `inspection_debugging.cv-generation-diagnostics`

## Goal

Complete the remaining inspection-debugging evidence gaps with the smallest
truthful metadata and proof backfill possible.

## Acceptance Criteria

1. `src/fitcv_cp/app.py` directly owns both remaining capabilities.
2. `tests/test_fitcv_cp/test_app.py` directly proves both capabilities.
3. `repo_config/adoption-mode.yaml` enforces both capabilities.
4. Generated contract and lineage surfaces refresh cleanly.
5. `inspection_debugging` moves from `2/2` missing code/test evidence to `0/0`.
6. Repo-wide totals move from `14/14` to `12/12`.

## Execution Notes

Status: `completed`

Completed changes:

- added direct code ownership in `src/fitcv_cp/app.py`
- added direct `@proves` coverage for CV-analysis diagnostics using existing
  run-health assertions
- added two focused CV-generation diagnostics tests for rendered visibility and
  hidden-when-absent behavior
- extended the pilot enforcement in `repo_config/adoption-mode.yaml`

Measured result:

- `inspection_debugging` moved from `2/2` missing code/test evidence to `0/0`
- repo-wide missing direct evidence moved from `14/14` to `12/12`
