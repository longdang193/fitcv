---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-agentic-gate-integration
targets:
  - docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/04-deterministic-truth-agentic-gate-integration.md
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
---

# Deterministic Truth Agentic Gate Integration Bootstrap Spec

## Summary

Define how agentic seams must feed deterministic acceptance truth without bypassing stage authority.

## Contract

- Agentic analysis and generation outputs are advisory until translated to stage-owned decisions.
- Gate integration preserves blocked/skipped/rejected/accepted semantics and subreasons.
- Agentic traces may enrich evidence but cannot override deterministic policy decisions.

## Acceptance Criteria

- Agentic seams preserve stage-owned status vocabulary end-to-end.
- Pipeline decision chains remain deterministic even when agentic providers vary.
- Control-plane diagnostics can explain gate outcomes from persisted stage facts.
