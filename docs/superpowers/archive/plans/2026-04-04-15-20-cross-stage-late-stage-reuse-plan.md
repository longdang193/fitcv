---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement exact-match late-stage reuse for ranking AI-score rows and cv_analysis records, plus artifact and run-detail reuse visibility."
---

# Cross-Stage Late-Stage Reuse Plan

## Summary

Implement strict stage-owned reuse for:

- `ranking` AI-score outputs
- `cv_analysis` analysis results

The rollout keeps reuse:

- per job
- fingerprint-based
- stage-local
- explicitly visible in artifacts and run detail

`cv_generation` reuse remains out of scope.

## Scope

This plan covers:

- ranking-time AI-score reuse lookup and reuse status reporting
- `cv_analysis` result reuse lookup and reuse status reporting
- run-level reuse metrics for inspection/debugging
- doc and artifact contract updates

This plan does not cover:

- `cv_generation` reuse
- generic whole-run caching
- admin-editable reuse settings

## Task 1: Add Ranking AI-Score Fingerprints

### Goal

Define and compute a strict per-job fingerprint for ranking AI-score reuse.

### Code targets

- `src/fitcv/ai_score.py`
- `src/fitcv/pipeline.py`
- shared config/helper modules if a small stage-local helper is needed

### Work

- define the ranking AI-score input contract fields
- compute a deterministic ranking AI-score fingerprint from:
  - job snapshot fields consumed by the reranker
  - candidate profile fields consumed by the reranker
  - reranker prompt/runtime fingerprint
  - ranking AI-score contract version
- keep final weighted-ranking weights out of this fingerprint unless they truly affect AI-score prompt construction

### Output

- reusable ranking AI-score input fingerprint per scored job

## Task 2: Add Ranking AI-Score Reuse Lookup

### Goal

Reuse prior AI-score outputs when the ranking-stage fingerprint matches exactly.

### Code targets

- `src/fitcv/pipeline.py`
- any stage-owned store/load helpers needed for ranking outputs

### Work

- define a stage-owned reuse lookup path for AI-score outputs
- for each ranking input:
  - compute fingerprint
  - look up a previous exact-match AI-score output
  - reuse if exact match exists
  - otherwise compute fresh
- preserve current final ranking behavior on top of the resulting scored rows

### Output

- mixed fresh/reused ranking AI-score rows in the same run when appropriate

## Task 3: Add `cv_analysis` Fingerprints

### Goal

Define and compute a strict per-job fingerprint for analysis-result reuse.

### Code targets

- `src/fitcv/evidence.py`
- `src/fitcv/pipeline.py`

### Work

- define the `cv_analysis` input contract fields
- compute a deterministic analysis fingerprint from:
  - ranked job snapshot
  - candidate evidence-bearing profile fingerprint
  - evidence-selection contract fingerprint
  - semantic-alignment contract fingerprint
  - gap-analysis / fit-gate contract fingerprint

### Output

- reusable `cv_analysis` input fingerprint per ranked job

## Task 4: Add `cv_analysis` Reuse Lookup

### Goal

Reuse prior `cv_analysis` records when the analysis-stage fingerprint matches exactly.

### Code targets

- `src/fitcv/pipeline.py`
- any stage-owned store/load helpers needed for `cv_analysis` records

### Work

- define a stage-owned lookup path for persisted analysis records
- for each ranked job:
  - compute fingerprint
  - look up exact-match persisted analysis record
  - reuse if exact match exists
  - otherwise run analysis fresh
- ensure reused records preserve the same downstream contract expected by `cv_generation`

### Output

- mixed fresh/reused `cv_analysis` records in the same run when appropriate

## Task 5: Expose Reuse Visibility In Artifacts And Run Outputs

### Goal

Make reuse observable and debuggable without inspecting internals.

### Code targets

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- worker/export serializers if run-level export needs new fields

### Work

- add ranking reuse fields such as:
  - `ai_score_reuse_status`
  - `ai_score_input_fingerprint`
- add `cv_analysis` reuse fields such as:
  - `analysis_reuse_status`
  - `analysis_input_fingerprint`
- add bounded stage-level counts:
  - reused
  - fresh
- add run-level reuse metrics summary
- surface those metrics in run detail and stage artifacts

### Output

- reuse visibility in:
  - `ranking` artifacts
  - `cv_analysis` artifacts
  - run-level results/debug surfaces

## Task 6: Add Focused Tests For Exact-Match And Invalidation Behavior

### Goal

Lock the reuse contract down with narrow, high-signal coverage.

### Test targets

- `tests/test_pipeline.py`
- stage-specific tests if ranking/analysis helpers are unit-testable in isolation
- control-plane tests if run detail/export changes

### Cases

- ranking reuses exact-match AI-score output
- ranking recomputes when prompt/runtime fingerprint changes
- ranking recomputes when job snapshot fingerprint changes
- `cv_analysis` reuses exact-match analysis record
- `cv_analysis` recomputes when semantic-alignment settings change
- `cv_analysis` recomputes when evidence-selection settings change
- run outputs include reuse visibility fields

## Task 7: Sync Docs And Generated Discovery

### Goal

Update the source-of-truth stage and feature contracts plus generated discovery.

### Doc targets

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/stages/ranking.yaml`
- `docs/stages/cv_analysis.yaml`
- `docs/FitCV-pipeline.md`
- `docs/generated/feature_overview.md`
- `docs/generated/features_index.yaml`
- `docs/generated/feature_capabilities_index.yaml`

### Work

- describe stage-owned reuse behavior
- document exact-match fingerprint invalidation model
- document reuse visibility in artifacts/run detail

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py
.\.venv\Scripts\python.exe -m py_compile src\fitcv\pipeline.py src\fitcv\ai_score.py src\fitcv\evidence.py src\fitcv_cp\app.py src\fitcv_cp\worker_job.py
```

If helper-level tests are added, run those focused files too.

## Risks

- fingerprints that are too weak can produce stale reuse
- fingerprints that are too broad can erase most reuse value
- stage-owned lookup paths may need careful schema/version gating

## Rollout Order

1. ranking fingerprint + reuse
2. `cv_analysis` fingerprint + reuse
3. artifact/run-detail reuse visibility
4. docs + generated sync

## Done Criteria

- `ranking` reuses AI-score rows on exact match only
- `cv_analysis` reuses analysis records on exact match only
- fresh recompute happens automatically on contract change
- artifacts clearly distinguish reused vs fresh rows
- run detail exposes late-stage reuse metrics
