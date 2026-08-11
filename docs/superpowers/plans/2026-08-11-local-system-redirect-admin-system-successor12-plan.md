---
artifact_type: plan
template_id: implementation-plan
name: local-system-redirect-admin-system-successor12
status: active
layer: change
targets:
  - src/fitcv_cp/local_routes.py
  - tests/test_fitcv_cp/test_local_routes.py
coordination:
  target_branch: main
  base_ref: 135817b2cb11947f50b2b992b2c9abbb0c942fa8
  tasks:
    - id: local-system-redirect-admin-system-successor12
      depends_on: []
      execution_mode: single_work_lane
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      verification_checks:
        local-system-redirect-focused-pytest:
          - uv
          - run
          - pytest
          - tests/test_fitcv_cp/test_local_routes.py::test_local_system_redirects_to_admin_system
          - -q
        local-system-redirect-semantic:
          - uv
          - run
          - python
          - -c
          - >-
            import asyncio; from fastapi.templating import Jinja2Templates; from fitcv_cp.local_routes import build_local_router; router = build_local_router(Jinja2Templates(directory="src/fitcv_cp/templates")); route = next(item for item in router.routes if getattr(item, "path", None) == "/local/system"); response = asyncio.run(route.endpoint(None)); assert response.status_code == 302; assert response.headers["location"] == "/admin/system"
---

# Implementation Plan: Local System Redirect To Admin System — Successor 12

## Goal

Change `GET /local/system` to return exact `302 Location: /admin/system`.

## Historical Boundary

- Successors 10 and 11 are terminal `blocked`; retain packets, claims, and terminal evidence unchanged.
- This task creates only `local-system-redirect-admin-system-successor12`.
- Do not inspect or edit historical `.harness` evidence.

## Task Breakdown

### Task 1: Redirect Local System To Admin System

**Coordination ID:** `local-system-redirect-admin-system-successor12`

**Owned Paths:**
- `src/fitcv_cp/local_routes.py`
- `tests/test_fitcv_cp/test_local_routes.py`

**Required Work:**
1. Add `test_local_system_redirects_to_admin_system` using existing `local_client` with redirects disabled. Assert query remains absent, status is `302`, and `Location` is exactly `/admin/system`.
2. Run that focused test red before source change.
3. Change only `local_system` redirect target from `/admin/lifecycle` to `/admin/system`.
4. Run focused test green.
5. Return exactly one JSON `claimed_result` with nonempty `summary` and string-list `changed_files` containing both owned paths.

**Packet Verification:**
- Packet-owned `diff` check.
- Host-owned focused pytest check.
- Host-owned semantic route postcondition checking exact status and `Location` from registered `/local/system` handler.
- Change-set requires both owned paths.
- Enforced read-only validator.
