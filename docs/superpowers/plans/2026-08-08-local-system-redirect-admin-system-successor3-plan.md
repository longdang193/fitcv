---
artifact_type: plan
status: active
layer: change
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: local-system-redirect-admin-system-successor3
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
---

# Implementation Plan: Local System Redirect To Admin System — Successor 3

## Goal

Change `GET /local/system` to redirect to approved target `/admin/system`.

## Implementation Outcomes

### Redirect Contract

`GET /local/system` returns `302` with `Location: /admin/system`, preserving
existing query-parameter and redirect semantics unless current route behavior
proves otherwise.

### Boundary Proof

Focused route coverage proves redirect contract and direct backend coverage
proves `/local/lifecycle/status` remains unchanged.

## Execution Approach

- Mode: `sequential_work_lanes`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`
- Isolation: `current workspace`
- Commit policy: `external authorization`
- Parallel ownership: `none`
- Sequential fallback: `one writer lane, then enforced read-only validator`

## Historical Boundary

- Previous identity `local-system-redirect-admin-system-successor2` is terminal
  and excluded from this plan.
- This plan creates only `local-system-redirect-admin-system-successor3`.

## Task Breakdown

### Task 1: Redirect Local System To Admin System

**Coordination ID:** `local-system-redirect-admin-system-successor3`

**Files And Symbols:**
- `src/fitcv_cp/local_routes.py` — `local_system`
- `tests/test_fitcv_cp/test_local_routes.py` — closest local-route assertions

**Dependencies:** None.

**Steps:**
1. Add failing focused regression proving `GET /local/system` returns `302`
   with `Location: /admin/system`.
2. Make only redirect-target change needed for that contract.
3. Preserve current query parameters and redirect semantics unless current route
   behavior proves otherwise.
4. Prove preserved `/local/lifecycle/status` behavior at direct backend
   boundary.

## Verification

- Focused route test fails before change and passes after.
- Direct success proof covers status `302` and `Location: /admin/system`.
- Direct preserved-boundary proof covers `/local/lifecycle/status`.
- Fresh enforced read-only validator and packet `diff` check pass.

## Completion Criteria

- Only manifest paths change.
- Writer claim, validator claim, check evidence, and changed-path evidence
  exist before controller acceptance.
