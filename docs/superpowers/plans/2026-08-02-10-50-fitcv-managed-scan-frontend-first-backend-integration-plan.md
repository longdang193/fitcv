---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-managed-scan-frontend-first-backend-integration
parent_spec: docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md
targets:
  - src/fitcv/job_sources.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/scan_contracts.py
  - src/fitcv_cp/scan_mock.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/scans_list.html
  - src/fitcv_cp/templates/scan_detail.html
  - tests/test_job_sources.py
  - tests/test_fitcv_cp/scan_fixtures.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/job-data-input.md
  - docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md
  - docs/fitcv-scan-ui-prototype.integration.md
---

# FitCV Managed Scan Frontend-First Backend Integration Plan

## Goal

Implement managed Scans in three deliberate stages without creating a second transport contract:

1. expose the approved API through a temporary deterministic in-memory adapter
2. build and verify the real frontend against those HTTP routes and every required UI state
3. replace the temporary adapter with SQLite persistence, provider execution, queueing, and additive Run input while leaving frontend request and response handling unchanged

Preserve legacy path, paste, upload-mode, and direct-scanner Run contracts during migration. Keep `src/fitcv/contracts.py`, `src/fitcv/ingest.py`, and the Option C provider registry as canonical owners of job fields, canonicalization, and provider routing.

## Implementation Outcomes

### One Executable Scan Contract

Pydantic request and response models, enums, capability projection, publication-window resolution, stable errors, and store method signatures materialize the managed-Scan specification once. Temporary mock responses and final SQLite responses pass the same route tests and expose the same OpenAPI shapes.

### Frontend Proven Before Provider Work

Scans workspace, New Scan, tracked-company management, Scan Details, Console, Table and JSON output, archive lifecycle, and additive Run source selection operate against real HTTP routes backed by deterministic mock state. Browser proof covers loading, empty, ready, pending, terminal, stale, error, integrity, accessibility, responsive, and theme states before external acquisition is implemented.

### Persistent Managed Scan Backend

Existing control-plane SQLite, idempotent actions, process events, queue infrastructure, and provider acquisition implement tracked-company persistence, immutable Scan snapshots, asynchronous execution, output integrity, cancellation, Run Again, archive symmetry, delete preview, restart persistence, and atomic provider failure. No second job-row truth or Scan-specific event store is introduced.

### Additive Run Input

Managed multipart `POST /runs` accepts one optional upload and ordered unique Scan IDs, requires at least one source, validates all sources before persistence, merges upload first and Scan outputs in explicit order, stores one immutable Run snapshot, and persists protected `run_scan_inputs` references in the same transaction. Legacy callers retain existing source-mode behavior until separate removal approval.

### Mock Removal And Contract Closeout

Production code contains no mock backend, mock-only route, or mock-only flag after real integration. Test fixtures retain deterministic state coverage. Frontend integration sidecar is deleted only after backend, browser, and accessibility evidence passes.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-using-git-worktrees`, `skill-test-driven-development`, `skill-code-standards`, `skill-full-stack-integration`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: create a new worktree and `codex/managed-scan-integration` branch from current `HEAD`, then copy only the current approved versions of `docs/superpowers/plans/2026-08-02-10-50-fitcv-managed-scan-frontend-first-backend-integration-plan.md`, `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`, `docs/fitcv-scan-ui-prototype.integration.md`, and `docs/fitcv-settings-ui-prototype.html` into that worktree before Task 1; do not copy unrelated `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md` or `.playwright-mcp` files
- Parallel ownership: none; `src/fitcv_cp/app.py`, `src/fitcv_cp/store.py`, `src/fitcv_cp/sqlite_store.py`, and Run persistence are shared sequential owners
- Sequential fallback: contract shell, temporary mock API, frontend and browser checkpoint, SQLite store, worker execution, additive Run resolution, mock removal and final verification
- Route impact gate: before changing `POST /runs`, run GitNexus `api_impact` for `/runs` when indexed; otherwise use `rg` over `src`, `tests`, and templates to record every caller and legacy mode
- Mock boundary: `src/fitcv_cp/scan_mock.py` is temporary and must be deleted in Task 7; frontend templates may not import it or branch on mock state

## Task Breakdown

### Task 1: Materialize Scan Contract And Store Seam

**Purpose:**
- Create one executable contract used by mock routes, frontend responses, SQLite implementation, and tests.

**Specification Coverage:**
- Shared conventions; tracked-company registry; Scan request and resource contracts; publication windows; capabilities; stable errors; state invariants.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`
- Inspect: `src/fitcv_cp/app.py:ApiError`
- Inspect: `src/fitcv_cp/app.py:_data_response`
- Inspect: `src/fitcv_cp/app.py:_collection_response`
- Inspect: `src/fitcv_cp/store.py:RunStore`
- Inspect: `src/fitcv_cp/store.py:ControlPlaneStore`
- Add: `src/fitcv_cp/scan_contracts.py:PublishedWindow`
- Add: `src/fitcv_cp/scan_contracts.py:ScanExecutionStatus`
- Add: `src/fitcv_cp/scan_contracts.py:ScanCapabilities`
- Add: `src/fitcv_cp/scan_contracts.py:TrackedCompanyResource`
- Add: `src/fitcv_cp/scan_contracts.py:ScanCreateRequest`
- Add: `src/fitcv_cp/scan_contracts.py:ScanResource`
- Add: `src/fitcv_cp/scan_contracts.py:resolve_publication_cutoff`
- Add: `src/fitcv_cp/scan_contracts.py:derive_scan_capabilities`
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Add: `tests/test_fitcv_cp/test_scan_contracts.py`
- Modify: `tests/test_fitcv_cp/test_store.py`

