---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
targets:
  - docs/intent/workstreams/workstream-fitcv-semantic-spine.md
  - docs/architecture.md
  - docs/pipeline.md
related_features:
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

# Phase 2 Semantic Spine Flow Authority

## Summary

Define the Phase 2 flow-authority contract:

- flow = orchestrator

and ensure docs do not blur stage ownership or checkpoint semantics.

## Scope

- clarify orchestration ownership in architecture/pipeline docs
- keep stage order and checkpoint meaning stable
- align wording with roadmap Phase 2 boundary model

## Non-Goals

- no runtime orchestration migration
- no stage behavior changes

## Bounded-Thread Execution Pass Checkpoint Contract

Treat each bounded-thread execution pass under this spec as a checkpoint.

- checkpoint unit = bounded change thread
- each meaningful execution pass emits one checkpoint result pack
- pack template = `docs/operating_system/templates/checkpoint-result-pack.md`
- canonical location = `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- verification must include `python scripts/validate_checkpoint_packs.py`

## Acceptance Criteria

1. Architecture and pipeline docs explicitly state orchestrator flow authority.
2. No conflicting language implies policy or UI owns stage progression.
3. Stage sequence semantics remain unchanged.
