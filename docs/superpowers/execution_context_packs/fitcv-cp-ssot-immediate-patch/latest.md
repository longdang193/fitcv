# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-06-26-11-35-fitcv-cp-ssot-immediate-patch-plan.md`
- **Goal:** Sync planning artifacts to completed source truth for FitCV control-plane SSOT immediate patch and record remaining out-of-scope repo-wide blockers truthfully.
- **Bounded Scope (in-scope only):**
  - `src/fitcv_cp/backend_runtime.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/bq_store.py`
  - `src/fitcv_cp/main.py`
  - `src/fitcv_cp/orchestrator.py`
  - `src/fitcv_cp/queue.py`
  - `src/fitcv_cp/reconciler_service.py`
  - `src/fitcv_cp/settings_schema.py`
  - `src/fitcv_cp/settings_store.py`
  - `src/fitcv_cp/store.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/templates/base.html`
  - `src/fitcv_cp/templates/run_detail.html`
  - `src/fitcv_cp/templates/settings.html`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_main.py`
  - `tests/test_fitcv_cp/test_queue.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - planning sync docs for this lane only
- **Out of Scope (explicit):**
  - unrelated planning-artifact cleanup for Indeed adapter spec/plan lineage
  - unrelated whitespace cleanup in `config/runtime/control_plane.yaml` and `src/fitcv/ingest.py`
  - new live-run trigger work not requested by current plan

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-06-26-11-35-fitcv-cp-ssot-immediate-patch-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-06-26-11-20-fitcv-cp-ssot-immediate-patch-spec.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/06-fitcv-cp-app-ssot-symmetry-refactor.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - runtime-owner consolidation landed
  - orchestration submission truth and queue identity patch landed
  - lifecycle/reconcile guards landed
  - run-contract parity and unknown-status diagnostics landed
  - settings canonicalization and single-key write failure surfacing landed
  - immediate template SSOT fixes landed
  - planning artifacts synced to completed lane state
- **In Progress:** none
- **Deferred / Dropped:**
  - unrelated repo-wide validator cleanup for Indeed adapter planning artifacts
  - unrelated pre-existing whitespace cleanup outside lane
- **Known divergence from plan (if any):**
  - plan-level repo-wide validator and `git diff --check` remain red for out-of-scope pre-existing drift; scoped `fitcv_cp` deliverables and targeted verification are green

## 4) Files Changed This Session

- `docs/superpowers/specs/2026-06-26-11-20-fitcv-cp-ssot-immediate-patch-spec.md` — marked execution-ready waves completed
- `docs/superpowers/plans/2026-06-26-11-35-fitcv-cp-ssot-immediate-patch-plan.md` — marked tasks completed and recorded truthful verification blockers
- `docs/intent/workstreams/threads/workstream-operator-control-plane/06-fitcv-cp-app-ssot-symmetry-refactor.md` — synced thread status and downstream follow-up artifacts
- `docs/superpowers/execution_context_packs/fitcv-cp-ssot-immediate-patch/latest.md` — canonical handoff packet for this lane
- `artifacts/execution_context_pack.md` — optional mirror of canonical handoff packet

## 5) Verification State

- **Last commands run:**
  - `python -m pytest tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "runtime or sqlite or bigquery or reconciler or submission or orchestration or retry or continue or redis or cancel or queued or running or jobs_input_manifest or unknown or diagnostics or settings or alias or canonical or save_setting or save_settings_group or template or hover or font"`
  - `python scripts/hooks/run_validator.py --fast`
  - `git diff --check`
- **Result summary:**
  - scoped `fitcv_cp` verification passed: `198 passed, 459 deselected`
  - repo-wide validator failed only on unrelated Indeed adapter planning artifacts and stale `docs/generated/planning_lineage.yaml`
  - `git diff --check` failed only on unrelated pre-existing whitespace issues
- **Failing checks (if any):**
  - `python scripts/hooks/run_validator.py --fast`
  - `git diff --check`
- **Gaps still unverified:**
  - no live-run trigger or live-run verification action is eligible from current plan artifacts
  - no full repo-green proof because remaining failures are outside bounded lane

## 6) Open Blockers / Risks

- repo-wide closeout proof remains noisy because unrelated planning lineage and whitespace issues still exist
- if full-repo green is required before merge/closeout, separate cleanup lane needed

## 7) Next Exact Action

Single smallest concrete action to run first in next session.

- **Action type:** closeout
- **Target:** this lane only
- **Exact command or edit intent:** treat `fitcv-cp-ssot-immediate-patch` as complete at lane scope and move to branch/PR closeout; do not trigger live run because current plan does not require one and targeted verification already covers adopted fixes
- **Why this is next:** in-scope code and focused verification are complete, planning artifacts now match that truth, and remaining red checks are unrelated repo drift outside lane

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** n/a
- **overview_log:** n/a
- **consult_if:** only if raw session chronology is needed beyond source files and this context pack
- **notes_from_log (optional, concise):** n/a

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