**Dependencies:**
- Approved managed-Scan specification remains canonical.
- Existing `ApiError`, response-envelope, pagination, revision, and idempotency conventions remain unchanged.

**Steps:**
- [x] Step 1: Add failing tests for every enum value, UTC cutoff, date-only comparison rule, request trimming and ordered deduplication, capability matrix, output eligibility, bounded warning serialization, and invalid transition input.
- [x] Step 2: Implement Pydantic models and pure helper functions in `scan_contracts.py`; reference canonical job ownership instead of copying job-field schemas.
- [x] Step 3: Extend `RunStore` and `ControlPlaneStore` with exact operations `query_tracked_companies`, `create_tracked_company`, `create_scan`, `query_scans`, `get_scan_detail`, `request_scan_cancel`, `commit_scan_output`, `get_scan_output`, `query_scan_jobs`, `transition_scan_lifecycle`, `preview_delete_archived_scans`, and `delete_archived_scans`; `create_scan` accepts the reserved `idempotency_action_id`; reuse existing `get_process_events` and idempotent-action methods instead of adding Scan-specific equivalents.
- [x] Step 4: Route new store methods through existing override-function pattern; use one explicit `_scan_backend_unavailable` default until Task 4 supplies SQLite functions.
- [x] Step 5: Add parameterized store tests proving every new override dispatches and every absent override fails through `_scan_backend_unavailable` without touching SQLite.
- [x] Step 6: Add OpenAPI-compatible response-envelope types without changing existing Run or Candidate Profile response models.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_store.py -q`
- [x] `uv run python -m compileall -q src/fitcv_cp/scan_contracts.py src/fitcv_cp/store.py`
- Expected: contract tests pass; invalid enum, order, warning, capability, and cutoff cases fail deterministically; no database or provider call occurs.

**Exit Criteria:**
- Every mock and real implementation can satisfy one named store and Pydantic contract without frontend-specific data shapes.

### Task 2: Expose Temporary Mock API

**Purpose:**
- Provide complete managed-Scan HTTP behavior for frontend construction before SQLite and provider execution exist.

**Specification Coverage:**
- API routes; envelopes; list and detail states; events; output views; lifecycle actions; errors; idempotency; tracked-company verification and creation.

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:create_app`
- Inspect: `src/fitcv_cp/app.py:_required_idempotency_key`
- Inspect: `src/fitcv_cp/app.py:get_process_events`
- Add: `src/fitcv_cp/scan_mock.py:MockScanBackend`
- Add: `src/fitcv_cp/scan_mock.py:install_mock_scan_store`
- Add: `src/fitcv_cp/scan_mock.py:app`
- Modify: `src/fitcv_cp/app.py:create_app`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 contract and store seam complete.

