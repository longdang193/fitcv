# Run Detail Results and Large-Table Usability — Implementation Plan

**Date:** 2026-03-27
**Spec:** [2026-03-27-run-detail-results-and-large-table-usability-design.md](../specs/2026-03-27-run-detail-results-and-large-table-usability-design.md)
**Branch:** `feat/admin-control-plane`

---

## Summary

One small server-side change in `app.py` and front-end changes to `run_detail.html` (no new API routes, no BQ schema changes):

1. **Generated output links** — replace the generic `View Job ↗` label with the actual job title, resolved from the enriched jobs data already available in the template context.
2. **Enriched jobs table** — add summary counts, pass/reject filter buttons, client-side text search, and client-side pagination.

All filtering, search, and pagination is client-side. The existing `enriched_jobs` and `filter_results_by_job_url` context variables already contain everything needed.

---

## Context

| Template variable | What it contains |
|---|---|
| `cv_versions` | `version_id`, `job_url`, `fit_classification` — **no title** |
| `enriched_jobs` | `job_url`, `title`, `domain`, `job_family`, `required_skills`, `location_type`, `seniority` |
| `filter_results_by_job_url` | `job_url → {passed: bool, reasons: list}` |

The `cv_versions → title` link must be resolved via `job_url` from `enriched_jobs`. This join **must happen in app.py** (server-side) so the Jinja template stays readable. No new BQ query is needed.

---

## Proposed Changes

---

### Component 1: Server-side enrichment in `app.py`

#### [MODIFY] [app.py](file:///workspaces/fitcv/src/fitcv_cp/app.py)

In `admin_run_detail()`, after building `filter_results_by_job_url`, compute two additional derived values and pass them to the template context:

```python
# Build job title lookup: job_url → title (for cv_versions link labels)
job_title_by_url: dict[str, str] = {
    j["job_url"]: j.get("title") or ""
    for j in enriched_jobs
}

# Pre-compute pass/reject summary counts from filter_results_by_job_url.
# Rows where fr is missing are NOT counted as rejected — they are unknown.
# This preserves the existing template's three-state distinction (pass / reject / —).
enriched_passed_count = sum(
    1 for j in enriched_jobs
    if filter_results_by_job_url.get(j["job_url"], {}).get("passed") is True
)
enriched_rejected_count = sum(
    1 for j in enriched_jobs
    if filter_results_by_job_url.get(j["job_url"], {}).get("passed") is False
)
# enriched_jobs with no entry in filter_results_by_job_url are not counted in either bucket.
```

Add all three to the `TemplateResponse` context: `job_title_by_url`, `enriched_passed_count`, `enriched_rejected_count`.

---

### Component 2: Generated output link labels

#### [MODIFY] [run_detail.html](file:///workspaces/fitcv/src/fitcv_cp/templates/run_detail.html)

In the `Generated Outputs` loop (lines 74–82), replace the static `View Job ↗` anchor text:

```diff
- <a href="{{ cv.job_url }}" target="_blank">View Job ↗</a>
+ <a href="{{ cv.job_url }}" target="_blank">
+   {{ job_title_by_url.get(cv.job_url) or 'View Job' }} ↗
+ </a>
```

---

### Component 3: Enriched jobs table — summary counts, filters, search, pagination

#### [MODIFY] [run_detail.html](file:///workspaces/fitcv/src/fitcv_cp/templates/run_detail.html)

Replace the entire `pane-enriched` div contents with the new table markup. Changes are:

**a) Summary count row** — rendered from the server-computed counts from `app.py` (pass/reject outcome lives in `filter_results_by_job_url`, a separate lookup dict, not a direct attribute on `job`, so Jinja `selectattr` cannot reach it cleanly):

```jinja
<span>Total: {{ enriched_jobs | length }}</span>
<span>Passed: {{ enriched_passed_count }}</span>
<span>Rejected: {{ enriched_rejected_count }}</span>
```

**b) Filter + search controls row** — three toggle buttons (`All`, `Passed`, `Rejected`) + a text `<input>` for search. The active filter button gets `data-active="true"`.

```html
<div id="enr-controls" ...>
  <div>
    <button onclick="setFilter('all')">All</button>
    <button onclick="setFilter('passed')">Passed</button>
    <button onclick="setFilter('rejected')">Rejected</button>
  </div>
  <input id="enr-search" type="search" placeholder="Search title, domain, job family…" oninput="onSearch()">
</div>
```

**c) Table `<tbody>` rows** — embed `data-filter` with three possible values to preserve current three-state semantics: `passed`, `rejected`, or `unknown` (when no filter result exists for the job). All nullable search fields must use empty-string fallbacks:

```html
<tr data-filter="{% if fr is not none %}{{ 'passed' if fr.passed else 'rejected' }}{% else %}unknown{% endif %}"
    data-title="{{ (job.title or '') | lower }}"
    data-domain="{{ (job.domain or '') | lower }}"
    data-family="{{ (job.job_family or '') | lower }}">
```

**d) Sticky header** — apply `position:sticky` to the `<th>` cells themselves, not the `<thead>` element. Browser support for sticky on `<thead>` is inconsistent; stickiness on `<th>` is reliable across all current browsers:

```css
/* Added inline or via an existing shared style rule */
.enr-table th { position: sticky; top: 0; z-index: 1; background: var(--table-header-bg); }
```

**e) Pagination controls** — `← Prev`, page indicator, `Next →` + page-size selector.

**f) Empty state** — shown when no `<tr>` is visible after filtering:

```html
<tr id="enr-empty-row" style="display:none">
  <td colspan="7">No jobs match the current controls. <a onclick="resetControls()">Show all</a></td>
</tr>
```

---

### Component 4: Client-side JS

#### [MODIFY] [run_detail.html](file:///workspaces/fitcv/src/fitcv_cp/templates/run_detail.html)

Add a `<script>` block with:

```
EnrichedTable = {
  PAGE_SIZE: 50,          // configurable via select
  currentFilter: 'all',
  currentSearch: '',
  currentPage: 1,

  allRows: [],            // NodeList snapshot on DOMContentLoaded
  visibleRows: [],        // rows matching current filter+search

  setFilter(f),           // update currentFilter, reset page, re-render
  onSearch(q),            // update currentSearch, reset page, re-render
  setPageSize(n),         // update PAGE_SIZE, reset page, re-render
  render(),               // apply filter+search → visibleRows, slice page, toggle display
  updatePagination(),     // update prev/next buttons + page label
  resetControls(),        // clear filter to 'all', clear search input, re-render
}
```

Filtering rules:
- `filter === 'all'` → show all rows
- `filter === 'passed'` → show only `data-filter="passed"` rows
- `filter === 'rejected'` → show only `data-filter="rejected"` rows
- Search is applied **after** filter: substring match (case-insensitive) across `data-title`, `data-domain`, `data-family`
- Changing filter or search resets `currentPage` to `1`
- Changing page-size also resets to page `1`

---

## Test Plan

### Automated (new app tests in `tests/test_fitcv_cp/test_app.py`)

| Test | Assertion |
|---|---|
| `test_run_detail_cv_versions_show_job_title` | When enriched_jobs includes a matching title, rendered HTML contains that title in the cv_versions section — not `View Job` |
| `test_run_detail_cv_versions_fallback_when_no_title` | When no enriched_jobs match the cv job_url, rendered HTML contains `View Job` |
| `test_run_detail_enriched_shows_summary_counts` | `Total:`, `Passed:`, `Rejected:` present in rendered HTML |
| `test_run_detail_enriched_shows_filter_controls` | `All`, `Passed`, `Rejected` buttons present |
| `test_run_detail_enriched_shows_search_box` | `id="enr-search"` present |
| `test_run_detail_enriched_rows_have_data_attributes` | Each enriched row has `data-filter=`, `data-title=`, `data-domain=`, `data-family=` |
| `test_run_detail_enriched_shows_pagination` | Pagination controls present |
| `test_run_detail_enriched_unknown_filter_not_counted_as_rejected` | When an enriched job has no entry in `filter_results_by_job_url`, its `data-filter` is `unknown`, not `rejected`, and `enriched_rejected_count` does not include it |

### Manual Browser Verification

1. Open a run with 50+ enriched jobs — verify summary counts, filter tabs, and search all function together
2. Click `Passed` → only passed rows show; then type in search box → search applies within passed rows
3. Change page size to 25 → page resets to 1
4. Clear search → rows re-expand correctly
5. Verify `View Job` fallback in Generated Outputs for a run where job_url has no enriched match
6. Verify job title label appears for runs with matches

---

## Acceptance Criteria Mapping

| Spec item | Component |
|---|---|
| CV output links use job title when available | Component 1 + 2 |
| CV output links fall back to `View Job` | Component 2 |
| Summary counts (total/passed/rejected) | Component 3a |
| All/Passed/Rejected filter controls | Component 3b |
| Client-side text search (title, domain, job family) | Component 3b + 4 |
| Case-insensitive substring match, row matches if any field matches | Component 4 |
| Pagination with default 50, options 25/50/100 | Component 3e + 4 |
| Filter+search+pagination work together predictably | Component 4 |
| Changing filter/search resets page to 1 | Component 4 |
| Sticky table header | Component 3d |
| Empty state with reset action | Component 3f + 4 |
