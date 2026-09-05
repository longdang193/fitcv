---
artifact_type: spec
status: approved
template_id: draft-specification
layer: change
name: fitcv-run-history-api-ownership
related_features:
  - run-history
  - pipeline-console
  - normalized-control-plane
  - frontend-backend-integration
---

# FitCV Run History API Ownership

## Goal and Scope

- problem or opportunity: Run history has two persistence families and two event paths. `local_pipeline_runs` and `local_pipeline_run_events` remain beside normalized `pipeline_runs`, `run_inputs`, `run_stage_executions`, `run_jobs`, and `process_events`. Normalized list/detail reads can make legacy rows unreachable; append and read can use different event stores; search and counts differ by path; backend nested pagination conflicts with frontend flat fields.
- affected users or systems: FitCV frontend Run History, Run Details, Pipeline Results, Console, legacy admin routes, `ControlPlaneStore`, SQLite migrations, workers, and operators inspecting historical runs.
- desired outcome: one backend-owned run-history contract with one canonical persistence family, one event SSOT, deterministic filters/counts, exact cursor behavior, and one frontend adapter contract.
- included scope: ownership matrix, canonical resource schemas, list/detail/jobs/events behavior, search and count rules, idempotent legacy backfill, compatibility/deprecation policy, failure behavior, rollout/rollback, and acceptance tests.
- excluded scope: implementation files, migration scripts, generated schemas, frontend code, database changes, configuration changes, test code, UI redesign, event retention changes, and deletion of legacy tables.

## User Flow and Business Rules

### User or System Flow

1. Client requests `GET /runs`, optionally with lifecycle, search, and page parameters.
2. Backend queries canonical `pipeline_runs` and owned projections, applies filters before pagination, and returns one collection envelope.
3. Client selects a Run and requests `GET /runs/{run_id}`; backend returns canonical Run state, immutable input summary, six stage resources, counts, warnings, and capabilities.
4. Client requests jobs or events. Jobs use page-number pagination. Events use an opaque forward cursor over immutable `process_events`.
5. Worker records lifecycle events through canonical append. Compatibility callers delegate to the same append path.
6. Backfill reconciles legacy rows into canonical rows using stable IDs and source fingerprints. Re-running backfill produces no duplicates and never overwrites canonical rows.

### Business Rules

- `pipeline_runs` owns Run lifecycle and identity. `run_inputs` owns immutable input/profile/settings snapshots. `run_stage_executions` owns six stage rows. `run_jobs` owns stable per-input job identity. `process_events` owns immutable Run chronology.
- Legacy tables are migration sources only. Canonical API reads do not query `local_pipeline_runs` or `local_pipeline_run_events` after read cutover.
- No write path updates legacy and normalized stores as independent truths.
- Incomplete historical data remains reachable with explicit unknown/legacy markers; it is never filled from current settings, profiles, jobs, or runtime state.
- Search and counts run over one identical filtered dataset definition. Pagination never changes count values.
- Event order is stable by `(recorded_at ASC, event_id ASC)`. Cursor is exclusive.
- Clients treat IDs as opaque strings and do not parse cursor contents.

## UI Intent and Known States

- target platform: FitCV web frontend consuming JSON APIs.
- intended interaction: Run list supports active/archived/all tabs, search, page navigation, and selection. Run detail supports stage and job inspection. Console supports incremental event loading with a cursor.
- loading: preserve prior valid page while refreshing; show pending state for first load and inline refresh for later loads.
- empty: distinguish no Runs from no matches after search; distinguish no events from event history unavailable.
- success: render only canonical resources; do not reconstruct lifecycle or counts from artifacts, HTML, legacy blobs, or event messages.
- error: render standard `error` envelope message and `action`; retain prior data when safe; allow retry for `retryable=true` failures.
- disabled: disable next-page/load-more controls when exhausted; prevent duplicate same-request submissions.
- accessibility or responsive intent: preserve semantic controls, keyboard navigation, visible focus, status announcements, and responsive rendering for long names, messages, and payloads.
- durable design-system owner: existing FitCV frontend design system; this specification owns transport state, not visual styling.

## Assumptions and Open Questions

### Verified Facts

