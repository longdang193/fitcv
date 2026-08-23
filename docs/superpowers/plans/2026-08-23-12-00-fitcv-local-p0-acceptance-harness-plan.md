---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-local-p0-acceptance-harness
targets:
  - tests/test_fitcv_cp/acceptance_harness.py
  - tests/test_fitcv_cp/test_acceptance_harness.py
  - scripts/run_fitcv_local_p0_acceptance.py
  - scripts/validate_template_required_sections.py
  - tests/test_validate_template_required_sections.py
  - docs/superpowers/plans/2026-08-23-12-00-fitcv-local-p0-acceptance-harness-plan.md
---

# FitCV Local P0 Acceptance Harness Plan

## Goal

Create disposable, Local-only acceptance harness that can deterministically
hold and release serialized work, build canonical Scan/Profile fixtures, run
remaining blocked probes, and emit evidence without changing production Local behavior.

## Implementation Outcomes

### Test-only Local execution control

Provide controlled executor under test ownership that preserves `LocalJobExecutor.submit` contract while exposing deterministic submitted, held, released, completed, and failed states. Production executor code remains unchanged.

### Disposable acceptance fixtures and runner

Provide acceptance-owned Profile, tracked-company, Scan, settings, semantic-job, failure, retry, race, and historical-persistence fixtures plus one runner that records exactly P2, P3, P6, P7, P9, P11, P12, P14, P19, P20, P22, P23, and P25.

### Evidence and safety

Runner output records baseline, Local configuration, probe outcome, state and artifact evidence, validator result, and Git drift. It never requires Redis, Docker, RQ, production debug endpoints, timing sleeps, or full 25-probe execution.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: declared harness/test/plan-validator edits, disposable Local SQLite setup, provider calls through configured `control_plane.yaml`, bounded 13-probe run, read-only validation
- User-approval actions: commit, push, full 25-probe run, Redis/Docker changes, product behavior changes, sample-data changes
- Parallel ownership: `none`
- Sequential fallback: `red control tests`, helper/runner implementation, focused proof, 13-probe run, independent validation

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `ca2f337bfcc1e5e2bc67a937fc12eaa66598a964`
- Active task(s): `none`
- Expected workspace: `main` at base with preserved harness changes and separate uncommitted P20 product-fix changes
- Next action: run separate approved 25-probe P0 integration acceptance task
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | red/green control tests, focused harness tests, 13 probe results, independent validator result, Git scope review | PASS: original 12 probes PASS; fresh canonical P20 rerun PASS; no full 25-probe run |

## Task Breakdown

### Task 1: Build and validate Local acceptance harness

**Purpose:**
- Make all remaining blocked probes executable against disposable FitCV Local state.

**Task Function:**
- Acceptance harness implementation and evidence collection.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: coupled runtime control, SQLite fixtures, provider-backed pipeline traces, and failure-state proof.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: independent source/scope review, harness-only barrier proof, and acceptance evidence review.

**Specification Coverage:**
- P2, P3, P6, P7, P9, P11, P12, P14, P19, P20, P22, P23, P25.
- Local mode remains `FITCV_LOCAL_MODE=1`, `FITCV_CP_INLINE_EXECUTION=1`, no Redis URL.
- No production pause/failure/debug endpoint or acceptance timing dependency.

**Files And Symbols:**
- Modify: `tests/test_fitcv_cp/acceptance_harness.py`
- Modify: `tests/test_fitcv_cp/test_acceptance_harness.py`
- Modify: `scripts/run_fitcv_local_p0_acceptance.py`
- Modify: `scripts/validate_template_required_sections.py`
- Modify: `tests/test_validate_template_required_sections.py`
- Verify: `src/fitcv_cp/local_app.py`, `src/fitcv_cp/queue.py`, `src/fitcv_cp/worker_job.py`, `config/runtime/control_plane.yaml`

**Dependencies:**
- Current `main` at `ca2f337bfcc1e5e2bc67a937fc12eaa66598a964`.
- Accepted bootstrap, lifecycle, and P0 recovery plans remain completed and untouched.

**Authority:**
- Preauthorized local actions: test/harness ownership and disposable runtime evidence only.
- Stop for: product defect, plan/Git mismatch, provider failure, scope drift, or need for Redis/Docker/full 25 probes.

**Steps:**
- [x] Add failing tests for deterministic hold/release and cleanup.
- [x] Implement minimal test-only executor and fixture/runner helpers.
- [x] Run focused tests and backend boundary checks.
- [x] Execute all 13 named probes against fresh Local state; P20 fails at product retry boundary.
- [x] Obtain independent read-only validator result and reconcile Git; validator confirms harness scope and P20 product defect.
- [x] Reconcile active execution status with template validation; active plans now pass required-section validation.

**Verification:**
- [x] `py -m pytest tests/test_fitcv_cp/test_acceptance_harness.py -q`
- Expected: control and fixture tests pass; production `LocalJobExecutor` tests remain green.
- [x] Runner emitted one result for each named probe in the recorded 13-probe run; P20 was then rerun canonically after its separate product fix; no full 25-probe result exists.
- [x] `git diff --check` and changed-file scope pass.

**Exit Criteria:**
- All 13 probes are executable and executed, each classified PASS/FAIL/BLOCKED with evidence grade.
- Production behavior changed: `NONE`.
- Independent validator result recorded; task returns `FAIL` because P20 found a genuine product defect.

## Acceptance Result

`PASS`

- P2, P3, P6, P7, P9, P11, P12, P14, P19, P22, P23, and P25: `PASS`, evidence grade `A`.
- P20: `PASS`, fresh canonical Local rerun after separate product fix; evidence includes distinct attempt IDs, immutable snapshots, and stable `run_jobs` cardinality.
- Root cause and product fix are owned by `docs/superpowers/plans/2026-08-23-fitcv-local-p20-retry-state-reconciliation-plan.md`.
- Independent validator: `PASS`; confirms Local-only harness, deterministic controls, disposable fixtures, and P20 retry-state reconciliation.
- Required follow-up: separate approved 25-probe P0 integration acceptance task.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_acceptance_harness.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_queue.py -q`
- `git diff --check`
- Final runner report and independent validator evidence.

## Completion Criteria

1. Test-only control seam is deterministic and covered.
2. Disposable canonical fixtures are created without mutating tracked sample data.
3. All 13 required probes have fresh evidence or an explicit blocker.
4. No production Local behavior, Redis/Docker lane, or full 25-probe acceptance changed.
5. Plan/Git state reconciles and completion verification accepts result; separate P20 source/test changes remain owned by the P20 plan.
