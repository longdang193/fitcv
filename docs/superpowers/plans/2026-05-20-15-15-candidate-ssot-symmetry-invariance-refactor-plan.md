---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: candidate-module-ssot-symmetry-invariance-refactor-plan
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
parent_spec: docs/superpowers/specs/2026-05-20-15-12-candidate-ssot-symmetry-invariance-spec.md
targets:
  - src/fitcv/candidate.py
  - tests/test_candidate.py
related_features: []
related_stages: []
---

## Goal

Implement bounded refactor for `src/fitcv/candidate.py` to enforce SSOT normalization/validation flow, symmetry across equivalent profile concepts, and stable invariants, without breaking current external behavior.

## Key Deliverables

### Deliverable 1: Unified profile normalization/validation path

`candidate.py` exposes one internal canonical profile preparation boundary reused by parsing and consumer paths, so downstream operations (`infer_effective_preferences`, `prepare_profile_rows`) see consistent normalized input assumptions.

### Deliverable 2: Contract-consistent section and skills handling

Section-role constants and skills-shape handling are made non-contradictory across validation, flattening, and row-preparation behaviors, with compatibility-first behavior preserved for existing callers.

### Deliverable 3: Regression-proofed refactor evidence

`tests/test_candidate.py` updated to assert invariants for loader parity, parser error consistency, skills-shape contract, and explicit-preference precedence, with targeted commands proving no regressions.

## Task/Wave Breakdown

### Task 1: Establish normalized profile SSOT boundary

**Purpose:**
- create single internal path for profile normalization and readiness used across parsing and direct-consumer entrypoints

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Modify: `src/fitcv/candidate.py`
- Verify: `tests/test_candidate.py`

**Preconditions:**
- parent spec approved for implementation handoff
- current tests baseline passing or known

**Steps:**
- [ ] Step 1: add internal helper boundary (for example `_ensure_normalized_profile`) that applies canonical normalization rules once
- [ ] Step 2: route `load_profile_yaml`, `load_profile_json_text`, and `load_profile_text` through shared parse+validate+normalize sequence
- [ ] Step 3: route direct consumers (`infer_effective_preferences`, `prepare_profile_rows`) through same internal readiness boundary where needed

**Verification:**
- [ ] `uvx pytest tests/test_candidate.py -k "load_profile or infer_effective_preferences or prepare_profile_rows"`

**Exit Criteria:**
- all relevant entrypoints consume equivalent normalized profile assumptions

### Task 2: Remove section-role and skills-shape contradictions

**Purpose:**
- enforce symmetry for section semantics and skills handling while preserving compatibility

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Modify: `src/fitcv/candidate.py`
- Verify: `tests/test_candidate.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: introduce explicit constants for required sections, id-bearing sections, and evidence-ref participant sections
- [ ] Step 2: refactor validation loops to use shared section constants and remove implicit drift
- [ ] Step 3: implement compatibility-first skills normalization policy so validation/flattening/row-prep no longer conflict

**Verification:**
- [ ] `uvx pytest tests/test_candidate.py -k "validate_profile or flatten_skills or prepare_profile_rows"`

**Exit Criteria:**
- single declared skills policy enforced consistently across all candidate helpers

### Task 3: Unify parser error contract and strengthen invariant tests

**Purpose:**
- align JSON/YAML parsing error semantics and lock new invariants with tests

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Modify: `src/fitcv/candidate.py`
- Modify: `tests/test_candidate.py`
- Verify: `tests/test_candidate.py`

**Preconditions:**
- Tasks 1-2 complete

**Steps:**
- [ ] Step 1: centralize parse error handling for JSON code paths (`load_profile_json_text` and `load_profile_text(..., format_hint="json")`)
- [ ] Step 2: add/update tests for parser error parity and normalized loader parity
- [ ] Step 3: add/update tests confirming explicit preferences not overridden and evidence-ref integrity preserved

**Verification:**
- [ ] `uvx pytest tests/test_candidate.py`

**Exit Criteria:**
- invariants covered by tests with stable error contract assertions

### Task 4: Final scope safety and completion checks

**Purpose:**
- ensure bounded impact and implementation readiness for merge/next workflow

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Inspect: `tests/test_candidate.py`
- Verify: repo validation and optional advisory GitNexus scope checks

**Preconditions:**
- Tasks 1-3 complete and tests passing

**Steps:**
- [ ] Step 1: run repo hook subset validator for contract compliance
- [ ] Step 2: review diff scope to ensure only intended files/behaviors changed
- [ ] Step 3: if committing, run `gitnexus_detect_changes()` advisory check per repo guidance and compare with expected scope

**Verification:**
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `uvx pytest tests/test_candidate.py`

**Exit Criteria:**
- change set bounded, validated, and ready for execution closeout workflow

## Verification

- `uvx pytest tests/test_candidate.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
