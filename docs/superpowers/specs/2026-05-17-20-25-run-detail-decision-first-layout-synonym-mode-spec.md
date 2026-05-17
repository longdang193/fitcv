---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: run-detail-decision-first-layout-synonym-mode
author: codex
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_app.py
  - docs/usage.md
related_features:
  - run_lifecycle_controls
  - trigger_run_management
related_stages:
  - cv_generation
---

## Goal

Define a stable, decision-first run detail information architecture with strict SSOT ownership, fixed section order, conditional synonym-review depth, and advanced-debug relegation to end-of-page so operators can make next decisions quickly without losing audit/debug access.

## Key Deliverables

### Deliverable 1: Fixed section-order contract

Run detail page renders one canonical section order with no dynamic section reordering:

1. Header
2. Run Overview
3. Synonym Review
4. Pipeline Results
5. Event Timeline
6. Artifacts
7. Advanced & Diagnostics (collapsed)

### Deliverable 2: Synonym review conditional-depth contract

Synonym Review section keeps fixed placement but supports controlled depth states:
- `hidden`
- `summary`
- `decision_active`

`decision_active` state must surface explicit mode choices (`AI-Assisted Review`, `Manual Review`) and preserve canonical workspace entry.

### Deliverable 3: Surface deduplication and ownership boundaries

Remove duplicated/overlapping run-detail content (`Outputs`, `Run exports workspace`, duplicate overview summary) and enforce single-owner surfaces per fact.

### Deliverable 4: Advanced diagnostics simplification contract

Move all advanced/debug technical information to page end under collapsed `Advanced & Diagnostics`; remove non-working/overcomplicating diagnostic buttons.

### Deliverable 5: SSOT field/state matrix and non-regression checks

Add explicit field ownership/state visibility matrix and testable invariance/equivalence checks preventing reintroduction of duplication, dead CTAs, or section-order drift.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current run-detail duplication/overlap, route integrity, and button viability baseline

**Steps:**
- [ ] inventory current run-detail sections, order, and duplicated facts
- [ ] map existing synonym review rendering states and route behavior
- [ ] identify advanced diagnostics controls that are non-functional or redundant
- [ ] define current owner of exports/download artifacts across run detail and artifacts surfaces

**Verification:**
- [ ] baseline matrix of `section -> fields -> source -> route/action` is complete

**Exit Criteria:**
- current-state ambiguities are eliminated before redesign decisions

### Wave 2: Decision closure

**Purpose:**
- finalize layout, visibility-state, and ownership rules

**Steps:**
- [ ] lock fixed section order contract
- [ ] define synonym state transitions (`hidden|summary|decision_active`) and exact triggers
- [ ] define hard removals for overlapping/duplicated sections and dead diagnostic buttons
- [ ] define canonical route/fallback behavior for `Open Synonym Review Workspace`
- [ ] define advanced section placement and collapse-default behavior

**Verification:**
- [ ] each unresolved UX issue from operator feedback maps to one explicit rule in this spec

**Exit Criteria:**
- no major behavior remains unspecified or implementation-dependent by interpretation

### Wave 3: Validation and approval readiness

**Purpose:**
- produce implementation-ready proof requirements

**Steps:**
- [ ] define acceptance criteria and state visibility matrix
- [ ] define regression tests for section order, deduplication, and CTA validity
- [ ] define compatibility behavior for legacy links/bookmarks

**Verification:**
- [ ] validation plan covers behavior correctness, invariance, and route integrity

**Exit Criteria:**
- spec can hand off directly to implementation planning without re-brainstorming

## Design Decisions

### Decision: Fixed section order with conditional depth, not conditional position

- context: dynamic section moves increase cognitive load and create drift across runs/states
- choice: keep static section order and vary only section depth/content state
- alternatives considered:
  - dynamic insertion of Synonym Review near active step
  - per-status custom page layouts
- impact:
  - consistent operator scanning pattern
  - reduced UI complexity and test matrix size

### Decision: Synonym Review is first-class workflow section above Pipeline Results

- context: operators need predictable place for synonym workflow and mode decision
- choice: always render Synonym Review before Pipeline Results; switch between summary and decision-active content
- alternatives considered:
  - keep synonym details fully off-page in dedicated route only
  - place synonym section below timeline when inactive
- impact:
  - workflow discoverability improves
  - summary mode remains compact for non-decision stages

