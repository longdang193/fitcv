---
thread_id: workstream-operator-control-plane.fitcv-cp-run-artifact-ssot-symmetry-refactor
status: completed
---

# fitcv-cp-run-artifact-ssot-symmetry-refactor

## Goal

Refactor `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/bq_store.py` to enforce SSOT, symmetry, and invariance for:

- run artifact payload envelope + schema version stamping
- stable JSON encoding and hashing/fingerprints
- persistence result semantics across BigQuery vs sqlite backends
- schema evolution (missing column) behavior via centralized policy

## Key Deliverables

### Deliverable 1: Artifact envelope + encoding SSOT

- canonical envelope enforced across persisted artifacts
- single encoder path used by all worker-built artifacts
- backward-compatible schema version key migration documented and tested

### Deliverable 2: Persistence API symmetry

- all `update_run_*` functions return same `PersistenceResult` contract
- missing-column compatibility uses shared policy and stable reason codes

### Deliverable 3: Validation evidence

- unit tests for payload/encoding/fingerprint invariants
- unit tests for sqlite + BigQuery missing-column degraded behavior
- `scripts/validate_repo_contracts.py --fast` passes with evidence captured in lane context pack

## Task/Wave Breakdown

### Wave 1: Planning + baseline gates

**Purpose:**
- ensure spec/plan lineage valid and baseline validators pass before refactor

**Steps:**
- [x] link spec + plan
- [x] baseline validator pass recorded

**Verification:**
- [x] `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- spec/plan ready for execution with passing validators

### Wave 2: Implementation execution

**Purpose:**
- execute implementation plan tasks with evidence-first verification

**Steps:**
- [x] execute plan tasks under isolated lane worktree
- [x] keep execution context pack updated per governance

**Verification:**
- [x] plan-defined verification commands pass

**Exit Criteria:**
- plan complete and ready for closure gates
