---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: settings-page-v3-domain-and-real-stage
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define V3 Settings IA that removes redundant selection surfaces, keeps one primary grouping axis, and aligns stage filtering with actual pipeline stages used by runtime.

## Key Deliverables

### Deliverable 1: Axis simplification contract

Single primary IA axis (`Domain`) replaces redundant `Intent Layer` surface, with consistent naming across schema, API context, and template.

### Deliverable 2: Real-stage filter contract

`Workflow Stage` filter uses actual pipeline stages (`normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, `cv_generation`) instead of lifecycle-state labels.

### Deliverable 3: Compact help and editing contract

Setting rows remain user-oriented and compact: long prose stays collapsed behind help toggles/tooltips; direct editing is available without redundant `Enable override` gate.

### Deliverable 4: Backward-compatibility and invariance contract

No backend behavior or persisted setting-key contracts change; IA is presentation and discoverability refinement only.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current V2 behavior and identify exact redundancy and stage-mismatch points

**Steps:**
- [ ] inventory current filter surfaces and identify overlap between `Intent Layer` and `Domain`
- [ ] compare current `settings_stage_filters` taxonomy against `PIPELINE_STAGE_SEQUENCE`
- [ ] map each setting key to one domain and one or more real pipeline stages
- [ ] identify rows with long prose that should be moved into compact help surfaces

**Verification:**
- [ ] coverage table shows all keys mapped without orphan keys

**Exit Criteria:**
- no V3 decision depends on ambiguous ownership or inferred stage semantics

### Wave 2: Decision closure

**Purpose:**
- finalize V3 IA and interaction model

**Steps:**
- [ ] define single primary axis label and behavior: `Domain`
- [ ] define secondary filter set from canonical pipeline stage sequence
- [ ] define row help policy: short inline summary + expandable details
- [ ] define summary-card and status-indicator behavior for modified/errors/overrides
- [ ] define compatibility rule for legacy context aliases during migration window

**Verification:**
- [ ] each user complaint maps to one explicit V3 UI contract response

**Exit Criteria:**
- V3 model is MECE, symmetric, and operationally coherent

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations explicit before plan execution

**Steps:**
- [ ] define rendering assertions for axis simplification and stage correctness
- [ ] define regression checks for save/validation behavior invariance
- [ ] define migration checks for context aliases and template bindings

**Verification:**
- [ ] validation plan proves discoverability improvement and zero behavior regression

**Exit Criteria:**
- spec is implementation-ready

## Design Decisions

### Decision: Replace Intent Layer selector with Domain selector

- context: `Intent Layer` and `Domain` currently communicate overlapping categories and create unnecessary choice count
- choice: keep one selector named `Domain`; remove separate `Intent Layer` chip set from default IA
- alternatives considered:
  - keep both selectors and improve copy only
  - keep `Intent Layer` and remove `Domain`
- impact:
  - reduces redundancy and scan friction
  - preserves single ownership path for each setting key

### Decision: Bind Workflow Stage filter to runtime pipeline stages

- context: lifecycle labels (`Setup/Draft/Review/Approved/Archived`) are not runtime stage truth and can mislead operators
- choice: stage filter derives from canonical pipeline stage sequence in runtime orchestration
- alternatives considered:
  - keep lifecycle labels as stage filter
  - show both lifecycle and runtime stage filters simultaneously
- impact:
  - strengthens semantic invariance with runtime
  - improves debugging and operational predictability

### Decision: Keep compact user-oriented rows with optional detail expansion

- context: always-visible `What/Effect/Applies when/Dependencies` prose causes vertical bloat
- choice: default compact row; move long guidance to help expander/tooltip
- alternatives considered:
  - keep full prose inline
  - hide all explanations and rely on external docs
- impact:
  - improves scannability while preserving contextual clarity

### Decision: Remove redundant override gating

- context: `Enable override` gate adds extra interaction without safety gain for normal settings edits
- choice: present editable controls directly; retain existing validation and guardrails
- alternatives considered:
  - keep explicit gate for all settings
  - only gate high-risk settings
- impact:
  - lowers interaction cost
  - keeps behavior safety anchored on backend validation

## Invariants

- Setting keys, config paths, and persistence payload contracts remain unchanged.
- Backend validation remains canonical; UI preflight checks cannot replace server validation.
- Each setting key belongs to exactly one primary domain.
- Stage-filter metadata must reflect actual runtime pipeline stage semantics.
- High-risk controls remain separated and explicitly labeled.
- Long guidance content is available contextually, not forced inline in default scan mode.

## Validation Plan

- proof target: redundant axis removed without discoverability loss
  - method: template/context inspection plus rendering tests for `Domain` selector only
  - evidence: passing tests showing filter behavior still locates all keys
- proof target: stage filter reflects canonical runtime stages
  - method: compare emitted `settings_stage_filters` IDs to `PIPELINE_STAGE_SEQUENCE`
  - evidence: automated assertion parity between UI filter IDs and runtime sequence
- proof target: compact help policy applied
  - method: template rendering tests for collapsed help surfaces and absence of always-expanded long prose
  - evidence: HTML assertions for `<details>`/tooltip patterns on rows with extended guidance
- proof target: behavior invariance preserved
  - method: existing settings save/validation test suites
  - evidence: unchanged pass/fail behavior for valid and invalid payloads

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
