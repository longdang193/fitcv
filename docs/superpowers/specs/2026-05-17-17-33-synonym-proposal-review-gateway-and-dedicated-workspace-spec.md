---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: synonym-proposal-review-gateway-and-dedicated-workspace
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
related_features: []
related_stages: []
---

## Goal

Define a two-tier UX contract for Synonym Proposal Review that keeps run page as summary-and-decision gateway while moving manual proposal inspection/edit/review/promotion controls into a dedicated review workspace.

## Key Deliverables

### Run-page gateway contract

Define exact information density and action surface for run page so operators can pick fast path vs manual path without per-proposal workflow clutter.

### Dedicated review workspace contract

Define detailed review-page information architecture and action model for per-item decisions (`approve`, `defer`, `reject`, `edit`) and controlled promotion.

### Promotion execution and audit contract

Define deterministic state transitions, partial-success handling, failure recovery, and audit evidence so promotion outcomes remain trustworthy and inspectable.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current run-page review behavior, overload points, and existing promotion semantics before changing UI flow

**Steps:**
- [ ] inspect current run-detail synonym review blocks, controls, and diagnostics density
- [ ] inspect current backend endpoints/actions for recommendation acceptance, manual decisions, and promotion
- [ ] identify current status model used for proposals and promotion outcomes

**Verification:**
- [ ] current state and pain points are explicit enough to prevent accidental regression in existing run workflow

**Exit Criteria:**
- no design decision depends on assumptions about current decision/promotion behavior

### Wave 2: Decision closure

**Purpose:**
- resolve UI-boundary and state-model decisions for gateway/manual split and promotion semantics

**Steps:**
- [ ] define run page as summary-only gateway with two primary actions
- [ ] define dedicated review page IA (filters, proposal cards/table, conflict drilldowns, batch controls)
- [ ] define single proposal decision state model and promotion eligibility rules
- [ ] define edge-case handling for partial acceptance, edits, stale data, and failed promotions

**Verification:**
- [ ] each user intent (`trust AI`, `manual control`, `audit/debug`) has one clear interface and no ambiguous overlap

**Exit Criteria:**
- design is MECE, internally coherent, and bounded to synonym-review UX/promotion flow

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof requirements explicit for correctness, usability, and auditability of new flow

**Steps:**
- [ ] define test matrix for run gateway rendering and action behavior
- [ ] define test matrix for manual review transitions and promotion execution outcomes
- [ ] define audit/logging evidence requirements for fast-path and manual-path decisions

**Verification:**
- [ ] validation plan proves SSOT state handling, path symmetry, and safe failure behavior

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Run page is decision gateway, not detailed review surface

- context: current run page mixes summary, per-proposal operations, and promotion internals, creating cognitive overload and action ambiguity
- choice: keep run page limited to summary metrics, risk signals, and two route actions (`Accept AI Review and Promote`, `Manually Review and Promote`)
- alternatives considered:
  - keep full review controls on run page
  - keep current mixed model with incremental cleanup
- impact:
  - lower cognitive load for common path
  - clearer navigation boundary between quick action and deep review

### Decision: Dedicated review page owns all per-item decision controls

- context: manual review requires side-by-side comparison, conflict handling, batch operations, and edit flows that do not fit run-page summary role
- choice: provide dedicated Synonym Proposal Review page for item-level inspection and decisions before promotion
- alternatives considered:
  - modal-based deep review from run page
  - accordion expansion inside run page
- impact:
  - complete manual control without bloating run page
  - clearer ownership of review-state lifecycle

### Decision: Single SSOT proposal decision model

- context: split UX can drift if decision states are recomputed differently across run and review surfaces
- choice: proposal state is owned by one canonical enum: `PENDING | APPROVED | DEFERRED | REJECTED | EDITED_PENDING_APPROVAL | SUPPRESSED`; only `APPROVED` is promotion-eligible
- alternatives considered:
  - separate run-page summary statuses and review-page statuses
  - deriving statuses from loosely coupled flags
- impact:
  - deterministic rendering across surfaces
  - reduced ambiguity for partial/mixed outcomes

