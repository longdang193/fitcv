# 2026-05-02 Run-Scoped Multi-Field Synonym Overlay Parity Implementation Execution Map

## Metadata
- Date: 2026-05-02
- Source spec: `docs/superpowers/specs/2026-05-02-run-scoped-multi-field-synonym-overlay-parity-spec.md`
- Objective: make run-scoped synonym overlay apply consistently across `skill`, `domain`, and `role_family`, with backward compatibility and clear diagnostics

## Execution Principles
1. Preserve legacy skill-only overlay behavior while adding multi-field capability.
2. Keep overlay normalization deterministic and shared with config loader semantics.
3. Ensure trigger-time and in-run replacement behavior are parity-aligned.
4. Ship observability and UI wording updates with behavioral changes.

## Wave Plan

## Wave 1: Parser + Runtime Apply Core
### Scope
- Introduce generic overlay parser and apply helpers in config layer.
- Keep skill-only wrappers delegating to generic implementation.

### File Ownership
- `src/fitcv/config.py`
  - add `parse_runtime_synonym_overlay_yaml`
  - add `apply_runtime_synonym_overlay`
  - keep `parse_skill_synonym_overlay_yaml`/`apply_runtime_skill_synonym_overlay` compatibility wrappers
- `tests/test_config.py`
  - parser acceptance tests (legacy + multi-field)
  - normalization tests for alias/neighbor sections

### Deliverables
1. One canonical parsed payload shape for overlay sections.
2. Generic runtime apply function that merges skill/domain/role-family maps.
3. Zero regression for legacy skill-only call paths.

### Verification Gate
- `pytest -q tests/test_config.py -k "overlay and synonym"`

---

## Wave 2: Trigger + Replacement Endpoint Wiring
### Scope
- Wire trigger upload and stage-by-stage replacement endpoints to new parser/apply function.
- Persist per-field overlay metadata in effective settings.

### File Ownership
- `src/fitcv_cp/app.py`
  - parse uploaded YAML with generic parser
  - apply generic runtime overlay
  - enrich runtime metadata (`overlay_section_counts`, field flags)
- `tests/test_fitcv_cp/test_app.py`
  - upload-trigger and replacement tests for non-skill field application

### Deliverables
1. Trigger-uploaded YAML can modify domain/role-family maps for run scope.
2. Stage-by-stage replacement applies multi-field map updates.
3. Runtime metadata exposes field-level overlay usage.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym overlay and (upload or replacement or domain or role_family)"`

---

## Wave 3: UI + Diagnostics Parity
### Scope
- Update Trigger and Run Detail copy/inspection panels for multi-field overlay visibility.
- Show per-field section counts and applied status.

### File Ownership
- `src/fitcv_cp/templates/runs.html`
- `src/fitcv_cp/templates/run_detail.html`
- `src/fitcv_cp/app.py` (context payload for new UI fields)
- `tests/test_fitcv_cp/test_app.py` (render assertions)

### Deliverables
1. Trigger copy explicitly names skills/domain/role-family overlay support.
2. Run detail overlay card displays per-field section counts.
3. YAML snapshot remains available and truthful.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym overlay and run_detail"`

---

## Wave 4: Proposal-Regeneration Consistency
### Scope
- Ensure non-skill proposal queue regenerates against updated effective overlay.
- Verify suppression of now-covered mappings by field.

### File Ownership
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/worker_job.py` (only if trace/suppression summary wiring needs adjustment)
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_worker_job.py`

### Deliverables
1. Regenerate action reflects current multi-field effective map.
2. Suppression diagnostics remain field-correct after overlay updates.
3. Queue no longer shows stale non-skill pairs covered by uploaded overlay.

### Verification Gate
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and regenerate"`
- `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "suppressed_reason_counts_by_field"`

---

## Cross-Wave Validation Checklist
1. Legacy skill-only overlays continue to work unchanged.
2. Multi-field overlays affect ranking/proposal-relevant non-skill maps.
3. Trigger and replacement flows have parity behavior and metadata.
4. Run detail diagnostics and queue outcomes align with effective overlay state.

## Suggested Command Sequence
1. `pytest -q tests/test_config.py -k "overlay and synonym"`
2. `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym overlay"`
3. `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym and regenerate"`
4. `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "suppressed_reason_counts_by_field"`

## Rollback Strategy
1. Keep parser generic but gate non-skill apply via runtime flag if needed.
2. Temporarily disable non-skill overlay application while retaining skill path.
3. Preserve diagnostics payload to support postmortem and fast re-enable.

## Done Criteria
1. Run-scoped overlay supports skills/domain/role-family in one YAML.
2. UI and diagnostics make per-field overlay application explicit.
3. Proposal review reflects refreshed effective map for all fields.
4. Backward compatibility and targeted tests remain green.
