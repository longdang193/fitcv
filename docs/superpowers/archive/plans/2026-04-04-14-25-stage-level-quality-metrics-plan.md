---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Implement run-level and stage-local quality metrics for shortlist, ranking, cv_analysis, and cv_generation so bottlenecks are visible without artifact-by-artifact inspection."
---

# Stage-Level Quality Metrics Implementation Plan

## Scope

Implement the observability upgrade defined in [2026-04-04-14-10-stage-level-quality-metrics-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/superpowers/specs/2026-04-04-14-10-stage-level-quality-metrics-spec.md).

This rollout stays intentionally narrow:

- derive stage-level quality metrics from existing stage outputs only
- add those metrics to run-level summaries, stage artifacts, and compact admin inspection surfaces
- keep formulas explicit and stable across exports and UI
- support succeeded runs and paused manual staged runs cleanly
- do not change ranking, fit-gate, or CV-generation behavior

## Source-of-Truth Alignment

Affected current-state docs:

- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [shortlist.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/shortlist.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/ranking.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

Generated refresh required:

- yes

## Invariants

- Metrics are observability-only and do not affect stage behavior.
- Each metric has a single explicit formula with stable numerator and denominator fields.
- Stage-owned metrics are computed where the relevant counts already exist.
- Partial/manual-staged runs must not emit misleading fake zeros for stages that have not executed.
- Run-level summaries aggregate stage metric blocks rather than recomputing competing definitions.

## Implementation Tasks

### Task 1: Add Shared Stage-Quality Metric Helpers

Create bounded helper functions that compute the new quality metrics from existing stage counts.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)

Changes:

- add small helpers for:
  - shortlist backfill metrics
  - ranking label-distribution metrics
  - `cv_analysis` rate metrics
  - `cv_generation` rate metrics
- enforce explicit zero-denominator behavior
- keep returned payloads compact and bounded

Acceptance criteria:

- helpers return stable metric payloads with counts, rates, and denominator totals
- zero-denominator cases return safe bounded values
- metric helpers do not depend on UI code

### Task 2: Emit Stage-Owned Quality Metrics In Stage Artifacts

Attach stage-level metric blocks to each affected stage artifact decision summary.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)

Changes:

- add `quality_metrics` under:
  - `stage_transition_artifacts.shortlist.decision_summary`
  - `stage_transition_artifacts.ranking.decision_summary`
  - `stage_transition_artifacts.cv_analysis.decision_summary`
  - `stage_transition_artifacts.cv_generation.decision_summary`
- use stage-local counts already present in each artifact builder
- omit the block when a stage has not executed yet

Acceptance criteria:

- each completed affected stage emits the correct metric block
- manual staged runs paused before a later stage do not emit misleading later-stage metrics
- artifact metric values match the stage’s underlying counts

### Task 3: Add Run-Level `stage_quality_metrics` Summary

Expose a compact cross-stage bottleneck view in the run results summary.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)

Changes:

- add a new `stage_quality_metrics` block to the run summary/results payload
- aggregate stage-owned metric blocks without redefining formulas
- include only stages that have actually executed

Acceptance criteria:

- run summary contains one compact cross-stage metric block
- metric values align with the stage artifact versions
- staged runs show only available stage metrics

### Task 4: Render Compact Stage Quality Metrics In Admin Run Detail

Make the new metrics visible in the admin UI without requiring stage JSON downloads.

Primary targets:

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

Changes:

- add a compact `Stage Quality Metrics` section to run detail
- show, per stage:
  - metric label
  - rate
  - numerator / denominator
- keep the display lightweight and readable in both active and completed runs

Acceptance criteria:

- run detail shows the new metrics when available
- missing stages do not render misleading placeholders
- existing run-detail layout remains stable

### Task 5: Add Metric Coverage For Core Diagnostic Scenarios

Lock in the intended interpretation behavior with focused tests.

Primary targets:

- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)

Changes:

- add tests for:
  - shortlist backfill rate from mixed raw-hit/backfill outputs
  - ranking label distribution over scored inputs
  - `cv_analysis` skip/ready/failure rates
  - `cv_generation` validation-fail/accepted/failure rates
  - partial staged runs that should omit later-stage metrics

Acceptance criteria:

- the core formulas are covered directly
- partial-run behavior is protected by tests
- UI tests confirm metrics render only when present

### Task 6: Sync Feature, Stage, and Cross-Cutting Docs

Update source-of-truth docs so the new observability layer is discoverable and consistently described.

Targets:

- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [shortlist.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/shortlist.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/ranking.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
- generated docs under `docs/generated/`

Acceptance criteria:

- docs describe the new stage-quality metric surfaces and formulas at a high level
- stage contracts identify their owned metric blocks
- generated discovery files point back to updated source docs

## Verification

Focused verification commands:

```powershell
python -m pytest -q tests\test_pipeline.py -k "quality_metrics or stage_quality"
python -m pytest -q tests\test_fitcv_cp\test_app.py -k "quality_metrics"
python -m py_compile src\fitcv\pipeline.py src\fitcv_cp\app.py
```

If the local Python environment differs, use the repo’s normal test runner equivalent for the `e2e-0` worktree.

## Risks And Rollback

### Risks

- ranking label distribution may be accidentally computed over final top-N instead of scored inputs
- partial staged runs may show misleading zeros if unavailable stages are not handled carefully
- UI can become too noisy if the metric section is overdesigned

### Rollback Trigger

- metric payloads disagree with stage-local counts
- staged runs show false later-stage metrics
- run detail becomes materially harder to scan

### Rollback Method

- remove the new metric blocks from run summary and stage artifact builders
- remove the compact UI rendering section
- keep underlying stage behavior unchanged
