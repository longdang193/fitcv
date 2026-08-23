---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-p0-integration-recovery
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/superpowers/plans/2026-08-22-12-00-fitcv-p0-integration-recovery-plan.md
---

# FitCV P0 Integration Recovery Patch Plan

## Goal

Repair three proven Run + Scan integration owners from the accepted bootstrap
state, prove each with focused regression tests, obtain independent validation,
and rerun only P10, P16, P17, and P18. Do not rerun the full 25-probe suite.

## Implementation Outcomes

### Run Details renders from the source control-plane store

`GET /admin/runs/{run_id}` renders successfully when a persisted candidate
profile snapshot exists. Candidate-profile JSON parsing uses the module's
canonical JSON alias and no longer raises `NameError`.

### Run job projection conserves persisted source occurrences

`GET /runs/{run_id}/jobs?stage=all` returns every persisted `run_jobs` row,
including duplicate job occurrences with distinct `run_job_id` and
`source_index`, while stage-specific filters retain their existing semantics.

### Run event projection reads canonical pipeline events

`GET /runs/{run_id}/events` returns persisted `process_events` written with
`process_type='pipeline'`, preserving event order, pagination metadata, and
the existing response envelope.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `deepagents`
- Required skills: `skill-executing-plans`, `skill-deepagents-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared files, add regression tests, run focused tests, run isolated live probes P10/P16/P17/P18, run validated DeepAgents validation
- User-approval actions: commit, push, merge, destructive cleanup, discard, changes outside declared ownership, full 25-probe execution
- Parallel ownership: `none`
- Sequential fallback: lead controller writes tests and fixes, then dispatches one independent validator

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `441d9bb4c611ea025c407a2af68b3c1a1aa4ed6d`
- Active task(s): `none`
- Expected workspace: `main` with preserved sample-data changes and no accepted bootstrap changes reopened
- Next action: run separate 25-probe P0 integration task
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `dcode-project --role high` | none | red tests, green focused tests, backend boundary proof, independent validator PASS, P10/P16/P17/P18 live results | base `441d9bb4`; final verification passed; no commit |

## Task Breakdown

### Task 1: Recover three P0 integration owners

**Purpose:**
- Restore Run Details, job occurrence conservation, and pipeline event projection without changing accepted bootstrap or broader Scan/Run architecture.

**Task Function:**
- Implement and validate a narrow integration recovery patch.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: three coupled backend/API defects with live evidence, persistence semantics, and integration proof.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: independent source review, regression execution, scope reconciliation, and proof review.

**Specification Coverage:**
- Fix Run Details HTTP 500 caused by `json` alias mismatch.
- Make `stage=all` include pending persisted job occurrences and preserve stable identity fields.
- Query canonical pipeline process events for Run event projection.
- Preserve canonical `sqlite_store` ownership, accepted bootstrap commit, user sample-data changes, and the separate 25-probe task.

**Required Skills:**
- `skill-executing-plans`
- `skill-deepagents-executing-plans`
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect/modify: `src/fitcv_cp/app.py: get_run_events_list`, `src/fitcv_cp/app.py: admin_run_detail`
- Inspect/modify: `src/fitcv_cp/sqlite_store.py: _filtered_run_job_rows`
- Modify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `config/runtime/control_plane.yaml`, isolated runtime root `C:\tmp\fitcv-p0-20260822`

**Dependencies:**
- Accepted bootstrap commit `441d9bb4` remains base.
- Existing sample-data changes remain untouched.
- Existing Scan + Run plan remains untouched.

**Authority:**
- Preauthorized local actions: declared source/test edits, focused tests, read-only SQLite inspection, isolated server lifecycle, four named live probes, and one bounded DeepAgents validator.
- Stop for: plan/Git mismatch, missing provider/runtime prerequisites, failed regression proof, validator `FAIL` or `BLOCKED`, scope drift, or any need to rerun all 25 probes.

**Steps:**
- [x] Step 1: Add minimal failing tests for Run Details JSON parsing, `stage=all` job conservation, and pipeline event projection; run them red.
- [x] Step 2: Apply smallest owner fixes in `app.py` and `sqlite_store.py`; rerun focused tests green.
- [x] Step 3: Run backend boundary and integration checks, `git diff --check`, and inspect changed-file scope.
- [x] Step 4: Dispatch independent `dcode-project --role high` validator with validated handoff facts; accept only `PASS` with evidence.
- [x] Step 5: Rerun only P10, P16, P17, and P18 against isolated runtime and record status, artifacts, provider errors, and Git drift.

**Verification:**
- [x] Focused regression tests fail before fixes and pass after fixes.
- [x] `py -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q` passes: `581 passed`.
- [x] Direct API boundary checks prove Run Details HTTP 200, all 7 persisted job occurrences returned with source indexes 0 through 6 and 7 distinct IDs, and 34 ordered pipeline events returned.
- [x] Independent validator returns `PASS` with repository-relative evidence and confirms no edits, commits, live probes, or full 25-probe run.
- [x] P10, P16, P17, and P18 pass on isolated source runtime at `http://127.0.0.1:8901`; evidence: `C:\tmp\fitcv-p0-20260822\recovery-probes-20260822.json`.
- [x] `git diff --check` passes and only declared files plus preserved user changes remain.

**Exit Criteria:**
- Three proven owners fixed with focused regression proof, independent validator PASS, and four named P0 probes rerun successfully or with exact expected outcomes.
- No full 25-probe run, bootstrap redesign, unrelated sample-data mutation, or unauthorized commit occurs.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- `git diff --check`
- Isolated runtime readiness and P10/P16/P17/P18 probe commands from accepted evidence harness
- Final `git status --short --branch` and `git diff --stat`

## Completion Criteria

The plan is ready for completion verification when:

1. all three owner fixes are implemented at canonical owners;
2. red-green regression evidence exists for each defect;
3. focused backend and API boundary proof passes;
4. independent DeepAgents validation returns `PASS`;
5. only P10, P16, P17, and P18 are rerun and their evidence is recorded;
6. accepted bootstrap, user sample-data changes, and the existing Scan/Run plan remain intact;
7. final Git scope and `git diff --check` pass;
8. no commit or full 25-probe run occurs without separate authorization.

Only `skill-verification-before-completion` may change this plan to `completed`
after returning `verified`.
