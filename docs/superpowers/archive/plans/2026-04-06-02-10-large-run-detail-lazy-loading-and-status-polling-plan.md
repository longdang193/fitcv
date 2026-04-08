# Large Run Detail Lazy Loading And Status Polling Plan

Status: completed

## Tasks

1. Split run-detail initial render into a lightweight summary shell.
Status: completed
Notes:
- Keep the first HTML response limited to:
  - run header and lifecycle actions
  - run summary
  - exports
  - synonym overlay
  - run health
  - bounded timeline slice
- Remove eager loading of:
  - full enriched-job inspection rows
  - full filter results
- Preserve the existing route shape at `/admin/runs/{run_id}` so the page architecture changes without breaking navigation.

2. Add lazy-loaded run-detail tab endpoints.
Status: completed
Notes:
- Introduce dedicated run-detail tab endpoints for:
  - enriched jobs
  - original job input
  - candidate profile
- Prefer HTML fragment responses so the control plane stays server-rendered and template-consistent.
- Make the tabs render loading placeholders until the fragment is fetched.

3. Add server-side pagination and bounded query shapes for heavy inspection data.
Status: completed
Notes:
- Add page size and paging controls for enriched-job inspection first.
- Bound the default page size to `25` or `50`.
- Keep search/filter server-owned rather than rendering all rows client-side.
- Ensure no path renders all `500+` or `1000+` jobs in one response.

4. Keep polling lightweight and state-only.
Status: completed
Notes:
- Keep `/runs/{run_id}` as the polling endpoint and keep it status-only.
- Ensure polling never triggers:
  - stage-artifact parsing
  - enriched-job queries
  - filter-result queries
  - CV-version queries
- Tighten the browser poll loop to:
  - non-overlapping requests
  - slower cadence
  - visibility-aware polling
  - reload only on real state transitions

5. Bound timeline rendering for large runs.
Status: completed
Notes:
- Render only the latest timeline slice on first paint.
- Add a progressive loading mechanism for older rows via bounded `timeline_limit` expansion from the shell route.
- Preserve aggregate stage-row ownership for stage downloads while paginating older history.

6. Align run-detail templates and labels with the lazy model.
Status: completed
Notes:
- Make the initial tab surfaces visually clear that detail is available but not yet loaded.
- Keep exports usable without opening tabs first.
- Ensure run health and summary remain top-priority diagnostics while tab detail becomes opt-in.

7. Add focused regression and scale-oriented coverage.
Status: completed
Notes:
- Add control-plane tests proving the initial run-detail render does not depend on heavy tab queries.
- Add tests proving tab endpoints return bounded paginated content.
- Add tests proving polling still works from the lightweight `/runs/{run_id}` route.
- Add at least one scale-oriented test or fixture shape that simulates a large enriched-job result set without rendering the full set into the initial page.

8. Sync feature docs and discovery.
Status: completed
Notes:
- Updated:
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/history.md`
- Generated discovery was not refreshed in this implementation pass.

## Verification

- Focused control-plane tests in:
  - `tests/test_fitcv_cp/test_app.py`
- Verification observed:
  - `60 passed, 143 deselected` for the focused run-detail slice using a local `--basetemp`
- Any supporting store/query tests needed for bounded inspection endpoints
- Manual sanity check on:
  - a small run (`~10` jobs)
  - a medium run (`~50` jobs)
  - a simulated large run (`500+` jobs worth of inspection rows`)
- Browser sanity check that:
  - initial run detail is fast
  - tabs lazy-load correctly
  - polling no longer feels like constant localhost waiting
- `py_compile` on touched Python modules
