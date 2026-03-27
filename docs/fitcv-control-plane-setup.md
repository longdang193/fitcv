# FitCV Admin Control Plane — Local Setup Guide

> How to run the FastAPI web server and RQ background worker locally on Windows.

---

## Architecture

```
================================================================================
                    ASYNC PIPELINE: FASTAPI + REDIS + RQ
================================================================================

1. THE REQUEST PHASE (Synchronous)
   The Browser triggers a run. FastAPI acts as the gatekeeper.

   [ BROWSER / UI ]
          |
          |  POST /runs (Payload)
          V
   +------------------+       [ BIGQUERY / STATE ]
   |  FASTAPI SERVER  | ----> | Initial Run Row  | (Status: PENDING)
   +------------------+       +------------------+
          |
          |  (Job Metadata)
          V
   [ REDIS BROKER ] <--------- "Here is a new job. 201 CREATED!"
   ( Job Queue [||||] )        The Browser is released immediately.

================================================================================

2. THE EXECUTION PHASE (Asynchronous)
   The RQ Worker lives in its own world, pulling jobs when ready.

   [ REDIS BROKER ]
          |
          |  (Pop Job)
          V
   +------------------+       [ BIGQUERY / EVENTS ]
   |    RQ WORKER     | ----> | Update: "STARTED" |
   +------------------+       +------------------+
          |
          |  run_pipeline()   <-- The "Heavy Lifting" happens here.
          |
          V
   [ SUCCESS / FAIL ]
          |
          |                   [ BIGQUERY / FINAL ]
          +-----------------> | Update: "COMPLETE"| (Logs + Metrics)
                              +------------------+

================================================================================
   KEY TAKEAWAY:
   The User never waits for the pipeline to finish. 
   FastAPI records the intent in BigQuery and Redis, then says "Got it!" 
   The RQ Worker handles the reality of the work in the background.
================================================================================
```

The **web server** (FastAPI/uvicorn) handles the admin UI and REST API.
The **RQ worker** consumes jobs from Redis and executes `run_pipeline()`.
Both connect to **Redis** for the queue and **BigQuery** for state.

**Both services must be running** for pipeline runs to execute.

---

## Prerequisites

- Docker Desktop (for Redis)
- Python 3.11+ (for the web server)
- GCP project with:
  - BigQuery datasets (`fitcv` by default)
  - Vertex AI enabled
  - Service account with BigQuery + Vertex AI roles
- `uv` package manager

---

## 1. Start Redis

Redis runs in a Docker container:

```bash
docker compose up -d redis
```

Verify it is running:

```bash
docker compose ps
```

Expected output:

```
NAME                 STATUS
job-project-redis-1  Up 2 minutes
```

Redis is reachable at `redis://localhost:6379/0`.

---

## 2. Start the FastAPI Web Server

Set the required environment variables, then launch uvicorn:

```bash
# Required environment variables
export GCP_PROJECT="your-gcp-project-id"
export REDIS_URL="redis://localhost:6379/0"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export PYTHONPATH="src"

# Launch FastAPI (from project root)
uv run uvicorn fitcv_cp.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Windows (PowerShell):**
>
> ```powershell
> $env:GCP_PROJECT="your-gcp-project-id"
> $env:REDIS_URL="redis://localhost:6379/0"
> $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
> $env:PYTHONPATH="src"
> uv run uvicorn fitcv_cp.main:app --host 0.0.0.0 --port 8000 --reload
> ```

The server starts at **<http://localhost:8000>**. Open:

- Admin UI: **<http://localhost:8000/admin/runs>**
- API docs: **<http://localhost:8000/docs>**
- Health check: **<http://localhost:8000/healthz>**

---

## 3. Start the RQ Background Worker

The worker consumes pipeline jobs from Redis. It must be started **separately** from the web server.

### Option A — Run inside Docker Compose (recommended for production parity)

Set `GCP_PROJECT` and use `docker compose`:

```bash
export GCP_PROJECT="your-gcp-project-id"
docker compose up -d worker
```

The worker container uses the same Dockerfile as the web server, with the service account key mounted at `/app/sa_key.json`. The `.env.yaml` config (`service_account_key: /app/sa_key.json`) is already correct for this setup.

### Option B — Run locally with `uv`

```bash
export GCP_PROJECT="your-gcp-project-id"
export REDIS_URL="redis://localhost:6379/0"
export BIGQUERY_DATASET="fitcv"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export PYTHONPATH="src"

