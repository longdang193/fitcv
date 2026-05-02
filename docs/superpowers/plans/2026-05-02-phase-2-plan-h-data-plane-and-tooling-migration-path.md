---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-control-plane-degraded-mode-portability-spec.md
targets:
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/models.py
  - config
  - docs/architecture.md
  - docs/configuration.md
  - docs/usage.md
related_features:
  - settings_system
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan H Data Plane And Tooling Migration Path

**Goal:** Establish a safe migration path from current BigQuery-first runtime to scalable multi-backend architecture without breaking current operations.

## Scope

- introduce storage/artifact interface boundaries (ports/adapters)
- keep BigQuery adapter as current default
- define migration path toward Postgres + object storage
- add telemetry/tooling integration path (OTel/Langfuse now-compatible; ClickHouse/MLflow later)

## Non-Goals

- full cutover to Postgres in this plan
- orchestrator migration to Dagster in this plan

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Adapter Boundary Introduction
- [ ] Define store interfaces for run state, events, and artifacts.
- [ ] Wrap current BigQuery implementation behind adapter boundary.
- [ ] Keep existing behavior unchanged under default config.

## Task 2: Runtime Mode + Backend Selection
- [ ] Add configuration keys for backend and mode selection (`full/local/degraded`).
- [ ] Ensure app boots in local/degraded modes with clear capability status signaling.

## Task 3: Migration Strategy Artifacts
- [ ] Document dual-write strategy and cutover checkpoints.
- [ ] Define telemetry split path (transactional state vs high-volume analytics).

## Task 4: Tooling Roadmap Stitching
- [ ] Ensure OTel-compatible IDs remain first-class in artifacts/events.
- [ ] Add docs guidance for Langfuse/MLflow/ClickHouse adoption phases without forcing immediate dependency switch.

## Verification

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. Adapter boundaries exist and BigQuery remains functional as default.
2. Runtime/backend mode contracts are documented and visible to operators.
3. Migration path to Postgres/object storage is implementation-ready.
4. Tooling roadmap is explicitly staged (now vs later) without ambiguity.
