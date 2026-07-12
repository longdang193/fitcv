---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-5-control-plane-monolith-reduction-and-storage-normalization
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-15-41-fitcv-ssot-symmetry-phase-5-control-plane-monolith-reduction-and-storage-normalization-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/run_artifact_mirror.py
  - docs/architecture.md
  - docs/api.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Implement Phase 5 from
`docs/superpowers/specs/2026-07-12-15-41-fitcv-ssot-symmetry-phase-5-control-plane-monolith-reduction-and-storage-normalization-spec.md`:

- extract bounded control-plane helper families from `src/fitcv_cp/app.py` into `src/fitcv_cp/app_run_support.py`
- extract bounded worker helper families from `src/fitcv_cp/worker_job.py` into `src/fitcv_cp/worker_run_support.py`
- keep public HTTP and worker entrypoints stable
- normalize only the storage helper residue directly touched by those extractions

## Key Deliverables

### Deliverable 1: `app.py` is assembly-first

`src/fitcv_cp/app.py` keeps `create_app(...)` and route boundaries, while extracted run-detail, artifact-download, and review helper families live in `src/fitcv_cp/app_run_support.py` with unchanged HTTP behavior.

### Deliverable 2: `worker_job.py` is entrypoint-first

`src/fitcv_cp/worker_job.py` keeps `execute_pipeline_run(...)` and `execute_cv_regenerate_once(...)`, while checkpoint/snapshot/synonym helper families move to `src/fitcv_cp/worker_run_support.py` with unchanged worker behavior.

### Deliverable 3: route and store contracts stay stable

One route-manifest test locks native FastAPI `(path, methods, name)` truth for admin routes, and any touched `sqlite_store.py` cleanup remains internal/support-only with no persistence-contract drift.

## Task/Wave Breakdown

### Task 1: Lock extraction seams and route contract

**Purpose:**
- define extract-now boundaries before moving code and add contract checks that prevent silent FastAPI drift

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Phase 5 spec accepted
- Phases 1-4 remain semantic source of truth; this task is structural only

**Steps:**
- [ ] Step 1: inventory `app.py` and `worker_job.py` helper clusters as `extract-now`, `keep-inline`, or `defer`
- [ ] Step 2: add one native FastAPI route-manifest assertion over `create_app().routes` for admin routes
- [ ] Step 3: keep route-path, response-class, and route-name contract explicit before extraction starts

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -k "route_manifest or review or synonym or settings_used or artifacts" -q`

**Exit Criteria:**
- route contract is locked and extraction seams are explicit enough to execute without guessing

### Task 2: Extract app support helpers

**Purpose:**
- reduce `app.py` around stable helper families while keeping HTTP assembly and route decorators local

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- extracted helpers stay pure or boundary-local and do not become a service layer

**Steps:**
- [ ] Step 1: move run-detail shaping, artifact-download/read-model, and review-queue helper families into `src/fitcv_cp/app_run_support.py`
- [ ] Step 2: move route-adjacent action helpers only when they are pure/helper-level and not direct FastAPI boundary code
- [ ] Step 3: rewire `app.py` imports and keep `create_app(...)` + route decorators local

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- `app.py` is materially narrower and tests prove unchanged route behavior

### Task 3: Extract worker support helpers

**Purpose:**
- reduce `worker_job.py` around stable helper families while preserving public worker entrypoints

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_run_support.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- worker helper extraction must not change snapshot payload contracts or event semantics

**Steps:**
- [ ] Step 1: move checkpoint/snapshot/synonym-automation helper families into `src/fitcv_cp/worker_run_support.py`
- [ ] Step 2: keep `execute_pipeline_run(...)` and `execute_cv_regenerate_once(...)` as entrypoints in `worker_job.py`
- [ ] Step 3: rewire imports and remove now-dead local helper copies

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- `worker_job.py` is entrypoint-first and worker tests prove unchanged behavior

### Task 4: Normalize touched storage helpers only

**Purpose:**
- delete duplicated storage leaf code exposed by extraction work without reopening persistence semantics

**Files:**
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Tasks 2-3 complete
- any change here must stay internal/support-only

**Steps:**
- [ ] Step 1: collapse duplicated internal field-update helpers in `sqlite_store.py` only if extraction touched them
- [ ] Step 2: remove leftover local compatibility-shaped leaf signatures only where every direct caller is updated in same patch
- [ ] Step 3: leave schema, persisted JSON contract, and store boundaries unchanged

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q`

**Exit Criteria:**
- touched storage residue is reduced without semantic persistence drift

### Task 5: Final docs and proof bundle

**Purpose:**
- align cross-cutting docs and run final bounded proof for Phase 5

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/api.md`
- Modify: `docs/observability.md`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Tasks 2-4 complete

**Steps:**
- [ ] Step 1: update docs only where extraction changed code-location guidance or observability ownership explanation
- [ ] Step 2: run bounded repo search to confirm no repo-wide monolith or service-layer expansion slipped in
- [ ] Step 3: refresh planning lineage and run validators

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q`
- [ ] `rg -n "APIRouter|Depends\(|service layer|domain/application/infrastructure|pipeline.py split" src/fitcv_cp docs`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Phase 5 proof is bounded, green, and doc drift is closed

## Verification

- `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q`
- `rg -n "def create_app|def execute_pipeline_run|def execute_cv_regenerate_once" src/fitcv_cp`
- `rg -n "APIRouter|Depends\(|service layer|domain/application/infrastructure|pipeline.py split" src/fitcv_cp docs`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
