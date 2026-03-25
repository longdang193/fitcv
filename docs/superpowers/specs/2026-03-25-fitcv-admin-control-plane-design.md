# FitCV Admin Control Plane Design

## Summary

This design introduces an internal administration control plane for FitCV. It provides an admin UI, a FastAPI backend, and a background worker to trigger pipeline runs and inspect their status, history, and event logs without requiring terminal access.

## Architecture

A new `src/fitcv_cp/` control-plane package wraps the existing `run_pipeline()` function without modifying its core business logic.

The architecture consists of:
- **FastAPI Backend:** Handles admin pages and exposes a REST API.
- **Background Worker:** A Redis-backed RQ worker executes the pipeline asynchronously in the background.
- **BigQuery Storage:** Two new BigQuery tables (`pipeline_runs` and `pipeline_run_events`) track the lifecycle state and event logs of pipeline runs. BigQuery is used here as an append-only event log and a single-row per run status tracker — not as a transactional app database. Keep this state model simple.
- **Docker Integration:** A single `Dockerfile` is shared by both the `web` and `worker` services. They are orchestrated locally via `docker-compose.yml`.

## Goal

Add an internal admin UI + FastAPI backend + Redis worker that lets an admin trigger FitCV pipeline runs and inspect run status, history, and event logs without using the terminal.

## Tech Stack

- **Python:** 3.11
- **Web Framework:** FastAPI
- **Templating:** Jinja2 (server-rendered templates)
- **Background Jobs:** RQ + Redis
- **Data Persistence:** `google-cloud-bigquery`
- **Infrastructure:** Docker + docker-compose

## State Consistency Contract

`POST /runs` must always:
1. Create the `run_id` (UUID)
2. Insert the `pipeline_runs` row with status `queued` **first**
3. Enqueue the worker job **second**

The database is the source of truth. If enqueue fails after insert, the run sits in `queued` permanently — acceptable. If insert fails before enqueue, the worker must never start — enforced by this order.

## Summary Contract for `run_pipeline()`

The worker depends on `run_pipeline()` returning a dict with exactly these keys:

```
total_jobs      int
passed_filter   int
ranked          int
cvs_generated   int
```

This contract must be documented and enforced — not inferred.

## Event Level and Stage Contracts

`RunEvent.level` must be one of: `info`, `warning`, `error`

`RunEvent.stage` standardised values:
- `pipeline_start`
- `layer1_jobs`
- `layer2_candidate`
- `layer3_filter`
- `layer3_ranking`
- `layer4_cv_skip` (fit=skip per job)
- `layer4_cv_validation_failed` (per job)
- `pipeline_complete`
- `pipeline_failed`

## File Map

### New package — `src/fitcv_cp/`

| File | Responsibility |
|------|---------------|
| `src/fitcv_cp/__init__.py` | Package marker |
| `src/fitcv_cp/models.py` | `RunStatus` enum; `EventLevel`/`EventStage` enums; `PipelineRun` and `RunEvent` dataclasses |
| `src/fitcv_cp/bq_store.py` | BigQuery reads/writes for `pipeline_runs` and `pipeline_run_events`; parameterized queries only |
| `src/fitcv_cp/reporter.py` | `PipelineReporter` callback passed into `run_pipeline()` |
| `src/fitcv_cp/queue.py` | Redis/RQ queue setup and `enqueue_run()` helper |
| `src/fitcv_cp/worker_job.py` | `execute_pipeline_run()` — the RQ job function |
| `src/fitcv_cp/app.py` | FastAPI app factory, admin routes, Jinja2 templates |
| `src/fitcv_cp/templates/base.html` | HTML base layout |
| `src/fitcv_cp/templates/runs_list.html` | `/admin/runs` page — trigger form + run table with status badges |
| `src/fitcv_cp/templates/run_detail.html` | `/admin/runs/{run_id}` page — metadata + event timeline |

### Modified Files

| File | Change |
|------|--------|
| `src/fitcv/pipeline.py` | Accept optional `reporter` kwarg; emit stage events via reporter |
| `assets/bigquery/pipeline_runs.sql` | New DDL — control-plane run metadata |
| `assets/bigquery/pipeline_run_events.sql` | New DDL — append-only event stream |
| `requirements.txt` | Add `fastapi`, `uvicorn`, `rq`, `redis`, `jinja2`, `httpx`, `pytest-mock` |

### New Infrastructure

| File | Responsibility |
|------|---------------|
| `Dockerfile` | Single image for `web` and `worker` services |
| `docker-compose.yml` | Local dev stack: `web`, `worker`, `redis` |
| `src/fitcv_cp/main.py` | Uvicorn entrypoint |

### New Tests — `tests/fitcv_cp/`

| File                                | What it tests                                                          |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `tests/fitcv_cp/test_models.py`     | `RunStatus` enum values; dataclass fields                              |
| `tests/fitcv_cp/test_bq_store.py`   | All BQ helpers with mocked BQ client                                   |
| `tests/fitcv_cp/test_reporter.py`   | Reporter emits correct event payloads; no-op without BQ client         |
| `tests/fitcv_cp/test_queue.py`      | `enqueue_run()` puts job on queue; returns `run_id`                    |
| `tests/fitcv_cp/test_worker_job.py` | Worker lifecycle: marks running → succeeded; marks failed on exception; emits error event |
| `tests/fitcv_cp/test_app.py`        | POST /runs (insert before enqueue), GET /runs, GET /runs/{id}, GET /runs/{id}/events |

## Non-Goals

- No complex retry logic on pipeline failure (retry is a future concern)
- No real-time WebSocket streaming — polling the events endpoint is sufficient
- No role-based access control — this is an internal-only admin tool
