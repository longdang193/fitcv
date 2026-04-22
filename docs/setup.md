# Setup

Use [fitcv-control-plane-setup.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/fitcv-control-plane-setup.md) as the detailed runbook for local web, worker, Docker, credentials, and troubleshooting.

This setup layer covers prerequisites, dependency installation, bootstrap order, and tool version expectations for the control plane and worker runtime.

## Minimum Setup Path

1. Provide Google credentials outside the repo or as an untracked local `sa_key.json`.
2. Start either local mode with `.\start_web.ps1` and `.\start_worker.ps1`, or Docker mode with `docker compose up -d --build redis web worker`.
3. Open `http://localhost:8000/admin/runs`.
4. Verify the health endpoint and run-trigger flow before changing pipeline settings.

## Prerequisites

- Install Python and keep the project tool version aligned with the checked-in dependency set before running local bootstrap commands.
- Install Docker Desktop if you want the containerized bootstrap path.
- Provision Redis, Google credentials, and any other external prerequisite required by the selected run mode.

## Related Docs

- [configuration.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/configuration.md)
- [usage.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/usage.md)
- [architecture.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/architecture.md)
