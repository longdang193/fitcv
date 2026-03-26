# Admin UI Consistency and Theme Toggle — Design Spec

**Date:** 2026-03-26
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The FitCV Admin UI currently feels like multiple adjacent interfaces rather than one coherent control plane.

The main inconsistencies are:

- action buttons use different sizes, placements, and visual weights for similar actions
- page sections use different spacing and density patterns
- settings groups mix per-row forms and grouped forms without a shared action hierarchy
- raw group names such as `global_job_filters` leak into the UI
- the current visual system is dark-only, with no user-selectable light theme

These inconsistencies increase cognitive load and make the admin UI feel improvised rather than systematic.

---

## Goal

Define a shared admin design system so the control plane feels visually and behaviorally consistent across:

- runs list
- settings
- run detail

Also add a user-toggle between dark and light themes, with the chosen theme persisting across pages.

The admin should experience:

- one clear visual hierarchy for actions
- one consistent layout and spacing system
- one set of reusable component patterns
- predictable dark and light theme behavior

---

## Non-Goals

- Full information-architecture redesign of the control plane
- Rewriting admin pages into a frontend framework
- Adding per-user server-side theme persistence
- Reworking underlying backend behavior unrelated to UI consistency

---

## Design

### Shared Design System

The admin UI should move to a shared visual system defined at the base layout level.

This system should use semantic CSS custom properties for:

- background surfaces
- text colors
- borders
- primary actions
- secondary actions
- badges and status states
- table headers and row hover states
- form fields and focus states

All page templates should consume the same shared tokens rather than defining page-local styles that drift over time.

Shared visual primitives for buttons, cards, tables, forms, badges, spacing, and theme tokens should be defined centrally in `base.html` or one shared stylesheet block and reused across templates.

Page templates should avoid introducing page-local styling unless the pattern is truly page-specific.

Primary implementation anchor:

- `src/fitcv_cp/templates/base.html`

### No-Drift Rule

The design system should explicitly prevent visual drift from reappearing over time.

Avoid:

- template-local button styles for common actions
- one-off spacing hacks for standard sections
- page-specific input variants without a clear page-specific reason
- ad hoc redefinitions of table, badge, card, or form primitives

New shared UI behavior should be added to the central design system first, then consumed by templates.

---

### Theme Model

The admin UI should support two user-selectable themes:

1. dark
2. light

The selected theme should be applied through a root attribute such as:

- `data-theme="dark"`
- `data-theme="light"`

Theme switching should:

- happen client-side
- affect all pages consistently
- persist across page reloads using `localStorage`

Recommended behavior:

- default to the current dark theme when no preference is saved
- theme toggle lives in the top navigation bar
- toggle updates the root theme attribute immediately
- saved preference is applied on page load before the page visibly flashes the wrong theme

Implementation note:

- apply the saved theme from `localStorage` using a very small inline script in `base.html` before visible content renders

This feature is a user preference, not a server-side setting.

---

### Action Hierarchy

The UI should use a consistent action hierarchy across all admin pages.

Define at least three action styles:

1. primary action
2. secondary action
3. section action

#### Primary action

Use for the main action in a section or card.

Examples:

- `Trigger Run`
- grouped settings save actions

Primary actions should:

- be visually prominent
- have consistent height, padding, radius, and font weight
- appear in predictable locations such as section footers or card action rows

#### Secondary action

Use for supporting actions that matter but are not the main CTA.

Examples:

- `Refresh Status`
- theme toggle

Secondary actions should not visually compete with the primary CTA.

#### Section action

Use for a coherent section of independent settings that are edited together.

Examples:

- `Save Retrieval Settings`
- `Save Timing Settings`
- `Save Global Job Filters`

Section actions should:

- appear once per section, typically in the section footer
- be visually consistent with grouped-save actions, while remaining scoped to one section
- avoid repeating many tiny `Save` buttons across otherwise similar rows

This distinction is especially important on the settings page, where the UI should not mix repeated row-level saves with group saves that have very different scope.

---

### Settings Page Consistency

The settings page should become structurally consistent within itself.

Rules:

- human-readable group headings only
- no raw internal identifiers such as `global_job_filters`
- grouped ranking forms should look like intentional grouped sections, not like ad hoc exceptions
- independent settings sections should use one section-form pattern
- grouped ranking sections should share one group-card pattern

