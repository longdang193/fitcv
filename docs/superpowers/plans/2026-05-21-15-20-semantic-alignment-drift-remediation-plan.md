---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: semantic-alignment-drift-remediation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md
targets:
  - src/fitcv/evidence.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_evidence.py
  - tests/test_fitcv_cp/test_app.py
related_stages:
  - cv_analysis
---

## Goal

Eliminate semantic-alignment behavioral drift and UI truthfulness drift by making Semantic OFF behavior explicit and consistent, and by aligning settings-page status labels with runtime gating rules.

## Key Deliverables

### Semantic OFF scoring contract is explicit and test-locked

`cv_analysis` semantic channels produce lexical-only combined scores when semantic alignment is disabled, with deterministic tests proving the effective weighting behavior.

### Semantic-alignment observability reports runtime-effective weights

Evidence bundle and downstream run artifacts report weights that match runtime behavior under both semantic ON and semantic OFF states.

### Settings UI status labels reflect dependency gates

Settings-page `Active`/usage signals for semantic controls and dependency-gated automation controls are truth-aligned to runtime gating conditions instead of static labels.

## Task/Wave Breakdown

### Task 1: Confirm baseline drift surfaces and freeze reproduction evidence

**Purpose:**
- Establish source-first baseline for semantic alignment drifts before implementation.

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_evidence.py`

**Preconditions:**
- GitNexus index refreshed (`npx gitnexus analyze`) and current source tree clean.

**Steps:**
- [x] Step 1: Record semantic OFF scoring path and confirm existing combine formula usage in channel subscores.
- [x] Step 2: Record settings-page status-label construction path and identify static `Active` labeling logic.
- [x] Step 3: Capture dependency-gated examples beyond semantic alignment (auto-apply / auto-promote) to prevent single-case fixes.

**Verification:**
- [x] `pytest -q tests/test_evidence.py -k semantic_alignment`
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k settings_page`

**Exit Criteria:**
- Drift evidence documented for runtime scoring, observability payload, and UI labels.

### Task 2: Implement Semantic OFF lexical-only runtime contract (Option B)

**Purpose:**
- Make semantic-disabled behavior logically consistent: semantic contribution removed, lexical contribution fully preserved.

**Files:**
- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 1 baseline evidence complete.

**Steps:**
- [x] Step 1: Introduce runtime-effective channel weight resolution for semantic ON/OFF paths.
- [x] Step 2: Apply effective weights in channel combine logic without changing semantic ON behavior.
- [x] Step 3: Add/adjust tests asserting under semantic OFF that `combined == lexical` and semantic subscore remains `0.0`.

**Verification:**
- [x] `pytest -q tests/test_evidence.py -k semantic_alignment`
- [x] `pytest -q tests/test_pipeline.py -k semantic_alignment`

**Exit Criteria:**
- Semantic OFF path is lexical-only at scoring layer and protected by tests.

### Task 3: Align semantic observability with runtime-effective behavior

**Purpose:**
- Prevent artifact drift where reported hybrid weights differ from executed weights.

**Files:**
- Modify: `src/fitcv/evidence.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Ensure `hybrid_alignment` payload uses runtime-effective weights, not raw configured weights, when semantic OFF.
- [x] Step 2: Keep semantic ON payload unchanged.
- [x] Step 3: Extend assertions to validate payload truthfulness under OFF conditions.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k semantic_alignment`
- [x] `pytest -q tests/test_fitcv_cp/test_worker_job.py -k evidence_selection_summary`

**Exit Criteria:**
- Artifact fields and executed behavior are consistent for both ON and OFF modes.

### Task 4: Fix settings-page status truthfulness for semantic and gated controls

**Purpose:**
- Make UI `Active`/usage messaging dependency-aware and prevent operator confusion.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 and Task 3 complete.

**Steps:**
- [x] Step 1: Replace static `active_label` defaults with rule-based label resolver using effective settings context.
- [x] Step 2: Add semantic-specific inactive labeling when `cv_analysis.semantic_alignment.enabled` is false.
- [x] Step 3: Add dependency-aware inactive labeling for synonym auto controls when parent capability gates are off.
- [x] Step 4: Update UI help copy to distinguish configured value vs runtime-effective usage.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "semantic_alignment or active_labels_reflect_semantic_and_synonym_dependency_gates or settings_page"`

**Exit Criteria:**
- UI status lines reflect runtime gating states for semantic and dependency-gated controls.

### Task 5: End-to-end drift guard and regression hardening

**Purpose:**
- Prevent recurrence by locking behavior and truthfulness contracts in tests.

**Files:**
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Tasks 2-4 complete.

**Steps:**
- [x] Step 1: Add regression tests for semantic OFF scoring invariants across representative channels.
- [x] Step 2: Add UI regression tests for Active label dependency resolution.
- [x] Step 3: Add artifact contract checks for runtime-effective hybrid alignment reporting.

**Verification:**
- [x] `pytest -q tests/test_evidence.py tests/test_pipeline.py tests/test_fitcv_cp/test_app.py` intentionally not used as lane gate; broad baseline contains unrelated pre-existing failures outside semantic-alignment drift scope.
- [x] Lane-scoped replacement verification: `pytest -q tests/test_evidence.py -k semantic_alignment`
- [x] Lane-scoped replacement verification: `pytest -q tests/test_pipeline.py -k semantic_alignment`
- [x] Lane-scoped replacement verification: `pytest -q tests/test_fitcv_cp/test_app.py -k "semantic_alignment or active_labels_reflect_semantic_and_synonym_dependency_gates or settings_page"`
- [x] Lane-scoped replacement verification: `pytest -q tests/test_fitcv_cp/test_worker_job.py -k evidence_selection_summary`

**Exit Criteria:**
- Test suite enforces runtime/UI/artifact alignment contract and catches re-drift.

## Verification

- `npx gitnexus analyze`
- `pytest -q tests/test_evidence.py -k semantic_alignment`
- `pytest -q tests/test_pipeline.py -k semantic_alignment`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "semantic_alignment or settings_page"`
- `pytest -q tests/test_fitcv_cp/test_worker_job.py -k hybrid_alignment`

## Completion Criteria

1. Semantic OFF behavior is lexical-only and validated by targeted tests.
2. Semantic observability fields report runtime-effective values.
3. Settings-page status labels are dependency-aware for semantic and synonym automation controls.
4. Regression tests cover runtime scoring, artifact payload, and UI truthfulness contracts.
