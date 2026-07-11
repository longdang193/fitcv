---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-pipeline-identity-and-filter-truth
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-results-ledger-contract
parent_spec: docs/superpowers/specs/2026-06-26-16-40-fitcv-pipeline-identity-and-filter-truth-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/store.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_storage_backend_parity.py
related_features:
  - admin_control_plane_core
  - inspection_debugging
related_stages:
  - rule_filter
  - cv_generation
---

# FitCV Pipeline Identity And Filter Truth Plan

## Goal

Implement stable per-job pipeline identity, full rule-filter truth persistence across storage backends, and truthful control-plane degradation so enriched-tab `Filter` and `Pipeline Outcome` stop going blank or silently misreporting state when URLs drift.

## Key Deliverables

### Canonical identity propagation through pipeline and export

Pipeline stages, results export, and control-plane joins use one shared identity contract (`raw_job_fingerprint` first, then stable URL fallbacks) instead of raw URL-only equality.

### Backend-parity rule-filter persistence

Both BigQuery and sqlite persist and expose full run-scoped rule-filter rows with aligned semantic shape, including identity fields needed for downstream joins.

### Truthful control-plane rendering and diagnostics

Enriched-tab filter/outcome surfaces render known truth when available, explicit unknown/missing-truth when not, and no longer treat sample artifacts or guessed pass states as canonical.

## Task/Wave Breakdown

### Task 1: Lock failing regressions

**Purpose:**
- capture current bug classes in tests before changing runtime logic

**Files:**
- Inspect: `docs/superpowers/specs/2026-06-26-16-40-fitcv-pipeline-identity-and-filter-truth-spec.md`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_storage_backend_parity.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`

**Preconditions:**
- spec decisions approved as implementation source of truth
- existing URL-drift and sqlite-fallback behavior understood from source/live evidence

**Steps:**
- [x] Step 1: add pipeline/export regression covering same logical job with enriched/source URL differing from downstream canonical URL
- [x] Step 2: add control-plane enriched-tab regressions covering missing persisted filter rows and fingerprint-based truth joins under URL drift
- [x] Step 3: add backend-parity regression asserting sqlite and BigQuery expose semantically equivalent rule-filter rows for same fixture

**Verification:**
- [x] targeted pytest for new failing cases in `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_app.py`, and `tests/test_fitcv_cp/test_storage_backend_parity.py`

**Exit Criteria:**
- regressions fail for current bug classes and clearly describe intended truth behavior

### Task 2: Add shared identity and URL-key helpers in pipeline core

**Purpose:**
- replace ad-hoc URL-only joins with one reusable identity/key contract in pipeline-side code

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 1 complete
- source fields carrying `raw_job_fingerprint` and source/display URLs identified

**Steps:**
- [x] Step 1: add minimal shared helpers for normalized secondary URL keys and canonical identity extraction from pipeline rows
- [x] Step 2: thread canonical identity through pipeline maps and results-export status derivation so matching prefers `raw_job_fingerprint`, then stable source/display URL fallbacks
- [x] Step 3: preserve display `job_url` behavior while exporting enough identity metadata for downstream control-plane joins

**Verification:**
- [x] targeted pytest for pipeline export/status tests, including new URL-drift regression

**Exit Criteria:**
- pipeline export no longer falls to `unknown_pipeline_state` when downstream truth exists under same logical job identity

### Task 3: Persist full rule-filter truth in sqlite and align row contract

**Purpose:**
- remove backend-mode truth split by making sqlite persist same run-scoped filter truth class as BigQuery

**Files:**
- Inspect: `src/fitcv/rule_filter.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/store.py`
- Modify: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/store.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_storage_backend_parity.py`

**Preconditions:**
- Task 2 complete
- canonical persisted row shape finalized from spec

**Steps:**
- [x] Step 1: extend rule-filter persistence path to write full run-scoped rows in sqlite mode instead of returning early
- [x] Step 2: align BigQuery and sqlite read/write contracts around shared fields: run id, identity fields, pass/reject flags, reasons, marks, timestamp
- [x] Step 3: keep backward compatibility for legacy reads where new fields may be absent, with deterministic fallback ordering

**Verification:**
- [x] targeted pytest for `test_bq_store.py` and backend-parity tests proving aligned semantic row output

**Exit Criteria:**
- `list_filter_results_for_run()` returns full per-job truth in both storage modes for runs that reached rule filter

### Task 4: Make control-plane joins and degradation truthful

**Purpose:**
- make enriched-tab consume canonical truth sources in correct order and show explicit unknown state when truth is missing

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete
- Task 3 complete

**Steps:**
- [x] Step 1: update enriched-tab join logic to prefer canonical identity fields over raw URL-only matching
- [x] Step 2: demote stage-artifact samples to diagnostics-only fallback and remove synthetic pass inference for missing canonical truth
- [x] Step 3: add explicit filter/outcome unknown-state rendering data via existing unknown-state surfaces and canonical lookup keys for missing-truth rows

**Verification:**
- [x] targeted pytest for enriched-tab context/render tests covering known truth, partial artifacts, and explicit unknown-state cases

**Exit Criteria:**
- control-plane surfaces complete truth when persisted rows exist and explicit unknown state when canonical truth is absent

### Task 5: Final verification and bounded live-run proof

**Purpose:**
- prove regression fixed at artifact level and catch backend/UI drift before closeout

**Files:**
- Inspect: `docs/superpowers/specs/2026-06-26-16-40-fitcv-pipeline-identity-and-filter-truth-spec.md`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_storage_backend_parity.py`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: run targeted test slices for pipeline export, app enriched-tab behavior, store contract, and backend parity
- [x] Step 2: run broader regression subset covering existing enriched-tab and results-export cases touched by new identity logic
- [x] Step 3: attempt bounded runtime-style inspection; local persisted run DB contained no runs, so live-style proof was unavailable and is recorded in audit evidence rather than fabricated

**Verification:**
- [x] targeted pytest:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_storage_backend_parity.py`
- [x] focused scripted check attempted against local sqlite run store; no persisted runs were available for runtime-style replay in this workspace

**Exit Criteria:**
- tests pass for bounded touched surfaces and live/run-level evidence no longer shows silent blanks for rows with canonical truth

## Verification

- run targeted pytest for touched suites:
  - `pytest tests/test_pipeline.py -k "identity or pipeline_status or export"`
  - `pytest tests/test_fitcv_cp/test_app.py -k "enriched or pipeline outcome or filter"`
  - `pytest tests/test_fitcv_cp/test_bq_store.py -k "filter_results"`
  - `pytest tests/test_fitcv_cp/test_storage_backend_parity.py`
- run exact failing regression tests added in this plan
- if runtime available, inspect one representative run context or container-backed route payload to confirm row truth and unknown-state diagnostics

## Completion Criteria

1. All Key Deliverables are satisfied.
2. All plan tasks are terminal.
3. Every task is `completed` or `dropped`.

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
