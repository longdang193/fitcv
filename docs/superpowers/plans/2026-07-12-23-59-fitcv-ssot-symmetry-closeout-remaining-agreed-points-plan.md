---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-closeout-remaining-agreed-points
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-23-58-fitcv-ssot-symmetry-closeout-remaining-agreed-points-spec.md
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-07-12-23-58-fitcv-ssot-symmetry-closeout-remaining-agreed-points-spec.md
  - docs/generated/planning_lineage.yaml
  - src/fitcv/config.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_config.py
  - tests/test_pipeline.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_reconcile_integration_sqlite.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
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

Implement remaining agreed SSOT/symmetry closeout work from `docs/superpowers/specs/2026-07-12-23-58-fitcv-ssot-symmetry-closeout-remaining-agreed-points-spec.md` with one bounded lane:

- remove active persistence compatibility residue across web, worker, and reconciler paths
- centralize lifecycle command/transition truth
- centralize late-stage outcome meaning including control-plane projections
- finish schema-derived settings ownership without breaking settings persistence
- finish runtime-routing symmetry across startup, trigger snapshot, worker, and diagnostics
- align master remediation lineage so this closeout lane is canonical remaining-work owner

## Key Deliverables

### Planning lineage alignment

`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md` and generated `docs/generated/planning_lineage.yaml` point remaining agreed work at this closeout lane instead of leaving stale competing child-spec sequencing.

### Active runtime persistence and lifecycle SSOT

`src/fitcv_cp/app.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/reconciler.py`, `src/fitcv_cp/reconciler_service.py`, `src/fitcv_cp/store.py`, and `src/fitcv_cp/sqlite_store.py` stop carrying dead backend-shape truth and share one lifecycle command/transition owner.

### Late-stage, settings, and routing convergence

`src/fitcv/late_stage_contract.py`, `src/fitcv/pipeline.py`, `src/fitcv/agentic_cv_analysis.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/settings_store.py`, and `src/fitcv/runtime_routing.py` converge on one owner per fact with targeted regression proof.

## Task/Wave Breakdown

### Task 1: Lock lineage and characterization proof

**Purpose:**
- freeze remaining-work ownership and add tests that pin intended closeout behavior before broad edits

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
- Inspect: `docs/superpowers/specs/2026-07-12-23-58-fitcv-ssot-symmetry-closeout-remaining-agreed-points-spec.md`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- patched closeout spec accepted as source of truth
- current targeted tests runnable in workspace

**Steps:**
- [ ] Step 1: patch master remediation spec so remaining unresolved work points at closeout spec instead of stale phase fan-out
- [ ] Step 2: add or tighten characterization tests for active persistence residue, reconciler lifecycle behavior, and settings-store save/load parity
- [ ] Step 3: add or tighten app-side characterization tests for late-stage projection and routing snapshot symmetry where current behavior must be preserved

**Verification:**
- [ ] `python -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- remaining-work lineage is source-correct and closeout claims are pinned by failing-first or characterization proof

### Task 2: Remove persistence residue across web, worker, and reconciler

**Purpose:**
- make active control-plane runtime SQLite-shaped end to end

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/reconciler_service.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/worker_job.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: remove active `project` / `dataset` threading where values are ignored, constant, or leaf-only compatibility noise
- [ ] Step 2: collapse any unavoidable local shim behind one adapter instead of repeating backend-shape args through app and worker
- [ ] Step 3: make active config ingress treat `bigquery_dataset` as absent or explicit inert compatibility only
- [ ] Step 4: ensure reconciler entry path uses same cleaned persistence contract as web and worker

**Verification:**
- [ ] `python -m pytest tests/test_config.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "\bproject: str\b|\bdataset: str\b|\bbigquery_dataset\b|ControlPlaneStore" src/fitcv_cp src/fitcv/config.py`

**Exit Criteria:**
- active runtime no longer pretends backend polymorphism across web, worker, or reconciler paths

### Task 3: Centralize lifecycle and late-stage outcome truth

**Purpose:**
- unify run command/transition meaning and late-stage outcome meaning without new architecture layers

**Files:**
- Modify: `src/fitcv/late_stage_contract.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/reconciler.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv/late_stage_contract.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: extract one callable lifecycle owner used by route handlers, worker paths, and reconciler transitions
- [ ] Step 2: remove duplicate lifecycle predicates, status groups, and open-coded transition checks from active consumers
- [ ] Step 3: move remaining late-stage outcome literals and meaning tables under `late_stage_contract.py`
- [ ] Step 4: rewire control-plane projections to derive labels, subreasons, and acceptance/rejection meaning from canonical late-stage truth

**Verification:**
- [ ] `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "RUN_STATUS_GROUPS|can_cancel|can_archive|can_unarchive|blocked_by_reranker_fit|skipped_fit_gate|ready_for_generation|analysis_failed|validation_failed|generation_failed|persistence_failed" src/fitcv src/fitcv_cp`

**Exit Criteria:**
- lifecycle and late-stage meaning each have one active owner with app-side and pipeline-side proof

### Task 4: Finish schema-derived settings ownership with store parity

**Purpose:**
- remove remaining parallel settings truth without breaking persisted settings behavior

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Verify: `src/fitcv_cp/settings_schema.py`
- Verify: `src/fitcv_cp/settings_store.py`

**Preconditions:**
- Task 1 complete
- Task 2 complete if settings code still consumes persistence helpers touched there

**Steps:**
- [ ] Step 1: move remaining section/group/stage/control-surface/native-attribute facts into schema rows or one schema-owned projection layer
- [ ] Step 2: delete parallel maps and suffix heuristics that only restate schema truth
- [ ] Step 3: keep settings-store coercion and save/load behavior aligned with schema-derived ownership

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- [ ] `rg -n "RANKING_GROUPS|SETTINGS_SECTIONS|CV_GROUPS|_KEY_TO_STAGE_ID|_GROUP_TO_CONTROL_SURFACE|suffix|_secs" src/fitcv_cp`

**Exit Criteria:**
- settings render, coercion, and persistence paths all derive from same canonical settings facts

### Task 5: Finish routing symmetry and regenerate planning artifacts

**Purpose:**
- unify equivalent routing snapshot truth and leave repo verification clean

**Files:**
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_runtime_routing.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 2-4 complete

**Steps:**
- [ ] Step 1: remove remaining ad hoc routing snapshot assembly where equivalent fields can derive from canonical resolver output
- [ ] Step 2: keep startup, trigger snapshot, worker execution, and diagnostics aligned on provider/model/base URL/API-key-availability truth for same inputs
- [ ] Step 3: regenerate planning lineage after source-plan updates and confirm validator passes

**Verification:**
- [ ] `python -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- equivalent routing surfaces agree on resolved truth and planning artifacts validate cleanly

## Verification

- `python -m pytest tests/test_config.py tests/test_pipeline.py tests/test_runtime_routing.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
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
