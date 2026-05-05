---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - none
related_stages:
  - cv_generation
---

# Plan 3: Run-All Auto-Accept Low-Risk Gating

## Goal
Implement run-all terminalization gating so only policy-allowlisted low-risk `review_required` CV records are auto-accepted when `auto_accept_ai_action_enabled` is true, while high-risk records still park the run in `awaiting_review`.

## Key Deliverables
- Worker terminalization path applies auto-accept only for low-risk reason codes.
- `awaiting_review` behavior remains for high-risk or mixed pending review-required records.
- Auto-accept accounting is persisted in summary/event payload for traceability.
- Focused worker tests cover low-risk auto-accept and high-risk hold behavior.

## Task Breakdown
- task 1: add run-mode policy helpers in `worker_job.py`
  - read `auto_accept_ai_action_enabled` from run effective settings
  - classify reason codes from review-required records
  - define conservative low-risk allowlist and accounting
- task 2: update run-all terminalization flow
  - apply auto-accept only in run_all when enabled
  - resolve final run status from post-policy pending count
  - emit review event payload with `auto_accepted|remaining|reason_counts`
- task 3: add focused tests
  - low-risk-only review_required -> run succeeds
  - high-risk review_required present -> awaiting_continue + awaiting_review checkpoint preserved

## Verification
```powershell
pytest -q tests/test_fitcv_cp/test_worker_job.py -k "auto_accept or review_hold_uses_non_null_snapshot_timestamp"
```

## Completion Criteria
1. low-risk-only pending review-required records no longer block run_all completion when auto-accept is enabled,
2. high-risk review-required records still enforce awaiting_review,
3. terminalization behavior for manual_staged remains unchanged,
4. focused worker tests pass.
