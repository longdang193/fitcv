# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-15-14-10-run-detail-download-visibility-plan.md`
- **Goal:** Add run-scoped `output_availability` payload + deterministic UI download visibility in run detail.
- **Bounded Scope (in-scope only):** `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/run_detail.html`, small focused tests under `tests/test_fitcv_cp/`.
- **Out of Scope (explicit):** DB schema migrations; CV generation logic changes; orchestration sequencing changes.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-15-14-10-run-detail-download-visibility-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-15-13-04-run-detail-download-visibility-spec.md`, `docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md`
- **Governance / workflow rules used:** `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`, `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:** Task 1, Task 2, Task 3, Task 4
- **In Progress:** none
- **Deferred / Dropped:** none
- **Known divergence from plan (if any):**
  - Live-run debugging revealed sqlite backend run-status staleness due to in-process cache; applied bounded fix in `src/fitcv_cp/bq_store.py` to keep `/runs/<id>` accurate under `docker compose` web+worker split.

## 4) Files Changed This Session

- `src/fitcv_cp/app.py` — add `_build_output_availability` + wire into `admin_run_detail` context as `output_availability`
- `src/fitcv_cp/templates/run_detail.html` — add persistent Outputs action card + refactor Pipeline Results to use `output_availability`
- `src/fitcv_cp/bq_store.py` — fix sqlite run-status staleness by reading sqlite source-of-truth instead of in-process cache
- `tests/test_fitcv_cp/test_run_detail_output_availability.py` — add state-matrix tests + template-contract presence assertion
- `docs/superpowers/plans/2026-05-15-14-10-run-detail-download-visibility-plan.md` — mark Tasks 1–3 completed in checklist
- `artifacts/execution_context_pack.md` — mirror pointer to canonical context pack

## 5) Verification State

- **Last commands run:**
  - `python -m pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -p no:anyio -p no:langsmith -p no:tmpdir -p no:cacheprovider -vv`
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "admin_run_detail_success_banner or cv_versions_show_job_title or cv_versions_fallback_when_no_title" -p no:anyio -p no:langsmith -p no:tmpdir -p no:cacheprovider -vv`
  - `python scripts/validate_repo_contracts.py --fast`
- **Live-run evidence (docker mode):**
  - Run created: `7034068f-9487-4f12-af4b-f333612c1d42`
    - Worker completed job OK, but `/runs/<id>` initially returned `status=queued` (stale) while `/runs/<id>/events` showed `pipeline_complete`.
    - After `src/fitcv_cp/bq_store.py` fix + `docker compose up -d --build web worker`, `/runs/7034068f-9487-4f12-af4b-f333612c1d42` returned `status=succeeded` with `started_at/finished_at` populated.
  - Run created post-fix: `d7030f71-d129-4e3c-b9af-28372762ce6b`
    - `/runs/d7030f71-d129-4e3c-b9af-28372762ce6b` reached `status=succeeded`.
    - Initial `/admin/runs/d7030f71-d129-4e3c-b9af-28372762ce6b` showed `state=mismatch` with meta `generated=1, version_rows=0, downloadables=0`.
    - Root cause: `src/fitcv_cp/bq_store.py` sqlite CV-version functions gated on `FITCV_CP_DATA_BACKEND` env, but docker runtime selects sqlite via `config/runtime/control_plane.yaml` (no env), so web returned empty CV list.
    - Bounded fix: treat `bq is None` as sqlite mode in `list_cvs_for_run`, `get_cv_markdown`, `insert_cv_version_row`.
    - After `docker compose up -d --build web worker`, `/admin/runs/d7030f71-d129-4e3c-b9af-28372762ce6b` shows `state=available` meta `generated=1, version_rows=1, downloadables=1`, and download endpoint `/admin/cvs/9603dfdf-9393-41ae-a757-12c4ed54b2d4/download` returns `200`.
- **Result summary:** selected tests passed; repo contracts passed
- **Failing checks (if any):** n/a
- **Gaps still unverified:** none (run-detail download visibility still not re-validated in browser UI)

## 6) Open Blockers / Risks

- GitNexus stale (advisory-only). Source code is authority.
- Live run `d7030f71-d129-4e3c-b9af-28372762ce6b` still running at last check; completion can be re-polled for final `succeeded/failed`.

## 7) Next Exact Action

- **Action type:** verification (live run)
- **Target:** live run `d7030f71-d129-4e3c-b9af-28372762ce6b`
- **Exact command or edit intent:** poll `/runs/<id>` until terminal, then open `/admin/runs/<id>` and confirm Outputs card state matches `output_availability`.
- **Why this is next:** closest end-to-end proof for run-detail UI contract after backend+template changes.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
