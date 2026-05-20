# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-20-18-16-upload-jobs-provenance-plan.md`
- **Goal:** show upload-mode jobs path as merged artifact plus source-file provenance wording.
- **Bounded Scope (in-scope only):** `src/fitcv_cp/*` run metadata + list/detail rendering + tests; scoped unblock in `src/fitcv/ai_score.py` for test execution.
- **Out of Scope (explicit):** unrelated runtime behavior changes.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-20-18-16-upload-jobs-provenance-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
  - `docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/governance/repo-governance.md`

## 3) Current Task State

- **Completed:**
  - Upload provenance field persisted: `jobs_input_manifest_json`.
  - Upload trigger populates provenance filenames; non-upload modes remain fallback-safe.
  - Runs list/detail show invariant wording:
    - `data/uploads/<id>_merged_jobs.json (merged from: foo.json, bar.json, ...)`
  - CV analysis timeline summary patched to omit missing concurrency field.
  - Plan status synced to `completed`.
- **In Progress:**
  - none.
- **Deferred / Dropped:**
  - none.
- **Known divergence from plan (if any):**
  - none.

## 4) Files Changed This Session

- `src/fitcv_cp/models.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/templates/run_detail.html`
- `src/fitcv_cp/templates/runs_list.html`
- `tests/test_fitcv_cp/test_app.py`
- `src/fitcv/ai_score.py`
- `docs/superpowers/plans/2026-05-20-18-16-upload-jobs-provenance-plan.md`
- `docs/superpowers/execution_context_packs/upload-jobs-provenance-impl/latest.md`

## 5) Verification State

- **Last commands run:**
  - `pytest tests/test_fitcv_cp/test_app.py::test_run_detail_timeline_uses_bounded_cv_analysis_payload_counts -q`
  - `pytest tests/test_fitcv_cp/test_app.py -k "upload or jobs_path or run_detail or runs_list" -q`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_repo_contracts.py --fast`
- **Result summary:**
  - Focused regression: pass.
  - Targeted suite: `173 passed, 292 deselected`.
  - Closeout validators: pass.
- **Failing checks (if any):**
  - none.
- **Gaps still unverified:**
  - full end-to-end manual smoke on live upload run not re-run in this exact step.

## 6) Open Blockers / Risks

- no blocking defects in scoped implementation.
- residual risk: long provenance lists may reduce runs-list readability despite wrapping.

## 7) Next Exact Action

- **Action type:** close now
- **Target:** lane closure handoff
- **Exact command or edit intent:** prepare commit/push or merge flow per lane policy.
- **Why this is next:** all plan deliverables and strict closeout validators are satisfied.

## 8) Resume Prompt (Copy/Paste)

```text
Plan and context pack are closure-ready. Run lane closeout flow (commit/push/PR or reconcile) per governance.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:**
- **overview_log:** `.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/overview.txt`
- **consult_if:** closure orchestration ambiguity remains.

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
