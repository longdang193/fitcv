---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/run_detail.html
  - docs/configuration.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_generation
  - cv_analysis
---

# Settings Clarity: CV Generation Model vs Agentic Controls

## Summary

Clarify ownership and runtime behavior on `/admin/settings` so operators can
immediately understand:

1. when `cv_generation_model` is active
2. when agentic live runtime provider/model are active
3. where each control is edited
4. where actual run-used truth is verified

This is a UI-contract clarity change, not a generation-logic rewrite.

## Problem

Current settings presentation mixes two control planes:

- settings-backed future-run defaults (for non-agentic generation path)
- env/runtime-managed live provider bridge (for agentic generation path)

This causes operator confusion:

- users expect `cv_generation_model` to control all CV generation modes
- users are unsure why run artifacts show a different provider/model
- current explanation is verbose and easy to miss in long “Settings Truth” text

## Goals

- make control ownership explicit at field level
- make active-mode implications explicit next to affected controls
- keep provider secrets and setup-only values non-editable
- connect settings page to run-detail runtime provenance check

## Non-Goals

- no new provider credential editing on settings page
- no migration of env runtime controls into persisted settings
- no change to agentic generation business logic in this slice

## Proposed UX Contract

## 1. Split CV generation controls by mode ownership

Settings page should expose two distinct conceptual groups:

### A) Non-Agentic CV Generation (settings-owned)

- includes `cv_generation_model`
- includes prompt/composition controls already owned by settings
- explicitly labeled as active when agentic late-stage is OFF

### B) Agentic Live Generation (runtime-owned, read-only)

- displays current runtime provider/model provenance source (env-managed)
- shows values as metadata-only (not editable in settings)
- includes pointer to setup ownership docs and run-detail runtime alignment

## 2. Per-field ownership + activity badges

Each relevant row should display:

- `Owner: Settings` or `Owner: Runtime Env` (or equivalent short copy)
- `Active: Yes/No` relative to current mode (`cv.agentic_late_stage.enabled`)

For `cv_generation_model`, when agentic mode is enabled:

- show “Active: No (used when agentic mode is OFF)”

## 3. Compact mode status strip (replace verbose ambiguity)

At top of settings page, add compact status facts:

- `Agentic Late-Stage: ON/OFF`
- `Runtime Provider: <value or —>`
- `Runtime Model: <value or —>`
- `Settings CV Generation Model: <value or —>`

Purpose:

- make relationship visible without reading long explanatory prose

## 4. Explicit link to run-truth verification

Settings page should include one short operator action:

- “Verify actual provider/model on a run in Run Detail → Agentic Runtime Alignment”

This keeps historical truth in run surfaces, not in settings assumptions.

## 5. Copy constraints

Copy should be:

- short and operational
- mode-specific
- non-technical where possible

Avoid:

- long “contract essay” text blocks
- wording that implies env/runtime values are editable here

## Data/Behavior Contract

Inputs required by settings render context:

- effective `cv.agentic_late_stage.enabled`
- effective `cv_generation_model`
- runtime env-derived provider/model summary (read-only)

No new persistence keys required.

## Acceptance Criteria

- operator can answer in one glance:
  - which model controls non-agentic CV generation
  - whether agentic live runtime is active
  - which runtime provider/model is currently configured
- settings page no longer implies `cv_generation_model` controls agentic live path
- run-detail drift/alignment remains the source for per-run actual execution truth
- no editable provider credential/runtime-bridge controls are introduced

## Validation

Minimum checks:

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or run_detail"
python scripts/validate_repo_contracts.py --fast
```

Manual checks:

1. with agentic mode OFF, confirm `cv_generation_model` shows active
2. with agentic mode ON, confirm `cv_generation_model` shows inactive-for-agentic note
3. confirm runtime provider/model are visible as read-only metadata
4. confirm settings page includes direct pointer to run-detail runtime alignment

## Risks

- too much copy can preserve confusion instead of reducing it
- ownership badges without active-mode badge may still be ambiguous
- mixing runtime facts into editable controls can regress trust

## Next Artifact

Implementation plan with 3 bounded waves:

1. settings page mode/ownership UX restructure
2. context payload and metadata wiring
3. tests + docs touch-up
