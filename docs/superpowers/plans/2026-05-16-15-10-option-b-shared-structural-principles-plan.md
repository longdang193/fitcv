---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: option-b-shared-structural-principles-incremental-consolidation-plan
parent_thread: workstream-agentic-synonym-management.agentic-synonym-proposal-engine
parent_spec: docs/superpowers/specs/2026-05-16-14-20-option-b-shared-structural-principles-spec.md
targets:
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
related_stages:
  - enrich
---

## Goal

Execute Option B incremental consolidation by centralizing the highest-duplication shared-structure patterns (proposal builder, proposal status transition logic, and snapshot persistence path) while preserving current control-plane behavior and artifact compatibility.

## Key Deliverables

### Deliverable 1: Canonical synonym proposal builder routing

`worker_job` and `app` proposal-generation call paths use one canonical proposal builder implementation in `src/fitcv_cp/synonym_proposals.py`, with equivalent payload outputs for equivalent inputs.

### Deliverable 2: Canonical proposal transition routing

Automated and manual proposal action paths consume one shared transition evaluator so status progression is equivalent across worker and app surfaces.

### Deliverable 3: Canonical snapshot persistence routing

Checkpoint/partial/final snapshot persistence flows route through one reusable writer path with consistent persistence-status and degraded-warning behavior.

### Deliverable 4: Equivalence and no-regression test coverage

Focused `test_fitcv_cp` suites include coverage proving proposal payload equivalence, transition equivalence, persistence envelope parity, and no endpoint-contract regression.

## Task/Wave Breakdown

### Task 1: Baseline duplication inventory and callable boundary map

**Purpose:**
- lock exact consolidation boundaries before edits so implementation stays scoped to Option B

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `tests/test_fitcv_cp/test_worker_job.py`
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Inspect: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `docs/superpowers/plans/2026-05-16-15-10-option-b-shared-structural-principles-plan.md`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- approved parent spec exists at `docs/superpowers/specs/2026-05-16-14-20-option-b-shared-structural-principles-spec.md`
- worktree baseline validators pass

**Steps:**
- [x] Step 1: identify all proposal-builder entry points and current caller paths in worker/app modules
- [x] Step 2: identify all proposal status transition call paths for automated and manual actions
- [x] Step 3: identify repeated snapshot persistence blocks for checkpoint/partial/final flows
- [x] Step 4: record compatibility-critical fields that must not change in output payloads

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k synonym`

**Exit Criteria:**
- callable boundary map is explicit enough to route all target paths to canonical functions without ambiguity

### Task 2: Consolidate proposal builder to canonical module

**Purpose:**
- remove proposal-builder duplication by routing all relevant paths through `src/fitcv_cp/synonym_proposals.py`

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- canonical builder API shape agreed from existing behavior

**Steps:**
- [x] Step 1: expose/confirm canonical builder interface in `src/fitcv_cp/synonym_proposals.py`
- [x] Step 2: replace worker-local builder usage with canonical module call
- [x] Step 3: replace app-local builder usage with canonical module call where applicable
- [x] Step 4: remove or deprecate duplicate builder blocks while preserving expected payload shape

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "synonym_proposals or mapping_suggestions"`

**Exit Criteria:**
- one active proposal-builder implementation remains for targeted worker/app flows

### Task 3: Consolidate proposal status transition evaluator

**Purpose:**
- enforce one transition rule source for automated and manual proposal actions

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete
- canonical transition semantics preserved from current policy behavior

**Steps:**
- [x] Step 1: define shared transition evaluator function and canonical allowed transitions
- [x] Step 2: route worker auto-action transitions to shared evaluator
- [x] Step 3: route app manual-action transitions to shared evaluator
- [x] Step 4: ensure equivalent invalid-transition handling behavior across both entry points

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "transition or approve_for_run_overlay or defer or reject"`

**Exit Criteria:**
- transition outcomes are equivalent for same input status/action across worker and app paths

### Task 4: Consolidate snapshot persistence writer path

**Purpose:**
- replace repeated checkpoint/partial/final persistence blocks with one reusable writer path and consistent warning/degradation behavior

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`

**Preconditions:**
- Task 3 complete
- current snapshot envelope fields documented and preserved

**Steps:**
- [x] Step 1: extract shared snapshot persistence helper with inputs for lifecycle mode and payload type
- [x] Step 2: route checkpoint path through shared helper
- [x] Step 3: route partial/final paths through shared helper
- [x] Step 4: preserve existing persistence-status and degraded-warning event behavior

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_bq_store.py -k "snapshot or persistence or degradation"`

**Exit Criteria:**
- targeted snapshot persistence flows use one shared writer path and produce compatible envelopes

### Task 5: Equivalence and no-regression finalization

**Purpose:**
- prove consolidated behavior matches expected contracts and no targeted regressions are introduced

**Files:**
- Inspect: `tests/test_fitcv_cp/test_worker_job.py`
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Inspect: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `docs/superpowers/specs/2026-05-16-14-20-option-b-shared-structural-principles-spec.md`

**Preconditions:**
- Tasks 1 through 4 complete

**Steps:**
- [x] Step 1: add/adjust tests to assert proposal payload equivalence for shared input bundles
- [x] Step 2: add/adjust tests to assert transition equivalence for shared status/action inputs
- [x] Step 3: add/adjust tests to assert persistence envelope parity across lifecycle modes
- [x] Step 4: run focused full `test_fitcv_cp` target suites

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py`

**Exit Criteria:**
- all targeted suites pass and deliverables 1 through 4 are satisfied

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
