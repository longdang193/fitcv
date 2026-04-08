---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Fix premature run-detail exports, restore a direct normalize-stage artifact link for paused runs, and make run-health metrics stage-aware instead of treating 0/0 as healthy."
invariants:
  - Stage-owned downloads must not appear before the owning stage has been reached.
  - Timeline artifact links must stay attached to aggregate stage lifecycle rows rather than per-job subevents.
  - Paused manual runs must still expose the latest completed stage artifact without relying on a separate fallback export surface.
  - Run Health must distinguish not-reached, not-applicable, and healthy states.
---

# Run-Detail Stage Gating And Pending-Health Fix

## Triage

Feature type: MODIFY  
Summary: Fix three run-detail contract gaps around premature mapping exports, missing normalize-stage download ownership, and misleading `0/0` health semantics.  
Reasoning: This is an existing inspection surface whose current behavior drifts from both the intended stage-ownership model and the operator expectation that diagnostics should reflect real stage progress. The work is a targeted behavior correction, not a new feature family.  
Invariants:
- A stage-owned artifact must not be visible or downloadable before its stage has been reached.
- The normalize stage artifact already exists after normalize and should become reachable through the normal timeline ownership model, not a one-off fallback button.
- `Run Health` must never imply success for a stage that has not been reached.
- Health semantics should remain compact and operator-readable.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- stage-transition artifact generation in `normalize`, `enrich`, `shortlist`, `ranking`, `cv_analysis`, and `cv_generation`
Affected stages:
- normalize
- enrich
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- `inspection_debugging`
- `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs: none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Migration needed: no
Risk level: medium

## Problem

Three run-detail issues are still visible to operators:

1. `Mapping Suggestions JSON` can still appear before `enrich`, even though its owning stage has not completed and the payload is effectively empty.
2. A paused manual run after `normalize` can have a real normalize artifact in the stage bundle but no direct stage download link in the timeline.
3. `Run Health` metrics with `0/0` are still easy to misread as a positive result instead of a stage-progress placeholder.

These are related, but they do not share the same root cause:

- the mapping issue is primarily an **artifact persistence timing** problem
- the normalize download issue is primarily a **timeline ownership/event emission** problem
- the health issue is primarily a **semantic classification** problem

## Goals

- Prevent stage-owned artifacts from being persisted or surfaced before the owning stage is reached.
- Ensure paused runs after `normalize` expose a direct normalize download through the standard timeline ownership model.
- Make `Run Health` explicitly stage-aware so `Pending`, `N/A`, and `Healthy` are clearly different states.
- Keep the run-detail page compact and consistent with the existing stage-centric diagnostics model.

## Non-Goals

- Reintroducing a generic `Latest Stage` export fallback on run detail.
- Moving stage downloads back onto per-job timeline rows.
- Replacing the existing stage-transition artifact architecture.
- Removing `Run Health` or hiding all unfinished-stage metrics entirely.

## Source-Of-Truth Alignment

Current feature/state contracts:

- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [normalize.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/normalize.yaml)
- [enrich.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/enrich.yaml)

Primary implementation targets:

- [worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/worker_job.py)
- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- [test_worker_job.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_worker_job.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_pipeline.py)

## Detailed Findings And Design

## 1. Mapping Suggestions Must Not Persist Before `enrich`

### Root Cause

`mapping_suggestions_json` is currently created from checkpoint summary data even before `enrich` has been reached. That means the run may already carry a formally valid artifact blob with:

- schema version
- created timestamp
- empty `suggestions`

Even if the run-detail UI later tries to gate visibility correctly, the artifact already exists too early and can leak through any weaker visibility logic.

### Design

Treat mapping suggestions as an `enrich`-owned artifact at both layers:

1. **Persistence ownership**
- do not persist `mapping_suggestions_json` until the run has actually reached `enrich`
- before `enrich`, absence is the correct state, not an empty artifact

2. **Visibility ownership**
- run detail should only show `Mapping Suggestions JSON` when:
  - `enrich` has been reached
  - the run has an enrich stage artifact
  - a mapping-suggestions payload exists

3. **Endpoint ownership**
- download endpoints must return not found before `enrich`
- empty but premature payloads are not valid substitutes for stage ownership

### Required Outcome

For a paused-after-normalize run:
- `Mapping Suggestions JSON` is absent from the UI
- direct download endpoint is unavailable

For a run that has reached `enrich`:
- the link appears normally
- the payload reflects the enrich-stage output contract

## 2. Normalize Artifact Download Must Be Owned By A Real Normalize Timeline Row

### Root Cause

The normalize stage artifact already exists after `normalize`, but the run detail only exposes stage downloads on recognized aggregate stage rows. Today, the aggregate normalize row is only emitted when deduplication removed at least one job. If no duplicates were removed, a paused-after-normalize run can have:

- `stage_transition_artifacts.normalize`
- a checkpoint row saying `Paused after normalize`
- no dedicated `Normalize` stage row that owns the download link

That creates the false impression that no normalize artifact exists.

### Design

Normalize needs a stable aggregate stage row regardless of whether deduplication removed anything.

### Required Behavior

After `normalize`, the pipeline should always emit an aggregate normalize lifecycle event that:

- represents the normalize stage completion
- includes the normalize summary message
- can own the `Download Normalize JSON` link

This event must exist whether dedupe removed:

- many jobs
- one job
- zero jobs

### Why This Design Is Better Than A Fallback Export

The artifact already belongs to the normalize stage. The correct fix is to restore stage ownership in the timeline, not invent a separate run-level fallback action such as `Download Normalize JSON (Latest Stage)`.

That preserves the existing information architecture:

- timeline rows own stage downloads
- run exports own run-scoped bundles and run-scoped ledgers

## 3. `Run Health` Must Distinguish `Pending`, `N/A`, And `Healthy`

### Root Cause

The current health surface is still too denominator-centric. A `0/0` metric can mean at least two very different things:

1. the owning stage has not been reached yet
2. the stage was reached, but there were no eligible rows for that metric

Those should not both collapse into a healthy-looking state.

### Design

Health severity must become stage-aware.

### Status Semantics

#### `Pending`

Use when:
- the owning stage has not been reached yet

Display:
- neutral/muted styling
- label: `Pending`
- rate shown as `—`

#### `N/A`

Use when:
- the owning stage was reached
- denominator is zero because the metric had no eligible rows

Display:
- neutral but distinct from `Pending`
- label: `N/A`
- rate shown as `—`

#### `Healthy` / `Watch` / `Needs Attention`

Use only when:
- the owning stage has been reached
- denominator is greater than zero

Display:
- severity-colored treatment
- percent plus numerator/denominator

### Contract Requirement

The UI must not infer health solely from `0/0`. It must combine:

- metric numerator/denominator
- owning stage reachability
- stage status when available

### Example

For a paused-after-normalize run:

- shortlist metrics -> `Pending`
- ranking metrics -> `Pending`
- cv_analysis metrics -> `Pending`
- cv_generation metrics -> `Pending`

For a completed run with no generation-ready jobs:

- cv_generation accepted rate -> `N/A`
- cv_generation validation-fail rate -> `N/A`

This keeps the surface honest without hiding structurally useful metrics.

## UI And Messaging Rules

### Run Exports

- `Mapping Suggestions JSON` must not appear before `enrich`
- `Stage Artifacts JSON (Diagnostics)` may remain visible whenever the bundle exists

### Event Timeline

- `Normalize` aggregate row must appear for all normalize completions
- `Download Normalize JSON` belongs on that row
- checkpoint rows remain checkpoint rows and do not become stage-download owners

### Run Health

- not-yet-reached stages render as `Pending`
- reached-but-not-applicable metrics render as `N/A`
- only reached-and-measured metrics render severity colors

## Testing Requirements

Add focused coverage for:

1. **Mapping suggestions persistence and gating**
- no `mapping_suggestions_json` before enrich
- no link before enrich
- endpoint unavailable before enrich
- normal link after enrich

2. **Normalize timeline ownership**
- paused-after-normalize run with zero dedupes still gets a normalize aggregate timeline row
- that row owns the normalize artifact download

3. **Run health semantics**
- unreached stage metric -> `Pending`
- reached stage with zero denominator -> `N/A`
- reached stage with positive denominator -> severity based on rate

## Documentation Impact

Update:

- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)

Refresh generated discovery after source-of-truth docs are updated.

## Recommendation

Implement this as a narrow correction pass:

1. fix mapping-suggestions ownership at persistence plus visibility
2. make normalize always emit a download-owning aggregate row
3. make `Run Health` stage-aware with explicit `Pending` and `N/A`

That solves the operator-facing confusion without reopening the broader run-detail redesign.
