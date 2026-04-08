---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Align final succeeded `Stage by Stage` artifacts with the already-correct reranker-blocked truth contract used by `Run All`."
invariants:
  - "Succeeded `Run All` and succeeded `Stage by Stage` runs must emit the same reranker-blocked artifact truth for equivalent pipeline outcomes."
  - "`blocked_by_reranker_fit` remains distinct from `skipped_fit_gate`."
  - "The fix stays narrow: no broad artifact redesign, no run-mode contract rollback, and no change to reranker short-circuit runtime behavior."
---

# Staged Final Artifact Reranker-Truth Alignment

## Triage

Feature type: MODIFY  
Summary: Fix the succeeded `Stage by Stage` final-artifact finalization path so reranker-blocked rows land in `results.json` and `cv-debug.json` with the same truth contract already emitted by succeeded `Run All` runs.  
Reasoning: The latest bundles show that `Run All` is already emitting the correct post-fix contract, while `Stage by Stage` still finalizes some reranker-blocked rows using older compact-status and coverage semantics. This is a mode-specific artifact finalization drift, not a pipeline-stage algorithm difference.  
Invariants:
- Equivalent final outcomes must serialize identically across `Run All` and `Stage by Stage`
- `blocked_by_reranker_fit` rows must not degrade to `ranked_no_cv` or `not_run`
- `cv-debug.json` must count reranker-blocked ranked jobs as explicit non-attempted rows
- Existing artifact versioning and run-mode metadata remain intact
Dependencies:
- `src/fitcv_cp/worker_job.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py` only if consumer wording depends on stale staged-only values
Affected stages:
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/cv_system/history.md`
    - `docs/features/trigger_run_management/history.md`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The latest artifact bundles show a mode-specific truth drift in the final succeeded export path.

For succeeded `Run All` runs:

- reranker-blocked jobs serialize as `pipeline_status = "ranked_blocked_by_reranker_fit"`
- compact `decision_chain.cv_analysis.status` also says `blocked_by_reranker_fit`
- `cv-debug.json` counts reranker-blocked ranked jobs as explicit non-attempted rows

For succeeded `Stage by Stage` runs:

- the row-level `cv_analysis.status` correctly says `blocked_by_reranker_fit`
- but compact `decision_chain.cv_analysis.status` still falls back to `not_run`
- `pipeline_status` still falls back to `ranked_no_cv`
- `cv-debug.json` can omit reranker-blocked ranked jobs entirely from non-attempted coverage

This makes the same runtime outcome appear differently depending on execution mode.

## Evidence

### Correct `Run All` bundle

Run `cb29d3d6-94fd-4359-bf20-dbd6501c53a0`:

- [manifest.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/manifest.json)
- [results.json#L86](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/results.json#L86): `pipeline_status = "ranked_blocked_by_reranker_fit"`
- [results.json#L98](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/results.json#L98): row-level `cv_analysis.status = "blocked_by_reranker_fit"`
- [results.json#L112](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/results.json#L112): compact `decision_chain.cv_analysis.status = "blocked_by_reranker_fit"`
- [cv-debug.json#L11](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/cv-debug.json#L11): `non_attempted_ranked_jobs_total = 2`
- [cv-debug.json#L12](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/cv-debug.json#L12): omission reason `blocked_by_reranker_fit`

### Incorrect `Stage by Stage` bundle

Run `a9272d8f-9edc-4d52-b8a3-16e35be8bdd0`:

- [manifest.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/manifest.json)
- [results.json#L86](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/results.json#L86): `pipeline_status = "ranked_no_cv"`
- [results.json#L98](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/results.json#L98): row-level `cv_analysis.status = "blocked_by_reranker_fit"`
- [results.json#L112](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/results.json#L112): compact `decision_chain.cv_analysis.status = "not_run"`
- [cv-debug.json#L11](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/cv-debug.json#L11): `non_attempted_ranked_jobs_total = 0`
- [cv-debug.json#L12](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/cv-debug.json#L12): omission reasons empty

### Shared stage-local truth is already aligned

Both runs already agree in stage-local `cv_analysis` artifacts:

- [cb29 cv_analysis.json#L14](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-cb29d3d6-94fd-4359-bf20-dbd6501c53a0-artifacts/cv_analysis.json#L14)
- [a927 cv_analysis.json#L14](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a9272d8f-9edc-4d52-b8a3-16e35be8bdd0-artifacts/cv_analysis.json#L14)

Both report:

- `blocked_by_reranker_fit = 2`
- `generation_ready = 1`

So the drift is in final run-scoped artifact finalization, not in stage-local pipeline output.

## Root Cause

The succeeded `Stage by Stage` finalization path is still reconstructing some final run-scoped fields from an older compact-status/coverage model.

That stale path appears to affect:

- compact row-level final `pipeline_status`
- compact `decision_chain.cv_analysis`
- CV-debug non-attempted ranked-job coverage accounting

`Run All` already uses the corrected truth path, which is why the drift shows up only in staged final bundles.

## Goals

1. Make succeeded `Stage by Stage` final artifacts truth-identical to succeeded `Run All` for the same reranker-blocked outcomes.
2. Keep the fix narrow and avoid changing the already-correct `Run All` path.
3. Preserve the current artifact versions unless the contract changes again materially during implementation.

## Proposed Design

### 1. Unify final run-scoped artifact truth at the shared finalization boundary

Ensure the final succeeded artifact builders consume the same normalized final outcome facts for both modes.

Specifically, for reranker-blocked rows in both modes:

- `pipeline_status = "ranked_blocked_by_reranker_fit"`
- `cv_analysis.status = "blocked_by_reranker_fit"`
- `decision_chain.cv_analysis.status = "blocked_by_reranker_fit"`
- `decision_chain.cv_analysis.completed = false`
- `cv_generation.status = "not_attempted"`
- `cv_generation.attempted = false`

### 2. Make CV-debug coverage mode-independent at final success

For both modes, `cv-debug.json` must:

- treat reranker-blocked ranked jobs as explicit non-attempted ranked jobs
- include them in `omission_reason_counts.blocked_by_reranker_fit`
- report `snapshot_complete = true` when every ranked job is either attempted or explicitly accounted for as a non-attempted ranked job

### 3. Preserve stage-local ownership

Do not redesign:

- `cv_analysis.json`
- `cv_generation.json`
- `stage-artifacts.json`
- the artifact bundle layout

The fix should only align the run-scoped final ledger and coverage surfaces with the stage-local truth they already receive.

## Non-Goals

- Tightening upstream rule filtering
- Reworking reranker thresholds
- Redesigning artifact versions or bundle contents again
- Changing the reranker short-circuit runtime behavior

## Acceptance Criteria

1. A succeeded `Run All` bundle and a succeeded `Stage by Stage` bundle with the same final outcomes serialize reranker-blocked rows the same way in `results.json`.
2. `Stage by Stage` no longer emits `pipeline_status = "ranked_no_cv"` for reranker-blocked rows.
3. `Stage by Stage` no longer emits `decision_chain.cv_analysis.status = "not_run"` for reranker-blocked rows.
4. `Stage by Stage` `cv-debug.json` counts reranker-blocked ranked jobs in non-attempted coverage exactly as `Run All` does.
5. Stage-local `cv_analysis` and `cv_generation` artifact shapes remain unchanged.

## Expected Docs to Update

- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [inspection_debugging history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
- [trigger_run_management history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/history.md)
- [cv_system history](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- generated discovery under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated)

