---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: synonym-proposal-review-gateway-and-dedicated-workspace
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-17-17-33-synonym-proposal-review-gateway-and-dedicated-workspace-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/synonym_review.html
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
related_features: []
related_stages: []
---

## Goal

Implement SSOT-consistent two-tier Synonym Proposal Review UX: run page as summary-and-route gateway, dedicated review page for detailed per-item decisions and promotion.

## Key Deliverables

### Deliverable 1: Run-page gateway is simplified and decision-focused

Run detail presents synonym review summary with recommendation/risk counts and exactly two primary actions (`Accept AI Review and Promote`, `Manually Review and Promote`) while removing per-item manual review clutter from that surface.

### Deliverable 2: Dedicated review workspace supports full manual control

A dedicated Synonym Proposal Review page provides proposal-level compare, filter, decision (`approve/defer/reject/edit`), and controlled promotion interactions with clear staged state.

### Deliverable 3: Promotion outcomes are deterministic, recoverable, and auditable

Fast-path and manual-path promotion flows enforce approved-only promotion eligibility, support partial-failure recovery, and emit auditable decision/promotion result records.

## Task/Wave Breakdown

### Task 1: Introduce canonical proposal-state and summary resolver in control plane

**Purpose:**
- establish backend SSOT so run and review surfaces consume same decision/promotion semantics

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- approved design in parent spec is available
- existing synonym proposal decision and promotion handlers are identified

**Steps:**
- [ ] Step 1: add/normalize canonical proposal decision enum (`PENDING`, `APPROVED`, `DEFERRED`, `REJECTED`, `EDITED_PENDING_APPROVAL`, `SUPPRESSED`) and shared summary counter resolver.
- [ ] Step 2: refactor run-detail and dedicated-review context builders to use same resolver outputs (counts, risk badges, promotion-eligible subset).
- [ ] Step 3: enforce approved-only promotion eligibility in one backend path used by both fast and manual flows.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (summary or state or promote)"`

**Exit Criteria:**
- summary and promotion-eligibility semantics derive from one backend resolver without per-surface divergence

### Task 2: Convert run detail to summary + two-action gateway

**Purpose:**
- make run page low-friction decision gateway and remove detailed manual review controls

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: replace detailed proposal decision rows on run page with summary block (pending, recommended split, risk/suppressed counts).
- [ ] Step 2: add two primary actions: fast-path accept-and-promote and manual-review navigation.
- [ ] Step 3: add fast-path confirmation contract with exact action preview counts before execution.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail and synonym"`

**Exit Criteria:**
- run detail shows gateway-only synonym review UX with no per-item manual decision controls

### Task 3: Build dedicated Synonym Proposal Review page and routes

**Purpose:**
- provide full manual review workspace for proposal inspection, decision editing, and promotion

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- route and permission patterns for operator pages are confirmed

**Steps:**
- [ ] Step 1: add dedicated review route/handler with run-bound proposal data load and stale/version token.
- [ ] Step 2: implement review UI sections (summary bar, filters, proposal cards/table, conflict drilldown, per-item decisions, batch actions).
- [ ] Step 3: implement edit path that marks item `EDITED_PENDING_APPROVAL` and requires revalidation before promotion eligibility.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym_review"`

**Exit Criteria:**
- dedicated page supports complete manual decision workflow independent of run-page clutter

### Task 4: Implement promotion result reporting, retry, and audit evidence

**Purpose:**
- ensure promotion outcome transparency and safe recovery for partial failures

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_review.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: implement result payload with promoted/failed/skipped counts and per-item failure reasons for both fast and manual paths.
- [ ] Step 2: add retry-failed-subset action with idempotent guard (do not duplicate prior successful writes).
- [ ] Step 3: persist audit events with decision source (`ai_fast_path` or `manual_review`) and promotion outcome snapshot.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (promotion or retry or audit)"`

**Exit Criteria:**
- promotion failures are explicit, recoverable, and auditable without status ambiguity

### Task 5: Documentation and end-to-end verification closure

**Purpose:**
- align operator documentation and provide final proof of contract conformance

**Files:**
- Modify: `docs/configuration.md`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `docs/superpowers/specs/2026-05-17-17-33-synonym-proposal-review-gateway-and-dedicated-workspace-spec.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: document run-page gateway vs dedicated review responsibilities and operator action semantics.
- [ ] Step 2: document fast-path confirmation and partial-failure retry behavior.
- [ ] Step 3: run full targeted synonym-review test slice and fast repo validator.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs, tests, and validator evidence align with parent spec acceptance criteria

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym"`
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
