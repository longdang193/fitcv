# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-24-14-25-fitcv-cp-worker-job-ssot-symmetry-refactor-plan.md`
- **Goal:** Execute R-WJ-01..06 refactor for `src/fitcv_cp/worker_job.py` (SSOT/symmetry/invariance) with tests + validators green.
- **Bounded Scope (in-scope only):**
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/run_artifact_contracts.py` (helper additions only)
  - `src/fitcv/contracts.py` (schema-version constants only)
  - targeted tests under `tests/test_fitcv_cp/`
- **Out of Scope (explicit):**
  - BigQuery schema changes
  - control-plane route/API shape changes
  - `fitcv.pipeline` internal refactor

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-24-14-25-fitcv-cp-worker-job-ssot-symmetry-refactor-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-24-14-27-fitcv-cp-worker-job-ssot-symmetry-refactor-spec.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/06-fitcv-cp-app-ssot-symmetry-refactor.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - Worktree: `C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT\\.worktrees\\fitcv-cp-worker-job-ssot-symmetry-refactor` on branch `codex/fitcv-cp-worker-job-ssot-symmetry-refactor`
  - GitNexus indexed (worktree): `npx gitnexus analyze` PASS
  - Task 0 baseline: `python scripts/hooks/run_validator.py --fast` PASS; `uv run pytest tests/test_fitcv_cp/` PASS
  - GitNexus impact captured before edits:
    - `execute_cv_regenerate_once` risk LOW
    - `_append_synonym_suppression_summary_event` risk LOW
    - `_persist_synonym_proposals_snapshot` risk LOW
    - `_build_settings_used_payload` risk LOW
    - `_stable_sha256_json` risk LOW
    - `decode_json_object_or_none` risk CRITICAL (do not change semantics; additive-only)
  - Task 1:
    - Added `decode_json_object_or_raise` in `src/fitcv_cp/run_artifact_contracts.py`
    - Migrated `execute_cv_regenerate_once` to SSOT decode helper
    - Migrated `_append_synonym_suppression_summary_event` to SSOT tolerant decode helper
    - Migrated `_persist_synonym_proposals_snapshot` to SSOT strict decode helper before automation mutation
    - Added invalid JSON regression test for `execute_cv_regenerate_once`
  - Task 2:
    - Added `SETTINGS_USED_SCHEMA_VERSION` constant in `src/fitcv/contracts.py`
    - Updated worker settings-used payload builder to use constant
  - Task 3:
    - Unified `effective_settings_json` parse path via `_effective_settings_payload_from_run_record()`
    - Added invalid effective-settings JSON default test
  - Task 4:
    - Switched synonym suppression summary dedupe fingerprint to SHA256 (keeps legacy SHA1 dedupe)
    - Added `stable_json_dumps` / `stable_sha256_fingerprint` in `src/fitcv_cp/run_artifact_contracts.py`
    - Added legacy SHA1 suppression fingerprint dedupe regression test
  - Task 5:
    - Extracted dict-first payload builders for settings-used + stage-transition artifacts
    - Routed payload encoding through `fitcv_cp.run_artifact_contracts.encode_json_object`
    - Added dict-shape unit tests for dict builders
  - Task 6:
    - Audited `_build_synonym_proposals_payload` callers (tests-only)
    - Removed shim from `src/fitcv_cp/worker_job.py`; tests now call `fitcv_cp.synonym_proposals.build_synonym_proposals_payload`
- **In Progress:**
  - none
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - none

## 4) Files Changed This Session

- `src/fitcv_cp/run_artifact_contracts.py` — add `decode_json_object_or_raise`
- `src/fitcv_cp/run_artifact_contracts.py` — add `stable_json_dumps`, `stable_sha256_fingerprint`
- `src/fitcv_cp/worker_job.py` — migrate JSON decode in `execute_cv_regenerate_once`, `_append_synonym_suppression_summary_event`, `_persist_synonym_proposals_snapshot`; use schema constant for settings-used
- `src/fitcv/contracts.py` — add `SETTINGS_USED_SCHEMA_VERSION`
- `tests/test_fitcv_cp/test_worker_job.py` — add invalid JSON regression test for `execute_cv_regenerate_once`
- `src/fitcv_cp/worker_job.py` — unify `effective_settings_json` parse path
- `tests/test_fitcv_cp/test_worker_job.py` — add invalid effective-settings JSON default test
- `src/fitcv_cp/worker_job.py` — SHA256 suppression fingerprint + legacy SHA1 dedupe compat
- `tests/test_fitcv_cp/test_worker_job.py` — add legacy SHA1 suppression fingerprint dedupe regression test
- `src/fitcv_cp/worker_job.py` — dict-first payload builders for settings-used + stage-transition artifacts
- `tests/test_fitcv_cp/test_worker_job.py` — add dict-shape tests for dict builders
- `docs/superpowers/specs/2026-05-24-14-27-fitcv-cp-worker-job-ssot-symmetry-refactor-spec.md` — update `parent_thread`
- `docs/superpowers/plans/2026-05-24-14-25-fitcv-cp-worker-job-ssot-symmetry-refactor-plan.md` — set `status: active`, update `parent_thread`, update task checkbox state
- `docs/generated/planning_lineage.yaml` — regenerated after linkage update

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze` (worktree) PASS
  - `npx gitnexus detect-changes -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT\\.worktrees\\fitcv-cp-worker-job-ssot-symmetry-refactor" --scope staged` (risk=high; reviewed)
  - `python scripts/hooks/run_validator.py --fast` PASS
  - `uv run pytest tests/test_fitcv_cp/` PASS (887 passed)
  - `uv run pytest tests/test_fitcv_cp/test_worker_job.py -k "execute_cv_regenerate_once"` PASS (3 tests)
  - `uv run pytest tests/test_fitcv_cp/test_worker_job.py -k "persists_settings_used_json_on_success"` PASS
  - `uv run pytest tests/test_fitcv_cp/test_worker_job.py -k "synonym_policy_defaults_when_effective_settings_json_invalid"` PASS
- **Result summary:**
  - all current changes green
- **Failing checks (if any):**
  - none
- **Gaps still unverified:**
  - none for Tasks 1–2

## 6) Open Blockers / Risks

- Risk: `decode_json_object_or_none` is CRITICAL blast radius; keep changes additive-only and do not change its existing semantics.

## 7) Next Exact Action

- **Action type:** edit
- **Target:** Plan completion (commit-ready)
- **Exact command or edit intent:**
  - Prepare commit for lane: confirm staged diff scope acceptable, then commit with message referencing plan + lane id.
- **Why this is next:**
  - Plan Tasks 0–6 complete; staged scope confirmed via GitNexus detect-changes.
 

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **consult_if:** need raw terminal evidence beyond plan/spec/thread/context pack

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
