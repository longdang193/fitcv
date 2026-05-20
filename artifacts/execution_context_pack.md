## 1) Objective

- **Workstream / Plan:** `workstream-operator-control-plane.operator-control-plane-run-detail-truth` / `docs/superpowers/plans/2026-05-20-17-21-pipeline-results-company-display-plan.md`
- **Goal:** Implement SSOT primary label format: `Job Title (Company, Location)` or `Job Title (Company)` when location missing, across Pipeline Results and Bookmarked Jobs.
- **Bounded Scope (in-scope only):** `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/run_detail.html`, `src/fitcv_cp/templates/bookmarks.html`, targeted tests, plan-state sync.
- **Out of Scope (explicit):** unrelated telemetry planning-artifact repair and global lineage regeneration.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-20-17-21-pipeline-results-company-display-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-20-16-07-pipeline-results-bookmark-feature-spec.md`, `docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md`
- **Governance / workflow rules used:** `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`, `docs/operating_system/templates/execution-context-pack-template.md`, `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:** Task 1 complete; Task 2 complete; Task 3 complete; Task 4 complete (Step 2 executed and deferred per explicit user decision).
- **In Progress:** none.
- **Deferred / Dropped:** none.
- **Known divergence from plan (if any):** validator blocked by pre-existing telemetry plan/spec contract drift unrelated to this lane.

## 4) Files Changed This Session

- `src/fitcv_cp/app.py` — added `_build_job_primary_label`, metadata mapping, run-detail/bookmark view-model wiring.
- `src/fitcv_cp/templates/run_detail.html` — switched primary link text to helper-prepared label; save form now carries company/location.
- `src/fitcv_cp/templates/bookmarks.html` — switched primary link text to helper-prepared label; removed inline concat logic.
- `tests/test_fitcv_cp/test_app.py` — added company/location and fallback primary-label tests; updated bookmark page assertion.
- `docs/superpowers/plans/2026-05-20-17-21-pipeline-results-company-display-plan.md` — plan status/checklist sync to completed with defer rationale captured.

## 5) Verification State

- **Last commands run:**
  - `pytest tests/test_fitcv_cp/test_app.py -k "bookmark or primary_label or company_location_label"`
  - `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
  - `python scripts/hooks/run_validator.py --fast`
- **Result summary:** targeted pytest commands passed; fast validator failed due unrelated telemetry plan/spec/doc lineage drift.
- **Failing checks (if any):**
  - `python scripts/hooks/run_validator.py --fast` with errors in `docs/superpowers/specs/2026-05-20-17-15-telemetry-ssot-symmetry-refactor-spec.md`, `docs/superpowers/plans/2026-05-20-17-20-telemetry-ssot-symmetry-refactor-plan.md`, and stale `docs/generated/planning_lineage.yaml`.
- **Gaps still unverified:** none in feature-scoped tests.

## 6) Open Blockers / Risks

- Global validator executed and deferred to telemetry lane owner by explicit user decision.
- Root instruction files currently dirty from GitNexus operations (`AGENTS.md`, `CLAUDE.md`, `.claude/skills/gitnexus/*`); must remain untouched unless explicitly requested.

## 7) Next Exact Action

- **Action type:** closeout merge
- **Target:** lane branch `codex/pipeline-results-company-display-impl` to `main`
- **Exact command or edit intent:** run closure pre-merge checks, fast-forward merge into local `main`, run post-merge checks, push `main`.
- **Why this is next:** lane implementation and scoped verification are complete; defer decision recorded and artifacts synchronized.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** current-codex-thread
- **overview_log:** `.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/overview.txt`
- **consult_if:** ambiguity about validator ownership and cross-lane policy appears.
- **notes_from_log (optional, concise):** n/a

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only

