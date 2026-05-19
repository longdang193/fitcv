---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: agentic-review-queue-routing-and-selection
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# 2026-05-19 Agentic Review Queue Routing + Select-All Spec

## Goal
Define UX and behavioral contract for Agentic Review Queue routing and bulk selection so operators can decide faster with fewer clicks while preserving existing audit-safe action semantics.

## Key Deliverables

### Deliverable 1: Queue routing contract
A deterministic visibility rule that keeps small review sets inline in run detail and routes larger sets to a dedicated queue surface.

### Deliverable 2: Batch selection interaction contract
A stable Select-All/Clear-All pattern for review-required rows that works with existing batch endpoints and selection-based action scope.

### Deliverable 3: Terminology clarity contract
Operator-facing wording updates that remove ambiguity around batch scope and individual review mode.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current queue behavior, route wiring, and test coverage boundaries before changing UX contract

**Steps:**
- [ ] inspect run-detail queue markup and batch form wiring in `src/fitcv_cp/templates/run_detail.html`
- [ ] inspect CV review action routes in `src/fitcv_cp/app.py`
- [ ] inspect current queue UI assertions in `tests/test_fitcv_cp/test_app.py`
- [ ] confirm GitNexus index freshness and exploration context for cross-file impact awareness

**Verification:**
- [ ] current-state contract is explicit for routing threshold, selection mechanics, and button copy

**Exit Criteria:**
- no proposed UX decision depends on unstated template or route assumptions

### Wave 2: Decision closure

**Purpose:**
- close UX and behavior decisions for queue routing and bulk selection with minimal refactor risk

**Steps:**
- [ ] finalize threshold decision (`pending_count > 5` routes to dedicated page CTA)
- [ ] finalize Select-All/Clear-All interaction model for visible rows
- [ ] finalize wording set for batch vs one-by-one review
- [ ] define minimal reuse strategy (shared partial for queue body across run detail and dedicated page)

**Verification:**
- [ ] each major UX decision has explicit rationale and downstream implementation boundary

**Exit Criteria:**
- design is bounded, symmetric, and implementation-plan ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof expectations and regression checks for safe handoff

**Steps:**
- [ ] define template-level assertions for threshold and button visibility
- [ ] define form behavior checks for Select-All/Clear-All scope
- [ ] define wording regression assertions

**Verification:**
- [ ] validation plan proves routing behavior and selection behavior without lifecycle regressions

**Exit Criteria:**
- spec is approved or ready for implementation planning

## Design Decisions

### Decision: Threshold-based routing with inline-first default

- context: run detail currently contains full Agentic Review Queue UI, which is efficient for small sets but visually heavy for large queues.
- choice: keep inline queue for `pending_count <= 5`; switch to compact summary + dedicated-queue CTA when `pending_count > 5`.
- alternatives considered:
  - always-inline only (rejected: poor scanability for larger runs)
  - always-dedicated only (rejected: extra navigation cost for small queues)
- impact:
  - preserves current low-friction path for most runs
  - introduces scalable path for high-volume review runs

### Decision: Select-All/Clear-All controls scoped to visible selectable rows

- context: existing batch flow requires manual checkbox-by-checkbox selection.
- choice: add explicit `Select All` and `Clear All` controls that toggle only rows currently rendered and eligible in queue card/page.
- alternatives considered:
  - single tri-state master checkbox only (deferred: higher implementation complexity and edge-case messaging)
  - global select across hidden/filtered rows (rejected: ambiguous scope, audit risk)
- impact:
  - faster operator throughput
  - clear selection scope aligned to visible rows and current form submission

### Decision: Wording normalization for action scope clarity

- context: existing labels contain ambiguity and typo risk for decision mode.
- choice:
  - replace `Apply To Selected` with `Apply to Selected Jobs`
  - replace ambiguous mode text with `Review One by One`
  - use `Apply One Action to Selected Jobs` for batch-mode explanation
- alternatives considered:
  - keep legacy labels (rejected: lower clarity)
- impact:
  - reduces operator misclick/misread risk
  - improves consistency across inline and dedicated surfaces

### Decision: Structural symmetry via shared queue partial

- context: same queue semantics should not diverge between run detail and dedicated queue page.
- choice: extract queue body into shared template partial; mount with context-specific shell (inline vs dedicated).
- alternatives considered:
  - duplicate markup in two templates (rejected: drift risk)
- impact:
  - single source of UX truth
  - easier regression testing and copy consistency

## Invariants

- CV review action semantics and audit trail remain unchanged; this spec changes presentation/routing and selection affordances only.
- Batch actions apply only to explicit selected `job_url` values in request payload.
- Selection helpers must not auto-submit or auto-apply actions.
- Routing threshold must be deterministic and derived from queue state (`pending_count`).
- Inline and dedicated queue surfaces must share identical per-row decision controls and action meanings.

## Acceptance Criteria

1. When `pending_count <= 5`, run detail renders inline review rows and no forced navigation to dedicated queue.
2. When `pending_count > 5`, run detail shows queue summary + CTA to dedicated review queue page.
3. Queue UI exposes `Select All` and `Clear All` controls; `Select All` checks all visible selectable rows, `Clear All` unchecks all.
4. Batch submit uses only checked row `job_url` values.
5. Updated wording appears in UI:
   - `Apply One Action to Selected Jobs`
   - `Apply to Selected Jobs`
   - `Review One by One`
6. Existing single-row actions (`Accept Draft As Final CV`, `Regenerate Once`, `Reject`) remain available and unchanged in semantics.

## Non-Goals

- No change to review lifecycle transition rules, run status transitions, or closure gating logic.
- No change to underlying `cv-review-action` or `cv-review-batch-action` payload contracts.
- No new moderation policy or auto-approval logic.
- No redesign of markdown preview quality checks or synonym review surfaces.

## Risks and Mitigations

- Risk: threshold logic causes inconsistent visibility between inline and dedicated states.
  - Mitigation: centralize threshold check in one helper/context variable used by template rendering.
- Risk: Select-All scope confusion when future filtering/search is added.
  - Mitigation: explicitly label scope as visible rows; keep controls adjacent to selection context text.
- Risk: wording drift between inline and dedicated pages.
  - Mitigation: shared partial with common labels and tests asserting exact strings.
- Risk: accidental behavior drift from duplicated markup.
  - Mitigation: enforce partial extraction before adding dedicated page shell.

## Validation Plan

- proof target: threshold routing behavior is deterministic at boundary values
  - method: route/template tests with `pending_count` values `5` and `6`
  - evidence: assertions in `tests/test_fitcv_cp/test_app.py` for inline vs summary/CTA rendering

- proof target: Select-All/Clear-All controls toggle visible row checkboxes correctly
  - method: template/DOM-level behavior test or server-side rendered-control presence + JS unit coverage where available
  - evidence: test assertions for control presence and expected checkbox state transitions

- proof target: batch action scope remains selected-row only
  - method: existing batch route tests plus explicit mixed-selected scenario
  - evidence: route test confirms only selected `job_url` entries are processed

- proof target: wording contract remains stable
  - method: response text assertions in run-detail and dedicated queue views
  - evidence: exact-string checks in `tests/test_fitcv_cp/test_app.py`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
