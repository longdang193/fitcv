---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-managed-scan-lifecycle
targets:
  - src/fitcv/job_sources.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/scan_contracts.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/scan_detail.html
  - src/fitcv_cp/templates/scans_list.html
  - tests/test_job_sources.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
  - docs/fitcv-settings-ui-prototype.html
related_features:
  - cv_system
  - trigger_run_management
  - scan_management
related_stages:
  - normalize
---

# FitCV Managed Scan Lifecycle

## Goal and Problem

### Problem

FitCV can acquire jobs from supported careers portals, but current control-plane behavior performs acquisition inside Run creation and asks users for provider, company name, and careers URL each time. That makes retrieval configuration a repeated user input, prevents a successful scan from being inspected or reused, and couples provider availability to Run creation.

The approved product flow requires Scan to be a managed resource. Users select tracked companies and filters, Scan writes one canonical FitCV JSON artifact, and a later Run may supply one uploaded job file, one or more Scan outputs, or both. Provider-specific acquisition remains owned by the Option C provider contract; this specification owns the minimum tracked-company registry required by Scan V1, Scan persistence, API behavior, errors, lifecycle, and Run references.

### Goal

Define one reusable Scan resource whose output is the same canonical job array accepted by upload mode.

- users trigger one Scan for one, multiple, or all active scannable tracked companies
- users never re-enter careers URLs during Scan creation
- every Scan records immutable input and tracked-company snapshots
- successful Scan output is immutable and downloadable as a FitCV JSON file, including `[]`
- Run creation may combine one optional uploaded job file with one or more active, successful, non-empty Scan outputs
- archive state remains independent from execution state
- provider additions do not change Scan API, persistence, UI states, or Run integration

## Relationship to Existing Contracts

- `docs/superpowers/specs/2026-07-24-13-15-fitcv-job-source-option-c-spec.md` owns provider detection, retrieval, provider-boundary adaptation, canonicalization, and acquisition safety.
- `src/fitcv/contracts.py` and `src/fitcv/ingest.py` remain canonical owners of accepted job fields and canonical job serialization.
- this specification owns the minimum runtime tracked-company registry needed to list, verify, and add active scannable companies from the Scan UI. Provider definitions and provider detection remain owned by the Option C provider registry.
- this specification replaces direct user-submitted provider, company-name, and careers-URL fields as the intended V1 Scan flow. Compatibility removal for existing trigger-time scanner fields belongs to implementation planning and migration.

## Required Outcomes

### Outcome: Managed Scan Resource

- affected actor or system: Scans workspace, control-plane API, worker, and persistence
- required result: each trigger creates one inspectable Scan before external acquisition begins
- success condition: queued, running, terminal, archived, output, and event states survive process restart

### Outcome: Tracked-Company Selection

- affected actor or system: non-technical user and company registry
- required result: Scan creation references registry company IDs instead of accepting portal URLs
- success condition: one, multiple, and all selections resolve through the same request and snapshot path

### Outcome: Runtime Tracked-Company Registry

- affected actor or system: Scan company picker, Add Company flow, provider registry, and persistence
- required result: verified tracked companies are stored once as runtime resources and exposed through one searchable API
- success condition: adding a supported company requires no repository-file edit, provider metadata is not duplicated, and subsequent Scans reference the new company by ID

### Outcome: Upload-Symmetric Output

- affected actor or system: Scan output, Run creation, and pipeline input
- required result: Scan output is one canonical UTF-8 JSON array copied into the existing immutable Run input snapshot
- success condition: downstream pipeline behavior cannot distinguish equivalent upload and Scan-derived arrays

### Outcome: Additive Run Input

- affected actor or system: Run trigger UI, Run API, Run input persistence, and pipeline worker
- required result: one optional upload and an ordered unique Scan selection resolve through one atomic canonicalization path
- success condition: upload-only, Scan-only, and combined requests create the same immutable Run snapshot shape and preserve deterministic source provenance

### Outcome: Safe Reuse and Deletion

- affected actor or system: Scan lifecycle and Run provenance
- required result: Runs retain ordered references to source Scans and referenced Scans cannot be deleted
- success condition: archive is reversible, delete is previewed, and no Run loses input provenance

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| How are scanner jobs acquired now? | Run creation accepts provider, company name, careers URL, keywords, limits, and timeout, then acquires synchronously before Run persistence. | `src/fitcv_cp/app.py`, `src/fitcv/job_sources.py` | high | Managed Scan must remove repeated portal input and separate acquisition from Run creation. |
| What owns canonical job validation? | `canonicalize_jobs` and existing ingest contracts validate and serialize ordered job arrays. | `src/fitcv/ingest.py`, `src/fitcv/contracts.py` | high | Scan output must call this owner and must not define another field schema. |
| What Run input contract exists now? | Multipart `POST /runs` requires an exclusive `source_mode`, accepts exactly one upload in upload mode, and performs direct scanner acquisition in scanner mode. | `src/fitcv_cp/app.py`, `tests/test_fitcv_cp/test_app.py` | high | New managed UI must omit exclusive mode selection, accept optional upload plus ordered Scan IDs, and retain legacy modes only behind their existing compatibility contract. |
| Which reusable API conventions exist? | Control plane already provides data envelopes, collection pagination, stable API errors, idempotent actions, signed delete previews, and row revisions. | `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py` | high | Scan API should reuse these conventions instead of adding parallel infrastructure. |
| Which event store is reusable? | Generic immutable `process_events` supports arbitrary process type and ID with cursor retrieval and sanitization. | `src/fitcv_cp/models.py`, `src/fitcv_cp/sqlite_store.py` | high | Scan Console should use `process_type = "scan"`; no Scan event table is needed. |
| What UI behavior is approved? | Unified prototype defines Scans workspace, Active/Archived lifecycle, details, Console, Table/JSON output, and Run input selection. | `docs/fitcv-settings-ui-prototype.html` | high | Backend capabilities and states must materialize prototype without layout-specific transport rules. |

