---
layer: change
artifact_type: plan
status: completed
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

### Deliverable 4: Follow-on Refactor Sequencing Record

Plan state explicitly records that:
- RA-04 (`generate_embedding` path) is high-impact and must be preceded by explicit degradation-policy spec decision.
- RA-02 broad extraction is deferred until query/failure invariants are locked.
- RA-03 and RA-05 remain cleanup candidates but are lower risk-reduction priority than RA-01.

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
- [x] Step 1: confirm `_load_latest_job_embedding_metadata` current SQL construction and output shape
- [x] Step 2: map existing tests asserting `embed_and_store_jobs` reuse/fresh behavior
- [x] Step 3: enumerate fields and statuses that must remain invariant after patch

**Verification:**
- [x] invariants checklist recorded in implementation notes and matched to spec

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
- [x] Step 1: replace direct `job_urls` SQL interpolation with parameterized query path
- [x] Step 2: preserve query semantics (latest row tie logic, selected columns, normalization behavior)
- [x] Step 3: keep function signature and return shape unchanged for callers

**Verification:**
- [x] code inspection confirms no direct URL interpolation remains in lookup SQL path
- [x] static review confirms unchanged output dictionary schema

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
- [x] Step 1: add/adjust test asserting apostrophe-containing job URL path remains safe and functional
- [x] Step 2: assert mixed reused/fresh flow still yields expected statuses and insert count
- [x] Step 3: avoid brittle SQL-string snapshot assertions; validate behavior and query-parameter intent

**Verification:**
- [x] targeted test run for `tests/test_embeddings.py` passes

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
- [x] Step 1: run required fast validators and targeted tests (targeted tests pass; strict validator closure waived by explicit user decision due pre-existing unrelated spec/doc drift)
- [x] Step 2: confirm changed-file scope stays within RA-01 targets
- [x] Step 3: record rollback plan (revert only RA-01 diff) and residual follow-on items (RA-02..RA-05), with explicit ordering:
  - RA-04 requires dedicated degradation-policy decision first (high-impact path).
  - RA-02 executes after invariants lock.
  - RA-03 and RA-05 remain lower-priority cleanup.

**Verification:**
- [x] `python scripts/hooks/run_validator.py --fast` (known unrelated blocker accepted by explicit scope decision)
- [x] `pytest tests/test_embeddings.py -q`
- [x] scope inspection via git diff (and GitNexus detect-changes during implementation if commit phase reached)

**Exit Criteria:**
- implementation patch is validated, bounded, and ready for next-action execution

### Task 5: RA-02 cross-module extraction

**Purpose:**
- centralize duplicated runtime helpers to improve symmetry and reduce repeated BigQuery/client wiring

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/shortlist_runtime.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`

**Preconditions:**
- Task 4 scoped safety checks complete
- query/failure invariants preserved

**Steps:**
- [x] Step 1: add shared helper(s) for BigQuery client construction in `shortlist_runtime.py`
- [x] Step 2: update embedding and vector-search flows to use shared helper(s)
- [x] Step 3: confirm behavior parity and no contract-field regressions

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`
- [x] `pytest tests/test_vector_search.py -q`

**Exit Criteria:**
- duplicated cross-module runtime setup reduced with preserved behavior

### Task 6: RA-03 contract-fingerprint SSOT cleanup

**Purpose:**
- enforce one deterministic fingerprint pathway across equivalent embedding-contract flows

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/shortlist_runtime.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`

**Preconditions:**
- Task 5 complete

**Steps:**
- [x] Step 1: add shared contract-fingerprint helper in `shortlist_runtime.py`
- [x] Step 2: route job and candidate-query fingerprint builders through shared helper
- [x] Step 3: keep payload schemas and version fields unchanged

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`
- [x] `pytest tests/test_vector_search.py -q`

**Exit Criteria:**
- contract fingerprint generation is centralized and invariant-preserving

### Task 7: RA-04 degradation policy gate for high-impact embedding path

**Purpose:**
- add explicit failure-policy decision point for `generate_embedding` without changing default runtime semantics

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `tests/test_embeddings.py`

**Preconditions:**
- Task 6 complete
- high-impact guard acknowledged for `generate_embedding` path

**Steps:**
- [x] Step 1: add explicit `embedding_failure_policy` resolver and policy constants
- [x] Step 2: keep default behavior as deterministic fallback; add `raise` policy branch
- [x] Step 3: add tests for policy behavior and preserve existing passing behavior

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`

**Exit Criteria:**
- degradation policy is explicit, default behavior preserved, and policy branch tested

### Task 8: RA-05 obsolete/duplication cleanup

**Purpose:**
- remove dead wrappers and duplicate payload-json derivation to improve symmetry and reduce maintenance noise

**Files:**
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`

**Preconditions:**
- Tasks 5-7 complete

**Steps:**
- [x] Step 1: remove dead `_canonicalize_for_hash` wrappers
- [x] Step 2: use canonical `hash_payload` output for `payload_json` fields
- [x] Step 3: confirm no behavior regressions in covered tests

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`
- [x] `pytest tests/test_vector_search.py -q`

**Exit Criteria:**
- dead duplication removed and serialization symmetry preserved

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest tests/test_embeddings.py -q`
- inspect `git diff -- src/fitcv/embeddings.py tests/test_embeddings.py`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Scope Evolution Note

- Initial lane intent was RA-01 bounded execution.
- Scope expanded in-lane to RA-02 through RA-05 by explicit user instruction.
- Strict full-validator closure remained outside scoped remediation and was waived with known-blocker note.

## Execution Addendum (RA-02 to RA-05)

Follow-on work executed in this lane after explicit sequencing update:

- [x] RA-02: broad extraction started across modules by centralizing shared runtime helpers in `src/fitcv/shortlist_runtime.py` and wiring `embeddings.py` + `vector_search.py` to shared BigQuery client/fingerprint helpers.
- [x] RA-03: contract fingerprint cleanup executed via shared deterministic helper usage.
- [x] RA-04: high-impact `generate_embedding` path updated with explicit degradation policy gate (`embedding_failure_policy`), default behavior preserved.
- [x] RA-05: cleanup applied for dead helpers and duplicate payload-json derivations.

Verification evidence for addendum:

- `pytest tests/test_embeddings.py -q`
- `pytest tests/test_vector_search.py -q`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
