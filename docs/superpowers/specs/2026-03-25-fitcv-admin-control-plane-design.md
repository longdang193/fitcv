# FitCV Admin Control Plane Design

## Summary

This design introduces an internal administration control plane for FitCV. It provides an admin UI, a FastAPI backend, and a background worker to trigger pipeline runs and inspect their status, history, and event logs without requiring terminal access.

## Architecture

A new `src/fitcv_cp/` control-plane package wraps the existing `run_pipeline()` function without modifying its core business logic. 

The architecture consists of:
- **FastAPI Backend:** Handles admin pages and exposes a REST API.
- **Background Worker:** A Redis-backed RQ worker executes the pipeline asynchronously in the background.
- **BigQuery Storage:** Two new BigQuery tables (`pipeline_runs` and `pipeline_run_events`) track the lifecycle state and event logs of pipeline runs.
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

## File Map

### New package — `src/fitcv_cp/`

| File | Responsibility |
|------|---------------|
| `src/fitcv_cp/__init__.py` | Package marker |
| `src/fitcv_cp/models.py` | `RunStatus` enum; `PipelineRun` and `RunEvent` dataclasses |
| `src/fitcv_cp/bq_store.py` | BigQuery reads/writes for `pipeline_runs` and `pipeline_run_events` |
| `src/fitcv_cp/reporter.py` | `PipelineReporter` callback passed into `run_pipeline()` |
| `src/fitcv_cp/queue.py` | Redis/RQ queue setup and `enqueue_run()` helper |
| `src/fitcv_cp/worker_job.py` | `execute_pipeline_run()` — the RQ job function |
| `src/fitcv_cp/app.py` | FastAPI app factory, admin routes, Jinja2 templates |
| `src/fitcv_cp/templates/base.html` | HTML base layout |
| `src/fitcv_cp/templates/runs_list.html` | `/admin/runs` page |
| `src/fitcv_cp/templates/run_detail.html` | `/admin/runs/{run_id}` page |

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
| `src/fitcv_cp/worker_main.py` | RQ worker entrypoint docs |

### New Tests — `tests/fitcv_cp/`

| File                                | What it tests                                                          |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `tests/fitcv_cp/test_models.py`     | `RunStatus` enum values; dataclass fields                              |
| `tests/fitcv_cp/test_bq_store.py`   | All BQ helpers with mocked BQ client                                   |
| `tests/fitcv_cp/test_reporter.py`   | Reporter emits correct event payloads; no-op without BQ client         |
| `tests/fitcv_cp/test_queue.py`      | `enqueue_run()` puts job on queue; returns `run_id`                    |
| `tests/fitcv_cp/test_worker_job.py` | Worker lifecycle: marks running → succeeded; marks failed on exception |
| `tests/fitcv_cp/test_app.py`        | POST /runs, GET /runs, GET /runs/{id}, GET /runs/{id}/events           |