### Constraints and Alternatives

- constraint: canonical output must remain usable wherever uploaded FitCV JSON is accepted
- constraint: provider registry, company registry, Scan lifecycle, canonical job schema, and Run snapshot each require one owner
- constraint: local SQLite and existing FastAPI/Pydantic/store patterns remain implementation baseline
- alternative: keep trigger-time scanner fields inside Run creation
  - benefit: smallest immediate code change
  - trade-off: no reusable output, repeated URLs, no Scan history, and provider failures block Run creation synchronously
  - reason rejected: violates approved managed-Scan flow and future tracked-company expansion
- alternative: persist one normalized Scan job row per output item
  - benefit: direct SQL pagination
  - trade-off: duplicates canonical JSON truth and requires synchronization
  - reason rejected: V1 output cap makes parsing one immutable array cheaper and safer
- alternative: create Scan-specific event and idempotency stores
  - benefit: isolated tables
  - trade-off: duplicates existing generic infrastructure and lifecycle rules
  - reason rejected: existing stores already satisfy required behavior

## Scope

### In Scope

- Scan list and detail resources
- tracked-company list, verification, and create operations required by Scan V1
- Scan creation for selected or all tracked companies
- title, location, predefined publication-window, and total-row filters
- asynchronous execution, cancellation, events, and terminal failures
- immutable canonical output, paginated table projection, JSON display, and download
- Run Again as creation of a new Scan
- Active and Archived Scan lifecycle
- bulk Archive, Unarchive, delete preview, and delete
- one optional upload plus one or multiple successful Scan outputs as Run job input
- stable API errors, idempotency, revisions, and capabilities

### Out of Scope

- tracked-company rename, archive, delete, bulk import, or general registry-management workspace
- provider-native request or response schemas
- canonical FitCV job-field definitions
- provider credentials or secret storage
- scheduling or recurring Scans
- cross-Scan deduplication
- mutable Scan output
- mandatory public CLI parity

## Contract Ownership

| Concern | Owner | Rule |
|---|---|---|
| Provider retrieval | Option C provider registry | Scan executor calls one registered provider per tracked-company snapshot. |
| Canonical job shape | `fitcv.contracts` and `fitcv.ingest` | Scan API and UI never redefine job fields. |
| Company configuration | runtime tracked-company registry defined here | Scan stores an immutable snapshot; provider identity still derives from the Option C provider registry. |
| Scan lifecycle | managed Scan store and API | Execution status, archive state, output manifest, capabilities, and errors derive here. |
| Console events | existing `process_events` store | Scan uses `process_type = "scan"`; no second event table. |
| Run input snapshot | existing Run input contract | Scan outputs are copied, not referenced at execution time. |
| Run-to-Scan provenance | `run_scan_inputs` relation | One ordered relation owns reference checks and deletion blocking. |

## API Contract

### Shared Conventions

- resource responses use the existing `{ "data": ... }` envelope
- list responses use existing `data`, `page`, and `meta` collection shape
- API errors use existing `error.code`, `error.message`, `error.field_errors`, `error.retryable`, and `error.action`
- page numbers start at 1; `page_size` accepts existing values `10`, `20`, or `50`
- mutating requests require `Idempotency-Key`; reuse with a different normalized request returns `idempotency_conflict`
- timestamps are UTC RFC 3339 strings
- IDs are opaque strings; UI may display them but must not parse them
- list order defaults to `created_at DESC, scan_id DESC`
- `row_revision` increments on every mutable Scan-row change and supports stale-action detection

### Routes

| Method | Route | Success | Purpose |
|---|---|---:|---|
| `GET` | `/scans` | 200 | List Active or Archived Scans with filters and pagination. |
| `GET` | `/tracked-companies` | 200 | List active scannable companies for Scan selection. |
| `POST` | `/tracked-companies/actions/verify` | 200 | Validate and probe one proposed company without persistence. |
| `POST` | `/tracked-companies` | 201 | Reverify and persist one active scannable company. |
| `POST` | `/scans` | 201 | Persist input snapshot and enqueue a new Scan. |
| `GET` | `/scans/{scan_id}` | 200 | Return Scan detail, snapshots, output manifest, failure, and capabilities. |
| `GET` | `/scans/{scan_id}/events` | 200 | Return cursor-aware Console events from shared process-event store. |
| `GET` | `/scans/{scan_id}/jobs` | 200 | Return paginated rows parsed from canonical Scan output. |
| `GET` | `/scans/{scan_id}/output` | 200 | Return exact canonical JSON bytes for JSON view or download. |
| `POST` | `/scans/{scan_id}/actions/cancel` | 202 | Request cancellation for queued or running Scan. |
| `POST` | `/scans/{scan_id}/actions/run-again` | 201 | Create a new Scan from original logical inputs and current registry state. |
| `POST` | `/scans/actions/archive` | 200 | Archive selected terminal Active Scans atomically. |
| `POST` | `/scans/actions/unarchive` | 200 | Restore selected Archived Scans atomically. |
| `POST` | `/scans/actions/delete-archived/preview` | 200 | Resolve eligible, referenced, invalid, and missing selected Scans. |
| `POST` | `/scans/actions/delete-archived` | 200 | Delete previewed eligible Scans atomically. |

### Tracked-Company Registry

`GET /tracked-companies` accepts `search`, `page`, and `page_size`. Search matches company name, provider ID, and careers-URL host case-insensitively. Results contain `company_id`, `company_name`, canonical `careers_url`, `provider_id`, `row_revision`, and created and updated times. Only active scannable resources are selectable in V1.

`POST /tracked-companies/actions/verify` accepts:

| Field | Requirement |
|---|---|
| `company_name` | Required trimmed string, maximum 120 characters. |
| `careers_url` | Required public canonical HTTPS URL without credentials, query, or fragment. |

