---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-results-ledger-contract
parent_spec: docs/superpowers/specs/2026-05-03-deterministic-truth-results-ledger-contract-bootstrap-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_worker_job.py
---

# Deterministic Truth Results Ledger Contract Bootstrap Plan

## Steps

1. Confirm deterministic outcome + stage subreason mapping in results ledger rows.
2. Ensure export/status projections preserve blocked/skipped/rejected distinctions.
3. Validate persisted summaries remain consistent with `results.json` truth.
4. Run targeted tests and validator scripts.
