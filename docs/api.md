---
doc_id: api
doc_type: reference
explains:
  features:
    - inspection_debugging
    - settings_system
    - trigger_run_management
  components:
    - src/fitcv_cp
---

# API

This page documents the stable JSON and download contracts used by the
prototype-defined Settings, Runs, Run Details, and Pipeline Results interface.
Route registration and boundary validation live in `src/fitcv_cp/app.py`;
normalized query behavior lives behind `ControlPlaneStore`.

## Contract Conventions

Single-resource and synchronous action responses use:

```json
{"data": {}}
```

Collections use:

```json
{
  "data": [],
  "page": {
    "number": 1,
    "size": 20,
    "total_items": 0,
    "total_pages": 0
  },
  "meta": {}
}
```

Page numbers start at `1`. Supported page sizes are `10`, `20`, and `50`.
Runs default to `20`; Run jobs default to `10`. Console events use cursor
pagination with `limit=100` by default and allow `1..500`.

Errors use one actionable envelope:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed.",
    "field_errors": [
      {"field": "page", "code": "invalid_value", "message": "Use 1 or greater."}
    ],
    "retryable": false,
    "action": "Fix highlighted fields and retry."
  }
}
```

Stable identifiers are `candidate_profile_id`, `run_id`, `run_job_id`,
`version_id`, `cv_evaluation_id`, `review_event_id`, `bookmark_id`, and
`action_id`. Clients must treat them as opaque strings.

`Idempotency-Key` is required for prototype Run upload trigger, selected
archived deletion, and CV regeneration. Reusing a key with a different request
returns `409 idempotency_conflict`; replaying the same request returns the
stored result.

## Stable Status Values

- Run backend status: `queued`, `running`, `awaiting_continue`, `cancelling`,
  `cancelled`, `succeeded`, `failed`
- Run stage status: `pending`, `running`, `succeeded`, `warning`, `partial`,
  `failed`, `cancelled`, `skipped`
- Job-stage status: `pending`, `passed`, `rejected`, `blocked`, `skipped`,
  `failed`, `review_required`, `generated`
- Result bucket: `passed`, `rejected`
- CV generation status: `pending`, `running`, `generated`, `review_required`,
  `validation_failed`, `generation_failed`, `persistence_failed`, `cancelled`
- CV evaluation status: `pending`, `running`, `succeeded`, `failed`
- CV review state: `none`, `stretch`, `manual_required`, `approved`, `rejected`
- Event level: `info`, `warning`, `error`

Prototype stage IDs and order are fixed:

1. `enrichment`
2. `screening`
3. `shortlisting`
4. `ranking`
5. `cv-analysis`
6. `cv-generation`

Responses expose server-owned `display_status`, `status_detail`, counts,
capabilities, `result_bucket`, and review state. Frontends format timestamps but
do not infer lifecycle or totals.

## Health

### `GET /healthz`

Returns `{"ok": true}` when the service process is available.

### `GET /local/readiness`

Returns `{"ready": bool, "reasons": string[]}`. Profile readiness is true
only when the canonical Candidate Profile store has at least one record with
`creation_status = "succeeded"` and `lifecycle = "active"`; onboarding state
flags and drafts do not count. If local onboarding state or the profile catalog
cannot be read, returns `503` with `error.code =
"local_readiness_unavailable"`, `retryable = true`, and recovery action.

## Pipeline Settings

### `GET /settings/pipeline`

Returns one resource containing `revision`, schema/IA metadata, effective
`values`, `defaults`, source ownership, disabled reasons, warnings, and
validation errors. Response includes an `ETag` containing the revision.

### `PATCH /settings/pipeline`

Body:

```json
{
  "changes": {"pipeline_timeout_minutes": 45},
  "updated_by": "admin",
  "expected_revision": "<sha256>"
}
```

Changes are validated and persisted atomically. Managed groups must be sent as
complete groups. A stale revision returns `409 settings_revision_conflict`.

### `POST /settings/pipeline/actions/reset`

Body:

```json
{
  "keys": ["pipeline_timeout_minutes"],
  "updated_by": "admin",
  "expected_revision": "<sha256>"
}
```

Deletes only listed overrides and reveals packaged defaults. Reset is atomic
and returns the refreshed Settings resource and `ETag`.

`GET /settings` remains a compatibility read surface. Prototype code uses only
the `/settings/pipeline` resource.

### Candidate Profile contract freeze

- `POST /candidate-profile-creation-attempts` stages `.md`, `.docx`, or `.yaml` ingestion. No direct `POST /candidate-profiles` route.
- Sole source-block route: `GET /candidate-profile-creation-attempts/{attempt_id}/source-blocks/{source_block_id}`. Missing attempt or block returns `404`; no profile-level alias.
- Confirming or updating profile data uses immutable successor revisions. Request includes `expected_revision` CAS and ordered review operations. Server uses `converge_candidate_profile_for_runtime()`, validates canonical V2, computes canonical checksum, and writes new `profile_revision_id`; confirmed revisions never overwrite. CAS mismatch returns `409`; malformed references return `422`.
- Success `data` includes `profile_id`, `profile_revision_id`, `revision`, `checksum`, `lifecycle`, `canonical`, and capabilities. Historical revisions and run snapshots remain unchanged.
- Lifecycle allows only `active -> archived` and `archived -> active`; each mutation requires revision CAS. Archived profiles remain resolvable for history but cannot start new profile-selected runs.

#### Run trigger inventory

| Trigger | Contract | Profile rule |
| --- | --- | --- |
| JSON `POST /runs` | Compatibility delegate for historical JSON body | Explicit legacy `default_config` remains supported; profile-selected JSON requires persisted active `profile_id` |
| Managed multipart `POST /runs` | Multipart upload, `Idempotency-Key`, active `profile_id` | Missing, malformed, stale, archived, or disallowed selected profile fails closed |
| `POST /admin/upload-trigger` | Legacy compatibility form; separate `candidate_profile_id` field | Preserves legacy behavior; does not alias managed multipart contract |

Run records persist one authoritative `run_inputs` snapshot at trigger time, including selected profile revision when present. Null or empty legacy snapshots remain historical records and display as such; never backfill from current settings.

### Personalization

`GET /personalization` and `PATCH /personalization` expose only the
completion-critical ranking preference. Responses use the standard `data`
envelope and include `ranking_mode`, `effective_ranking_mode`,
`personalization_strength`, `baseline_fallback`, `active_policy_id`,
`revision`, `bounds`, and `updated_at`. `ETag` equals `revision` in quotes.

`PATCH` requires `ranking_mode`, `expected_revision`, and optional
`personalization_strength` and `updated_by`. Unknown fields are rejected.
Settings CAS failures return `409 personalization_revision_conflict`; invalid
settings return `422 validation_failed`. Optimization history and operator
administration remain outside this JSON resource.


### Field schema

`GET /candidate-profile-field-schema` returns the executable v2 field registry,
including section order, labels, controls, requirements, evidence kinds, and
date grammar. Its checksum owns `ETag`; matching `If-None-Match` returns `304`.

### Staged creation

- `GET /candidate-profile-creation-attempts`
- `POST /candidate-profile-creation-attempts`
- `GET /candidate-profile-creation-attempts/{attempt_id}`
- `GET /candidate-profile-creation-attempts/{attempt_id}/source`
- `GET /candidate-profile-creation-attempts/{attempt_id}/source-blocks/{source_block_id}`

Creation requires `Idempotency-Key` plus multipart `profile_name` and one
non-empty `.md`, `.docx`, or `.yaml` `profile_file`. All formats enter the same
accepted-upload, deterministic extraction, review, approval, and confirmation
lifecycle. Success returns `202`; no direct `POST /candidate-profiles` bypass
exists.

### Review and approval

- `GET|PATCH /candidate-profile-creation-attempts/{attempt_id}/baseline`
- `POST /candidate-profile-creation-attempts/{attempt_id}/baseline/actions/regenerate`
- `POST /candidate-profile-creation-attempts/{attempt_id}/baseline/actions/undo-regeneration`
- `POST /candidate-profile-creation-attempts/{attempt_id}/baseline/actions/approve`
- `GET|PATCH /candidate-profile-creation-attempts/{attempt_id}/derived`
- `POST /candidate-profile-creation-attempts/{attempt_id}/derived/actions/regenerate`
- `POST /candidate-profile-creation-attempts/{attempt_id}/derived/actions/undo-regeneration`
- `POST /candidate-profile-creation-attempts/{attempt_id}/derived/actions/approve`

PATCH uses one attempt CAS revision and ID-addressed `add`, `replace`, or
`remove` operations. Regeneration accepts explicit field or entry targets;
approval requires current revision and stage fingerprint. Baseline approval
queues controlled derivation. Derived approval also binds the approved baseline
fingerprint.

Undo restores only the snapshot retained immediately before the latest completed
regeneration for that review stage. It requires `Idempotency-Key` and current
`expected_revision`, clears downstream approvals, and requires review approval
again. Server review capabilities expose `undo_regeneration` only when this
operation is available.

### Confirmation and recovery

- `GET /candidate-profile-creation-attempts/{attempt_id}/confirmation`
- `POST /candidate-profile-creation-attempts/{attempt_id}/actions/confirm`
- `POST /candidate-profile-creation-attempts/{attempt_id}/actions/retry`

Confirmation requires revision, baseline fingerprint, derived fingerprint, and
confirmation fingerprint. It creates one immutable Candidate Profile revision;
same-key replay returns the same profile. Retry is available only when server
capabilities permit it.

### Catalog and lifecycle

- `GET /candidate-profiles?view=active|archived&status=&search=&page=&page_size=`
- `GET /candidate-profiles/{profile_id}`
- `GET /candidate-profiles/{profile_id}/runs`
- `POST /candidate-profiles/{profile_id}/actions/archive`
- `POST /candidate-profiles/{profile_id}/actions/restore`
- `POST /candidate-profiles/{profile_id}/actions/delete`

Catalog, confirmation, and details expose the same persisted canonical profile
resource. Archive and restore require `Idempotency-Key` plus
`expected_revision`; archived profiles remain historically resolvable but are
not eligible for new Runs. Delete requires `Idempotency-Key` plus
`expected_revision`, accepts only archived succeeded profiles with no related
Run profile or profile-revision reference, and permanently removes the profile
and linked creation artifacts. Same-key replay returns stored deletion receipt.

### Candidate Profile errors

- `404`: missing attempt, source, source block, or profile
- `409`: stale revision/fingerprint, invalid transition, processing claim,
  idempotency conflict, referenced-profile deletion, or unavailable regeneration undo
- `410`: source bytes or private review content purged after retention expiry
- `413`: upload or bounded model input exceeds limit
- `415`: unsupported extension or media mismatch
- `422`: invalid request, review operation, or canonical profile

Unconfirmed inactive attempts purge private source bytes, source blocks, and
review snapshots atomically after 30 days. Safe filename, media type, size,
checksum, timestamps, and failure diagnostics remain inspectable.

## Run Trigger

### `POST /runs`

Managed Runs trigger uses `multipart/form-data` plus `Idempotency-Key`:

- `jobs_file`: optional single non-empty UTF-8 `.json` or `.jsonl` file, maximum
  50 MB
- `scan_ids`: optional repeated ordered Scan IDs; duplicates are trimmed while
  preserving first occurrence
- `profile_id`: required active profile for upload, scan, and combined managed Runs
  submissions
- `run_name`: optional, defaults to filename stem, maximum 120 characters
- `config_path`: optional, defaults to `.env.yaml`
- `triggered_by`: optional, defaults to `admin`

At least one of `jobs_file` or `scan_ids` is required. Upload-only, Scan-only,
and combined requests use one resolver and persist one canonical Run snapshot;
Scan-only and combined requests include Scan provenance in the input manifest.

The backend persists Run, immutable input/profile/settings snapshots, six stage
rows, and stable Run Job IDs before enqueue. Success returns `201` with the Run
resource and `action_id`. Queue failure returns `503` with both persisted Run
data and `run_enqueue_failed`; the failed Run remains inspectable.

The historical JSON body (`jobs_path`, `config_path`, `triggered_by`,
`config_overrides`, `run_mode`) remains a compatibility delegate for older
automation. It does not define the prototype contract.

## Runs And Pipeline Results

### `GET /runs`

Query parameters:

- `view=active|archived|all`, default `active`
- `search`, server-side across Run identity/name/input/profile
- `page=1`
- `page_size=20`

Metadata includes active/archived counts, applied filters, and server time.

### `GET /runs/{run_id}`

Returns Run overview, immutable input summary, server-owned status/detail,
counts, capabilities, debug-bundle availability, and six stage rows.

### `GET /runs/{run_id}/stages`

Returns the six ordered stage resources.

### `GET /runs/{run_id}/jobs`

Query parameters:

- `page=1`
- `page_size=10`
- `search`
- `stage=all|enrichment|screening|shortlisting|ranking|cv-analysis|cv-generation`
- `result_bucket=all|passed|rejected`

Metadata includes `total_evaluated`, `passed`, and `rejected` for the full
filtered set. Rows include stable job identity, attributes, skills, current
stage/outcome, capabilities, bookmark, Application Interest, CV summary, and
evaluation/review state.

### Lifecycle actions

- `POST /runs/{run_id}/actions/cancel`
- `POST /runs/{run_id}/actions/archive`
- `POST /runs/{run_id}/actions/unarchive`
- `POST /runs/actions/delete-archived`

Cancel/archive/unarchive are repeat-safe and return the refreshed Run.
`delete-archived` requires `Idempotency-Key` and body
`{"run_ids":["..."]}`. Every selected Run must exist and be archived or the
whole request returns `409 run_state_conflict`; no partial deletion occurs.

### Bookmark and Application Interest

- `PUT /runs/{run_id}/jobs/{run_job_id}/bookmark`
- `DELETE /runs/{run_id}/jobs/{run_job_id}/bookmark`
- `PUT /runs/{run_id}/jobs/{run_job_id}/interest`
- `DELETE /runs/{run_id}/jobs/{run_job_id}/interest`

Interest body is `{"rating":1..5,"rating_contract_revision":"application-interest-v1"}`.
A stale contract returns `409 rating_contract_stale`.

### `GET /runs/{run_id}/jobs/export.csv`

Accepts the same `search`, `stage`, and `result_bucket` filters as Pipeline
Results and exports the full filtered set, not only the visible page. Response
uses `text/csv`, `Content-Disposition: attachment`, and
`X-Content-Type-Options: nosniff`.

## CV Versions

### `GET /runs/{run_id}/jobs/{run_job_id}/cvs`

Returns ordered version history with generation metadata, capabilities,
evaluation, and review state.

### `GET /cv-versions/{version_id}/download`

Returns the persisted CV bytes after checksum verification. Headers include
`Content-Disposition`, `Content-Length`, checksum-backed `ETag`, and
`X-Content-Type-Options: nosniff`. Missing versions return `cv_not_found`;
missing or corrupt content returns `artifact_not_available`.

### `GET /cv-versions/{version_id}/preview`

Returns exact persisted `text/markdown` or `text/plain` bytes for selected
immutable version with `Content-Disposition: inline`, checksum-backed `ETag`,
`Content-Length`, `X-CV-Version-ID`, and `X-Content-Type-Options: nosniff`.
Missing versions return `cv_not_found`; pending, failed, corrupt, or
unsupported media returns `artifact_not_available` in standard error envelope.
This route never changes evaluation, review, version, or download state.

### `POST /runs/{run_id}/jobs/{run_job_id}/cvs/actions/regenerate`

Requires `Idempotency-Key`. Optional body:

```json
{"parent_cv_version_id": "<version_id>"}
```

The backend reserves and persists a child CV version before enqueue. Success
returns `202` with `action_id`, queue job ID, and the pending version. Queue
failure persists `generation_failed` and returns retryable
`503 cv_regeneration_failed`. Evaluation and `stretch` review are separate
persisted state; generation success never implies evaluation acceptance.

## Console And Diagnostics

### `GET /runs/{run_id}/events`

Query parameters are optional `cursor` and `limit`. Response metadata includes
`next_cursor` and integrity-conflict count. Events are immutable process-event
projections. UI Clear View is local-only and never calls a delete route.

### `GET /runs/{run_id}/debug-bundle`

Returns a redacted ZIP when diagnostics are available. Missing/not-ready
evidence returns `409 artifact_not_available` with retryability and operator
action derived from availability.

## Legacy Admin Boundary

`/admin/settings` hosts the prototype-compatible interface. Existing
`/admin/runs`, `/admin/runs/{run_id}`, `/admin/upload-trigger`, and historical
artifact/review routes remain compatibility surfaces for current operators.
They must delegate to shared stores/services where behavior overlaps; the
prototype frontend does not parse their HTML or artifacts for lifecycle truth.
`POST /admin/runs/bulk/cancel`, `/admin/runs/bulk/archive`, and
`/admin/runs/bulk/unarchive` require `Idempotency-Key`; same-key replay returns
the stored summary and a different payload returns `409 idempotency_conflict`.
The legacy `/admin/upload-trigger` form keeps its separate
`candidate_profile_id` field contract; it is not the managed `/runs` form.
