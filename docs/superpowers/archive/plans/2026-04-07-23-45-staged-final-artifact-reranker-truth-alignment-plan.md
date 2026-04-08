---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Align succeeded `Stage by Stage` final artifacts with the already-correct reranker-blocked truth contract used by succeeded `Run All` runs."
---

# Staged Final Artifact Reranker-Truth Alignment Plan

## Outcome

Make the succeeded `Stage by Stage` finalization path emit the same reranker-blocked artifact truth already emitted by succeeded `Run All` runs.

After this change:

- reranker-blocked staged rows use `pipeline_status = "ranked_blocked_by_reranker_fit"`
- compact `decision_chain.cv_analysis.status` stays `blocked_by_reranker_fit`
- `cv-debug.json` counts reranker-blocked staged rows as explicit non-attempted ranked jobs
- stage-local artifact ownership stays unchanged

## Tasks

1. Trace the staged-only finalization path

- Inspect the succeeded `manual_staged` finalization flow in [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py).
- Compare it with the succeeded `run_all` path and identify where staged runs still degrade:
  - `pipeline_status`
  - compact `decision_chain.cv_analysis`
  - CV-debug coverage accounting
- Confirm whether the drift comes from stale summary inputs, stale export-row builders, or staged-only final payload reconstruction.

2. Unify compact `results.json` outcome mapping

- Update the shared final row mapping so reranker-blocked rows in succeeded `manual_staged` runs serialize exactly like succeeded `run_all` rows.
- Ensure staged reranker-blocked rows now emit:
  - `pipeline_status = "ranked_blocked_by_reranker_fit"`
  - `cv_analysis.status = "blocked_by_reranker_fit"`
  - `decision_chain.cv_analysis.status = "blocked_by_reranker_fit"`
  - `decision_chain.cv_analysis.completed = false`
  - `cv_generation.status = "not_attempted"`
  - `cv_generation.attempted = false`

3. Fix staged CV-debug coverage accounting at final success

- Update the staged final CV-debug snapshot builder path so reranker-blocked ranked jobs are counted even when no generation attempt happened.
- Ensure succeeded staged runs now report:
  - `non_attempted_ranked_jobs_total`
  - `omission_reason_counts.blocked_by_reranker_fit`
  - `snapshot_complete = true` when every ranked job is either attempted or explicitly accounted for

4. Preserve the narrow artifact boundary

- Do not redesign:
  - `cv_analysis.json`
  - `cv_generation.json`
  - `stage-artifacts.json`
  - artifact bundle contents
- Keep the fix scoped to the final run-scoped artifact truth for succeeded staged runs.

5. Align control-plane wording only if needed

- Review [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py) consumers to confirm no staged-only fallback wording still assumes:
  - `ranked_no_cv`
  - `cv_analysis = not_run`
- Only patch UI mapping if the stale staged artifact values were being masked or reintroduced there.

6. Add focused regression coverage

- Extend [test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_fitcv_cp/test_worker_job.py) with a succeeded `manual_staged` regression that proves:
  - reranker-blocked rows keep the same compact truth as `run_all`
  - staged CV-debug coverage includes reranker-blocked rows
- Extend [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py) only if a shared export-row helper needs explicit outcome assertions.
- Add or update app tests only if run-detail behavior depends on the staged artifact correction.

7. Sync docs and discovery

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [inspection_debugging history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [trigger_run_management history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/history.md)
  - [cv_system history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Refresh generated discovery under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated).

## Verification

- Focused worker tests for succeeded staged finalization and CV-debug coverage
- Focused pipeline tests if shared row-mapping logic changes
- Focused app tests only if run-detail consumers need adjustment
- `python -m py_compile` for touched Python files

## Completion Criteria

- Succeeded `Run All` and succeeded `Stage by Stage` bundles serialize reranker-blocked rows the same way in `results.json`
- Staged reranker-blocked rows no longer degrade to `ranked_no_cv` or `decision_chain.cv_analysis.status = not_run`
- Staged `cv-debug.json` counts reranker-blocked ranked jobs in non-attempted coverage
- Stage-local artifact shapes remain unchanged

## Completion Notes

- Preserved `cv_generation_debug_records` in the staged checkpoint payload so reranker-blocked rows survive the pause after `cv_analysis`
- Added focused pause/resume pipeline regressions proving succeeded staged runs now finalize reranker-blocked rows the same way as `Run All`
- Existing worker-side `cv-debug.json` coverage logic then counts those staged reranker blocks correctly without broad artifact redesign