Verification uses the Option C provider registry to require exactly one provider match, applies its URL and transport security policy, and performs the provider's bounded public portal-shape probe. Success returns normalized company name, canonical careers URL, provider ID, and safe provider label. It writes no registry row.

`POST /tracked-companies` accepts the same fields, requires `Idempotency-Key`, repeats verification server-side, rejects a canonical URL already present, and inserts one active scannable tracked-company resource. The create operation never trusts prior verification response fields supplied by the client. Runtime SQLite persistence is the tracked-company SSOT; repository YAML is not required for user-managed companies.

Scan creation resolves current tracked-company rows and stores an immutable ordered company snapshot plus a checksum of the resolved rows. Later company edits cannot change historical Scan input.

### List Scans

`GET /scans` accepts:

- `lifecycle`: `active` or `archived`; default `active`
- `execution_status`: optional `queued`, `running`, `cancelling`, `succeeded`, `failed`, or `cancelled`
- `usable_for_run`: optional boolean derived from capabilities
- `search`: optional trimmed substring matched case-insensitively against Scan ID and Scan name
- `page` and `page_size`: existing pagination contract

List resources contain summary fields only: identity, name, execution status, lifecycle, timestamps, company count, output record count, failure summary, `row_revision`, and capabilities. Input snapshots, events, and output rows remain detail endpoints.

### Create Scan Request

`POST /scans` accepts one request shape:

| Field | Requirement |
|---|---|
| `scan_name` | Optional trimmed string, maximum 120 characters. Blank creates a server-generated time-based display name. |
| `company_ids` | Required non-empty ordered list of tracked-company IDs; trimmed, deduplicated preserving order, maximum 500. Selecting every tracked company uses the same list field. |
| `job_titles` | Optional ordered list of trimmed non-empty strings; deduplicated preserving order; maximum 50 items and 120 characters each. Empty means any title. |
| `locations` | Optional ordered list of trimmed non-empty strings; deduplicated preserving order; maximum 50 items and 200 characters each. Empty means any location. |
| `published_window` | Required enum: `any`, `past_12_hours`, `past_24_hours`, `past_7_days`, `past_30_days`, or `past_180_days`; default `any`. |
| `total_rows` | Integer from 1 through 200; default 50. This is one global output cap across selected companies. |

Ordinary users cannot submit provider IDs, company names, careers URLs, transport timeouts, TLS settings, redirect policy, or request limits. Those values come from tracked-company snapshots and central scanner configuration.

### Create Scan Behavior

1. validate and normalize request before external network access
2. resolve selected active scannable registry entries
3. preserve normalized requested company order; UI Select All expands to the same explicit `company_ids` list before submission
4. resolve `published_window` against Scan `created_at` and store both requested window and concrete UTC cutoff
5. reserve the normalized request through existing idempotent-action infrastructure
6. inside one `BEGIN IMMEDIATE` transaction, re-read the reserved action; return its existing Scan when a provisional response already contains `scan_id`, otherwise store the queued Scan, logical request, immutable execution-safe company snapshots, and a provisional action response containing the new `scan_id`
7. enqueue execution with one stable queue job ID derived from `scan_id`
8. persist the queue binding, complete the idempotent action with the final response, and return the Scan resource

If execution stops after action reservation but before Scan persistence, retry completes the same reserved action. If execution stops after Scan persistence but before enqueue completion, retry loads the same Scan from the provisional action response and resumes enqueue with the same stable queue job ID. Concurrent retries cannot create a second Scan. If queue submission fails after persistence, Scan becomes `failed` with `scan_enqueue_failed`; the action stores the same HTTP 503 response containing safe Scan identity in `data`. No queued orphan remains.

### Retrieval, Filtering, and Ordering

- all filters are evaluated against provider-adapted canonical fields, not provider-native shapes
- values within `job_titles` use case-insensitive Unicode substring OR matching
- values within `locations` use case-insensitive Unicode substring OR matching
- title, location, and publication filters combine with AND semantics
- `any` applies no publication cutoff; every other window compares publication time inclusively against the stored UTC cutoff
- full provider timestamps compare exactly after UTC normalization
- provider date-only values compare by UTC calendar date against the cutoff date, intentionally allowing the cutoff date because finer precision is unavailable
- jobs without a parseable publication date are excluded only when the selected window is not `any`
- providers may apply native server-side filters for efficiency but must apply shared canonical checks before returning accepted jobs
- output order is immutable company snapshot order, then provider-return order within each company
- executor appends matching jobs until `total_rows`, source exhaustion, cancellation, or total deadline; no cross-company deduplication occurs
- any selected-company acquisition failure fails whole Scan and commits no output; partial company results remain event diagnostics only

### Scan Resource

One Scan resource exposes:

- identity: `scan_id`, `scan_name`
- lifecycle: `execution_status`, `lifecycle`, `row_revision`
- times: `created_at`, `started_at`, `finished_at`, `cancel_requested_at`, `archived_at`
- actor fields: `created_by`, `cancel_requested_by`, `archived_by`
- progress: `companies_completed`, `companies_total`
- counts: `output_record_count` derived from output manifest
- input summary: requested company IDs, resolved company count, filters, total-row cap, registry snapshot revision
- output manifest when succeeded: record count, byte length, SHA-256, media type, canonical schema revision, created time
- failure when failed: stable code, safe message, retryable flag, and action
- provenance: `rerun_of_scan_id` when created by Run Again
- warnings: bounded non-fatal diagnostics that do not represent a failed company, failed portal, missing required detail, or incomplete acquisition
- derived capabilities: `inspect`, `cancel`, `run_again`, `download`, `archive`, `unarchive`, `delete`, `use_for_run`

Capabilities are server-derived and are the UI action owner:

