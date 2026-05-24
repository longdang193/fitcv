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

- **Completed:**
  - Worktree: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-cp-app-ssot-symmetry-refactor` on branch `codex/fitcv-cp-app-ssot-symmetry-refactor`
  - GitNexus indexed (worktree path): `npx gitnexus analyze` PASS
  - Validator (hook subset): `python scripts/hooks/run_validator.py --fast` PASS
  - Task 1 (R1): remove shadow-import collisions in `src/fitcv_cp/app.py` (favor `bq_store_module` / `_persist_*`)
  - Task 2 (R3): remove `RUN_MODE_LABELS` from `src/fitcv_cp/app.py`; route UI/manifests to `fitcv_cp.run_artifact_contracts.run_mode_label`
  - Task 2 verification: add `tzdata` to dev deps (Windows zoneinfo), update `uv.lock`, focused unit tests PASS
  - Task 3 (R4): centralize JSON decode/pretty/schema helpers; remove ad-hoc JSON parsing drift; tests added
  - Task 4 (R2): centralize RunStore backend selection via `_resolve_run_store`
  - Task 5 (R5): bound `_RUN_SUBMISSION_CACHE` (TTL + max size + pruning) and keep submit/continue invariants
- **In Progress:**
  - Task 6: final proof + scope check (commit/push remaining; typecheck baseline noted)
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - none

## 4) Files Changed This Session

- `src/fitcv_cp/app.py` — R1/R2/R3/R4/R5 changes + UX text alignment for settings/review surfaces
- `src/fitcv_cp/orchestrator.py` — `RunSubmission` init supports `backend=` kw for back-compat tests
- `tests/test_fitcv_cp/test_run_artifact_contracts.py` — run-mode invariance tests
- `src/fitcv_cp/settings_schema.py` — agentic section + default contract alignment
- `src/fitcv_cp/synonym_proposals.py` — synonym-management runtime defaults (mode) retained
- `src/fitcv_cp/templates/_cv_review_queue.html` — add deterministic message string for tests/UX
- `src/fitcv_cp/templates/settings.html` — restore SSOT UI strings/contracts expected by tests
- `pyproject.toml` — add `tzdata` to dev deps
- `uv.lock` — lock update after dev dep change
- `docs/superpowers/plans/2026-05-24-10-05-fitcv-cp-app-ssot-symmetry-refactor-plan.md` — sync task checkbox state + notes
- `docs/superpowers/execution_context_packs/fitcv-cp-app-ssot-symmetry-refactor-impl/latest.md` — keep lane handoff current
- `artifacts/execution_context_pack.md` — mirror pointer

## 5) Verification State

- **Last commands run:**
  - `python scripts/hooks/run_validator.py --fast`
  - `uv run pytest tests/test_fitcv_cp/test_run_artifact_contracts.py`
  - `uv run pytest tests/test_fitcv_cp/test_app.py`
  - `uv run pytest tests/test_fitcv_cp/`
  - `uv run pytest tests/test_fitcv_cp/test_app.py -k "synonym_proposals_regenerate"`
  - `uv run mypy src --show-error-codes` (fails on known baseline issues outside lane)
  - `uv run mypy src/fitcv_cp/synonym_proposals.py --show-error-codes` (PASS)
  - `npx gitnexus impact build_synonym_proposals_payload -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT\\.worktrees\\fitcv-cp-app-ssot-symmetry-refactor" --direction upstream --include-tests` (Risk: HIGH; change was type-only)
  - `npx gitnexus detect-changes -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT\\.worktrees\\fitcv-cp-app-ssot-symmetry-refactor" --scope all` (Risk: critical; expected for `app.py`)
- **Result summary:**
  - validator PASS
  - `tests/test_fitcv_cp/` PASS
- **Failing checks (if any):**
  - `uv run mypy src --show-error-codes` fails due to pre-existing typing/stubs issues in `src/fitcv/*` (ex: missing `yaml` stubs) and unrelated typing drift; lane-fixed file `src/fitcv_cp/synonym_proposals.py` now mypy-clean when checked alone.
- **Gaps still unverified:**
  - broader regression suite (`uv run pytest tests/`)
  - full typecheck green (not currently true repo-wide)

## 6) Open Blockers / Risks

- Risk: `src/fitcv_cp/app.py:get_run` has high blast radius; require GitNexus impact check before editing any core symbols; prefer minimal edits per task.
- Note: `uvx pytest ...` may lack dev deps; lane uses `uv sync --group dev` + `uv run pytest ...` for test verification.

## 7) Next Exact Action

- **Action type:** command + edit
- **Target:** Plan Task 6 (final proof) + commit/push
- **Exact command or edit intent:**
  - Stage changes + commit with lane summary
  - Push branch `codex/fitcv-cp-app-ssot-symmetry-refactor`
- **Why this is next:**
  - R1–R5 deliverables landed + verified; remaining work is closeout + handoff.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- conversation_id: none
- consult_if: need raw terminal evidence beyond plan/spec/thread/context pack

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
