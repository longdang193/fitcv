---
layer: change
artifact_type: plan
status: completed
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

1. [x] Verify run-detail and runs-list projections map directly to runtime/stage-owned outcomes.
   - confirmed staged continue previously allowed stale checkpoint fields to overwrite terminal run truth after fast worker completion
   - patched `src/fitcv_cp/app.py` so queued/checkpoint state is persisted before enqueue on staged continue
2. [x] Ensure timeline and decision-chain labels preserve blocked/skipped/rejected distinctions.
   - verified this fix preserves terminal staged truth instead of collapsing a succeeded run into stale queued-for-continue UI semantics
3. [x] Validate run lifecycle actions stay consistent with deterministic state and event history.
   - added regression coverage in `tests/test_fitcv_cp/test_app.py` asserting status/checkpoint writes occur before enqueue
4. [x] Run targeted app tests and close with checkpoint evidence.
   - targeted pytest: `tests/test_fitcv_cp/test_app.py -k "admin_continue_run_requeues_manual_paused_run or admin_continue_run_uses_canonical_next_stage_from_completed_truth"` → pass
   - live rerun verification: `Run All` `23533bfe-4380-4162-ba4a-c5f51495a6d8` and `Stage by Stage` `c0b191a2-0784-4b2e-821b-c6d5d8425850` both finished with truthful terminal state
   - checkpoint evidence: `docs/intent/workstreams/checkpoints/workstream-operator-control-plane/operator-control-plane-run-detail-truth/20260509-0848.md`
