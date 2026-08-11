---
artifact_type: plan
status: active
layer: change
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: local-system-redirect-admin-system
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
---

# Implementation Plan: Local System Redirect To Admin System

## Goal

Change `GET /local/system` to redirect to approved target `/admin/system`.

## Historical Boundary

- Terminal runs `fitcv-lifecycle-local-system-redirect-20260806-successor3` and
  `fitcv-lifecycle-local-system-redirect-20260807-successor1` remain immutable.
- This plan is a new task identity. Never resume either terminal `run_id`.

## Task Breakdown

### Task 1: Redirect Local System To Admin System

**Coordination ID:** `local-system-redirect-admin-system`

**Required Skills:** `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv_cp/local_routes.py` — `local_system`
- `tests/test_fitcv_cp/test_local_routes.py` — closest local-route assertions

**Steps:**
1. Add a failing focused regression proving `GET /local/system` returns `302`
   with `Location: /admin/system`.
2. Make only redirect-target change needed for that contract.
3. Preserve current query parameters and redirect semantics unless current route
   behavior proves otherwise.
4. Prove preserved `/local/lifecycle/status` behavior at direct backend
   boundary.

**Verification:**
- Focused route test fails before change and passes after.
- Direct success proof covers status `302` and `Location: /admin/system`.
- Direct preserved-boundary proof covers `/local/lifecycle/status`.
- Fresh enforced read-only validator and packet `diff` check pass.

**Exit Criteria:**
- Only manifest paths change.
- Writer claim, validator claim, check evidence, and changed-path evidence
  exist before controller acceptance.
