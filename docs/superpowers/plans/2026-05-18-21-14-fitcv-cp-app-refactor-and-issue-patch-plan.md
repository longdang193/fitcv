---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-cp-app-refactor-and-issue-patch-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-18-21-12-fitcv-cp-app-refactor-and-issue-patch-spec.md
targets:
  - src/fitcv_cp/app.py
  - tests/
related_features: []
related_stages: []
---

# Implementation Plan: fitcv_cp app.py Refactor And Issue Patch

## Goal

Execute bounded, behavior-preserving refactor of `src/fitcv_cp/app.py` to enforce SSOT, symmetry, and invariance defined in parent spec, with patch-first correctness and staged extraction guarded by GitNexus impact checks.

## Key Deliverables

### D1: Correctness patch for duplicate semantic-outcome logic

Single canonical `_timeline_semantic_outcome` implementation with parity-preserving behavior for legacy and canonical stage aliases, plus regression tests.

### D2: Route/service symmetry for repeated control-plane patterns

Canonical helpers/services for:
- run fetch + not-found handling
- orchestration status accessor naming
- settings write pipeline
- synonym overlay parse/validate pathway

with unchanged external route contracts.

### D3: Verified invariance and bounded blast radius

Execution evidence proving route behavior parity, status-policy invariants, and bounded dependency scope via GitNexus and test/type checks.

## Task/Wave Breakdown

### Task 1: Baseline and impact gate setup

**Purpose:**
- Establish trusted baseline and explicit blast-radius map before edits.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `tests/`
- Verify: `docs/superpowers/specs/2026-05-18-21-12-fitcv-cp-app-refactor-and-issue-patch-spec.md`

**Preconditions:**
- parent spec approved for execution
- GitNexus index fresh

**Steps:**
- [ ] Step 1: capture baseline with `uvx pytest tests/` and `uvx mypy src --show-error-codes`.
- [ ] Step 2: run `gitnexus_context` and `gitnexus_impact(direction="upstream")` for first-wave symbols:
  - `_timeline_semantic_outcome`
  - `get_queue_job_status`
  - `orchestration_job_status`
- [ ] Step 3: record expected affected callers/processes and risk level for each symbol.

**Verification:**
- [ ] baseline test/type command outputs captured.
- [ ] GitNexus impact outputs captured for each first-wave symbol.

**Exit Criteria:**
- first-wave edits have explicit caller/process map and bounded risk.

### Task 2: Patch duplicate semantic-outcome definition (RF-001)

**Purpose:**
- Remove duplicate function definition drift without behavior regression.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/` (existing + new/updated unit tests)

**Preconditions:**
- Task 1 complete
- impact gate for `_timeline_semantic_outcome` complete

**Steps:**
- [ ] Step 1: collapse duplicate `_timeline_semantic_outcome` into single canonical function.
- [ ] Step 2: preserve accepted stage alias coverage (`layer4_cv_validation_failed` and `cv_validation_failed`).
- [ ] Step 3: add/adjust focused tests asserting expected outcome mapping for representative payload combinations.

**Verification:**
- [ ] targeted tests for timeline semantic outcome pass.
- [ ] no second definition remains in `app.py`.

**Exit Criteria:**
- duplicate definition removed; behavior parity proven by tests.

### Task 3: Normalize run-fetch and orchestration status helpers (RF-002 partial)

**Purpose:**
- Enforce symmetry for run lookup and status access patterns.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: route tests covering run-not-found and queue-status flows

**Preconditions:**
- Task 2 complete
- impact gate for helper symbols complete

**Steps:**
- [ ] Step 1: introduce SSOT helper for run retrieval + standardized 404 handling contract per route type (HTML vs JSON).
- [ ] Step 2: consolidate queue/orchestration status accessor into one canonical helper name and call path.
- [ ] Step 3: migrate selected route families first, then remaining equivalent callsites.

**Verification:**
- [ ] representative HTML and JSON routes preserve expected not-found semantics.
- [ ] no divergent status accessor helpers remain.

**Exit Criteria:**
- equivalent run-fetch and status-access flows share canonical helper(s).

### Task 4: Consolidate settings write and overlay parse pipelines (RF-004 + RF-005 bounded slice)

**Purpose:**
- Remove hidden duplication in settings and synonym overlay input handling.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Optional modify (if extracted): `src/fitcv_cp/settings_service.py`, `src/fitcv_cp/input_parsers.py`
- Verify: settings and overlay route tests

**Preconditions:**
- Task 3 complete
- impact gate for settings/overlay helper candidates complete

**Steps:**
- [ ] Step 1: extract canonical settings mutation flow (`coerce -> validate -> save`) used by single-key/group/section handlers.
- [ ] Step 2: extract shared synonym overlay parser/validator (UTF-8 decode, YAML parse, scope validate).
- [ ] Step 3: update route handlers to delegate through extracted flow while preserving response contract and status codes.

**Verification:**
- [ ] settings route matrix passes (single-key/group/section).
- [ ] overlay input matrix passes (missing file, empty bytes, non-UTF8, invalid YAML, invalid scope).

**Exit Criteria:**
- duplicated settings and overlay logic replaced by SSOT flow(s) with parity tests.

### Task 5: Final scope verification, containment, and handoff

**Purpose:**
- Prove bounded change scope and prepare safe merge/handoff.

**Files:**
- Inspect: modified files from Tasks 2-4
- Verify: `tests/`, `docs/superpowers/specs/2026-05-18-21-12-fitcv-cp-app-refactor-and-issue-patch-spec.md`

**Preconditions:**
- Tasks 2-4 complete

**Steps:**
- [ ] Step 1: run full regression gates: `uvx pytest tests/` and `uvx mypy src --show-error-codes`.
- [ ] Step 2: run `gitnexus_detect_changes()` and compare affected symbols/processes to planned scope.
- [ ] Step 3: if drift exceeds planned scope, split/rollback last slice and re-run checks.

**Verification:**
- [ ] tests and type checks pass.
- [ ] GitNexus detect-changes output matches expected bounded scope.

**Exit Criteria:**
- refactor ready for review with explicit evidence and bounded blast radius.

## Verification

- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `gitnexus_detect_changes()`
- `python scripts/hooks/run_validator.py --fast`

## Rollback And Containment

- rollback unit: one task slice at a time; do not batch-revert multiple tasks.
- if route contract regression appears, revert latest task-local edits and keep prior completed tasks.
- if GitNexus detect-changes risk rises above planned scope, stop and split remaining changes into new bounded slice before continuing.

## Completion Criteria

1. all Key Deliverables completed with evidence
2. parent-spec acceptance criteria satisfied
3. task-level and final verification commands pass
4. GitNexus scope verification confirms no unplanned cross-process impact
