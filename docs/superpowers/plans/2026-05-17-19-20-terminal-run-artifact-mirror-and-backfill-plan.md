---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: terminal-run-artifact-mirror-and-backfill
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-17-17-33-synonym-proposal-review-gateway-and-dedicated-workspace-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - scripts/
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

## Goal

Eliminate artifact-storage ambiguity by ensuring every terminal run has deterministic filesystem artifact mirror at `artifacts/live_run_<run_id>/`, with safe backfill path for historical runs that only exist in DB.

## Key Deliverables

### Deliverable 1: Terminal-run filesystem mirror is deterministic

On run terminalization (`succeeded`, `failed`, `cancelled`), control plane writes canonical artifact files into `artifacts/live_run_<run_id>/` from run-scoped persisted fields/endpoints, not only on ad-hoc audit collection.

### Deliverable 2: Historical run backfill is first-class

A bounded backfill command can materialize missing live-run artifact folders for existing DB runs without mutating run semantics.

### Deliverable 3: Operator contract is explicit and test-backed

Docs and tests clearly separate authoritative artifact truth (DB/persisted fields) from filesystem evidence mirror, and prove mirror creation + idempotent backfill.

## Task/Wave Breakdown

### Task 1: Confirm root-cause boundary and contract target

**Purpose:**
- lock root cause and avoid symptom patching

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `docs/superpowers/plans/audit/20260517-1416-live-run-invalid-api-key/report.md`
- Inspect: `docs/superpowers/plans/audit/20260516-1542-terminal-artifact-inconsistency/report.md`

**Preconditions:**
- run `5e963b7f-bbe4-4f03-ba0e-fb06721211c4` evidence retrieved from sqlite

**Steps:**
- [x] Step 1: record current behavior: run artifacts are served from persisted run fields/endpoints; `artifacts/live_run_<run_id>/` appears only when explicit evidence capture commands run.
- [x] Step 2: define target contract: terminal runs must have optional-but-deterministic local mirror, with DB fields remaining SSOT.
- [x] Step 3: list non-goals (no change to artifact payload schemas, no change to run status semantics).

**Verification:**
- [x] root-cause note added to execution log/context or patch PR notes with concrete evidence links

**Exit Criteria:**
- patch scope is root-cause aligned and bounded

## Execution Progress Log

- 2026-05-17: Task 1 completed. Root cause confirmed: run artifacts are persisted and served from DB-backed run fields/endpoints; `artifacts/live_run_<run_id>/` folders are created by manual evidence capture workflows, not automatic terminal-run persistence.
- 2026-05-17: Task 2 completed. Added terminal artifact mirror helpers in `src/fitcv_cp/worker_job.py` and invoked mirror persistence for success/cancel/fail terminal paths.
- 2026-05-17: Task 3 completed. Added `scripts/backfill_live_run_artifacts.py` with `--run-id` and `--dry-run`; validated create and idempotent skip behavior for `5e963b7f-bbe4-4f03-ba0e-fb06721211c4`.
- 2026-05-17: Task 4 completed. Updated `docs/observability.md` and `docs/usage.md`; added regression `test_worker_persists_terminal_artifact_mirror_for_succeeded_run`.

### Task 2: Implement terminal artifact mirror writer

**Purpose:**
- create live-run filesystem folder automatically for terminal runs

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: add helper to build run artifact file set from existing artifact builders (same content contract as bundle/export routes).
- [x] Step 2: add mirror writer to persist files under `artifacts/live_run_<run_id>/` with atomic write and idempotent overwrite behavior.
- [x] Step 3: invoke writer exactly once on terminal transitions (succeeded/failed/cancelled), with warning-only fallback on mirror-write errors.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "artifact and (zip or export or mirror)" -q`

**Exit Criteria:**
- new terminal run consistently creates mirror folder/files without changing existing download endpoints

### Task 3: Add historical backfill command

**Purpose:**
- repair missing folders for prior runs like `5e963b7f-bbe4-4f03-ba0e-fb06721211c4`

**Files:**
- Modify: `scripts/` (new backfill script)
- Verify: `tests/` (script/unit smoke test as appropriate)

**Preconditions:**
- Task 2 helper available/reusable

**Steps:**
- [x] Step 1: add script to enumerate runs and create mirror for runs missing `artifacts/live_run_<run_id>/`.
- [x] Step 2: support `--run-id` and `--dry-run` flags for bounded use.
- [x] Step 3: emit summary counts (`created`, `skipped_existing`, `missing_payload`, `errors`).

**Verification:**
- [x] script dry-run output on local DB proves target run selection
- [x] bounded real run creates folder for `5e963b7f-bbe4-4f03-ba0e-fb06721211c4`

**Exit Criteria:**
- historical missing mirror folders can be generated safely and repeatably

### Task 4: Update docs and regression coverage

**Purpose:**
- keep operator expectations and contracts aligned

**Files:**
- Modify: `docs/observability.md`
- Modify: `docs/usage.md`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 2-3 complete

**Steps:**
- [x] Step 1: document SSOT boundary: DB fields/endpoints authoritative, filesystem mirror is deterministic local evidence cache.
- [x] Step 2: document backfill procedure and expected folder structure.
- [x] Step 3: add regression asserting terminal run mirror creation and idempotent re-run behavior.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "artifact and mirror" -q`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs and tests explain and enforce new artifact-mirror contract

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py -k "artifact"`
- `python scripts/hooks/run_validator.py --fast`
- `python scripts/validate_repo_contracts.py --fast`

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
