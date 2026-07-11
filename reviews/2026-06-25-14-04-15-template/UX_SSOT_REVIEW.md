# UX / HTML SSOT, Symmetry, and Invariance Review

## Scope

Reviewed 15 original Jinja/HTML templates (4,809 lines). Static indicators:

- 315 inline `style` attributes
- 34 inline event handlers
- 58 hard-coded `/admin` route references
- 3 undefined CSS custom properties used by the templates

The supplied patch is intentionally focused: it fixes high-confidence template defects without guessing backend endpoint names or changing API contracts.

## Highest-priority findings

### 1. Settings filters violate the intersection invariant — Critical

**Files:** `settings.html:864-900`, `settings.html:1002-1068`

Two independent functions mutate the same `is-filter-hidden` class:

- `applyAxisFilters()` applies complexity/stage/control-surface filters.
- `applySearchFilter()` applies text search.

Changing an axis after typing a search runs only `applyAxisFilters()`, so rows excluded by search can reappear. The intended invariant is:

```text
row.visible = axisMatch AND searchMatch
```

There is a second defect: `applyAxisFilters()` hides every task section without a visible `.settings-panel`. The `danger-zone` section contains a summary rather than a `.settings-panel`, so the initial filter pass can hide it permanently.

**Patch:** Replace both visibility writers with one `applySettingsFilters()` function that computes the full predicate and explicitly preserves the danger-zone section.

### 2. “All bookmarks” is not actually all — Critical

**File:** `bookmarks.html:79-99`

The `view == 'all'` branch renders active and submitted bookmarks but never renders `archived_bookmarks`. The empty-state condition still checks `archived_bookmarks`, so a user with only archived bookmarks sees a blank card instead of rows or an empty message.

**Patch:** Render an Archived group in the All view.

### 3. Destructive-delete preview and execution do not share the same scope — Critical, backend patch required

**File:** `runs_list.html:532-583`

The confirmation count is calculated from archived checkboxes currently present in the DOM. The request sends only `older_than_days`, not those IDs:

```js
body: JSON.stringify({ older_than_days: olderThanDays })
```

If the table is paginated, filtered, or incomplete, the confirmation can say “delete N” while the server deletes a larger global set. This violates:

```text
previewed set == executed set
```

**Recommended patch:** Add a server preview endpoint that returns an immutable operation token plus exact count/IDs, then commit using that token. A smaller alternative is to submit the exact `run_ids` shown in the confirmation and make the backend reject IDs outside the archived/age predicate.

### 4. Shared design tokens are referenced but not defined — High

**Files:** `settings.html:77,148,156,199,319`; `run_detail.html:162,1028`; `synonym_review.html:211`; `base.html`

Undefined variables:

- `--surface-0`
- `--panel-bg`
- `--card-bg` (nested fallback only)

Also, templates emit `.badge-neutral`, but `base.html` does not define that class. Status classes such as `badge-cancelling`, `badge-cancelled`, and `badge-awaiting_continue` can also be emitted without canonical styling.

**Patch:** Define the tokens and canonical status aliases in `base.html` for both themes.

### 5. Synonym UI has duplicate sources of truth — High

**Files:** `_synonym_overlay_upload_form.html`; `synonym_review.html:15-24`; `run_detail.html:155-196`; `synonym_review.html:207-244`

Two separate SSOT violations:

1. The overlay upload form exists as a partial and is independently copied into `synonym_review.html`.
2. The decision-ledger table, badge mapping, columns, and empty state are independently copied into `run_detail.html` and `synonym_review.html`.

The copies have already drifted in max height, wrappers, and spacing.

**Patch:** Use the existing upload partial everywhere and introduce `_synonym_decision_ledger.html` with one compact modifier.

### 6. Run-detail tabs maintain multiple conflicting state representations — High

**File:** `run_detail.html:355-379`, `run_detail.html:723-734`

Tab state is represented simultaneously by:

- `.active` on the button
- `.active` on the panel
- inline `style.display`

The update queries are global (`document.querySelectorAll('.tab-pane')`), so another tab set added later would be affected. The markup also lacks `role=tab`, `aria-selected`, `aria-controls`, panel labels, and keyboard navigation.

