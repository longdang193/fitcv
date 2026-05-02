# 2026-05-02 Synonym Overlay Split Upload Controls and Guardrails Implementation Execution Map

## Metadata
- Date: 2026-05-02
- Source spec: `docs/superpowers/specs/2026-05-02-synonym-overlay-split-upload-controls-and-guardrails-spec.md`
- Objective: reduce accidental cross-field overlay updates by adding scoped upload controls and payload-scope validation

## Execution Principles
1. Keep `combined` upload path as backward-compatible default.
2. Enforce strict scope validation for field-specific uploads.
3. Keep trigger and Stage-by-Stage replacement behavior parity.
4. Ship UI clarity and diagnostics with backend validation.

## Wave Plan

## Wave 1: Backend Scope Validation Core
### Scope
- Implement scope guard helper and wire defaults.
- Validate payload sections against selected scope.

### File Ownership
- `src/fitcv_cp/app.py`
  - add `_validate_overlay_scope(...)`
  - apply guard in trigger upload + staged overlay replacement
  - default omitted scope to `combined`
- `tests/test_fitcv_cp/test_app.py`
  - scope mismatch/acceptance unit tests

### Deliverables
1. `scope=skill` rejects non-skill sections.
2. `scope=domain` accepts `domain_alias_map` (+ optional `domain_neighbors`) only.
3. `scope=role_family` accepts `role_family_alias_map` (+ optional `role_family_neighbors`) only.
4. `scope=combined` accepts mixed payload.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and overlay and scope"`

---

## Wave 2: Trigger UI Split Controls
### Scope
- Add explicit upload scope controls in trigger page.
- Submit scope with upload action.

### File Ownership
- `src/fitcv_cp/templates/runs_list.html`
  - add combined/skill/domain/role_family upload controls
  - helper text for allowed sections
- `src/fitcv_cp/app.py` (request parsing for scope)
- `tests/test_fitcv_cp/test_app.py` (render + submit path assertions)

### Deliverables
1. Trigger UI exposes distinct scoped upload choices.
2. Trigger submit carries `overlay_upload_scope`.
3. Existing flow without explicit scope remains `combined`.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "upload_trigger and synonym overlay"`

---

## Wave 3: Run Detail Split Controls + Diagnostics
### Scope
- Add scope control for Stage-by-Stage replacement form.
- Include scope in event diagnostics payload.

### File Ownership
- `src/fitcv_cp/templates/run_detail.html`
- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_app.py`

### Deliverables
1. Run detail replacement supports scoped upload modes.
2. Scope mismatch returns actionable `422` details.
3. Success events include `scope` + `section_counts`.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym-overlay and run_detail"`

---

## Cross-Wave Validation Checklist
1. Combined upload still works with old payloads.
2. Scoped uploads block unintended cross-field updates.
3. Trigger and run-detail upload behavior are consistent.
4. Diagnostics expose selected scope and applied section counts.

## Suggested Command Sequence
1. `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and overlay and scope"`
2. `pytest -q tests/test_fitcv_cp/test_app.py -k "upload_trigger and synonym overlay"`
3. `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym-overlay and run_detail"`
4. `pytest -q tests/test_config.py -k "overlay and synonym"` (regression guard)

## Rollback Strategy
1. Disable strict scoped validation while preserving controls (temporarily route all scopes as combined).
2. Keep backend parser/apply unchanged so existing combined flow remains stable.

## Done Criteria
1. Separate scoped upload actions exist and are test-covered.
2. Scope-payload mismatches are blocked safely.
3. Combined path remains backward-compatible.
4. Operator intent is explicit and auditable in diagnostics.
