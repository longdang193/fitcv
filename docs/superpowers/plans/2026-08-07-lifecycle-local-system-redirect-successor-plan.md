---
artifact_type: plan
status: active
layer: change
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: lifecycle-local-system-redirect-successor
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
---

# Implementation Plan: Local System Redirect Successor

## Goal

Resolve the incorrect `GET /local/system` redirect without weakening terminal
run evidence or reusing the blocked Task 1 run.

## Historical Handoff

- Supersedes execution only, not evidence, from blocked run
  `fitcv-lifecycle-local-system-redirect-20260806-successor3`.
- That run used packet API `3` and provider contract `2`; its writer completed
  shell calls but returned no claim before the default and escalated timeouts.
- Preserve its immutable `run.json`, timeout observations, and terminal
  `blocked` state. Never resume its `run_id`.
- This successor binds current request API `4`, packet API `4`, and host API
  `3` through current policy and host admission.

## Task Breakdown

### Task 1: Determine And Correct Local System Redirect

**Coordination ID:** `lifecycle-local-system-redirect-successor`

**Purpose:** Find authoritative intended destination, then change only
`GET /local/system` redirect behavior.

**Required Skills:** `skill-test-driven-development`,
`skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv_cp/local_routes.py` — `local_system`
- `tests/test_fitcv_cp/test_local_routes.py` — closest route regression test

**Dependencies:** Current managed admission must prove request API `4`, packet
API `4`, host API `3`, and enforced sequential validator capability.

**Steps:**
1. Inspect route registry, route tests, product documentation, and nearby
   `/local/*` routes for intended destination. Do not infer from the obsolete
   redirect.
2. If evidence conflicts or no authority names a destination, return a blocked
   writer claim. Do not edit product files.
3. Add a failing focused regression test for current incorrect redirect.
4. Make smallest redirect-only change that preserves query parameters,
   authorization behavior, unrelated routes, and response semantics.
5. Run focused tests and direct route-boundary proof: redirect success plus
   preserved `/local/lifecycle/status` behavior.

**Verification:**
- Fresh focused route-test output demonstrates fail before change, pass after.
- Direct backend proof covers redirect status and `Location`, plus preserved
  status-resource boundary.
- Enforced read-only validator compares allowed paths, source, tests, route
  behavior, and claim evidence.
- Packet `diff` check passes after validator.

**Exit Criteria:**
- Destination has authoritative evidence, or packet records blocked missing or
  conflicting evidence with no product change.
- Any change stays within manifest paths and has focused regression proof.
- Writer claim, validator evidence, and packet check evidence exist before
  controller decision.
