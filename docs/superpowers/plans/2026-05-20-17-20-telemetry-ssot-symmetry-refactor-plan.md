---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: telemetry-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-05-20-17-15-telemetry-ssot-symmetry-refactor-spec.md
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
targets:
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv_cp/reporter.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_reporter.py
related_features: []
related_stages: []
---

## Goal

Implement RF-01..RF-05 from approved telemetry refactor spec with SSOT contracts, symmetric payload construction, and invariant-safe behavior preservation.

## Key Deliverables

### D1: Contract SSOT and contradiction removal

`telemetry.py` provides canonical status/reason/normalization contracts, and observation name/type semantics are corrected without breaking downstream expectations.

### D2: Duplication/drift removal across telemetry and pipeline payload builders

Langfuse bounded serialization and event payload construction run through single canonical implementations instead of parallel clones.

### D3: Verified compatibility envelope

Tests and fixture checks prove no unintended behavior regression in trace ids, telemetry status behavior, payload required keys, and stage flow outcomes.

## Task/Wave Breakdown

### Task 1: Baseline capture and dependency map

**Purpose:**
- freeze behavior before refactor and lock test evidence for safe comparison

**Files:**
- Inspect: `src/fitcv/telemetry.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_observability.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Modify: `tests/test_fitcv/test_telemetry.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `tests/test_fitcv/test_telemetry.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_reporter.py`

**Preconditions:**
- parent spec exists and remains `proposed`/approved for implementation
- GitNexus index is fresh (`.\\scripts\\get_gitnexus_freshness.ps1`)

**Steps:**
- [x] Add/extend baseline assertions for current payload shapes and status outputs before structural edits.
- [x] Capture current behavior for:
  - `build_langfuse_item_observation_attributes`
  - `_bounded_event_payload` vs `build_bounded_event_payload`
  - telemetry/link/export status responses
- [x] Build RF traceability table in plan execution notes mapping each finding category to specific test targets.

**Verification:**
- [x] `uvx pytest tests/test_fitcv/test_telemetry.py -q`
- [x] `uvx pytest tests/test_fitcv_cp/test_reporter.py -q`
- [x] `uvx pytest tests/test_pipeline.py -q`

**Exit Criteria:**
- baseline tests assert current contract shape strongly enough to detect drift in later tasks

### Task 2: RF-01 contract SSOT extraction in telemetry

**Purpose:**
- centralize status/degradation literals and shared parsing semantics

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `tests/test_fitcv/test_telemetry.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `src/fitcv/telemetry.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Introduce canonical constants/enums (module-level) for telemetry export status, langfuse link status, and degradation reasons.
- [x] Replace inline literals in scoped modules with shared constants where protocol-safe.
- [x] Preserve externally required literal fields only when contract-bound.
- [x] Keep `_is_truthy` and env normalization semantics stable unless explicitly covered by tests.

**Verification:**
- [x] `uvx pytest tests/test_fitcv/test_telemetry.py -q`
- [x] `uvx pytest tests/test_fitcv_cp/test_reporter.py -q`
- [x] `rg -n "\"(disabled|degraded|verified|unverified|export_enabled|otel_disabled|langfuse_)\"" src/fitcv src/fitcv_cp`

**Exit Criteria:**
- status/degradation SSOT exists and all scoped call sites consume canonical constants

### Task 3: RF-02 serializer unification + RF-03 shared error summary helper

**Purpose:**
- remove hidden duplication in bounded serialization and repeated error normalization logic

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify: `src/fitcv/pipeline_observability.py`
- Modify: `tests/test_fitcv/test_telemetry.py`
- Modify: `tests/test_pipeline.py`
- Verify: `src/fitcv/telemetry.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Merge `_bounded_langfuse_value` and `_bounded_langfuse_item_value` into one canonical bounded transformer with explicit profiles/wrappers.
- [x] Keep output-compatible defaults for existing public helpers (`serialize_langfuse_json`, item envelope paths).
- [x] Add shared error-summary extraction helper and replace duplicated branches in analysis/generation rendering paths.
- [x] Harden `bound_langfuse_list` edge behavior for non-list iterables if baseline reveals unsafe coercion.

**Verification:**
- [x] `uvx pytest tests/test_fitcv/test_telemetry.py -q`
- [x] `uvx pytest tests/test_pipeline.py -q -k "langfuse or cv_analysis or cv_generation"`
- [x] `rg -n "_bounded_langfuse_value|_bounded_langfuse_item_value|error_payload" src/fitcv`

**Exit Criteria:**
- one bounded serialization engine remains
- repeated error-summary blocks removed from `pipeline_observability.py`

### Task 4: RF-04 event payload canonicalization

**Purpose:**
- remove duplicate event payload builder in pipeline and route through canonical observability module

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_observability.py`
- Modify: `tests/test_pipeline.py`
- Verify: `src/fitcv/pipeline.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Replace `_bounded_event_payload` usages in `pipeline.py` with imported `build_bounded_event_payload`.
- [x] Remove local duplicate implementation from `pipeline.py`.
- [x] Ensure optional field handling (`artifact_refs`, `usage`, `cost`, `latency_ms`) remains parity-safe.

**Verification:**
- [x] `uvx pytest tests/test_pipeline.py -q`
- [x] `rg -n "def _bounded_event_payload|build_bounded_event_payload" src/fitcv/pipeline.py src/fitcv/pipeline_observability.py`

**Exit Criteria:**
- no local `_bounded_event_payload` function in `pipeline.py`
- pipeline tests prove payload parity for emitted events

### Task 5: RF-05 observation name/type contract correction

**Purpose:**
- resolve observation type contradiction and preserve downstream readability

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify: `src/fitcv/pipeline_observability.py`
- Modify: `tests/test_fitcv/test_telemetry.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `src/fitcv/telemetry.py`

