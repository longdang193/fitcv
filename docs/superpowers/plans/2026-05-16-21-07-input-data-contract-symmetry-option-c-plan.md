---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: input-data-contract-symmetry-option-c
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
parent_spec: docs/superpowers/specs/2026-05-16-21-02-input-data-contract-symmetry-option-c-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv/candidate.py
  - src/fitcv/config.py
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
---

## Goal

Implement Option C from the approved spec so trigger-time input handling for jobs, candidate profile, and synonym overlay becomes artifact-centric, mode-symmetric, and runtime-invariant.

## Key Deliverables

### Unified artifact input contract implementation

Control-plane trigger paths use canonical per-artifact parse/validate/normalize flows, with mode selecting source only.

### Runtime envelope invariance preservation

Canonical runtime snapshots and normalized runtime overlay structures remain stable and equivalent across supported input modes and representations.

### Coverage and UI contract alignment

Tests prove mode symmetry/invariance, and trigger UI copy/accept metadata aligns with backend contract behavior.

## Task/Wave Breakdown

### Task 1: Establish canonical input-contract helpers

**Purpose:**
- introduce shared helper boundaries so parsing semantics are artifact-based, not mode-based

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv/candidate.py`
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/candidate.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Spec `input-data-contract-symmetry-option-c` remains proposed/active and unchanged in scope
- Existing trigger runtime envelope contract fields are confirmed (`jobs_input_json`, `candidate_profile_json`)

**Steps:**
- [x] Step 1: Define canonical helper entrypoints for artifact parsing/validation in control-plane boundary.
- [x] Step 2: Extend candidate parsing support to representation-equivalent ingestion (YAML/JSON where spec requires) while preserving existing schema validation.
- [x] Step 3: Keep synonym overlay normalization path delegated to existing runtime overlay parser/normalizer.
- [x] Step 4: Ensure helper outputs are canonicalized for downstream envelope insertion.

**Verification:**
- [x] New/updated helper-level tests or focused assertions prove candidate representation equivalence and canonical output shape.

**Exit Criteria:**
- Artifact-level helper contracts exist and expose no mode-specific parser divergence.

### Task 2: Route all trigger modes through artifact-centric paths

**Purpose:**
- remove mode-dependent behavior divergence in `/admin/upload-trigger` while preserving mode source semantics

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: Refactor jobs/candidate/synonym mode branches to use artifact contract helpers for parse/validate/normalize.
- [x] Step 2: Keep source metadata (`jobs_input_source`, `candidate_profile_source`, overlay source metadata) intact for observability.
- [x] Step 3: Preserve trigger-time runtime envelope shape and downstream orchestration payload boundaries.
- [x] Step 4: Normalize error handling to artifact-level validation outcomes instead of mode-specific parser exceptions.

**Verification:**
- [x] Existing mode-behavior tests pass and new assertions confirm equivalent acceptance/rejection by artifact semantics.

**Exit Criteria:**
- Trigger mode selection affects source acquisition only, not artifact parsing semantics.

### Task 3: Align trigger UI contract to backend symmetry

**Purpose:**
- remove UI wording/accept hints that imply obsolete format asymmetry

**Files:**
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: Update candidate profile labels/help text to representation-neutral wording consistent with backend contract.
- [x] Step 2: Update candidate input `accept` hints to match supported representation set.
- [x] Step 3: Preserve jobs and synonym UI guidance consistency with their final artifact contracts.

**Verification:**
- [x] Template-focused tests/assertions validate expected labels, helper text, and accept attributes.

**Exit Criteria:**
- UI no longer encodes contradictory parser restrictions relative to backend behavior.

### Task 4: Prove invariance and regressions at plan scope

**Purpose:**
- deliver artifact-level proof that contract symmetry and runtime invariance hold without unrelated behavior drift

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv/candidate.py`
- Verify: `src/fitcv/config.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: Add/adjust mode matrix tests for jobs/candidate/synonym inputs.
- [x] Step 2: Add equivalence tests for semantically-equal candidate YAML/JSON payloads producing equal canonical runtime snapshots.
- [x] Step 3: Add assertions that synonym overlay normalization/merge behavior remains unchanged for valid inputs.
- [x] Step 4: Run targeted suite and capture pass evidence.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "candidate_profile_mode or upload_trigger or synonym_overlay"`

**Exit Criteria:**
- Plan-scoped tests demonstrate symmetry, invariance, equivalence, and no unintended trigger contract regressions.

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k "candidate_profile_mode or upload_trigger or synonym_overlay"`
- `pytest tests/test_fitcv_cp/test_app.py -k "settings_page_cv_sections_no_raw_yaml or run_detail"`
- `python scripts/validate_planning_lifecycle.py`

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

