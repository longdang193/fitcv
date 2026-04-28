---
doc_id: setup
doc_type: setup-guide
explains:
  features:
    - admin_control_plane_core
    - trigger_run_management
  components:
    - src/fitcv
    - src/fitcv_cp
---

# Setup

FitCV is a **managed-architecture-metadata** repo with two practical runtime
surfaces:

- an operator-facing FastAPI control plane in `src/fitcv_cp/`
- a staged background pipeline in `src/fitcv/`

Use [fitcv-control-plane-setup.md](fitcv-control-plane-setup.md) as the
detailed runbook. This page is the short setup map so someone new can tell what
must exist before the system is usable.

## What You Need

- Python with the checked-in dependency set available through the repo virtual
  environment
- Docker Desktop if you want Redis-only or full container startup
- Google service-account credentials for BigQuery-backed runtime surfaces
- Redis for the queue backend

The repo expects credentials to stay outside version control. A local untracked
`sa_key.json` is supported for convenience, but it should never be committed.

## Main Startup Modes

Choose one runtime mode at a time.

### Local mode

Use local mode when you want the web server and worker to run directly from the
current checkout:

1. start Redis
2. run `.\start_web.ps1`
3. run `.\start_worker.ps1` in a second shell
4. open `http://localhost:8000/admin/runs`

The PowerShell helpers also set the expected environment variables for Redis,
BigQuery project and dataset, and credentials.

### Docker mode

Use Docker mode when you want `redis`, `web`, and `worker` together from a
single checkout or worktree:

```powershell
docker compose up -d --build redis web worker
```

Run Docker from the exact checkout or worktree whose files you want active.

## Bootstrap Order

The shortest reliable path is:

1. make sure credentials are available
2. make sure Redis is running
3. start the web service
4. start the worker service
5. verify `http://localhost:8000/healthz`
6. trigger a test run from the UI or `POST /runs`

Both the web service and worker must be live for queued runs to progress.

## Repo-Specific Setup Notes

- `docker-compose.yml` mounts `./.env.yaml` and `./config/env.yaml` into the
  containers
- local start scripts use the repo virtual environment at `.venv\Scripts`
- Windows local worker startup should go through `.\start_worker.ps1`, not a
  raw `rq worker ...` invocation
- BigQuery tables and datasets are part of the runtime contract; use
  `scripts/bootstrap_bigquery.py` when environment bootstrapping requires it

## After Setup

Once the system starts, the next useful docs are:

- [configuration.md](configuration.md) for runtime config ownership and
  override layering
- [usage.md](usage.md) for operator and developer workflows
- [pipeline.md](pipeline.md) for the stage flow and runtime semantics
- [architecture.md](architecture.md) for the control-plane, worker, storage,
  and managed-doc shape

## Validation

For setup-adjacent repo checks, the canonical validation path is:

```powershell
python scripts/sync_architecture_docs.py --check
python scripts/validate_repo_contracts.py --fast
```
