# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-24-12-20-pipeline-extract-job-url-title-nameerror-fix-plan.md`
- **Goal:** Restore live-run pipeline stability by removing invalid `_extract_job_url` / `_extract_job_title` references in stage-transition artifact wiring.
- **Bounded Scope (in-scope only):**
  - `src/fitcv/pipeline.py`
  - targeted tests under `tests/test_pipeline.py` (stage-transition artifacts subset)
- **Out of Scope (explicit):**
  - broader pipeline refactors
  - settings/runtime contract redesign
  - control-plane UI changes

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-24-12-20-pipeline-extract-job-url-title-nameerror-fix-plan.md`
- **Specs / maps / thread docs:** none (bugfix lane)
- **Governance / workflow rules used:**
  - `docs/operating_system/prompt_templates/single-lane-merge-and-reconcile-prompt.md`
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:**
  - Root cause confirmed: `src/fitcv/pipeline.py` referenced `_extract_job_url` / `_extract_job_title` but symbols not defined.
  - Fix applied: wire to imported `extract_job_url` / `extract_job_title`.
  - Verification: tests + validator + live run succeed (see Section 5).
  - Branch pushed: `codex/fix-pipeline-extract-job-url-nameerror` (commit `041174f1`).
- **In Progress:**
  - Merge/reconcile into `main` (closure actions).
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - none

## 4) Files Changed This Session

- `src/fitcv/pipeline.py` — restore job URL/title extractor wiring for stage-transition artifacts.

## 5) Verification State

- **Last commands run:**
  - `python scripts/hooks/run_validator.py --fast` (PASS)
  - `uv run pytest tests/test_pipeline.py -k "stage_transition_artifacts"` (PASS; 13 tests)
  - Live run (Docker compose):
    - `docker compose up -d --build redis web worker`
    - `GET http://localhost:8000/healthz` (200)
    - `POST http://localhost:8000/runs` (201) and poll `GET /runs/{run_id}` to terminal `status=succeeded`
    - `docker compose down`
- **Result summary:**
  - stage-transition artifacts no longer crash with `NameError`
  - live run reaches `status=succeeded` (example run: `4c6941d3-838b-4e0a-ba63-5abbbf5fdf31`)
- **Failing checks (if any):**
  - none observed in bounded scope
- **Gaps still unverified:**
  - full pipeline regression suite

## 6) Open Blockers / Risks

- None for merge, assuming `main` is clean and fast-forward possible.

## 7) Next Exact Action

- **Action type:** merge + verification
- **Target:** merge `codex/fix-pipeline-extract-job-url-nameerror` into `main`
- **Exact command or edit intent:**
  - run `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
  - `git checkout main && git pull --ff-only && git merge --ff-only codex/fix-pipeline-extract-job-url-nameerror`
  - rerun `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
  - `git push origin main`
- **Why this is next:**
  - lane complete and verified; needs merge to restore normal live runs on `main`.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **consult_if:** need raw docker logs / run ids beyond current evidence

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only

