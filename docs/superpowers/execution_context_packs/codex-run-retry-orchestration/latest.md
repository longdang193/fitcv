# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** docs/superpowers/plans/2026-05-27-16-02-fitcv-run-retry-orchestration-plan.md
- **Goal:** Implement SSOT-first retry + crash-safe orchestration for FITCV control-plane runs.
- **Bounded Scope (in-scope only):** `src/fitcv_cp/*` orchestration + SSOT + worker-job lifecycle; config under `config/runtime/control_plane.yaml`; tests under `tests/test_fitcv_cp/`.
- **Out of Scope (explicit):** pipeline algorithm refactors; prompt/chunk tuning; resume-from-checkpoint design.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** docs/superpowers/plans/2026-05-27-16-02-fitcv-run-retry-orchestration-plan.md
- **Specs / maps / thread docs:**
  - docs/superpowers/specs/2026-05-27-15-24-fitcv-run-retry-orchestration-spec.md
  - docs/intent/workstreams/threads/workstream-operator-control-plane/06-fitcv-cp-app-ssot-symmetry-refactor.md
- **Governance / workflow rules used:**
  - docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md
  - docs/operating_system/governance/execution-context-pack-governance.md
  - docs/operating_system/templates/execution-context-pack-template.md

## 3) Current Task State

- **Completed:**
  - Task 0 baseline green restored for `tests/test_fitcv_cp/`.
  - Task 2 failure classification helper + unit tests.
  - Task 3: worker emits attempt start/renew/terminal events with lease timestamps.
  - Task 4: RQ retry wiring + unit test (env-driven).
  - Task 5: reconciler handles lease expiry (requeue/fail/cancel) + dedicated reconciler service + integration test.
  - Task 6: operator endpoints (stop/retry) + attempt timeline UI + policy tests.
- **In Progress:**
  - Task 1: attempt SSOT schema still missing formal CRUD surface; currently event-sourced via `pipeline_run_events`.
  - Task 5: scheduling mechanism still TBD (currently manual trigger only).
  - Task 7: config SSOT integration (currently env-driven toggles).
- **Deferred / Dropped:**
  - None.
- **Known divergence from plan (if any):**
  - Attempt SSOT implemented as event-sourced (`pipeline_run_events`) for sqlite/BQ parity (no BQ schema migration).

## 4) Files Changed This Session

- `src/fitcv_cp/run_artifact_contracts.py` — `run_attempt.v1` payload helper + decoder.
- `src/fitcv_cp/store.py` — tolerant `_call_dict` wrappers + `list_run_attempt_payloads`.
- `src/fitcv_cp/retry_policy.py` — shared exception classifier.
- `src/fitcv_cp/queue.py` — RQ retry wiring (env-driven) + inline attempt id propagation.
- `src/fitcv_cp/worker_job.py` — attempt start/renew/terminal attempt events.
- `src/fitcv_cp/reconciler.py` — reconcile abandoned attempts + bounded re-enqueue.
- `src/fitcv_cp/app.py` — admin endpoints: `POST /admin/reconciler/run-attempts`, `POST /admin/runs/{run_id}/retry`, run-detail attempt parsing.
- `src/fitcv_cp/templates/run_detail.html` — render Run Attempt Timeline under Advanced & Diagnostics.
- `tests/test_fitcv_cp/test_retry_policy.py` — classifier tests.
- `tests/test_fitcv_cp/test_reconciler.py` — reconciler tests.
- `tests/test_fitcv_cp/test_queue.py` — retry wiring test.
- `docs/superpowers/plans/2026-05-27-16-02-fitcv-run-retry-orchestration-plan.md` — progress checkbox updates.
- `docs/generated/planning_lineage.yaml` — regenerated.

## 5) Verification State

- **Last commands run:**
  - `python scripts/hooks/run_validator.py --fast` (PASS)
  - `python -m pytest -q tests/test_fitcv_cp` (PASS)
- **Result summary:**
  - pytest: 929 passed
- **Failing checks (if any):**
  - none

## 6) Open Blockers / Risks

- No hard blocker.
- Risk: lease renewal uses event emission; lease_seconds too small could spam attempt events.

## 7) Next Exact Action

- **Action type:** implement
- **Target:** closeout readiness + merge/reconcile gate.
- **Exact command or edit intent:**
  - Add optional background reconciler tick (default disabled) controlled by config/env.
  - Move retry knobs from env-only to `config/runtime/control_plane.yaml` SSOT and load via `load_control_plane_config()`.
  - Update queue/reconciler to read policy from config SSOT (symmetry).

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only

