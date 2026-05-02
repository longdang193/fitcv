---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-component-boundary-interface-contract-spec.md
targets:
  - src/fitcv
  - src/fitcv_cp
  - config
  - docs/architecture.md
  - docs/observability.md
  - docs/usage.md
  - tests
related_features:
  - trigger_run_management
  - inspection_debugging
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

# Phase 2 Plan K Component Boundaries And Interface Contracts

**Goal:** Formalize component boundaries and dependency rules so scaling changes (storage/tooling/orchestration) do not leak across concerns.

## Scope

- define component ownership contracts for:
  - orchestration
  - evidence contract
  - telemetry
  - policy engine
  - data plane
  - AI runtime
  - control-plane API/UI
- define dependency direction and forbidden cross-component imports/calls
- map existing modules to target component ownership

## Non-Goals

- immediate full refactor of all modules
- full storage/runtime migration in this plan
- replacing existing stage contracts

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Component Contract Definition
- [ ] Publish component ownership matrix and interface contract schema.
- [ ] Define single source-of-truth ownership per concern.

## Task 2: Dependency Rules
- [ ] Define allowed dependency directions and anti-coupling rules.
- [ ] Add lightweight validation guidance/checks to prevent regressions.

## Task 3: Codebase Mapping
- [ ] Map current modules (`src/fitcv`, `src/fitcv_cp`) to target components.
- [ ] Identify high-risk shared-surface collisions and migration order.

## Task 4: Bounded Adoption Steps
- [ ] Define adoption waves that align with Plans I/J/H/G/F without delivery conflict.
- [ ] Add checkpoint templates for component-boundary passes.

## Verification

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. Component ownership and interfaces are explicit and versioned.
2. Dependency direction rules are documented and actionable.
3. Migration/adoption waves are sequenced with existing Phase-2 plans.
4. Cross-surface coupling risks are called out with bounded mitigation steps.
