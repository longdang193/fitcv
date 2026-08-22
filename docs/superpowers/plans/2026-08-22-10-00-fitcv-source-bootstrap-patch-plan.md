---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-source-mode-database-bootstrap
targets:
  - src/fitcv_cp/main.py
  - tests/test_fitcv_cp/test_main.py
---

# FitCV Source-Mode Database Bootstrap Patch Plan

## Goal

Recover and accept existing uncommitted source-mode bootstrap changes under one
narrow Git-tracked task. Source startup must establish current control-plane
SQLite schema through existing `sqlite_store` contract before creating app.

Existing diff predates plan activation. It is recovered into this task and is
not treated as previously accepted work.

## Implementation Outcomes

### Source startup readiness

Source mode resolves `runtime.sqlite_path`, resolves configured candidate profile
path from existing config/env layer, calls `ensure_control_plane_database()`
before `create_app()`, and never duplicates schema or migration SQL.

### Regression and acceptance evidence

Focused tests prove fresh, empty schema-0, current-schema, incompatible,
non-openable, ordering, and Local-mode behavior. Isolated live probes prove
schema 5, SQLite integrity, required tables, normal routes, and non-destructive
incompatible-storage failure.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `deepagents`
- Required skills: `skill-executing-plans`, `skill-deepagents-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`; commit requires separate authorization
- Preauthorized local actions: inspect and verify existing in-scope diff, update plan state, run focused tests and isolated live probes
- User-approval actions: commit, push, merge, destructive cleanup, discard, or changes outside declared ownership
- Parallel ownership: `none`
- Sequential fallback: `lead controller performs verification after bounded validator`

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `efd3b735a4c1a52c14f965be1b5c0f5891354c91`
- Active task(s): `none`
- Expected workspace: `main` with preserved sample-data changes and existing bootstrap diff
- Next action: Runtime Readiness Gate from accepted bootstrap state
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `dcode-project --role high` | none | focused tests, isolated live probes, independent validator PASS | worker proof passed; DeepAgents validator PASS |

## Task Breakdown

### Task 1: Recover, verify, and accept source bootstrap

**Purpose:**
- Accept or reject existing changes in `src/fitcv_cp/main.py` and `tests/test_fitcv_cp/test_main.py` without reimplementation.

**Task Function:**
- Recover existing implementation, execute backend verification, and reconcile acceptance evidence.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: material startup/backend behavior with schema compatibility and non-destructive failure risk.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: independent source, Git-scope, regression, fresh-database, live-route, and incompatible-storage validation.

**Specification Coverage:**
- Source mode bootstraps missing and empty schema-0 databases through canonical initializer.
- Current schema remains idempotent.
- Nonempty incompatible schema-0 and unopenable storage fail before app creation without reset.
- Local mode keeps existing initialization ownership.
- Unrelated sample-data changes remain untouched.

**Required Skills:**
- `skill-executing-plans`
- `skill-deepagents-executing-plans`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:ensure_control_plane_database`
- Inspect: `src/fitcv_cp/local_app.py:database initialization`
- Modify or accept: `src/fitcv_cp/main.py:build_app`
- Modify or accept: `tests/test_fitcv_cp/test_main.py:source startup regression tests`
- Verify: `config/runtime/control_plane.yaml`, `config/env.private.yaml`, `start_web.ps1`

**Dependencies:**
- Existing uncommitted candidate diff is present.
- Completed Scan/Run plan remains untouched.

**Authority:**
- Preauthorized local actions: inspect, test, isolated temporary database probes, and update this plan ledger.
- Stop for: scope drift, preserved-data mutation, plan/Git mismatch, validator BLOCKED/FAIL, or destructive storage action.

**Steps:**
- [x] Step 1: Activate plan after readiness review and reconcile existing diff with Task 1 ownership.
- [x] Step 2: Run focused, SQLite/control-plane, Local storage, compile, and diff checks.
- [x] Step 3: Run isolated source success and incompatible-storage live probes.
- [x] Step 4: Run independent DeepAgents validator and require `PASS` first — PASS; focused tests 12, schema 13, Local 19.
- [x] Step 5: Reconcile Git and evidence, update task ledger, then request final verification.

**Verification:**
- [x] `py -m pytest -q tests/test_fitcv_cp/test_main.py` — 12 passed.
- [x] `py -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py -k schema` — 17 passed, 108 deselected.
- [x] `py -m pytest -q tests/test_fitcv_cp/test_local_storage.py` — 19 passed.
- [x] `py -m compileall -q src/fitcv_cp/main.py tests/test_fitcv_cp/test_main.py` — passed.
- [x] `git diff --check` — passed.
- [x] Isolated source startup — schema 5, integrity `ok`, required tables, `/healthz`, `/runs`, `/candidate-profiles`, `/scans` all 200.
- [x] Isolated incompatible schema-0 startup — exit 1, `DatabaseSchemaIncompatibleError`, schema 0, preserved value `keep`.
- [x] Independent validator result begins `PASS` — `dcode-project --role high`; canonical owner, source ordering, Local skip, propagated errors, and Git scope confirmed.

**Exit Criteria:**
- Existing implementation satisfies acceptance criteria, fresh worker proof passes, independent validator returns `PASS`, plan/Git agree, and no unrelated change is staged or modified.

## Verification

- `py scripts/validate_planning_lifecycle.py --strict`
- `git diff --check`
- Fresh focused and isolated live evidence recorded in Task 1.

## Completion Criteria

1. Task 1 has accepted implementation and validator evidence.
2. Canonical schema ownership remains in `src/fitcv_cp/sqlite_store.py`.
3. Source and Local bootstrap behavior remain symmetric without duplicate initialization.
4. Incompatible storage remains non-destructive and fails before normal app creation.
5. Preserved sample-data changes remain untouched.
6. Final verification returns `verified` before plan status changes to `completed`.
