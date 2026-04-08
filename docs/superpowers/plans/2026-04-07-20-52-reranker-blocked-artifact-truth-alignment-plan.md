---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Implement the narrow artifact-truth fix for reranker-blocked ranked jobs so compact results and CV-debug coverage align with the new runtime path."
---

# Reranker-Blocked Artifact Truth Alignment Plan

## Outcome

Make the operator-facing artifact layer tell one truthful story for reranker-blocked ranked jobs:

- `results.json` rows no longer mix `blocked_by_reranker_fit` with `decision_chain.cv_analysis.status = not_run`
- `cv-debug.json` counts reranker-blocked ranked jobs as non-attempted ranked jobs
- omission reasons explicitly include `blocked_by_reranker_fit`
- stage-owned artifacts keep their current ownership and remain the deeper debug source

## Tasks

1. Align the compact results-ledger row contract

- Audit the row-building path in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py).
- Find where reranker-blocked rows still fall back to the stale `not_run` compact decision-chain placeholder.
- Update reranker-blocked rows so the compact ledger carries:
  - `cv_analysis.status = blocked_by_reranker_fit`
  - `decision_chain.cv_analysis.status = blocked_by_reranker_fit`
  - `decision_chain.cv_analysis.completed = false`
  - `decision_chain.cv_generation.status = not_attempted`
  - `decision_chain.cv_generation.attempted = false`

2. Fix CV-debug ranked-job coverage accounting

- Audit the CV-debug snapshot builder in [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py) and any upstream payload assembly in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py).
- Ensure reranker-blocked rows contribute to:
  - `non_attempted_ranked_jobs_total`
  - `omission_reason_counts.blocked_by_reranker_fit`
- Keep `debug_records_captured` scoped to rows with real generation debug payloads so the coverage math stays understandable.

3. Preserve the distinction between reranker-blocked and true analyzed skips

- Reconfirm the compact and stage-owned contracts still distinguish:
  - `blocked_by_reranker_fit`
  - `skipped_fit_gate`
- Ensure the narrow fix does not collapse those two statuses back together.
- Keep `cv_generation` explicitly unattempted for both paths, while preserving the different reasons.

4. Keep the artifact scope narrow

- Confirm this change targets:
  - `results.json`
  - `cv-debug.json`
  - any compact UI/export consumer that relies on those fields
- Avoid broad reshaping of:
  - `cv_analysis.json`
  - `stage-artifacts.json`
  - artifact bundle zip contents
- Touch stage-owned artifacts only if a minimal label or summary compatibility adjustment is required.

5. Align control-plane rendering if needed

- Review [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py) for any UI text derived from the stale compact `decision_chain`.
- Ensure reranker-blocked rows render as an explicit blocked outcome rather than a vague not-run state.
- Keep the UI wording compact and compatible with the current run-detail design.

6. Add focused regression coverage

- Extend [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py) to prove reranker-blocked rows are internally consistent in `results.json`.
- Extend [test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_fitcv_cp/test_worker_job.py) to prove `cv-debug.json` coverage accounting includes reranker-blocked ranked jobs.
- Include at least one assertion that true `skipped_fit_gate` rows still retain their distinct semantics.

7. Sync feature docs and history

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Keep the wording scoped to artifact truth propagation rather than broader performance tuning.

8. Refresh generated discovery

- Regenerate:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`
- Ensure the new spec and plan are discoverable from the updated feature refs.

## Verification

- Focused pipeline/export regression for reranker-blocked `results.json` rows
- Focused worker regression for `cv-debug.json` coverage accounting
- One assertion that `blocked_by_reranker_fit` and `skipped_fit_gate` remain distinct
- `python -m py_compile` for touched Python modules

## Completion Criteria

- Reranker-blocked rows are internally consistent in `results.json`.
- `cv-debug.json` no longer drops reranker-blocked ranked jobs from non-attempted coverage.
- The artifact layer tells one truthful story about ranked jobs stopped before generation.
- The fix stays narrow and does not turn into a broader artifact redesign.
