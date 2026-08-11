---
artifact_type: plan
template_id: implementation-plan
name: local-system-redirect-admin-system-successor9
status: active
layer: change
targets:
  - src/fitcv_cp/local_routes.py
  - tests/test_fitcv_cp/test_local_routes.py
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: local-system-redirect-admin-system-successor9
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
---

# Implementation Plan: Local System Redirect To Admin System — Successor 9

## Goal

Change `GET /local/system` to return `302 Location: /admin/system`.

## Source Facts

- `local_system` returns `RedirectResponse("/admin/lifecycle", status_code=302)`.
- `local_system` does not forward request query parameters.
- `GET /local/lifecycle/status` returns `JSONResponse(local_lifecycle_status_resource(request))`.
- Target paths are clean at base `6b43029d6eec0b7839da2fbd8e619bb30040d1e7`.

## Historical Boundary

- Successors 2 through 8 are terminal blocked evidence and remain untouched.
- This plan creates only `local-system-redirect-admin-system-successor9`.
- Do not copy a prior request, packet, run state, or provider binding.

## Admission

- Current policy owns request API `5`, route skill resolution, operating profile, and execution budget. Locked core resolves current packet API; do not force a legacy packet API.
- Host must resolve a fresh immutable `provider_runtime_binding` at admission from trusted `stdio` preflight. Planning evidence is host API `6`, provider contract `6`, and configuration digest `c1c5b1e42e8748f9efcf167bcd8177b32293af2a579df3fc06fa4a257b70bffe`; recheck before packet creation.
- Required route skill set is `local_change_base`; select optional `backend_verification` for HTTP route behavior.
- Dispatch requires current ready host capabilities and clean packet-base evidence.

## Task Breakdown

### Task 1: Redirect Local System To Admin System

**Coordination ID:** `local-system-redirect-admin-system-successor9`

**Dependencies:** None.

**Owned Paths:**
- `src/fitcv_cp/local_routes.py` — `local_system`
- `tests/test_fitcv_cp/test_local_routes.py` — focused route regression

**Required Skills:**
- `skill-executing-plans`
- `skill-test-driven-development`
- `skill-backend-verification`

**Steps:**
1. Add a focused failing `TestClient` regression for `GET /local/system?tab=advanced` with redirects disabled. Assert `302` and exact `Location: /admin/system`.
2. Add direct boundary coverage that `GET /local/lifecycle/status` remains `200` JSON with existing `system`, `active_work_reasons`, and `capabilities` keys.
3. Change only `local_system` redirect target from `/admin/lifecycle` to `/admin/system`; retain status `302` and fixed-location query behavior.
4. Run focused local-route test file red before source change and green after source change.

**Verification:**
- Direct backend boundary proof: `uv run pytest tests/test_fitcv_cp/test_local_routes.py -q`.
- Packet-selected diff check, change-set scope check, and enforced read-only validator.

**Exit Criteria:**
- Only owned paths change.
- `/local/system` returns exact `302 Location: /admin/system`.
- Query remains absent from `Location`.
- `/local/lifecycle/status` remains unchanged.
- Writer claim and validator evidence exist before controller acceptance.
