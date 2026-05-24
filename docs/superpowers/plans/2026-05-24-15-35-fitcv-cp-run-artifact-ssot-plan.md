---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv_cp_run_artifact_ssot_symmetry_invariance_plan
parent_thread: workstream-operator-control-plane.fitcv-cp-run-artifact-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-05-24-15-32-fitcv-cp-run-artifact-ssot-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/bq_store.py
related_features: []
related_stages: []
---

# FitCV CP Run Artifact SSOT + Symmetry Refactor (Implementation Plan)

## Goal

Implement SSOT + symmetry + invariance refactor for run-artifact payload encoding/fingerprints and persistence behavior across `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/bq_store.py`, with backward-compatible schema evolution handling and evidence-first verification.

## Key Deliverables

### Deliverable 1: Worker artifact SSOT encoding + envelope contract

All worker-built persisted run artifacts:
- share one canonical envelope shape (required keys + naming)
- use one canonical JSON encoding helper (no ad-hoc `json.dumps` for persisted artifacts)
- stamp schema version consistently per spec (migration window rules honored)

### Deliverable 2: Persistence result symmetry across `bq_store.update_run_*`

All `update_run_*` write paths (sqlite and BigQuery):
- return one shared `PersistenceResult` shape
- apply centralized missing-column policy with stable reason codes
- avoid silent success on degraded writes

### Deliverable 3: Central registries for field names + schema evolution policy

Introduce SSOT registries:
- allowed pipeline run JSON field names
- schema evolution policy (missing-column behaviors) consumed by update helpers

## Task/Wave Breakdown

### Task 0: Fix planning lineage + baseline validator gate

**Purpose:**
- ensure spec/plan/thread lineage satisfies validators before code work

**Files:**
- Modify: `docs/intent/workstreams/threads/workstream-operator-control-plane/07-fitcv-cp-run-artifact-ssot-symmetry-refactor.md`
- Modify: `docs/superpowers/specs/2026-05-24-15-32-fitcv-cp-run-artifact-ssot-spec.md`
- Modify: `docs/superpowers/plans/2026-05-24-15-35-fitcv-cp-run-artifact-ssot-plan.md`

**Preconditions:**
- none

**Steps:**
- [x] Create bounded change thread doc with `thread_id` used by spec/plan
- [x] Ensure spec and plan reference `parent_thread` and pass validators
- [x] Run baseline validator gate

**Verification:**
- [x] `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- validator passes; lineage is stable for execution

### Task 1: Confirm current-state inventory and blast radius

**Purpose:**
- lock baseline behavior + identify callsites before changing contracts

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Inspect: `src/fitcv_cp/models.py`

**Preconditions:**
- Prefer: GitNexus is fresh (`.\scripts\get_gitnexus_freshness.ps1`)
- If GitNexus unavailable in worktree: proceed source-first and record limitation in lane context pack

**Steps:**
- [x] Enumerate worker-built artifacts and record:
  - payload keys, schema version keys, encoder used
  - where payload is persisted and with what function
- [x] Enumerate all `bq_store.update_run_*` callsites and group by:
  - expected return handling (ignored today vs checked)
  - missing-column fallbacks used today
- [x] Identify any downstream readers/parsers that assume old key names (schema key drift)

**Verification:**
- [x] Update spec inventory section (no code yet) if gaps discovered (no spec changes needed)

**Exit Criteria:**
- no unknown callsites remain for functions planned to change signature/return contract

### Task 2: Introduce SSOT registries + `PersistenceResult` contract (X-R1 + BQ-R1)

**Purpose:**
- create the shared contracts used by subsequent refactors

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (if best home for shared result/type)
- Verify: `src/fitcv_cp/worker_job.py` (callsite compatibility)

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Define `PersistenceResult` shape + reason code registry (SSOT)
- [x] Define registry for allowed JSON field names on `pipeline_runs`
- [x] Define schema evolution policy mapping:
  - field name → missing-column behavior (`degrade`, `skip`, `legacy_fallback`, `raise`)
- [x] Refactor internal update helper(s) to:
  - validate field names via registry
  - handle missing-column per policy
  - always return `PersistenceResult`

**Verification:**
- [x] Add/extend unit tests for:
  - invalid field name fails fast
  - missing-column produces expected `PersistenceResult`

**Exit Criteria:**
- helper(s) exist and at least one update path uses them end-to-end with tests

### Task 3: Normalize `update_run_*` API symmetry (BQ-R1)

**Purpose:**
- migrate all `update_run_*` functions to shared result contract and policy

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/worker_job.py` (callers updated to record/propagate result where needed)

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Update each `update_run_*` to return `PersistenceResult`:
  - sqlite path: degrade reasons explicit (run_not_found, sqlite failures)
  - BigQuery path: missing-column handled via policy
