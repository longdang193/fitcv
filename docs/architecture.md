---
doc_id: architecture
doc_type: architecture-guide
explains:
  features:
    - cv_system
    - inspection_debugging
    - settings_system
    - trigger_run_management
  components:
    - src/fitcv
    - src/fitcv_cp
---

# Architecture

FitCV combines a control plane, a staged background pipeline, shared runtime
configuration, and a managed architecture-metadata documentation layer.

## Runtime Components

### Control plane

`src/fitcv_cp/` owns:

- the FastAPI app and HTML admin surfaces
- run triggering and lifecycle actions
- settings management
- run-detail inspection and exports
- queue handoff and worker integration
- BigQuery-backed persistence adapters for run state and events

### Pipeline runtime

`src/fitcv/` owns:

- stage execution logic
- candidate/job normalization and enrichment
- deterministic filtering, shortlist retrieval, and ranking
- CV analysis and CV generation
- contracts, evidence handling, validation, and repair behavior

### Supporting services

- Redis provides the queue backend
- RQ provides background execution
- BigQuery persists run rows, events, structured intermediate data, and CV
  outputs

## System Boundaries

The main runtime boundary is between:

1. the operator-facing control plane that captures inputs, snapshots settings,
   and exposes inspection
2. the worker-driven pipeline that executes staged processing and emits
   artifacts and events

Control flow moves through trigger -> enqueue -> worker -> checkpoint/continue
-> terminal run state. Data flow moves through input capture -> staged job
artifacts -> persisted results -> operator inspection and export.

## Managed Documentation Architecture

This repo uses `managed_architecture_metadata`, not a docs-as-freeform model.

The important ownership split is:

- human-owned:
  - `docs/features/<feature_id>/feature.source.yaml`
  - `docs/stages/<stage_id>.source.yaml`
  - root and operating-system docs that describe repo-wide behavior
- generated:
  - `docs/features/<feature_id>/<feature_id>.yaml`
  - `docs/features/<feature_id>/lineage.generated.yaml`
  - `docs/stages/<stage_id>.yaml`
  - `docs/generated/*.yaml`

That means generated YAML should be refreshed through the wrapper, not edited by
hand.

## Canonical Sync And Validation

Refresh and validate managed architecture surfaces with:

```powershell
python scripts/sync_architecture_docs.py
python scripts/sync_architecture_docs.py --check
python scripts/validate_repo_contracts.py --fast
```

## Where To Go Deeper

- [pipeline.md](pipeline.md) for the stage flow
- [configuration.md](configuration.md) for runtime config and override layering
- [setup.md](setup.md) for local and Docker startup
- [docs/generated/architecture_dag.yaml](generated/architecture_dag.yaml) for
  generated topology
- [docs/generated/capability_lineage.yaml](generated/capability_lineage.yaml)
  for generated capability evidence
