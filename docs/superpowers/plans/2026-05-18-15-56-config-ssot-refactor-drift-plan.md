---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-config-ssot-refactor-and-drift-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-18-15-52-config-ssot-refactor-drift-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv/config_loader.py
  - src/fitcv/config_normalizers.py
  - src/fitcv/config_validators.py
  - src/fitcv/config_compat.py
  - tests/
related_features: []
related_stages: []
---

## Goal

Execute behavior-preserving refactor and drift patch for `src/fitcv/config.py` into SSOT-aligned modular structure, with GitNexus-gated blast-radius control and explicit compatibility-window safety.

## Key Deliverables

### Deliverable 1

Config system split into focused modules (`loader`, `normalizers`, `validators`, `compat`) while preserving existing public config API behavior through `src/fitcv/config.py` facade.

### Deliverable 2

Deterministic one-pass load pipeline implemented with explicit SSOT enforcement mode (`warn` default, `strict` opt-in), eliminating duplicate normalization drift and reducing ownership overlap risk.

### Deliverable 3

Regression and structural verification evidence complete: targeted tests pass, type checks pass for touched modules, and GitNexus detect-changes confirms expected impact scope before commit.

## Task/Wave Breakdown

### Task 1: Baseline and GitNexus impact gates

**Purpose:**
- freeze current behavior and map caller blast radius before edits

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `tests/`
- Verify: `docs/superpowers/specs/2026-05-18-15-52-config-ssot-refactor-drift-spec.md`

**Preconditions:**
- GitNexus index fresh (`.\scripts\get_gitnexus_freshness.ps1`)
- parent spec approved for implementation

**Steps:**
- [ ] Run impact/context for each target symbol:
  - `load_config`
  - `_normalize_config_keys`
  - `_detect_env_canonical_ownership_overlaps`
  - `_detect_pipeline_ssot_overlap`
  - `apply_cv_compatibility_projection`
- [ ] Record direct callers, affected flows, and risk level for each symbol.
- [ ] Capture current regression baseline by running existing config-related tests.

**Verification:**
- [ ] GitNexus outputs captured in execution notes and align with expected config surfaces.
- [ ] Baseline test run output stored for before/after comparison.

**Exit Criteria:**
- all target symbols have known blast radius and baseline behavior evidence

### Task 2: Extract module boundaries and keep facade contract

**Purpose:**
- separate concerns without breaking imports/behavior

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_loader.py`
- Modify: `src/fitcv/config_normalizers.py`
- Modify: `src/fitcv/config_validators.py`
- Modify: `src/fitcv/config_compat.py`

**Preconditions:**
- Task 1 complete
- target module dependency graph agreed (`loader -> normalizers -> validators -> compat`, facade on top)

**Steps:**
- [ ] Create new modules and move functions by single ownership domain.
- [ ] Keep public API entrypoints in `config.py` and route to extracted modules.
- [ ] Remove duplicate in-module logic where equivalent abstractions now exist.
- [ ] Ensure no circular imports; adjust helper placement if needed.

**Verification:**
- [ ] Import smoke check for `fitcv.config` and consumers passes.
- [ ] Static inspection confirms extracted functions no longer duplicated across modules.

**Exit Criteria:**
- module split complete; facade stable; no import breakage

### Task 3: Implement deterministic SSOT pipeline and drift patch

**Purpose:**
- enforce single-pass pipeline and contain legacy behavior cleanly

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_normalizers.py`
- Modify: `src/fitcv/config_validators.py`
- Modify: `src/fitcv/config_compat.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Refactor `load_config` orchestration to one normalization pass and one validation pass.
- [ ] Add SSOT enforcement mode branch (`warn` vs `strict`) in overlap validation path.
- [ ] Move compatibility projections and legacy bridge stripping into compat module only.
- [ ] Preserve env precedence and compatibility defaults per parent spec invariants.

**Verification:**
- [ ] Unit assertions prove duplicate normalization removed.
- [ ] Overlap fixtures show warn-mode logs and strict-mode hard-fail behavior.

**Exit Criteria:**
- single-pass pipeline active with mode-gated SSOT enforcement and isolated compat logic

### Task 4: Tests and refactoring quality gates

**Purpose:**
- prove no behavior regression and enforce Python refactoring quality constraints

**Files:**
- Modify: `tests/` (targeted config tests)
- Verify: `src/fitcv/config.py`
- Verify: `src/fitcv/config_loader.py`
- Verify: `src/fitcv/config_normalizers.py`
- Verify: `src/fitcv/config_validators.py`
- Verify: `src/fitcv/config_compat.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Add/update tests for backend resolution, prompt defaults, CV acceptance policy normalization, SSOT overlap behavior, and compatibility projections.
- [ ] Run focused pytest suite for config-related tests.
- [ ] Run full required refactor checks:
  - `uvx pytest tests/`
  - `uvx mypy src --show-error-codes`

**Verification:**
- [ ] All targeted tests pass.
- [ ] Type check passes for touched modules.

**Exit Criteria:**
- regression and type-safety evidence complete for refactor scope

### Task 5: GitNexus scope audit, docs alignment, and handoff

**Purpose:**
- confirm change scope bounded and execution artifact ready for closeout

**Files:**
- Verify: `src/fitcv/config.py`
- Verify: `src/fitcv/config_loader.py`
- Verify: `src/fitcv/config_normalizers.py`
- Verify: `src/fitcv/config_validators.py`
- Verify: `src/fitcv/config_compat.py`
- Modify: `docs/superpowers/plans/2026-05-18-15-56-config-ssot-refactor-drift-plan.md` (status/update notes as needed)

**Preconditions:**
- Task 4 complete

**Steps:**
- [ ] Run `gitnexus_detect_changes()` and compare affected symbols/flows to planned scope.
- [ ] If scope expansion appears, run additional impact checks and document disposition.
- [ ] Update execution notes/checkpoint artifacts per thread workflow.
- [ ] Prepare handoff to execution/closeout workflow with proof links.

**Verification:**
- [ ] Detect-changes output matches intended scope or deviations are explicitly accepted.
- [ ] Required artifact references and evidence paths are complete.

**Exit Criteria:**
- implementation package ready for execution closeout and commit review

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `.\scripts\get_gitnexus_freshness.ps1`
- `gitnexus_detect_changes()`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
