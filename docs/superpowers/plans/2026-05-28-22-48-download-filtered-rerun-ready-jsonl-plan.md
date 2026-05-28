---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: run-detail-download-filtered-rerun-jsonl-manifest-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-28-22-40-download-filtered-rerun-ready-jsonl-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_app.py
  - docs/api.md
related_features: []
related_stages: []
---

## Goal

Implement bounded Phase-1 operator flow for downloading server-filtered enriched jobs as rerun-ready `JSONL + manifest` bundle, with direct compatibility for triggering a new run from exported data.

## Key Deliverables

### Deliverable 1: Pipeline outcome-aware filter + download action in Enriched tab

Enriched tab supports multi-select `pipeline_outcome` filtering and exposes `Download filtered` action wired to a new export endpoint that uses full server-side filtered set (not current page).

### Deliverable 2: Deterministic filtered export bundle contract

Backend export endpoint returns `export-filtered.zip` containing `jobs.filtered.jsonl` and `jobs.filtered.manifest.json` with schema versions, filter snapshot, deterministic order, row count, and SHA-256 checksum.

### Deliverable 3: Direct rerun ingestion of exported JSONL

Trigger upload path accepts exported JSONL and maps each row’s `raw_job` payload to canonical jobs array so operator can start a new run without manual conversion.

### Deliverable 4: Regression-safe tests and API docs

Tests prove filter correctness, manifest integrity, rerun compatibility, and non-regression for existing JSON-array input modes; API docs updated with endpoint and payload contracts.

## Task/Wave Breakdown

### Task 1: Extend enriched filter model and tab UX

**Purpose:**
- add canonical pipeline outcome filter controls and preserve existing filter semantics

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Spec approved: `docs/superpowers/specs/2026-05-28-22-40-download-filtered-rerun-ready-jsonl-spec.md`
- Existing outcome taxonomy remains source of truth in `PIPELINE_OUTCOME_META`

**Steps:**
- [x] Add request/query parsing for repeated `pipeline_outcome` values in enriched tab route(s).
- [x] Extend `_build_enriched_tab_context` to apply outcome filters before pagination using canonical status keys.
- [x] Add multi-select UI control for pipeline outcomes and persist selection across Apply/pagination.
- [x] Add `Download filtered` link/button that forwards active filter query params to export endpoint.

**Verification:**
- [x] Run targeted tests for enriched-tab filter state rendering and query behavior.
- [x] Manual inspection in run detail UI: selected outcomes remain stable across Apply/Next/Prev.

**Exit Criteria:**
- Enriched tab can express and display filtered cohort `not_shortlisted + scored_not_ranked` with stable UI state.

### Task 2: Implement filtered export ZIP endpoint

**Purpose:**
- produce deterministic rerun-ready JSONL + manifest from server-side filtered snapshot

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- Filtered row selection logic centralized/reusable (avoid duplicate filtering paths)

**Steps:**
- [x] Add `GET /admin/runs/{run_id}/enriched/export-filtered.zip` endpoint.
- [x] Reuse canonical filter path (`filter_name`, `q`, repeated `pipeline_outcome`) and ignore pagination for export.
- [x] Build JSONL rows with `rerun_input.v1` schema and include `raw_job` payload.
- [x] Sort rows deterministically (`job_url ASC`, stable fallback key if missing).
- [x] Generate manifest with metadata fields: schema version, generated timestamp, export id, source run id, filters, row count, ordering, checksum, warnings.
- [x] Package JSONL + manifest into zip response with deterministic filenames.

**Verification:**
- [x] Add/execute tests validating zip entries, row count parity, and checksum correctness.
- [x] Add test asserting exported rows all satisfy active filter criteria.

**Exit Criteria:**
- Export endpoint returns correct deterministic bundle for any valid enriched filter query.

### Task 3: Add JSONL rerun import bridge in trigger upload flow

**Purpose:**
- ensure exported JSONL can be used directly as new run input

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv/ingest.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete (export schema finalized)
- Existing JSON-array behaviors must remain unchanged

**Steps:**
- [x] Extend upload parser branch to detect `.jsonl` files (or line-delimited JSON content-type).
- [x] Parse JSONL safely line-by-line; validate row shape and extract `raw_job` as canonical ingest object.
- [x] Convert parsed rows into merged jobs JSON array snapshot used by existing trigger path.
- [x] Add explicit validation errors for malformed JSONL, missing `raw_job`, and empty valid rows.
- [x] Preserve existing path/upload/paste JSON-array handling unchanged.

**Verification:**
- [x] Add test that uploads exported JSONL and receives `201` with created run.
- [x] Add negative tests for malformed JSONL and missing required row fields.
- [x] Re-run existing upload mode tests for regression guard.

**Exit Criteria:**
- Operator can download filtered bundle and directly re-upload JSONL to trigger new run without manual conversion.

### Task 4: Documentation, compatibility checks, and closeout verification

**Purpose:**
- align API docs and confirm complete behavior contract

**Files:**
- Modify: `docs/api.md`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Document new endpoint, query params, zip contents, JSONL row schema, manifest schema, and rerun import expectations in `docs/api.md`.
- [x] Run targeted test selection for enriched filters/export/upload-trigger.
- [x] Run broader app test subset touching run detail and upload trigger flows.
- [x] Capture final verification notes and unresolved follow-ups (if any) in plan execution output.

**Verification:**
- [x] Docs and tests reflect same field names and schema versions.
- [x] No regressions in existing trigger modes.

**Exit Criteria:**
- Implementation artifacts, tests, and docs are consistent and handoff-ready.

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k "enriched or export or upload_trigger"`
- `pytest tests/test_fitcv_cp/test_app.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