- `docs/architecture.md` identifies normalized control-plane ownership and states that `process_events` is Console chronology SSOT.
- `docs/api.md` defines `/runs`, `/runs/{run_id}`, `/runs/{run_id}/stages`, `/runs/{run_id}/jobs`, and `/runs/{run_id}/events`, with nested collection pagination and cursor event pagination.
- `src/fitcv_cp/sqlite_store.py` still creates and reads `local_pipeline_runs` and `local_pipeline_run_events` while also creating normalized tables.
- `src/fitcv_cp/sqlite_store.py` contains legacy event migration into `process_events`, but compatibility helpers still expose separate legacy event append/read behavior.
- `frontend/src/features/runs/api.ts` accepts nested and flat pagination fields and derives `total_items` from several aliases. `frontend/src/features/runs/types.ts` exposes flat internal pagination fields.
- Normalized Run search currently covers Run ID/name while legacy fallback covers a different set. Normalized and legacy job paths also lack one documented search/count contract.

### Approved Lean Personal-Use Decisions

- Legacy Run and event backfill is idempotent.
- `pipeline_runs`, `run_inputs`, `run_stage_executions`, `run_jobs`, and `process_events` are sole canonical owners.
- Orphan events are quarantined with durable migration status.
- Page-number collections use nested `data`/`page`/`meta` envelopes; one frontend adapter normalizes transport once.
- Search covers Run ID, Run name, input filename, and profile identity.
- Active/archive counts apply search.
- Legacy readers remain read-only until one successful backfill proves zero unmigrated rows and focused tests pass; separate cleanup follows.
- No enterprise, multi-tenant, telemetry, or calendar-sunset requirements.

## Prototype and Validation Findings

- prototype reference: existing FitCV Run History, Run Details, Pipeline Results, and Console routes documented in `docs/api.md`; no new visual prototype required.
- UX approval: Approved for transport semantics; no visual design changes required.
- design export evidence or Not required: Not required: this is API ownership and transport semantics, not visual design.
- scenario tested: review findings compared legacy and normalized persistence, append/read event paths, search/count behavior, backend collection envelopes, and frontend parsers.
- observed result: legacy rows can remain beside normalized rows without canonical list/detail reachability; event append and event reads can split; search fields and count scopes vary; backend nested pagination and frontend flat fields are both accepted.
- accepted behavior: one canonical read/write owner, resumable idempotent backfill, deterministic search/count rules, nested backend collection envelope plus one frontend normalization boundary, and cursor-only event traversal.
- rejected behavior: permanent dual-read truth, permanent dual-write truth, frontend fallback to legacy rows, backend response aliases without sunset, page-number pagination for append-only events, and counts derived from visible page length.
- remaining uncertainty: None for approved lean personal-use scope.
- boundary implication when material: shared contract and data/state boundaries are affected; backend proof must exercise direct HTTP/API behavior and durable SQLite state before frontend proof is accepted.

## API Ownership and Contract

### Ownership Matrix

| Resource or behavior | Canonical owner | Read responsibility | Write responsibility | Forbidden owner overlap |
|---|---|---|---|---|
| Run identity/lifecycle | `pipeline_runs` and Run lifecycle registry | Run list/detail/action projections | Trigger and lifecycle transitions | Legacy JSON blob as lifecycle truth |
| Immutable Run input | `run_inputs` | Detail input summary | Trigger-time snapshot only | Current settings/profile reconstruction |
| Stage execution | `run_stage_executions` | Detail and stages projection | Worker/stage transition boundary | Event message as stage state |
| Run job identity | `run_jobs` | Jobs list/detail/export projections | Trigger-time stable IDs and job updates | Source URL as primary job identity |
| Job stage outcome | `run_job_stage_results` | Job status/outcome projection | Stage result boundary | Recomputed UI-only status as durable truth |
| Run chronology | `process_events` | Events endpoint and Console | One append boundary with fingerprint/idempotency | `local_pipeline_run_events` as read/write SSOT |
| Legacy compatibility | Compatibility adapter layer | Only where explicitly documented | No new legacy persistence | Legacy tables as fallback after cutover |
| Frontend pagination state | Frontend API adapter | Normalize canonical response once | URL/local UI state only | Frontend deciding backend totals or lifecycle |

### Common Types

