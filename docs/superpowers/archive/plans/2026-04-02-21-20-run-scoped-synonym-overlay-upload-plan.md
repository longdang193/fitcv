---
feature_type: modify
feature_name: trigger_run_management
status: completed
summary: "Implement a run-scoped synonym-overlay upload flow at the enrich checkpoint so manual staged runs can adjust skill matching before continuing into rule filter."
---

# Run-Scoped Synonym Overlay Upload Implementation Plan

## Scope

Implement the enrich-checkpoint upload flow defined in [2026-04-02-21-05-run-scoped-synonym-overlay-upload-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/superpowers/specs/2026-04-02-21-05-run-scoped-synonym-overlay-upload-spec.md).

This rollout does:

- add a run-scoped synonym-overlay upload action for manual staged runs paused after `enrich`
- validate uploaded overlay YAML before activation
- persist the uploaded overlay with the run/checkpoint
- continue downstream stages with one merged effective synonym map for that run
- expose uploaded-overlay status in the run-detail inspection UI

This rollout does not:

- mutate the trusted base `config/skill_synonyms.yaml`
- add a full synonym editor UI
- add paste-mode overlay editing in phase 1
- add overlay upload to `run_all` mode
- add automatic promotion from uploaded overlay to shared config

## Source-of-Truth Alignment

Affected current-state docs:

- [docs/features/trigger_run_management/trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/trigger_run_management/trigger_run_management.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/trigger_run_management/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/trigger_run_management/history.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/stages/rule_filter.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/FitCV-pipeline.md)

Affected code and tests:

- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv/config.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv/pipeline.py)
- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/models.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/bq_store.py)
- [src/fitcv_cp/worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/worker_job.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/templates/run_detail.html)
- [tests/test_config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_config.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_bq_store.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_worker_job.py)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_app.py)

Generated refresh required:

- none

## Invariants

- The base synonym YAML remains unchanged by run-scoped uploads.
- Uploaded overlays affect only the target run.
- The upload flow is only active for `manual_staged` runs paused after `enrich`.
- Downstream synonym-aware stages in the run consume one merged effective map.
- Existing manual checkpoint behavior remains linear and deterministic.

## Implementation Tasks

### Task 1: Extend The Run Contract With Run-Scoped Overlay Persistence

Add run-level persistence for the uploaded synonym overlay so it can survive refresh, resume, and worker continuation.

Primary files:

- [src/fitcv_cp/models.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/models.py)
- [src/fitcv_cp/bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/bq_store.py)
- BigQuery DDL and migration files as needed
- [tests/test_fitcv_cp/test_bq_store.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_bq_store.py)

Acceptance criteria:

- a run can persist a run-scoped synonym overlay payload
- persisted overlays are reloadable from the run record
- older runs without overlay data still load safely

### Task 2: Add Overlay YAML Parsing And Validation

Implement a validator/parser that accepts the supported synonym-overlay YAML shape and rejects invalid uploads with explicit errors.

Primary files:

- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv/config.py)
- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/app.py)
- [tests/test_config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_config.py)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- accepted YAML shape matches the project synonym-map contract
- invalid alias/value structures are rejected clearly
- validation errors are surfaced to the operator in the admin flow

### Task 3: Add An Enrich-Checkpoint Upload Route And UI Control

Add the admin endpoint and run-detail UI control to upload a synonym overlay when the run is paused after `enrich`.

Primary files:

- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/templates/run_detail.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- manual staged runs paused after `enrich` show an `Upload Synonym Overlay YAML` control
- the upload control is hidden outside the intended checkpoint/state
- successful uploads persist on the target run and survive refresh

### Task 4: Propagate The Uploaded Overlay Into Continuation Config

Ensure continuation from `enrich` rebuilds one effective merged synonym map from:

- base `skill_synonyms.yaml`
- plus the run-scoped uploaded overlay

Primary files:

- [src/fitcv_cp/worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/worker_job.py)
- [src/fitcv/config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv/config.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv/pipeline.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_worker_job.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_pipeline.py)

Acceptance criteria:

- continuation after `enrich` uses the uploaded overlay when present
- `rule_filter` and later synonym-aware stages consume the same effective merged map
- runs without an uploaded overlay continue using the base map unchanged

### Task 5: Expose Overlay Status In Run Inspection

Add run-detail visibility so operators can tell whether a run is continuing with the default map or an uploaded overlay.

Primary files:

- [src/fitcv_cp/app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/app.py)
- [src/fitcv_cp/templates/run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/src/fitcv_cp/templates/run_detail.html)
- [tests/test_fitcv_cp/test_app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/tests/test_fitcv_cp/test_app.py)

