---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Remove dead-weight pipeline summary work, slim operator-facing exports, and reduce large-run diagnostic noise without changing core pipeline behavior."
---

# Pipeline Dead-Weight Cleanup Plan

## Scope

This plan executes the cleanup defined in:

- [2026-04-06-02-35-pipeline-dead-weight-cleanup-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/superpowers/specs/2026-04-06-02-35-pipeline-dead-weight-cleanup-spec.md)

Primary source-of-truth docs:

- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/inspection_debugging.yaml)
- [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/pipeline_performance/pipeline_performance.yaml)
- [trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/trigger_run_management/trigger_run_management.yaml)

## Invariants

- Ranking, `cv_analysis`, `cv_generation`, and CV persistence behavior must not change.
- Existing reuse behavior for enrich, shortlist embeddings, ranking AI scores, and `cv_analysis` must remain intact.
- Run detail and stage-artifact diagnostics must remain sufficient for operators after any payload slimming.
- Compatibility-era fields can only be removed where their remaining owner is explicitly retired or replaced.

## Task 1: Remove top-level duplicate summary metrics

Remove dead-weight top-level summary fields that no longer feed a production consumer.

Targets:

- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_pipeline.py)

Changes:

- stop computing top-level `stage_quality_metrics`
- stop computing top-level `late_stage_reuse_metrics`
- stop building the top-level `shortlist_debug` summary block
- keep stage-owned quality and reuse diagnostics inside `stage_transition_artifacts`

Acceptance:

- `run_pipeline()` summary remains sufficient for the worker and checkpoint logic
- no production control-plane path depends on the removed top-level blocks

## Task 2: Slim `results.json` into a cleaner job ledger

Remove row-level payload that no longer powers operator-facing surfaces.

Targets:

- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/worker_job.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_worker_job.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Changes:

- remove row-level `shortlist_debug` from `export_results`
- verify run-detail enriched-jobs rendering still works from:
  - `pipeline_status`
  - `reject_reasons`
  - `rule_filter_marks`
  - `decision_chain`

Acceptance:

- `results.json` remains job-centric
- no visible regression in run-detail enriched-jobs behavior

## Task 3: Slim enrich payloads by separating runtime fields from debug baggage

Audit and remove enrich fields that are persisted/exported without a current active owner.

Targets:

- [enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/enrich.py)
- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_enrich.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_pipeline.py)

Subtasks:

1. classify enrich fields into:
   - canonical runtime fields
   - internal fingerprint/reuse support fields
   - operator/debug-only fields
2. remove raw duplicate classification fields from run-scoped/operator-facing exports unless a concrete debug owner remains:
   - `location_type_raw`
   - `seniority_raw`
   - `domain_raw`
   - `job_family_raw`
3. evaluate whether `description_cleaned` can stop being persisted/exported beyond fingerprinting support

Acceptance:

- enrich fingerprinting still works
- downstream filtering, shortlist, ranking, and CV stages behave identically
- operator-facing exports are slimmer and still useful

## Task 4: Reclassify `cv_prompt_version`

Reduce compatibility-era prompt metadata churn and make ownership explicit.

Targets:

- [config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/config.py)
- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [tracker.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/tracker.py)
- [bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/bq_store.py)
- [test_tracker.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_tracker.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_pipeline.py)

Changes:

- stop treating `cv_prompt_version` as meaningful live provenance in new operator-facing payloads
- keep it only where historical compatibility or storage schema still truly requires it
- prefer prompt id and template path as the active prompt contract

Acceptance:

- no active UI/debug surface implies that `cv_prompt_version` is the real prompt selector
- any retained `cv_prompt_version` field has an explicit compatibility owner

## Task 5: Reduce row-scaled Layer 4 timeline event spam

Move large-run event behavior toward aggregate stage reporting.

Targets:

- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [reporter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/reporter.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_pipeline.py)

Changes:

- remove or demote per-job Layer 4 event emission where aggregate stage rows and artifacts already explain the outcome
- preserve aggregate rows such as:
  - `layer4_cv_analysis`
  - `pipeline_complete`
- keep failure diagnostics recoverable through stage artifacts and job-ledger rows

Acceptance:

- large runs produce fewer timeline rows
- run detail still explains stage outcomes sufficiently
- stage artifact links remain the detailed diagnostic owner

## Task 6: Verification and regression coverage

Add or update focused tests for every contract change.

Coverage goals:

- `run_pipeline()` summary no longer exposes removed top-level fields
- `results.json` no longer includes row-level `shortlist_debug`
- enrich payload changes do not break fingerprinting or downstream stages
- retained compatibility for `cv_prompt_version` is explicit and tested
- timeline event volume is reduced without losing aggregate rows

Suggested test targets:

- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_pipeline.py)
- [test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_enrich.py)
- [test_tracker.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_tracker.py)
- [test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_worker_job.py)
- [test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/tests/test_fitcv_cp/test_app.py)

Verification commands:

- focused `pytest` slices for touched runtime, worker, and control-plane modules
- `py_compile` for touched Python files

## Task 7: Sync feature docs and history

Update the source-of-truth docs to reflect the slimmer contract.

Targets:

- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/inspection_debugging.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/history.md)
- [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/pipeline_performance/pipeline_performance.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/pipeline_performance/history.md)
- [trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/trigger_run_management/trigger_run_management.yaml) if run-detail timeline/event ownership changes materially

Doc outcomes:

- remove wording that implies retired duplicate metrics still belong to top-level summaries
- clarify where shortlist diagnostics now live
- clarify any retained compatibility owner for `cv_prompt_version`
- describe the aggregate-first timeline philosophy for large runs if event changes are material

## Rollout Notes

- do the summary cleanup first because it is the clearest dead-weight removal with the lowest behavioral risk
- do enrich payload slimming and `cv_prompt_version` cleanup only after verifying current consumers carefully
- treat event-volume cleanup as an operator-surface change and verify with realistic large-run expectations

## Completion Criteria

- dead-weight top-level summary computations are removed
- job-ledger export is slimmer without losing meaningful operator value
- enrich payloads no longer carry obvious unused baggage
- `cv_prompt_version` is either bounded to compatibility or retired from live diagnostics
- large-run timelines are less noisy while still diagnostic
- focused tests and `py_compile` pass
