---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-prefect-orchestration-adoption
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-prefect-orchestration-adoption-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv/pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
  - docs/architecture.md
  - docs/usage.md
related_features:
  - trigger_run_management
  - run_lifecycle_controls
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan I Prefect Orchestration Adoption

**Goal:** Implement Prefect-backed orchestration via an adapter boundary while preserving FitCV stage semantics and existing operator workflows.

## Scope

- introduce orchestration interface boundary for run lifecycle execution
- keep existing worker path as default fallback until Prefect mode is validated
- implement Prefect run submit/observe/cancel mapping to current control-plane semantics
- preserve checkpoint and continue behavior contracts

## Non-Goals

- stage logic redesign
- deterministic acceptance policy redesign
- forcing immediate removal of existing queue/worker runtime

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Orchestrator Adapter Boundary
- [ ] Define orchestration interface (`submit`, `status`, `cancel`, `continue`) and run mapping contract.
- [ ] Implement default current-runtime adapter and Prefect adapter behind same interface.

## Task 2: Prefect Execution Path
- [ ] Add Prefect-backed run submission and lifecycle wiring.
- [ ] Map Prefect lifecycle states to existing run statuses without semantics drift.

## Task 3: Checkpoint + Continue Compatibility
- [ ] Preserve manual staged checkpoint/continue invariants under Prefect mode.
- [ ] Verify continue uses canonical next-stage semantics.

## Task 4: Operator Surface + Verification
- [ ] Keep control-plane actions and status visibility unchanged from operator perspective.
- [ ] Add tests covering run/stop/continue across default adapter and Prefect adapter.

## Verification

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py
python -m pytest tests/test_pipeline.py
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. Prefect orchestration is available behind adapter boundary.
2. Existing operator lifecycle actions remain behavior-compatible.
3. Checkpoint/continue truth remains intact and test-covered.
4. Default fallback path remains functional if Prefect unavailable.
