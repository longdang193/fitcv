# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-24-10-05-fitcv-cp-app-ssot-symmetry-refactor-plan.md`
- **Goal:** Execute R1–R5 refactor for `src/fitcv_cp/app.py` SSOT/symmetry/invariance with tests + validators green.
- **Bounded Scope (in-scope only):**
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/run_artifact_contracts.py`
  - `src/fitcv_cp/store.py` (minimal interface tightening only if needed)
  - `src/fitcv_cp/orchestrator.py` (minimal interface tightening only if needed)
  - related tests
- **Out of Scope (explicit):**
  - BigQuery schema changes
  - route/API shape changes (unless required to resolve contradictions; then split)
  - `fitcv.pipeline` internal refactor

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-24-10-05-fitcv-cp-app-ssot-symmetry-refactor-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-24-10-02-fitcv-cp-app-ssot-symmetry-refactor-spec.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/06-fitcv-cp-app-ssot-symmetry-refactor.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Worktree:** `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-cp-app-ssot-symmetry-refactor`
- **Branch:** `codex/fitcv-cp-app-ssot-symmetry-refactor`
- **Status:** plan complete, pushed to origin.
- **Last pushed commit:** `c8f0da7d`

## 4) Files Changed (Lane)

- `src/fitcv_cp/app.py` — R1/R2/R3/R4/R5 changes + endpoint hardening (409 on invalid JSON export payloads)
- `src/fitcv_cp/run_artifact_contracts.py` — SSOT run-mode + JSON/schema helpers
- `src/fitcv_cp/orchestrator.py` — `RunSubmission` back-compat init (`backend=` kw)
- `src/fitcv_cp/settings_schema.py` — section + defaults contract alignment
- `src/fitcv_cp/synonym_proposals.py` — targeted typing annotation + runtime-default alignment
- `src/fitcv_cp/templates/settings.html` — UI string contract alignment
- `src/fitcv_cp/templates/_cv_review_queue.html` — deterministic hint string for tests
- `tests/test_fitcv_cp/test_run_artifact_contracts.py` — invariance tests
- `pyproject.toml`, `uv.lock` — dev dep update (`tzdata`) + lock refresh
- `docs/superpowers/plans/2026-05-24-10-05-fitcv-cp-app-ssot-symmetry-refactor-plan.md` — task-state sync
- `artifacts/execution_context_pack.md` — mirror pointer

## 5) Verification Evidence

- `python scripts/hooks/run_validator.py --fast` PASS
- `uv run pytest tests/test_fitcv_cp/` PASS (882 tests)
- `uv run pytest tests/test_fitcv_cp/test_app.py -k "synonym_proposals_regenerate"` PASS
- `uv run mypy src/fitcv_cp/synonym_proposals.py --show-error-codes` PASS
- `uv run mypy src --show-error-codes` FAIL (known baseline typing/stubs issues outside lane)
- `npx gitnexus detect-changes -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT\\.worktrees\\fitcv-cp-app-ssot-symmetry-refactor" --scope staged` Risk: critical (expected; `app.py` blast radius)
- Closeout validators:
  - `python scripts/validate_planning_lifecycle.py --strict` PASS
  - `python scripts/validate_checkpoint_packs.py` PASS
  - `python scripts/validate_repo_contracts.py --fast` PASS

## 6) Open Blockers / Risks

- None for lane completion.
- Note: repo-wide mypy not green; do not treat as regression from this lane unless proven.

## 7) Next Exact Action

- Optional: open PR for branch `codex/fitcv-cp-app-ssot-symmetry-refactor` and request review/merge.

## Source-Truth Rule

If context pack, source files, and raw checks disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only

