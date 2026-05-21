---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: routing-symmetry-and-settings-wording
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
related_features:
  - settings_system
related_stages:
  - enrich
---

## Goal

Eliminate cross-card overwrite bug in Agentic settings by enforcing routing symmetry between UI cards and backend section-save boundaries, then ship precise user-facing wording and guided prerequisite enforcement that separates capability permission from automation policy without silent state mutation.

## Key Deliverables

### Deliverable 1: Symmetric section-save routing for Agentic cards

Agentic `Enablement` and `Automation` cards each submit to distinct backend section slugs with disjoint keysets, so saving one card cannot mutate keys owned by other card.

### Deliverable 2: Regression-proof save behavior and tests

Route and payload behavior covered by route-level and schema-level tests proving unsubmitted keys remain unchanged and each save path persists only owned keys.

### Deliverable 3: Clear operator wording for Manual Capability Gate vs Automation

Settings descriptions and in-page instruction text updated to state exact gate/policy semantics, dependency rules, and safe operator sequence.

### Deliverable 4: Guided prerequisite enforcement for automation toggles

When an automation toggle is turned on while its required manual gate is off, save flow blocks and presents explicit operator choices (`Enable prerequisite and continue` or `Keep automation off`) instead of silently flipping state.

## Task/Wave Breakdown

### Task 1: Define symmetric section boundaries in schema

**Purpose:**
- Replace overloaded `agentic-core` section-save surface with explicit `agentic-enablement` and `agentic-automation` surfaces.

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Confirm current `AGENTIC_SETTINGS_SECTIONS` builder behavior and existing key ordering.

**Steps:**
- [x] Step 1: Add explicit section registry entries for `agentic-enablement` and `agentic-automation` with MECE key partition.
- [x] Step 2: Keep `agentic-advanced` mapping unchanged for non-target surfaces.
- [x] Step 3: Remove/retire implicit merged `agentic-core` save surface or keep as read-only compat alias that is not used by UI forms.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py -k agentic`

**Exit Criteria:**
- Schema exposes section slugs that mirror card ownership one-to-one.

### Task 2: Rewire settings cards to symmetric submit routes

**Purpose:**
- Ensure UI card action targets match new backend section slugs.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Update `settings_page_sections` card `submit_slug` for Enablement to `agentic-enablement`.
- [x] Step 2: Update `settings_page_sections` card `submit_slug` for Automation to `agentic-automation`.
- [x] Step 3: Confirm `all_settings_sections` lookup resolves both new slugs and no card references removed slug.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "agentic and section"`

**Exit Criteria:**
- Rendered form actions for both cards post to distinct symmetric section endpoints.

### Task 3: Add overwrite-regression tests

**Purpose:**
- Lock bugfix with direct tests for non-mutation guarantees.

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Add test: saving `agentic-enablement` does not change automation keys from active state.
- [x] Step 2: Add test: saving `agentic-automation` does not change enablement keys from active state.
- [x] Step 3: Add payload-capture assertions: each route persists only route-owned keys.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "agentic_enablement or agentic_automation or section_save"`

**Exit Criteria:**
- Tests fail on old coupled behavior, pass on symmetric routing.

### Task 4: Update wording/instruction surfaces

**Purpose:**
- Remove operator confusion around gate vs automation.

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: manual UI text inspection in rendered settings page

**Preconditions:**
- Tasks 1-3 complete.

**Steps:**
- [x] Step 1: Update descriptions for:
  - `Synonym Apply-to-Run (Manual Capability Gate)`
  - `Synonym Promote-Global (Manual Capability Gate)`
  - `Auto Apply Recommendation (Automatic Execution)`
  - `Auto Promote to Global (Automatic Execution)`
- [x] Step 2: Add concise help block in settings template:
  - gate = permission
  - automation = policy
  - 3-state matrix (`OFF/OFF`, `ON/OFF`, `ON/ON`)
  - dependency note (`OFF/ON` blocked)
- [x] Step 3: Keep wording symmetric across Apply and Promote flows.

**Verification:**
- [x] Render `/admin/settings` and verify exact copy placement and no contradictory labels.

**Exit Criteria:**
- Operator can infer correct behavior without external explanation.

### Task 5: Implement guided prerequisite enforcement (no silent auto-toggle)

**Purpose:**
- Keep UI simple while preserving explicit operator intent and auditability.

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 complete.

**Steps:**
- [x] Step 1: Add pre-submit guardrail in settings form JS:
  - if `Auto Apply = ON` and `Apply-to-Run = OFF`, raise prerequisite prompt.
  - if `Auto Promote = ON` and `Promote-Global = OFF`, raise prerequisite prompt.
- [x] Step 2: Prompt offers exactly two explicit actions:
  - `Enable prerequisite and continue`
  - `Keep automation off`
- [x] Step 3: Apply choice in form state before submit; do not mutate other keys.
- [x] Step 4: Add server-side validation mirror for direct POST safety:
  - reject inconsistent ON/OFF combination with clear error unless prerequisite key also ON in same payload.
- [x] Step 5: Ensure behavior symmetric for Apply and Promote pathways.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "prerequisite or auto_apply or auto_promote"`
- [x] UI behavior contract check: prerequisite prompt copy + deterministic server fallback verified through template inspection and route tests for ON/OFF prerequisite combinations.

**Exit Criteria:**
- No silent flips.
- Operator must explicitly choose prerequisite enable or automation-off fallback.

### Task 6: Spec and contract alignment

**Purpose:**
- Keep docs/tests aligned with behavior contract.

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md`
- Modify: `docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md`
- Verify: spec text matches implemented route/model semantics

**Preconditions:**
- Tasks 1-5 complete.

**Steps:**
- [x] Step 1: Add/adjust section describing symmetric save boundaries by decision area.
- [x] Step 2: Document gate/policy wording contract.
- [x] Step 3: Document prerequisite enforcement contract: block + explicit choice, no silent auto-enable.
- [x] Step 4: Ensure no outdated references to single `agentic-core` card-save behavior.

**Verification:**
- [x] `rg -n "agentic-core|agentic-enablement|agentic-automation|Manual Capability Gate|Automatic Execution" docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md`

**Exit Criteria:**
- Spec reflects final runtime + UI behavior and language.

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -k agentic`
- `pytest tests/test_fitcv_cp/test_app.py -k "agentic and section"`
- `pytest tests/test_fitcv_cp/test_app.py -k "enablement or automation or overwrite or section_save"`
- `pytest tests/test_fitcv_cp/test_app.py -k "prerequisite or auto_apply or auto_promote"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. All Key Deliverables satisfied.
2. All route-level and schema-level regression tests pass.
3. Wording/instruction copy is symmetric, dependency-correct, and visible in settings UI.
4. Automation prerequisite flow enforces explicit operator choice with no silent state mutation.

