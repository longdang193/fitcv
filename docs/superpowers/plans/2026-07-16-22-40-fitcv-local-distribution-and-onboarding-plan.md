---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-local-distribution-and-onboarding
parent_thread: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
parent_spec: docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md
targets:
  - pyproject.toml
  - uv.lock
  - src/fitcv/config.py
  - src/fitcv/runtime_routing.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/local_app.py
  - src/fitcv_cp/local_storage.py
  - src/fitcv_cp/local_credentials.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/templates
  - packaging/windows
  - scripts/build_fitcv_local.ps1
  - scripts/smoke_fitcv_local.ps1
  - tests/test_fitcv_cp
  - tests/test_config.py
  - tests/test_runtime_routing.py
  - tests/test_deployment_config.py
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/settings_system/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/run_lifecycle_controls/feature.source.yaml
  - docs/intent/project-charter.md
  - docs/fitcv-control-plane-setup.md
  - docs/setup.md
  - docs/configuration.md
  - docs/usage.md
  - docs/architecture.md
  - README.md
related_features:
  - admin_control_plane_core
  - settings_system
  - trigger_run_management
  - run_lifecycle_controls
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Implementation Plan: FitCV Local Distribution And Onboarding

## Goal

Ship Windows-first **FitCV Local** as an installable local application using the
existing FastAPI/Jinja control plane and repo-owned pipeline. Packaged users
launch from Start menu, complete onboarding, select user-owned data location,
configure LLM provider and models, run one in-process job at a time, back up or
move data, download sanitized diagnostics, and shut down from web UI without
Docker, Redis, separate worker, Python, Git, `.env`, or terminal setup.

This is one-spec serial execution. No implementation execution map is needed.

Non-goals:

- rewrite UI with Electron, Tauri, or native Windows controls
- remove Docker/Redis/RQ server and developer modes
- add macOS/Linux packaging in this pass
- add background self-update
- add multi-user or parallel packaged execution
- restore any external `fitcv-langgraph` dependency or transport

## Key Deliverables

### Packaged local runtime

`fitcv-local.exe` owns single-instance startup, loopback socket, browser launch,
one serialized executor, graceful shutdown, and packaged-resource working directory.
Server/developer entrypoints retain current behavior.

### User-owned storage and configuration

Atomic bootstrap pointer selects one data root containing SQLite, candidate
profile, narrow provider/model overlay, run artifacts, logs, backups, and exports.
Relocation, backup, and restore preserve recoverability under failure.

### Guided setup and safe LLM routing

Resumable onboarding configures data location, candidate profile, OpenAI or
OpenAI-compatible provider, Credential Manager secret, default model, advanced
task overrides, and readiness. Pipeline execution reads same canonical routing
owner as UI writes.

### Complete local lifecycle

Local-only routes provide native folder selection, Data & Backup UI, sanitized
diagnostics, active-work guards, and shared packaged-mode web protection. Every
unsafe existing and new route uses same Host/Origin/CSRF contract.

### Reproducible Windows release

PyInstaller directory bundle plus Inno Setup installer, checksums, smoke script,
clean-machine checklist, focused tests, docs, and generated lineage prove release.

## Task/Wave Breakdown

### Task 1: Lock boundaries and dependency choices

**Purpose:**
- establish source-first impact, dependency ceiling, route names, and test seams before runtime edits

