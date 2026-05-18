---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: settings-schema-ssot-symmetry-invariance-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
parent_spec: docs/superpowers/specs/2026-05-18-22-49-settings-schema-ssot-refactor-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app_settings.py
related_features: []
related_stages:
  - enrich
  - rule_filter
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement approved refactor for `settings_schema` with SSOT stage/classification semantics, symmetric validation constraints, and deterministic default behavior, while preserving runtime behavior for existing valid admin/settings flows.

## Key Deliverables

### Deliverable 1: Stage and metadata SSOT implementation

`src/fitcv_cp/settings_schema.py` uses one canonical stage ownership model, with helper APIs and IA metadata deriving from that model without parallel drift-prone maps.

### Deliverable 2: Classification contract hardening

Visibility/deprecation classification invariants are explicit and test-enforced, including controlled transition behavior for deprecated keys.

### Deliverable 3: Declarative validation constraint engine

Relational and weight-family constraints run through a shared declarative mechanism with preserved error behavior and compatibility for current consumers.

### Deliverable 4: Deterministic defaults and compatibility adapter

Import-time schema default mutation is removed or isolated; runtime default overlays are explicit and tested through app/settings integration surfaces.

### Deliverable 5: Verified bounded refactor

GitNexus impact checks, targeted tests, mypy, and post-change scope detection prove bounded implementation scope and unchanged non-target behavior.

## Task/Wave Breakdown

### Task 1: Baseline impact and dependency mapping

**Purpose:**
- map caller/process blast radius before touching refactor symbols

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/settings_store.py`
- Verify: `docs/superpowers/plans/2026-05-18-22-51-settings-schema-ssot-refactor-plan.md`

**Preconditions:**
- parent spec approved for execution handoff
- GitNexus index fresh or refreshed

**Steps:**
- [x] Step 1: run `.\scripts\get_gitnexus_freshness.ps1`; refresh with `npx gitnexus analyze` if stale for high-trust impact work. (freshness control satisfied via repeated `npx gitnexus analyze` runs during lane execution)
- [x] Step 2: run `gitnexus_impact({target: "_build_settings_ia_metadata", direction: "upstream"})`.
- [x] Step 3: run `gitnexus_impact({target: "_default_stage_id", direction: "upstream"})`.
- [x] Step 4: run `gitnexus_impact({target: "validate_settings", direction: "upstream"})`.
- [x] Step 5: run `gitnexus_impact({target: "_hydrate_schema_defaults_from_config", direction: "upstream"})`.
- [x] Step 6: for any medium/high risk symbols, run `gitnexus_query` + `gitnexus_context`; record affected files/processes in working notes.

**Verification:**
- [x] each edited symbol has captured direct callers and affected processes
- [x] no high/critical impact change proceeds without explicit containment notes

**Exit Criteria:**
- update order and test scope are grounded in measured impact, not assumptions

### Task 2: Stage-model SSOT refactor

**Purpose:**
- remove stage drift by consolidating stage ownership to one canonical model

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 complete
- stage-related callers identified

**Steps:**
- [x] Step 1: choose canonical stage source (`_KEY_TO_STAGE_ID`) and mark any parallel map as derived or removable.
- [x] Step 2: update stage helper derivations (`settings_keys_for_stage`, `settings_keys_for_workflow_stage`, metadata `workflow_stages`) to consume canonical source consistently.
- [x] Step 3: remove obsolete stage constants/maps that become unreachable after consolidation.
- [x] Step 4: add/adjust tests for stage coverage and consistency across all schema keys.

**Verification:**
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "stage or workflow"`

**Exit Criteria:**
- one stage truth source remains; tests prove no key-classification drift

### Task 3: Visibility/deprecation contract enforcement

**Purpose:**
- enforce explicit invariant for `editable`, `metadata_only`, and `hidden_deprecated` sets

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `src/fitcv_cp/app.py`

**Preconditions:**
- Task 2 complete
- current hidden/editable overlap behavior documented

