---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: bq-store-ssot-symmetry-invariance-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-18-21-58-bq-store-refactor-spec.md
targets:
  - src/fitcv_cp/bq_store.py
  - tests/
related_features: []
related_stages: []
---

## Goal

Implement behavior-preserving refactor of `src/fitcv_cp/bq_store.py` to enforce SSOT/symmetry/invariance across run mutation, degradation outcomes, and JSON normalization paths, with full regression safety.

## Key Deliverables

### Unified run-mutation implementation surface

Introduce shared internal mutation/update helpers used by equivalent `update_run_*` paths so local and BigQuery branches follow one consistent execution model, including retry and legacy fallback behavior.

### Standardized persistence/degradation contract and parse normalization

Normalize degradation status/reason vocabulary for degradable operations and centralize repeated JSON decode/default logic with explicit per-field-class behavior.

### Verified no-regression patch set

Deliver tests and validations proving external behavior parity, retry-path consistency, fallback compatibility, and controlled blast radius.

## Task/Wave Breakdown

### Task 1: Baseline And Dependency Safety Mapping

**Purpose:**
- establish safe change boundary and caller impact map before edits

**Files:**
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `tests/` (existing bq_store-related tests)
- Verify: `docs/superpowers/specs/2026-05-18-21-58-bq-store-refactor-spec.md`

**Preconditions:**
- parent spec approved for execution
- GitNexus index freshness checked (`.\scripts\get_gitnexus_freshness.ps1`)

**Steps:**
- [ ] Identify concrete symbols to refactor (`update_run_*`, `append_event`, JSON parse call sites).
- [ ] Run GitNexus impact/context workflow for each targeted symbol:
  - `gitnexus_impact({target: "<symbol>", direction: "upstream"})`
  - `gitnexus_query({query: "<symbol>"})`
  - `gitnexus_context({name: "<symbol>"})`
- [ ] Record expected affected callers/tests and classify risk per symbol.
- [ ] Freeze a bounded edit set for phase-1 (non-breaking internal refactor only).

**Verification:**
- [ ] Symbol impact notes exist and map to planned tasks.
- [ ] No high-risk symbol edit proceeds without explicit mitigation note.

**Exit Criteria:**
- refactor scope is caller-aware and bounded

### Task 2: Extract Shared Run-Mutation Primitive

**Purpose:**
- remove duplicated run-field update structure while preserving current API behavior

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/` (mutation/update behavior tests)

**Preconditions:**
- Task 1 complete with target symbol set finalized

**Steps:**
- [ ] Implement internal helper(s) for symmetric run mutation flow:
  - local mode load/mutate/save
  - BQ update execution through shared retry helper
  - optional per-column legacy fallback hooks
- [ ] Refactor equivalent `update_run_*` wrappers to use helper(s) without signature changes.
- [ ] Ensure `update_run_effective_settings` aligns with retry path used by peer updates.
- [ ] Keep SQL parameterization and existing field semantics intact.

**Verification:**
- [ ] Wrapper signatures unchanged.
- [ ] Existing behavior for success paths remains unchanged in tests.
- [ ] Retry helper usage confirmed for `pipeline_runs` updates.

**Exit Criteria:**
- duplicated update scaffolding collapsed into single internal abstraction

### Task 3: Standardize Degradation Outcome Contract

**Purpose:**
- enforce invariant status/reason semantics for degradable operations

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/` (append_event/synonym proposal outcome tests)

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Define canonical internal outcome vocabulary (status + reason + optional metadata).
- [ ] Normalize degradable return payloads in:
  - `append_event`
  - `update_run_synonym_proposals`
  - any helper paths that emit degradation outcomes
- [ ] Preserve external return shapes for backward compatibility in phase 1.
- [ ] Add/adjust logging so degraded states remain observable.

**Verification:**
- [ ] Success and degraded outcomes use canonical reason vocabulary.
- [ ] Caller-visible payload contracts remain backward compatible.

**Exit Criteria:**
- degradation semantics consistent across scoped degradable paths

### Task 4: Centralize JSON Normalization And Edge Guards

**Purpose:**
- remove hidden duplication in parsing/default logic and harden edge cases

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Verify: `tests/` (JSON parse/invalid input coverage)

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Extract shared JSON decode helper(s) for object-like and list-like field classes.
- [ ] Replace repeated inline parse blocks with helper calls in scoped functions.
- [ ] Harden edge conversions (`summary` numeric conversion, event replay parse failures) per spec.
- [ ] Preserve current default semantics where contractually required.

**Verification:**
- [ ] Invalid/empty/valid JSON fixtures produce deterministic expected defaults.
- [ ] No regressions in run/event/CV read paths.

**Exit Criteria:**
- repeated parse logic consolidated with explicit, tested policy

### Task 5: Test, Type, Blast-Radius, And Rollback Gates

**Purpose:**
- prove no-regression and ensure change scope remains expected

**Files:**
- Modify: `tests/` (new/updated tests only as needed)
- Verify: `src/fitcv_cp/bq_store.py`
- Verify: `docs/generated/planning_lineage.yaml` (if lifecycle validator requires refresh)

**Preconditions:**
- Tasks 2-4 complete

**Steps:**
- [ ] Add/adjust tests for:
  - backend matrix (`bq=None`, BQ success, BQ transient retry, missing-column fallback)
  - degradation outcome contract
  - JSON normalization classes
- [ ] Run `uvx pytest tests/`.
- [ ] Run `uvx mypy src --show-error-codes`.
- [ ] Run `gitnexus_detect_changes()` and confirm affected symbols/files match planned scope.
- [ ] Run `python scripts/hooks/run_validator.py --fast`.
- [ ] If required, regenerate planning lineage (`python scripts/generate_planning_lineage.py`) and re-run validator.

**Verification:**
- [ ] Tests green.
- [ ] Type check green.
- [ ] GitNexus changed-scope report matches planned blast radius.
- [ ] Repo fast validator green.

**Exit Criteria:**
- patch set is regression-safe and lifecycle-valid

## Verification

- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- `gitnexus_detect_changes()`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