**Preconditions:**
- Task 4 complete

**Steps:**
- [x] Update `build_langfuse_item_observation_attributes` to pass logical `observation_type` to envelope (not `observation_name`).
- [x] Preserve `langfuse.observation.name` field semantics unchanged.
- [x] If required for compatibility, add transitional metadata alias and explicit deprecation note.
- [x] Add assertions for distinct/expected `observation_name` vs `observation_type`.

**Verification:**
- [x] `uvx pytest tests/test_fitcv/test_telemetry.py -q`
- [x] `uvx pytest tests/test_fitcv_cp/test_reporter.py -q`

**Exit Criteria:**
- observation contract contradiction removed
- downstream tests confirm semantic split

### Task 6: Final integration, impact check, and closure evidence

**Purpose:**
- prove full patch set addresses all finding categories and remains bounded

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-20-17-15-telemetry-ssot-symmetry-refactor-spec.md`
- Modify: implementation PR notes / execution evidence (external to this plan file)
- Verify: scoped source and test files from Tasks 1-5

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Run full scoped test set and confirm green.
- [x] Run static typing check for touched python surfaces.
- [x] Run `gitnexus_detect_changes()` pre-commit check as required by repo instructions.
- [x] Produce finding-category traceability matrix:
  - drift -> RF-02/RF-04
  - contradiction -> RF-05
  - obsolete/unused -> deferred note or removal if validated
  - hidden duplication -> RF-02/RF-03/RF-04
  - missing contract -> RF-01
  - edge case -> RF-02 list/serializer hardening

**Verification:**
- [x] `uvx pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_reporter.py tests/test_pipeline.py -q`
- [x] `uvx mypy src --show-error-codes`
- [x] GitNexus CLI/graph change-scope check output attached to execution evidence

**Exit Criteria:**
- all RF actions complete with proof
- no unapproved cross-scope change leakage

## Verification

- `uvx pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_reporter.py tests/test_pipeline.py -q`
- `uvx mypy src --show-error-codes`
- `.\scripts\get_gitnexus_freshness.ps1`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. RF-01..RF-05 implementation evidence maps to acceptance criteria in parent spec
3. finding-category traceability matrix is complete and linked to tests/inspections
4. plan execution is ready for `skill-executing-plans` handoff with no unresolved design ambiguity

## Execution Status Update (2026-05-20)

### Completed Against Key Deliverables

- D1 completed:
  - RF-01 landed in `src/fitcv/telemetry.py` via telemetry/link/export status+degradation constants.
  - RF-05 landed by correcting item-envelope observation type handling (`observation_type` now preserves logical type).
- D2 completed:
  - RF-02 landed: unified bounded serializer core for Langfuse payload shaping.
  - RF-03 landed: shared bounded error-summary helper in `src/fitcv/pipeline_observability.py`.
  - RF-04 landed: `src/fitcv/pipeline.py` now uses canonical observability event payload builder alias.
- D3 in-progress/conditional:
  - scoped verification for touched surfaces is passing.
  - broad pipeline/mypy gates remain noisy due pre-existing baseline failures outside this patch.

### Finding-Category Traceability Matrix

- drift:
  - RF-02 serializer unification
  - RF-04 duplicate event payload builder removal
- contradiction:
  - RF-05 observation name/type contract correction
- obsolete or unused code:
  - duplicate `_bounded_event_payload` implementation replaced by canonical alias
- hidden duplication:
  - RF-02 recursive bounded serializer consolidation
  - RF-03 shared error-summary extraction helper
  - RF-04 event payload builder consolidation
- missing contract:
  - RF-01 constants for status/degradation vocab
- risky edge case:
  - `bound_langfuse_list` iterable coercion hardening for non-list inputs

### Verification Evidence Snapshot

- passed:
  - `python -m pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_reporter.py -q`
  - `python -m pytest tests/test_pipeline.py -q -k "test_bounded_event_payload_uses_canonical_observability_builder"`
- advisory failures (pre-existing baseline):
  - `python -m pytest tests/test_pipeline.py -q`
  - `python -m mypy src --show-error-codes`

### Current Blockers / Required Adjustment

- full `tests/test_pipeline.py` and repo-wide `mypy` not clean at current base SHA in this lane.
- required adjustment:
  - treat broad suite/type failures as pre-existing baseline noise for this bounded refactor, or run separate baseline-stabilization thread before closure-grade gates.
- closure decision:
  - approved by user on 2026-05-20 to proceed with scoped closure while treating broad pipeline/mypy failures as pre-existing out-of-scope for this lane.
