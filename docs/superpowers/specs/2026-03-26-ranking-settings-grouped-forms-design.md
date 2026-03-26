# Ranking Settings Grouped Forms — Design Spec

**Date:** 2026-03-26
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The current admin settings page treats ranking settings as independent rows with one save action per field. This is a poor fit for the ranking section because several settings are logically coupled and already have cross-field restrictions.

Examples:

- all ranking weights must sum to `1.0`
- `fit_label_thresholds.strong` must be greater than `fit_label_thresholds.stretch`
- `gap_thresholds.strong_min_matched_ratio` must be greater than `gap_thresholds.stretch_min_matched_ratio`

With per-row editing, an admin can easily hit validation failures while making a valid multi-field adjustment, because the intermediate state is temporarily invalid even when the final intended state is correct.

---

## Goal

Replace one-row-at-a-time editing for the ranking section with grouped editing UX that allows the admin to update related ranking settings together and validate the full set as one coherent configuration change.

The admin should be able to:

- edit all ranking weights together
- edit threshold pairs together
- see constraint errors in context before save
- avoid partial edits that break cross-field invariants

---

## Non-Goals

- Changing the meaning of existing ranking features or weights
- Introducing free-form formulas or custom scoring logic
- Reworking retrieval, timing, or global-job-filter settings in this feature

---

## Design

### UX Model

The ranking section should no longer behave like a list of unrelated settings rows.

Instead, it should be rendered as grouped editing forms aligned to the constraint boundaries already present in the backend validation.

Recommended grouping:

1. `Ranking Weights`
2. `Fit Label Thresholds`
3. `Gap Thresholds`

Each group has:

- editable inputs for all fields in the group
- one shared save action
- group-level validation feedback

Non-ranking sections may use their own section-level save pattern, but ranking settings must remain grouped by validation boundary rather than reverting to per-row saves.

---

### Group 1: Ranking Weights

This group includes:

- `ranking_weights.ai_score`
- `ranking_weights.must_have_match`
- `ranking_weights.vector_similarity`
- `ranking_weights.title_relevance`
- `ranking_weights.seniority_fit`
- `ranking_weights.preference_fit`

Constraint:

- all six values must be numeric values in `[0.0, 1.0]`
- all six values must sum to `1.0` within the existing validation tolerance of `±0.01`

Behavior:

- the admin edits all six fields in one form
- save validates the whole set together
- if the sum is invalid, the group save fails with a clear message showing the computed total

The UI should make the relationship obvious, for example by displaying a running total or a short note that the weights must sum to `1.0`.

---

### Group 2: Fit Label Thresholds

This group includes:

- `fit_label_thresholds.strong`
- `fit_label_thresholds.stretch`

Constraint:

- both values must be numeric values in `[0.0, 1.0]`
- `strong > stretch`

Behavior:

- both values are edited and saved together
- validation errors are shown at the group level

---

### Group 3: Gap Thresholds

This group includes:

- `gap_thresholds.strong_min_matched_ratio`
- `gap_thresholds.stretch_min_matched_ratio`

Constraint:

- both values must be numeric values in `[0.0, 1.0]`
- `strong_min_matched_ratio > stretch_min_matched_ratio`

Behavior:

- both values are edited and saved together
- validation errors are shown at the group level

---

### Validation Model

Existing backend validation logic should remain the source of truth.

This feature changes how ranking settings are submitted, not the fundamental validation rules.

Validation should happen at two levels:

1. client-facing grouped UX that keeps related fields together
2. server-side validation over the submitted group payload

The server must reject invalid grouped updates even if the client-side UI misses a case.

Grouped updates should be submitted as group-level payloads rather than as individual per-row form posts.

The exact route shape may vary, but the server contract should follow one of these models:

- one endpoint per ranking group
- one generic grouped-settings endpoint keyed by group name

Examples:

- `PATCH /settings/groups/ranking-weights`
- `PATCH /settings/groups/fit-label-thresholds`
- `PATCH /settings/groups/gap-thresholds`

or:

- `PATCH /settings/group/{group_name}`

---

### Persistence Model

Grouped editing should still persist settings using the existing settings store model, where values are saved as individual keys.

This feature does not require a new storage shape, but grouped updates must be represented as one logical change.

Expected behavior:

- the form submits multiple key/value pairs
- the server validates the entire group payload before any writes occur
- if valid, each setting is saved
- if invalid, no partial write occurs for that group submission

This preserves atomicity at the UX level even though storage remains key-based.

All settings rows written from one grouped save should share:

- a common `update_id` or `change_id`
- the same logical update timestamp

This allows grouped edits to be audited and reasoned about as one operation even when stored as multiple rows.

---

### Admin UX Details

The ranking section should visually distinguish grouped forms from the simpler sections above it.

Suggested UX details:

- subgroup headings inside the ranking section
- one save button per subgroup
- inline helper text for constraints
- group-level error message area
- live running total for the weights group
- inline comparison hints for threshold groups
- failed saves preserve the edited values in the form

Examples:

- `Weights must sum to 1.0`
- `Strong threshold must be greater than Stretch threshold`
- `Strong skill-ratio limit must be greater than Stretch limit`

---

## Acceptance Criteria

- [ ] Ranking settings are edited in grouped forms rather than one-row-per-save
- [ ] All six ranking weights can be updated in one submission
- [ ] Weight-group save rejects totals that do not sum to `1.0`
- [ ] Ranking weights and thresholds reject out-of-range numeric values
- [ ] Fit-label thresholds are edited and validated together
- [ ] Gap thresholds are edited and validated together
- [ ] Invalid grouped submissions do not partially save
- [ ] Grouped submissions are validated fully before any settings rows are written
- [ ] All keys written from one group save share a common logical update identifier or timestamp
- [ ] Unsaved edits remain visible after a failed group submission
- [ ] Existing backend validation remains the source of truth
- [ ] Retrieval, timing, and global-job-filter settings remain outside the ranking grouped-editing scope
