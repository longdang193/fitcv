---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-scan-run-pipeline
parent_spec: docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md
targets:
  - docs/learning/*.md
  - docs/api.md
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
  - src/fitcv_cp/scan_contracts.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/orchestrator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_lifecycle.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/templates/scans_list.html
  - src/fitcv_cp/templates/scan_detail.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/_jobs_input_sources.html
  - src/fitcv_cp/templates/_process_console.html
  - scripts/validate_template_required_sections.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_orchestrator.py
  - tests/test_fitcv_cp/test_admin_retry_endpoint.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_run_lifecycle.py
  - tests/test_job_sources.py
  - tests/test_fitcv_pipeline_prototype.py
  - tests/test_pipeline.py
  - tests/test_pipeline_store.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_outcome_fact.py
  - tests/test_pipeline_status_registry.py
  - tests/test_validate_template_required_sections.py
---

# Scan + Run Pipeline Patch Plan

## Goal

### 1. Executive Findings

**Goal:** make managed Scan a proven source of canonical Job Pipeline input, then make Trigger Run consume immutable copies from upload, one Scan, multiple Scans, or upload plus Scans without creating a second job schema or a second source-resolution path.

**Confirmed gaps, highest risk first:**

- Scan output is canonicalized in `src/fitcv_cp/scan_worker.py:execute_scan`, but `src/fitcv_cp/sqlite_store.py:commit_scan_output` persists only JSON-array shape. Persistence must re-run canonicalization and verify exact UTF-8 bytes, SHA-256, byte length, and record count before marking output usable.
- `ScanCreateRequest.total_rows` and the worker already enforce the active specification's global cap of `200`; the prototype limit is drift and must be reconciled to `200`. Provider requests remain capped at `200`; the worker must pass `min(remaining_rows, 200)` per company.
- `create_scan()` resolves publication cutoff during creation against `created_at`; preserve that stored value through claim, retry, and replay. The worker must never recompute cutoff from current time.
- Queue ID format `scan:{scan_id}` exists in `enqueue_scan_with_job_id`, but queue binding and worker liveness are not durable enough for restart and replay proof. Persist queue binding, heartbeat, claim identity, and reconciliation state without adding a second queue system.
- Existing process-event storage is reusable. Scan must emit bounded lifecycle, provider, filtering, canonicalization, output, cancellation, and failure events through `process_events`; no Scan-specific event table is planned.
- Trigger Run still contains a direct synchronous `source_mode == "scanner"` path in `app.py` and a separate multipart Scan path. Managed Run must use one resolver for upload-only, Scan-only, multi-Scan, and combined input, and the worker must consume only the copied Run snapshot.
- Scan Details already exposes Overview, immutable input, console, Table, JSON, pagination, and download surfaces, but pending, failed, cancelled, integrity-invalid, and empty-success states need one server-derived state contract and cursor-based polling.
- Tracked-company verification and creation routes exist, but the plan must prove provider-registry ownership, no persistence during verify, duplicate URL rejection, HTTPS validation, server-side revalidation during create, and discovery beyond the first 50 rows.
- Existing tests cover contract fragments, mock UI, and mock Scan behavior. They do not prove a live successful `Scan -> Run -> real Job Pipeline` path, immutable Run copies after Scan mutation, provider-failure atomicity, persistence cleanup, or upload-vs-Scan equivalence.

**Prototype/backend conflicts and decisions:**

1. **Total Rows:** use global Scan limit `1..200`, default `50`; retain provider request limit `<=200`; stop aggregation at global cap and align the prototype control with this contract.
2. **Publication cutoff:** store requested `published_window` and resolve `publication_cutoff` from Scan `created_at` during creation; reuse the stored cutoff for acquisition and let Run Again create a new Scan and cutoff.
3. **Canonical output:** reuse `fitcv.ingest.canonicalize_jobs` as sole canonicalizer; call it in worker and persistence boundary; reject non-canonical or digest-invalid output from Run selection.
4. **Events:** reuse `process_events` and `get_process_events("scan", scan_id, ...)`; event payloads remain bounded and diagnostic, not a second state store.
5. **Run sources:** upload bytes are materialized first, then selected Scan output bytes in ordered selection order; the combined canonical array and manifest follow the crash-consistent DB/filesystem/queue protocol before queueing.
6. **Run identity grains:** one caller-created `queue_job_id` identifies one durable submission/binding and is persisted before enqueue; one worker `attempt_id` identifies one execution try. RQ `Retry` and the inline retry loop may create multiple worker attempts under one submission. Manual Retry and Continue allocate a new submission and queue ID.

### Implementation Outcomes

- Scan creation, execution, cancellation, recovery, output integrity, details, download, lifecycle actions, and Run eligibility share one contract and survive process restart.
- Tracked-company discovery and management use the provider registry as SSOT; Scan creation stores immutable company snapshots and never accepts direct provider or careers URL input.
- Every usable Scan output is exact canonical UTF-8 JSON. Successful `[]` remains downloadable but is not selectable for Run.
- Trigger Run supports upload-only, Scan-only, multi-Scan, and upload plus Scan sources through one source-resolution path, with upload rows first and selected Scan rows following in stable order.
- Run persistence records immutable job bytes, manifest, source provenance, Scan output digests, and run-owned `jobs_path` through a crash-consistent DB/filesystem/queue protocol; pre-commit persistence failure removes staged files and creates no partial rows, while post-commit enqueue failure retains an inspectable retryable Run.
- The managed Run snapshot has an explicit immutable contract marker; marked snapshots validate strictly, while unmarked historical rows retain legacy compatibility without being misclassified as corrupt managed Runs.
- The real Job Pipeline consumes the same canonical array for Scan and equivalent uploaded JSON without a Scan-specific downstream adapter.
- Tests and live evidence prove prototype parity, HTTP contracts, SQLite final state, worker behavior, queue recovery, UI state transitions, and one successful Scan-to-Run-to-pipeline execution.

## Implementation Outcomes

The plan changes only listed target files and existing canonical helpers. `src/fitcv/ingest.py` and `src/fitcv/job_sources.py` remain read-only canonical owners unless a focused failing test proves an existing owner cannot express the approved contract; no duplicate schema or provider rule is introduced. Existing user changes in `data/sample_data_engineer_jobs.json`, `data/sample_jobs - Copy.json`, `data/sample_jobs_1.json`, and `data/sample_jobs_2.json` remain untouched.

## 2. End-to-End Data Flow

| Boundary | Current owner and behavior | Required patch and proof |
| --- | --- | --- |
| Scan form | `src/fitcv_cp/templates/scans_list.html` builds `ScanCreateRequest` from dialog fields, company picker, title and location lists, publication window, and total rows. | Align labels, limits, validation, disabled state, keyboard focus, mobile layout, and ordered selection with prototype. Prove request body and duplicate-submit lock in `test_app.py`. |
| Tracked-company lookup | `app.py` routes `/tracked-companies`, `/tracked-companies/actions/verify`, and `/tracked-companies`; `sqlite_store.query_tracked_companies`, `create_tracked_company`; provider verification is delegated to `verify_scanner_portal`. | Keep verify side-effect free; revalidate provider, normalized HTTPS URL, duplicate URL, and registry revision during create; expose server pagination and filtered Select all. Prove Personio, Greenhouse, Workday, invalid, duplicate, and unsupported cases. |
| Scan request | `app.py:post_scan` validates `ScanCreateRequest`, reserves idempotency, calls `run_store.create_scan`, then enqueues. | Preserve `Idempotency-Key`, ordered unique `company_ids`, stable error envelope, and one reservation. Validate registry IDs server-side and snapshot company rows in the same transaction. |
| Scan persistence | `sqlite_store:create_scan` writes `scans` and `scan_inputs`; `_scan_resource` derives capabilities; output and events are read from separate tables. | Freeze immutable input, requested window, company snapshots, and revision. Add durable queue binding, heartbeat, claim token, and output manifest checks. Keep lifecycle and capability derivation centralized. |
| Queue | `queue.py:enqueue_scan_with_job_id` uses `scan:{scan_id}` for RQ and inline execution; job ID is not sufficient recovery evidence by itself. | Persist queue binding after enqueue, make enqueue replay idempotent, reconcile queued and running states from queue status plus heartbeat, and prevent a stale worker from leaving `running` forever. |
| Scan worker | `scan_worker:execute_scan` claims, reads input, requests up to `200` per company, filters title/location/date, canonicalizes, and commits; exceptions fail Scan. | Claim once; use the stored created_at-resolved cutoff; emit bounded events; use global cap `200`; pass remaining provider cap; enforce required provider-detail success; canonicalize and validate before commit; terminalize cancellation and failure atomically. |
| Scan output | `sqlite_store:commit_scan_output`, `get_scan_output`, `query_scan_jobs`; `/scans/{scan_id}/output` returns stored bytes; `_scan_resource` checks digest and byte length. | Persist exact canonical bytes plus digest, byte length, and count. Recompute all values and canonical validity on read. Download exactly persisted bytes. Table and JSON use same output bytes; pagination never creates a second truth. |
| Scan Details | `app.py:admin_scan_detail` passes Overview, input, output pages, output JSON, and process console to `scan_detail.html`; `_process_console.html` renders current events. | Add pending, failed, cancelled, integrity-invalid, empty-success, and success states from server capabilities. Poll events and resource with cursor until terminal state; preserve focus and stop polling after terminal. |
| Run selection | `runs_list.html` queries `/scans?lifecycle=active&usable_for_run=true`, renders picker, and keeps upload selection. | Use `use_for_run` only from server capabilities: active, succeeded, integrity-valid, non-empty. Add search, pagination beyond 50, filtered Select all, stale selection removal, and explicit `scan_not_usable`. |
| Run request and assembly | `app.py:trigger_run` has JSON direct scanner acquisition and multipart Scan assembly branches; `sqlite_store:create_run_bundle` persists `run_inputs`, `run_scan_inputs`, and `run_jobs`. | Remove managed V1 dependence on direct provider/company/URL input. Centralize multipart source resolution; upload first, Scan IDs in request order; reject missing source, duplicate IDs, unavailable or unusable Scans; persist manifest, source digests, and immutable bytes through the crash-consistent DB/filesystem/queue protocol. |
| Run worker | `worker_job:_verify_jobs_input_projection` validates path, digest, manifest, and projected bytes before pipeline execution. | Extend verification to include source manifest and Scan digest/count/ordinal facts, while preserving legacy path runs. Worker reads only copied Run projection and never reopens live Scan output. |
| Job Pipeline | `src/fitcv/pipeline.py` and `worker_job.py` consume canonical Run input. | Prove Normalize, Enrichment, Screening, Shortlisting, Ranking, optional CV stages, counts, terminal status, and Run Details for representative upload-only, Scan-only, and combined modes. |

## 3. Prototype-to-Frontend Parity Matrix

| Prototype | Current frontend | Status | Evidence | Patch |
| --- | --- | --- | --- |
| Scans workspace has Active and Archived tabs, counts, status badges, selectable rows, pagination, empty state, New Scan action, and archive/unarchive/delete controls. | `scans_list.html` has tabs, counts, table, page controls, dialog, and bulk action scripts. | Partial | `tests/test_fitcv_cp/test_app.py:test_admin_scans_workspace_matches_managed_scan_intent`, `test_admin_scans_workspace_uses_prototype_visual_components`; template currently mixes server state and client action rendering. | Render all action availability from `ScanCapabilities`; preserve selection on page changes; make stale bulk preview atomic; add responsive table labels, empty states, keyboard focus, and accessibility assertions. |
| New Scan form permits optional name, required tracked companies, comma-separated titles and locations, all publication options, total rows, validation, and disabled Start Scan. | `scans_list.html` exposes these controls and posts JSON. | Prototype/backend drift | `scan_contracts.py:ScanCreateRequest` uses `le=200`; align prototype copy and validation cases to the active `200` contract. | Set UI/backend global limit to `200`; keep provider limit hidden from user; show stable field errors and retain values after failure. |
| Tracked-company picker searches company, provider, and domain/URL, supports Select all filtered, clear/apply, pagination, more than 50 records, and Add Company. | Picker loads `/tracked-companies` and has selection controls; coverage is structural. | Partial | `app.py` tracked-company routes; `scans_list.html`; existing app template tests. | Add server pagination/search state, filtered-set selection semantics, result-count feedback, stale-page handling, and Add Company verification/create flow. |
| Add Company verifies Personio, Greenhouse, Workday, rejects invalid or unsupported URLs, blocks duplicate careers URL, requires HTTPS, and does not persist on verify. | `app.py:_verify_tracked_company_input` and provider routes exist. | Partial | `tests/test_job_sources.py` proves provider detection/parsers; no complete verify-no-write and create-revalidate matrix. | Keep `verify_scanner_portal` as provider owner; add direct route tests and transaction assertions; surface exact field errors without writing a company during verify. |
| Scan Details shows immutable Overview/Input, company snapshot, events, output states, Table, JSON, pagination, Download JSON, and Run Again. | `scan_detail.html` renders these sections and routes; `admin_scan_detail` loads first page and up to 200 events. | Partial | `test_admin_scan_detail_reuses_detail_structure_and_output_views`, `test_admin_scan_detail_uses_prototype_visual_components`. | Add cursor polling, terminal stop, output integrity state, empty-success state, exact bytes download, same-data Table/JSON assertion, and Run Again snapshot proof. |
| Run picker selects only usable successful Scans and supports search, pagination, Select all filtered, stale selection handling, and upload coexistence. | `runs_list.html` queries eligible Scans and includes upload plus Scan controls. | Partial | `test_run_trigger_uses_additive_upload_and_scan_sources`, `test_run_trigger_reconciles_stale_scan_selection_without_losing_upload`. | Drive every state from `/scans` capabilities; preserve upload when Scan selection becomes stale; reject stale submit server-side; cover >50 eligible Scans. |
| Run Details displays source type, upload metadata, ordered Scan provenance, immutable snapshot, manifest, and pipeline results. | `run_detail_tab_jobs_input.html` and `_jobs_input_sources.html` render source badges and links. | Partial | `test_managed_run_combined_manifest_orders_upload_before_scan`; current direct scanner metadata still exists in `app.py`. | Render one manifest model for upload and Scans; show ordinal, digest, record count, and copied snapshot facts; remove V1 direct scanner fields from managed UI. |
| Console and async interactions have loading, retryable error, stale response, disabled, focus, reduced-motion, and mobile behavior. | Shared helpers exist and Scan scripts use idempotency keys; console is mostly initial render. | Missing for live Scan flow | Existing shared async tests and static tests; no browser proof for Scan polling or responsive states. | Reuse shared async helpers and focus patterns; add cursor-based refresh, `aria-live`, focus restoration, reduced-motion-safe transitions, 390px/1280px browser assertions, and no polling after terminal state. |

## 4. Frontend-to-Backend Contract Matrix

| UI action | Endpoint | Request | Response | Current gap | Patch |
| --- | --- | --- | --- | --- | --- |
| Load tracked companies | `GET /tracked-companies` | `search`, `page`, `page_size` | Collection with filtered `items`, `total`, page metadata | UI discovery and filtered Select all are not proven beyond first page. | Keep server search/pagination; return stable total and query echo; select only IDs in current filtered result set and expose total selected. |
| Verify Add Company | `POST /tracked-companies/actions/verify` | `{company_name, careers_url}` | Verification result with provider identity, normalized URL, and stable error envelope | Verification ownership and no-write behavior need direct proof. | Call provider registry only; never insert `tracked_companies`; return `provider_id` and normalized URL for create. |
| Create tracked company | `POST /tracked-companies` | `{company_name, careers_url}` plus idempotency and current verification data | Created company resource | Create must revalidate and reject duplicate normalized URL. | Re-run HTTPS/provider/duplicate validation in one SQLite transaction; persist provider ID only from registry resolution. |
| Create Scan | `POST /scans` | `{scan_name, company_ids, job_titles, locations, published_window, total_rows}` and `Idempotency-Key` | `201` data envelope with queued Scan resource | Request shape exists; limit, registry snapshot, idempotency conflict, and enqueue failure need complete proof. | Normalize ordered unique lists; accept total rows through `200`; validate active scannable IDs; create immutable snapshots; enqueue once; return stable errors. |
| List Scans | `GET /scans` | lifecycle, execution status, usable flag, search, page, page size | Collection of resources with capabilities | Capability derivation is present but integrity and stale-worker state are incomplete. | Recompute output integrity and canonical record count on read; reconcile stale execution state before response; use one capability contract. |
| Scan detail | `GET /scans/{scan_id}` | Scan ID | Full resource with input, snapshots, manifest, failure, capabilities | Detail does not consistently prove pending/integrity-invalid state transitions. | Return immutable input and current integrity state; never expose mutable registry values as historical input. |
| Scan events | `GET /scans/{scan_id}/events` | cursor, bounded limit | Events plus next cursor and terminal hint | Initial events work; cursor polling and bounded lifecycle payloads need proof. | Use `get_process_events("scan", scan_id, limit, cursor)`; return monotonic cursor; poll resource and events until terminal. |
| Scan jobs | `GET /scans/{scan_id}/jobs` | page, page size | Paginated canonical jobs | Table path may be trusted independently from JSON output. | Parse the exact persisted canonical bytes for the page; return only rows from that array and its stored count. |
| Download Scan output | `GET /scans/{scan_id}/output?download=true` | Scan ID | Exact canonical UTF-8 bytes, digest ETag, content length | Endpoint returns stored bytes but read-time canonical/integrity state is incomplete. | Allow download for succeeded output including `[]`; deny missing or integrity-invalid output; preserve exact bytes and digest headers. |
| Cancel, archive, unarchive, delete | Scan action endpoints in `app.py` | expected revision and idempotency key; delete uses preview revision | Updated resource or atomic batch result | State rules exist but stale preview, referenced delete, and queue cancellation need full matrix. | Route all actions through `derive_scan_capabilities` and SQLite CAS transactions; block referenced delete at DB level; cancel queue and worker cooperatively. |
| Load eligible Run sources | `GET /scans?lifecycle=active&usable_for_run=true` | search, page, page size | Only active, succeeded, non-empty, integrity-valid resources | UI assumes result list is authoritative but stale selections can change between load and submit. | Keep server eligibility SSOT; submit resolver rechecks every Scan in one transaction and returns `scan_not_usable` with field-level IDs. |
| Trigger managed Run | `POST /runs` multipart | optional `jobs_file`, ordered `scan_ids`, required `profile_id`, run settings, idempotency key | `201` Run resource | Current direct scanner JSON and multipart branches can drift; missing-source contract is incomplete. | Resolve upload and Scan sources once; upload first; preserve selected order; canonicalize merged jobs; persist manifest and provenance through the crash-consistent protocol; queue only after DB commit. |
| Inspect Run input | `GET /runs/{run_id}` and admin Run Details | Run ID | Run resource plus `jobs_input_source`, manifest, source metadata | Existing renderer supports source rows but direct scanner and managed Scan metadata differ. | Use one manifest schema; include upload digest/count and ordered Scan IDs/digests/counts; display copied bytes, not live source state. |
| Execute Run | Existing run queue and worker | Run-owned `jobs_path` and snapshot fields | Stage events, counts, terminal status | Worker integrity checks exist but Scan provenance and representative pipeline trace are unproven. | Extend `_verify_jobs_input_projection`; execute real pipeline from copied canonical JSON; preserve legacy path compatibility. |


## Task Breakdown

### 5. End-to-End Test Matrix

| Scenario | Fixture/input | UI assertion | API assertion | Persistence assertion | Pipeline assertion | Existing coverage | Missing test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Canonical fixture baseline | `data/sample_jobs_1.json` | Upload flow accepts file and shows count. | Upload request returns stable validation or success envelope. | SHA-256 `37c22534ed37269391efec803efb6e947e7f848c1089b0030ea49cf8c66f3f8`, byte length, and count persist. | Normalize sees 13 canonical jobs. | `test_job_sources.py` and run input tests partially cover canonicalization. | Add explicit fixture contract assertion before Scan tests. |
| Canonical fixture baseline | `data/sample_jobs_2.json` | Upload flow accepts file and shows count. | Same contract as first fixture. | SHA-256 `f327e69f32facf08749b8b7e65dedc7d6ad097b33d9c4dcc5bf4cc36653d5731`, byte length, and count persist. | Normalize sees 6 canonical jobs. | Partial. | Add second fixture assertion and pipeline count check. |
| Scans workspace parity | Active, archived, empty, running, failed, cancelled Scans | Tabs, counts, badges, selection, pagination, empty states, actions, mobile table, keyboard focus. | `GET /scans` returns capabilities matching status and lifecycle. | No action mutates immutable input; stale batch preview deletes nothing. | Not applicable. | Mock/static app tests are partial. | Add state-table route tests and browser viewport/accessibility assertions. |
| New Scan validation | Optional name, duplicate lists, empty company IDs, all publication windows, total rows 1, 50, 200, and 201 | Start disabled until required company selection and valid fields; field errors retain input. | `POST /scans` preserves order, deduplicates lists, rejects >200, requires idempotency. | No Scan row on validation failure or idempotency conflict. | Not applicable. | `test_scan_contracts.py` covers normalization and empty company selection; limit is contradicted. | Add limit, all-window, duplicate-submit, and stable-error tests. |
| Tracked-company management | Active registry with more than 50 rows; Personio, Greenhouse, Workday; invalid, unsupported, duplicate, credentialed, query, and fragment URLs | Search filters by company/provider/domain; Select all filtered selects only current result set; verify does not close or persist unexpectedly. | Verify returns provider/normalized URL; create revalidates and returns duplicate or unsupported errors. | Verify leaves row count unchanged; create inserts one normalized URL atomically. | Provider registry remains sole detector. | Provider parser tests are partial; route tests are missing. | Add route/store/provider boundary matrix and >50 pagination proof. |
| Scan transport | Ordered company IDs, title/location lists, publication window, total rows, repeated idempotency key, conflicting payload | One click creates one Scan and navigates to details. | Exact JSON body, `Idempotency-Key`, replay equality, conflict error, enqueue-failure error. | One Scan input row with immutable snapshots and no duplicate Scan. | Not applicable. | Mock replay test exists. | Add live app transport and persistence assertions. |
| Successful Scan | Provider fixtures return jobs across multiple companies with mixed titles, locations, dates, and >200 rows | Progress and console advance; terminal success shows output actions. | Status `queued -> running -> succeeded`; global count never exceeds requested cap. | One output row; count, digest, bytes, and canonical validity agree. | Canonical array passes same validation as upload. | Worker has one mock success test. | Add multi-company global cap, filter, cutoff, event, and output integrity assertions. |
| Cancellation and recovery | Queued and running Scan; worker interruption; stale heartbeat | Cancel button moves to Cancelling then Cancelled; retry/reload does not create duplicate work. | `cancel` is CAS/idempotent; replay claim has one winner; stale worker is reconciled. | No successful output for cancelled Scan; queue binding and heartbeat survive restart. | Pipeline never receives cancelled output. | Queue status tests are partial; Scan recovery missing. | Add injected interruption, restart reconciliation, and single-winner tests. |
| Provider failure atomicity | One provider success followed by listing, detail, timeout, malformed payload, or required-detail failure | Details show failed state and bounded actionable error, not warning-only success. | Terminal `failed` response and failure event; no partial success response. | No `scan_outputs` row; diagnostic events remain; input remains inspectable. | No Run eligibility and no downstream job count. | Provider error tests are partial. | Add worker failure matrix for each required failure class. |
| Scan output views | Successful non-empty, successful `[]`, corrupt bytes, wrong digest, wrong count, non-canonical object | Download enabled for `[]`; Run action disabled; Table and JSON show same jobs; integrity state visible. | Download returns exact bytes or stable `scan_output_integrity_failed`; jobs endpoint paginates same array. | Recomputed digest, byte length, canonical bytes, and count gate capabilities. | Only valid non-empty output can enter Run. | Empty success and mock integrity UI are partial. | Add byte-level store/API/detail tests and table/JSON equivalence. |
| Run eligibility | Active successful non-empty valid Scan; running, failed, cancelled, archived, empty, corrupt Scans | Picker excludes ineligible rows; search and filtered Select all work over >50; stale selection retains upload. | `GET /scans?usable_for_run=true` and `POST /runs` agree; stale submit returns `scan_not_usable`. | No `run_scan_inputs` row on rejected request. | Not applicable. | UI selection tests are partial. | Add lifecycle mutation between list and submit. |
| Upload-only Run | `sample_jobs_1.json` plus active Candidate Profile | Upload-only trigger succeeds; Run Details shows upload source. | Multipart has file and no Scan IDs; missing-source validation does not fire. | Snapshot, manifest, path, digest, count, and `jobs_input_source` are correct. | Real pipeline consumes 13 jobs and reaches expected terminal state. | Run path tests cover persistence partially. | Add end-to-end worker trace with stage counts. |
| Scan-only Run | One valid non-empty Scan plus Candidate Profile | Picker selection submits without upload. | Multipart contains ordered one Scan ID; profile required. | Upload rows absent; Scan provenance ordinal 0, digest, count; copied bytes are immutable. | Real pipeline consumes exact Scan array. | Managed Scan-only route test exists but mocks acquisition. | Replace/add live persisted Scan proof. |
| Multi-Scan Run | Two successful Scans with distinct ordered jobs | Picker order is visible and preserved. | Multipart contains unique Scan IDs in selection order. | `run_scan_inputs` stores ordinals and digests; merged manifest is deterministic. | Pipeline input count equals sum of Scan counts. | Combined manifest test is partial. | Add archive-after-create and worker replay proof. |
| Combined Run | Upload plus one or multiple Scans | Upload remains first; Scan picker and file state coexist. | Multipart contains file and ordered IDs; source validation accepts either or both only when at least one exists. | Upload source ordinal precedes Scan ordinals; one crash-consistent bundle protocol and run-owned path. | Pipeline consumes upload rows first, then Scan rows, preserving each internal order. | Existing app tests cover structural manifest ordering. | Add byte-level ordering and stage-count assertions. |
| Persistence failure before DB commit | Valid source resolution with injected bundle/filesystem failure | UI shows retryable error and does not navigate to phantom Run. | Stable error; no queue submission. | No Run, `run_inputs`, `run_jobs`, or `run_scan_inputs`; staged/unreferenced projection deleted. | No pipeline execution. | Missing. | Add injected pre-commit failure tests. |
| Enqueue failure after DB commit | Valid committed bundle with injected enqueue failure | UI shows inspectable retryable Run, not phantom success. | Stable failure/retry or reconciliation response. | One Run/input/job/provenance bundle remains with stable queue ID and no duplicate attempt. | No pipeline execution until retry/reconciliation. | Missing. | Add post-commit enqueue and response-loss tests. |
| Historical integrity | Create Run, then archive/delete-attempt Scan and change registry | Run Details remains readable and source links show historical state. | Referenced Scan delete is blocked; archive does not revoke existing Run. | Run bytes, manifest, and digests stay unchanged; DB FK blocks bypass. | Worker executes from copy after source mutation. | `_verify_jobs_input_projection` tests cover path drift and legacy runs. | Add Scan mutation and worker replay test. |
| Upload-vs-Scan equivalence | Download one successful Scan artifact, then use same bytes as upload | Both Run flows show equivalent jobs and pipeline result, different provenance labels. | Source metadata differs only by acquisition mode. | Canonical input bytes, digest, count, and order match. | Normalize through optional CV stages sees equivalent jobs and counts. | Missing live proof. | Add paired live run and compare stage/output fingerprints. |
| Full live path | Active, succeeded Candidate Profile; real provider Scan; local pipeline dependencies | Scan Details reaches success, Run picker selects it, Run Details shows results. | All lifecycle and Run endpoints return expected envelopes. | Scan output and Run snapshot remain exact after queue execution. | `Scan -> Run -> Normalize -> Enrichment -> Screening -> Shortlisting -> Ranking -> optional CV -> terminal` completes without adapter. | No confirmed live path. | Make this mandatory stop-gate evidence. |

### 6. Implementation Patch Plan

#### Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-backend-verification`, `skill-full-stack-integration`, `ui-ux-pro-max`, `skill-verification-before-completion`, `skill-code-standards`, `skill-systematic-debugging`
- Isolation: current workspace; preserve unrelated user changes
- Commit policy: plan remains `proposed` during planning; after approval, the lead changes it to `active` before Task 1, then updates the task ledger and creates an authorized checkpoint commit after each accepted task proof. No push, merge, publication, or destructive cleanup without separate authorization.
- Preauthorized local actions: read named source and tests, edit listed targets, run focused tests, run configured local app/browser checks, inspect Git status and diffs
- User-approval actions: push, merge, publication, destructive cleanup, discard of user changes, external provider writes
- Parallel ownership: none; `app.py`, `sqlite_store.py`, queue lifecycle, and shared templates create hidden ordering dependencies
- Sequential execution: Tasks 1 through 7 are the only task graph; stop if contract, schema, base, plan, or user-owned working-tree changes diverge

## Coordination State

- Coordination owner: single lead controller
- Branch: `main`
- Base commit: `efd3b735a4c1a52c14f965be1b5c0f5891354c91`
- Active task(s): none; Task 7 verification complete
- Expected workspace: preserve deleted `data/sample_data_engineer_jobs.json`, deleted `data/sample_jobs - Copy.json`, and untracked `data/sample_jobs_1.json`, `data/sample_jobs_2.json`
- Next action: hand off verified workspace to authorized branch finishing
- Blockers: none
- Runtime evidence: `.env` credentials plus `config/runtime/control_plane.yaml`; schema-5 temporary database; fresh real-provider Scan and Run traces; fixture upload probes; downloaded Scan-output upload equivalence; archive/delete guard; registry-mutation immutability; worker replay; fresh browser/API evidence; broad tests and repository validators pass

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | completed | current | codex | none | focused contract tests | `py -m pytest -q tests/test_fitcv_cp/test_scan_contracts.py`; 11 passed; focused Scan route tests; 4 passed |
| Task 2 | completed | current | codex | Task 1 | store transaction and integrity tests | `py -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py`; 121 passed; Scan route slice `py -m pytest -q tests/test_fitcv_cp/test_app.py -k "scan"`; 21 passed; `git diff --check` passed; Windows temp-directory cleanup warning remains nonblocking |
| Task 3 | completed | current | codex | Task 2 | worker, failure, cancellation, recovery tests | combined store/queue/worker proof: 144 passed; worker/queue slice: 21 passed; Scan route slice: 21 passed; post-fix dependent proof: `py -m pytest -q tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py` — 241 passed; `git diff --check` passed |
| Task 4 | completed | current | codex | Task 1, Task 2, Task 3 | route and multipart contract tests | managed Run slice: 8 passed; managed provenance/marker slice: 5 passed; existing Windows temp cleanup warning remains nonblocking |
| Task 5 | completed | current | dcode-project | Task 4 | prototype/UI and polling tests plus browser parity evidence | `py -m pytest -q tests/test_fitcv_cp/test_app.py -k "scan"`: 22 passed; extracted-template Node harness: 1 passed; `git diff --check` passed; in-place refresh preserves output view/focus, binds one handler, advances cursor monotonically, and avoids terminal navigation. Fresh browser parity captured on mock app at `http://127.0.0.1:8001`: pending `scan-1047` polled `/scans/{id}` and `/events?limit=50` with URL/navigation count unchanged; succeeded `scan-1048` rendered output rows, Download JSON, Run Again, and Archive; mobile/desktop overflow and unlabeled-control checks passed; Lighthouse accessibility 96, best practices 100. |
| Task 6 | completed | current | codex | Task 1, Task 2, Task 3, Task 4, Task 5 | focused pytest and projection-integrity tests | `51 passed`; `674 passed`; `37 passed`; managed marker regression `4 passed`; source guard added and rerun clean |
| Task 7 | completed | current | codex | Task 1, Task 2, Task 3, Task 4, Task 5, Task 6 | live Scan-to-Run trace plus browser/API stop-gate proof and sample-fixture upload probes | Schema-5 live runtime used `.env` plus `config/runtime/control_plane.yaml`; live DB `C:\tmp\fitcv-live-probe-d9447c36101f49349b25618f52630771\fitcv_cp.sqlite3`. `data/sample_jobs_1.json` (13 records, source bytes/SHA `72199`/`d1b843922aac0608149bc191789b6ecbaccc8792a8ef7db7f615a60981378820`) -> Run `283d894b-1cc9-4754-b7d7-fb4079ec8ba4` succeeded; persisted manifest/copy `13` records, `71458` canonical bytes, SHA `0e1354ecf164352560c85fcaa39c3ed77d5deb4a325289d50c8b323e6ced52c4`, stages enrichment/screening/shortlisting/ranking/cv-analysis `13/13`, cv-generation skipped, artifacts ZIP `176158` bytes. `data/sample_jobs_2.json` (6 records, source bytes/SHA `29444`/`ecf68bd62e6737949917d5e25665d87c9e329cc0ad8e0132701834a9991c6ab8`) -> Run `bea9db40-1994-4ae2-adca-ddd01034f98d` succeeded; persisted manifest/copy `6` records, `29311` canonical bytes, SHA `3f58f1d4f029338fda06e92ef939fd6e9e611b2f5c6b9486ae17ae8ccaa736a0`, same stage pattern, artifacts ZIP `97494` bytes. Reusing fixture 1 idempotency key replayed original Run ID with no duplicate. Fresh Greenhouse company `company-c1f51e88acca` produced Scan `scan-71386f8ea610` with queue binding `scan:scan-71386f8ea610`, `10` output records, output/download bytes `97645`, SHA `38a38c3271749ddf536890e68f81f66e9ca47137479d941756f38bb0ea7d6857`; `past_7_days` Scan `scan-ad9ea54f3bd0` persisted cutoff `2026-08-14T21:33:53Z`. Scan-only Run `c695a468-e49b-4503-b9ee-b98e85155b4d`, downloaded-output upload Run `5c1cd93e-dda3-4fc1-a54d-2770efeefa73`, and fresh combined Run `2ff74c71-0715-4e45-b33a-ce75f825dda7` succeeded; Scan-only/upload-equivalent share SHA `38a38c3271749ddf536890e68f81f66e9ca47137479d941756f38bb0ea7d6857`, `97645` bytes, `10` records, identical stage counts (`8` passed/`2` rejected), and terminal status. Combined input: `16` records, `11` passed, `5` rejected, all stages terminal. Fresh queue-binding probe Run `4b19a5ef-9151-40ce-bb28-573e10aa5bd7` reached `succeeded`; read-only query of `pipeline_runs` confirmed `queue_job_id` and `orchestration_run_id` both `run:4b19a5ef-9151-40ce-bb28-573e10aa5bd7`; API detail projection omits queue fields but persistence is intact. Archived Scan revision `5`; delete preview blocked with `run_count=1`; direct registry-name mutation left Scan snapshot name `Gropyus`, Run SHA, and succeeded results unchanged; worker replay after archive succeeded after clearing terminal `finished_at` on RUNNING transition. Initial fresh Scan enqueue exposed undefined `get_local_job_executor`; TDD regression watched red, one-line import fix applied, dependent proof `241 passed`. Fresh browser proof on mock app `http://127.0.0.1:8001`: pending `scan-1047` polled status/events with URL and navigation count stable; succeeded `scan-1048` rendered output table, 10-row page, JSON/download/Run Again/Archive actions; Lighthouse snapshot accessibility `97`, best practices `100`, agentic browsing `100`. Independent DeepAgents validator returned PASS; fresh proof reran dependent tests (`242 passed`), app/prototype tests (`459 passed`), validator tests (`25 passed`), template validator, and `git diff --check`. |

#### Task 1: Freeze Scan Contracts And Capability Rules

**Purpose:** establish one contract for limits, ordered inputs, lifecycle transitions, publication windows, and server-derived capabilities before changing persistence or consumers.

**Task Function:** reconcile approved Scan lifecycle semantics with current Pydantic contracts and existing canonical helpers.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: material contract ambiguity and downstream blast radius, bounded to one contract file and its tests.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independently check field limits, enum coverage, transition table, and capability truth table.

**Specification Coverage:** total rows, all publication windows, required company selection, ordered deduplication, immutable input, lifecycle symmetry, empty-success eligibility, and state-derived actions.

**Required Skills:** `skill-code-standards`, `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `src/fitcv/ingest.py:canonicalize_jobs`, `src/fitcv/job_sources.py:build_scanner_request`, `src/fitcv_cp/app.py:ScanCreateRequest` imports and error mapping.
- Modify: `src/fitcv_cp/scan_contracts.py:ScanCreateRequest`, `resolve_publication_cutoff`, `derive_scan_capabilities`, `validate_scan_transition`, and related constants.
- Verify: `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_app.py` Scan contract cases.

**Dependencies:** current spec and prototype decisions recorded above; no schema change before contract behavior is fixed.

**Authority:**
- Preauthorized local actions: edit contract definitions and focused tests; run contract and route tests.
- Stop for: a requirement that needs a new product behavior outside the approved spec, or a canonical-field change in `src/fitcv/ingest.py`.

**Steps:**
- [ ] Set `total_rows` default `50`, lower bound `1`, upper bound `200`; keep provider request cap separate and internal.
- [ ] Preserve ordered unique company, title, and location normalization with explicit list and item limits; preserve all six publication enum values.
- [ ] Keep `resolve_publication_cutoff` as the pure UTC resolver used during Scan creation with `created_at`; persist and reuse its result during execution.
- [ ] Keep `derive_scan_capabilities` as sole action and Run-eligibility truth, including empty-success download but `use_for_run = false`.
- [ ] Add parameterized tests for every lifecycle state, archive state, output integrity state, reference state, and invalid transition.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_scan_contracts.py`
- Expected: normalization, limit, cutoff, transition, and capability tests pass; no direct scanner schema is added.

**Exit Criteria:** contract tests prove the approved values and no consumer owns a second eligibility or transition rule.

#### Task 2: Make Scan And Run Persistence Crash-Consistent And Integrity-Checked

**Purpose:** persist immutable Scan inputs and canonical outputs, durable worker state, and a recoverable Run snapshot with complete provenance across separate DB, filesystem, and queue durability domains.

**Task Function:** extend existing SQLite transactions and schema migration helpers without adding a parallel persistence layer.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: backend state, migration, transaction rollback, integrity, foreign-key, and immutable snapshot risk.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: direct SQLite transaction and final-state validation must catch partial rows and digest drift.

**Specification Coverage:** Scan persistence, claim/recovery, output manifest, referenced delete restriction, Run source combinations, crash-consistent bundle protocol, orphan cleanup, immutable Run input, and historical integrity.

**Required Skills:** `skill-backend-verification`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`, `_scan_resource`, `create_scan`, `claim_scan_execution`, `commit_scan_output`, `get_scan_output`, `query_scan_jobs`, `create_run_bundle`, `preview_delete_archived_scans`, `delete_archived_scans`.
- Modify: same symbols and the existing `run_inputs`, `run_scan_inputs`, `pipeline_runs`, and `scans` schema migration path.
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py` persistence and route tests.

**Dependencies:** Task 1 contract; existing `run_scan_inputs` foreign key and `worker_job:_verify_jobs_input_projection` remain owners of their existing responsibilities.

**Authority:**
- Preauthorized local actions: additive SQLite migrations, transaction changes, store tests, and rollback assertions.
- Stop for: destructive schema rewrite, deletion of user data, or migration that cannot preserve existing legacy Run rows.

**Steps:**
- [ ] Add only the Scan execution metadata required for queue binding, claim identity, heartbeat, and recovery; migrate existing rows with safe null/default values.
- [ ] Add nullable, write-once `run_input_contract_version` to `run_inputs`; write `managed_v1` only for newly created managed snapshots after every required immutable field validates, leave historical/legacy rows null, and never backfill the marker into a row that cannot satisfy the full managed contract.
- [ ] Update `create_scan` to validate active scannable registry IDs, snapshot complete company rows in request order, resolve `published_window` against `created_at`, and persist the concrete cutoff for worker reuse.
- [ ] Update `claim_scan_execution` to use `BEGIN IMMEDIATE`, require queued active state, set `running`, `started_at`, claim token, and heartbeat in one winner transaction without recomputing the stored cutoff.
- [ ] Make `commit_scan_output` parse UTF-8 bytes, call `canonicalize_jobs`, require canonical serialized bytes, compute digest/length/count, and insert output plus succeeded state atomically.
- [ ] Make `_scan_resource`, `get_scan_output`, and `query_scan_jobs` recompute digest, byte length, count, and canonical validity before exposing download or Run capability.
- [ ] Make Run source resolution write `run_inputs` including `run_input_contract_version='managed_v1'`, `run_scan_inputs`, `run_jobs`, manifest, deterministic run-owned path metadata, and the caller-created stable `queue_job_id` in one DB transaction; treat that committed DB state as SSOT for later repair.
- [ ] Define one crash-consistent protocol: write and validate a staged projection, commit DB snapshot/path/queue ID, finalize or reconstruct the final projection from DB SSOT, enqueue by stable ID, and reconcile every interrupted state without duplicate execution.
- [ ] Distinguish pre-commit persistence failure (remove staged and unreferenced files; no Run rows) from post-commit enqueue failure (retain inspectable Run snapshot; expose retry/reconciliation; do not create another bundle).
- [ ] Preserve FK restriction for referenced Scan delete and make preview revision include current Scan revisions, eligibility, references, and missing IDs. Reconcile DB-committed/missing-file, DB-committed/not-enqueued, enqueue-unknown, and response-lost windows on startup or explicit retry.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py`
- [ ] Run injected persistence-failure tests that inspect every Run table and staged filesystem path.
- Expected: pre-commit failure leaves no Run rows or unreferenced projection; post-commit enqueue failure leaves one inspectable retryable Run with stable identity; DB-committed crash windows reconcile without duplicate queue work; valid output appears only after all integrity values match.

**Exit Criteria:** SQLite/filesystem/queue assertions prove atomic Scan output and crash-consistent Run bundle behavior for success, pre-commit failure, enqueue failure, replay, stale revision, recovery, and historical source mutation.

#### Task 3: Add Queue Recovery And Canonical Scan Worker Execution

**Purpose:** execute one Scan exactly once from immutable input, preserve global ordering and caps, and make Run submission identity distinct from worker-attempt identity while recovering stale queued or running work.

**Task Function:** implement queue binding, cooperative cancellation, worker heartbeats, provider acquisition, filtering, canonicalization, and terminal state transitions.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: concurrent worker claims, provider failure atomicity, cancellation, queue restart, and canonical output boundary.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: concurrency and failure injection can invalidate otherwise passing unit mocks.

**Specification Coverage:** queued/running/cancelling/cancelled/failed/succeeded lifecycle, global total-row cap, title/location/date filters, provider failure atomicity, queue replay, restart recovery, bounded events, and output canonicalization.

**Required Skills:** `skill-backend-verification`, `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/queue.py:enqueue_run_with_job_id`, `enqueue_scan_with_job_id`, `_run_inline_job`, RQ retry setup, and status/cancel paths; `src/fitcv_cp/orchestrator.py:RunSubmission`, `OrchestrationAdapter.submit`, `continue_run`; `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `_verify_jobs_input_projection`; `src/fitcv_cp/scan_worker.py:_published_at`, `execute_scan`; existing process-event writers and worker heartbeat patterns.
- Modify: `src/fitcv_cp/queue.py:enqueue_run_with_job_id`, `enqueue_scan_with_job_id`, inline and RQ status/cancel paths; `src/fitcv_cp/orchestrator.py:RunSubmission`, `OrchestrationAdapter.submit`, `continue_run`; `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `_verify_jobs_input_projection`; `src/fitcv_cp/scan_worker.py:execute_scan` and small local helpers only.
- Verify: `tests/test_fitcv_cp/test_queue.py`, `tests/test_fitcv_cp/test_orchestrator.py`, `tests/test_fitcv_cp/test_admin_retry_endpoint.py`, `tests/test_fitcv_cp/test_scan_worker.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`.

**Dependencies:** Task 2 durable state and claim contract; provider behavior remains owned by `src/fitcv/job_sources.py`.

**Authority:**
- Preauthorized local actions: queue/worker edits, deterministic fake provider tests, injected interruption tests, and local queue status checks.
- Stop for: adding a new broker, changing provider contracts, or requiring external credentials for focused tests.

**Steps:**
- [ ] Define the queue grains in code and tests: caller-created `queue_job_id` is one submission/binding; each worker execution try gets a fresh `attempt_id`; RQ `Retry` and the inline retry loop reuse the submission binding, while manual Retry and Continue create a new queue ID.
- [ ] Update `enqueue_run_with_job_id` and `OrchestrationAdapter.submit`/`continue_run` to accept and return the caller-created Run queue ID; use it for inline and RQ enqueue, return the existing job for replay, and never discover the managed Run ID only after enqueue. Keep backward-compatible generation only for non-managed callers.
- [ ] Update `execute_pipeline_run` and `_verify_jobs_input_projection` to enforce `managed_v1` strict snapshot validation and fail closed before `run_pipeline`; rows with no marker retain the existing legacy fallback contract, including historical `run_inputs` rows that only preserve profile relationships and pipeline-runs-only records.
- [ ] Persist and reconcile stable `scan:{scan_id}` binding with existing queue helpers; make repeated enqueue return the existing binding instead of adding work.
- [ ] Make RQ and inline execution report normalized queued, running, finished, failed, cancelled, and missing states through existing queue helpers.
- [ ] Add heartbeat updates around each provider request and reconciliation that fails stale `running` Scans or requeues only queued work with no live queue job.
- [ ] In `execute_scan`, read the claimed snapshot once, use `remaining_rows = total_rows - len(jobs)`, pass `max_jobs=min(remaining_rows, 200)`, preserve company order, filter titles and locations case-insensitively, and apply stored created_at-resolved cutoff to timestamps and date-only values.
- [ ] Emit bounded events for claim, provider start/result, filter counts, cancellation request, canonicalization result, output commit, failure, and terminal state. Do not persist full provider payloads in events.
- [ ] Treat listing, required-detail, timeout, malformed-payload, and invalid canonical payload failures as Scan failure; never commit partial output.
- [ ] On cancellation, stop before the next provider request, write cancelled terminal state, and leave no successful output row.
- [ ] On enqueue exception after Scan persistence, terminalize the existing Scan as failed with stable retryable evidence; on unknown queue state, reconcile by stable ID before retrying. Re-raise worker exceptions only after store terminalization so queue retry and API state remain consistent.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_scan_worker.py`
- [ ] Run a two-worker claim race and injected worker interruption against temporary SQLite.
- Expected: one claim winner, one Scan queue job, one queue job per Run submission, distinct worker attempts under automatic retry, correct global cap, deterministic order, bounded events, no partial output, and no Scan stuck in `running` after recovery.

**Exit Criteria:** worker and queue tests prove all important success, cancellation, provider failure, replay, and stale-worker paths at the SQLite boundary.

#### Task 4: Reconcile Scan API And Centralize Managed Run Source Resolution

**Purpose:** make API contracts match the approved managed Scan and additive Run behavior, including source validation, idempotency, stale selection handling, and crash-consistent provenance.

**Task Function:** replace competing Run input branches with one resolver while preserving legacy non-managed paths only where current compatibility requires them.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: large route surface, multipart parsing, idempotency, Candidate Profile gating, Scan lifecycle races, and downstream contract impact.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: direct HTTP and persistence proof must detect transport drift hidden by mocks.

**Specification Coverage:** tracked-company routes, Scan creation transport, lifecycle actions, Run source combinations, missing source, unavailable profile, stale Scan, idempotency conflict, queue failure, and canonical Run snapshot.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`, `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py` tracked-company routes, `post_scan`, Scan action routes, `trigger_run`, `_load_jobs_input_manifest`, `_project_jobs_input_sources`, `_execute_trigger_with_inputs`; `src/fitcv_cp/sqlite_store.py:create_run_bundle`.
- Modify: `src/fitcv_cp/app.py` route handlers and local source-resolution helpers; use existing `src/fitcv/job_sources.py` only for provider boundary and keep direct scanner compatibility isolated from managed V1.
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_worker_job.py`.

**Dependencies:** Tasks 1-3; store resolver contract and queue submission order must be fixed before route changes.

**Authority:**
- Preauthorized local actions: route, request-model, multipart resolver, and API regression edits; local TestClient and temporary filesystem checks.
- Stop for: changing public error codes without spec reconciliation, removing a legacy compatibility path without migration evidence, or external provider writes.

**Steps:**
- [ ] Add stable field-level validation for missing Candidate Profile, missing both job sources, empty upload, malformed upload, unavailable Scan, archived Scan, empty Scan, integrity failure, duplicate Scan IDs, and stale Scan revision.
- [ ] Make `/tracked-companies/actions/verify` side-effect free and make `/tracked-companies` revalidate provider, URL, duplicate, and active registry rules before insertion.
- [ ] Keep `/scans` idempotency reservation and create transaction coupled to immutable company snapshots; report enqueue failure without claiming success.
- [ ] Introduce one managed Run source resolver used by multipart `trigger_run`: parse upload bytes once, normalize ordered unique Scan IDs, load all Scan outputs in one transaction, reject unusable selections, and merge upload first followed by Scan order.
- [ ] Serialize one deterministic manifest with source type, ordinal, filename or Scan ID, digest, byte length, record count, and copied snapshot relationship; persist `jobs_input_source` as the managed mode rather than provider-specific scanner metadata.
- [ ] Allocate one Run `queue_job_id` before bundle persistence, pass the same ID through `create_run_bundle` and `OrchestrationAdapter.submit`, queue only after DB commit, preserve the committed snapshot on enqueue failure, expose retry/reconciliation without creating another bundle, and treat response loss after enqueue as idempotent replay.
- [ ] Keep direct JSON scanner acquisition outside managed V1 and mark its compatibility tests explicitly so it cannot become a second managed source path.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_app.py -k "scan or run or tracked_company"`
- [ ] Add TestClient multipart cases for upload-only, Scan-only, multi-Scan, combined, missing source, stale selection, duplicate ID, profile failure, persistence failure, and idempotency replay/conflict.
- Expected: exact requests return stable envelopes; successful bundles contain one canonical snapshot and ordered provenance; pre-commit failures leave no DB rows or unreferenced files, while post-commit enqueue failures leave one inspectable retryable Run.

**Exit Criteria:** API tests prove every managed source combination and no route constructs a competing Scan or job-data schema.

#### Task 5: Restore Prototype Parity In Scan And Run Templates

**Purpose:** expose backend truth consistently in the Scans workspace, Scan Details, Run picker, Run Details, Run input tab, and process console, including the explicit Run status, stage, outcome, and artifact projections consumed by those templates.

**Task Function:** implement stateful server-backed UI behavior with existing templates, shared async helpers, native controls, and project design tokens.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded template and client-state work using existing components and helper patterns.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: verify visible states, keyboard behavior, viewport layout, and request payload without redesigning unrelated pages.

**Specification Coverage:** prototype parity, responsive/mobile behavior, keyboard/focus, Scan Details views, Run picker eligibility, stale selection, console polling, and Run Details provenance.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`, `ui-ux-pro-max`

**Files And Symbols:**
- Inspect and modify: `docs/fitcv-settings-ui-prototype.html` Scan dialog limit, publication-window copy, and validation; update `docs/fitcv-settings-ui-prototype.integration.md` Scan ledger disposition, confirmed drift, affected tests, and post-edit blob/hash record.
- Inspect and modify: `src/fitcv_cp/templates/scans_list.html` Scan workspace, New Scan dialog, tracked-company picker, and action scripts.
- Inspect and modify: `src/fitcv_cp/templates/scan_detail.html` Overview, input, output views, action state, and polling.
- Inspect and modify: `src/fitcv_cp/templates/runs_list.html` Trigger Run form and eligible Scan picker.
- Inspect and modify: `src/fitcv_cp/templates/run_detail.html`, `src/fitcv_cp/templates/run_detail_tab_enriched.html`, `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`, `src/fitcv_cp/templates/_jobs_input_sources.html`, and `src/fitcv_cp/templates/_process_console.html` for six-card projection, one manifest, and cursor console contract.
- Inspect and modify: `src/fitcv_cp/run_lifecycle.py:run_display_status` and capability projection; `src/fitcv_cp/run_artifact_contracts.py` manifest validation; `src/fitcv_cp/run_artifact_mirror.py` warning/integrity projection; `src/fitcv_cp/app_run_support.py` server-side stage/outcome projections.
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_pipeline_prototype.py`, browser flow and accessibility checks.

**Dependencies:** Task 4 response shapes and capability contract; no template hard-codes eligibility or backend limits.

**Authority:**
- Preauthorized local actions: prototype/ledger reconciliation, template and inline script edits, named server-projection edits, existing style/component reuse, browser checks at defined viewports.
- Stop for: new dependency, unrelated design-system change, or visual redesign outside prototype parity.

**Steps:**
- [ ] Render Active/Archived counts, state badges, empty states, selection controls, pagination, and action buttons from server resources and capabilities.
- [ ] Compare the current prototype file with ledger owner blob `989af611bd7767c148022c79ac00c5069d8a3956` and record any baseline mismatch before editing; do not silently replace the approved owner hash.
- [ ] Update the prototype Scan control from `max="1000"` to `max="200"`, change copy to state that the rolling window is resolved when the Scan is created, and update prototype validation from `rows <= 1000` to `rows <= 200`; record these as confirmed drift and reconcile the ledger blob/hash/disposition after the edit.
- [ ] Update New Scan validation and copy to show optional name, required company selection, title/location parsing, six publication options, total rows up to `200`, creation-time cutoff semantics, loading, retryable error, and focus restoration.
- [ ] Implement tracked-company search, server pagination, Select all filtered, clear/apply, Add Company verify then create, and stale result handling for more than 50 companies.
- [ ] Implement Scan Details polling with resource revision and event cursor; stop on terminal state; show pending, failed, cancelled, integrity-invalid, empty-success, and non-empty success distinctly.
- [ ] Keep Table and JSON sourced from same `/scans/{scan_id}/output` bytes and paged `/jobs` array; enable Download JSON for `[]` but never show Run eligibility for empty or invalid output.
- [ ] Implement Run picker search, pagination, filtered Select all, stale selection removal that preserves upload, and server error rendering for `scan_not_usable`.
- [ ] Freeze preserved Run display behavior: backend `RunStatus.CANCELLED` remains exact backend truth and drives capabilities, while visible prototype status remains `Failed` with `statusDetail='Cancelled by user'`; queued, running, awaiting Continue, and cancelling remain visibly `Running` where the current projection already collapses them.
- [ ] Render Run Details from server projections: keep six persisted display stages, map Normalize into Enrichment explicitly, and source counts/outcomes/actions from stable backend facts and capabilities rather than frontend taxonomy.
- [ ] Render ordered upload and Scan manifest rows in Run Details with digest, count, ordinal, copied snapshot status, and canonical links; remove direct provider/company/URL fields from managed trigger UI.
- [ ] Reuse `_process_console.html` cursor semantics, `aria-live`, keyboard focus, reduced-motion-safe transitions, and responsive layout at 390px and 1280px.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_pipeline_prototype.py`
- [ ] Browser assertions at 390px and 1280px cover Scan creation, detail polling, output views, eligible picker, stale selection, and Run Details.
- [ ] `Get-FileHash -Algorithm MD5 docs/fitcv-settings-ui-prototype.html`
- Expected: prototype interaction states, visible labels, request payloads, focus behavior, responsive layout, ledger disposition, and the post-edit blob hash match the approved Scan and Run contract without hard-coded eligibility.

**Exit Criteria:** frontend tests and browser evidence show parity and all user-visible states are driven by API capabilities and stable error envelopes.

#### Task 6: Add Regression Proof Across Store, Worker, API, And Pipeline

**Purpose:** turn every required gap into focused automated evidence before live verification; this task adds or updates tests only.

**Task Function:** extend existing suites rather than create parallel test ownership; add only the smallest fixtures and helpers required for direct boundary proof.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: broad cross-layer matrix with existing large suites and pipeline snapshot integrity risk.

**Validator Profile:**
- Controller-selected: `xhigh`
- Selection basis: independent review of coverage classification and missing live-like boundaries.

**Specification Coverage:** all required Scan-first checks, all Run source modes, historical integrity, failures and recovery, SSOT audit, and actual downstream pipeline execution.

**Required Skills:** `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_scan_worker.py`, `tests/test_fitcv_cp/test_queue.py`, `tests/test_fitcv_cp/test_orchestrator.py`, `tests/test_fitcv_cp/test_admin_retry_endpoint.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_job_sources.py`, `tests/test_fitcv_pipeline_prototype.py`, `tests/test_pipeline.py`, `tests/test_pipeline_store.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_pipeline_outcome_fact.py`, and `tests/test_pipeline_status_registry.py`.
- Inspect only: `src/fitcv_cp/worker_job.py:_verify_jobs_input_projection`, `execute_pipeline_run`; `src/fitcv_cp/run_lifecycle.py:decide_terminal_run`, capability projection; `src/fitcv_cp/run_artifact_contracts.py` manifest validation; `src/fitcv_cp/run_artifact_mirror.py` warning/integrity reporting; `src/fitcv_cp/app_run_support.py` server projections.
- Inspect: `src/fitcv/ingest.py`, `src/fitcv/job_sources.py`, `src/fitcv/pipeline.py`, `src/fitcv/pipeline_contracts.py`, `tests/test_fitcv_cp/test_sqlite_store.py` v4 migration fixtures, and existing Candidate Profile fixtures; do not duplicate canonical contracts or change runtime stage order.

**Dependencies:** Tasks 1-5; tests must target final contract names and response fields.

**Authority:**
- Preauthorized local actions: test additions, deterministic fixtures, temporary SQLite/filesystem state, local TestClient, and pipeline stubs only where direct real dependency is unavailable.
- Stop for: any production-code edit, tests that require private credentials, destructive external data, or a new test framework. If verification exposes an implementation defect, mark Task 6 blocked, reconcile this plan, route the fix to Task 2, 3, 4, or 5 by owning symbol, then rerun Task 6.

**Steps:**
- [ ] Classify existing coverage in test names or test notes as proven, partially covered, mock-only, missing, or contradicted; replace contradicted expectations rather than preserve stale limits.
- [ ] Add direct output byte and manifest assertions, provider failure atomicity, cancellation, queue replay, stale worker, and referenced-delete tests.
- [ ] Add all six Run source combinations with exact multipart payload, DB rows, manifest order, path bytes, and provenance checks.
- [ ] Add `_verify_jobs_input_projection` regression checks for Scan manifest digest/count/ordinal and the versioned boundary: `run_input_contract_version='managed_v1'` requires full validation and fails closed; missing/legacy marker preserves historical `run_inputs` rows containing only profile relationships and pipeline-runs-only records; never infer managed mode from `run_inputs` row existence.
- [ ] Re-run the existing v4 `run-legacy` migration case and worker-compatibility proof to show nullable historical snapshot fields remain readable and executable under the legacy contract.
- [ ] Add queue-grain assertions: automatic RQ/inline retries share one submission queue ID while each worker try has a distinct `attempt_id`; admin Retry and Continue allocate new queue IDs. Reuse `tests/test_fitcv_cp/test_admin_retry_endpoint.py` for max-attempt and enqueue behavior.
- [ ] Add representative pipeline execution assertions for runtime Normalize, Enrich, Rule Filter, Shortlist, Ranking, optional CV stages, counts, and terminal Run status while asserting the existing six-row control-plane projection.
- [ ] Add paired Scan-download-versus-upload equivalence test with same Candidate Profile and settings.
- [ ] Verify artifact policy: checksum/schema/count failures disable only affected artifact actions and emit warnings; missing diagnostic or mirror artifacts do not invent a new Run failure state.
- [ ] Keep `test_fitcv_pipeline_prototype.py` focused on prototype contract and `test_job_sources.py` focused on provider/canonical boundary; no duplicate business logic in tests.
- [ ] Keep this task regression-only. If a newly exposed defect requires source changes, stop and route the smallest source patch to its owning task before continuing.

**Verification:**
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_queue.py tests/test_job_sources.py`
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_pipeline_prototype.py`
- [ ] `py -m pytest -q tests/test_fitcv_cp/test_orchestrator.py tests/test_fitcv_cp/test_admin_retry_endpoint.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Expected: focused suites pass with direct success/failure/final-state evidence, historical `run-legacy` compatibility, explicit submission/attempt identity, and no test depends on a mock-only Scan output for the canonical-path claim.

**Exit Criteria:** every scenario in the matrix has a named test or is explicitly reserved for the live stop gate, with no unclassified required behavior.

#### Task 7: Run Live Stop-Gate Verification And Reconcile Scope

**Purpose:** prove the complete path against active successful Candidate Profiles, local fixtures, real Scan output, and the real Job Pipeline.

**Task Function:** execute and record fresh cross-layer evidence after implementation, then reconcile plan status and unplanned changes.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: final cross-layer proof, real provider/pipeline dependency, browser evidence, and integrity comparison.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: independent acceptance decision against explicit stop gate and Git diff.

**Specification Coverage:** live successful Scan, Run ingestion, actual pipeline execution, upload-vs-Scan equivalence, recovery, and final prototype parity.

**Required Skills:** `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all target files plus `docs/fitcv-settings-ui-prototype.html`, `src/fitcv/ingest.py`, `src/fitcv/job_sources.py`, `src/fitcv/pipeline.py`.
- Modify: none unless fresh evidence identifies a required defect; any corrective edit returns to its owning task and reruns dependent proof.
- Verify: browser flow, API logs, SQLite final state, queue/worker events, Run Details, and Git diff/status.

**Dependencies:** Tasks 1-6 pass; active Candidate Profile exists; local provider and pipeline runtime are configured; `data/sample_jobs_1.json` and `data/sample_jobs_2.json` are revalidated as preflight local evidence, not treated as tracked baseline.

**Authority:**
- Preauthorized local actions: create temporary local Scan/Run data, run local provider/pipeline checks, capture browser/network evidence, and remove only temporary artifacts created by the verification run.
- Stop for: missing runtime dependency, unavailable provider credentials, external write, destructive cleanup, or mismatch between plan and working tree.

**Steps:**
- [x] Verify `data/sample_jobs_1.json` and `data/sample_jobs_2.json` against canonical input before exercising Run modes.
- [x] Create real Active, Succeeded Scans from tracked companies; record request, lifecycle events, stored cutoff resolved from `created_at`, output bytes, digest, count, and details views.
- [x] Trigger Scan-only, upload-only, and combined Runs with an Active, Succeeded Candidate Profile; record exact multipart request, persisted manifest, copied path, worker integrity check, and pipeline stage events.
- [x] Archive the source Scan after Run creation, block referenced delete, mutate registry data, and replay the Run worker; copied input and results remain unchanged.
- [x] Download Scan JSON and run equivalent upload flow; canonical bytes, count, order, stage counts, and terminal output match while provenance labels differ.
- [x] Repeat recoverable queue/API failure and duplicate button press; initial Scan enqueue failure terminalized safely, retry succeeded after regression fix, and idempotent replay returned the original Run ID without duplication.
- [x] Run final validators and inspect `git status --short`; preserve the four user-owned sample-file changes and report no unrelated file.

**Verification:**
- [x] `py -m pytest -q tests/test_validate_template_required_sections.py tests/test_validate_repo_contracts.py` — 25 passed.
- [x] `py scripts/validate_template_required_sections.py --repo-root .` — passed.
- [x] `git diff --check` — passed.
- [x] Record live browser/API/SQLite/worker evidence and acceptance decision `PASS`, `FAIL`, or `BLOCKED` — DeepAgents validator returned `PASS`; lead verification returned `verified`.
- Expected: one fresh successful `Scan -> Run -> real Job Pipeline` trace exists; all required contract, recovery, integrity, and capability gates pass; artifact warnings do not override the existing terminal lifecycle; no unplanned code or data-file changes occur.

**Exit Criteria:** `skill-verification-before-completion` returns `verified`, every task is reconciled against Git and this plan, and plan status changes only through the approved execution workflow.

## Run Pipeline

This section extends existing Scan-first plan. Candidate Profile lifecycle, canonical Scan output, and uploaded canonical job inputs are upstream fixtures. Every Run boundary that consumes them still requires proof. This section is a patch plan only.

### 1. Executive Findings

**P0 — runtime and display have different stage shapes.** `src/fitcv/pipeline_contracts.py:PIPELINE_STAGE_SEQUENCE` has seven runtime stages: `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, `cv_generation`. `src/fitcv_cp/run_lifecycle.py:PROTOTYPE_STAGES` has six display stages and maps Normalize into Enrichment. SQLite stage tables currently constrain IDs to six display stages. Normalize counts and artifacts can disappear from Run Details. **Decision:** runtime seven-stage sequence stays sole execution order; the existing six-card control-plane/UI schema remains persisted SSOT, with Normalize explicitly projected into Enrichment. Runtime-stage facts and artifacts remain inspection evidence; no seven-row control-plane migration is planned.

**P0 — managed Run can fall back to mutable configuration.** `src/fitcv_cp/worker_job.py:execute_pipeline_run` parses `effective_settings_json` and existing compatibility behavior can fall back to `config_path`. `test_worker_falls_back_to_config_path_if_no_snapshot` proves that fallback. Managed Runs need strict snapshot mode. Missing, invalid, or checksum-mismatched profile/settings snapshots must fail before `run_pipeline`; fallback remains legacy-only.

**P0 — artifact availability is not a second lifecycle owner.** Worker persistence calls for progress, results export, CV debug, stage artifacts, settings-used, and terminal mirror catch errors and log warnings. Preserve existing Run terminal decisions and record missing artifacts as integrity warnings. Results, stage, and CV artifacts are required only to enable their own download/action; settings-used, CV debug, and terminal mirror remain warning-only diagnostics. No artifact persistence failure changes `succeeded` to `failed` unless the existing lifecycle contract already requires the affected native state.

**Managed/legacy snapshot boundary:** classify a Run as managed only when `run_inputs.run_input_contract_version='managed_v1'`. That marker is written only for newly created managed snapshots after jobs snapshot, manifest, byte length, SHA-256, record count, Candidate Profile snapshot/checksum/revision, settings snapshot, and settings revision all validate. A marked row with any missing or invalid field fails closed before `run_pipeline`. A missing or legacy marker preserves the existing legacy compatibility contract, including historical `run_inputs` rows that only retain profile relationship fields and pipeline-runs-only records; `config_path` fallback remains legacy-only. Never backfill the marker into an incomplete historical row and never infer managed mode from `run_inputs` row existence.

**Artifact lifecycle policy:** snapshot persistence and native outcome facts remain lifecycle-critical. Artifact routes own artifact availability: missing results/stage/CV artifacts disable only affected downloads/actions; settings-used, CV debug, and terminal mirror failures emit bounded warnings. Artifact integrity must be tested, but it does not gate Run success in this plan.

**P1 — counts and rows have several projection owners.** `sqlite_store:get_run_detail`, `_filtered_run_job_rows`, `_results_export_rows`, `app_run_support.py`, `run_artifact_mirror.py`, and templates can independently shape Passed/Rejected, stage summaries, CV state, exports, and links. `get_run_detail` compares stored totals against Screening while UI has six display stages. Native outcome facts and stable `run_job_id` must own all projections.

**P1 — lifecycle labels hide backend states.** Preserve the existing deliberate projection: backend `RunStatus.CANCELLED` remains exact backend truth and drives capabilities, while the visible prototype status is `Failed` with `statusDetail='Cancelled by user'`; queued, running, awaiting Continue, and cancelling remain visibly `Running`. Treat this mapping as fixed behavior, not an open copy decision.

**P1 — retry, Continue, cancellation, and reconciliation use separate paths.** `admin_continue_run`, `admin_retry_run`, `request_run_cancel`, `execute_pipeline_run`, checkpoint persistence, lease renewal, and reconciler behavior need one attempt contract. Same Run ID may be reused for retry, but attempts and artifacts must remain distinguishable.

**P2 — frontend proof is mostly structural or mock-backed.** Existing tests cover route rendering, async helpers, worker branches, stage contracts, and artifact payload shapes. No fresh proof shows Run Details rows, counts, downloaded artifacts, CV links, and events equal persisted output from real upload-only, Scan-only, and combined Runs.

**P2 — prototype terminology differs from runtime terminology.** Prototype uses Enrichment, Screening, Shortlisting, Ranking, CV Analysis, and CV Generation. Runtime also has Normalize, Rule Filter, and Shortlist. No second pipeline sequence is allowed. `runtime-stage IDs` are the seven IDs owned by `src/fitcv/pipeline_contracts.py` and used by execution, runtime artifacts, and native runtime facts. `control-plane stage IDs` are the six IDs owned by `src/fitcv_cp/run_lifecycle.py` and used by normalized persistence and `/runs/{run_id}/stages`. One explicit alias/projection bridge maps runtime facts to control-plane stages; neither set is universally canonical.

### 2. Actual Run Data Flow

| Boundary | Current owner and behavior | Required patch and proof |
| --- | --- | --- |
| Trigger UI | `src/fitcv_cp/templates/runs_list.html` loads succeeded active Candidate Profiles and eligible Scans, retains upload plus Scan selection, posts multipart `/runs`. | Verify prototype fields, source combinations, disabled state, stale selection, focus, mobile layout, and duplicate-submit lock with browser network evidence. |
| Request | `src/fitcv_cp/app.py:trigger_run` accepts JSON compatibility and multipart. Multipart parses file, ordered `scan_ids`, profile, settings, and mode. | One managed source resolver for upload-only, Scan-only, multi-Scan, and combined; direct scanner compatibility cannot own managed source construction. |
| Canonicalization | `app.py:_execute_trigger`, `_execute_trigger_with_inputs`, and `fitcv.ingest:canonicalize_jobs` create `jobs_input_json`. | Store exact canonical bytes, digest, count, media type, and manifest; reject empty or malformed input before persistence. |
| Profile snapshot | `_execute_trigger_with_inputs` stores profile JSON, ID, revision, schema, and checksum in `run_inputs`. | Require active succeeded profile; validate snapshot at worker startup; pipeline never reloads current profile for managed Run. |
| Settings snapshot | Trigger builds effective settings and stores settings snapshots; worker parses effective settings. | Store schema, revision, checksum, and routing facts; strict managed mode fails on missing or invalid snapshot. |
| Run persistence | `sqlite_store:create_run_bundle` writes `pipeline_runs`, `run_inputs`, `run_jobs`, `run_scan_inputs`, and stage rows. | Commit DB truth with deterministic path and queue ID; finalize or reconstruct projection from DB SSOT; enqueue after DB commit; reconcile missing-file, not-enqueued, enqueue-unknown, and response-lost states. |
| Queue | `queue.py:enqueue_run_with_job_id`, `enqueue_run`, `update_run_queue_job_id`, and orchestration binding helpers connect Run to worker. | One caller-created queue binding per submission, durable IDs, replay-safe response failure, automatic retries sharing that submission, and stale attempt reconciliation without duplicate execution. |
| Worker startup | `worker_job:execute_pipeline_run` loads Run, retry settings, lease, snapshots, and checkpoint. | Validate Run, path, bytes, manifest, profile, settings, routing, attempt, and checkpoint before calling pipeline. |
| Integrity | `_verify_jobs_input_projection` checks path, canonical digest, and exact projected bytes. | Add byte length, record count, canonical shape, source manifest, profile/settings checksums, and classify managed by `run_input_contract_version='managed_v1'`; fail closed for invalid marked snapshots and preserve `config_path` fallback for unmarked historical/legacy rows only. |
| Pipeline | `src/fitcv/pipeline.py:run_pipeline` uses `PIPELINE_STAGE_SEQUENCE`, callbacks, checkpoint, reuse snapshots, and cancellation. | Verify prior-stage input, stable identity, outcome facts, artifacts, checkpoint boundaries, and no mutable settings reads. |
| Persistence | `worker_job` snapshot helpers and `sqlite_store:persist_pipeline_snapshot` write stage rows, job results, summary JSON, and artifact fields. | Make writes idempotent by Run/attempt/stage; block terminal success until required evidence is persisted; reconcile counts from facts. |
| Terminal state | `run_lifecycle:decide_terminal_run` and worker terminal branches choose Succeeded, Failed, Cancelled, or Awaiting Continue. | Preserve existing native terminal decision inputs: unresolved jobs, partial stages, cancellation, and checkpoint state. Artifact availability remains separate capability/warning state. |
| Artifacts | `run_artifact_mirror:build_terminal_run_artifact_payloads` and `persist_terminal_run_artifact_mirror` create terminal files. | Persist deterministic manifest/checksums and compare mirror bytes with DB payloads. |
| Run Details | `app.py:get_run_detail`, `get_run_stages`, `get_run_jobs`, event/download routes, and Run templates render projections. | Visible state must equal API, SQLite, and artifact truth after reload; templates do not classify outcomes. |
| User actions | Cancel, archive, unarchive, retry, Continue, bookmark, interest, CV regenerate/review, export, stage downloads, and bundles route through app/store. | Stable IDs, revisions, attempts, versions, idempotency, and historical snapshot preservation for every mutation. |

### 3. Prototype-to-Frontend Matrix

| Prototype | Runtime frontend | Status | Evidence | Required patch |
| --- | --- | --- | --- | --- |
| Runs workspace tabs, counts, table, status badges, selection, pagination, Trigger Run | `runs_list.html`, `app.py:get_runs_list`, `admin_runs` | Partial | Existing prototype and route tests; no browser comparison with persisted status/counts. | Derive rows, counts, capabilities, and labels from store projection; add active/archived/empty/error/retry browser proof. |
| Trigger dialog supports upload, Scan, multiple Scan, combined, profile, name, disabled Trigger | `runs_list.html`, `trigger_run`, `_execute_trigger_with_inputs` | Partial | Additive source tests exist; direct scanner path remains parallel. | One managed resolver; eligible profile/Scan only; preserve upload on stale picker response; require profile plus one source. |
| Status labels and actions are state-specific | `run_lifecycle.py` and templates | Preserved mapping | Backend `CANCELLED` remains exact; visible cancelled Run status is `Failed` with `Cancelled by user`, while queued/running/awaiting Continue/cancelling display `Running`. | Freeze current projection, expose exact capabilities, and test the intentional collapsed labels. |
| Run Details Overview and actions | `run_detail.html`, `admin_run_detail`, `get_run_detail` | Partial | Output availability and route tests. | Render persisted status, timestamps, duration, capability, stale, orphan, partial, and awaiting states after reload. |
| Run Input shows ordered sources, profile revision, settings, and immutable jobs | `run_detail.html`, `run_detail_tab_jobs_input.html`, `_jobs_input_sources.html` | Partial | Source manifest and template tests. | Show full manifest, checksums, ordinals, snapshot state, and copied bytes; links never reread mutable resources. |
| Pipeline Results shows stage tabs, Passed/Rejected, counts, rows, filters, search, pagination | `run_detail.html`, `run_detail_tab_enriched.html`, `get_run_stages`, `get_run_jobs` | High-risk drift | Six display stages query seven runtime stages; no live DB-to-HTML proof. | Use canonical stage/outcome projection, explicit Normalize mapping, stable IDs, reason facts, and count integrity warning. |
| Console shows canonical events, clear-local behavior, polling, and downloads | `_process_console.html`, event routes | Partial | Template renders persisted events; polling and event parity unproven. | Add cursor polling, terminal stop, stage/failure/cancel/Continue events, bounded payload checks, and local Clear View semantics. |
| Passed/Rejected is backend truth | `run_lifecycle.py`, `pipeline_contracts.py`, `app_run_support.py`, templates | High-risk drift | Outcome unit tests exist; complete DB-to-HTML comparison missing. | Render `job_outcome_surface` projection; remove frontend classification and duplicated reason maps. |
| CV states, versions, downloads, review, regenerate | CV routes, `sqlite_store:_cv_projection`, `app_run_support.py`, `run_detail.html` | Partial | CV worker and route tests. | Tie version and action to Run job, attempt, profile/settings checksum; preserve prior version on failure. |
| Stage downloads, exports, debug bundle | app download routes and `run_artifact_mirror.py` | Partial | Artifact contract/mirror tests. | Add manifest/checksum/attempt validation and byte comparison against persisted payloads. |
| Responsive, keyboard, focus, loading, retry, stale, reduced motion | Run templates and shared helpers | Missing live proof | Static and shared async tests. | Browser checks at 390px/1280px with keyboard, focus, aria-live, stale, duplicate click, and reduced motion. |

### 4. Frontend-to-Backend Matrix

| UI action | Route | Request | Response | Persistence | Current gap | Patch |
| --- | --- | --- | --- | --- | --- | --- |
| Runs list | `GET /runs`, `/admin/runs` | view, search, page, page size | rows, counts, pagination, capabilities | `pipeline_runs` and projections | Status and count source need live proof. | One server projection for status, duration, counts, and actions. |
| Candidate Profile picker | `GET /candidate-profiles?view=active&status=succeeded` | page/search | eligible profile resources | profile lifecycle | First-page-only discovery risk. | Search/paginate or document bounded contract; reject unavailable submit. |
| Scan picker | `GET /scans?lifecycle=active&usable_for_run=true` | search/page | usable Scan resources | Scan integrity | Stale selection between load and submit. | Revalidate every ID in bundle transaction; return `scan_not_usable`. |
| Trigger Run | `POST /runs` multipart | file, ordered `scan_ids`, `profile_id`, name, settings, mode, idempotency | `201` Run or stable error | all Run/input/job/stage rows | Multiple branches and persistence/enqueue order. | One managed resolver, crash-consistent DB/filesystem/queue protocol, enqueue after DB commit, cleanup/reconciliation on failure. |
| Run detail | `GET /runs/{run_id}`, `/admin/runs/{run_id}` | Run ID | snapshots, status, stages, capabilities, warnings | store rows and JSON | Reconciliation can reconstruct without visible provenance. | Preserve raw values, explicit projection revision, integrity warnings. |
| Stage summaries | `GET /runs/{run_id}/stages` | Run ID | six persisted display stages plus runtime-stage mapping metadata | existing six-row control-plane facts and runtime evidence | Runtime Normalize must remain visible through Enrichment. | Return six control-plane stages with explicit Normalize/Enrich projection metadata; do not migrate stage rows to seven IDs. |
| Run jobs/results | `GET /runs/{run_id}/jobs`, admin stage tab | stage, result bucket, search, page | rows, counts, outcome facts, CV metadata | run jobs, stage results, CV rows | Current CV availability affects bucket; conservation unproven. | Include source identity, outcome, reason, evidence, artifact, attempt, revision. |
| Events | `GET /runs/{run_id}/events` | cursor, limit | event page and next cursor | process events | Polling/terminal stop unproven. | Cursor polling, schema validation, stable order, local clear only. |
| Cancel | `/runs/{run_id}/actions/cancel`, admin routes | expected revision/idempotency | updated status | cancel request/events | Worker observation and final evidence need proof. | CAS, queue cancel, cooperative stop, retained partial evidence. |
| Continue | `/admin/runs/{run_id}/continue` | revision/idempotency | queued/running attempt | checkpoint and attempt | Rerun boundary risk. | Require awaiting state, next-stage exactness, idempotent action, stable artifacts. |
| Retry | `/admin/runs/{run_id}/retry` | Run ID/idempotency | queued attempt | same snapshots, new attempt | Attempt/artifact separation needs proof. | Max attempts, same input/profile/settings checksums, accepted-attempt projection. |
| Lifecycle actions | archive/unarchive/delete routes | expected revision/preview/idempotency | resource/result | lifecycle rows | Active/reference guards need matrix. | Central capability and CAS; preserve historical evidence. |
| Job actions | bookmark, interest, export, CV review/regenerate routes | stable Run job/version IDs and action keys | updated projection or artifact | bookmark/interest/CV/export rows | Reload/stale semantics partial. | Stable IDs, revision checks, idempotent mutations, no pipeline truth mutation. |
| Downloads | results, stage artifacts, CV, debug, bundle routes | Run/stage/version | exact bytes and headers | DB/blob/mirror | Availability inferred from status. | Validate manifest/checksum; disable only affected action when unavailable; compare bytes without making artifact persistence a new terminal gate. |

### 5. Pipeline Stage Contract Matrix

| Input | Transformation | Output | Persistence | Counts | Failure semantics | Artifact | UI projection | Existing tests | Missing proof |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `normalize`: immutable `run_inputs.jobs_snapshot_json` and `run_jobs.source_snapshot_json` | `pipeline.py:run_pipeline` loads raw jobs, `normalize_batch` or `normalize_batch_with_exclusions`, applies identity, dates, descriptions, URLs, duplicate and invalid-row rules | normalized jobs plus explicit pre-enrichment exclusions and input-index identity | pipeline state, progress callback, `run_jobs`, stage facts via `persist_pipeline_snapshot` | input total equals normalized plus explicit rejected/skipped/deduplicated outcomes | setup/canonicalization failure fails Run; row failure retains reason fact | `normalize.json` | runtime Normalize mapped into prototype Enrichment card with explicit substage | checkpoint/resume and worker snapshot tests | byte artifact, conservation, URL/date/duplicate fixture, UI mapping |
| `enrich`: normalized eligible rows | `enrich_batch`, cache/reuse contract, profile/config/provider/prompt routing; structured fields, skills, seniority, domain, family, location | enriched rows, reuse metadata, per-job failure facts | structured-job store, stage artifact, job stage results | eligible Normalize rows equal fresh/reused/failed outcomes | setup/provider failure policy explicit; per-job failures retain identity; required routing failure fails stage | `enrich.json` | Enrichment display includes Normalize substage | settings/reuse tests | real snapshot routing, fresh/reuse proof, frontend counts |
| `rule_filter`: enriched rows plus frozen Run settings | `apply_pre_enrichment_global_filters` and `apply_rule_filters`; no frontend rule evaluation | passed and rejected rows with reason codes/facts | `PipelineStore.store_filter_results`, stage facts, artifact | passed + rejected equals input under documented deduplication | persistence failure fails required stage; row rejection retains reason | `rule_filter.json` | Screening label | pipeline/outcome tests | count equation, reason persistence, no frontend filtering |
| `shortlist`: Screening-passed rows, frozen profile, embedding/vector config | embed jobs/candidate, vector shortlist, audit, diagnostics, shortlist limits | selected shortlist rows, non-selected explicit outcomes, query diagnostics | vector store, `PipelineStore.store_shortlist`, stage facts | Screening-passed equals shortlisted plus not-selected outcomes | vector failure follows required policy; zero-hit guard visible | `shortlist.json` | Shortlisting label | resume/shortlist tests | stable identity, duplicate URL, vector failure, UI parity |
| `ranking`: shortlist rows and frozen preference/config policy | ranking features, AI scoring where enabled, final top-N ordering | ranked rows plus not-scored/not-ranked outcomes | `PipelineStore.store_final_ranking`, ranking facts, artifact | shortlist input equals ranked plus explicit exclusions | scorer failure follows policy; no rank without identity | `ranking.json` | Ranking label and rank/score rows | ranking/outcome tests | tie/missing score, preference snapshot, persisted rank equality |
| `cv_analysis`: ranked jobs, frozen profile/settings, analysis runtime | evidence retrieval, gap analysis, fit classification, requirement coverage, fit gate | one analysis outcome per ranked job: ready, blocked, skipped, failed, or canonical equivalent | analysis facts, trace, stage artifact, Run job projection | ranked input equals every explicit analysis outcome | per-job failure isolated; setup/routing failure fails required stage | `cv_analysis.json`, `cv-analysis-trace.json` | CV Analysis label and reason/evidence rows | status registry and worker tests | real snapshot identity, no ranked job loss, trace parity |
| `cv_generation`: analysis-eligible rows, frozen profile/settings, generation policy | generate, validate, persist version, review state, retry/reuse | generated, review-required, validation-failed, generation-failed, persistence-failed, cancelled outcomes | `cv_versions`, stage facts, debug/trace, terminal bundle | eligible analysis rows equal one generation outcome each | partial per-job outcomes only under explicit policy; native CV version/outcome persistence follows the existing terminal contract; diagnostic artifact failure warns only | `cv_generation.json`, `cv-debug.json`, review-required and trace artifacts | CV Generation label, versions, download, review, regenerate | CV worker/artifact tests | live generated/review/failure, version/checksum/link integrity |

`src/fitcv/pipeline_contracts.py` owns runtime IDs, order, labels, and artifact names. `src/fitcv_cp/run_lifecycle.py:PROTOTYPE_STAGES` owns the six persisted/display grouping. Runtime Normalize and Enrich facts may remain in native runtime evidence and artifacts, but `run_stage_executions` and `run_job_stage_results` keep their existing six display IDs.

### 6. Run Lifecycle Matrix

| Source state | Action/event | Target state | UI display | Capabilities | Persistence | Test |
| --- | --- | --- | --- | --- | --- | --- |
| queued | worker claim | running | Running or prototype equivalent | cancel, inspect | started time, attempt, lease, event | claim/queue test |
| queued | cancel before worker | cancelled | Failed with `Cancelled by user` detail | inspect, archive | cancel request, queue cancel, terminal snapshot | queued cancellation and display projection |
| queued | enqueue failure | failed with retry/reconciliation capability | retryable error | retry by stable queue ID and action key | error/event, retained snapshot, no duplicate attempt | enqueue failure |
| running | stage progress | running | Running with current stage | cancel, inspect | lease, progress, stage snapshot | progress persistence |
| running | runtime stages complete and existing native terminal decision succeeds | succeeded | Succeeded | inspect, archive, export, downloads subject to capability | terminal status and native facts; artifact warnings remain separate | full pipeline |
| running | required failure | failed | Failed with stage/reason | inspect, retry by policy, archive | error, partial evidence, attempt payload | failure injection |
| running | cancel observed | cancelled | Failed with `Cancelled by user` detail | inspect, archive | finish time, cancellation event, retained evidence | mid-stage cancellation and display projection |
| running | manual stage boundary | awaiting_continue | Awaiting Continue | Continue, cancel, inspect | checkpoint, next stage, completed stages | manual staged |
| awaiting_continue | Continue | queued then running | Awaiting then Running | Continue locked after submit | new attempt/event, same snapshots | repeated Continue |
| awaiting_continue | cancel | cancelled | Failed with `Cancelled by user` detail | inspect, archive | terminal checkpoint and evidence | awaiting cancellation and display projection |
| failed | retry allowed | queued then running | Retrying/Running | max attempts enforced | new attempt, same snapshots, old artifacts retained | retry semantics |
| terminal | archive/unarchive | archived/active lifecycle | Archived badge plus backend status | inspect, delete only when eligible | CAS lifecycle update | lifecycle tests |
| any active | stale or duplicate command | unchanged or idempotent replay | stale/retry state | no duplicate execution | action key and revision conflict | duplicate action |

All transitions use `run_lifecycle.py` capabilities and store CAS. Templates do not infer transitions from timestamps or stage labels.

### 7. Job Conservation Matrix

| Input identity | Normalize | Enrich | Screening | Shortlist | Ranking | CV Analysis | CV Generation | Final outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `run_job_id` from Run ID, source index, canonical job JSON | stable ID, source index, fingerprint | same ID, fresh/reused/failed fact | passed/rejected reason | selected or explicit not-selected | ranked or explicit not-ranked/not-scored | ready/blocked/skipped/failed | generated/review/validation/generation/persistence outcome | one native outcome fact with stage, outcome, reason, evidence, trace, artifact, attempt |
| duplicate URL occurrence | first retained by contract | duplicate excluded with identity | explicit deduplication fact | no duplicate row | no duplicate rank | no CV | no version | documented deduplicated outcome |
| invalid required field | Normalize rejection with input index | not entered | not entered | not entered | not entered | not entered | not entered | rejected with Normalize reason |
| Screening rejection | identity retained | identity retained | rejected facts | not eligible | not entered | not entered | not entered | rejected with Rule Filter evidence |
| shortlist non-selection | prior facts retained | prior facts retained | passed fact | explicit not-selected | not entered | not entered | not entered | skipped or rejected per contract |
| ranking non-selection | prior facts retained | prior facts retained | passed fact | selected fact | explicit not-ranked/not-scored | not entered | not entered | skipped or held per contract |
| CV analysis blocked/failed | all prior facts retained | all prior facts retained | all prior facts retained | all prior facts retained | ranked fact | explicit blocked/failed | no generation unless policy allows | blocked or rejected |
| CV review required | all prior facts retained | all prior facts retained | all prior facts retained | all prior facts retained | ranked fact | ready fact | review-required version and review state | held linked to version |
| CV generated | all prior facts retained | all prior facts retained | all prior facts retained | all prior facts retained | ranked fact | ready fact | generated version and checksum | accepted/generated downloadable outcome |

Automated conservation proof asserts every input occurrence has a stage fact or explicit documented deduplication, no fact references unknown `run_job_id`, and every CV version references exactly one Run job.

### 8. Artifact Matrix

| Artifact | Producer | Persistence owner | Availability | Consumer/UI | Download | Validation |
| --- | --- | --- | --- | --- | --- | --- |
| `normalize.json` | Normalize transition builder | worker plus `sqlite_store:update_run_stage_transition_artifacts`, mirror | after Normalize | stage projection/debug | stage artifact route | canonical JSON, identity, count, checksum |
| `enrich.json` | Enrich transition builder | same | after Enrich | Enrichment projection | stage artifact route | fresh/reused status, identity, counts |
| `rule_filter.json` | filter transition builder | same | after Rule Filter | Screening projection | stage artifact route | passed/rejected facts and counts |
| `shortlist.json` | shortlist transition builder | same | after Shortlist | Shortlisting projection | stage artifact route | selection, non-selection, audit, identity |
| `ranking.json` | ranking transition builder | same | after Ranking | Ranking projection | stage artifact route | rank, score, tie/order, identity |
| `cv_analysis.json` | CV analysis builder | same | after CV Analysis | CV Analysis projection | stage route | one outcome per ranked input, evidence/trace |
| `cv_generation.json` | CV generation builder | same | after CV Generation | CV Generation projection | stage route | one outcome per eligible input |
| `results.json` | `worker_job:_build_results_export_payload` | `update_run_results_export`, mirror | terminal | Results and JSON download | `/admin/runs/{run_id}/export.json` | native outcome ledger, checksum |
| `stage-artifacts.json` | stage payload builder | `update_run_stage_transition_artifacts`, mirror | boundary/terminal | debug and stage downloads | stage bundle routes | seven IDs, status, counts, checksum |
| `settings-used.json` | worker snapshot builder | `update_run_settings_used`, mirror | trigger/terminal | Run input/settings | settings route | effective config checksum/revision |
| `cv-debug.json` | `_build_cv_generation_debug_payload` | `update_run_cv_generation_debug`, mirror | CV terminal | CV debug | debug route | version/status/trace/checksum |
| CV content/version | CV runtime | `cv_versions`, `_cv_projection` | generated/review-required with valid content | Run Details/CV download | `/admin/cvs/{version_id}/download` | content checksum/length, version, job, snapshot revisions |
| events | reporter and worker | `process_events`, terminal mirror | event emission | Console/debug bundle | event export/bundle | cursor order, bounded payload, stage identity |
| terminal bundle | `run_artifact_mirror:persist_terminal_run_artifact_mirror` | filesystem mirror | terminal | debug bundle | `/admin/runs/{run_id}/artifacts.zip` | manifest, checksums, Run/attempt identity |

Artifact availability comes from persisted completion and integrity state. A stage label cannot imply that an artifact exists.

### 9. End-to-End Test Matrix

| Scenario | Input | UI assertion | API assertion | DB assertion | Worker assertion | Stage assertions | Artifact assertions | Run Detail assertion | Existing coverage | Missing test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Upload-only full Run | `data/sample_jobs_1.json` | Trigger, progress, stages, terminal detail | exact multipart and `201` | immutable input/profile/settings and stage rows | exact path/bytes/config | all applicable stages and counts | artifacts download and hash | rows/counts/status equal DB | route and worker tests | live full path |
| Second fixture | `data/sample_jobs_2.json` | same flow, distinct count | same contract | digest/count stable | same integrity | conservation on six jobs | artifact parity | correct persisted results | fixture tests partial | live comparison |
| Scan-only full Run | real successful non-empty Scan | eligible picker and provenance | ordered Scan ID only | `run_scan_inputs` digest/count/ordinal and copied bytes | never rereads Scan | same stages as upload | valid Scan-derived artifacts | source/results persist after archive | managed route mock | live proof |
| Upload plus Scan | fixture plus real Scan | upload first, Scan second | multipart order preserved | manifest, source indexes, copied path | worker sees merged snapshot | merged counts/conservation | artifact identities stable | input and results match DB | manifest test partial | live proof |
| Scan JSON uploaded | exact downloaded Scan bytes | only provenance label differs | source metadata differs only | canonical bytes/digest/count equal | same profile/settings snapshot | equivalent stages | compare deterministic artifact facts | equivalent rows/outcomes | missing | paired live equivalence |
| Missing source/profile | no file, no Scan, missing profile | Trigger disabled and field error | stable `validation_failed` | no Run/input rows | worker never starts | none | none | retry preserves form | partial route tests | direct multipart matrix |
| Input corruption | mutate projection, manifest, profile, or settings | error/console state | worker integrity failure | no successful terminal mutation | fails before pipeline | none | failure evidence only | error stage visible | projection unit tests | injected end-to-end drift |
| Queue duplicate/recovery | repeat trigger, response failure, stale attempt | one Run and retry state | one binding per submission; worker attempts remain distinct | no duplicate executable attempt | reconciler safe | no duplicate stage writes | attempts distinguishable | console shows recovery | queue/lease partial | full injected queue proof |
| Stage failure | inject Normalize, Enrich, filter persistence, vector, ranking, CV, artifact, final-status failure | stage error and retry state | terminal state/error envelope | partial facts retained, no false success | correct retryability | prior-stage facts stable | availability matches stage | rows/counts explain failure | unit tests partial | boundary matrix |
| Manual Continue | `manual_staged` Run | Awaiting Continue and exact next action | one Continue request | checkpoint complete | starts next stage only | prior artifacts unchanged | new attempt/event only | status/stage navigation correct | checkpoint tests | browser plus DB |
| Retry/resume | failure at stage boundary | history/current attempt visible | max attempts/idempotency | same snapshots, distinct attempts | reuse only policy-approved outputs | no silent overwrite | accepted artifact references correct attempt | current attempt rendered | retry tests partial | full matrix |
| Cancellation | queued, long stage, awaiting Continue | correct actions and terminal status | CAS cancel response | partial evidence retained | stops at boundary | no unsupported continuation | safe artifacts remain | console/status match | cancellation unit tests | live cancellation |
| CV outcomes | generated, review, validation, generation, persistence failures | versions/download/review state | CV routes stable | one version/outcome per job, prior preserved | immutable input and idempotency | counts reconcile | content checksum and trace valid | links work after reload | worker CV tests | live outcomes |
| Artifact/download parity | every stage and bundle | links only when valid | status/headers correct | payload/checksum persisted | no fake availability | stage/count match rows | downloaded bytes equal DB/mirror | user can inspect history | artifact tests | byte parity |
| Export actions | selected stable Run job IDs with filters | preview and CSV state | stale preview rejects, order stable | only selected IDs | no pipeline mutation | selected facts match | CSV matches rows | export visible after reload | export tests partial | browser + bytes |
| Historical replay | mutate settings, prompts, synonyms, profile, Scan after success | old Run remains readable | same historical API | snapshots/artifacts/outcomes unchanged | replay uses Run-owned truth | stage results unchanged | downloads unchanged | detail matches prior | snapshot tests partial | live mutation replay |

Coverage labels stay conservative: existing unit, route, or mocked worker tests are not live-proven. Every missing row needs direct boundary proof or live evidence below.

### 10. Implementation Patch Tasks

Run-specific work is folded into the single Tasks 1-7 graph above. Do not create a second Run task graph or coordination ledger.

- **Task 2:** owns crash-consistent Run snapshot persistence, deterministic filesystem projection, stable queue ID, pre-commit cleanup, post-commit enqueue failure, and restart reconciliation.
- **Task 3:** owns Scan queue binding, enqueue failure terminalization, stale recovery, cancellation, and reuse of the stored `created_at`-resolved cutoff.
- **Task 4:** owns one managed Run source resolver, ordered provenance, idempotency, compatibility isolation, and API failure envelopes.
- **Task 5:** owns Run picker and Run Details rendering through six persisted display stages, explicit Normalize-to-Enrichment projection, server capabilities, and stable IDs.
- **Task 6:** owns direct boundary tests for managed/legacy discrimination, job conservation, stage projection, artifact capability warnings, retries, Continue, cancellation, and upload-vs-Scan equivalence.
- **Task 7:** owns fresh live evidence across upload-only, Scan-only, combined, recovery, historical replay, artifact integrity, and final scope reconciliation.

All Run proof uses the same Task 1-7 ledger, dependencies, validator profiles, and checkpoint-commit workflow.

### 11. Live Verification Procedure

Use an Active, Succeeded Candidate Profile and configured local runtime. Use temporary local data. Preserve existing user-owned files.

1. Recompute canonical record counts and SHA-256 for `data/sample_jobs_1.json` and `data/sample_jobs_2.json`; record observed values as preflight evidence only and stop on malformed or unexpected local fixture changes.
2. Run upload-only with `sample_jobs_1.json`; capture request, Run ID, queue binding, snapshots, worker integrity, all stage transitions, artifacts, terminal status, API projections, visible rows/counts, and downloaded bytes.
3. Repeat upload-only with `sample_jobs_2.json`; compare count and stage conservation.
4. Run Scan-only from one real successful non-empty Scan; archive source after trigger and attempt referenced delete; prove copied Run input still executes.
5. Download exact Scan JSON and run it as upload with same profile/settings; compare canonical bytes, count, order, stage facts, outcomes, and deterministic artifacts. Provenance labels may differ.
6. Run combined upload plus Scan; assert upload rows precede Scan rows, internal order is stable, manifest ordinals/digests match `run_scan_inputs`, and pipeline counts equal merged snapshot.
7. Inject pre-commit persistence, post-commit projection, enqueue, input-integrity, Normalize, Enrich, filter persistence, vector, ranking, CV Analysis, CV Generation, validation, artifact, and final-status failures. Record backend state, retryability, retained evidence, UI state, and cleanup; distinguish artifact warnings from lifecycle failure.
8. Cancel while queued and during one long stage; execute manual Continue when supported. Assert no duplicate work, exact next-stage resume, stable prior artifacts, and correct terminal capabilities.
9. Change settings, prompts, synonyms, LLM routing, Candidate Profile, and source Scan after success. Reload and replay historical Run using Run-owned snapshots; record any explicitly non-snapshotted infrastructure.
10. Browser-check 390px and 1280px, keyboard/focus, reduced motion, console cursor polling, stale actions, retry, duplicate click, export, CV download, reload, and action persistence.
11. Compare every visible Run Detail count and row with `/runs/{run_id}`, `/runs/{run_id}/stages`, `/runs/{run_id}/jobs`, SQLite, and artifact JSON. Visual similarity alone fails acceptance.

### 12. Stop Gate

Do not mark Run Pipeline integrated until fresh evidence proves:

1. **Prototype parity:** Runs workspace, Trigger Run, Run Input, Pipeline Results, stage navigation, Passed/Rejected, Console, lifecycle actions, responsive layout, keyboard/focus, loading, retry, stale, and empty states match the current prototype.
2. **Frontend/API integration:** exact request and response contracts for Trigger, list, detail, stages, jobs, events, Continue, Retry, Cancel, Archive/Unarchive, bookmarks, interest, exports, CV actions, downloads, and debug bundle are captured.
3. **Immutable snapshots:** worker bytes equal immutable Run input; pipeline profile and settings equal captured checksums/revisions; later Scan and mutable configuration changes do not alter historical evidence.
4. **Queue/worker execution:** one durable queue binding per submission, distinct worker attempts under automatic retry, no duplicate execution, durable lease/attempt events, safe stale recovery, startup integrity checks, and no orphan after persistence failure.
5. **All applicable stages:** seven runtime-stage IDs execute in `PIPELINE_STAGE_SEQUENCE`; runtime Normalize, Enrich, Rule Filter, Shortlist, Ranking, CV Analysis, and CV Generation receive expected prior output; an explicit projection maps runtime facts/artifacts into the existing six control-plane stages, with Normalize visible inside Enrichment. No seven-row control-plane migration occurs.
6. **Job conservation:** every input occurrence has stable identity and explicit terminal/intermediate outcome; no silent loss or duplicate; equations reconcile after documented deduplication.
7. **Artifact correctness:** every artifact/download has correct Run/stage/attempt/version identity, checksum, schema, count, and rows matching persisted facts; unavailable artifacts disable only affected actions and emit integrity warnings without redefining terminal success.
8. **Run Details persisted truth:** visible status, counts, rows, reasons, rank, CV state, selection, exports, console, and links equal DB/API/artifact projections after reload; frontend taxonomy is absent.
9. **Terminal lifecycle:** Succeeded follows orchestration and the existing native terminal decision; Failed, Cancelled, Awaiting Continue, and partial results retain correct evidence and capabilities. Artifact warnings disable affected actions without redefining lifecycle; retry/resume/Continue do not mutate completed snapshots.
10. **User actions:** export, bookmark, interest, CV review/regenerate, cancel, archive, unarchive, retry, Continue, stage download, and debug bundle target stable IDs and remain idempotent under stale revisions or duplicate clicks.
11. **Historical reproducibility:** post-run changes to settings, prompts, synonyms, profile, Scan lifecycle, and registry do not alter snapshots, artifacts, outcomes, CVs, or Run Details. External exceptions are recorded.
12. **SSOT audit:** stage order, display mapping, lifecycle, terminal decision, outcome taxonomy, counts, artifact names/availability, snapshots, attempts/checkpoints, CV state, and Run Detail rows each have one canonical owner.

Insufficient evidence: `POST /runs` returns `201`, Run reaches `Succeeded`, browser page looks correct, mocked `run_pipeline`, isolated stage tests, generated CV exists, or documentation claims alignment.

## Verification

### 7. Stop Gate

The feature is not integrated until all gates below have fresh evidence:

1. **Prototype parity:** Scans workspace, New Scan, tracked-company picker, Scan Details, Run picker, Run Details, responsive layout, keyboard/focus, loading/error/stale/disabled states, and console polling match `docs/fitcv-settings-ui-prototype.html`.
2. **Frontend/API integration:** browser network evidence shows exact `POST /scans`, tracked-company verify/create, eligible Scan query, and managed multipart `POST /runs`; duplicate submission and stale selection return stable errors.
3. **Backend persistence:** SQLite/filesystem/queue evidence shows immutable Scan input snapshots, one-winner claim, stored created_at-resolved cutoff, queue binding, output manifest, crash-consistent Run bundle, ordered `run_scan_inputs`, referenced-delete restriction, and recovery or cleanup for every interrupted state.
4. **Canonical Scan output:** real provider output passes the same `canonicalize_jobs` contract as upload data; output is exact UTF-8 JSON, digest/byte length/count match, Table and JSON agree, `[]` downloads but is not Run-eligible, and integrity failure disables Run.
5. **Run ingestion:** upload-only, Scan-only, multi-Scan, upload plus one Scan, and upload plus multiple Scans preserve upload-first and selected-Scan ordering, source digests, ordinals, manifest, copied path, and immutable bytes.
6. **Historical integrity:** archiving or registry changes do not alter existing Run snapshots; referenced Scan delete is blocked; Run worker verifies copied path, bytes, digest, manifest, and Scan provenance before execution.
7. **Actual downstream execution:** at least one real Scan-derived Run reaches Normalize, Enrichment, Screening, Shortlisting, Ranking, optional CV stages where enabled, and correct terminal status; no Scan-specific adapter exists downstream.
8. **Equivalence:** one downloaded successful Scan artifact produces equivalent canonical input and pipeline behavior when uploaded directly, with acquisition provenance as the only expected difference.
9. **SSOT audit:** no duplicate canonical job schema, Scan eligibility rule, provider detector, lifecycle rule, template limit, or Run source-construction branch remains.
10. **Scope reconciliation:** all changed files are listed targets or explicitly approved supporting files; the four pre-existing sample-data changes remain untouched.

The following are insufficient by themselves: rendered UI, successful API response, mocked Scan output, successful Run creation, or existing documentation claiming parity.

## Completion Criteria

The plan is ready for completion verification when:

1. Tasks 1 through 7 have accepted task-local proof and no unresolved dependency or blocker.
2. Scan contract, tracked-company boundary, lifecycle, queue, worker, output, API, persistence, UI, and Run snapshot owners match the approved spec.
3. All required scenario rows are proven, with mock-only evidence replaced by direct boundary or live evidence where the stop gate requires it.
4. Canonical Scan output and uploaded equivalent bytes pass the same downstream pipeline path.
5. No referenced Scan can be deleted, no Run rereads live Scan output, and persistence failure leaves no partial rows or staged files.
6. Final verification is fresh, Git status is reconciled, `git diff --check` passes, and no user-owned data changes are discarded.
7. Execution changes plan status from `proposed` to `active` before Task 1; only `skill-verification-before-completion` may change an active plan to `completed` after returning `verified`.