```json
{
  "RunStatus": ["queued", "running", "awaiting_continue", "cancelling", "cancelled", "succeeded", "failed"],
  "RunLifecycle": ["active", "archived", "all"],
  "RunStageId": ["enrichment", "screening", "shortlisting", "ranking", "cv-analysis", "cv-generation"],
  "RunStageStatus": ["pending", "running", "succeeded", "warning", "partial", "failed", "cancelled", "skipped"],
  "JobStageStatus": ["pending", "passed", "rejected", "blocked", "skipped", "failed", "review_required", "generated"],
  "ResultBucket": ["passed", "rejected", null],
  "EventLevel": ["info", "warning", "error"]
}
```

All timestamps are RFC 3339 UTC strings. All identifiers are non-empty opaque strings. Nullable fields use JSON `null`, not omitted values, when the schema declares them nullable. Unknown top-level fields are not public contract; extensibility belongs inside `attributes`, `payload`, `diagnostic_refs`, or `links`.

### Run Resource

`RunResource` is used by list and detail, with `input` and `stages` omitted from list items and present in detail.

```json
{
  "run_id": "run_123",
  "run_name": "jobs-2026-09-05",
  "backend_status": "succeeded",
  "display_status": "Succeeded",
  "status_detail": null,
  "created_at": "2026-09-05T10:00:00Z",
  "started_at": "2026-09-05T10:00:02Z",
  "finished_at": "2026-09-05T10:03:00Z",
  "archived_at": null,
  "counts": {"total": 10, "passed": 4, "rejected": 5, "skipped": 1, "cvs_generated": 3},
  "progress": {"completed": 10, "total": 10},
  "warnings": {},
  "errors": {"code": null, "message": null},
  "partial_completion": false,
  "input": null,
  "stages": [],
  "capabilities": {"inspect": true, "cancel": false, "archive": true, "unarchive": false, "delete": false, "export": true},
  "integrity_warnings": [],
  "debug_bundle": {"run_id": "run_123", "status": "available", "reason": null, "action": null},
  "links": {"self": "/runs/run_123", "jobs": "/runs/run_123/jobs", "events": "/runs/run_123/events"}
}
```

Field rules:

- list items include `run_id`, `run_name`, `backend_status`, `display_status`, timestamps, `counts`, `progress`, `warnings`, `errors`, `partial_completion`, `capabilities`, `integrity_warnings`, `debug_bundle`, and `links`; list items omit `input` and `stages`.
- detail includes all fields and supplies `input` plus exactly six `stages`, ordered by `ordinal` 1 through 6.
- `errors` is an object with nullable `code` and `message`; it is not an error envelope.
- `integrity_warnings` reports stored-versus-recomputed conflicts without silently changing stored state.

### Run Input Summary

```json
{
  "run_id": "run_123",
  "original_filename": "jobs.jsonl",
  "media_type": "application/jsonl",
  "byte_length": 2048,
  "sha256": "hex_sha256",
  "record_count": 10,
  "jobs_input_source": "upload",
  "jobs_input_manifest": {},
  "candidate_profile": {
    "profile_id": "profile_1",
    "revision_id": "profile_revision_1",
    "revision": 2,
    "schema_version": "candidate_profile_v2",
    "checksum": "hex_sha256",
    "name": "Data Engineering",
    "availability": "historical_snapshot"
  },
  "settings_revision": "settings_2026_09_05",
  "sources": [{"type": "upload", "filename": "jobs.jsonl", "record_count": 10, "sha256": "hex_sha256", "byte_length": 2048}],
  "legacy": {"is_backfilled": false, "unknown_fields": []}
}
```

`RunInputSummary` is a public projection. Raw private snapshot JSON is not returned unless an existing authorized artifact route owns it.

### Stage Resource

```json
{
  "stage_id": "screening",
  "label": "Screening",
  "ordinal": 2,
  "status": "succeeded",
  "progress": {"completed": 10, "total": 10},
  "started_at": "2026-09-05T10:00:10Z",
  "finished_at": "2026-09-05T10:01:00Z",
  "duration_ms": 50000,
  "warnings": {},
  "error": {"code": null, "message": null},
  "results_available": true,
  "recomputed_counts": {"passed": 4, "rejected": 6},
  "legacy": {"is_derived": false, "source": null}
}
```

### Job Resource

