---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-local-p20-retry-state-reconciliation
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - tests/test_fitcv_cp/test_admin_retry_endpoint.py
  - tests/test_fitcv_cp/test_local_app.py
  - docs/superpowers/plans/2026-08-23-fitcv-local-p20-retry-state-reconciliation-plan.md
---

# FitCV Local P20 Retry State Reconciliation

## Goal

Fix failed-Run retry state reconciliation for FitCV Local without changing the
schema CHECK constraint, Local execution contract, Redis/RQ lane, or preserved
acceptance-harness work.

## Implementation Outcomes

### Canonical retry transition

Failed Run retry uses the persistence owner to enter a valid queued state with
`finished_at` cleared and immutable Run inputs, snapshots, and prior evidence
preserved.

### Enqueue failure safety

Retry submission failure restores a valid terminal state, records explicit retry
enqueue failure evidence, avoids phantom queue bindings, and does not strand a
Run in `queued`.

### Regression and live proof

Focused tests and one fresh Local P20 live probe prove retry identity,
immutability, attempt history, cardinality, max-attempt policy, cancellation
policy, enqueue rollback, and Continue non-regression.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `optional worktree`
- Commit policy: `no commits during execution`
- Preauthorized local actions: product source/test edits in declared files, disposable Local SQLite setup, focused tests, canonical P20 rerun, read-only validation
- User-approval actions: full 25-probe suite, Redis/Docker/RQ changes, acceptance-harness redesign, commit, push, merge, cleanup
- Parallel ownership: `none`
- Sequential fallback: `red regression`, canonical persistence fix, focused proof, live P20, independent validation

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `ca2f337bfcc1e5e2bc67a937fc12eaa66598a964`
- Active task(s): `none`
- Expected workspace: `main` at base with preserved acceptance-harness changes and this separate P20 patch
- Next action: run separate approved 25-probe P0 acceptance task
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | main | `codex` | none | red/green retry tests, focused backend proof, live P20, independent validation | PASS: focused tests, Local P20, read-only SQLite validator, and DeepAgents validator |

## Task Breakdown

### Task 1: Reconcile Local P20 retry state

**Purpose:**
- Make failed→queued retry transitions valid and rollback-safe.

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py` retry transition owner.
- Modify: `src/fitcv_cp/store.py` only if the canonical store boundary needs the new operation.
- Modify: `src/fitcv_cp/app.py` retry route and error/event handling.
- Modify: `tests/test_fitcv_cp/test_admin_retry_endpoint.py`.
- Modify: `tests/test_fitcv_cp/test_local_app.py` only if direct Local boundary coverage belongs there.

**Preserved invariants:**
- SQLite CHECK remains unchanged.
- `run_id`, Run inputs, Profile/settings/source snapshots, prior events, artifacts, and prior attempt IDs remain unchanged.
- Local uses inline `LocalJobExecutor`; no Redis, Docker, RQ, or worker requirement is added.
- Continue behavior remains unchanged.

**Steps:**
- [x] Add red tests for timestamp reset, immutable snapshots, attempt identity, no duplicate jobs, policy limits, cancellation, and enqueue rollback.
- [x] Implement smallest canonical persistence transition and route rollback handling.
- [x] Run focused regression and backend state proofs.
- [x] Rerun canonical P20 only through Local acceptance harness.
- [x] Obtain independent read-only validation and reconcile with preserved harness work.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_admin_retry_endpoint.py -q` → `4 passed`
- `py -m pytest tests/test_fitcv_cp/test_local_app.py -q -k "local_job_executor or prepare_local_environment or packaged_provider_api or packaged_llm_configuration or packaged_system_settings or submit_run_maps_local_busy or recovery_app or open_browser"` → `9 passed, 7 deselected`
- Direct read-only SQLite inspection → schema `5`, required tables, succeeded Run, finished timestamp, two distinct attempts, one `run_jobs` row, retry event.
- Canonical P20 only → `PASS`; no full 25-probe run.
- Independent DeepAgents validator → `PASS`; independent SQLite validator → `PASS`.
- `py -m py_compile src/fitcv_cp/app.py src/fitcv_cp/sqlite_store.py scripts/run_fitcv_local_p20_acceptance.py` and `git diff --check` → pass.
- Full `tests/test_fitcv_cp/test_local_app.py` was not used as a gate because unrelated `test_second_launch_opens_existing_url_and_exits` hangs in this Windows harness; its isolated run was not part of the P20 ownership scope. Relevant Local tests passed.

## Completion Criteria

1. Failed Run retry clears `finished_at` before worker consumption.
2. Retry preserves immutable Run truth and prior attempt/event/artifact evidence.
3. Retry creates distinct Local submission/attempt identity without duplicate Run jobs.
4. Enqueue failure restores valid terminal state with explicit event and no phantom binding.
5. Existing max-attempt, cancellation, and Continue behavior remains valid.
6. Focused tests, direct SQLite proof, live P20, and independent validation pass.
7. Full 25-probe acceptance remains unrun and is deferred to its separate approved task.

## Acceptance Result

`PASS`

- Failed→queued retry clears terminal fields through `sqlite_store` and preserves the schema CHECK invariant.
- Enqueue failure restores the original failed state, clears queue binding, records `retry_enqueue_failed`, and returns HTTP `503`.
- Fresh Local P20 report: `C:\tmp\fitcv-p20-acceptance-current.json`.
- Fresh database: schema `5`; required tables present; final Run `succeeded`; two distinct attempt IDs; one `run_jobs` row; immutable snapshots unchanged.
- Preserved acceptance-harness changes remain uncommitted and are not redesigned here.
