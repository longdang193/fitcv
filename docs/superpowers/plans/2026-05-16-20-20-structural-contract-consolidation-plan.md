---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: structural-contract-consolidation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-16-20-10-structural-contract-consolidation-spec.md
targets:
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_fitcv_cp/test_synonym_proposals.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
related_features:
  - run_lifecycle_controls
  - settings_system
  - admin_control_plane_core
related_stages:
  - enrich
  - rule_filter
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement structural contract consolidation defined in parent spec: remove duplicated proposal lifecycle builders, centralize stage artifact schema identity and synonym-management default projection, and unify status/stage projection semantics while preserving backward-compatible read behavior.

## Key Deliverables

### Deliverable 1: Single-owner proposal lifecycle contracts

`transition_synonym_proposal_status` and synonym proposal trace payload construction are owned by one canonical module and consumed by worker/app call paths without duplicate builders.

### Deliverable 2: Single-owner lifecycle schema/version contract registry

Stage transition artifact schema/version constants are centralized and consumed by pipeline, worker payload persistence, and app artifact projection.

### Deliverable 3: Single-owner synonym-management default resolver

A shared resolver computes effective synonym-management defaults, and app trigger envelope, app snapshot loader, and worker automation paths consume it.

### Deliverable 4: Canonical status/stage projection for UI/API

App projection layer provides canonical status groups/labels derived from model contracts, and templates consume projection outputs instead of scattered literal status tuples.

### Deliverable 5: Structural equivalence and regression coverage

Tests prove transition equivalence, schema identity invariance, default projection symmetry, and run-detail status rendering consistency.

## Task/Wave Breakdown

### Task 1: Consolidate proposal lifecycle contract ownership

**Purpose:**
- remove duplicate proposal lifecycle implementations and enforce one canonical owner

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_synonym_proposals.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- parent spec approved for canonical ownership in `fitcv_cp.synonym_proposals`

**Steps:**
- [ ] Step 1: keep canonical transition matrix and trace builder in `src/fitcv_cp/synonym_proposals.py` and expose explicit public helpers.
- [ ] Step 2: remove duplicate `_build_synonym_proposals_trace_payload` implementation from `src/fitcv_cp/worker_job.py`; switch worker call sites to canonical import.
- [ ] Step 3: add/adjust tests that compare representative trace payloads and transitions to pre-change expected semantics.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_synonym_proposals.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- exactly one runtime implementation of transition matrix and proposal trace builder remains

### Task 2: Centralize lifecycle schema/version identity constants

**Purpose:**
- enforce invariance of schema/version identity across pipeline, worker, and app surfaces

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/contracts.py` (new or existing contract surface)
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- compatibility policy fixed: read legacy tags, write canonical tags

**Steps:**
- [ ] Step 1: introduce canonical constants for targeted artifact/schema/version identities.
- [ ] Step 2: replace local literals in pipeline/worker/app targeted families with shared constants.
- [ ] Step 3: add compatibility reader assertions for legacy persisted payload tags where applicable.

**Verification:**
- [ ] `pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- targeted schema/version families are sourced from one contract registry

### Task 3: Consolidate synonym-management default projection

**Purpose:**
- restore symmetry in policy projection across trigger, load, and automation paths

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/synonym_proposals.py` (only if shared helper location selected there)
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: implement one shared resolver for effective synonym-management defaults.
- [ ] Step 2: replace duplicated `setdefault` and fallback blocks in app and worker with resolver usage.
- [ ] Step 3: add regression tests proving same input settings snapshot yields same flags in all three call paths.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- no duplicated default blocks remain for targeted synonym-management keys

### Task 4: Canonicalize status/stage projection for templates

**Purpose:**
- remove ad-hoc status grouping literals and align UI projection with model contracts

**Files:**
- Inspect: `src/fitcv_cp/models.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: define canonical status grouping/label projection in app layer derived from `RunStatus` contract.
- [ ] Step 2: update templates to consume projected booleans/labels instead of inline literal status tuples where targeted.
- [ ] Step 3: add regression tests for all run statuses and archived-state rendering branches.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- targeted templates no longer encode duplicated status grouping logic

### Task 5: Structural guardrails and final regression pass

**Purpose:**
- prevent recurrence and prove consolidated behavior end-to-end

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_synonym_proposals.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: add structural guardrail checks for duplicate forbidden builders and targeted literal schema tags.
- [ ] Step 2: run targeted suite for proposal lifecycle, worker/app lifecycle payloads, pipeline artifact identity, and run-detail rendering.
- [ ] Step 3: record post-change verification evidence and residual risk note if legacy-read adapters remain.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_synonym_proposals.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_pipeline.py -q`

**Exit Criteria:**
- all targeted tests pass and structural duplication guardrails are enforced

## Verification

- `pytest tests/test_fitcv_cp/test_synonym_proposals.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_pipeline.py -q`
- `.\.venv\Scripts\python.exe scripts/hooks/run_validator.py --fast`
- `rg -n "def _build_synonym_proposals_trace_payload" src/fitcv_cp`
- `rg -n "stage_transition_artifacts_(run|stage)_v1|stage_transition_artifacts_v6" src/fitcv src/fitcv_cp`

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