**Steps:**
- [x] Step 1: Add failing route tests for every tracked-company and Scan endpoint, response envelope, status code, error code, capability field, completed idempotent replay, pending replay with provisional `scan_id`, stale revision, delete preview, and exact output bytes.
- [x] Step 2: Add route handlers in `create_app` that call only `app.state.run_store`; handlers may not inspect mock fixture identity or derive lifecycle actions outside `scan_contracts.py`.
- [x] Step 3: Add managed multipart `POST /runs` dispatch for absence of legacy mode fields, parse one optional upload plus repeated ordered `scan_ids`, and resolve sources through existing `ControlPlaneStore` output operations. Mock-backed resolution may use existing Run bundle persistence, but request shape, validation, merge order, and response envelope are final.
- [x] Step 4: Implement deterministic in-memory resources for queued, running, cancelling, succeeded, empty, failed, cancelled, archived, and integrity-failed states.
- [x] Step 5: Implement temporary mock-only scenario control inside `scan_mock.py` for delayed responses, registry loading failure, empty registry, empty Active list, empty Archived list, one-shot list refresh failure, revision conflict, delete-preview staleness, and stale Run selection. This route exists only on `scan_mock.py:app`, never on ordinary `create_app`.
- [x] Step 6: Make mock mutations update resources and events through the same request and response shapes as final persistence, including pending idempotent replay returning the same Scan and Run Again creating a new identity.
- [x] Step 7: Assert `/openapi.json` exposes canonical routes and models without mock-only schemas.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py -k "tracked_company or scan_contract or scan_route or scan_action" -q`
- [x] `uv run python -m compileall -q src/fitcv_cp/app.py src/fitcv_cp/scan_mock.py`
- Expected: all API states are reachable through HTTP; normal app has no mock-only route; mock app returns exact canonical envelopes.

**Exit Criteria:**
- Frontend can be implemented without direct fixture imports, browser storage, or transport branching.

### Task 3: Build Frontend Against Mock Routes

**Purpose:**
- Materialize approved prototype in actual server-rendered UI and prove every frontend state before real backend work.

**Specification Coverage:**
- Scans workspace; New Scan; Manage Tracked Companies; Add Company; Scan Details; Console; Table and JSON output; Active and Archived actions; additive Run job input; accessibility and responsive behavior.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html`
- Inspect: `docs/fitcv-scan-ui-prototype.integration.md`
- Inspect: `src/fitcv_cp/templates/base.html`
- Inspect: `src/fitcv_cp/templates/runs_list.html:triggerRun`
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Add: `src/fitcv_cp/templates/scans_list.html`
- Add: `src/fitcv_cp/templates/scan_detail.html`
- Modify: `src/fitcv_cp/app.py:admin_runs`
- Add: `src/fitcv_cp/app.py:admin_scans`
- Add: `src/fitcv_cp/app.py:admin_scan_detail`
- Add: `src/fitcv_cp/app.py:_project_jobs_input_sources`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 2 mock API passes route tests.
- Prototype remains visual SSOT; integration sidecar remains state-intent owner until Task 7.

