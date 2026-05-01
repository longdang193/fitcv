---
doc_id: usage
doc_type: operator-guide
explains:
  features:
    - inspection_debugging
    - settings_system
    - trigger_run_management
  stages:
    - cv_analysis
    - cv_generation
    - ranking
---

# Usage

FitCV has two main usage tracks:

- **operator usage** through the admin UI and run-detail surfaces
- **engineering usage** through local runtime, tests, and managed-doc workflows

This page is a current-state summary, not the detailed contract for every
screen or stage.

## Operator Workflow

The main entrypoint is:

```text
http://localhost:8000/admin/runs
```

A typical operator flow is:

1. trigger a run from uploaded files, pasted JSON, or path-based input
2. choose `Run All` or `Stage by Stage`
3. inspect stage progress, run health, and timeline events
4. open run detail to review job outcomes and stage-owned artifacts
5. download exports such as:
   - run results
   - CV debug data
   - settings used
   - mapping suggestions
   - approved synonym overlay YAML (run-approved delta only)
   - global synonym YAML (full canonical map)
   - stage artifacts
   - artifact bundles
6. continue, cancel, archive, or repair a run when lifecycle action is needed

The settings surface at `/admin/settings` is part of normal operator use when
runtime tuning is required.

When using `/admin/settings`, keep the truth hierarchy in mind:

1. the page edits future-run defaults, not past runs
2. fixed runtime-owned fields may appear as metadata instead of editable inputs
3. per-run overrides are captured at trigger time
4. `settings-used.json` on a completed run is the historical source of truth

Within `/admin/settings`, the `Agentic` section is where operators adjust the
bounded agentic defaults that actually affect future runs. Use that section for
late-stage agentic enablement and semantic-alignment tuning, then use run
detail plus `settings-used.json` on completed runs to confirm what a specific
run actually used and did.

For synonym review flows:

1. review run-scoped proposals in run detail
2. approve/defer/reject (single or batch)
3. optionally export approved overlay YAML (delta-only)
4. promote approved rows to global with preview/confirm

Promotion is merge/overlay behavior, not full replacement of the canonical
global synonym file.

## Engineering Workflow

The everyday engineering loop is:

1. update code, config, or docs
2. run the web and worker locally or through Docker
3. use the admin UI and API surfaces to validate behavior
4. run targeted tests
5. run repo contract checks before merging

For doc and metadata work, the standard checks are:

```powershell
python scripts/sync_architecture_docs.py --check
python scripts/validate_repo_contracts.py --fast
```

## Useful Runtime Surfaces

Primary API and UI surfaces include:

- `GET /healthz`
- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /admin/runs`
- `GET /admin/runs/{run_id}`
- `GET /admin/settings`

The admin run-detail page is the most important inspection surface because it
pulls together stage progress, artifacts, exports, and lifecycle actions.

## What To Read Next

- [setup.md](setup.md) for startup and environment expectations
- [pipeline.md](pipeline.md) for stage flow and checkpoint model
- [architecture.md](architecture.md) for the runtime and managed-doc layout
- [FitCV-pipeline.md](FitCV-pipeline.md) for the fuller pipeline explainer
