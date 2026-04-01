---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Implement the ranking contract drift cleanup by versioning the updated ranking artifact shape, aligning admin settings copy, and syncing stale ranking docs."
---

# Ranking Contract Drift Cleanup Implementation Plan

## Scope

Implement the cleanup defined in [2026-04-01-12-15-ranking-contract-drift-cleanup-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/specs/2026-04-01-12-15-ranking-contract-drift-cleanup-spec.md) without changing six-feature ranking behavior.

This plan is intentionally narrow:

- bump the stage-transition artifact schema version for newly produced artifacts
- update any in-repo expectations that assert the old version
- fix inaccurate ranking settings descriptions in the admin schema registry
- fix stale ranking terminology in the cross-cutting pipeline explainer
- sync affected feature and stage docs plus history entries

## Source-of-Truth Alignment

Affected current-state docs:

- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)

Affected history docs:

- [docs/features/settings_system/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/history.md)
- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)

Affected code and tests:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)
- [src/fitcv_cp/settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_fitcv_cp/test_worker_job.py)

Generated refresh required:

- none

## Invariants

- The supported ranking features remain unchanged.
- The ranking decision-summary field names remain unchanged from the six-feature rollout.
- Historical artifacts stay valid as `stage_transition_artifacts_v2`.
- Newly produced artifacts after this cleanup become `stage_transition_artifacts_v3`.
- Ranking settings keys, defaults, and validation behavior remain unchanged.

## Implementation Tasks

### Task 1: Version the Changed Ranking Artifact Contract

Update [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) so newly emitted stage-transition artifacts report `schema_version: "stage_transition_artifacts_v3"`.

Acceptance criteria:

- the top-level stage-transition artifact version changes to `v3`
- the ranking block keeps the current six-feature shape
- no ranking decision-summary keys are renamed in this cleanup

### Task 2: Update In-Repo Artifact Version Expectations

Update tests and any runtime packaging expectations that currently hardcode `stage_transition_artifacts_v2` for newly produced artifacts.

Primary targets:

- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py)
- [tests/test_fitcv_cp/test_worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_fitcv_cp/test_worker_job.py)

Acceptance criteria:

- tests assert `v3` for newly built stage-transition artifacts
- ranking artifact content assertions still validate the six-feature block

### Task 3: Align Ranking Settings Copy With Runtime Semantics

Update the wording in [src/fitcv_cp/settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py) for:

- `ranking_weights.title_relevance`
- `ranking_weights.preference_fit`

Expected wording intent:

- `title_relevance` describes similarity between the job title and the candidate target role
- `preference_fit` describes candidate preference alignment such as domain and location type

Acceptance criteria:

- no key names change
- no defaults change
- no validation logic changes
- UI descriptions match runtime behavior

### Task 4: Correct Stale Cross-Cutting Ranking Terminology

Update [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) so it uses the current six-feature terminology, especially `must_have_match`.

Acceptance criteria:

- the ranking formula uses the current runtime field names
- no obsolete ranking field names remain in the ranking formula section

### Task 5: Sync Feature, Stage, and History Docs

Update these docs to reflect the cleanup:

- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)
- [docs/features/settings_system/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/history.md)
- [docs/features/inspection_debugging/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)

Acceptance criteria:

- settings-system docs mention accurate ranking feature semantics
- inspection-debugging docs mention the updated artifact version where relevant
- ranking stage docs describe the current artifact version for newly generated runs
- history entries capture the cleanup as a follow-up to the six-feature rollout

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "stage_transition_artifacts or ranking"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "stage_transition_artifacts"
```

If settings copy tests exist or are added, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_settings_schema.py
```

Manual verification checklist:

- inspect a representative stage-transition artifact payload and confirm `schema_version` is `stage_transition_artifacts_v3`
- confirm ranking `decision_summary` still contains `configured_ranking_weights`, `configured_missing_value_defaults`, `zero_weight_features`, and `contributing_features`
- confirm the admin ranking settings text now matches runtime semantics
- confirm [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) uses current ranking field names

## Risks and Mitigations

### Artifact Consumer Risk

Risk:

- a parser or test may assume newly generated artifacts are always `v2`

Mitigation:

- keep the payload shape unchanged apart from the explicit version marker
- update all in-repo version assertions in the same change

### Scope Creep Risk

Risk:

- implementation drifts back into ranking-runtime changes

Mitigation:

- treat runtime scoring as frozen for this cleanup
- reject any change that alters weights, feature construction, or ranking formulas

## Done Definition

The work is complete when:

- new stage-transition artifacts emit `stage_transition_artifacts_v3`
- targeted tests pass with the new version
- admin ranking descriptions accurately describe runtime semantics
- stale ranking terminology is removed from [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- affected feature, stage, and history docs are updated in the same rollout

## Task Status

Status: complete

- [x] Task 1: Version the changed ranking artifact contract
- [x] Task 2: Update in-repo artifact version expectations
- [x] Task 3: Align ranking settings copy with runtime semantics
- [x] Task 4: Correct stale cross-cutting ranking terminology
- [x] Task 5: Sync feature, stage, and history docs
- [x] Run targeted verification
- [x] Update plan status after implementation