**Steps:**
- [x] Step 1: Add Scans navigation and HTML routes using existing base tokens, detail-page structure, table density, pagination, dialog, status-badge, Console, and action-group patterns.
- [x] Step 2: Build Scans workspace with URL-owned Active or Archived view, page, page size, page-local selection, Archive, Unarchive, and delete preview; retain search and execution-status filtering in the API without duplicating controls absent from the prototype.
- [x] Step 3: Build New Scan dialog with one managed Tracked Companies field, searchable checkbox list, filtered select-all, draft Apply or Cancel, verified Add Company, Job Titles, Job Locations, `published_window`, Total Rows, validation summary, and focus restoration.
- [x] Step 4: Build Scan Details with server capability actions, immutable Scan Overview and Input, polling Console, Table and JSON output views, shared pagination, exact download, integrity blocking, and Run Again behavior.
- [x] Step 5: Replace exclusive Run source selector with independent optional upload and managed eligible-Scan picker; submit no `source_mode`, append repeated ordered `scan_ids`, preserve picker draft order, and show one shared missing-source validation message.
- [x] Step 6: Project `jobs_input_manifest_json.sources` once in `_project_jobs_input_sources` and render uploaded filename plus ordered Scan IDs and names in Run Overview and Jobs Input without parsing JSON in Jinja.
- [x] Step 7: Add TestClient HTML assertions for headings, controls, dialog semantics, route links, capability-controlled actions, no duplicated company selector, exact publication options, no direct careers URL in New Scan, no exclusive Run mode field, and ordered combined-source Run summary.
- [x] Step 8: Start temporary mock app with `uv run uvicorn fitcv_cp.scan_mock:app --host 127.0.0.1 --port 8892`; use mock scenario route only from test tooling to exercise every state without frontend knowledge.
- [x] Step 9: Exercise keyboard company selection, Add Company success and failure, Scan creation, Console polling, output tabs, pagination, archive, delete, empty, error, revision-conflict, integrity, and additive Run states with isolated Playwright because shared MCP Chrome profiles were externally locked.
- [x] Step 10: Inspect request payload order, status codes, duplicate-submit prevention, console errors, dialog top-layer behavior, and layout stability through isolated Playwright network and DOM evidence because Chrome DevTools MCP shared profile was externally locked.
- [x] Step 11: Verify desktop 1440x900, narrow 390x844, 200% zoom, light, dark, reduced motion, long names, long URLs, and long error text.
- [x] Step 12: Fix client-side navigation initialization so dynamically activated Runs and Run Details scripts initialize after `DOMContentLoaded` and remain safe on repeated navigation; add focused regression proof.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py -k "admin_scans or scan_ui or trigger_run_scan_picker" -q`
- [x] Browser state checklist records pass or fail for every state named in `docs/fitcv-scan-ui-prototype.integration.md`.
- [x] Browser console contains no uncaught error and network payload contains upload first and repeated Scan IDs in applied order.
- Expected: UI uses HTTP contract only; switching mock scenarios changes visible state without template or client changes.

**Exit Criteria:**
- Frontend acceptance passes against mock routes before Task 4 begins. Any contract defect found here is fixed in `scan_contracts.py`, specification, and route tests before persistence work.

### Task 4: Implement SQLite Registry And Scan Persistence

**Purpose:**
- Replace in-memory resource storage with restart-safe tracked-company, Scan, output, lifecycle, and provenance persistence.

**Specification Coverage:**
- Data model; immutable snapshots; output SSOT; archive symmetry; delete protection; revisions; idempotency; migration and restart behavior.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`
- Inspect: `src/fitcv_cp/sqlite_store.py:create_run_bundle`
- Inspect: `src/fitcv_cp/sqlite_store.py:append_process_event`
- Inspect: `src/fitcv_cp/sqlite_store.py:reserve_idempotent_action`
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`
- Add: `src/fitcv_cp/sqlite_store.py:query_tracked_companies`
- Add: `src/fitcv_cp/sqlite_store.py:create_tracked_company`
- Add: `src/fitcv_cp/sqlite_store.py:create_scan`
- Add: `src/fitcv_cp/sqlite_store.py:query_scans`
- Add: `src/fitcv_cp/sqlite_store.py:get_scan_detail`
- Add: `src/fitcv_cp/sqlite_store.py:request_scan_cancel`
- Add: `src/fitcv_cp/sqlite_store.py:commit_scan_output`
- Add: `src/fitcv_cp/sqlite_store.py:get_scan_output`
- Add: `src/fitcv_cp/sqlite_store.py:query_scan_jobs`
- Add: `src/fitcv_cp/sqlite_store.py:transition_scan_lifecycle`
- Add: `src/fitcv_cp/sqlite_store.py:preview_delete_archived_scans`
- Add: `src/fitcv_cp/sqlite_store.py:delete_archived_scans`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Task 3 frontend contract checkpoint accepted.
- Schema uses existing local SQLite migration path; no migration framework is added.

**Steps:**
- [x] Step 1: Add failing migration and store tests for `tracked_companies`, `scans`, `scan_inputs`, `scan_outputs`, and `run_scan_inputs`, including constraints, foreign keys, indexes, and idempotent repeated schema initialization.
- [x] Step 2: Add registry CRUD required by V1 with canonical URL uniqueness, revisions, active-scannable query, restart persistence, and no provider metadata duplication.
- [x] Step 3: Make `create_scan(..., idempotency_action_id=...)` run under `BEGIN IMMEDIATE`, re-read the reserved action, return its existing Scan when provisional response contains `scan_id`, otherwise insert the queued Scan and immutable input plus write provisional `scan_id` response in the same transaction; route retry resumes enqueue for that Scan instead of creating another.
- [x] Step 4: Add list, detail, capability projection input, output commit, output read, paginated projection from `output_json`, cancellation, Run Again input retrieval, archive, unarchive, delete preview, and delete operations.
- [x] Step 5: Enforce output immutability, terminal-status immutability, revision checks, no archive while non-terminal, no delete while referenced, and no second persisted Scan-job table.
- [x] Step 6: Switch `ControlPlaneStore` Scan defaults from `_scan_backend_unavailable` to SQLite functions while retaining override slots used by tests and temporary mock app.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_sqlite_store.py -k "tracked_company or scan or run_scan_input" -q`
- [x] `uv run python -m compileall -q src/fitcv_cp/sqlite_store.py src/fitcv_cp/store.py`
- Expected: schema initialization is idempotent; restart preserves resources; injected stops after reservation and after Scan commit replay one Scan identity; invalid mutation rolls back fully; exact output bytes and digest remain stable.

