## Metadata

- Audit ID: `20260516-1542-terminal-artifact-inconsistency`
- Status: `mitigated`
- Severity: `high`
- Owner: `codex`
- Created At: `2026-05-16T15:42:37.0481671+02:00`
- Updated At: `2026-05-16T16:45:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-16-15-10-option-b-shared-structural-principles-plan.md`

## Scope

- Environment: `Windows-10-10.0.19045-SP0`, `Python 3.13.5`, local API at `http://localhost:8000`
- Commit/Branch: `29bc933` on `codex/shared-structural-principles`
- Affected Surface: `src/fitcv_cp/worker_job.py`, artifact endpoints in `src/fitcv_cp/app.py`, run artifact contracts in `docs/api.md`

## Findings

### Finding `F-01`: terminal run missing expected terminal exports

- Classification: `other`
- Impact: operator cannot download terminal evidence bundle (`export.json`, `settings-used.json`, trace exports) even after run terminalization.
- Expected Behavior: terminal/succeeded run should expose run-scoped export/debug routes documented in `docs/api.md`.
- Actual Behavior: run `57aac5b2-9f13-4991-b0f2-92d98c3d4ae6` shows `status=succeeded` but endpoint probe returned `404` for `export.json`, `settings-used.json`, `cv-analysis-trace.json`, `agentic-live-trace.json`.

### Finding `F-02`: stage-artifacts snapshot remains partial/non-terminal

- Classification: `other`
- Impact: stage transition artifact gives stale runtime picture (`running`, `partial_snapshot`) inconsistent with terminal run state.
- Expected Behavior: for terminalized run, stage-artifacts snapshot should be terminal-consistent and complete.
- Actual Behavior: both sampled runs return `stage-artifacts.json` with `status=running`, `snapshot_complete=false`, `degradation_reason=partial_snapshot`.

## Evidence

- Run status snapshots:
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6.run_status.json`
  - `evidence/87050a4b-e274-4c49-8406-748894f44728.run_status.json`
- Endpoint probe matrices:
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6.endpoint_probe.json`
  - `evidence/87050a4b-e274-4c49-8406-748894f44728.endpoint_probe.json`
