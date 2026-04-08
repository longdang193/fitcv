---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement a pre-`cv_analysis` short-circuit for reranker `fit_label = skip` jobs so they stop before expensive analysis work and carry a distinct operator-facing status."
---

# Reranker Skip Pre-CV-Analysis Short-Circuit Plan

## Outcome

Prevent reranker-`skip` jobs from paying full `cv_analysis` cost while keeping artifacts and UI honest about where they were blocked.

Target state:

- ranked jobs with `fit_label = skip` stop before evidence retrieval
- they get a distinct status such as `blocked_by_reranker_fit`
- true analyzed-and-skipped jobs continue to use `skipped_fit_gate`
- `cv_generation` remains unattempted for both blocked paths

## Tasks

1. Add the pre-analysis short-circuit in the `cv_analysis` loop

- Update the final-stage loop in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py).
- Check the authoritative ranking fit label before any evidence retrieval or gap work.
- For `fit_label = skip`:
  - do not call `retrieve_evidence_bundle(...)`
  - do not call `retrieve_evidence(...)`
  - do not call `compute_gap(...)`
  - do not build semantic-alignment payloads
- Emit a synthetic final-stage record and continue.

2. Introduce and thread the new blocked-before-analysis status

- Add the distinct status contract for reranker-blocked jobs.
- Keep it separate from `skipped_fit_gate`.
- Update helper builders so:
  - row-level `cv_analysis`
  - `decision_chain`
  - CV-generation debug records
  - stage summaries
  all understand the new status.

3. Keep `results.json` compact but explicit

- Update compact ledger rows so reranker-blocked jobs carry:
  - `cv_analysis.status = blocked_by_reranker_fit`
  - `analysis_reuse_status = not_run_reranker_skip` or equivalent
  - no analysis fingerprint when analysis did not run
- Keep `cv_generation.attempted = false`
- Avoid reintroducing heavy row payloads.

4. Update stage-owned artifact shapes and counts

- Make `cv_analysis.json` and `stage-artifacts.json` distinguish:
  - `blocked_by_reranker_fit`
  - `generation_ready`
  - `skipped_fit_gate`
  - `analysis_failed`
- Ensure summary counts and quality metrics stay coherent.
- Preserve existing artifacts for genuine analyzed-and-skipped rows.

5. Align control-plane wording with the new distinction

- Update run-detail and any results-ledger rendering in [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py) and templates.
- Show a human-readable distinction such as:
  - `Blocked by reranker fit`
  - `Skipped after CV analysis`
- Keep pipeline-outcome detail compact and consistent.

6. Add focused regression coverage

- Extend [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py) to prove:
  - reranker-`skip` jobs no longer call expensive `cv_analysis` dependencies
  - reranker-blocked jobs get the new status
  - true `skipped_fit_gate` behavior still works when analysis really runs
- Add or extend any control-plane tests needed for status labeling.

7. Sync feature docs and history

- Update:
  - [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
  - [cv_system history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [pipeline_performance history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/history.md)
  - [inspection_debugging history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Keep the docs scoped to the short-circuit and new status semantics.

8. Refresh generated discovery

- Regenerate:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`
- Ensure the new spec and plan are discoverable from feature refs.

## Verification

- Focused pipeline tests covering:
  - reranker-`skip` short-circuit path
  - preserved analyzed-and-skipped path
  - unchanged accepted path
- One assertion that expensive `cv_analysis` helpers are not called for reranker-blocked rows
- `python -m py_compile` for touched Python modules

## Completion Criteria

- Reranker-`skip` jobs no longer pay evidence-retrieval or gap-analysis cost inside `cv_analysis`.
- A distinct status separates reranker-blocked rows from true fit-gate skips.
- Artifacts and UI clearly reflect where the job was stopped.
- The fix stays narrow and does not turn into a broader ranking or artifact redesign.