**Exit Criteria:**
- Every resource and lifecycle operation used by frontend has a SQLite implementation with transaction and restart proof.

### Task 5: Implement Verification, Queueing, And Scan Worker

**Purpose:**
- Execute real tracked-company acquisition asynchronously through existing provider, queue, event, and canonical-output owners.

**Specification Coverage:**
- Company verification; asynchronous execution; filtering and ordering; publication windows; cancellation; events; atomic provider failure; output integrity; Run Again.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/job_sources.py:build_scanner_request`
- Inspect: `src/fitcv/job_sources.py:acquire_scanner_jobs`
- Inspect: `src/fitcv_cp/queue.py:enqueue_run_with_job_id`
- Inspect: `src/fitcv_cp/models.py:ProcessEvent`
- Add: `src/fitcv/job_sources.py:verify_scanner_portal`
- Add: `src/fitcv_cp/queue.py:enqueue_scan_with_job_id`
- Add: `src/fitcv_cp/scan_worker.py:execute_scan`
- Modify: `src/fitcv_cp/app.py:create_scan`
- Modify: `src/fitcv_cp/app.py:verify_tracked_company`
- Modify: `src/fitcv_cp/app.py:create_tracked_company`
- Modify: `src/fitcv_cp/app.py:cancel_scan`
- Modify: `src/fitcv_cp/app.py:run_scan_again`
- Modify: `tests/test_job_sources.py`
- Add: `tests/test_fitcv_cp/test_scan_worker.py`
- Modify: `tests/test_fitcv_cp/test_queue.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 4 persistence complete.
- Existing Option C provider registry remains provider-routing SSOT.

**Steps:**
- [x] Step 1: Add fixture-backed verification tests for supported, unsupported, ambiguous, unsafe, duplicate, unreachable, malformed, and successful portal proposals.
- [x] Step 2: Implement bounded `verify_scanner_portal` by reusing provider detection, URL security, transport limits, and provider parsing; return safe normalized identity only.
- [x] Step 3: Add queue submission using one stable queue job ID derived from `scan_id`; pending request replay may call enqueue again with that identity, while enqueue failure terminalizes the same Scan as `scan_enqueue_failed` without a queued orphan.
- [x] Step 4: Implement atomic compare-and-swap worker claim from `queued` to `running`, then progress, process events, company-order acquisition, canonical title and location filters, stored publication cutoff, global row cap, cooperative cancellation, canonicalization, and atomic output commit; duplicate claim exits before provider work and writes no event or output.
- [x] Step 5: Fail entire Scan on listing, required-detail, timeout, malformed payload, or canonicalization failure; persist no output and retain bounded redacted diagnostic events.
- [x] Step 6: Permit successful `[]`, set `use_for_run = false`, keep Download JSON enabled, and stop event polling after final cursor fetch.
- [x] Step 7: Implement Run Again as new Scan creation using current registry rows and fresh publication cutoff while preserving original logical filters and `rerun_of_scan_id`.

**Verification:**
- [x] `uv run pytest tests/test_job_sources.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_app.py -k "scan or tracked_company" -q`
- [x] `uv run python -m compileall -q src/fitcv/job_sources.py src/fitcv_cp/queue.py src/fitcv_cp/scan_worker.py src/fitcv_cp/app.py`
- [x] Add a duplicate-worker test proving one `queued` to `running` claim wins and the second invocation performs no acquisition, event append, or output commit.
- Required expected result: every deterministic failure commits zero output; cancellation commits zero output; successful output order and digest are deterministic; events contain no secrets or provider bodies.
- Non-hermetic release evidence: run `New-Item -ItemType Directory -Force .tmp-tests/managed-scan-live | Out-Null`, then the three exact provider commands below and record command exit, HTTP classification, output count, and artifact path.
  - `uv run python -m fitcv.job_sources --provider personio --company "areto consulting" --careers-url https://areto.jobs.personio.de --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/managed-scan-live/personio.json`
  - `uv run python -m fitcv.job_sources --provider greenhouse --company GROPYUS --careers-url https://job-boards.eu.greenhouse.io/gropyus --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/managed-scan-live/greenhouse.json`
  - `uv run python -m fitcv.job_sources --provider workday --company Zalando --careers-url https://zalando.wd3.myworkdayjobs.com/ZalandoSiteWD --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/managed-scan-live/workday.json`