| Capability | True when |
|---|---|
| `inspect` | Scan exists. |
| `cancel` | Active and status is `queued` or `running` with no cancellation request. |
| `run_again` | Status is terminal. Archive state does not matter. |
| `download` | Status is `succeeded` and output manifest exists, including zero rows. |
| `archive` | Active and status is terminal. |
| `unarchive` | Archived and status is terminal. |
| `delete` | Archived, terminal, and no Run references the Scan. Commit still requires preview. |
| `use_for_run` | Active, `succeeded`, output integrity is valid, and output record count is greater than zero. |

### Events

`GET /scans/{scan_id}/events` reuses existing process-event pagination and returns events where `process_type = "scan"` and `process_id = scan_id`.

- operations identify lifecycle steps such as registry resolution, company retrieval, canonicalization, output commit, and cancellation
- event payloads remain bounded and redacted by existing process-event sanitization
- Console polling uses returned `next_cursor`; terminal Scan status stops automatic polling after final refresh
- event failure does not permit mutation of immutable prior events

### Output

Successful output is one immutable canonical UTF-8 JSON array.

- `scan_outputs.output_json` stores canonical bytes as text and is the output SSOT
- manifest SHA-256 and byte length are computed from exact UTF-8 bytes
- `[]` is a valid successful Scan output with record count zero
- status changes to `succeeded` only in the transaction that stores valid output and manifest
- failed, cancelled, queued, running, and cancelling Scans have no output row
- output never changes after success; Run Again creates a new Scan

`GET /scans/{scan_id}/jobs` parses this same output and returns a paginated table projection. It does not persist a second job table. With the V1 cap of 200 rows, parsing the canonical array per request is sufficient.

`GET /scans/{scan_id}/output` returns exact stored bytes with:

- media type `application/json; charset=utf-8`
- `ETag` equal to quoted output SHA-256
- `X-Content-Type-Options: nosniff`
- `Content-Disposition` attachment only when `download=true`; filename is a sanitized Scan ID plus `.json`

Queued, running, and cancelling output requests return `scan_output_not_ready`. Failed and cancelled output requests return `scan_output_unavailable`.

### Run Again

Run Again never mutates or resumes a terminal Scan.

- copies original logical filters, total-row cap, and requested company IDs
- preserves the original `published_window` but resolves a new cutoff from the new Scan `created_at`
- re-resolves original requested company IDs from current registry state
- creates new input and company snapshots
- sets `rerun_of_scan_id` to original Scan ID
- accepts optional replacement `scan_name`; otherwise derives a new display name
- fails before creation if current registry cannot satisfy selection

### Archive and Unarchive

Archive and Unarchive use one batch request shape containing `items`, each with `scan_id` and `expected_revision`.

- duplicate IDs are rejected as `validation_failed`
- server validates entire selection before mutation
- archive requires Active terminal Scans
- unarchive requires Archived terminal Scans
- stale revisions return `scan_revision_conflict`
- any missing or invalid item rejects entire batch; no partial mutation
- successful response returns refreshed resources in request order
- same endpoint supports one detail-page Scan or many workspace selections

### Delete Preview and Commit

Delete is limited to Archived terminal Scans and follows existing preview/commit behavior.

Preview returns:

- requested IDs
- eligible IDs
- referenced IDs with related Run counts
- non-Archived or non-terminal blocked IDs
- missing IDs
- signed `preview_revision` with five-minute expiry

Commit requires same IDs, `preview_revision`, and `Idempotency-Key`. Any changed lifecycle, revision, Run reference, or missing record returns `delete_preview_stale` and deletes nothing. Database foreign keys use `ON DELETE RESTRICT` for Run references as final protection.

Successful delete removes Scan, input, and output rows. Existing immutable `process_events` remain under their existing retention policy, contain no canonical job payload, and are no longer reachable through Scan API after resource deletion.

### Run Input Integration

Managed UI Run creation uses multipart `POST /runs` and submits:

| Field | Requirement |
|---|---|
| `jobs_file` | Optional single JSON or JSONL upload using existing upload validation. |
| `scan_ids` | Optional repeated form field containing ordered Scan IDs; trim and deduplicate preserving first occurrence. |
| `profile_id` | Required Active, Succeeded Candidate Profile ID. |
| `run_name` | Optional trimmed string, maximum 120 characters. |

The managed UI does not submit `source_mode` or `jobs_input_mode`. At least one of `jobs_file` or `scan_ids` must be present. Upload-only, Scan-only, and combined requests use one resolver. Legacy JSON, path, paste, upload-mode, and direct-scanner contracts remain separate compatibility inputs until their approved migration; no synthetic combined value is added to either legacy mode field.

Before Run creation, the server:

1. validates the request, Candidate Profile, and optional upload without creating a Run
2. loads selected Scans in request order and requires every Scan to satisfy `use_for_run`
3. verifies every selected output byte length and SHA-256 before parsing
4. concatenates uploaded rows first when present, then Scan rows in selected order, preserving each source's internal order
5. passes the complete merged row list through existing canonicalization once
6. materializes one Run-owned filesystem projection through the existing atomic file writer after all source validation succeeds
7. stores Run, immutable Run job snapshot, Run job projection rows, upload and ordered Scan provenance in `jobs_input_manifest_json`, and ordered `run_scan_inputs` references in one SQLite transaction
8. deletes the newly materialized filesystem projection if the SQLite transaction fails before commit
9. queues the existing pipeline only after the SQLite transaction commits

Source resolution performs no persistence. SQLite owns one transaction for Run, Run input, Run job projection rows, and `run_scan_inputs`; the filesystem projection cannot participate in SQLite atomicity and is therefore staged first and removed on transaction failure. Invalid upload, missing sources, unavailable Scan, integrity failure, Candidate Profile conflict, or persistence failure creates no Run records and leaves no orphan projection. Queue failure occurs after commit, preserves the Run-owned projection, and terminalizes the persisted Run through its existing failure contract.

