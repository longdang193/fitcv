# FitCV Admin Control Plane Setup

FitCV Local is primary non-technical path. Docker and Redis/RQ remain optional
developer/server deployment modes.

## FitCV Local

### Install And Launch

1. Run `FitCV-Local-<version>-Technical-Preview-Setup.exe`.
2. Launch **FitCV Local** from Start menu.
3. Browser opens local onboarding or `/admin/runs`.

No terminal, repository checkout, Python, Git, Docker, Redis, worker, or manual
`.env` setup is required. Current unsigned artifact is Technical Preview.

### Onboarding

Choose local fixed-disk data folder, review candidate profile, then configure:

- provider: OpenAI, OpenAI-compatible, or 9router
- API root
- auth mode: required, optional, or none
- wire API: Responses or Chat Completions
- API key when required
- default model and optional task-specific models

Use **Discover models** and **Test provider**. Run submission remains blocked
until readiness passes. API keys are stored in Windows Credential Manager.

### Data And Backup

Default data root is `%LOCALAPPDATA%\FitCV\data`. Open **Data & Backup** to:

- inspect data root, database path/size/integrity, and last backup
- download validated `fitcv-backup.v1` ZIP
- move data through cold relocation and restart
- import validated backup into selected restore folder and restart

Import and relocation reject UNC/network/removable/relative/non-writable paths,
active work, unsafe ZIP members, checksum mismatch, incompatible schema, failed
SQLite integrity, and insufficient free space. Source data remains retained.

### Diagnostics And Shutdown

Open **System** to download redacted diagnostics or shut application down.
Shutdown requires confirmation and is rejected during active work. Accepted
shutdown renders stopped page, closes local server, and exits process.

If storage cannot open, recovery page preserves existing data and asks user to
restore folder availability/write access before relaunch.

## Developer / Server Mode

Use one source deployment mode at a time.

### Local Source Mode

Without `REDIS_URL`, Windows web startup uses inline execution:

```powershell
.\start_web.ps1
```

For intentional Redis/RQ mode:

```powershell
docker compose up -d redis
.\start_web.ps1
.\start_worker.ps1
```

Open `http://localhost:8000/admin/runs`.

Stop source processes:

```powershell
.\stop_fitcv.ps1
```

### Docker Mode

Run from checkout or worktree whose files should build:

```powershell
docker compose up -d --build redis web worker
```

Open `http://localhost:8000/admin/runs`.

Do not pass Windows host paths into container-triggered runs. Use paths mounted
inside container or upload/paste input through UI.

### Developer LLM Credential

Set repo-local ignored `.env`:

```dotenv
FITCV_LLM_API_KEY=replace_me
```

Provider, model, base URL, wire API, and timeout remain owned by
`config/runtime/control_plane.yaml`. Restart web and worker after credential
change.

## Verify Setup

### UI And Health

```powershell
Invoke-WebRequest http://localhost:8000/healthz -UseBasicParsing
```

Then open `/admin/runs` and trigger small test run.

### Queued Run Troubleshooting

- FitCV Local: another packaged job may be active; wait for completion.
- Source inline mode: inspect web logs.
- Redis/RQ mode: verify Redis reachable and worker running.
- Docker mode: inspect `docker compose logs web --tail 50` and
  `docker compose logs worker --tail 50`.

Use `start_worker.ps1`; do not start raw `rq worker` on Windows.

### Missing Credential

- FitCV Local: reopen onboarding, save API key, and rerun provider test.
- Developer/server mode: set `FITCV_LLM_API_KEY`, then restart web/worker.

### Missing Config In Docker

Run Docker command from intended checkout and rebuild:

```powershell
docker compose down
docker compose up -d --build redis web worker
```

## Key Files

| File | Purpose |
|---|---|
| `src/fitcv_cp/local_app.py` | single-instance packaged launcher and executor |
| `src/fitcv_cp/local_storage.py` | user data, backup, restore, and relocation |
| `src/fitcv_cp/local_setup.py` | provider/model validation and narrow overlay |
| `src/fitcv_cp/local_credentials.py` | OS credential storage |
| `src/fitcv_cp/local_routes.py` | onboarding, data, diagnostics, and shutdown UI |
| `packaging/windows/fitcv-local.spec` | PyInstaller onedir bundle |
| `packaging/windows/FitCV.iss` | per-user Windows installer |
| `start_web.ps1` | source FastAPI startup |
| `start_worker.ps1` | source Windows-safe RQ worker |
| `docker-compose.yml` | server `redis`, `web`, and `worker` services |

## OpenTelemetry Collector Setup

Developer/server mode may export telemetry in addition to persisted run artifacts:

```powershell
$env:FITCV_OTEL_ENABLED="true"
$env:FITCV_OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost/v1/traces"
$env:FITCV_OTEL_SERVICE_NAME="fitcv-control-plane"
```

Exporter failure is non-destructive. Stage artifacts remain authoritative.