- Live classification: a reachable provider response that violates canonical contract blocks that provider's release evidence; DNS, TLS, rate-limit, upstream HTTP availability, or legitimate zero-opening state is recorded as external evidence and does not replace or invalidate deterministic fixture proof.

**Exit Criteria:**
- Real Scan creation, execution, inspection, rerun, and cancellation satisfy same route tests previously served by mock adapter.

### Task 6: Implement Additive Run Input And Protected Provenance

**Purpose:**
- Replace exclusive managed Run source selection with upload plus ordered Scan outputs while preserving legacy callers.

**Specification Coverage:**
- Additive Run input; deterministic merge order; atomic validation and persistence; `run_scan_inputs`; errors; idempotency; replay independence; compatibility.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:trigger_run`
- Inspect: `src/fitcv_cp/app.py:_execute_trigger_with_inputs`
- Inspect: `src/fitcv_cp/sqlite_store.py:create_run_bundle`
- Inspect: `src/fitcv_cp/models.py:PipelineRun`
- Inspect: `src/fitcv_cp/templates/runs_list.html:triggerRun`
- Modify: `src/fitcv_cp/app.py:trigger_run`
- Modify: `src/fitcv_cp/app.py:_resolve_managed_run_jobs`
- Modify: `src/fitcv_cp/sqlite_store.py:create_run_bundle`
- Modify: `src/fitcv_cp/models.py:PipelineRun.jobs_input_source`
- Modify: `src/fitcv_cp/models.py:PipelineRun.jobs_input_manifest_json`
- Modify: `src/fitcv_cp/templates/runs_list.html:triggerRun`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Task 5 real Scan output and integrity contract complete.
- Route impact gate completed before editing `trigger_run`.

**Steps:**
- [x] Step 1: Record every JSON, multipart, path, paste, upload-mode, and scanner-mode caller of `POST /runs`; add regression tests before changing dispatch.
- [x] Step 2: Replace temporary mock-backed source reads with SQLite-backed output reads while preserving the Task 2 managed multipart dispatch and response shape; do not introduce a combined mode enum.
- [x] Step 3: Reject missing both sources with `validation_failed`; preserve existing upload errors; reject any stale, Archived, non-succeeded, empty, or integrity-invalid Scan with `scan_not_usable` or `scan_output_integrity_failed`.
- [x] Step 4: Parse upload when present, verify every Scan, merge upload first and Scans in applied order, preserve internal order, canonicalize once, and calculate idempotency fingerprint from upload digest, ordered Scan IDs and digests, Candidate Profile revision, and Run name.
- [x] Step 5: After all source validation, materialize the Run-owned filesystem projection through existing atomic file writing, then extend `create_run_bundle` with optional ordered Scan provenance and insert Run, `run_inputs`, Run job projection rows, and `run_scan_inputs` in one SQLite transaction; do not describe the filesystem write as part of that transaction.
- [x] Step 6: Delete the newly materialized filesystem projection when `create_run_bundle` raises before commit; retain it when database commit succeeds, including queue failure that terminalizes the persisted Run.
- [x] Step 7: Persist `jobs_input_source` as `upload`, `scan`, or `combined` provenance and one ordered `sources` manifest; keep relational deletion blocking in `run_scan_inputs`.
- [x] Step 8: Prove archive does not affect existing Run replay, referenced Scan delete is blocked, worker reads only Run-owned projection, duplicates are preserved, persistence failure leaves no Run rows or projection file, and queue failure retains the failed Run projection.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py -k "managed_run or scan_input or run_scan_input or trigger_run" -q`
- [x] `uv run python -m compileall -q src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/sqlite_store.py`
- [x] OpenAPI and multipart request tests prove new managed fields and legacy behavior coexist.
- Expected: upload-only, Scan-only, and combined requests share one result shape; merge and provenance order are deterministic; missing sources never return `empty_job_input`; injected bundle failure leaves no database rows or filesystem projection.

