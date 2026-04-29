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

This page summarizes the main HTTP surfaces exposed by the FitCV control plane.
It is intentionally concise: enough to make the routes discoverable and usable,
without duplicating lower-level implementation details from the code or managed
feature docs.

## API Shape

The repo exposes two broad classes of HTTP surface:

- JSON-oriented API routes for runs, events, and settings
- HTML admin routes for operators

Most agentic observation and operator actions happen through the admin routes,
while automation and programmatic inspection usually start with the JSON routes.

## Health

### `GET /healthz`

Purpose:
- lightweight service health check

Typical response:

```json
{
  "ok": true
}
```

## Run Trigger And Inspection API

### `POST /runs`

Purpose:
- create a run through the JSON API

Behavior:
- captures input source
- snapshots effective settings
- inserts the run row before enqueue
- enqueues background execution

Typical payload shape:

```json
{
  "jobs_path": "data/sample_jobs.json",
  "config_path": ".env.yaml",
  "triggered_by": "admin"
}
```

Additional trigger variants may include resolved jobs input, candidate profile
input, run mode, and per-run overrides depending on the caller.

Typical response:
- `201 Created`
- JSON representation of the created run

### `GET /runs`

Purpose:
- list pipeline runs in JSON form

Typical response:
- array of run objects with status, lifecycle, and summary fields

### `GET /runs/{run_id}`

Purpose:
- fetch one run in JSON form

Typical response:
- one run object, or `404` if missing

### `GET /runs/{run_id}/events`

Purpose:
- fetch the raw persisted event stream for one run

Typical response:
- ordered array of event objects

Event shape includes:

```json
{
  "run_id": "example-run-id",
  "event_id": "example-event-id",
  "stage": "pipeline_complete",
  "level": "info",
  "message": "Pipeline complete",
  "created_at": "2026-04-28T19:00:11+00:00",
  "payload_json": "{...}"
}
```

## Settings API

### `GET /settings`

Purpose:
- fetch the current active settings view

Typical response:
- JSON object of active settings values

### `POST /settings/{key}`

Purpose:
- update one settings key through the JSON API

Behavior:
- coerces value to schema type
- validates before persistence

Typical response:
- `200 OK`

## Operator HTML Surfaces

### `GET /admin/runs`

Purpose:
- runs list UI

### `GET /admin/runs/{run_id}`

Purpose:
- run detail UI

This is the main human-facing inspection surface for:

- timeline
- run health
- stage metrics
- exports
- checkpoint/continue flow
- synonym review activity

### `GET /admin/settings`

Purpose:
- settings UI

## Run Lifecycle Action Routes

These are primarily operator-facing action endpoints:

- `POST /admin/runs/{run_id}/stop`
- `POST /admin/runs/bulk/cancel`
- `POST /admin/runs/bulk/archive`
- `POST /admin/runs/bulk/unarchive`
- `POST /admin/runs/{run_id}/archive`
- `POST /admin/runs/{run_id}/unarchive`
- `POST /admin/runs/{run_id}/repair-cancellation`
- `POST /admin/runs/{run_id}/continue`
- `POST /admin/runs/{run_id}/synonym-overlay`

These generally redirect in the HTML workflow, and they may return conflict or
not-found errors when the run is not in a valid state for the action.

## Export And Debug Routes

### Run-scoped exports

- `GET /admin/runs/{run_id}/export.json`
- `GET /admin/runs/{run_id}/cv-debug.json`
- `GET /admin/runs/{run_id}/cv-analysis-trace.json`
- `GET /admin/runs/{run_id}/agentic-live-trace.json`
- `GET /admin/runs/{run_id}/stage-artifacts.json`
- `GET /admin/runs/{run_id}/stage-artifacts/{stage_id}.json`
- `GET /admin/runs/{run_id}/settings-used.json`
- `GET /admin/runs/{run_id}/mapping-suggestions.json`
- `GET /admin/runs/{run_id}/synonym-proposals.json`
- `GET /admin/runs/{run_id}/synonym-proposals-trace.json`
- `GET /admin/runs/{run_id}/artifacts.zip`

These routes expose the main observation payloads for completed or sufficiently
advanced runs.

Common behavior:

- `404` when the artifact does not exist yet
- `409` when the route is only valid for succeeded runs and the run is not yet
  terminal

Trace-specific note:

- shared-standard trace downloads currently include:
  - `cv-analysis-trace.json` with `step_id=cv_analysis`
  - `agentic-live-trace.json` with `step_id=cv_generation`
  - `synonym-proposals-trace.json` with `step_id=synonym_proposals`

### Aggregate exports

- `GET /admin/mapping-suggestions.json`
- `GET /admin/synonym-proposals.json`

These are useful for cross-run review workflows and higher-level operator
inspection.

## Synonym Proposal Review Routes

- `POST /admin/synonym-proposals/{proposal_id}/start-review`
- `POST /admin/synonym-proposals/{proposal_id}/approve-for-run-overlay`
- `POST /admin/synonym-proposals/{proposal_id}/reject`
- `POST /admin/synonym-proposals/{proposal_id}/defer`

Purpose:
- move a persisted proposal through the review workflow

Typical form fields:

- `acted_by`
- `note`

Typical response shape:

```json
{
  "proposal_id": "synprop-example",
  "run_id": "run-example",
  "proposal_status": "approved_for_run_overlay"
}
```

## File Download Routes

### `GET /admin/cvs/{version_id}/download`

Purpose:
- download one generated CV as Markdown

## Notes On Payload Expectations

- Run objects expose lifecycle and summary data, not every stage detail inline
- Event payloads may include JSON-encoded machine detail inside `payload_json`
- Export routes are the preferred source for detailed agentic and stage-owned
  debugging payloads
- The API shape is closely tied to the control plane and background worker, not
  a separate public product API boundary

## Related Docs

- [observability.md](observability.md)
- [usage.md](usage.md)
- [setup.md](setup.md)
- [architecture.md](architecture.md)
