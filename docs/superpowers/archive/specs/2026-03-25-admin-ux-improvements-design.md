# Admin Control Plane UX Polish — Design

## Summary

This design addresses three UX improvements for the FitCV Admin Control Plane: making pipeline settings more end-user friendly, adding global navigation links across admin pages, and improving the visibility of final pipeline outputs (like CVs generated).

## Goal

Allow an admin to:
1. Easily understand what each Pipeline Setting does through user-friendly labels and clear descriptions, rather than raw dot-notated keys.
2. Navigate seamlessly between the "Runs" list and "Settings" pages through a global navigation bar.
3. Immediately see whether CVs were actually generated after a run completes, with a visually highlighted success banner on the run detail page.

## Non-Goals

- We will not implement real-time log streaming for the UI in this iteration.
- We will not serve the generated CV files directly for download via the web app; we will simply indicate how many were persisted to BigQuery.

## Architecture & Data Changes

### 1. User-Friendly Settings Schema

The `settings_schema.py` registry will be extended. Each dictionary entry in `SETTINGS_SCHEMA` will gain a new `description` string. The existing `label` fields will be conversationalized.

For example, `pipeline.vector_search_top_n` will change:
- **Label**: "Initial Candidate Pool Size"
- **Description**: "The number of candidates to retrieve from the vector database after applying deterministic rule filters."

The table in `settings.html` will be updated to display the `label` as the primary setting name, with the `description` text rendered slightly smaller below it. The raw `key` will be hidden or deprioritized.

### 2. Global Navigation

The `<nav>` element in `src/fitcv_cp/templates/base.html` will be updated to host persistent links. Currently, users must change the `/admin/runs` URL to `/admin/settings` manually.

We will add the following link structure:
```html
<nav>
  <span class="brand">⚡ FitCV Admin</span>
  <a href="/admin/runs">Runs</a>
  <a href="/admin/settings">Settings</a>
  <a href="/healthz">Health</a>
</nav>
```

### 3. Generated CVs Visibility

The `pipeline_runs` BigQuery table already tracks `cvs_generated` correctly. However, in `run_detail.html`, this integer is buried inside a generic key-value grid.

We will introduce a new Jinja2 UI component. When `run.status.value == 'succeeded'`, the page will evaluate `run.cvs_generated`.
- If `cvs_generated > 0`, it will render a highlighted, green success banner (e.g., "🎉 Successfully generated 5 candidate CVs! The generated CV markdowns have been persisted to the cv_versions BigQuery table.")
- If `cvs_generated == 0`, it will highlight a warning that no CVs passed the final ranking threshold.

## New / Modified Files

| File | Change |
|---|---|
| `src/fitcv_cp/settings_schema.py` | Add `description` field to all 16 keys; translate `label`s to conversational English. |
| `src/fitcv_cp/templates/base.html` | Add `<a href="/admin/settings">Settings</a>` to the global `<nav>` bar. |
| `src/fitcv_cp/templates/settings.html` | Redesign the table rows to emphasize `label` and `description` instead of the raw technical `key`. |
| `src/fitcv_cp/templates/run_detail.html` | Extract `cvs_generated` from the general grid; render an eye-catching success banner if CVs were created. |
| `tests/test_fitcv_cp/test_settings_schema.py` | Ensure new `description` field is validated in unit tests. |
| `tests/test_fitcv_cp/test_app.py` | Add UI rendering tests for the global nav link and conditional CV success banner. |

## Verification

### Automated tests
- `test_settings_schema.py`: Validate that every dictionary in `SETTINGS_SCHEMA` has a `description` key.
- `test_app.py`: Validate that the "Settings" link appears in the base layout, and that the success banner correctly renders conditionally based on `cvs_generated` and includes the BigQuery reference.

### Manual smoke test
1. Open `http://localhost:8000/admin/runs` and click "Settings" in the top navbar.
2. Verify all settings have user-friendly titles and subtitles.
3. Open an existing completed run and verify if a "🎉 Successfully generated N candidate CVs!" component appears at the top.
