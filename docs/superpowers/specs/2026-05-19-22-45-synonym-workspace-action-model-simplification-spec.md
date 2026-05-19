---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: synonym-workspace-action-model-simplification
parent_thread: workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_fitcv_cp/test_app.py
related_features:
  - admin_control_plane_core
related_stages:
  - enrich
---

## Goal

Eliminate Synonym Workspace UX drift by making it single-home, action-coherent, and mode-consistent so operators can review, decide, and promote without route jumps, duplicated controls, or ambiguous state.

## Key Deliverables

### Deliverable 1: Single-home navigation contract

All synonym workspace actions return to `/admin/runs/{run_id}/synonym-review` (or stay on promote preview) unless user explicitly clicks back to run detail.

### Deliverable 2: Simplified action surface

Workspace exposes one decision lane, one AI assist action, one promote lane, and one actor input source without redundant parallel controls.

### Deliverable 3: Deterministic feedback contract

All action outcomes are surfaced as workspace-local info/result banners with stable query keys and no raw JSON/HTTP exception pages for expected operator states.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- map current workspace flows and identify drift/redundancy boundaries

**Steps:**
- [ ] inventory synonym routes and redirect targets in `src/fitcv_cp/app.py`
- [ ] inventory workspace controls and client-side mode behavior in `src/fitcv_cp/templates/synonym_review.html`
- [ ] classify duplicate capabilities (batch vs per-row vs AI mode toggles)
- [ ] confirm blast radius with GitNexus CLI (`context`, `impact`) as advisory due stale index

**Verification:**
- [ ] route/control inventory contains every operator action from workspace

**Exit Criteria:**
- drift causes and redundant UI paths are explicit and bounded

### Wave 2: Decision closure

**Purpose:**
- resolve final UX/action contract and route behavior

**Steps:**
- [ ] define redirect matrix for each synonym action endpoint
- [ ] define simplified workspace action model
- [ ] define promote preview/commit behavior for empty/blocked/success cases
- [ ] define run detail role (summary-only vs interactive control host)

**Verification:**
- [ ] each action has one primary trigger path and one deterministic return path

**Exit Criteria:**
- no action requires contextual page switching to complete normal operator flow

### Wave 3: Validation and approval readiness

**Purpose:**
- produce testable acceptance gates and regression proof shape

**Steps:**
- [ ] define targeted test cases for redirect destinations, banner rendering, and control visibility
- [ ] define compatibility checks for existing query-param summaries
- [ ] define rollback-safe boundaries (no semantic change to proposal status transitions)

**Verification:**
- [ ] validation plan proves behavior and UX contract invariants

**Exit Criteria:**
- spec ready for implementation planning and patch execution

## Design Decisions

### Decision: Synonym Workspace is single interactive surface

- context: recent drift came from mixed redirects between workspace and run detail
- choice: all synonym review actions redirect back to workspace; run detail remains summary and entrypoint only
- alternatives considered:
  - keep mixed redirects and add more banners to run detail
  - move all synonym controls to run detail and retire workspace
- impact:
  - removes context switching
  - lowers drift risk between two control surfaces
  - keeps current `/synonym-review` deep-link valid

### Decision: Remove redundant decision controls

- context: same mutation is currently available via batch dropdown + per-row instant buttons + mode toggles
- choice: keep batch dropdown + single submit as canonical decision mutation path; deprecate per-row instant action buttons
- alternatives considered:
  - keep both batch and per-row actions
  - keep only per-row actions, remove batch
- impact:
  - fewer competing controls
  - easier test matrix
  - clearer operator mental model for staged decisions

### Decision: AI assist is explicit action, not pseudo-mode

- context: AI/Manual toggle currently only mutates local select values and creates false mode semantics
- choice: replace mode concept with explicit `Apply AI Recommendations` action that only pre-fills empty decisions
- alternatives considered:
  - keep mode toggle and document limitation
  - make real backend-persisted mode
- impact:
  - aligns UI label with actual behavior
  - avoids implied persistent state that does not exist

### Decision: Workspace-only status messaging contract

- context: user-facing info appears in multiple pages, causing drift and confusion
- choice: synonym action result banners render in workspace; run detail keeps only high-level historical summary blocks
- alternatives considered:
  - duplicate all status messages in both pages
  - remove all query-based banners
- impact:
  - deterministic feedback location
  - less template drift

### Decision: Guard expected no-op/error states with info banners

- context: expected operator states (no approved rows, unchanged global pairs) previously leaked as raw error views or confusing counters
- choice: convert expected states to handled redirects + info banners in workspace/promotion preview
- alternatives considered:
  - preserve raw HTTPException responses for all states
  - suppress feedback entirely on no-op
- impact:
  - operator-safe UX
  - preserves backend status codes for true invalid/server states only

## Invariants

- Synonym proposal status transitions remain unchanged (`approve_for_run_overlay`, `defer`, `reject` semantics unchanged).
- Promote-to-global remains merge/overlay behavior, never full replacement.
- No expected operator path renders raw JSON/exception page.
- Workspace remains cache-disabled (`no-store`) to reflect latest proposal state.
- Run detail remains accessible as summary page and manual navigation target.

## Acceptance Criteria

- Every POST action triggered from Synonym Workspace returns to workspace or promote preview (never forced jump to run detail for normal flow).
- Workspace shows exactly one canonical decision mutation lane.
- AI assist is exposed as explicit action, not persistent mode.
- Promote preview no-approved state shows info banner in workspace.
- Existing global-promotion summary semantics remain intact (`new_aliases`, `unchanged_aliases`, `overridden_aliases`).

## Non-Goals

- No redesign of synonym scoring/recommendation model quality.
- No change to global synonym YAML schema or storage backend.
- No rewrite of run detail page architecture outside synonym drift cleanup.
- No migration to SPA/state-store architecture.

## Risks and Mitigations

- Risk: users relying on per-row instant buttons lose quick path.
  - Mitigation: retain keyboard-friendly dropdown + submit; optional follow-up quick-action shortcut in separate approved change.
- Risk: query-param banner contract drift with existing tests.
  - Mitigation: add explicit redirect/banners tests before removing old controls.
- Risk: stale GitNexus index can mislead call graph trust.
  - Mitigation: treat GitNexus advisory-only; source/tests are authoritative.

## Validation Plan

- proof target: all workspace actions return to correct page
  - method: route-level tests for each POST endpoint redirect `Location`
  - evidence: `tests/test_fitcv_cp/test_app.py` assertions for `/synonym-review` or preview route

- proof target: redundant decision controls removed without behavior regression
  - method: template render tests + targeted UI string assertions
  - evidence: test assertions for removed per-row forms and presence of canonical batch actions

- proof target: expected no-op states show info banners
  - method: endpoint tests for no-approved/no-op promote flows
  - evidence: response body contains info banner text, no raw JSON detail page

- proof target: synonym transition semantics preserved
  - method: existing approve/defer/reject/promotion tests rerun
  - evidence: pass results from targeted pytest selection

- proof target: repo contract health unchanged
  - method: run validator hook
  - evidence: `python scripts/hooks/run_validator.py --fast` pass output

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
