---
name: execution-context-pack
template_id: execution-context-pack-template
document_type: execution_context_pack
lane_id: fitcv-cp-run-artifact-ssot-symmetry-impl
status: active
---

# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-24-15-35-fitcv-cp-run-artifact-ssot-plan.md`
- **Goal:** Run artifact SSOT + symmetry + invariance refactor for `fitcv_cp` worker + store.
- **Bounded Scope (in-scope only):** `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/bq_store.py`, plus minimal helper/test surfaces required by plan.
- **Out of Scope (explicit):** BigQuery schema migrations; unrelated pipeline/stage refactors.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-24-15-35-fitcv-cp-run-artifact-ssot-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-24-15-32-fitcv-cp-run-artifact-ssot-spec.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/07-fitcv-cp-run-artifact-ssot-symmetry-refactor.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/templates/execution-context-pack-template.md`

## 3) Current Task State

- **Completed:**
  - created isolated worktree: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-cp-run-artifact-ssot-symmetry-impl`
  - created venv and installed `requirements.txt`
  - GitNexus index updated via `npx gitnexus analyze` inside worktree path
  - Task 0 (planning lineage + baseline validator gate)
  - Task 1 (current-state inventory and blast radius)
  - Task 2 (SSOT registries + PersistenceResult contract)
  - Task 3 (normalize `update_run_*` API symmetry)
  - Task 4 (backend selection SSOT cleanup)
  - Task 5 (sqlite connection contract drift)
  - Task 6 (normalize worker artifact encoding SSOT)
  - Task 7 (unify fingerprinting SSOT and migration)
  - Task 8 (contract-ize artifact envelope enforcement)
- **In Progress:**
  - none
- **Deferred / Dropped:** none
- **Known divergence from plan (if any):**
  - Task 0 added to plan to satisfy validator-required lineage gates before code work
  - none

## 4) Files Changed This Session

- `docs/superpowers/specs/2026-05-24-15-32-fitcv-cp-run-artifact-ssot-spec.md` — add `parent_thread` to satisfy validator
- `docs/superpowers/plans/2026-05-24-15-35-fitcv-cp-run-artifact-ssot-plan.md` — add `parent_thread` + Task 0 for baseline gate
- `docs/intent/workstreams/threads/workstream-operator-control-plane/07-fitcv-cp-run-artifact-ssot-symmetry-refactor.md` — new bounded change thread for lineage

## 5) Verification State

- **Last commands run:**
  - `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "results_export or cv_generation_debug or mapping_suggestions or manual_checkpoint"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_run_artifact_contracts.py`
  - `.\scripts\get_gitnexus_freshness.ps1`
  - `npx gitnexus analyze`
  - `.\.venv\Scripts\python.exe -m pytest -q`
- **Result summary:**
  - PASSED after adding `parent_thread`, adding bounded change thread, and regenerating planning lineage
  - `tests\test_fitcv_cp\test_bq_store.py`: 68 passed
  - `tests\test_fitcv_cp\test_worker_job.py` subset: pass
  - `tests\test_fitcv_cp\test_run_artifact_contracts.py`: pass (10 passed)
  - GitNexus freshness: fresh (after `npx gitnexus analyze`)
- **Failing checks (if any):**
  - `.\.venv\Scripts\python.exe -m pytest -q` fails (38 failed) due to missing private/runtime artifacts and unrelated baseline expectations (ex: `data/candidate_profile.private.yaml`).
- **Gaps still unverified:**
  - full-suite pass in this worktree environment (blocked by missing `data/candidate_profile.private.yaml` + runtime config expectations)

## 6) Open Blockers / Risks

- none

## 7) Next Exact Action

- **Action type:** docs sync
- **Target:** `docs/superpowers/plans/2026-05-24-15-35-fitcv-cp-run-artifact-ssot-plan.md`
- **Exact command or edit intent:** record verification evidence and document that full-suite pytest requires private/runtime artifacts (blocked in this lane) while targeted unit tests + repo contract validator provide bounded proof for this plan scope.
- **Why this is next:** plan Verification expects a repo test command; now evidence shows full-suite not eligible in this environment without extra artifacts.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **overview_log:** (not used)
- **consult_if:** (not used)
- **notes_from_log (optional, concise):** (none)

### Current-state notes (Task 1, partial)

- `src/fitcv_cp/store.py` drift: `RunStore.update_run_synonym_proposals(...)` returns `dict[str, str]` while other `update_run_*` methods return `None` (symmetry break; impacts BQ-R1).
- `src/fitcv_cp/worker_job.py` encoding drift: mix of `encode_json_object(...)` and direct `json.dumps(...)` in payload builder paths; needs inventory split:
  - persisted artifacts (store snapshots) vs
  - event payloads / telemetry payloads (may remain `json.dumps` if not persisted artifact contract).

### Current-state inventory (Task 1, evidence-first summary)

**Callsites affected by BQ-R1 (update_run_* return contract):**
- `src/fitcv_cp/worker_job.py`:
  - treats `update_run_synonym_proposals(...)` return as dict (`synonym_status = ...`)
  - calls other `update_run_*` as fire-and-forget (`None` return today)
- `src/fitcv_cp/store.py`:
  - `RunStore` Protocol encodes signature drift: only `update_run_synonym_proposals(...)` returns dict; other updates return `None`.
  - `ControlPlaneStore` wrappers currently mirror this drift.
- `src/fitcv_cp/app.py`:
  - provides wrapper functions delegating to `RunStore`; will need signature/return alignment when `update_run_*` returns normalized `PersistenceResult`.
- `src/fitcv_cp/queue.py`:
  - calls `update_run_status(...)` (will need to accept return if signature changes).

**Worker persisted artifact builders and current encoding:**
- `_build_results_export_payload(...)` → `json.dumps(...)` (used for `update_run_results_export`)
- `_build_cv_generation_debug_payload(...)` → `json.dumps(...)` (used for `update_run_cv_generation_debug`)
- `_build_stage_transition_artifacts_payload(...)` → `encode_json_object(...)` (used for `update_run_stage_transition_artifacts`)
- `_build_settings_used_payload(...)` → `encode_json_object(...)` (used for `update_run_settings_used`)
- `_build_mapping_suggestions_payload(...)` → `json.dumps(...)` (used for `update_run_mapping_suggestions`)

**BQ store current missing-column patterns (not exhaustive yet):**
- `insert_run(...)` has legacy SQL fallback for older schema missing `orchestration_*` columns.
- `update_run_orchestration_binding(...)` falls back to `update_run_queue_job_id(...)` if `orchestration_*` columns missing.
- `update_run_synonym_proposals(...)` returns a dict persistence status and degrades on missing `synonym_proposals_json` column (different contract vs other updates).

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
