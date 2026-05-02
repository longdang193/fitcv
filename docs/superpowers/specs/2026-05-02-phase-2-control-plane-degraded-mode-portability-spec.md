---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - docs/intent/workstreams/workstream-operator-control-plane.md
  - docs/observability.md
  - docs/configuration.md
  - docs/usage.md
related_features:
  - trigger_run_management
  - settings_system
related_stages:
  - enrich
  - rule_filter
  - cv_analysis
  - cv_generation
---

# Phase 2 Control Plane Degraded Mode And Portability Surface

## Summary

Define operator-facing mode and authority clarity for portability:

- operations = control plane UI

with explicit full/local/degraded mode narratives.

## Scope

- document control-plane behavior expectations when dependencies are unavailable
- preserve recommendation-vs-acceptance authority messaging
- align configuration docs for backend and mode selection narratives

## Non-Goals

- no UI redesign
- no forced backend switch in this phase

## Bounded-Thread Execution Pass Checkpoint Contract

Treat each bounded-thread execution pass under this spec as a checkpoint.

- checkpoint unit = bounded change thread
- each meaningful execution pass emits one checkpoint result pack
- pack template = `docs/operating_system/templates/checkpoint-result-pack.md`
- canonical location = `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- verification must include `python scripts/validate_checkpoint_packs.py`

## Acceptance Criteria

1. Docs define full/local/degraded mode expectations for operator surfaces.
2. Docs preserve policy authority outside control-plane ownership.
3. Config/usage docs include backend portability narratives without conflicting truth sources.
