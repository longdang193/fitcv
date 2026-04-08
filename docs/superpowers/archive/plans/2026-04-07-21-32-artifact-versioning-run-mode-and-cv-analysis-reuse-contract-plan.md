---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Implement explicit post-fix artifact versioning, export run-mode metadata in run-scoped bundles, and replace ambiguous `cv_analysis` reuse totals with execution-aware metrics."
---

# Artifact Versioning, Run-Mode Metadata, and CV-Analysis Reuse Contract Plan

## Outcome

Make new run-scoped artifacts self-describing and easier to compare across runs and execution modes:

- post-fix bundles use explicit new schema versions
- `results.json`, `cv-debug.json`, and the run artifact bundle manifest export `run_mode`
- `cv_analysis` reuse metrics describe executed analysis work instead of mixing analyzed rows with pre-analysis reranker blocks
- older bundles remain readable but are clearly distinguishable by version

## Tasks

1. Bump the run-scoped artifact schema versions

- Update the persisted version strings in [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py) and any related bundle/manifest builders in [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py).
- Apply the version bump to:
  - `results_job_ledger_v2` → `results_job_ledger_v3`
  - `cv_generation_debug_v2` → `cv_generation_debug_v3`
  - `run_artifact_bundle_v1` → `run_artifact_bundle_v2`
- Keep older versions readable; do not attempt to rewrite historical logs.

2. Export run-mode metadata in run-scoped artifacts

- Extend run-scoped artifact headers to include:
  - `run_mode`
  - `run_mode_label`
- Add this to:
  - `results.json`
  - `cv-debug.json`
  - run artifact bundle `manifest.json`
- Reuse the existing control-plane `run_mode` truth rather than inventing a new execution-policy source.

3. Reframe `cv_analysis` reuse metrics around executed analysis

- Update the reuse-metric builders in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) so the metric family explicitly separates:
  - executed analysis rows
  - reused executed analysis rows
  - fresh executed analysis rows
  - reranker-blocked rows that never executed analysis
- Replace or de-emphasize ambiguous keys like:
  - `total_analysis_records`
- Prefer execution-aware keys such as:
  - `analysis_rows_executed`
  - `reused_analysis_rows`
  - `fresh_analysis_rows`
  - `blocked_before_analysis_rows`
  - `analysis_reuse_rate`

4. Keep run health and inspection UI compatible with the new metric names

- Audit [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py) for consumers of `reused_analysis_records`, `fresh_analysis_records`, and `total_analysis_records`.
- Update compact run-detail health summaries to use the new execution-aware metric names without changing the overall layout.
- Keep reranker-blocked rows visible as their own outcome rather than folding them into generic pending/not-run states.

5. Preserve narrow artifact ownership

- Keep this change scoped to:
  - artifact headers
  - compact run-scoped summaries
  - `cv_analysis` reuse-metric semantics
- Avoid redesigning:
  - stage sample structure
  - `results.json` row compactness
  - bundle contents and zip layout
  - broader run-detail information architecture

6. Add focused regression coverage

- Extend [test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_fitcv_cp/test_worker_job.py) to assert:
  - new schema versions
  - exported `run_mode` / `run_mode_label`
  - `cv-debug.json` header fields
- Extend [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py) to assert:
  - new `cv_analysis` reuse metric names and values
  - reranker-blocked rows are excluded from executed-analysis denominators
- Add or extend app tests if bundle metadata or run-health consumers depend on the renamed metrics.

7. Sync feature docs and history

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [inspection_debugging history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [trigger_run_management history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/history.md)
  - [cv_system history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [pipeline_performance history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Keep wording scoped to artifact contract clarity, run-mode discoverability, and reuse-metric semantics.

8. Refresh generated discovery

- Regenerate:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`
  - any other discovery files touched by the docs generator
- Ensure the new spec and plan are discoverable from the feature refs.

## Verification

- Focused worker tests for run-scoped artifact headers and schema versions
- Focused pipeline tests for execution-aware `cv_analysis` reuse metrics
- Focused app tests if run-detail consumers depend on renamed metric keys
- `python -m py_compile` for touched Python modules

## Completion Criteria

- New artifacts clearly advertise the post-fix contract version
- Exported bundles state whether the run was `Run All` or `Stage by Stage`
- `cv_analysis` reuse metrics are self-explanatory and no longer mix executed analysis with reranker-blocked rows
- Historical bundles remain readable and distinguishable by version
