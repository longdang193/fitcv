---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-6-registry-closeout-and-legacy-arg-deletion
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-23-35-fitcv-ssot-symmetry-phase-6-registry-closeout-and-legacy-arg-deletion-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - scripts/backfill_live_run_artifacts.py
  - tests/test_config.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - inspection_debugging
  - trigger_run_management
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement Phase 6 from
`docs/superpowers/specs/2026-07-12-23-35-fitcv-ssot-symmetry-phase-6-registry-closeout-and-legacy-arg-deletion-spec.md`:

- remove dead runtime-alignment residue
- make `bigquery_dataset` behavior explicit and boundary-only
- patch the active backfill script off `bq_store`
- remove public `project` / `dataset` legacy args from active control-plane runtime, with at most one explicit local shim if needed
- centralize control-plane stage/artifact presentation under one small registry owner
- tighten settings schema boundary derivation for native attrs and card/section projections

## Key Deliverables

### Deliverable 1: active runtime no longer leaks legacy backend shape

`src/fitcv_cp/app.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/sqlite_store.py`, and `scripts/backfill_live_run_artifacts.py` stop exposing BigQuery-era control-plane shape on active paths, while chosen `bigquery_dataset` compatibility behavior is explicit and tested.

### Deliverable 2: stage/artifact presentation is registry-driven

`src/fitcv_cp/app.py` derives stage order, stage labels, bundle members, artifact labels, and artifact availability from one small registry owner rather than parallel tuples, `RunArtifactFile(...)` clusters, and filename switch chains.

### Deliverable 3: settings boundary behavior is schema-driven where touched

`src/fitcv_cp/settings_schema.py` stops deriving native numeric attrs and selected card/filter groupings from suffix folklore where explicit schema metadata or one schema-owned projection can own the same behavior.

## Task/Wave Breakdown

### Task 1: Lock final contracts before edits

**Purpose:**
- freeze the exact Phase 6 contracts so cleanup work cannot drift into rewrite-by-guessing

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `scripts/backfill_live_run_artifacts.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Phase 6 spec accepted
- baseline active tests are runnable in current workspace

**Steps:**
- [ ] Step 1: add characterization test for final `bigquery_dataset` behavior at config ingress
- [ ] Step 2: add characterization test for stale-run backfill script behavior on SQLite-only path
- [ ] Step 3: add or tighten artifact/stage contract tests so current route-boundary outputs are locked before registry refactor
- [ ] Step 4: define one allowed temporary shim location if public arg deletion cannot finish in one patch without scope blowout

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -k "bigquery_dataset or artifact or stage or backfill or settings_used" -q`

**Exit Criteria:**
- Phase 6 behavior claims are testable and no major cleanup step depends on unstated assumptions

### Task 2: Remove dead residue and patch active backfill script

**Purpose:**
- delete easy dead surfaces first and move the active repair script onto native SQLite-only runtime

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `scripts/backfill_live_run_artifacts.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: delete `_resolve_mode_summary()` and any now-dead settings-page copy branching that exists only for removed runtime-alignment presentation
- [ ] Step 2: implement chosen `bigquery_dataset` behavior as boundary-only config handling
- [ ] Step 3: switch `scripts/backfill_live_run_artifacts.py` from `fitcv_cp.bq_store` to active SQLite store/runtime path
- [ ] Step 4: verify one stale-run repair path works without `bq_store` import or BigQuery runtime branch

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -k "bigquery_dataset or backfill or settings" -q`
- [ ] `rg -n "_resolve_mode_summary|from fitcv_cp\.bq_store|backend_type.*bigquery" src/fitcv_cp scripts/backfill_live_run_artifacts.py`

**Exit Criteria:**
- dead alignment residue is gone and active backfill tooling is SQLite-native

### Task 3: Delete public legacy args, isolate any remaining local shim

