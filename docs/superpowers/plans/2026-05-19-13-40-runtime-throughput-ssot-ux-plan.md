---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: runtime-throughput-ssot-ux-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-19-13-36-runtime-throughput-ssot-ux-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement SSOT-aligned runtime-throughput UX so operators tune throughput in one canonical settings surface, while legacy aliases remain compatibility-only and non-primary.

## Key Deliverables

### Canonical runtime-throughput section registry

`src/fitcv_cp/app.py` exposes a single authoritative throughput card assembly path that owns editable canonical `stage_runtime.*` keys across enrich, ranking, cv_analysis, and cv_generation.

### Compatibility-surface-only legacy alias presentation

Legacy throughput alias keys are demoted from primary editable peers and represented as compatibility metadata/projection in UI context/rendering.

### Regression-safe UI contract proof

`tests/test_fitcv_cp/test_app.py` proves one ownership surface and preserves metadata truthfulness (`stage`, `control surface`, `runtime-used`) plus advanced disclosure semantics.

## Task/Wave Breakdown

### Task 1: Consolidate runtime-throughput registry ownership

**Purpose:**
- remove dual-surface throughput ownership in settings section registry

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec `docs/superpowers/specs/2026-05-19-13-36-runtime-throughput-ssot-ux-spec.md` approved for implementation
- `gitnexus impact` for `_build_settings_context` remains `LOW` risk

**Steps:**
- [x] Step 1: define one canonical throughput-key classifier/helper for editable canonical keys vs compatibility alias-only keys.
- [x] Step 2: replace dual card split (`Agentic Runtime Throughput` and `Advanced Runtime Tuning`) with one primary runtime-throughput card source.
- [x] Step 3: ensure save path remains compatible (`section/timing` behavior preserved) and no runtime schema behavior changes occur.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "settings_page_surfaces_late_stage_stage_runtime_controls_in_agentic_section" -q` passes with updated single-surface expectations.

**Exit Criteria:**
- exactly one primary editable throughput ownership path remains in section registry

### Task 2: Align template layout to SSOT ownership model

**Purpose:**
- make UI rendering match single ownership and compatibility-only alias semantics

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: render one canonical throughput card block with grouped canonical stage rows.
- [x] Step 2: keep alias linkage visible as compatibility metadata/help only, not as competing primary control rows.
- [x] Step 3: preserve filter and badge data attributes (`data-decision-stage`, `data-control-surface`, runtime-used badges) for canonical rows.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "admin_settings_late_stage_runtime_rows_have_truthful_stage_and_runtime_badges or admin_settings_renders_legacy_alias_keys_as_compatibility_surface" -q` passes.

**Exit Criteria:**
- template shows one canonical throughput control surface with truthful metadata and compatibility projection retained

### Task 3: Update and extend settings-page contract tests

**Purpose:**
- lock refactor with explicit assertions against SSOT regressions

**Files:**
- Inspect: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: update existing dual-card assertions to single-card ownership expectations.
- [x] Step 2: add/adjust tests asserting compatibility alias rows are non-primary and canonical rows remain primary runtime surface.
- [x] Step 3: retain advanced disclosure coverage with updated helper copy/placement semantics.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "settings and (runtime or advanced_disclosure or legacy_alias or late_stage)" -q` passes.

**Exit Criteria:**
- tests fully capture SSOT ownership and compatibility-only alias intent

### Task 4: End-to-end bounded verification and scope proof

**Purpose:**
- prove bounded refactor scope and closure readiness

**Files:**
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates/settings.html`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: run final targeted app/settings verification commands.
- [x] Step 2: run `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` and confirm changed symbols remain inside planned surfaces.
- [x] Step 3: run `python scripts/hooks/run_validator.py --fast`.

**Verification:**
- [x] all targeted commands pass
- [x] `gitnexus detect-changes` risk remains acceptable and scope-aligned
- [x] repo contract hook subset passes

**Exit Criteria:**
- implementation evidence is sufficient for execution closeout handoff

Task progress:
- Task 1 complete: consolidated throughput key classification and collapsed dual card model into canonical + compatibility surfaces in `src/fitcv_cp/app.py`.
- Task 2 complete: template rendering contract remained compatible; runtime/alias metadata assertions pass without additional template structural changes.
- Task 3 complete: settings runtime/legacy/advanced disclosure assertions pass for single-surface ownership model.
- Task 4 complete: targeted verification commands, `gitnexus detect-changes`, and validator hook executed.

## Verification

- [x] `pytest tests/test_fitcv_cp/test_app.py -k "settings_page_surfaces_late_stage_stage_runtime_controls_in_agentic_section or settings_page_uses_advanced_disclosure_for_expert_controls or admin_settings_late_stage_runtime_rows_have_truthful_stage_and_runtime_badges" -q` passes
- [x] `pytest tests/test_fitcv_cp/test_app.py -k "admin_settings_renders_legacy_alias_keys_as_compatibility_surface" -q` passes
- [x] `pytest tests/test_fitcv_cp/test_settings_schema.py -k "ia_contract or runtime_used" -q` passes
- [x] `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` completed (risk reported `critical` due generated instruction surfaces in repo-level scope; functional runtime-throughput symbols stayed bounded to settings surfaces).
- [x] `python scripts/hooks/run_validator.py --fast` passes

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




