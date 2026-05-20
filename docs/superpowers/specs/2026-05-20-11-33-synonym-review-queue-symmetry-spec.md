---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: synonym-review-queue-symmetry
parent_workstream: none
targets:
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/_cv_review_queue.html
  - src/fitcv_cp/app.py
related_features:
  - none
related_stages:
  - none
---

## Goal

Define symmetric, explicit, and reversible operator interaction model for Synonym Review so it matches Agentic Review Queue selection semantics, removes deferred-row dead ends, and adds a dedicated Review Promote to Global workbench page.

## Key Deliverables

### Deliverable 1: Unified selection contract for review queues

Specify shared interaction contract for queue-like admin surfaces:
- row checkbox selection
- select all / clear all
- selected count
- explicit batch apply action over selected ids

### Deliverable 2: Synonym decision state transition clarity

Specify allowed row actions and state transitions for synonym proposals, including explicit reopen path for deferred decisions.

### Deliverable 3: Promote-preview behavior alignment

Specify promote-preview preconditions and user-facing responses so operator sees deterministic outcomes when no approved/promotable rows exist.

### Deliverable 4: Dedicated Review Promote to Global page

Specify a dedicated promote-review surface that clearly separates:
- rows ready for promotion
- rows already present in global synonyms
- rows blocked by conflicts or invalid status

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current asymmetry and affected boundaries before design choice

**Steps:**
- [ ] map Agentic queue UX + batch contract (`job_url[]` selection)
- [ ] map Synonym queue UX + batch contract (`proposal_action__<id>` pending-only controls)
- [ ] map promote preview fallback behavior when selected set absent

**Verification:**
- [ ] asymmetry documented with concrete file/symbol references

**Exit Criteria:**
- no design claim depends on unstated UI or backend behavior

### Wave 2: Decision closure

**Purpose:**
- resolve target interaction model and state machine boundaries

**Steps:**
- [ ] define shared queue interaction invariants
- [ ] define synonym row selectability and action transition matrix
- [ ] define dedicated promote-review page route, grouped sections, and commit contract

**Verification:**
- [ ] all major design questions have explicit decision

**Exit Criteria:**
- design internally coherent and bounded to review-surface behavior

### Wave 3: Validation and approval readiness

**Purpose:**
- make implementation proof obligations explicit

**Steps:**
- [ ] define acceptance criteria with observable UI/API evidence
- [ ] define regression checks against Agentic queue behavior
- [ ] define non-goals to prevent scope creep into unrelated pipeline logic

**Verification:**
- [ ] validation plan can prove symmetry without ambiguous interpretation

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Adopt shared `SelectableReviewQueue` interaction contract

- context: Agentic queue already uses explicit multi-select contract; Synonym queue uses pending-only implicit row form controls, causing operator confusion and non-recoverable deferred state handling.
- choice: Synonym Review must adopt same top-level interaction primitives as Agentic queue: checkbox selection, select all, clear all, selected count, batch apply to selected rows.
- alternatives considered:
  - keep pending-only row dropdown model and add helper copy
  - auto-include deferred rows invisibly in batch endpoint
- impact:
  - UI symmetry across admin review surfaces
  - reduced hidden behavior
  - shared mental model for operators

### Decision: Expand synonym batch endpoint input shape to explicit selected ids

- context: current synonym batch action resolves rows from populated pending dropdown fields, not explicit selected identity set.
- choice: batch submission contract must include explicit `proposal_id[]` selected rows and a single batch action value, parallel to CV queue `job_url[]` model.
- alternatives considered:
  - infer selected rows from non-empty action fields only
  - keep per-row mixed actions with no selection requirement
- impact:
  - deterministic server-side selection scope
  - clearer error reporting (`422` when selected set empty)
  - easier regression testing

### Decision: Add explicit `reopen_pending` transition for deferred rows

- context: deferred synonym rows currently become non-pending and lose actionable controls in UI.
- choice: allow deferred rows to be selected and moved back to pending via explicit batch action (`reopen_pending`), then re-reviewed.
- alternatives considered:
  - allow direct approve/reject from deferred without reopen
  - keep deferred terminal until regenerate
