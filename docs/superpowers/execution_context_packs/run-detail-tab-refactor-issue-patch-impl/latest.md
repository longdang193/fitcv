# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `workstream-agentic-observability.agentic-observability-operator-surface` / `docs/superpowers/plans/2026-05-19-16-12-run-detail-tab-refactor-and-issue-patch-plan.md`
- **Goal:** Execute run-detail template SSOT/symmetry refactor and issue patches.
- **Bounded Scope (in-scope only):** `run_detail.html`, `run_detail_tab_enriched.html`, `run_detail_tab_jobs_input.html`, `run_detail_tab_profile.html`, shared snapshot partial, related tests.
- **Out of Scope (explicit):** backend API/schema changes, unrelated UI redesign, merge/closeout orchestration.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-19-16-12-run-detail-tab-refactor-and-issue-patch-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-19-16-10-run-detail-tab-refactor-spec.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/governance/repo-governance.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - GitNexus index refreshed in active worktree.
  - Plan critical review complete; alignment to thread confirmed.
- **In Progress:**
  - Task 1 (shared snapshot-tab rendering contract).
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - none

## 4) Files Changed This Session

- `docs/superpowers/execution_context_packs/run-detail-tab-refactor-issue-patch-impl/latest.md` — initialized canonical execution context pack.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze`
  - `npx gitnexus impact -r fitcv "ensureTabLoaded" --direction upstream`
- **Result summary:**
  - index refreshed successfully
  - impact lookup returned target not found for template JS symbol
- **Failing checks (if any):**
  - none
- **Gaps still unverified:**
  - Task 1 template parity and tests not yet executed.

## 6) Open Blockers / Risks

- Template JS helpers may not resolve through GitNexus symbol graph; source-first inspection required for template-level refactors.

## 7) Next Exact Action

- **Action type:** edit
- **Target:** `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`, `src/fitcv_cp/templates/run_detail_tab_profile.html`, new shared partial
- **Exact command or edit intent:** implement shared snapshot partial/include and swap both tabs to it without text drift.
- **Why this is next:** first eligible unblocked task in plan dependency order.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** not recorded
- **overview_log:** not used
- **consult_if:** ambiguity remains after source and plan review
- **notes_from_log (optional, concise):** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