### Decision: Artifacts is sole owner for outputs/exports

- context: `Outputs`, `Run exports workspace`, and Artifacts currently overlap
- choice: remove overlapping cards and keep only Artifacts as file/export owner
- alternatives considered:
  - retain outputs summary card with duplicate download actions
  - split export ownership by file type
- impact:
  - single source for downloads/exports
  - lower operator ambiguity

### Decision: Advanced diagnostics moved to end and simplified

- context: technical controls and debug cards compete with decision flow
- choice: move debug-heavy content after timeline, collapsed by default, remove dead/non-working advanced buttons
- alternatives considered:
  - keep advanced split across multiple mid-page cards
  - keep buttons disabled with explanatory tooltips
- impact:
  - reduced clutter in primary flow
  - preserves audit/debug access with explicit progressive disclosure

### Decision: Canonical synonym workspace route and fallback contract

- context: `Open full workspace` currently fails in some states
- choice: use canonical route `/admin/runs/{run_id}/synonym-review` with deterministic fallback messaging
- alternatives considered:
  - anchor-only navigation to inline subsection
  - route + opaque redirect chain
- impact:
  - predictable navigation
  - fewer broken CTA paths

## Invariants

- one fact has one owner surface (SSOT ownership)
- run detail section order is static across run states
- Synonym Review placement remains above Pipeline Results
- Artifacts is the only run-detail surface owning exports/download workflows
- Event Timeline remains the primary chronological audit surface
- Advanced & Diagnostics is last and collapsed by default
- visible buttons must map to working routes/actions; no dead CTAs
- synonym mode selector appears only in `decision_active` state
- counts/status rendered in summary sections remain equivalent to canonical backing records

## Acceptance Criteria

- page renders exactly one `Run Overview` block
- `Outputs` and `Run exports workspace` are absent from run detail
- `Synonym Review` section is rendered above `Pipeline Results` for all states where shown
- when run enters synonym decision state, `AI-Assisted Review` and `Manual Review` options appear in Synonym Review
- `Open Synonym Review Workspace` navigates to canonical route successfully
- `Artifacts` appears after Event Timeline and contains export/download ownership
- advanced diagnostics appears only after Artifacts, collapsed by default
- advanced quick buttons listed as removals are not rendered

## Non-Goals

- redesigning artifacts detail page IA beyond ownership move from run detail
- changing underlying pipeline stage semantics or synonym proposal decision logic
- adding new orchestration backends or queue semantics
- revising telemetry schema beyond run-detail presentation and access ordering

## Risks and Mitigations

- risk: hidden diagnostics may reduce discoverability for expert users
  - mitigation: add clear `View Advanced Diagnostics` affordance and preserve deep-link anchors where valid
- risk: moving exports to Artifacts may break operator muscle memory
  - mitigation: add transitional helper text in run detail and maintain route redirects where feasible
- risk: synonym-state trigger mismatch can show wrong mode controls
  - mitigation: define explicit backend flag contract and add state-matrix tests
- risk: stale bookmarked links to removed sections
  - mitigation: provide compatibility redirects or inline “moved to Artifacts/Advanced” notices

## Validation Plan

- proof target: fixed section order is preserved
  - method: template render assertions and UI snapshot checks
  - evidence: tests assert ordered occurrence of section markers in run detail HTML

- proof target: duplicated/overlapping sections are removed
  - method: regression assertions against removed labels/IDs
  - evidence: tests fail if `Outputs` or `Run exports workspace` sections reappear

- proof target: synonym mode options appear only in decision-active state
  - method: state-driven route render tests using representative fixtures
  - evidence: tests confirm selector present in decision-active and absent otherwise

- proof target: synonym workspace CTA is functional
  - method: route test for `/admin/runs/{run_id}/synonym-review` plus fallback case
  - evidence: HTTP success for valid route; deterministic message for unavailable state

- proof target: artifacts ownership boundary holds
  - method: render + route scope assertions
  - evidence: export/download actions present in Artifacts surface only

- proof target: advanced diagnostics placement and collapse default hold
  - method: template structure inspection and initial-state assertions
  - evidence: advanced block appears after timeline/artifacts and renders collapsed

- proof target: invariance/equivalence across summary and canonical records
  - method: data consistency assertions for status/count fields
  - evidence: tests comparing overview/synonym summary values against canonical run payloads

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
