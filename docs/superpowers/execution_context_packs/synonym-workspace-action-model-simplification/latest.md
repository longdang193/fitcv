# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `workstream-agentic-synonym-management` / `docs/superpowers/plans/2026-05-19-23-10-synonym-workspace-action-model-simplification-plan.md`
- **Goal:** execute synonym workspace action-model simplification in isolated worktree.
- **Bounded Scope (in-scope only):** Task 1 redirect normalization first, then subsequent plan tasks.
- **Out of Scope (explicit):** merge/closeout orchestration, unrelated failing test remediation outside plan scope.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-19-23-10-synonym-workspace-action-model-simplification-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-19-22-45-synonym-workspace-action-model-simplification-spec.md`
  - `docs/intent/workstreams/threads/workstream-agentic-synonym-management/04-agentic-synonym-canonical-promotion-flow.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/templates/execution-context-pack-template.md`

## 3) Current Task State

- **Completed:**
  - isolated worktree created: `.worktrees/synonym-workspace-action-model-simplification`
  - GitNexus index refreshed in worktree (`npx gitnexus analyze`)
  - plan/spec/thread reviewed and aligned to thread goal.
  - Task 1 redirect normalization completed:
    - `triage-refresh` -> `/synonym-review`
    - `ai-fast-path-execute` -> `/synonym-review`
    - `promote-commit` (success/conflict) -> `/synonym-review`
  - Task 1 targeted redirect tests passing.
- **In Progress:**
  - Task 2: simplify workspace action surface.
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - baseline synonym test suite in this branch already has pre-existing failures.

## 4) Files Changed This Session

- `docs/superpowers/execution_context_packs/synonym-workspace-action-model-simplification/latest.md` — canonical execution context initialization.
- `src/fitcv_cp/app.py` — synonym action redirect normalization for workspace-origin flows.
- `tests/test_fitcv_cp/test_app.py` — redirect assertions updated and AI fast-path redirect test added.
- `docs/superpowers/plans/2026-05-19-23-10-synonym-workspace-action-model-simplification-plan.md` — Task 1 checklist progress marked complete.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze`
  - `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym"`
  - `pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh_redirects_with_summary or ai_fast_path_redirects_to_synonym_review or promote_commit_updates_global_policy_and_redirects or promote_commit_accepts_checkbox_selection_list"`
- **Result summary:**
  - GitNexus index refreshed successfully.
  - Baseline synonym tests: failing (`11 failed, 59 passed`) with pre-existing issues.
  - Task 1 redirect matrix targeted tests: pass (`3 passed`).
- **Failing checks (if any):**
  - `NameError: request is not defined` in synonym overlay upload route.
  - multiple run-detail synonym UI expectation mismatches.
- **Gaps still unverified:**
  - post-edit redirect matrix for Task 1.

## 6) Open Blockers / Risks

- existing baseline failures can mask regressions if broad test selection used.
- run-detail vs workspace tests may need coordinated expectation updates in later tasks.

## 7) Next Exact Action

- **Action type:** edit
- **Target:** `src/fitcv_cp/templates/synonym_review.html` + `tests/test_fitcv_cp/test_app.py`
- **Exact command or edit intent:** execute Task 2 by removing per-row instant decision POST buttons and simplifying AI/manual control language to explicit assist behavior while preserving batch lane.
- **Why this is next:** Task 1 exit criteria satisfied; Task 2 is next eligible unblocked step in dependency order.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** current Codex thread
- **overview_log:** none
- **consult_if:** ambiguity on lane sequencing beyond plan
- **notes_from_log (optional, concise):** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
