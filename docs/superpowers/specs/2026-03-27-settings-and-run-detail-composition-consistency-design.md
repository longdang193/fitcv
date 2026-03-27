# Settings and Run Detail Composition Consistency — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

Two parts of the admin UI still break the shared composition model defined in the broader UI consistency work:

1. the `Ranking` area on the settings page is visually treated like one long custom mega-block, even though it actually contains three distinct grouped forms with separate save scopes:
   - `Ranking Weights`
   - `Fit Label Thresholds`
   - `Gap Thresholds`
2. the run-detail inspection tabs (`Enriched Jobs`, `Original Job Input`, `Candidate Profile`) use a tab/pane border treatment that feels different from the shared section-card system, making the inspection area look like a separate UI kit

These inconsistencies are not just cosmetic. They weaken the admin’s mental model of:

- where section boundaries are
- which save action belongs to which form
- which surfaces are built from shared primitives versus page-local exceptions

They also violate the DRY direction of the admin UI design system by encouraging page-specific composition rules.

---

## Goal

Make the settings page and run-detail inspection area use the same shared composition system as the rest of the admin UI.

Specifically:

1. keep `Ranking` as one semantic top-level settings section, but render its three grouped forms as three sibling sub-cards instead of one merged block
2. render the run-detail inspection area as one shared inspection card with an attached tab bar and one consistent pane container

The result should feel systematic:

- top-level sections use one card model
- grouped sub-forms use one sub-card model
- tabbed inspection uses one attached-tab inspection-card model
- shared border, radius, spacing, and background rules live centrally

---

## Non-Goals

- Redesigning the ranking grouped-editing behavior itself
- Changing validation or save semantics for ranking groups
- Redesigning the contents of the enriched jobs table
- Replacing the run-detail tab model
- Creating a new general-purpose component framework

---

## Design

### Shared Composition Principle

The admin UI should distinguish clearly between:

1. top-level section cards
2. grouped sub-cards inside a section
3. inspection cards with attached tabs

These are composition patterns, not one-off page-specific exceptions.

Shared composition primitives should be defined centrally in:

- `src/fitcv_cp/templates/base.html`

Templates should compose those primitives rather than recreate border, spacing, or attachment rules inline.

---

### Settings Page: Ranking Section Structure

The settings page should keep `Ranking` as a single top-level section, consistent with:

- `Retrieval Settings`
- `Timing Settings`
- `Global Job Filters`

But the content inside `Ranking` should no longer appear as one long uninterrupted block.

Instead:

- `Ranking` is one top-level section card
- inside it, render three sibling grouped sub-cards

Required subgroup structure:

1. `Ranking Weights`
2. `Fit Label Thresholds`
3. `Gap Thresholds`

Each subgroup should use the same internal pattern:

- subgroup header
- subgroup helper text
- subgroup table/form body
- subgroup footer action row

This makes the save scope visually match the transactional scope.

---

### Settings Page: Why One Outer Ranking Section Still Exists

`Ranking Weights`, `Fit Label Thresholds`, and `Gap Thresholds` should not become three unrelated top-level cards.

They are still part of one conceptual policy area: ranking behavior.

Therefore the right hierarchy is:

- top-level section: `Ranking`
- child grouped forms: `Weights`, `Fit Thresholds`, `Gap Thresholds`

This preserves semantic grouping while avoiding the current visual problem where all three groups look like one continuous custom block.

---

### Ranking Sub-Card Rules

The ranking subgroup cards should follow one shared sub-card pattern.

Required rules:

- each subgroup has its own bordered container inside the outer ranking section
- subgroup spacing is consistent between all three cards
- subgroup header text uses the same type scale and spacing
- subgroup save action is footer-aligned within that subgroup only
- no subgroup should visually run directly into the next one without a clear container boundary

This pattern should be reusable for future grouped settings forms if more appear later.

---

### Run Detail: Inspection Card Model

The run-detail inspection area should use one shared inspection-card composition:

- attached tab bar on top
- one bordered pane container below
- active pane content rendered inside that container

This should replace the current look where the tab bar and pane body feel visually detached from the shared card system.

The inspection area should read as one card with tabbed views, not as separate border treatments layered on top of each other.

---

### Attached Tab Bar Rules

The tab bar should be visually attached to the inspection card.

Required rules:

- tabs sit on the top edge of the inspection card
- active tab blends into the active pane body
- inactive tabs remain visually subordinate
- the border relationship between tab bar and pane body is shared and consistent
- tab spacing, radius, and active-state treatment come from shared styles, not page-local overrides

This should be a reusable tabbed-inspection pattern, not something unique to run detail.

---

### Inspection Pane Rules

All three inspection panes must share one pane container style:

- same border
- same radius
- same inner padding
- same top-edge attachment behavior relative to the tab bar
- same background and divider behavior

This applies to:

1. `Enriched Jobs`
2. `Original Job Input`
3. `Candidate Profile`

The pane content itself may differ, but the outer container should not.

---

### DRY Rule

The fix should not introduce new page-local layout hacks.

Therefore:

- shared sub-card styles belong in `base.html`
- shared attached-tab inspection styles belong in `base.html`
- `settings.html` should only compose ranking section + subgroup cards
- `run_detail.html` should only compose inspection card + shared tab/pane primitives

Avoid:

- inline border/radius tweaks for ranking subgroup layout
- run-detail-only tab border logic duplicated in the template
- separate visual definitions for card-like containers that differ only slightly from existing shared primitives

---

### Visual Consistency Rules

After this change:

- the outer `Ranking` section should align visually with other top-level settings sections
- the three ranking groups should read as sibling transactional units
- the run-detail inspection area should read as one tabbed card
- border thickness, corner radius, spacing, and background stacking should feel like part of one design system

The goal is not maximum visual variety. The goal is coherent structural hierarchy.

---

## Acceptance Criteria

- [ ] The settings page keeps `Ranking` as one top-level section card
- [ ] `Ranking Weights`, `Fit Label Thresholds`, and `Gap Thresholds` render as three sibling subgroup cards inside the outer ranking section
- [ ] Each ranking subgroup has its own clear header, body, and footer action area
- [ ] The ranking area no longer appears as one long merged block
- [ ] The run-detail inspection area renders as one inspection card with an attached tab bar
- [ ] `Enriched Jobs`, `Original Job Input`, and `Candidate Profile` share one consistent pane container style
- [ ] Shared sub-card and attached-tab styles are defined centrally and reused across templates
- [ ] The change reduces page-local border and spacing exceptions rather than adding new ones

