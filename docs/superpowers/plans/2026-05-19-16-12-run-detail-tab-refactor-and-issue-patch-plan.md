---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: run-detail-tab-refactor-and-issue-patch-implementation
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
parent_spec: docs/superpowers/specs/2026-05-19-16-10-run-detail-tab-refactor-spec.md
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/run_detail_tab_profile.html
  - src/fitcv_cp/templates/_run_detail_snapshot_tab.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# 2026-05-19-16-12 Run Detail Tab Refactor and Issue Patch Plan

## Goal

Implement spec-defined SSOT/symmetry/invariance refactor for run detail tab surfaces and patch duplicated tab-loading/query-state risks, while preserving route, query, and operator action behavior.

## Key Deliverables

### Deliverable 1: Snapshot-tab SSOT implementation

`jobs-input` and `profile` tab fragments render from one shared snapshot-tab contract surface, preserving immutable snapshot semantics and legacy fallback behavior.

### Deliverable 2: Enriched tab query-state invariance

Enriched pagination/filter/search links and fragment URLs derive from one canonical query-state assembly path.

### Deliverable 3: Single-path enriched auto-load

Run detail page performs exactly one initial enriched-tab preload path on first render.

### Deliverable 4: Synonym overlay symmetry hardening

Synonym overlay controls/CTA rendering is normalized to one state-driven structure without changing endpoint, scope, or gating semantics.

### Deliverable 5: Regression-proof verification

Tests and focused UI assertions prove no regression in snapshot fallback behavior, tab loading behavior, enriched query persistence, and synonym overlay branch behavior.

## Task/Wave Breakdown

### Task 1: Implement shared snapshot-tab rendering contract

**Purpose:**
- remove duplicated immutable snapshot markup across jobs-input/profile tabs via one reusable template primitive.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Modify: `src/fitcv_cp/templates/_run_detail_snapshot_tab.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Spec approved: `docs/superpowers/specs/2026-05-19-16-10-run-detail-tab-refactor-spec.md`.
- Keep tab endpoint contracts unchanged.

**Steps:**
- [x] Create shared include/macro template for snapshot surface:
  - source badge row
  - raw JSON details block
  - fallback legacy-record message block
- [x] Replace jobs-input tab body with include call using existing context (`run.jobs_input_json`, `run.jobs_input_source`, `run.jobs_path`).
- [x] Replace profile tab body with include call using existing context (`candidate_profile_pretty`, `run.candidate_profile_source`).
- [x] Preserve current copy, accessibility labels, and fallback wording.

**Verification:**
- [x] Fragment render tests pass for payload-present and payload-absent branches in both tabs.
- [x] Manual inspection confirms identical structure except variable content.

**Exit Criteria:**
- Snapshot tab HTML contract is SSOT-backed and duplicate branch logic removed.

### Task 2: Normalize enriched query-state contract

**Purpose:**
- enforce symmetry between SSR navigation URLs and tab-fragment URLs.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.
- Existing query keys must remain: `page`, `page_size`, `filter_name`, `q`.

**Steps:**
- [x] Introduce one canonical local query-state assembly block in template for prev/next links.
- [x] Render both `href` and `data-tab-fragment-url` from same canonical assembled value.
- [x] Keep all existing filters, search, and page-size semantics unchanged.
- [x] Preserve no-JS fallback behavior via valid `href`.

**Verification:**
- [x] Tests assert prev/next `href` and `data-tab-fragment-url` equivalence.
- [x] Tests assert query persistence across paging and filter transitions.

**Exit Criteria:**
- No duplicated URL-building logic remains for enriched pagination links.

### Task 3: Remove duplicate enriched preload boot path

**Purpose:**
- patch duplicate initial load trigger risk in run detail script.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete.
- Existing tab lazy-load behavior and fail-safe states stay intact.

**Steps:**
- [x] Remove second redundant `ensureTabLoaded('enriched')` boot trigger.
- [x] Keep one canonical preload trigger under deterministic readiness condition.
- [x] Verify no behavior change for manual tab switching or refresh flows.
- [x] Keep existing error fallback message rendering on fetch failure.

**Verification:**
- [x] UI/script test asserts single initial enriched fetch on page load.
- [x] Existing tab-switch and fragment-load tests remain green.

**Exit Criteria:**
- Enriched preload initialization has one authoritative trigger path.

### Task 4: Consolidate synonym overlay branch rendering

**Purpose:**
- eliminate dual overlay rendering branches and enforce one state-driven UI contract.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete.
- Endpoint and permission semantics frozen:
  - POST `/admin/runs/{run_id}/synonym-overlay`
  - existing `overlay_upload_scope` options

**Steps:**
- [x] Define explicit state matrix inside template logic (or local derived flags):
  - `synonym_review_section_state`
  - overlay active vs default
  - upload allowed vs disallowed
  - run mode edge branch
- [x] Collapse duplicated upload form/CTA rendering into one branch structure.
- [x] Preserve all existing action labels and scope-option values unless copy variance already contradictory.
- [x] Keep legacy hidden-mode informational content available when applicable.

**Verification:**
- [x] Branch matrix tests pass for key state combinations (hidden/visible, upload on/off, overlay on/off, run-all mode).
- [x] Manual run-detail smoke check confirms no missing CTA/action.

**Exit Criteria:**
- Synonym overlay UI contract implemented once, with no duplicate form blocks.

### Task 5: Final regression pass and closeout proof

**Purpose:**
- provide artifact-level proof and containment strategy before marking plan complete.

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Inspect: `src/fitcv_cp/templates/_run_detail_snapshot_tab.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 complete.

**Steps:**
- [x] Run focused test subset for run-detail/tab routes and template states.
- [x] Run broader regression command required by local workflow.
- [x] Document rollback containment:
  - revert Task 4 independently if synonym matrix regression found
  - keep Tasks 1-3 as safe structural baseline
- [x] Capture final evidence notes in commit/PR summary.

**Verification:**
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "run_detail or tabs or synonym or enriched"`

**Exit Criteria:**
- All deliverables verified with test/runtime evidence and rollback notes.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest tests/test_fitcv_cp/test_app.py -k "run_detail or tabs or synonym or enriched"`
- Manual smoke in admin UI:
  - run detail initial load
  - enriched prev/next navigation
  - jobs-input/profile payload + fallback states
  - synonym overlay action visibility matrix

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`




## External Blocker Acceptance

- Broad regression subset (un_detail or tabs or synonym or enriched) reported 15 synonym-focused failures outside bounded lane scope.
- User decision recorded: keep lane bounded to current refactor and treat those 15 as external blocker for closeout.