**Exit Criteria:**
- Actual Run frontend submits canonical managed request and queues one immutable combined projection with protected Scan references.

### Task 7: Remove Mock Adapter And Close Integration

**Purpose:**
- Make SQLite and worker behavior the only production Scan backend, retain deterministic test fixtures, reconcile documentation, and produce final evidence.

**Specification Coverage:**
- Mock removal; provider expansion isolation; frontend/backend parity; documentation SSOT; required evidence; completion criteria.

**Required Skills:**
- `skill-full-stack-integration`
- `ui-ux-pro-max`
- `skill-verification-before-completion`

**Files And Symbols:**
- Delete: `src/fitcv_cp/scan_mock.py`
- Add: `tests/test_fitcv_cp/scan_fixtures.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `docs/job-data-input.md`
- Modify after evidence: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`
- Delete after evidence: `docs/fitcv-scan-ui-prototype.integration.md`
- Verify unchanged visual source: `docs/fitcv-settings-ui-prototype.html`

**Dependencies:**
- Tasks 1 through 6 complete with task-local proof.

**Steps:**
- [x] Step 1: Move deterministic resource builders needed by tests into `tests/test_fitcv_cp/scan_fixtures.py`; tests inject store functions through existing `ControlPlaneStore` override seam.
- [x] Step 2: Delete mock app, mock scenario route, mock store, and every production import or reference; assert ordinary OpenAPI contains no mock route or schema.
- [x] Step 3: Seed a temporary SQLite data root through public store operations with Active, Archived, pending, succeeded, empty, failed, cancelled, and referenced Scans; create the integrity-invalid case only by tampering one copied output row directly in that disposable test database after normal commit, with no production corruption hook.
- [x] Step 4: Repeat critical browser flows: company search and add, New Scan validation, pending Console, Table and JSON output, pagination, archive symmetry, delete preview, upload plus ordered Scan selection, stale Scan submit recovery, keyboard flow, 390x844, 1440x900, 200% zoom, light, dark, reduced motion, and long content.
- [x] Step 5: Confirm Chrome DevTools network payloads, response codes, no duplicate submission, no console errors, and no layout shift in affected states.
- [x] Step 6: Update `docs/job-data-input.md` from direct scanner UI to managed tracked companies, reusable Scan outputs, additive Run input, immutable provenance, and legacy compatibility without copying provider or job schemas.
- [x] Step 7: Delete `docs/fitcv-scan-ui-prototype.integration.md` only after every listed state and evidence item passes; remove its frontmatter target and temporary-reference sentence from the parent specification while retaining the specification's durable UI invariants.
- [x] Step 8: Record any implementation deviation in this plan before final verification; do not mark plan or specification completed manually.

**Verification:**
- [x] `$matches = rg -n "scan_mock|/__mock__|FITCV_SCAN_MOCK" src; if ($LASTEXITCODE -eq 0) { $matches; throw "Production mock references remain" }; if ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }; "No production mock references."`
- Expected: command exits zero only when production `src` contains no mock adapter, route, import, or flag reference; test fixtures and historical plan text are inspected separately.
- [x] Broad diagnostic: `uv run pytest tests/test_job_sources.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q` produced 594 passes and three unrelated failures: two require the declared `local` extra, and one unchanged settings assertion expects the retired reset request.
- [x] Environment follow-up: `uv run --extra local pytest tests/test_fitcv_cp/test_app.py::test_trigger_runtime_envelope_snapshots_prompt_metadata_without_text tests/test_fitcv_cp/test_app.py::test_trigger_runtime_envelope_snapshots_system_retry_resource -q` passed both optional-keyring tests.
- [x] Changed-scope proof: exact provider, contract, worker, queue, SQLite provenance, Scan route, frontend, direct-load, stale-selection, and managed Run tests passed 54 tests.
- [x] `uv run python -m compileall -q src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/scan_contracts.py src/fitcv_cp/scan_worker.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/queue.py`
- [x] `git diff --check`
- Expected: focused suite, compilation, browser matrix, accessibility checks, and whitespace validation pass against real backend.

**Exit Criteria:**
- Production frontend and backend use one contract and real persistence; mock production code and temporary sidecar are absent; required evidence is ready for fresh completion verification.

## Execution Deviations And Evidence

