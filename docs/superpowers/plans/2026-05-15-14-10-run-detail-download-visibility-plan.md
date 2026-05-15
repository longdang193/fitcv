---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: run-detail-download-visibility-contract
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-15-13-04-run-detail-download-visibility-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/store.py
  - tests/test_fitcv_cp/
related_features:
  - admin_control_plane_core
related_stages:
  - cv_generation
---

## Goal

Implement run-scoped `output_availability` contract so run detail UI always renders output download state explicitly (enabled or disabled with deterministic state), including the `generated_count > 0 && downloadable_count == 0` mismatch diagnostic, without schema migration.

## Key Deliverables

### Backend `output_availability` payload is single source of truth

`/admin/runs/{run_id}` route computes `output_availability` with `generated_count`, `version_row_count`, `downloadable_count`, and `state`, and passes it to `run_detail.html` as mandatory context.

### Run detail header renders persistent outputs action region

`run_detail.html` renders outputs action region regardless of run status, enables CTA when `downloadable_count > 0`, and renders disabled state messaging otherwise (no silent hiding).

### Mismatch and empty-state diagnostics are deterministic and testable

Template and backend changes include focused tests that prove `state` selection and rendering behavior for `available / none_generated / mismatch` (and `not_ready` only if explicitly used), while preserving existing download URLs.

## Task/Wave Breakdown

### Task 1: Baseline current behavior + define exact state precedence

**Purpose:**
- lock down current split-brain behavior (`run.cvs_generated` vs `cv_versions`) and define deterministic `output_availability.state` precedence (razor: smallest set needed to satisfy spec acceptance criteria)

**Files:**
- Inspect: `src/fitcv_cp/app.py` (route `admin_run_detail`)
- Inspect: `src/fitcv_cp/templates/run_detail.html` (Pipeline Results banner)
- Inspect: `src/fitcv_cp/store.py` (store wrappers)
- Inspect: `src/fitcv_cp/bq_store.py` (cv_versions query / markdown fetch)
- Verify: `docs/superpowers/specs/2026-05-15-13-04-run-detail-download-visibility-spec.md`

**Preconditions:**
- spec approved (this plan assumes contract shape is final)

**Steps:**
- [x] Step 1: identify exact inputs available in `admin_run_detail` for `generated_count`, version rows, and download link construction
- [x] Step 2: define deterministic `state` precedence and document it in code docstring / test matrix (no extra reason taxonomy)
- [x] Step 3: decide whether `not_ready` is needed; if not needed, omit it entirely from implementation

**Verification:**
- [x] inspection notes capture existing template gate and mismatch scenario

**Exit Criteria:**
- `state` mapping is unambiguous and bounded to acceptance criteria

### Task 2: Implement backend `output_availability` view-model builder

**Purpose:**
- compute single `output_availability` payload in backend so template stops inferring state from multiple fields

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/store.py` (optional helper exposure only if needed)
- Modify: `src/fitcv_cp/bq_store.py` (only if `downloadable_count` needs a new query shape; prefer reusing existing row shape)
- Add/Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py` (or similar)

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: add small pure function (or dataclass) that maps `(run, cv_versions)` -> `output_availability`
- [x] Step 2: define `downloadable_count` using same rules used by download link rendering (avoid false positives on missing `version_id`)
- [x] Step 3: wire payload into `admin_run_detail` template context as mandatory key

**Verification:**
- [x] unit tests cover `available / none_generated / mismatch` state mapping with minimal fixtures

**Exit Criteria:**
- backend contract exists and can be validated without rendering template

### Task 3: Refactor `run_detail.html` to use `output_availability` only

**Purpose:**
- ensure download visibility never silently hides and mismatch is explicit

**Files:**
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Add/Modify: `tests/test_fitcv_cp/test_run_detail_template_render.py` (or fold into Task 2 test file)

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: add header-level outputs action region that always renders and uses `output_availability.downloadable_count` for enablement
- [x] Step 2: replace existing Pipeline Results banner conditional that currently requires `run.status == succeeded && run.cvs_generated is not none`
- [x] Step 3: render explicit empty-state block when `output_availability.state != available`, including `mismatch` when `generated_count > 0 && downloadable_count == 0`

**Verification:**
- [x] template render test asserts presence of outputs action region regardless of run status
- [x] template render test asserts mismatch diagnostic presence for `mismatch`

**Exit Criteria:**
- template has single source of truth (`output_availability`) and no silent hide path

### Task 4: Guardrails: preserve download URLs + existing artifacts behavior

**Purpose:**
- ensure per-CV download links and artifact bundle endpoints remain compatible

**Files:**
- Inspect: `src/fitcv_cp/app.py` (download endpoints: `/admin/cvs/{version_id}/download`, artifacts zip route if present)
- Verify: tests added in Tasks 2–3

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Step 1: assert template continues to render `/admin/cvs/<version_id>/download` unchanged when rows exist
- [x] Step 2: if artifacts zip endpoint exists for run, confirm unchanged behavior with targeted test (mock store) or source inspection

**Verification:**
- [x] tests assert anchor hrefs unchanged

**Exit Criteria:**
- new contract changes visibility/diagnostics only; download mechanics unchanged

## Verification

- `python -m pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -p no:tmpdir -p no:cacheprovider -vv`
- `python -m pytest tests/test_fitcv_cp/test_app.py -k "admin_run_detail_success_banner or cv_versions_show_job_title or cv_versions_fallback_when_no_title" -p no:tmpdir -p no:cacheprovider -vv`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. `output_availability` is mandatory route payload and is the sole template input for output visibility decisions
5. acceptance criteria in `docs/superpowers/specs/2026-05-15-13-04-run-detail-download-visibility-spec.md` are covered by automated tests or explicit render assertions

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
