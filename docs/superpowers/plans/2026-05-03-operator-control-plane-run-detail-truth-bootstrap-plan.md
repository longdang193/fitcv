---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_app.py
---

# Operator Control Plane Run Detail Truth Bootstrap Plan

## Steps

1. Verify run-detail and runs-list projections map directly to runtime/stage-owned outcomes.
2. Ensure timeline and decision-chain labels preserve blocked/skipped/rejected distinctions.
3. Validate run lifecycle actions stay consistent with deterministic state and event history.
4. Run targeted app tests and close with checkpoint evidence.
