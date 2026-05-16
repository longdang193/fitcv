---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cv-composition-grouped-principle-contract
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv/section_policy.py
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

Define one explicit, principle-compliant contract for CV composition section visibility so UI states, generation behavior, and validation decisions are symmetric, invariant, and equivalent under a grouped policy model.

## Key Deliverables

### Deliverable 1: Two MECE section groups with explicit semantics

Section visibility semantics are split into two non-overlapping groups:

- Group A (profile-baseline): `Education`, `Languages`
- Group B (role-tailored/evidence-coupled): `Summary`, `Experience`, `Skills`, `Certifications`, `Projects`, `Publications`

Each group has one explicit state model and no hidden special-case behavior outside that model.

### Deliverable 2: Canonical decision-state algebra

All sections map to exactly one terminal runtime state:

1. hidden_by_toggle
2. hidden_by_ineligible_data
3. included

No section can occupy multiple states at once, and every section always occupies one state.

### Deliverable 3: UI/runtime equivalence contract

Settings UI "Current" value reflects effective runtime state instead of raw toggle-only status, with reason-bearing labels where needed.

### Deliverable 4: Generator-validator-policy symmetry

Prompt construction, template filtering, section rendering, and validation all consume the same section-policy decision object so no layer silently reinterprets inclusion logic.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current section policy divergence before contract changes

**Steps:**
- [ ] inventory current inclusion logic across settings UI, generator, validator, and section policy helpers
- [ ] document current exceptions (`Certifications` evidence gate, `Education` validator skip behavior)
- [ ] identify equivalence breaks between displayed "Included/Hidden" and final CV output

**Verification:**
- [ ] each divergence is traceable to concrete source locations

**Exit Criteria:**
- no design decision depends on unstated behavior assumptions

### Wave 2: Grouped contract closure

**Purpose:**
- close policy ambiguity using grouped principle contract

**Steps:**
- [ ] define Group A and Group B state semantics as normative contract
- [ ] define canonical decision function outputs and reason codes
- [ ] align UI current-state labels to effective decision states
- [ ] remove hidden one-off section behavior outside declared group policy

**Verification:**
- [ ] every section maps to one group and one deterministic state machine

**Exit Criteria:**
- no section-specific inclusion behavior remains undocumented or implicit

### Wave 3: Validation and approval readiness

**Purpose:**
- prove principle compliance and regression safety

**Steps:**
- [ ] add/update tests for all 3 states per section group
- [ ] validate UI current-state text against runtime output and validator outcomes
- [ ] confirm policy payload appears in run artifacts for operator debugging

**Verification:**
- [ ] acceptance criteria have concrete evidence paths

**Exit Criteria:**
- spec is implementation-plan ready with no unresolved policy ambiguity

## Design Decisions

### Decision: Adopt grouped semantics instead of one global section rule

- context: current behavior already diverges (`Education` and `Certifications` do not follow uniform semantics)
- choice: codify two explicit groups with stable per-group rules
- alternatives considered:
  - force one strict global toggle rule for all sections
  - preserve current mixed behavior and only improve docs
- impact:
  - preserves meaningful domain distinctions while eliminating hidden logic
  - improves operator predictability and debugging speed

### Decision: Make effective state first-class in UI and artifacts

- context: raw toggle display creates false equivalence with final output
- choice: expose effective state and omission reason directly
- alternatives considered:
  - keep current UI labels and rely on run logs only
  - add only warning text without state model
- impact:
  - restores equivalence principle across UI, runtime, and validation
  - reduces confusion during review-required and validation-failed runs

### Decision: Unify policy consumption in one decision layer

- context: generator and validator currently apply partially different section logic
- choice: define canonical section-policy decision object consumed by both layers
- alternatives considered:
  - patch each callsite independently
  - validator-only alignment
- impact:
  - enforces symmetry and invariance by construction
  - lowers future regression risk

## Invariants

- each section belongs to exactly one policy group
- each section resolves to exactly one terminal decision state (`hidden_by_toggle`, `hidden_by_ineligible_data`, `included`)
- effective UI current state equals runtime section decision state
- generator inclusion behavior and validator requiredness decisions are derived from the same policy result
- omission reasons are explicit and machine-readable when a section is not included

## Acceptance Criteria

- all 8 composition sections are assigned to exactly one of two groups with no overlap
- Group A (`Education`, `Languages`) shares one profile-baseline inclusion contract
- Group B sections share one role-tailored/evidence-coupled inclusion contract
- settings page no longer claims "Included" when runtime policy would omit the section
- validator missing-section checks match generator section-inclusion outcomes for all section states
- tests cover all three decision states for both groups, including no-data edge cases

## Non-Goals

- redesigning CV content quality heuristics unrelated to section visibility contract
- changing ranking/enrichment selection logic outside section-policy inputs
- broad settings-page visual redesign beyond state/label clarity needed for contract compliance
- modifying unrelated planning/governance documents

## Risks and Mitigations

- risk: grouped semantics introduce migration confusion for existing operators
  - mitigation: add concise policy matrix in settings help text and run-detail diagnostics
- risk: legacy tests assume raw toggle implies inclusion
  - mitigation: replace/extend tests with effective-state assertions tied to policy output
- risk: partial rollout leaves generator and validator out of sync
  - mitigation: require shared policy function and parity tests before closure

## Validation Plan

- proof target: section grouping is MECE and complete
  - method: static inspection and schema-level assertions
  - evidence: test cases asserting exact partition membership for all composition sections

- proof target: symmetry across generator and validator
  - method: paired behavior tests using identical policy inputs
  - evidence: passing tests where section presence and requiredness outcomes match state contract

- proof target: invariance under repeated runs with same inputs
  - method: deterministic replay of policy decisions
  - evidence: identical effective state outputs for repeated same-input fixtures

- proof target: equivalence between UI current-state and runtime output
  - method: integration checks for settings page + generated CV/validation outcome
  - evidence: tests proving displayed "Current" state equals effective policy result and final section presence

- proof target: operator-debug visibility for omitted sections
  - method: run artifact inspection
  - evidence: policy decision payload with omission reason codes present in stage artifacts

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
