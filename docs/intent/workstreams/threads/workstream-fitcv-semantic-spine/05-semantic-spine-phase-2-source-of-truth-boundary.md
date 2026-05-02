---
thread_id: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
status: proposed
---

# semantic-spine-phase-2-source-of-truth-boundary

## Goal

Lock the Phase 2 source-of-truth boundary for flow ownership:

- flow = orchestrator

while preserving original stage order, stage meaning, and checkpoint semantics.

## Why Now

Phase 2 architecture hardening can accidentally drift semantics unless flow ownership is explicitly constrained at thread level before downstream specs and plans.

## Dependencies

master roadmap phase-2 section; stage authority contract; checkpoint truth contract

## Shared Surfaces

master roadmap; semantic-spine workstream docs; stage source contracts

## Notes

This thread is boundary-setting only. It does not redesign stages or replay behavior.

