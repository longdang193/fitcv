---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: run-detail-download-filtered-rerun-jsonl-manifest
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
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

Add run-detail export path to download filtered enriched jobs as rerun-ready `JSONL` plus manifest, using Pipeline Outcome filters (including multi-select outcomes), with deterministic server-side snapshot semantics.

## Key Deliverables

### Deliverable 1: Filtered export endpoint + UI action

Run detail Enriched Jobs tab exposes `Download filtered` action that uses current filter state and returns bundle with:
- `jobs.filtered.jsonl`
- `jobs.filtered.manifest.json`

### Deliverable 2: Rerun-ready JSONL schema contract

Each JSONL row matches new-run ingest expectations (`parse_jobs_file` consumes JSON array objects today) via explicit compatibility decision:
- export rows carry canonical raw-job payload sufficient for future run input
- import bridge accepts exported JSONL directly in trigger flow with no manual transform

### Deliverable 3: Deterministic manifest + auditability

Manifest records exact filter query, source run, row count, checksum, schema versions, and ordering so exported subset is reproducible and traceable.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current enriched-tab filter semantics, pipeline outcome labels, and trigger-run ingest constraints before interface design

**Steps:**
- [x] inspect enriched tab UI filter controls in `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- [x] inspect enriched-tab server context builder in `src/fitcv_cp/app.py::_build_enriched_tab_context`
- [x] inspect pipeline outcome surface mapping in `src/fitcv_cp/app.py::PIPELINE_OUTCOME_META` and `_pipeline_outcome_surface`
- [x] inspect trigger ingest constraints in `src/fitcv/ingest.py::parse_jobs_file` and `/admin/upload-trigger`
- [x] refresh GitNexus index via `npx gitnexus analyze` and verify status up-to-date

**Verification:**
- [x] current table filters only support pass/reject/unknown + text query; no pipeline outcome filter or filtered export endpoint exists
- [x] trigger ingest currently accepts JSON array files (path/upload/paste), not JSONL

**Exit Criteria:**
- no key contract decision depends on unknown source behavior

### Wave 2: Decision closure

**Purpose:**
- close schema, endpoint, and compatibility decisions for bounded Phase-1 feature

**Steps:**
- [ ] define canonical filter query model including pipeline outcome multi-select
- [ ] define export endpoint response type and file naming
- [ ] define JSONL row schema + manifest schema versioning
- [ ] define rerun compatibility bridge (JSONL import path)
- [ ] define size limits and fallback behavior

**Verification:**
- [ ] decisions eliminate manual post-export conversion before rerun

**Exit Criteria:**
- implementation plan can be written without unresolved API/schema questions

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof expectations for correctness, determinism, and compatibility

**Steps:**
- [ ] specify endpoint tests for filter correctness and row counts
- [ ] specify checksum/manifest consistency tests
- [ ] specify rerun ingestion test from downloaded JSONL

**Verification:**
- [ ] validation plan proves exported data can start new run directly

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Add explicit pipeline outcome filter to enriched tab query model

- context: current filter model (`all|passed|rejected|unknown` + query text) cannot express user target cohort (`Passed filter, not shortlisted` + `Scored, not final top-N`)
- choice:
  - extend enriched tab controls with `pipeline_outcome_in` multi-select using canonical status keys:
    - `not_shortlisted`
    - `scored_not_ranked`
    - plus existing keys from `PIPELINE_OUTCOME_META`
  - filter applied server-side before pagination
- alternatives considered:
  - infer outcomes from label text search
  - export all rows then client-side filter
- impact:
  - exact subset reproducibility
  - eliminates label-string coupling and locale risk

### Decision: New dedicated export endpoint returns ZIP bundle

- context: two-file output (`jsonl` + `manifest`) requires single-click download
- choice:
  - add endpoint `GET /admin/runs/{run_id}/enriched/export-filtered.zip`
  - endpoint accepts same query params as enriched tab:
    - `filter_name`
    - `q`
    - repeated `pipeline_outcome`
  - endpoint ignores pagination params intentionally; exports full filtered set
- alternatives considered:
  - two separate endpoints for jsonl and manifest
  - embed manifest as first JSONL row
- impact:
  - cleaner operator workflow
  - safer contract boundaries

### Decision: JSONL row schema is rerun-input canonical object, not UI projection

- context: rerun must not depend on run-detail projection fields that are partial
- choice:
  - each line contains `rerun_input.v1` object with stable fields:
    - `schema_version`
    - `job_url` (or canonical ID field)
    - `source_run_id`
    - `pipeline_outcome`
    - `filter_status`
    - `shortlist_status`
    - `scoring_status`
    - `final_top_n_status`
    - `raw_job` (full raw job object compatible with ingest)
  - `raw_job` remains source-of-truth for next-run parse path
- alternatives considered:
  - minimal row with only `job_url`
  - full enriched projection without raw job object
- impact:
  - direct rerun compatibility
  - stable future ingestion evolution via schema version

### Decision: Import bridge supports JSONL directly in upload trigger path

- context: current upload trigger enforces JSON array file; exported JSONL would otherwise need manual conversion
- choice:
  - extend `/admin/upload-trigger` jobs upload parser:
    - accept `.jsonl` input mode/file
    - parse lines to list of objects
    - map `raw_job` entries into canonical jobs array for pipeline ingest
  - preserve existing JSON array behavior unchanged
- alternatives considered:
  - export JSON array instead of JSONL
  - require external conversion utility
- impact:
  - “download then trigger new run” is one continuous operator flow
  - no regressions to current uploads

### Decision: Deterministic export order + checksum

- context: reproducibility needed for audit and rerun consistency
- choice:
  - sort export rows by `job_url ASC` (fallback stable key by title+url hash when missing)
  - compute `sha256` over exact `jobs.filtered.jsonl` bytes
  - store checksum + row_count in manifest
- alternatives considered:
  - preserve in-memory current ordering
- impact:
  - deterministic bundle across retries
  - easier debugging and diffing

## Invariants

- Invariant 1: Export uses server-side filtered dataset snapshot, never current page slice.
- Invariant 2: Manifest `row_count` equals JSONL line count exactly.
- Invariant 3: Manifest checksum validates JSONL bytes exactly.
- Invariant 4: Every exported row has `schema_version` and rerun-usable `raw_job` payload.
- Invariant 5: Existing enriched tab behavior (without new outcome params) remains backward compatible.
- Invariant 6: Existing `/admin/upload-trigger` JSON-array modes remain unchanged.

## Acceptance Criteria

1. Enriched tab supports selecting multiple Pipeline Outcomes and applying filter server-side.
2. `Download filtered` exports only rows matching active filters (including pipeline outcome set).
3. Export bundle includes exactly two files: `jobs.filtered.jsonl` and `jobs.filtered.manifest.json`.
4. JSONL line count equals manifest `row_count` and backend filtered total.
5. Manifest captures: `schema_version`, `generated_at`, `export_id`, `source_run_id`, `filters`, `row_count`, `ordering`, `checksum_sha256`.
6. Uploading exported JSONL through trigger flow starts a new run without manual transformation.
7. Existing JSON array upload/paste/path trigger modes continue passing existing tests.

## Non-Goals

- Saved filter presets.
- One-click “create rerun now” action from run-detail page.
- CSV export.
- Cross-run cohort union export.
- Policy changes to pipeline outcome taxonomy itself.

## Risks and Mitigations

- Risk: JSONL schema drift from ingest contract.
  - Mitigation: include explicit schema version + import bridge test matrix.
- Risk: export performance/memory issues on large runs.
  - Mitigation: stream JSONL generation and zipped response; enforce max-row cap with clear error.
- Risk: mismatch between UI labels and backend status keys.
  - Mitigation: filter uses canonical status keys only; UI labels remain presentation layer.
- Risk: hidden partial data if raw job not recoverable for some rows.
  - Mitigation: fail closed for rows missing required rerun payload and surface count/reason in manifest warnings.

## Validation Plan

- proof target: pipeline outcome filter correctness
  - method: API test for enriched fragment and export endpoint with seeded outcomes (`not_shortlisted`, `scored_not_ranked`, rejected)
  - evidence: assertions that only expected job URLs exist in JSONL

- proof target: deterministic manifest integrity
  - method: export twice with same run/filter snapshot; compare checksum and ordered row URLs
  - evidence: equal checksum and equal line-order sequence

- proof target: rerun compatibility from exported JSONL
  - method: integration-style test path through `/admin/upload-trigger` with exported `jobs.filtered.jsonl`
  - evidence: trigger returns `201` and created run has non-empty `jobs_input_json` parsed from JSONL lines

- proof target: backward compatibility for existing trigger modes
  - method: run existing tests covering path/upload/paste JSON array modes
  - evidence: unchanged passing tests in `tests/test_fitcv_cp/test_app.py`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Triage Block

Layer: change
Feature type: ADD
Summary: Add Pipeline Outcome-aware filtered export as rerun-ready JSONL + manifest from Enriched Jobs tab.
Reasoning: bounded operator-control-plane change; no intent/workstream governance shift; requires contract between run-detail filtering and trigger ingest.
Invariants:
- export full filtered server snapshot
- deterministic ordering + checksum
- direct rerun usability without manual transforms
Dependencies:
- `src/fitcv_cp/app.py::_build_enriched_tab_context`
- pipeline outcome status mapping (`PIPELINE_OUTCOME_META`, `_pipeline_outcome_surface`)
- trigger ingestion entrypoint (`/admin/upload-trigger`)
- ingest parser constraints (`src/fitcv/ingest.py::parse_jobs_file`)
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-28-22-40-download-filtered-rerun-ready-jsonl-spec.md
  - docs/api.md
- generated:
  - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
