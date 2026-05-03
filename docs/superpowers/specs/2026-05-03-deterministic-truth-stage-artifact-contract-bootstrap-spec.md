---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-stage-artifact-contract
targets:
  - docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/02-deterministic-truth-stage-artifact-contract.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
---

# Deterministic Truth Stage Artifact Contract Bootstrap Spec

## Summary

Define the authoritative stage artifact shape and ownership rules so decision truth and evidence stay stage-scoped and replay-safe.

## Contract

- Stage artifacts are stage-owned and immutable once emitted for a run step.
- Stage result envelope is canonical: `output`, `evidence`, `validation`, `decision`, `policy_version`, `trace_context`.
- Operator and export surfaces must read from stage artifacts, not infer alternate truth.

## Acceptance Criteria

- Runtime stores stage results with canonical envelope fields.
- Worker snapshots preserve policy and trace context for stage-result summaries.
- Run detail surfaces render stage-owned outcomes without flattening subreasons.
