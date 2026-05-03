---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-results-ledger-contract
targets:
  - docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/03-deterministic-truth-results-ledger-contract.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
---

# Deterministic Truth Results Ledger Contract Bootstrap Spec

## Summary

Define results-ledger truth rules so per-job terminal outcomes remain reconstructable from stage-owned subreasons.

## Contract

- `results.json` remains a compact canonical ledger, never a secondary narrative source.
- Each late-stage row must preserve deterministic outcome plus stage-owned subreason.
- Results exports and timeline summaries must resolve to the same canonical outcome vocabulary.

## Acceptance Criteria

- `results.json` rows preserve stable deterministic outcome mapping.
- No export surface discards stage-owned subreason for blocked/skipped/rejected states.
- Worker persistence and control-plane views agree with the ledger contract.
