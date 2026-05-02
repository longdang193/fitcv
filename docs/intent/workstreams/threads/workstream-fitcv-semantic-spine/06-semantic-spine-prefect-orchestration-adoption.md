---
thread_id: workstream-fitcv-semantic-spine.semantic-spine-prefect-orchestration-adoption
status: proposed
---

# semantic-spine-prefect-orchestration-adoption

## Goal

Adopt Prefect as the orchestration implementation boundary while preserving FitCV stage order, stage meaning, checkpoint semantics, and current operator-visible run truth.

## Why Now

Phase 2 currently defines `flow = orchestrator` as a source-of-truth boundary, but lacks a bounded execution thread to implement Prefect adoption safely.

## Dependencies

semantic-spine phase-2 source-of-truth boundary thread; checkpoint-and-continue truth thread; operator control-plane trigger/mode contract thread

## Shared Surfaces

worker orchestration path; control-plane lifecycle endpoints; checkpoint payload contracts; run lifecycle tests

## Notes

This thread introduces an orchestrator adapter boundary and Prefect-backed implementation path. It does not redefine stage logic or deterministic acceptance authority.
