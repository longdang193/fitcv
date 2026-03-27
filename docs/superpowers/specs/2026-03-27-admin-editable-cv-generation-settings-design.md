# Admin-Editable CV Generation Settings — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

CV generation is becoming a first-class configurable subsystem, but the admin UI does not yet expose those settings as a coherent editable surface.

If CV behavior is centralized in `config/cv.yaml` but remains invisible or inconsistently editable in the control plane, the product creates a gap between:

- where CV settings are defined
- where admins expect to tune runtime behavior

This would also create a new inconsistency in the settings UI if CV settings were added as ad hoc rows or a separate custom editor instead of following the section-card and grouped-form model already being established elsewhere.

---

## Goal

Add a fully admin-editable `CV Generation` settings area to the control plane that:

1. fits the shared settings-page composition model
2. exposes CV generation and validation settings as grouped forms
3. lets admins edit those settings without leaving the control plane

The UI should treat CV settings as a first-class policy surface, not a hidden file-only concern.

---

## Non-Goals

- Building a full template editor for CV markdown
- Rendering a live CV preview in this iteration
- Moving pipeline orchestration settings such as `pipeline.evidence_top_k` into the CV section
- Replacing the broader settings system with a custom CV-only editor

---

## Design

### Section Placement

Add a new top-level settings section:

- `CV Generation`

This section should appear alongside other top-level admin settings areas such as:

- `Retrieval Settings`
- `Timing Settings`
- `Global Job Filters`
- `Ranking`

It should use the same outer section-card composition as those sections.

---

### Section Structure

Inside `CV Generation`, render two sibling grouped sub-cards:

1. `Generation`
2. `Validation`

This follows the same structural principle used for grouped ranking settings:

- one semantic top-level section
- multiple grouped transactional sub-forms inside it

---

### Generation Group

The `Generation` sub-card should include:

- `CV Generation Model`
- `CV Template Path`
- `Prompt Version`

These fields belong together because they control how CV content is generated rather than how it is validated after generation.

The group should use one grouped save action:

- `Save Generation Settings`

---

### Validation Group

The `Validation` sub-card should include:

- `Required CV Sections`
- `Maximum CV Pages`

These fields belong together because they define the validation contract for generated CV output.

The group should use one grouped save action:

- `Save Validation Settings`

---

### Field Editing Model

The UI should remain fully admin-editable, but the editing controls should match the shape of the data.

Recommended controls:

- `CV Generation Model`
  - single-line text input
- `CV Template Path`
  - single-line text input
  - advanced setting
- `Prompt Version`
  - single-line text input
- `Required CV Sections`
  - grouped multi-value editor, not a raw YAML blob
- `Maximum CV Pages`
  - numeric input

For `Required CV Sections`, the first iteration may use a simple repeated text-input list if that is easiest to implement cleanly.

Expected list-editor behavior:

- add item
- remove item
- preserve item order
- reject duplicate section names
- reject empty or whitespace-only section names

The UI should avoid exposing raw YAML editing for these values in the settings page.

`CV Template Path` should follow the project’s standard config path convention and be validated accordingly.
It may remain editable as free text in the first iteration, but it should be presented as an advanced setting rather than a casual everyday control.

`Prompt Version` identifies which CV prompt variant/version is in use for generation and traceability.
It does not directly edit prompt content in this UI.

---

### Validation Rules

The admin UI should reflect the config contract clearly.

Required validation rules:

- `CV Generation Model`
  - non-empty string
  - whitespace-only value is invalid
- `CV Template Path`
  - non-empty string
  - whitespace-only value is invalid
- `Prompt Version`
  - non-empty string
  - whitespace-only value is invalid
- `Required CV Sections`
  - non-empty list
  - each item must be a non-empty string
  - whitespace-only items are invalid
  - duplicate items are invalid
- `Maximum CV Pages`
  - integer
  - must be `>= 1`

The backend remains the source of truth for validation, but the form should surface obvious issues before submit where practical.

---

### Settings-System Integration

This feature should integrate with the existing admin settings system, not bypass it.

That means:

- CV settings should be represented in the same schema/registry model as other admin-editable settings
- grouped save behavior should follow the same validate-first semantics used by other grouped forms
- the settings page should not introduce a custom one-off persistence path for CV configuration

Grouped CV settings submissions must validate the full subgroup before persisting any of its keys.
Invalid submissions must not partially update a subgroup.

The goal is consistency, not a special-case editor.

---

### Relationship to Existing Settings

`CV Generation` should own only CV-specific settings.

It should not absorb unrelated orchestration settings such as:

- `pipeline.evidence_top_k`

That value should remain outside this section because it affects retrieval/evidence orchestration, not just CV generation policy.

This keeps config ownership and UI ownership aligned.

---

### UX Consistency Rules

The new `CV Generation` area should follow the same settings-page composition rules as other sections:

- one outer section card
- grouped sub-cards inside that section
- one footer action per grouped sub-card
- shared table/form styling
- no row-level save buttons

This prevents the CV settings UI from becoming another exception in the settings page.

---

## Acceptance Criteria

- [ ] The settings page includes a top-level `CV Generation` section
- [ ] `CV Generation` contains two grouped sub-cards: `Generation` and `Validation`
- [ ] `Generation` includes editable controls for `CV Generation Model`, `CV Template Path`, and `Prompt Version`
- [ ] `Validation` includes editable controls for `Required CV Sections` and `Maximum CV Pages`
- [ ] Each CV subgroup uses one grouped save action rather than row-level saves
- [ ] Grouped CV settings submissions are validated fully before any subgroup keys are written
- [ ] The backend remains the source of truth for CV settings validation
- [ ] `Required CV Sections` uses structured list editing rather than raw YAML input
- [ ] Empty or whitespace-only CV field values are rejected by validation
- [ ] `CV Template Path` is validated according to the project’s path convention
- [ ] The UI integrates with the existing settings system rather than using a one-off persistence path
- [ ] `pipeline.evidence_top_k` remains outside the `CV Generation` section
