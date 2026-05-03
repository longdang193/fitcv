---
thread_id: workstream-agentic-observability.agentic-observability-otel-id-and-trace-context-alignment
status: completed
---

# agentic-observability-otel-id-and-trace-context-alignment

## Goal

Define Phase 2 trace-context alignment for observability surfaces:

- traces = OTel-compatible IDs

with consistent `trace_id`/`span_id` semantics across run-scoped artifacts.

## Why Now

Current observability is rich but portable cross-system correlation needs explicit ID-compatibility guidance before expanding spec sets.

## Dependencies

shared trace standard thread; provider provenance thread; operator run-detail truth thread

## Shared Surfaces

observability docs; run artifacts; event timeline payload conventions

## Linked Spec

- docs/superpowers/specs/2026-05-02-phase-2-observability-otel-trace-context-spec.md

## Linked Plan

- docs/superpowers/plans/2026-05-03-phase-2-master-closeout-matrix.md

## Notes

This thread governs trace identity and portability, not policy-gate decisions.
Trace-context portability is now evidenced in completed Phase 2 OTel/export and StageResult envelope implementation checkpoints.
