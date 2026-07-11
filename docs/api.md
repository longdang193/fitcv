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

## Control-Plane Runtime Backend

The supported control-plane runtime is SQLite-backed.

Behavior:

- startup always resolves to the local SQLite control-plane store
- supported local startup does not require GCP ADC or cloud database credentials

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
  "triggered_by": "admin",
  "config_overrides": {},
  "run_mode": "run_all"
}
```

`run_mode` supports:

- `run_all`
- `manual_staged`

Typical response:

```json
{
  "run_id": "<uuid>",
  "status": "queued",
  "triggered_by": "admin"
}
```

### `GET /runs/{run_id}`

Purpose:

- fetch one run record

Typical response shape:

```json
{
  "run_id": "<uuid>",
  "status": "running",
  "triggered_by": "admin",
  "created_at": "2026-05-02T22:11:00+00:00"
}
```

### `GET /runs/{run_id}/events`

Purpose:

- fetch persisted event timeline for one run

Typical response shape:

```json
[
  {
    "event_id": "<uuid>",
    "stage": "enrich",
    "level": "info",
    "message": "Stage complete"
  }
]
```

## Admin HTML Routes

### `GET /admin/runs`

Purpose:

- operator runs list UI

Behavior:

- lists queued/running/completed runs
- supports active/all/archived views
- exposes archive/unarchive and bulk lifecycle actions

### `GET /admin/runs/{run_id}`

Purpose:

- operator run detail UI

Behavior:

- shows summary, events, stage progress, artifacts, and exports
- hides removed replay/advanced-diagnostics surfaces from this trim lane

## Artifact Export Surfaces

These routes expose persisted run-scoped evidence files, such as:

- `GET /admin/runs/{run_id}/export.json`
- `GET /admin/runs/{run_id}/settings-used.json`
- `GET /admin/runs/{run_id}/hitl-review-audit.json`
- `GET /admin/runs/{run_id}/cv-debug.json`
- `GET /admin/runs/{run_id}/cv-analysis-trace.json`

These are useful for cross-run review workflows and higher-level operator
inspection.
