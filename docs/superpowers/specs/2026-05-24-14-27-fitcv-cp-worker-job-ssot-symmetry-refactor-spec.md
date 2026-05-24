---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv_cp.worker_job SSOT/symmetry/invariance refactor (R-WJ-01..06)
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv/contracts.py
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Detailed Spec: `fitcv_cp.worker_job` SSOT / symmetry / invariance refactor (R-WJ-01..06)

## Goal

Normalize `src/fitcv_cp/worker_job.py` artifact snapshot/persistence flows for SSOT (JSON/schema/hashing), symmetry (equivalent flows use equivalent structure), and invariance (shared rules/defaults stay consistent), without changing intended runtime behavior.

## Key Deliverables

### Deliverable 1: JSON/schema SSOT

- Worker JSON decode/encode uses `fitcv_cp.run_artifact_contracts`.
- Worker schema-version values come from `fitcv.contracts` constants (no literals for in-scope artifacts).
- Malformed stored JSON does not crash worker; per-surface policy is explicit and tested.

### Deliverable 2: Symmetric payload pipeline

- High-risk artifacts follow shape: build dict → validate/invariants → encode → persist → event (if needed).
- Fingerprints use SHA256 + stable canonicalization.

### Deliverable 3: Contradiction/obsolete cleanup

- Duplicate imports removed.
- Deprecated shim `_build_synonym_proposals_payload` audited and removed or contained with deprecation path + tests.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior + drift points before refactor

**Steps:**
- [x] Inventory JSON parse sites + payload builders + snapshot persisters in `worker_job.py`.
- [x] Map equivalent concepts vs `fitcv_cp.app` (JSON failure policy, schema versions, hashing, effective settings parsing).
- [x] Record GitNexus impact for each symbol to be edited.

**Verification:**
- [x] Equivalence map covers R-WJ-01..06 targets.

**Exit Criteria:**
- no change depends on unstated assumptions.

### Wave 2: Decision closure

**Purpose:**
- resolve SSOT ownership and migration rules

**Steps:**
- [x] Choose worker JSON failure policy per surface (skip/warn/fail).
- [x] Define schema-version constant placement.
- [x] Define SHA256 fingerprint migration note.
- [x] Decide compat shim handling rules.

**Verification:**
- [x] Acceptance criteria per R-WJ item documented.

**Exit Criteria:**
- spec ready for plan authoring.

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof + safety controls

**Steps:**
- [x] Test matrix for malformed JSON, schema versions, fingerprint dedupe, effective-settings defaults.
- [x] Repo checks + GitNexus detect-changes gates.

**Verification:**
- [x] Validation plan provides evidence-first proof for invariants.

**Exit Criteria:**
- implementation plan can be written with bounded tasks.

## Design Decisions

### Decision: JSON helper SSOT (R-WJ-01)

- context: `worker_job.py` uses ad-hoc `json.loads`; `app.py` uses shared helpers.
- choice: extend and use `fitcv_cp.run_artifact_contracts` helpers for worker surfaces.
- impact: consistent parsing and test-enforced failure policy.

### Decision: Schema-version constants (R-WJ-02)

- context: worker contains schema literals (ex: settings used).
- choice: add missing constants to `fitcv.contracts`; worker consumes constants only.

### Decision: One effective-settings parse (R-WJ-03)

- context: repeated parse of `effective_settings_json` risks inconsistent defaults.
- choice: parse once per path; reuse parsed dict for derived flags.

### Decision: SHA256 fingerprint invariance (R-WJ-04)

- context: SHA1 and SHA256 both used for “fingerprint/dedupe”.
- choice: standardize on SHA256 + stable canonical JSON.

### Decision: Dict-first payload builders (R-WJ-05)

- context: inline encode makes invariants hard to test.
- choice: dict-first builders for high-risk artifacts; encode via SSOT helper.

### Decision: Compat shim handling (R-WJ-06)

- context: deprecated shim exists; caller set unknown.
- choice: audit callers; remove if safe; else isolate as explicit compat with deprecation + test pin.

## Invariants

- Worker never crashes on malformed stored JSON; behavior is explicit and tested.
- Persisted payload keys and schema-version values remain stable.
- Run-mode normalization/labels stay sourced from `fitcv_cp.run_artifact_contracts`.
- Synonym automation remains opt-in via effective settings.

## Validation Plan

- proof target: JSON failure policy enforced for migrated worker surfaces
  - method: unit tests with malformed JSON fixtures
  - evidence: `uv run pytest tests/test_fitcv_cp/` PASS
- proof target: schema-version constants used everywhere in scope
  - method: unit tests + `rg` checks
  - evidence: tests PASS; no literals remain
- proof target: SHA256 dedupe stable
  - method: unit test repeats identical payload; assert no duplicate event
  - evidence: tests PASS
- proof target: repo contracts intact
  - method: validator + contract check
  - evidence: `python scripts/hooks/run_validator.py --fast` PASS

## Completion Criteria

1. Key Deliverables satisfied.
2. Validation evidence green.
3. Spec ready for execution handoff.

