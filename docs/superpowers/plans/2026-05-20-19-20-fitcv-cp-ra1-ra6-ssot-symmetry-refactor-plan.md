---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-cp-ra1-ra6-ssot-symmetry-refactor
parent_workstream: none
targets:
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/orchestrator.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/queue.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_fitcv_cp/test_orchestrator.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_queue.py
related_features:
  - none
related_stages:
  - none
---

## Goal
Execute RA-01..RA-06 as bounded control-plane refactor that enforces SSOT, symmetry, and invariance across reporter/orchestrator/store/queue, while preserving public runtime behavior and backward compatibility.

## Key Deliverables

### D1: Canonical orchestration status contract (RA-01)
Introduce one normalized status vocabulary and mapping path used by queue and orchestrator so equivalent queue/prefect/inline states resolve consistently.

### D2: Truthful submission backend semantics (RA-02)
Ensure submission metadata distinguishes requested backend vs actual execution backend for Prefect fallback paths without breaking existing `submission.backend` usage.

### D3: Queue flow symmetry and deduplication (RA-03 + RA-06)
Unify duplicated inline enqueue/job-runner paths, normalize terminal status behavior, and explicitly preserve/deprecate unused `triggered_by` pass-through contract.

### D4: Shared env parsing SSOT (RA-04)
Consolidate truthy and bounded numeric env parsing into reusable helper(s) consumed by reporter and queue.

### D5: Store delegation simplification (RA-05)
Reduce repetitive wrapper boilerplate in `ControlPlaneStore` using internal call helpers while preserving protocol signatures and injected-function testability.

### D6: Regression-proof verification bundle
Update/extend unit tests and run scoped checks (`pytest` + `mypy`) proving no contract regressions.

## Task/Wave Breakdown

### Task 1: Baseline and dependency lock
**Purpose:**
- establish safe execution baseline and dependency visibility before refactor edits.

**Files:**
- Inspect: `src/fitcv_cp/orchestrator.py`
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect: `src/fitcv_cp/store.py`

**Preconditions:**
- GitNexus index is up-to-date (`npx gitnexus status`)
- If GitNexus warns degraded FTS, proceed source-first and use impact output as primary graph signal.

**Steps:**
- [ ] Capture current behavior snapshots from existing tests.
- [ ] Re-run `gitnexus impact` for symbols edited first.
- [ ] Confirm no unrelated code files are included in patch scope.

**Verification:**
- [ ] `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" OrchestrationAdapter`
- [ ] `git status --short`

**Exit Criteria:**
- bounded refactor scope and dependency touchpoints confirmed.

### Task 2: Implement status SSOT surface (RA-01)
**Purpose:**
- add single status normalization contract used across queue/orchestrator paths.

**Files:**
- Inspect: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/orchestrator.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_orchestrator.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Define canonical orchestration status values and alias mapping.
- [ ] Normalize RQ raw statuses through shared mapper.
- [ ] Normalize Prefect states through same mapper.

**Verification:**
- [ ] Add/adjust unit tests for canonical status outputs across queue/prefect/inline.

**Exit Criteria:**
- both adapters produce canonical statuses for equivalent runtime states.

### Task 3: Implement truthful backend binding (RA-02)
**Purpose:**
- preserve compatibility while exposing true backend execution semantics.

**Files:**
- Modify: `src/fitcv_cp/orchestrator.py`
- Verify: `tests/test_fitcv_cp/test_orchestrator.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [ ] Extend `RunSubmission` contract with requested vs execution backend fields.
- [ ] Keep `backend` compatibility behavior for existing callers.
- [ ] Update Prefect fallback path to report queue execution truthfully.

**Verification:**
- [ ] Tests for Prefect success and fallback assert both compatibility and truth fields.

**Exit Criteria:**
- fallback no longer mislabels execution backend.

### Task 4: Queue symmetry + obsolete arg handling (RA-03 + RA-06)
**Purpose:**
- remove hidden duplication in inline enqueue paths and formalize `triggered_by` compatibility.

**Files:**
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [ ] Extract shared inline enqueue helper(s) for run and regenerate-once jobs.
- [ ] Align error/terminal status assignment rules.
- [ ] Mark `triggered_by` as intentionally unused compatibility parameter and cover with test/assertion.

**Verification:**
- [ ] Existing queue tests pass.
- [ ] New test(s) cover inline status symmetry and compatibility behavior.

**Exit Criteria:**
- duplicated queue branching removed and obsolete-arg behavior explicit.

### Task 5: Env parser SSOT (RA-04)
**Purpose:**
- enforce consistent env parsing semantics between reporter and queue.

**Files:**
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`

**Preconditions:**
- Task 4 complete.

**Steps:**
- [ ] Introduce shared env parser utility (module-local or shared helper module).
- [ ] Replace duplicated truthy and bounded-float parsing logic.
- [ ] Preserve current defaults and accepted truthy values.

**Verification:**
- [ ] Add targeted parser behavior tests for true/false/default/bounds.

**Exit Criteria:**
- reporter and queue read env flags with one semantic contract.

### Task 6: Store delegation compression (RA-05)
**Purpose:**
- reduce repeated delegation boilerplate without changing public API.

**Files:**
- Modify: `src/fitcv_cp/store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Add private helper(s) for resolving injected function or default bq_store function.
- [ ] Refactor wrappers to call helpers while keeping signatures unchanged.
- [ ] Keep list/dict return-shape normalization intact.

**Verification:**
- [ ] Existing injected-function tests pass without adjustment drift.

**Exit Criteria:**
- wrapper duplication reduced; protocol behavior preserved.

### Task 7: Cross-surface regression pass
**Purpose:**
- prove behavioral invariance after refactor.

**Files:**
- Verify: `tests/test_fitcv_cp/test_orchestrator.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Tasks 2-6 complete.

**Steps:**
- [ ] Run scoped pytest for fitcv_cp refactor surfaces.
- [ ] Run mypy for `src` typing regression.
- [ ] Resolve failures with bounded follow-up edits only.

**Verification:**
- [ ] `uvx pytest tests/test_fitcv_cp/test_orchestrator.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_store.py`
- [ ] `uvx mypy src --show-error-codes`

**Exit Criteria:**
- scoped tests and types pass with no unmanaged regressions.

### Task 8: Scope integrity and closeout evidence
**Purpose:**
- ensure refactor touched only intended graph/files and document next-action gate.

**Files:**
- Verify: `src/fitcv_cp/orchestrator.py`
- Verify: `src/fitcv_cp/queue.py`
- Verify: `src/fitcv_cp/reporter.py`
- Verify: `src/fitcv_cp/store.py`

**Preconditions:**
- Task 7 complete.

**Steps:**
- [ ] Run GitNexus changed-scope analysis on final diff.
- [ ] Record residual risks and deferred follow-ups.
- [ ] Prepare handoff for execution or review.

**Verification:**
- [ ] `npx gitnexus detect-changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- [ ] `git diff --name-only`

**Exit Criteria:**
- final patch scope and residual risks explicitly captured.

## Verification
- `uvx pytest tests/test_fitcv_cp/test_orchestrator.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_store.py`
- `uvx mypy src --show-error-codes`
- `npx gitnexus detect-changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

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
