# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `workstream-operator-control-plane.operator-control-plane-agentic-settings-surface` / `docs/superpowers/plans/2026-05-17-14-39-settings-page-deprecated-surface-removal-plan.md`
- **Goal:** remove deprecated settings controls from `/admin/settings` and enforce write rejection on hidden deprecated keys.
- **Bounded Scope (in-scope only):** settings schema visibility contract, admin settings render filtering, settings-save route guardrails, tests, and docs sync.
- **Out of Scope (explicit):** runtime compatibility projection removal, pipeline/stage logic changes, run-history schema changes.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-17-14-39-settings-page-deprecated-surface-removal-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-17-14-38-settings-page-deprecated-surface-removal-spec.md`, `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`
- **Governance / workflow rules used:** `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`, `docs/operating_system/templates/execution-context-pack-template.md`, `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:** Plan Tasks 1-5 implemented; deprecated key visibility contract landed; render/save guardrails landed; tests/docs/validators passed.
- **In Progress:** none.
- **Deferred / Dropped:** none.
- **Known divergence from plan (if any):** none.

## 4) Files Changed This Session

- `src/fitcv_cp/settings_schema.py` — added `ui_deprecation_state` and hidden deprecated key helper; marked `cv_generation_model` as `hidden_deprecated`; removed it from `CV_GROUPS["cv-preset"]`.
- `src/fitcv_cp/app.py` — filtered hidden deprecated keys from settings cards/keys; added 422 rejection for hidden deprecated writes across single-key/group/section routes.
- `tests/test_fitcv_cp/test_app.py` — updated legacy expectations and added assertions for hidden deprecated render/write rejection behavior.
- `docs/configuration.md` — documented `hidden-deprecated` operator-surface semantics.
- `docs/superpowers/plans/2026-05-17-14-39-settings-page-deprecated-surface-removal-plan.md` — task checklist/progress log updated to executed state.

## 5) Verification State

- **Last commands run:**
  - `pytest tests/test_fitcv_cp/test_app.py -q`
  - `python scripts/hooks/run_validator.py --fast`
  - `python scripts/validate_repo_contracts.py --fast`
- **Result summary:** `388 passed` for `test_app`; fast validator and repo-contract fast checks passed.
- **Failing checks (if any):** none.
- **Gaps still unverified:** full-repo pytest not rerun (out-of-scope for this patch).

## 6) Open Blockers / Risks

- No active blocker.
- Residual product risk: hidden deprecated key still exists in compatibility layer; future cleanup can remove key completely after deprecation gate approval.

## 7) Next Exact Action

- **Action type:** closeout verification
- **Target:** strict closeout gate commands for this execution request.
- **Exact command or edit intent:** run `validate_planning_lifecycle --strict`, `validate_checkpoint_packs`, `validate_repo_contracts --fast`.
- **Why this is next:** plan tasks are complete and user requested closeout gates when workstream/plan closes.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify strict closeout gates, then prepare branch finish summary with changed files, verification evidence, and remaining follow-ups.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** current Codex thread
- **overview_log:** `.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/overview.txt`
- **consult_if:** ambiguity between prior AI-plane lane and this settings-lane execution state.
- **notes_from_log (optional, concise):** none.

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