Run-trigger idempotency fingerprint includes upload SHA-256 when present, ordered selected Scan IDs and verified output SHA-256 values, Candidate Profile ID and revision, and normalized Run name.

`jobs_input_source` records `upload`, `scan`, or `combined` as persisted provenance only. `jobs_input_manifest_json` contains one ordered `sources` array: upload first when present, then Scan entries. Upload entries retain filename, media type, byte length, SHA-256, and record count. Scan entries retain Scan ID, output SHA-256, record count, and selected ordinal. `run_scan_inputs` remains the relational owner of Scan references and deletion blocking.

No Scan output is read during worker execution. Run replay uses the copied Run snapshot and never rereads the tracked-company registry.

## Design Decisions

### Decision: Managed Scan Owns Acquisition Lifecycle

- context: provider acquisition currently occurs inside Run creation
- selected approach: create and finish Scan independently; Run later selects immutable Scan output
- rationale: separates external retrieval reliability from pipeline execution and enables reuse
- alternatives considered: direct scanner Run mode or separate scanner service
- accepted trade-offs: one additional persisted resource and worker lifecycle
- affected owners and boundaries: control plane, Scan worker, Run creation, and UI

### Decision: One Canonical Output JSON Is SSOT

- context: UI needs Table, JSON, download, and Run input views
- selected approach: persist one canonical JSON array and derive every view from it
- rationale: avoids output synchronization and preserves upload symmetry
- alternatives considered: output file plus DB rows, or provider-native result storage
- accepted trade-offs: bounded JSON parsing for Table requests
- affected owners and boundaries: Scan output store, output API, and Run input resolver

### Decision: Archive Is Orthogonal to Execution

- context: lifecycle organization and execution completion are different facts
- selected approach: immutable execution status plus reversible archive metadata
- rationale: same state model supports succeeded, failed, and cancelled records uniformly
- alternatives considered: archive as execution status or separate archived tables
- accepted trade-offs: capabilities must evaluate both axes
- affected owners and boundaries: Scan row, list filters, detail actions, and delete guard

### Decision: Run Copies Output and Stores Ordered References

- context: Run must remain replayable if Scan or registry state changes
- selected approach: verify each selected source, merge upload first and Scan outputs in explicit order, serialize one Run snapshot, and persist ordered `run_scan_inputs`
- rationale: immutable execution plus relational deletion safety
- alternatives considered: worker reads Scan output live or manifest-only references
- accepted trade-offs: combined requests reserialize canonical rows once instead of copying one source's bytes verbatim
- affected owners and boundaries: Run input persistence, worker replay, Scan deletion

### Decision: Runtime Registry Owns User-Managed Companies

- context: Scan selection and Add Company require persistent runtime mutation, while provider definitions are code-owned
- selected approach: store tracked-company resources in existing SQLite persistence and derive provider identity from the Option C registry during verification
- rationale: UI additions survive restart without repository edits or duplicated provider metadata
- alternatives considered: `company_portals.yaml`, browser-local storage, or provider-specific company tables
- accepted trade-offs: registry rows require ordinary API validation, revisions, and migration
- affected owners and boundaries: tracked-company API, control-plane store, provider registry, and Scan input snapshots

### Decision: Publication Filters Use Stable Windows

- context: UI offers predefined relative periods rather than arbitrary dates
- selected approach: accept one `published_window` enum, resolve its UTC cutoff at Scan creation, and store both values in immutable input
- rationale: every provider receives one stable execution-time boundary and Run Again can resolve a fresh cutoff without mutating history
- alternatives considered: client-calculated dates or arbitrary calendar input
- accepted trade-offs: date-only provider values use documented day-granularity approximation
- affected owners and boundaries: Scan request, input snapshot, canonical filtering, and Scan details

### Decision: Reuse Generic Control-Plane Infrastructure

- context: events, idempotency, envelopes, pagination, revisions, and delete preview already exist
- selected approach: extend those patterns to Scan without new frameworks or stores
- rationale: fewer owners and symmetric API behavior
- alternatives considered: Scan-specific abstractions
- accepted trade-offs: Scan routes follow existing control-plane conventions even where another API shape could be shorter
- affected owners and boundaries: FastAPI routes, store, SQLite schema, and UI client

### Compatibility, Migration, and Risk

- old behavior: Run creation may accept direct scanner provider and portal fields
- new behavior: Scans workspace acquires jobs first; managed Run creation accepts one upload, ordered Scan outputs, or both
- compatibility boundary: existing historical Run snapshots remain readable and executable
- migration or backfill: no historical Scan backfill; direct scanner Runs remain Runs without Scan references
- rollout and rollback: add Scan resources and Run selection before removing direct scanner form fields; rollback keeps historical Scan rows inert and preserves Run snapshots
- deprecation or consumer impact: direct scanner request fields require explicit implementation-plan deprecation and route-test updates
- risk: existing installations have no tracked-company rows
  - mitigation: migration creates an empty registry without inventing companies; New Scan remains unavailable until a verified company is added
- risk: output corruption could affect download and Run creation
  - mitigation: SHA-256 and byte-length verification fail closed before either operation

## Data Model

### `tracked_companies`

Mutable runtime registry row:

| Column | Contract |
|---|---|
| `company_id` | Primary key, opaque ID. |
| `company_name` | Required display name, maximum 120 characters. |
| `careers_url` | Canonical public HTTPS URL, unique. |
| `provider_id` | Provider registry ID derived during verification. |
| `is_active`, `is_scannable` | Boolean guards; V1 create sets both true only after successful verification. |
| `created_at`, `updated_at` | UTC timestamps. |
| `created_by`, `updated_by` | Actor identity from authenticated request context. |
| `row_revision` | Positive integer incremented on mutation. |

Provider labels, detectors, transport behavior, request limits, and credentials are not copied into this table. Scan snapshots copy only execution-safe values needed to reproduce one acquisition attempt.

### `scans`

Mutable lifecycle row:

| Column | Contract |
|---|---|
| `scan_id` | Primary key, opaque ID. |
| `scan_name` | Display name, maximum 120 characters. |
| `execution_status` | `queued`, `running`, `cancelling`, `succeeded`, `failed`, or `cancelled`. |
| `created_by` | Actor identity from authenticated request context. |
| `created_at`, `started_at`, `finished_at` | UTC lifecycle timestamps. |
| `cancel_requested_at`, `cancel_requested_by` | Nullable cancellation request metadata. |
| `archived_at`, `archived_by` | Nullable archive metadata; null means Active. |
| `companies_completed`, `companies_total` | Non-negative progress counters. |
| `failure_code`, `failure_message`, `failure_retryable` | Populated only for failed execution. |
| `warning_json` | Bounded non-fatal diagnostics; empty unless successful acquisition remains complete and trustworthy. |
| `rerun_of_scan_id` | Nullable self-reference with `ON DELETE SET NULL`. |
| `queue_job_id` | Nullable queue binding. |
| `row_revision` | Positive integer incremented on lifecycle mutation. |

Database checks enforce valid statuses, non-negative progress counts, terminal `finished_at`, and no archive while non-terminal. Output count is read from `scan_outputs`; it is not duplicated on `scans`.

### `scan_inputs`

Immutable one-to-one row with `ON DELETE CASCADE` from Scan:

- `request_json`: one normalized logical request containing ordered requested company IDs, filters, `published_window`, resolved UTC publication cutoff, and total-row cap
- `company_snapshot_json`: ordered execution-safe tracked-company snapshots resolved at creation
- registry snapshot revision or checksum
- input schema revision
- created time

Company snapshot includes only registry fields required for execution and inspection: stable company ID, display name, provider ID, canonical public careers URL, registry row revision, and provider-safe retrieval configuration. Secrets are forbidden; only credential handles may appear when a future provider requires them.

### `scan_outputs`

Immutable optional one-to-one row with `ON DELETE CASCADE` from Scan:

- `output_json` containing canonical JSON array
- `record_count`
- `byte_length`
- `sha256`
- `media_type`
- canonical schema revision
- created time

An immutable-update trigger rejects output mutation. Service transaction inserts output and marks Scan succeeded together.

### Existing `process_events`

No new Scan event table. Use existing generic events with `process_type = "scan"`.

### `run_scan_inputs`

Immutable ordered relation:

| Column | Contract |
|---|---|
| `run_id` | Foreign key to Run with `ON DELETE CASCADE`. |
| `ordinal` | Positive selection order, unique per Run. |
| `scan_id` | Foreign key to Scan with `ON DELETE RESTRICT`. |
| `output_sha256` | Scan output identity copied at Run creation. |
| `record_count` | Scan output count copied at Run creation. |
| `created_at` | UTC relation time. |

Primary key is `(run_id, ordinal)` and `(run_id, scan_id)` is unique.

Existing `run_inputs` remains the Run job snapshot SSOT. No upload-provenance or combined-input table is added; `jobs_input_manifest_json` owns descriptive source provenance while `run_scan_inputs` owns relational Scan references.

### Existing Idempotent Actions

Reuse existing idempotent-action persistence for Scan create, cancel, Run Again, Archive, Unarchive, and delete commit. No Scan-specific idempotency table is permitted. Scan create uses the reserved action row as the crash-recovery SSOT: its provisional response stores `scan_id` in the same transaction as Scan creation while action status remains pending, and its final response is completed only after enqueue succeeds or the Scan is terminalized with `scan_enqueue_failed`.

## State Transitions

### Execution State Machine

| From | Trigger | To | Required effect |
|---|---|---|---|
| none | valid create request | `queued` | persist Scan and immutable input snapshot before enqueue |
| `queued` | worker claims work | `running` | atomic compare-and-swap; set `started_at` once; duplicate claimant performs no provider work and writes no event or output |
| `queued` | enqueue fails | `failed` | set terminal failure `scan_enqueue_failed` |
| `queued` | cancel accepted | `cancelling` | record cancellation request and prevent duplicate action |
| `running` | cancel accepted | `cancelling` | record cancellation request; worker stops at safe boundary |
| `cancelling` | cancellation observed | `cancelled` | set `finished_at`; store no output |
| `running` | valid output transaction commits | `succeeded` | store output, manifest, count, and `finished_at` atomically |
| `running` | acquisition or output failure | `failed` | persist stable safe failure and `finished_at`; store no output |
| `cancelling` | unrecoverable execution failure | `failed` | persist failure when cancellation cannot complete safely |

Terminal statuses are `succeeded`, `failed`, and `cancelled`. Terminal execution status never changes. Retry is represented by a new Scan through Run Again.

### Archive State Machine

Archive is orthogonal to execution:

| From | Trigger | To | Guard |
|---|---|---|---|
| Active | Archive | Archived | execution is terminal and revision matches |
| Archived | Unarchive | Active | execution is terminal and revision matches |
| Archived | Delete | removed | preview valid and no Run references Scan |

Execution and archive transitions never occur in one ordinary user action. A Scan cannot be archived while queued, running, or cancelling.

## Error Contract

