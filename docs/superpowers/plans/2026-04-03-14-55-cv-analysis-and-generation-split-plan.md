---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement the split of the current final CV stage into sequential `cv_analysis` and `cv_generation` stages with separate artifacts and resumable checkpoints."
---

# CV Analysis and Generation Split Implementation Plan

## Scope

Implement the stage split defined in [2026-04-03-14-40-cv-analysis-and-generation-split-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/superpowers/specs/2026-04-03-14-40-cv-analysis-and-generation-split-spec.md).

This plan keeps the rollout intentionally bounded:

- insert a new `cv_analysis` stage between `ranking` and `cv_generation`
- keep `ranking` as the sole owner of authoritative post-filter ranking fit
- move evidence retrieval, gap analysis, and Layer 4 fit-gate preparation into `cv_analysis`
- make `cv_generation` consume persisted `cv_analysis` outputs rather than recomputing them by default
- emit separate bounded stage-transition artifact blocks for `cv_analysis` and `cv_generation`
- add staged/manual pause-resume support at both new Layer 4 boundaries

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/trigger_run_management/trigger_run_management.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/ranking.yaml)
- new: `docs/stages/cv_analysis.yaml`
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/inspection_debugging/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/trigger_run_management/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/evidence.py)
- [gap_analysis.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/gap_analysis.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/cv_generator.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/validator.py)
- [worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv_cp/worker_job.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/tests/test_pipeline.py)
- [test_worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/tests/test_fitcv_cp/test_worker_job.py)
- any focused tests added for stage-artifact/debug payload changes

Generated refresh required:

- yes

## Invariants

- Ranking remains the sole owner of authoritative post-filter ranking fit labels and ranked-job selection.
- `cv_analysis` must not persist accepted or rejected final CV versions.
- `cv_generation` must consume explicit `cv_analysis` outputs rather than silently recomputing evidence retrieval and fit-gate logic by default.
- `cv_analysis` and `cv_generation` each emit their own bounded stage-transition artifact blocks.
- Manual staged mode must pause after `cv_analysis` and resume into `cv_generation` using persisted checkpoint payloads.
- Existing run-results export and CV debug download surfaces remain supported during rollout.

## Implementation Tasks

### Task 1: Add the New `cv_analysis` Stage Contract and Stage Sequence

Update the runtime stage model so `cv_analysis` becomes an explicit stage between `ranking` and `cv_generation`.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- new: `docs/stages/cv_analysis.yaml`
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/cv_generation.yaml)

Changes:

- add `cv_analysis` to the pipeline stage sequence
- update stage validation helpers and checkpoint summary helpers
- update stage-transition artifact builder so it knows about the new stage key

Acceptance criteria:

- the pipeline stage sequence is `normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`
- `cv_analysis` is treated as a first-class stage in both continuous and manual-staged execution
- unreached or partial runs still emit interpretable stage blocks

### Task 2: Extract Layer 4 Analysis into `cv_analysis`

Split the current monolithic Layer 4 logic so `cv_analysis` owns preparation and gating only.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- helper modules only if small targeted extraction improves clarity

Changes:

- move ranked-plus-enriched merge into analysis-owned flow
- move evidence retrieval into `cv_analysis`
- move gap analysis into `cv_analysis`
- move Layer 4 fit-gate resolution into `cv_analysis`
- produce one `analysis_record` per ranked job
- produce `generation_ready_jobs` for jobs that should proceed

Acceptance criteria:

- `cv_analysis` can explain which jobs are ready for writing and which are blocked
- `cv_generation` no longer needs to decide or rediscover evidence/gap/fit inputs during normal execution
- the runtime data shape is explicit and bounded

### Task 3: Refactor `cv_generation` to Consume Analysis Outputs

Make `cv_generation` a pure generation/validation/persistence stage over `generation_ready_jobs`.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/cv_generator.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/validator.py) only if needed for clearer stage boundaries

Changes:

- feed `generate_cv(...)` from analysis-prepared inputs
- keep validation and repair in `cv_generation`
- keep persistence in `cv_generation`
- keep accepted / validation_failed / generation_failed / persistence_failed outcomes in the generation-owned debug records

Acceptance criteria:

- `cv_generation` no longer recomputes evidence retrieval, gap analysis, or fit-gate results by default
- accepted CV version persistence remains unchanged in semantics
- generation failures are isolated from analysis failures

### Task 4: Split Stage Artifacts and CV Debug Payload Ownership

Update the artifact system so `cv_analysis` and `cv_generation` have separate bounded blocks and the debug payload reflects the two-stage lifecycle.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- [worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv_cp/worker_job.py)

Changes:

