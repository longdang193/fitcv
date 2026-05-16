---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cv-composition-grouped-principle-contract
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-16-23-58-cv-composition-grouped-principle-contract-spec.md
targets:
  - src/fitcv/section_policy.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Implement grouped CV composition policy contract so section visibility decisions are deterministic, shared across generator/validator/UI, and principle-compliant (symmetry, invariance, equivalence).

## Key Deliverables

### Deliverable 1: Canonical grouped section-policy engine

A single policy decision surface classifies all composition sections into Group A (profile-baseline) and Group B (role-tailored/evidence-coupled), then resolves each section to exactly one effective state:

1. `hidden_by_toggle`
2. `hidden_by_ineligible_data`
3. `included`

### Deliverable 2: Generator and validator parity

CV generation section inclusion, prompt section guidance, and validator required-section checks all consume shared policy decisions with no section-specific hidden overrides outside the declared group contract.

### Deliverable 3: UI current-state equivalence

Settings composition matrix and run diagnostics expose effective state labels and omission reasons so displayed status matches runtime output contract.

### Deliverable 4: Regression-proof test coverage

Automated tests cover full 3-state behavior for both groups, including no-data and evidence-gating edge cases, with parity assertions across runtime layers.

## Task/Wave Breakdown

### Task 1: Define canonical grouped policy primitives

**Purpose:**
- establish one source of truth for group membership, eligibility rules, and effective-state resolution

**Files:**
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv/section_policy.py`
- Verify: `tests/test_validator.py`

**Preconditions:**
- parent spec accepted as implementation source
- no unresolved grouping changes pending

**Steps:**
- [x] Add explicit section-group registry for all 8 composition sections.
- [x] Add normalized policy decision object fields: `group`, `state`, `reason_code`, `required`.
- [x] Encode Group A rules (`Education`, `Languages`) using profile-meaningful-data eligibility.
- [x] Encode Group B rules with eligibility tied to section contract (selected evidence where applicable).
- [x] Keep decision outputs MECE and deterministic.

**Verification:**
- [x] Add/adjust unit tests asserting exact group partition and single-state resolution per section.

**Exit Criteria:**
- policy layer can evaluate any section with one stable decision payload

### Task 2: Align CV generation with grouped policy decisions

**Purpose:**
- remove generator-local interpretation drift and consume canonical decision payload

**Files:**
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/cv_generator.py`
- Verify: `tests/test_cv_generator.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Replace local section filtering branches with policy-driven inclusion checks.
- [x] Drive prompt section constraints and section-evidence blocks from policy outcomes.
- [x] Ensure certifications path uses shared eligibility state instead of ad hoc empty-list behavior.
- [x] Ensure Group A sections respect profile-baseline contract and reason codes.

**Verification:**
- [x] Update generator tests for ON/OFF + no-data + eligible-data scenarios across both groups.

**Exit Criteria:**
- generated template scope and prompt contract match shared policy decisions exactly

### Task 3: Align validator requiredness and missing-section logic

**Purpose:**
- enforce parity between what generator includes and what validator requires

**Files:**
- Inspect: `src/fitcv/validator.py`
- Modify: `src/fitcv/validator.py`
- Verify: `tests/test_validator.py`

**Preconditions:**
- Task 1 complete
- Task 2 behavior contract established

**Steps:**
- [x] Replace section-specific exceptions with grouped policy decision checks.
- [x] Make `Education` and `Languages` follow same Group A contract behavior.
- [x] Ensure required-section pruning relies on `state`/`required` from policy payload.
- [x] Preserve existing synthetic-row safety checks.

**Verification:**
- [x] Add parity tests that compare generator inclusion outcomes vs validator missing-section outcomes for same fixtures.

**Exit Criteria:**
- validator does not contradict generator on section presence expectations

### Task 4: Update settings UI and diagnostics for effective-state equivalence

**Purpose:**
- make control-plane status readable and truthful to runtime policy outcomes

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 policy payload includes human-readable reason/state fields

**Steps:**
- [x] Update helper text to distinguish visibility intent from effective inclusion.
- [x] Render effective `Current` labels from policy state (`Included`, `Hidden (toggle)`, `Hidden (no data)`, `Hidden (eligibility)`).
- [x] Group composition rows visually/semantically into Group A vs Group B.
- [x] Surface omission reason code in run diagnostics payload path for operator inspection.

**Verification:**
- [x] Add UI tests asserting effective-state labels and grouped section arrangement.

**Exit Criteria:**
- UI current-state text is equivalent to runtime policy state

### Task 5: End-to-end verification and contract closeout

**Purpose:**
- prove full contract compliance and prevent regression

**Files:**
- Inspect: `tests/test_cv_generator.py`
- Inspect: `tests/test_validator.py`
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Inspect: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `docs/superpowers/specs/2026-05-16-23-58-cv-composition-grouped-principle-contract-spec.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Run targeted test suites for generator, validator, settings schema, and settings UI.
- [x] Run fast validator hook and address repo-level blockers.
- [x] Capture proof mapping from acceptance criteria to test evidence.

**Verification:**
- [x] `python -m pytest tests/test_cv_generator.py tests/test_validator.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- all acceptance criteria from parent spec have concrete passing evidence

## Verification

- `python -m pytest tests/test_cv_generator.py tests/test_validator.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

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