| HTTP | Code | When | Retryable |
|---:|---|---|---|
| 422 | `validation_failed` | malformed fields, invalid bounds, missing both Run job sources, duplicate lifecycle selection IDs, or missing Idempotency-Key | false |
| 409 | `tracked_company_duplicate` | canonical careers URL already exists in registry | false |
| 422 | `unsupported_provider_url` | proposed careers URL matches no admissible provider or matches ambiguously | false |
| 502 | `company_verification_failed` | supported public portal cannot pass bounded reachability or shape verification | status-dependent |
| 404 | `scan_not_found` | detail or action targets unknown Scan | false |
| 409 | `company_ids_unavailable` | requested IDs are missing, archived, disabled, or not scannable | false |
| 409 | `scan_action_not_allowed` | action is invalid for current execution or archive state | false |
| 409 | `scan_revision_conflict` | lifecycle action uses stale `expected_revision` | false |
| 409 | `scan_output_not_ready` | output requested before terminal completion | true |
| 409 | `scan_output_unavailable` | failed or cancelled Scan has no output | false |
| 409 | `scan_not_usable` | Run selection includes non-Active, non-succeeded, empty, or integrity-invalid Scan | false |
| 500 | `scan_output_integrity_failed` | stored output bytes do not match manifest during read or Run creation | false |
| 409 | `delete_preview_stale` | delete state, references, or signed preview changed or expired | false |
| 409 | `idempotency_conflict` | key was used for different normalized request | false |
| 422 | `empty_job_input` | a supplied legacy non-managed source resolves to zero canonical jobs | false |
| 503 | `scan_enqueue_failed` | Scan worker could not be queued | true |

### Execution Failure Codes

Provider and output failures occur asynchronously after `POST /scans` succeeds. They do not become later HTTP 502 responses. Scan transitions to `failed`; `GET /scans/{scan_id}` still returns HTTP 200 with failure resource, and Console records same stable code.

| Code | Meaning | Retryable |
|---|---|---|
| `invalid_scanner_request` | immutable company snapshot or central scanner configuration cannot build valid provider request | false |
| `unknown_provider` | tracked company references provider absent from executing registry version | false |
| `unsupported_provider_url` | tracked company URL is not valid for configured provider | false |
| `ambiguous_provider_url` | automatic detection matches multiple providers | false |
| `provider_timeout` | bounded provider deadline elapsed | true |
| `provider_http_error` | provider returned HTTP failure; retryability derives from safe status classification | status-dependent |
| `provider_payload_error` | provider response cannot be parsed or adapted | false |
| `provider_detail_error` | required detail retrieval failed | status-dependent |
| `scan_output_validation_failed` | merged provider jobs fail canonical output contract | false |
| `scan_enqueue_failed` | persisted Scan could not be queued | true |

Execution failure messages include safe provider and company context but never response bodies, credentials, query secrets, or internal stack traces.

Batch lifecycle conflicts include safe structured `data` listing missing, blocked, and stale Scan IDs. Field errors retain stable field paths so UI can focus invalid controls.

## UI State Intent

Durable UI invariants are:

- Scans workspace uses Active and Archived tabs with URL-owned tab and pagination state; provider-independent list search and status filters remain API capabilities, not duplicate V1 workspace controls
- one list selection model supports one or many Scans
- Active selection exposes Archive only when every selected capability allows it
- Archived selection exposes Unarchive and Delete; Delete always previews first
- Scan Details uses server capabilities for Cancel, Run Again, Download JSON, Archive, and Unarchive
- Console uses Scan events and explicit loading, retry, empty, polling, cancellation, and terminal states
- Scan Output Table and JSON are two views of one immutable output, never separately edited or cached as competing truth
- New Scan uses one Tracked Companies summary field with Manage, searchable native multi-selection, and verified Add Company
- Published At uses the six predefined windows owned by this contract
- Run creation shows upload and eligible Scan outputs as independent optional controls, requires at least one, and supports ordered multiple Scan selection

## Invariants and Edge Cases

### Invariants

- company registry resolution occurs before any external fetch
- provider URL, redirect, TLS, timeout, request-cap, and response-size controls remain mandatory Option C behavior
- Scan request cannot override transport security or provider routing
- output and event payloads are bounded by existing scanner and process-event limits
- exact output integrity is checked before download and Run snapshot creation
- provider or required-detail failure never becomes successful partial output; warnings are limited to non-fatal conditions that preserve complete trustworthy acquisition
- Run source resolution validates every supplied source before atomically creating one snapshot and its provenance
- database foreign keys and transaction boundaries protect Run provenance and deletion safety
- cancellation is cooperative; it prevents output commit after cancellation is observed

### Edge Cases

- empty or minimal input: Scan requires at least one company; successful no-match output is `[]`; empty Scan is not usable for Run; managed Run creation requires upload, Scan IDs, or both
- normal and large input: one global 200-row cap bounds output; Table pagination derives from same JSON
- duplicate, missing, malformed, or unsupported data: request lists normalize where specified; unavailable companies fail before network; malformed canonical output fails whole Scan
- retry, cancellation, timeout, partial failure, or concurrency: pending idempotent-action replay returns or resumes one Scan; stable queue identity prevents duplicate enqueue; one atomic worker claim wins; cancellation commits no output; any selected-company failure fails whole Scan; concurrent Scans share no mutable execution state
- migration or mixed-version state: historical Runs need no Scan relation; legacy source modes remain callable during migration; Run snapshots remain executable without original provider, registry, or Scan availability
- generated-source consistency: frontend consumes canonical contract owners and copies no provider or job schema
- security or accessibility boundary: user cannot submit arbitrary URLs or transport controls; actions use server capabilities; UI preserves keyboard, focus, contrast, zoom, and responsive behavior

## Validation Plan

### Acceptance Criterion: Verify and Add Tracked Company

- setup: provider registry fixtures contain supported, unsupported, duplicate, unreachable, and malformed public careers URLs
- action: verify each proposal, create supported company, then list tracked companies
- expected: verification writes nothing; create repeats verification, persists one active scannable row, returns provider-derived identity, and makes the company selectable without repository-file changes
- failure condition: unsupported or unsafe URL reaches transport, duplicate row is created, client-supplied provider identity is trusted, or failed verification mutates registry
- proof method: API, provider-boundary, and SQLite persistence tests
- expected evidence: stable errors for invalid cases and one restart-persistent tracked-company resource for success

### Acceptance Criterion: Create One, Multiple, and All

- setup: registry fixtures contain active scannable, archived, disabled, and unsupported companies
- action: submit selected one, selected multiple, and all requests
- expected: same endpoint validates, resolves, snapshots, queues, and orders every admissible case; unavailable selections fail before network access
- proof: API and store tests with captured immutable snapshots