**Patch:** Scope the controller to `.inspection-card`; use `hidden` plus ARIA as the visibility/selection contract; add Arrow/Home/End behavior.

### 7. Run-trigger choices have three state stores — High

**File:** `runs_list.html:318-365`

Each segmented choice is represented in:

- a JavaScript global (`_jobsMode`, `_profMode`, etc.)
- `aria-pressed`
- pane `style.display`

The arrays, ID naming rules, defaults, and submitted values are manually repeated. Adding a mode requires coordinated edits in several places.

**Recommended patch:** Use a reusable `data-choice-group` controller and a hidden form input as the only submitted source of truth. Derive button state and panel visibility from that input. Prefer a normal `<form>` over constructing `FormData` manually.

### 8. Selection controllers are copied and behavior has drifted — Medium/High

**Files:** `_cv_review_queue.html:149-196`; `synonym_review.html:247-327`; `synonym_promote_preview.html:135-171`; `run_detail.html:1220-1279`

Select-all, clear-all, selected-count, empty controls, and selectors are implemented repeatedly. The promotion implementations already use different selectors and empty-state behavior.

**Recommended patch:** One declarative controller, for example:

```html
<div data-selection-group data-item-selector="input[data-promote-selectable]">
```

The shared controller should own count, all/none buttons, indeterminate state, and submit-button disabled state.

### 9. Render order changes only after JavaScript — Medium/High

**File:** `run_detail.html:272-353`, `run_detail.html:1221-1227`

When outputs are available, JavaScript moves `#generated-outputs` before the overview card. Without JS, during initial paint, and for assistive technology following source order, the hierarchy differs. Other output states are not moved.

**Recommended patch:** Render the card in its intended location server-side for every state. Do not use DOM relocation for document hierarchy.

### 10. Settings validation remains split between backend metadata and hard-coded JavaScript — Medium

**File:** `settings.html:749-768`, `settings.html:909-944`

The template receives `ranking_weight_keys`, but preflight validation separately hard-codes the same six keys and the UI text says “All six weights.” Preference keys and threshold relationships are also embedded in JavaScript.

**Patch included:** Ranking validation and total text now derive from `ranking_weight_keys`.

**Further patch:** Send all validation constraints as JSON metadata, e.g. sum groups and ordered threshold pairs. The browser should interpret that contract rather than name settings directly.

### 11. Routes are repeated as string literals — Medium

There are 58 `/admin` references across templates and JavaScript. Renaming a route requires coordinated edits, and redirect targets repeat the same strings as action URLs.

**Recommended patch:** Generate links/forms with `url_for()` and expose API URLs through `data-*` attributes rendered by the server. JavaScript should consume those attributes rather than rebuild paths.

### 12. Base claims canonical styling, but page templates own much of the design system — Medium

There are 315 inline style attributes. Repeated patterns include page actions, card headings, notices, inline forms, section headers, table cells, and selection toolbars. `run_detail.html` alone has 110.

**Recommended patch order:**

1. Extract semantic components: notice, toolbar, inline-form, icon-button, ledger, empty-state.
2. Move page-specific `<style>` blocks to static CSS modules.
3. Remove `icon_button_style()` and use an `.icon-button` class.
4. Add a CI check that rejects new inline styles except documented dynamic cases.

## Patch contents

The focused patch:

- defines missing theme tokens and neutral/lifecycle status styles;
- normalizes invalid persisted theme values;
- centralizes the synonym decision ledger;
- reuses the synonym upload partial and makes file selection required;
- fixes archived bookmarks in the All view;
- unifies settings search and axis filtering;
- derives ranking-weight validation from server-provided keys;
- converts run-detail tabs to one scoped, accessible state controller.

## Validation performed

- All 16 patched templates parse successfully with Jinja2.
- Every referenced CSS custom property is defined after the patch.
- No backend endpoint names or request schemas were guessed.

Browser rendering and backend integration tests were not available in the uploaded archive, so the destructive-delete scope fix and route generation changes remain recommendations rather than applied changes.
