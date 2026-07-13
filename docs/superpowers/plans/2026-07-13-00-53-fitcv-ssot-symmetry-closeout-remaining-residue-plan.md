---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-closeout-remaining-residue
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-23-58-fitcv-ssot-symmetry-closeout-remaining-agreed-points-spec.md
targets:
  - docs/generated/planning_lineage.yaml
  - docs/superpowers/plans/2026-07-13-00-53-fitcv-ssot-symmetry-closeout-remaining-residue-plan.md
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/runtime_routing.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/run_lifecycle.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_pipeline.py
  - tests/test_runtime_routing.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Close remaining residue left after commit `09c262ed` so closeout claims become fully true for:

- SQLite-only active persistence surface
- shared lifecycle command semantics
- late-stage status-family ownership
- schema-owned settings stage/control-surface metadata
- routing snapshot symmetry across equivalent runtime surfaces

## Key Deliverables

### SQLite-only active persistence surface

`src/fitcv_cp/sqlite_store.py` no longer exposes active `project` / `dataset` compatibility arguments on live helper call surfaces, and storage tests prove no caller depends on them.

### Shared lifecycle and late-stage status-family ownership

`src/fitcv_cp/app.py`, `src/fitcv_cp/run_lifecycle.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv/pipeline.py`, and `src/fitcv/late_stage_contract.py` use one owner for cancel-target semantics and one owner for late-stage attempted/omission status families.

### Schema-owned settings and routing snapshots

`src/fitcv_cp/settings_schema.py` derives workflow-stage and control-surface defaults from schema entry metadata instead of parallel maps, app-facing settings consumers keep matching that schema-owned truth, and `src/fitcv/runtime_routing.py` owns reusable routing snapshot assembly consumed by app/startup/worker/runtime surfaces.

## Task/Wave Breakdown

### Task 1: Remove final SQLite compatibility args

**Purpose:**
- finish active persistence closeout at leaf store helpers

**Files:**
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `src/fitcv_cp/worker_job.py`

**Preconditions:**
- current baseline remains green at HEAD `09c262ed`

**Steps:**
- [ ] Step 1: remove dead `project` / `dataset` params and back-compat comment from live sqlite JSON-field helpers
- [ ] Step 2: confirm no active caller passes removed args; patch tests only where signatures changed
- [ ] Step 3: grep for remaining active persistence residue in closeout-owned runtime paths

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "\bproject\b|\bdataset\b|bigquery_dataset|_persistence_scope_kwargs" src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/reconciler.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py`

**Exit Criteria:**
- sqlite active helper signatures are SQLite-shaped only

### Task 2: Collapse remaining cancel-path split

**Purpose:**
- make single-run and bulk-run cancel paths derive target-status meaning from one lifecycle helper

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/run_lifecycle.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/run_lifecycle.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: extract smallest shared cancel-request decision helper needed for both single and bulk stop flows
- [ ] Step 2: rewire `/admin/runs/{run_id}/stop` to use same target-status semantics already used by bulk cancel
- [ ] Step 3: keep event wording and returned API statuses stable unless tests prove current behavior is contradictory

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "awaiting_continue or cancelled_from_queue or stop_requested" -q`
- [ ] `rg -n "cancel_request_target_status\(|RunStatus\.CANCELLING.value|RunStatus\.CANCELLED.value" src/fitcv_cp/app.py src/fitcv_cp/run_lifecycle.py`

**Exit Criteria:**
- equivalent cancel actions no longer compute target status in parallel branches

### Task 3: Finish late-stage status-family extraction

**Purpose:**
- move repeated late-stage attempted/omission status families under `late_stage_contract.py`

**Files:**
- Modify: `src/fitcv/late_stage_contract.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: add smallest shared frozensets/helpers for CV-generation attempted statuses and CV-debug analysis omission statuses
- [ ] Step 2: replace local literal families in pipeline and worker with imported shared owners
- [ ] Step 3: leave genuinely status-specific branches local; only shared family membership moves

**Verification:**
- [ ] `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "_CV_GENERATION_ATTEMPTED_STATUSES|_CV_DEBUG_ANALYSIS_OMISSION_STATUSES" src/fitcv/pipeline.py src/fitcv_cp/worker_job.py src/fitcv/late_stage_contract.py`

**Exit Criteria:**
- late-stage status families have one owner and consumers import them

### Task 4: Finish schema-owned stage and control-surface metadata

**Purpose:**
- remove remaining parallel ownership maps from settings defaults

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `src/fitcv_cp/app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: add explicit per-entry metadata for workflow stage and control surface where current defaults come from `_KEY_TO_STAGE_ID` and `_GROUP_TO_CONTROL_SURFACE`
- [ ] Step 2: switch `_default_stage_id` and `_default_control_surface` to schema-row metadata fallback instead of manual parallel registries
- [ ] Step 3: keep derived registries like `RANKING_GROUPS` / `SETTINGS_SECTIONS` only if they remain pure projections from schema rows

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- [ ] `rg -n "_KEY_TO_STAGE_ID|_GROUP_TO_CONTROL_SURFACE" src/fitcv_cp/settings_schema.py`

**Exit Criteria:**
- stage and control-surface ownership derive from schema entries, not standalone maps

### Task 5: Unify routing snapshot assembly

**Purpose:**
- stop rebuilding equivalent provider/model/base_url/wire_api/api-key-availability truth in app-local code

**Files:**
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_runtime_routing.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 4 complete

**Steps:**
- [ ] Step 1: add one reusable routing snapshot/helper in `runtime_routing.py` for resolved provider/model/base_url/wire_api plus API-key-available boolean
- [ ] Step 2: make synonym-triage runtime inspection and diagnostics consume shared snapshot truth, only layering stage-local fields like `sleep_secs` / `concurrency` at boundary
- [ ] Step 3: patch startup, worker, and runtime call sites only where they duplicate same resolved snapshot fields

**Verification:**
- [ ] `python -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "provider|model|base_url|wire_api|api_key" src/fitcv/runtime_routing.py src/fitcv_cp/app.py src/fitcv_cp/backend_runtime.py src/fitcv_cp/main.py src/fitcv_cp/worker_job.py`

**Exit Criteria:**
- equivalent runtime surfaces derive routing snapshot truth from one helper

## Verification

- `python -m pytest tests/test_pipeline.py tests/test_runtime_routing.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
