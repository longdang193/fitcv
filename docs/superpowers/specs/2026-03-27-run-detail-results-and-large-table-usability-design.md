# Run Detail Results and Large-Table Usability — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The current run detail page has two usability issues:

1. In the generated outputs section, each result links out with the generic label `View Job`, which makes it hard to distinguish one generated CV from another.
2. The enriched jobs table does not scale well for large runs. When a run contains 200 or more jobs, the page becomes long, dense, and difficult to scan.

These are not data-quality problems. They are presentation and navigation problems in the admin UI.

---

## Goal

Improve run-detail usability by:

1. replacing generic generated-output job links with human-readable job titles
2. making the enriched jobs tab manageable for large runs through filtering, search, and pagination

The design should keep the current inspection model intact while making high-volume runs much easier to review.

---

## Non-Goals

- Replacing the enriched jobs table with a completely different visualization
- Changing pipeline filtering or ranking behavior
- Changing the stored run data model beyond what is needed to render the UI
- Full-text search across all run artifacts

---

## Design

### Generated Outputs Link Label

In the `Pipeline Results` section, each generated output should use the job title as the primary link label instead of the generic `View Job`.

Recommended behavior:

- if the generated CV row can be associated with a job title from stored run data, render that title as the outbound job link text
- keep the external-link affordance
- if no title is available, fall back to `View Job`

Implementation rule:

- use the title from the associated stored job record for that generated output
- do not fetch, infer, or derive the title from external page content at render time

Examples:

- `Senior Data Engineer ↗`
- `Data Scientist, Pricing ↗`
- fallback: `View Job ↗`

This gives the admin immediate context when several generated outputs are listed together.

---

### Enriched Jobs Table Scaling Strategy

The enriched jobs tab should remain a table, but large runs should no longer render as one unbounded flat list by default.

Recommended controls:

1. summary counts
2. status filters
3. text search
4. pagination

These controls should work together without changing the underlying data semantics.

---

### Summary Counts

At the top of the enriched jobs tab, show a lightweight summary row with:

- total jobs
- passed
- rejected

These counts should be derived from the run-scoped filter results already available for the page.

This gives the admin fast orientation before scanning rows.

---

### Filter Controls

Add simple filter controls for the enriched jobs table:

1. `All`
2. `Passed`
3. `Rejected`

Behavior:

- `All` shows all enriched job rows
- `Passed` shows only rows whose filter result passed
- `Rejected` shows only rows whose filter result failed

`Passed` and `Rejected` refer to the run-scoped deterministic filter outcome for each job, not whether the job later received AI scoring or produced a generated CV.

The default view should be `All`.

These controls should apply only to the enriched jobs table, not the whole run detail page.

---

### Search

Add a lightweight client-side search box for the enriched jobs table.

Initial search scope:

- job title
- domain
- job family

This is enough to support common admin inspection tasks without expanding into a full advanced filter system.

Search should work within the currently selected pass/reject filter.

Recommended search semantics:

- case-insensitive
- substring match
- a row matches if any searchable field matches

---

### Pagination

Add pagination to the enriched jobs table.

Recommended defaults:

- default page size: `50`
- page-size options: `25`, `50`, `100`

Behavior:

- pagination applies after filter and search
- page changes should not reset the selected pass/reject filter
- page changes should not reset the current search query
- changing filter resets the current page to `1`
- changing search resets the current page to `1`

This keeps large runs usable without requiring server-side query redesign in the first iteration.

---

### Table Presentation Rules

The enriched jobs table should also get a few presentation improvements to reduce scanning fatigue:

- sticky table header
- consistent empty state after filtering/search
- keep long skill text truncated/collapsed as it is today, or tighten it further if needed

Empty-state behavior should be explicit:

- when no rows match the current filter/search, show a message such as `No jobs match the current controls`
- include a lightweight clear/reset action if practical, such as `Clear search` or `Show all`

Optional follow-up, not required for v1:

- sortable columns
- server-side pagination

---

### Data Access Model

The first implementation can remain page-local and render from the existing run-detail data payload.

Recommended first step:

- render all run rows once
- apply pass/reject filtering, search, and pagination client-side

This avoids introducing a new API immediately.

If browser performance becomes a problem for very large runs later, the design can evolve to server-side pagination or query-backed filtering.

---

### UX Behavior

The new controls should preserve the current tab model.

Rules:

- generated outputs remain in the pipeline results section
- enriched jobs remains the default inspection tab
- filter/search/pagination state should remain local to the enriched jobs tab
- changing tabs should not unexpectedly clear the table state during the current page session

---

## Acceptance Criteria

- [ ] Generated output links use the job title when a title is available
- [ ] Generated output links fall back to `View Job` when no title is available
- [ ] The enriched jobs tab shows summary counts for total, passed, and rejected rows
- [ ] The enriched jobs tab supports `All`, `Passed`, and `Rejected` filters
- [ ] The enriched jobs tab supports client-side search by title, domain, or job family
- [ ] Search is case-insensitive substring matching, and a row matches if any searchable field matches
- [ ] The enriched jobs tab supports pagination with a default page size of 50
- [ ] Filter, search, and pagination work together predictably
- [ ] Changing filter or search resets pagination to page 1
- [ ] Large runs with 200+ enriched rows remain usable without rendering one long unstructured list as the only interaction model
- [ ] The new controls do not change underlying run data or filtering semantics
