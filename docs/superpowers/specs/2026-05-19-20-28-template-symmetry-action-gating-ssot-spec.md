---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: template-symmetry-action-gating-ssot
parent_workstream: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
targets:
  - src/fitcv_cp/templates/_cv_review_queue.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/base.html
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - settings_system
  - inspection_debugging
related_stages:
  - cv_generation
  - enrich
---

## Goal

Patch template-level symmetry/SSOT drift in control-plane decision surfaces so UI actionability, decision state rendering, and decision-mode controls are structurally consistent across run detail, review queue, and synonym workspace.

## Key Deliverables

### Deliverable 1: Resolved-state action gating contract

Resolved rows in review surfaces render as non-actionable everywhere; pending rows render actionable controls everywhere.

### Deliverable 2: Decision-control visual symmetry contract

Equivalent decision controls (`AI-Assisted Decide + Promote`, `Manual Decide + Promote`) use one visual/state contract independent of element type and page context.

### Deliverable 3: Reusable decision-toggle component behavior

Decision-mode controls expose explicit active/inactive state via shared attributes/classes and consistent interaction semantics.

### Deliverable 4: Regression-proof verification coverage

Template + route tests assert no state/action mismatch and no cross-page decision-control style drift for in-scope surfaces.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm all current state/action mismatches and style-contract drift points

**Steps:**
- [ ] enumerate all in-scope template controls with pending/resolved semantics
- [ ] map element-type and class differences across equivalent controls
- [ ] confirm backend guardrails vs UI affordance drift

**Verification:**
- [ ] violation matrix includes exact file + line references and state contract deltas

**Exit Criteria:**
- no proposed patch relies on assumptions not proven in source templates/routes

### Wave 2: Decision closure

**Purpose:**
- lock one canonical UI contract for action gating and decision-mode controls

**Steps:**
- [ ] define resolved-row lock behavior and pending-row action behavior
- [ ] define one decision-toggle style/state contract for run detail + workspace
- [ ] define minimal template refactor boundaries and shared helper class usage

**Verification:**
- [ ] each control in scope maps to exactly one canonical contract row

**Exit Criteria:**
- no duplicate or conflicting control semantics remain in design

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof targets explicit before implementation planning

**Steps:**
- [ ] define template rendering proof targets for pending/resolved rows
- [ ] define UI parity proof targets for AI/manual decision controls
- [ ] define regression test additions and expected assertions

**Verification:**
- [ ] validation plan can fail if any symmetry/SSOT drift reappears

**Exit Criteria:**
- spec can hand off directly to implementation planning without ambiguity

## Design Decisions

### Decision: Resolved review items must be interaction-locked in-template

- context: `_cv_review_queue.html` shows resolved badge but still renders live action buttons
- choice: gate per-row action forms behind `item.pending`; resolved rows render locked status note only
- alternatives considered:
  - keep buttons visible and rely on backend 409
  - disable buttons via client JS only
- impact:
  - removes misleading affordance drift
  - aligns rendered affordance with run-state truth

### Decision: Decision-mode controls use a shared stateful toggle contract

- context: run detail and workspace use mixed element types and inconsistent active styling
- choice: enforce a shared `decision-toggle` contract (`class + data-active + disabled`) for both pages
- alternatives considered:
  - keep mixed anchor/button forms and patch CSS ad hoc
  - migrate all to links only
- impact:
  - preserves endpoint semantics while normalizing visual state and interaction behavior

### Decision: No duplicate manual-entry controls with overlapping intent

- context: run detail surfaces both `Manual Decide + Promote` and `Open Synonym Workspace`
- choice: collapse to one canonical manual-entry control with unambiguous wording
- alternatives considered:
  - keep both controls and document difference text-only
- impact:
  - reduces cognitive ambiguity and prevents control-surface divergence

### Decision: SSOT for mode state lives in template attributes, not implicit CSS behavior

- context: workspace JS updates helper text but not active-state attributes
- choice: mode switch JS updates `data-active` on both controls and maintains deterministic state
- alternatives considered:
  - rely on hover/focus and text message only
- impact:
  - deterministic UI state and testable contract

## Invariants

- a row marked `resolved` must not expose actionable per-row decision controls
- a row marked `pending` must expose actionable controls unless explicitly disabled by policy
- equivalent decision controls across run detail and synonym workspace must share style/state contract
- decision-mode active state must be machine-observable (`data-active`) and testable
- backend guardrails remain authoritative; UI must not advertise actions known to be non-actionable

## Acceptance Criteria

1. in review queue templates, resolved rows render no live action forms/buttons for approve/regenerate/reject.
2. pending rows still render actionable controls and batch selection paths.
3. run detail and synonym workspace decision toggles render same control class/state contract.
4. one manual-entry control remains on run detail for synonym workspace path.
5. automated tests fail if resolved rows regain actionable controls or if cross-page decision-control parity regresses.

## Non-Goals

- changing decision policy logic (approve/defer/reject semantics)
- changing queue orchestration or checkpoint backend behavior
- redesigning broader admin UI theme, spacing, or typography system
- introducing new workflow modes outside current `run_all` and `manual_staged`

## Risks and Mitigations

- risk: over-gating hides useful troubleshooting controls for resolved rows
  - mitigation: keep non-action metadata visible (`last action`, timestamps, preview)
- risk: style unification breaks other button contexts
  - mitigation: scope new contract classes to synonym/review controls only
- risk: mixed anchor/button semantics require endpoint-specific handling
  - mitigation: preserve HTTP method semantics; normalize class/state layer only

## Validation Plan

- proof target: resolved rows are non-actionable in review queue
  - method: template render test with resolved queue items
  - evidence: `tests/test_fitcv_cp/test_app.py` assertion absence of per-row action form elements for resolved rows

- proof target: pending rows remain actionable
  - method: template render test with pending queue items
  - evidence: assertion presence of per-row action form elements and batch-select checkbox

- proof target: cross-page decision-control parity
  - method: render run detail + synonym workspace and compare required class/state attributes
  - evidence: assertions for identical `decision-toggle` contract markers

- proof target: active mode state updates deterministically
  - method: JS behavior test or server-render contract + minimal DOM assertion
  - evidence: `data-active` state changes observed for AI/manual controls

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