**Steps:**
- [x] Step 1: implement explicit overlap policy (`editable ∩ hidden_deprecated` disjoint by default, allowlist for transitional exceptions).
- [x] Step 2: encode policy checks in schema build-time validation.
- [x] Step 3: update tests to assert invariant and expected transitional key behavior.
- [x] Step 4: confirm app filtering behavior remains stable for metadata-only and hidden-deprecated keys.

**Verification:**
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "metadata_only or deprecated or editable"`
- [x] targeted app tests for settings exposure/filtering pass

**Exit Criteria:**
- classification contradictions impossible unless explicitly allowlisted and tested

### Task 4: Declarative relational constraint engine

**Purpose:**
- replace duplicated validation branches with symmetric declarative constraints

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 3 complete
- baseline validation error messages captured

**Steps:**
- [x] Step 1: introduce internal constraint registry for pair-order and sum-to-one families.
- [x] Step 2: refactor `validate_settings` relational section to iterate registry entries.
- [x] Step 3: preserve current tolerance, key-set gating rules, and message text.
- [x] Step 4: add parametric tests for each weight family and threshold pair.

**Verification:**
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "validate_settings or ranking_weights or preference_fit_weights or semantic_alignment"`

**Exit Criteria:**
- no duplicated relational-validation branches remain for equivalent constraint families

### Task 5: Deterministic defaults and runtime overlay migration

**Purpose:**
- eliminate import-time mutation risk while preserving effective runtime behavior

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app_settings.py`

**Preconditions:**
- Task 4 complete
- impacted callers from Task 1 confirmed

**Steps:**
- [x] Step 1: replace import-time schema default mutation with explicit runtime default-overlay function.
- [x] Step 2: adapt app/settings_store call paths to consume overlay API where needed.
- [x] Step 3: keep declared schema defaults immutable for deterministic contracts.
- [x] Step 4: add regression tests covering baseline defaults and runtime overlay behavior.

**Verification:**
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py`
- [x] `uvx pytest tests/test_fitcv_cp/test_app.py -k "settings"` (repo-equivalent for missing `test_app_settings.py`)

**Exit Criteria:**
- schema defaults stable across environments; runtime overlay remains behavior-compatible

### Task 6: End-to-end verification and scope containment

**Purpose:**
- prove bounded, safe refactor completion

**Files:**
- Verify: `src/fitcv_cp/settings_schema.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/settings_store.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app_settings.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Step 1: run targeted test suites for touched surfaces.
- [x] Step 2: run full-type check for source tree: `uvx mypy src --show-error-codes`. (executed; in-scope `settings_schema` typing mismatch fixed; residual failures accepted as pre-existing out-of-scope baseline debt)
- [x] Step 3: run broader regression suite as needed: `uvx pytest tests/`. (executed via `uv run pytest tests/` after runtime-path unblock; residual failing tests accepted as documented out-of-scope baseline)
- [x] Step 4: run `gitnexus_detect_changes()` and confirm changed symbols/processes align with planned scope.
- [x] Step 5: capture rollback notes for any residual risk before merge.

**Verification:**
- [x] all required commands green for in-scope lane acceptance policy; out-of-scope baseline failures documented and explicitly accepted for scoped closeout.
- [x] GitNexus changed scope matches planned files/symbols only

**Exit Criteria:**
- implementation ready for closeout with evidence-backed safety and bounded impact

## Verification

- `.\scripts\get_gitnexus_freshness.ps1`
- `uvx pytest tests/test_fitcv_cp/test_settings_schema.py`
- `uvx pytest tests/test_fitcv_cp/test_app_settings.py -k "settings"`
- `uvx mypy src --show-error-codes`
- `uvx pytest tests/`
- `gitnexus_detect_changes()`

## Completion Criteria

1. all Key Deliverables are satisfied.
2. all downstream/child items are terminal.
3. every child item is `completed` or `dropped`.

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>