- add `stage_transition_artifacts.cv_analysis`
- narrow `stage_transition_artifacts.cv_generation` to generation-only behavior
- evolve CV debug records so analysis and generation statuses are distinguishable
- keep payloads bounded and reviewer-friendly

Acceptance criteria:

- `cv_analysis` artifact shows analysis counts, evidence/gap context, and fit-gate outcomes
- `cv_generation` artifact shows generation, validation, repair, and persistence outcomes
- run-scoped debug/export surfaces remain compatible while becoming more stage-accurate

### Task 5: Update Manual Staged Checkpoints and Resume Flow

Make `cv_analysis` and `cv_generation` separate resumable checkpoints in the admin control plane.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- [worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv_cp/worker_job.py)
- any run-detail template or status copy only if the checkpoint names are surfaced explicitly there

Changes:

- `ranking` should pause with `next_stage = cv_analysis`
- `cv_analysis` should pause with `next_stage = cv_generation`
- the checkpoint payload stored after `cv_analysis` must be sufficient for `cv_generation`
- resume logic should not need to reconstruct analysis from older stages by default

Acceptance criteria:

- manual runs can pause after `cv_analysis`
- resuming from `cv_generation` uses analysis checkpoint payloads successfully
- stage resume tests cover the new handoff

### Task 6: Keep Exports and Inspection Backward-Compatible During Rollout

Preserve existing operator surfaces while aligning them to the new two-stage ownership model.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/src/fitcv/pipeline.py)
- any inspection/export helpers already used by run detail and downloads

Changes:

- keep run-results export working for accepted/skipped/failed Layer 4 jobs
- ensure decision-chain/export records still read coherently with the split
- add additive fields rather than destructive shape changes where practical

Acceptance criteria:

- current run-detail/debug/export flows still work
- operators can tell analysis skip from generation failure
- rollout does not require a parallel custom viewer

### Task 7: Sync Feature, Stage, History, and Generated Docs

Update the source-of-truth docs and generated discovery outputs once runtime behavior is in place.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/trigger_run_management/trigger_run_management.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/ranking.yaml)
- new: `docs/stages/cv_analysis.yaml`
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/cv_generation.yaml)
- history files listed above
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs match the new sequential Layer 4 model
- stage contracts and feature contracts tell the same story
- generated discovery reflects the added stage and updated capabilities

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "cv_generation or cv_analysis or checkpoint or resume"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "manual or checkpoint or cv_generation"
```

If artifact/debug payload tests are split further, run the focused slices that cover:

- stage-transition artifact shape
- run-results export shape
- CV debug snapshot shape

Manual verification checklist:

- run a staged/manual flow and confirm pause after `ranking` leads to `cv_analysis`
- confirm pause after `cv_analysis` leads to `cv_generation`
- inspect both stage artifact downloads and confirm they are distinct and bounded
- confirm a fit-gate skip appears in `cv_analysis`, not as a generation failure
- confirm accepted CV generation still persists and downloads correctly

## Risks and Mitigations

### Boundary Drift Risk

Risk:

- logic could remain duplicated between `cv_analysis` and `cv_generation`, making the split cosmetic rather than real

Mitigation:

- keep the analysis payload explicit and make `cv_generation` consume it directly

### Backward-Compatibility Risk

Risk:

- run-detail exports or debug JSON may break if the record shape changes too abruptly

Mitigation:

- keep additive compatibility fields during the rollout
- update stage ownership without destructive export removal

### Resume Complexity Risk

Risk:

- manual staged checkpoint payloads may miss derived variables and fail on resume

Mitigation:

- add dedicated resume tests for `ranking -> cv_analysis` and `cv_analysis -> cv_generation`
- recompute derived debug variables from restored checkpoint state where needed

## Done Definition

The work is complete when:

- `cv_analysis` exists as a first-class stage between `ranking` and `cv_generation`
- `cv_analysis` owns evidence retrieval, gap analysis, and fit-gate preparation
- `cv_generation` owns writing, validation, repair, and persistence
- both stages emit their own bounded artifact blocks
- manual staged runs can pause after `cv_analysis` and resume into `cv_generation`
- run inspection and exports remain usable during the rollout
- targeted tests pass
- affected docs and generated discovery are updated in the same rollout

## Task Status

Status: completed

- [x] Task 1: Add the new `cv_analysis` stage contract and stage sequence
- [x] Task 2: Extract Layer 4 analysis into `cv_analysis`
- [x] Task 3: Refactor `cv_generation` to consume analysis outputs
- [x] Task 4: Split stage artifacts and CV debug payload ownership
- [x] Task 5: Update manual staged checkpoints and resume flow
- [x] Task 6: Keep exports and inspection backward-compatible during rollout
- [x] Task 7: Sync feature, stage, history, and generated docs
- [x] Run targeted verification
- [x] Update plan status after implementation
