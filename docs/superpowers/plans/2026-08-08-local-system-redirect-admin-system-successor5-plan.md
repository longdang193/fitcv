---
artifact_type: plan
template_id: implementation-plan
name: local-system-redirect-admin-system-successor5
status: active
layer: change
targets:
  - src/fitcv_cp/local_routes.py
  - tests/test_fitcv_cp/test_local_routes.py
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: local-system-redirect-admin-system-successor5
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
---

# Implementation Plan: Local System Redirect To Admin System — Successor 5

## Goal

Change `GET /local/system` to redirect to `/admin/system`.

## Source Facts

- `local_system` currently returns `RedirectResponse("/admin/lifecycle", status_code=302)`.
- Current route ignores its `Request`; query parameters are not forwarded.
- `GET /local/lifecycle/status` returns `local_lifecycle_status_resource(request)` as JSON.

## Historical Boundary

- Successor2 and successor3 are terminal blocked and remain untouched.
- Successor4 remains nonterminal `running` after an external host timeout-recording failure. This plan neither resumes nor mutates successor4.
- This plan creates only `local-system-redirect-admin-system-successor5`.

## Execution Approach

- Mode: `sequential_work_lanes`.
- Route: `local_change` with route-owned required skill sets.
- Optional facet: `backend_verification` for HTTP route behavior changes.
- Operating profile: route default only.
- Timeout handling: packet-approved escalation only.

## Task Breakdown

### Task 1: Redirect Local System To Admin System

**Coordination ID:** `local-system-redirect-admin-system-successor5`

**Purpose:** Replace retired lifecycle redirect target with canonical system page.

**Specification Coverage:** `GET /local/system` returns `302` and `Location: /admin/system`; `/local/lifecycle/status` stays available and unchanged.

**Required Skills:** Route-resolved required sets plus optional `backend_verification`.

**Files And Symbols:**
- `src/fitcv_cp/local_routes.py` — `local_system`
- `tests/test_fitcv_cp/test_local_routes.py` — focused local-route regression

**Dependencies:** None.

**Steps:**
1. Add focused failing test for `GET /local/system` with redirects disabled; assert `302` and exact `Location: /admin/system`.
2. Include a request query in that test and assert exact fixed location; current source proves query parameters are not forwarded.
3. Change only `local_system` redirect target from `/admin/lifecycle` to `/admin/system`; keep `302`.
4. Add direct route assertion that `GET /local/lifecycle/status` remains `200` JSON with existing `system`, `active_work_reasons`, and `capabilities` keys.

**Verification:**
1. Run focused `tests/test_fitcv_cp/test_local_routes.py` regression before and after change.
2. Run packet-resolved checks and enforced read-only validator.

**Exit Criteria:**
- Only task manifest paths change.
- Writer claim, validator claim, packet diff proof, and fresh test output exist before acceptance.