- [x] Replace ad-hoc missing-column fallback code with policy helper where eligible
- [x] Ensure `append_event` and “update-style” functions converge on consistent degrade semantics (per spec)

**Verification:**
- [x] Unit tests cover:
  - sqlite `run_not_found` degrade
  - BigQuery missing-column degrade for at least one field configured as degrade/skip
- [x] Run repo contract validator:
  - `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- no `update_run_*` returns `None`; callsites compile/typecheck (if typing enforced) and tests pass

### Task 4: Backend selection SSOT cleanup (BQ-R2)

**Purpose:**
- remove backend-mode drift and misleading knobs

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Inspect/Modify: `src/fitcv_cp/backend_runtime.py` (only if needed to preserve contract)

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Remove or repurpose `_sqlite_mode_enabled()` so there is one backend-mode concept
- [x] Ensure `bq_store` does not read env to decide mode (mode = `bq is None`)
- [x] Document backend expectation in docstring / module comment for `bq_store` entrypoints

**Verification:**
- [x] Unit test asserts sqlite path used when `bq is None`

**Exit Criteria:**
- no unused backend-mode helpers remain; behavior documented and tested

### Task 5: Fix sqlite connection contract drift (BQ-R3)

**Purpose:**
- eliminate signature/behavior contradictions in sqlite connection helper

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`

**Preconditions:**
- Task 3 complete (so changes land on stabilized helper surface)

**Steps:**
- [x] Remove `ensure_parent` parameter OR implement it correctly (per spec decision)
- [x] Ensure parent-dir creation behavior remains correct for all callsites
- [x] Add/adjust tests for sqlite open retry + parent-dir behavior (bounded, no flakiness)

**Verification:**
- [x] Unit test: db parent directory created only when intended

**Exit Criteria:**
- sqlite helper signature matches behavior; no ignored parameters remain

### Task 6: Normalize worker artifact encoding SSOT (WJ-R1)

**Purpose:**
- eliminate JSON encoding drift in worker artifacts

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (if helper changes needed)

**Preconditions:**
- Task 2 complete (encoding helper + envelope rules must be ready)

**Steps:**
- [x] Replace direct `json.dumps` usage for persisted worker artifacts with SSOT encoder
- [x] Ensure payload dicts obey canonical envelope rules (even if dual-key migration required)
- [x] Remove duplicate imports / small contradictions discovered in Task 1

**Verification:**
- [x] Unit tests for artifact payload encoding determinism
- [x] Repo contract validator:
  - `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- no persisted artifact builder uses ad-hoc encoding; payloads contain required keys

### Task 7: Unify fingerprinting SSOT and migration (WJ-R2)

**Purpose:**
- remove duplicate hash helpers and lock stable identity hashing

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (if canonical helper needs adjustment)

**Preconditions:**
- Task 6 complete (encoding stable before hashing)

**Steps:**
- [x] Replace `_stable_sha256_json` with SSOT fingerprint helper usage
- [x] If hash bytes change, implement migration strategy from spec (dual hash or compatibility mode) (not required for this internal fingerprint)
- [x] Add tests for fingerprint stability and compatibility where needed

**Verification:**
- [x] Unit test: known payload → expected hash (golden)

**Exit Criteria:**
- single fingerprint helper in codebase for this domain; tests pass

### Task 8: Contract-ize artifact envelope enforcement (WJ-R3)

**Purpose:**
- enforce shared envelope invariants across worker payload builders

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py`

**Preconditions:**
- Task 6 complete

**Steps:**
- [x] Introduce envelope builder/validator helper (dict or lightweight dataclass)
- [x] Refactor artifact payload dict builders to compose envelope + artifact body
- [x] Add validation checks (fail fast) for missing required keys

**Verification:**
- [x] Unit tests for each artifact family: required keys enforced, degradation_reason rules applied

**Exit Criteria:**
- envelope used by all worker persisted artifact builders; invariants enforced by tests

## Verification

- `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
- Run repo test suite command (determine exact command in Task 1; prefer targeted tests first, then full suite if available)
  - Evidence: full-suite `.\.venv\Scripts\python.exe -m pytest -q` may fail in lanes missing private/runtime artifacts (ex: `data/candidate_profile.private.yaml`); treat as environment-gated, not plan-scope regression.
  - Required bounded proof for this plan:
    - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
    - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py -k "results_export or cv_generation_debug or mapping_suggestions or manual_checkpoint"`
    - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_run_artifact_contracts.py`
- If `scripts/sync_architecture_docs.py` is impacted by doc changes, run:
  - `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`

## Completion Criteria

1. all Key Deliverables satisfied
2. all tasks above `completed` or `dropped`
3. validators/tests in Verification pass with captured evidence in lane context pack during execution