- Browser matrix: Playwright MCP and Chrome DevTools MCP supplied the main real-backend interaction, network, console, viewport, theme, reduced-motion, and performance evidence when the packaged browser client was unavailable. Final long-output checks used the packaged in-app browser client against the same real SQLite server.
- Zoom substitution: the in-app browser did not expose a working native zoom setter, and `Ctrl` + `+` did not change `devicePixelRatio`. A 432 CSS-pixel viewport against the 864-pixel reference width exercised the equivalent 2x layout constraint; document overflow remained absent, while Table and JSON content stayed inside native horizontal scroll containers.
- Long-output proof: archived `scan-dc1cdf88748b` exposed 25 jobs with 10-row pagination. At the 432 CSS-pixel viewport, document `scrollWidth` remained below `innerWidth`; the 1320-pixel Table and 47,476-pixel JSON payload scrolled only within their owning containers.
- Console classification: stale Scan submission intentionally returns HTTP 409 and produces one failed-resource browser entry; no uncaught JavaScript error occurs, and the frontend refreshes eligible Scans while preserving upload and ordered selections.
- Live providers: Personio, Greenhouse, and Workday commands completed with three canonical jobs each. Artifacts are `.tmp-tests/managed-scan-live/personio.json`, `.tmp-tests/managed-scan-live/greenhouse.json`, and `.tmp-tests/managed-scan-live/workday.json`.
- Implementation corrections found during browser proof: shared page initialization moved before child scripts for direct loads; stale Scan reconciliation now refreshes eligible Scans and renders a removable unavailable selection.

## Verification

- `uv run pytest tests/test_job_sources.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q`
- `uv run python -m compileall -q src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/scan_contracts.py src/fitcv_cp/scan_worker.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/queue.py`
- Record the three Personio, Greenhouse, and Workday live command outcomes from Task 5 as non-hermetic release evidence; deterministic provider fixtures remain implementation completion proof, while reachable canonical-contract failures remain provider-specific release blockers.
- Focused planning validation: call `validate_artifact` from `scripts/validate_planning_lifecycle.py` for this plan and its parent specification; repository-wide historical metadata failures are reported separately and never fixed in this lane.
- Unified prototype JavaScript: extract inline `<script>` from `docs/fitcv-settings-ui-prototype.html` and run `node --check`.
- `git diff --check`
- `$matches = rg -n "scan_mock|/__mock__|FITCV_SCAN_MOCK" src; if ($LASTEXITCODE -eq 0) { $matches; throw "Production mock references remain" }; if ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }; "No production mock references."`
- GitNexus change detection or source-first equivalent confirms `/runs`, Scan routes, store methods, queue functions, and provider boundary changed only within planned blast radius.
- Playwright MCP completes the full real-backend flow and all state, keyboard, viewport, zoom, theme, reduced-motion, and focus checks.
- Chrome DevTools MCP confirms canonical payload order, response codes, no duplicate requests, no uncaught console errors, and stable layout.

## Completion Criteria

The plan is ready for completion verification when:

1. temporary mock routes and data prove every frontend state before real backend replacement
2. frontend templates call only canonical HTTP routes and derive actions from server capabilities
3. tracked-company registry, Scan input, output, lifecycle, events, and references persist through restart; pending request replay reuses one Scan and stable queue identity, and one worker claim wins
4. publication windows store stable cutoffs and apply documented timestamp and date-only semantics
5. provider and required-detail failures create no successful partial output
6. successful empty Scan remains downloadable and unusable for Run
7. upload-only, Scan-only, and combined Runs preserve deterministic order, immutable projection, complete provenance, atomic database failure, and no orphan filesystem projection
8. legacy Run source contracts remain covered and unchanged except for separately approved deprecation wiring
9. referenced Scans cannot be deleted and historical Runs execute without registry or live Scan output
10. production mock adapter and mock-only routes are deleted; deterministic fixtures remain test-owned
11. frontend integration sidecar is deleted only after matching real-backend and browser evidence passes
12. focused tests, compilation, contract checks, browser checks, accessibility checks, and whitespace validation pass
13. unrelated dirty workspace files and historical planning-validator findings remain untouched and classified
14. implementation deviations, substitutions, blockers, and external provider-test results are recorded

The plan may be marked `completed` only when `skill-verification-before-completion` runs fresh final proof, reconciles every task and acceptance criterion against repository evidence, finds no unresolved required work or unrecorded deviation, returns `verified`, and updates plan status.