### Acceptance Criterion: Idempotent Retry Reuses One Scan

- setup: inject stops after action reservation, after Scan transaction commit, and after queue submission but before final response; also invoke the same worker twice
- action: retry the same normalized request with the same `Idempotency-Key` and fingerprint
- expected: one Scan ID, one stable queue job ID, one `queued` to `running` claim, no duplicate provider request, and the same final response; a different fingerprint returns `idempotency_conflict`
- failure condition: retry creates another Scan, duplicate worker performs acquisition, or a pending action cannot recover
- proof method: route, SQLite transaction, queue, and worker concurrency tests
- expected evidence: one Scan row, one input row, at most one output row, and one winning worker claim across every injected stop point

### Acceptance Criterion: Publication Windows Stay Stable

- setup: jobs contain full timestamps, date-only values, missing dates, and values on both sides of every supported window cutoff
- action: create Scans for `any`, 12 hours, 24 hours, 7 days, 30 days, and 180 days, then Run Again after time advances
- expected: each Scan stores requested window and one immutable UTC cutoff; timestamps compare exactly, date-only values use cutoff-date inclusion, missing dates pass only for `any`, and Run Again resolves a fresh cutoff
- failure condition: worker uses current time after creation, client supplies arbitrary cutoff, or original Scan snapshot changes
- proof method: deterministic clock-controlled filtering and snapshot tests
- expected evidence: repeatable accepted job IDs and immutable stored request values

### Acceptance Criterion: Successful Empty Scan

- setup: providers return no matching jobs
- action: complete Scan, open details, download output, then attempt Run creation
- expected: Scan is `succeeded`, output is exact `[]`, Download is enabled, `use_for_run` is false, and explicit Run selection returns `scan_not_usable`
- proof: output integrity and Run contract tests

### Acceptance Criterion: Output Views Share One Artifact

- setup: successful Scan contains more than one UI page of jobs
- action: inspect Table, JSON, and downloaded file
- expected: same count, order, values, SHA-256, and canonical bytes; Table pagination creates no second persisted job truth
- proof: API tests plus browser network and visible-state evidence

### Acceptance Criterion: Run Uses Immutable Copies

- setup: provide one valid upload and select multiple successful non-empty Scans
- action: create combined Run, then archive selected Scans
- expected: Run snapshot contains upload rows first and Scan rows in selection order, preserves each source order, records upload and ordered Scan provenance, and executes without rereading source artifacts
- proof: persistence and worker replay tests

### Acceptance Criterion: Run Persistence Failure Leaves No Orphan

- setup: valid managed Run sources pass resolution and filesystem projection succeeds, then Candidate Profile or SQLite bundle persistence fails before commit
- action: submit managed Run creation
- expected: no Run, Run input, Run job, or `run_scan_inputs` row exists and the newly materialized filesystem projection is deleted
- failure condition: orphan projection remains, partial database rows commit, or pipeline queueing begins
- proof method: injected persistence-failure route and filesystem assertions
- expected evidence: unchanged Run tables, absent projection path, and no queue submission

### Acceptance Criterion: Managed Run Requires One Job Source

- setup: valid Candidate Profile exists and no upload or Scan ID is supplied
- action: submit managed multipart Run request
- expected: response is HTTP 422 `validation_failed` with job-source field error and no Run or provenance row
- failure condition: request reaches canonicalization, returns `empty_job_input`, or creates partial persistence
- proof method: route and transaction tests
- expected evidence: stable validation response and unchanged Run tables

### Acceptance Criterion: Provider Failure Is Atomic

- setup: one selected company succeeds and another has listing, required-detail, timeout, or malformed-payload failure
- action: execute Scan
- expected: Scan becomes `failed`, output row is absent, completed work remains diagnostic events only, and no successful partial output is selectable
- failure condition: Scan succeeds with incomplete jobs or warning hides failed required acquisition
- proof method: worker failure-path and persistence tests
- expected evidence: one failed Scan, zero output rows, and safe bounded failure events

### Acceptance Criterion: Referenced Delete Is Blocked

- setup: Archived Scans include referenced and unreferenced records
- action: preview and commit delete
- expected: referenced IDs are blocked, stale commit deletes nothing, eligible unreferenced commit succeeds, and database restriction prevents bypass
- proof: store transaction and API preview tests

### Acceptance Criterion: State and Actions Stay Symmetric

- setup: Scans cover every execution and archive state
- action: list and inspect capabilities, invoke single and bulk actions
- expected: same server-derived capability rules control workspace and details; invalid batch rejects atomically; Run Again always creates a new Scan
- proof: state-table parameterized tests and frontend state tests

### Acceptance Criterion: Provider Expansion Is Isolated

- setup: add one admissible provider and tracked company
- action: trigger selected and all Scans
- expected: no Scan API, data model, UI state, Run integration, or persistence branch changes
- proof: changed-file review plus provider and managed-Scan contract suites

## Completion Criteria

Specification is implemented when:

1. tracked-company list, verification, create, persistence, errors, and provider-registry boundary match this contract
2. managed Scan API, publication windows, persistence, events, output, errors, transitions, pending idempotent replay, and single-winner worker claim match this contract
3. direct user entry of provider, company name, and careers URL is absent from V1 Scan creation
4. successful `[]` output is downloadable but has `use_for_run = false`
5. managed Run creation accepts upload, ordered usable Scan IDs, or both, records protected deterministic provenance atomically, and removes its staged filesystem projection when database persistence fails
6. missing both managed Run sources returns `validation_failed`; unusable selected Scan returns `scan_not_usable`
7. provider and required-detail failures create no successful partial Scan output
8. Active and Archived list/detail actions derive from one capability contract
9. frontend, backend, browser, accessibility, and responsive evidence passes
