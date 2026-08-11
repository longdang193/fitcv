---
artifact_type: plan
status: active
layer: change
coordination:
  target_branch: main
  base_ref: 6b43029d6eec0b7839da2fbd8e619bb30040d1e7
  tasks:
    - id: local-system-redirect-destination-research
      depends_on: []
      execution_mode: single_work_lane
      allowed_paths:
        - src/fitcv_cp/app.py
        - src/fitcv_cp/local_routes.py
        - tests/test_fitcv_cp/test_local_routes.py
        - docs/fitcv-settings-ui-prototype.integration.md
        - docs/usage.md
      planned_write_paths: []
---

# Research Plan: Local System Redirect Destination

## Goal

Establish one authoritative destination for `GET /local/system` before another
implementation packet exists.

## Task Breakdown

### Task 1: Resolve Destination Evidence

**Coordination ID:** `local-system-redirect-destination-research`

**Purpose:** Read bounded authoritative sources. Return a machine-readable
destination decision or a blocked result. Never edit product files.

**Files And Symbols:**
- `src/fitcv_cp/local_routes.py` — `local_system` and nearby `/local/*` routes
- `src/fitcv_cp/app.py` — mounted route registry
- `tests/test_fitcv_cp/test_local_routes.py` — existing route expectations
- `docs/fitcv-settings-ui-prototype.integration.md` — current UI-to-route map
- `docs/usage.md` — operator-facing route documentation

**Dependencies:** Request API `4`, packet API `4`, host API `3`, provider
preflight `ready`, and read-only packet workspace.

**Steps:**
1. Use only listed sources. Use at most five packet tool calls total.
2. Compare current route registry, nearby local routes, test expectations, and
   current product documentation. Do not rely on historical plans or old run
   claims as destination authority.
3. Return exactly one JSON `claimed_result` with `changed_files: []`.
4. If one destination is explicitly supported without conflict, include
   `status: "resolved"`, `destination`, and source path plus line evidence.
5. Otherwise include `status: "blocked"`, `destination: null`, and each
   missing or conflicting source. Do not guess and do not edit files.

**Verification:**
- Packet workspace remains read-only with no changed paths.
- Packet `diff` check passes.
- Controller reads claim and terminal tool count before any implementation
  packet decision.

**Exit Criteria:**
- A single explicit destination with source evidence exists, or a blocked JSON
  claim documents why evidence cannot support one.

## Deferred Host Improvement Candidate

Separate from this research and product implementation: evaluate capped shell
response size or capped prompt-discovery budget. Existing timeout observations
make oversized discovery output a contributor candidate only; they do not prove
it is the sole writer-completion cause. No host change is approved by this plan.
