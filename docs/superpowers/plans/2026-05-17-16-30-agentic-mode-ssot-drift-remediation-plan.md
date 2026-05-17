---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: agentic-mode-ssot-drift-remediation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-17-14-38-settings-page-deprecated-surface-removal-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/bq_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - docs/configuration.md
  - docs/superpowers/execution_context_packs/settings-page-deprecated-surface-removal/latest.md
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Eliminate single-source-of-truth drift in `/admin/settings` mode strip by unifying authority semantics for `Agentic Mode`, `Live Provider`, and `Live Model`, while preserving bounded compatibility behavior and backend symmetry.

## Key Deliverables

### Deliverable 1: Mode-strip authority contract is explicit and invariant

Define and implement one canonical runtime-authority resolver for mode-strip fields so all rendered values come from one coherent source contract (no mixed settings/env truth without explicit status annotation).

### Deliverable 2: SQLite settings persistence parity is fully integrated in operator flow

Keep sqlite-mode settings persistence restart-safe and ensure admin settings retrieval/write paths use persistent store semantics consistent with BigQuery latest-row behavior.

### Deliverable 3: Drift observability and docs are aligned

Add deterministic diagnostics/tests/documentation that classify mode-strip state as `aligned` or `drifted` and describe operator remediation path.

## Task/Wave Breakdown

### Task 1: Define canonical mode-strip authority resolver

**Purpose:**
- establish SSOT semantics for strip fields and drift classification

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- current settings-surface deprecation patch is merged in working tree
- existing mode-strip behavior confirmed from live page

**Steps:**
- [x] Step 1: add internal resolver that computes `agentic_mode`, `runtime_provider`, `runtime_model`, and `authority_state` from one explicit authority contract.
- [x] Step 2: prevent silent mixed-authority rendering by attaching `drift_reason` when env runtime differs from settings-mode expectations.
- [x] Step 3: wire resolver output into settings context; remove ad hoc per-field assembly.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k "mode_summary_strip or agentic_mode"`

**Exit Criteria:**
- mode strip fields render from one resolver contract with explicit drift state

### Task 2: UI and copy alignment for drift-safe operator semantics

**Purpose:**
- ensure UI communicates authority and drift without exposing deprecated controls

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `docs/configuration.md`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: render `authority_state`/`drift_reason` note in strip area with minimal visual noise.
- [x] Step 2: keep deprecated fields hidden and unchanged from prior patch boundaries.
- [x] Step 3: update docs to define strip semantics and remediation guidance.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k "settings and (mode_summary or hidden_deprecated)"`

**Exit Criteria:**
- operator can distinguish aligned vs drifted mode-strip state directly from UI

### Task 3: Persistence-parity hardening check (bounded)

**Purpose:**
- confirm sqlite settings persistence contract remains stable and bounded

**Files:**
- Inspect: `src/fitcv_cp/settings_store.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: verify no regression in sqlite `pipeline_settings` latest-row behavior.
- [x] Step 2: add/adjust tests for restart-safe retrieval of `cv.agentic_late_stage.enabled` and related mode-strip dependencies.
- [x] Step 3: classify non-settings in-memory fallbacks in `bq_store.py` as deferred risk (no broad refactor in this patch).

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- [x] `pytest tests/test_fitcv_cp/test_settings_store.py -q`

**Exit Criteria:**
- sqlite settings persistence parity validated; broader fallback risks explicitly deferred

### Task 4: Final verification and context-pack sync

**Purpose:**
- close patch slice with verifiable evidence and synchronized execution artifacts

**Files:**
- Modify: `docs/superpowers/execution_context_packs/settings-page-deprecated-surface-removal/latest.md`
- Optional Modify: `artifacts/execution_context_pack.md`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: run full `test_app` suite for settings-lane regression evidence.
- [x] Step 2: run fast validator hook.
- [x] Step 3: update canonical execution context pack with evidence, residual risks, and selected next action state.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- evidence complete; context pack reflects latest SSOT-remediation state

## Verification

- `pytest tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- `pytest tests/test_fitcv_cp/test_settings_store.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -q`
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

## Execution Progress Log

- 2026-05-17: Task 1 completed. Added canonical mode-summary resolver in `src/fitcv_cp/app.py` with `authority_state` and `drift_reason`.
- 2026-05-17: Task 2 completed. Updated settings strip in `src/fitcv_cp/templates/settings.html`; updated docs in `docs/configuration.md`; added drift summary regression test.
- 2026-05-17: Task 3 completed. Verified sqlite settings persistence tests remain green and explicit for `cv.agentic_late_stage.enabled`.
- 2026-05-17: Task 4 completed. Full `test_app` suite passed (`389 passed`) and `python scripts/hooks/run_validator.py --fast` passed.