**Files:**
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/persistence.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_config.py`
- Verify: `tests/test_runtime_routing.py`

**Preconditions:**
- approved parent spec remains source of design truth
- current unrelated working-tree edits are recorded and preserved
- external `fitcv-langgraph` removal stays intact

**Steps:**
- [ ] Step 1: run GitNexus upstream impact for `build_app`, `create_app`, `load_control_plane_config`, `resolve_openai_compatible_api_key`, and `get_local_sqlite_path`; warn before HIGH/CRITICAL edits
- [ ] Step 2: record current inline-run, config-path, routing, settings-store, active-run, and template behavior with focused tests
- [ ] Step 3: add `keyring` as FitCV Local runtime dependency because safe Credential Manager access is not a few-line stdlib path
- [ ] Step 4: add PyInstaller as build-only dependency; keep Inno Setup external to runtime dependencies
- [ ] Step 5: freeze proposed local routes under `/local/*` and `/admin/system/*`; no duplicate public API family
- [ ] Step 6: record baseline machine and lock spec budgets: installed <= 600 MiB,
  idle RSS <= 250 MiB, health <= 8 seconds, first page <= 10 seconds

**Verification:**
- [ ] `uv lock --check`
- [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_main.py tests/test_config.py tests/test_runtime_routing.py -q`
- [ ] dependency review confirms `keyring` is runtime-only and PyInstaller is build-only

**Exit Criteria:**
- shared-symbol blast radius, dependency decisions, fixed performance budgets,
  and global route-security boundary are explicit

### Task 2: Add atomic user data-root bootstrap

**Purpose:**
- resolve all packaged mutable paths before database or settings initialization

**Files:**
- Create: `src/fitcv_cp/local_storage.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/persistence.py`
- Verify: `tests/test_fitcv_cp/test_local_storage.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 1 dependency and shared-symbol checks complete

**Steps:**
- [ ] Step 1: define `%APPDATA%\FitCV\bootstrap.json` schema with version, data-root path, and last application version only
- [ ] Step 2: implement UTF-8 JSON read plus same-directory temporary write, flush, `os.replace`, and malformed-file recovery
- [ ] Step 3: define default `%LOCALAPPDATA%\FitCV\data` layout for `fitcv.sqlite3`, `candidate_profile.yaml`, `config/local_routing_overlay.yaml`, `artifacts`, `exports`, `logs`, and `backups`
- [ ] Step 4: activate default root on first launch; allow change before first run
  and reject UNC, network, removable, relative, source-equal, non-writable, and
  insufficient-space destinations; require free space >= twice source size plus 512 MiB
- [ ] Step 5: create public-safe candidate profile only when absent; never copy
  full packaged control-plane config into user data
- [ ] Step 6: define versioned local overlay schema limited to `providers` and
  `model_routing.parts`; reject all other control-plane keys
- [ ] Step 7: merge packaged control-plane defaults plus local overlay inside
  `load_control_plane_config()` through one explicit precedence owner
- [ ] Step 8: set every packaged mutable root before app construction: SQLite,
  settings, entry config, candidate profile, artifacts, exports, logs, backups,
  uploads, and temporary work
- [ ] Step 9: add packaged write-boundary test proving no normal mutable write
  lands under bundle/install root
- [ ] Step 10: keep source/server default resolution unchanged when packaged-local mode is absent

**Verification:**
- [ ] bootstrap atomic-write failure leaves previous pointer readable
- [ ] malformed bootstrap falls back to safe recovery screen, not silent data-root replacement
- [ ] reinstall simulation reuses existing data root without overwriting user files
- [ ] upgraded packaged defaults apply automatically when overlay omits new key
- [ ] overlay rejects non-routing keys and full copied control-plane documents
- [ ] bundle/install root remains unchanged after onboarding and representative run
- [ ] existing config and persistence tests pass without packaged-local environment

**Exit Criteria:**
- application resolves one writable user root before any mutable store opens

### Task 3: Build packaged launcher and single-instance runtime

**Purpose:**
- start one loopback-bound FitCV process, one serialized executor, and existing browser UI without Redis/RQ services

**Files:**
- Create: `src/fitcv_cp/local_app.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`

**Preconditions:**
- Task 2 can resolve packaged paths before `build_app()`

**Steps:**
- [ ] Step 1: detect frozen bundle root and set packaged working directory before loading relative read-only resources
- [ ] Step 2: acquire Windows named mutex; second launch reads sanitized local runtime metadata, opens existing URL, and exits
- [ ] Step 3: create pre-bound `127.0.0.1` socket on port `0` and pass socket directly to programmatic Uvicorn server to avoid port race
- [ ] Step 4: persist sanitized URL/port/process metadata only; no browser login or one-time launch token exists
- [ ] Step 5: replace packaged daemon-per-enqueue threads with one process-owned
  `ThreadPoolExecutor(max_workers=1)` and one active/pending Future registry
- [ ] Step 6: reject additional pipeline submission while executor has queued or
  running work; reuse same busy state for background packaged jobs
- [ ] Step 7: force `FITCV_CP_INLINE_EXECUTION=1`, remove packaged `REDIS_URL`, and reject packaged attempts to enable queue mode
- [ ] Step 8: expose launcher shutdown callback and executor state through app state instead of route-level `os.kill` or process-name scanning
- [ ] Step 9: open existing local URL with `webbrowser.open`; normal route redirects incomplete setup to onboarding
- [ ] Step 10: on unexpected restart, invoke existing orphan reconciliation for interrupted packaged work
- [ ] Step 11: keep `uvicorn fitcv_cp.main:app`, Docker, and RQ worker entrypoints unchanged outside packaged mode

**Verification:**
- [ ] first launch starts one loopback socket and opens browser
- [ ] second launch does not create second app/database writer
- [ ] browser close leaves process and inline job alive
- [ ] rapid double submission starts one job and returns busy response for second
- [ ] packaged executor has at most one queued/running Future and no daemon job thread
- [ ] interrupted packaged run is reconciled on next startup
- [ ] packaged mode never calls `redis.from_url` or constructs RQ queue

**Exit Criteria:**
- one local process owns web server, inline job execution, and graceful stop signal

### Task 4: Add credential and LLM setup authority

**Purpose:**
- let UI configure provider/model routing without persisting API keys in FitCV data

**Files:**
- Create: `src/fitcv_cp/local_credentials.py`
- Create: `src/fitcv_cp/local_setup.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `config/runtime/control_plane.yaml`
- Verify: `tests/test_fitcv_cp/test_local_credentials.py`
- Verify: `tests/test_fitcv_cp/test_local_setup.py`
- Verify: `tests/test_runtime_routing.py`
- Verify: `tests/test_fitcv_cp/test_provider_routing.py`

**Preconditions:**
- Tasks 1-3 provide user config path and packaged runtime state

**Steps:**
- [ ] Step 1: store one credential per configured provider through `keyring`; service/account names are stable and contain no secret
- [ ] Step 2: expose set, replace, delete, and configured-state operations; no read-secret operation crosses route/template boundary
- [ ] Step 3: add local setup schema for provider type, display name, API-root
  base URL, `auth_mode: required | optional | none`, explicit wire API, timeout,
  default model, and four task overrides
- [ ] Step 4: reject operation endpoint URLs such as `/chat/completions`; normalize
  API root once and derive operation paths from wire API
- [ ] Step 5: write only narrow non-secret routing overlay with atomic YAML replacement and existing secret-hygiene validation
- [ ] Step 6: make `resolve_openai_compatible_api_key()` read Credential Manager only in packaged mode and preserve `FITCV_LLM_API_KEY` authority in server/developer mode
- [ ] Step 7: make same provider validator own auth requirement for readiness,
  connection test, discovery, and pipeline execution
- [ ] Step 8: implement provider test using existing internal LLM runtime transport, bounded timeout, normalized failure, and no raw response logging
- [ ] Step 9: discover models at `{base_url}/models`; fall back to validated manual model ID without adding provider SDKs
- [ ] Step 10: derive one readiness result for provider, auth mode, credential state, default model, four task routes, and representative request

**Verification:**
- [ ] secret canary absent from YAML, JSON, SQLite, logs, rendered HTML, diagnostics, and test backup archive
- [ ] OpenAI, authenticated compatible, and unauthenticated local compatible configurations resolve correctly
- [ ] endpoint-shaped base URLs reject; API-root URLs round-trip unchanged
- [ ] `required`, `optional`, and `none` auth modes produce same result across readiness, test, discovery, and runtime
- [ ] server mode still resolves `FITCV_LLM_API_KEY` and ignores local credential store
- [ ] invalid provider config fails before run creation with actionable reason

**Exit Criteria:**
- UI and pipeline share one non-secret routing file and one mode-specific credential authority

### Task 5: Implement resumable onboarding and readiness

**Purpose:**
- replace file and environment editing with one guided first-run flow

**Files:**
- Create: `src/fitcv_cp/local_routes.py`
- Create: `src/fitcv_cp/templates/local_onboarding.html`
- Modify: `src/fitcv_cp/local_setup.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/trigger.html`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 4 provides provider, credential, model, and readiness operations

**Steps:**
- [ ] Step 1: add local route registration through one `APIRouter`; `create_app()` includes it only when packaged-local context exists
- [ ] Step 2: add one packaged-mode middleware/dependency boundary validating
  loopback server mode, expected Host, and same-origin Origin/Referer
- [ ] Step 3: generate one per-process CSRF token, inject through shared template
  context/form helper, and require it for every unsafe existing and new route
- [ ] Step 4: add regression inventory covering all current `POST`, `PUT`, `PATCH`,
  and `DELETE` routes; no prefix-based security exception is allowed
- [ ] Step 5: persist onboarding progress as non-secret versioned JSON under data root with steps `welcome`, `data`, `profile`, `provider`, `models`, `review`, `complete`
- [ ] Step 6: implement native folder chooser using stdlib `tkinter.filedialog.askdirectory` in packaged Windows mode only; keep typed-path fallback for tests and inaccessible dialog cases
- [ ] Step 7: create candidate profile from public template or import YAML/JSON through existing candidate validation before atomic write
- [ ] Step 8: render provider test, discovered/manual model selection, default-model path, and Advanced task overrides
- [ ] Step 9: redirect incomplete onboarding state to onboarding while allowing health, static assets, and recovery routes
- [ ] Step 10: block trigger submission with explicit readiness reasons when profile or required LLM route is missing; do not block browsing existing runs

**Verification:**
- [ ] onboarding resumes exact last completed step after process restart
- [ ] malformed profile or provider input preserves draft and reports field-level error
- [ ] CSRF, wrong Host/Origin, and server-mode unsafe requests reject across existing and new routes
- [ ] second launch opens existing URL without cookie or token exchange
- [ ] completed onboarding reaches existing runs page without alternate product shell

**Exit Criteria:**
- new user configures application without terminal, `.env`, or YAML editing

### Task 6: Add data relocation, backup, and restore

**Purpose:**
- give user safe ownership and portability for complete FitCV data root

**Files:**
- Modify: `src/fitcv_cp/local_storage.py`
- Modify: `src/fitcv_cp/local_routes.py`
- Create: `src/fitcv_cp/templates/local_data_backup.html`
- Modify: `src/fitcv_cp/templates/base.html`
- Verify: `tests/test_fitcv_cp/test_local_storage.py`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Task 5 global packaged-mode web guard exists
- executor state plus run-status helper can report queued, running, cancelling, or awaiting-continue work

**Steps:**
- [ ] Step 1: add one active-work guard shared by backup, relocate, import, and shutdown; executor pending/running and paused/manual awaiting-continue count active until cancelled or completed
- [ ] Step 2: render resolved data root, database path, DB size, integrity state, and last backup time
- [ ] Step 3: define `fitcv-backup.v1` manifest with app version, data-layout version, DB schema version, creation time, included paths, byte sizes, and SHA-256 checksums
- [ ] Step 4: create SQLite snapshot with `sqlite3.Connection.backup()`; never raw-copy active DB/WAL/SHM files
- [ ] Step 5: export candidate profile, narrow routing overlay, and selected completed-run artifacts; exclude credentials, logs, backups, exports, temporary/runtime metadata, WAL/SHM, and incomplete-run artifacts
- [ ] Step 6: cap archive upload at 4 GiB, extracted content at 8 GiB, and one
  member at 2 GiB; reject symlinks, absolute paths, `..`, duplicate entries,
  checksum drift, and unsupported schema downgrade
- [ ] Step 7: persist pending import/relocation operation, return restart-required state, and shut application down cleanly
- [ ] Step 8: launcher stages import/relocation before DB initialization, validates checksums/schema/integrity, switches bootstrap pointer, starts app, and rolls pointer back if startup validation fails
- [ ] Step 9: never auto-delete old source; report old path and manual cleanup guidance

**Verification:**
- [ ] successful backup restores on fresh data root
- [ ] injected staging, ZIP validation, checksum, integrity, pointer, restart-validation, and rollback failures preserve recoverable source
- [ ] backup and diagnostics secret-canary scans return zero matches
- [ ] backup/relocation/import reject during every active lifecycle/executor state
- [ ] no hot path attempts to close all SQLite connections or rebind active process storage

**Exit Criteria:**
- user can back up, restore, and move complete data without silent loss or secret export

### Task 7: Add shutdown, diagnostics, and recovery surfaces

**Purpose:**
- complete local lifecycle and support from browser UI

**Files:**
- Modify: `src/fitcv_cp/local_app.py`
- Modify: `src/fitcv_cp/local_routes.py`
- Create: `src/fitcv_cp/templates/local_system.html`
- Create: `src/fitcv_cp/templates/local_stopped.html`
- Create: `src/fitcv_cp/templates/local_recovery.html`
- Modify: `src/fitcv_cp/templates/base.html`
- Verify: `tests/test_fitcv_cp/test_local_app.py`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 3, 5, and 6 provide launcher callback, global web guard, executor state, and active-work guard

**Steps:**
- [ ] Step 1: add menu items for Data & Backup, System, Change Log, and Shutdown only in packaged-local mode
- [ ] Step 2: implement POST-only confirmation shutdown that rejects executor/run activity, marks app draining, flushes logs/settings, returns stopped page, then signals Uvicorn exit
- [ ] Step 3: make shutdown callback idempotent and bounded; failed cleanup logs sanitized warning but does not leave launcher mutex permanently held
- [ ] Step 4: build diagnostics ZIP from allowlisted metadata and sanitized log tail; redact home path and URL credentials
- [ ] Step 5: expose application version, build ID, OS, data-path summary, DB schema/integrity, provider host, wire API, model IDs, and readiness only
- [ ] Step 6: show recovery page when bootstrap, data-root, config, credential backend, or SQLite open fails before normal app construction
- [ ] Step 7: verify browser close does nothing; only explicit guarded Shutdown exits app

**Verification:**
- [ ] idle shutdown closes port and releases named mutex with no FitCV process left
- [ ] repeat shutdown request is harmless
- [ ] active-run shutdown rejects and run remains healthy
- [ ] every existing and new unsafe route rejects missing/invalid CSRF in packaged mode
- [ ] diagnostics contain no profile, prompts, CV text, job descriptions, DB rows, authorization headers, or API keys

**Exit Criteria:**
- normal support and stop flows need no terminal or process manager

### Task 8: Build Windows bundle and installer

**Purpose:**
- produce reproducible installable artifacts with packaged resources and no runtime prerequisites

**Files:**
- Create: `packaging/windows/fitcv-local.spec`
- Create: `packaging/windows/FitCV.iss`
- Create: `packaging/windows/version_info.txt`
- Create: `scripts/build_fitcv_local.ps1`
- Create: `scripts/smoke_fitcv_local.ps1`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Verify: `tests/test_fitcv_local_packaging.py`
- Verify: `tests/test_deployment_config.py`

**Preconditions:**
- Tasks 2-7 run correctly from source in packaged-local mode

**Steps:**
- [ ] Step 1: add console entrypoint for `fitcv-local` targeting `fitcv_cp.local_app:main`
- [ ] Step 2: configure PyInstaller `onedir` bundle with templates, prompts, config defaults, candidate template, timezone data, Tcl/Tk assets, and keyring Windows backend
- [ ] Step 3: bundle Redis/RQ Python libraries when current imports require them but never start Redis service or RQ worker; remove libraries only after measured size failure justifies import-boundary refactor
- [ ] Step 4: make build script create clean bundle, record version/build ID, run import smoke, and emit SHA-256 checksums
- [ ] Step 5: create Inno Setup installer with per-user install, Start menu shortcut, optional desktop shortcut, Change Log link, and uninstall data-preservation default
- [ ] Step 6: sign public installer and executable; otherwise mark artifacts technical preview in filename, UI, and release notes
- [ ] Step 7: keep user bootstrap/data outside install directory and never delete it during normal uninstall
- [ ] Step 8: create smoke script covering first launch, health, onboarding redirect, global CSRF, second-instance reuse, busy-run rejection, idle shutdown, and post-shutdown port/process check
- [ ] Step 9: prove installed <= 600 MiB, idle RSS <= 250 MiB, health <= 8 seconds, and first page <= 10 seconds on documented baseline; spec revision required before any budget change

**Verification:**
- [ ] `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_fitcv_local.ps1`
- [ ] `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath <built-bundle>`
- [ ] unpacked bundle starts on clean Windows VM without Python, Git, Docker, Redis, or network
- [ ] installer upgrade preserves data; uninstall preserves data unless explicit delete selected
- [ ] public artifacts verify valid code signature or explicit technical-preview labeling

**Exit Criteria:**
- versioned installer, unpacked bundle, checksums, and smoke evidence exist

### Task 9: Align metadata, docs, and release proof

**Purpose:**
- publish truthful user setup and close implementation with focused evidence

**Files:**
- Modify: `docs/features/admin_control_plane_core/feature.source.yaml`
- Modify: `docs/features/settings_system/feature.source.yaml`
- Modify: `docs/features/trigger_run_management/feature.source.yaml`
- Modify: `docs/features/run_lifecycle_controls/feature.source.yaml`
- Modify: `docs/intent/project-charter.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `README.md`
- Modify: `docs/setup.md`
- Modify: `docs/configuration.md`
- Modify: `docs/usage.md`
- Modify: `docs/architecture.md`
- Modify: `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- Modify: `docs/superpowers/plans/2026-07-16-22-40-fitcv-local-distribution-and-onboarding-plan.md`
- Refresh: `docs/generated/planning_lineage.yaml`
- Refresh: `docs/generated/architecture_dag.yaml`
- Refresh: `docs/generated/capability_lineage.yaml`
- Create: `docs/intent/workstreams/checkpoints/workstream-operator-control-plane/fitcv-local-distribution-and-onboarding/<timestamp>.md`
- Verify: `scripts/validate_planning_lifecycle.py`
- Verify: `scripts/validate_repo_contracts.py`

**Preconditions:**
- Tasks 1-8 complete with clean-machine evidence

**Steps:**
- [ ] Step 1: document FitCV Local as primary non-technical path; keep Docker/server setup in separate developer section
- [ ] Step 2: update project charter and control-plane runbook so no active source claims external `fitcv-langgraph` or worker-first end-user setup
- [ ] Step 3: document data ownership, narrow overlay, credential boundary, backup/import/cold relocation, provider schema, global CSRF, shutdown, diagnostics, budgets, signing, update limits, and recovery
- [ ] Step 4: update human-owned feature sources with local packaging, onboarding, trigger readiness, data ownership, and shutdown capabilities
- [ ] Step 5: regenerate planning and architecture outputs from sources; never hand-edit generated meaning
- [ ] Step 6: add checkpoint result pack with installer/signature hash, clean-machine profile, fixed-budget results, smoke commands, secret scan, and known limitations
- [ ] Step 7: mark task checklists and plan status only after evidence exists; set thread terminal only with checkpoint pack
- [ ] Step 8: run GitNexus change detection and classify expected startup, config, routing, settings, lifecycle, packaging, docs, and test impact

**Verification:**
- [ ] public instructions contain no hidden Docker, Redis, worker, `.env`, repo checkout, or terminal prerequisite for FitCV Local
- [ ] project charter, control-plane runbook, root docs, and feature sources describe one internal runtime and same packaged workflow
- [ ] generated docs are clean after refresh
- [ ] planning lifecycle resolves thread, spec, plan, and checkpoint
- [ ] no active surface references external `fitcv-langgraph`

**Exit Criteria:**
- code, release artifact, docs, metadata, generated lineage, and checkpoint evidence agree

## Verification

Focused runtime and security:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_credentials.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_config.py tests/test_runtime_routing.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_local_packaging.py tests/test_deployment_config.py -q`

Dependency and package integrity:

- `uv lock --check`
- `uv run python -m pip check`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_fitcv_local.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath <built-bundle>`
- SHA-256 output matches installer and unpacked bundle artifacts

Security and residue:

- secret-canary test proves zero matches in user files, SQLite, logs, HTML, diagnostics, backup, and API responses
- archive tests reject absolute paths, traversal, symlinks, duplicate manifest entries, oversize content, and unsupported schema
- every packaged unsafe route rejects missing CSRF, wrong Host/Origin, and server mode; no prefix-only guard exists
- provider tests cover API-root URL plus `required`, `optional`, and `none` auth modes symmetrically
- local overlay tests reject full copied control-plane config and non-routing keys
- active-doc residue search covers `docs/intent/project-charter.md`, `docs/fitcv-control-plane-setup.md`, README, root product docs, feature sources, source, config, packaging, and scripts; archives, audit evidence, and superseded specs are excluded only by explicit globs
- `rg -n "REDIS_URL|rq worker|docker compose" packaging/windows scripts/build_fitcv_local.ps1 scripts/smoke_fitcv_local.ps1 README.md docs/setup.md docs/fitcv-control-plane-setup.md` confirms matches are absent from FitCV Local instructions or explicitly confined to developer/server sections

Clean-machine release proof:

- clean Windows VM has no Python, Git, Docker, Redis, or repo checkout
- installer launches onboarding from Start menu
- second launch reuses first instance
- OpenAI-compatible test route and one representative pipeline run succeed
- rapid second run submission returns busy state and never starts concurrent executor work
- browser close does not cancel run
- native SQLite backup restores into fresh data root
- cold relocation/import succeed and injected pre-open failure preserves source/pointer
- idle Shutdown closes port, exits process, and releases named mutex
- upgrade preserves data and user routing; uninstall preserves data by default
- installed <= 600 MiB, idle RSS <= 250 MiB, health <= 8 seconds, and first page <= 10 seconds on documented Windows 11 baseline
- public installer/executable signature verifies, or artifact is explicitly labeled technical preview

Docs and lifecycle:

- `.\.venv\Scripts\python.exe scripts\generate_planning_lineage.py`
- `.\.venv\Scripts\python.exe tools\docs\generate_architecture_metadata.py --check`
- `.\.venv\Scripts\python.exe scripts\validate_template_required_sections.py`
- `.\.venv\Scripts\python.exe scripts\validate_planning_lifecycle.py`
- `.\.venv\Scripts\python.exe scripts\validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py --fast`
- `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py`
- GitNexus `detect_changes(scope="all")` reports only expected local runtime, storage, routing, UI, lifecycle, packaging, tests, docs, and generated-lineage effects
- `git diff --check`
- `git status --short`

Rollback policy:

- packaged-local release can be withheld without reverting server/developer runtime
- failed upgrade or cold data migration restores previous bootstrap pointer and retained data copy before DB opens
- never roll back by restoring external `fitcv-langgraph`, bundled Redis, plaintext secrets, route-level process killing, or automatic old-data deletion

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. every task checklist and verification line is marked `- [x]`
3. every child item is `completed` or `dropped`
4. clean Windows install launches FitCV Local without Python, Git, Docker, Redis, worker, `.env`, repo checkout, or terminal setup
5. packaged mode runs one loopback-bound process and one serialized executor job at a time
6. second launch reuses current instance and browser close does not stop active work
7. packaged config remains canonical and narrow local routing overlay survives upgrades without forking unrelated defaults
8. user data root and bootstrap pointer survive reinstall, upgrade, cold relocation, import, and uninstall rules
9. candidate profile, explicit provider API root/auth mode/wire API, credential, default model, and advanced task routes are configurable through onboarding
10. credentials exist only in Windows Credential Manager and secret-canary proof passes
11. `fitcv-backup.v1`, native SQLite backup, cold restore, and cold relocation prove integrity, atomicity, traversal resistance, size bounds, and failure recovery
12. every unsafe packaged route uses same Host/Origin/CSRF contract; shutdown is active-work guarded, graceful, and idempotent
13. diagnostics are allowlisted and contain no personal or secret content
14. installed size/start/memory budgets pass without post-hoc revision
15. versioned bundle, signed public installer or labeled technical preview, checksums, release notes, and clean-machine checkpoint evidence exist
16. server/developer Docker and Redis/RQ modes retain current supported behavior
17. no external `fitcv-langgraph` dependency, mount, import, flag, or transport returns
18. project charter, control-plane runbook, feature sources, root docs, generated lineage, and runtime behavior agree
19. focused tests, packaging smoke, security scans, lifecycle validators, repo contracts, and GitNexus checks pass

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- `docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md`
- `docs/features/admin_control_plane_core/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/features/run_lifecycle_controls/feature.source.yaml`
- `docs/intent/project-charter.md`
- `docs/fitcv-control-plane-setup.md`
- `src/fitcv_cp/main.py`
- `src/fitcv_cp/app.py`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/config.py`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