### Decision: Fast-path promotion remains explicit and confirmable

- context: one-click acceptance improves speed but can cause accidental irreversible operations without clear preview
- choice: `Accept AI Review and Promote` shows confirmation with exact counts (approve/defer/reject/suppressed) and promotes approved subset only
- alternatives considered:
  - immediate no-confirm execution
  - requiring manual page for all promotions
- impact:
  - preserves low-friction path while reducing accidental promotion risk

### Decision: Promotion result is first-class outcome surface

- context: partial failures and retries are operationally common and must be auditable
- choice: always present promoted/failed/skipped counts, per-item errors, and retry-failed-subset action; record immutable audit event
- alternatives considered:
  - toast-only success messaging
  - silent partial-failure fallback
- impact:
  - clearer recovery path
  - stronger auditability and operator trust

## Invariants

- Run page remains summary-and-routing surface; it does not host full per-proposal decision UI.
- Manual review page is single owner of item-level decision controls and edit operations.
- Proposal decision state model is SSOT and shared across all UX surfaces.
- Promotion executes only on `APPROVED` proposals.
- Promotion actions are idempotent for retry safety and preserve successful writes during partial failures.
- Audit trail records decision source (`ai_fast_path` vs `manual_review`) and promotion outcome.

## Validation Plan

- proof target: run page exposes only gateway summary + two actions
  - method: template/UI inspection and endpoint behavior tests
  - evidence: tests confirming absence of per-item edit/decision controls on run page and presence of two gateway actions

- proof target: manual review page supports full item-level control
  - method: integration tests for proposal list/filter/action workflow
  - evidence: tests showing `approve/defer/reject/edit` transitions and persisted state updates

- proof target: SSOT state model is consistent across run and review surfaces
  - method: unit tests for state resolver and cross-surface rendering assertions
  - evidence: deterministic mapping tests for all enum states and summary counts

- proof target: fast-path confirm/apply/promotion behavior is deterministic
  - method: integration tests for confirmation, AI decision application, and approved-only promotion
  - evidence: tests showing exact count preview and resulting promoted/deferred/rejected totals

- proof target: partial promotion failures are recoverable and auditable
  - method: failure-injection integration tests
  - evidence: tests showing partial success reporting, failed-subset retry path, and audit records with per-item failure reasons

- proof target: concurrency/staleness safety prevents silent overwrite
  - method: integration tests with version token mismatch and concurrent review updates
  - evidence: tests showing stale-write block, refresh requirement, and preserved prior decisions

## Acceptance Criteria

- Run page shows synonym-review summary, recommendation/risk counts, and exactly two primary actions.
- Manual review path opens dedicated page with per-item compare/decision/edit workflow.
- Proposal decisions use canonical enum model; promotion eligibility is `APPROVED` only.
- Fast path includes confirmation preview and promotes approved subset only.
- Promotion result surface reports promoted/failed/skipped counts and per-item errors.
- Partial failure retry mechanism exists and is idempotent.
- Audit entries capture decision source, decision snapshot, promotion attempt, and outcomes.

## Non-Goals

- Redesigning synonym proposal generation model/prompting logic.
- Replacing existing global synonym data model/storage backend.
- Overhauling unrelated run-detail sections outside synonym review flow.
- Introducing new cross-feature governance or publication-boundary workflows.

## Risks and Mitigations

- Risk: split-page flow may feel slower for power users
  - mitigation: preserve one-click fast path on run page with clear confirmation and result summary

- Risk: state drift between gateway and review surfaces
  - mitigation: shared SSOT enum and centralized state resolver/tests

- Risk: promotion partial failures degrade trust
  - mitigation: explicit per-item error visibility, retry-failed-subset action, immutable audit log

- Risk: manual edits bypass AI confidence assumptions
  - mitigation: edited-state revalidation before promotion and explicit `edited` badge/reasoning indicator

- Risk: concurrent reviewer actions cause hidden overrides
  - mitigation: optimistic locking/version token checks and forced refresh on conflict

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
