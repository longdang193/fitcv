---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-prefect-orchestration-adoption
---

# 2026-05-02 Phase 2 Prefect Orchestration Adoption Spec

## Summary

Introduce Prefect orchestration behind a stable adapter boundary while preserving FitCV stage semantics, checkpoint behavior, and operator lifecycle truth.

## Scope

- orchestration adapter with default runtime + Prefect runtime implementations
- lifecycle state mapping compatibility
- checkpoint/continue compatibility

## Non-Goals

- stage logic redesign
- policy decision redesign

## Acceptance

1. Prefect mode is available behind adapter boundary.
2. Existing control-plane run actions remain behavior-compatible.
3. Checkpoint/continue semantics are preserved and test-covered.