- Raw downloaded artifacts:
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6/stage-artifacts.json`
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6/synonym-proposals.json`
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6/synonym-proposals-trace.json`
  - `evidence/87050a4b-e274-4c49-8406-748894f44728/stage-artifacts.json`
- Artifact zip extraction with terminal payloads for run 1:
  - `evidence/57aac5b2-9f13-4991-b0f2-92d98c3d4ae6/artifacts_unzipped/*`
- Checksums for all evidence items are registered in `manifest.yaml`.

## Reproduction

- Preconditions:
  - local control-plane web + worker reachable on `localhost:8000`
  - input dataset `data/sample_jobs.json`
- Steps:
  1. Trigger live run with `run_mode=run_all`.
  2. Poll `/runs/{run_id}` until terminal or review pause.
  3. Download run artifacts and probe export/debug endpoints.
  4. Compare `/runs/{run_id}` state with `stage-artifacts.json` and endpoint responses.
- Commands:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8000/runs' -Method Post -ContentType 'application/json' -Body '{"jobs_path":"data/sample_jobs.json","config_path":"config/env.yaml","triggered_by":"codex-live-debug","run_mode":"run_all"}'
Invoke-RestMethod -Uri 'http://localhost:8000/runs/<run_id>' -Method Get
Invoke-WebRequest -Uri 'http://localhost:8000/admin/runs/<run_id>/stage-artifacts.json' -OutFile 'artifacts/live_run_<run_id>/stage-artifacts.json'
Invoke-WebRequest -Uri 'http://localhost:8000/admin/runs/<run_id>/synonym-proposals.json' -OutFile 'artifacts/live_run_<run_id>/synonym-proposals.json'
Invoke-WebRequest -Uri 'http://localhost:8000/admin/runs/<run_id>/synonym-proposals-trace.json' -OutFile 'artifacts/live_run_<run_id>/synonym-proposals-trace.json'
Invoke-WebRequest -Uri 'http://localhost:8000/admin/runs/<run_id>/artifacts.zip' -OutFile 'artifacts/live_run_<run_id>/artifacts.zip'
```

- Determinism notes: same input dataset used for both runs; failures reproduced across two run IDs.

## Root Cause And Boundary

- Failure boundary: control-plane artifact publication contract at terminalization boundary (`cv_generation` completion to run export surfaces).
- Root cause summary: unresolved. Evidence shows mismatch between run terminal state and exposed artifact endpoint/state snapshots; likely divergence between terminal persistence path and per-route artifact read/write availability.

## Fix And Verification

- Fix summary: patched worker finalize path to persist terminal snapshots with a non-null timestamp even when review queue keeps run in `awaiting_continue`.
- Bounded patch scope:
  - `src/fitcv_cp/worker_job.py`: introduce `artifact_snapshot_at = finished_at or now` and route results/settings/stage snapshot builders through it.
  - `tests/test_fitcv_cp/test_worker_job.py`: add regression test for `awaiting_review` persistence path.
- Attempted fix path and outcomes:
  - root cause confirmed: `finished_at=None` caused snapshot builders requiring `.isoformat()` to throw and skip writes under review-required closure path.
  - code patch applied and regression test added.
- Verification commands:

```powershell
python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "awaiting_review_persists_terminal_snapshots_without_finished_at"
python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py
```

- Verification evidence links:
  - `evidence/post_fix/pytest_worker_fix_targeted.txt`
  - `evidence/post_fix/pytest_full_target_suite.txt`
  - `evidence/post_fix/live_rerun_blocked/trigger_attempt_env_yaml.json`
  - `evidence/post_fix/live_rerun_blocked/trigger_attempt_dot_env_yaml.json`
  - `evidence/post_fix/live_rerun_blocked/web_logs_since_10m.log`
  - `evidence/post_fix/live_rerun_blocked/container_config_inventory.txt`
  - `evidence/post_fix/live_rerun_blocked/container_app_listing.txt`

## Post-Fix Live Rerun (Patched Worktree)

- Runtime source: rebuilt from patched worktree (`codex/shared-structural-principles`) using compose project `shared-structural-principles`.
- Trigger result: `POST /runs` succeeded with run id `a9bdad07-bd8b-4b41-8f3e-9a67ff58d4b1`.
- Run state after polling: `/runs/{id}` remained `status=awaiting_continue`, `checkpoint_status=awaiting_review`, `finished_at=null`.
- Endpoint probe evidence refreshed under:
  - `evidence/post_fix/live_rerun_patched/trigger_response.json`
  - `evidence/post_fix/live_rerun_patched/run_final.json`
  - `evidence/post_fix/live_rerun_patched/run_final_after_continue.json`
  - `evidence/post_fix/live_rerun_patched/admin_runs_a9bdad07-bd8b-4b41-8f3e-9a67ff58d4b1_stage-artifacts.json.json`
  - `evidence/post_fix/live_rerun_patched/admin_runs_a9bdad07-bd8b-4b41-8f3e-9a67ff58d4b1_stage-artifacts.after_continue.json`

- Current observation:
  - artifact exports now exist (no trigger-time config failure).
  - consistency concern remains: run detail endpoint reports `awaiting_continue`, while stage-artifacts payload reports `status=succeeded` and `snapshot_complete=true`.

## Post-Fix Status-Contract Patch

- Patch applied:
  - `src/fitcv_cp/worker_job.py`: persist stage-transition artifact terminal status using `terminal_status` instead of hardcoded `RunStatus.SUCCEEDED`.
  - `tests/test_fitcv_cp/test_worker_job.py`: updated awaiting-review snapshot test to assert `status=awaiting_continue`, `snapshot_complete=false`, and `degradation_reason=partial_snapshot_non_terminal_success`.
- Verification:
  - targeted tests passed for review-hold persistence paths.
- Live rerun on patched runtime:
  - run id: `9fe2dcdb-6881-481d-8a73-524821d58ffe`
  - run endpoint: `status=awaiting_continue`, `checkpoint_status=awaiting_review`
  - immediate stage-artifacts probe returned stale `status=running` (transient)
  - settled probe returned aligned non-terminal payload:
    - `status=awaiting_continue`
    - `snapshot_complete=false`
    - `degradation_reason=partial_snapshot_non_terminal_success`

- Evidence links:
  - `evidence/post_fix/live_rerun_patched_after_status_fix/trigger_response.json`
  - `evidence/post_fix/live_rerun_patched_after_status_fix/run_final.json`
  - `evidence/post_fix/live_rerun_patched_after_status_fix/stage-artifacts.json`
  - `evidence/post_fix/live_rerun_patched_after_status_fix/stage-artifacts.after_settle.json`
  - `evidence/post_fix/live_rerun_patched_after_status_fix/settings-used.error.json`

## Succeeded-Path Probe And Final Store-Path Fix

- Succeeded-path probe (before store-path fix) found remaining inconsistency:
  - run id `c520b897-8f4b-4a4a-9b43-5ccd3c5a58f8` reached `status=succeeded`
  - stage-artifacts still showed prior non-terminal snapshot (`status=awaiting_continue`)
  - evidence:
    - `evidence/post_fix/live_rerun_succeeded_path/run_final.json`
    - `evidence/post_fix/live_rerun_succeeded_path/stage-artifacts.json`
    - `evidence/post_fix/live_rerun_succeeded_path/consistency_check_after_settle.json`

- Root cause refinement:
  - review-closure terminalization path in app did not reliably overwrite stage-artifacts through active `ControlPlaneStore` abstraction.

- Final patch:
  - `src/fitcv_cp/store.py`: add `update_run_stage_transition_artifacts` surface to `RunStore`/`ControlPlaneStore`.
  - `src/fitcv_cp/app.py`:
    - add wrapper `update_run_stage_transition_artifacts(...)` using store abstraction.
    - wire `ControlPlaneStore` with `update_run_stage_transition_artifacts_fn`.
    - refresh terminal stage-artifacts snapshot when review closure marks run `SUCCEEDED` (single and batch review actions).

- Live verification after store-path fix:
  - run id `f7a4a050-41c4-4171-88ff-33f321d0321c`
  - review-closure transition ended with:
    - `/runs/{id}` => `status=succeeded`
    - `/admin/runs/{id}/stage-artifacts.json` => `status=succeeded`
  - evidence:
    - `evidence/post_fix/live_review_closure_stage_refresh_after_store_fix/run_final.json`
    - `evidence/post_fix/live_review_closure_stage_refresh_after_store_fix/stage-artifacts.final.json`
    - `evidence/post_fix/live_review_closure_stage_refresh_after_store_fix/consistency_summary.json`

## Risk And Disposition

- Residual risk: low. Terminal stage-artifacts now refreshed on both worker completion and review-closure succeeded transition; only short-lived read-after-write lag may still appear if probed immediately.
- Disposition decision: `mitigated`
- Follow-ups:
  - optional: add explicit consistency retry/backoff in diagnostics probe tooling to avoid false mismatch from immediate reads.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
