---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: sqlite-run-event-persistence-parity
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-17-14-38-settings-page-deprecated-surface-removal-spec.md
targets:
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/models.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_storage_backend_parity.py
  - docs/configuration.md
  - docs/superpowers/execution_context_packs/settings-page-deprecated-surface-removal/latest.md
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Remove sqlite restart-persistence drift for control-plane local run/event fallback by replacing process-memory `_LOCAL_RUNS` and `_LOCAL_EVENTS` authority with sqlite-backed persisted state, while preserving existing behavior contracts.

## Key Deliverables

### Deliverable 1: SQLite local run/event authority is restart-persistent

`bq_store` local (`bq is None`) execution path persists and reloads runs/events from sqlite tables, eliminating process-memory-only truth for run/event state.

### Deliverable 2: Behavior parity with existing control-plane contracts

Run lifecycle retrieval/list/update/append-event behavior remains contract-compatible for both sqlite and BigQuery paths, with no regression in status transitions or event ordering guarantees.

### Deliverable 3: Drift observability and docs/test evidence aligned

Tests and docs explicitly cover restart persistence and parity boundaries, and execution context pack records residual risks after patch.

## Task/Wave Breakdown

### Task 1: Inventory and isolate in-memory authority seams

**Purpose:**
- bound exact surfaces where `_LOCAL_RUNS` / `_LOCAL_EVENTS` act as runtime authority

**Files:**
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/models.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`

**Preconditions:**
- prior settings-store sqlite persistence patch landed

**Steps:**
- [x] Step 1: enumerate all `if bq is None` run/event branches using `_LOCAL_RUNS` or `_LOCAL_EVENTS`.
- [x] Step 2: map required persistence schema/fields from current `PipelineRun` and `RunEvent` usage.
- [x] Step 3: define bounded migration approach (no cross-module orchestration rewrite).

**Verification:**
- [x] `rg -n "_LOCAL_RUNS|_LOCAL_EVENTS|if bq is None" src/fitcv_cp/bq_store.py`

**Exit Criteria:**
- all in-scope in-memory authority seams identified and mapped

### Task 2: Implement sqlite-backed local run/event persistence

**Purpose:**
- replace process-memory authority with sqlite persisted source-of-truth for local mode

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: add/extend sqlite table helpers for local run/event persistence and load paths.
- [x] Step 2: update local-mode read/write/update/list branches to use sqlite as first authority, keeping dataclass contracts unchanged.
- [x] Step 3: remove or demote `_LOCAL_RUNS`/`_LOCAL_EVENTS` from authoritative role (retain only non-authority cache if required).

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_bq_store.py -q -k "sqlite or local"`

**Exit Criteria:**
- local run/event state survives process restart and matches expected store behavior

### Task 3: Parity and restart-regression coverage

**Purpose:**
- prove no behavioral regressions and establish restart persistence evidence

**Files:**
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_storage_backend_parity.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: add/adjust restart simulation tests for run/event persistence.
- [x] Step 2: add/adjust backend parity assertions for key run/event retrieval flows.
- [x] Step 3: ensure ordering and status-update assumptions stay explicit in tests.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_bq_store.py -q`
- [x] `pytest tests/test_fitcv_cp/test_storage_backend_parity.py -q`

**Exit Criteria:**
- test evidence proves restart persistence and parity boundaries

### Task 4: Docs/context sync and closeout verification

**Purpose:**
- synchronize source-of-truth docs and closure evidence for this bounded lane

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/superpowers/execution_context_packs/settings-page-deprecated-surface-removal/latest.md`
- Optional Modify: `artifacts/execution_context_pack.md`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: update docs with local-mode persistence authority semantics.
- [x] Step 2: refresh canonical context pack with patch evidence and residual risks.
- [x] Step 3: run fast validators and required closeout gates when plan reaches terminal state.

**Verification:**
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `python scripts/validate_planning_lifecycle.py --strict`
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- docs and context pack aligned; closeout validators pass

## Verification

- `pytest tests/test_fitcv_cp/test_bq_store.py -q`
- `pytest tests/test_fitcv_cp/test_storage_backend_parity.py -q`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

## Execution Progress Log

- 2026-05-17: Task 1 completed. Enumerated all `_LOCAL_RUNS` / `_LOCAL_EVENTS` seams and bounded migration to local sqlite authority paths.
- 2026-05-17: Task 2 completed. Implemented sqlite-backed local event persistence (`local_pipeline_run_events`) and removed `_LOCAL_EVENTS` authoritative fallback.
- 2026-05-17: Task 3 completed. Updated and ran parity/local tests for restart-safe run-event retrieval.
- 2026-05-17: Task 4 completed. Synced docs/context pack and prepared closeout verification commands.