```json
{
  "run_job_id": "run_job_123",
  "job_id": "job_123",
  "title": "Senior Data Engineer",
  "company": "Example Co",
  "location": "Remote",
  "source_url": "https://example.test/jobs/123",
  "current_stage_id": "ranking",
  "status": "passed",
  "result_bucket": "passed",
  "bookmarked": false,
  "bookmark_id": null,
  "interest_rating": null,
  "cv_versions_count": 1,
  "latest_cv_generation_status": "generated",
  "latest_cv_review_state": "none",
  "attributes": {},
  "capabilities": {"bookmark": true, "interest": true, "cv_view": true, "cv_generate": true}
}
```

`JobResource` exposes stable public fields only. Source snapshots, evidence, and stage-specific detail remain under explicit fields or dedicated routes; raw normalized table columns are not transport schema.

### Event Resource

```json
{
  "event_id": "event_123",
  "time": "2026-09-05T10:00:10Z",
  "stage_id": "screening",
  "level": "info",
  "operation": "screening",
  "state": "completed",
  "message": "Screening completed.",
  "payload": {},
  "diagnostic_refs": {}
}
```

Event `payload` and `diagnostic_refs` are sanitized bounded JSON objects. Event resources never expose credentials, raw source bytes, or unsanitized exception content.

## Endpoint Contracts

### `GET /runs`

Query:

- `view`: `active|archived|all`, default `active`.
- `search`: optional UTF-8 string, trimmed and Unicode-normalized.
- `page`: integer `>=1`, default `1`.
- `page_size`: `10|20|50`, default `20`.

Response:

```json
{
  "data": [{"run_id": "run_123", "run_name": "jobs-2026-09-05", "backend_status": "succeeded", "display_status": "Succeeded", "created_at": "2026-09-05T10:00:00Z", "started_at": "2026-09-05T10:00:02Z", "finished_at": "2026-09-05T10:03:00Z", "archived_at": null, "counts": {"total": 10, "passed": 4, "rejected": 5, "skipped": 1, "cvs_generated": 3}, "progress": {"completed": 10, "total": 10}, "warnings": {}, "errors": {"code": null, "message": null}, "partial_completion": false, "capabilities": {"inspect": true, "cancel": false, "archive": true, "unarchive": false, "delete": false, "export": true}, "integrity_warnings": [], "debug_bundle": {"run_id": "run_123", "status": "available", "reason": null, "action": null}, "links": {"self": "/runs/run_123", "jobs": "/runs/run_123/jobs", "events": "/runs/run_123/events"}}],
  "page": {"number": 1, "size": 20, "total_items": 1, "total_pages": 1},
  "meta": {"active_count": 1, "archived_count": 0, "view": "active", "search": "", "server_time": "2026-09-05T10:05:00Z"}
}
```

`page.total_items` counts rows matching `view` and `search`. `meta.active_count` and `meta.archived_count` count rows matching `search` before `view`. `total_pages` is `0` when `total_items` is `0`; otherwise it is the ceiling of `total_items / page.size`.

### `GET /runs/{run_id}`

Response is `{"data": RunResource}` with detail fields and exactly six stages. Missing Run returns standard `run_not_found` error envelope.

### `GET /runs/{run_id}/stages`

Response is `{"data": [StageResource, ...]}`. Data contains exactly six resources in ordinal order. This endpoint is not page-number paginated.

### `GET /runs/{run_id}/jobs`

Query:

- `page`: integer `>=1`, default `1`.
- `page_size`: `10|20|50`, default `10`.
- `search`: optional normalized substring search.
- `stage`: `all|enrichment|screening|shortlisting|ranking|cv-analysis|cv-generation`, default `all`.
- `result_bucket`: `all|passed|rejected`, default `all`.

Response:

```json
{
  "data": [{"run_job_id": "run_job_123", "job_id": "job_123", "title": "Senior Data Engineer", "company": "Example Co", "location": "Remote", "source_url": "https://example.test/jobs/123", "current_stage_id": "ranking", "status": "passed", "result_bucket": "passed", "bookmarked": false, "bookmark_id": null, "interest_rating": null, "cv_versions_count": 1, "latest_cv_generation_status": "generated", "latest_cv_review_state": "none", "attributes": {}, "capabilities": {"bookmark": true, "interest": true, "cv_view": true, "cv_generate": true}}],
  "page": {"number": 1, "size": 10, "total_items": 1, "total_pages": 1},
  "meta": {"run_id": "run_123", "stage": "all", "result_bucket": "all", "search": "", "total_evaluated": 10, "passed": 4, "rejected": 5, "skipped": 1}
}
```

