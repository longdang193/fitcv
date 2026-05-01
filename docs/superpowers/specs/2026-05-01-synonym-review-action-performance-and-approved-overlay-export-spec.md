---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/api.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - inspection_debugging
related_stages:
  - enrich
  - rule_filter
---

# Synonym Review Action Performance And Approved Overlay Export

## Summary

Patch synonym review actions to remove avoidable latency for both single and
batch operations, and add a direct export for the reviewed
`approved-synonym-proposals.yaml` overlay.

## Problem

Current review action path is expensive:

- batch action calls the single-action path repeatedly
- single-action resolution scans many runs (`list_runs(limit=500)`) before
  finding a proposal
- each decision incurs repeated persistence/event overhead and full page reload

Current operator export gap:

- no direct download endpoint for run-reviewed
  `approved-synonym-proposals.yaml`

## Goals

- make single action run-local and O(1)-style for proposal lookup in that run
- make batch action true in-memory batch apply with minimal writes
- preserve full audit trail semantics
- add direct approved overlay YAML export in run detail exports

## Non-Goals

- no redesign of proposal generation heuristics
- no change to HITL authority model
- no global synonym memory/promotion design in this patch

## Proposed Contract

## 1) Single Action Fast Path

Single action route (`/admin/runs/{run_id}/synonym-proposals/{proposal_id}/action`)
must:

1. load run by id
2. load proposal payload from that run
3. find proposal index in run payload
4. apply transition
5. persist run proposal payload once
6. persist run effective settings only when approve changes overlay
7. append audit event(s)

It must not call cross-run `list_runs(...)` for run-scoped action routing.

## 2) Batch Action True Bulk Apply

Batch action route (`/admin/runs/{run_id}/synonym-proposals/batch-action`) must:

1. load run + payload once
2. parse selected actions
3. validate transitions per proposal in-memory
4. apply all valid transitions in-memory
5. perform one proposal snapshot write
6. perform at most one effective-settings write when needed
7. append one summary event (with itemized result payload)

Response model must report:

- `applied_count`
- `skipped_count`
- `failed_count`
- per-item results (`proposal_id`, `requested_action`, `outcome`, `reason?`)

## 3) Approved Overlay YAML Export

Add run endpoint:

- `GET /admin/runs/{run_id}/approved-synonym-proposals.yaml`

Behavior:

- return 404 if no proposal-review overlay exists for run
- return YAML generated from current approved proposal set for that run
- include link under Run Exports when available

## 4) Backward Compatibility

- existing single proposal approve/defer/reject buttons continue working
- existing proposal JSON exports unchanged
- existing artifact bundle behavior unchanged unless explicitly extended

## Acceptance Criteria

1. Single action no longer depends on cross-run `list_runs` scan.
2. Batch action no longer loops full single-action persistence path per row.
3. Batch action returns deterministic summary counts/results.
4. `approved-synonym-proposals.yaml` is downloadable when approved overlay exists.
5. Run detail exports show approved overlay download link when applicable.
6. Audit trail remains complete for single and batch actions.

## Validation Plan

- app tests for single-action run-scoped lookup path
- app tests for batch action summary behavior and persistence minimization
- app tests for approved overlay YAML endpoint + run export link visibility
- contract gate:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. implement run-scoped helper for in-run proposal transitions
2. refactor single route to run-scoped helper
3. implement batch in-memory apply + consolidated persistence
4. add approved overlay YAML endpoint + export link
5. update docs (`docs/api.md`, `docs/observability.md`)
6. run tests + contract validator
