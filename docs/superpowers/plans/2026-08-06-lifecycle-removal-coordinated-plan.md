---
artifact_type: plan
status: active
layer: change
coordination:
  target_branch: main
  base_ref: HEAD
  tasks:
    - id: lifecycle-local-system-redirect
      depends_on: []
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
      planned_write_paths:
          - src/fitcv_cp/local_routes.py
          - tests/test_fitcv_cp/test_local_routes.py
    - id: lifecycle-admin-route-removal
      depends_on: [lifecycle-local-system-redirect]
      execution_mode: sequential_work_lanes
      allowed_paths:
        - src/fitcv_cp/app.py
        - src/fitcv_cp/templates/lifecycle.html
        - tests/test_fitcv_cp/test_lifecycle_removal.py
      planned_write_paths:
          - src/fitcv_cp/app.py
          - src/fitcv_cp/templates/lifecycle.html
          - tests/test_fitcv_cp/test_lifecycle_removal.py
    - id: lifecycle-contract-documentation
      depends_on: [lifecycle-admin-route-removal]
      execution_mode: sequential_work_lanes
      allowed_paths:
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md
      planned_write_paths:
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md
---

# Implementation Plan: Lifecycle Removal

## Goal

Remove user-facing Lifecycle through three bounded packet tasks. Preserve
shutdown status behavior without another same-sized timed-out scope.

## Implementation Outcomes

- `docs/fitcv-settings-ui-prototype.html` blob
  `989af611bd7767c148022c79ac00c5069d8a3956` owns visible UI truth. It excludes
  Lifecycle.
- FastAPI routes, Pydantic models, and tests own transport behavior.
- `/local/lifecycle/status` remains the shutdown-dialog resource. It is not a
  user-facing Lifecycle page.

## Outcome

Remove user-facing Lifecycle. `/admin/lifecycle` must not render a page.
`/local/system` must redirect to `/admin/system`. Preserve
`/local/lifecycle/status` and shutdown behavior.

## Execution Approach

- One task runs only after accepted predecessor evidence.
- Each task uses packet-selected `normal` writer plus fresh enforced read-only
  validator.
- No task may write outside its manifest paths. Preserve unrelated work and
  operational `.harness` records.
- Use `skill-test-driven-development` before behavior changes and
  `skill-backend-verification` for direct route proof. Browser proof never
  replaces route tests.
- No broad formatting, cleanup, commit, or route-contract invention.

## Task Breakdown

### Task 1: Redirect Legacy System Route

**Coordination ID:** `lifecycle-local-system-redirect`

**Depends on:** none

**Files:**
- `src/fitcv_cp/local_routes.py`
- `tests/test_fitcv_cp/test_local_routes.py`

**Change:** Redirect `GET /local/system` to `/admin/system`; retain
`GET /local/lifecycle/status` unchanged.

**Acceptance:**
- `GET /local/system` returns `302` with `Location: /admin/system`.
- `GET /local/lifecycle/status` retains current status contract.
- Existing local system and shutdown routes remain reachable.

**Proof:** Focused route tests; direct success, redirect, and status-resource
boundary checks; fresh validator compares route behavior and planned paths.

### Task 2: Remove Lifecycle Page Route And Template

**Coordination ID:** `lifecycle-admin-route-removal`

**Depends on:** `lifecycle-local-system-redirect`

**Files:**
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/lifecycle.html`
- `tests/test_fitcv_cp/test_lifecycle_removal.py`

**Change:** Remove `GET /admin/lifecycle` renderer and delete its template.
Do not remove `/local/lifecycle/status` or shutdown-dialog usage.

**Acceptance:**
- `GET /admin/lifecycle` has no page route.
- No runtime template reference resolves `lifecycle.html`.
- Shutdown dialog still requests `/local/lifecycle/status`.

**Proof:** New narrow regression test proves route absence and preserved status
resource; direct FastAPI boundary proof; fresh validator checks source, route
table, template lookup, and allowed paths.

### Task 3: Align Prototype Integration Documentation

**Coordination ID:** `lifecycle-contract-documentation`

**Depends on:** `lifecycle-admin-route-removal`

**Files:**
- `docs/fitcv-settings-ui-prototype.integration.md`
- `docs/superpowers/plans/2026-08-04-16-00-fitcv-prototype-runtime-parity-and-full-stack-integration-patch-plan.md`

**Change:** Record Lifecycle removal, `/local/system` redirect target, and
preserved shutdown status resource. Keep all unrelated parent-plan tasks
unchanged.

**Acceptance:**
- Integration mapping matches frozen prototype and implemented routes.
- Parent plan no longer requires direct `/admin/lifecycle` compatibility.
- Prototype hash remains `989af611bd7767c148022c79ac00c5069d8a3956`.

**Proof:** `git hash-object docs/fitcv-settings-ui-prototype.html`, focused doc
review, and fresh validator diff against Task 1 and Task 2 evidence.

## Verification

- Every task proves its direct route boundary, focused regression tests, and
  packet change-set constraint.
- Fresh enforced read-only validator compares source, route behavior, planned
  paths, and frozen prototype hash after each task.
- Run `git hash-object docs/fitcv-settings-ui-prototype.html` during Task 3.

## Completion Criteria

- `/local/system` redirects to `/admin/system`.
- `/admin/lifecycle` has no user-facing page route or template.
- `/local/lifecycle/status` and shutdown dialog behavior remain intact.
- Task 3 documentation matches implemented routes and prototype truth.

## Controller Escalation Rule

If a packet writer times out, controller records `escalate` while run awaits
decision. Do not create another same-sized request. Split approved scope into
the next ready manifest task and bind a fresh packet to that task.