`page.total_items` counts rows matching Run, search, stage, and result bucket. `meta.total_evaluated`, `passed`, `rejected`, and `skipped` count rows matching Run, search, and stage before `result_bucket`. Ordering is `title` case-insensitively ascending, then `run_job_id` ascending.

### `GET /runs/{run_id}/events`

Query:

- `cursor`: optional opaque cursor returned by prior response.
- `limit`: integer `1..500`, default `100`.

Response is cursor-only and does not use page-number fields:

```json
{
  "data": [{"event_id": "event_123", "time": "2026-09-05T10:00:10Z", "stage_id": "screening", "level": "info", "operation": "screening", "state": "completed", "message": "Screening completed.", "payload": {}, "diagnostic_refs": {}}],
  "meta": {"run_id": "run_123", "limit": 100, "cursor": null, "next_cursor": null, "total_count": 1, "integrity_conflicts": 0}
}
```

Events select `process_type="pipeline"` and `process_id=run_id`, ordered ascending by `(recorded_at, event_id)`. `next_cursor` is null at end. Cursor is exclusive and invalid/mismatched cursors return `422 validation_failed`. `total_count` is query-time count and may increase as events append; it is not a page count.

## Search and Count Semantics

### Normalization

1. Decode query as UTF-8.
2. Apply Unicode NFKC normalization.
3. Trim leading/trailing whitespace.
4. Case-fold for comparison.
5. Empty normalized query means no search predicate.
6. Matching uses substring semantics, not token, prefix, fuzzy, or relevance ranking.

### Run Search Fields

Search matches any of these public values:

- `run_id`
- `run_name`
- `input.original_filename`
- `input.jobs_input_source`
- `input.candidate_profile.name`
- each `input.sources[].filename`
- each `input.sources[].scan_id`
- each `input.sources[].scan_name`

Search excludes event messages, private snapshots, artifact contents, current settings, and HTML.

### Job Search Fields

Search matches any of these public values:

- `run_job_id`
- `job_id`
- `title`
- `company`
- `location`
- `source_url`
- display skill labels from the canonical job skill projection

Search excludes arbitrary serialized JSON, event messages, CV contents, and private evidence.

### Count Invariants

- Every `total_items` equals count after all endpoint filters and before `LIMIT/OFFSET`.
- Run tab counts use search but ignore selected `view`.
- Job facet counts use search and stage but ignore selected `result_bucket`.
- Event `total_count` counts all matching immutable events at query time; cursor does not change its definition.
- Empty pages beyond last page return `data: []` with computed counts; backend does not silently move page number.
- Counts are integers and never use visible array length as fallback in canonical responses.

## Event Append and Read Ownership

- Canonical append input is a `ProcessEvent` with `schema_version`, `event_id`, `process_type`, `process_id`, `operation`, `state`, `level`, `message`, sanitized payload/diagnostic/trace JSON, `recorded_at`, and `event_fingerprint`.
- `event_id` is the idempotency key for insertion. Same ID and same fingerprint is an equal no-op. Same ID and different fingerprint creates an integrity conflict and does not overwrite the original.
- Canonical read returns only `process_events` plus recorded integrity conflicts. Journal replay is an implementation detail of this owner, not a second API source.
- Compatibility `RunEvent` append converts once to `ProcessEvent` with `process_type="pipeline"`, `process_id=run_id`, `operation=stage`, and `state="recorded"` when legacy callers lack state. It then uses canonical append.
- Compatibility `get_events` converts canonical events to its historical object shape for explicitly retained callers. It never reads `local_pipeline_run_events`.
- `local_pipeline_run_events` is backfill input only. New writes stop before read cutover.

## Idempotent Legacy Backfill

### Source Scope

- Source runs: every row in `local_pipeline_runs` with stable non-empty `run_id`.
- Source events: every row in `local_pipeline_run_events`, including events whose Run row is missing; orphan events are quarantined with durable migration status and are not promoted to canonical Run history.
- Existing normalized rows remain canonical and are never replaced by legacy rows.