Recommended presentation model:

- page title + intro text
- settings sections as stacked cards or clearly separated panels
- each section with a visible header, optional helper text, body, and action area

For settings specifically:

- independent sections use section-level save actions
- grouped ranking forms use footer-aligned primary save buttons
- grouped ranking forms should visually reinforce their transactional save scope and differ clearly from simpler section-level settings forms
- button labels should follow consistent conventions

Examples:

- section-level actions: `Save Retrieval Settings`, `Save Timing Settings`, `Save Global Job Filters`
- group-level actions: `Save Weights`, `Save Fit Thresholds`, `Save Gap Thresholds`

Avoid mixing:

- repeated row-level save buttons
- footer actions with inconsistent scope
- inconsistent button text verbosity

within the same page without a clear pattern.

---

### Cross-Page Layout Consistency

The runs list, settings page, and run-detail page should share the same page-level structure.

Each page should consistently use:

- page header row
- optional page-level actions on the right
- card containers with shared padding and border radius
- consistent table styling
- consistent section spacing

The goal is not to make every page identical, but to make them clearly belong to the same system.

---

### Forms and Inputs

Input controls should follow one shared style system across all pages.

This includes:

- text inputs
- number inputs
- file inputs where practical
- textareas
- tab-like mode selectors

Shared rules should cover:

- height
- padding
- border radius
- border colors
- focus state
- disabled state

Grouped forms and row forms should differ by layout, not by unrelated input styling.

---

### Table and Section Rules

Tables should share one common pattern across the admin UI:

- consistent header background
- consistent uppercase header treatment
- consistent row padding
- consistent hover state
- consistent empty-state styling

Status badges should also use one shared semantic pattern across all pages, including:

- success
- warning
- error
- neutral or info

Badge color, contrast, and label formatting should remain consistent in both dark and light themes.

Section headers should also follow one pattern:

- title
- optional subtitle/helper text
- optional action area

This avoids the current mix of plain headings, table headings, and ad hoc inline explanatory text.

---

### Naming and Display Normalization

Internal keys and implementation names should not leak directly into the UI unless they are explicitly useful for debugging.

Examples that should be normalized:

- `global_job_filters` → `Global Job Filters`
- raw slug-like group labels
- inconsistent capitalization across sections

The UI should use human-readable labels consistently across both dark and light themes.

---

### Light Theme Requirements

The light theme should not be a low-effort inversion of the dark theme.

It must preserve:

- sufficient contrast for data tables
- readable muted text
- clear border separation between surfaces
- strong status badge visibility
- visible focus states for keyboard users

Special attention is required for:

- table header backgrounds
- row hover states
- badge colors
- form input borders
- helper text and metadata text

The design system should define separate semantic tokens for light mode rather than reusing dark values with minor tweaks.

### Accessibility and Responsiveness

Focus-visible states, table contrast, and form readability must remain clear in both themes.

Key states should not rely on color alone.

At narrower widths:

- section headers and action rows should wrap cleanly
- forms should remain usable without overlapping controls
- wide tables may overflow horizontally rather than collapsing into broken layouts

---

### Initial Scope

Apply the consistency and theming system to:

- `base.html`
- `runs_list.html`
- `settings.html`
- `run_detail.html`

This should be enough to make the admin control plane feel coherent end-to-end.

---

## Acceptance Criteria

- [ ] The admin UI has a shared token-based visual system defined in the base layout
- [ ] Shared button, card, table, form, and badge styles are defined centrally and reused across templates
- [ ] A user can toggle between dark and light themes from the admin UI
- [ ] Theme preference persists across page loads
- [ ] Theme preference is applied before visible content renders to avoid theme flash
- [ ] Runs, Settings, and Run Detail pages use consistent card, table, input, and section patterns
- [ ] Action hierarchy clearly distinguishes primary, secondary, and section-level actions, and any remaining inline row actions are visually subordinate and used intentionally
- [ ] Grouped ranking save buttons and section-level settings save buttons use intentionally different but consistent action styles
- [ ] Raw internal group names are replaced with human-readable labels in the UI
- [ ] Light theme remains readable and usable for tables, badges, forms, and helper text
- [ ] Focus states and status badges remain readable and distinct in both themes
