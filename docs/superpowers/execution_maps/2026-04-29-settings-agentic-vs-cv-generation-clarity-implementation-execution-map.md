---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-operator-control-plane
map_type: implementation_execution
threads:
  - workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
specs:
  - docs/superpowers/specs/2026-04-29-settings-agentic-vs-cv-generation-clarity-spec.md
---

# Settings Agentic-vs-CV-Generation Clarity Implementation Execution Map

## Scope

Execute a bounded settings-page clarity patch so operators can distinguish:

- settings-owned non-agentic CV model controls
- runtime-owned agentic provider/model controls
- per-run truth verification surfaces

## Waves

### Wave 1: Render Context Contract

- `src/fitcv_cp/app.py`

Deliver:

- mode-aware summary payload:
  - agentic mode on/off
  - settings cv generation model
  - runtime provider/model
- per-field ownership/activity metadata for relevant keys

### Wave 2: Settings UI Restructure

- `src/fitcv_cp/templates/settings.html`

Deliver:

- compact mode status strip
- clearer ownership and activity labels near CV generation controls
- short run-detail alignment pointer

### Wave 3: Verification + Docs

- `tests/test_fitcv_cp/test_app.py`
- `docs/configuration.md`
- `docs/observability.md`

Deliver:

- tests proving clarity strings and mode/ownership rendering
- docs aligned with updated operator mental model

## Verification

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or run_detail"
python scripts/validate_repo_contracts.py --fast
```

## Execution order

1. context payload first
2. template changes second
3. tests/docs last
