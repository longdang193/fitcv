# Scan Management Integration

Operation: `listScans`, `createScan`, `getScan`, `listScanEvents`, `listScanJobs`, `getScanOutput`, `cancelScan`, `runScanAgain`, `archiveScans`, `unarchiveScans`, `previewDeleteScans`, `deleteScans`
Contract owner: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md#api-contract`; provider behavior remains in `docs/superpowers/specs/2026-07-24-13-15-fitcv-job-source-option-c-spec.md`; canonical job fields remain in `src/fitcv/contracts.py` and `src/fitcv/ingest.py`
Registry dependency: tracked-company list, verification, and creation operations require a separate canonical registry contract; this sidecar defines UI states only and does not invent transport operation names
Run integration: existing Run creation operation still uses exclusive source modes and requires canonical reconciliation before it can accept additive upload and Scan inputs
Status: pending; Run input integration is blocked on the contract deltas below

## UI Source

- unified visual and layout intent: `docs/fitcv-settings-ui-prototype.html`
- Scan pages reuse the same page structure, typography, spacing, tables, detail sections, Console, and action placement as Runs and Candidate Profiles
- backend capabilities own action availability; frontend must not recreate lifecycle rules

## State Ownership

- URL owns Active/Archived tab, search, execution-status filter, page, page size, selected Scan detail, Scan Output view, and output page
- server owns Scan resource, tracked-company registry, execution status, archive state, progress, failure, output manifest, revisions, and capabilities
- component-local state owns open dialogs, temporary form values, company-picker search and draft selection, pending request IDs, and current bulk selection
- canonical Scan output owns both Table and JSON content; UI keeps no separately editable output copy

## Run Contract Reconciliation Required

- contract owner: update `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md#run-input-integration`; this sidecar records required UI behavior but does not own transport schemas
- API: replace exclusive caller-selected Upload/Scan mode with optional upload input plus optional ordered unique Scan IDs; require at least one source and merge uploaded jobs first, then Scan outputs in applied selection order
- data model: keep existing immutable Run snapshot and `run_scan_inputs` ordered relation; add no picker or Scan-selection table; canonical Run provenance must distinguish upload-only, Scan-only, and combined inputs and retain upload plus ordered Scan provenance
- errors: both sources absent is `validation_failed`, not `empty_job_input`; invalid upload keeps existing upload validation; stale or unusable selected Scans return `scan_not_usable`; output digest mismatch remains `scan_output_integrity_failed`; every failure creates no partial Run or references
- state transitions: managed Scan execution and archive state machines remain unchanged; Run submission adds only validation and atomic input-resolution behavior, while picker Open, Apply, Cancel, and stale-submit recovery remain component-local states
- compatibility: preserve legacy path, paste, upload, and direct-scanner contracts until their separately approved migration; do not overload `jobs_input_mode` with a synthetic combined mode in the new UI contract

## Scans Workspace

- loading: keep page heading and filters visible; show table skeleton; disable bulk actions
- empty Active: explain how to create first Scan and expose `New Scan`
- empty Archived: state that no Scans are archived; do not show `New Scan` inside empty card
- error: preserve current URL filters and prior rows when safe; show retry beside error summary
- retry: repeat same list query without resetting tab, search, filter, selection, or page unless page no longer exists
- selection: checkbox selection is page-local and clears when tab, search, status filter, or page changes
- Active actions: show Archive only when every selected resource has `capabilities.archive`; otherwise disable with reason
- Archived actions: show Unarchive when every selected resource allows it; Delete always opens preview and renders referenced, blocked, and missing results before confirmation
- mutation pending: lock only affected selected rows and action; prevent duplicate submission; retain unrelated navigation
- mutation success: reconcile returned resources, clear affected selection, and move rows between tabs without optimistic lifecycle invention
- stale or conflict: on `scan_revision_conflict` or `delete_preview_stale`, keep selection, refresh affected rows, and require a new action or preview

## New Scan

- tracked-company summary uses the shared New Scan form-field structure: label above one full-width bordered field shell, selected count or short preview inside, and one `Manage` action; it must not reuse settings-page cards or rows
- `Tracked Companies` is the sole company-selection control; `Manage` edits one ordered set of active company IDs, and Scan submission stores that explicit selection plus registry snapshot
- Manage loading: keep search and actions visible; show list skeleton; disable Apply until registry entries load
- Manage ready: native search filters company name, provider, and portal domain; a bounded scroll list uses native checkboxes, selected count, `Select all filtered`, and `Clear selection`
- Manage empty search: show no-match state without clearing draft selection; Add Company remains available
- Manage Apply: copy draft selection into New Scan and return focus to Manage; Cancel discards picker changes
- modal transitions keep exactly one native dialog in the top layer: Manage replaces New Scan, Add Company replaces Manage, and Apply, Cancel, Close, or Escape restores the prior dialog and focus without backdrop blur
- 100-company registries use the native filtered scroll list; add virtualization only after measured browser problems at larger registry sizes
- Add Company launches a separate registry flow from Manage; New Scan never becomes registry owner
- Add Company requires Company Name and HTTPS Careers URL; verification normalizes URL, rejects duplicates, detects a supported provider, tests portal reachability/shape through the registry backend, and enables Add only after success
- Add Company success persists one active scannable registry resource, selects it in the current draft, and returns to Manage; failure preserves inputs and shows a safe actionable reason
- optional filters: Job Titles, Job Locations, Published At, and Total Rows
- Published At uses one predefined rolling-window selector: `Any time`, `Past 12 hours`, `Past 24 hours`, `Past week`, `Past month`, and `Past 6 months`; arbitrary calendar dates are unavailable
- Published At transport remains contract-owned; backend resolves the selected window against Scan creation time, stores the requested window and concrete UTC cutoff in the immutable Scan snapshot, and applies one documented approximation policy when providers expose date-only publication precision
- validation: server field paths map to existing labeled controls and error summary; first invalid field receives focus after summary activation
- submission pending: disable submit and selection-changing controls; keep entered values; provide one progress label
- success: navigate to new Scan Details and start status/event polling
- error before creation: preserve values and show actionable error
- queue failure with returned Scan identity: navigate to failed Scan Details so persisted failure remains inspectable