Acceptance criteria:

- run detail shows whether an overlay is active
- run detail shows overlay filename and entry count when available
- the UI state stays accurate after upload and after continuation

### Task 6: Update Docs And History For The Upload Workflow

Sync the current-state docs so the enrich checkpoint upload flow is part of the documented staged-run lifecycle.

Primary files:

- [docs/features/trigger_run_management/trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/trigger_run_management/trigger_run_management.yaml)
- [docs/features/trigger_run_management/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/trigger_run_management/history.md)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/stages/rule_filter.yaml)
- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/FitCV-pipeline.md)

Acceptance criteria:

- trigger/run-management docs describe the enrich-checkpoint upload action
- inspection docs describe uploaded-overlay visibility
- stage docs explain the enrich-to-rule-filter handoff with optional run-scoped overlay input

## Execution Order

1. Complete Task 1 first so run-scoped overlay persistence has a stable contract.
2. Complete Task 2 next so upload-time validation is explicit before wiring the UI.
3. Complete Task 3 to expose the upload path at the enrich checkpoint.
4. Complete Task 4 so continuation actually uses the uploaded overlay.
5. Complete Task 5 to make the active overlay inspectable.
6. Complete Task 6 last so the docs reflect implemented behavior.

## Verification Plan

Targeted verification should cover:

```powershell
python -m pytest -q tests\test_config.py -k "synonym_overlay"
```

```powershell
python -m pytest -q tests\test_fitcv_cp\test_bq_store.py -k "synonym_overlay"
```

```powershell
python -m pytest -q tests\test_fitcv_cp\test_app.py -k "synonym_overlay or upload"
```

```powershell
python -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "synonym_overlay"
```

```powershell
python -m pytest -q tests\test_pipeline.py -k "effective_skill_synonyms"
```

Manual verification checklist:

- trigger a `manual_staged` run and pause after `enrich`
- confirm the run detail page shows the synonym-overlay upload control
- upload a valid overlay YAML and verify the run detail page shows the uploaded filename and entry count
- upload an invalid overlay YAML and verify the error is explicit
- continue to `rule_filter` and confirm downstream stages use the merged effective synonym map
- confirm runs without uploaded overlays still continue normally

## Risks and Mitigations

### Run-State Drift Risk

Risk:

- the uploaded overlay may not be consistently reapplied during manual continuation or later downstream stages

Mitigation:

- store the overlay on the run record
- rebuild one effective merged map at continuation time
- add worker/pipeline tests covering post-enrich continuation

### UI Scope Creep Risk

Risk:

- the upload flow could expand into a full synonym-management interface prematurely

Mitigation:

- keep phase 1 file-upload only
- keep uploads run-scoped only
- defer editing, promotion, and multi-checkpoint support

## Task Status

- [x] Task 1: Extend the run contract with run-scoped overlay persistence
- [x] Task 2: Add overlay YAML parsing and validation
- [x] Task 3: Add an enrich-checkpoint upload route and UI control
- [x] Task 4: Propagate the uploaded overlay into continuation config
- [x] Task 5: Expose overlay status in run inspection
- [x] Task 6: Update docs and history for the upload workflow

## Verification Status

- [x] `python -m py_compile` passed for touched Python files
- [x] Targeted pytest slice passed with explicit node ids:

```powershell
$env:PYTHONPATH='c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Rule-filter\src'
& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe' -m pytest -q `
  tests\test_config.py::test_parse_skill_synonym_overlay_yaml_accepts_nested_skill_synonyms `
  tests\test_config.py::test_parse_skill_synonym_overlay_yaml_rejects_invalid_mapping_values `
  tests\test_config.py::test_apply_runtime_skill_synonym_overlay_merges_entries_and_runtime_metadata `
  tests\test_fitcv_cp\test_bq_store.py::test_update_run_effective_settings_updates_only_effective_settings_field `
  tests\test_fitcv_cp\test_worker_job.py::test_worker_manual_resume_uses_uploaded_run_scoped_synonym_overlay `
  tests\test_fitcv_cp\test_app.py::test_admin_run_detail_shows_synonym_overlay_upload_for_manual_enrich_checkpoint `
  tests\test_fitcv_cp\test_app.py::test_admin_upload_synonym_overlay_updates_run_effective_settings `
  tests\test_fitcv_cp\test_app.py::test_admin_upload_synonym_overlay_rejects_invalid_yaml `
  --basetemp 'c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\pytest-tmp-overlay'
```

- [x] Result: `8 passed`
