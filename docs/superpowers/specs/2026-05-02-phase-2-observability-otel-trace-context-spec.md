---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-otel-id-and-trace-context-alignment
targets:
  - docs/intent/workstreams/workstream-agentic-observability.md
  - docs/observability.md
  - docs/api.md
related_features:
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# Phase 2 Observability OTel Trace Context

## Summary

Standardize trace identity language around OTel-compatible IDs:

- traces = OTel-compatible IDs

while preserving existing FitCV run artifact surfaces.

## Scope

- define `trace_id` / `span_id` / parent linkage expectations in docs
- map existing run-trace artifacts to this identity model
- clarify trace data vs decision authority boundaries

## Non-Goals

- no immediate backend/tool migration mandate
- no replacement of existing trace artifacts

## Bounded-Thread Execution Pass Checkpoint Contract

Treat each bounded-thread execution pass under this spec as a checkpoint.

- checkpoint unit = bounded change thread
- each meaningful execution pass emits one checkpoint result pack
- pack template = `docs/operating_system/templates/checkpoint-result-pack.md`
- canonical location = `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- verification must include `python scripts/validate_checkpoint_packs.py`

## Acceptance Criteria

1. Observability docs define OTel-compatible trace context fields.
2. API/artifact narratives stay consistent with existing run exports.
3. Decision authority remains documented outside observability ownership.
