# 2026-05-02 Synonym Overlay Split Upload Controls and Guardrails Spec

## Metadata
- Date: 2026-05-02
- Owner surfaces: `src/fitcv_cp/templates/runs_list.html`, `src/fitcv_cp/templates/run_detail.html`, `src/fitcv_cp/app.py`, `src/fitcv/config.py`
- Type: operator UX safety hardening
- Related: run-scoped multi-field synonym overlay parity

## Problem Statement
Current upload mode uses one YAML file input for all synonym sections.  
Operators can accidentally mix `skill`, `domain`, and `role_family` sections when they intended to update only one field, causing unintended run-scoped changes.

## Goals
1. Add field-specific upload controls to reduce accidental mixing.
2. Preserve a combined upload path for advanced/batch usage.
3. Enforce payload-to-action alignment with clear validation errors.
4. Show explicit pre-apply section summary so operator sees what will change.

## Non-Goals
1. Replacing YAML-based overlay system.
2. Changing global promotion workflow.
3. Introducing auto-approval of proposals.

## UX Design

### A) Upload modes
Provide four explicit upload actions:
1. `Combined Upload` (existing broad behavior)
2. `Skills Upload`
3. `Domain Upload`
4. `Role Family Upload`

### B) Intent model
Each action submits an `overlay_upload_scope`:
- `combined`
- `skill`
- `domain`
- `role_family`

### C) Preview summary
Before apply (or in server-validated response), show:
- section counts:
  - `skill_synonyms`
  - `domain_alias_map`
  - `role_family_alias_map`
  - optional neighbors
- effective target scope

## Validation Rules

### Scope alignment
1. `combined`: any supported sections allowed.
2. `skill`: only `skill_synonyms` allowed.
3. `domain`: only `domain_alias_map` (+ optional `domain_neighbors`) allowed.
4. `role_family`: only `role_family_alias_map` (+ optional `role_family_neighbors`) allowed.

### Error behavior
On mismatch:
- return `422`
- message must state:
  - selected scope
  - found sections
  - allowed sections
- no config updates persisted

## Backend Changes

### A) Parser output usage
Reuse existing normalized multi-field payload from `parse_runtime_synonym_overlay_yaml`.

### B) Scope guard function
Add helper in app layer:
- `_validate_overlay_scope(payload, scope) -> None | raises HTTPException(422)`

### C) Endpoint wiring
Apply guard in both:
1. trigger upload endpoint (`/admin/upload-trigger`)
2. staged overlay replacement endpoint (`/admin/runs/{run_id}/synonym-overlay`)

## Template Changes

### Trigger page
- replace single generic upload toggle with:
  - combined upload tab
  - skill/domain/role_family scoped upload tabs or buttons
- include hidden `overlay_upload_scope` per action

### Run detail page
- for Stage-by-Stage replacement form:
  - include scope selector/buttons
  - include helper text for allowed sections

## Diagnostics and Events
For successful upload event payload include:
- `scope`
- `section_counts`
- `filename`

For failed scope validation include structured error in response detail.

## Backward Compatibility
1. Existing combined YAML behavior remains via `combined` scope.
2. Existing skill-only files continue to work.
3. API clients omitting scope default to `combined`.

## Acceptance Tests
1. Trigger upload with `scope=skill` rejects payload containing domain section.
2. Trigger upload with `scope=domain` accepts domain(+neighbors) only.
3. Trigger upload with `scope=role_family` accepts role_family(+neighbors) only.
4. Trigger upload with `scope=combined` accepts mixed payload.
5. Stage-by-Stage overlay replacement enforces same scope rules.
6. Render tests show separate controls/labels for combined + field-specific uploads.
7. Regression: existing combined upload tests still pass when scope omitted.

## Rollout Plan
1. Wave 1: backend scope validation + defaults.
2. Wave 2: trigger UI split controls + tests.
3. Wave 3: run detail split controls + diagnostics updates.

## Risks
1. Extra controls may increase UI complexity.
2. Strict scope enforcement may surprise users with legacy mixed files.

## Mitigations
1. Keep `combined` as default to preserve permissive path.
2. Provide clear error copy and examples for each scope.

## Done Criteria
1. Operators can upload per-field overlays without accidental cross-field updates.
2. Combined path remains available and explicit.
3. Scope mismatch is blocked with actionable validation.
4. Trigger and run-detail flows are parity-aligned.