## Scan Details

- loading: preserve details page shell and action area; show section skeletons
- not found: show `Scan not found` with Back to Scans
- action placement: use same details-page heading action group as Run Details; no floating, fixed, or section-local duplicate actions
- queued or running: show Cancel when `capabilities.cancel`; poll detail and events; display progress in Console
- cancelling: disable Cancel, show cancellation-requested status, and continue polling
- terminal: show Run Again; show Download JSON only when `capabilities.download`; show Archive or Unarchive from capability
- failed: show safe failure summary and action before Console; never expose provider response body or stack trace
- cancelled: explain no output exists and keep Run Again available
- mutation pending: lock only invoked action; prevent double click; preserve loaded detail and Console
- stale or conflict: refresh detail, keep user on page, and explain changed state

## Console Log

- loading: show initial loading state without replacing loaded Scan sections
- empty non-terminal: show `Waiting for Scan events` and continue polling
- empty terminal: show `No Scan events recorded`
- progress: append cursor results in server order and preserve scroll unless user has moved away from bottom
- retry: keep prior events, show inline retry, and resume from last accepted cursor
- clear: clears visible client log only; server events remain unchanged and a refresh restores them
- terminal: perform one final cursor fetch, then stop automatic polling

## Scan Output

- pending: queued, running, or cancelling shows output-not-ready state; no Table/JSON controls
- unavailable: failed or cancelled shows safe no-output state and Run Again path
- ready empty: successful zero-row output shows empty Table and exact `[]` JSON; Download JSON remains enabled; Run selection remains unavailable
- Table: request paginated rows from Scan jobs operation; reuse Run Details table density, overflow, row numbering, pagination, and long-cell handling
- JSON: request exact canonical output; render read-only formatted JSON without changing values or order
- view switching: Table and JSON tabs preserve current Scan; switching back restores prior table page
- integrity failure: replace output viewer with blocking error and remove Run-use affordance; retain Console and Download only if server capability still allows it

## Run Job Input

- Job data file and Eligible Scan outputs are independent optional controls; remove exclusive mode selection and require at least one source plus one available Candidate Profile
- one shared nearby requirement message owns the job-source rule; associate both source controls with it and reuse its text for the empty-source validation state
- one upload file may be combined with one or multiple Scans in the same Run
- deterministic merge order is uploaded jobs first, then Scan outputs in selected order; preserve each source's internal row order
- Scan picker query: Active Scans with `capabilities.use_for_run = true`
- picker field: reuse the Tracked Companies summary-plus-Manage pattern instead of an inline checkbox block or single-value dropdown
- Manage dialog: search and multi-select by Scan ID, Scan Name, or tracked company; show company count, job count, and completion time
- selection owner: one ordered unique Scan ID list; picker changes stay in a draft until Apply, and Cancel restores the applied list unchanged
- empty picker: link to Scans workspace and explain that upload remains available
- validation: reject only when no job source is supplied, no Candidate Profile is available or selected, an upload is invalid, or any selected Scan becomes unusable
- stale submit: `scan_not_usable` preserves the selected upload and unaffected Scan IDs, refreshes Scan resources, marks unavailable selections, and requires explicit reselection
- success: Run input summary shows uploaded filename when present and ordered source Scan IDs and names; pipeline executes one copied canonical Run snapshot, not live Scan output
- duplicate rows are preserved in V1; do not silently add cross-source deduplication outside canonical ingest ownership

## Accessibility and Responsive Behavior

- use native buttons, links, checkboxes, radios, search input, URL input, select, and multi-select semantics where existing components permit
- tabs expose selected state and keyboard navigation; dialogs trap focus and return it to invoking control
- status is never color-only; pending and disabled actions retain visible text reason
- action groups wrap in source order without overlap; narrow layout keeps primary action first and destructive action last
- Table uses accessible heading cells and scroll container; JSON view has an accessible label
- honor existing light, dark, focus-visible, zoom, reduced-motion, and long-content behavior

## Required Evidence

- backend contract tests cover request normalization, one/multiple/all selection, status transitions, output integrity, errors, idempotency, archive symmetry, delete preview, and Run references
- store tests cover migration idempotency, transaction atomicity, immutable output, event reuse, foreign-key delete restriction, and restart persistence
- frontend state tests cover every capability combination, URL restoration, pending locks, stale conflicts, empty output, company selection, picker search and draft preservation, verified Add Company, publication windows, and multi-Scan Run selection order
- Playwright flow covers company Manage search/selection, select-all-filtered behavior, verified Add Company, each publication window, Scan create, progress, cancel, Run Again, Table/JSON, download, archive, unarchive, blocked delete, successful delete, and Run creation from multiple Scans
- Chrome DevTools evidence confirms request payloads, response codes, no console errors, no duplicate submissions, and no layout shift in affected states
- browser checks cover keyboard flow, focus restoration, 200% zoom, narrow container, long localized content, and supported themes
