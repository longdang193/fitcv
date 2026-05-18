---
name: execution-context-pack
template_id: execution-context-pack-template
document_type: execution_context_pack
---

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md`
- **Goal:** Execute bounded SSOT/symmetry/invariance refactor and issue patches for `fitcv_cp` worker flow.
- **Bounded Scope (in-scope only):** `worker_job.py`, `synonym_proposals.py`, shared helper extraction, tests, execution docs sync.
- **Out of Scope (explicit):** merge/closeout orchestration, broad pipeline behavior redesign, unrelated feature work.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-18-21-35-fitcv-cp-worker-job-refactor-and-issue-patch-spec.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:** Task 1 preflight and GitNexus impact/context capture.
- **In Progress:** Task 2 (shared artifact-contract helper extraction).
- **Deferred / Dropped:** none.
- **Known divergence from plan (if any):** none.

## 4) Files Changed This Session

- `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md` — Task 1 checklist state synced.
- `docs/superpowers/execution_context_packs/fitcv-cp-worker-job-refactor-and-issue-patch-impl/latest.md` — canonical context pack created.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze`
  - `npx gitnexus context execute_pipeline_run --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-cp-worker-job-refactor-and-issue-patch-impl"`
  - `npx gitnexus impact <symbol> --direction upstream --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-cp-worker-job-refactor-and-issue-patch-impl"`
- **Result summary:** index refreshed; all targeted pre-edit impacts reported `LOW`.
- **Failing checks (if any):**
  - baseline `uvx pytest -q` fails in collection due missing dependencies (`yaml`, `jinja2`, `pydantic`, `fastapi`, `google.cloud`, `httpx`, ...).
- **Gaps still unverified:** post-refactor regression/type checks pending after edits.

## 6) Open Blockers / Risks

- missing Python dependencies in workspace block meaningful full test pass.
- high-surface function `execute_pipeline_run` remains risk area; mitigate with extraction-only edits and parity checks.

## 7) Next Exact Action

- **Action type:** edit
- **Target:** `src/fitcv_cp/run_artifact_contracts.py` + `src/fitcv_cp/worker_job.py`
- **Exact command or edit intent:** add shared helpers for run-mode normalization and replay-context projection; wire artifact builders to helper APIs without payload key/schema changes.
- **Why this is next:** first eligible unblocked action from Task 2 after Task 1 preflight completion.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **overview_log:** none
- **consult_if:** only if source files and context pack diverge.
- **notes_from_log (optional, concise):** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
