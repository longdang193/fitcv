---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: fitcv_cp.worker_job SSOT/symmetry/invariance refactor implementation plan (R-WJ-01..06)
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-05-24-14-27-fitcv-cp-worker-job-ssot-symmetry-refactor-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv/contracts.py
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Implementation Plan: `fitcv_cp.worker_job` SSOT / symmetry / invariance refactor (R-WJ-01..06)

## Goal

Refactor `src/fitcv_cp/worker_job.py` artifact snapshot/persistence flows to use SSOT JSON/schema/hashing helpers with symmetric structure and invariant behavior, backed by tests.

## Key Deliverables

### Deliverable 1: JSON + schema SSOT

- Worker routes JSON decode/encode through `fitcv_cp.run_artifact_contracts`.
- Worker artifact schema-version literals replaced by SSOT constants in `fitcv.contracts`.
- Malformed stored JSON never crashes worker; per-surface policy is explicit and tested.

### Deliverable 2: Symmetric snapshot structure

- High-risk artifact snapshot builders follow consistent pattern: dict → invariants/schema → encode → persist → event.
- Fingerprint/dedupe uses SHA256 + stable canonicalization.

### Deliverable 3: Obsolete/duplicate surface cleanup

- Duplicate imports removed.
- Deprecated shim `_build_synonym_proposals_payload` audited and removed or isolated as explicit compat surface with tests.

## Task/Wave Breakdown

### Task 0: Baseline + impact rails

**Purpose:**
- capture baseline proof and blast-radius evidence

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- GitNexus fresh: `npx gitnexus analyze`

**Steps:**
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `uv run pytest tests/test_fitcv_cp/`
- [x] Record GitNexus impact for each edited symbol before edits:
  - `npx gitnexus impact <symbol> --direction upstream --include-tests -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT"`

**Verification:**
- [x] baseline tests green and impact evidence captured

**Exit Criteria:**
- proceed only if blast radius understood.

### Task 1: R-WJ-01 JSON helper SSOT adoption

**Purpose:**
- eliminate ad-hoc `json.loads` drift and unify failure policy

**Files:**
- Modify: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 0 complete

**Steps:**
- [x] Add/extend helpers (tolerant decode, stable encode) in `run_artifact_contracts`. (added `decode_json_object_or_raise`)
- [x] Migrate worker call sites (start with):
  - `execute_cv_regenerate_once` (migrated to `decode_json_object_or_raise`)
  - `_append_synonym_suppression_summary_event` (migrated to `decode_json_object_or_none`)
  - `_persist_synonym_proposals_snapshot` (migrated to `decode_json_object_or_raise`)
- [x] Add tests pinning invalid JSON behavior for each migrated surface. (added invalid JSON test for `execute_cv_regenerate_once`)

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- worker JSON behavior consistent and test-enforced.

### Task 2: R-WJ-02 Schema-version constants SSOT

**Purpose:**
- remove schema-version literals and keep versions centralized

**Files:**
- Modify: `src/fitcv/contracts.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Add missing schema constants (ex: settings used). (`SETTINGS_USED_SCHEMA_VERSION`)
- [x] Replace worker literals with constants.
- [x] Add tests asserting schema-version key/value. (existing `test_worker_persists_settings_used_json_on_success`)

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- no in-scope schema literals remain.

### Task 3: R-WJ-03 Unify `effective_settings_json` parsing

**Purpose:**
- remove duplicated parsing and enforce consistent synonym policy defaults

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Introduce single parse path and reuse parsed dict for:
  - skill_synonyms derivation
  - synonym mode resolution
- [x] Add tests for invalid/missing JSON and explicit opt-in/out. (added invalid JSON default test)

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- single parse path enforced, behavior preserved.

### Task 4: R-WJ-04 SHA256 dedupe fingerprints

**Purpose:**
- standardize fingerprint hashing invariant

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Convert SHA1 fingerprint to SHA256 with stable canonicalization helper.
- [x] Add test proving dedupe prevents duplicate event emission.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- dedupe invariant enforced by tests.

### Task 5: R-WJ-05 Dict-first payload symmetry

**Purpose:**
- make payload invariants testable and reduce duplication

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Tasks 1–2 complete

**Steps:**
- [x] Extract dict builders for high-risk artifacts:
  - settings used
  - stage transition artifacts
  - synonym proposals (worker snapshot)
- [x] Route encoding via SSOT encode helper.
- [x] Add dict-shape tests (required keys/types).

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- consistent builder shape for in-scope artifacts.

### Task 6: R-WJ-06 Compat shim cleanup

**Purpose:**
- remove or isolate deprecated shim safely

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Tasks 1–5 complete

**Steps:**
- [x] Audit callers via GitNexus + `rg`.
- [x] Remove shim if no external callers; otherwise convert to explicit compat with deprecation note + test pin.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/`

**Exit Criteria:**
- compat surface handled with explicit audit evidence.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uv run pytest tests/test_fitcv_cp/`
- `npx gitnexus detect-changes -r "C:\\Users\\HOANG PHI LONG DANG\\repos\\JOB-PROJECT" --scope staged`

## Completion Criteria

1. Key Deliverables satisfied.
2. Final verification commands PASS.
3. GitNexus detect-changes shows only expected scope.