- impact:
  - removes dead-end workflow
  - keeps audit trail explicit (`defer -> reopen -> next decision`)

### Decision: Promote preview must operate on explicit approved subset only

- context: promote preview currently supports implicit fallback selection when request has no selected ids; user may perceive no-op behavior.
- choice: introduce dedicated route `GET /admin/runs/{run_id}/synonym-proposals/promote-review` as promote workbench. Workbench consumes explicit selected ids (or explicit “select approved” UI action before submit). If no approved selected rows exist, return visible status banner with counts and actionable guidance.
- alternatives considered:
  - keep implicit server fallback over all approved rows
  - auto-open preview with all approved rows unconditionally
- impact:
  - transparent operator intent
  - less surprising outcomes

### Decision: Promote workbench must expose grouped review sections

- context: operators need clear distinction between actionable promotions and rows already globally present.
- choice: page groups rows into:
  - `Ready to Promote`: approved rows with `diff_type in {add, update}`
  - `Already Global (No Change)`: approved rows with `diff_type=skip` and reason `already_present`
  - `Blocked/Conflict`: rows with `diff_type=conflict` or non-promotable reasons
- alternatives considered:
  - single flat table with status filter only
  - separate pages for each section
- impact:
  - faster operator comprehension
  - explicit auditability of why rows are/are not promotable

## Invariants

- Synonym Review and Agentic Review Queue keep equivalent top-level selection semantics.
- Batch actions never apply to rows outside explicit selected identity set.
- Deferred synonym rows remain reversible by explicit operator action.
- Promote review never silently mutates selection scope.
- Promote workbench clearly separates promotable vs already-global vs blocked rows.
- Existing run data model and proposal payload schema remain backward compatible unless version bump explicitly planned.

## Acceptance Criteria

- Synonym Review page shows row checkboxes, Select All, Clear All, and Selected count for actionable proposal rows.
- Submitting batch action with zero selected rows returns operator-visible error.
- Deferred rows can be selected and reopened to pending state.
- Dedicated `Review Promote to Global` page exists and renders grouped sections for ready/already-global/blocked.
- Promote review submission provides deterministic status when no approved rows selected.
- Agentic Review Queue behavior remains unchanged.

## Non-Goals

- No changes to synonym generation heuristics or recommendation model scoring.
- No changes to global synonym persistence format.
- No changes to CV generation or ranking logic.
- No redesign of full admin styling system.
- No introduction of asynchronous background promotion jobs in this change.

## Risks and Mitigations

- Risk: Transition-matrix mismatch introduces invalid state changes.
  - Mitigation: enforce server-side allowed transitions and add explicit 422 reasons.
- Risk: UI parity changes regress existing operator habits.
  - Mitigation: keep current row-level quick actions where safe; add clear helper text for new batch path.
- Risk: stale GitNexus index yields incomplete dependency view.
  - Mitigation: treat GitNexus outputs advisory; verify against source and targeted tests.

## Validation Plan

- proof target: Synonym Review selection semantics match Agentic queue semantics
  - method: template inspection + browser interaction test
  - evidence: updated template sections and recorded manual test steps with screenshots
- proof target: Batch action scope restricted to explicit selected ids
  - method: endpoint test (selected subset vs non-selected control rows)
  - evidence: targeted test logs asserting only selected proposal ids changed
- proof target: Deferred rows can be reopened and re-decided
  - method: integration test over proposal status transitions
  - evidence: event ledger entries showing `deferred -> pending -> approve|reject|defer`
- proof target: Promote preview failure modes are explicit and deterministic
  - method: endpoint tests for promote-review no-selected, no-approved, no-promotable cases
  - evidence: response status/query flags and rendered status banners
- proof target: Promote workbench section grouping is correct
  - method: fixture-based inspection test for grouped counts and row membership by `diff_type/reason`
  - evidence: test assertions for Ready to Promote, Already Global, and Blocked sections

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. implementation plan references this spec and preserves stated invariants
