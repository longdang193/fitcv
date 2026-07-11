---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: delete-archived-runs
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-06-25-11-41-delete-archived-runs-spec.md
targets:
  - src/fitcv_cp/store.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/usage.md
  - docs/api.md
  - docs/generated/planning_lineage.yaml
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages: []
---

## Goal

Implement `Delete archived runs` as one bulk archived-view cleanup action with
server-owned eligibility, destructive confirmation, run-owned artifact cleanup,
and focused regression coverage.

## Key Deliverables

### Deliverable 1: Store-backed archived-run deletion contract

`src/fitcv_cp/store.py` and `src/fitcv_cp/bq_store.py` expose one canonical
bulk-delete API that selects archived runs by `archived_at` age, deletes only
eligible runs, and removes run-owned persisted surfaces together.

### Deliverable 2: Admin route and archived-view UI

`src/fitcv_cp/app.py` and `src/fitcv_cp/templates/runs_list.html` add archived
view controls for age-filtered deletion, confirmation, and truthful processed
feedback without introducing generic cache-clearing behavior.

### Deliverable 3: Regression coverage and doc alignment

Focused tests prove eligibility, destructive scope, no-match behavior, and
protection of non-run/shared data; `docs/usage.md` and `docs/api.md` reflect the
new lifecycle step.

## Task/Wave Breakdown

### Task 1: Add canonical store/delete contract for archived runs

**Purpose:**
- create one SSOT deletion entrypoint instead of scattering run-row and
  artifact cleanup logic across route code

**Files:**
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`

**Preconditions:**
- approved spec exists at `docs/superpowers/specs/2026-06-25-11-41-delete-archived-runs-spec.md`
- current archive/unarchive helpers remain non-destructive and unchanged in meaning

**Steps:**
- [ ] Step 1: extend `RunStore` with one bulk delete method shaped around
      server-owned filter input, not caller-supplied run ids.
- [ ] Step 2: add `ControlPlaneStore` pass-through wiring to the new bq/local
      delete helper.
- [ ] Step 3: implement local-mode helper in `bq_store.py` that:
  - computes eligible archived runs from `archived_at`
  - deletes run rows from local in-memory/local persistence surfaces
  - deletes local event history and deterministic mirror folder
  - returns deleted count and possibly deleted run ids for route feedback
- [ ] Step 4: implement BigQuery-mode helper in `bq_store.py` that deletes:
  - `pipeline_runs` rows for eligible archived runs
  - `pipeline_run_events` rows for those runs
  - any other run-owned persisted tables/rows keyed by `run_id`
  - with parameterized queries and explicit threshold handling
- [ ] Step 5: keep shared/non-run-scoped surfaces out of scope, including
      enrichment reuse, embedding caches, bookmarks, and shared settings.

**Verification:**
- [ ] add store tests proving zero-match, threshold-match, and shared-surface
      preservation behavior
- [ ] add bq-store tests proving parameterized delete queries and local-mode
      mirror cleanup

**Exit Criteria:**
- one canonical store API owns archived-run deletion for both backends
- deletion boundary is explicit and testable

### Task 2: Add admin bulk-delete route with safe request/response contract

**Purpose:**
- expose one server-authoritative admin endpoint that translates age filter into
  deletion work and clear response payloads

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- existing bulk lifecycle route patterns in `app.py` remain source shape for
  processed/skipped/no-op summaries where useful

**Steps:**
- [ ] Step 1: add `POST /admin/runs/bulk/delete-archived` route.
- [ ] Step 2: validate request payload shape for `older_than_days` with support
      for fixed integer thresholds and `all` sentinel.
- [ ] Step 3: derive delete scope on server only; do not trust client-submitted
      run ids.
- [ ] Step 4: return stable JSON shape for:
  - deleted matches
  - no matches
  - invalid threshold
  - backend failure
- [ ] Step 5: log aggregate deletion audit details and keep success reporting
      tied to completed delete work only.

**Verification:**
- [ ] route tests cover `200 deleted`, `200 no_matches`, and `422 invalid threshold`
- [ ] route tests prove archived-only eligibility and no false success count

**Exit Criteria:**
- route is deterministic, admin-only, and aligned with spec payload contract

### Task 3: Add archived-view control, filter selector, and confirmation UX

**Purpose:**
- make destructive cleanup discoverable in archived view while keeping archive
  and delete clearly distinct

**Files:**
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete
- archived list view already exists at `/admin/runs?view=archived`

**Steps:**
- [ ] Step 1: render delete controls only for archived view, not active/all and
      not run detail.
- [ ] Step 2: add age-threshold selector with default `Older than 30 days` and
      fixed options from spec.
- [ ] Step 3: add helper copy: `Permanently deletes archived runs you no longer need.`
- [ ] Step 4: add confirmation UX that includes matched count, threshold label,
      and irreversible warning before POST.
- [ ] Step 5: show truthful success/no-match/error feedback after response and
      refresh archived list state.

**Verification:**
- [ ] template/route tests prove archived-only visibility and default filter
- [ ] UI tests prove confirmation/no-match copy hooks are present in rendered HTML/JS

**Exit Criteria:**
- operator can trigger deletion only from archived view with explicit warning
- no cache-clearing language appears in UI

### Task 4: Wire run-owned artifact cleanup and protect shared surfaces

**Purpose:**
- ensure bulk deletion removes all run-owned persisted artifacts without
  touching cross-run/shared data

**Files:**
- Inspect: `src/fitcv_cp/models.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 store helper exists
- known run-owned persisted fields remain:
  - `results_export_json`
  - `cv_generation_debug_json`
  - `stage_transition_artifacts_json`
  - `settings_used_json`

**Steps:**
- [ ] Step 1: inventory exact run-owned persistence surfaces and keep deletion
      helper responsible for all of them.
- [ ] Step 2: add deterministic local mirror removal for
      `artifacts/live_run_<run_id>/` when present.
- [ ] Step 3: confirm download endpoints and run-detail views naturally return
      not-found behavior after deletion rather than dangling artifact state.
- [ ] Step 4: keep shared caches and non-run operator tables untouched.

**Verification:**
- [ ] tests prove deleted runs no longer expose run-owned artifacts
- [ ] tests prove unrelated caches/records survive deletion pass

**Exit Criteria:**
- run-owned cleanup is complete enough that deleted runs leave no broken
  control-plane references

### Task 5: Focused docs, lineage refresh, and final verification

**Purpose:**
- align operator/API docs with new lifecycle step and close out plan safely

**Files:**
- Modify: `docs/usage.md`
- Modify: `docs/api.md`
- Modify: `docs/generated/planning_lineage.yaml`
- Verify: `docs/superpowers/specs/2026-06-25-11-41-delete-archived-runs-spec.md`
- Verify: `docs/superpowers/plans/2026-06-25-12-19-delete-archived-runs-plan.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: document archived-view delete action and archive-vs-delete
      distinction in `docs/usage.md`.
- [ ] Step 2: document new admin route and request/response shape in `docs/api.md`.
- [ ] Step 3: regenerate `docs/generated/planning_lineage.yaml`.
- [ ] Step 4: run focused tests for store/app lifecycle coverage.
- [ ] Step 5: run fast validator hook.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_store.py -k "archive or delete"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "archive or delete"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "archive or unarchive or delete_archived or bulk"`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs and generated lineage are current
- touched-surface tests and validator pass

## Verification

- `python -m pytest tests/test_fitcv_cp/test_store.py -k "archive or delete"`
- `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "archive or delete"`
- `python -m pytest tests/test_fitcv_cp/test_app.py -k "archive or unarchive or delete_archived or bulk"`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