### Source Fingerprints

- Run fingerprint: SHA-256 of canonical JSON containing source table, `run_id`, `created_at`, and exact `run_json` bytes.
- Event fingerprint: existing `event_fingerprint` when available; otherwise SHA-256 of canonical JSON containing source table, `run_id`, `event_id`, `stage`, `level`, `message`, `payload_json`, and `created_at`.
- Migration ledger records `migration_id`, source table, source row identity, source fingerprint, disposition, canonical ID, error code, and timestamps.

### Transformation Rules

- Valid legacy Run JSON maps to `pipeline_runs` identity/lifecycle fields and stores unmapped historical fields under `compatibility_json.legacy_run`.
- Legacy input fields map to `run_inputs` immutable snapshot fields. Missing values use explicit historical unknown markers, never current settings or profile values.
- Backfilled Run receives six `run_stage_executions` rows. Known `completed_stages` map to `succeeded`; known current/next stage maps to `running` only when source status proves active execution; unproven stage state maps to `pending` for non-terminal history or `skipped` with `legacy.is_derived=true` for terminal history.
- Existing normalized `run_jobs` are preserved. Legacy job arrays are inserted only when no canonical job with same `(run_id, source_index)` or source fingerprint exists. Duplicate source records remain distinct when source indices differ.
- Legacy events map to immutable `process_events` with `process_type="pipeline"`, `process_id=run_id`, `operation=stage`, `state="recorded"`, original level/message/payload, and original timestamp.
- Malformed payload JSON is preserved under `payload.legacy_payload_json`; malformed Run JSON with stable ID becomes degraded compatibility metadata; no row is silently discarded.

### Retry and Conflict Rules

- Backfill is resumable by source row identity and fingerprint.
- Re-running same source row with same fingerprint is a no-op.
- Same source identity with changed fingerprint creates migration conflict and does not overwrite canonical data.
- Same canonical event ID and equal event fingerprint is a no-op; mismatched fingerprint is recorded in `process_event_integrity_conflicts`.
- Backfill commits each Run bundle atomically: Run, input, six stages, eligible jobs, and migration disposition commit together or none commit. Event migration may commit independently because events are immutable and independently keyed.
- Backfill never deletes or mutates legacy source rows.
- Completion requires source counts, inserted/equal/conflict/degraded counts, and source fingerprint queryable from migration status.

## Compatibility and Deprecation Policy

### Compatibility Window

1. **Prepare:** canonical schema and migration capability exist; legacy rows remain untouched.
2. **Backfill:** stable legacy runs/events reconcile; parity report records conflicts and degraded rows.
3. **Dual observation:** canonical endpoints serve normalized rows only; operators compare legacy and canonical reports outside request handling.
4. **Read cutover:** `/runs*` and Console read canonical stores only. Legacy routes delegate to canonical projections where behavior overlaps.
5. **Write cutover:** all new Run and event writes target normalized stores only.
6. **Deprecation:** retain legacy readers as read-only until one successful backfill proves zero unmigrated rows and focused tests pass.
7. **Removal:** remove legacy readers, then tables, only in separate owner-approved change after exit criteria.

### Legacy API Rules

- Historical `/admin/*` HTML and JSON routes remain compatibility surfaces until separately retired.
- Compatibility routes may adapt canonical resources to historical shapes but may not create new persistence or divergent lifecycle/event truth.
- Canonical `/runs` responses do not include both nested and flat pagination aliases after compatibility sunset.
- Frontend may parse old flat fields during the window, but this is temporary, observable, and removed after sunset.
- Legacy table names must not appear in canonical API response payloads.

### Deprecation Exit Criteria

- Legacy readers remain read-only until one successful backfill proves zero unmigrated rows and focused tests pass; cleanup follows in a separate owner-approved change.
- 100% of stable legacy Run IDs resolve through canonical list/detail according to parity report.
- 100% of legacy event rows are equal, inserted, or explicitly conflicted with durable evidence.
- No production write path records new rows in legacy tables for one full release cycle.
- No canonical endpoint reads legacy tables in route-level and store-level evidence.
- Frontend no longer requires flat/nested dual parsing.
- Owner signs removal approval with rollback snapshot retained.

## Frontend Contract

