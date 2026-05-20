---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: embedding-cache-query-ssot-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-20-15-10-embedding-cache-query-ssot-refactor-spec.md
targets:
  - src/fitcv/embeddings.py
  - tests/test_embeddings.py
related_features: []
related_stages: []
---

## Goal

Implement RA-01 safely by replacing interpolated job URL SQL in `_load_latest_job_embedding_metadata` with parameterized BigQuery query flow, while preserving shortlist embedding reuse semantics and all existing downstream contracts.

## Key Deliverables

### Deliverable 1: Parameterized Metadata Lookup in Embeddings Module

`src/fitcv/embeddings.py` uses parameterized BigQuery query input for job URL filtering (no direct URL interpolation in SQL text), with unchanged returned metadata mapping and unchanged caller behavior.

### Deliverable 2: Regression-Safe Test Coverage for Query Safety and Reuse Invariants

`tests/test_embeddings.py` includes concrete coverage for apostrophe-containing URLs and behavior-parity checks for reused/fresh outcomes, preserving existing contract assertions.

### Deliverable 3: Verified Bounded Change Scope

Implementation evidence confirms scope stays within RA-01 targets and does not alter embedding fallback policy, schema versions, or status naming contracts.

## Task/Wave Breakdown

### Task 1: Prepare and lock current behavior baseline

**Purpose:**
- capture current behavior surfaces and test anchors before edit so refactor remains contract-preserving

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Inspect: `tests/test_embeddings.py`
- Verify: `docs/superpowers/specs/2026-05-20-15-10-embedding-cache-query-ssot-refactor-spec.md`

**Preconditions:**
- parent spec remains proposed and unchanged in invariants
- no expanded scope beyond RA-01

**Steps:**
- [ ] Step 1: confirm `_load_latest_job_embedding_metadata` current SQL construction and output shape
- [ ] Step 2: map existing tests asserting `embed_and_store_jobs` reuse/fresh behavior
- [ ] Step 3: enumerate fields and statuses that must remain invariant after patch

**Verification:**
- [ ] invariants checklist recorded in implementation notes and matched to spec

**Exit Criteria:**
- bounded edit contract is explicit and implementation-ready

### Task 2: Refactor metadata lookup query to parameterized form

**Purpose:**
- remove interpolation risk and align with symmetric candidate-query lookup style

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/embeddings.py`
- Verify: `src/fitcv/vector_search.py`

**Preconditions:**
- Task 1 complete
- BigQuery parameter API pattern chosen and syntax validated against repo conventions

**Steps:**
- [ ] Step 1: replace direct `job_urls` SQL interpolation with parameterized query path
- [ ] Step 2: preserve query semantics (latest row tie logic, selected columns, normalization behavior)
- [ ] Step 3: keep function signature and return shape unchanged for callers

**Verification:**
- [ ] code inspection confirms no direct URL interpolation remains in lookup SQL path
- [ ] static review confirms unchanged output dictionary schema

**Exit Criteria:**
- parameterized lookup implemented with no public behavior contract changes

### Task 3: Add regression tests for safety and parity

**Purpose:**
- prove query safety improvements without reuse behavior regressions

**Files:**
- Inspect: `tests/test_embeddings.py`
- Modify: `tests/test_embeddings.py`
- Verify: `src/fitcv/embeddings.py`

**Preconditions:**
- Task 2 complete
- existing test style preserved

**Steps:**
- [ ] Step 1: add/adjust test asserting apostrophe-containing job URL path remains safe and functional
- [ ] Step 2: assert mixed reused/fresh flow still yields expected statuses and insert count
- [ ] Step 3: avoid brittle SQL-string snapshot assertions; validate behavior and query-parameter intent

**Verification:**
- [ ] targeted test run for `tests/test_embeddings.py` passes

**Exit Criteria:**
- tests prove RA-01 acceptance criteria and invariants

### Task 4: Validate full bounded change and handoff readiness

**Purpose:**
- complete quality gate and prepare clean handoff for execution/merge workflow

**Files:**
- Verify: `src/fitcv/embeddings.py`
- Verify: `tests/test_embeddings.py`
- Verify: `docs/superpowers/specs/2026-05-20-15-10-embedding-cache-query-ssot-refactor-spec.md`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: run required fast validators and targeted tests
- [ ] Step 2: confirm changed-file scope stays within RA-01 targets
- [ ] Step 3: record rollback plan (revert only RA-01 diff) and residual follow-on items (RA-02..RA-05)

**Verification:**
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `pytest tests/test_embeddings.py -q`
- [ ] scope inspection via git diff (and GitNexus detect-changes during implementation if commit phase reached)

**Exit Criteria:**
- implementation patch is validated, bounded, and ready for next-action execution

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest tests/test_embeddings.py -q`
- inspect `git diff -- src/fitcv/embeddings.py tests/test_embeddings.py`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
