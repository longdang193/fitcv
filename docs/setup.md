---
doc_id: setup
doc_type: setup-guide
explains:
  features:
    - admin_control_plane_core
    - settings_system
    - trigger_run_management
  components:
    - src/fitcv
    - src/fitcv_cp
---

# Setup

FitCV Local is the primary setup path for Windows users. Developer and server
deployment stays available, but is not required for normal local use.

## 1) Install FitCV Local

1. Download `FitCV-Local-<version>-Technical-Preview-Setup.exe`.
2. Run per-user installer.
3. Keep Start menu shortcut; desktop shortcut is optional.
4. Launch **FitCV Local**; browser opens onboarding or the run dashboard.
5. FitCV Local adds a Windows notification-area icon with **Open FitCV** and **Shutdown FitCV** actions. You can also use **System → Shutdown** in the web UI.

Technical Preview is currently unsigned. Windows may show reputation warning.
Stable release requires signed executable and installer plus clean-Windows-VM
acceptance.

FitCV Local bundles application runtime. Users do not install Python, Git,
Docker, Redis, RQ, or repository dependencies.

## 2) Complete Onboarding

Browser onboarding is resumable and stores non-secret progress under selected
data root.

1. **Local data**: keep default `%LOCALAPPDATA%\FitCV\data`, or choose another
   writable absolute folder on local fixed disk before first run.
2. **Candidate profile**: review and save candidate YAML.
3. **LLM provider**: choose OpenAI, OpenAI-compatible, or 9router; enter API
   root, auth mode, wire API, timeout, API key, and default model.
4. **Models**: optionally discover provider models and assign task-specific
   models for enrichment, ranking, CV generation, and synonym triage.
5. **Run retry**: optionally retry whole failed runs using bounded attempts,
   backoff, lease, and reconciler settings from the controller.
6. **Prompt customization**: add up to 4000 characters of task guidance. FitCV
   inserts it before fixed JSON/schema instructions, which users cannot remove.
7. **Test and finish**: provider test and readiness checks must pass before run
   submission is enabled.

API keys go to Windows Credential Manager through OS keyring. They are not
written to candidate profile, routing overlay, database, diagnostics, or logs.

## 3) Data Ownership

`%APPDATA%\FitCV\bootstrap.json` stores only data-root pointer and minimal
version metadata. Selected data root owns:

- `fitcv.sqlite3`
- `candidate_profile.yaml`
- `config/local_controller_overlay.yaml`
- `artifacts/`, `exports/`, `logs/`, `backups/`, `uploads/`, and temporary files

Install and uninstall do not remove this user data. Reinstall preserves it.
A legacy `config/local_routing_overlay.yaml` is migrated once and retained as
`local_routing_overlay.yaml.migrated.bak` after successful validation.

## 4) Backup, Import, And Move

Open **Data & Backup** in FitCV Local:

- **Download backup** creates validated `fitcv-backup.v1` ZIP using SQLite
  online backup API.
- **Move data** stages cold relocation and restarts application.
- **Import backup** validates ZIP paths, links, duplicates, checksums, schema,
  SQLite integrity, and size limits before switching data root.

Move/import reject active work. Original source remains retained. Failed restart
validation restores prior bootstrap pointer.

## 5) Shutdown And Recovery

Use **System → Shutdown**. Shutdown is CSRF-protected, confirmation-gated, and
rejected while queued or running work exists. Accepted shutdown shows stopped
page, closes server, and exits process.

If selected data folder cannot open safely, FitCV shows recovery page and does
not delete existing data. Close FitCV, restore folder availability and write
access, then relaunch.

## 6) Developer / Server Setup

Engineering prerequisites:

- Python 3.11+
- Git
- Docker Desktop for container mode
- Redis for queued local/server mode

Clone and install:

```powershell
git clone https://github.com/longdang193/fitcv-public.git
cd fitcv-public
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Docker mode:

```powershell
docker compose up -d --build redis web worker
```

Source local mode:

```powershell
.\start_fitcv_dev.ps1
```

The single-command developer launcher starts FastAPI, waits for `/healthz`,
then starts Vite. It stops both processes on exit and prevents an unavailable
backend from becoming opaque frontend `Internal Server Error` responses.

For separate engineering processes:

```powershell
.\start_web.ps1
.\start_worker.ps1
```

Direct Windows web start without `REDIS_URL` uses inline execution. Configure
`REDIS_URL` only when queue mode is intentional.

## 7) Developer Configuration

- `.env.yaml`: bootstrap trigger input
- `.env`: untracked developer/server credential and environment values
- `config/dev-server.json`: source-mode host and port SSOT
- `config/runtime/control_plane.yaml`: canonical provider/model defaults
- `config/runtime/pipeline.yaml`: canonical pipeline execution settings
- `data/candidate_profile.yaml`: source-run candidate profile

FitCV Local does not require these files from user. It bundles read-only defaults
and stores narrow user-owned overlay under selected data root.

## 8) Validate

FitCV Local release budgets on documented Windows baseline:

- bundle/installed size: at most 600 MiB
- idle resident memory: at most 250 MiB
- health response: at most 8 seconds from launch
- first page: at most 10 seconds from launch

Developer health check:

```powershell
Invoke-WebRequest http://localhost:8000/healthz -UseBasicParsing
```

## Related Docs

- [fitcv-control-plane-setup.md](fitcv-control-plane-setup.md)
- [configuration.md](configuration.md)
- [usage.md](usage.md)
- [architecture.md](architecture.md)
