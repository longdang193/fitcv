---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/models.py
  - docs/observability.md
  - docs/api.md
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# HITL-First Agentic-Assisted Synonym Review Policy

## Summary

Adopt a policy where synonym proposal governance is always human-in-the-loop
(HITL), while agentic components provide recommendation support and batch
review acceleration.

This policy keeps decision authority with operators, improves review speed, and
preserves deterministic audit truth across runs.

## Problem

Current synonym proposal operations are slow and inconsistent for larger runs:

- actions are often performed one proposal at a time
- deferred/rejected/approved intent is tracked run-scoped but not consistently
  leveraged for review assistance
- no explicit policy boundary enforces human approval before meaningful reuse

## Goals

- enforce HITL as the default and required decision authority model
- introduce agentic recommendation assistance without autonomous mutation
- support batch review actions with per-row override
- retain complete run-scoped audit trail and deterministic replay

## Non-Goals

- no fully autonomous global synonym mutation
- no removal of run-scoped artifact snapshots
- no replacement of deterministic proposal generation logic

## Policy Contract

## 1) HITL Is Mandatory For Decision Finalization

- proposals may be generated and recommended automatically
- proposal state transitions to approved/rejected/deferred require human action
- no proposal may be globally promoted without explicit human confirmation

## 2) Agentic Assistance Is Advisory

Per proposal, assistant may emit:

- recommended action: `approve` / `defer` / `reject`
- confidence and rationale
- conflict/risk flags

These are suggestions only; final action remains operator-owned.

## 3) Batch Review Is First-Class

Run detail must support:

- per-row action selection (`keep_pending`, `approve`, `defer`, `reject`)
- optional “apply recommendation to selected/all filtered”
- single batch submit endpoint for selected proposals
- partial-success response model with applied/skipped/failed counts

## 4) Scope Model

- run-scoped decision record is always written for each run
- optional global promotion is explicit, separate, and audited
- global policy memory (future extension) must not bypass HITL gate

## 5) Audit Requirements

For every decision (single or batch), store:

- proposal id + run id
- previous and next status
- actor
- timestamp
- optional note
- if recommendation existed: recommended action, recommendation confidence,
  recommendation rationale snapshot

## 6) Reuse Policy Compatibility

Policy must be compatible with `OFF` / `ASSISTED` / `STRICT` reuse modes:

- regardless of mode, run-scoped decision records are still created
- mode affects prefill/recommendation and reuse behavior, not HITL authority

## Acceptance Criteria

1. Operators can review and submit decisions in batch for synonym proposals.
2. Human confirmation is required for any state-changing approval/rejection.
3. Agent recommendations are visible but never auto-finalized.
4. Audit trail records both recommendation context and human action context.
5. Existing single-action flows remain functional for backward compatibility.

## API Surface (Proposed)

- `POST /admin/runs/{run_id}/synonym-proposals/batch-action`
  - request: list of `{proposal_id, action, note?}`
  - response: `{applied_count, skipped_count, failed_count, results[]}`

- optional preview endpoint:
  - `POST /admin/runs/{run_id}/synonym-proposals/batch-preview`
  - returns proposed transitions and validation warnings before commit

## Validation Plan

- app tests for batch action success/partial failure/state conflict handling
- app tests for recommendation visibility + human override path
- worker/app tests for audit payload completeness
- validator gate:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. add batch action route + service logic
2. add run-detail batch UI controls
3. add recommendation display fields (advisory only)
4. add/expand audit payloads and exports
5. run tests + repo contract validation