rq worker fitcv --url redis://localhost:6379/0
```

The worker listens on the `fitcv` queue and updates BigQuery as it processes runs.

---

## 4. Verify Everything is Working

### Check the worker is listening

```bash
docker logs job-project-worker-1 --tail 5
```

Expected:

```
Worker <id>: started with PID 1, version 2.7.0
*** Listening on fitcv...
Worker <id>: cleaning registries for queue: fitcv
```

### Trigger a test run

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json", "config_path": ".env.yaml", "triggered_by": "admin"}'
```

Returns:

```json
{"run_id": "<uuid>"}
```

### Check the run status

```bash
curl http://localhost:8000/runs/<uuid>
```

Expected progression:

1. `"status": "queued"` — just created (instant)
2. `"status": "running"` — worker picked it up (typically within 5 seconds)
3. `"status": "succeeded"` or `"failed"` — pipeline finished

Or open **<http://localhost:8000/admin/runs/><uuid>** in the browser.

---

## 5. Stopping Services

```bash
# Stop the web server (Ctrl+C in its terminal)

# Stop Docker services
docker compose stop worker
docker compose stop redis   # optional — can keep running

# Or stop everything at once
docker compose down
```

---

## Troubleshooting

### Run stays "queued" — worker not running

If a run is created but never transitions to "running", the worker is not consuming the queue.

1. Check the worker is running:

   ```bash
   docker compose ps worker
   ```

2. Check the worker logs:

   ```bash
   docker logs job-project-worker-1 --tail 20
   ```

3. If the worker crashed on startup, it is likely a Python import error. Check the logs for `Traceback`.

### Worker crashes: `ValueError: cannot find context for 'fork'`

This happens when running the **web server** (not the worker) on Windows without the `queue.py` Windows fix. The FastAPI app imports `rq` which uses `fork`-style multiprocessing internally.

**Fix:** Apply the Windows multiprocessing patch in `src/fitcv_cp/queue.py` (already committed). Rebuild the Docker image or pull the latest code.

### Worker crashes: `No such file or directory: '/workspaces/fitcv/...'`

The `.env.yaml` contains a hardcoded Docker Compose path (`/workspaces/fitcv/...`) that does not exist locally. Update it:

```yaml
service_account_key: "/path/to/your/service-account.json"
# or for Docker Compose:
service_account_key: "/app/sa_key.json"
```

### `429 RESOURCE_EXHAUSTED` — Vertex AI rate limit

Reduce the enrichment rate by increasing `enrichment_sleep_secs` in `.env.yaml`:

```yaml
enrichment_sleep_secs: 5   # default is 3
```

Wait a few minutes before retrying — Vertex AI quotas replenish over time.

### BigQuery permission errors

Verify the service account has the correct roles:

- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`
- `roles/aiplatform.user`

---

## All-In-One Start Script

To start all services (web + worker + Redis) from the project root:

```bash
export GCP_PROJECT="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Start Redis and worker in Docker
docker compose up -d redis worker

# Start the web server in the foreground
uv run uvicorn fitcv_cp.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Key Files

| File | Purpose |
|---|---|
| `src/fitcv_cp/main.py` | uvicorn entrypoint — creates FastAPI app with GCP + Redis config |
| `src/fitcv_cp/app.py` | FastAPI app — all routes, templates, queue integration |
| `src/fitcv_cp/worker_job.py` | RQ job function — calls `run_pipeline()`, updates BQ lifecycle |
| `src/fitcv_cp/queue.py` | Redis/RQ queue setup + Windows multiprocessing fix |
| `src/fitcv_cp/bq_store.py` | BigQuery read/write for runs and events |
| `src/fitcv_cp/models.py` | Pydantic models and `RunStatus` enum |
| `.env.yaml` | Config: GCP project, SA key path, model names, rate limits |
| `docker-compose.yml` | Redis + web + worker services |
| `Dockerfile` | Shared image for web and worker |
