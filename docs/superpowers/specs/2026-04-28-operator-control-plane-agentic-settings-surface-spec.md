---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
  - docs/usage.md
related_features:
  - settings_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Operator Control Plane Agentic Settings Surface

## Summary

Define the bounded operator-facing settings contract for supported agentic seams
so `/admin/settings` can expose real agentic runtime controls without blurring
the line between operator-tunable defaults, provider/setup glue, and run-scoped
inspection truth.

This spec extends the existing settings-system surface rather than creating a
separate control plane. The page should gain a clear `Agentic` section only if
there are real schema-backed, persisted, future-run defaults for those agentic
behaviors.

## Triage

Layer: `change`  
Feature type: `MODIFY`

Reasoning:

- the operator control plane already owns runtime-facing settings and controls
- the current settings page has no explicit surface for bounded agentic runtime
  controls
- the work touches one managed feature (`settings_system`) plus operator-facing
  explanation and inspection relationships
- the change is broader than a small template tweak because it requires schema,
  feature-contract, and UI truth alignment

Invariants:

- only real operator-tunable agentic settings may appear in the settings page
- provider secrets, deployment-only flags, and implementation glue stay out of
  `/admin/settings`
- agentic defaults remain future-run settings, not historical run truth
- run-scoped `settings-used.json` and observability surfaces remain the source
  of truth for what a run actually used
- deterministic acceptance and late-stage outcome contracts stay authoritative

Dependencies:

- `docs/features/settings_system/feature.source.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/intent/workstreams/threads/workstream-operator-control-plane/05-operator-control-plane-agentic-settings-surface.md`
- `docs/intent/workstreams/workstream-agentic-observability.md`
- `docs/intent/workstreams/workstream-bounded-agentic-cv-quality.md`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/app.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added because planning
lineage and managed contracts derive thread/spec linkage from source metadata.

Plan needed: `yes` after the bounded contract is approved.

## Problem

The current settings page is clearer and more truthful than before, but it
still has an operator-facing gap:

- agentic seams exist in the product roadmap and runtime direction
- operators can inspect some agentic behavior later in run detail or exports
- but there is no explicit settings surface for supported agentic defaults

That leaves two bad outcomes:

1. operators infer that agentic behavior is not configurable at all
2. future agentic knobs get added ad hoc under unrelated sections such as
   retrieval or advanced runtime tuning

This spec exists to keep agentic settings explicit, bounded, and owned.

## Goals

- identify which agentic runtime controls are genuinely operator-tunable
- define where those controls belong in the task-first settings surface
- distinguish editable agentic defaults from fixed metadata and from out-of-scope
  provider or setup controls
- connect the settings page to run-scoped observability and `settings-used`
  truth without making the settings UI a run-inspection surface

## Non-Goals

- no exposure of provider credentials, hidden model plumbing, or secret values
- no attempt to make every agentic payload or diagnostic configurable
- no replacement of run detail, event logs, or `settings-used.json`
- no synonym review queue or review action UI in this slice

## Proposed Contract

## 1. Agentic Settings Eligibility

A setting belongs in the operator-facing `Agentic` section only when all of the
following are true:

- the runtime uses it as a future-run default
- it is meaningful for operators to tune across runs
- it has a schema-backed persistence key
- changing it does not require redeploying, rotating secrets, or editing setup
  files directly

Examples of eligible classes:

- bounded enable/disable gates for approved agentic seams
- bounded scoring, threshold, or weighting defaults for approved agentic
  analysis or recommendation seams
- operator-facing pacing or fallback preferences when those are already runtime
  defaults rather than deployment-only settings

Examples of ineligible classes:

- API keys, auth, and provider credentials
- deployment-specific hostnames or cloud resources
- internal prompts or provider request-shape glue that operators should not
  manipulate directly

## 2. Agentic Section Placement

The settings page should gain a dedicated `Agentic` task section when there are
enough eligible controls to justify it.

Placement rules:

- agentic controls should not be hidden inside unrelated sections once they
  become a meaningful operator surface
- if there is only one truly eligible agentic control, it may remain in its
  runtime-adjacent section temporarily, but the contract should still identify
  it as agentic-owned
- advanced expert-only agentic tuning may still live behind disclosure inside
  the `Agentic` section

## 3. Editable vs Fixed Agentic Surface

The same fixed-versus-editable rules from the settings-system contract apply.

Agentic fields should render as:

- editable controls when they are real operator-tunable defaults
- metadata-only when the active runtime supports only one valid value but the
  setting still matters for explanation or provenance
- out of scope when the field belongs to setup or implementation glue

## 4. Truth Hierarchy

Agentic settings follow the same truth hierarchy as the rest of the page:

1. checked-in runtime defaults and contract
2. persisted active settings defaults
3. per-run overrides at trigger time
4. run-scoped `settings-used.json` and observability surfaces as historical
   truth

The settings page must not imply that changing an agentic default mutates any
previous run or changes a completed run’s agentic trace.

## 5. Relationship To Observability

The `Agentic` section should explain that:

- these controls affect future runs
- run detail and observability show what the agentic layer actually did
- `settings-used.json` remains the historical contract for the effective
  settings used by a specific run

The settings page should point operators toward those run-scoped surfaces
without trying to reproduce them inline.

## 6. Bounded First Surface

The first implementation should prefer a small, truthful surface.

Acceptable first scope:

- promote already-supported agentic defaults into explicit operator-facing
  schema groups
- add only a handful of real settings with strong ownership and tests
- keep advanced disclosures for expert-only agentic tuning

Unacceptable first scope:

- generic placeholder fields with no runtime owner
- provider knobs exposed only because they exist somewhere in code
- a large speculative section without stable capability ownership

## 7. Completion Criteria

This thread is complete when:

- `settings_system` names the operator-facing agentic settings capability
- the settings schema distinguishes editable, fixed, and excluded agentic
  surfaces from source-of-truth metadata
- `/admin/settings` exposes a bounded agentic section or clearly owned
  agentic-labeled controls
- tests prove save behavior, truth messaging, and omission of setup-only fields
- docs explain how agentic settings relate to `settings-used.json` and run
  detail observability

## Affected Runtime Surfaces

- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/settings.html`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_app.py`

## Affected Capability IDs

- `settings_system.task-first-settings-ui`
- `settings_system.advanced-settings-disclosure`
- `settings_system.metadata-only-fixed-controls`
- `settings_system.grouped-form-validation`
- `settings_system.trigger-time-effective-settings-snapshot`
- `settings_system.settings-used-exports`
- `inspection_debugging.settings-used-export`

## Validation Expectations

- add or update tests for schema-owned agentic setting classification
- add or update settings-page tests for explicit agentic section rendering when
  applicable
- verify metadata-only and excluded agentic fields are not persisted as editable
  settings
- refresh managed planning lineage and architecture metadata outputs

Minimum validation path:

```powershell
python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py
python scripts/generate_planning_lineage.py
python scripts/sync_architecture_docs.py
python scripts/sync_architecture_docs.py --check
python scripts/validate_repo_contracts.py --fast
```

## Rollout / Revert

- rollout should begin with one bounded, source-backed set of agentic controls
- revert by removing the new schema-backed agentic surface as one bounded slice
  if it drifts from actual runtime ownership