- Backend owns resource schemas, filter interpretation, ordering, totals, cursors, and error codes.
- Frontend API adapter owns one normalization step from canonical transport to internal types:
  - `payload.data` remains collection data.
  - `payload.page.number` maps to internal `page`.
  - `payload.page.size` maps to internal `page_size`.
  - `payload.page.total_items` maps to internal `total_items`.
  - `payload.page.total_pages` maps to internal `total_pages`.
  - `payload.meta` maps to feature metadata.
  - Event `payload.meta.next_cursor` maps to internal `next_cursor`; event `payload.meta.total_count` maps to internal `total_count`.
- Frontend must not infer totals from `data.length` when canonical total is present or missing. Missing required pagination metadata is contract error, not zero-result success.
- Frontend must not send `stage=all` or `result_bucket=all` when omitting a filter is canonical; recommended default: omit default-valued filters.
- Frontend preserves URL state for Run view, search, page, page size, stage, and result bucket where router support exists.
- Frontend keeps prior data during refresh, resets page to `1` when search/filter changes, and discards stale cursor when Run ID changes.
- Frontend renders `integrity_conflicts` as diagnostic state, not Run failure unless resource `errors` or endpoint error says so.

## Failure Behavior

All failures use existing error envelope:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed.",
    "field_errors": [{"field": "page", "code": "invalid_value", "message": "Use 1 or greater."}],
    "retryable": false,
    "action": "Fix highlighted fields and retry."
  }
}
```

- `400` is reserved for malformed HTTP/request encoding where field-level validation is impossible.
- `404 run_not_found` means no canonical Run exists after read cutover. Request path never falls back to a legacy row.
- `422 validation_failed` covers invalid view, page, page size, stage, result bucket, limit, search encoding, or cursor.
- `409 integrity_conflict` is used for an explicitly requested operation that cannot safely resolve an event or migration conflict. Reads return conflict metadata without rewriting canonical data.
- `409 run_state_conflict` remains for lifecycle action preconditions.
- `503 persistence_unavailable` or existing retryable persistence code is returned when canonical durable write cannot be confirmed. Response must not claim success. If Run reservation persisted before queue failure, return inspectable Run data and failure code.
- Event append fallback to a local journal is allowed only as canonical event durability behavior; reads replay that same journal into canonical event view and expose persistence degradation to operators.
- Database schema incompatibility fails closed with actionable `database_schema_incompatible`; route does not switch to legacy truth silently.
- Backfill failure rolls back current atomic bundle, records failure in migration status when possible, and resumes from source identity on retry.

## Rollout and Rollback

### Rollout

1. Owner approves pagination, count, orphan, and deprecation decisions.
2. Capture database backup and migration source fingerprint.
3. Preflight canonical schema, foreign keys, event immutability, and migration ledger.
4. Run resumable backfill in bounded batches; stop on integrity or schema incompatibility rather than guessing.
5. Compare parity: Run IDs, event IDs, status/timestamp projections, counts, and list/detail/events reachability.
6. Switch canonical reads, then canonical writes; keep legacy readers read-only until approved cleanup criteria pass.
7. Monitor missing Run rate, count mismatches, event conflicts, cursor failures, persistence degradation, and endpoint errors through one release cycle.

### Rollback

- Before write cutover: stop read cutover and resume legacy compatibility reads only for rows not yet canonicalized; preserve canonical backfill rows.
- After write cutover: do not revert to legacy tables, because that recreates split truth. Roll back route code to prior canonical-compatible version or disable only affected operation while retaining normalized writes and reads.
- Data rollback requires owner approval and restore from pre-migration backup. Do not delete canonical or legacy rows as ad hoc rollback.
- Event conflicts, degraded rows, and migration ledger records survive application rollback for diagnosis.
- Legacy table cleanup is never part of rollback.

## Acceptance Tests

### Backend Verification Claims

- direct boundary: exercise `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/stages`, `GET /runs/{run_id}/jobs`, `GET /runs/{run_id}/events`, and canonical event append against real SQLite persistence.
- important success and failure behavior: prove active/archived/all filtering, normalized search, empty results, missing Run, invalid page/filter/cursor, event integrity conflict, schema incompatibility, and persistence failure behavior.
- final state or side effects: assert canonical Run/input/stage/job/event rows; assert no new legacy writes after write cutover; assert integrity conflicts are durable.
- rollback/idempotency behavior: repeat backfill and equal event insertion; compare counts and IDs before/after; changed source fingerprint creates conflict without overwrite.
- canonical contract and conformance proof: verify exact envelopes, required fields, enum values, nullability, order, and nested page versus cursor-only event shape.
- real dependencies requiring proof: use real SQLite transactions, foreign keys, unique IDs, immutable event triggers, and filesystem journal replay when configured.
- representative-operation trace mechanism: trace one Run from trigger, canonical row creation, stage/job updates, event append, list/detail read, cursor read, and terminal state.
- performance claim and threshold: no new target beyond bounded page sizes and event limits; record query behavior for representative and large histories if existing harness supports it.

### Acceptance Criterion: Legacy Runs remain reachable

- setup or precondition: legacy-only Run row exists with complete and incomplete snapshots; no normalized row exists initially.
- action: run backfill twice, then call canonical list/detail/stages/events routes.
- expected result: Run appears once, detail resolves, six stages exist, historical unknown markers are explicit, and second backfill changes no canonical counts.
- failure condition: legacy row remains list-invisible, current settings fill historical nulls, duplicate Run appears, or second run changes canonical data.
- proof method: direct backend boundary plus durable database assertions.

### Acceptance Criterion: Existing canonical rows win conflicts

- setup or precondition: normalized Run/event exists with same ID as changed legacy source.
- action: run backfill.
- expected result: canonical row remains unchanged; migration ledger records equal/conflict disposition and source fingerprint.
- failure condition: legacy JSON overwrites lifecycle, timestamps, input snapshot, or event payload.
- proof method: before/after row and fingerprint comparison.

### Acceptance Criterion: Append/read use one event SSOT

- setup or precondition: append one event through compatibility caller and one through canonical caller.
- action: read pages through `/runs/{run_id}/events` with a cursor.
- expected result: both events appear once in stable order; equal duplicate append is no-op; mismatched duplicate creates durable integrity conflict; `local_pipeline_run_events` is not read.
- failure condition: append succeeds but event is absent from canonical read, duplicate appears, or legacy table diverges.
- proof method: direct append boundary, route response, and SQLite state.

### Acceptance Criterion: Search/count semantics stay stable

- setup or precondition: fixture includes active/archived Runs, matching/nonmatching Run fields, jobs across stages/buckets, and more rows than one page.
- action: query each view/search/stage/result combination and request page 1 plus later page.
- expected result: counts equal full filtered sets; active/archive counts apply search but ignore view; job facet counts apply search/stage but ignore result bucket; order is deterministic.
- failure condition: counts equal visible page length, change by page, differ between legacy/normalized path, or search matches excluded private fields.
- proof method: direct endpoint response compared with independent SQL count query.

### Acceptance Criterion: Frontend consumes one transport shape

- setup or precondition: canonical nested collection response and cursor event response are available.
- action: run Run list, jobs pagination, search reset, and Console load-more flows.
- expected result: adapter produces flat internal fields once; UI sends canonical query parameters; pagination uses backend totals/cursors; no dual-shape fallback is needed after sunset.
- failure condition: UI derives totals from page length, sends stale cursor across Runs, or silently accepts missing pagination metadata.
- proof method: existing frontend contract tests and browser flow evidence; this supplements, never replaces, backend proof.

### Acceptance Criterion: Failure behavior prevents false success

- setup or precondition: induce invalid cursor, missing Run, persistence failure, queue failure, and event fingerprint mismatch.
- action: call affected boundary.
- expected result: standard error envelope has stable code, retryability, and action; durable state reflects only confirmed writes; inspectable failed Run remains inspectable when reservation already committed.
- failure condition: success payload claims unpersisted state, route falls back to legacy silently, or partial migration overwrites data.
- proof method: direct boundary plus final-state assertions and representative trace.

## Promotion Readiness

- owner approval: Approved for lean personal-use scope.
- approval reference: owner approval recorded in this specification on 2026-09-05.
- remaining blockers: None for this specification; implementation plan and schema/route updates follow separately.
- approved deferrals: legacy cleanup remains separate until successful backfill, zero unmigrated rows, and focused tests pass.
- unresolved behavior-changing questions: None within approved scope.