**Purpose:**
- remove user-facing and active-runtime `project` / `dataset` leakage without forcing uncontrolled same-pass repo churn

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `scripts/backfill_live_run_artifacts.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- Task 2 complete if backfill script still depends on old signatures

**Steps:**
- [ ] Step 1: remove `project` / `dataset` from active script and public control-plane wrapper calls first
- [ ] Step 2: update direct helper callers in `app.py`, `worker_job.py`, and `sqlite_store.py` where every caller is local and covered by tests
- [ ] Step 3: if needed, keep exactly one explicit internal shim and mark it boundary-local rather than ambient compatibility
- [ ] Step 4: drop no-longer-needed test fixtures that still pass `project="proj"` / `dataset="ds"` on active paths

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "project=|dataset=" src/fitcv_cp scripts/backfill_live_run_artifacts.py tests/test_fitcv_cp`

**Exit Criteria:**
- no public control-plane runtime boundary or active script exposes legacy backend args, and any retained shim is single-owner and local-only

### Task 4: Introduce one control-plane presentation registry

**Purpose:**
- replace parallel stage/artifact lists and filename switches with one small derived owner

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 artifact/stage contract tests exist

**Steps:**
- [ ] Step 1: add one small registry owner with explicit `ControlPlaneStageSpec` and `ControlPlaneArtifactSpec` row shapes
- [ ] Step 2: derive stage loops, stage labels, artifact labels, and artifact bundle rows from that registry
- [ ] Step 3: replace filename-switch availability logic with registry-driven availability resolution plus small shared helpers
- [ ] Step 4: keep route handlers and `RunArtifactFile` response shape unchanged at boundary

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -k "artifact or bundle or stage or review_required" -q`
- [ ] `rg -n "for stage_id in \(|if filename ==" src/fitcv_cp/app.py`

**Exit Criteria:**
- one registry drives control-plane stage/artifact presentation with stable route behavior

### Task 5: Tighten settings schema boundary derivation

**Purpose:**
- replace suffix-driven boundary logic with schema-owned metadata or one schema-owned projection helper

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 settings tests exist or are extended

**Steps:**
- [ ] Step 1: patch `settings_native_input_attrs(...)` so numeric attrs come from explicit schema metadata where practical
- [ ] Step 2: patch current settings-page projection helpers so section/card key ownership is not built from ad hoc suffix filters where schema metadata can own it
- [ ] Step 3: keep one schema-owned projection if full inline metadata would be noisier than the problem it solves
- [ ] Step 4: keep page copy and save/load behavior stable unless a proven mismatch is fixed in same patch

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- touched settings boundary behavior is schema-driven and suffix folklore is reduced or isolated behind one explicit projection

### Task 6: Final bounded proof and lifecycle validation

**Purpose:**
- prove Phase 6 closed intended residue without hidden scope creep

**Files:**
- Verify: `tests/test_config.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 2-5 complete

**Steps:**
- [ ] Step 1: run bounded test suite
- [ ] Step 2: run grep-based residue checks for removed terms and legacy arg leakage
- [ ] Step 3: regenerate planning lineage and run validators

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "_resolve_mode_summary|from fitcv_cp\.bq_store|backend_type.*bigquery|bigquery_dataset" src scripts/backfill_live_run_artifacts.py`
- [ ] `rg -n "project=|dataset=" src/fitcv_cp scripts/backfill_live_run_artifacts.py`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Phase 6 proof is green and remaining compatibility behavior, if any, is explicit boundary-only debt rather than ambient drift

## Verification

- `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- `rg -n "_resolve_mode_summary|from fitcv_cp\.bq_store|backend_type.*bigquery|bigquery_dataset" src scripts/backfill_live_run_artifacts.py`
- `rg -n "project=|dataset=" src/fitcv_cp scripts/backfill_live_run_artifacts.py`
- `rg -n "for stage_id in \(|if filename ==" src/fitcv_cp/app.py`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
