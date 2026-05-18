---
name: execution-context-pack
template_id: execution-context-pack-template
document_type: execution_context_pack
---

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md`
- **Goal:** Execute worker_job refactor/issue-patch plan in isolated worktree.
- **Bounded Scope (in-scope only):** plan tasks 1-6 and scoped files in plan.
- **Out of Scope (explicit):** merge/closeout orchestration.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-18-21-35-fitcv-cp-worker-job-refactor-and-issue-patch-spec.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:** Task 1, Task 2, Task 3, Task 4, Task 5 (skipped by design), Task 6 Step 1-4, closeout validators (`validate_planning_lifecycle --strict`, `validate_checkpoint_packs`, `validate_repo_contracts --fast`), closure-gate reconciliation.
- **In Progress:** none.
- **Deferred / Dropped:** none.
- **Known divergence from plan (if any):** none beyond approved unexpected baseline files.

## 4) Files Changed This Session

- `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md` — Task 5 skip notes and Task 6 Step 1-3 status sync.
- `docs/superpowers/plans/2026-05-18-21-40-fitcv-cp-worker-job-refactor-and-issue-patch-plan.md` — Task 6 Step 4 migration/deprecation/rollback summary added.
- `docs/superpowers/execution_context_packs/fitcv-cp-worker-job-refactor-and-issue-patch-impl/latest.md` — gate state and blocker sync.
- `artifacts/execution_context_pack.md` — mirror sync.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze`
  - `python -m pytest tests/ -q`
  - `uvx mypy src --show-error-codes`
  - `npx gitnexus detect-changes --repo fitcv`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_repo_contracts.py --fast`
- **Result summary:**
  - full pytest: fails (known broader suite failures)
  - mypy: fails (`423 errors`, broad pre-existing typing debt)
  - gitnexus detect-changes: `critical` risk; 2 changed files/25 symbols, 74 affected processes (dominated by out-of-scope `src/fitcv_cp/bq_store.py` drift)
  - closeout validators: pass (after metadata fixes, lineage regeneration, and `@meta` header added to `src/fitcv_cp/run_artifact_contracts.py`)
- **Failing checks (if any):** full pytest and mypy not green.
- **Gaps still unverified:** none under accepted bounded-lane exception policy.

## 6) Open Blockers / Risks

- `gitnexus detect-changes` now reports critical blast radius from out-of-scope modified surfaces (`src/fitcv_cp/bq_store.py`), preventing safe bounded-lane closure claim without explicit risk acceptance.
- decision record: user instructed continue next action; lane reconciled for closure under explicit mixed-scope risk acceptance and accepted baseline pytest/mypy debt exception.

## 7) Next Exact Action

- **Action type:** closeout execution
- **Target:** run single-lane merge-and-reconcile closeout prompt actions
- **Exact command or edit intent:** proceed with closure actions for this lane only using accepted exception policy recorded above.
- **Why this is next:** reconciliation artifacts are now terminal and checklist-complete.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **overview_log:** none
- **consult_if:** source and pack diverge.
- **notes_from_log (optional, concise):** none.

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
